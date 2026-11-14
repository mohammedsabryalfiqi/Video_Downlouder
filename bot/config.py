"""إعدادات البوت — تُقرأ من متغيرات البيئة (أو ملف .env محلياً).

مُهيأة للنشر على Railway:
  • اللوحة تقرأ المنفذ من PORT تلقائياً عبر scripts/start-dashboard.sh
  • DATABASE_PATH يمكن توجيهه إلى Volume مركّب
  • TELEGRAM_LOCAL_API (اختياري) لتفعيل حدود تيليجرام المحلية (حتى 2GB)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # python-dotenv اختياري
    pass

ROOT = Path(__file__).resolve().parent.parent

# 👑 المالك — دائماً مشرف بكل الصلاحيات حتى لو لم يُضف لـ ADMIN_IDS
DEFAULT_OWNER_ID = 5231453921


def _parse_ids(raw: str) -> list[int]:
    ids: list[int] = []
    for chunk in raw.replace(";", ",").split(","):
        chunk = chunk.strip()
        if chunk.isdigit():
            ids.append(int(chunk))
    return ids


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    # ── Telegram ──────────────────────────────────────────────
    bot_token: str = os.getenv("BOT_TOKEN", "")
    owner_id: int = _int_env("OWNER_ID", DEFAULT_OWNER_ID)
    _admin_ids: tuple[int, ...] = field(
        default_factory=lambda: tuple(_parse_ids(os.getenv("ADMIN_IDS", "")))
    )

    # ── خادم Bot API محلي (اختياري — لرفع الملفات حتى 2GB) ─────
    # مثال: TELEGRAM_LOCAL_API=http://telegram-bot-api:8081
    telegram_local_api: str = os.getenv("TELEGRAM_LOCAL_API", "").rstrip("/")

    # ── قاعدة البيانات والتخزين المؤقت ─────────────────────────
    database_path: str = os.getenv("DATABASE_PATH", str(ROOT / "data" / "bot.db"))
    download_dir: str = os.getenv("DOWNLOAD_DIR", str(ROOT / "downloads"))

    # ── حدود الاستخدام (0 = بلا حدود) ──────────────────────────
    # 0 في MAX_FILE_SIZE_MB تعني «تلقائي»: 2000MB مع خادم محلي، و49MB بدونه
    max_file_size_mb: int = _int_env("MAX_FILE_SIZE_MB", 0)
    request_cooldown_seconds: float = float(os.getenv("REQUEST_COOLDOWN", "0"))
    daily_download_limit: int = _int_env("DAILY_DOWNLOAD_LIMIT", 0)  # 0 = بلا حد يومي
    pending_ttl_seconds: int = _int_env("PENDING_TTL", "900")

    # ── خيارات متقدمة لـ yt-dlp (اختياري) ───────────────────────
    ytdlp_proxy: str = os.getenv("YTDLP_PROXY", "")            # مثال: socks5://user:pass@host:1080
    ytdlp_cookies_file: str = os.getenv("YTDLP_COOKIES_FILE", "")  # ملف كوكيز (Netscape) للمحتوى المحظور
    # محتوى الكوكيز نفسه كأسطر — أو base64:<...> — مثالي لـ Railway (لا حاجة لرفع ملفات)
    ytdlp_cookies_text: str = os.getenv("YTDLP_COOKIES_TEXT", "")

    # ── لوحة التحكم ────────────────────────────────────────────
    dashboard_password: str = os.getenv("DASHBOARD_PASSWORD", "")
    seed_demo_data: bool = os.getenv("SEED_DEMO_DATA", "false").lower() in {"1", "true", "yes", "on"}

    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # ── مشتقات ─────────────────────────────────────────────────
    @property
    def env_admin_ids(self) -> tuple[int, ...]:
        """المشرفون المعرفون في متغير البيئة فقط (بدون المالك)."""
        return self._admin_ids

    @property
    def admin_ids(self) -> tuple[int, ...]:
        """كل المشرفين: قائمة البيئة + المالك (دائماً)."""
        return tuple(sorted(set(self._admin_ids) | {self.owner_id}))

    @property
    def local_api_mode(self) -> bool:
        """True لو مفعّل خادم Bot API المحلي."""
        return bool(self.telegram_local_api)

    @property
    def effective_max_file_size_mb(self) -> int:
        if self.max_file_size_mb > 0:
            return self.max_file_size_mb
        return 2000 if self.local_api_mode else 49

    @property
    def max_file_size_bytes(self) -> int:
        return self.effective_max_file_size_mb * 1024 * 1024


settings = Settings()
