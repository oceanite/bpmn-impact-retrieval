# S07: Accept backorders at the stock gateway

- **Split:** test (frozen 2026-11-04)
- **Process:** Order-to-Cash (`l2-order-to-cash.bpmn`)
- **Change type:** modify gateway (name + documentation) and its outgoing flow (name + **condition**)
- **Source:** Simple-ERP `docs/bpmn/l2-order-to-cash.bpmn` @ `c76a313`

## BPMN change

| Element | Old | New |
|---|---|---|
| `GW-O2C-STOCK` (gateway) | Stock available? | Stock available or backorder accepted? (+ documentation) |
| `FLOW-O2C-004` (sequence flow) | "Available", `stockAvailable = true` | "Available or backorder", `stockAvailable = true or backorderAccepted = true` |

## Business rationale

Customers who accept a later delivery are turned away because the order cannot be submitted
while stock is short. Such orders should be submitted and approved anyway; the shortfall is
delivered later through the existing partial-delivery flow.

## Expected impact

- `sales/adapter/postgres/store.go` `TransitionOrder`: the `submit` and `approve` cases reject the order when `salesOrderStockAvailable` is false.
- `api/openapi.yaml`: sales-order command 409 "Invalid transition, stock, or maker-checker conflict".
- Test: `TestSubmitOrderRequiresAvailableStock` (asserts that submit fails without stock).

## Notes

- Where `backorderAccepted` is stored (sales-order column, customer flag or setting) is a design
  choice and is left out, as in S01. A new column would also need a new migration.
- `ValidateStock` (the explicit "Validate Stock" action, task `SAL-SO-003`) still reports the
  shortage; only the gateway decision changes, so it is not in the answer key.
- Delivery posting keeps its own stock check (`TestConcurrentDeliveriesCannotOversell`), unchanged.
