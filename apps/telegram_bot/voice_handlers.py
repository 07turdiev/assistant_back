"""Telegram orqali ovozli xabar → AI → Draft pipeline.

Oqim:
1. Foydalanuvchi `🎤 Topshiriq berish` yoki `📅 Tadbir yaratish` tugmasini bosadi
   → state = waiting_voice_for_task / waiting_voice_for_event
   → bot "Iltimos, ovozli xabar yuboring" deydi
2. Foydalanuvchi ovoz yuboradi
   → bot ovozni Telegram Bot API'dan yuklab oladi
   → STT API → matn
   → matnni AI parser'ga yuboradi → JSON
   → resolver natijasiga ko'ra EventDraft yoki ReportDraft yaratadi
   → tasdiq xabarini yuboradi (inline keyboard bilan)
3. Foydalanuvchi "saytda tahrir qilaman" tugmasini bosadi → callback
   → bot saytdagi qoralama URL'ini yuboradi
   → quyi xodimning botida ham yangi qoralama haqida xabar paydo bo'ladi
"""
from __future__ import annotations

import io
import logging
from datetime import date as date_cls
from pathlib import Path

from aiogram import Bot, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.files.base import ContentFile

from .keyboards import (
    BTN_HELP,
    BTN_NEW_EVENT,
    BTN_NEW_TASK,
    confirm_draft_keyboard,
    main_reply_keyboard,
)

logger = logging.getLogger(__name__)


class VoiceStates(StatesGroup):
    waiting_voice_for_event = State()
    waiting_voice_for_task = State()


# --------- DB helpers (sync wrapped) ---------

@sync_to_async
def _get_user(telegram_id: int):
    from apps.users.models import User
    return User.objects.filter(telegram_id=telegram_id, enabled=True).first()


@sync_to_async
def _create_draft_pipeline(
    *,
    sender,
    raw_text: str,
    voice_bytes: bytes,
    voice_filename: str,
    intent_type_hint: str,  # 'event' yoki 'report' — tugma orqali kelgan turi
):
    """Matn → AI → resolver → draft yaratish (sync, transaction).

    Returns:
        (draft, intent_dict, warnings_list)
    """
    from apps.ai.services import parse_intent
    from apps.drafts.resolver import resolve_intent
    from apps.drafts.services import (
        create_event_draft_from_intent,
        create_report_draft_from_intent,
    )

    intent = parse_intent(raw_text, today=date_cls.today())

    # Tugma orqali kelgan tur (event/task) ustun — model adashsa ham
    if intent_type_hint == 'event':
        intent['type'] = 'event'
    elif intent_type_hint == 'task':
        intent['type'] = 'report'

    resolved = resolve_intent(intent=intent, sender=sender)

    voice_file = ContentFile(voice_bytes, name=voice_filename)

    if intent['type'] == 'event':
        draft = create_event_draft_from_intent(
            intent=intent,
            created_by=sender,
            assigned_to=resolved.assigned_to,
            target_direction=resolved.target_direction,
            suggested_participants=resolved.suggested_participants,
            unresolved_names=resolved.unresolved_names,
            raw_transcript=raw_text,
            voice_file=voice_file,
        )
    else:
        draft = create_report_draft_from_intent(
            intent=intent,
            created_by=sender,
            assigned_to=resolved.assigned_to,
            target_direction=resolved.target_direction,
            suggested_participants=resolved.suggested_participants,
            unresolved_names=resolved.unresolved_names,
            raw_transcript=raw_text,
            voice_file=voice_file,
        )

    return draft, intent, resolved.warnings


@sync_to_async
def _get_draft_assignee_telegram(draft_kind: str, draft_id: str):
    """Draft.assigned_to'ning telegram_id'sini qaytaradi (mavjud bo'lsa)."""
    from apps.drafts.models import EventDraft, ReportDraft
    Model = EventDraft if draft_kind == 'event' else ReportDraft
    draft = Model.objects.filter(pk=draft_id).select_related('assigned_to').first()
    if not draft or not draft.assigned_to:
        return None, None
    return draft.assigned_to.telegram_id, _format_assignee_name(draft.assigned_to)


def _format_assignee_name(user) -> str:
    parts = [user.last_name, user.first_name]
    if user.father_name:
        parts.append(user.father_name)
    return ' '.join(p for p in parts if p)


# --------- Handlers ---------

async def on_button_new_task(message: Message, state: FSMContext):
    user = await _get_user(message.chat.id)
    if not user:
        await message.answer('Iltimos, avval /start orqali tizimga kiring.')
        return
    await state.set_state(VoiceStates.waiting_voice_for_task)
    await message.answer(
        '🎤 Topshiriq matnini ovozli xabar shaklida yuboring.\n\n'
        'Misol: "Sherzodga ayting, Toshkent viloyati hisobotini juma kuniga tayyorlasin"'
    )


