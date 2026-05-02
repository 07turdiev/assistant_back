"""Fayl yuklash xavfsizlik logikasi (production AttachmentServiceImpl ekvivalenti)."""
import time
from pathlib import Path

import filetype
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from rest_framework.exceptions import ValidationError

from .models import Attachment

# Production whitelist — tika orqali aniqlanadigan content type'lar
ALLOWED_CONTENT_TYPES: set[str] = {
    'image/jpeg',
    'image/png',
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
    'application/vnd.ms-excel',                                            # .xls
    'application/msword',                                                  # .doc
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
}

MAX_FILE_NAME_LENGTH = 100
MAX_SIZE_MB = 50

# Folder ↔ target mapping
TARGETS = {
    'documents': 'documents',
    'protocols': 'protocols',
    'chat-files': 'chat-files',
    'photos': 'photos',
}


def _detect_content_type(file: UploadedFile) -> str:
    """Magic bytes asosida content type. Fallback: file.content_type."""
    head = file.read(2048)
    file.seek(0)
    kind = filetype.guess(head)
    if kind:
        return kind.mime
    return file.content_type or 'application/octet-stream'


def secure_upload(file: UploadedFile, target: str) -> Attachment:
    """Faylni xavfsiz tekshirib diskka saqlaydi va Attachment yozuvini yaratadi.

    Production'dagi `AttachmentServiceImpl.upload` mantiqi:
    1. Fayl nomini uzunligini tekshirish (52 dan kam)
    2. Tika orqali content type aniqlash (extension'ga ishonmaslik)
    3. Whitelist tekshirish
    4. Random nom (timestamp + ext) bilan saqlash
    """
    if target not in TARGETS:
        raise ValidationError(f"Noto'g'ri target: {target}")

    if not file.name or len(file.name) > MAX_FILE_NAME_LENGTH:
        raise ValidationError("Fayl nomi haddan tashqari uzun")

    if file.size > MAX_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"Fayl hajmi {MAX_SIZE_MB} MB dan oshmasligi kerak")

    detected = _detect_content_type(file)
    if detected not in ALLOWED_CONTENT_TYPES:
        raise ValidationError(f"Ruxsat berilmagan fayl turi: {detected}")

    ext = Path(file.name).suffix.lower()
    random_name = f"{int(time.time() * 1000)}{ext}"
    target_dir = Path(settings.MEDIA_ROOT) / target
    target_dir.mkdir(parents=True, exist_ok=True)
    save_path = target_dir / random_name

    with open(save_path, 'wb') as f:
        for chunk in file.chunks():
            f.write(chunk)

    return Attachment.objects.create(
        file_name=file.name,
        random_name=random_name,
        path=f"{target}/",
        content_type=detected,
        size=save_path.stat().st_size,
    )


def upload_many(files: list[UploadedFile], target: str) -> list[Attachment]:
    return [secure_upload(f, target) for f in files]


def remove_attachment(att: Attachment) -> None:
    """Diskdan fayl + DB yozuvini o'chirish."""
    file_path = Path(settings.MEDIA_ROOT) / att.path / att.random_name
    if file_path.exists():
        try:
            file_path.unlink()
        except OSError:
            pass
    att.delete()
