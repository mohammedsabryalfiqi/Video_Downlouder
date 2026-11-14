"""غلاف yt-dlp: جلب معلومات الوسائط + التحميل بصيغة MP4 / MP3.

ملاحظة: تيك توك يُرجع yt-dlp روابط بدون علامة مائية (play URL) افتراضياً.
"""

from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yt_dlp

from bot.constants import MP4_HEIGHT


class DownloadError(Exception):
    """خطأ متوقع في التحميل — الرسالة تُعرض للمستخدم كما هي."""


@dataclass
class MediaInfo:
    url: str
    platform: str
    title: str
    uploader: str | None
    duration: int | None
    views: int | None
    thumbnail: str | None
    is_audio_only: bool = False
    webpage_url: str | None = None
    # أغنية مجلوبة من سبوتيفاي/أنجامي (البحث يتم عبر يوتيوب)
    resolved_query: str | None = None
    raw: dict = field(default_factory=dict, repr=False)


def _base_opts(settings) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 30,
        "retries": 5,
        "fragment_retries": 5,
        "noprogress": True,
        "windowsfilenames": True,
        "restrictfilenames": False,
    }
    # حجم غير محدود = لا نضع سقفاً في yt-dlp (تيليجرام هو من يفرض عند الإرسال)
    if settings.max_file_size_mb > 0:
        opts["max_filesize"] = settings.max_file_size_bytes
    # خيارات متقدمة (اختيارية)
    if settings.ytdlp_proxy:
        opts["proxy"] = settings.ytdlp_proxy
    if settings.ytdlp_cookies_file and Path(settings.ytdlp_cookies_file).is_file():
        opts["cookiefile"] = settings.ytdlp_cookies_file
    return opts


def _clean_title(title: str | None) -> str:
    title = (title or "بدون عنوان").strip()
    return title[:120] + ("…" if len(title) > 120 else "")


def _map_error(exc: Exception) -> DownloadError:
    msg = str(exc)
    low = msg.lower()
    if "max_filesize" in low or "too large" in low or "file is larger" in low:
        return DownloadError("📦 الملف أكبر من الحد المسموح (49 م.بايت).")
    if "private" in low:
        return DownloadError("🔒 المحتوى خاص (Private) — لا يمكن تحميله.")
    if "age" in low and ("confirm" in low or "restrict" in low):
        return DownloadError("🔞 محتوى محظور على القُصّر — لا يمكن تحميله.")
    if "unavailable" in low or "not available" in low or "removed" in low:
        return DownloadError("🚫 هذا المحتوى غير متاح أو تم حذفه.")
    if "login" in low or "sign in" in low or "cookies" in low:
        return DownloadError("🔑 المنصة تطلب تسجيل الدخول لهذا المحتوى.")
    if "unsupported url" in low:
        return DownloadError("🔗 الرابط غير مدعوم. جرّب رابطاً آخر.")
    if "timed out" in low or "timeout" in low:
        return DownloadError("⏰ انتهت مهلة الاتصال — حاول مرة أخرى.")
    if "no space" in low or "disk" in low:
        return DownloadError("💽 مساحة القرص غير كافية على الخادم.")
    return DownloadError("⚠️ تعذر التحميل. تأكد من الرابط وحاول مرة أخرى.")


def fetch_info_sync(url: str, platform: str, settings) -> MediaInfo:
    opts = _base_opts(settings)
    opts["skip_download"] = True
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            data = ydl.extract_info(url, download=False)
    except Exception as exc:
        raise _map_error(exc) from exc

    if not data:
        raise DownloadError("⚠️ تعذر قراءة بيانات الرابط.")

    if data.get("_type") == "playlist" or "entries" in data:
        raise DownloadError("📋 قوائم التشغيل غير مدعومة حالياً — أرسل رابط فيديو/أغنية واحدة.")

    views = data.get("view_count")
    try:
        views = int(views) if views is not None else None
    except (TypeError, ValueError):
        views = None

    duration = data.get("duration")
    try:
        duration = int(duration) if duration is not None else None
    except (TypeError, ValueError):
        duration = None

    return MediaInfo(
        url=url,
        platform=platform,
        title=_clean_title(data.get("title") or data.get("fulltitle")),
        uploader=(data.get("uploader") or data.get("channel") or data.get("uploader_id")),
        duration=duration,
        views=views,
        thumbnail=data.get("thumbnail"),
        is_audio_only=bool(data.get("is_live") is False and data.get("vcodec") == "none"),
        webpage_url=data.get("webpage_url") or url,
        raw={"extractor": (data.get("extractor_key") or "").lower()},
    )


