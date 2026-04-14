# Frontend handoff: Order, Driver Tracking va Swagger

Bu hujjat frontend jamoaga yuborish uchun tayyorlandi: nima talab qilingan edi, backendda nima qilindi, qaysi endpointlardan qanday foydalaniladi va qanday javob keladi.

---

## 1) Nima ish qilinishi kerak edi

Quyidagi muammolarni yechish so'ralgan:

1. Swagger endpointlar tartibsiz ko'rinayotgan edi (`Order`, `Driver` taglari ostida juda uzun ro'yxat).
2. `manage-price` oqimida chalkashlik bor edi:
   - order create qilishdan oldingi narx tekshiruvi (plan bosqichi),
   - order yaratilgandan keyingi order item narxini boshqarish.
3. Driver real-time oqimida rider cancel qilganini ko'rish kerak edi.
4. Driver location tracking bilan birga "necha minutda yetib keladi (ETA)" ni ham yuborish kerak edi.
5. Frontend uchun bu o'zgarishlar bitta aniq texnik hujjatga tushirilishi kerak edi.

---

## 2) Nima implement qilindi

### 2.1 Swagger strukturasi professional tarzda qayta guruhlandi

Endpointlar quyidagi mantiqiy taglarga bo'lindi:

- `Rider: Orders`
- `Rider: Preferences`
- `Rider: Pricing`
- `Rider: Order items`
- `Rider: Active ride`
- `Rider: Live tracking`
- `Driver: Orders & trips`
- `Driver: Location`
- `Driver: Earnings & wallet`
- `Driver: Availability`
- `Trip ratings`
- `Trip chat`

Natija: frontend uchun kerakli endpointlarni tez topish osonlashdi.

---

### 2.2 Manage-price oqimi aniq ajratildi

#### A) Plan (order create oldidan)

- **Endpoint:** `POST /api/v1/order/price-estimate/manage-price/`
- **Maqsad:** tanlangan narx (`adjusted_price`) ruxsat etilgan intervalda ekanini tekshirish.
- **Kalit nuqta:** bu endpointda `ride_type_id` ishlatiladi.

**So'rov namunasi:**

```json
{
  "ride_type_id": 1,
  "latitude_from": 41.31,
  "longitude_from": 69.24,
  "latitude_to": 41.29,
  "longitude_to": 69.28,
  "adjusted_price": 28000
}
```

**Muvaffaqiyatli javob (`200`):**

```json
{
  "message": "Price validated successfully",
  "status": "success",
  "data": {
    "id": 1,
    "ride_type_id": 1,
    "distance_km": 6.2,
    "surge_multiplier": 1.1,
    "calculated_price": 30000,
    "min_price": 24000,
    "max_price": 45000,
    "adjusted_price": 28000,
    "valid": true
  }
}
```

**Noto'g'ri interval (`400`):**

```json
{
  "message": "Price is outside allowed range",
  "status": "error",
  "data": {
    "valid": false
  }
}
```

#### B) Order yaratilgandan keyin (order item bo'yicha)

- **Endpoint:** `PATCH /api/v1/order/order-item/{order_item_id}/manage-price/`
- **Maqsad:** aynan yaratilgan order item narxini boshqarish.
- **Kalit nuqta:** bu endpointda `order_item_id` ishlatiladi (`ride_type_id` emas).

**So'rov namunasi:**

```json
{
  "adjusted_price": 32000
}
```

**Javob (`200`):**

```json
{
  "message": "Order item price managed successfully",
  "status": "success",
  "data": {
    "id": 987,
    "adjusted_price": 32000
  }
}
```

---

### 2.3 Driver uchun rider cancel real-time yuborish

- **Kanal:** `ws://HOST/ws/driver/orders/?token=<JWT>`
- Rider `POST /api/v1/order/{order_id}/cancel/` qilganda driverga websocket event ketadi.
- Event nomi: `order_cancelled_by_rider`.

**Event payload:**

```json
{
  "type": "order_cancelled_by_rider",
  "change": "cancelled_rider",
  "message": "The rider cancelled this ride.",
  "order": {
    "id": 123,
    "status": "cancelled"
  },
  "cancel": {
    "cancelled_by": "rider",
    "reason": "changed_mind",
    "other_reason": null,
    "created_at": "2026-04-14T12:00:00Z"
  }
}
```

Frontend tavsiya:

- `type == "order_cancelled_by_rider"` bo'lsa kartani ro'yxatdan olib tashlash,
- kerak bo'lsa "Ride cancelled" toast/modal ko'rsatish.

---

### 2.4 Driver location tracking ichida ETA yuborish

Rider tracking ekrani uchun ETA shu tracking websocketdan keladi.

- **Tracking kanal:** `ws://HOST/ws/order/{order_id}/tracking/?token=<JWT>`
- Driver location yangilanganda `driver_location_update` event keladi.

**Event payload:**

```json
{
  "type": "driver_location_update",
  "order_id": 123,
  "driver_id": 45,
  "latitude": "41.311081",
  "longitude": "69.240562",
  "updated_at": "2026-04-14T12:05:00Z",
  "eta_minutes": 6,
  "eta_to_pickup_minutes": 6,
  "eta_to_destination_minutes": 14,
  "tracking_phase": "to_pickup"
}
```

`tracking_phase` qiymatlari:

- `to_pickup` — haydovchi klient oldiga ketmoqda
- `arrived` — haydovchi yetib kelgan
- `to_destination` — safar boshlangan, manzilga ketmoqda

Frontend tavsiya:

- badge/label uchun asosiy maydon: `eta_minutes`
- qo'shimcha progress UI uchun: `tracking_phase`.

---

## 3) API/WS bo'yicha qisqa ishlatish ketma-ketligi

### Rider app

1. `GET /api/v1/order/rider/active-ride/`
2. Agar aktiv ride bo'lsa: `ws/order/{order_id}/tracking/` ga ulanish
3. `driver_location_update` eventidan `eta_minutes` ni chiqarish

### Driver app

1. `GET /api/v1/order/driver/active-ride/`
2. `ws/driver/orders/` ga ulanish
3. `new_order`, `order_timeout`, `order_cancelled_by_rider` eventlarini tinglash

---

## 4) Frontend uchun muhim mapping (xatoni oldini olish uchun)

- `price-estimate` javobidagi `estimates[].id` => `ride_type_id` (plan bosqichi)
- `order detail` javobidagi `order_items[].id` => `order_item_id` (order yaratilgandan keyin)

---

## 5) Yakuniy holat

- Swagger struktura tozalandi va aniq taglarga bo'lindi.
- Manage-price oqimi 2 bosqichga aniq ajratildi (pre-order vs post-order).
- Rider cancel holati driverga websocket orqali real-time yuboriladi.
- Driver location tracking eventida ETA maydonlari yuboriladi.
- Frontend integratsiya uchun kerakli request/response formatlari yuqorida berildi.

