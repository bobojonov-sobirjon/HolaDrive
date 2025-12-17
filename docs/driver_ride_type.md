## Driver Ride Types (HolaDrive)

Bu hujjat **frontend** jamoa uchun mo‘ljallangan. Unda haydovchi mashinasiga bog‘liq **ride type** (Standard/Hola, Premium, Eco va h.k.) qanday ishlashi tushuntiriladi.

---

## 1. Asosiy tushuncha

Backend’da haydovchining mashinasi `VehicleDetails` modeli orqali saqlanadi va har bir mashina bir nechta ride type’ni qo‘llab-quvvatlashi mumkin:

- **Standard (Hola)** – barcha mashinalar uchun mavjud (asosiy servis).
- **Premium** – premium brandlar yoki yangi va a’lo holatdagi mashinalar.
- **Eco** – elektr yoki hybrid mashinalar.

Ride type’lar o‘zi `RideType` modelida saqlanadi (masalan: `id=1 → Hola`, `id=2 → Premium`, `id=3 → Eco`).

---

## 2. Mashina yaratish (POST `/accounts/vehicle/`)

**Endpoint**:  
`POST /api/v1/accounts/vehicle/`

**Auth**: JWT, **Role**: Driver  
**Request format**: `multipart/form-data`

### 2.1. Majburiy fieldlar

- `brand` (string)  
  Masalan: `"Toyota"`, `"Tesla"`, `"BMW"`.

- `model` (string)  
  Masalan: `"Camry"`, `"Model 3"`, `"5 Series"`.

- `year_of_manufacture` (integer)  
  2015 yoki undan yangi. Masalan: `2024`.

- `vin` (string)  
  8–17 belgili noyob VIN. Masalan: `"24785499ABCDEF123"`.

### 2.2. Ixtiyoriy fieldlar (ride type bilan bog‘liq)

- `vehicle_condition` (string, enum)  
  Qiymatlar: `"excellent"`, `"good"`, `"fair"`  
  Default: `"good"`  
  Bu qiymat **Premium** recommendation’ga ta’sir qiladi (pastda tushuntirilgan).

- `default_ride_type` (integer, optional)  
  Mashina uchun asosiy ride type ID. Agar yuborilmasa, backend avtomatik ravishda birinchi taklif qilingan ride type’ni default qilib qo‘yadi.

- `supported_ride_types` (array of integer, optional)  
  Ushbu mashina qo‘llab-quvvatlaydigan ride type ID’lar ro‘yxati.

  Misollar:
  - `[1]` → faqat Standard (Hola)
  - `[1, 2]` → Standard + Premium
  - `[1, 2, 3]` → Standard + Premium + Eco

  Agar **umuman yuborilmasa yoki bo‘sh array bo‘lsa**, backend avtomatik ravishda mashina xususiyatlariga qarab to‘ldiradi (qarang: 2.3).

- `images_data` (array of file, optional)  
  Mashina rasmlari (bir nechta rasm).

### 2.3. Avtomatik ride type suggestion logikasi

Agar frontend `supported_ride_types` yubormasa yoki bo‘sh yuborsa, backend `suggest_ride_types()` orqali ride type’larni **o‘zi tanlaydi**:

1. **Standard (Hola)**  
   - Har doim qo‘shiladi (agar aktiv bo‘lsa).

2. **Premium** – quyidagi holatlardan biri bo‘lsa:
   - Brand premium bo‘lsa:
     - `"mercedes"`, `"mercedes-benz"`, `"bmw"`, `"audi"`, `"lexus"`, `"porsche"`,  
       `"tesla"`, `"jaguar"`, `"land rover"`, `"range rover"`, `"bentley"`,  
       `"rolls-royce"`, `"maserati"`, `"ferrari"`, `"lamborghini"`, `"mclaren"` va h.k.
   - Yoki quyidagilar birga bo‘lsa:
     - `year_of_manufacture >= 2020`
     - `vehicle_condition == "excellent"`

3. **Eco** – mashina elektr/hybrid bo‘lsa:
   - `brand + model` satrida quyidagi so‘zlar bo‘lsa:
     - `"tesla"`, `"nissan leaf"`, `"bmw i"`, `"audi e"`, `"hyundai ioniq"`,  
       `"kia ev"`, `"volkswagen id"`, `"electric"`, `"ev"`, `"hybrid"`,  
       `"prius"`, `"bolt"`, `"volt"`, `"model 3"`, `"model s"`, `"model x"`, `"model y"`.

4. Agar nimadir sabab bo‘lib bironta suggestion chiqmasa, kamida **Standard (Hola)** qo‘shiladi.

Backend natijada:

- `supported_ride_types` ni shu ro‘yxat bilan to‘ldiradi.
- Agar `default_ride_type` berilmagan bo‘lsa – **birinchi suggested type** (odatda Hola) ni default qilib qo‘yadi.

### 2.4. Request misollari

