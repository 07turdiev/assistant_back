"""Eski Report yozuvlarini `kind` bo'yicha to'g'ri belgilash.

0002 da `kind` default=TASK bilan qo'shildi. Lekin eski "so'rov" yozuvlari
(yordamchi tomonidan yuborilgan) aslida REQUEST bo'lgan. Ularni legacy REQUEST
deb belgilaymiz — shunda ular yangi "topshiriqlar" ro'yxatiga aralashmaydi.
"""
from django.db import migrations

ASSISTANT_ROLES = ('ASSISTANT', 'ASSISTANT_PREMIER')


def backfill_kind(apps, schema_editor):
    Report = apps.get_model('reports', 'Report')
    # Yordamchi yuborgan eski yozuvlar → legacy REQUEST
    Report.objects.filter(sender__role__name__in=ASSISTANT_ROLES).update(kind='REQUEST')
    # Qolganlari TASK bo'lib qoladi (0002 default)


def reverse_kind(apps, schema_editor):
    Report = apps.get_model('reports', 'Report')
    Report.objects.filter(kind='REQUEST').update(kind='TASK')


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0002_report_kind'),
    ]

    operations = [
        migrations.RunPython(backfill_kind, reverse_kind),
    ]
