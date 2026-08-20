# Passenger live location for driver

Driver sees the rider’s live GPS on the same order tracking WebSocket (no new socket).

## WebSocket (existing)

```
wss://api.holadrive.app/ws/order/{order_id}/tracking/?token=<JWT>
```

Both **rider** and **assigned driver** may connect.

### Events from server

| `type` | Who needs it | Fields |
|--------|----------------|--------|
| `connection_established` | both | `order_id` |
| `driver_location_update` | rider | `driver_id`, `latitude`, `longitude`, `eta_*`, `tracking_phase` |
| `rider_location_update` | **driver** | `rider_id`, `latitude`, `longitude`, `updated_at`, `order_id` |

Example (driver listens):

```json
{
  "type": "rider_location_update",
  "order_id": 42,
  "rider_id": 17,
  "latitude": "45.50170000000000",
  "longitude": "-73.56730000000000",
  "updated_at": "2026-08-20T12:00:00+00:00"
}
```

On connect, server sends the latest **driver** snapshot and **rider** snapshot (if available).

### Rider can also push over WS

```json
{ "type": "rider_location", "latitude": 45.50, "longitude": -73.56 }
```

## HTTP

### Rider → update location

`POST /api/v1/order/rider/location/update/`  
Auth: Rider JWT

```json
{
  "latitude": 45.5017,
  "longitude": -73.5673,
  "order_id": 42
}
```

`order_id` optional — if omitted, broadcasts to all of the rider’s **active** orders (`accepted` / `on_the_way` / `arrived` / `in_progress`).

### Driver → fetch rider location (fallback)

`GET /api/v1/order/{order_id}/rider/location/`  
Auth: assigned Driver (or the Rider)

## Mobile flow

1. After driver accepts: both apps open `ws/order/{id}/tracking/`
2. Rider: every ~3–5s call `POST …/rider/location/update/` **or** send `rider_location` on the WS
3. Driver: on `rider_location_update` move passenger marker on the map
4. Driver continues `POST …/driver/location/update/` as today (rider already gets `driver_location_update`)
