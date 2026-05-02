"""Role, User."""
import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from .enums import RoleName, UserStatus
from .managers import UserManager


class Role(models.Model):
    name = models.CharField(max_length=32, unique=True, choices=RoleName.choices)
    label_uz = models.CharField(max_length=255)
    label_ru = models.CharField(max_length=255)

    class Meta:
        ordering = ['id']

    def __str__(self) -> str:
        return self.label_uz


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user — UUID PK, lavozim ikki tilda, role/direction/chief bog'lanishlari."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Audit (User'ga to'g'ridan-to'g'ri AuditMixin qo'shmaymiz, chunki o'zining FK lari bor)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    created_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        editable=False, related_name='+',
    )
    updated_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        editable=False, related_name='+',
    )

    username = models.CharField(max_length=255, unique=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    father_name = models.CharField(max_length=255, blank=True, default='')

    position_uz = models.CharField(max_length=255, blank=True, default='')
    position_ru = models.CharField(max_length=255, blank=True, default='')

    phone_number = models.CharField(max_length=64, blank=True, default='')
    email = models.EmailField(blank=True, null=True)
    office_number = models.CharField(max_length=64, blank=True, default='')
    company_car = models.JSONField(blank=True, null=True)

    enabled = models.BooleanField(default=True)
    status = models.CharField(max_length=32, choices=UserStatus.choices, default=UserStatus.AT_WORK)

    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='users')
    direction = models.ForeignKey(
        'directions.Direction',
        on_delete=models.PROTECT,
        related_name='users',
        null=True,
        blank=True,
    )
    chief = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates',
    )

    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    telegram_id = models.BigIntegerField(blank=True, null=True, unique=True)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self) -> str:
        return f'{self.last_name} {self.first_name} ({self.username})'

    @property
    def full_name(self) -> str:
        parts = [self.last_name, self.first_name, self.father_name]
        return ' '.join(p for p in parts if p).strip()

    def save(self, *args, **kwargs):
        from apps.core.middleware import get_current_user
        actor = get_current_user()
        now = timezone.now()
        is_new = self._state.adding
        if is_new:
            self.created_at = now
            if actor and getattr(actor, 'is_authenticated', False) and actor != self:
                self.created_by = actor
                self.updated_by = actor
        elif actor and getattr(actor, 'is_authenticated', False):
            self.updated_by = actor
        self.updated_at = now
        super().save(*args, **kwargs)