async def on_button_new_event(message: Message, state: FSMContext):
    user = await _get_user(message.chat.id)
    if not user:
        await message.answer('Iltimos, avval /start orqali tizimga kiring.')
        return
    await state.set_state(VoiceStates.waiting_voice_for_event)
    await message.answer(
        '🎤 Tadbir tafsilotlarini ovozli xabar shaklida yuboring.\n\n'
        'Misol: "Ertaga soat 14 da Senat zalida kollegiya yig\'ilishi, 90 daqiqa"'
    )


async def on_button_help(message: Message):
    await message.answer(
        'ℹ️ Yordamchi\n\n'
        '🎤 Topshiriq berish — ovozli xabar yuborib tezkor topshiriq bering\n'
        '📅 Tadbir yaratish — ovoz orqali tadbir qoralamasini tayyorlang\n\n'
        f'Qoralamalar saytda tahrir qilinadi: {settings.FRONTEND_BASE_URL}/drafts',
        reply_markup=main_reply_keyboard(),
    )


async def on_voice_message(message: Message, state: FSMContext, bot: Bot):
    """Foydalanuvchi ovoz yuborgan holat — agar `waiting_voice_for_*` state'da bo'lsa."""
    current_state = await state.get_state()
    if current_state not in (
        VoiceStates.waiting_voice_for_event.state,
        VoiceStates.waiting_voice_for_task.state,
    ):
        await message.answer(
            'ℹ️ Ovozli xabar qabul qilish uchun avval pastdagi tugmalardan birini bosing.',
            reply_markup=main_reply_keyboard(),
        )
        return

    user = await _get_user(message.chat.id)
    if not user:
        await message.answer('Iltimos, avval /start orqali tizimga kiring.')
        return

    intent_hint = 'event' if current_state == VoiceStates.waiting_voice_for_event.state else 'task'

    voice = message.voice or message.audio
    if not voice:
        await message.answer('Iltimos, ovozli xabar yuboring.')
        return

    progress = await message.answer('⏳ Ovoz yuklanmoqda va matnga aylantirilmoqda...')

    try:
        # 1. Telegram'dan ovozni yuklab olish
        file_obj = await bot.get_file(voice.file_id)
        voice_bytes_io = io.BytesIO()
        await bot.download_file(file_obj.file_path, voice_bytes_io)
        voice_bytes = voice_bytes_io.getvalue()
        voice_filename = f'tg_voice_{message.message_id}.ogg'

        # 2. STT
        transcript = await _stt_transcribe(voice_bytes, voice_filename)
        if not transcript:
            await progress.edit_text('❌ Matn aniqlanmadi. Iltimos, qayta urinib ko\'ring.')
            await state.clear()
            return

        await progress.edit_text(f'📝 Matn:\n«{transcript}»\n\n🤖 AI tahlil qilmoqda...')

        # 3. AI + Draft
        draft, intent, warnings = await _create_draft_pipeline(
            sender=user,
            raw_text=transcript,
            voice_bytes=voice_bytes,
            voice_filename=voice_filename,
            intent_type_hint=intent_hint,
        )

    except Exception as e:
        logger.exception('Ovoz pipeline xatosi: %s', e)
        await progress.edit_text(
            f'❌ Xato yuz berdi: {e}\n\nIltimos, qayta urinib ko\'ring yoki saytda qo\'lda yarating.'
        )
        await state.clear()
        return

    await state.clear()

    # 4. Tasdiq xabari
    draft_kind = 'event' if intent['type'] == 'event' else 'report'
    summary = _format_draft_summary(intent, draft, warnings)
    await progress.edit_text(
        summary,
        reply_markup=confirm_draft_keyboard(draft_kind, str(draft.id)),
    )

    # 5. Quyi xodimga ogohlantirish
    if draft.assigned_to and draft.assigned_to.telegram_id:
        try:
            await _notify_assignee(bot, draft, draft_kind, transcript)
        except Exception:
            logger.exception('Quyi xodim botiga xabar yuborishda xato')


async def _stt_transcribe(voice_bytes: bytes, filename: str) -> str:
    """STT API ni async wrapper orqali chaqiradi."""
    from apps.ai.services import UzbekVoiceClient
    return await sync_to_async(_stt_sync)(voice_bytes, filename)


def _stt_sync(voice_bytes: bytes, filename: str) -> str:
    from apps.ai.services import UzbekVoiceClient
    client = UzbekVoiceClient()
    file_obj = io.BytesIO(voice_bytes)
    file_obj.name = filename
    return client.transcribe(file_obj, language=settings.UZBEKVOICE_LANGUAGE, model=settings.UZBEKVOICE_MODEL)


