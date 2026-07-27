# Safety Tools API — Mobile Frontend

Base: `/api/v1/safety/`  
Auth: `Authorization: Bearer <ACCESS_JWT>`  
(Public share endpoints — JWT kerak emas)

---

## 0. Umumiy response

Success:
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
  "code": "forbidden",
  "errors": {}
}
```

---

## 1. Safety tools config (menu)

### `GET /api/v1/safety/tools/`
Auth: JWT

Response `data`:
```json
{
  "emergency_number": "911",
  "emergency_tel_uri": "tel:911",
  "features": {
    "contact_911": true,
    "contact_safety_agent": true,
    "voice_recording": true,
    "share_trip_status": true
  }
}
```

**Contact 911:** app `tel:911` ochadi (backend chaqirish shart emas).

---

## 2. Share trip status

Faqat **active** order: `accepted` | `on_the_way` | `arrived` | `in_progress`  
Faqat **rider** share qila oladi.

### 2.1 Create share link
`POST /api/v1/safety/share/`  
Auth: JWT

Body:
```json
{ "order_id": 61 }
```

Response `data` misol:
```json
{
  "id": 1,
  "token": "AbCdEf123...",
  "share_url": "https://api.autohandy.app/trip/share/AbCdEf123...",
  "deep_link": "holadrive://trip/share/AbCdEf123...",
  "public_api_url": "https://api.autohandy.app/api/v1/safety/share/AbCdEf123.../",
  "order_id": 61,
  "order_code": "HD-xxx",
  "order_status": "on_the_way",
  "expires_at": "2026-07-25T18:00:00Z",
  "is_active": true,
  "is_valid": true,
  "revoked_at": null,
  "created_at": "2026-07-25T12:00:00Z",
  "ws_url_path": "/ws/safety/share/AbCdEf123.../"
}
```

| Field | Frontend nima qiladi |
|--------|----------------------|
| `share_url` | Native share sheet (WhatsApp / SMS / Share) — **HTTPS** |
| `deep_link` | App ichida ochish (`holadrive://...`) |
| `public_api_url` | Do‘st/app JSON olish |
| `token` | Deep link routing |
| `ws_url_path` | Live location WS |

### 2.2 List my shares
`GET /api/v1/safety/share/list/`  
Auth: JWT

### 2.3 Revoke
`DELETE /api/v1/safety/share/<token>/revoke/`  
Auth: JWT

### 2.4 Public trip status (do‘st — login yo‘q)
`GET /api/v1/safety/share/<token>/`  
Auth: **yo‘q**

Response `data`:
```json
{
  "token": "...",
  "share_url": "https://api.../trip/share/...",
  "deep_link": "holadrive://trip/share/...",
  "public_api_url": "https://api.../api/v1/safety/share/.../",
  "expires_at": "...",
  "order": {
    "id": 61,
    "order_code": "HD-xxx",
    "status": "on_the_way",
    "pickup": "456 Rue ...",
    "destination": "Notre-Dame ...",
    "pickup_latitude": 45.50,
    "pickup_longitude": -73.56,
    "destination_latitude": 45.51,
    "destination_longitude": -73.55
  },
  "route": {
    "pickup": { "latitude": 45.50, "longitude": -73.56 },
    "destination": { "latitude": 45.51, "longitude": -73.55 }
  },
  "driver": {
    "id": 22,
    "full_name": "John D"
  },
  "location": {
    "latitude": "45.50",
    "longitude": "-73.56",
    "updated_at": "...",
    "eta_minutes": 8,
    "tracking_phase": "to_pickup"
  },
  "ws_url_path": "/ws/safety/share/<token>/"
}

**Flutter (deep link `holadrive://trip/share/:token`):**
1. `GET /api/v1/safety/share/<token>/` — draw route A→B from `route`
2. Put live marker from `location`
3. Connect `ws/safety/share/<token>/` — update marker on `driver_location_update`
4. Do **not** show raw lat/lng text to the user — only the map
```
Telefon / email / to‘lov ma’lumoti **yo‘q**.

### 2.5 Public live WS (login yo‘q)
```
wss://<host>/ws/safety/share/<token>/
```

Events:
```json
{ "type": "connection_established", "order_id": 61, "token": "..." }
```
```json
{
  "type": "driver_location_update",
  "order_id": 61,
  "driver_id": 22,
  "latitude": "45.50",
  "longitude": "-73.56",
  "updated_at": "...",
  "eta_minutes": 8,
  "eta_to_pickup_minutes": 8,
  "eta_to_destination_minutes": 20,
  "tracking_phase": "to_pickup"
}
```

### 2.6 Do‘st ochadigan sahifa (brauzer)
```
https://<api-host>/trip/share/<token>/
```
Alohida website emas — API serverdagi oddiy mobil HTML.

### App oqimi
1. `POST /safety/share/`
2. Share sheet ga `share_url` berish (HTTPS)
3. Do‘st linkni bosadi → `/trip/share/<token>/` landing:
   - App **bor** → `holadrive://trip/share/<token>` ochiladi
   - App **yo‘q** → iOS App Store / Android Google Play
4. Flutter app deep link handle qilishi kerak: `holadrive://trip/share/:token`

