"""Grid-search BM25 k1 and b on the dev set (S01–S06).

Usage (from the repo root):
    python experiments/tune.py                        # default grid, optimise F1@5
    python experiments/tune.py --metric f1@10         # change optimisation target
    python experiments/tune.py --k1 0.5 1.0 1.5 2.0  # custom k1 values
    python experiments/tune.py --b 0.25 0.5 0.75      # custom b values

Writes per-combination rows to experiments/results/tune_results.csv.
Prints a table sorted by the chosen metric (best first) and the recommended config.
"""
from __future__ import annotations

import argparse
import csv
import sys
from itertools import product
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from impact_retrieval.evaluation import evaluate_all, summarize  # noqa: E402
from impact_retrieval.pipeline import ImpactPipeline             # noqa: E402

DEFAULT_K1 = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]
DEFAULT_B  = [0.0, 0.25, 0.5, 0.75, 1.0]

VALID_METRICS = {"f1@1", "f1@3", "f1@5", "f1@10",
                 "recall@1", "recall@3", "recall@5", "recall@10",
                 "mrr"}


def parse_metric(raw: str) -> tuple[str, int | None]:
    """Return (stat, k) e.g. ('f1', 5) or ('mrr', None)."""
    raw = raw.lower()
    if raw == "mrr":
        return "mrr", None
    if "@" in raw:
        stat, k = raw.split("@", 1)
        return stat, int(k)
    raise argparse.ArgumentTypeError(f"unrecognised metric {raw!r}; choose one of {sorted(VALID_METRICS)}")


def score_row(row: dict, stat: str, k: int | None) -> float:
    if stat == "mrr":
        return float(row["mrr"])
    return float(row[f"{stat}@{k}"])


def main() -> int:
    ap = argparse.ArgumentParser(description="Tune BM25 k1/b on the dev set")
    ap.add_argument("--metric", default="f1@5",
                    help="optimisation target: f1@k | recall@k | mrr (default: f1@5)")
    ap.add_argument("--k1", nargs="+", type=float, default=DEFAULT_K1, metavar="K1",
                    help="k1 values to try")
    ap.add_argument("--b", nargs="+", type=float, default=DEFAULT_B, metavar="B",
                    help="b values to try (each must be in [0, 1])")
    args = ap.parse_args()

    for v in args.b:
        if not 0.0 <= v <= 1.0:
            ap.error(f"b values must be in [0, 1], got {v}")

    stat, k = parse_metric(args.metric)
    combos = list(product(sorted(set(args.k1)), sorted(set(args.b))))
    total = len(combos)
    print(f"Tuning BM25 on dev set — {total} combinations, optimising {args.metric}\n")

    rows: list[dict] = []

    for idx, (k1, b) in enumerate(combos, 1):
        print(f"  [{idx:>2}/{total}] k1={k1:.2f}  b={b:.2f} ...", end=" ", flush=True)
        pipe = ImpactPipeline(overrides={"retrieval": {"bm25": {"k1": k1, "b": b}}})
        results = evaluate_all(pipe, ["bm25"], split="dev")
        summary = summarize(results, "file")

        row: dict = {"k1": k1, "b": b}
        for s in summary:
            row[f"p@{s['k']}"]      = round(s["precision"], 4)
            row[f"recall@{s['k']}"] = round(s["recall"], 4)
            row[f"f1@{s['k']}"]     = round(s["f1"], 4)
            row[f"fpr@{s['k']}"]    = round(s["fpr"], 5)
            row["mrr"]              = round(s["mrr"], 4)
            row["latency_ms"]       = round(s["latency_ms"], 1)
        rows.append(row)
        print(f"{args.metric}={score_row(row, stat, k):.4f}")

    rows.sort(key=lambda r: score_row(r, stat, k), reverse=True)

    out_dir = ROOT / "experiments" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "tune_results.csv"
    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    # --- summary table (top 10) ---
    print(f"\n## Top 10 by {args.metric} — file level, mean over dev set\n")
    header = f"| k1 | b | P@5 | R@5 | F1@5 | F1@10 | MRR | latency ms |"
    print(header)
    print("|---|---|---|---|---|---|---|---|")
    for r in rows[:10]:
        print(f"| {r['k1']:.2f} | {r['b']:.2f} | {r['p@5']:.3f} | {r['recall@5']:.3f} | "
              f"{r['f1@5']:.3f} | {r['f1@10']:.3f} | {r['mrr']:.3f} | {r['latency_ms']:.1f} |")

    best = rows[0]
    baseline_k1, baseline_b = 1.5, 0.75

    print(f"\n## Best config (by {args.metric})\n")
    print(f"  k1 = {best['k1']}  (baseline: {baseline_k1})")
    print(f"  b  = {best['b']}  (baseline: {baseline_b})")
    print(f"\n  To apply, update config/default.yaml — retrieval.bm25 section:")
    print(f"    bm25:")
    print(f"      k1: {best['k1']}")
    print(f"      b:  {best['b']}")
    print(f"\nAll results saved to {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
