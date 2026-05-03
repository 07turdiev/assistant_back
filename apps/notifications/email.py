"""Email yuborish — Django `send_mail()` orqali.

Production EmailService.java mantig'i:
- Subject: "Информация от министерства ассистента"
- Body: text-only (SimpleMailMessage)
- Recipients: filterli (None'larsiz)
"""
import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

DEFAULT_SUBJECT = 'Smart Assistant — bildirishnoma'


def send_to_many(emails: list[str], text: str, *, subject: str = DEFAULT_SUBJECT) -> int:
    """Bir nechta email manziliga matnli xabar yuborish."""
    valid = [e.strip() for e in (emails or []) if e and '@' in e]
    if not valid or not text:
        return 0

    from_email = (
        getattr(settings, 'DEFAULT_FROM_EMAIL', None)
        or getattr(settings, 'EMAIL_HOST_USER', '')
        or 'noreply@madaniyat.uz'
    )

    try:
        sent = send_mail(
            subject=subject,
            message=text,
            from_email=from_email,
            recipient_list=valid,
            fail_silently=False,
        )
        return sent
    except Exception as e:  # noqa: BLE001
        logger.warning(f'Email yuborishda xato: {e}')
        return 0
