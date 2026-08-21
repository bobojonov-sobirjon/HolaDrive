# Multi-stop rides (+ mid-ride stops)

**Status:** backend API bor — `stops[]` create/estimate da, `POST /api/v1/order/{id}/stops/`, WS `change: stops_updated`.

## Nima kerak (Trello)

Rider safar oldidan yoki **yo‘lda**:

1. Oraliq stop qo‘shadi yoki destination o‘zgartiradi  
2. “Fare may change” ogohlantirishini tasdiqlaydi  
3. Marshrut yangilanadi (bir nechta pin)  
4. Narx qayta hisoblanadi; driver ham yangi marshrutni ko‘radi  

## Model

`OrderItem` (order ga bog‘langan):

| Field | Ma’nosi |
|-------|---------|
| `address_from` / `address_to` | Manzillar |
| `latitude_*` / `longitude_*` | Koordinatalar |
| `stop_sequence` | Tartib (1, 2, 3…) |
| `is_final_stop` | Oxirgi dropoff |
| `distance_km`, `estimated_time`, `ride_type` | Narx / ETA |

1-leg: bitta item, pickup → dropoff, `is_final_stop=true`.  
Multi-stop: pickup → stop(lar) → final; oxirgi item `is_final_stop=true`. To‘liq marshrut narxi `order_items[0]` da (base fare bir marta).

## API

```http
POST /api/v1/order/create/
POST /api/v1/order/price-estimate/
POST /api/v1/order/price-estimate/manage-price/
```

Optional `stops[]`: `{ address, lat, lng, type: pickup|stop|dropoff }`. Yo‘q bo‘lsa — oddiy A→B.

```http
POST /api/v1/order/{id}/stops/
{
  "action": "add" | "replace_destination",
  "address": "...",
  "latitude": ...,
  "longitude": ...
}
→ { "fare_preview": { "calculated_price": "..." }, "order": {...} }
```

Faqat `accepted` / `on_the_way` / `arrived` / `in_progress`. Max 3 oraliq stop.

WS: `rider_order_updated` va `driver_order_updated` — `change: "stops_updated"`, `order.order_items[...]`. Nearby/offer payloadida ham `order_items` bor (map pinlari shundan).
