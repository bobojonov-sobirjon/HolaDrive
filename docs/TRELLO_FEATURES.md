# Trello features — FE / Backend notes

Faqat shu 3 ta vazifa:

1. [Ride cancel reason → order WebSocket](#1-ride-cancel-reason--order-websocket)
2. [Passenger live location for driver](#2-passenger-live-location-for-driver)
3. [Multi-stop rides (+ mid-ride stops)](#3-multi-stop-rides--mid-ride-stops)

---

## 1) Ride cancel reason → order WebSocket

**Status:** backend qilindi.

Bekor qilish sababi REST dan tashqari **order WebSocket** orqali ham yuboriladi (Rider va Driver).

### Socketlar

| Role | URL |
|------|-----|
| Driver | `wss://api.holadrive.app/ws/driver/orders/?token=<JWT>` |
| Rider | `wss://api.holadrive.app/ws/rider/orders/?token=<JWT>` |
| Tracking | `wss://api.holadrive.app/ws/order/{order_id}/tracking/?token=<JWT>` |

### `cancel` obyekti

```json
{
  "cancelled_by": "rider",
  "reason": "change_in_plans",
  "reason_display": "Change in Plans",
  "other_reason": null,
  "created_at": "2026-08-20T12:00:00+00:00",
  "order_driver_id": 123
}
```

UI: `reason === "other"` → `other_reason`; aks holda `reason_display`.

### Eventlar

| Kim bekor qildi | Socket | `type` |
|-----------------|--------|--------|
| Rider | driver orders | `order_cancelled_by_rider` + `cancel` |
| Rider | rider orders | `rider_order_updated` (`change=cancelled_rider`) + `cancel` |
| Driver | rider orders | `order_cancelled_by_driver` **va** `rider_order_updated` + `cancel` |
| Ikkalasi | tracking | `order_cancelled` + `cancel` |

### REST

- Rider: `POST /api/v1/order/{order_id}/cancel/` — `{ "reason", "other_reason?" }`
- Driver: `POST /api/v1/order/driver/cancel/` — `{ "order_id", "reason", "other_reason?" }`

Batafsil: `docs/ORDER_CANCEL_WEBSOCKET.md`

---

## 2) Passenger live location for driver

**Status:** backend qilindi.

Driver passenger GPS ni **mavjud** tracking socket orqali ko‘radi (yangi socket yo‘q).

### WebSocket

```
wss://api.holadrive.app/ws/order/{order_id}/tracking/?token=<JWT>
```

| `type` | Kim uchun |
|--------|-----------|
| `driver_location_update` | Rider |
| `rider_location_update` | **Driver** (yangi) |

```json
{
  "type": "rider_location_update",
  "order_id": 42,
  "rider_id": 17,
  "latitude": "45.5017",
  "longitude": "-73.5673",
  "updated_at": "2026-08-20T12:00:00+00:00"
}
```

Connect da: oxirgi driver + rider snapshot.

Rider WS dan ham push qilishi mumkin:

```json
{ "type": "rider_location", "latitude": 45.50, "longitude": -73.56 }
```

### HTTP

- Rider update: `POST /api/v1/order/rider/location/update/`  
  `{ "latitude", "longitude", "order_id?" }`
- Driver fallback: `GET /api/v1/order/{order_id}/rider/location/`

### Mobile flow

1. Accept dan keyin ikkala app `ws/order/{id}/tracking/` ochadi  
2. Rider ~3–5s: HTTP yoki WS `rider_location`  
3. Driver: `rider_location_update` → passenger marker  

Batafsil: `docs/PASSENGER_LIVE_LOCATION.md`

---

## 3) Multi-stop rides (+ mid-ride stops)

**Status:** hali to‘liq implement qilinmagan (model tayyor, API/flow yo‘q).

### Mahsulot (Trello / Uber uslubi)

Safar oldidan yoki **safar davomida** rider:

1. Oraliq stop / destination qo‘shadi yoki o‘zgartiradi (“Add or change”)
2. “If you update your destination, your fare may change” → tasdiqlaydi
3. Marshrut: Pickup → Stop(lar) → Final dropoff
4. Narx qayta hisoblanadi; driver map da yangi pinlar / route ko‘rinadi

### Modelda allaqachon bor

`OrderItem`:

- `stop_sequence` — stop tartibi (1, 2, 3…)
- `is_final_stop` — oxirgi destination
- `address_*`, `latitude_*`, `longitude_*`, `distance_km`, …

Hozir odatda bitta from→to item; multi-stop uchun bir nechta `OrderItem` ketma-ketligi kerak.

### Backend qilish kerak (plan)

| # | Vazifa |
|---|--------|
| 1 | Order create: pickup + N stop + final destination |
| 2 | Faol trip: stop qo‘shish / destination o‘zgartirish API (masalan `PATCH …/orders/{id}/stops/`) |
| 3 | Yangi marshrut bo‘yicha **narx qayta hisoblash** + rider/driverga ko‘rsatish |
| 4 | Driverga realtime WS: yangi stops + route |
| 5 | Stop progress: `pending` / `arrived` / `completed` (ixtiyoriy) |
| 6 | Price estimate API multi-leg distance |

### FE (keyin)

- Create trip: bir nechta stop UI  
- In-ride: “Add or change” → Go → fare preview  
- Driver map: multiple dropoff pins  

Batafsil plan: `docs/MULTI_STOP_RIDES.md`
