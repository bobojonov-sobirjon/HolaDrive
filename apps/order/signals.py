from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import SurgePricing


def _build_surge_zones_payload():
    """
    Helper: barcha active SurgePricing zonalarni WebSocket uchun tayyorlaydi.
    """
    zones = []
    for z in SurgePricing.objects.filter(is_active=True).order_by("-priority", "name"):
        zones.append({
            "id": z.id,
            "name": z.name,
            "zone_name": z.zone_name,
            "latitude": float(z.latitude) if z.latitude is not None else None,
            "longitude": float(z.longitude) if z.longitude is not None else None,
            "radius_km": float(z.radius_km) if z.radius_km is not None else None,
            "multiplier": float(z.multiplier) if z.multiplier is not None else 1.0,
            "start_time": str(z.start_time) if z.start_time else None,
            "end_time": str(z.end_time) if z.end_time else None,
            "days_of_week": z.days_of_week or [],
        })
    return zones


def _broadcast_surge_zones():
    """
    driver_surge_zones guruhiga joriy zonalarni push qiladi.
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    zones = _build_surge_zones_payload()
    async_to_sync(channel_layer.group_send)(
        "driver_surge_zones",
        {
            "type": "surge_zones_update",
            "zones": zones,
        },
    )


@receiver(post_save, sender=SurgePricing)
def surge_pricing_saved(sender, **kwargs):
    _broadcast_surge_zones()


@receiver(post_delete, sender=SurgePricing)
def surge_pricing_deleted(sender, **kwargs):
    _broadcast_surge_zones()

