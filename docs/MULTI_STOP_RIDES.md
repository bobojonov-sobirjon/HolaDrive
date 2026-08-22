# Multi-stop rides — backend contract (tayyor)

**Kimga:** frontend (rider `hola_rider`, driver `holadrive`)  
**Status:** backend ishga tushgan. 1-leg (pickup → dropoff) o‘zgarmagan.  
**Base:** `/api/v1/`

Mapdagi pinlar `order.order_items[]` dan olinadi (har item `latitude_*` / `longitude_*`). Flat `address_from` / `address_to` faqat 2 pin (pickup + final).

---

## Qisqa

| Nima | Holat |
|------|--------|
| Create / price-estimate / manage-price da optional `stops[]` | Bor |
| `POST /order/{id}/stops/` | Bor |
| `OrderItem.stop_sequence`, `is_final_stop` | Bor |
| WS `change: "stops_updated"` rider + driver | Bor |
| Driver nearby / offer da `order_items` | Bor |

**V1 da yo‘q:** stop-by-stop `pending` / `arrived` / `completed`. Driver Navigation SDK zanjir bo‘ylab olib boradi.

---

## Limitlar

| Qoida | Qiymat |
|-------|--------|
| Max oraliq stop | **3** (pickup + 3 stop + 1 final dropoff) |
| `stops` yuborilishi | Faqat kamida 1 ta `type: "stop"` bo‘lsa |
| `stops` yo‘q | Hozirgi 1-leg body — regression yo‘q |
| Mid-ride ruxsat | `accepted`, `on_the_way`, `arrived`, `in_progress` |
| Boshqa status (`pending`, `completed`, `cancelled`, …) | `400` |
| Limit oshsa | `400` |
| Noto‘g‘ri `stops` (ignore qilinmaydi) | `400` |

Koordinatlar **string yoki number** bo‘lishi mumkin (`lat` / `lng` yoki `latitude` / `longitude`).

---

## 1) Create / estimate / manage-price

| Method | Path | Qachon `stops` |
|--------|------|----------------|
| POST | `order/create/` | Oraliq stop bor |
| POST | `order/price-estimate/` | Oraliq stop bor |
| POST | `order/price-estimate/manage-price/` | Oraliq stop bor |

Auth: rider JWT.

### Create body

1-leg maydonlar **har doim** bor. `address_from` / `lat/lng_from` = pickup, `address_to` / `lat/lng_to` = **final** dropoff.

```json
{
  "address_from": "Pickup address",
  "address_to": "Final destination",
  "latitude_from": "41.311081",
  "longitude_from": "69.279737",
  "latitude_to": "41.351200",
  "longitude_to": "69.301400",
  "order_type": 2,
  "ride_type_id": 1,
  "payment_type": "card",
  "adjusted_price": "12.50",
  "stops": [
    { "address": "Pickup address", "lat": 41.311081, "lng": 69.279737, "type": "pickup" },
    { "address": "Cafe Stop", "lat": 41.325000, "lng": 69.285000, "type": "stop" },
    { "address": "Final destination", "lat": 41.351200, "lng": 69.301400, "type": "dropoff" }
  ]
}
```

- `adjusted_price` optional (faqat rider narxni o‘zgartirganda).
- `stops[].type`: `"pickup"` | `"stop"` | `"dropoff"`.
- `stops` tartibi: pickup → stop(lar) → dropoff.
- Estimate / manage-price da ham xuddi shu `stops` + `latitude_from/to`, `longitude_from/to` (manage-price da qo‘shimcha `ride_type_id`, `adjusted_price`).

**Muhim:** `stops` kelmasa — oddiy 1-leg. Kelgan `stops` ignore qilinmaydi; noto‘g‘ri bo‘lsa `400` (FE 1-leg ga avtomatik qaytmasin).

### OrderItem zanjiri

Misol: pickup + 2 stop + final → **3 ta item**:

| stop_sequence | address_from | address_to | is_final_stop |
|---------------|--------------|------------|---------------|
| 1 | Pickup | Stop 1 | false |
| 2 | Stop 1 | Stop 2 | false |
| 3 | Stop 2 | Final | **true** |

1-leg: bitta item, pickup → dropoff, `is_final_stop: true`.

**Narx:** butun marshrut (barcha leg yig‘indisi). Base fare **bir marta**. To‘liq summa `order_items[0]` da (`calculated_price` / `original_price` / `adjusted_price`). Keyingi itemlarda narx `0` — **summalamang**, `[0]` ni o‘qing yoki driver WS dagi `net_price`.

`order_items[0].distance_km` va `estimated_time` — **butun marshrut**. Qolgan itemlarda o‘sha leg masofasi/ETA.

Javobda `order_items` to‘liq qaytadi.

### Map pinlar (muhim)

Har pin = zanjir nuqtasi:

1. Birinchi item: `latitude_from` / `longitude_from` → **pickup**
2. Har item: `latitude_to` / `longitude_to` → keyingi stop yoki final
3. `is_final_stop == true` → **final dropoff**

`order_items` ni `stop_sequence` bo‘yicha sort qiling.

---

## 2) Mid-ride: stop qo‘shish / destination o‘zgartirish

```http
POST /api/v1/order/{id}/stops/
Authorization: Bearer <rider JWT>
```

