# Real BPMN change from Simple-ERP history

An actual before/after pair from Simple-ERP's git history. It is **not** an evaluation
scenario: it has no ground truth, and `pipeline.scenarios()` ignores this folder. Use it
to demo the upload on the mapping page.

| File | Source (Simple-ERP) |
|---|---|
| `l0-simple-erp_old.bpmn` | `docs/bpm-haqi/level-0/l0-simple-erp.bpmn` @ `c934497` (Oct 22, 2026, first version) |
| `l0-simple-erp_new.bpmn` | same file @ `c76a313` ("BPMN fix", Oct 22, 2026) |

Both are byte-identical to the git blobs (`git show <commit>:<path>`).

## What changed
Only diagram tidy-up, no business-process change:

- 6 duplicate end events "Aksi selesai / hasil diterima" removed (merged into one)
- 7 sequence flows removed and 7 added (rewired to the single end event)
- labels removed from 6 sequence flows ("Procure to Pay", "Order to Cash", ...)
- 1 gateway modified (its outgoing default flow)

No code was changed in that commit, so there is no "correct" answer for the impact report.

## What the pipeline does with it
The query is built from Indonesian labels ("Akses dan pengguna", "Kebutuhan apa?"). BM25
therefore matches Indonesian UI text in `frontend/app/*/page.tsx`, mostly through the word
"dan" ("and"). Two lessons follow for the query builder (task for Orang 2 in `docs/TASKS.md`):

1. Indonesian stopwords (`dan`, `atau`, `yang`, `di`, ...) are missing from the config.
2. An Indonesian → English term list is needed before the `bpm-haqi` models can be used.
