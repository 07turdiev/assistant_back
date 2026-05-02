"""Lookup enum'lar — events/reports apps yaratilguncha bu yerda yashaydi.

Qiymatlar production `assistant.jar` dan to'liq ko'chirilgan (mavjud ma'lumotlar bilan
mos kelishi shart).
"""
from django.db import models


class Sphere(models.TextChoices):
    """27 ta soha — production JAR Sphere enum'iga to'liq mos."""
    FUNDAMENTALS_OF_PUBLIC_ADMINISTRATION = 'FUNDAMENTALS_OF_PUBLIC_ADMINISTRATION', 'Davlat boshqaruvi asoslari'
    CIVIL_LAW = 'CIVIL_LAW', 'Fuqarolik huquqi'
    FAMILY = 'FAMILY', 'Oila'
    LABOR_AND_EMPLOYMENT_OF_THE_POPULATION = 'LABOR_AND_EMPLOYMENT_OF_THE_POPULATION', 'Mehnat va aholi bandligi'
    SOCIAL_SECURITY_SOCIAL_INSURANCE_AND_SOCIAL_PROTECTION = 'SOCIAL_SECURITY_SOCIAL_INSURANCE_AND_SOCIAL_PROTECTION', "Ijtimoiy ta'minot, sug'urta va himoya"
    FINANCIAL_RELATIONS = 'FINANCIAL_RELATIONS', 'Moliya munosabatlari'
    BANKING_ACTIVITIES = 'BANKING_ACTIVITIES', 'Bank faoliyati'
    HOUSEHOLD = 'HOUSEHOLD', 'Maishiy'
    UTILITIES = 'UTILITIES', 'Kommunal xizmatlar'
    BUSINESS_ACTIVITIES = 'BUSINESS_ACTIVITIES', 'Tadbirkorlik'
    HOUSEWIFELY_ACTIVITY = 'HOUSEWIFELY_ACTIVITY', "Uy xo'jaligi"
    ECONOMIC_ACTIVITY = 'ECONOMIC_ACTIVITY', 'Iqtisodiy faoliyat'
    CUSTOMS_ACTIVITIES = 'CUSTOMS_ACTIVITIES', 'Bojxona'
    ECOLOGY_AND_ENVIRONMENT_PROTECTION = 'ECOLOGY_AND_ENVIRONMENT_PROTECTION', 'Ekologiya va atrof-muhitni muhofaza qilish'
    SPHERE_OF_INFORMATION_TECHNOLOGY_AND_COMMUNICATIONS = 'SPHERE_OF_INFORMATION_TECHNOLOGY_AND_COMMUNICATIONS', 'AKT sohasi'
    EDUCATION_SCIENCE = 'EDUCATION_SCIENCE', "Ta'lim, fan"
    CULTURAL_WORKS = 'CULTURAL_WORKS', 'Madaniyat ishlari'
    WORK_ON_PHYSICAL_CULTURE_AND_SPORTS = 'WORK_ON_PHYSICAL_CULTURE_AND_SPORTS', 'Jismoniy tarbiya va sport'
    HEALTH_CARE_SECTOR = 'HEALTH_CARE_SECTOR', "Sog'liqni saqlash"
    TOURIST_ACTIVITIES = 'TOURIST_ACTIVITIES', 'Turizm'
    ARMED_FORCES_DEFENSE = 'ARMED_FORCES_DEFENSE', 'Qurolli kuchlar, mudofaa'
    ENSURING_SECURITY_AND_LAW_AND_ORDER = 'ENSURING_SECURITY_AND_LAW_AND_ORDER', 'Xavfsizlik va huquq tartibot'
    JUDICIAL_BRANCH = 'JUDICIAL_BRANCH', 'Sud hokimiyati'
    ACTIVITIES_OF_THE_PROSECUTORS_OFFICE = 'ACTIVITIES_OF_THE_PROSECUTORS_OFFICE', 'Prokuratura faoliyati'
    JUSTICE_BODIES = 'JUSTICE_BODIES', 'Adliya organlari'
    INTERNATIONAL_RELATIONS_INTERNATIONAL_LAW = 'INTERNATIONAL_RELATIONS_INTERNATIONAL_LAW', 'Xalqaro munosabatlar, xalqaro huquq'
    VARIOUS_QUESTIONS = 'VARIOUS_QUESTIONS', 'Boshqa savollar'


class EventType(models.TextChoices):
    """Tadbir turi — production'da PascalCase saqlanadi (UPPERCASE EMAS!)."""
    COLLECTION = 'Collection', "Yig'ilish"
    PRESIDIUM = 'Presidium', 'Prezidium'
    SELECTOR = 'Selector', 'Selektor'
    DISCUSSION = 'Discussion', 'Muhokama'
    PRESENTATION = 'Presentation', 'Taqdimot'
    MEETING = 'Meeting', 'Uchrashuv'
    FORUM = 'Forum', 'Forum'
    SEMINAR = 'Seminar', 'Seminar'


REPLY_CHOICES = [
    ('REJECTED', {'label_uz': 'Rad etildi', 'label_ru': 'Отклонено', 'reply_for': 'TASK', 'color': '#f56c6c'}),
    ('MUST_REJECT', {'label_uz': 'Rad etilishi kerak', 'label_ru': 'Подлежит отклонению', 'reply_for': 'REQUEST', 'color': '#e6a23c'}),
    ('BY_PHONE', {'label_uz': 'Telefon orqali', 'label_ru': 'По телефону', 'reply_for': 'BOTH', 'color': '#909399'}),
    ('QUICKLY', {'label_uz': 'Tezda', 'label_ru': 'Срочно', 'reply_for': 'BOTH', 'color': '#67c23a'}),
    ('EXECUTE', {'label_uz': 'Bajarish kerak', 'label_ru': 'Выполнить', 'reply_for': 'TASK', 'color': '#409eff'}),
]


class NotificationType(models.TextChoices):
    """Bildirishnoma turi (production NotificationType bilan mos)."""
    NEW = 'NEW', 'Yangi'
    EDITED = 'EDITED', "O'zgartirildi"
    DELETED = 'DELETED', 'Bekor qilindi'
    REMINDED = 'REMINDED', 'Eslatma'
    PRE_EVENT = 'PRE_EVENT', "Boshlang'ich tadbir"


class TgState(models.TextChoices):
    """Telegram bot FSM holati (production TgState bilan mos)."""
    AUTHENTICATED = 'AUTHENTICATED', "Autentifikatsiya o'tilgan"
    FIRST_STATE = 'FIRST_STATE', 'Login kutilmoqda'
    SECOND_STATE = 'SECOND_STATE', 'Parol kutilmoqda'
