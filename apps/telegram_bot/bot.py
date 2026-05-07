"""Aiogram bot launcher + handlers — FSM auth flow (uz/uz-Cyrl/ru tilida).

Auth oqimi:
1. /start → loginni so'raydi
2. User username yuboradi → DB'da topilsa, parol so'raymiz; aks holda xato
3. User parol yuboradi → check_password → User.telegram_id = chat_id, state = AUTHENTICATED
   - Brute-force himoyasi: 5 marta noto'g'ri urinishdan keyin 15 daqiqa lock
4. AUTHENTICATED user → ovozli xabar yoki tugmalar orqali draft yaratadi

Bot avtomatik ishga tushadi: `apps/telegram_bot/apps.py` orqali (server start bilan birga).
Yoki alohida process'da: `python manage.py run_bot`
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from asgiref.sync import sync_to_async
from django.conf import settings

from .i18n import detect_lang, t
from .keyboards import main_reply_keyboard
from .rate_limit import (
    LOCK_DURATION_SECONDS,
    MAX_ATTEMPTS,
    format_remaining,
    is_locked,
    record_failure,
    reset as reset_rate_limit,
)
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


def _lang_from_message(message: Message):
    """Telegram user.language_code asosida til aniqlash."""
    code = getattr(message.from_user, 'language_code', None) if message.from_user else None
    return detect_lang(code)


# --- Handlers ---

async def cmd_start(message: Message, state: FSMContext):
    lang = _lang_from_message(message)
    user = await find_user_by_telegram_id(message.chat.id)
    if user:
        await state.set_state(AuthStates.authenticated)
        await message.answer(
            t('start.welcome_back', lang=lang, name=user.first_name),
            reply_markup=main_reply_keyboard(),
        )
        return
    await state.set_state(AuthStates.waiting_username)
    await message.answer(t('start.greeting', lang=lang))


async def on_username(message: Message, state: FSMContext):
    lang = _lang_from_message(message)
    # Lock holatida bo'lsa darhol xabar berib chiqamiz
    locked, remaining = await is_locked(message.chat.id)
    if locked:
        await message.answer(t('login.locked', lang=lang, wait=format_remaining(remaining)))
        return

    username = (message.text or '').strip()
    user = await find_user_by_username(username)
    if not user:
        await message.answer(t('login.username_not_found', lang=lang))
        return

    await state.update_data(user_id=str(user.id))
    await state.set_state(AuthStates.waiting_password)
    await message.answer(t('login.password_prompt', lang=lang))


async def on_password(message: Message, state: FSMContext):
    lang = _lang_from_message(message)

    locked, remaining = await is_locked(message.chat.id)
    if locked:
        await message.answer(t('login.locked', lang=lang, wait=format_remaining(remaining)))
        return

    data = await state.get_data()
    user_pk = data.get('user_id')
    password = (message.text or '').strip()
    if not user_pk:
        await state.set_state(AuthStates.waiting_username)
        await message.answer(t('login.session_expired', lang=lang))
        return

    ok = await verify_password_and_bind(user_pk, password, message.chat.id)
    if not ok:
        attempts, lock_triggered = await record_failure(message.chat.id)
        if lock_triggered:
            await message.answer(
                t('login.locked', lang=lang, wait=format_remaining(LOCK_DURATION_SECONDS)),
            )
            await state.set_state(AuthStates.waiting_username)
        else:
            remaining_attempts = max(0, MAX_ATTEMPTS - attempts)
            await message.answer(
                t('login.password_wrong', lang=lang, remaining=remaining_attempts),
            )
        return

    # Muvaffaqiyatli — counter'ni tozalaymiz
    await reset_rate_limit(message.chat.id)
    await state.set_state(AuthStates.authenticated)
    await message.answer(
        t('login.success', lang=lang, url=settings.FRONTEND_BASE_URL),
        reply_markup=main_reply_keyboard(),
    )


async def on_authenticated_other(message: Message):
    lang = _lang_from_message(message)
    await message.answer(
        t('other.unknown_command', lang=lang),
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
