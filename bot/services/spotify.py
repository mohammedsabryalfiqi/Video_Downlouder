"""سبوتيفاي: نقرأ بيانات الأغنية من صفحة التضمين (بدون مفاتيح API)، ثم نبحث عنها في يوتيوب.

open.spotify.com/embed/track/<id> يعيد HTML فيه JSON-LD بالاسم والفنان والمدة والغلاف.
لو فشل، نستخدم oEmbed كاحتياطي.
"""

from __future__ import annotations

import json
import re

import aiohttp

from bot.services.downloader import DownloadError, MediaInfo

_TRACK_RE = re.compile(r"open\.spotify\.com/(?:intl-[a-z]{2}/)?track/([A-Za-z0-9]+)", re.I)
_ALBUM_RE = re.compile(r"open\.spotify\.com/(?:intl-[a-z]{2}/)?(album|playlist)/([A-Za-z0-9]+)", re.I)
_DUR_RE = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept-Language": "ar,en;q=0.9",
}


def parse_spotify_url(url: str):
    """يرجع (kind, id) حيث kind ∈ track|album|playlist|None."""
    m = _TRACK_RE.search(url)
    if m:
        return "track", m.group(1)
    m = _ALBUM_RE.search(url)
    if m:
        return m.group(1), m.group(2)
    # روابط مختصرة spotify.link — نحلّها في fetch_track
    if "spotify.link" in url:
        return "shortlink", None
    return None, None


async def _resolve_shortlink(session: aiohttp.ClientSession, url: str) -> str:
    async with session.head(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=15)) as r:
        return str(r.url)


def _iso_duration(value: str | None) -> int | None:
    if not value:
        return None
    m = _DUR_RE.fullmatch(value.strip())
    if not m:
        return None
    h, mnt, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mnt * 60 + s


async def fetch_track(url: str, platform: str = "spotify") -> MediaInfo:
    kind, track_id = parse_spotify_url(url)
    timeout = aiohttp.ClientTimeout(total=20)

    async with aiohttp.ClientSession(headers=_HEADERS, timeout=timeout) as session:
        if kind == "shortlink":
            url = await _resolve_shortlink(session, url)
            kind, track_id = parse_spotify_url(url)

        if kind in {"album", "playlist"}:
            raise DownloadError("📋 الألبومات والقوائم غير مدعومة حالياً — أرسل رابط أغنية واحدة (track).")
        if kind != "track" or not track_id:
            raise DownloadError("🔗 رابط سبوتيفاي غير مفهوم. أرسل رابط أغنية (track).")

        # 1) صفحة التضمين (فيها JSON-LD غني)
        title = artist = thumbnail = None
        duration = None
        try:
            async with session.get(f"https://open.spotify.com/embed/track/{track_id}") as r:
                html = await r.text(errors="ignore")
            m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
            if m:
                data = json.loads(m.group(1))
                title = data.get("name")
                by_artist = data.get("byArtist") or []
                if isinstance(by_artist, list):
                    artist = ", ".join(a.get("name", "") for a in by_artist if a.get("name"))
                elif isinstance(by_artist, dict):
                    artist = by_artist.get("name")
                duration = _iso_duration(data.get("duration"))
                thumbnail = data.get("thumbnailUrl")
        except Exception:
            pass

        # 2) احتياطي: oEmbed
        if not title:
            try:
                async with session.get(
                    "https://open.spotify.com/oembed", params={"url": f"https://open.spotify.com/track/{track_id}"}
                ) as r:
                    data = await r.json(content_type=None)
                    title = data.get("title")
                    thumbnail = thumbnail or data.get("thumbnail_url")
            except Exception:
                pass

    if not title:
        raise DownloadError("😕 تعذر قراءة بيانات الأغنية من سبوتيفاي. حاول مرة أخرى.")

    title = re.sub(r"\s*[\|–-]\s*Spotify\s*$", "", title).strip()
    artist = (artist or "").strip()
    query = f"{artist} - {title}" if artist else title

    display = f"{title} — {artist}" if artist else title
    return MediaInfo(
        url=url,
        platform=platform,
        title=display,
        uploader=artist or "Spotify",
        duration=duration,
        views=None,
        thumbnail=thumbnail,
        is_audio_only=True,
        webpage_url=url,
        resolved_query=f"{query} audio",
        raw={"source": "spotify"},
    )