### Request

```json
{
  "action": "add",
  "address": "New stop or new destination",
  "latitude": "41.330000",
  "longitude": "69.290000"
}
```

`lat` / `lng` ham qabul qilinadi.

| `action` | Ma’nosi |
|----------|---------|
| `add` | Yangi **oraliq** stop. Final dropoff o‘zgarmaydi; yangi stop oxirgi dropoff **oldiga** qo‘shiladi. |
| `replace_destination` | Faqat **oxirgi** dropoff o‘zgaradi. Oraliq stoplar saqlanadi. |

Dry-run yo‘q. FE avval “fare may change” ko‘rsatadi, keyin shu POST ni commit qiladi.

### Response `200`

Ikkala shakl ham bor (`data` wrapper + top-level):

```json
{
  "message": "Stops updated successfully",
  "status": "success",
  "fare_preview": {
    "calculated_price": "18.40"
  },
  "order": { },
  "data": {
    "fare_preview": {
      "calculated_price": "18.40"
    },
    "order": { }
  }
}
```

- `order` — to‘liq order (`order_items`, `driver`, `order_driver`, …).
- `fare_preview.calculated_price` — yangi narx. Bo‘lmasa `order_items[0]` effective price.

### Xatolar

| Holat | HTTP |
|-------|------|
| Order yo‘q | `404` |
| Boshqa user | `403` |
| Status ruxsat etilmagan | `400` |
| Max 3 oraliq oshdi (`add`) | `400` |
| Noto‘g‘ri coord / address / action | `400` |

---

## 3) Reprice

`stops` create yoki mid-ride update dan keyin:

1. Yangi total distance (barcha leg).
2. Ride type + surge bilan qayta hisoblash.
3. `order_items[0]` narxlari yangilanadi.
4. Rider va driver ga REST javob + WS.

---

## 4) WebSocket

FE `change == "stops_updated"` ni kutadi. `order` ichida yangilangan `order_items` bo‘ladi.

### Rider — `/ws/rider/orders/`

```json
{
  "type": "rider_order_updated",
  "change": "stops_updated",
  "message": "Ride stops updated",
  "order": { }
}
```

`order` — id, status, `order_items`, driver, …

### Driver — `/ws/driver/orders/`

Bu xabar **yangi nearby offer emas**. Overlay ochilmasin.

```json
{
  "type": "driver_order_updated",
  "change": "stops_updated",
  "message": "Ride stops updated",
  "order": { }
}
```

FE **faqat** `change: "stops_updated"` ga qarab ajratadi. `order.id` aktiv tripga mos kelmasa — ignore.

Tracking WS (`/ws/order/{id}/tracking/`) da stops refresh v1 shart emas — order WS yetarli.

---

## 5) Driver offer / nearby

Yangi buyurtmada ham `order_items` keladi. Aks holda map faqat 2 pin.

- WS `new_order` / `initial_orders` — `order.order_items`
- REST `GET /api/v1/order/driver/nearby-orders/` — har orderda `order_items`

Flat maydonlar:

- `address_from` / `latitude_from` / `longitude_from` → pickup
- `address_to` / `latitude_to` / `longitude_to` → **final** dropoff (birinchi item emas)
- `net_price` (WS) → to‘liq marshrut narxi

1-leg: bitta `order_item`. Multi-stop: bir nechta item — map shundan.

---

## 6) `order_items[]` maydonlari

| Field | Izoh |
|-------|------|
| `id` | OrderItem id |
| `address_from` / `address_to` | Leg manzillari |
| `latitude_from` / `longitude_from` | Leg boshi |
| `latitude_to` / `longitude_to` | Leg oxiri (stop yoki dropoff) |
| `stop_sequence` | 1, 2, 3… |
| `is_final_stop` | Oxirgi dropoff leg |
| `distance_km` | `[0]` = butun marshrut; qolganlari = o‘sha leg |
| `estimated_time` | `"12 min"` / `"1h 5m"` |
| `calculated_price` / `original_price` / `adjusted_price` | To‘liq fare faqat `[0]` da |
| `min_price` / `max_price` | Manage-price oralig‘i (`[0]`) |
| `ride_type` | id, name, … |

---

## FE checklist

- [ ] Create: `stops` bilan → N ta `order_item`, mapda pickup + stoplar + final
- [ ] Create: `stops` yo‘q → 1-leg, 2 pin
- [ ] Estimate narxi 1-leg dan katta (masofa oshganda)
- [ ] Create `stops` 4xx → toast, 1-leg ga avtomatik qaytmasin
- [ ] `POST …/stops/` `add` — yangi pin + reprice
- [ ] `replace_destination` — faqat final pin o‘zgaradi
- [ ] `pending` / `completed` da “Add or change” yashiriladi (yoki 400)
- [ ] 4-chi `add` → toast (400)
- [ ] Driver: `stops_updated` yangi offer overlay ochmaydi, route/marker refresh
- [ ] Nearby/offer da `order_items` dan pinlar

---

## Eski orderlar

Shu API dan **oldin** yaratilgan tripda `stops` saqlanmagan (faqat 1 item). Mapda stop chiqishi uchun **yangi** buyurtma `stops[]` bilan yaratilishi kerak.
