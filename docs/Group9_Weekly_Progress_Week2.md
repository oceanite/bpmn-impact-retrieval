# BPMN Change Impact Retrieval — Weekly Progress (Week 2)
**Group:** 9 · Software Engineering (Semester 7)  
**Date:** 19 November 2026  
**Target Milestone:** Milestone M2 (Query Enhancements, Frozen Test Set, & Web UI Polish)  
**Repository Status:** 100% CI pass rate (136 unit tests) · All 6 PRs merged into `main` · Live web dashboard active  

---

## 1. Executive Summary

During Week 2 (Milestone M2), Group 9 successfully transitioned the initial end-to-end prototype into an optimized, robust retrieval system with empirical validation and production-ready web tooling.

### Key Highlights:
1. **PIC Feedback Implemented:** Successfully incorporated **Task Context** (neighboring activity traversal) into the query builder, producing a pure **+2.8 percentage point increase in File-level F1@5** (0.657 $\rightarrow$ 0.685).
2. **Cross-Language Mismatch Solved:** Developed domain synonym normalization and an **Indonesian $\rightarrow$ English** business dictionary. On real Indonesian BPMN models (`data/bpmn/real/`), every Indonesian business term was correctly translated to English code identifiers, accurately promoting `backend/cmd/api/main.go` to rank #1.
3. **Rigorous Anti-Leakage & Ground Truth Validation:** Completed an independent second review of all **69 ground-truth rows** against the Simple-ERP codebase (`c76a313`). **Test Set S07–S10 is officially frozen** and was never evaluated or tuned against.
4. **BM25 Parameter Optimization:** Hyperparameter tuning on the dev set improved length normalization, lifting overall File-level **F1@5 from 0.657 to 0.750 (+9.3pp)**, Recall@5 from 0.667 to **0.756 (+8.9pp)**, and maintaining a perfect **MRR of 1.000**.
5. **Interactive Web Interface & Exports:** Upgraded the web interface with semantic, color-coded BPMN diff views (🟢 Added, 🔴 Removed, 🟡 Modified), upload file size indicators, and 1-click **CSV / JSON impact report downloads**.

---

## 2. Completed Pull Requests & Changelog

All team members completed their assigned M2 tasks via structured branches and clean Pull Requests:

| PR # | Branch | Author | Key Deliverables |
|---|---|---|---|
| **PR #1** | `feat/task-context` | Orang 2 (Sinta) | Task context query role (`task_context: 0.3`), domain synonyms, and Indonesian $\rightarrow$ English dictionary. |
| **PR #2** | `docs/gt-review` | Orang 3 (Bella) | Ground truth review 2 in `REVIEW_LOG.md`, BM25 grid search script `tune.py`, and initial tuned metrics report. |
| **PR #3** | `docs/gt-review` | Orang 3 (Bella) | Leave-One-Scenario-Out (LOSO) cross-validation framework and `--with-synonyms` / `--with-translation` CLI flags in `tune.py`. |
| **PR #4** | `feat/task-context` | Orang 2 (Sinta) | Comprehensive Week 2 evaluation report (`docs/results/week2.md`) with isolated attribution and real BPMN test. |
| **PR #5** | `docs/report-outline` | Orang 4 | Final report structure (`docs/report/outline.md`): 8 chapters, 3 Research Questions, 7 charts, and 9 tables. |
| **PR #6** | `feat/web-download` | Orang 4 | Color-coded diff view by element type, `/download/csv` and `/download/json` endpoints, and upload limits. |

---

## 3. Core Empirical Results & Ablation Decomposition

All quantitative evaluations were conducted exclusively on the **Development Set (`S01`–`S06`, 50 ground-truth rows)** against the Simple-ERP target codebase. The held-out **Test Set (`S07`–`S10`) remains strictly un-evaluated until Milestone M4**.

### Full Decomposition Table (File Level, Mean over Dev Set)

| Stage | Configuration | P@5 | R@5 | F1@5 | R@10 | F1@10 | MRR | Latency | Key Takeaway |
|---|---|---|---|---|---|---|---|---|---|
| **1. Baseline (M1)** | `k1=1.5, b=0.75`, No Task Context | 0.733 | 0.667 | **0.657** | 0.932 | 0.664 | **1.000** | 4.7 ms | Official locked benchmark (`v0.1-baseline`) |
| **2. + Person 2 (Query)** | `k1=1.5, b=0.75`, + Task Context 0.3 | 0.767 | 0.690 | **0.685** | 0.911 | 0.645 | **1.000** | 5.0 ms | **+2.8pp F1@5** pure query contribution |
| **3. + Person 3 (Tuning)** | `k1=0.5, b=1.0`, + Task Context 0.3 | **0.833** | **0.756** | **0.750** | **0.932** | **0.664** | **1.000** | 5.1 ms | **+9.3pp F1@5 total gain** via length normalization |
| **4. + Dictionaries (All)** | Tuned + TC + Synonyms + ID $\rightarrow$ EN | 0.767 | 0.732 | **0.722** | 0.932 | 0.664 | 1.000 | 5.3 ms | Drop due to `approve ↔ review` synonym clash in S06 |
| **5. + ID $\rightarrow$ EN Only** | Tuned + TC + ID $\rightarrow$ EN Translation | **0.833** | **0.756** | **0.750** | **0.932** | **0.664** | **1.000** | 5.1 ms | **Zero regression** on English dev set |

