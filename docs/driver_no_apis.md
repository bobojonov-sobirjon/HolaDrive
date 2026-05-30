# Hola Driver — Missing & Partial APIs

This document lists **driver-facing features from Figma** that are **not implemented**, **partially implemented**, or **only available via WebSocket** (no REST). Use it for mobile/backend planning.

**Base URL:** `/api/v1/`  
**Auth:** JWT Bearer (Driver group) unless noted.

---

## Onboarding — first 5 screens

| # | Screen | Backend needed? | Status |
|---|--------|-----------------|--------|
| 1 | Splash | No | UI only |
| 2 | Welcome | No | UI only |
| 3 | Your Ride Preferences | Yes | **Partial** — see §3 |
| 4 | Track Your Earnings | Yes | **Partial** — see §4 |
| 5 | Powerful Tools (heatmap, dynamic radius) | Yes | **Partial** — see §5 |

---

## Not implemented (new work required)

### 1. Driver ride-type preferences

**Figma:** Screen 3 — choose which ride types to accept (Standard, XL, Comfort, etc.).

**Current:** `VehicleDetails.supported_ride_types` exists on the vehicle, but there is **no driver preference** for “which trip types I want to receive.”

**Suggested API:**

| Method | Path | Body / response |
|--------|------|-----------------|
| `GET` | `/accounts/driver/ride-type-preferences/` | List of `ride_type_id` + labels + `is_enabled` |
| `PATCH` | `/accounts/driver/ride-type-preferences/` | `{ "ride_type_ids": [1, 2, 3] }` |

**Notes:** Reuse `order.RideType` (active types). Optionally filter `driver/nearby-orders/` by these preferences.

---

### 2. Driver promotions / bonuses

**Figma:** Earnings dashboard — “Promotion” amount (e.g. $79.00).

**Current:** `GET /order/driver/dashboard/` returns `overview.promotion` **hardcoded to `0.0`** in `apps/order/services/driver_dashboard.py`.

**Suggested API:** Either:

- Implement promotion ledger (model + admin grants), and include real totals in dashboard/earnings, or  
- `GET /order/driver/promotions/` with period filter (`day`, `week`, `last_30`).

---

### 3. Stripe Instant Payout

**Figma:** Screen 4 — “Access instant payouts when you need them.”

**Current:**

- Internal wallet cash-out: `POST /order/driver/cashouts/` (admin approval flow).
- Stripe Connect: bank setup, balance, checkout history under `/payment/driver/...`.
- Payout schedule is weekly (env: `STRIPE_CONNECT_PAYOUT_*`), not instant.

**Missing:**

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/payment/driver/stripe-instant-payout/` | Trigger Stripe instant payout to default external account (if eligible) |

**Depends on:** Connect account `payouts_enabled`, available balance, Stripe instant payout availability per country.

---

### 4. Dynamic pickup radius

**Figma:** Screen 5 — “dynamic radius control” (auto-adjust based on demand).

**Current:** Static `maximum_pickup_distance` on `DriverPreferences` (`GET/PATCH /accounts/driver/preferences/`).

**Missing:** Algorithm + API to suggest or apply radius changes (e.g. expand in surge zones). No backend logic exists.

**Possible design:**

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/order/driver/suggested-pickup-radius/` | Returns recommended km from surge + driver location |
| Optional | Auto-update `maximum_pickup_distance` with driver opt-in flag |

---

### 5. Demand heatmap — REST

**Figma:** Screen 5 — heatmap on map.

**Current:** WebSocket only — `ws/driver/surge-zones/` (`DriverSurgeZonesConsumer`). Initial payload: `{ "type": "surge_zones", "zones": [...] }`. Client can send `{ "type": "refresh" }`.

**Missing (if mobile cannot use WS):**

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/order/driver/surge-zones/` | Same zone list as WS (lat/lon, multiplier, etc.) |

---

### 6. Veriff integration (profile photo)

**Figma:** Identification — profile photo verified by Veriff.

**Current:** File upload via identification upload flow; model help text mentions Veriff; **no Veriff session API, webhook, or status sync**.

**Missing:**

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/accounts/driver/veriff/session/` | Create Veriff session, return URL/token |
| `POST` | `/accounts/webhooks/veriff/` | Webhook → update upload/verification status |

---

### 7. Trip invoice / receipt (driver)

**Figma:** Ride invoice — fare, tip, tax, transaction ID, booking ID, “Share receipt”.

**Current:** `GET /order/<order_id>/` (driver access via `OrderDriver`) may expose order data, but **no dedicated invoice breakdown** endpoint.

**Suggested API:**

| Method | Path | Response |
|--------|------|----------|
| `GET` | `/order/driver/rides/<order_id>/invoice/` | `ride_fare`, `tip`, `tax`, `total`, `transaction_id`, `booking_id`, rider summary |

**Related (exists):** `GET /order/<order_id>/checkout-preview/` — fee preview before/at charge, not post-trip receipt.

---

### 8. Cities lookup

