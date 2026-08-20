# Ride cancellation on order WebSockets

When a ride is cancelled, the **cancellation reason** is broadcast on the rider/driver order sockets (not only status change).

## Channels

| Role | Socket | Group |
|------|--------|--------|
| Driver | `ws/driver/orders/` | `driver_orders_<user_id>` |
| Rider | `ws/rider/orders/` | `rider_orders_<user_id>` |

## `cancel` object (both sides)

```json
{
  "cancelled_by": "driver" | "rider",
  "reason": "changed_mind",
  "reason_display": "Changed my mind",
  "other_reason": null,
  "created_at": "2026-08-20T12:00:00+00:00",
  "order_driver_id": 123
}
```

`order_driver_id` is present when a `CancelOrder` row is linked to an `OrderDriver`.

## Rider cancelled → drivers

Event: **`order_cancelled_by_rider`**

```json
{
  "type": "order_cancelled_by_rider",
  "change": "cancelled_rider",
  "message": "The rider cancelled this ride.",
  "order": { "...": "OrderDetailSerializer + cancel" },
  "cancel": { "cancelled_by": "rider", "reason": "...", "reason_display": "...", "other_reason": null }
}
```

## Driver cancelled → rider

Events (both sent):

1. **`order_cancelled_by_driver`** — dedicated cancel event with `cancel`
2. **`rider_order_updated`** — `change: "cancelled_driver"` with top-level `cancel` and `order.cancel`

```json
{
  "type": "order_cancelled_by_driver",
  "change": "cancelled_driver",
  "message": "Your ride has been cancelled by the driver.",
  "order": { "status": "cancelled", "cancel": { "...": "..." } },
  "cancel": { "cancelled_by": "driver", "reason": "...", "reason_display": "...", "other_reason": "..." }
}
```

## Rider cancelled → rider (own socket)

**`rider_order_updated`** with `change: "cancelled_rider"` and the same `cancel` / `order.cancel` shape.

## Client tips

- Prefer listening for `order_cancelled_by_*` for UI alerts; use `rider_order_updated` / order list refresh for state sync.
- On the live map (`ws/order/{id}/tracking/`), also listen for `order_cancelled` (same `cancel` object).
- Show `other_reason` when `reason` is `other`; otherwise show `reason_display` (or `reason`).
