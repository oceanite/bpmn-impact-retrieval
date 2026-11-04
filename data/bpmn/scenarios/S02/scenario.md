# S02: Remove inventory adjustment review

- **Process:** Inventory Adjustment (`l2-inventory-adjustment.bpmn`)
- **Change type:** remove (task + gateway + end event), rewire flow
- **Source:** Simple-ERP `docs/bpmn/l2-inventory-adjustment.bpmn` @ `c76a313`

## BPMN change

| Element | Change |
|---|---|
| `INV-ADJ-003` Review inventory adjustment (userTask, Admin) | removed |
| `GW-INV-APPROVED` Adjustment approved? | removed |
| `INV-END-REJECTED` Adjustment rejected | removed |
| `FLOW-INV-004/005/006` | removed |
| `FLOW-INV-003` | retargeted: `INV-ADJ-002` → `GW-INV-DIFFERENCE` |
| `INV-ADJ-002` Submit inventory adjustment | documentation added |

## Business rationale

Small warehouses have one person doing counts. The maker-checker review slows them down, so
submitted adjustments should go straight to posting.

## Expected impact

- `inventory/adapter/postgres/store.go` `TransitionAdjustment`: the `approve`/`reject` cases and the `APPROVED` status go away or change.
- `inventory/adapter/postgres/store.go` `PostAdjustment`: requires `status = APPROVED` before posting.
- `inventory/domain/adjustment.go` `Approve`, `Complete`: the state machine (`Complete` requires `APPROVED`).
- `inventory/adapter/http/handler.go` `action`: role check for `approve`/`reject`.
- `inventory-adjustment-panel.tsx` `InventoryAdjustmentPanel`: Approve/Reject buttons.
- `api/openapi.yaml`: action enum `[submit, approve, reject, cancel, post, reverse]`.
- `reporting/adapter/postgres/store.go` `Summary`: counts `SUBMITTED` adjustments as pending approvals on the dashboard (added in the review).
- Tests: `TestINVADJ002And003MakerChecker`, `TestInventoryApprovalRejectsChangedSnapshot`, `TestApprovedInventoryAdjustmentCanRecoverFromStaleSnapshot`.

## Notes

- The stock-snapshot check currently runs inside `approve`. It would have to move to submit or
  post, which is covered by the same functions.
- A migration that tightens the status `CHECK` would be a new file and is not in the answer key.
