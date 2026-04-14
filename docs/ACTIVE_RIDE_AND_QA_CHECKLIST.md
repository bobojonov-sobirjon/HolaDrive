# Active ride API va tekshirish ro‘yxati (QA)

Bu hujjat: (1) yangi **active ride** endpointlari qanday ishlatiladi, (2) avvalgi sessiyada qilingan boshqa ishlarni ketma-ket tekshirish uchun qisqa ro‘yxat.

---

## 1. Yangi: Rider — aktiv safar (`GET`)

**Maqsod:** Klient ilovadan chiqib qayta kirganda hozir davom etayotgan buyurtma bormi-yo‘qligini bilish; `status` bo‘yicha to‘g‘ri ekranga o‘tish.

| Maydon | Qiymat |
|--------|--------|
| **Method** | `GET` |
| **URL** | `{BASE}/api/v1/order/rider/active-ride/` |
| **Auth** | `Authorization: Bearer <access_token>` (rider hisobi) |

**Javob (aktiv safar yo‘q):**

```json
{
  "message": "No active ride",
  "status": "success",
  "has_active_ride": false,
  "data": null
}
```

**Javob (aktiv safar bor):** `has_active_ride: true`, `data` — `OrderDetailSerializer` bilan **xuddi** `GET /api/v1/order/{order_id}/` dagi kabi: `order_items`, `user`, qabul qilingan bo‘lsa `driver`, `order_driver`, va hokazo.

**Qaysi order statuslari “aktiv” hisoblanadi:** `pending`, `accepted`, `on_the_way`, `arrived`, `in_progress`.  
**Aktiv emas:** `completed`, `cancelled`, `rejected`.

**Bir nechta mos keladigan buyurtma bo‘lsa:** eng oxirgi `updated_at` bo‘yicha bittasi qaytariladi (chetdagi holat).

**Front ketma-ketligi (tavsiya):** cold start → shu `GET` → agar `has_active_ride` bo‘lsa `data.id` va `data.status` bilan ekran + `wss://.../ws/rider/orders/?token=...` ga ulanish.

### 1.1 Real-time yangilanish (WS, connectdan keyin bir marta)

`active-ride` holati socketga ulangandan keyin bir marta yuboriladi:

1. Driver/rider `ws/.../orders/` ga ulanadi
2. Backend `apps.order.tasks.send_active_ride_snapshot_once` taskini `countdown=3` bilan ishga tushiradi
3. Taxminan 3 sekund ichida `active_ride_snapshot` event keladi

```json
{
  "type": "active_ride_snapshot",
  "scope": "rider",
  "has_active_ride": true,
  "order": { "...": "OrderDetailSerializer payload" },
  "checked_at": "2026-04-14T03:00:00Z",
  "message": "Active ride status refreshed"
}
```

Driver uchun `scope = "driver"` bo'ladi.

Qaysi groupga yuboriladi:
- Rider: `rider_orders_{user_id}`
- Driver: `driver_orders_{user_id}`

Front ishlatishi:
- `ws/rider/orders/` yoki `ws/driver/orders/` ga ulangandan keyin `active_ride_snapshot` eventni tinglash.
- Event bir martalik keladi (har 3 sekundda takrorlanmaydi).
- `has_active_ride=true` bo'lsa order ekranini davom ettirish.
- `has_active_ride=false` bo'lsa bo'sh/home holatga qaytish.

---

## 2. Yangi: Driver — aktiv safar (`GET`)

**Maqsod:** Haydovchi qabul qilgan safarni ilova qayta ochilganda davom ettirish.

| Maydon | Qiymat |
|--------|--------|
| **Method** | `GET` |
| **URL** | `{BASE}/api/v1/order/driver/active-ride/` |
| **Auth** | `Authorization: Bearer <access_token>` (driver hisobi) |

