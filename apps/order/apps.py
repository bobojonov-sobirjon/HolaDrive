from django.apps import AppConfig


class OrderConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.order"
    verbose_name = "Order"

    def ready(self):
        # Import signals so that surge pricing updates are broadcast over WebSocket.
        from . import signals  # noqa: F401