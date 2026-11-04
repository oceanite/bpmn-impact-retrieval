# Ground truth (answer key)

`ground_truth.csv` columns: `scenario_id, file_path, function`.

- `file_path` is relative to the Simple-ERP root (`data/target_repo/`).
- `function` is the Go function/method, TSX component, or TS type that must change.
  **Empty** means the whole file is affected (e.g. `api/openapi.yaml`, or a file that
  needs a new function that does not exist yet).

## Inclusion rules

A row is included only if, given the BPMN change, that code **must be edited**:

1. Code that implements the changed behaviour (the SQL state transition, a precondition,
   the domain rule that mirrors it).
2. The HTTP handler or route registration, if the API surface changes.
3. The frontend component that triggers or displays the changed step.
4. `api/openapi.yaml`, if a route, action enum, or response description changes.
5. Existing tests that assert the old behaviour (they would fail after the change), including
   tests that only fail because their setup calls a removed or changed step (e.g. the `confirm`
   action in S03, posting a DRAFT receipt in S06).
6. Existing tests that would still pass but only **vacuously**: they assert that something is
   rejected, and after the change it is rejected for a different reason, so they must be edited
   to keep testing what their name says (e.g. `TestPostingDraftReceiptCannotReviveCancelledOrder` in S06).

Excluded on purpose:

- Thin pass-through layers whose signature does not change (most `application/service.go`
  methods just forward to the store).
- New files that would have to be created, e.g. a new SQL migration. They cannot be retrieved
  because they are not in the corpus yet. Each `scenario.md` notes them.
- `docs/` in Simple-ERP. It is not indexed (see `config/default.yaml`).

## Splits

| Split | Scenarios | Rows | Use |
|---|---|---|---|
| dev | S01–S06 | 50 | experiments, tuning (leave-one-scenario-out) |
| test | S07–S10 | 19 | **frozen 2026-11-04**; evaluated once, with the final config (M4) |

The split is defined in `config/default.yaml` (`evaluation.splits`). After the freeze, S07–S10
and their rows must not change; if a real error is found, fix it in a commit that says so and
report it in the final results.

Verified against Simple-ERP commit `c76a313`. Changes and reasons: [`REVIEW_LOG.md`](REVIEW_LOG.md).
