from django.db import models


class RoleName(models.TextChoices):
    """Tashkiliy tuzilmaga moslangan rollar (2026 buyrug'i).

    Kontekst `chief` va `direction` orqali aniqlanadi:
    - YORDAMCHI kimning yordamchisi → chief (VAZIR yoki ORINBOSAR)
    - BOSHLIQ boshqarma yoki bo'lim boshlig'imi → Direction.kind
    """
    SUPER_ADMIN = 'SUPER_ADMIN', 'Super admin'
    ADMIN = 'ADMIN', 'Admin'
    VAZIR = 'VAZIR', 'Vazir'
    ORINBOSAR = 'ORINBOSAR', "Vazir o'rinbosari"
    YORDAMCHI = 'YORDAMCHI', 'Yordamchi'
    BOSHLIQ = 'BOSHLIQ', 'Boshliq'
    XODIM = 'XODIM', 'Xodim'


class UserStatus(models.TextChoices):
    """Foydalanuvchi holati. Production JAR'dagi qiymatlarga to'liq mos."""
    AT_WORK = 'AT_WORK', 'Ish joyida'
    ON_HOLIDAY = 'ON_HOLIDAY', "Ta'tilda"
    WORK_TRIP = 'WORK_TRIP', 'Komandirovkada'
    DISMISSED = 'DISMISSED', "Ishdan bo'shagan"
    IN_CHILDHOOD_RAISING = 'IN_CHILDHOOD_RAISING', 'Bola parvarishida'


class PhoneNumberType(models.TextChoices):
    """Qo'shimcha telefon raqami turi (production JAR'da PhoneDto'da)."""
    HOME = 'HOME', 'Uy'
    MOBILE = 'MOBILE', 'Mobil'
    OFFICE = 'OFFICE', 'Ish'
