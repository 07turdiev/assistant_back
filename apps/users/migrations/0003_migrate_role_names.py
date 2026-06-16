"""Eski rollarni yangi tuzilmaga ko'chirish.

- PREMIER_MINISTER → VAZIR
- VICE_MINISTER    → ORINBOSAR
- HEAD             → BOSHLIQ
- EMPLOYEE         → XODIM
- ASSISTANT_PREMIER + ASSISTANT → YORDAMCHI (birlashtiriladi)
"""
from django.db import migrations

RENAMES = {
    'PREMIER_MINISTER': ('VAZIR', 'Vazir', 'Министр'),
    'VICE_MINISTER': ('ORINBOSAR', "Vazir o'rinbosari", 'Замминистра'),
    'HEAD': ('BOSHLIQ', 'Boshliq', 'Руководитель'),
    'EMPLOYEE': ('XODIM', 'Xodim', 'Сотрудник'),
    'SUPER_ADMIN': ('SUPER_ADMIN', 'Super admin', 'Супер админ'),
    'ADMIN': ('ADMIN', 'Admin', 'Админ'),
}

ENSURE = [
    ('SUPER_ADMIN', 'Super admin', 'Супер админ'),
    ('ADMIN', 'Admin', 'Админ'),
    ('VAZIR', 'Vazir', 'Министр'),
    ('ORINBOSAR', "Vazir o'rinbosari", 'Замминистра'),
    ('YORDAMCHI', 'Yordamchi', 'Помощник'),
    ('BOSHLIQ', 'Boshliq', 'Руководитель'),
    ('XODIM', 'Xodim', 'Сотрудник'),
]


def forwards(apps, schema_editor):
    Role = apps.get_model('users', 'Role')
    User = apps.get_model('users', 'User')

    # 1) Oddiy qayta nomlash
    for old, (new, luz, lru) in RENAMES.items():
        Role.objects.filter(name=old).update(name=new, label_uz=luz, label_ru=lru)

    # 2) Ikkala yordamchi rolini bittaga birlashtirish
    yordamchi, _ = Role.objects.get_or_create(
        name='YORDAMCHI', defaults={'label_uz': 'Yordamchi', 'label_ru': 'Помощник'},
    )
    for old in ('ASSISTANT_PREMIER', 'ASSISTANT'):
        old_role = Role.objects.filter(name=old).first()
        if old_role and old_role.id != yordamchi.id:
            User.objects.filter(role=old_role).update(role=yordamchi)
            old_role.delete()

    # 3) Barcha yangi rollar mavjudligini kafolatlash
    for name, luz, lru in ENSURE:
        Role.objects.get_or_create(name=name, defaults={'label_uz': luz, 'label_ru': lru})


def backwards(apps, schema_editor):
    Role = apps.get_model('users', 'Role')
    reverse = {
        'VAZIR': ('PREMIER_MINISTER', 'Вазир', 'Министр'),
        'ORINBOSAR': ('VICE_MINISTER', 'Вазир ўринбосари', 'Замминистра'),
        'BOSHLIQ': ('HEAD', 'Бошлиқ', 'Руководитель'),
        'XODIM': ('EMPLOYEE', 'Ходим', 'Сотрудник'),
        'YORDAMCHI': ('ASSISTANT', 'Ёрдамчи', 'Помощник'),
    }
    for new, (old, luz, lru) in reverse.items():
        Role.objects.filter(name=new).update(name=old, label_uz=luz, label_ru=lru)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_role_name'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
