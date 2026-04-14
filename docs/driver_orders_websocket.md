# Driver Orders WebSocket - Real-Time API

Driver uchun order yangilanishlarini real-time qabul qilish.

## URL

```
ws://HOST/ws/driver/orders/?token=JWT_TOKEN
```

yoki

```
ws://HOST/ws/driver/orders/JWT_TOKEN
```

## Autentifikatsiya

- JWT token kerak (query param `token` yoki path ichida)
- User Driver guruhida bo'lishi kerak

### Postman / client: `403` yoki ulanmayapti

1. **URLda `?` bo‘lishi kerak:** to‘g‘ri: `.../ws/driver/orders/?token=eyJ...`  
   Noto‘g‘ri (ba’zi clientlar shunday yuboradi): `.../ws/driver/orders/token=eyJ...` — middleware tokenni baribir pathdan olishga harakat qiladi, lekin standart query shakli afzal.
2. **Access token yangi bo‘lsin.** Muddat tugagan token bilan SimpleJWT `token_not_valid` qaytaradi; server logida `Reject: anonymous (no valid token)` va JWT rad xabari ko‘rinadi. **Login** yoki **refresh** qilib yangi `access` yuboring.
3. **Shu backendning `SECRET_KEY`** bilan chiqarilgan token ishlating (boshqa muhitdan ko‘chirilgan JWT imzosi mos kelmasligi mumkin).
4. Token **Driver** roliga ega foydalanuvchiga tegishli bo‘lishi kerak — aks holda ulanishdan keyin `4403` / ruxsat rad.

## Xabarlar (Server → Client)

### 1. `connection_established`

Ulanish muvaffaqiyatli bo'lganda:

```json
{
  "type": "connection_established",
  "message": "Connected to driver orders",
  "driver_id": 5
}
```

### 2. `initial_orders`

Ulanishdan keyin darhol - driverning hozirgi pending orderlari (avtomatik):

```json
{
  "type": "initial_orders",
  "orders": [
    {
      "id": 123,
      "order_code": "ORD-000123",
      "status": "pending",
      "order_type": "pickup",
      "created_at": "2026-02-21T10:00:00",
      "requested_at": "2026-02-21T10:00:05",
      "estimated_time": "15 min",
      "address_from": "...",
      "address_to": "...",
      "distance_to_pickup_km": 2.5,
      "net_price": 12500.50,
      "client": {
        "id": 10,
        "first_name": "John",
        "last_name": "Doe",
        "full_name": "John Doe",
        "phone_number": "+998901234567",
        "email": "john@example.com",
        "avatar": "/media/avatars/xxx.jpg"
      }
    }
  ],
  "message": "Current pending orders"
}
```

### 3. `new_order`

Yangi order driverga tushganda:

```json
{
  "type": "new_order",
  "order": {
    "id": 123,
    "order_code": "ORD-000123",
    "status": "pending",
    "order_type": "pickup",
    "created_at": "2026-02-21T10:00:00",
    "requested_at": "2026-02-21T10:00:05",
    "estimated_time": "15 min",
    "address_from": "...",
    "address_to": "...",
    "latitude_from": "41.311081",
    "longitude_from": "69.240562",
    "latitude_to": "41.299496",
    "longitude_to": "69.240074",
    "distance_to_pickup_km": 2.5,
    "net_price": 12500.50,
    "client": {
      "id": 10,
      "first_name": "John",
      "last_name": "Doe",
      "full_name": "John Doe",
      "phone_number": "+998901234567",
      "email": "john@example.com",
      "avatar": "/media/avatars/xxx.jpg"
    }
  },
  "message": "New ride request available"
}
```

### 4. `order_timeout`

Order timeout bo'lib boshqa driverga o'tganda:

```json
{
  "type": "order_timeout",
  "order_id": 123,
  "message": "Order expired or reassigned to another driver"
}
```

### 5. `order_cancelled_by_rider` — rider buyurtmani bekor qilganda

**Maqsod:** Haydovchi ilovasi real-time bilishi kerak: yo‘lovchi safarni bekor qildi (masalan, haydovchi allaqachon taklifni ko‘rib turgan yoki qabul qilgan, lekin yo‘lda emas).

**Backend oqimi:**

