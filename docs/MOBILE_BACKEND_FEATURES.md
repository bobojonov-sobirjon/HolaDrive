# HolaDrive — Backend o‘zgarishlar hujjati

**Production base URL:** `https://apiss.firepole.ru`  
**API prefix:** `/api/v1/`  
**Auth:** `Authorization: Bearer <JWT_ACCESS_TOKEN>`  
**WebSocket auth:** `?token=<JWT_ACCESS_TOKEN>` (Bearer prefiksi shart emas)

---

## 1. Support chat (Rider / Driver ↔ Admin)

Support chat — rider yoki driver admin bilan yozishmalar uchun. Order chat (`ChatRoom`) dan **alohida** tizim.

### Modellar

| Model | Ma’nosi |
|-------|---------|
| `SupportRoom` | Bitta user (rider/driver) + bitta admin. `(user, admin)` juftligi unique — qayta ochganda **xuddi shu room** qayta ishlatiladi. |
| `SupportMessage` | Xabarlar. `message_type`: `user` \| `admin` \| `system` |
| `SupportRoom.orders` | M2M — bir nechta buyurtma bilan bog‘lanishi mumkin |

Admin tanlash: Django `Admin` guruhi ichidan tasodifiy staff/superuser (`get_support_admin_random()`). Guruh bo‘sh bo‘lsa — `admin@admin.com` fallback.

**Migration:** `python manage.py migrate chat` (`0004_support_rooms`)

---

### REST API

Barcha endpointlar: `/api/v1/chat/support/...`

#### 1.1 Room ochish (yoki mavjudini qayta ishlatish)

```
POST /api/v1/chat/support/rooms/open/
```

**Body (ixtiyoriy):**
```json
{
  "order_id": 123
}
```

**Javob:**
```json
{
  "message": "OK",
  "status": "success",
  "data": {
    "id": 5,
    "user": { "...": "..." },
    "admin": { "...": "..." },
    "order_ids": [123],
    "messages": null,
    "created_at": "...",
    "updated_at": "..."
  }
}
```

**Mantiq:**
- Birinchi marta — yangi `SupportRoom` yaratiladi, admin biriktiriladi.
- Keyingi safar — **shu user + admin** uchun mavjud room qaytariladi.
- `order_id` berilsa va roomda yo‘q bo‘lsa — order M2M ga qo‘shiladi + system xabar: `"Chat opened for order #X"` yoki `"Chat context switched to order #X"`.

---

#### 1.2 Roomlar ro‘yxati

```
GET /api/v1/chat/support/rooms/
```

| Kim | Ko‘radi |
|-----|---------|
| Admin (staff/superuser) | Barcha roomlar. `?user_id=7` bilan filter. |
| Rider/Driver | Faqat o‘z roomlari |

---

#### 1.3 Room ID bo‘yicha (xabarlar bilan)

```
GET /api/v1/chat/support/rooms/<room_id>/
```

**Javobda `messages[]` inline** keladi (oxirgi 500 ta, `created_at` bo‘yicha).

Har bir xabarda:
- `sender_type`: `initiator` (joriy user yuborgan) \| `receiver` \| `system`
- `message_type`: `user` \| `admin` \| `system`
- `order` — ixtiyoriy buyurtma ID

---

#### 1.4 Xabarlar (pagination)

```
GET /api/v1/chat/support/rooms/<room_id>/messages/?page=1&page_size=50
```

---

#### 1.5 Xabar yuborish (REST)

```
POST /api/v1/chat/support/rooms/<room_id>/messages/
```

**Body:**
```json
{
  "message": "Salom, yordam kerak",
  "order_id": 123
}
```

**Huquq:**
- User — faqat o‘z roomida yozadi.
- Admin — faqat **shu roomga biriktirilgan admin** javob beradi (`room.admin_id`).

Xabar yuborilganda qarshi tomonga **push notification** + `ws/notifications/` event yuboriladi.

---

### WebSocket (real-time)

```
wss://apiss.firepole.ru/ws/support/<room_id>/?token=<JWT>
```

**Ulanishdan keyin:**
```json
{
  "type": "connection_established",
  "message": "Connected to support chat",
  "room_id": 5
}
```

**Xabar yuborish:**
```json
{
  "type": "chat_message",
  "message": "Salom",
  "order_id": 123
}
```

**Qabul qilish:**
```json
{
  "type": "chat_message",
  "message_id": 42,
  "message_type": "user",
  "message": "Salom",
  "order_id": 123,
  "sender_id": 7,
  "sender_name": "Shahob",
  "sender_type": "user",
  "created_at": "2026-06-17T12:00:00+00:00"
}
```

