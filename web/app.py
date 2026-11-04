"""FastAPI website. Thin layer: every result comes from impact_retrieval.pipeline / .evaluation.

Run from the repo root:
    uvicorn web.app:app --reload
then open http://127.0.0.1:8000
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile  # noqa: E402
from fastapi.responses import HTMLResponse  # noqa: E402
from fastapi.templating import Jinja2Templates  # noqa: E402

from impact_retrieval.bpmn import BpmnParseError  # noqa: E402
from impact_retrieval.config import load_config  # noqa: E402
from impact_retrieval.evaluation import evaluate_all, summarize  # noqa: E402
from impact_retrieval.pipeline import ImpactPipeline  # noqa: E402
from impact_retrieval.retrieval import METHODS  # noqa: E402
from impact_retrieval.types import FIELDS  # noqa: E402

MAX_UPLOAD_BYTES = 5 * 1024 * 1024

app = FastAPI(title="BPMN Change Impact Retrieval")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
DEFAULTS = load_config()


def _overrides(k1: float | None, b: float | None, top_k: int | None, weights: dict[str, float]) -> dict:
    """Settings form -> config overrides (only values the user actually set)."""
    retrieval: dict[str, Any] = {}
    bm25 = {key: val for key, val in (("k1", k1), ("b", b)) if val is not None}
    if bm25:
        retrieval["bm25"] = bm25
    if top_k:
        retrieval["top_k"] = top_k
    if weights:
        retrieval["field_weights"] = weights
    return {"retrieval": retrieval} if retrieval else {}


def _weights_from(form: dict) -> dict[str, float]:
    out = {}
    for f in FIELDS:
        raw = form.get(f"w_{f}")
        if raw not in (None, ""):
            out[f] = float(raw)
    return out


def _settings_context(cfg: dict) -> dict:
    r = cfg["retrieval"]
    return {"k1": r["bm25"]["k1"], "b": r["bm25"]["b"], "top_k": r["top_k"],
            "weights": {f: r["field_weights"].get(f, 1.0) for f in FIELDS}}


# --------------------------------------------------------------------------- mapping page

@app.get("/", response_class=HTMLResponse)
def mapping_form(request: Request):
    pipe = ImpactPipeline(cfg=DEFAULTS)
    return templates.TemplateResponse(request, "mapping.html", {
        "scenarios": pipe.scenarios(), "methods": METHODS, "report": None, "error": None,
        "selected": {"scenario": "", "method": DEFAULTS["retrieval"]["method"]},
        "settings": _settings_context(DEFAULTS), "fields": FIELDS})


@app.post("/", response_class=HTMLResponse)
async def mapping_run(request: Request, scenario: str = Form(""), method: str = Form("bm25"),
                      old_file: UploadFile | None = File(None), new_file: UploadFile | None = File(None),
                      k1: float | None = Form(None), b: float | None = Form(None), top_k: int | None = Form(None)):
    form = dict(await request.form())
    cfg = load_config(overrides=_overrides(k1, b, top_k, _weights_from(form)))
    pipe = ImpactPipeline(cfg=cfg)
    report, error = None, None
    try:
        old_bytes = await _read_upload(old_file)
        new_bytes = await _read_upload(new_file)
        if old_bytes and new_bytes:
            report = pipe.run(old_bytes, new_bytes, method=method)
        elif scenario:
            report = pipe.run_scenario(scenario, method=method)
        else:
            error = "Choose a scenario or upload both an old and a new BPMN file."
    except (BpmnParseError, FileNotFoundError, ValueError) as exc:
        error = str(exc)
    return templates.TemplateResponse(request, "mapping.html", {
        "scenarios": pipe.scenarios(), "methods": METHODS, "report": report, "error": error,
        "selected": {"scenario": scenario, "method": method},
        "settings": _settings_context(cfg), "fields": FIELDS})


async def _read_upload(upload: UploadFile | None) -> bytes | None:
    if upload is None or not upload.filename:
        return None
    data = await upload.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"{upload.filename} is larger than 5 MB")
    return data


# --------------------------------------------------------------------------- evaluation page

@app.get("/evaluation", response_class=HTMLResponse)
def evaluation(request: Request, k: int = 5, level: str = "file", k1: float | None = None,
               b: float | None = None):
    if level not in ("file", "function"):
        raise HTTPException(400, "level must be file or function")
    cfg = load_config(overrides=_overrides(k1, b, None, _weights_from(dict(request.query_params))))
    k_values = sorted({1, 3, 5, 10, k})
    cfg["evaluation"]["k_values"] = k_values
    pipe = ImpactPipeline(cfg=cfg)
    results = evaluate_all(pipe, METHODS, k_values=k_values)
    summary = [row for row in summarize(results, level) if row["k"] == k]
    per_scenario: dict[str, dict[str, Any]] = {}
    for r in results:
        ev = r.file_level if level == "file" else r.function_level
        per_scenario.setdefault(r.scenario_id, {})[r.method] = {"cut": ev.at(k), "mrr": ev.mrr,
                                                                "latency": r.report.latency_ms}
    return templates.TemplateResponse(request, "evaluation.html", {
        "k": k, "level": level, "methods": METHODS, "summary": summary, "per_scenario": per_scenario,
        "settings": _settings_context(cfg), "fields": FIELDS})


# --------------------------------------------------------------------------- JSON API

@app.get("/api/scenarios/{scenario_id}")
def api_scenario(scenario_id: str, method: str = "bm25", k: int = 10):
    try:
        return ImpactPipeline(cfg=DEFAULTS).run_scenario(scenario_id, method=method, k=k).to_dict()
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/evaluation")
def api_evaluation(level: str = "file"):
    pipe = ImpactPipeline(cfg=DEFAULTS)
    return summarize(evaluate_all(pipe, METHODS), level)
