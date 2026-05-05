"""Draft status va manba enumlari."""
from django.db import models


class DraftStatus(models.TextChoices):
    """Qoralama holati."""
    PENDING_REVIEW = 'PENDING_REVIEW', 'Tahrir kutilmoqda'
    PUBLISHED = 'PUBLISHED', 'Joylangan'
    REJECTED = 'REJECTED', 'Rad etilgan'
    EXPIRED = 'EXPIRED', 'Muddati o\'tgan'


class DraftSource(models.TextChoices):
    """Qoralama qaerdan kelgan."""
    VOICE_TELEGRAM = 'VOICE_TELEGRAM', 'Telegram ovozli xabar'
    MANUAL = 'MANUAL', 'Qo\'lda kiritilgan'
