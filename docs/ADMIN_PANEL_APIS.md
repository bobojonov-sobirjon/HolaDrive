## Admin Panel APIs (HolaDrive) — Orders module (16 sections)

All endpoints below are under:

- **Base**: `/api/v1/admin-panel/`
- **Auth**: `Authorization: Bearer <admin_access_token>`
- **Permission**: **superuser only** (otherwise 403)

Response envelope (most endpoints):

- **list**: `{ message, status, count, data: [] }`
- **detail/create/update**: `{ message, status, data: {} }`
- **delete**: `{ message, status }`

---

## 01 Orders

- **GET** `orders/` — list of orders **using the same serializer as detail** (full data).
- **GET** `orders/{order_id}/` — order detail (full data).

**Returned data**: uses existing `OrderDetailSerializer` from `apps/order/serializers/order.py` (includes nested order_items, preferences, passengers, schedules, drivers, cancel_orders, payment_splits, etc).

> Note: this admin module currently implements GET only for Orders (no create/update/delete here).

---

## 02 Ride Types (CRUD) — Swagger tag: **Admin Ride Types**

- **GET** `ride-types/`
- **POST** `ride-types/`
- **GET** `ride-types/{ride_type_id}/`
- **PATCH** `ride-types/{ride_type_id}/`
- **DELETE** `ride-types/{ride_type_id}/`

**Body (POST/PATCH)**: JSON, model fields (e.g. `name`, `name_large`, `base_price`, `price_per_km`, `capacity`, `icon`, `is_premium`, `is_ev`, `is_active`).

---

## 03 Order Items (CRUD)

- **GET** `order-items/`
- **POST** `order-items/`
- **GET** `order-items/{order_item_id}/`
- **PATCH** `order-items/{order_item_id}/`
- **DELETE** `order-items/{order_item_id}/`

**Body (POST/PATCH)**: JSON, `OrderItem` model fields (`order`, addresses, coords, ride_type, distance_km, prices, etc).

---

## 04 Additional Passengers (CRUD)

- **GET** `additional-passengers/`
- **POST** `additional-passengers/`
- **GET** `additional-passengers/{additional_passenger_id}/`
- **PATCH** `additional-passengers/{additional_passenger_id}/`
- **DELETE** `additional-passengers/{additional_passenger_id}/`

**Body (POST/PATCH)**: JSON, `AdditionalPassenger` model fields (`order`, `full_name`, `phone_number`, `email`).

---

## 05 Order Preferences (CRUD)

- **GET** `order-preferences/`
- **POST** `order-preferences/`
- **GET** `order-preferences/{order_preferences_id}/`
- **PATCH** `order-preferences/{order_preferences_id}/`
- **DELETE** `order-preferences/{order_preferences_id}/`

**Body (POST/PATCH)**: JSON, `OrderPreferences` model fields (`order`, chatting/music/temp preferences, etc).

---

## 06 Order Drivers (CRUD)

- **GET** `order-drivers/`
- **POST** `order-drivers/`
- **GET** `order-drivers/{order_driver_id}/`
- **PATCH** `order-drivers/{order_driver_id}/`
- **DELETE** `order-drivers/{order_driver_id}/`

**Body (POST/PATCH)**: JSON, `OrderDriver` model fields (`order`, `driver`, `status`, timestamps, etc).

---

## 07 Surge Pricings (CRUD) — traffic multiplier

- **GET** `surge-pricings/`
- **POST** `surge-pricings/`
- **GET** `surge-pricings/{surge_pricing_id}/`
- **PATCH** `surge-pricings/{surge_pricing_id}/`
- **DELETE** `surge-pricings/{surge_pricing_id}/`

**Body (POST/PATCH)**: JSON, `SurgePricing` model fields (`name`, `multiplier`, time window, days_of_week, zone/radius, driver thresholds, `priority`, `is_active`).

---

## 08 Cancel Orders (CRUD)

