# S04: Keep sessions on password reset

- **Process:** Access Lifecycle (`l2-access-lifecycle.bpmn`)
- **Change type:** modify (rename + documentation)
- **Source:** Simple-ERP `docs/bpmn/l2-access-lifecycle.bpmn` @ `c76a313`

## BPMN change

| Element | Old | New |
|---|---|---|
| `AUTH-PWD-005` (serviceTask) | Consume reset and revoke sessions | Consume password reset token (+ documentation) |

## Business rationale

Users who reset a forgotten password on one device complain that they are logged out
everywhere else. The business accepts keeping existing sessions active after a reset.

## Expected impact

- `auth/adapter/postgres/lifecycle.go` `Consume`: the `UPDATE sessions SET revoked_at=now()` branch for `PasswordReset`.
- `api/openapi.yaml`: `/auth/reset-password` response "Password replaced and sessions revoked".

## Notes

- A deliberately **small** answer key (2 rows), used to test precision.
- No existing test asserts session revocation on reset, so no test row is included.
- `Consume` is shared with invitation activation. Only its password-reset branch changes.
