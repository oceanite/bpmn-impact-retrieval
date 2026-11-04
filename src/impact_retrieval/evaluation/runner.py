"""Run the pipeline over scenarios and score it against the ground truth (used by web + experiments)."""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Sequence

from ..config import resolve_path
from ..pipeline import ImpactPipeline
from ..types import ImpactReport
from .metrics import Evaluation, evaluate_ranking, load_ground_truth


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: str
    method: str
    report: ImpactReport
    file_level: Evaluation
    function_level: Evaluation


def evaluate_scenario(pipe: ImpactPipeline, scenario_id: str, method: str,
                      k_values: Sequence[int] | None = None) -> ScenarioResult:
    ev_cfg = pipe.cfg.get("evaluation", {})
    k_values = sorted(set(k_values or ev_cfg.get("k_values", [1, 3, 5, 10])))
    truth = load_ground_truth(resolve_path(pipe.cfg, "ground_truth")).get(scenario_id, [])
    # Retrieve deeper than max(k) so the file-level ranking (several docs per file) is filled.
    depth = max(int(ev_cfg.get("retrieve_depth", 100)), max(k_values))
    report = pipe.run_scenario(scenario_id, method=method, k=depth)
    ranked = [(r.document.path, r.document.function) for r in report.results]
    universe = [(d.path, d.function) for d in pipe.documents]
    return ScenarioResult(
        scenario_id, method, report,
        evaluate_ranking(ranked, truth, universe, k_values, "file"),
        evaluate_ranking(ranked, truth, universe, k_values, "function"))


def evaluate_all(pipe: ImpactPipeline, methods: Sequence[str], scenario_ids: Sequence[str] | None = None,
                 k_values: Sequence[int] | None = None) -> list[ScenarioResult]:
    ids = list(scenario_ids or pipe.scenarios())
    return [evaluate_scenario(pipe, s, m, k_values) for m in methods for s in ids]


def summarize(results: Sequence[ScenarioResult], level: str = "file") -> list[dict]:
    """Mean over scenarios, one row per (method, k)."""
    rows = []
    for method in dict.fromkeys(r.method for r in results):
        group = [r for r in results if r.method == method]
        evs = [r.file_level if level == "file" else r.function_level for r in group]
        for cut in evs[0].cutoffs:
            k = cut.k
            rows.append({
                "method": method, "level": level, "k": k,
                "precision": mean(e.at(k).precision for e in evs),
                "recall": mean(e.at(k).recall for e in evs),
                "f1": mean(e.at(k).f1 for e in evs),
                "fpr": mean(e.at(k).fpr for e in evs),
                "mrr": mean(e.mrr for e in evs),
                "latency_ms": mean(r.report.latency_ms for r in group),
            })
    return rows
