"""Legacy frontend serving — JAR ichidagi Vue 2 SPA static fayllari.

Maqsad: foydalanuvchiga production'ning haqiqiy UI'sini ko'rsatish va Vue 3'da
piksel-piksel ko'chirib qurish uchun referens sifatida ishlatish.
"""
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.views.generic import View

LEGACY_DIR = Path(settings.BASE_DIR) / 'legacy_frontend'


class LegacyStaticView(View):
    """`/legacy/...` ostida JAR'dan kelgan static fayllarni serve qiladi."""

    def get(self, request, path: str = ''):
        # Default → index.html (SPA fallback)
        if not path or path.endswith('/'):
            target = LEGACY_DIR / 'index.html'
        else:
            target = LEGACY_DIR / path
            if not target.exists() or target.is_dir():
                # Vue Router fallback
                target = LEGACY_DIR / 'index.html'

        if not target.exists():
            raise Http404
        return FileResponse(open(target, 'rb'))


class LegacyAssetView(View):
    """`/static/...`, `/favicon.ico`, `/favicon-16x16.png` — legacy assetlari.

    Production'da bu yo'llar Spring static handler tomonidan xizmatlanardi.
    """

    def get(self, request, path: str):
        target = LEGACY_DIR / path
        if not target.exists() or target.is_dir():
            raise Http404
        # Content-Type'ni Django avtomatik aniqlaydi
        return FileResponse(open(target, 'rb'))
