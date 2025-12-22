# Tracking & Advanced Driver Features - End-to-End Flow (Uber Model)

Bu hujjat **frontend** jamoa uchun. Unda **to'liq ketma-ketlik** (end-to-end flow) tushuntiriladi - rider order ochgandan to ride tugaguncha qaysi API lar qanday ketma-ketlikda chaqiriladi.

**⚠️ MUHIM:** Bu sistemada **Uber modeli** ishlatiladi - order yaratilganda avtomatik eng yaqin driverga yuboriladi, driver 25 soniya ichida javob berishi kerak.

---

## 📱 TO'LIQ KETMA-KETLIK (End-to-End Flow)

### **BOSQICH 1: Rider Order Ochadi**

#### 1.1. Rider Order Yaratadi

**API:** `POST /api/v1/order/create/`

**Request:**
```json
{
  "address_from": "Toshkent, Chilonzor",
  "address_to": "Toshkent, Yunusobod",
  "latitude_from": 41.311081,
  "longitude_from": 69.240562,
  "latitude_to": 41.325000,
  "longitude_to": 69.300000,
  "order_type": 1  // 1 = PICKUP, 2 = FOR_ME
}
```

**Response:**
```json
{
  "message": "Order created successfully",
  "status": "success",
  "data": {
    "id": 123,
    "order_code": "ORD-000123",
    "status": "pending",  // ← Hali driver tayinlanmagan
    "order_type": "pickup",
    "order_items": [...]
  }
}
```

**Nima bo'ladi (Uber modeli + Radius-based search + Destination matching):**
- `Order` yaratiladi, `status = pending`
- `OrderItem` yaratiladi (from/to koordinatalar bilan)
- **Backend radius-based search ishlatadi:**
  1. **Birinchi marta 5 km radius ichida** driverlarni qidiradi:
     - **Bo'sh driverlar** (active order yo'q)
     - **Active order bor driverlar**, lekin ularning **destination'i yangi order'ning pickup'iga yaqin** (3 km radius ichida) - **Uber-style matching**
  2. Agar topilmasa, **10 soniya kutadi** (driverlar bo'sh bo'lishi mumkin)
  3. Keyin **10 km radius** ichida qidiradi
  4. Agar topilmasa, yana **10 soniya kutadi**
  5. Keyin **15 km radius**, keyin **20 km radius**...
- **Topilgan eng yaqin driverga push notification yuboriladi**
- `OrderDriver` yaratiladi (`status = requested`, `requested_at = hozirgi vaqt`)
- **Driver 25 soniya ichida javob berishi kerak**
- **Muhim:** 
  - **Bo'sh driverlar** (active order yo'q) yuboriladi
  - **Active order bor driverlar ham yuboriladi**, agar ularning **destination'i yangi order'ning pickup'iga 3 km radius ichida** bo'lsa (Uber-style)

---

#### 1.2. Rider Ride Type Tanlaydi (ixtiyoriy)

**API:** `PUT /api/v1/order/order-item/{order_item_id}/update/`

**Request:**
```json
{
  "ride_type_id": 1  // 1 = Hola (Standard), 2 = Premium, 3 = Eco
}
```

**Response:**
```json
{
  "message": "Order item updated successfully",
  "status": "success",
  "data": {
    "id": 456,
    "ride_type": 1,
    "ride_type_name": "Hola",
    "calculated_price": 15000.00,
    "distance_km": 5.2,
    "estimated_time": "15 min"
  }
}
```

**Nima bo'ladi:**
- `OrderItem.ride_type` o'rnatiladi
- Narx avtomatik hisoblanadi (`calculated_price`)
- Masofa va vaqt hisoblanadi

---

### **BOSQICH 2: Driver Orderni Ko'radi va Javob Beradi**

#### 2.1. Driver App Ochilganda Lokatsiyani Yuboradi

**API:** `POST /api/v1/order/driver/location/update/`

**Request:**
```json
{
  "latitude": 41.310000,
  "longitude": 69.240000
}
```

**Response:**
```json
{
  "message": "Location updated successfully",
  "status": "success"
}
```

**Nima bo'ladi:**
- `CustomUser.latitude` va `longitude` yangilanadi
- Bu driverning **hozirgi joylashuvi**
- **Muhim:** Driver lokatsiyasi yangilanmasa, orderlarga assign qilinmaydi

---

#### 2.2. Driver O'ziga Yuborilgan Orderlarni Ko'radi

**API:** `GET /api/v1/order/driver/nearby-orders/`

**Request:**
```
GET /api/v1/order/driver/nearby-orders/
Authorization: Bearer <driver_token>
```

**Response:**
```json
{
  "message": "Assigned orders retrieved successfully",
  "status": "success",
  "data": [
    {
      "id": 123,
      "order_code": "ORD-000123",
      "status": "pending",
      "address_from": "Toshkent, Chilonzor",
      "address_to": "Toshkent, Yunusobod",
      "latitude_from": 41.311081,
      "longitude_from": 69.240562,
      "latitude_to": 41.325000,
      "longitude_to": 69.300000,
      "distance_to_pickup_km": 2.35,  // ← Driverdan pickup nuqtasigacha masofa
      "ride_type_name": "Hola",
      "calculated_price": 15000.00,
      "time_remaining_seconds": 15  // ← 25 soniyadan qolgan vaqt (agar timeout bo'lmasa)
    }
  ]
}
```

