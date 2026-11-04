# S10: Supervisor posts deliveries, invoice per delivery

- **Split:** test (frozen 2026-11-04)
- **Process:** Order-to-Cash (`l2-order-to-cash.bpmn`)
- **Change type:** **multi-change**: two tasks in one process (task type, lane, rename, documentation)
- **Source:** Simple-ERP `docs/bpmn/l2-order-to-cash.bpmn` @ `c76a313`

## BPMN change

| Element | Old | New |
|---|---|---|
| `SAL-DLV-002` | serviceTask "Post delivery and stock", lane System | userTask "Approve and post delivery", lane Admin (+ documentation) |
| `SAL-INV-001` | Generate sales invoice | Generate sales invoice per delivery (+ documentation) |

## Business rationale

1. Operators post their own deliveries straight to stock. A supervisor should check and post
   them, and the creator may not post their own delivery (maker-checker).
2. Customers with long partial deliveries want to be invoiced for what they received, not only
   after the last delivery.

## Expected impact

Change 1, delivery posting:
- `sales/adapter/http/handler.go` `post`: role check `CanCreate` becomes `CanApprove`.
- `sales/adapter/postgres/store.go` `PostDelivery`: maker-checker check on the delivery creator.
- `delivery-panel.tsx` `DeliveryPanel`: the Post button is shown for `canCreate`.
- Tests where the operator who created the delivery posts it: `TestConcurrentDeliveriesCannotOversell`
  (would fail), `TestPostingDraftDeliveryCannotReviveCancelledOrder` (would only pass vacuously).

Change 2, invoice per delivery:
- `finance/adapter/postgres/store.go` `CreateSalesInvoice`: requires sales-order status `DELIVERED` and invoices the full delivered quantity.
- `finance-workspace.tsx` `FinanceWorkspace`: only offers sales orders with status `DELIVERED`.
- `api/openapi.yaml`: "Create the consolidated sales invoice after full delivery".

## Notes

- The sequence flows were not rewired: the invoice task still follows "All goods delivered?".
  The change is carried by the task name and documentation.
- Tracking already-invoiced quantities per order line would need a new column (new migration),
  which is not in the answer key.
