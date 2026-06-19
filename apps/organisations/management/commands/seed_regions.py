"""Vaqtinchalik seed: O'zbekiston viloyatlari va tumanlarini qo'shadi.

Ishlatish:
    python manage.py seed_regions

Idempotent — qayta ishga tushirsa dublikat yaratmaydi (name bo'yicha get_or_create).
Hudud/tuman tarkibi vaqt o'tishi bilan o'zgaradi — ro'yxatni kerak bo'lsa shu yerda
yangilab, qayta ishga tushiring. Kerak bo'lmasa bu faylni o'chirib tashlasa bo'ladi.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.organisations.models import District, Region

# (region_uz, region_ru, [(district_uz, district_ru), ...])
REGIONS: list[tuple[str, str, list[tuple[str, str]]]] = [
    ("Qoraqalpog'iston Respublikasi", "Республика Каракалпакстан", [
        ("Amudaryo", "Амударьинский"),
        ("Beruniy", "Берунийский"),
        ("Bo'zatov", "Бозатауский"),
        ("Chimboy", "Чимбайский"),
        ("Ellikqal'a", "Элликкалинский"),
        ("Kegeyli", "Кегейлийский"),
        ("Mo'ynoq", "Муйнакский"),
        ("Nukus tumani", "Нукусский"),
        ("Qanliko'l", "Канлыкульский"),
        ("Qo'ng'irot", "Кунградский"),
        ("Qorao'zak", "Караузякский"),
        ("Shumanay", "Шуманайский"),
        ("Taxtako'pir", "Тахтакупырский"),
        ("To'rtko'l", "Турткульский"),
        ("Xo'jayli", "Ходжейлийский"),
        ("Nukus shahri", "город Нукус"),
        ("Taxiatosh", "Тахиаташ"),
    ]),
    ("Andijon viloyati", "Андижанская область", [
        ("Andijon", "Андижанский"),
        ("Asaka", "Асакинский"),
        ("Baliqchi", "Балыкчинский"),
        ("Bo'z", "Бозский"),
        ("Buloqboshi", "Булакбашинский"),
        ("Izboskan", "Избасканский"),
        ("Jalaquduq", "Джалакудукский"),
        ("Xo'jaobod", "Ходжаабадский"),
        ("Qo'rg'ontepa", "Кургантепинский"),
        ("Marhamat", "Мархаматский"),
        ("Oltinko'l", "Алтынкульский"),
        ("Paxtaobod", "Пахтаабадский"),
        ("Shahrixon", "Шахриханский"),
        ("Ulug'nor", "Улугнорский"),
        ("Andijon shahri", "город Андижан"),
        ("Xonobod shahri", "город Ханабад"),
    ]),
    ("Buxoro viloyati", "Бухарская область", [
        ("Buxoro", "Бухарский"),
        ("Vobkent", "Вабкентский"),
        ("G'ijduvon", "Гиждуванский"),
        ("Jondor", "Жондорский"),
        ("Kogon", "Каганский"),
        ("Olot", "Алатский"),
        ("Peshku", "Пешкунский"),
        ("Qorako'l", "Каракульский"),
        ("Qorovulbozor", "Караулбазарский"),
        ("Romitan", "Ромитанский"),
        ("Shofirkon", "Шафирканский"),
        ("Buxoro shahri", "город Бухара"),
        ("Kogon shahri", "город Каган"),
    ]),
    ("Jizzax viloyati", "Джизакская область", [
        ("Arnasoy", "Арнасайский"),
        ("Baxmal", "Бахмальский"),
        ("Do'stlik", "Дустликский"),
        ("Forish", "Фаришский"),
        ("G'allaorol", "Галляаральский"),
        ("Sharof Rashidov", "Шараф-Рашидовский"),
        ("Zarbdor", "Зарбдарский"),
        ("Zafarobod", "Зафарабадский"),
        ("Zomin", "Зааминский"),
        ("Mirzacho'l", "Мирзачульский"),
        ("Paxtakor", "Пахтакорский"),
        ("Yangiobod", "Янгиабадский"),
        ("Jizzax shahri", "город Джизак"),
    ]),
    ("Qashqadaryo viloyati", "Кашкадарьинская область", [
        ("G'uzor", "Гузарский"),
        ("Dehqonobod", "Дехканабадский"),
        ("Qamashi", "Камашинский"),
        ("Qarshi", "Каршинский"),
        ("Kasbi", "Касбийский"),
        ("Kitob", "Китабский"),
        ("Koson", "Касанский"),
        ("Mirishkor", "Миришкорский"),
        ("Muborak", "Мубарекский"),
        ("Nishon", "Нишанский"),
        ("Chiroqchi", "Чиракчинский"),
        ("Shahrisabz", "Шахрисабзский"),
        ("Yakkabog'", "Яккабагский"),
        ("Qarshi shahri", "город Карши"),
        ("Shahrisabz shahri", "город Шахрисабз"),
    ]),
    ("Navoiy viloyati", "Навоийская область", [
        ("Konimex", "Канимехский"),
        ("Karmana", "Карманинский"),
        ("Qiziltepa", "Кызылтепинский"),
        ("Navbahor", "Навбахорский"),
        ("Nurota", "Нуратинский"),
        ("Tomdi", "Тамдынский"),
        ("Uchquduq", "Учкудукский"),
        ("Xatirchi", "Хатырчинский"),
        ("Navoiy shahri", "город Навои"),
        ("Zarafshon shahri", "город Зарафшан"),
    ]),
    ("Namangan viloyati", "Наманганская область", [
        ("Kosonsoy", "Касансайский"),
        ("Mingbuloq", "Мингбулакский"),
        ("Namangan", "Наманганский"),
        ("Norin", "Нарынский"),
        ("Pop", "Папский"),
        ("To'raqo'rg'on", "Туракурганский"),
        ("Uchqo'rg'on", "Учкурганский"),
        ("Uychi", "Уйчинский"),
        ("Chortoq", "Чартакский"),
        ("Chust", "Чустский"),
        ("Yangiqo'rg'on", "Янгикурганский"),
        ("Davlatobod", "Давлатабадский"),
        ("Namangan shahri", "город Наманган"),
    ]),
    ("Samarqand viloyati", "Самаркандская область", [
        ("Bulung'ur", "Булунгурский"),
        ("Ishtixon", "Иштыханский"),
        ("Jomboy", "Джамбайский"),
        ("Kattaqo'rg'on", "Каттакурганский"),
        ("Qo'shrabot", "Кошрабадский"),
        ("Narpay", "Нарпайский"),
        ("Nurobod", "Нурабадский"),
        ("Oqdaryo", "Акдарьинский"),
        ("Past Darg'om", "Пастдаргомский"),
        ("Paxtachi", "Пахтачийский"),
        ("Payariq", "Пайарыкский"),
        ("Samarqand", "Самаркандский"),
        ("Toyloq", "Тайлакский"),
        ("Urgut", "Ургутский"),
        ("Samarqand shahri", "город Самарканд"),
        ("Kattaqo'rg'on shahri", "город Каттакурган"),
    ]),
    ("Sirdaryo viloyati", "Сырдарьинская область", [
        ("Oqoltin", "Акалтынский"),
        ("Boyovut", "Баяутский"),
        ("Guliston", "Гулистанский"),
        ("Mirzaobod", "Мирзаабадский"),
        ("Sayxunobod", "Сайхунабадский"),
        ("Sardoba", "Сардобинский"),
        ("Sirdaryo", "Сырдарьинский"),
        ("Xovos", "Хавастский"),
        ("Guliston shahri", "город Гулистан"),
        ("Shirin shahri", "город Ширин"),
        ("Yangiyer shahri", "город Янгиер"),
    ]),
    ("Surxondaryo viloyati", "Сурхандарьинская область", [
        ("Angor", "Ангорский"),
        ("Bandixon", "Бандиханский"),
        ("Boysun", "Байсунский"),
        ("Denov", "Денауский"),
        ("Jarqo'rg'on", "Джаркурганский"),
        ("Qiziriq", "Кизирикский"),
        ("Qumqo'rg'on", "Кумкурганский"),
        ("Muzrabot", "Музрабадский"),
        ("Oltinsoy", "Алтынсайский"),
        ("Sariosiyo", "Сариасийский"),
        ("Sherobod", "Шерабадский"),
        ("Sho'rchi", "Шурчинский"),
        ("Termiz", "Термезский"),
        ("Uzun", "Узунский"),
        ("Termiz shahri", "город Термез"),
    ]),
    ("Farg'ona viloyati", "Ферганская область", [
        ("Beshariq", "Бешарыкский"),
        ("Bog'dod", "Багдадский"),
        ("Buvayda", "Бувайдинский"),
        ("Dang'ara", "Дангаринский"),
        ("Farg'ona", "Ферганский"),
        ("Furqat", "Фуркатский"),
        ("Qo'shtepa", "Куштепинский"),
        ("O'zbekiston", "Узбекистанский"),
        ("Oltiariq", "Алтыарыкский"),
        ("Quva", "Кувинский"),
        ("Rishton", "Риштанский"),
        ("So'x", "Сохский"),
        ("Toshloq", "Ташлакский"),
        ("Uchko'prik", "Учкуприкский"),
        ("Yozyovon", "Язъяванский"),
        ("Farg'ona shahri", "город Фергана"),
        ("Marg'ilon shahri", "город Маргилан"),
        ("Qo'qon shahri", "город Коканд"),
        ("Quvasoy shahri", "город Кувасай"),
    ]),
    ("Xorazm viloyati", "Хорезмская область", [
        ("Bog'ot", "Багатский"),
        ("Gurlan", "Гурленский"),
        ("Qo'shko'pir", "Кошкупырский"),
        ("Urganch", "Ургенчский"),
        ("Xazorasp", "Хазараспский"),
        ("Xonqa", "Ханкинский"),
        ("Xiva", "Хивинский"),
        ("Shovot", "Шаватский"),
        ("Yangiariq", "Янгиарыкский"),
        ("Yangibozor", "Янгибазарский"),
        ("Tuproqqal'a", "Тупраккалинский"),
        ("Urganch shahri", "город Ургенч"),
        ("Xiva shahri", "город Хива"),
    ]),
    ("Toshkent viloyati", "Ташкентская область", [
        ("Bekobod", "Бекабадский"),
        ("Bo'ka", "Букинский"),
        ("Bo'stonliq", "Бостанлыкский"),
        ("Chinoz", "Чиназский"),
        ("Qibray", "Кибрайский"),
        ("Ohangaron", "Ахангаранский"),
        ("Oqqo'rg'on", "Аккурганский"),
        ("Parkent", "Паркентский"),
        ("Piskent", "Пскентский"),
        ("Quyichirchiq", "Куйичирчикский"),
        ("O'rtachirchiq", "Уртачирчикский"),
        ("Toshkent tumani", "Ташкентский"),
        ("Yangiyo'l", "Янгиюльский"),
        ("Yuqorichirchiq", "Юкоричирчикский"),
        ("Zangiota", "Зангиатинский"),
        ("Nurafshon shahri", "город Нурафшан"),
        ("Olmaliq shahri", "город Алмалык"),
        ("Angren shahri", "город Ангрен"),
        ("Bekobod shahri", "город Бекабад"),
        ("Chirchiq shahri", "город Чирчик"),
        ("Yangiyo'l shahri", "город Янгиюль"),
    ]),
    ("Toshkent shahri", "город Ташкент", [
        ("Bektemir", "Бектемирский"),
        ("Chilonzor", "Чиланзарский"),
        ("Mirobod", "Мирабадский"),
        ("Mirzo Ulug'bek", "Мирзо-Улугбекский"),
        ("Olmazor", "Алмазарский"),
        ("Sergeli", "Сергелийский"),
        ("Shayxontohur", "Шайхантахурский"),
        ("Uchtepa", "Учтепинский"),
        ("Yakkasaroy", "Яккасарайский"),
        ("Yashnobod", "Яшнабадский"),
        ("Yunusobod", "Юнусабадский"),
        ("Yangihayot", "Янгихаётский"),
    ]),
]


class Command(BaseCommand):
    help = "O'zbekiston viloyatlari va tumanlarini qo'shadi (idempotent seed)."

    @transaction.atomic
    def handle(self, *args, **options):
        regions_created = 0
        districts_created = 0
        districts_updated = 0

        for region_uz, region_ru, districts in REGIONS:
            region, r_created = Region.objects.get_or_create(
                name_uz=region_uz,
                defaults={'name_ru': region_ru},
            )
            if r_created:
                regions_created += 1
            elif region.name_ru != region_ru:
                region.name_ru = region_ru
                region.save(update_fields=['name_ru'])

            for d_uz, d_ru in districts:
                district, d_created = District.objects.get_or_create(
                    region=region,
                    name_uz=d_uz,
                    defaults={'name_ru': d_ru},
                )
                if d_created:
                    districts_created += 1
                elif district.name_ru != d_ru:
                    district.name_ru = d_ru
                    district.save(update_fields=['name_ru'])
                    districts_updated += 1

        total_regions = Region.objects.count()
        total_districts = District.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Tayyor! Hudud: +{regions_created} yangi (jami {total_regions}). "
            f"Tuman: +{districts_created} yangi, {districts_updated} yangilandi "
            f"(jami {total_districts})."
        ))
