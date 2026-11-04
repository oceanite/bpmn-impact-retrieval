# S08: Send an invoice dispute notice to the supplier

- **Split:** test (frozen 2026-11-04)
- **Process:** Procure-to-Pay (`l2-procure-to-pay.bpmn`)
- **Change type:** add **message flow** to an external participant, documentation
- **Source:** Simple-ERP `docs/bpmn/l2-procure-to-pay.bpmn` @ `c76a313`

## BPMN change

| Element | Change |
|---|---|
| `MSG-P2P-005` Invoice dispute notice (`PUR-INV-003` → Supplier) | added |
| `PUR-INV-003` Resolve invoice mismatch | documentation added |

## Business rationale

When an invoice does not match, the admin corrects the lines but the supplier never learns why.
The resolution must record a dispute reason, and that reason is sent to the supplier.

## Expected impact

- `finance/adapter/postgres/store.go` `ResolveSupplierInvoice`: accepts and stores the dispute reason (audit entry).
- `finance/application/service.go` `ResolveSupplierInvoice`: the signature gains the reason (not a pure pass-through any more).
- `finance/adapter/http/handler.go` `resolveSupplierInvoice`: decodes the reason from the request body.
- `finance-workspace.tsx` `FinancePanel`: the resolve form sends the reason.
- `api/openapi.yaml`: `SupplierMatchResolution` schema and the resolve-match body description.
- Test: `TestP2PConsolidatedInvoiceExactMatchPartialPaymentCloseAndVoid` calls `ResolveSupplierInvoice` with the old signature.

## Notes

- The component that actually sends the notice (mail or EDI adapter) would be a new file and is
  not in the answer key.
