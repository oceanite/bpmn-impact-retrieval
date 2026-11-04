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
5. Existing tests that assert the old behaviour (they would fail after the change).

Excluded on purpose:

- Thin pass-through layers whose signature does not change (most `application/service.go`
  methods just forward to the store).
- New files that would have to be created, e.g. a new SQL migration. They cannot be retrieved
  because they are not in the corpus yet. Each `scenario.md` notes them.
- `docs/` in Simple-ERP. It is not indexed (see `config/default.yaml`).

Verified against Simple-ERP commit `c76a313`.
