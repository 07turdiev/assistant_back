"""Aiogram bot launcher + handlers — FSM auth flow (O'zbek tilida).

Auth oqimi:
1. /start → loginni so'raydi
2. User username yuboradi → DB'da topilsa, parol so'raymiz; aks holda xato
3. User parol yuboradi → check_password → User.telegram_id = chat_id, state = AUTHENTICATED
4. AUTHENTICATED user → bu bot faqat bildirishnoma uchun ekanligi haqida xabar

Bot avtomatik ishga tushadi: `apps/telegram_bot/apps.py` orqali (server start bilan birga).
Yoki alohida process'da: `python manage.py run_bot`
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from asgiref.sync import sync_to_async
from django.conf import settings

from .keyboards import main_reply_keyboard
from .voice_handlers import register_voice_handlers

logger = logging.getLogger(__name__)


class AuthStates(StatesGroup):
    waiting_username = State()
    waiting_password = State()
    authenticated = State()


# --- Sync DB helpers (aiogram async, Django ORM sync) ---

@sync_to_async
def find_user_by_telegram_id(telegram_id: int):
    from apps.users.models import User
    return User.objects.filter(telegram_id=telegram_id).first()


@sync_to_async
def find_user_by_username(username: str):
    from apps.users.models import User
    return User.objects.filter(username=username, enabled=True).first()


@sync_to_async
def verify_password_and_bind(user_pk, password: str, telegram_id: int) -> bool:
    from apps.users.models import User
    user = User.objects.get(pk=user_pk)
    if not user.check_password(password):
        return False
    user.telegram_id = telegram_id
    user.save(update_fields=['telegram_id', 'updated_at'])
    return True


# --- Handlers ---

async def cmd_start(message: Message, state: FSMContext):
    user = await find_user_by_telegram_id(message.chat.id)
    if user:
        await state.set_state(AuthStates.authenticated)
        await message.answer(
            f"Salom, {user.first_name}! Siz allaqachon tizimga kirgansiz ✅\n\n"
            "Pastdagi tugmalardan foydalaning yoki ovozli xabar yuboring.",
            reply_markup=main_reply_keyboard(),
        )
        return
    await state.set_state(AuthStates.waiting_username)
    await message.answer(
        "Assalomu alaykum! 👋\n\n"
        "Tizimga kirish uchun loginingizni yuboring:"
    )


async def on_username(message: Message, state: FSMContext):
    username = (message.text or '').strip()
    user = await find_user_by_username(username)
    if not user:
        await message.answer(
            "❌ Bunday login topilmadi.\n"
            "Iltimos, loginingizni qayta tekshirib yuboring:"
        )
        return

    await state.update_data(user_id=str(user.id))
    await state.set_state(AuthStates.waiting_password)
    await message.answer("🔑 Endi parolingizni kiriting:")


async def on_password(message: Message, state: FSMContext):
    data = await state.get_data()
    user_pk = data.get('user_id')
    password = (message.text or '').strip()
    if not user_pk:
        await state.set_state(AuthStates.waiting_username)
        await message.answer("Iltimos, /start buyrug'i orqali qaytadan boshlang.")
        return

    ok = await verify_password_and_bind(user_pk, password, message.chat.id)
    if not ok:
        await message.answer("❌ Parol noto'g'ri. Qaytadan kiriting:")
        return

    await state.set_state(AuthStates.authenticated)
    await message.answer(
        "✅ Tizimga muvaffaqiyatli kirdingiz!\n\n"
        "Pastdagi tugmalardan foydalaning yoki ovozli xabar yuboring:\n"
        "🎤 Topshiriq berish — ovozli buyruq orqali topshiriq qoralamasini yarating\n"
        "📅 Tadbir yaratish — ovoz orqali tadbir qoralamasini tayyorlang\n\n"
        f"Saytdagi to'liq ko'rinish: {settings.FRONTEND_BASE_URL}",
        reply_markup=main_reply_keyboard(),
    )


async def on_authenticated_other(message: Message):
    await message.answer(
        "ℹ️ Buyruqni tushunmadim. Pastdagi tugmalardan foydalaning yoki "
        "/start orqali boshlang.",
        reply_markup=main_reply_keyboard(),
    )


# --- Bot factory ---

def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.register(cmd_start, Command('start'))
    dp.message.register(on_username, AuthStates.waiting_username)
    dp.message.register(on_password, AuthStates.waiting_password)

    # Voice / button handlerlar — autentifikatsiyalangan foydalanuvchilar uchun
    register_voice_handlers(dp)

    # Fallback (boshqa har qanday xabar) — autentifikatsiyadan keyin
    dp.message.register(on_authenticated_other, AuthStates.authenticated)
    dp.message.register(on_authenticated_other)
    return dp


async def run_polling():
    token = getattr(settings, 'TG_BOT_TOKEN', '')
    if not token:
        logger.error('TG_BOT_TOKEN sozlanmagan, bot ishga tushmadi')
        return

    bot = Bot(token=token)
    dp = create_dispatcher()
    logger.info(f'Bot ishga tushmoqda: @{(await bot.get_me()).username}')
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


def main():
    """Sync entry point — `python manage.py run_bot` orqali chaqiriladi."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    try:
        asyncio.run(run_polling())
    except (KeyboardInterrupt, SystemExit):
        logger.info('Bot to\'xtatildi')