Env:
```
APP_DEEP_LINK_SCHEME=holadrive
APP_SHARE_HTTPS_BASE=https://api.autohandy.app
IOS_APP_STORE_URL=https://apps.apple.com/app/idXXXXXXXX
ANDROID_PLAY_STORE_URL=https://play.google.com/store/apps/details?id=com.your.app
```

---

## 3. Contact safety agent (chat)

Support chatga o‘xshash, lekin **alohida** safety room.

### 3.1 Open / reuse room
`POST /api/v1/safety/rooms/open/`  
Auth: JWT

Body:
```json
{ "order_id": 61 }
```
`order_id` **ixtiyoriy** (bo‘sh `{}` ham bo‘ladi).

Response `data`: room (`id`, `user_id`, `agent_id`, `order_ids`, `messages`, …)

### 3.2 List rooms
`GET /api/v1/safety/rooms/`  
Auth: JWT  
User: o‘z roomlari. Admin/staff: hammasi.

### 3.3 Room detail
`GET /api/v1/safety/rooms/<room_id>/`  
Auth: JWT

### 3.4 Messages list
`GET /api/v1/safety/rooms/<room_id>/messages/?page=1&page_size=50`  
Auth: JWT

Response `data`:
```json
{
  "count": 12,
  "page": 1,
  "page_size": 50,
  "results": [
    {
      "id": 1,
      "room_id": 3,
      "sender_id": 11,
      "sender_name": "Rider",
      "message_type": "user",
      "message": "I need help",
      "order_id": 61,
      "created_at": "..."
    }
  ]
}
```

`message_type`: `user` | `agent` | `system`

### 3.5 Send message (HTTP)
`POST /api/v1/safety/rooms/<room_id>/messages/`  
Auth: JWT

Body:
```json
{
  "message": "Please help me",
  "order_id": 61
}
```
`order_id` ixtiyoriy.

### 3.6 Safety chat WebSocket
```
wss://<host>/ws/safety/<room_id>/?token=<ACCESS_JWT>
```

Connect:
```json
{ "type": "connection_established", "room_id": 3 }
```

Client → server:
```json
{ "type": "chat_message", "message": "Hello", "order_id": 61 }
```

Server → client:
```json
{
  "type": "chat_message",
  "message": {
    "id": 10,
    "room_id": 3,
    "sender_id": 11,
    "sender_name": "...",
    "message_type": "user",
    "message": "Hello",
    "order_id": 61,
    "created_at": "..."
  }
}
```

### App oqimi
1. `POST /safety/rooms/open/` (+ optional `order_id`)
2. WS ulash `ws/safety/<room_id>/?token=...`
3. Xabar: WS yoki HTTP POST messages

---

## 4. Voice recording

Client mikrofonni **o‘zi** yozadi, keyin faylni upload qiladi.

### 4.1 Start
`POST /api/v1/safety/recordings/start/`  
Auth: JWT

Body:
```json
{ "order_id": 61 }
```

Response `data`:
```json
{
  "id": 5,
  "order_id": 61,
  "user_id": 11,
  "status": "recording",
  "audio_url": null,
  "started_at": "...",
  "ended_at": null,
  "duration_seconds": null,
  "created_at": "..."
}
```

### 4.2 Stop + upload
`POST /api/v1/safety/recordings/<recording_id>/stop/`  
Auth: JWT  
Content-Type: `multipart/form-data`

Fields:
- `audio` (yoki `file`) — audio fayl
- `duration_seconds` — ixtiyoriy number

Response `data`: `status: "uploaded"`, `audio_url`, `ended_at`, `duration_seconds`

### 4.3 List
`GET /api/v1/safety/recordings/?order_id=61`  
Auth: JWT

### 4.4 Detail
`GET /api/v1/safety/recordings/<recording_id>/`  
Auth: JWT

### App oqimi
1. Start → `recording.id` saqlash  
2. Local mic record  
3. Stop → multipart upload `audio` + `duration_seconds`

---

## 5. WebSocket summary

| Maqsad | URL | Auth |
|--------|-----|------|
| Safety chat | `wss://host/ws/safety/<room_id>/?token=JWT` | JWT |
| Share live map | `wss://host/ws/safety/share/<token>/` | yo‘q |

---

## 6. Safety sheet UI → API

| UI tugma | API / action |
|----------|----------------|
| Contact 911 | `GET /tools/` → `tel:` |
| Contact safety agent | `POST /rooms/open/` + WS |
| Voice recording | start → local record → stop upload |
| Share trip status | `POST /share/` → native share `share_url` |

---

## 7. Tipik xato kodlari

| code | Ma’nosi |
|------|---------|
| `not_found` | Order / room / link / recording yo‘q |
| `forbidden` | Ruxsat yo‘q |
| `invalid_order_status` | Trip active emas |
| `share_inactive` | Link expire / revoke |
| `trip_ended` | Trip tugagan |
| `no_agent` | Safety agent (admin) yo‘q |
| `invalid_status` | Recording allaqachon stop |

---

## 8. Checklist (frontend)

- [ ] Safety sheet ochilganda `GET /safety/tools/`
- [ ] Share: create → share sheet (`share_url`)
- [ ] Deep link handle: `holadrive://trip/share/:token`
- [ ] Safety agent: open room → WS chat
- [ ] Voice: start / stop+upload
- [ ] 911: `tel:911`
