"""Fayl yuklab olish endpoint."""
from pathlib import Path

from django.conf import settings
from django.db.models import Q
from django.http import FileResponse, Http404
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .models import Attachment


def _user_can_access(user, att: Attachment) -> bool:
    """Foydalanuvchi shu attachment'ga tegishli obyektga (event/chat) kirish huquqi bormi."""
    # Super-admin, Django superuser va ADMIN — har qanday faylga kira oladi
    role_name = getattr(getattr(user, 'role', None), 'name', None)
    if user.is_superuser or role_name in ('SUPER_ADMIN', 'ADMIN'):
        return True

    # Event fayli (file_event yoki protocol_event)
    event = att.file_event or att.protocol_event
    if event is not None:
        # Yopiq tadbir bo'lsa — faqat speaker/participant/created_by ko'ra oladi
        if event.is_private:
            return (
                event.speaker_id == user.id
                or event.created_by_id == user.id
                or event.participant_links.filter(user_id=user.id).exists()
            )
        # Ochiq tadbir — autentifikatsiyalangan har kim ko'ra oladi
        return True

    # Chat xabari fayli — faqat suhbat ishtirokchilari (sender/receiver)
    chat_msg = att.file_chat
    if chat_msg is not None:
        return chat_msg.sender_id == user.id or chat_msg.receiver_id == user.id

    # Hech qanday parent obyektga bog'lanmagan fayl (yetim) — faqat yuklagan/superadmin
    return att.created_by_id == user.id


class FileDownloadView(APIView):
    """`GET /api/file/{id}/` — fayl yuklab olish, kirish huquqi tekshiruvi bilan.

    Mantiq:
    - Event faylida (ochiq tadbir): har bir autentifikatsiyalangan foydalanuvchi
    - Yopiq tadbir fayli: faqat speaker/participant/created_by
    - Chat fayli: faqat sender/receiver
    - SUPER_ADMIN/ADMIN/superuser: hammasi
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        att = (
            Attachment.objects
            .select_related('file_event', 'protocol_event', 'file_chat')
            .filter(pk=pk)
            .first()
        )
        if not att:
            raise Http404
        if not _user_can_access(request.user, att):
            raise PermissionDenied('Bu faylga kirish huquqingiz yo\'q')

        full_path = Path(settings.MEDIA_ROOT) / att.path / att.random_name
        if not full_path.exists():
            raise Http404('Fayl diskda topilmadi')

        response = FileResponse(open(full_path, 'rb'), content_type=att.content_type)
        # Filename'ni quote qilamiz — qo'shtirnoq inji'da bo'lsa header buziladi
        safe_name = att.file_name.replace('"', "'")
        response['Content-Disposition'] = f'attachment; filename="{safe_name}"'
        return response
