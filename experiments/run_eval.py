"""Evaluate every method on every scenario and print BM25 vs baselines.

Usage (from the repo root):
    python experiments/run_eval.py                 # all scenarios, all methods
    python experiments/run_eval.py --level function --methods bm25 keyword

Writes per-scenario rows to experiments/results/metrics.csv (gitignored).
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from impact_retrieval.evaluation import evaluate_all, summarize  # noqa: E402
from impact_retrieval.pipeline import ImpactPipeline  # noqa: E402
from impact_retrieval.retrieval import METHODS  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--methods", nargs="+", default=list(METHODS), choices=METHODS)
    ap.add_argument("--scenarios", nargs="+")
    ap.add_argument("--level", choices=["file", "function", "both"], default="both")
    args = ap.parse_args()

    pipe = ImpactPipeline()
    results = evaluate_all(pipe, args.methods, args.scenarios)

    out = ROOT / "experiments" / "results"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "metrics.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["scenario", "method", "level", "k", "precision", "recall", "f1", "fpr", "mrr", "latency_ms"])
        for r in results:
            for ev in (r.file_level, r.function_level):
                for c in ev.cutoffs:
                    w.writerow([r.scenario_id, r.method, ev.level, c.k, f"{c.precision:.4f}", f"{c.recall:.4f}",
                                f"{c.f1:.4f}", f"{c.fpr:.4f}", f"{ev.mrr:.4f}", f"{r.report.latency_ms:.2f}"])

    levels = ["file", "function"] if args.level == "both" else [args.level]
    for level in levels:
        print(f"\n## Mean over {len({r.scenario_id for r in results})} scenarios - {level} level\n")
        print("| method | k | P@k | R@k | F1@k | FPR@k | MRR | latency ms |")
        print("|---|---|---|---|---|---|---|---|")
        for row in summarize(results, level):
            print(f"| {row['method']} | {row['k']} | {row['precision']:.3f} | {row['recall']:.3f} | {row['f1']:.3f} "
                  f"| {row['fpr']:.4f} | {row['mrr']:.3f} | {row['latency_ms']:.1f} |")

    print("\n## MRR per scenario (file level)\n")
    ids = list(dict.fromkeys(r.scenario_id for r in results))
    print("| method | " + " | ".join(ids) + " |")
    print("|---|" + "---|" * len(ids))
    for m in args.methods:
        cells = [next(r for r in results if r.method == m and r.scenario_id == s).file_level.mrr for s in ids]
        print(f"| {m} | " + " | ".join(f"{c:.2f}" for c in cells) + " |")
    print(f"\nper-scenario rows: {out / 'metrics.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
