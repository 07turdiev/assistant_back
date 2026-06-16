from django.db import models


class DirectionKind(models.TextChoices):
    """Tashkiliy birlik turi (chart bo'yicha)."""
    BOSHQARMA = 'BOSHQARMA', 'Boshqarma'
    BOLIM = 'BOLIM', "Bo'lim"
    XIZMAT = 'XIZMAT', 'Xizmat'
    MUTAXASSIS = 'MUTAXASSIS', 'Yakka mutaxassis'
    KOTIBIYAT = 'KOTIBIYAT', 'Kotibiyat'
    BOSHQA = 'BOSHQA', 'Boshqa'
