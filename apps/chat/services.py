"""Chat biznes mantig'i — production `ChatServiceImpl` ekvivalenti.

Production behavior:
- POST /api/chat (multipart) → DB ga yozish + WebSocket push receiver'ga
- GET /api/chat?receiverId — sahifali tarix (ikkalasi orasidagi xabarlar)
- GET /api/chat/count — o'qilmaganlar soni (sender bo'yicha guruhlangan)
"""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models import Count, Q

from apps.attachments.services import secure_upload
from apps.notifications.webpush import send_to_user as send_webpush_to_user
from apps.users.models import User

from .models import ChatMessage

logger = logging.getLogger(__name__)


def _send_ws(user_id, payload: dict) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    try:
        async_to_sync(layer.group_send)(f'chat_{user_id}', {
            'type': 'chat.message',
            'payload': payload,
        })
    except Exception as e:  # noqa: BLE001
        logger.warning(f'WS chat push xatosi (user={user_id}): {e}')


class ChatService:

    @classmethod
    @transaction.atomic
    def send(cls, *, sender: User, receiver_id, message: str = '', files: list | None = None) -> ChatMessage:
        if not (message or files):
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Xabar matni yoki fayl kerak")

        try:
            receiver = User.objects.get(pk=receiver_id, enabled=True)
        except User.DoesNotExist as exc:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'receiver_id': "Qabul qiluvchi topilmadi"}) from exc

        msg = ChatMessage.objects.create(
            sender=sender, receiver=receiver, message=(message or '').strip(),
        )

        # Fayllar
        if files:
            for f in files:
                att = secure_upload(f, target='chat-files')
                att.file_chat = msg
                att.save(update_fields=['file_chat'])

        # WS push receiver ga
        _send_ws(receiver.id, {
            'channel': 'chat',
            'from': str(sender.id),
            'message_id': str(msg.id),
            'message': msg.message,
            'created_at': msg.created_at.isoformat(),
        })

        # Web Push (tab yopiq/blur bo'lganda OS bildirishnomasi)
        try:
            sender_name = ' '.join(filter(None, [sender.last_name, sender.first_name])).strip() \
                or sender.username
            preview = (msg.message or ('📎 Fayl' if files else '')).strip()[:140]
            send_webpush_to_user(
                receiver.id,
                title=sender_name,
                body=preview,
                url=f'/?openChat={sender.id}',
                tag=f'chat-{sender.id}',
                data={'channel': 'chat', 'sender_id': str(sender.id), 'skipIfFocused': True},
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f'Chat web push xatosi: {e}')

        return msg

    @staticmethod
    def history_qs(user: User, partner_id):
        """Ikki user orasidagi xabarlar (chronological reverse — eng yangisi avval)."""
        return ChatMessage.objects.filter(
            (Q(sender=user) & Q(receiver_id=partner_id))
            | (Q(receiver=user) & Q(sender_id=partner_id))
        ).select_related('sender', 'receiver').prefetch_related('files')

    @staticmethod
    def unread_count_total(user: User) -> int:
        return ChatMessage.objects.filter(receiver=user, viewed=False).count()

    @staticmethod
    def unread_count_by_sender(user: User) -> list[dict]:
        """Sender bo'yicha guruhlangan o'qilmaganlar (production CountDto.bySender)."""
        rows = (
            ChatMessage.objects
            .filter(receiver=user, viewed=False)
            .values('sender_id')
            .annotate(count=Count('id'))
            .order_by()
        )
        return [{'sender_id': str(r['sender_id']), 'count': r['count']} for r in rows]

    @staticmethod
    def mark_read(user: User, message_ids: list) -> int:
        """Ko'rsatilgan xabarlarni o'qilgan deb belgilash."""
        return ChatMessage.objects.filter(
            id__in=message_ids, receiver=user, viewed=False,
        ).update(viewed=True)

    @staticmethod
    def mark_thread_read(user: User, partner_id) -> int:
        """Ikki user orasidagi BARCHA o'qilmaganlarni read qilish."""
        return ChatMessage.objects.filter(
            sender_id=partner_id, receiver=user, viewed=False,
        ).update(viewed=True)
