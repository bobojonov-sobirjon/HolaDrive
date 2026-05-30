# Hola Rider — Missing & Partial APIs

Gap analysis for **Rider** Figma flows vs the current HolaDrive backend.  
**Base URL:** `/api/v1/` · **Auth:** JWT Bearer (Rider group) unless noted.

Companion doc for drivers: [driver_no_apis.md](./driver_no_apis.md)

---

## Figma areas covered

| Section | Figma content |
|---------|----------------|
| Onboarding & auth | Splash, carousel, T&C, phone/email login, OTP, password reset, register, preferences, edit profile |
| Discovery & planning | Location permission, map, Hola Suggestions, plan ride, multi-stop, schedule, switch rider / contacts |
| Booking & payment | Price estimate, manage price, ride types, preferences, saved cards, Hola Wallet, promos |
| Active trip | Finding driver, pickup, PIN, driver info, chat, call, cancel reasons, update destination |
| Post-trip | Rate & tip, tags, invoice/receipt, split fare, ride history |
| Settings | Profile, payments, notifications, security, linked accounts, language/theme, trusted contacts, support, referrals, safety tools |

---

## Not implemented (new work required)

### Auth & account

| Feature | Figma | Suggested API | Notes |
|---------|-------|---------------|-------|
| Social login | Google, Facebook, Apple on login | `POST /accounts/auth/google/`, `.../apple/`, `.../facebook/` | Only email/password `login/` + `register/` exist |
| Phone-first login | Enter number + OTP | `POST /accounts/auth/phone/send-otp/`, `.../verify/` | `send-verification-code/` is email-oriented registration flow |
| Rider terms (onboarding) | Accept / Decline T&C | `GET/POST /accounts/rider/terms/` | Terms exist under **driver-only** `driver/registration-terms/` |
| Deactivate account | Account & Security | `POST /accounts/me/deactivate/` | — |
| Delete account | Permanent delete | `DELETE /accounts/me/` (soft-delete) | — |
| Device management | List/revoke sessions | `GET/DELETE /accounts/me/devices/` | — |
| 2FA toggles | SMS / WhatsApp / Google Authenticator | `GET/PATCH /accounts/me/security/` | — |
| Biometric / Face ID | Toggles in UI | Client-only (optional server flag) | — |
| App language | English, French, … | `GET/PATCH /accounts/me/settings/` (`language`) | — |
| App theme | Light / dark / system | Same settings payload (`theme`) | — |
| Linked accounts | Google/Apple/FB connect status | `GET/POST/DELETE /accounts/me/linked-accounts/` | — |
| App info / About | Version, privacy, terms URLs | `GET /accounts/app-info/` (AllowAny) | — |
| Cities dropdown | Montreal, etc. | `GET /accounts/metadata/cities/` | Profile uses free-text `address` on `me/` |

### Discovery, addresses & POI

| Feature | Figma | Suggested API | Notes |
|---------|-------|---------------|-------|
| Address autocomplete | Search destination / pickup | `GET /places/autocomplete/?q=` | No Google/Mapbox proxy |
| Reverse geocoding | Pin on map → address | `GET /places/reverse/?lat=&lon=` | — |
| Recent locations | Home map / plan ride | `GET /order/rider/recent-locations/` | — |
| Repeat trip | “Repeat” on history row | `POST /order/rider/repeat/` or embed in history | Use `ride-history` + client replay only today |
| Hola Suggestions | Hotels, Grocery, Parks, … | `GET /places/suggestions/?category=` | — |
| Nearby drivers on map | Car icons on home map | `GET /order/rider/nearby-drivers/?lat=&lon=` | Drivers not exposed to rider HTTP (WS tracking only after assign) |

### Book for others / contacts

| Feature | Figma | Suggested API | Notes |
|---------|-------|---------------|-------|
| Saved riders (“Switch rider”) | Me, John Doe, add contact | `GET/POST/PATCH /accounts/rider/saved-riders/` | `additional-passenger/` is **per order**, not a saved list |
| Device contacts sync | Choose from contacts | Optional `POST /accounts/rider/contacts/import/` | Usually client-side only |

### Multi-stop & mid-trip changes

| Feature | Figma | Suggested API | Notes |
|---------|-------|---------------|-------|
| Multi-stop route | A → B → C, reorder stops | `POST /order/create/` with `stops[]` or `POST /order/<id>/stops/` | Create flow builds **one** `OrderItem` (`stop_sequence=1`) |
| Update destination mid-trip | “Add or change” while riding | `PATCH /order/<id>/destination/` | `order-item/update/` only changes **ride_type**, not addresses |
| Reorder stops | Drag handles | `PATCH /order/<id>/stops/reorder/` | Model has `stop_sequence`; no rider API |

### Hola Wallet (rider)

| Feature | Figma | Suggested API | Notes |
|---------|-------|---------------|-------|
| Wallet balance | Hola Wallet CA$10 | `GET /payment/rider/wallet/` | `payment_type=hola_wallet_cash` on order only; **no rider balance ledger** |
| Rewards | “Every 5 rides → $1” | `GET /payment/rider/wallet/rewards/` | — |
| Top-up wallet | Add funds | `POST /payment/rider/wallet/top-up/` | — |

