"""
Celery configuration for HolaDrive project.
Handles background tasks like order timeout checking.
"""
import os
import sys
from celery import Celery

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('holadrive')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Windows uchun pool sozlash (prefork Windows'da ishlamaydi)
if sys.platform == 'win32':
    app.conf.worker_pool = 'solo'  # Windows uchun solo pool ishlatish
    app.conf.worker_concurrency = 1  # Solo pool uchun concurrency 1 bo'lishi kerak

# Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'check-order-timeouts': {
        'task': 'apps.order.tasks.check_order_timeouts',
        'schedule': 5.0,  # Har 5 soniyada ishlaydi
    },
}

# Timezone
app.conf.timezone = 'UTC'