**Nima bo'ladi (Uber modeli):**
- Backend **faqat o'ziga `requested` statusdagi** orderlarni qaytaradi
- Ya'ni, faqat shu driverga yuborilgan orderlar ko'rinadi
- **Timeout tekshiriladi:** Agar 25 soniya o'tgan bo'lsa, order keyingi driverga yuboriladi
- **Driver bu orderni accept yoki reject qilishi kerak**

---

### **BOSQICH 3: Driver Accept/Reject Qiladi**

#### 3.1. Driver Accept Qiladi

**API:** `POST /api/v1/order/driver/order-action/`

**Request:**
```json
{
  "order_id": 123,
  "action": "accept"  // yoki "reject"
}
```

**Response (Accept):**
```json
{
  "message": "Order accepted successfully",
  "status": "success"
}
```

**Nima bo'ladi:**
- `OrderDriver.status` = `requested` → `accepted` ga o'zgaradi
- `OrderDriver.responded_at` = hozirgi vaqt
- `Order.status` = `pending` → `confirmed` ga o'zgaradi
- **Rider push notification oladi:** "Driver found - Your ride has been accepted"
- **Order endi boshqa driverlarga ko'rinmaydi**

---

#### 3.2. Driver Reject Qiladi

**API:** `POST /api/v1/order/driver/order-action/`

**Request:**
```json
{
  "order_id": 123,
  "action": "reject"
}
```

**Response:**
```json
{
  "message": "Order rejected. Reassigned to next driver.",
  "status": "success"
}
```

**Nima bo'ladi (Uber modeli):**
- `OrderDriver.status` = `requested` → `rejected` ga o'zgaradi
- `OrderDriver.responded_at` = hozirgi vaqt
- **Backend avtomatik keyingi eng yaqin driverni topadi**
- **Keyingi driverga push notification yuboriladi**
- **Yangi `OrderDriver` yaratiladi** (`status = requested`)
- `Order.status` = `pending` qoladi

---

#### 3.3. Timeout (25 soniya ichida javob berilmagan)

**Nima bo'ladi (avtomatik - Celery orqali):**
- Agar driver 25 soniya ichida javob bermasa:
  - **Celery Beat har 5 soniyada timeout tekshiradi** (avtomatik background task)
  - `OrderDriver.status` = `requested` → `timeout` ga o'zgaradi
  - **`OrderDriver` modelida saqlanadi** - bu driver endi bu orderni ko'rmaydi
  - **Backend avtomatik keyingi eng yaqin driverni topadi** (oldingi driver exclude qilingan)
  - **Keyingi driverga push notification yuboriladi**
  - **Yangi `OrderDriver` yaratiladi** (`status = requested`, yangi driver uchun)
  - **Jarayon takrorlanadi** - keyingi driver ham 25 soniya ichida javob berishi kerak

