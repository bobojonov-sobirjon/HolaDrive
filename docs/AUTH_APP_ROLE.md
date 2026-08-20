# Rider vs Driver login isolation

A **Rider** account cannot sign in from the **Driver** app, and a **Driver** account cannot sign in from the **Rider** app.

All mobile auth endpoints now **require** `role`: `"rider"` | `"driver"`.

| Method | Path |
|--------|------|
| POST | `/api/v1/accounts/login/` |
| POST | `/api/v1/accounts/send-verification-code/` |
| POST | `/api/v1/accounts/verify-code/` |
| POST | `/api/v1/accounts/google/` (and Apple / Facebook) |

## Success

Same as before. Always send:

```json
{ "phone_number": "+15145551234", "role": "driver" }
```

or email login:

```json
{ "email": "a@b.com", "password": "…", "role": "rider" }
```

`verify-code` must send the **same** `role`.

## Wrong app (HTTP 403)

```json
{
  "message": "This account is registered as a Rider. Please sign in with the Rider app.",
  "status": "error",
  "code": "wrong_app_role",
  "errors": {
    "role": ["This account is registered as a Rider. Please sign in with the Rider app."]
  },
  "data": {
    "account_role": "rider",
    "requested_role": "driver"
  }
}
```

Frontend: show the `message`, do not complete login, optionally deep-link to the other app.

`code: mixed_app_roles` — account has both groups (data issue); contact support.

## New sign-up

If the phone/email is new, `role` creates the Rider or Driver group. That account can only use that app after that.
