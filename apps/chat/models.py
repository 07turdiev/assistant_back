"""ChatMessage — production sxemasiga to'liq mos.

Production'da nom `Chat` edi, lekin Django'da `chat` app nomi bilan to'qnashmaslik uchun
`ChatMessage` deb nomlandi.

Maydonlar (production'dagidek):
- sender, receiver (User FK)
- message (String)
- viewed (boolean)
- files: List<Attachment> — `Attachment.file_chat` FK orqali OneToMany
"""
from django.db import models

from apps.core.models import AuditMixin


class ChatMessage(AuditMixin):
    sender = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='chat_sent',
    )
    receiver = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='chat_received',
    )
    message = models.TextField(blank=True, default='')
    viewed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sender', 'receiver', '-created_at']),
            models.Index(fields=['receiver', 'viewed']),
        ]

    def __str__(self) -> str:
        return f'{self.sender_id} → {self.receiver_id}: {self.message[:30]}'
