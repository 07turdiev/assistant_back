"""Attachment — production JAR sxemasiga mos.

JPA strukturasi:
- randomName, fileName, path, contentType, size
- fileEvent (Event FK), protocolEvent (Event FK), fileChat (Chat FK — chat app paytida)
"""
from django.db import models

from apps.core.models import AuditMixin


class Attachment(AuditMixin):
    file_name = models.CharField(max_length=255)            # original
    random_name = models.CharField(max_length=255)          # diskdagi (timestamp + ext)
    path = models.CharField(max_length=255)                 # documents/, protocols/, chat-files/, photos/
    content_type = models.CharField(max_length=255)
    size = models.BigIntegerField()

    file_event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='files',
    )
    protocol_event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='protocols',
    )
    # file_chat — Chat ilovasi yaratilganda alohida migratsiyada qo'shiladi

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.file_name

    @property
    def url(self) -> str:
        """API endpoint orqali yuklab olish URL."""
        return f'/api/file/{self.id}/'
