"""Ranking metrics against the ground truth.

Two match levels:

* ``file``     - results are collapsed to a ranked list of unique files (first occurrence wins).
                 A file is relevant if any ground-truth row names it.
* ``function`` - each retrieved document is judged on its own. A document is relevant if it
                 matches a row: same path and same function, or the row's function is empty
                 (whole-file impact). Recall counts ground-truth rows found.

At cut-off k::

    P@k   = TP / k
    R@k   = relevant found in top k / all relevant
    F1@k  = harmonic mean of P@k and R@k
    FPR@k = FP / (negatives in the corpus)
    MRR   = 1 / rank of the first relevant item (0 if none); one value per query
"""
from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class GroundTruthRow:
    scenario_id: str
    file_path: str
    function: str        # "" = whole file

    def matches(self, path: str, function: str) -> bool:
        return path == self.file_path and (not self.function or function == self.function)


def load_ground_truth(path: str | Path) -> dict[str, list[GroundTruthRow]]:
    rows: dict[str, list[GroundTruthRow]] = defaultdict(list)
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows[r["scenario_id"].strip()].append(
                GroundTruthRow(r["scenario_id"].strip(), r["file_path"].strip(), (r.get("function") or "").strip()))
    return dict(rows)


@dataclass(frozen=True)
class CutoffMetrics:
    k: int
    precision: float
    recall: float
    f1: float
    fpr: float
    tp: tuple[str, ...]      # relevant items retrieved in top k
    fp: tuple[str, ...]      # non-relevant items retrieved in top k
    fn: tuple[str, ...]      # relevant items (or GT rows) not retrieved in top k

    def to_dict(self) -> dict:
        return {"k": self.k, "precision": self.precision, "recall": self.recall, "f1": self.f1,
                "fpr": self.fpr, "tp": list(self.tp), "fp": list(self.fp), "fn": list(self.fn)}


@dataclass(frozen=True)
class Evaluation:
    level: str
    mrr: float
    first_relevant_rank: int | None
    cutoffs: tuple[CutoffMetrics, ...]

    def at(self, k: int) -> CutoffMetrics:
        return next(c for c in self.cutoffs if c.k == k)

    def to_dict(self) -> dict:
        return {"level": self.level, "mrr": self.mrr, "first_relevant_rank": self.first_relevant_rank,
                "cutoffs": [c.to_dict() for c in self.cutoffs]}


def _f1(p: float, r: float) -> float:
    return 2 * p * r / (p + r) if p + r else 0.0


def _label(path: str, function: str) -> str:
    return f"{path}::{function}" if function else path


def evaluate_ranking(ranked: Sequence[tuple[str, str]], truth: Sequence[GroundTruthRow],
                     universe: Iterable[tuple[str, str]], k_values: Sequence[int],
                     level: str = "file") -> Evaluation:
    """``ranked``: retrieved (path, function) in rank order. ``universe``: every (path, function) in the corpus."""
    if level == "file":
        return _evaluate_files(ranked, truth, {p for p, _ in universe}, k_values)
    if level == "function":
        return _evaluate_functions(ranked, truth, list(universe), k_values)
    raise ValueError("level must be 'file' or 'function'")


def _evaluate_files(ranked, truth, universe_files: set[str], k_values) -> Evaluation:
    files = list(dict.fromkeys(p for p, _ in ranked))
    relevant = {r.file_path for r in truth}
    negatives = max(len(universe_files | relevant) - len(relevant), 1)
    first = next((i + 1 for i, f in enumerate(files) if f in relevant), None)
    cutoffs = []
    for k in k_values:
        top = files[:k]
        tp = [f for f in top if f in relevant]
        fp = [f for f in top if f not in relevant]
        fn = sorted(relevant - set(top))
        p, r = len(tp) / k, (len(tp) / len(relevant) if relevant else 0.0)
        cutoffs.append(CutoffMetrics(k, p, r, _f1(p, r), len(fp) / negatives, tuple(tp), tuple(fp), tuple(fn)))
    return Evaluation("file", 1 / first if first else 0.0, first, tuple(cutoffs))


def _evaluate_functions(ranked, truth, universe, k_values) -> Evaluation:
    def is_relevant(path, function):
        return any(row.matches(path, function) for row in truth)

    relevant_docs = sum(1 for p, f in universe if is_relevant(p, f))
    negatives = max(len(universe) - relevant_docs, 1)
    first = next((i + 1 for i, (p, f) in enumerate(ranked) if is_relevant(p, f)), None)
    cutoffs = []
    for k in k_values:
        top = list(ranked[:k])
        tp = [_label(p, f) for p, f in top if is_relevant(p, f)]
        fp = [_label(p, f) for p, f in top if not is_relevant(p, f)]
        found = [row for row in truth if any(row.matches(p, f) for p, f in top)]
        fn = [_label(row.file_path, row.function) for row in truth if row not in found]
        p, r = len(tp) / k, (len(found) / len(truth) if truth else 0.0)
        cutoffs.append(CutoffMetrics(k, p, r, _f1(p, r), len(fp) / negatives, tuple(tp), tuple(fp), tuple(fn)))
    return Evaluation("function", 1 / first if first else 0.0, first, tuple(cutoffs))