**Figma:** Edit profile — City dropdown (e.g. Montreal).

**Current:** `CustomUser.address` (text); **no cities list API**.

**Suggested API:**

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/accounts/metadata/cities/` | `[{ "id", "name", "region" }]` |

---

### 9. App info / About application

**Figma:** About — version, privacy, terms, community guidelines links.

**Current:** Terms/legal via driver identification and registration terms endpoints; **no single “app info” payload**.

**Suggested API:**

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/accounts/app-info/` | `version`, `privacy_url`, `terms_url`, `community_guidelines_url`, `support_email` (AllowAny or authenticated) |

---

### 10. Granular notification settings

**Figma:** Settings — many toggles (General, Safety, Ride status, Promo, Ratings, etc.).

**Current:** Single field `notification_intensity` (`minimal` | `moderate` | `high`) on `/accounts/driver/preferences/`.

**Missing:** Per-category booleans (10+ toggles).

**Suggested API:**

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/accounts/driver/notification-settings/` | All toggle keys + values |
| `PATCH` | `/accounts/driver/notification-settings/` | Partial update |

---

## Partially implemented (exists but incomplete for Figma)

| Feature | What exists | Gap |
|---------|-------------|-----|
| Ride preferences (screen 3) | `/accounts/driver/preferences/` — trip length, max pickup km, working hours, notification intensity | No ride-type selection; no dynamic radius |
| Earnings (screen 4) | `/order/driver/dashboard/`, `/order/driver/earnings/`, cashouts, Stripe Connect | `promotion` always 0; no instant Stripe payout |
| Heatmap (screen 5) | `ws/driver/surge-zones/` | No REST; no dynamic radius |
| Driver profile header (rating 4.8) | `/accounts/me/` — name, avatar, tax, etc. | **Average rating not on `me/`** — only computed in some order endpoints |
| Online / map home | `/order/driver/online-status/`, `/order/driver/location/update/` | OK for Figma home map |
| Identification checklist | `/accounts/driver/identification/checklist/` + upload/terms/legal | OK for Figma identification flow |
| Application under review | `/accounts/driver/identification/completed/` → `DriverVerification` (`status`, `estimated_review_hours`) | OK for “reviewing 48h” screen |

---

## Already implemented (reference — not missing)

Use these for the driver app; no new backend required for basic flows.

### Accounts (`/api/v1/accounts/`)

| Area | Endpoints |
|------|-----------|
| Auth | `register/`, `login/`, `verify-code/`, `token/refresh/`, password reset |
| Profile | `me/`, `me/avatar/` |
| Driver preferences | `driver/preferences/` |
| Vehicle | `vehicle/`, `vehicle/<pk>/`, `vehicle/image/<pk>/` |
| PIN | `pin-verification/` |
| Identification | `driver/identification/checklist/`, upload submit, legal/terms accept/decline |
| Verification status | `driver/identification/completed/` |

### Orders (`/api/v1/order/`)

| Area | Endpoints |
|------|-----------|
| Availability | `driver/online-status/` (GET/POST) |
| Location | `driver/location/update/` |
| Trips | `driver/nearby-orders/`, `driver/order-action/`, `driver/on-the-way/`, `driver/arrived/`, `driver/pickup/`, `driver/complete/`, `driver/cancel/`, `driver/active-ride/` |
| Earnings | `driver/dashboard/`, `driver/earnings/`, `driver/ride-history/`, `driver/cash-history/`, `driver/cashouts/` (POST) |
| Rating rider | `driver/rating/create/` |

### Payment (`/api/v1/payment/`)

| Area | Endpoints |
|------|-----------|
| Stripe Connect | `driver/stripe-connect/bank-account/`, `driver/stripe-connect/complete-setup/`, `driver/stripe-balance/`, `driver/checkout-history/` |

### WebSockets

| Path | Purpose |
|------|---------|
| `ws/driver/orders/` | New ride requests |
| `ws/driver/surge-zones/` | Surge / heatmap zones |
| `ws/notifications/` | Push-style notifications |
| `ws/chat/...` / order chat | Trip chat |

---

## Suggested implementation priority

1. **Driver rating on `me/`** (or `GET /accounts/driver/summary/`) — small change, unblocks profile menu.  
2. **Ride-type preferences** — matches onboarding screen 3.  
3. **Promotions** — real `promotion` in dashboard.  
4. **`GET /order/driver/surge-zones/`** — if mobile avoids WS.  
5. **Trip invoice endpoint** — earnings/history detail screens.  
6. **Veriff + instant payout** — larger; depends on product/legal.  
7. **Granular notification settings** — when settings UI is built.  
8. **Dynamic radius** — needs product rules + surge integration.

---

## Related docs

- [STRIPE_HolaDrive_INTEGRATION.md](./STRIPE_HolaDrive_INTEGRATION.md) — rider cards, trip charge, driver Connect, wallet cash-out.

---

*Last updated from Figma driver onboarding (screens 1–5) and driver app flows. Regenerate this list after implementing any item above.*
