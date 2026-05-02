"""Boshlang'ich ma'lumotlar seed: rol, region/district, organisation, direction, test userlar."""
from datetime import date, datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.directions.models import Direction
from apps.events.models import Event, EventParticipant, PreEvent, Visitor
from apps.info.enums import EventType, NotificationType, Sphere  # noqa: F401
from apps.organisations.models import District, Organisation, Region
from apps.users.enums import RoleName
from apps.users.models import Role, User

ROLES = [
    ('SUPER_ADMIN', 'Супер Админ', 'Супер Админ'),
    ('PREMIER_MINISTER', 'Вазир', 'Министр'),
    ('VICE_MINISTER', 'Вазир ўринбосари', 'Замминистра'),
    ('ASSISTANT_PREMIER', 'Вазир ёрдамчиси', 'Помощник министра'),
    ('HEAD', 'Бошлиқ', 'Руководитель'),
    ('ASSISTANT', 'Ёрдамчи', 'Помощник'),
    ('ADMIN', 'Админ', 'Админ'),
    ('EMPLOYEE', 'Ходим', 'Сотрудник'),
]

REGIONS = [
    ('Toshkent shahri', 'город Ташкент'),
    ('Toshkent viloyati', 'Ташкентская область'),
]

DISTRICTS_TASHKENT_CITY = [
    ('Bektemir', 'Бектемир'),
    ('Chilonzor', 'Чиланзар'),
    ('Mirobod', 'Мирабад'),
    ('Mirzo Ulug\'bek', 'Мирзо-Улугбек'),
    ('Olmazor', 'Алмазар'),
    ('Sergeli', 'Сергели'),
    ('Shayxontohur', 'Шайхантахур'),
    ('Uchtepa', 'Учтепа'),
    ('Yakkasaroy', 'Яккасарай'),
    ('Yashnobod', 'Яшнабад'),
    ('Yunusobod', 'Юнусабад'),
]


