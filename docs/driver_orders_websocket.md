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
      "address_from": "...",
      "address_to": "...",
      "distance_to_pickup_km": 2.5
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
    "address_from": "...",
    "address_to": "...",
    "latitude_from": "41.311081",
    "longitude_from": "69.240562",
    "latitude_to": "41.299496",
    "longitude_to": "69.240074",
    "distance_to_pickup_km": 2.5
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
| Order driverga assign qilindi | `new_order` |
| Order timeout (5 min) - Celery | `order_timeout` (eski driver), `new_order` (yangi driver) |
| Order timeout - Driver poll qilganda | `order_timeout` (o'sha driver) |

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
  }
};
```
