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
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='events_as_speaker',
    )
    participants = models.ManyToManyField(
        'users.User',
        through='EventParticipant',
        through_fields=('event', 'user'),
        related_name='events',
    )
    # Tadbir yo'naltirilgan bo'lim/boshqarmalar (ma'sul shaxslar shulardan olinadi).
    # Yuqori rollar (VAZIR/ORINBOSAR/YORDAMCHI) bo'lim tanlaydi → boshliq qatnashchi bo'ladi.
    participant_directions = models.ManyToManyField(
        'directions.Direction',
        blank=True,
        related_name='events_as_target',
    )
    # "Nomidan" — yordamchi yaratsa, asl egasi (vazir/o'rinbosar). Bo'sh bo'lsa = yaratuvchi.
    on_behalf_of = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='events_on_behalf',
    )
    # Manzil — ikki rejim:
    #  (a) Vazirlik binosi: `hall` tanlanadi (hona band qilinadi, to'qnashuv tekshiriladi)
    #  (b) Tashqi hudud: `region` + `district` + `address` (qo'shimcha maydon)
    hall = models.ForeignKey(
        'events.Hall', on_delete=models.SET_NULL, null=True, blank=True, related_name='events',
    )
    region = models.ForeignKey(
        'organisations.Region', on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )
    district = models.ForeignKey(
        'organisations.District', on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
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


class Hall(models.Model):
    """Vazirlik binosidagi yig'ilish zali — etaj raqami + zal nomi.

    Misol: floor=-1, name="Katta yig'ilishlar zali"; floor=2, name="Vazir priyomniy".
    Admin paneldan boshqariladi.
    """

    floor = models.IntegerField()  # -1, 1, 2, ...
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ['floor', 'name']

    def __str__(self) -> str:
        return f'{self.floor}-etaj: {self.name}'


class HallBooking(AuditMixin):
    """Yig'ilish honasi bandligi (yagona yozuv).

    Ikki manba:
      - Tadbir vazirlik honasida bo'lsa → `event` bog'langan bron avtomatik yaratiladi.
      - Bo'lim/boshqarma alohida band qilsa → `event` bo'sh, faqat `title` (maqsad).
    To'qnashuv (bir hona, bir vaqt) qattiq bloklanadi.
    """

    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='bookings')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    # Kim nomidan band qilingan (bo'lim/boshqarma)
    direction = models.ForeignKey(
        'directions.Direction', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='hall_bookings',
    )
    # Tadbirga bog'liq bo'lsa — o'sha tadbir (har tadbirda ko'pi bilan 1 bron)
    event = models.OneToOneField(
        Event, on_delete=models.CASCADE,
        null=True, blank=True, related_name='hall_booking',
    )
    # Alohida bron uchun maqsad/nomi (tadbir bo'lsa — tadbir sarlavhasidan olinadi)
    title = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['date', 'start_time']
        indexes = [
            models.Index(fields=['hall', 'date']),
        ]

    def __str__(self) -> str:
        return f'{self.hall} · {self.date} {self.start_time}-{self.end_time}'
