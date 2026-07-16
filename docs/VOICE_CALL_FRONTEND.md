# HolaDrive — Real-time Voice Call (Frontend guide)

Backend audio uchun **Agora RTC**, signaling (qo‘ng‘iroq keldi / qabul / tugadi) uchun **WebSocket**, barcha actionlar uchun **REST API** ishlatiladi.

> Muhim: WebSocket faqat **server → client** event beradi. Accept / reject / cancel / end — **faqat REST**.

---

## 1. Umumiy arxitektura

```
┌─────────────┐     REST initiate      ┌─────────────┐
│  Caller app │ ─────────────────────► │   Backend   │
│ (Rider/Drv) │ ◄──── agora token ──── │  + Agora    │
└──────┬──────┘                        └──────┬──────┘
       │                                      │
       │ Agora join (audio)                   │ WS event: incoming_call
       │                                      ▼
       │                               ┌─────────────┐
       └──────── same channel ────────►│ Callee app  │
                                       │ (Drv/Admin) │
                                       └─────────────┘
```

1. Har ikkala tomon avval **JWT** oladi (login).
2. Har ikkala tomon **Voice Call WS** ga ulanadi.
3. Caller **REST** orqali call boshlaydi → response da o‘zining **Agora** credentials.
4. Callee **WS** da `incoming_call` (yoki support da `incoming_support_call`) oladi.
5. Callee **REST accept** → o‘zining Agora credentials.
6. Ikkalasi Agora channel ga **join + mic publish**.
7. Tugash: **end / reject / cancel** REST.

---

## 2. Auth

Barcha REST:

```http
Authorization: Bearer <ACCESS_JWT>
Content-Type: application/json
```

Base URL misol:

- Local: `http://127.0.0.1:8001`
- Prod: `https://api....`

---

## 3. WebSocket (signaling)

### Connect

```
ws://<host>/ws/voice-call/?token=<ACCESS_JWT>
```

HTTPS da: `wss://...`

Anon / yaroqsiz token → close code **4401**.

### Connect muvaffaqiyat

```json
{
  "type": "connection_established",
  "message": "Connected to voice call signaling",
  "user_id": 11
}
```

### Server → client eventlar

Barcha eventlar shu formatda:

```json
{
  "type": "<event_name>",
  "payload": { ... }
}
```

| `type` | Kimga | Qachon |
|--------|--------|--------|
| `incoming_call` | Callee (driver/rider yoki on-duty admin) | Yangi call |
| `incoming_support_call` | Admin (support duty group) | Support call |
| `call_accepted` | Caller (+ callee) | Accept qilindi |
| `call_rejected` | Caller | Reject |
| `call_cancelled` | Callee | Caller cancel |
| `call_ended` | Ikkalasi | End / missed |

### Tipik `payload` maydonlari

```json
{
  "call_id": 42,
  "call_type": "trip",
  "status": "ringing",
  "order_id": 61,
  "support_room_id": null,
  "channel_name": "trip_61_abc123def0",
  "app_id": "<AGORA_APP_ID>",
  "initiator_role": "rider",
  "ring_started_at": "...",
  "answered_at": null,
  "caller": { "id": 11, "full_name": "...", "email": "..." },
  "callee": { "id": 22, "full_name": "...", "email": "..." },
  "agora": {
    "app_id": "...",
    "channel_name": "...",
    "token": "...",
    "uid": 11,
    "expires_at": 1710000000
  }
}
```

> `agora` har doim bo‘lmasligi mumkin. Asosan **REST** response dagi `data.agora` ni join uchun ishlating. Kerak bo‘lsa `GET /voice-call/<id>/` yangi token beradi (`ringing` / `answered`).

### Frontend qoidalar

- App foreground da WS ochiq tuting (reconnect + JWT refresh).
- Incoming kelganda UI (incoming screen) oching, `call_id` saqlang.
- WS orqali accept yubormang — faqat REST.
- Push / `ws/notifications/` ham kelishi mumkin (`related_object_type: voice_call`) — background uchun.

---

## 4. Call turlari (`call_type`)

