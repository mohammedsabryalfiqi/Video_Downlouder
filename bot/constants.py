"""ثوابت البوت: اكتشاف المنصات، الجودات، التنسيق."""

from __future__ import annotations

import re

# ── اكتشاف المنصة من الرابط ────────────────────────────────────────────────
URL_REGEX = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)

PLATFORM_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("youtube", re.compile(r"(youtube\.com|youtu\.be|youtube-nocookie\.com|m\.youtube)", re.I)),
    ("tiktok", re.compile(r"(tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com)", re.I)),
    ("instagram", re.compile(r"instagram\.com", re.I)),
    ("facebook", re.compile(r"(facebook\.com|fb\.watch|fb\.com)", re.I)),
    ("x", re.compile(r"(x\.com|twitter\.com|t\.co)", re.I)),
    ("spotify", re.compile(r"(open\.spotify\.com|spotify\.link)", re.I)),
    ("anghami", re.compile(r"(anghami\.com|play\.anghami\.com|anghami\.link)", re.I)),
    ("soundcloud", re.compile(r"soundcloud\.com", re.I)),
]


def detect_platform(url: str) -> str:
    for name, pattern in PLATFORM_PATTERNS:
        if pattern.search(url):
            return name
    return "other"


PLATFORM_LABELS_AR: dict[str, str] = {
    "youtube": "يوتيوب",
    "tiktok": "تيك توك",
    "instagram": "إنستجرام",
    "facebook": "فيسبوك",
    "x": "إكس",
    "spotify": "سبوتيفاي",
    "anghami": "أنجامي",
    "soundcloud": "ساوند كلاود",
    "other": "رابط خارجي",
}

PLATFORM_EMOJI: dict[str, str] = {
    "youtube": "▶️",
    "tiktok": "🎵",
    "instagram": "📸",
    "facebook": "📘",
    "x": "𝕏",
    "spotify": "🟢",
    "anghami": "🟣",
    "soundcloud": "🟠",
    "other": "🔗",
}

# المنصات الصوتية التي يكون فيها المحتوى أغنية (بدون خيارات الفيديو)
AUDIO_ONLY_PLATFORMS = {"spotify", "anghami"}

# ── خيارات الجودة ──────────────────────────────────────────────────────────
# خيار "max" = أفضل جودة متاحة على المنصة مهما كان حجم الملف (بلا حدود)
MP4_QUALITIES = ["360p", "720p", "1080p", "max"]
MP4_QUALITY_LABELS = {"360p": "360p", "720p": "720p", "1080p": "1080p", "max": "🚀 بلا حدود"}
MP3_QUALITIES = ["128k", "192k", "320k"]
MP4_HEIGHT = {"360p": 360, "720p": 720, "1080p": 1080, "max": None}

# ── نصوص مساعدة للتنسيق ────────────────────────────────────────────────────

def fmt_duration(seconds: float | int | None) -> str:
    if not seconds:
        return "غير معروفة"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def fmt_views(views: int | None) -> str:
    if views is None:
        return "—"
    if views >= 1_000_000:
        return f"{views / 1_000_000:.1f} مليون"
    if views >= 1_000:
        return f"{views / 1_000:.1f} ألف"
    return str(views)


def fmt_bytes(num: float | int | None) -> str:
    if not num:
        return "0 بايت"
    num = float(num)
    for unit in ("بايت", "ك.بايت", "م.بايت", "ج.بايت"):
        if num < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} ت.بايت"


def progress_bar(percent: float, width: int = 14) -> str:
    filled = int(round(width * max(0.0, min(1.0, percent)) / 100))
    return "█" * filled + "░" * (width - filled)
