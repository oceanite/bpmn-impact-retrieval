# S06: Approve goods receipt before posting

- **Process:** Procure-to-Pay (`l2-procure-to-pay.bpmn`)
- **Change type:** add (task + flow), rewire flow
- **Source:** Simple-ERP `docs/bpmn/l2-procure-to-pay.bpmn` @ `c76a313`

## BPMN change

| Element | Change |
|---|---|
| `PUR-GR-003` Approve goods receipt (userTask, Admin lane) | added (+ documentation) |
| `FLOW-P2P-009` | retargeted: `PUR-GR-001` → `PUR-GR-003` |
| `FLOW-P2P-009A` | added: `PUR-GR-003` → `PUR-GR-002` |

## Business rationale

Receiving clerks have posted wrong quantities straight to stock. An admin should approve each
draft goods receipt before it is posted.

## Expected impact

- `purchasing/adapter/postgres/store.go` `PostReceipt`: precondition `status = DRAFT` becomes `APPROVED`.
- `purchasing/adapter/http/handler.go` `Register`, `postReceipt`: new approve route; posting rules change.
- `purchasing/application/service.go` (file level): a new approve method on the service and store interface.
- `goods-receipt-panel.tsx` `GoodsReceiptPanel`: Approve button before Post.
- `api/openapi.yaml`: goods-receipt action enum `[post, cancel, reverse]`.
- Tests that post DRAFT receipts directly: `TestP2PPartialReceiptPostsImmutableSourceLinkedLedger`, `TestPostingDraftReceiptCannotReviveCancelledOrder`.

## Notes

- Tests the **add** change type. The new task's words ("approve goods receipt") have to find
  code that does not exist yet, so retrieval depends on the neighbouring code.
- `goods_receipts.status` has `CHECK(status IN('DRAFT','POSTED','CANCELLED','REVERSED'))` in
  `000005_operations.up.sql`. Adding `APPROVED` needs a **new** migration, which is not in the answer key.
