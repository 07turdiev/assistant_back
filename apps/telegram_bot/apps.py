"""Telegram bot AppConfig — server ishga tushganda bot ham avto-start qiladi.

`TG_BOT_AUTOSTART=True` va `TG_BOT_TOKEN` sozlangan bo'lsa, daemon thread'da
aiogram polling ishga tushadi. runserver auto-reloader ikki marta ishga tushishini
oldini olish uchun `RUN_MAIN` tekshiruvi mavjud.
"""
import logging
import os
import sys
import threading
import time

from django.apps import AppConfig

logger = logging.getLogger(__name__)

_bot_started = False
_lock = threading.Lock()

# Server jarayoni emas — botni ishga tushirmaymiz
_NON_SERVER_COMMANDS = frozenset([
    'migrate', 'makemigrations', 'collectstatic', 'shell', 'shell_plus',
    'createsuperuser', 'seed', 'test', 'check', 'showmigrations', 'sqlmigrate',
    'dbshell', 'flush', 'inspectdb', 'loaddata', 'dumpdata',
    'startapp', 'startproject', 'run_bot',
])


class TelegramBotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.telegram_bot'

    def ready(self):
        global _bot_started
        with _lock:
            if _bot_started:
                return
            if not _should_autostart():
                return
            _bot_started = True

        thread = threading.Thread(
            target=_run_bot_loop, daemon=True, name='tg-bot-polling',
        )
        thread.start()
        logger.info('Telegram bot avto-start: thread spawned')


def _should_autostart() -> bool:
    from django.conf import settings

    if not getattr(settings, 'TG_BOT_TOKEN', ''):
        return False
    if not getattr(settings, 'TG_BOT_AUTOSTART', False):
        return False

    # Management komandalari — server emas
    if len(sys.argv) > 1 and sys.argv[1] in _NON_SERVER_COMMANDS:
        return False

    # runserver auto-reloader: faqat asosiy worker'da (RUN_MAIN=true bola jarayonida).
    # --noreload bayrog'i bilan ishga tushganda esa fork bo'lmaydi va bot bevosita ishga tushadi.
    if 'runserver' in sys.argv:
        if '--noreload' not in sys.argv and os.environ.get('RUN_MAIN') != 'true':
            return False

    return True


def _run_bot_loop():
    """Bot polling — crash bo'lsa 10 sekundda restart qiladi."""
    import asyncio

    from apps.telegram_bot.bot import run_polling

    while True:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_polling())
            # Polling tinch chiqdi (token yo'q va h.k.) — boshqa urinmaymiz
            logger.info('Bot polling tinch yakunlandi')
            return
        except KeyboardInterrupt:
            return
        except Exception as e:  # noqa: BLE001
            logger.exception('Bot crashed, 10s da qayta urinish: %s', e)
            time.sleep(10)
        finally:
            try:
                loop.close()
            except Exception:  # noqa: BLE001
                pass
