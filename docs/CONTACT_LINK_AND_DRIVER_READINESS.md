# Contact link + Driver readiness — Frontend

Base: `/api/v1/accounts/`  
Auth: `Authorization: Bearer <ACCESS_JWT>`

Umumiy success:

```json
{
  "message": "...",
  "status": "success",
  "data": {}
}
```

Error:

```json
{
  "message": "...",
  "status": "error",
  "code": "phone_taken",
  "errors": { "phone_number": ["..."] }
}
```

---

## 1. Telefon — profil update (har qanday davlat)

### `PUT` / `PATCH` `/api/v1/accounts/me/`

Telefon endi **faqat Canada/US emas** — xalqaro E.164.

| Qoida | Misol |
|--------|--------|
| Country code bilan | `+998901234567`, `+15145551234` |
| Raqamlar soni | **8–15** digit (faqat raqamlar, `+` dan keyin) |
| Unique | Boshqa akkauntda bo‘lsa → xato |

**OK:**
```json
{ "phone_number": "+998 90 123 45 67" }
```
Backend saqlaydi: `+998901234567`

**Xato (band):**
```json
{
  "message": "Validation error",
  "status": "error",
  "errors": {
    "phone_number": ["This phone number is already linked to another account."]
  }
}
```

**Tavsiya:** Telefon/email qo‘shishni to‘g‘ridan-to‘g‘ri `/me/` orqali emas, balki pastdagi **OTP contact link** API orqali qiling (tasdiqlangan kontakt).

---

## 2. Email yoki telefonni akkauntga biriktirish (OTP)

Maqsad: telefon bilan ochilgan akkauntga email qo‘shish, yoki email akkauntga telefon qo‘shish — **avval OTP**, keyin save.

### 2.1 Kod so‘rash

`POST /api/v1/accounts/me/contact/request/`  
Auth: JWT

**Faqat bittasini** yuboring (`email` **yoki** `phone_number`).

Phone:
```json
{ "phone_number": "+998901234567" }
```

Email:
```json
{ "email": "driver@example.com" }
```

Success `data`:
```json
{
  "channel": "phone",
  "sent_to": "+998901234567",
  "expires_at": "2026-08-14T10:20:00+00:00"
}
```

`channel`: `phone` | `email`

### 2.2 Kodni tasdiqlash → akkauntga yozish

`POST /api/v1/accounts/me/contact/confirm/`  
Auth: JWT

```json
{
  "phone_number": "+998901234567",
  "code": "1234"
}
```

yoki

```json
{
  "email": "driver@example.com",
  "code": "1234"
}
```

Success: `data` = to‘liq user profile (`/me/` bilan bir xil shape).

### 2.3 App oqimi

```
1. User email yoki phone kiritadi
2. POST /me/contact/request/
3. OTP screen
4. POST /me/contact/confirm/  { contact + code }
5. Profile yangilanadi
```

### 2.4 Xato kodlari

| `code` | Ma’nosi | UI |
|--------|---------|-----|
| `phone_taken` | Boshqa userda bor | "Already used" |
| `email_taken` | Boshqa userda bor | "Already used" |
| `already_linked` | Shu akkauntda allaqachon shu kontakt | Info |
| `invalid_code` | OTP noto‘g‘ri / eskirgan | Qayta kiriting |
| `invalid_phone` | Format xato | Format hint |
| `send_failed` | SMS/email yuborilmadi | Retry |
| `invalid_payload` | Email va phone birga / ikkalasi bo‘sh | — |

---

## 3. Driver readiness (true / false checklist)

Driver ride qabul qilishdan oldin qaysi qadamlar tayyor — **bitta API**.

### `GET /api/v1/accounts/driver/readiness/`

Auth: JWT  
Role: **Driver** (Rider → `403`)

### Response `data`

```json
{
  "is_driver": true,
  "ready_for_rides": false,
  "completion_percent": 38,
  "checks": {
    "profile": false,
    "profile_photo": true,
    "identification": false,
    "registration_terms": false,
    "preferences": true,
    "vehicle": true,
    "pin": false,
    "bank_account": false
  },
  "incomplete_actions": {
    "profile": {
      "screen": "edit_profile",
      "path": "/api/v1/accounts/me/",
      "use_details": "details.profile.missing_fields / details.profile.actions"
    },
    "identification": {
      "screen": "identification_checklist",
      "message": "Complete identification checklist and submit documents",
      "use_details": "details.identification.verification_status"
    },
    "pin": {
      "screen": "pin_setup",
      "method": "POST",
      "path": "/api/v1/accounts/pin-verification/",
      "message": "Create a PIN"
    },
    "bank_account": {
      "screen": "bank_account",
      "path": "/api/v1/payment/driver/stripe-connect/",
      "message": "Link Stripe Connect and add a bank account"
    }
  },
  "details": {
    "profile": {
      "full_name": true,
      "phone_number": false,
      "email": true,
      "date_of_birth": false,
      "address": false,
      "required_fields": ["full_name", "phone_number", "date_of_birth"],
      "missing_fields": ["phone_number", "date_of_birth"],
      "next_screen": "edit_profile",
      "next_path": "/api/v1/accounts/me/",
      "next_field": "phone_number",
      "actions": [
        {
          "field": "phone_number",
          "message": "Add and verify phone number",
          "screen": "edit_profile",
          "method": "PUT",
          "path": "/api/v1/accounts/me/",
          "body_hint": { "phone_number": "+15145551234" },
          "preferred_flow": {
            "request": "POST /api/v1/accounts/me/contact/request/",
            "confirm": "POST /api/v1/accounts/me/contact/confirm/"
          }
        },
        {
          "field": "date_of_birth",
          "message": "Add date of birth",
          "screen": "edit_profile",
          "method": "PUT",
          "path": "/api/v1/accounts/me/",
          "body_hint": { "date_of_birth": "1990-01-15" }
        }
      ]
    },
    "identification": {
      "checklist_complete": true,
      "verification_status": "not_submitted",
      "verification_approved": false,
      "steps_total": 5,
      "steps_accepted": 5,
      "message": "Documents submitted — waiting for admin approval",
      "next_screen": "identification_status"
    },
    "bank_account": {
      "stripe_connect_linked": false,
      "bank_linked": false,
      "payouts_enabled": false,
      "message": "Link Stripe Connect and add a bank account",
      "next_screen": "bank_account",
      "next_path": "/api/v1/payment/driver/stripe-connect/"
    },
    "required_for_rides": [
      "profile",
      "identification",
      "preferences",
      "vehicle",
      "bank_account"
    ]
  }
}
```

