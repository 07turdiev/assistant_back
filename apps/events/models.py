"""Event, PreEvent, Visitor, EventParticipant — production JAR sxemasiga mos."""
from django.db import models

from apps.core.models import AuditMixin
from apps.info.enums import EventType, NotificationType, Sphere  # noqa: F401


class Event(AuditMixin):
    """Tadbir.

    Production JAR'da:
    - title, description, address: String
    - date: LocalDate, startTime/endTime: LocalTime (DATE va TIME alohida)
    - sphere: Sphere enum, type: Type enum (PascalCase)
    - isPrivate, isImportant: boolean
    - serialNumber: unique protokol tartib raqami (nullable)
    - direction (FK), speaker (User FK)
    - notifyTime: List<Integer> (@ElementCollection table=event_notify_time)
    - participants: List<User> (M2M)
    - files, protocols: List<Attachment> (OneToMany via Attachment.fileEvent / .protocolEvent)
    - visitors: List<Visitor>
    - conclusion: String
    """

    title = models.TextField()
    description = models.TextField(blank=True, default='')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    address = models.CharField(max_length=255, blank=True, default='')
    serial_number = models.CharField(max_length=255, unique=True, null=True, blank=True)
    sphere = models.CharField(max_length=128, choices=Sphere.choices)
    type = models.CharField(max_length=32, choices=EventType.choices)
    is_important = models.BooleanField(default=False)
    is_private = models.BooleanField(default=False)
    conclusion = models.TextField(blank=True, default='')

    direction = models.ForeignKey(
        'directions.Direction',
        on_delete=models.CASCADE,
        related_name='events',
    )
    speaker = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='events_as_speaker',
    )
    participants = models.ManyToManyField(
        'users.User',
        through='EventParticipant',
        through_fields=('event', 'user'),
        related_name='events',
    )
    # `notify_time` (List<Integer>) — SQLite dev uchun JSONField,
    # PostgreSQL ga ko'chganda ArrayField'ga converted bo'lsa ham bo'ladi.
    notify_time = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-date', '-start_time']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['speaker']),
        ]

    def __str__(self) -> str:
        return f'{self.title} ({self.date})'


class EventParticipant(AuditMixin):
    """Tadbir qatnashchisi (M2M through). Production'da `event_participants` jadvali."""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='participant_links')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    is_present = models.BooleanField(default=False)
    comment = models.CharField(max_length=1000, blank=True, default='')

    class Meta:
        unique_together = [('event', 'user')]


class PreEvent(AuditMixin):
    """Tadbir loyihasi (event'ga aylantirilishi mumkin).

    DIQQAT: production'da `startTime`/`endTime` — **LocalDateTime** (Event.start_time/end_time
    LocalTime'dan farqli). Bu erda `start_time`/`end_time` DateTimeField.
    """

    title = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True, default='')
    date = models.DateField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    class Meta:
        ordering = ['-date', '-start_time']

    def __str__(self) -> str:
        return self.title


class Visitor(AuditMixin):
    """Tadbir mehmonlari ro'yxati."""

    full_name = models.CharField(max_length=255)
    organisation_name = models.CharField(max_length=255, blank=True, default='')
    position = models.CharField(max_length=255, blank=True, default='')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='visitors')

    class Meta:
        ordering = ['full_name']

    def __str__(self) -> str:
        return self.full_name
