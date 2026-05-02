"""Fayl yuklab olish endpoint."""
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .models import Attachment


class FileDownloadView(APIView):
    """`GET /api/file/{id}/` — autentifikatsiyalangan foydalanuvchilar uchun.

    Production'da xuddi shunday: faqat ID, ruxsat alohida tekshirilmaydi
    (URL'ni topish — kirish huquqini bilish demakdir, mantiq biznes ehtiyoji bilan).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            att = Attachment.objects.get(pk=pk)
        except Attachment.DoesNotExist as exc:
            raise Http404 from exc

        full_path = Path(settings.MEDIA_ROOT) / att.path / att.random_name
        if not full_path.exists():
            raise Http404('Fayl diskda topilmadi')

        response = FileResponse(open(full_path, 'rb'), content_type=att.content_type)
        response['Content-Disposition'] = f'attachment; filename="{att.file_name}"'
        return response
