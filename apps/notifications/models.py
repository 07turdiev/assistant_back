"""Notification, WebPushSubscription — production sxemasiga mos."""
from django.db import models

from apps.core.models import AuditMixin
from apps.info.enums import NotificationType


class Notification(AuditMixin):
    """In-app bildirishnoma yozuvi (history).

    Production sxemasiga to'liq mos:
    - user_id: bare UUID (FK YO'Q — JAR'da shunaqa, audit trail uchun)
    - event_id, pre_event_id: bare UUID (event o'chirilsa ham notification qoladi)
    - notification_type: NEW/EDITED/DELETED/REMINDED/PRE_EVENT
    """

    user_id = models.UUIDField(db_index=True)
    title = models.CharField(max_length=255)
    notification_type = models.CharField(max_length=32, choices=NotificationType.choices)

    event_id = models.UUIDField(null=True, blank=True)
    pre_event_id = models.UUIDField(null=True, blank=True)

    date = models.DateField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_important = models.BooleanField(default=False)
    seen = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id', 'seen']),
            models.Index(fields=['user_id', '-created_at']),
        ]

    def __str__(self) -> str:
        return f'{self.notification_type}: {self.title}'


class WebPushSubscription(AuditMixin):
    """Foydalanuvchining brauzer push subscriptioni."""

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='webpush_subscriptions',
    )
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=500, blank=True, default='')
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
        ]

    def __str__(self) -> str:
        return f'WebPush({self.user.username})'