def _search_query(query: str, settings):
    """يبحث في يوتيوب ويرجع أول نتيجة (للأغاني المجلوبة من سبوتيفاي/أنجامي)."""
    opts = _base_opts(settings)
    opts["skip_download"] = True
    opts["default_search"] = "ytsearch"
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            data = ydl.extract_info(f"ytsearch1:{query}", download=False)
    except Exception as exc:
        raise _map_error(exc) from exc
    entries = (data or {}).get("entries") or []
    if not entries:
        raise DownloadError("🔍 لم أجد الأغنية — حاول رابطاً آخر.")
    return entries[0]


def download_audio_sync(info: MediaInfo, bitrate: str, settings, tmpdir: Path) -> Path:
    """تحميل أفضل صوت + تحويله إلى MP3 بالجودة المطلوبة. يرجع مسار الملف."""
    search_target = f"ytsearch1:{info.resolved_query}" if info.resolved_query else info.url
    outtmpl = str(tmpdir / "%(title).90s.%(ext)s")

    opts = _base_opts(settings)
    opts.update(
        {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "default_search": "ytsearch",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": bitrate.rstrip("kK"),
                }
            ],
        }
    )
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([search_target])
    except Exception as exc:
        raise _map_error(exc) from exc

    files = sorted(tmpdir.glob("*.mp3"), key=os.path.getmtime, reverse=True)
    if not files:
        raise DownloadError("⚠️ فشل تحويل الملف إلى MP3 (هل ffmpeg مثبت؟).")
    return files[0]


def download_video_sync(info: MediaInfo, max_height: str, settings, tmpdir: Path) -> Path:
    """تحميل MP4 بالجودة المطلوبة (بدون دمج صوت إن أمكن).

    max_height = 'max' تعني أفضل جودة متوفرة على المنصة بدون أي حد للحجم.
    """
    height = MP4_HEIGHT.get(max_height, 720)
    outtmpl = str(tmpdir / "%(title).90s.%(ext)s")

    # يفضّل ملفات MP4 جاهزة (صوت+صورة في ملف واحد)، وإلا يدمج ويضيف ffmpeg
    if height is None:
        fmt = "best[ext=mp4][vcodec!=none][acodec!=none]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
    else:
        fmt = (
            f"best[ext=mp4][height<={height}][vcodec!=none][acodec!=none]/"
            f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={height}]+bestaudio/"
            f"best[height<={height}]/best"
        )
    opts = _base_opts(settings)
    opts.update({"format": fmt, "outtmpl": outtmpl, "merge_output_format": "mp4"})
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([info.webpage_url or info.url])
    except Exception as exc:
        raise _map_error(exc) from exc

    files = sorted(
        [p for p in tmpdir.iterdir() if p.suffix.lower() in {".mp4", ".mkv", ".webm"}],
        key=os.path.getmtime,
        reverse=True,
    )
    if not files:
        raise DownloadError("⚠️ لم يتم إنتاج ملف فيديو.")
    return files[0]


async def fetch_info(url: str, platform: str, settings) -> MediaInfo:
    return await asyncio.to_thread(fetch_info_sync, url, platform, settings)


async def download_audio(info: MediaInfo, bitrate: str, settings, tmpdir: Path) -> Path:
    return await asyncio.to_thread(download_audio_sync, info, bitrate, settings, tmpdir)


async def download_video(info: MediaInfo, quality: str, settings, tmpdir: Path) -> Path:
    return await asyncio.to_thread(download_video_sync, info, quality, settings, tmpdir)


def safe_filename(path: Path, fallback: str = "media") -> str:
    name = re.sub(r"[^\w\-. ()\[\]\u0600-\u06FF]+", "_", path.name)
    return name[:90] or fallback
