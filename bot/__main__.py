"""نقطة التشغيل الرئيسية: python -m bot"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.exceptions import TelegramUnauthorizedError

from bot import __version__
from bot.config import settings
from bot.database import Database
from bot.handlers import register_handlers
from bot.services.broadcaster import broadcast_worker


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


async def main() -> None:
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    log = logging.getLogger("bot")

    if not settings.bot_token:
        raise SystemExit(
            "❌ BOT_TOKEN غير مضبوط!\n"
            "1) انسخ .env.example إلى .env\n"
            "2) ضع توكن البوت من @BotFather في BOT_TOKEN\n"
            "3) شغّل: python -m bot"
        )

    db = Database(settings.database_path)
    await db.connect()

    bot = build_bot()
    dp = Dispatcher()
    dp["db"] = db
    dp["settings"] = settings
    register_handlers(dp)

    worker = asyncio.create_task(broadcast_worker(bot, db), name="broadcast-worker")

    log.info("✅ بوت تحميل الفيديوهات يعمل — الإصدار %s | المالك: %s | المشرفون: %d",
             __version__, settings.owner_id, len(settings.admin_ids))
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except TelegramUnauthorizedError:
        log.error("⛔ التوكن غير صالح! تأكد منه من @BotFather ثم أعد التشغيل.")
        raise SystemExit(1)
    finally:
        worker.cancel()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
