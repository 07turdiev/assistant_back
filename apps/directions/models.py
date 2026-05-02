from django.db import models
from mptt.models import MPTTModel, TreeForeignKey

from apps.core.models import AuditMixin


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

    class MPTTMeta:
        order_insertion_by = ['name_uz']

    def __str__(self) -> str:
        return self.name_uz
