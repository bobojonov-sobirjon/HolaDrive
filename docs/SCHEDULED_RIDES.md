# Scheduled rides (Now / Later) — backend

**Kimga:** frontend (`hola_rider`)  
**Holat:** qisman bor. Figma: *When do you need a ride? → Choose a time → Ride scheduled.*  
**Base:** `/api/v1/`

---

## Qisqa

| Figma | Backend |
|--------|---------|
| **Now** — hozir buyurtma | Alohida flag yo‘q. Oddiy `POST /order/create/` (schedule yo‘q). |
| **Later** — vaqt tanlash | `POST /order/schedule/` — orderga pickup/dropoff vaqti yoziladi |
| Pickup at / Dropoff by | `schedule_type`: `pickup_at` \| `drop_off_by` |
| Today / Tomorrow / Select date | `schedule_time_type`: `today` \| `tomorrow` \| `select_date` |
| Sana + soat picker | `schedule_date` + `schedule_time` |
| Ride scheduled / Activity | **Yo‘q** — list/GET/update/delete endpoint yo‘q |
| Traffic asosida dropoff estimate | **Yo‘q** |
| Cancel free 1 hour before pickup | **Yo‘q** (umumiy cancel bor) |
| Vaqt yetganda driverga offer | **Yo‘q** — create dan keyin driver **darhol** assign qilinadi |

---

## Model: `OrderSchedule`

`apps/order/models.py`

| Field | Type | Qiymatlar |
|-------|------|-----------|
| `order` | FK → Order | Rider order |
| `schedule_type` | string | `pickup_at`, `drop_off_by` |
| `schedule_time_type` | string | `today`, `tomorrow`, `select_date` |
| `schedule_date` | date | optional; bo‘sh bo‘lsa order `created_at` sanasi |
| `schedule_time` | time | optional; bo‘sh bo‘lsa order `created_at` vaqti |

Bir orderda bir nechta schedule yozuvi chiqishi mumkin (update emas, har safar **create**).

---

## API

Auth: rider JWT.

### `POST /api/v1/order/schedule/`

Order **avval** `POST /order/create/` bilan yaratiladi, keyin schedule ulanadi.

**Body**

```json
{
  "order_id": 42,
  "schedule_type": "pickup_at",
  "schedule_time_type": "tomorrow",
  "schedule_date": "2026-09-17",
  "schedule_time": "20:00:00"
}
```

| Field | Required | Izoh |
|-------|----------|------|
| `order_id` | ha | Faqat shu user orderi |
| `schedule_type` | ha | `pickup_at` yoki `drop_off_by` |
| `schedule_time_type` | ha | `today` \| `tomorrow` \| `select_date` |
| `schedule_date` | yo‘q | `YYYY-MM-DD` |
| `schedule_time` | yo‘q | `HH:MM:SS` |

**201**

```json
{
  "message": "Order schedule created successfully",
  "status": "success",
  "data": {
    "id": 1,
    "order": 42,
    "schedule_type": "pickup_at",
    "schedule_date": "2026-09-17",
    "schedule_time": "20:00:00",
    "schedule_time_type": "tomorrow",
    "created_at": "2026-08-31T06:00:00Z",
    "updated_at": "2026-08-31T06:00:00Z"
  }
}
```

**400** — validation; order topilmasa yoki boshqa userniki.

---

## FE flow (hozirgi backend bilan)

```
1. Pickup / dropoff / ride type / price
2. Now  → POST /order/create/   (tugadi)
   Later → POST /order/create/
         → POST /order/schedule/  { order_id, schedule_type, schedule_time_type, schedule_date, schedule_time }
3. Success UI — schedule 201 dan
```

**Now** uchun schedule chaqirilmaydi.

---

## Yo‘q narsalar (Figma vs backend)

1. **Now / Later** alohida enum — FE o‘zi ajratadi.
2. **GET** scheduled rides (Activity: “You can see scheduled rides in the activity menu”).
3. Schedule **update / delete**.
4. **Timezone** (Figma: `8:20 pm MDT`) — server UTC; timezone field yo‘q.
5. **ETA / traffic** (“About 10 mins ride”, projected dropoff).
6. **Dispatch delay** — scheduled order ham hozirgi kabi darhol driverga ketadi. Later uchun worker/queue yo‘q.
7. **1 soat oldin bepul cancel** — `POST /order/{id}/cancel/` umumiy qoida.

---

## Related

| Endpoint | Vazifa |
|----------|--------|
| `POST /order/create/` | Order (Now yoki Later asosi) |
| `POST /order/{id}/cancel/` | Bekor qilish |
| `GET /order/my-orders/` | Order list (schedule filter yo‘q) |
| `GET /order/rider/ride-history/` | Tarix |

Kod: `OrderSchedule`, `OrderScheduleSerializer`, `OrderScheduleCreateView`.