| Qiymat | Ma’nosi |
|--------|---------|
| `trip` | Rider ↔ Driver (order bo‘yicha) |
| `rider_support` | Rider → Support/Admin |
| `driver_support` | Driver → Support/Admin |

### Statuslar (`status`)

```
ringing ──accept──► answered ──end──► ended
   │
   ├─reject──► rejected
   ├─cancel──► cancelled   (faqat caller, hali ringing)
   └─end─────► missed      (ringing holatda end)
```

---

## 5. Agora (ovoz)

REST muvaffaqiyatli initiate/accept/detail dan keyin:

```json
"agora": {
  "app_id": "…",
  "channel_name": "…",
  "token": "…",
  "uid": 11,
  "expires_at": 1710000000
}
```

Frontend (Agora Web / Flutter / native SDK):

1. `createClient` / engine init (`app_id`)
2. `join(channel_name, token, uid)` — **uid** backend bergan user id
3. Local mic track create + **publish**
4. Remote user `user-published` → subscribe + play audio
5. Call tugaganda: unpublish + leave + release mic

**Ikkalasi bir xil `channel_name` ga join qilishi shart.**

---

## 6. REST API — birma-bir

Prefix: `/api/v1/voice-call/`

Umumiy success:

```json
{
  "message": "...",
  "status": "success",
  "data": { ... }
}
```

Xato:

```json
{
  "message": "...",
  "status": "error",
  "code": "invalid_order_status",
  "errors": {}
}
```

---

### 6.1 Trip call — rider ↔ driver

#### `POST /api/v1/voice-call/trip/initiate/`

**Kim:** orderdagi rider yoki **accepted** driver.

**Body:**

```json
{ "order_id": 61 }
```

**Shartlar:**

- Order status: `accepted` | `on_the_way` | `arrived` | `in_progress`
- Driver accept qilgan bo‘lishi kerak (`pending` da **ishlamaydi**)
- Userda boshqa active call bo‘lmasligi kerak

**Response:** `201` — session + caller `agora`.

Callee WS: `incoming_call`.

---

### 6.2 Support call — order bilan (ixtiyoriy)

#### `POST /api/v1/voice-call/support/initiate/`

**Kim:** Rider yoki Driver group.

**Body (order bilan):**

```json
{ "order_id": 61 }
```

**Body (order-siz ham mumkin):**

```json
{}
```

yoki `order_id: null`.

**Response:** `201` — session + caller `agora`. Support da `callee` dastlab `null` (admin accept qilguncha).

Adminlar: `incoming_support_call` + `incoming_call` (on-duty).

---

### 6.3 Support call — order-siz (alohida endpoint)

#### `POST /api/v1/voice-call/support/direct/`

**Kim:** Rider yoki Driver.

**Body:** bo‘sh

```json
{}
```

Order context yo‘q. Accept/reject/end oqimi support/initiate bilan bir xil.

---

### 6.4 Accept

#### `POST /api/v1/voice-call/<call_id>/accept/`

**Kim:**

- Trip: faqat **callee** (caller emas)
- Support: faqat **admin/staff/superuser**

**Body:** yo‘q.

**Response:** `200` — session (`answered`) + **accepter** uchun `agora`.

Caller WS: `call_accepted`.

---

### 6.5 Reject

#### `POST /api/v1/voice-call/<call_id>/reject/`

**Body (ixtiyoriy):**

```json
{ "reason": "Busy" }
```

Faqat `ringing`. Support da admin; trip da callee.

---

### 6.6 Cancel

#### `POST /api/v1/voice-call/<call_id>/cancel/`

**Kim:** faqat **caller**, faqat `ringing`.

```json
{ "reason": "Changed mind" }
```

Callee WS: `call_cancelled`.

---

### 6.7 End

#### `POST /api/v1/voice-call/<call_id>/end/`

**Kim:** caller yoki callee.

```json
{ "reason": "Done" }
```

| Holat | Natija |
|-------|--------|
| `ringing` | `missed` |
| `answered` | `ended` + `duration_seconds` |

WS: `call_ended`.

---

### 6.8 Detail (token yangilash)

#### `GET /api/v1/voice-call/<call_id>/`