**Kirish huquqi:** `room.user_id == token.user` **yoki** admin bo‘lib `room.admin_id == token.user`.

> **Eslatma:** Support chatda rasm yuborish hozircha **implement qilinmagan** (faqat matn). Keyinroq qo‘shiladi.

---

### Mobile integratsiya oqimi (support)

```
1. POST /api/v1/chat/support/rooms/open/  (+ ixtiyoriy order_id)
2. room.id ni saqlash
3. WS: wss://.../ws/support/{room_id}/?token=...
4. GET /api/v1/chat/support/rooms/{room_id}/  — tarixni olish
5. Xabar: WS yoki POST .../messages/
6. Bildirishnomalar: ws/notifications/ yoki GET /api/v1/notification/
```

---

## 2. Price estimate — latitude xatosi tuzatildi

### Muammo

```
POST /api/v1/order/price-estimate/
```

Mobil GPS koordinatalari ko‘pincha 14 dan ko‘p kasr xonali keladi (masalan Google Maps `39.8009868123456789`). Eski limit:

```json
{
  "message": "Validation error",
  "status": "error",
  "errors": {
    "latitude_to": ["Ensure that there are no more than 14 decimal places."]
  }
}
```

### Yechim

`decimal_places` **14 → 18** ga oshirildi:

| Fayl | O‘zgarish |
|------|-----------|
| `apps/order/serializers/order.py` | `PriceEstimateSerializer` — `latitude_from/to`, `longitude_from/to`: `max_digits=24`, `decimal_places=18` |
| `apps/order/models.py` | `OrderItem` va `SurgePricing` lat/lon maydonlari |
| `apps/order/migrations/0025_latlon_precision_18.py` | DB migration |

**Serverda ishga tushirish:**
```bash
python manage.py migrate order
```

### API ishlatish

```
POST /api/v1/order/price-estimate/
Authorization: Bearer <token>
```

**Body:**
```json
{
  "latitude_from": 41.311081,
  "longitude_from": 69.240562,
  "latitude_to": 41.299496,
  "longitude_to": 69.240074
}
```

**Javob:** har bir aktiv `ride_type` uchun `estimates[]` — `id` = `ride_type_id`, `price`, `distance_km`, `surge_multiplier` va hokazo.

Narxni min/max oralig‘ida tekshirish:
```
POST /api/v1/order/price-estimate/manage-price/
```
(xuddi shu koordinatalar + `ride_type_id` + `adjusted_price`)

---

## 3. Trip Complete — Stripe `No such destination` xatosi

### Muammo (rasmdagi xato)

Driver **Complete Ride** bosganda:

```
No such destination: 'acct_1TeJQ73Ef6svs8so'
```

**Sabab:** Haydovchining `stripe_connect_account_id` bazada saqlangan, lekin Stripe da bu Connect account **o‘chirilgan**, test/live mode mos kelmaydi yoki account noto‘g‘ri. PaymentIntent `transfer_data.destination` ga yuborilganda Stripe rad etadi.

### Yechim

`apps/payment/services/trip_charge.py` — `_resolve_connect_destination()`:

1. Driver `stripe_connect_account_id` ni oladi (`acct_...` formatida).
2. Stripe `Account.retrieve()` bilan tekshiradi.
3. Account yo‘q yoki o‘chirilgan bo‘lsa:
   - User yozuvidan `stripe_connect_account_id` **tozalanadi**
   - `destination=None` — to‘lov **platforma** orqali olinadi (trip complete bloklanmaydi).
4. Account mavjud bo‘lsa — destination charge + `application_fee_amount` (sozlamaga qarab).

**API:**
```
POST /api/v1/order/driver/complete/
```

**Body:**
```json
{
  "order_id": 456
}
```

Card to‘lovda `charge_trip_card_payment()` chaqiriladi. Stripe xatosi bo‘lsa `400` + `message` qaytadi; order `stripe_trip_payment_error` ga yoziladi.

### Driver tomonda tavsiya

Agar xato takrorlansa:
1. Driver **bank/Connect setup** ni qayta tugatishi kerak (`complete-setup` flow).
2. Test/live Stripe kalitlari bir xil mode da bo‘lishi kerak.
3. Admin paneldan driver `stripe_connect_account_id` ni tekshirish.

---

## 4. Driver ↔ Rider chat (order chat)

Order bo‘yicha rider va driver o‘rtasidagi chat. Support chatdan **farqli**.

### REST API

```
GET /api/v1/chat/rooms/?order_id=<order_id>     — order bo‘yicha room
GET /api/v1/chat/rooms/rider/                   — rider roomlari
GET /api/v1/chat/rooms/driver/                  — driver roomlari
GET /api/v1/chat/rooms/<room_id>/messages/      — xabarlar tarixi
```

