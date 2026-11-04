# S01: Invoice match with price tolerance

- **Process:** Procure-to-Pay (`l2-procure-to-pay.bpmn`)
- **Change type:** modify (rename + documentation)
- **Source:** Simple-ERP `docs/bpmn/l2-procure-to-pay.bpmn` @ `c76a313`

## BPMN change

| Element | Old | New |
|---|---|---|
| `PUR-INV-002` (serviceTask) | Validate three-way match | Validate invoice match within price tolerance (+ documentation) |
| `GW-P2P-MATCHED` (gateway) | Invoice matched? | Invoice within tolerance? |

## Business rationale

Supplier invoices currently need an exact match on quantity and unit price. Small price
differences, such as rounding or freight, send the invoice to manual resolution. The business
wants unit-price differences inside a configured percentage to be accepted automatically.

## Expected impact

- `finance/domain/finance.go` `ExactMatch`: the zero-tolerance comparison becomes tolerance-based.
- `finance/adapter/postgres/store.go` `MatchSupplierInvoice`: calls the match rule and decides `POSTED` vs `MATCH_EXCEPTION`.
- Tests asserting zero tolerance: `TestPURINV002ExactMatchHasZeroTolerance`, `TestP2PConsolidatedInvoiceExactMatchPartialPaymentCloseAndVoid`.

## Notes

- The code compares invoice lines with **purchase-order lines only**; it never reads goods
  receipts. The old BPMN label "three-way match" already overstates what the code does.
- Where the tolerance value would be stored (settings table or env config) is a design choice
  and is left out of the answer key.
