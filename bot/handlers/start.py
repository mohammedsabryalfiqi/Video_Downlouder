"""أوامر البداية والمساعدة: /start /help /about + أزرار القائمة."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from bot import messages, permissions
from bot.database import Database
from bot.keyboards import start_keyboard

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database) -> None:
    user = message.from_user
    if user:
        await db.upsert_user(user.id, user.username, user.first_name)
        if await db.is_banned(user.id):
            await message.answer(messages.BANNED)
            return
    await message.answer(messages.WELCOME, reply_markup=start_keyboard())
    if user and permissions.is_owner(user.id):
        await message.answer(messages.OWNER_NOTE)


@router.message(Command("help"))
async def cmd_help(message: Message, db: Database) -> None:
    user = message.from_user
    if user:
        await db.upsert_user(user.id, user.username, user.first_name)
    await message.answer(messages.HELP)


@router.message(Command("about"))
async def cmd_about(message: Message) -> None:
    await message.answer(messages.ABOUT)


@router.callback_query(F.data == "menu:start")
async def menu_start(callback: CallbackQuery) -> None:
    await callback.message.edit_text(messages.WELCOME, reply_markup=start_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:help")
async def menu_help(callback: CallbackQuery) -> None:
    await callback.message.edit_text(messages.HELP, reply_markup=start_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:about")
async def menu_about(callback: CallbackQuery) -> None:
    await callback.message.edit_text(messages.ABOUT, reply_markup=start_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:try_spotify")
async def menu_try_spotify(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🎵 <b>التحميل من سبوتيفاي وأنجامي بخطوات بسيطة:</b>\n\n"
        "1️⃣ افتح التطبيق ← اختر الأغنية\n"
        "2️⃣ اضغط مشاركة (Share) ← نسخ الرابط\n"
        "3️⃣ الصق الرابط هنا في المحادثة\n"
        "4️⃣ اختار جودة MP3 (128k / 192k / 320k) واستمتع 🎧\n\n"
        "<i>البوت يبحث عن الأغنية على يوتيوب ويحمّلها لك كملف MP3 عالي الجودة.</i>",
        reply_markup=start_keyboard(),
    )
    await callback.answer()
