# S05: Email invitation links automatically

- **Process:** Access Lifecycle (`l2-access-lifecycle.bpmn`)
- **Change type:** modify (task type userTask → serviceTask, rename, lane Admin → System, documentation)
- **Source:** Simple-ERP `docs/bpmn/l2-access-lifecycle.bpmn` @ `c76a313`

## BPMN change

| Element | Old | New |
|---|---|---|
| `AUTH-USR-003` | userTask "Share invitation link manually", lane Admin | serviceTask "Send invitation link by email", lane System (+ documentation) |

## Business rationale

Admins copy the one-time invitation token from the screen and send it by hand, which is
error-prone. The system should email the link and mark the invitation as shared itself.

## Expected impact

- `auth/application/lifecycle.go` `Invite`: sends the email instead of returning the raw token to the admin.
- `auth/application/lifecycle.go` `MarkShared`, `auth/adapter/postgres/lifecycle.go` `MarkTokenShared`: called by the system after sending, not by the admin.
- `auth/adapter/http/lifecycle.go` `invite`, `shared`: response no longer exposes the token; the manual mark-shared endpoint changes.
- `platform/config/config.go` `Config`, `Load`: mail server settings.
- `users-panel.tsx` `UsersPanel`: shows "Token undangan (tampil sekali)" today.
- Test: `TestAUTHUSR001InviteReturnsRawTokenOnce`.

## Notes

- Tests the **lane / task-type** change type, not just renames.
- A new mail-sender adapter would be a new file and is not in the answer key.
- The `mark-shared` route is not in `api/openapi.yaml`, so OpenAPI is not included.