class Command(BaseCommand):
    help = "Seed boshlang'ich ma'lumotlar (rol, region, organisation, test userlar)"

    @transaction.atomic
    def handle(self, *args, **options):
        self._seed_roles()
        regions = self._seed_regions()
        districts = self._seed_districts(regions[0])
        org = self._seed_organisation(districts[0] if districts else None)
        directions = self._seed_directions(org)
        self._seed_users(directions[0] if directions else None)
        self._seed_sample_events(directions[0] if directions else None)
        self.stdout.write(self.style.SUCCESS('Seed yakunlandi'))

    def _seed_sample_events(self, direction):
        """Sample events — kalendar UI ni sinash uchun."""
        if not direction:
            return
        if Event.objects.exists():
            self.stdout.write('Sample events allaqachon mavjud')
            return

        premier = User.objects.filter(role__name=RoleName.PREMIER_MINISTER).first()
        head = User.objects.filter(role__name=RoleName.HEAD).first()
        employee = User.objects.filter(role__name=RoleName.EMPLOYEE).first()
        if not premier:
            return

        today = timezone.localdate()
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)

        samples = [
            {
                'title': 'Vazirlik kengashi yig\'ilishi',
                'description': 'Oylik hisobotlar muhokamasi',
                'date': tomorrow,
                'start_time': time(10, 0),
                'end_time': time(12, 0),
                'address': 'Vazirlik bosh binosi, 3-qavat, Katta zal',
                'sphere': Sphere.CULTURAL_WORKS,
                'type': EventType.COLLECTION,
                'is_important': True,
                'speaker': premier,
                'participants': [u for u in [head, employee] if u],
            },
            {
                'title': 'Madaniyat sohasi muhokamasi',
                'description': 'Yangi madaniy loyihalar bo\'yicha',
                'date': next_week,
                'start_time': time(14, 30),
                'end_time': time(16, 0),
                'address': 'Konferens-zal',
                'sphere': Sphere.CULTURAL_WORKS,
                'type': EventType.DISCUSSION,
                'is_important': False,
                'speaker': premier,
                'participants': [u for u in [head] if u],
                'visitors': [
                    {'full_name': 'Karim Karimov', 'organisation_name': 'Madaniyat instituti', 'position': 'Direktor'},
                ],
            },
        ]

        for spec in samples:
            participants = spec.pop('participants', [])
            visitors = spec.pop('visitors', [])
            event = Event.objects.create(direction=direction, **spec)
            for u in participants:
                EventParticipant.objects.create(event=event, user=u)
            for v in visitors:
                Visitor.objects.create(event=event, **v)
            self.stdout.write(f'  + Event: {event.title}')

        # PreEvent ham 1 dona
        if not PreEvent.objects.exists():
            PreEvent.objects.create(
                title='Kelgusi tadbir loyihasi',
                description='Aniqlanmagan',
                date=today + timedelta(days=14),
                start_time=timezone.make_aware(datetime.combine(today + timedelta(days=14), time(9, 0))),
                end_time=timezone.make_aware(datetime.combine(today + timedelta(days=14), time(11, 0))),
            )
            self.stdout.write('  + PreEvent yaratildi')

    def _seed_roles(self):
        for name, uz, ru in ROLES:
            Role.objects.update_or_create(name=name, defaults={'label_uz': uz, 'label_ru': ru})
        self.stdout.write(f'Roles: {Role.objects.count()}')

    def _seed_regions(self):
        regions = []
        for uz, ru in REGIONS:
            r, _ = Region.objects.get_or_create(name_uz=uz, defaults={'name_ru': ru})
            regions.append(r)
        self.stdout.write(f'Regions: {Region.objects.count()}')
        return regions

    def _seed_districts(self, region):
        if not region:
            return []
        districts = []
        for uz, ru in DISTRICTS_TASHKENT_CITY:
            d, _ = District.objects.get_or_create(
                name_uz=uz, region=region, defaults={'name_ru': ru}
            )
            districts.append(d)
        self.stdout.write(f'Districts: {District.objects.count()}')
        return districts

    def _seed_organisation(self, district):
        org, _ = Organisation.objects.get_or_create(
            name_uz='Madaniyat va turizm vazirligi',
            defaults={
                'name_ru': 'Министерство культуры и туризма',
                'address_uz': 'Toshkent shahri',
                'address_ru': 'г. Ташкент',
                'phone_number': '+998711234567',
                'district': district,
            },
        )
        self.stdout.write(f'Organisation: {org}')
        return org

    def _seed_directions(self, org):
        if not org:
            return []
        root, _ = Direction.objects.get_or_create(
            name_uz='Vazir',
            organisation=org,
            parent=None,
            defaults={'name_ru': 'Министр'},
        )
        children_data = [
            ('Vazir kotibiyati', 'Секретариат министра'),
            ('Vazir protokol xizmati', 'Протокольная служба'),
            ('Sport va turizm rivojlantirish', 'Развитие спорта и туризма'),
        ]
        children = [root]
        for uz, ru in children_data:
            child, _ = Direction.objects.get_or_create(
                name_uz=uz,
                organisation=org,
                parent=root,
                defaults={'name_ru': ru},
            )
            children.append(child)
        self.stdout.write(f'Directions: {Direction.objects.count()}')
        return children

    def _seed_users(self, direction):
        seed_pwd = 'Admin12345!'
        roles = {r.name: r for r in Role.objects.all()}

        defaults_common = {
            'direction': direction,
            'enabled': True,
            'is_active': True,
        }

        seeds = [
            {
                'username': 'superadmin',
                'role': roles[RoleName.SUPER_ADMIN],
                'first_name': 'Super',
                'last_name': 'Admin',
                'is_staff': True,
                'is_superuser': True,
                'position_uz': 'Tizim administratori',
                'position_ru': 'Системный администратор',
            },
            {
                'username': 'premier',
                'role': roles[RoleName.PREMIER_MINISTER],
                'first_name': 'Premier',
                'last_name': 'Minister',
                'position_uz': 'Vazir',
                'position_ru': 'Министр',
            },
            {
                'username': 'vice1',
                'role': roles[RoleName.VICE_MINISTER],
                'first_name': 'Vice',
                'last_name': 'Minister',
                'position_uz': "Vazir o'rinbosari",
                'position_ru': 'Замминистра',
            },
            {
                'username': 'admin1',
                'role': roles[RoleName.ADMIN],
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True,
                'position_uz': 'Admin',
                'position_ru': 'Админ',
            },
            {
                'username': 'head1',
                'role': roles[RoleName.HEAD],
                'first_name': 'Head',
                'last_name': 'User',
                'position_uz': "Bo'lim boshlig'i",
                'position_ru': 'Начальник отдела',
            },
            {
                'username': 'employee1',
                'role': roles[RoleName.EMPLOYEE],
                'first_name': 'Employee',
                'last_name': 'One',
                'position_uz': 'Xodim',
                'position_ru': 'Сотрудник',
            },
        ]

        for spec in seeds:
            user, created = User.objects.get_or_create(
                username=spec['username'],
                defaults={**defaults_common, **{k: v for k, v in spec.items() if k != 'username'}},
            )
            if created:
                user.set_password(seed_pwd)
                user.save()
                self.stdout.write(f'  + {user.username} ({user.role.name})')
            else:
                self.stdout.write(f'    {user.username} (mavjud)')

        self.stdout.write(self.style.WARNING(f"Seed userlar paroli: {seed_pwd}"))
