"""Telegram bot xabarlari uchun ko'p tilli translation lug'ati.

Foydalanish:
    text = t('login.welcome', lang='ru', name='Ali')

Default til — `uz` (lotin). Foydalanuvchi locale'si Telegram `language_code`
asosida aniqlanadi (faqat 'ru' alohida ushlab olinadi, qolgani — uz).
"""
from __future__ import annotations

from typing import Literal

Lang = Literal['uz', 'uz-Cyrl', 'ru']

DEFAULT_LANG: Lang = 'uz'


def detect_lang(language_code: str | None) -> Lang:
    """Telegram user.language_code asosida — `'uz'`, `'uz-Cyrl'`, yoki `'ru'`."""
    if not language_code:
        return DEFAULT_LANG
    code = language_code.lower()
    if code.startswith('ru'):
        return 'ru'
    if code.startswith('uz') and ('cyr' in code or 'cy' in code):
        return 'uz-Cyrl'
    return 'uz'


# Barcha xabarlar shu yerda. Yangi til kerak bo'lsa shu joydan kengaytiriladi.
MESSAGES: dict[str, dict[Lang, str]] = {
    # ----- /start -----
    'start.welcome_back': {
        'uz': "Salom, {name}! Siz allaqachon tizimga kirgansiz ✅\n\n"
              "Pastdagi tugmalardan foydalaning yoki ovozli xabar yuboring.",
        'uz-Cyrl': "Салом, {name}! Сиз аллақачон тизимга кирғансиз ✅\n\n"
                   "Пастдаги тугмалардан фойдаланинг ёки овозли хабар юборинг.",
        'ru': "Здравствуйте, {name}! Вы уже авторизованы ✅\n\n"
              "Используйте кнопки ниже или отправьте голосовое сообщение.",
    },
    'start.greeting': {
        'uz': "Assalomu alaykum! 👋\n\nTizimga kirish uchun loginingizni yuboring:",
        'uz-Cyrl': "Ассалому алайкум! 👋\n\nТизимга кириш учун логинингизни юборинг:",
        'ru': "Здравствуйте! 👋\n\nВведите ваш логин для входа:",
    },

    # ----- Login flow -----
    'login.username_not_found': {
        'uz': "❌ Bunday login topilmadi.\nIltimos, loginingizni qayta tekshirib yuboring:",
        'uz-Cyrl': "❌ Бундай логин топилмади.\nИлтимос, логинингизни қайта текшириб юборинг:",
        'ru': "❌ Логин не найден.\nПроверьте и отправьте логин ещё раз:",
    },
    'login.password_prompt': {
        'uz': "🔑 Endi parolingizni kiriting:",
        'uz-Cyrl': "🔑 Энди паролингизни киритинг:",
        'ru': "🔑 Теперь введите пароль:",
    },
    'login.session_expired': {
        'uz': "Iltimos, /start buyrug'i orqali qaytadan boshlang.",
        'uz-Cyrl': "Илтимос, /start буйруғи орқали қайтадан бошланг.",
        'ru': "Пожалуйста, начните заново через /start.",
    },
    'login.password_wrong': {
        'uz': "❌ Parol noto'g'ri. Qaytadan kiriting (qolgan urinishlar: {remaining}):",
        'uz-Cyrl': "❌ Парол нотўғри. Қайтадан киритинг (қолган уринишлар: {remaining}):",
        'ru': "❌ Неверный пароль. Попробуйте снова (осталось попыток: {remaining}):",
    },
    'login.locked': {
        'uz': "🔒 Juda ko'p noto'g'ri urinish. Iltimos, {wait} kuting va qaytadan urining.",
        'uz-Cyrl': "🔒 Жуда кўп нотўғри уриниш. Илтимос, {wait} кутинг ва қайтадан уриниб кўринг.",
        'ru': "🔒 Слишком много неверных попыток. Подождите {wait} и попробуйте снова.",
    },
    'login.success': {
        'uz': "✅ Tizimga muvaffaqiyatli kirdingiz!\n\n"
              "Pastdagi tugmalardan foydalaning yoki ovozli xabar yuboring:\n"
              "🎤 Topshiriq berish — ovozli buyruq orqali topshiriq qoralamasini yarating\n"
              "📅 Tadbir yaratish — ovoz orqali tadbir qoralamasini tayyorlang\n\n"
              "Saytdagi to'liq ko'rinish: {url}",
        'uz-Cyrl': "✅ Тизимга муваффақиятли кирдингиз!\n\n"
                   "Пастдаги тугмалардан фойдаланинг ёки овозли хабар юборинг:\n"
                   "🎤 Топшириқ бериш — овозли буйруқ орқали топшириқ қораламасини яратинг\n"
                   "📅 Тадбир яратиш — овоз орқали тадбир қораламасини тайёрланг\n\n"
                   "Сайтдаги тўлиқ кўриниш: {url}",
        'ru': "✅ Вход выполнен!\n\n"
              "Используйте кнопки ниже или отправьте голосовое сообщение:\n"
              "🎤 Поручение — голосом создайте черновик поручения\n"
              "📅 Мероприятие — голосом подготовьте черновик мероприятия\n\n"
              "Полная версия на сайте: {url}",
    },

    # ----- Other -----
    'other.unknown_command': {
        'uz': "ℹ️ Buyruqni tushunmadim. Pastdagi tugmalardan foydalaning yoki /start orqali boshlang.",
        'uz-Cyrl': "ℹ️ Буйруқни тушунмадим. Пастдаги тугмалардан фойдаланинг ёки /start орқали бошланг.",
        'ru': "ℹ️ Команда не распознана. Используйте кнопки ниже или начните через /start.",
    },

    # ----- Voice flow -----
    'voice.need_login': {
        'uz': "Iltimos, avval /start orqali tizimga kiring.",
        'uz-Cyrl': "Илтимос, аввал /start орқали тизимга киринг.",
        'ru': "Пожалуйста, сначала войдите через /start.",
    },
    'voice.send_for_task': {
        'uz': "🎤 Topshiriq tafsilotlarini ovozli xabar shaklida yuboring.\n\n"
              "Misol: «Ertaga ish vaqti tugashiga qadar Aliyevdan hisobotni so'rang»",
        'uz-Cyrl': "🎤 Топшириқ тафсилотларини овозли хабар шаклида юборинг.\n\n"
                   "Мисол: «Эртага иш вақти тугашига қадар Алиевдан ҳисоботни сўранг»",
        'ru': "🎤 Отправьте детали поручения голосовым сообщением.\n\n"
              "Пример: «Завтра до конца рабочего дня запросите отчёт у Алиева»",
    },
    'voice.send_for_event': {
        'uz': "🎤 Tadbir tafsilotlarini ovozli xabar shaklida yuboring.\n\n"
              "Misol: «Ertaga soat 14 da Senat zalida kollegiya yig'ilishi, 90 daqiqa»",
        'uz-Cyrl': "🎤 Тадбир тафсилотларини овозли хабар шаклида юборинг.\n\n"
                   "Мисол: «Эртага соат 14 да Сенат залида коллегия йиғилиши, 90 дақиқа»",
        'ru': "🎤 Отправьте детали мероприятия голосовым сообщением.\n\n"
              "Пример: «Завтра в 14:00 в Сенат-зале коллегия, 90 минут»",
    },
    'voice.help': {
        'uz': "ℹ️ Yordamchi\n\n"
              "🎤 Topshiriq berish — ovozli xabar yuborib tezkor topshiriq bering\n"
              "📅 Tadbir yaratish — ovoz orqali tadbir qoralamasini tayyorlang\n\n"
              "Qoralamalar saytda tahrir qilinadi: {url}/drafts",
        'uz-Cyrl': "ℹ️ Ёрдамчи\n\n"
                   "🎤 Топшириқ бериш — овозли хабар юбориб тезкор топшириқ беринг\n"
                   "📅 Тадбир яратиш — овоз орқали тадбир қораламасини тайёрланг\n\n"
                   "Қораламалар сайтда таҳрир қилинади: {url}/drafts",
        'ru': "ℹ️ Помощь\n\n"
              "🎤 Поручение — отправьте голосовое сообщение для быстрого поручения\n"
              "📅 Мероприятие — голосом подготовьте черновик\n\n"
              "Черновики редактируются на сайте: {url}/drafts",
    },
    'voice.button_first': {
        'uz': "ℹ️ Ovozli xabar qabul qilish uchun avval pastdagi tugmalardan birini bosing.",
        'uz-Cyrl': "ℹ️ Овозли хабар қабул қилиш учун аввал пастдаги тугмалардан бирини босинг.",
        'ru': "ℹ️ Сначала нажмите одну из кнопок ниже, чтобы я мог принять голосовое сообщение.",
    },
    'voice.send_voice': {
        'uz': "Iltimos, ovozli xabar yuboring.",
        'uz-Cyrl': "Илтимос, овозли хабар юборинг.",
        'ru': "Пожалуйста, отправьте голосовое сообщение.",
    },
    'voice.processing': {
        'uz': "⏳ Ovoz yuklanmoqda va matnga aylantirilmoqda...",
        'uz-Cyrl': "⏳ Овоз юкланмоқда ва матнга айлантирилмоқда...",
        'ru': "⏳ Загружаю голос и распознаю текст...",
    },
    'voice.transcribe_failed': {
        'uz': "❌ Matn aniqlanmadi. Iltimos, qayta urinib ko'ring.",
        'uz-Cyrl': "❌ Матн аниқланмади. Илтимос, қайта уриниб кўринг.",
        'ru': "❌ Не удалось распознать речь. Попробуйте ещё раз.",
    },
    'voice.analyzing': {
        'uz': "📝 Matn:\n«{text}»\n\n🤖 AI tahlil qilmoqda...",
        'uz-Cyrl': "📝 Матн:\n«{text}»\n\n🤖 АИ таҳлил қилмоқда...",
        'ru': "📝 Текст:\n«{text}»\n\n🤖 ИИ анализирует...",
    },
    'voice.pipeline_error': {
        'uz': "❌ Xato yuz berdi. Iltimos, qayta urinib ko'ring yoki saytda qo'lda yarating.",
        'uz-Cyrl': "❌ Хато юз берди. Илтимос, қайта уриниб кўринг ёки сайтда қўлда яратинг.",
        'ru': "❌ Произошла ошибка. Попробуйте ещё раз или создайте вручную на сайте.",
    },

    # ----- Draft summary footer -----
    'draft.edit_on_site': {
        'uz': "Saytda tahrir qiling: {url}",
        'uz-Cyrl': "Сайтда таҳрир қилинг: {url}",
        'ru': "Редактировать на сайте: {url}",
    },
    'draft.cancelled': {
        'uz': "🛑 Qoralama bekor qilindi.",
        'uz-Cyrl': "🛑 Қоралама бекор қилинди.",
        'ru': "🛑 Черновик отменён.",
    },
    'draft.cancelled_short': {
        'uz': "Qoralama bekor qilindi",
        'uz-Cyrl': "Қоралама бекор қилинди",
        'ru': "Черновик отменён",
    },
    'draft.open_on_site': {
        'uz': "Saytda oching",
        'uz-Cyrl': "Сайтда очинг",
        'ru': "Открыть на сайте",
    },
}


def t(key: str, lang: Lang | None = None, **kwargs) -> str:
    """Berilgan til'da xabar matnini qaytaradi (yo'q bo'lsa default'ga tushadi)."""
    lang = lang or DEFAULT_LANG
    msg = MESSAGES.get(key, {}).get(lang)
    if msg is None:
        msg = MESSAGES.get(key, {}).get(DEFAULT_LANG, key)
    if kwargs:
        try:
            return msg.format(**kwargs)
        except (KeyError, IndexError):
            return msg
    return msg