Room order yaratilganda avtomatik ochiladi (alohida POST yo‘q).

### WebSocket (matn xabarlar — ishlaydi)

```
wss://apiss.firepole.ru/ws/order/<order_id>/chat/?token=<JWT>
```

**Ulanish:**
```json
{
  "type": "connection_established",
  "message": "Connected to order chat",
  "order_id": 456,
  "user_type": "rider"
}
```

**Xabar yuborish:**
```json
{
  "type": "chat_message",
  "message": "Men yetib keldim"
}
```

**Qabul qilish:**
```json
{
  "type": "chat_message",
  "message_id": 88,
  "message": "Men yetib keldim",
  "sender_id": 7,
  "sender_name": "Shahob",
  "sender_type": "rider",
  "created_at": "...",
  "attachment_url": null,
  "file_type": null,
  "file_name": null
}
```

`sender_type`: `rider` | `driver`

**Alternativ WS** (room_id bo‘yicha):
```
wss://apiss.firepole.ru/ws/chat/<room_id>/?token=<JWT>
```

---

### Rasm yuborish — hozirgi holat va reja

> **Muhim:** Mobil UI da paperclip (rasm) tugmasi bor, lekin backend da **to‘liq rasm yuborish hali tugallanmagan**. `ChatMessage` modelida `attachment` maydoni yo‘q; WS javobida `attachment_url` maydoni bor, lekin hozircha doim `null`.

Tayyor infratuzilma:
- `apps/chat/utils.py` → `save_base64_file()` — base64 rasmni `chat/attachments/image/` ga saqlaydi
- `get_file_type_from_mime()` / `get_file_type_from_extension()` — fayl turini aniqlash

#### Rejalashtirilgan implementatsiya (keyingi qadam)

**1. Model kengaytirish** (`ChatMessage`):
```python
attachment = models.FileField(upload_to='chat/attachments/', null=True, blank=True)
file_type = models.CharField(max_length=20, null=True, blank=True)  # image | file | audio
file_name = models.CharField(max_length=255, null=True, blank=True)
```

**2. WebSocket payload (rasm bilan):**
```json
{
  "type": "chat_message",
  "message": "",
  "file_base64": "data:image/jpeg;base64,/9j/4AAQ...",
  "file_name": "photo.jpg",
  "file_type": "image"
}
```

**3. `OrderChatConsumer.receive()` da:**
- `file_base64` bo‘lsa → `save_base64_file()` → DB ga `attachment` saqlash
- `attachment_url` = `PUBLIC_BASE_URL + media path` (yoki `request.build_absolute_uri`)

**4. REST tarix** (`GET .../rooms/<id>/messages/`):
- Serializer ga `attachment_url`, `file_type`, `file_name` qo‘shish

**5. Mobil tomonda:**
- Rasm tanlash → base64 encode → WS orqali yuborish
- Yoki `multipart/form-data` REST endpoint (keyinroq qo‘shish mumkin)

**Vaqtinchalik workaround (mobil):** Rasmni avval media upload API ga yuborib, matn xabarda URL yuborish — lekin bu rasm preview UX uchun yomon; to‘g‘ri yechim — yuqoridagi WS + attachment flow.

---

## Deploy checklist

Har bir o‘zgarishdan keyin production serverda:

```bash
git pull
python manage.py migrate
# Daphne / gunicorn restart
daphne -b 0.0.0.0 -p 8001 config.asgi:application
```

| O‘zgarish | Migration |
|-----------|-----------|
| Support chat | `migrate chat` |
| Lat/lon precision | `migrate order` |
| Stripe complete fix | Kod yangilanishi yetarli |
| Driver-rider rasm | Hali migration kerak (keyingi release) |

---

## Tezkor endpoint jadvali

| Vazifa | Method | URL |
|--------|--------|-----|
| Support room ochish | POST | `/api/v1/chat/support/rooms/open/` |
| Support room + messages | GET | `/api/v1/chat/support/rooms/<id>/` |
| Support xabar (REST) | POST | `/api/v1/chat/support/rooms/<id>/messages/` |
| Support WS | WS | `/ws/support/<room_id>/?token=` |
| Narx reja | POST | `/api/v1/order/price-estimate/` |
| Trip tugatish | POST | `/api/v1/order/driver/complete/` |
| Order chat tarix | GET | `/api/v1/chat/rooms/<room_id>/messages/` |
| Order chat WS | WS | `/ws/order/<order_id>/chat/?token=` |
| Bildirishnomalar | GET | `/api/v1/notification/` |
