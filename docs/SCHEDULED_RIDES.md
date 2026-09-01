# Scheduled rides (Now / Later) — frontend contract

**Kimga:** frontend (`hola_rider`, driver `holadrive`)  
**Mahsulot:** Uber Reserve uslubi — Later buyurtma **hozir haydovchi qidirilmaydi**.  
**Base:** `/api/v1/`  
**Holat:** backend ishga tushgan. Eski 2-qadamli `create/` + `schedule/` flow **ishlatilmaydi**.

---

## Qisqa

| UI | Backend |
|----|---------|
| **Now** | `POST /order/create/` — `when` yo‘q yoki `"now"`. Haydovchi darhol. |
| **Later** | `POST /order/create/` ichida `when: "later"` + `scheduled_at`. Haydovchi **vaqt yaqinida**. |
| Pickup at / Dropoff by | `schedule_type`: `pickup_at` \| `drop_off_by` |
| Today / Tomorrow / calendar | **Faqat FE**. API ga bitta ISO datetime ketadi. |
| Ride scheduled | Create `201` + `status: "scheduled"` |
| Activity — upcoming | `GET /order/scheduled/` |
| Vaqtni o‘zgartirish | `PATCH /order/{id}/schedule/` |
| Bekor qilish | `POST /order/{id}/cancel/` (scheduled qoida) |

**Now** va **Later** ikkala ham bitta create. Alohida `POST /order/schedule/` chaqirmang.

---

## Rider ekranlar

### 1) When do you need a ride?

| Tanlov | Keyingi qadam |
|--------|----------------|
| Now | Oddiy create. Schedule field yuborilmaydi. |
| Later | Choose a time |

### 2) Choose a time

FE o‘zi:

- chip: Today / Tomorrow / Select date
- `pickup_at` yoki `drop_off_by`
- sana + soat picker (lokal timezone, masalan Calgary `America/Edmonton`)

API ga faqat:

```json
{
  "when": "later",
  "schedule_type": "pickup_at",
  "scheduled_at": "2026-09-17T20:00:00-06:00"
}
```

`today` / `tomorrow` / `select_date` **body da yo‘q**.

`drop_off_by`: rider “shu vaqtgacha yetib borish” ni tanlaydi. `scheduled_at` = **yetib borish** vaqti. Pickup vaqtini backend duration dan hisoblaydi (`schedule.pickup_at` javobda).

### 3) Ride scheduled (success)

Create `201` dan:

- pickup / dropoff
- `schedule.display_at` (lokal format, masalan `Wed, Sep 17 · 8:00 PM`)
- `schedule.timezone` (masalan `MDT`)
- “See in Activity”

Haydovchi qidiruv / map tracking **ochilmaydi**. `status === "scheduled"`.

### 4) Activity — upcoming

`GET /order/scheduled/` — faqat kelgusi Later trip lar (`scheduled` + hali dispatch bo‘lmagan / yaqinlashgan).

Completed / cancelled — `GET /order/rider/ride-history/`.

---

## API

Auth: rider JWT. Barcha path lar `/api/v1/` ostida.

### Create — Now

Hozirgi create body. `when` ixtiyoriy.

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

Javob: `status: "pending"` — haydovchi offer (hozirgi Now flow).

### Create — Later

Create body +:

