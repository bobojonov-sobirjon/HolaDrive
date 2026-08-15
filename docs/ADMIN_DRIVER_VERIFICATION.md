# Admin — Driver identification / registration review

Base: `/api/v1/admin-panel/`  
Auth: JWT (superuser)

## 1. Driver detail (existing)

`GET /drivers/<driver_id>/`

Includes:

- `driver_verification` — status (`not_submitted` | `in_review` | `approved` | `rejected`)
- `upload_identifications` — submitted ID docs
- `registration_agreements` — with `required_complete: true/false`
- `legal_agreements`, `terms_acceptance`

## 2. Review + approve (new — preferred)

### `GET /drivers/<driver_id>/verification/`

Admin sees identification + registration terms + readiness checklist (same shape as mobile).

```json
{
  "message": "Driver verification retrieved successfully",
  "status": "success",
  "data": {
    "driver_id": 17,
    "email": "driver@email.com",
    "full_name": "Sobir Bobojonov",
    "verification": {
      "id": 3,
      "status": "in_review",
      "status_display": "In review",
      "comment": null,
      "reviewer_email": null
    },
    "identification": {
      "checklist_complete": true,
      "steps_total": 5,
      "steps_accepted": 5,
      "verification_status": "in_review",
      "verification_approved": false,
      "steps": []
    },
    "registration_terms": {
      "required_complete": false,
      "required_active_count": 1,
      "accepted_count": 0
    },
    "readiness": {
      "ready_for_rides": false,
      "completion_percent": 38,
      "checks": {
        "profile": false,
        "identification": false,
        "registration_terms": false,
        "preferences": true,
        "vehicle": true,
        "bank_account": false
      }
    }
  }
}
```

### `PATCH` / `PUT /drivers/<driver_id>/verification/`

Approve / reject / set in review:

```json
{
  "status": "approved",
  "comment": "Documents look good"
}
```

| `status` | Effect on mobile readiness |
|----------|----------------------------|
| `approved` | `checks.identification` → **true** |
| `rejected` | stays false; driver can resubmit |
| `in_review` | docs received, waiting |
| `not_submitted` | reset |

Optional: `estimated_review_hours` (int).

Success `data` = verification row (`id`, `status`, `reviewer_email`, …).

## 3. Legacy (still works)

- `GET /verification-drivers/`
- `PATCH /verification-drivers/<verification_id>/` with `{ "status": "approved", "comment": "..." }`

Prefer **by `driver_id`** endpoint above.

## Admin UI flow

1. Open driver → `GET …/drivers/{id}/verification/`
2. Check `identification.checklist_complete` + uploaded files on driver detail
3. Check `registration_terms.required_complete`
4. If OK → `PATCH` `{ "status": "approved" }`
5. Mobile readiness Identification becomes ✅