def _format_draft_summary(intent: dict, draft, warnings: list[str]) -> str:
    """Foydalanuvchiga ko'rsatish uchun qoralama xulosasini matn qiladi."""
    lines = []
    if intent['type'] == 'event':
        lines.append('📅 *Tadbir qoralamasi tayyor*')
    else:
        lines.append('📋 *Topshiriq qoralamasi tayyor*')
    lines.append('')
    lines.append(f'*Sarlavha:* {intent.get("title")}')

    if intent.get('date'):
        lines.append(f'*Sana:* {intent["date"]}')
    if intent.get('start_time'):
        time_str = intent['start_time']
        if intent.get('end_time'):
            time_str += f' — {intent["end_time"]}'
        lines.append(f'*Vaqt:* {time_str}')
    if intent.get('location'):
        lines.append(f'*Manzil:* {intent["location"]}')
    if intent.get('is_important'):
        lines.append('*🔴 Muhim*')
    if intent.get('is_private'):
        lines.append('*🔒 Yopiq*')

    if draft.assigned_to:
        lines.append(f'*Tayinlanadi:* {_format_assignee_name(draft.assigned_to)}')
    if draft.target_direction:
        lines.append(f'*Bo\'lim:* {draft.target_direction.name_uz}')

    if warnings:
        lines.append('')
        lines.append('⚠️ *Diqqat:*')
        for w in warnings:
            lines.append(f'• {w}')

    lines.append('')
    lines.append('Saytda tahrir qilib, "Joylash" tugmasini bosing.')
    return '\n'.join(lines)


async def _notify_assignee(bot: Bot, draft, draft_kind: str, transcript: str):
    """Quyi xodimning botiga yangi qoralama haqida xabar yuboradi."""
    if not draft.assigned_to or not draft.assigned_to.telegram_id:
        return

    sender_name = _format_assignee_name(draft.created_by) if draft.created_by else 'Kimdir'
    icon = '📅' if draft_kind == 'event' else '📋'
    kind_uz = 'tadbir' if draft_kind == 'event' else 'topshiriq'
    text = (
        f'{icon} *{sender_name}* sizga yangi {kind_uz} qoralamasi yubordi:\n\n'
        f'«{transcript}»\n\n'
        f'Saytda ko\'rib, tahrir qilib, joylashtirishingiz mumkin:\n'
        f'{settings.FRONTEND_BASE_URL}/drafts/{draft_kind}/{draft.id}'
    )
    await bot.send_message(
        chat_id=draft.assigned_to.telegram_id,
        text=text,
        parse_mode='Markdown',
    )


# --------- Callback handlers ---------

async def on_draft_callback(callback: CallbackQuery):
    """Tasdiq tugmasi (qoralamani saytda ochish) yoki bekor qilish."""
    data = callback.data or ''
    if data.startswith('draft_open:'):
        _, kind, draft_id = data.split(':', 2)
        await callback.answer('Saytda oching')
        await callback.message.answer(
            f'Saytda tahrir qiling: {settings.FRONTEND_BASE_URL}/drafts/{kind}/{draft_id}',
            reply_markup=main_reply_keyboard(),
        )
    elif data.startswith('draft_cancel:'):
        _, kind, draft_id = data.split(':', 2)
        await _reject_draft_async(kind, draft_id, reason='Telegram orqali bekor qilindi')
        await callback.answer('Qoralama bekor qilindi')
        await callback.message.edit_text('🛑 Qoralama bekor qilindi.')


@sync_to_async
def _reject_draft_async(kind: str, draft_id: str, reason: str):
    from apps.drafts.models import EventDraft, ReportDraft
    from apps.drafts.services import reject_draft
    Model = EventDraft if kind == 'event' else ReportDraft
    draft = Model.objects.filter(pk=draft_id).first()
    if draft:
        try:
            reject_draft(draft, reason=reason)
        except Exception:
            logger.exception('Draft rad etishda xato')


# --------- Registration helper ---------

def register_voice_handlers(dp):
    """Dispatcher'ga voice handler'larni ulaydi.

    Mavjud `apps/telegram_bot/bot.py` `create_dispatcher()` ichidan chaqiriladi.
    """
    dp.message.register(on_button_new_task, F.text == BTN_NEW_TASK)
    dp.message.register(on_button_new_event, F.text == BTN_NEW_EVENT)
    dp.message.register(on_button_help, F.text == BTN_HELP)
    dp.message.register(
        on_voice_message,
        F.voice | F.audio,
    )
    dp.callback_query.register(on_draft_callback, F.data.startswith('draft_'))