1. Yo‘lovchi `POST /api/v1/order/{order_id}/cancel/` chaqiradi (`OrderCancelView`).
2. Buyurtma `cancelled` bo‘ladi, `CancelOrder` yozuvi yaratiladi.
3. `apps.order.services.driver_orders_websocket.notify_drivers_order_cancelled_by_rider(order_id, request)` chaqiriladi.
4. Shu buyurtmada `OrderDriver` statusi **`requested`** yoki **`accepted`** bo‘lgan **barcha** haydovchilar aniqlanadi (bir nechta taklif bo‘lsa ham).
5. Har biriga Channels orqali `driver_orders_{driver_user_id}` guruhiga `type: order_cancelled_by_rider` yuboriladi.
6. `DriverOrdersConsumer.order_cancelled_by_rider` klientga JSON qaytaradi.

**Eslatma:** Agar haydovchi bu buyurtmada `requested`/`accepted` da bo‘lmasa, xabar **kelmaydi** (masalan, faqat boshqa haydovchilarga taklif ketgan bo‘lsa). Shuning uchun ilovada REST (`GET .../driver/active-ride/`) bilan socketni birga ishlatish tavsiya etiladi.

**Namuna javob:**

```json
{
  "type": "order_cancelled_by_rider",
  "change": "cancelled_rider",
  "message": "The rider cancelled this ride.",
  "order": { "...": "OrderDetailSerializer — to'liq buyurtma (REST bilan bir xil shakl)" },
  "cancel": {
    "cancelled_by": "rider",
    "reason": "changed_mind",
    "other_reason": null,
    "created_at": "2026-04-14T12:00:00+00:00",
    "order_driver_id": 42
  }
}
```

`cancel` ba’zi maydonlari `null` bo‘lishi mumkin; front `type === "order_cancelled_by_rider"` bo‘lsa ro‘yxatdan olib tashlash yoki “bekor qilindi” ekranini ko‘rsatishi kerak.

### 6. `active_ride_snapshot` — ulanishdan keyin bir marta (aktiv safar holati)

Ulanishdan so‘ng Celery task taxminan 3 soniyada bitta snapshot yuboradi (`send_active_ride_snapshot_once`). Bu **rider kuzatish** emas, balki “hozir qabul qilingan safar bormi?” ni sinxronlashtirish uchun.

```json
{
  "type": "active_ride_snapshot",
  "scope": "driver",
  "has_active_ride": true,
  "order": { "...": "OrderDetailSerializer yoki null" },
  "checked_at": "2026-04-14T12:00:00Z",
  "message": "Active ride status refreshed"
}
```

Batafsil: `docs/ACTIVE_RIDE_AND_QA_CHECKLIST.md` (active ride + WS).

**Yo‘lovchini xaritada kuzatish (haydovchi pozitsiyasi yo‘lovchiga):** alohida endpoint — `ws/order/{order_id}/tracking/` (`OrderTrackingConsumer`). Bu hujjat faqat `ws/driver/orders/` kanalini qamrab oladi.

## Client → Server (ixtiyoriy)

### `ping` - keepalive

```json
{"type": "ping"}
```

Javob: `{"type": "pong"}`

## Qachon yuboriladi

| Voqea | WebSocket xabari |
|-------|------------------|
| Driver ulandi | `connection_established` + `initial_orders` (avtomatik) |
| ~3 s keyin (bir marta) | `active_ride_snapshot` |
| Order driverga assign qilindi | `new_order` |
| Order timeout (5 min) - Celery | `order_timeout` (eski driver), `new_order` (yangi driver) |
| Order timeout - Driver poll qilganda | `order_timeout` (o'sha driver) |
| Rider `POST .../{order_id}/cancel/` | `order_cancelled_by_rider` (faqat `requested` / `accepted` haydovchilarga) |

## Mobile app misoli (JavaScript)

```javascript
const token = 'YOUR_JWT_TOKEN';
const ws = new WebSocket(`wss://api.example.com/ws/driver/orders/?token=${token}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch (data.type) {
    case 'connection_established':
      console.log('Connected');
      break;
    case 'initial_orders':
      setOrdersList(data.orders);  // Avtomatik - hozirgi orderlar
      break;
    case 'new_order':
      addOrderToList(data.order);
      break;
    case 'order_timeout':
      removeOrderFromList(data.order_id);
      break;
    case 'order_cancelled_by_rider':
      removeOrderFromList(data.order?.id);
      showToast(data.message);
      break;
    case 'active_ride_snapshot':
      syncActiveRideUI(data.has_active_ride, data.order);
      break;
  }
};
```

## Kod manbalari

| Qism | Fayl |
|------|------|
| URL / consumer | `config/routing.py`, `apps/order/consumers.py` — `DriverOrdersConsumer` |
| Rider cancel → driver push | `apps/order/views.py` — `OrderCancelView`; `apps/order/services/driver_orders_websocket.py` — `notify_drivers_order_cancelled_by_rider` |
