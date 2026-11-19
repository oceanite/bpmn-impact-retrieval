# Final Report Outline — BPMN Change Impact Retrieval (Group 9)

Values marked **[TBD]** are filled in after the corresponding experiment (see `docs/results/`).

---

## Part 1. Report Structure

### Abstract
- Problem, approach (deterministic IR: BM25 vs keyword/grep baseline, TF-IDF), main result, limitation.

### 1. Introduction
1.1 Background: business process changes (BPMN) and their effect on code
1.2 Problem statement: given old/new BPMN, find files/functions likely affected
1.3 Objectives and research questions
- RQ1: Does BM25 outperform the keyword baseline?
- RQ2: Does task context (neighbor activities) improve the query?
- RQ3: Do synonym and Indonesian→English dictionaries help?
1.4 Scope and constraints (no LLM or agentic AI, target codebase Simple-ERP)
1.5 Contributions

### 2. Background and Related Work
2.1 BPMN 2.0 (tasks, gateways, events, sequence flows, lanes)
2.2 Change impact analysis
2.3 Information retrieval for traceability: TF-IDF, BM25, BM25F (field weights)
2.4 Evaluation metrics in IR (Precision@k, Recall@k, F1@k, MRR)

### 3. Methodology (system design)
3.1 Pipeline overview
3.2 BPMN parsing and diff (added / removed / modified)
3.3 Query building: roles, weights, ID cleaning, task context
3.4 Code extraction: documents (functions, components, routes, DB tables, tests, config) and fields
3.5 Preprocessing: identifier splitting, stopwords, stemming, synonyms, ID→EN dictionary
3.6 Retrieval methods: BM25F, TF-IDF, keyword baseline; deterministic tie-breaking
3.7 Impact report: file, function, score, evidence
3.8 Policy for new files (new-files limitation)

### 4. Dataset and Ground Truth
4.1 Target codebase: Simple-ERP (modules, size, languages)
4.2 Scenarios S01–S10: type of change per scenario
4.3 Ground truth construction (file/function level)
4.4 Independent review process and `REVIEW_LOG.md` (borderline rows)
4.5 Dev/test split, test set freeze, anti-leakage rules
4.6 Real BPMN pair from Simple-ERP history (demo only, no ground truth)

### 5. Implementation
5.1 Architecture and repository layout
5.2 Configuration (`config/default.yaml`, no hardcoded parameters)
5.3 Website: mapping page (diff view, ranked results, evidence), evaluation page, settings
5.4 Report download (CSV / JSON) and upload limits
5.5 Testing strategy (fixture-based unit tests, 135+ tests)

### 6. Evaluation
6.1 Experimental setup: metrics, k values {1, 3, 5, 10}, file vs function level, latency
6.2 Tuning protocol: grid search on k1, b, field weights with Leave-One-Scenario-Out (dev only)
6.3 Results on dev set: BM25 vs TF-IDF vs keyword [TBD]
6.4 Ablation: task context, synonyms, ID→EN dictionary, field weights [TBD]
6.5 Final result on frozen test set (S07–S10), run once [TBD]
6.6 Per-scenario analysis and error analysis (false positives / false negatives)

### 7. Discussion
7.1 Answers to RQ1–RQ3
7.2 Threats to validity: small dataset, ground truth subjectivity, single codebase, multilingual mismatch, new-files limitation, vacuous-pass tests
7.3 Practical usage and limitations

### 8. Conclusion and Future Work

### References
### Appendices
A. Default configuration
B. Scenario descriptions (S01–S10)
C. Ground truth table
D. Web user guide (screenshots)
E. Full metric tables

---

## Part 2. Required Tables and Figures

| # | Type | Content | Section |
|---|---|---|---|
| F1 | Figure | Pipeline diagram (BPMN → diff → query → index → rank → report) | 3.1 |
| F2 | Figure | Example BPMN old vs new with highlighted diff | 3.2 |
| F3 | Figure | System architecture (web → pipeline → modules) | 5.1 |
| F4 | Figure | Screenshots: mapping page, evaluation page | 5.3 |
| F5 | Chart | P@k / R@k / F1@k vs k, BM25 vs TF-IDF vs keyword | 6.3 |
| F6 | Chart | Per-scenario F1@5 comparison | 6.6 |
| F7 | Chart | Ablation: before/after each query feature | 6.4 |
| T1 | Table | Simple-ERP modules and indexed document counts | 4.1 |
| T2 | Table | Scenario list: ID, change type, split (dev/test), GT rows | 4.2 |
| T3 | Table | Document fields and BM25F default weights | 3.4 |
| T4 | Table | Query roles and weights (name, documentation, task_context, ...) | 3.3 |
| T5 | Table | Dev-set results (file and function level) [TBD] | 6.3 |
| T6 | Table | Ablation results [TBD] | 6.4 |
| T7 | Table | Test-set results [TBD] | 6.5 |
| T8 | Table | Latency per method | 6.1 |
| T9 | Table | Threats to validity and mitigations | 7.2 |

---

## Part 3. Presentation Skeleton (14 slides)

| # | Slide | Content | Visual |
|---|---|---|---|
| 1 | Title | Project name, Group 9, course, date | — |
| 2 | Problem | Process change → which code is affected? Cost of manual tracing | Simple before/after sketch |
| 3 | Objective and scope | Input/output, deterministic IR only, Simple-ERP | — |
| 4 | Pipeline overview | 6 stages | F1 |
| 5 | BPMN diff | Added/removed/modified elements | F2 |
| 6 | Query building | Roles, weights, task context, ID cleaning | T4 |
| 7 | Code indexing | Documents, fields, preprocessing | T3 |
| 8 | Retrieval methods | BM25F vs TF-IDF vs keyword baseline | Formula + short notes |
| 9 | Dataset and ground truth | S01–S10, dev/test split, independent review | T2 |
| 10 | Evaluation setup | Metrics, k, LOSO tuning, anti-leakage | — |
| 11 | Results | BM25 vs baselines, ablation | F5, F7 |
| 12 | Live demo | Mapping page → ranked results → download | Screenshots F4 |
| 13 | Limitations and threats | New files, small dataset, multilingual mismatch | T9 |
| 14 | Conclusion and future work | Answers to RQ1–RQ3, next steps | — |

Optional backup slides: per-scenario errors (F6), default configuration, test-set results.
