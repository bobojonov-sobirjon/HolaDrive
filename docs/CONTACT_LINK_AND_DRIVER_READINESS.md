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
  "completion_percent": 62,
  "checks": {
    "profile": true,
    "profile_photo": false,
    "identification": false,
    "registration_terms": true,
    "preferences": true,
    "vehicle": true,
    "pin": false,
    "bank_account": false
  },
  "details": {
    "profile": {
      "full_name": true,
      "phone_number": true,
      "email": false,
      "date_of_birth": true,
      "address": false
    },
    "identification": {
      "checklist_complete": true,
      "verification_status": "in_review",
      "verification_approved": false,
      "steps_total": 5,
      "steps_accepted": 5
    },
    "bank_account": {
      "stripe_connect_linked": true,
      "bank_linked": false,
      "payouts_enabled": false
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
3. `ready_for_rides === false` → online tugma disable + qaysi step yetishmayotganini ochish
4. `completion_percent` — progress bar
5. `details.identification.verification_status` — `not_submitted` | `in_review` | `approved` | `rejected`

### Qaysi ekranga olib borish

| Check false | Screen / API |
|-------------|--------------|
| `profile` | Edit profile `/me/` |
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
