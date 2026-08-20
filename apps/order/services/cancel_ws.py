"""Shared cancel metadata for order WebSocket payloads."""
from __future__ import annotations

from typing import Any


def build_cancel_ws_payload(order) -> dict[str, Any] | None:
    """
    Latest CancelOrder row for an order, shaped for WS clients.
    Expects ``cancel_orders`` related manager (prefetch optional).
    """
    cancels = getattr(order, 'cancel_orders', None)
    if cancels is None:
        return None
    cancel = cancels.order_by('-created_at').first()
    if not cancel:
        return None

    reason = cancel.reason
    reason_display = ''
    try:
        reason_display = cancel.get_reason_display()
    except Exception:
        reason_display = str(reason or '')

    data: dict[str, Any] = {
        'cancelled_by': cancel.cancelled_by,
        'reason': reason,
        'reason_display': reason_display,
        'other_reason': cancel.other_reason,
        'created_at': cancel.created_at.isoformat() if cancel.created_at else None,
    }
    if getattr(cancel, 'driver_id', None):
        data['order_driver_id'] = cancel.driver_id
    return data
