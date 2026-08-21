"""Throttle GPS persistence so live tracking does not write Postgres on every tick."""
import logging

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


def persist_user_location(user, latitude, longitude) -> bool:
    """
    Always update the in-memory user instance.
    Persist to DB at most every LOCATION_DB_THROTTLE_SECONDS.
    Returns True if a DB write happened.
    """
    user.latitude = latitude
    user.longitude = longitude
    now = timezone.now()
    user.updated_at = now

    throttle_s = int(getattr(settings, 'LOCATION_DB_THROTTLE_SECONDS', 10) or 10)
    cache_key = f'loc:lastwrite:{user.pk}'
    try:
        if cache.get(cache_key):
            return False
    except Exception:
        logger.warning('location cache read failed; writing DB', exc_info=True)

    user.save(update_fields=['latitude', 'longitude', 'updated_at'])
    try:
        cache.set(cache_key, 1, timeout=max(throttle_s, 1))
    except Exception:
        logger.warning('location cache write failed', exc_info=True)
    return True
