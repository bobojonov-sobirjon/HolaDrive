# Trip Share — Frontend (Flutter / Mobile)

Do‘stga trip holatini ulashish: rider link yaratadi → do‘st app yoki brauzerda **jonli xarita** ko‘radi.

Base API: `/api/v1/safety/`  
Auth: JWT (create / list / revoke)  
Public: JWT **kerak emas** (status + live WS)

---

## 1. Maqsad (UI)

Do‘st ko‘rishi kerak:

| Narsa | Xaritada | Matnda |
|--------|----------|--------|
| **A — Pickup** | Yashil pin | From address |
| **B — Destination** | Qizil pin | To address |
| **Driver hozir** | Orange live marker (WS) | Driver name + ETA |
| Status | — | `accepted` / `on_the_way` / … |

**Qilmang:**

- A→B **to‘g‘ri chiziq** (dashed polyline) chizmang
- Raw **lat/long** matn ko‘rsatmang
- Telefon / email / to‘lov ma’lumotini kutmang (public API da yo‘q)

**Qiling:**

- Asosiy e’tibor: **driver qayerda** (real-time)
- Destination pin: **qayerga ketayotgani**
- Pickup pin: **qayerdan**

---

## 2. Rider: share yaratish

Faqat **active** trip: `accepted` | `on_the_way` | `arrived` | `in_progress`  
Faqat **rider** (order egasi).

### `POST /api/v1/safety/share/`
Auth: JWT

```json
{ "order_id": 61 }
```

Response `data` (muhim fieldlar):

```json
{
  "token": "AbCdEf123...",
  "share_url": "http://127.0.0.1:8001/trip/share/AbCdEf123...",
  "deep_link": "holadrive://trip/share/AbCdEf123...",
  "public_api_url": "http://127.0.0.1:8001/api/v1/safety/share/AbCdEf123.../",
  "ws_url_path": "/ws/safety/share/AbCdEf123.../",
  "order_id": 61,
  "order_status": "on_the_way",
  "expires_at": "2026-07-25T18:00:00Z",
  "is_valid": true
}
```

| Field | Flutter |
|--------|---------|
| `share_url` | Native Share sheet (WhatsApp / SMS) — **shu linkni** ulashing |
| `deep_link` | App ichida ochish / Universal Link fallback |
| `token` | Deep link route param |
| `ws_url_path` | Live map WS |

### Boshqa

- `GET /api/v1/safety/share/list/` — mening aktiv linklarim  
- `DELETE /api/v1/safety/share/<token>/revoke/` — linkni o‘chirish  

---

## 3. Do‘st / App: deep link ekran

### Deep link

```
holadrive://trip/share/<token>
```

Landing (brauzer, app yo‘q bo‘lsa):

```
{BASE}/trip/share/<token>/
```

Local misol:

```
http://127.0.0.1:8001/trip/share/<token>/
```

### App oqimi

```
1. Deep link → token olish
2. GET /api/v1/safety/share/<token>/   (auth yo‘q)
3. Xaritaga A, B, live marker chizish
4. WS  /ws/safety/share/<token>/       (auth yo‘q)
5. driver_location_update → live markerni yangilash
```

---

## 4. Public snapshot API

### `GET /api/v1/safety/share/<token>/`
Auth: **yo‘q**

```json
{
  "message": "...",
  "status": "success",
  "data": {
    "token": "...",
    "expires_at": "...",
    "order": {
      "id": 61,
      "order_code": "ORD-000061",
      "status": "on_the_way",
      "pickup": "string A",
      "destination": "string B",
      "pickup_latitude": 39.7664393,
      "pickup_longitude": 64.4342933,
      "destination_latitude": 39.8327373,
      "destination_longitude": 64.4348037
    },
    "route": {
      "pickup": { "latitude": 39.7664393, "longitude": 64.4342933 },
      "destination": { "latitude": 39.8327373, "longitude": 64.4348037 }
    },
    "driver": {
      "id": 14,
      "full_name": "Muzaffar Bobojomov"
    },
    "location": {
      "latitude": "39.76644",
      "longitude": "64.43429",
      "updated_at": "...",
      "eta_minutes": 0,
      "tracking_phase": "to_pickup"
    },
    "ws_url_path": "/ws/safety/share/<token>/"
  }
}
```

