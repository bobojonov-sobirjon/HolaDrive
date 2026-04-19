"""
Order ↔ driver PIN: copy from PinVerificationForUser onto OrderDriver for display/verification.
"""
from apps.accounts.models import PinVerificationForUser
from apps.order.models import OrderDriver


def attach_driver_pin_to_order_driver(order_driver: OrderDriver) -> None:
    """Set OrderDriver.pin_code from the driver's saved PIN (if any)."""
    row = (
        PinVerificationForUser.objects.filter(user_id=order_driver.driver_id)
        .values_list('pin', flat=True)
        .first()
    )
    pin = row or ''
    if order_driver.pin_code != pin:
        order_driver.pin_code = pin
        order_driver.save(update_fields=['pin_code'])
