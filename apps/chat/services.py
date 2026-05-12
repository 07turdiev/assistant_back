"""Chat biznes mantig'i — production `ChatServiceImpl` ekvivalenti.

Production behavior:
- POST /api/chat (multipart) → DB ga yozish + WebSocket push receiver'ga
- GET /api/chat?receiverId — sahifali tarix (ikkalasi orasidagi xabarlar)
- GET /api/chat/count — o'qilmaganlar soni (sender bo'yicha guruhlangan)
"""
import html
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import transaction
from django.db.models import Count, Max, Q
from django.utils import timezone

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

        # Sender ism va xabar previewi — web push va telegram'da ishlatiladi
        sender_name = ' '.join(filter(None, [sender.last_name, sender.first_name])).strip() \
            or sender.username
        preview = (msg.message or ('📎 Fayl' if files else '')).strip()[:140]

        # Sender avatar — bildirishnomada sayt logosi o'rniga ko'rsatiladi.
        # OS notification icon'i absolyut URL kutadi (push servisi alohida domenda).
        sender_avatar_url = ''
        if sender.avatar:
            base = getattr(settings, 'FRONTEND_BASE_URL', '').rstrip('/')
            sender_avatar_url = f'{base}{sender.avatar.url}' if base else sender.avatar.url

        # Web Push (tab yopiq/blur bo'lganda OS bildirishnomasi)
        try:
            send_webpush_to_user(
                receiver.id,
                title=sender_name,
                body=preview,
                url=f'/?openChat={sender.id}',
                tag=f'chat-{sender.id}',
                icon=sender_avatar_url,
                data={'channel': 'chat', 'sender_id': str(sender.id), 'skipIfFocused': True},
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f'Chat web push xatosi: {e}')

        # Telegram bildirishnoma — receiver botga ulangan bo'lsa
        # `CHAT_TELEGRAM_NOTIFY=False` qilib settings'da o'chirib qo'yish mumkin
        if (
            getattr(settings, 'CHAT_TELEGRAM_NOTIFY', True)
            and receiver.telegram_id
        ):
            try:
                from apps.telegram_bot.notify import send_message as send_tg
                # HTML escape — sender ismi yoki xabar matnida `<`, `>`, `&` bo'lsa
                safe_sender = html.escape(sender_name)
                safe_preview = html.escape(preview) if preview else '📎 Fayl'
                # Saytda ochish uchun chuqurlikdagi link (bot xabarni Markdown'siz yuboradi)
                deep_link = (
                    f'{settings.FRONTEND_BASE_URL}/?openChat={sender.id}'
                    if getattr(settings, 'FRONTEND_BASE_URL', '')
                    else ''
                )
                text = f'💬 <b>{safe_sender}</b>\n\n{safe_preview}'
                if deep_link:
                    text += f'\n\n<a href="{deep_link}">Saytda ochish</a>'
                send_tg(receiver.telegram_id, text, parse_mode='HTML')
            except Exception as e:  # noqa: BLE001
                logger.warning(f'Chat TG dispatch xatosi: {e}')

        return msg

    @staticmethod
    def history_qs(user: User, partner_id):
        """Ikki user orasidagi xabarlar (chronological reverse — eng yangisi avval).

        Soft-delete bilan o'chirilgan xabarlar foydalanuvchilarga ko'rinmaydi.
        """
        return ChatMessage.objects.filter(
            is_deleted=False,
        ).filter(
            (Q(sender=user) & Q(receiver_id=partner_id))
            | (Q(receiver=user) & Q(sender_id=partner_id))
        ).select_related('sender', 'receiver').prefetch_related('files')

    @staticmethod
    def admin_conversation_qs(user_a_id, user_b_id):
        """SUPER_ADMIN uchun istalgan ikki foydalanuvchi orasidagi suhbat.

        O'chirilgan xabarlarni HAM ko'rsatadi (audit uchun) — frontend ularni
        belgilab ko'rsatadi (is_deleted=True).
        """
        return ChatMessage.objects.filter(
            (Q(sender_id=user_a_id) & Q(receiver_id=user_b_id))
            | (Q(sender_id=user_b_id) & Q(receiver_id=user_a_id))
        ).select_related('sender', 'receiver', 'deleted_by').prefetch_related('files')

    @staticmethod
    def admin_threads(*, search: str = '', limit: int = 200) -> list[dict]:
        """Tizimdagi barcha suhbat juftliklari (eng yangisi avval).

        Har bir element: user_a, user_b (ID lar tartibli), last_message_at, total_count.
        Filter `search` — har ikki tomonning ism/familiya/username bo'yicha.
        """
        from django.db.models.functions import Least, Greatest
        qs = ChatMessage.objects.all()
        if search:
            qs = qs.filter(
                Q(sender__first_name__icontains=search)
                | Q(sender__last_name__icontains=search)
                | Q(sender__username__icontains=search)
                | Q(receiver__first_name__icontains=search)
                | Q(receiver__last_name__icontains=search)
                | Q(receiver__username__icontains=search)
            )
        rows = (
            qs.annotate(
                u1=Least('sender_id', 'receiver_id'),
                u2=Greatest('sender_id', 'receiver_id'),
            )
            .values('u1', 'u2')
            .annotate(last_at=Max('created_at'), total=Count('id'))
            .order_by('-last_at')[:limit]
        )
        return [
            {
                'user_a_id': str(r['u1']),
                'user_b_id': str(r['u2']),
                'last_message_at': r['last_at'].isoformat() if r['last_at'] else None,
                'total': r['total'],
            }
            for r in rows
        ]

    @staticmethod
    @transaction.atomic
    def soft_delete(*, message: ChatMessage, by_user: User) -> ChatMessage:
        """Habarni soft-delete qilib, ikki tomonga WS signal yuboradi."""
        if message.is_deleted:
            return message
        message.is_deleted = True
        message.deleted_at = timezone.now()
        message.deleted_by = by_user
        message.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by', 'updated_at'])

        payload = {
            'channel': 'chat',
            'event': 'deleted',
            'message_id': str(message.id),
            'sender_id': str(message.sender_id),
            'receiver_id': str(message.receiver_id),
        }
        _send_ws(message.sender_id, payload)
        _send_ws(message.receiver_id, payload)
        return message

    @staticmethod
    def unread_count_total(user: User) -> int:
        return ChatMessage.objects.filter(
            receiver=user, viewed=False, is_deleted=False,
        ).count()

    @staticmethod
    def unread_count_by_sender(user: User) -> list[dict]:
        """Sender bo'yicha guruhlangan o'qilmaganlar (production CountDto.bySender)."""
        rows = (
            ChatMessage.objects
            .filter(receiver=user, viewed=False, is_deleted=False)
            .values('sender_id')
            .annotate(count=Count('id'))
            .order_by()
        )
        return [{'sender_id': str(r['sender_id']), 'count': r['count']} for r in rows]

    @staticmethod
    def mark_read(user: User, message_ids: list) -> int:
        """Ko'rsatilgan xabarlarni o'qilgan deb belgilash."""
        return ChatMessage.objects.filter(
            id__in=message_ids, receiver=user, viewed=False, is_deleted=False,
        ).update(viewed=True)

    @staticmethod
    def mark_thread_read(user: User, partner_id) -> int:
        """Ikki user orasidagi BARCHA o'qilmaganlarni read qilish."""
        return ChatMessage.objects.filter(
            sender_id=partner_id, receiver=user, viewed=False, is_deleted=False,
        ).update(viewed=True)