### Xarita mapping

```dart
// Pseudocode
A = data.route.pickup          // yoki order.pickup_latitude/longitude
B = data.route.destination
live = data.location           // null bo‘lishi mumkin → "Waiting for driver GPS"
```

`tracking_phase` misollari: `to_pickup` | `to_destination` | `unknown`

---

## 5. Live WebSocket

```
ws://<host>/ws/safety/share/<token>/
wss://<host>/ws/safety/share/<token>/
```

JWT **kerak emas**.

### Connect

```json
{ "type": "connection_established", "order_id": 61, "token": "..." }
```

### Live update

```json
{
  "type": "driver_location_update",
  "order_id": 61,
  "driver_id": 14,
  "latitude": "39.77000",
  "longitude": "64.44000",
  "updated_at": "...",
  "eta_minutes": 5,
  "eta_to_pickup_minutes": 5,
  "eta_to_destination_minutes": 18,
  "tracking_phase": "to_pickup"
}
```

Flutter:

1. Live markerni `latitude` / `longitude` ga suring  
2. ETA matnini yangilang  
3. Ixtiyoriy: camera follow driver  

Driver GPS yubormasa `location` bo‘sh qolishi mumkin — A/B pinlar turadi, live marker keyin chiqadi.

---

## 6. Tavsiya etilgan UI (bitta ekran)

```
┌─────────────────────────┐
│ Logo  HolaDrive         │
│                         │
│        [ MAP ]          │  A green · B red · live orange
│                         │
├─────────────────────────┤
│ Shared trip    [status] │
│ From | To               │
│ Driver                  │
│ ETA · phase             │
│ [Open in app]           │  (brauzer landing uchun)
└─────────────────────────┘
```

- Responsive / bitta viewport (map + bottom sheet)  
- Brand: `#1B1B1B` bg, `#E62A00` primary, logo `hola_logo.png`  

---

## 7. Xato kodlari

| code | Ma’nosi | UI |
|------|---------|-----|
| `not_found` | Token noto‘g‘ri | "Link not found" |
| `share_inactive` | Expire / revoke | "Link expired" |
| `trip_ended` | Trip tugagan | "Trip ended" |
| `invalid_order_status` | Create paytida trip active emas | Share tugmasini disable |
| `forbidden` | Boshqa odamning orderi | — |

---

## 8. Checklist (Flutter)

- [ ] Safety sheet → Share → `POST /share/` → native share (`share_url`)
- [ ] Deep link: `holadrive://trip/share/:token`
- [ ] Screen: `GET` public share → A/B/live pins
- [ ] WS live update (no auth)
- [ ] No A→B straight line
- [ ] No raw coordinates on UI
- [ ] Revoke from rider trip/safety UI
- [ ] Handle expire / trip_ended

---

## 9. Local test

```
BASE=http://127.0.0.1:8001

# Landing
http://127.0.0.1:8001/trip/share/<token>/

# Public JSON
http://127.0.0.1:8001/api/v1/safety/share/<token>/

# WS
ws://127.0.0.1:8001/ws/safety/share/<token>/
```

Env (backend):

```
APP_DEEP_LINK_SCHEME=holadrive
APP_SHARE_HTTPS_BASE=http://127.0.0.1:8001
```

Prod da `APP_SHARE_HTTPS_BASE` API hostga qo‘yiladi (masalan `https://api.autohandy.app`).

---

## 10. Related

To‘liq safety sheet (911, agent chat, voice recording):  
`docs/SAFETY_TOOLS_FRONTEND.md`
