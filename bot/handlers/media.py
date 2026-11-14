"""قلب البوت: استقبال الروابط، المعاينة الحية، أزرار الجودة، والتحميل والإرسال."""

from __future__ import annotations

import asyncio
import logging
import secrets
import shutil
import time
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, FSInputFile, Message

from bot import messages
from bot.config import settings
from bot.constants import (
    AUDIO_ONLY_PLATFORMS,
    URL_REGEX,
    detect_platform,
)
from bot.database import Database
from bot.keyboards import cancelled_keyboard, quality_keyboard
from bot.services.downloader import (
    DownloadError,
    MediaInfo,
    download_audio,
    download_video,
    fetch_info,
)
from bot.services.spotify import fetch_track
from bot.services.anghami import fetch_song

log = logging.getLogger("bot.media")
router = Router(name="media")

# الطلبات المعلّقة: token → (info, created_at)
_pending: dict[str, tuple[MediaInfo, float]] = {}
# آخر طلب لكل مستخدم (للـ cooldown)
_last_request: dict[int, float] = {}


def _remember(info: MediaInfo) -> str:
    _gc_pending()
    token = secrets.token_hex(4)
    _pending[token] = (info, time.monotonic())
    return token


def _pop(token: str) -> MediaInfo | None:
    _gc_pending()
    item = _pending.pop(token, None)
    return item[0] if item else None


def _peek(token: str) -> MediaInfo | None:
    _gc_pending()
    item = _pending.get(token)
    return item[0] if item else None


def _gc_pending() -> None:
    now = time.monotonic()
    ttl = settings.pending_ttl_seconds
    for key in [k for k, (_, ts) in _pending.items() if now - ts > ttl]:
        _pending.pop(key, None)


# ─────────────────────────────── استقبال الروابط ───────────────────────────────

@router.message(F.text)
async def handle_text(message: Message, bot: Bot, db: Database) -> None:
    user = message.from_user
    if user:
        await db.upsert_user(user.id, user.username, user.first_name)
        if await db.is_banned(user.id):
            await message.answer(messages.BANNED)
            return

    urls = URL_REGEX.findall(message.text or "")
    if not urls:
        await message.answer(messages.NOT_A_LINK)
        return

    url = urls[0].rstrip(".,!?)]}>")
    platform = detect_platform(url)

    # Cooldown بسيط لمنع الإغراق
    if user:
        now = time.monotonic()
        last = _last_request.get(user.id, 0.0)
        if now - last < settings.request_cooldown_seconds:
            await message.answer(messages.COOLDOWN)
            return
        _last_request[user.id] = now

    if user and settings.daily_download_limit > 0:
        used = await db.download_count_today(user.id)
        if used >= settings.daily_download_limit:
            await message.answer(messages.DAILY_LIMIT.format(limit=settings.daily_download_limit))
            return

    placeholder = await message.answer(messages.LINK_SEEN)

    # ── جلب بيانات الوسائط حسب المنصة ─────────────────────────────
    try:
        if platform == "spotify":
            info = await fetch_track(url)
        elif platform == "anghami":
            info = await fetch_song(url)
        else:
            info = await fetch_info(url, platform, settings)
    except DownloadError as exc:
        await placeholder.edit_text(f"{messages.ERROR_PREFIX} {exc}")
        return
    except Exception:
        log.exception("فشل تحليل الرابط: %s", url)
        await placeholder.edit_text(messages.SOMETHING_WRONG)
        return

    # ── المعاينة الحية + أزرار الجودة ──────────────────────────────
    audio_only = platform in AUDIO_ONLY_PLATFORMS or info.is_audio_only
    token = _remember(info)
    caption = messages.preview_caption(info)
    keyboard = quality_keyboard(token, audio_only=audio_only)

    try:
        if info.thumbnail:
            await message.answer_photo(
                photo=info.thumbnail,
                caption=caption,
                reply_markup=keyboard,
            )
        else:
            await message.answer(caption, reply_markup=keyboard)
    except Exception:
        # لو الصورة فاشلة (رابط غلاف ميت) نرسل نصاً فقط
        try:
            await message.answer(caption, reply_markup=keyboard)
        except Exception:
            log.exception("تعذر إرسال المعاينة")
            await message.answer(messages.SOMETHING_WRONG)
    finally:
        try:
            await placeholder.delete()
        except Exception:
            pass


