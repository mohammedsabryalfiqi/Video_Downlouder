"""عامل الإذاعة: يراقب جدول broadcasts في قاعدة البيانات وينفّذ الرسائل المعلّقة.

هكذا تستطيع لوحة التحكم (أو أمر /broadcast داخل البوت) دفع رسائل جماعية
لكل المستخدمين بدون أي اتصال مباشر بينهما — التنسيق عبر SQLite فقط.
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.utils.markdown import html_decoration

from bot.database import Database

log = logging.getLogger("bot.broadcaster")

POLL_INTERVAL = 5          # ثوانٍ بين كل فحص
SEND_DELAY = 0.05          # ~20 رسالة/ثانية لتفادي حد تيليجرام
PROGRESS_EVERY = 20        # تحديث العدادات كل N مستخدم


async def broadcast_worker(bot: Bot, db: Database) -> None:
    log.info("📡 عامل الإذاعة يعمل — يفحص كل %s ثوانٍ", POLL_INTERVAL)
    while True:
        try:
            await _tick(bot, db)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("خطأ في عامل الإذاعة")
        await asyncio.sleep(POLL_INTERVAL)


async def _tick(bot: Bot, db: Database) -> None:
    row = await db.claim_next_broadcast()
    if not row:
        return

    broadcast_id = row["id"]
    text = row["text"]
    log.info("📣 بدء الإذاعة #%s (%s مستلم)", broadcast_id, row["total"])

    user_ids = await db.active_user_ids()
    sent = failed = 0
    safe_text = html_decoration.quote(text)

    for i, user_id in enumerate(user_ids, start=1):
        try:
            await bot.send_message(user_id, f"📣 <b>رسالة من الإدارة</b>\n\n{safe_text}")
            sent += 1
        except TelegramRetryAfter as exc:
            await asyncio.sleep(float(exc.retry_after) + 1)
            try:
                await bot.send_message(user_id, f"📣 <b>رسالة من الإدارة</b>\n\n{safe_text}")
                sent += 1
            except Exception:
                failed += 1
        except TelegramForbiddenError:
            failed += 1  # المستخدم حظر البوت
        except Exception:
            failed += 1

        if i % PROGRESS_EVERY == 0:
            await db.broadcast_progress(broadcast_id, sent, failed)
        await asyncio.sleep(SEND_DELAY)

    await db.broadcast_progress(broadcast_id, sent, failed)
    await db.broadcast_done(broadcast_id)
    log.info("✅ انتهت الإذاعة #%s — تم: %s | فشل: %s", broadcast_id, sent, failed)
