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
pip install -e .          # makes `impact_retrieval` importable (CLI, experiments, web)

# Target codebase (not committed)
git clone https://github.com/AbimanyuDA/Simple-ERP.git data/target_repo
```

Simple-ERP layout (what gets indexed):

| Path | Contents |
|---|---|
| `backend/internal/<module>/` | Go domain code: auth, finance, inventory, masterdata, purchasing, reporting, sales, platform |
| `backend/migrations/` | SQL migrations (DB tables) |
| `backend/test/` | Go integration tests |
| `frontend/app/`, `frontend/features/` | Next.js pages and feature modules (TS/TSX) |
| `api/openapi.yaml` | API routes |
| `docs/` | Simple-ERP's own BPMN models — **excluded from the index**, used only as scenario sources |

## Usage

```bash
pytest                                                   # all tests
uvicorn web.app:app --reload                             # website → http://127.0.0.1:8000

python -m impact_retrieval.pipeline S03                  # impact report for a scenario (BM25)
python -m impact_retrieval.pipeline S03 --method keyword -k 20
python -m impact_retrieval.pipeline old.bpmn new.bpmn --json

python experiments/run_eval.py                           # BM25 vs keyword vs TF-IDF on all scenarios
python experiments/build_scenarios.py                    # regenerate data/bpmn/scenarios
```

First results (default config, S01–S06, file level): BM25 F1@5 = 0.648, R@10 = 0.944, MRR = 1.00,
compared with keyword 0.465 / 0.692 / 0.78 and TF-IDF 0.560 / 0.861 / 1.00.
Details and threats to validity: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
Team task list: [`docs/TASKS.md`](docs/TASKS.md).

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
