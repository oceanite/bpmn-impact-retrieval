# Ground-truth review log

## Review 1: 2026-11-04 (S01–S06, dev set)

Method: every row was checked against the code at Simple-ERP `c76a313`. Each row's file and function
exists in the indexed corpus (checked by script). Then the call sites, SQL, UI conditions,
OpenAPI text and integration tests were searched for each business change, looking for missing
rows. Rules are in `README.md`; rule 5 was clarified and rule 6 added during this review.

Result: 41 rows became 50 (+10, −1).

| Scenario | Change | Row | Reason |
|---|---|---|---|
| S01 | **removed** | `backend/test/integration/finance_test.go` `TestP2PConsolidatedInvoiceExactMatchPartialPaymentCloseAndVoid` | Its mismatch is a quantity difference (invoice 9 vs order 10). Under a price-only tolerance it is still an exception, so the test keeps passing (rule 5). |
| S01 | added | `api/openapi.yaml` | Summary "Record a consolidated supplier invoice for exact matching" becomes wrong (rule 4). |
| S02 | added | `backend/internal/reporting/adapter/postgres/store.go` `Summary` | Counts `SUBMITTED` adjustments as pending approvals; without a review step nobody approves them (rule 1). Borderline: depends on whether `SUBMITTED` stays as a state. |
| S03 | added | `backend/internal/sales/application/service.go` `OrderDetail` | Carries the `Confirmed` field returned by `GetOrder` (rule 1, same as `WorkflowDocumentDetail`). |
| S03 | added | `backend/test/integration/operations_test.go` `TestConcurrentDeliveriesCannotOversell` | Calls `confirm` and fails if it errors (rule 5). |
| S03 | added | `backend/test/integration/operations_test.go` `TestPostingDraftDeliveryCannotReviveCancelledOrder` | Same (rule 5). |
| S03 | added | `backend/test/integration/finance_test.go` `TestO2CConsolidatedInvoicePartialPaymentCompletionAndVoid` | Same (rule 5). |
| S05 | added | `api/openapi.yaml` | `/user-invitations` 201 "One-time invitation token": the token is no longer returned. The old `scenario.md` note ("OpenAPI not included") only applied to the mark-shared route (rule 4). |
| S05 | added | `backend/internal/auth/adapter/http/lifecycle.go` `AdminRoutes` | Registers `/user-invitations/{id}/mark-shared`, which the admin no longer calls (rule 2). |
| S06 | added | `backend/test/integration/operations_test.go` `TestSuperAdminCanSelfApproveP2P` | Posts a DRAFT receipt directly (rule 5). |
| S06 | added | `backend/test/integration/finance_test.go` `TestP2PConsolidatedInvoiceExactMatchPartialPaymentCloseAndVoid` | Posts a DRAFT receipt directly before invoicing (rule 5). |
| S06 | kept | `TestPostingDraftReceiptCannotReviveCancelledOrder` | Still passes after the change, but only vacuously (new rule 6). |
| S04 | no change | — | No other code revokes sessions on reset; the frontend reset form shows no session text. |

Considered and **not** added (with reason):
- S02 `frontend` dashboard tile for pending approvals: display only, the number comes from `Summary`.
- S03 `ValidateStock`, S07 `ValidateStock`: unchanged behaviour.
- S06 `CancelReceipt`: whether an `APPROVED` receipt can be cancelled is a design choice.

## Test set S07–S10: written 2026-11-04, then frozen

19 rows, written with the same rules and the same method. Reasons per row are in each
`data/bpmn/scenarios/S0x/scenario.md`.

## Still open

- [ ] **Second reviewer (a team member)** checks Review 1 and the test-set rows, especially the
      borderline rows (S02 `Summary`, S05 `AdminRoutes`, rule 6). Record agreement or changes below.
- [ ] Re-run `python experiments/run_eval.py` (dev split) after any change and log the numbers.

| Date | Reviewer | Scenarios | Result |
|---|---|---|---|
| | | | |
