# BPMN Change Impact Retrieval — Group 9

Given an old and a new version of a BPMN 2.0 process model, find the files and
functions in the **Simple-ERP** codebase that are most likely affected by the
change. The output is a ranked **impact report** with evidence — not code changes.

All methods are deterministic information retrieval (BM25, keyword/grep baseline,
optional TF-IDF). No LLMs or agentic AI.

## Pipeline

```
old.bpmn + new.bpmn
   │  1. parse & diff          → added / removed / modified elements
   │  2. build query           → tokens from changed element names/docs
   ▼
Simple-ERP source
   │  3. extract documents     → paths, functions/classes, API routes,
   │                             DB tables, comments, config, tests
   │  4. preprocess            → split camelCase/snake_case, lowercase,
   │                             stopwords, stemming
   ▼
   5. rank (BM25 vs baseline)
   6. impact report            → {file, function, score, evidence}
```

## Repository layout

| Path | Contents |
|---|---|
| `config/default.yaml` | All tunable parameters (k1, b, top-k, field weights, …) |
| `data/target_repo/` | Simple-ERP clone — **gitignored, never commit** |
| `data/bpmn/scenarios/<ID>/` | `old.bpmn`, `new.bpmn`, `scenario.md` per change scenario |
| `data/ground_truth/ground_truth.csv` | Answer key: `scenario_id,file_path,function` |
| `src/impact_retrieval/bpmn/` | BPMN parsing and diff |
| `src/impact_retrieval/query/` | Changed elements → text query |
| `src/impact_retrieval/code/` | Codebase extraction into documents |
| `src/impact_retrieval/preprocessing/` | Tokenization, identifier splitting, stemming |
| `src/impact_retrieval/retrieval/` | BM25, keyword baseline, TF-IDF |
| `src/impact_retrieval/report/` | Impact report construction |
| `src/impact_retrieval/evaluation/` | Precision@k, Recall@k, F1@k, MRR, FPR, latency |
| `src/impact_retrieval/pipeline.py` | Single entry point used by web and experiments |
| `web/` | FastAPI website (mapping + evaluation pages) |
| `experiments/` | Scripts for BM25 vs baseline comparisons |
| `tests/`, `tests/fixtures/` | Unit tests with small fixtures |
| `docs/` | Report and design notes |

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# Target codebase (not committed)
git clone <simple-erp-url> data/target_repo
```

## Usage

> Not implemented yet. Planned entry points:
>
> - `python -m impact_retrieval.pipeline --scenario <ID> --method bm25` — impact report for one scenario
> - `uvicorn web.app:app --reload` — website
> - `pytest` — tests

## Website (final deliverable)

- **Mapping page** — upload/select old + new BPMN, view detected changes and the
  ranked results with evidence; choose BM25 or baseline.
- **Evaluation page** — compare against the ground truth: TP/FP/FN per file,
  Precision@k, Recall@k, F1@k, MRR, FPR, latency; BM25 vs baseline side by side;
  adjustable k.
- **Settings** — k1, b, top-k, field weights.

## Conventions

- Every retrieval method implements `search(query, k) -> results`.
- The web layer calls `pipeline.py`; it never duplicates retrieval logic.
- Parameters come from `config/default.yaml`, never hardcoded.
- Same input → same ranking (deterministic tie-breaking).
- Parser, diff, preprocessing and metrics are covered by fixture-based tests.
