import os

from django.apps import AppConfig


class SchedulerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.scheduler'

    def ready(self):
        # `runserver` autoreload paytida ikki marta ishga tushmasligi uchun
        if os.environ.get('RUN_MAIN') != 'true' and not os.environ.get('SCHEDULER_FORCE_START'):
            return
        # Migratsiyalar paytida ishga tushirmaslik
        import sys
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            return

        from .runner import start_poller
        start_poller()