# ─────────────────────────────── أزرار الجودة ───────────────────────────────

@router.callback_query(F.data.startswith("dl:"))
async def handle_quality(callback: CallbackQuery, bot: Bot, db: Database) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 4:
        await callback.answer()
        return
    _, kind, quality, token = parts

    if kind == "cancel":
        _pop(token)
        await _safe_edit(callback, messages.CANCELLED, reply_markup=cancelled_keyboard())
        await callback.answer("تم الإلغاء ❌")
        return

    info = _peek(token)
    if info is None:
        await callback.answer("⌛ انتهت صلاحية هذا الطلب — أرسل الرابط مرة أخرى.", show_alert=True)
        return
    _pop(token)

    user = callback.from_user
    await callback.answer("⏳ جاري التحميل…")
    too_big_text = messages.TOO_BIG.format(limit=settings.effective_max_file_size_mb)

    tmpdir = Path(settings.download_dir) / token
    tmpdir.mkdir(parents=True, exist_ok=True)

    media_type = "mp3" if kind == "mp3" else "mp4"
    try:
        if media_type == "mp3":
            await _safe_edit(callback, messages.CONVERTING_MP3.format(quality=quality))
            path = await download_audio(info, quality, settings, tmpdir)
        else:
            await _safe_edit(callback, messages.PROCESSING_MP4.format(quality=quality))
            path = await download_video(info, quality, settings, tmpdir)

        size = path.stat().st_size
        if size > settings.max_file_size_bytes:
            await _safe_edit(callback, too_big_text)
            await db.add_download(
                user.id, url=info.url, platform=info.platform, media_type=media_type,
                quality=quality, title=info.title, duration=info.duration,
                file_size=size, status="failed", error="file too big",
            )
            return

        await _safe_edit(callback, messages.UPLOADING)
        caption = messages.download_caption(info, quality, media_type)
        chat_id = callback.message.chat.id
        document = FSInputFile(path)

        try:
            if media_type == "mp3":
                await bot.send_audio(
                    chat_id, document,
                    caption=caption, title=info.title[:64],
                    performer=(info.uploader or "")[:64] or None,
                )
            else:
                await bot.send_video(
                    chat_id, document,
                    caption=caption, supports_streaming=True,
                )
        except Exception as exc:
            low = str(exc).lower()
            if "too big" in low or "file is too" in low or "request entity" in low:
                raise DownloadError(too_big_text)
            raise

        await db.add_download(
            user.id, url=info.url, platform=info.platform, media_type=media_type,
            quality=quality, title=info.title, duration=info.duration,
            file_size=size, status="done",
        )

        # نحذف رسالة المعاينة بعد الإرسال — المحادثة تفضل نظيفة
        try:
            await callback.message.delete()
        except Exception:
            pass

    except DownloadError as exc:
        await _safe_edit(callback, f"{messages.ERROR_PREFIX} {exc}")
        await db.add_download(
            user.id, url=info.url, platform=info.platform, media_type=media_type,
            quality=quality, title=info.title, duration=info.duration,
            file_size=None, status="failed", error=str(exc)[:300],
        )
    except Exception:
        log.exception("فشل التحميل")
        await _safe_edit(callback, messages.SOMETHING_WRONG)
        await db.add_download(
            user.id, url=info.url, platform=info.platform, media_type=media_type,
            quality=quality, title=info.title, duration=info.duration,
            file_size=None, status="failed", error="unexpected error",
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


async def _safe_edit(callback: CallbackQuery, text: str, **kwargs) -> None:
    """يعدّل نص الرسالة سواء كانت نصية أو caption لصورة."""
    message = callback.message
    try:
        if message.photo:
            await message.edit_caption(caption=text, **kwargs)
        else:
            await message.edit_text(text, **kwargs)
    except Exception:
        try:
            await message.answer(text)
        except Exception:
            pass
