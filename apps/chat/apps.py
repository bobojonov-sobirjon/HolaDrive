from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.chat'
    verbose_name = 'Chat for Support and Feedback'

    def ready(self):
        # Ensure group setup & other post_migrate tasks.
        from . import signals  # noqa: F401