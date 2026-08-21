# Ride cancel reason — WebSocket (FE)

Bekor qilish sababi endi faqat REST javobida emas — **order WebSocket** orqali ham keladi (Rider ham, Driver ham).

---

## Qisqa xulosa

| Kim bekor qildi | Qaysi socket | Event `type` | Sabab qayerda |
|-----------------|--------------|--------------|---------------|
| Rider | `ws/driver/orders/` | `order_cancelled_by_rider` | `cancel` (+ `order.cancel`) |
| Rider | `ws/rider/orders/` | `rider_order_updated` (`change=cancelled_rider`) | `cancel` / `order.cancel` |
| Driver | `ws/rider/orders/` | `order_cancelled_by_driver` **va** `rider_order_updated` | `cancel` / `order.cancel` |
| Ikkalasi | `ws/order/{order_id}/tracking/` | `order_cancelled` | `cancel` |

UI alert uchun: `order_cancelled_by_*` yoki tracking dagi `order_cancelled`.  
State sync uchun: `rider_order_updated`.

---

## Socket URL lar

```
wss://api.holadrive.app/ws/driver/orders/?token=<JWT>
wss://api.holadrive.app/ws/rider/orders/?token=<JWT>
wss://api.holadrive.app/ws/order/<order_id>/tracking/?token=<JWT>
```

(Local: `ws://…` — loyiha `WEBSOCKET_*` sozlamasiga qarab.)

---

## Umumiy `cancel` obyekti

Har bir cancel eventda (top-level) va ko‘pincha `order.cancel` ichida ham:

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

| Field | Ma’nosi |
|-------|---------|
| `cancelled_by` | `"rider"` yoki `"driver"` |
| `reason` | API choice code (pastda) |
| `reason_display` | Odamiy matn (UI uchun) |
| `other_reason` | `reason === "other"` bo‘lsa matn; aks holda `null` |
| `created_at` | ISO datetime |
| `order_driver_id` | Optional — `CancelOrder` → `OrderDriver` bog‘langanda |

**UI qoida:** `reason == "other"` → `other_reason` ko‘rsat; aks holda `reason_display` (yoki `reason`).

---

## 1) Rider bekor qildi → Driver

**REST:** `POST /api/v1/order/{order_id}/cancel/`  
Body: `{ "reason": "...", "other_reason": "..." }`

**Driver WS event:**

```json
{
  "type": "order_cancelled_by_rider",
  "change": "cancelled_rider",
  "message": "The rider cancelled this ride.",
  "order": { "...": "order detail", "cancel": { "...": "..." } },
  "cancel": {
    "cancelled_by": "rider",
    "reason": "change_in_plans",
    "reason_display": "Change in Plans",
    "other_reason": null,
    "created_at": "2026-08-20T12:00:00+00:00"
  }
}
```

Rider o‘z socketida: `rider_order_updated` + `change: "cancelled_rider"` + `cancel`.

---

## 2) Driver bekor qildi → Rider

**REST:** `POST /api/v1/order/driver/cancel/`  
Body: `{ "order_id": 123, "reason": "...", "other_reason": "..." }`

Riderga **ikki** event ketadi:

### A) `order_cancelled_by_driver` (asosiy alert)

```json
{
  "type": "order_cancelled_by_driver",
  "change": "cancelled_driver",
  "message": "Your ride has been cancelled by the driver.",
  "order": {
    "id": 123,
    "status": "cancelled",
    "cancel": { "...": "..." }
  },
  "cancel": {
    "cancelled_by": "driver",
    "reason": "rider_not_at_pickup",
    "reason_display": "Rider Not at Pickup Location",
    "other_reason": null,
    "created_at": "2026-08-20T12:00:00+00:00",
    "order_driver_id": 45
  }
}
```

### B) `rider_order_updated` (state sync)

```json
{
  "type": "rider_order_updated",
  "change": "cancelled_driver",
  "message": "Your ride has been cancelled by the driver.",
  "order": { "status": "cancelled", "cancel": { "...": "..." } },
  "cancel": { "...": "same cancel object" }
}
```

---

## 3) Live map / tracking socket

Agar trip paytida `ws/order/{order_id}/tracking/` ochiq bo‘lsa:

```json
{
  "type": "order_cancelled",
  "order_id": 123,
  "change": "cancelled_driver",
  "message": "Your ride has been cancelled by the driver.",
  "cancel": { "...": "..." },
  "order": { "...": "rider order payload" }
}
```

`change`: `cancelled_driver` yoki `cancelled_rider`.

---

## Reason code lar (REST body)

### Rider cancel

| `reason` | Display |
|----------|---------|
| `change_in_plans` | Change in Plans |
| `waiting_for_long_time` | Waiting for Long Time |
| `driver_denied_to_go_to_destination` | Driver Denied to Go to Destination |
| `driver_denied_to_come_to_pickup` | Driver Denied to Come to Pickup |
| `wrong_address_shown` | Wrong Address Shown |
| `the_price_is_not_reasonable` | The Price is Not Reasonable |
| `emergency_situation` | Emergency Situation |
| `other` | Other → `other_reason` majburiy |

### Driver cancel

| `reason` | Display |
|----------|---------|
| `rider_not_at_pickup` | Rider Not at Pickup Location |
| `rider_asked_to_cancel` | Rider Asked to Cancel |
| `vehicle_issue` | Vehicle Issue |
| `safety_concern` | Safety Concern |
| `emergency_situation` | Emergency Situation |
| `other` | Other → `other_reason` majburiy |

---

## Flutter / client checklist

1. Driver app: `order_cancelled_by_rider` → dialog + `cancel.reason_display` / `other_reason`.
2. Rider app: `order_cancelled_by_driver` → dialog + sabab; `rider_order_updated` bilan list/status yangilash.
3. Tracking screen: `order_cancelled` → map yopish / cancel UI.
4. Push FCM `data` da ham `reason`, `reason_display`, `other_reason`, `cancelled_by` bor (background).

---

## Backend o‘zgarishlar (qisqa)

- `apps/order/services/cancel_ws.py` — umumiy `cancel` payload
- Rider/Driver order WS + `OrderTrackingConsumer`
- `OrderCancelView` / `DriverCancelOrderView` — WS broadcast

Deploy dan keyin: `sudo systemctl restart hola_daphne.service`
