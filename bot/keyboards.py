"""لوحات المفاتيح المضمّنة (Inline Keyboards) — بالعربية مع إيموجي واضحة."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.constants import MP3_QUALITIES, MP4_QUALITIES, MP4_QUALITY_LABELS

CB_PREFIX = "dl"  # dl:<kind>:<quality>:<token>


def start_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📖 طريقة الاستخدام", callback_data="menu:help")
    builder.button(text="ℹ️ عن البوت", callback_data="menu:about")
    builder.button(text="🎵 جرّب: أغنية من سبوتيفاي", callback_data="menu:try_spotify")
    builder.adjust(2, 1)
    return builder.as_markup()


def quality_keyboard(token: str, audio_only: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if not audio_only:
        for q in MP4_QUALITIES:
            builder.button(text=f"🎬 {MP4_QUALITY_LABELS.get(q, q)}", callback_data=f"{CB_PREFIX}:mp4:{q}:{token}")

    for q in MP3_QUALITIES:
        builder.button(text=f"🎧 MP3 · {q}", callback_data=f"{CB_PREFIX}:mp3:{q}:{token}")
    builder.button(text="❌ إلغاء", callback_data=f"{CB_PREFIX}:cancel::{token}")
    builder.adjust(*([4, 3, 1] if not audio_only else [3, 1]))
    return builder.as_markup()


def try_spotify_keyboard(example_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📋 نسخ الرابط والمحاولة", url=example_url))
    builder.row(InlineKeyboardButton(text="🔙 رجوع", callback_data="menu:start"))
    return builder.as_markup()


def cancelled_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 البداية", callback_data="menu:start")
    return builder.as_markup()
