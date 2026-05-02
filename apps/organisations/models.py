from django.db import models
from mptt.models import MPTTModel, TreeForeignKey

from apps.core.models import AuditMixin


class Region(models.Model):
    name_uz = models.CharField(max_length=255)
    name_ru = models.CharField(max_length=255)

    class Meta:
        ordering = ['name_uz']

    def __str__(self) -> str:
        return self.name_uz


class District(models.Model):
    name_uz = models.CharField(max_length=255)
    name_ru = models.CharField(max_length=255)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='districts')

    class Meta:
        ordering = ['region__name_uz', 'name_uz']

    def __str__(self) -> str:
        return self.name_uz


class Organisation(MPTTModel, AuditMixin):
    name_uz = models.CharField(max_length=255)
    name_ru = models.CharField(max_length=255)
    address_uz = models.CharField(max_length=255, blank=True, default='')
    address_ru = models.CharField(max_length=255, blank=True, default='')
    phone_number = models.CharField(max_length=64, blank=True, default='')
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    district = models.ForeignKey(
        District, on_delete=models.PROTECT, related_name='organisations',
        null=True, blank=True,
    )
    parent = TreeForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='children',
    )

    class MPTTMeta:
        order_insertion_by = ['name_uz']

    def __str__(self) -> str:
        return self.name_uz
