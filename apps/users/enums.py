from django.db import models


class RoleName(models.TextChoices):
    SUPER_ADMIN = 'SUPER_ADMIN', 'Супер Админ'
    PREMIER_MINISTER = 'PREMIER_MINISTER', 'Вазир'
    VICE_MINISTER = 'VICE_MINISTER', 'Вазир ўринбосари'
    ASSISTANT_PREMIER = 'ASSISTANT_PREMIER', 'Вазир ёрдамчиси'
    HEAD = 'HEAD', 'Бошлиқ'
    ASSISTANT = 'ASSISTANT', 'Ёрдамчи'
    ADMIN = 'ADMIN', 'Админ'
    EMPLOYEE = 'EMPLOYEE', 'Ходим'


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
