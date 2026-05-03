"""Scheduling biznes mantig'i — ScheduledTask CRUD + execution.

Production EventServiceImpl notify_time ga asosan har bir qatnashchi uchun
TaskScheduler.schedule(...) chaqirardi. Biz bir ScheduledTask yaratamiz
(har notify_time uchun bittadan), execution paytida qatnashchilarni topib
bildirishnoma yuboramiz.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from django.db import transaction
from django.utils import timezone

from .models import ScheduledTask, ScheduledTaskKind

logger = logging.getLogger(__name__)

# Production'da `±3 daqiqa` oynaga to'g'ri kelishini tekshirardi (notification spam'ini oldini olish).
EXECUTION_WINDOW_MINUTES = 3


def schedule_event_reminders(event) -> int:
    """Tadbir uchun har bir `notify_time` (minut) uchun reminder yaratadi.

    `event.notify_time` (List[int]) ichidagi har son uchun:
        run_at = event_end_datetime - notify_time minut

    Returns: yaratilgan ScheduledTask soni.
    """
    if not event.notify_time:
        return 0

    end_dt = datetime.combine(event.date, event.end_time)
    if timezone.is_naive(end_dt):
        end_dt = timezone.make_aware(end_dt)

    now = timezone.now()
    created = 0
    for nt in event.notify_time:
        run_at = end_dt - timedelta(minutes=nt)
        if run_at <= now:
            continue  # vaqt o'tib ketgan
        ScheduledTask.objects.create(
            kind=ScheduledTaskKind.EVENT_REMINDER,
            event_id=event.id,
            notify_time=nt,
            run_at=run_at,
        )
        created += 1

    logger.info(f'Event {event.id}: {created} ta reminder rejalashtirildi')
    return created


def cancel_event_reminders(event_id) -> int:
    """Tadbir o'chirilganda barcha rejalashtirilgan reminder'larni bekor qilish."""
    deleted, _ = ScheduledTask.objects.filter(
        kind=ScheduledTaskKind.EVENT_REMINDER,
        event_id=event_id,
        executed=False,
    ).delete()
    return deleted


def schedule_report_followup(report, notify_time_min: int) -> Optional[ScheduledTask]:
    """Hisobotga `notify_time` minutdan keyin eslatma."""
    if notify_time_min <= 0:
        return None
    run_at = timezone.now() + timedelta(minutes=notify_time_min)
    return ScheduledTask.objects.create(
        kind=ScheduledTaskKind.REPORT_FOLLOWUP,
        event_id=None,
        user_id=report.sender_id,  # eslatma sender'ga ketadi
        notify_time=notify_time_min,
        run_at=run_at,
    )


# --- Execution ---

def fetch_due_tasks(limit: int = 50) -> list:
    """Vaqti kelgan, hali bajarilmagan task'larni olish."""
    now = timezone.now()
    return list(
        ScheduledTask.objects
        .filter(executed=False, run_at__lte=now)
        .filter(
            # locked_until is None OR locked_until < now (boshqa worker hozir bajarmayapti)
            models_locked_q(now)
        )
        .order_by('run_at')[:limit]
    )


def models_locked_q(now):
    from django.db.models import Q
    return Q(locked_until__isnull=True) | Q(locked_until__lt=now)


@transaction.atomic
def claim_task(task: ScheduledTask) -> bool:
    """Task'ni bajarishga qayd qilish (multi-worker uchun lock).

    Returns True agar muvaffaqiyatli claimed, False agar boshqa worker oldindan oldi.
    """
    now = timezone.now()
    updated = ScheduledTask.objects.filter(
        id=task.id, executed=False,
    ).filter(
        models_locked_q(now)
    ).update(
        locked_until=now + timedelta(minutes=2),
        updated_at=now,
    )
    return updated > 0


def execute_task(task: ScheduledTask) -> None:
    """Task'ni bajaradi — kind ga qarab dispatcher chaqiradi."""
    try:
        if task.kind == ScheduledTaskKind.EVENT_REMINDER:
            _execute_event_reminder(task)
        elif task.kind == ScheduledTaskKind.REPORT_FOLLOWUP:
            _execute_report_followup(task)
        else:
            logger.warning(f'Unknown task kind: {task.kind}')

        task.executed = True
        task.executed_at = timezone.now()
        task.error = ''
        task.locked_until = None
        task.save(update_fields=['executed', 'executed_at', 'error', 'locked_until', 'updated_at'])
    except Exception as e:  # noqa: BLE001
        logger.exception(f'ScheduledTask {task.id} execution xatosi: {e}')
        task.error = str(e)[:500]
        task.locked_until = None
        task.save(update_fields=['error', 'locked_until', 'updated_at'])


def _execute_event_reminder(task: ScheduledTask) -> None:
    from apps.events.models import Event
    from apps.info.enums import NotificationType
    from apps.notifications.services import NotificationService

    if not task.event_id:
        return
    try:
        event = Event.objects.select_related('speaker', 'direction').prefetch_related(
            'participants', 'participants__chief',
        ).get(pk=task.event_id)
    except Event.DoesNotExist:
        logger.info(f'Event {task.event_id} topilmadi — reminder bekor qilindi')
        return

    NotificationService.dispatch_event(event, notification_type=NotificationType.REMINDED)
    logger.info(f'Reminder yuborildi: event {event.id} ({task.notify_time} minut oldin)')


def _execute_report_followup(task: ScheduledTask) -> None:
    # TODO: Reports'da reply'da notify_time bo'lsa, sender'ga eslatma yuborish
    logger.info(f'Report followup task {task.id} — placeholder')
