# Book for someone else (Switch rider) — frontend contract

**Kimga:** frontend (`hola_rider`, driver `holadrive`)  
**Mahsulot:** Figma **Switch rider** — o‘zing yoki boshqa odam uchun taksi.  
**Base:** `/api/v1/`  
**Holat:** backend ishga tushgan.

---

## Qisqa

| UI | Backend |
|----|---------|
| **Me** | Create da `booked_for` yo‘q yoki `"me"`. Payer = passenger = JWT user. |
| **John Doe** (saqlangan) | `GET /order/saved-riders/` → create da `booked_for: "someone_else"` + `saved_rider_id`. |
| **Add new contact / New rider** | `POST /order/saved-riders/` **yoki** create da `guest` + `save_guest: true`. |
| **Choose a rider** (device contacts) | Faqat FE. Tanlangan name/phone/email ni `guest` yoki saved-riders ga yuboring. |
| **Later** (“Share ride info with others coming”) | **Switch rider dan olib tashlang.** Bu trip share: `POST /safety/share/` (order yaratilgandan keyin). Scheduled ride esa **Pickup now** tugmasi: `when: "later"`. |

Payer **har doim** logged-in user. Guest akkaunt ochilmaydi. Haydovchi `passenger` dan kimni olishini ko‘radi.

`additional-passenger/` — safarda **yana bir** odam (o‘zing bilan). Switch rider emas.

---

## Rider ekranlar

### 1) For me → Switch rider

FE o‘zi: Me / saved list / Add new contact.

`GET /order/saved-riders/` — **Me yo‘q** (u current user). Ro‘yxat = John Doe qatorlari.

**Ok** bosilganda faqat tanlovni saqlang. Order hali yaratilmaydi.

### 2) Add new contact → New rider

| Field | Required |
|-------|----------|
| Full Name | ha |
| Phone Number | ha (`+1…`, E.164) |
| Email | yo‘q, lekin Figma formda to‘ldirish mumkin |

Button enable: name + phone (email ixtiyoriy).

Ikki yo‘l (ikkalasi ham OK):

**A.** Avval saqlash, keyin create:

```http
POST /api/v1/order/saved-riders/
{ "full_name": "John Doe", "email": "j@x.com", "phone_number": "+16251234567" }
```

Keyin create: `saved_rider_id`.

**B.** Create bilan birga (default `save_guest: true` address book ga yozadi):

```json
"booked_for": "someone_else",
"guest": {
  "full_name": "John Doe",
  "email": "j@x.com",
  "phone_number": "+16251234567"
}
```

### 3) Confirm order

Hozirgi create body + passenger fieldlar. `order_type` ni 2 qoldirish mumkin — `someone_else` da backend `pickup` qilib yozadi.

---

## API

Auth: rider JWT. Path lar `/api/v1/` ostida.

### Saved riders (address book)

| Method | Path |
|--------|------|
| `GET` | `/order/saved-riders/` |
| `POST` | `/order/saved-riders/` |
| `GET` | `/order/saved-riders/{id}/` |
| `PATCH` | `/order/saved-riders/{id}/` |
| `DELETE` | `/order/saved-riders/{id}/` |

POST bir xil telefon bo‘lsa — yangi qator emas, mavjudini yangilaydi.

```json
{
  "message": "Saved riders",
  "status": "success",
  "data": [
    {
      "id": 12,
      "full_name": "John Doe",
      "email": "j@x.com",
      "phone_number": "+16251234567",
      "created_at": "2026-09-03T12:00:00+00:00",
      "updated_at": "2026-09-03T12:00:00+00:00"
    }
  ]
}
```

### Create — Me (o‘zgarmagan)

```json
{
  "address_from": "Pickup",
  "address_to": "Dropoff",
  "latitude_from": "51.0447",
  "longitude_from": "-114.0719",
  "latitude_to": "51.0544",
  "longitude_to": "-114.0667",
  "order_type": 2,
  "ride_type_id": 1,
  "payment_type": "card"
}
```

### Create — saqlangan kontakt

```json
{
  "address_from": "Pickup",
  "address_to": "Dropoff",
  "latitude_from": "51.0447",
  "longitude_from": "-114.0719",
  "latitude_to": "51.0544",
  "longitude_to": "-114.0667",
  "order_type": 2,
  "ride_type_id": 1,
  "payment_type": "card",
  "booked_for": "someone_else",
  "saved_rider_id": 12
}
```

### Create — yangi rider

```json
{
  "address_from": "Pickup",
  "address_to": "Dropoff",
  "latitude_from": "51.0447",
  "longitude_from": "-114.0719",
  "latitude_to": "51.0544",
  "longitude_to": "-114.0667",
  "order_type": 2,
  "ride_type_id": 1,
  "payment_type": "card",
  "booked_for": "someone_else",
  "guest": {
    "full_name": "John Doe",
    "email": "jborisbelov@gmail.com",
    "phone_number": "+16251234567"
  },
  "save_guest": true
}
```

`saved_rider_id` va `guest` **birga** yuborilmaydi.

### `passenger` (create / detail / active / WS)

**Me:**

```json
{
  "booked_for": "me",
  "is_guest": false,
  "full_name": "Boris Belov",
  "email": "boris@…",
  "phone_number": "+1…",
  "saved_rider_id": null
}
```

**Someone else:**

```json
{
  "booked_for": "someone_else",
  "is_guest": true,
  "full_name": "John Doe",
  "email": "j@x.com",
  "phone_number": "+16251234567",
  "saved_rider_id": 12
}
```

UI: `passenger.is_guest` → “Pickup for John Doe”. `user` = to‘lovchi (Boris).

Haydovchi offer / nearby / `new_order` WS da ham `passenger` bor. `client` = booker (rating, to‘lov).

---

## SMS

Twilio sozlangan bo‘lsa, guest telefoniga:

1. Order create — kim chaqirgani, pickup / dropoff.
2. Driver accept — PIN (bo‘lsa).

SMS xatosi orderni 500 qilmaydi.

Consent matni (Figma): FE “Add rider” da ko‘rsatadi. Backend SMS shu ruxsatga tayanadi.

WhatsApp alohida yo‘q — hozircha SMS.

---

## Later ni qayerga qo‘ymaslik

Switch rider dagi **Later** = “Share ride info with others coming”.

- Trip share: `POST /api/v1/safety/share/` `{ "order_id": 32 }` — trip **bor** bo‘lgach.
- Vaqt (Pickup later): `when: "later"` + `scheduled_at` — boshqa tugma. `docs/SCHEDULED_RIDES.md`.

---

## Driver

`passenger.is_guest === true` → ism/telefon guest. PIN baribir orderda; guest SMS da ham ketadi.

---

## Xato

| Holat | HTTP |
|-------|------|
| `someone_else` lekin guest/saved yo‘q | 400 `guest` |
| `saved_rider_id` boshqa userniki | 400 |
| `me` + guest birga | 400 |
| Noto‘g‘ri telefon | 400 `phone_number` |