### Promotions & vouchers

| Feature | Figma | Suggested API | Notes |
|---------|-------|---------------|-------|
| List promos | Best deals, % off | `GET /order/rider/promos/` | `PromoCode` managed in **admin panel** only |
| Redeem code | Enter + Redeem | `POST /order/rider/promos/redeem/` | — |
| Apply to order | Use now on booking | `POST /order/<id>/apply-promo/` | `OrderPromoCode` model exists; no rider endpoint |

### Split fare

| Feature | Figma | Suggested API | Notes |
|---------|-------|---------------|-------|
| Start split | Select contacts, even/custom | `POST /order/<id>/split-fare/` | `OrderPaymentSplit` model exists; **admin CRUD only** |
| Edit split amounts | Per-person $ | `PATCH /order/<id>/split-fare/<split_id>/` | — |
| Add split participant | Manual name/email/phone | `POST /order/<id>/split-fare/participants/` | — |

### Payments (beyond Stripe cards)

| Feature | Figma | Suggested API | Notes |
|---------|-------|---------------|-------|
| Google Pay | Payment method row | Stripe Payment Element / native SDK | Only `saved-cards/` (Stripe PM) |
| Bitcoin | Payment method | — | Not supported |
| Charge tip on card | Tip % + submit | `POST /order/rating/create/` stores `tip_amount`; **no separate Stripe tip charge** | Confirm product: tip included in PI or follow-up charge |

### Post-trip & history

| Feature | Figma | Suggested API | Notes |
|---------|-------|---------------|-------|
| Trip invoice / receipt | Transaction ID, booking ID, tax | `GET /order/rider/rides/<order_id>/invoice/` | `order/<id>/` + `checkout-preview/` partial |
| Download / share receipt | PDF / share sheet | `GET .../invoice/pdf/` | — |
| Feedback history | List with Pending / Positive | `GET /order/rider/feedback-history/` | Only `POST rating/create/` + `rating/feedback-tags/` |
| Driver review detail | “See review” text | `GET /order/rider/feedback/<id>/` | — |
| Driver public reviews | Driver 4.76 + list | `GET /accounts/drivers/<id>/reviews/` | Rating computed inside some order responses only |
| Rider profile rating | Header “4.8” | Include `average_rating` on `GET /accounts/me/` | **Not on `me/` today** |
| Cancel reasons list | Radio list before cancel | `GET /order/rider/cancel-reasons/` | Reasons exist on `CancelOrder` model; cancel accepts `reason` string without discovery endpoint |

### Safety & trust

| Feature | Figma | Suggested API | Notes |
|---------|-------|---------------|-------|
| Trusted contacts | Select from contacts | `GET/POST/DELETE /accounts/rider/trusted-contacts/` | — |
| Share trip link | Safety tools | `GET /order/<id>/share-link/` | — |
| Safety agent chat | Dedicated support chat | `GET/POST /support/chat/...` | Order chat + generic `chat/rooms/` only |
| Voice recording | Start/stop on trip | `POST /order/<id>/safety/recording/start|stop/` | — |
| Route deviation alert | “Off route” + I’m okay | `POST /order/<id>/safety/check-in/` | No backend geofence logic |
| Emergency contacts | Safety tools shortcut | `GET/POST /accounts/rider/emergency-contacts/` | — |
| In-app voice call | Call driver / safety | Twilio/Agora mask | **No call API** (icons in UI only) |

### Notifications

| Feature | Figma | Suggested API | Notes |
|---------|-------|---------------|-------|
| Notification preferences | 10+ toggles | `GET/PATCH /accounts/rider/notification-settings/` | No rider notification settings API |
| In-app notification inbox | — | `GET /notification/` | `apps/notification/urls.py` is **empty** |
| Register FCM token | Login/register | `POST /accounts/device-token/` | Model `UserDeviceToken` exists; **no public URL** in accounts urls |

### Referrals & support

| Feature | Figma | Suggested API | Notes |
|---------|-------|---------------|-------|
| Referral offers UI | 50% off 2 rides, share code | Extend `invitations/` for rider-facing promo status | `invitations/generate/`, `invitations/users/` exist; no “active offers” payload for Figma |
| Support chat (Frandis) | Help / safety | Support room API or reuse chat with `is_support` | — |

---

## Partially implemented

