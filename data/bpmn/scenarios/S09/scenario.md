# S09: Purchase orders are created by the admin

- **Split:** test (frozen 2026-11-04)
- **Process:** Procure-to-Pay (`l2-procure-to-pay.bpmn`)
- **Change type:** **lane change only** (Operator → Admin); name, type and documentation unchanged
- **Source:** Simple-ERP `docs/bpmn/l2-procure-to-pay.bpmn` @ `c76a313`

## BPMN change

| Element | Old | New |
|---|---|---|
| `PUR-PO-001` Create purchase order (userTask) | lane Operator | lane Admin |

## Business rationale

Converting an approved request into a purchase order commits spend with a supplier. Only a
supervisor (Admin lane) should do it.

## Expected impact

- `purchasing/adapter/http/handler.go` `prAction`: the `purchase-order` action checks `CanCreate`; it becomes `CanApprove`.
- `purchase-order-panel.tsx` `PurchaseOrderPanel`: the "Konversi PR menjadi PO" form is shown for `canCreate`.

## Notes

- A deliberately **small** answer key (2 rows) with almost no new words in the query: the only
  signal is the task name plus the lane. Tests how retrieval copes with a pure role change.
- The store (`ConvertToOrder`) does not check roles, so the integration tests that convert with
  `operatorID` keep passing and are not included.
