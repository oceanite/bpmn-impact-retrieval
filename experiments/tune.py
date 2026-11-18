"""Grid-search BM25 k1/b on the dev set using Leave-One-Scenario-Out (LOSO).

For every (k1, b) combination the dev set is split 6 ways: each scenario is
held out once and scored; the other 5 form the implicit tuning fold. The LOSO
score is the mean of the 6 held-out scores. Only held-out scores are reported.

Usage (from the repo root):
    python experiments/tune.py                        # default grid, optimise F1@5
    python experiments/tune.py --metric recall@10
    python experiments/tune.py --with-synonyms        # test Person 2's synonym dict
    python experiments/tune.py --with-translation     # test Person 2's ID→EN dict
    python experiments/tune.py --with-synonyms --with-translation
    python experiments/tune.py --k1 0.9 1.2 1.5 2.0 --b 0.3 0.5 0.75 1.0

Writes per-combination rows to experiments/results/tune_results.csv.
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

from impact_retrieval.evaluation import evaluate_scenario, split_scenarios  # noqa: E402
from impact_retrieval.evaluation import summarize                            # noqa: E402
from impact_retrieval.pipeline import ImpactPipeline                        # noqa: E402

# Default grid as specified in docs/TASKS.md
DEFAULT_K1 = [0.9, 1.2, 1.5, 2.0]
DEFAULT_B  = [0.3, 0.5, 0.75, 1.0]

VALID_METRICS = {"f1@1", "f1@3", "f1@5", "f1@10",
                 "recall@1", "recall@3", "recall@5", "recall@10", "mrr"}


def parse_metric(raw: str) -> tuple[str, int | None]:
    raw = raw.lower()
    if raw == "mrr":
        return "mrr", None
    if "@" in raw:
        stat, k = raw.split("@", 1)
        return stat, int(k)
    raise argparse.ArgumentTypeError(
        f"unrecognised metric {raw!r}; choose one of {sorted(VALID_METRICS)}")


def score_from_eval(result, stat: str, k: int | None, level: str = "file") -> float:
    ev = result.file_level if level == "file" else result.function_level
    if stat == "mrr":
        return ev.mrr
    return ev.at(k).f1 if stat == "f1" else ev.at(k).recall


def main() -> int:
    ap = argparse.ArgumentParser(description="Tune BM25 k1/b via LOSO on the dev set")
    ap.add_argument("--metric", default="f1@5",
                    help="optimisation target: f1@k | recall@k | mrr (default: f1@5)")
    ap.add_argument("--k1", nargs="+", type=float, default=DEFAULT_K1, metavar="K1")
    ap.add_argument("--b",  nargs="+", type=float, default=DEFAULT_B,  metavar="B")
    ap.add_argument("--with-synonyms",   action="store_true",
                    help="enable preprocessing.use_synonyms (test Person 2's synonym dict)")
    ap.add_argument("--with-translation", action="store_true",
                    help="enable preprocessing.use_translation (test Person 2's ID→EN dict)")
    args = ap.parse_args()

    for v in args.b:
        if not 0.0 <= v <= 1.0:
            ap.error(f"b values must be in [0, 1], got {v}")

    stat, k = parse_metric(args.metric)
    combos = list(product(sorted(set(args.k1)), sorted(set(args.b))))
    total = len(combos)

    # Build preprocessing overrides once (shared across all combos)
    pre_overrides: dict = {}
    if args.with_synonyms:
        pre_overrides["use_synonyms"] = True
    if args.with_translation:
        pre_overrides["use_translation"] = True

    # Discover dev scenarios using a plain pipeline (no retrieval override needed here)
    base_pipe = ImpactPipeline(overrides={"preprocessing": pre_overrides} if pre_overrides else None)
    dev_scenarios = split_scenarios(base_pipe, "dev")

    flags = []
    if args.with_synonyms:
        flags.append("synonyms")
    if args.with_translation:
        flags.append("translation")
    flag_str = f" [{', '.join(flags)}]" if flags else ""
    print(f"LOSO tuning — {total} combos × {len(dev_scenarios)} folds, "
          f"optimising {args.metric}{flag_str}\n")

    rows: list[dict] = []

    for idx, (k1, b) in enumerate(combos, 1):
        overrides: dict = {"retrieval": {"bm25": {"k1": k1, "b": b}}}
        if pre_overrides:
            overrides["preprocessing"] = pre_overrides

        pipe = ImpactPipeline(overrides=overrides)

        # LOSO: evaluate on each held-out scenario independently
        held_out_results = []
        for held_out in dev_scenarios:
            held_out_results.append(evaluate_scenario(pipe, held_out, "bm25"))

        # Aggregate held-out scores (mean over the 6 folds)
        loso_score = mean(score_from_eval(r, stat, k) for r in held_out_results)
        summary = summarize(held_out_results, "file")

        row: dict = {"k1": k1, "b": b}
        for s in summary:
            row[f"p@{s['k']}"]      = round(s["precision"], 4)
            row[f"recall@{s['k']}"] = round(s["recall"], 4)
            row[f"f1@{s['k']}"]     = round(s["f1"], 4)
            row[f"fpr@{s['k']}"]    = round(s["fpr"], 5)
            row["mrr"]              = round(s["mrr"], 4)
            row["latency_ms"]       = round(s["latency_ms"], 1)
        rows.append(row)

        print(f"  [{idx:>2}/{total}] k1={k1:.2f}  b={b:.2f}  LOSO {args.metric}={loso_score:.4f}")

    def row_score(r: dict) -> float:
        if stat == "mrr":
            return r["mrr"]
        return r[f"{stat}@{k}"]

    rows.sort(key=row_score, reverse=True)

    out_dir = ROOT / "experiments" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = ("_" + "_".join(flags)) if flags else ""
    out_path = out_dir / f"tune_results{suffix}.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"\n## Top 10 by LOSO {args.metric} — file level{flag_str}\n")
    print("| k1 | b | P@5 | R@5 | F1@5 | F1@10 | MRR | latency ms |")
    print("|---|---|---|---|---|---|---|---|")
    for r in rows[:10]:
        print(f"| {r['k1']:.2f} | {r['b']:.2f} | {r['p@5']:.3f} | {r['recall@5']:.3f} | "
              f"{r['f1@5']:.3f} | {r['f1@10']:.3f} | {r['mrr']:.3f} | {r['latency_ms']:.1f} |")

    best = rows[0]
    print(f"\n## Best config (LOSO {args.metric}){flag_str}\n")
    print(f"  k1 = {best['k1']}  |  b = {best['b']}")
    print(f"\n  Update config/default.yaml — retrieval.bm25:")
    print(f"    bm25:")
    print(f"      k1: {best['k1']}")
    print(f"      b:  {best['b']}")
    print(f"\nAll results saved to {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
