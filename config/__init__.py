# Celery setup (lazy: migrations work without celery installed)
try:
    from .celery import app as celery_app
except ImportError:
    celery_app = None

__all__ = ('celery_app',)