### `checks` — nima degani

| Key | `true` qachon |
|-----|----------------|
| `profile` | Ism + telefon + DOB bor |
| `profile_photo` | Avatar yuklangan |
| `identification` | `DriverVerification` status = **`approved`** |
| `registration_terms` | Barcha aktiv registration terms accepted (yo‘q bo‘lsa → true) |
| `preferences` | Driver preferences yozuvi bor |
| `vehicle` | Kamida 1 ta vehicle |
| `pin` | PIN yaratilgan |
| `bank_account` | Stripe Connect + bank linked (+ payouts/onboarding) |

### Profile — Frontend qayerga olib boradi

`checks.profile === false` bo‘lsa:

1. `details.profile.missing_fields` — qaysi maydonlar yetishmayapti (`full_name` | `phone_number` | `date_of_birth`)
2. `details.profile.actions[]` — har bir missing field uchun `screen`, `path`, `body_hint`
3. `details.profile.next_field` — birinchi to‘ldirilishi kerak field (primary CTA)
4. `incomplete_actions.profile` — umumiy step navigation

**Majburiy** (profile ✅ uchun): `full_name`, `phone_number`, `date_of_birth`  
**Majburiy emas:** `email`, `address` (faqat status)

Misollar:
- `missing_fields: ["phone_number"]` → Edit profile / contact OTP flow
- `missing_fields: ["date_of_birth"]` → `PUT /me/` with `date_of_birth`
- `missing_fields: []` va `checks.profile: true` → Profile qatoriga ✅

### Identification — matn

`checks.identification` faqat **approved** da `true`.  
Matn uchun `details.identification.verification_status` + `message` ishlating — `false` ni “Not submitted” deb map qilmang.

### `ready_for_rides`

`true` faqat shu `required_for_rides` hammasi `true` bo‘lsa:

- `profile`
- `identification` (admin approved)
- `preferences`
- `vehicle`
- `bank_account`

`profile_photo` va `pin` — progress uchun ko‘rsatiladi, lekin `ready_for_rides` ga majburiy emas (hozirgi backend qoidasi).

### UI tavsiya

1. Driver home / “Go online” oldidan `GET …/driver/readiness/`
2. Har bir `checks.*` uchun qator: ✅ / ❌
3. Qator bosilganda: `incomplete_actions[key]` yoki `details.profile.actions`
4. Profile ❌ → `missing_fields` bo‘yicha form focus
5. `ready_for_rides === false` → online tugma disable
6. `completion_percent` — progress bar
7. Identification subtitle: `verification_status` (`not_submitted` | `in_review` | `approved` | `rejected`)

### Qaysi ekranga olib borish

| Check false | Screen / API |
|-------------|--------------|
| `profile` | `details.profile.actions` / `PUT /me/` |
| `profile_photo` | `PUT /me/avatar/` |
| `identification` | Identification checklist + wait for admin |
| `registration_terms` | Registration terms accept |
| `preferences` | `POST /driver/preferences/` |
| `vehicle` | Vehicle CRUD |
| `pin` | `POST /pin-verification/` |
| `bank_account` | Stripe Connect bank APIs |

---

## 4. Frontend checklist

- [ ] Phone input: any country (`+` + 8–15 digits)
- [ ] Profile phone unique error handle
- [ ] Link phone/email: request → OTP → confirm
- [ ] Driver readiness on driver home / go-online
- [ ] Disable accept/online when `ready_for_rides` is false
- [ ] Show each `checks` item as true/false

---

## 5. Quick reference

| Method | Path | Auth |
|--------|------|------|
| PUT/PATCH | `/api/v1/accounts/me/` | JWT |
| POST | `/api/v1/accounts/me/contact/request/` | JWT |
| POST | `/api/v1/accounts/me/contact/confirm/` | JWT |
| GET | `/api/v1/accounts/driver/readiness/` | JWT (Driver) |
