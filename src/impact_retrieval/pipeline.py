"""Single entry point: old/new BPMN -> diff -> query -> retrieval -> impact report.

The website and the experiment scripts call this module; they never re-implement any stage.

    >>> from impact_retrieval.pipeline import ImpactPipeline
    >>> report = ImpactPipeline().run_scenario("S01", method="bm25", k=10)
    >>> report.results[0].document.path

CLI::

    python -m impact_retrieval.pipeline S01 --method bm25 -k 10
    python -m impact_retrieval.pipeline path/old.bpmn path/new.bpmn --method keyword --json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Mapping, Sequence

from .bpmn import diff_models, parse_bpmn
from .code import extract_corpus
from .config import load_config, resolve_path
from .query import build_query
from .retrieval import METHODS, Retriever, make_retriever
from .types import CodeDocument, ImpactReport

_CORPUS_CACHE: dict[str, list[CodeDocument]] = {}
_INDEX_CACHE: dict[str, Retriever] = {}


def _key(*parts: object) -> str:
    return json.dumps(parts, sort_keys=True, default=str)


class ImpactPipeline:
    def __init__(self, cfg: Mapping | None = None, overrides: Mapping | None = None,
                 documents: Sequence[CodeDocument] | None = None):
        self.cfg = dict(cfg) if cfg is not None else load_config(overrides=overrides)
        self._documents = list(documents) if documents is not None else None

    # ---- corpus & indexes (cached per process) ---------------------------------------
    @property
    def documents(self) -> list[CodeDocument]:
        if self._documents is None:
            repo = resolve_path(self.cfg, "target_repo")
            key = _key(str(repo), self.cfg.get("code_extraction"))
            if key not in _CORPUS_CACHE:
                _CORPUS_CACHE[key] = extract_corpus(repo, self.cfg.get("code_extraction", {}))
            self._documents = _CORPUS_CACHE[key]
        return self._documents

    def retriever(self, method: str) -> Retriever:
        if method not in METHODS:
            raise ValueError(f"unknown method {method!r}; choose one of {METHODS}")
        key = _key(method, [d.doc_id for d in self.documents[:1]], len(self.documents),
                   self.cfg.get("preprocessing"), self.cfg.get("retrieval"), id(self._documents))
        if key not in _INDEX_CACHE:
            _INDEX_CACHE[key] = make_retriever(method, self.cfg).index(self.documents)
        return _INDEX_CACHE[key]

    # ---- running ---------------------------------------------------------------------
    def run(self, old: str | Path | bytes, new: str | Path | bytes, method: str | None = None,
            k: int | None = None) -> ImpactReport:
        """``old``/``new`` are BPMN file paths or raw bytes (e.g. web uploads)."""
        method = method or self.cfg["retrieval"].get("method", "bm25")
        k = int(k or self.cfg["retrieval"].get("top_k", 10))
        old_model, new_model = parse_bpmn(old), parse_bpmn(new)
        diff = diff_models(old_model, new_model)
        retriever = self.retriever(method)          # indexing is excluded from latency

        start = time.perf_counter()
        query = build_query(diff, old_model, new_model, self.cfg.get("query"))
        results = retriever.search(query, k) if not query.is_empty else []
        latency_ms = (time.perf_counter() - start) * 1000

        params = {"k": k, **({"k1": self.cfg["retrieval"]["bm25"]["k1"], "b": self.cfg["retrieval"]["bm25"]["b"],
                              "field_weights": self.cfg["retrieval"].get("field_weights")}
                             if method == "bm25" else {})}
        return ImpactReport(method=method, query=query, results=tuple(results), changes=diff,
                            latency_ms=latency_ms, params=params)

    def scenario_dir(self, scenario_id: str) -> Path:
        d = resolve_path(self.cfg, "scenarios") / scenario_id
        if not (d / "old.bpmn").is_file() or not (d / "new.bpmn").is_file():
            raise FileNotFoundError(f"scenario {scenario_id!r} needs old.bpmn and new.bpmn in {d}")
        return d

    def run_scenario(self, scenario_id: str, method: str | None = None, k: int | None = None) -> ImpactReport:
        d = self.scenario_dir(scenario_id)
        return self.run(d / "old.bpmn", d / "new.bpmn", method=method, k=k)

    def scenarios(self) -> list[str]:
        root = resolve_path(self.cfg, "scenarios")
        return sorted(p.name for p in root.iterdir() if (p / "old.bpmn").is_file() and (p / "new.bpmn").is_file())


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="BPMN change impact retrieval")
    ap.add_argument("inputs", nargs="+", help="scenario id (e.g. S01) or OLD.bpmn NEW.bpmn")
    ap.add_argument("--method", choices=METHODS)
    ap.add_argument("-k", type=int)
    ap.add_argument("--json", action="store_true", help="print the full report as JSON")
    args = ap.parse_args(argv)

    pipe = ImpactPipeline()
    if len(args.inputs) == 1:
        report = pipe.run_scenario(args.inputs[0], args.method, args.k)
    elif len(args.inputs) == 2:
        report = pipe.run(args.inputs[0], args.inputs[1], args.method, args.k)
    else:
        ap.error("give one scenario id or two BPMN files")
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return 0
    print(f"method={report.method}  changes={len(report.changes)}  latency={report.latency_ms:.1f} ms")
    print("query:", " | ".join(f"{p.text} ({p.role} {p.weight})" for p in report.query.parts))
    for r in report.results:
        top = ", ".join(f"{e.term}@{e.field}" for e in r.evidence[:4])
        print(f"{r.rank:>3}  {r.score:8.3f}  {r.document.path}::{r.document.function or '-'}  [{top}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
