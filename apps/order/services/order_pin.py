"""
Order ↔ driver PIN: generate a per-trip code (never copy a hashed user PIN).
"""
import secrets

from apps.order.models import OrderDriver


def attach_driver_pin_to_order_driver(order_driver: OrderDriver) -> None:
    """Set a unique 4-digit ride PIN on OrderDriver if empty."""
    if order_driver.pin_code:
        return
    order_driver.pin_code = f'{secrets.randbelow(9000) + 1000:04d}'
    order_driver.save(update_fields=['pin_code'])
