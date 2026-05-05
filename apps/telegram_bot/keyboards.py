"""Telegram bot uchun klaviaturalar.

Reply Keyboard — autentifikatsiyadan o'tgan foydalanuvchilarda doimo ko'rinadi.
"""
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)


# Tugma matnlari (handler'da ham shu nomlar bo'yicha aniqlaymiz)
BTN_NEW_TASK = '🎤 Topshiriq berish'
BTN_NEW_EVENT = '📅 Tadbir yaratish'
BTN_HELP = 'ℹ️ Yordam'


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Asosiy reply klaviatura — autentifikatsiyalangan foydalanuvchilarda doimo ko'rinadi."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=BTN_NEW_TASK),
                KeyboardButton(text=BTN_NEW_EVENT),
            ],
            [KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder='Ovozli xabar yuboring yoki tugmani bosing',
    )


def remove_reply_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def confirm_draft_keyboard(draft_kind: str, draft_id: str) -> InlineKeyboardMarkup:
    """Qoralama yaratilgandan keyin foydalanuvchiga tasdiq tugmalari.

    `draft_kind` — 'event' yoki 'report'.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text='✅ Tasdiq va saytda tahrir qilaman',
                    callback_data=f'draft_open:{draft_kind}:{draft_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    text='🛑 Bekor qilish',
                    callback_data=f'draft_cancel:{draft_kind}:{draft_id}',
                ),
            ],
        ]
    )


def choose_subordinate_keyboard(draft_kind: str, draft_id: str, subordinates) -> InlineKeyboardMarkup:
    """Bot agar `assigned_to` aniqlanmasa, ko'p bo'ysunuvchi orasidan tanlash.

    `subordinates` — User QuerySet/list.
    """
    rows = []
    for user in subordinates[:8]:  # 8 tagacha ko'rsatamiz
        full_name = f'{user.last_name} {user.first_name}'.strip() or user.username
        rows.append([
            InlineKeyboardButton(
                text=full_name,
                callback_data=f'draft_assign:{draft_kind}:{draft_id}:{user.id}',
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