- **GET** `cancel-orders/`
- **POST** `cancel-orders/`
- **GET** `cancel-orders/{cancel_order_id}/`
- **PATCH** `cancel-orders/{cancel_order_id}/`
- **DELETE** `cancel-orders/{cancel_order_id}/`

**Body (POST/PATCH)**: JSON, `CancelOrder` model fields (`order`, `driver`, `cancelled_by`, `reason`, `other_reason`).

---

## 09 Order Payment Status (CRUD) — Payment splits

- **GET** `order-payment-status/`
- **POST** `order-payment-status/`
- **GET** `order-payment-status/{payment_split_id}/`
- **PATCH** `order-payment-status/{payment_split_id}/`
- **DELETE** `order-payment-status/{payment_split_id}/`

**Body (POST/PATCH)**: JSON, `OrderPaymentSplit` model fields (`order`, `user`, `split_type`, `amount`, `percentage`, `payment_status`, etc).

---

## 10 Promo Codes (CRUD)

- **GET** `promo-codes/`
- **POST** `promo-codes/`
- **GET** `promo-codes/{promo_code_id}/`
- **PATCH** `promo-codes/{promo_code_id}/`
- **DELETE** `promo-codes/{promo_code_id}/`

**Body (POST/PATCH)**: JSON, `PromoCode` model fields (`code`, `discount_type`, `discount_value`, `user`, `max_uses`, `is_active`, `valid_from`, `valid_until`, etc).

---

## 11 Order Promo Codes (CRUD)

- **GET** `order-promo-codes/`
- **POST** `order-promo-codes/`
- **GET** `order-promo-codes/{order_promo_code_id}/`
- **PATCH** `order-promo-codes/{order_promo_code_id}/`
- **DELETE** `order-promo-codes/{order_promo_code_id}/`

**Body (POST/PATCH)**: JSON, `OrderPromoCode` model fields (order + promo_code linkage fields).

---

## 12 Rating Feedback (CRUD)

- **GET** `rating-feedback/`
- **POST** `rating-feedback/`
- **GET** `rating-feedback/{rating_feedback_tag_id}/`
- **PATCH** `rating-feedback/{rating_feedback_tag_id}/`
- **DELETE** `rating-feedback/{rating_feedback_tag_id}/`

**Body (POST/PATCH)**: JSON, `RatingFeedbackTag` fields.

---

## 13 Trip Ratings (CRUD)

- **GET** `trip-ratings/`
- **POST** `trip-ratings/`
- **GET** `trip-ratings/{trip_rating_id}/`
- **PATCH** `trip-ratings/{trip_rating_id}/`
- **DELETE** `trip-ratings/{trip_rating_id}/`

**Body (POST/PATCH)**: JSON, `TripRating` fields.

---

## 14 Driver Rider Ratings (CRUD)

- **GET** `driver-rider-ratings/`
- **POST** `driver-rider-ratings/`
- **GET** `driver-rider-ratings/{driver_rider_rating_id}/`
- **PATCH** `driver-rider-ratings/{driver_rider_rating_id}/`
- **DELETE** `driver-rider-ratings/{driver_rider_rating_id}/`

**Body (POST/PATCH)**: JSON, `DriverRiderRating` fields.

---

## 15 Driver Cashouts (CRUD)

- **GET** `driver-cashouts/`
- **POST** `driver-cashouts/`
- **GET** `driver-cashouts/{driver_cashout_id}/`
- **PATCH** `driver-cashouts/{driver_cashout_id}/`
- **DELETE** `driver-cashouts/{driver_cashout_id}/`

**Body (POST/PATCH)**: JSON, `DriverCashout` fields.

---

## 16 Order preferences Admin (CRUD) — User templates

- **GET** `order-preferences-admin/`
- **POST** `order-preferences-admin/`
- **GET** `order-preferences-admin/{user_order_preferences_id}/`
- **PATCH** `order-preferences-admin/{user_order_preferences_id}/`
- **DELETE** `order-preferences-admin/{user_order_preferences_id}/`

**Body (POST/PATCH)**: JSON, `UserOrderPreferences` fields.

