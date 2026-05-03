"""Background poller — Django runserver yoki gunicorn ichida ishlaydi.

Production'da Celery worker'ga ko'chirish kerak. Hozircha oddiy thread loop:
- Har 30 sekundda due task'larni qidiradi
- Topganini claim qilib (lock) executes
- Lock yo'lqolib qolgan task'lar boshqa worker tomonidan tugatiladi

DIQQAT: Multi-worker (gunicorn -w 4) bilan ishlaganda har worker o'z poller'ini
ishga tushiradi. `claim_task` orqali atomic lock orqali ishonchli — bir vaqtda
faqat bitta worker bitta task'ni execute qiladi.
"""
import logging
import threading
import time

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 30
_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _poll_loop():
    """Polling loop. Stop event bilan to'xtatiladi."""
    from .services import claim_task, execute_task, fetch_due_tasks

    logger.info('ScheduledTask poller ishga tushdi')
    while not _stop_event.is_set():
        try:
            due = fetch_due_tasks(limit=20)
            for task in due:
                if claim_task(task):
                    execute_task(task)
        except Exception as e:  # noqa: BLE001
            # Loop'ni to'xtatmaslik uchun barcha xatolarni tutib qolamiz
            logger.exception(f'Poller iteratsiyasi xatosi: {e}')

        # Wait with cancellation
        _stop_event.wait(POLL_INTERVAL_SECONDS)
    logger.info('ScheduledTask poller to\'xtatildi')


def start_poller() -> None:
    """Poller'ni boshqarish: agar hali ishlamayotgan bo'lsa, thread yaratadi."""
    global _thread
    if _thread is not None and _thread.is_alive():
        return
    _stop_event.clear()
    _thread = threading.Thread(target=_poll_loop, name='ScheduledTaskPoller', daemon=True)
    _thread.start()


def stop_poller() -> None:
    _stop_event.set()