Participant yoki admin.  
Status `ringing` / `answered` bo‘lsa response da yangi `agora` bo‘lishi mumkin.

---

### 6.9 History

#### `GET /api/v1/voice-call/history/?call_type=trip&page=1&page_size=20`

Query:

- `call_type` — ixtiyoriy: `trip` | `rider_support` | `driver_support`
- `page`, `page_size`

List da odatda to‘liq `agora` / recording yo‘q.

---

### 6.10 Support duty (admin)

#### `GET /api/v1/voice-call/support-duty/`

O‘z holati: `{ "is_on_duty": true/false, ... }`

#### `POST /api/v1/voice-call/support-duty/`

**Kim:** staff / superuser.

```json
{ "is_on_duty": true }
```

Support ring olish uchun admin **on duty** + **WS ulangan** bo‘lishi kerak.

---

## 7. Admin panel REST (superuser)

Prefix: `/api/v1/admin-panel/voice-calls/`

| Method | Path | Maqsad |
|--------|------|--------|
| GET | `/` | List (`?status=ringing`) |
| GET | `/<call_id>/` | Detail |
| POST | `/<call_id>/accept/` | Accept |
| POST | `/<call_id>/reject/` | Reject |
| POST | `/<call_id>/end/` | End |
| PATCH | `/<call_id>/note/` | `{ "operator_note": "..." }` |

Mobile accept bilan bir xil ma’noda; admin UI shu pathlarni ishlatadi.

---

## 8. Frontend oqimlari (checklist)

### A) Trip call (Rider → Driver)

1. Rider + Driver: login → JWT  
2. Ikkalasi: `ws/voice-call/?token=...`  
3. Order status accept+  
4. Rider: `POST .../trip/initiate/` `{ order_id }` → Agora join  
5. Driver: WS `incoming_call` → UI  
6. Driver: `POST .../<call_id>/accept/` → Agora join  
7. Audio  
8. Kimdir: `POST .../end/` → leave Agora  

### B) Support + order

1. Admin: duty `true` + WS  
2. Rider/Driver: WS  
3. `POST .../support/initiate/` `{ order_id }`  
4. Admin: `incoming_support_call` → accept → Agora  
5. End  

### C) Support order-siz

1. Admin: duty + WS  
2. User: WS  
3. `POST .../support/direct/` `{}`  
4. Admin accept → Agora → end  

---

## 9. UI holat mashinasi (tavsiya)

```
idle
  → connecting_ws
  → ready
  → outgoing_ringing     (initiate OK, agora joined, kutish)
  → incoming_ringing     (WS incoming_*, hali accept yo‘q)
  → in_call              (answered + remote audio)
  → ended / rejected / cancelled / missed / error
```

Har bir terminal statusda: Agora leave + mic release.

---

## 10. Tipik xato kodlari

| `code` | Sabab |
|--------|--------|
| `invalid_order_status` | Trip: order hali `pending` yoki tugagan |
| `no_driver` | Accepted driver yo‘q |
| `forbidden` | Bu order/call ishtirokchisi emas |
| `active_call_exists` | Userda allaqachon ringing/answered |
| `order_call_active` | Shu orderda active call bor |
| `agora_not_configured` | Serverda Agora env yo‘q |
| `not_found` | Call/order topilmadi |
| `invalid_status` | Masalan ringing emas, lekin accept |

---

## 11. Local test

- Daphne + Redis  
- Tester (same-origin): `http://127.0.0.1:8001/voice-call-test/`  
  - `file://` dan ochmang (CORS / Failed to fetch)  
- Swagger: `/swagger/` — tag **Voice calls**

---

## 12. Qisqa xulosa frontend uchun

| Vazifa | Qayerda |
|--------|---------|
| Call boshlash | REST initiate / direct |
| Ring UI | WS `incoming_*` |
| Qabul / rad / bekor / tugatish | REST accept / reject / cancel / end |
| Ovoz | Agora (`data.agora`) |
| Admin ring olish | `support-duty` + WS |

**Trip** = order + accepted driver.  
**Support + order** = `support/initiate` + optional `order_id`.  
**Support order-siz** = `support/direct`.
