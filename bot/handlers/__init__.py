"""تسجيل كل الـ routers في الـ Dispatcher."""

from __future__ import annotations

from aiogram import Dispatcher

from bot.handlers import admin, media, start


def register_handlers(dp: Dispatcher) -> None:
    dp.include_router(start.router)
    dp.include_router(media.router)
    dp.include_router(admin.router)