**Mantiq:** faqat `OrderDriver.status == accepted` **va** buyurtma statusi yuqoridagi aktiv ro‘yxatda bo‘lsa qaytariladi.  
**Eslatma:** faqat **requested** (taklif) bo‘lgan buyurtmalar bu yerda **yo‘q** — ular uchun `driver/nearby-orders/` va `ws/driver/orders/`.

Javob shakli rider bilan bir xil: `has_active_ride` + `data` (`OrderDetailSerializer` yoki `null`).

**Front ketma-ketligi:** cold start → `GET .../driver/active-ride/` → keyin `wss://.../ws/driver/orders/?token=...`.

### 2.1 Driver: real-time (shu socketda nima bo‘ladi)

Haydovchi **bitta** asosiy kanal — `wss://.../ws/driver/orders/?token=...` — orqali:

- **Takliflar:** `new_order`, `initial_orders`, vaqt tugaganda `order_timeout`.
- **Aktiv safar sinxroni:** ulanishdan ~3 s keyin bir marta `active_ride_snapshot` (yuqoridagi 1.1).
- **Rider bekor qilganda:** agar sizning `OrderDriver` holatingiz `requested` yoki `accepted` bo‘lsa, server **`order_cancelled_by_rider`** yuboradi — to‘liq `order` + `cancel` metama’lumotlari bilan.

Bu alohida “tracking” socket emas: yo‘lovchi haydovchini xaritada ko‘rishi uchun `ws/order/{order_id}/tracking/` rider tomonda ishlatiladi. Driver uchun rider bekorini bilish — **`ws/driver/orders/`** ichidagi `order_cancelled_by_rider`.

To‘liq xabar shakllari va JS misoli: **`docs/driver_orders_websocket.md`**.

---

## 3. Kodda qayerda

| Qism | Fayl |
|------|------|
| Statuslar ro‘yxati va query | `apps/order/services/active_ride.py` |
| Viewlar | `apps/order/views.py` — `RiderActiveRideView`, `DriverActiveRideView` |
| URLlar | `apps/order/urls.py` |

---

## 4. Swagger / OpenAPI

`GET /api/v1/order/rider/active-ride/` — Swagger tag **Rider: Active ride**.  
`GET /api/v1/order/driver/active-ride/` — Swagger tag **Driver: Orders & trips**.  
Tokenni Swagger UI da saqlash uchun `persistAuthorization` sozlangan bo‘lsa, bir marta kiritib qo‘yish kifoya.

---

## 5. Avvalgi ishlar — tekshirish uchun qisqa ro‘yxat

Quyidagilar boshqa sessiyada/amalda qilingan; kerak bo‘lsa alohida sinab chiqing:

1. **Order statuslar hayoti** — `pending`, `accepted`, `on_the_way`, `arrived`, `in_progress`, `completed`, `cancelled`, `rejected`; migratsiya bilan eski qiymatlar yangilangan bo‘lishi kerak.
2. **Rider bekor → driver WebSocket** — rider cancel qilganda driver `ws/driver/orders/` orqali `type: order_cancelled_by_rider`, `order` + `cancel` obyektlari (batafsil: `docs/driver_orders_websocket.md`).
3. **Driver WebSocket URL** — `ws(s)://HOST/ws/driver/orders/?token=<JWT>` (yoki path orqali token — `config/middleware/tokenauth_middleware.py`).
4. **Rider WebSocket** — `ws(s)://HOST/ws/rider/orders/?token=<JWT>`.
5. **Narx / estimate** — `price-estimate` javobida `id` (ride type), `manage-price`, `POST order/create/` da ixtiyoriy `adjusted_price` (Swagger tavsiflari).
6. **Swagger** — `persistAuthorization` yoqilgan (`config/settings.py`).

---

## 6. Minimal QA stsenariylari (active ride)