---

## 4. Workstream Breakdown

### Workstream A: Query Builder & NLP (Person 2)
* **Task Context Implementation:** For each changed task in a BPMN model, the builder traverses incoming/outgoing sequence flows through unnamed gateways to find immediate named predecessor and successor tasks.
  * **S05 (User Invitations) Breakthrough:** Precision@5 jumped from $0.60 \rightarrow 0.80$ (+20pp) and Recall@5 from $0.43 \rightarrow 0.57$ (+14pp). Context terms (`Generate invitation token`, `Set initial password`) successfully pulled lifecycle handlers into top ranks.
  * **S01–S04:** Completely stable with zero regression.
  * **S06 (Goods Receipt Approval):** Slight function-level trade-off ($-0.022$ F1@5) where neighbor posting tasks promoted common helper functions.
* **Domain Synonym & ID $\rightarrow$ EN Dictionary:**
  * Created dictionary mapping business Indonesian terms (`pengguna → user`, `penjualan → sales`, `pembelian → purchase`, `akses → access`, `laporan → report`).
  * **Qualitative Validation (`data/bpmn/real/`):** Previously, labels matched code only through accidental English words (`Finance`, `Order to Cash`). With translation active, every business term matched cleanly, correctly ranking `backend/cmd/api/main.go` to **#1**.
  * **Domain Insight:** In Simple-ERP, *reviewing* an inventory adjustment and *approving* a purchase order are separate state machine transitions. Grouping `approve: [review]` created noise in S06. The team recommended decoupling `review` before activating synonyms by default.

### Workstream B: Ground Truth & Parameter Tuning (Person 3)
* **Ground Truth Second Review:**
  * Independently verified all 69 rows against Simple-ERP `c76a313`.
  * Formally settled borderline entries in `data/ground_truth/REVIEW_LOG.md`:
    * S02 `store.go Summary`: Retained because pending-approval counts directly drive the dashboard UI.
    * S05 `lifecycle.go AdminRoutes`: Retained as valid dead-code impact (route remains registered but admin no longer calls it).
    * Rule 6 (*vacuous-pass tests*): Tests that pass vacuously post-change are formally tracked as impacted tests that require maintenance.
* **Hyperparameter Tuning & Leave-One-Scenario-Out (LOSO):**
  * Built `experiments/tune.py` covering 45 grid combinations ($k_1 \in [0.5, 3.0]$, $b \in [0.0, 1.0]$) and upgraded it to support 6-fold LOSO cross-validation.
  * Discovered that $b = 1.0$ (full document length normalization) handles Simple-ERP's heterogeneous document lengths (small SQL migrations vs long Go service handlers) significantly better than default $b=0.75$.

### Workstream C: Web Application & Documentation (Person 4)
* **Enhanced Visual Diff:**
  * Change table categorizes modifications into *Activities / Tasks*, *Gateways*, *Events*, and *Sequence Flows*.
  * Colored border tags: 🟢 Added, 🔴 Removed, 🟡 Modified. Unnamed sequence flows are collapsed by default to reduce visual clutter.
* **Impact Report Exporting:**
  * Implemented `/download/csv` and `/download/json` endpoints.
  * Added 1-click download buttons on the mapping results screen.
* **Upload Limits Display:**
  * Form explicitly displays maximum file size constraints: 5 MB for BPMN models, 50 MB for Codebase ZIP archives.
* **Final Report Architecture (`docs/report/outline.md`):**
  * Completed the full report outline comprising 8 chapters, 3 Research Questions (RQ1–RQ3), 7 charts, and 9 data tables.

---

## 5. Live Demonstration Guide (1-Minute Walkthrough)

To demonstrate the live application running at `http://localhost:8000`:

1. **Open the Web Interface:** Navigate to `http://localhost:8000`.
2. **Form Checks:** Notice the file size limits displayed under file inputs (`Max 5 MB` / `Max 50 MB`).
3. **Execute Scenario:**
   * Select **`S05` (Email invitation links automatically)** from the Scenario dropdown.
   * Method: **BM25**.
   * Click **"Find impacted code"**.
4. **Inspect Results:**
   * **Diff Table:** Show the grouped, color-coded cards highlighting modified invitation tasks in yellow and new flows in green.
   * **Ranked Code:** Observe affected Go auth handlers and Next.js frontend pages ranked at the top with term evidence.
   * **Export:** Click **"Download Report (CSV)"** to instantly download the clean report file.

---

## 6. Next Steps (Milestone M3: 23–29 November 2026)

1. **Ablation Study per Field:** Zero out weights for `path`, `name`, `route`, `db_table`, `test`, `comment`, and `body` one by one to quantify the exact ranking power of each code attribute.
2. **Refine Dictionaries:** Decouple `review` from `approve` in the synonym dictionary and evaluate whether tuned parameters with clean synonyms surpass 0.750 F1@5.
3. **Evaluation Page Visualizations:** Embed dynamic $P@k$ and $R@k$ curves for BM25 vs Baseline Keyword vs TF-IDF directly on `/evaluation`.
4. **Internal Dry Run & Tag `v0.2-tuned`:** Validate clean-clone reproduction before locking the tuned configuration.
