"""Atomic driver accept — one accepted driver per order."""
from django.db import transaction
from django.utils import timezone

from apps.order.models import Order, OrderDriver


class OrderAcceptError(Exception):
    def __init__(self, message: str, code: str = 'error'):
        super().__init__(message)
        self.message = message
        self.code = code


def accept_order_for_driver(order_id: int, driver_id: int) -> tuple[Order, OrderDriver]:
    with transaction.atomic():
        order = (
            Order.objects.select_for_update()
            .select_related('user')
            .get(pk=order_id)
        )
        if order.status != Order.OrderStatus.PENDING:
            raise OrderAcceptError('Order is not available for accepting', 'not_available')

        already = (
            OrderDriver.objects.select_for_update()
            .filter(order=order, status=OrderDriver.DriverRequestStatus.ACCEPTED)
            .exists()
        )
        if already:
            raise OrderAcceptError('Order was already accepted by another driver', 'taken')

        order_driver = (
            OrderDriver.objects.select_for_update()
            .filter(
                order=order,
                driver_id=driver_id,
                status=OrderDriver.DriverRequestStatus.REQUESTED,
            )
            .first()
        )
        if not order_driver:
            raise OrderAcceptError(
                'This order is not assigned to you or has already been processed',
                'not_assigned',
            )

        now = timezone.now()
        order_driver.status = OrderDriver.DriverRequestStatus.ACCEPTED
        order_driver.responded_at = now
        order_driver.save(update_fields=['status', 'responded_at'])
        order.status = Order.OrderStatus.ACCEPTED
        order.save(update_fields=['status'])
        return order, order_driver
