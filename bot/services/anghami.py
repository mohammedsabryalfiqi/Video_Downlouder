"""أنجامي: نقرأ وسوم og:* من صفحة الأغنية (مع حلّ الروابط المختصرة)، ثم نبحث عنها في يوتيوب.

أنجامي لا تُوفّر API عاماً، لذا نعتمد على Open Graph tags الموجودة في كل صفحة أغنية:
  og:title       → اسم الأغنية
  og:description → غالباً «أغنية · الفنان - الألبوم» أو ما شابه
  og:image       → غلاف الألبوم
لو تعذر التحليل، نستخدم عنوان الصفحة <title> كاحتياطي.
"""

from __future__ import annotations

import html as html_lib
import re

import aiohttp

from bot.services.downloader import DownloadError, MediaInfo

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept-Language": "ar,en;q=0.9",
}

_OG_PAIRS = re.compile(
    r'<meta[^>]+(?:property|name)=["\']([^"\']+)["\'][^>]+content=["\']([^"\']*)["\']', re.I
)
_OG_PAIRS_REV = re.compile(
    r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\']([^"\']+)["\']', re.I
)
_TWITTER_GENERIC = re.compile(
    r'<meta[^>]+(?:property|name)=["\']twitter:(\w+)["\'][^>]+content=["\']([^"\']*)["\']', re.I
)
_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
_SUFFIX_RE = re.compile(
    r"\s*[\|·\-–—]\s*(anghami|أنجامي|أنغامي|أنجامى).*$", re.I | re.S
)
_CLOUDFLARE_RE = re.compile(r"(just a moment|cf-browser-challenge|cloudflare|attention required)", re.I)


def _clean(text: str | None) -> str:
    if not text:
        return ""
    text = html_lib.unescape(text).strip()
    text = _SUFFIX_RE.sub("", text).strip()
    return text[:120]


async def _fetch_page(session: aiohttp.ClientSession, url: str) -> tuple[str, str]:
    async with session.get(url, allow_redirects=True) as resp:
        final_url = str(resp.url)
        html = await resp.text(errors="ignore")
        return final_url, html


async def fetch_song(url: str) -> MediaInfo:
    timeout = aiohttp.ClientTimeout(total=20)

    async with aiohttp.ClientSession(headers=_HEADERS, timeout=timeout) as session:
        try:
            final_url, html = await _fetch_page(session, url)
        except Exception as exc:
            raise DownloadError("🌐 تعذر فتح رابط أنجامي — تأكد منه وحاول مرة أخرى.") from exc

    # لو وصلتنا صفحة تحدٍّ من Cloudflare (شائعة مع سيرفرات السحابة) نعطي رسالة مفيدة
    if _CLOUDFLARE_RE.search(html):
        raise DownloadError(
            "🛡 أنجامي رفضت فتح الصفحة من الخادم (حماية Cloudflare).\n"
            "جرّب: 1) انسخ الرابط من زر «مشاركة» داخل التطبيق نفسه 2) وحاول مرة أخرى بعد قليل،\n"
            "أو ابحث عن الأغنية نفسها على يوتيوب وابعت رابطها مباشرة."
        )

    tags: dict[str, str] = {}
    for key, value in _OG_PAIRS.findall(html):
        tags[key.strip().lower()] = value
    for value, key in _OG_PAIRS_REV.findall(html):
        tags.setdefault(key.strip().lower(), value)
    for key, value in _TWITTER_GENERIC.findall(html):
        tags.setdefault(f"twitter:{key.strip().lower()}", value)

    def pick(*keys: str) -> str:
        for key in keys:
            value = tags.get(key)
            if value and value.strip():
                return value.strip()
        return ""

    title = _clean(pick("og:title", "twitter:title"))
    description = _clean(pick("og:description", "twitter:description", "description"))
    image = pick("og:image", "twitter:image") or None

    if not title:
        m = _TITLE_RE.search(html)
        title = _clean(m.group(1) if m else None)

    if not title:
        raise DownloadError("😕 تعذر قراءة بيانات الأغنية من أنجامي. جرّب نسخ الرابط من زر المشاركة.")

    # الوصف غالباً: «كلمات · الفنان – الألبوم» — نستخرج اسم الفنان لتحسين البحث
    artist = ""
    desc = description.replace("أغنية", " ").replace("Song", " ").strip(" ·-–—|")
    parts = re.split(r"[\-–—|·]", desc)
    parts = [p.strip() for p in parts if p and p.strip()]
    if len(parts) >= 2:
        artist = parts[0]

    query_base = f"{title} {artist}".strip()

    display = f"{title} — {artist}" if artist and artist.lower() not in title.lower() else title
    return MediaInfo(
        url=url,
        platform="anghami",
        title=display,
        uploader=artist or "Anghami",
        duration=None,
        views=None,
        thumbnail=image,
        is_audio_only=True,
        webpage_url=final_url,
        resolved_query=f"{query_base} audio",
        raw={"source": "anghami"},
    )
