"""أوامر الإدارة — المالك 👑 + المشرفون.

للجميع (مشرف فأعلى):
  /stats            إحصائيات فورية
  /admins           قائمة المشرفين الحاليين
  /ban <id>         حظر مستخدم
  /unban <id>       إلغاء حظر مستخدم
  /broadcast <نص>   إذاعة لكل المستخدمين

للمالك فقط:
  /addadmin <id>    تعيين مشرف جديد
  /deladmin <id>    إزالة مشرف
"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot import permissions
from bot.config import settings
from bot.constants import fmt_bytes
from bot.database import Database

router = Router(name="admin")


def _uid(message: Message) -> int | None:
    return message.from_user.id if message.from_user else None


@router.message(Command("stats"))
async def cmd_stats(message: Message, db: Database) -> None:
    if not await permissions.is_admin(db, _uid(message)):
        await message.answer("⛔ هذا الأمر للمشرفين فقط.")
        return
    o = await db.overview()
    await message.answer(
        "📊 <b>إحصائيات البوت</b>\n\n"
        f"👥 المستخدمون: <b>{o['users']}</b> (جُدُد اليوم: {o['users_today']})\n"
        f"🚫 المحظورون: {o['banned']}\n"
        f"🟢 النشطون اليوم: {o['active_today']}\n\n"
        f"📥 إجمالي التحميلات: <b>{o['downloads']}</b>\n"
        f"📅 اليوم: {o['downloads_today']} | أمس: {o['downloads_yesterday']}\n"
        f"✅ ناجحة: {o['done']} | ❌ فاشلة: {o['failed']}\n"
        f"📈 معدل النجاح: {o['success_rate']}%\n"
        f"💾 حجم الملفات المُرسلة: {fmt_bytes(o['bytes_sent'])}\n"
        f"🎬 MP4: {o['mp4']} | 🎧 MP3: {o['mp3']}"
    )


@router.message(Command("admins"))
async def cmd_admins(message: Message, db: Database) -> None:
    if not await permissions.is_admin(db, _uid(message)):
        await message.answer("⛔ هذا الأمر للمشرفين فقط.")
        return
    ids = await permissions.all_admin_ids(db)
    lines = ["🛡 <b>المشرفون الحاليون</b>\n"]
    for admin_id in ids:
        if admin_id == settings.owner_id:
            lines.append(f"👑 <code>{admin_id}</code> — المالك")
        elif admin_id in settings.env_admin_ids:
            lines.append(f"⭐ <code>{admin_id}</code> — من ADMIN_IDS")
        else:
            lines.append(f"🛡 <code>{admin_id}</code>")
    lines.append(f"\nالإجمالي: {len(ids)} مشرف")
    await message.answer("\n".join(lines))


@router.message(Command("addadmin"))
async def cmd_addadmin(message: Message, db: Database) -> None:
    if not permissions.is_owner(_uid(message)):
        await message.answer("👑 هذا الأمر للمالك فقط.")
        return
    args = (message.text or "").split()
    if len(args) != 2 or not args[1].isdigit():
        await message.answer("الاستخدام: /addadmin <telegram_id>")
        return
    target = int(args[1])
    if target == settings.owner_id:
        await message.answer("👑 المالك مشرف افتراضياً بالفعل.")
        return
    added = await db.add_admin(target, added_by=_uid(message))
    await message.answer("✅ تمت إضافة المشرف." if added else "ℹ️ هو مشرف بالفعل.")


@router.message(Command("deladmin"))
async def cmd_deladmin(message: Message, db: Database) -> None:
    if not permissions.is_owner(_uid(message)):
        await message.answer("👑 هذا الأمر للمالك فقط.")
        return
    args = (message.text or "").split()
    if len(args) != 2 or not args[1].isdigit():
        await message.answer("الاستخدام: /deladmin <telegram_id>")
        return
    target = int(args[1])
    if target == settings.owner_id or target in settings.env_admin_ids:
        await message.answer("⚠️ لا يمكن إزالة مالك البوت أو مشرف من ADMIN_IDS — عدّل متغيرات البيئة.")
        return
    removed = await db.remove_admin(target)
    await message.answer("✅ تمت إزالة المشرف." if removed else "ℹ️ هذا المعرف ليس مشرفاً مضافاً.")


@router.message(Command("ban"))
async def cmd_ban(message: Message, db: Database) -> None:
    if not await permissions.is_admin(db, _uid(message)):
        return
    args = (message.text or "").split()
    if len(args) != 2 or not args[1].isdigit():
        await message.answer("الاستخدام: /ban <telegram_id>")
        return
    target = int(args[1])
    if target == settings.owner_id:
        await message.answer("👑 لا يمكن حظر المالك.")
        return
    ok = await db.set_banned(target, True)
    await message.answer("✅ تم الحظر." if ok else "❌ مستخدم غير موجود.")


@router.message(Command("unban"))
async def cmd_unban(message: Message, db: Database) -> None:
    if not await permissions.is_admin(db, _uid(message)):
        return
    args = (message.text or "").split()
    if len(args) != 2 or not args[1].isdigit():
        await message.answer("الاستخدام: /unban <telegram_id>")
        return
    ok = await db.set_banned(int(args[1]), False)
    await message.answer("✅ تم إلغاء الحظر." if ok else "❌ مستخدم غير موجود.")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, db: Database) -> None:
    if not await permissions.is_admin(db, _uid(message)):
        return
    text = (message.text or "").partition(" ")[2].strip()
    if len(text) < 3:
        await message.answer("الاستخدام: /broadcast <نص الرسالة>")
        return
    broadcast_id = await db.create_broadcast(text)
    await message.answer(
        f"📣 أُضيفت للطابور برقم #{broadcast_id} — سيصل لكل المستخدمين خلال لحظات.\n"
        "تابع التقدم من لوحة التحكم ← تبويب «الإذاعة»."
    )
