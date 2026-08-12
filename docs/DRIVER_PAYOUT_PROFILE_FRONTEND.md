# Driver payout + Canada profile — Frontend handoff

## 1. Instant withdraw (Payment Settings)

**Old copy:** "Earnings are transferred on a regular schedule"  
**New:** Driver withdraws when they want.

### Balance
`GET /api/v1/payment/driver/stripe-balance/`

Key fields:
- `payout_mode`: `manual_withdraw`
- `available_cents` / `available_total`
- `instant_available_cents` — max instant withdraw
- `withdraw_on_demand`: true

### Withdraw
`POST /api/v1/payment/driver/stripe-connect/withdraw/`  
Auth: JWT (driver)

```json
{ "instant": false }
```

Withdraw all available (standard, 1–2 business days):

```json
{ "amount_cents": 5000, "instant": true }
```

Partial instant (when Stripe allows):

Response `data.payout`: `id`, `amount`, `status`, `method` (`standard` | `instant`)

**UI:** Replace "regular schedule" with **Withdraw** button → call API → show success + updated balance.

---

## 2. Edit profile — Canada taxes

`GET/PUT /api/v1/accounts/me/`

| Field | Label (UI) | Notes |
|--------|------------|--------|
| `tax_number` | GST/HST (federal) | 9–15 chars |
| `tvq_number` | TVQ / QST (provincial) | Quebec — **new field** |

Validation error example:
```json
{ "phone_number": ["Phone number must include country code +1 and 10 digits (example: +1 514 555 1234)."] }
```

---

## 3. Phone number

**Format:** `+1` + **10 digits** (North America)

- Wrong: `+1 123 456 789` (9 digits)
- OK: `+1 514 555 1234` or `5145551234`

Backend normalizes on save (`PUT /me/`).

**Frontend:** Input mask `+1 XXX XXX XXXX` (10 digits after +1).

---

## 4. Checklist

- [ ] Payment screen: Withdraw button + balance from `stripe-balance`
- [ ] Optional: Instant toggle when `instant_available_cents` > 0
- [ ] Profile: two tax fields (`tax_number`, `tvq_number`)
- [ ] Profile: phone mask 10 digits after +1
- [ ] Remove "weekly automatic deposit" copy