**Muhim:**
- **Oldingi driver yana bu orderni ko'rmaydi** - chunki `OrderDriver` modelida `status = timeout` saqlanadi va `exclude_driver_ids` ga qo'shiladi
- **Celery Beat har 5 soniyada avtomatik tekshiradi** - driver API chaqirmasdan ham ishlaydi
- Timeout bo'lganda, order darhol keyingi driverga yuboriladi (avtomatik reassignment)
- **Celery worker va beat ishga tushirilishi kerak** (qarang: "Celery Setup va Run Qilish" bo'limi)

---

### **BOSQICH 4: Real-Time Tracking (Driver Accept Qilgandan Keyin)**

#### 4.1. Driver Lokatsiyasini Davomiy Yangilaydi

**API:** `POST /api/v1/order/driver/location/update/`

**Request (har 5-10 soniyada):**
```json
{
  "latitude": 41.310500,
  "longitude": 69.240500
}
```

**Response:**
```json
{
  "message": "Location updated successfully",
  "status": "success"
}
```

**Nima bo'ladi:**
- `CustomUser.latitude` va `longitude` yangilanadi
- **Driver harakatlanayotganda** bu API ni **har 5-10 soniyada** chaqirish kerak
- Bu lokatsiya rider tomonidan ko'riladi

---

#### 4.2. Rider Driver Lokatsiyasini Ko'radi (Polling)

**API:** `GET /api/v1/order/{order_id}/driver/location/`

**Request:**
```
GET /api/v1/order/123/driver/location/
Authorization: Bearer <rider_token>
```

**Response:**
```json
{
  "message": "Driver location retrieved successfully",
  "status": "success",
  "data": {
    "driver_id": 45,
    "latitude": 41.310500,
    "longitude": 69.240500,
    "updated_at": "2025-01-01T12:01:00Z"
  }
}
```

**Nima bo'ladi:**
- Rider **har 3-5 soniyada** bu API ni chaqiradi (polling)
- Driver lokatsiyasi (`CustomUser.latitude/longitude`) qaytariladi
- **Frontend map'da driver marker'ini yangilaydi**
- Faqat `confirmed` statusdagi orderlar uchun ishlaydi

---

### **BOSQICH 5: Ride Tugaydi**

#### 5.1. Order Completed (Admin yoki Backend avtomatik)

**API:** (Backend ichki yoki Admin panel orqali)

**Nima bo'ladi:**
- `Order.status` = `confirmed` → `completed` ga o'zgaradi
- Payment jarayoni boshlanadi (agar kerak bo'lsa)

---

## 🔄 KETMA-KETLIK DIAGRAMMASI (Uber Modeli)

```
┌─────────┐
│  RIDER  │
└────┬────┘
     │
     │ 1. POST /order/create/
     │    → Order yaratiladi (status: pending)
     │    → Backend eng yaqin driverni topadi
     │    → Driver #1 ga push notification
     │    → OrderDriver yaratiladi (status: requested)
     ▼
┌─────────┐
│ BACKEND │
└────┬────┘
     │
     │ 2. Driver #1 push notification oladi
     │    → "New ride request available nearby"
     ▼
┌─────────┐
│ DRIVER  │
│   #1    │
└────┬────┘
     │
     │ 3. POST /order/driver/location/update/
     │    → Driver lokatsiyasi yangilanadi
     │
     │ 4. GET /order/driver/nearby-orders/
     │    → O'ziga yuborilgan orderlar ro'yxati
     │    → Order #123 ko'rinadi (25 soniya timeout)
     │
     │ 5. POST /order/driver/order-action/
     │    action: "accept" yoki "reject"
     │
     │    AGAR ACCEPT:
     │    → OrderDriver.status = "accepted"
     │    → Order.status = "confirmed"
     │    → Rider push notification oladi
     │    → Real-time tracking boshlanadi
     │
     │    AGAR REJECT:
     │    → OrderDriver.status = "rejected"
     │    → Backend keyingi eng yaqin driverni topadi
     │    → Driver #2 ga push notification
     │    → Yangi OrderDriver yaratiladi (status: requested)
     │
     │    AGAR TIMEOUT (25 soniya) - Celery orqali:
     │    → Celery Beat har 5 soniyada timeout tekshiradi
     │    → Celery Worker: OrderDriver.status = "timeout"
     │    → Backend keyingi eng yaqin driverni topadi
     │    → Driver #2 ga push notification
     │    → Yangi OrderDriver yaratiladi (status: requested)
     ▼
┌─────────┐
│ BACKEND │
└────┬────┘
     │
     │ 6. Real-time tracking boshlanadi (accept bo'lsa)
     │
     │    Driver tomonidan:
     │    POST /order/driver/location/update/ (har 5-10 s)
     │
     │    Rider tomonidan:
     │    GET /order/{order_id}/driver/location/ (har 3-5 s)
     │
     ▼
┌─────────┐
│  RIDER  │
└─────────┘
     │
     │ 7. Order completed
     ▼
```

---

## 📋 API LAR RO'YXATI

### **Rider uchun:**

1. **Order yaratish:**
   - `POST /api/v1/order/create/` - Order yaratadi, avtomatik eng yaqin driverga yuboriladi

2. **Ride type tanlash:**
   - `PUT /api/v1/order/order-item/{order_item_id}/update/` - Ride type va narx

3. **Order holatini ko'rish:**
   - `GET /api/v1/order/my-orders/` - Barcha orderlar
   - `GET /api/v1/order/my-orders/?status=confirmed` - Faqat confirmed orderlar

4. **Driver lokatsiyasini kuzatish:**
   - `GET /api/v1/order/{order_id}/driver/location/` - Driver lokatsiyasi (polling, har 3-5 s)

5. **Order bekor qilish:**
   - `POST /api/v1/order/{order_id}/cancel/` - Order bekor qilish

---

### **Driver uchun:**

1. **Lokatsiya yangilash:**
   - `POST /api/v1/order/driver/location/update/` - GPS lokatsiyasi (app ochilganda va har 5-10 s)

2. **O'ziga yuborilgan orderlarni ko'rish:**
   - `GET /api/v1/order/driver/nearby-orders/` - Faqat o'ziga `requested` statusdagi orderlar

3. **Accept/Reject:**
   - `POST /api/v1/order/driver/order-action/` - Accept yoki reject (25 soniya ichida)

4. **O'z orderlarini ko'rish:**
   - `GET /api/v1/order/my-orders/?status=confirmed` - Qabul qilingan orderlar

---

## ⚠️ MUHIM ESLAVLAR (Uber Modeli)

### **1. Order Yaratilganda (Uber Modeli)**

- Order yaratilganda **avtomatik eng yaqin driverga yuboriladi**
- Driver **push notification oladi** ("New ride request available nearby")
- `OrderDriver` yaratiladi (`status = requested`, `requested_at = hozirgi vaqt`)
- **Driver 25 soniya ichida javob berishi kerak**

### **2. Driver Lokatsiya Yangilash**

- Driver app ochilganda **darhol** lokatsiyani yuborish kerak
- Harakatlanayotganda **har 5-10 soniyada** yangilash kerak
- **Agar lokatsiya yangilanmasa, orderlarga assign qilinmaydi**

### **3. Driver Orderlarni Ko'rish (Uber Modeli)**

- `GET /order/driver/nearby-orders/` **faqat o'ziga yuborilgan** orderlarni qaytaradi
- Ya'ni, faqat `OrderDriver.status = requested` va `driver = current_driver` bo'lgan orderlar
- **Timeout tekshiriladi:** Agar 25 soniya o'tgan bo'lsa, order keyingi driverga yuboriladi
- **Barcha driverlar bir vaqtda bir xil orderni ko'rmaydi** - faqat birinchi eng yaqin driver

### **4. Driver Accept/Reject (Uber Modeli)**

- **Accept:** Order driverga assign qilinadi, rider push notification oladi
- **Reject:** Order keyingi eng yaqin driverga yuboriladi (avtomatik)
- **Timeout (25 soniya):** Order keyingi eng yaqin driverga yuboriladi (avtomatik)
- **Faqat o'ziga `requested` statusdagi orderlarni accept/reject qilish mumkin**

### **5. Rider Polling**

- Driver accept qilgandan keyin **har 3-5 soniyada** `GET /order/{order_id}/driver/location/` chaqirish kerak
- Bu polling - WebSocket emas (keyinchalik WebSocket qo'shilishi mumkin)

### **6. Order Status**

- `pending` - Hali driver tayinlanmagan yoki driver javob bermagan
- `confirmed` - Driver accept qilgan (tracking boshlanadi)
- `completed` - Ride tugagan
- `cancelled` - Bekor qilingan

### **7. OrderDriver Status**

- `requested` - Driverga so'rov yuborilgan (25 soniya timeout)
- `accepted` - Driver accept qilgan
- `rejected` - Driver reject qilgan
- `timeout` - Driver 25 soniya ichida javob bermagan

---

## 🎯 MISOL SCENARIO (Uber Modeli)

### **Scenario: Rider Toshkentdan Yunusobodga ketmoqchi**

1. **Rider order ochadi:**
   ```
   POST /order/create/
   → Order #123 yaratiladi (status: pending)
   → Backend eng yaqin driverni topadi (Driver #1, 2.35 km uzoqlikda)
   → Driver #1 ga push notification: "New ride request available nearby"
   → OrderDriver yaratiladi (status: requested, requested_at: 12:00:00)
   ```

2. **Driver #1 app ochiladi:**
   ```
   POST /order/driver/location/update/
   → Driver lokatsiyasi: 41.310000, 69.240000
   ```

3. **Driver #1 o'ziga yuborilgan orderlarni ko'radi:**
   ```
   GET /order/driver/nearby-orders/
   → Order #123 ko'rinadi (distance: 2.35 km, time_remaining: 20 seconds)
   ```

4. **Driver #1 accept qiladi (15 soniyada):**
   ```
   POST /order/driver/order-action/
   action: "accept"
   → OrderDriver.status = "accepted"
   → Order.status = "confirmed"
   → Rider push notification: "Driver found - Your ride has been accepted"
   ```

5. **Real-time tracking:**
   ```
   Driver: POST /order/driver/location/update/ (har 5-10 s)
   Rider: GET /order/123/driver/location/ (har 3-5 s)
   → Rider map'da driver marker'ini ko'radi
   ```

6. **Ride tugaydi:**
   ```
   Order.status = "completed"
   → Payment jarayoni boshlanadi
   ```

---

### **Scenario: Driver Reject Qiladi**

1. **Rider order ochadi:**
   ```
   POST /order/create/
   → Order #123 yaratiladi
   → Driver #1 ga yuboriladi (status: requested)
   ```

2. **Driver #1 reject qiladi:**
   ```
   POST /order/driver/order-action/
   action: "reject"
   → OrderDriver.status = "rejected"
   → Backend keyingi eng yaqin driverni topadi (Driver #2, 3.50 km uzoqlikda)
   → Driver #2 ga push notification: "New ride request available nearby"
   → Yangi OrderDriver yaratiladi (status: requested, driver: Driver #2)
   ```

3. **Driver #2 accept qiladi:**
   ```
   POST /order/driver/order-action/
   action: "accept"
   → OrderDriver.status = "accepted"
   → Order.status = "confirmed"
   → Rider push notification: "Driver found"
   ```

---

### **Scenario: Timeout (25 soniya) - Celery orqali**

1. **Rider order ochadi:**
   ```
   POST /order/create/
   → Order #123 yaratiladi
   → Driver #1 ga yuboriladi (status: requested, requested_at: 12:00:00)
   → OrderDriver yaratiladi (order=123, driver=Driver#1, status=requested)
   → Driver #1 ga push notification: "New ride request available nearby"
   ```

2. **Celery Beat har 5 soniyada timeout tekshiradi (avtomatik):**
   ```
   Celery Beat task: check_order_timeouts()
   → Har 5 soniyada barcha requested orderlarni tekshiradi
   → 12:00:05 - timeout yo'q (5 soniya < 25 soniya)
   → 12:00:10 - timeout yo'q (10 soniya < 25 soniya)
   → 12:00:15 - timeout yo'q (15 soniya < 25 soniya)
   → 12:00:20 - timeout yo'q (20 soniya < 25 soniya)
   → 12:00:25 - timeout topildi! (25 soniya >= 25 soniya)
   ```

3. **Celery task timeout'ni bajaradi (12:00:25):**
   ```
   Celery Worker: check_order_timeouts task
   → OrderDriver.status = "timeout" (order=123, driver=Driver#1)
   → OrderDriver modelida saqlanadi (bu driver endi bu orderni ko'rmaydi)
   → Backend keyingi eng yaqin driverni topadi (Driver #2, Driver #1 exclude qilingan)
   → Driver #2 ga push notification: "New ride request available nearby"
   → Yangi OrderDriver yaratiladi (order=123, driver=Driver#2, status=requested, requested_at: 12:00:25)
   ```

4. **Driver #1 yana ko'rmaydi:**
   ```
   GET /order/driver/nearby-orders/ (Driver #1 tomonidan)
   → Order #123 ko'rinmaydi (chunki OrderDriver.status = "timeout")
   → Driver #1 endi bu orderni ko'rmaydi
   ```

5. **Driver #2 accept qiladi:**
   ```
   POST /order/driver/order-action/
   action: "accept"
   → OrderDriver.status = "accepted" (order=123, driver=Driver#2)
   → Order.status = "confirmed"
   → Rider push notification: "Driver found"
   ```

**Muhim:** Timeout tekshirish **Celery Beat orqali avtomatik** ishlaydi. Driver API chaqirmasdan ham, 25 soniya o'tgandan keyin order keyingi driverga yuboriladi.

---

## 📝 QO'SHIMCHA MA'LUMOTLAR

### **Masofa Hisoblash**

- Backend **Haversine formula** ishlatadi
- Masofa **kilometrlarda** qaytariladi
- `DriverPreferences.maximum_pickup_distance` bo'yicha filtrlash
- Eng yaqin driver topilganda, faqat `maximum_pickup_distance` ichidagi driverlar ko'rib chiqiladi

### **Push Notifications**

- **Order yaratilganda:** Eng yaqin driverga push notification yuboriladi
- **Driver accept qilganda:** Riderga push notification yuboriladi ("Driver found")
- **Driver reject qilganda:** Keyingi driverga push notification yuboriladi
- **Timeout bo'lganda:** Keyingi driverga push notification yuboriladi
- `UserDeviceToken` modeli orqali boshqariladi
- Firebase FCM orqali yuboriladi

### **Error Handling**

- Agar driver lokatsiya yubormasa → orderlarga assign qilinmaydi
- Agar order allaqachon `confirmed` bo'lsa → boshqa driverlarga yuborilmaydi
- Agar driver reject qilsa → Order keyingi eng yaqin driverga yuboriladi (oldingi driver exclude qilingan)
- Agar timeout bo'lsa → Order keyingi eng yaqin driverga yuboriladi (oldingi driver exclude qilingan, `OrderDriver.status = timeout` saqlanadi)
- **Oldingi driver yana ko'rmaydi** - chunki `OrderDriver` modelida `status = timeout` yoki `status = rejected` saqlanadi va `exclude_driver_ids` ga qo'shiladi
- Agar barcha driverlar reject qilsa yoki timeout bo'lsa → Order `pending` qoladi

### **Uber Modeli Xususiyatlari**

- **Bir vaqtda bir driverga yuboriladi** - barcha driverlar bir xil orderni ko'rmaydi
- **25 soniya timeout** - agar driver javob bermasa, keyingi driverga yuboriladi
- **Avtomatik reassignment** - reject yoki timeout bo'lsa, keyingi eng yaqin driverga yuboriladi
- **Push notification** - har bir yangi assignment'da driverga push notification yuboriladi
- **Radius-based search** - avval yaqin (5km), keyin uzoq (10km, 15km, 20km)
- **Waiting time** - har bir radius o'rtasida 10 soniya kutadi (driverlar bo'sh bo'lishi mumkin)
- **Bo'sh driverlar** - active order yo'q driverlarga yuboriladi
- **Destination-based matching (Uber-style)** - agar driver'ning hozirgi order'ining destination'i yangi order'ning pickup'iga yaqin bo'lsa (3 km radius ichida), u driverga ham yuboriladi. Bu driver birinchi order'ni tushirib, keyin yangi order'ni olishga boradi

---

## 📱 RIDER UCHUN API LAR

### **1. Order Yaratish**

**API:** `POST /api/v1/order/create/`

**Description:** Yangi order yaratadi. Order yaratilganda avtomatik eng yaqin driverga yuboriladi va push notification yuboriladi.

**Request:**
```json
{
  "address_from": "Toshkent, Chilonzor",
  "address_to": "Toshkent, Yunusobod",
  "latitude_from": 41.311081,
  "longitude_from": 69.240562,
  "latitude_to": 41.325000,
  "longitude_to": 69.300000,
  "order_type": 1  // 1 = PICKUP, 2 = FOR_ME
}
```

**Response:**
```json
{
  "message": "Order created successfully",
  "status": "success",
  "data": {
    "id": 123,
    "order_code": "ORD-000123",
    "status": "pending",
    "order_type": "pickup",
    "order_items": [...]
  }
}
```

---

### **2. Ride Type Tanlash**

**API:** `PUT /api/v1/order/order-item/{order_item_id}/update/`

**Description:** Order item uchun ride type tanlash va narx hisoblash.

**Request:**
```json
{
  "ride_type_id": 1  // 1 = Hola (Standard), 2 = Premium, 3 = Eco
}
```

**Response:**
```json
{
  "message": "Order item updated successfully",
  "status": "success",
  "data": {
    "id": 456,
    "ride_type": 1,
    "ride_type_name": "Hola",
    "calculated_price": 15000.00,
    "distance_km": 5.2,
    "estimated_time": "15 min"
  }
}
```

---

### **3. Orderlar Ro'yxatini Ko'rish**

**API:** `GET /api/v1/order/my-orders/`

**Description:** Foydalanuvchining barcha orderlarini ko'rish. Status va order_type bo'yicha filtrlash mumkin.

**Query Parameters:**
- `status` (optional): `pending`, `confirmed`, `completed`, `cancelled`
- `order_type` (optional): `pickup`, `for_me`
- `page` (optional): Sahifa raqami
- `page_size` (optional): Har bir sahifadagi elementlar soni

**Request:**
```
GET /api/v1/order/my-orders/?status=confirmed&page=1&page_size=10
Authorization: Bearer <rider_token>
```

**Response:**
```json
{
  "message": "Orders retrieved successfully",
  "status": "success",
  "count": 5,
  "next": "http://api.example.com/api/v1/order/my-orders/?page=2",
  "previous": null,
  "data": [
    {
      "id": 123,
      "order_code": "ORD-000123",
      "status": "confirmed",
      "order_type": "pickup",
      "order_items": [...],
      "created_at": "2025-01-01T12:00:00Z"
    }
  ]
}
```

---

### **4. Driver Lokatsiyasini Kuzatish (Real-Time Tracking)**

**API:** `GET /api/v1/order/{order_id}/driver/location/`

**Description:** Driver lokatsiyasini ko'rish. Driver accept qilgandan keyin ishlatiladi. Har 3-5 soniyada polling qilish kerak.

**Request:**
```
GET /api/v1/order/123/driver/location/
Authorization: Bearer <rider_token>
```

**Response:**
```json
{
  "message": "Driver location retrieved successfully",
  "status": "success",
  "data": {
    "driver_id": 45,
    "latitude": 41.310500,
    "longitude": 69.240500,
    "updated_at": "2025-01-01T12:01:00Z"
  }
}
```

**Eslatma:** Faqat `confirmed` statusdagi orderlar uchun ishlaydi.

---

### **5. Order Bekor Qilish**

**API:** `POST /api/v1/order/{order_id}/cancel/`

**Description:** Order bekor qilish. Faqat `pending` yoki `confirmed` statusdagi orderlarni bekor qilish mumkin.

**Request:**
```json
{
  "reason": "change_in_plans",  // yoki boshqa sabab
  "other_reason": "Plans o'zgardi"  // reason = "other" bo'lsa majburiy
}
```

**Available Reasons:**
- `change_in_plans` - Rejalar o'zgardi
- `waiting_for_long_time` - Uzoq kutish
- `driver_denied_to_go_to_destination` - Driver manzilga bormaslikni rad etdi
- `driver_denied_to_come_to_pickup` - Driver pickup ga kelmaslikni rad etdi
- `wrong_address_shown` - Noto'g'ri manzil ko'rsatilgan
- `the_price_is_not_reasonable` - Narx noto'g'ri
- `emergency_situation` - Favqulodda holat
- `other` - Boshqa (other_reason majburiy)

**Response:**
```json
{
  "message": "Order cancelled successfully",
  "status": "success",
  "data": {
    "id": 123,
    "order_code": "ORD-000123",
    "status": "cancelled",
    "cancel_orders": [...]
  }
}
```

---

### **6. Narxni Taxmin Qilish**

**API:** `POST /api/v1/order/price-estimate/`

**Description:** Barcha ride type lar uchun narxni taxmin qilish (order yaratishdan oldin).

**Request:**
```json
{
  "latitude_from": 41.311081,
  "longitude_from": 69.240562,
  "latitude_to": 41.325000,
  "longitude_to": 69.300000
}
```

**Response:**
```json
{
  "message": "Price estimates retrieved successfully",
  "status": "success",
  "data": {
    "distance_km": 5.2,
    "surge_multiplier": 1.0,
    "estimates": [
      {
        "ride_type_id": 1,
        "ride_type_name": "Hola",
        "estimated_price": 15000.00,
        "base_price": 5000.00,
        "price_per_km": 2000.00
      },
      {
        "ride_type_id": 2,
        "ride_type_name": "Premium",
        "estimated_price": 25000.00,
        "base_price": 10000.00,
        "price_per_km": 3000.00
      }
    ]
  }
}
```

---

## 🚗 DRIVER UCHUN API LAR

### **1. Lokatsiya Yangilash**

**API:** `POST /api/v1/order/driver/location/update/`

**Description:** Driver GPS lokatsiyasini yangilash. App ochilganda va har 5-10 soniyada chaqirish kerak.

**Request:**
```json
{
  "latitude": 41.310000,
  "longitude": 69.240000
}
```

**Response:**
```json
{
  "message": "Location updated successfully",
  "status": "success",
  "data": {
    "driver_id": 45,
    "latitude": 41.310000,
    "longitude": 69.240000,
    "updated_at": "2025-01-01T12:00:00Z"
  }
}
```

**Muhim:** Agar lokatsiya yangilanmasa, orderlarga assign qilinmaydi.

---

### **2. O'ziga Yuborilgan Orderlarni Ko'rish**

**API:** `GET /api/v1/order/driver/nearby-orders/`

**Description:** O'ziga `requested` statusdagi orderlarni ko'rish. Faqat shu driverga yuborilgan orderlar ko'rinadi.

**Request:**
```
GET /api/v1/order/driver/nearby-orders/
Authorization: Bearer <driver_token>
```

**Response:**
```json
{
  "message": "Assigned orders retrieved successfully",
  "status": "success",
  "data": [
    {
      "id": 123,
      "order_code": "ORD-000123",
      "status": "pending",
      "address_from": "Toshkent, Chilonzor",
      "address_to": "Toshkent, Yunusobod",
      "latitude_from": 41.311081,
      "longitude_from": 69.240562,
      "latitude_to": 41.325000,
      "longitude_to": 69.300000,
      "distance_to_pickup_km": 2.35,
      "ride_type_name": "Hola",
      "calculated_price": 15000.00,
      "time_remaining_seconds": 15  // 25 soniyadan qolgan vaqt
    }
  ]
}
```

**Muhim:** 
- Faqat o'ziga `requested` statusdagi orderlar ko'rinadi
- Timeout tekshiriladi (25 soniya)
- Agar timeout bo'lsa, order keyingi driverga yuboriladi

---

### **3. Order Accept/Reject Qilish**

**API:** `POST /api/v1/order/driver/order-action/`

**Description:** Order accept yoki reject qilish. Faqat o'ziga `requested` statusdagi orderlarni accept/reject qilish mumkin. 25 soniya ichida javob berish kerak.

**Request:**
```json
{
  "order_id": 123,
  "action": "accept"  // yoki "reject"
}
```

**Response (Accept):**
```json
{
  "message": "Order accepted successfully",
  "status": "success"
}
```

**Response (Reject):**
```json
{
  "message": "Order rejected. Reassigned to next driver.",
  "status": "success"
}
```

**Nima bo'ladi:**
- **Accept:** Order driverga assign qilinadi, `Order.status = confirmed`, riderga push notification
- **Reject:** Order keyingi eng yaqin driverga yuboriladi (avtomatik)
- **Timeout (25 soniya):** Order keyingi eng yaqin driverga yuboriladi (avtomatik)

---

### **4. O'z Orderlarini Ko'rish**

**API:** `GET /api/v1/order/my-orders/`

**Description:** Driverning barcha orderlarini ko'rish. Status bo'yicha filtrlash mumkin.

**Query Parameters:**
- `status` (optional): `pending`, `confirmed`, `completed`, `cancelled`
- `page` (optional): Sahifa raqami
- `page_size` (optional): Har bir sahifadagi elementlar soni

**Request:**
```
GET /api/v1/order/my-orders/?status=confirmed&page=1&page_size=10
Authorization: Bearer <driver_token>
```

**Response:**
```json
{
  "message": "Orders retrieved successfully",
  "status": "success",
  "count": 3,
  "next": null,
  "previous": null,
  "data": [
    {
      "id": 123,
      "order_code": "ORD-000123",
      "status": "confirmed",
      "order_type": "pickup",
      "order_items": [...],
      "order_drivers": [
        {
          "driver": 45,
          "status": "accepted",
          "requested_at": "2025-01-01T12:00:00Z",
          "responded_at": "2025-01-01T12:00:15Z"
        }
      ],
      "created_at": "2025-01-01T12:00:00Z"
    }
  ]
}
```

---

## 📊 API LAR JADVALI

| API | Method | Rider | Driver | Description |
|-----|--------|-------|--------|-------------|
| `/order/create/` | POST | ✅ | ❌ | Order yaratish |
| `/order/order-item/{id}/update/` | PUT | ✅ | ❌ | Ride type tanlash |
| `/order/my-orders/` | GET | ✅ | ✅ | Orderlar ro'yxati |
| `/order/{id}/driver/location/` | GET | ✅ | ❌ | Driver lokatsiyasi |
| `/order/{id}/cancel/` | POST | ✅ | ❌ | Order bekor qilish |
| `/order/price-estimate/` | POST | ✅ | ❌ | Narxni taxmin qilish |
| `/order/driver/location/update/` | POST | ❌ | ✅ | Driver lokatsiyasini yangilash |
| `/order/driver/nearby-orders/` | GET | ❌ | ✅ | O'ziga yuborilgan orderlar |
| `/order/driver/order-action/` | POST | ❌ | ✅ | Accept/Reject qilish |

---

---

## ⚙️ CELERY SETUP VA RUN QILISH

### **Celery Nima?**

Celery - Django uchun background task processing kutubxonasi. Bizda **avtomatik timeout tekshirish** uchun ishlatiladi.

### **Qanday Ishlaydi?**

1. **Celery Worker** - background tasklarni bajaradi
2. **Celery Beat** - periodic tasklarni (har 5 soniyada) chaqiradi
3. **Redis** - message broker (tasklar uchun queue)

### **Setup Qilish**

#### 1. Redis O'rnatish

**Windows:**
```bash
# Redis Windows versiyasini yuklab oling:
# https://github.com/microsoftarchive/redis/releases
# yoki WSL2 orqali:
wsl --install
# WSL2 ichida:
sudo apt-get update
sudo apt-get install redis-server
redis-server
```

**Linux/Mac:**
```bash
sudo apt-get install redis-server  # Ubuntu/Debian
brew install redis  # Mac
redis-server
```

#### 2. Python Paketlarini O'rnatish

```bash
pip install celery redis
```

#### 3. Environment Variables (.env)

```env
# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### **Run Qilish**

#### 1. Redis Ishga Tushirish

```bash
# Terminal 1: Redis server
redis-server
```

#### 2. Django Server Ishga Tushirish

```bash
# Terminal 2: Django development server
python manage.py runserver
```

#### 3. Celery Worker Ishga Tushirish

```bash
# Terminal 3: Celery worker
celery -A config worker --loglevel=info
```

#### 4. Celery Beat Ishga Tushirish

```bash
# Terminal 4: Celery beat (periodic tasks)
celery -A config beat --loglevel=info
```

### **Production (Linux/Server)**

#### Systemd Service (Tavsiya etiladi)

**1. Celery Worker Service:**

`/etc/systemd/system/celery-worker.service`:
```ini
[Unit]
Description=Celery Worker for HolaDrive
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/var/www/HolaDrive
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/celery -A config worker --loglevel=info --logfile=/var/log/celery/worker.log --pidfile=/var/run/celery/worker.pid
ExecStop=/bin/kill -s TERM $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

**2. Celery Beat Service:**

`/etc/systemd/system/celery-beat.service`:
```ini
[Unit]
Description=Celery Beat for HolaDrive
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/path/to/HolaDrive
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/celery -A config beat --loglevel=info --logfile=/var/log/celery/beat.log --pidfile=/var/run/celery/beat.pid
ExecStop=/bin/kill -s TERM $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

**3. Service'larni Ishga Tushirish:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable celery-worker
sudo systemctl enable celery-beat
sudo systemctl start celery-worker
sudo systemctl start celery-beat

# Status tekshirish:
sudo systemctl status celery-worker
sudo systemctl status celery-beat
```

### **Celery Task Qanday Ishlaydi?**

**Task:** `apps.order.tasks.check_order_timeouts`

**Schedule:** Har 5 soniyada

**Nima qiladi:**
1. Barcha `status = requested` bo'lgan `OrderDriver` larni topadi
2. Har birining `requested_at` vaqtini tekshiradi
3. Agar 25 soniya o'tgan bo'lsa:
   - `OrderDriver.status = timeout` ga o'zgartiradi
   - Keyingi eng yaqin driverni topadi
   - Yangi `OrderDriver` yaratadi (`status = requested`)
   - Push notification yuboradi

**Loglar:**
- Celery worker loglari: `celery -A config worker --loglevel=info`
- Celery beat loglari: `celery -A config beat --loglevel=info`
- Django loglari: `logs/django.log`

### **Troubleshooting**

**1. Redis ishlamayapti:**
```bash
# Redis status tekshirish:
redis-cli ping
# "PONG" javob qaytishi kerak
```

**2. Celery worker ishlamayapti:**
```bash
# Task'larni ko'rish:
celery -A config inspect active
celery -A config inspect scheduled
```

**3. Celery beat ishlamayapti:**
```bash
# Beat schedule tekshirish:
celery -A config beat --loglevel=debug
```

**4. Task ishlamayapti:**
```bash
# Task'ni qo'lda chaqirish:
python manage.py shell
>>> from apps.order.tasks import check_order_timeouts
>>> check_order_timeouts()
```

---

---

## 🎯 DESTINATION-BASED MATCHING (Uber-Style)

### **Nima Bu?**

Uber'da order yaratilganda, agar driver'ning hozirgi order'ining **destination'i** (B nuqtasi) yangi order'ning **pickup'iga** (A nuqtasi) yaqin bo'lsa, u driverga ham yuboriladi. Bu driver birinchi order'ni tushirib, keyin yangi order'ni olishga boradi.

### **Qanday Ishlaydi?**

1. **Order yaratilganda:**
   - Backend avval **bo'sh driverlarni** qidiradi (active order yo'q)
   - Keyin **active order bor driverlarni** tekshiradi:
     - Driver'ning hozirgi order'ining **destination'i** (final stop) olinadi
     - Yangi order'ning **pickup'i** bilan masofa hisoblanadi
     - Agar masofa **3 km dan kam** bo'lsa → Driver ga yuboriladi

2. **Misol:**
   ```
   Driver #1 hozir Order #100 ni olgan:
   - Pickup: Chilonzor (A nuqtasi)
   - Destination: Yunusobod (B nuqtasi)
   
   Yangi Order #123 yaratiladi:
   - Pickup: Yunusobod (A nuqtasi) - Driver #1'ning destination'iga yaqin!
   - Destination: Sergeli
   
   Backend tekshiradi:
   - Driver #1'ning destination'i (Yunusobod) → yangi pickup (Yunusobod) = 2.5 km
   - 2.5 km < 3 km → Driver #1 ga yuboriladi!
   
   Driver #1:
   - Birinchi order'ni (Order #100) tushirib beradi
   - Keyin yangi order'ni (Order #123) olishga boradi
   ```

3. **Foyda:**
   - Driverlar ko'proq order olishadi
   - Riderlar tezroq driver topadi
   - Driverlar bo'sh qolmaydi (destination'ga yetib borgandan keyin darhol yangi order)

### **Texnik Detallar**

- **Max distance:** 3 km (driver'ning destination'idan yangi pickup'gacha)
- **Qanday tekshiriladi:**
  - Driver'ning active order'ining `is_final_stop=True` bo'lgan `OrderItem` olinadi
  - Uning `latitude_to` va `longitude_to` yangi order'ning `latitude_from` va `longitude_from` bilan solishtiriladi
  - Haversine formula orqali masofa hisoblanadi
  - Agar masofa ≤ 3 km → Driver available (destination matching)

### **Scenario: Destination-Based Matching**

1. **Driver #1 active order olgan:**
   ```
   Order #100:
   - Pickup: Chilonzor (41.311081, 69.240562)
   - Destination: Yunusobod (41.325000, 69.300000)
   - Status: confirmed (driver accept qilgan)
   ```

2. **Yangi Order #123 yaratiladi:**
   ```
   Order #123:
   - Pickup: Yunusobod (41.325000, 69.300000) - Driver #1'ning destination'iga yaqin!
   - Destination: Sergeli
   ```

3. **Backend tekshiradi:**
   ```
   Driver #1'ning destination'i (Yunusobod) → yangi pickup (Yunusobod) = 2.5 km
   2.5 km < 3 km → Driver #1 ga yuboriladi!
   → OrderDriver yaratiladi (order=123, driver=Driver#1, status=requested)
   → Driver #1 ga push notification: "New ride request available nearby"
   ```

4. **Driver #1 accept qiladi:**
   ```
   Driver #1:
   - Birinchi order'ni (Order #100) tushirib beradi
   - Keyin yangi order'ni (Order #123) olishga boradi
   ```

---

**Frontend jamoa uchun:** Bu hujjatda barcha API lar va ularning ketma-ketligi tushuntirilgan. Har bir bosqichda qaysi API chaqirilishini aniq ko'rsatilgan. **Uber modeli** ishlatilgani uchun, order yaratilganda avtomatik eng yaqin driverga yuboriladi va driver 25 soniya ichida javob berishi kerak. **Celery** orqali timeout avtomatik tekshiriladi va keyingi driverga yuboriladi. **Destination-based matching** orqali active order bor driverlar ham yangi orderlarga yuboriladi, agar ularning destination'i yangi pickup'ga yaqin bo'lsa (Uber-style).