| Field | Required | Izoh |
|-------|----------|------|
| `when` | ha (`later`) | `"now"` \| `"later"` |
| `scheduled_at` | `later` da ha | ISO 8601, offset bilan |
| `schedule_type` | yo‘q | default `pickup_at` |

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
  "when": "later",
  "schedule_type": "pickup_at",
  "scheduled_at": "2026-09-17T20:00:00-06:00"
}
```

**201** — order + `schedule`:

```json
{
  "message": "Order created successfully",
  "status": "success",
  "data": {
    "id": 42,
    "status": "scheduled",
    "schedule": {
      "type": "pickup_at",
      "scheduled_at": "2026-09-17T20:00:00-06:00",
      "pickup_at": "2026-09-17T20:00:00-06:00",
      "dropoff_by": null,
      "timezone": "America/Edmonton",
      "dispatch_at": "2026-09-17T19:30:00-06:00",
      "can_edit": true,
      "can_cancel_free": true,
      "free_cancel_until": "2026-09-17T19:00:00-06:00"
    }
  }
}
```

`drop_off_by` bo‘lsa: `scheduled_at` = arrive-by, `pickup_at` = hisoblangan pickup, `dropoff_by` = rider tanlagan vaqt.

**400** — o‘tgan vaqt, juda yaqin, juda uzoq (pastdagi limitlar).

Later da haydovchi **yo‘q**. Rider WS `ws/rider/orders/` da bu order “now offer” emas.

---

### `GET /order/scheduled/`

Upcoming Later trip lar, `scheduled_at` o‘sish tartibida.

Query (ixtiyoriy): `page`, `page_size`.

Har item — `OrderSerializer` + `schedule` (yuqoridagi obyekt).

Bo‘sh: `data: []`.

---

### `GET /order/{id}/` va `GET /order/my-orders/`

`schedule` maydoni:

- Later: to‘liq obyekt
- Now: `null`

`GET /order/my-orders/?status=scheduled` — Activity uchun ham ishlaydi (`GET /order/scheduled/` qulayroq).

---

### `PATCH /order/{id}/schedule/`

Faqat `status=scheduled` (hali haydovchi qabul qilmagan).

```json
{
  "schedule_type": "pickup_at",
  "scheduled_at": "2026-09-17T21:00:00-06:00"
}
```

**200** — yangilangan order + `schedule`.  
**400** — trip allaqachon dispatch / accepted, yoki vaqt limitdan tashqari.

---

### `POST /order/{id}/cancel/`

Hozirgi cancel body: `{ "reason", "other_reason?" }`.

| Holat | Natija |
|-------|--------|
| `scheduled`, pickup gacha ≥ 60 daqiqa | bepul |
| `scheduled`, pickup gacha < 60 daqiqa | fee (javobda `cancel_fee` bo‘lsa ko‘rsatilsin) |
| Now (`pending` …) | hozirgi umumiy cancel |

---

## Limitlar (FE validatsiya + backend 400)

| Qoida | Qiymat |
|-------|--------|
| Min oldindan | **30 daqiqa** (`scheduled_at` ≥ now + 30m) |
| Max | **7 kun** |
| Dispatch | pickup dan **30 daqiqa oldin** haydovchi qidiriladi |
| Bepul cancel | pickup dan **60 daqiqa** oldin |
| `scheduled_at` | offset **majburiy** (`Z` yoki `-06:00`) |

Picker da o‘tgan slotlarni o‘chiring. Backend baribir tekshiradi.

---

## Order `status` (Later)

```
scheduled  →  pending  →  accepted → on_the_way → … → completed
                 ↑
           dispatch_at da
```

| `status` | Rider UI |
|----------|----------|
| `scheduled` | Ride scheduled / Activity. Map tracking yo‘q. |
| `pending` | Haydovchi qidirilmoqda (Now dagi kabi). |
| `accepted`+ | Oddiy trip flow. |

`scheduled` → `pending` o‘tganda rider WS: `rider_order_updated` (`change: "scheduled_dispatch"` yoki status yangilanishi). Shu paytdan searching UI.

---

## Driver

| Holat | Driver app |
|-------|------------|
| Rider `scheduled` | Nearby / offer **yo‘q** |
| `dispatch_at` | Oddiy nearby + offer (Now kabi) |
| Accept dan keyin | Tracking, chat — o‘zgarmaydi |

Driverga “3 kundan keyin trip” kartochkasi v1 da yo‘q.

---

## FE qilmasligi kerak

1. `POST /order/create/` (Later) keyin `POST /order/schedule/` — **yo‘q**. `when` + `scheduled_at` create da.
2. `schedule_time_type`: `today` / `tomorrow` / `select_date` ni API ga yuborish.
3. Later success da “Finding your driver”.
4. `ws/order/{id}/tracking/` ni `scheduled` da ochish.
5. Bir nechta schedule qatori — bitta `schedule` obyekti.

Eski `POST /order/schedule/` — legacy. Yangi UI ulanmasin.

---

## Mobile flow (qisqa)

```
Pickup / dropoff / ride type / narx
        │
        ├─ Now  → POST /order/create/
        │         status=pending → finding driver
        │
        └─ Later → vaqt picker (lokal)
                   POST /order/create/  { when:"later", scheduled_at, schedule_type }
                   status=scheduled → Ride scheduled
                   Activity: GET /order/scheduled/
                   Edit: PATCH /order/{id}/schedule/
                   Cancel: POST /order/{id}/cancel/
                   ~30 min oldin: status=pending → searching (WS)
```

---

## V1 da yo‘q (keyinroq)

- Traffic asosida “About 10 mins ride” / live ETA
- Haydovchi oldindan Reserve calendar
- 24 soat / 1 soat reminder copy ni backend push qilishi mumkin — FE deep link: Activity / order detail

---

## Related

| Endpoint | Qachon |
|----------|--------|
| `POST /order/create/` | Now va Later |
| `GET /order/scheduled/` | Activity upcoming |
| `GET /order/{id}/` | Detail + `schedule` |
| `PATCH /order/{id}/schedule/` | Vaqt o‘zgartirish |
| `POST /order/{id}/cancel/` | Bekor |
| `GET /order/rider/ride-history/` | O‘tgan trip lar |
| `wss://…/ws/rider/orders/` | `scheduled` → `pending` |

Kod: `Order`, `OrderSchedule`, create serializer (`when`, `scheduled_at`).
