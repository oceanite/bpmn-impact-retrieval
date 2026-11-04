# S03: Remove sales order confirmation

- **Process:** Order-to-Cash (`l2-order-to-cash.bpmn`)
- **Change type:** remove (task + message flow), rewire flow
- **Source:** Simple-ERP `docs/bpmn/l2-order-to-cash.bpmn` @ `c76a313`

## BPMN change

| Element | Change |
|---|---|
| `SAL-SO-005` Confirm order to customer (serviceTask) | removed |
| `MSG-O2C-002` Order confirmation (message flow to Customer) | removed |
| `FLOW-O2C-010` | removed |
| `FLOW-O2C-008` "Approved" | retargeted: `GW-O2C-APPROVED` → `GW-O2C-DELIVERY-MERGE` |
| `SAL-DLV-001` Create delivery | documentation added |

## Business rationale

Customers already get the order through other channels, so the separate confirmation step only
delays delivery. An approved order should be deliverable right away.

## Expected impact

- `sales/adapter/postgres/store.go` `TransitionOrder`: the `confirm` action case.
- `sales/adapter/postgres/store.go` `CreateDelivery`: rejects orders where `confirmed_at IS NULL`.
- `sales/adapter/postgres/store.go` `GetOrder`: returns the `confirmed` flag.
- `sales-order-panel.tsx` `SalesOrderPanel`: Confirm button.
- `delivery-panel.tsx` `DeliveryPanel`: blocks delivery with "Sales order belum dikonfirmasi".
- `operations/types.ts` `WorkflowDocumentDetail` and `sales/application/service.go` `OrderDetail`: `confirmed` field.
- `api/openapi.yaml`: `confirm` in the sales-order action enum, and the "confirmation state" summary.
- Test: `TestDeliveryRequiresOrderConfirmation`.
- Tests that call the `confirm` action before delivering or invoicing (fail once the action is gone):
  `TestConcurrentDeliveriesCannotOversell`, `TestPostingDraftDeliveryCannotReviveCancelledOrder`,
  `TestO2CConsolidatedInvoicePartialPaymentCompletionAndVoid` (added in the review).
