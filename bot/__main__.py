"""نقطة التشغيل الرئيسية: python -m bot"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.exceptions import TelegramConflictError, TelegramNetworkError, TelegramUnauthorizedError

from bot import __version__
from bot.config import settings
from bot.database import Database
from bot.handlers import register_handlers
from bot.services.broadcaster import broadcast_worker
from bot.services.downloader import cookies_report

# رموز الخروج — يفهمها scripts/start-all.sh ويحدد هل يعيد تشغيل البوت أم لا
EXIT_CLEAN = 0        # إيقاف طبيعي
EXIT_FATAL = 2        # خطأ قاتل (توكن غير صالح) — إعادة التشغيل لن تحل المشكلة


def build_bot() -> Bot:
    """يبني البوت — مع خادم Bot API محلي لو كان TELEGRAM_LOCAL_API مضبوطاً.

    الخادم المحلي يرفع حدود الرفع من 50MB إلى 2000MB لكل ملف.
    """
    if settings.local_api_mode:
        session = AiohttpSession(
            api=TelegramAPIServer.from_base(settings.telegram_local_api, is_local=True)
        )
        logging.getLogger("bot").info(
            "🔧 خادم Bot API محلي: %s — الملفات حتى %d م.بايت",
            settings.telegram_local_api, settings.effective_max_file_size_mb,
        )
        return Bot(token=settings.bot_token, session=session)
    return Bot(token=settings.bot_token)


async def poll_forever(dp: Dispatcher, bot: Bot, log: logging.Logger) -> None:
    """polling مع إعادة تلقائية — انقطاع الشبكة أو تضارب النسخ لا يوقف البوت نهائياً."""
    while True:
        try:
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
            log.info("🛑 تم إيقاف البوت بشكل طبيعي.")
            return
        except TelegramUnauthorizedError:
            log.error("⛔ التوكن غير صالح! تأكد من BOT_TOKEN من @BotFather ثم أعد النشر.")
            raise SystemExit(EXIT_FATAL) from None
        except TelegramNetworkError as exc:
            log.warning("🌐 تعذر الوصول إلى Telegram API (%s) — إعادة المحاولة بعد 15 ثانية…", exc)
            await asyncio.sleep(15)
        except TelegramConflictError:
            log.error(
                "⚠️ نسخة أخرى من البوت تعمل بنفس التوكن (Conflict)!\n"
                "أوقف النسخة الأخرى (جهاز/خدمة أخرى) — سأحاول مجدداً بعد 20 ثانية…"
            )
            await asyncio.sleep(20)
        except Exception:
            log.exception("⚠️ انقطاع مؤقت في الاتصال بـ Telegram — إعادة المحاولة بعد 15 ثانية…")
            await asyncio.sleep(15)


async def main() -> None:
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    log = logging.getLogger("bot")

    if not settings.bot_token:
        log.error(
            "❌ BOT_TOKEN غير مضبوط!\n"
            "1) انسخ .env.example إلى .env وضع التوكن من @BotFather\n"
            "2) أو على Railway: تبويب Variables ← أضف BOT_TOKEN"
        )
        raise SystemExit(EXIT_FATAL)

    db = Database(settings.database_path)
    await db.connect()

    bot = build_bot()
    dp = Dispatcher()
    dp["db"] = db
    dp["settings"] = settings
    register_handlers(dp)

    worker = asyncio.create_task(broadcast_worker(bot, db), name="broadcast-worker")

    log.info(
        "✅ بوت تحميل الفيديوهات يعمل — الإصدار %s | المالك: %s | المشرفون: %d",
        __version__, settings.owner_id, len(settings.admin_ids),
    )
    log.info(cookies_report(settings))

    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except TelegramUnauthorizedError:
        log.error("⛔ التوكن غير صالح! تأكد من BOT_TOKEN من @BotFather ثم أعد النشر.")
        worker.cancel()
        await db.close()
        await bot.session.close()
        raise SystemExit(EXIT_FATAL) from None
    except Exception as exc:
        log.warning("⚠️ تعذر حذف الـ webhook (سيتم تجاهل الخطأ): %s", exc)

    try:
        await poll_forever(dp, bot, log)
    finally:
        worker.cancel()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
