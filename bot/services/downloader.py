"""غلاف yt-dlp: جلب معلومات الوسائط + التحميل بصيغة MP4 / MP3.

أبرز حلول مشكلة «يوتيوب يطلب تسجيل الدخول / Sign in to confirm you're not a bot»
وهي المشكلة الأشهر عند التشغيل من خوادم سحابية (Railway…):
  1. سلسلة عملاء YouTube بديلة (android/ios ← tv ← web_safari ← الافتراضي)
     تُجرَّب تلقائياً حتى لو حظر عميلٌ ما.
  2. كوكيز المستخدم نفسه عبر YTDLP_COOKIES_FILE أو YTDLP_COOKIES_TEXT
     (الحل النهائي للحظر).
  3. ملف الكوكيز المكسور (ترويسة ناقصة/خطأ إملائي/base64 بدون بادئة) يُصلَّح
     تلقائياً قبل الاستخدام — و Deploy Logs يطبع سطر «🍪» يؤكد عدد السجلات.

ملاحظة: تيك توك يُرجع yt-dlp روابط بدون علامة مائية (play URL) افتراضياً.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import yt_dlp

from bot.constants import MP4_HEIGHT

log = logging.getLogger("bot.downloader")


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


# ── أنماط حظر يوتيوب (راجع _with_yt_fallback و _map_error) ─────────────────
_BOT_CHECK_RE = re.compile(
    r"(not a bot|confirm you(?:.re| are) not a bot|bot.?check|unusual traffic|"
    r"sign in to confirm|verify you are human|too many requests.*bot)",
    re.I,
)

# سلسلة عملاء يوتيوب — yt-dlp يجرب أولها وينتقل للتالي فقط عند فشل «حظر الروبوت»
_YT_CLIENT_CHAIN = [["android", "ios"], ["tv", "android"], ["web_safari"], ["android_vr"], [None]]

# كوكيز من متغير البيئة تُكتب لملف مؤقت مرة واحدة فقط
_cookies_cache: str | None = None
_cookie_stats: dict = {"count": 0, "domains": [], "configured": False}
_B64_CHARS_RE = re.compile(r"^[A-Za-z0-9+/=\s]+$", re.S)


def _normalize_cookies(content: str):
    """يصلح ملف Netscape مهما كان مدخله (ترويسة ناقصة/خطأ إملائي/base64 خام).

    يرجع (النص المصحح, إحصائيات) أو (None, إحصائيات) لو لا توجد أي سجلات صالحة.
    """
    stats = {"count": 0, "domains": []}

    # لصق بأحرف هروب حرفية: \n \t \r كأحرف منفصلة (شائع عند النسخ من مخرجات الطرفية)
    if "\\" in (content or ""):
        content = (
            content.replace("\\r\\n", "\n")
            .replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace("\\r", "\n")
        )

    text = content.replace("\r\n", "\n").replace("\r", "\n").strip().strip('"').strip("'")
    # لو الصقوا السطر كاملاً: YTDLP_COOKIES_TEXT=...
    if text.startswith("YTDLP_COOKIES_TEXT="):
        text = text.split("=", 1)[1].strip().strip('"').strip("'")

    # base64 ببادئة صريحة
    if text.startswith("base64:"):
        try:
            text = base64.b64decode(text[len("base64:"):], validate=False).decode("utf-8", "ignore")
        except Exception:
            return None, stats
    elif "Cookie File" not in text and _B64_CHARS_RE.match(text):
        # غالباً base64 خام بدون بادئة — جرّب فكّه (النجاح يتطلب سطور كوكيز فعلية)
        try:
            decoded = base64.b64decode(text, validate=False).decode("utf-8", "ignore")
            if decoded.count("\t") >= 7:
                text = decoded
        except Exception:
            pass

    lines = [l for l in text.split("\n") if l.strip()]
    if not lines:
        return None, stats

    # البوت يصلح أي خطأ في السطر الأول (مثل «Notscape» الشهيرة)
    if lines[0].startswith("#"):
        lines[0] = "# Netscape HTTP Cookie File"
    else:
        lines.insert(0, "# Netscape HTTP Cookie File")

    cookie_lines = [
        l for l in lines[1:]
        if not l.lstrip().startswith("#") and len(l.split("\t")) >= 7
    ]
    stats = {
        "count": len(cookie_lines),
        "domains": sorted({l.split("\t")[0].lstrip(".") for l in cookie_lines}),
    }
    if not cookie_lines:
        return None, stats
    return "\n".join(lines) + "\n", stats


def _cookies_path(settings) -> str | None:
    global _cookies_cache, _cookie_stats
    # 1) ملف صريح من متغير بيئة
    cookies_file = getattr(settings, "ytdlp_cookies_file", "") or ""
    if cookies_file and Path(cookies_file).is_file():
        _cookie_stats = {"configured": True, **_cookie_stats}
        return cookies_file
    # 2) محتوى من متغير بيئة (نص خام أو base64:...) — مثالي لـ Railway
    cookies_text = getattr(settings, "ytdlp_cookies_text", "") or ""
    if not cookies_text.strip():
        _cookie_stats = {"configured": False, "count": 0, "domains": []}
        return None
    if _cookies_cache:
        return _cookies_cache

    normalized, stats = _normalize_cookies(cookies_text)
    _cookie_stats = {"configured": True, **stats}
    if not normalized:
        log.warning("⚠️ YTDLP_COOKIES_TEXT مضبوط لكن لم أجد أي سجل كوكيز صالح داخله — سأكمل بدون كوكيز")
        return None
    try:
        tmp = Path(tempfile.gettempdir()) / "video_downlouder_cookies.txt"
        tmp.write_text(normalized, encoding="utf-8")
        os.chmod(tmp, 0o600)
    except OSError:
        return None
    _cookies_cache = str(tmp)
    return _cookies_cache


def cookies_report(settings) -> str:
    """سطر تشخيص آمن للطباعة عند الإقلاع — بدون أي قيم سرية.

    يفحص فعلياً أن yt-dlp قادر على قراءة ملف الكوكيز — فلا تكتشف المشكلة
    من رسالة خطأ غامضة بعد أول تحميل، بل من أول سطر في Deploy Logs.
    """
    path = _cookies_path(settings)
    if not _cookie_stats.get("configured"):
        return "ℹ️ كوكيز يوتيوب: غير مضبوطة — سأعتمد على عملاء يوتيوب البديلة تلقائياً"
    if path and _cookie_stats.get("count"):
        domains = ", ".join(_cookie_stats["domains"]) or "?"
        count = _cookie_stats["count"]
        # تحقق فعلي: هل yt-dlp نفسه قادر على تحميل الملف؟
        try:
            from yt_dlp.cookies import YoutubeDLCookieJar
            jar = YoutubeDLCookieJar(path)
            jar.load(ignore_discard=True, ignore_expires=True)
            return f"🍪 كوكيز يوتيوب: {len(jar)} سجل صالح ({domains}) — يوتيوب سيعاملك كمسجل دخول"
        except Exception as exc:
            return (
                f"❌ YTDLP_COOKIES_TEXT مضبوط ({count} سجل) لكن yt-dlp رفض الملف: {exc} — "
                "راجع التنسيق (لازم: base64 -w0 cookies.txt ثم «base64:الناتج»)"
            )
    return (
        "❌ YTDLP_COOKIES_TEXT مضبوط لكن لم يُكتشف أي كوكيز صالح — "
        "تأكد أن القيمة هي محتوى cookies.txt كاملاً (أو base64:... الناتج من base64 -w0)"
    )


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
    if settings.ytdlp_proxy:
        opts["proxy"] = settings.ytdlp_proxy
    cookies = _cookies_path(settings)
    if cookies:
        opts["cookiefile"] = cookies
    return opts


def _clean_title(title: str | None) -> str:
    title = (title or "بدون عنوان").strip()
    return title[:120] + ("…" if len(title) > 120 else "")


def _map_error(exc: Exception) -> DownloadError:
    msg = str(exc)
    low = msg.lower()
    if _BOT_CHECK_RE.search(msg):
        return DownloadError(
            "🤖 يوتيوب بيحظر سيرفر Railway مؤقتاً وبيطلب تحقق «إني مش روبوت».\n"
            "الحل النهائي خلال دقيقة: أضف كوكيز حسابك في متغير YTDLP_COOKIES_TEXT "
            "(الخطوات في README ← قسم «يوتيوب يطلب تسجيل الدخول»)، وأي تحميل بعدها هينجح."
        )
    if "max_filesize" in low or "too large" in low or "file is larger" in low:
        return DownloadError("📦 الملف أكبر من الحد المسموح.")
    if "private" in low:
        return DownloadError("🔒 المحتوى خاص (Private) — لا يمكن تحميله.")
    if "age" in low and ("confirm" in low or "restrict" in low):
        return DownloadError("🔞 محتوى محظور على القُصّر — أضف كوكيز حسابك (YTDLP_COOKIES_TEXT) للتحميل.")
    if "unavailable" in low or "not available" in low or "removed" in low:
        return DownloadError("🚫 هذا المحتوى غير متاح أو تم حذفه.")
    if re.search(r"(does not look like a netscape|unable to load cookies|failed to load cookies|error loading cookies|cookie.*load.*error|load(ing)?.{0,30}cookie)", low):
        return DownloadError(
            "🍪 متغير YTDLP_COOKIES_TEXT مضبوط لكن yt-dlp لم يستطع قراءة الملف.\n"
            "افحص Deploy Logs على Railway — لازم تلاقي سطر «🍪 كوكيز يوتيوب: N سجل صالح».\n"
            "لو ظهر سطر «❌»، صحح القيمة: نفّذ `base64 -w0 cookies.txt` وضع الناتج بعد `base64:` — بدون أسطر وبلا مسافات."
        )
    if "login" in low or "sign in" in low or "cookies" in low:
        return DownloadError(
            "🔑 المنصة تمنع التحميل بدون كوكيز صالحة — راجع Deploy Logs على Railway؛\n"
            "لازم تلاقي سطر «🍪 كوكيز يوتيوب: N سجل صالح» — لو غير موجود فالكونفيج لم يُقرأ أو الكوكيز مكسورة."
        )
    if "unsupported url" in low:
        return DownloadError("🔗 الرابط غير مدعوم. جرّب رابطاً آخر.")
    if "timed out" in low or "timeout" in low:
        return DownloadError("⏰ انتهت مهلة الاتصال — حاول مرة أخرى.")
    if "no space" in low or "disk" in low:
        return DownloadError("💽 مساحة القرص غير كافية على الخادم.")
    if "403" in low or "forbidden" in low:
        return DownloadError("🚫 المنصة رفضت الطلب (403) — غالباً حظر مؤقت لسيرفرات السحابة. جرّب تاني بدري أو أضف كوكيز.")
    return DownloadError("⚠️ تعذر التحميل. تأكد من الرابط وحاول مرة أخرى.")


def _with_yt_fallback(build_opts, call, settings):
    """يجرب العملية بسلسلة عملاء يوتيوب ويعيد المحاولة فقط عند حظر «الروبوت»."""
    last_exc: Exception | None = None
    for clients in _YT_CLIENT_CHAIN:
        opts = build_opts()
        if clients:
            opts["extractor_args"] = {"youtube": {"player_client": clients}}
        try:
            return call(opts)
        except Exception as exc:
            last_exc = exc
            if not _BOT_CHECK_RE.search(str(exc)):
                raise _map_error(exc) from exc
            continue  # حظر روبوت؟ جرّب العميل التالي
    raise _map_error(last_exc) from last_exc  # type: ignore[arg-type]


def _extract(opts, url):
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def fetch_info_sync(url: str, platform: str, settings) -> MediaInfo:
    def build():
        opts = _base_opts(settings)
        opts["skip_download"] = True
        return opts

    data = _with_yt_fallback(build, lambda opts: _extract(opts, url), settings)

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


def download_audio_sync(info: MediaInfo, bitrate: str, settings, tmpdir: Path) -> Path:
    """تحميل أفضل صوت + تحويله إلى MP3 بالجودة المطلوبة. يرجع مسار الملف."""
    search_target = f"ytsearch1:{info.resolved_query}" if info.resolved_query else info.url
    outtmpl = str(tmpdir / "%(title).90s.%(ext)s")

    def build():
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
        return opts

    def call(opts):
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([search_target])

    _with_yt_fallback(build, call, settings)

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

    if height is None:
        fmt = "best[ext=mp4][vcodec!=none][acodec!=none]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
    else:
        fmt = (
            f"best[ext=mp4][height<={height}][vcodec!=none][acodec!=none]/"
            f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={height}]+bestaudio/"
            f"best[height<={height}]/best"
        )

    def build():
        opts = _base_opts(settings)
        opts.update({"format": fmt, "outtmpl": outtmpl, "merge_output_format": "mp4"})
        return opts

    def call(opts):
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([info.webpage_url or info.url])

    _with_yt_fallback(build, call, settings)

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