**Misol 1 – Tesla Model 3, hammasi avtomatik (Premium + Eco chiqadi):**

```json
{
  "brand": "Tesla",
  "model": "Model 3",
  "year_of_manufacture": 2023,
  "vin": "ABC123",
  "vehicle_condition": "excellent"
  // supported_ride_types yuborilmagan → backend: [Hola, Premium, Eco]
}
```

**Misol 2 – Toyota Camry, faqat Standard (qo‘lda):**

```json
{
  "brand": "Toyota",
  "model": "Camry",
  "year_of_manufacture": 2018,
  "vin": "XYZ789",
  "vehicle_condition": "good",
  "supported_ride_types": [1]  // faqat Standard (Hola)
}
```

**Misol 3 – BMW 5 Series, Standard + Premium (qo‘lda):**

```json
{
  "brand": "BMW",
  "model": "5 Series",
  "year_of_manufacture": 2022,
  "vin": "BMW123",
  "vehicle_condition": "excellent",
  "default_ride_type": 2,      // masalan Premium ID
  "supported_ride_types": [1, 2] // Standard + Premium
}
```

---

## 3. Mashinani yangilash (PUT `/accounts/vehicle/{id}/`)

**Endpoint**:  
`PUT /api/v1/accounts/vehicle/{id}/`

**Auth**: JWT, **Role**: Driver  
**Request format**: `multipart/form-data`  
Barcha fieldlar **ixtiyoriy** (partial update).

Yuborilishi mumkin bo‘lgan fieldlar:

- `brand`, `model`, `year_of_manufacture`, `vin`
- `vehicle_condition`
- `default_ride_type`
- `supported_ride_types`
- `images_data` (faqat yangi rasmlar qo‘shish; eski rasmlar o‘chirilmaydi)

### 3.1. `supported_ride_types` update qilinganda

- Agar **`supported_ride_types` umuman yuborilmasa** – mavjud ro‘yxat o‘zgarmaydi.
- Agar **`supported_ride_types` = [1, 2]** bo‘lsa:
  - Mashinaning butun ride type ro‘yxati `[1, 2]` ga **almashtiriladi**.
- Agar **`supported_ride_types` = []** (bo‘sh array) bo‘lsa:
  - Mashinaning ride type ro‘yxati tozalanadi.
  - Keyingi `save()` chaqirilganda backend yana avtomatik **suggestion** qilib to‘ldiradi (brand/year/condition/electric bo‘yicha).

Frontend agar "reset to auto" qilishni xohlasa, **bo‘sh array** yuborishi mumkin:

```json
{
  "supported_ride_types": []
}
```

---

## 4. Response struktura (VehicleDetails)

Backend javobi `VehicleDetailsSerializer` orqali qaytadi, muhim fieldlar:

- `vehicle_condition` – `"excellent" | "good" | "fair"`.
- `default_ride_type` – ID.
- `default_ride_type_name` – nomi (masalan: `"Hola"`).
- `default_ride_type_id` – ID (xuddi `default_ride_type`, lekin aniq int).
- `supported_ride_types` – ID’lar ro‘yxati (masalan: `[1,2,3]`).
- `supported_ride_types_names` – nomlar ro‘yxati (masalan: `["Hola", "Premium", "Eco"]`).
- `suggested_ride_types` – **read-only** (faqat ko‘rsatish uchun):
  - `id`
  - `name`
  - `reason` – nima uchun shu ride type taklif qilingan (masalan: `"Electric vehicle detected"`, `"Premium brand vehicle"`, `"Standard vehicle category"`).

Frontend:

- Agar UI’da haydovchiga ride type’larni tanlatmoqchi bo‘lsa:
  - `supported_ride_types` / `supported_ride_types_names` – hozirgi tanlanganlari.
  - `suggested_ride_types` – tavsiya qilinganlari + sabablar (tooltip yoki info text sifatida).

---

## 5. Frontend uchun tavsiyalar

- **Create (POST):**
  - Minimal variant: faqat `brand`, `model`, `year_of_manufacture`, `vin`, (ixtiyoriy `vehicle_condition`) yuboring – qolganini backend o‘zi hal qiladi.
  - Agar haydovchi qo‘lda tanlashi kerak bo‘lsa – UI’da ride type listini ko‘rsatib, tanlangan ID’larni `supported_ride_types` sifatida yuboring.

- **Update (PUT):**
  - Faqat o‘zgargan fieldlarni yuboring (masalan, faqat `supported_ride_types`).
  - “Avtomatik tavsiyaga qaytarish” knopkasi kerak bo‘lsa:
    - `supported_ride_types: []` yuboring → backend qayta auto-suggest qiladi.

Bu hujjatni frontend jamoaga to‘g‘ridan-to‘g‘ri berishingiz mumkin – unda API forma, fieldlar, misollar va auto-suggestion logikasi to‘liq tushuntirilgan.