| # | Kim | Qadam | Kutilgan natija |
|---|-----|--------|-----------------|
| A | Rider | Buyurtma yaratish (`pending`) → `GET rider/active-ride/` | `has_active_ride: true`, `data.status` = `pending` |
| B | Rider | Haydovchi qabul qilgach → `GET rider/active-ride/` | `accepted` (yoki keyingi statuslar) |
| C | Rider | Safar `completed` yoki `cancelled` → `GET rider/active-ride/` | `has_active_ride: false` |
| D | Driver | Taklifni ko‘rish (requested) → `GET driver/active-ride/` | `has_active_ride: false` |
| E | Driver | Accept qilgach → `GET driver/active-ride/` | `has_active_ride: true`, `data` to‘liq |
| F | Driver | Complete/cancel qilgach → `GET driver/active-ride/` | `has_active_ride: false` |

`{BASE}` odatda lokal: `http://127.0.0.1:8000`, production domeningiz bilan almashtiring.

---

## 7. Driver location WebSocket (endi qo'shildi)

Driver lokatsiyasini real-time kuzatish uchun tracking WebSocket qo'shildi.

### 7.1 WS URL

- `ws(s)://{HOST}/ws/order/{order_id}/tracking/?token=<ACCESS_JWT>`

### 7.2 Kim ulana oladi

1. Shu order egasi bo'lgan rider
2. Shu orderni `accepted` qilgan driver

Boshqa userlar 4403 bilan rad etiladi.

### 7.3 Event formati

Ulanganda:

```json
{
  "type": "connection_established",
  "message": "Connected to order tracking",
  "order_id": 123
}
```

Ulanganda darhol mavjud oxirgi koordinata bo'lsa:

```json
{
  "type": "driver_location_update",
  "order_id": 123,
  "driver_id": 45,
  "latitude": "41.2995",
  "longitude": "69.2401",
  "updated_at": "2026-04-14T12:34:56.000000+05:00",
  "eta_minutes": 6,
  "eta_to_pickup_minutes": 6,
  "eta_to_destination_minutes": 14,
  "tracking_phase": "to_pickup"
}
```

Driver yangi lokatsiya yuborganda ham shu event keladi: `type = driver_location_update`.
`eta_minutes` frontda asosiy badge uchun ishlatiladi (masalan: `6 min`).

`tracking_phase` qiymatlari:
- `to_pickup` — driver rider tomon kelyapti (`accepted`, `on_the_way`)
- `arrived` — pickupga yetib kelgan
- `to_destination` — safar boshlangan (`in_progress`)
- `unknown` — koordinata yetarli bo'lmasa

### 7.4 Qanday ishlaydi

1. Driver ilovasi odatdagidek `POST /api/v1/order/driver/location/update/` qiladi.
2. Backend accepted va aktiv statusdagi orderlar uchun `order_tracking_{order_id}` guruhiga WS push yuboradi.
3. Rider/driver tracking socketga ulangan bo'lsa darhol lokatsiya update oladi.

### 7.5 Kodda qayerda

- WS consumer: `apps/order/consumers.py` (`OrderTrackingConsumer`)
- WS route: `config/routing.py`
- Broadcast helper: `apps/order/services/order_tracking_websocket.py`
- Trigger point: `apps/order/views.py` (`DriverLocationUpdateView`)

---

## 8. PIN verification flow (rider + driver)

Bu bo'lim front savoliga javob sifatida tartiblangan.

### 8.1 Hozirgi holat (muhim)

Hozir `accounts/pin-verification/` faqat **foydalanuvchi profili PIN** uchun ishlaydi:

- `GET /api/v1/accounts/pin-verification/`
- `POST /api/v1/accounts/pin-verification/`

Bu PIN `PinVerificationForUser` modelida saqlanadi va **order/ride bilan bog'lanmagan**.  
Shuning uchun driver "ride ni tasdiqlash" uchun ishlata olmaydi (hozircha).

### 8.2 To'g'ri biznes flow (tavsiya etilgan)

1. Rider order yaratadi.
2. Driver orderni `accepted` qiladi.
3. Backend shu order uchun `ride_pin` (4 xonali) yaratadi.
4. Rider ilovada PIN ni ko'radi.
5. Driver riderdan PIN ni olib, verify API ga yuboradi.
6. Verify muvaffaqiyatli bo'lsa order status `in_progress` ga o'tadi.
7. Order `completed` yoki `cancelled` bo'lsa `ride_pin` o'chiriladi/yaroqsiz qilinadi.

