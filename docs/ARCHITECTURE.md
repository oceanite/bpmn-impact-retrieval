# Architecture

```
 old.bpmn ─┐
           ├─ bpmn/parser.py ── BpmnModel ─┐
 new.bpmn ─┘                               ├─ bpmn/diff.py ── BpmnDiff ── query/builder.py ── Query ─┐
                                           │                                                         │
 data/target_repo ───────────────────┐                                                               │
                                     ├─ code/extractor.py ── [CodeDocument] ──┐                      │
 uploaded ZIP ── code/archive.py ────┘  (safe extract to a temp folder)       ▼                      │
                                                     retrieval/{bm25,keyword,tfidf}.py ◄─────────────┘
                                                                    │
                                                         [SearchResult] (score + evidence)
                                                                    │
                                    pipeline.py ── ImpactReport ────┼──► web/app.py (mapping page)
                                                                    └──► evaluation/runner.py ──► web (evaluation page)
                                                                                                └► experiments/run_eval.py
```

Every stage talks to the next one only through the types in `src/impact_retrieval/types.py`.
`pipeline.py` is the only place that wires stages together; the website and experiment scripts
call it and never re-implement a stage.

## Modules

| Module | Input → output | Notes |
|---|---|---|
| `bpmn/parser.py` | BPMN XML (path or bytes) → `BpmnModel` | Keeps semantics only (type, name, documentation, lane, parent, flow endpoints, condition, event definitions, default, calledElement). Ignores diagram layout. Safe XML parser (no entities/DTD/network) for uploads. |
| `bpmn/diff.py` | two models → `BpmnDiff` | Match by element id. Added / removed / modified with field-level changes. Fixed order. |
| `query/builder.py` | diff + both models → `Query` | Weighted text parts by role: `name`, `name_old`, `documentation`, `flow`, `flow_endpoint`, `lane`, `process`. BPMN ids (`SAL-SO-001`) stripped. Weights in `config.query.weights`. |
| `preprocessing/text.py` | text → tokens | Split camelCase/snake_case/kebab, lowercase, stopwords (English + `code_stopwords` + `bpmn_stopwords`), min length, Porter stemming. **Same analyzer for query and code.** |
| `code/extractor.py` | repo → `[CodeDocument]` | tree-sitter Go + TS/TSX. Units: Go function/method/type/test, TS function/component/type, OpenAPI path, SQL migration, config file. Fields below. |
| `retrieval/bm25.py` | `Query` → ranked `SearchResult`s | BM25F-style: field-weighted term frequency and length. Evidence = contribution per (term, field); sums to the score. |
| `retrieval/keyword.py` | same | Baseline: grep-like case-insensitive substring match, no splitting/stemming. Score = distinct query words found (+ occurrence tie-break). |
| `retrieval/tfidf.py` | same | Baseline: scikit-learn TF-IDF (sublinear tf) + cosine, same analyzer, no field weights. |
| `evaluation/metrics.py` | ranking + ground truth → metrics | P@k, R@k, F1@k, FPR@k, MRR at **file** and **function** level, TP/FP/FN lists. |
| `evaluation/runner.py` | pipeline + scenarios → results | Used by the website and `experiments/run_eval.py`. |
| `code/archive.py` | uploaded ZIP → folder | Safe extraction: rejects `../`, absolute/drive/UNC paths and symlinks; file-count and unzipped-size limits (`config.upload`). Unwraps a single top-level folder (GitHub "Download ZIP"). Code is parsed, never executed. |
| `pipeline.py` | old/new BPMN → `ImpactReport` | Caches corpora and indexes (LRU, 8 entries) keyed by a content fingerprint, so different codebases never share an index. `ImpactPipeline.from_zip(bytes)` targets an uploaded codebase. CLI: `python -m impact_retrieval.pipeline S01`. |
| `web/app.py` | HTTP | FastAPI + Jinja templates. Mapping, Evaluation, JSON API. |

### Document fields

| Field | Filled from | Default BM25 weight |
|---|---|---|
| `path` | directory names + file stem | 2.0 |
| `name` | function / method / component / type name (+ Go receiver type) | 3.0 |
| `route` | Go `r.Post("/x", h.fn)` registrations (attached to the handler and the registering function), API paths used in TS strings, OpenAPI paths | 2.0 |
| `db_table` | table names in SQL strings and migrations (`FROM/JOIN/INTO/UPDATE/TABLE/ON x`) | 2.0 |
| `comment` | doc comments above a declaration + comments inside it | 1.0 |
| `config` | flattened keys/values of YAML/JSON files | 1.0 |
| `test` | Go test function name; TS test/spec titles | 2.0 |
| `body` | identifiers + string literals (incl. SQL) + JSX text | 1.0 |

