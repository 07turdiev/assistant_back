from django.db import models
from mptt.models import MPTTModel, TreeForeignKey

from apps.core.models import AuditMixin

from .enums import DirectionKind


class Direction(MPTTModel, AuditMixin):
    name_uz = models.CharField(max_length=255)
    name_ru = models.CharField(max_length=255)
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.PROTECT,
        related_name='directions',
    )
    parent = TreeForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='children',
    )

    # Birlik turi (boshqarma / bo'lim / xizmat / yakka mutaxassis)
    kind = models.CharField(
        max_length=16, choices=DirectionKind.choices, default=DirectionKind.BOLIM,
    )
    # MA'SUL SHAXS — bo'lim/boshqarma boshlig'i. Tadbirga shu qo'shiladi.
    head = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='headed_directions',
    )
    # Bu yo'nalish qaysi o'rinbosar (yoki vazir) tasarrufida — ko'rinish/filtrlash uchun
    supervisor = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='supervised_directions',
    )

    class MPTTMeta:
        order_insertion_by = ['name_uz']

    def __str__(self) -> str:
        return self.name_uz