| Figma feature | What exists | Gap |
|---------------|-------------|-----|
| Register / login / reset | `register/`, `login/`, `verify-code/`, reset password flow | No social / phone OTP login |
| Edit profile | `GET/PATCH /accounts/me/`, `me/avatar/` | No `city` enum; phone change blocked in copy only (no support ticket API) |
| Ride preferences (chat, temp, music, volume) | `/accounts/preferences/` **and** `/order/preferences/` | Accounts prefs lack pet/wheelchair/gender; full set on **order** template |
| Driver prefs (woman driver, pet, wheelchair, favorite) | `UserOrderPreferences` + copied to `OrderPreferences` on create | PATCH via `order/preferences/create|update/` — not separate “trip preferences” screen API name |
| Plan ride + schedule | `POST /order/create/`, `POST /order/schedule/` | Single stop only; schedule attached after order exists |
| For me / pickup | `order_type` `1=pickup`, `2=for_me` on create | Not the same as Figma “book for John Doe” saved rider |
| Extra passenger on trip | `POST /order/additional-passenger/` | Not pre-booking “switch rider” |
| Price estimate & slider | `price-estimate/`, `manage-price/`, `order-item/.../manage-price/` | “Manage price while searching” may need WS or PATCH on pending order |
| Choose plan | `price-estimate/` returns all ride types | Confirm ride = `POST /order/create/` + `payment-card/` |
| Saved cards | `GET/POST/PUT/DELETE /payment/saved-cards/` | No Google Pay / Bitcoin |
| Hola Wallet pay | `payment_type=hola_wallet_cash` on order | No balance/rewards API |
| Finding driver | `ws/rider/orders/` | HTTP poll fallback optional |
| Live tracking | `ws/order/<id>/tracking/`, `GET .../driver/location/` | — |
| Trip chat | `order/<id>/chat/`, `chat/messages/`, `ws/order/<id>/chat/` | — |
| PIN start trip | `pin/verify-rider/`, `pin/verify-driver/` | Figma “enter code sent to driver” — verify copy matches product |
| Cancel ride | `POST /order/<id>/cancel/` with reason | No `GET cancel-reasons/` |
| Rate & tip & tags | `POST /order/rating/create/`, `GET rating/feedback-tags/` | No feedback history list; tip charging unclear |
| Ride history | `GET /order/rider/ride-history/`, `my-orders/` | No invoice/repeat endpoints |
| Active ride resume | `GET /order/rider/active-ride/` | — |
| Stripe customer | `GET /accounts/stripe-customer/` | Rider cards |
| Invitations | `invitations/generate/`, `invitations/users/` | Not full referral dashboard |
| Push (backend) | `notification/services.py` + Celery | Device token registration URL missing |

---

## Already implemented (reference)

### Accounts — `/api/v1/accounts/`

| Area | Endpoints |
|------|-----------|
| Auth | `register/`, `login/`, `token/refresh/`, `send-verification-code/`, `verify-code/`, `reset-password/`, `verify-reset-code/`, `reset-password-confirm/` |
| Profile | `me/`, `me/avatar/` |
| Rider comfort prefs | `preferences/`, `preferences/delete/` |
| PIN (app security) | `pin-verification/` |
| Stripe | `stripe-customer/` |
| Referrals | `invitations/generate/`, `invitations/`, `invitations/users/` |

### Order — `/api/v1/order/`

| Area | Endpoints |
|------|-----------|
| Create & list | `create/`, `my-orders/`, `<order_id>/`, `rider/ride-history/`, `rider/active-ride/` |
| Pricing | `price-estimate/`, `price-estimate/manage-price/`, `order-item/<id>/manage-price/` |
| Preferences (trip) | `preferences/`, `preferences/create/`, `preferences/update/` |
| Passengers & schedule | `additional-passenger/`, `schedule/` |
| Payment on order | `<order_id>/payment-card/`, `<order_id>/checkout-preview/` |
| Cancel | `<order_id>/cancel/` |
| Rating | `rating/create/`, `rating/feedback-tags/` |
| Chat | `<order_id>/chat/`, `<order_id>/chat/messages/` |
| PIN | `pin/verify-rider/`, `pin/verify-driver/` |

### Payment — `/api/v1/payment/`

| Area | Endpoints |
|------|-----------|
| Cards | `saved-cards/`, `saved-cards/<id>/` |

### WebSockets

| Path | Purpose |
|------|---------|
| `ws/rider/orders/` | Order status, new driver, cancel, etc. |
| `ws/order/<id>/tracking/` | Driver location during trip |
| `ws/order/<id>/chat/` | Real-time order chat |
| `ws/notifications/` | Push-style notification channel |
| `ws/chat/...` | General chat rooms (if used) |

---

## Suggested implementation priority (rider)

1. **Device token API** + **notification inbox** — unlock push and settings screens.  
2. **Rider wallet balance + promos redeem/apply** — payment settings & booking.  
3. **Places autocomplete + recent locations** — home / plan ride.  
4. **Multi-stop create + mid-trip destination change** — core Figma ride planner.  
5. **Invoice + feedback history** — post-trip screens.  
6. **Split fare rider APIs** — model already exists.  
7. **Saved riders (book for others)** — switch rider flow.  
8. **Safety pack** (share link, trusted contacts, safety chat) — larger epic.  
9. **Social login + phone OTP** — auth parity with Figma.  
10. **Account lifecycle** (deactivate/delete, linked accounts, granular notifications).

---

## Related docs

- [STRIPE_HolaDrive_INTEGRATION.md](./STRIPE_HolaDrive_INTEGRATION.md) — rider saved cards, trip charge, Connect.  
- [driver_no_apis.md](./driver_no_apis.md) — driver-side gaps.

---

*Generated from Hola Rider Figma flows. Update this file when endpoints are added.*