### Configuration notes
* `code_extraction.openapi_spec` is the OpenAPI file of Simple-ERP; for an uploaded codebase any file
  named in `code_extraction.openapi_filenames` (`openapi.yaml`, `swagger.yml`, …) is read as a spec too.
* `upload` limits what the website accepts: `max_bpmn_mb` per BPMN file, `max_zip_mb` for the
  compressed ZIP, `max_unzipped_mb` and `max_files` after extraction (zip-bomb guard).
  Violations are shown as an error on the mapping page, never as a crash.

### Data
| Path | Contents |
|---|---|
| `data/bpmn/scenarios/S01–S06` | Evaluation scenarios (dev set), generated by `experiments/build_scenarios.py` |
| `data/ground_truth/` | `ground_truth.csv` (41 rows) and the inclusion rules (`README.md`) |
| `data/bpmn/real/` | A real before/after pair from Simple-ERP's git history (Indonesian `bpm-haqi` model). **No ground truth**, ignored by `pipeline.scenarios()`; used as a demo upload. |

### Determinism
Files are walked in sorted order, units in source order, the diff is sorted, and every ranking
breaks score ties by `doc_id`. The same input and config always give the same ranking
(tests check this).

## Evaluation definitions
* **File level:** the document ranking is collapsed to unique files (first occurrence keeps its
  rank). Relevant = any file in the ground truth for the scenario.
* **Function level:** each document is judged on its own; a ground-truth row with an empty
  `function` matches every document of that file. Recall counts ground-truth rows found.
* `P@k = TP / k` (even if fewer than k results), `FPR@k = FP / negatives in the corpus`,
  `MRR = 1 / rank of the first relevant item`.
* `retrieve_depth` (default 100) documents are retrieved before collapsing to files.
* Latency = query building + search; one-time extraction and indexing are excluded.

## First results (default config, no tuning)

`python experiments/run_eval.py` on S01–S06:

| Level | Method | P@5 | R@5 | F1@5 | R@10 | MRR |
|---|---|---|---|---|---|---|
| file | **bm25** | **0.667** | **0.688** | **0.648** | **0.944** | **1.000** |
| file | tfidf | 0.567 | 0.609 | 0.560 | 0.861 | 1.000 |
| file | keyword | 0.467 | 0.516 | 0.465 | 0.692 | 0.778 |
| function | **bm25** | **0.633** | **0.537** | **0.527** | **0.749** | **0.917** |
| function | tfidf | 0.400 | 0.408 | 0.367 | 0.506 | 0.681 |
| function | keyword | 0.400 | 0.335 | 0.337 | 0.520 | 0.750 |

Search latency is ~2–3 ms (BM25) and ~11–12 ms (keyword, TF-IDF) per scenario.

### Threats to validity (put these in the report)
* Only 6 scenarios / 41 ground-truth rows; one scenario changes the mean a lot.
* Scenarios and ground truth were written by the same team that built the system, and the
  ground truth has not been reviewed by a second person yet.
* Parameters are defaults. If you tune k1, b or field weights on S01–S06, report results on
  scenarios that were **not** used for tuning (e.g. leave-one-scenario-out or new S07+).
* Impact on files that would have to be **created** (new migrations, new adapters) cannot be
  retrieved and is excluded from the ground truth (see `data/ground_truth/README.md`).
* Frontend UI text in Simple-ERP is Indonesian; queries from the English models do not match it.
* The reverse also holds: on the real Indonesian pair in `data/bpmn/real/`, BPMN labels match
  Indonesian UI text mostly through the word "dan" ("and"), because the stopword lists are English
  only. Indonesian stopwords and an ID → EN term list are open tasks (`docs/TASKS.md`, Orang 2).
* The ZIP upload has been tested on Simple-ERP itself and on the small fixture repo; results on
  other codebases are not evaluated (no ground truth).

## How to extend
* **New retrieval method:** subclass `retrieval.base.Retriever` (`index`, `search`), register it
  in `retrieval/__init__.py` (`METHODS`, `make_retriever`). The website and evaluation pick it up.
* **New document field:** add it to `types.FIELDS`, fill it in `code/extractor.py`, give it a
  weight in `config/default.yaml`.
* **New scenario:** add a function to `experiments/build_scenarios.py` (or hand-write
  `old.bpmn`/`new.bpmn`), add `scenario.md`, add ground-truth rows, extend
  `EXPECTED_SCENARIOS` in `tests/test_bpmn_diff.py`.