### 8.3 Rider uchun nima ko'rinadi

- Active ride detail ichida `ride_pin` (faqat o'z orderi uchun).
- Agar hali driver accept qilmagan bo'lsa: `ride_pin = null`.
- Driver accept qilgach: `ride_pin` paydo bo'ladi.

### 8.4 Driver uchun nima kerak

Driverda alohida verify endpoint bo'lishi kerak:

- `POST /api/v1/order/driver/pin/verify/`
- Body:

```json
{
  "order_id": 123,
  "pin": "4821"
}
```

Kutilgan natija:
- PIN to'g'ri => `verified: true`, order `in_progress`.
- PIN noto'g'ri => `400`, xatolik.
- 3-5 marta xato urinish bo'lsa vaqtincha lock qo'yish mumkin.

### 8.5 WebSocket bilan yuborish varianti

Siz aytgan variant to'g'ri: driver accept qilganda pinni WS bilan yuborish mumkin.

Tavsiya:
- Driverga `ws/driver/orders/` da yangi event:
  - `type: rider_pin_required`
  - `order_id`
  - `pin_required: true`
  - (`pin` ni ochiq yubormaslik xavfsizroq)

Xavfsizlik bo'yicha eng yaxshi yo'l:
- PIN rider UI da ko'rinadi.
- Driver faqat verify qiladi.
- PIN ni driverga plain text yubormaslik.

### 8.6 Keyingi implementatsiya rejasi (agar hozir kod qilinsa)

1. `order` app ichida `OrderRidePin` model (order FK, pin, verified_at, attempts, expires_at).
2. Driver accept bo'lganda auto-generate.
3. Driver verify endpoint qo'shish.
4. `OrderDetailSerializer`ga rider uchun `ride_pin` qo'shish (driverga bermaslik).
5. `cancel`/`complete` flowda pinni invalid qilish.
6. Swagger + QA scenario yangilash.

---

## 9. Preferences (order create dan oldin) — yangilangan API

So'rov bo'yicha preferences flow order yaratishdan oldin ishlashi uchun o'zgartirildi.

### 9.1 Endi `order_id` kerak emas

Oldingi holat:
- `GET /api/v1/order/preferences/?order_id=...` talab qilardi.

Yangi holat:
- `GET /api/v1/order/preferences/` — current user uchun saqlangan template qaytadi.
- Agar user hali saqlamagan bo'lsa, default qiymatlar qaytadi (`200` bilan).

### 9.2 Create/Update endpointlar

1. `POST /api/v1/order/preferences/create/` — create yoki update (upsert)
2. `PUT /api/v1/order/preferences/create/` — update
3. `PUT /api/v1/order/preferences/update/` — update alias

Body (hammasi ixtiyoriy emas, standart preference maydonlari):
- `chatting_preference`
- `temperature_preference`
- `music_preference`
- `volume_level`
- `pet_preference`
- `kids_chair_preference`
- `wheelchair_preference`
- `gender_preference`
- `favorite_driver_preference`

### 9.3 Order create bilan bog'lanishi

`POST /api/v1/order/create/` bo'lganda backend user template (`UserOrderPreferences`) ni topadi va yangi orderga `OrderPreferences` sifatida avtomatik nusxalaydi.

Ya'ni frontdagi Preferences sahifasi -> keyin Confirm Ride bosilganda preference orderga o'tadi.

### 9.4 Kodda qayerda

- Model: `apps/order/models.py` (`UserOrderPreferences`)
- Migration: `apps/order/migrations/0019_userorderpreferences.py`
- Serializer: `apps/order/serializers/order_preferences.py` (`UserOrderPreferencesSerializer`)
- View: `apps/order/views.py` (`OrderPreferencesGetView`, `OrderPreferencesCreateView`)
- URL: `apps/order/urls.py`

