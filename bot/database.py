"""طبقة قاعدة البيانات (SQLite عبر aiosqlite) — مشتركة بين البوت ولوحة التحكم.

الجداول:
  users       بيانات مستخدمي البوت
  downloads   سجل كل عملية تحميل (ناجحة / فاشلة)
  broadcasts  طابور الإذاعات القادمة من لوحة التحكم للبوت
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id  INTEGER UNIQUE NOT NULL,
    username     TEXT,
    first_name   TEXT,
    is_banned    INTEGER NOT NULL DEFAULT 0,
    joined_at    TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_users_joined ON users(joined_at);

CREATE TABLE IF NOT EXISTS downloads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    url         TEXT NOT NULL,
    platform    TEXT NOT NULL DEFAULT 'other',
    media_type  TEXT NOT NULL DEFAULT 'mp4',   -- mp4 | mp3
    quality     TEXT NOT NULL DEFAULT '—',      -- 720p | 192k ...
    title       TEXT,
    duration    INTEGER,                        -- بالثواني
    file_size   INTEGER,                        -- بالبايت
    status      TEXT NOT NULL DEFAULT 'done',   -- done | failed
    error       TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_downloads_created ON downloads(created_at);
CREATE INDEX IF NOT EXISTS idx_downloads_user    ON downloads(user_id);
CREATE INDEX IF NOT EXISTS idx_downloads_platform ON downloads(platform);
CREATE INDEX IF NOT EXISTS idx_downloads_status  ON downloads(status);

CREATE TABLE IF NOT EXISTS broadcasts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    text        TEXT NOT NULL,
    total       INTEGER NOT NULL DEFAULT 0,
    sent        INTEGER NOT NULL DEFAULT 0,
    failed      INTEGER NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'pending',  -- pending | sending | done
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT
);

-- مشرفو البوت المضافون من داخل البوت (بالإضافة إلى ADMIN_IDS والمالك)
CREATE TABLE IF NOT EXISTS admins (
    user_id     INTEGER PRIMARY KEY,
    added_by    INTEGER,
    added_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class Database:
    def __init__(self, path: str):
        self.path = path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        self._db = await aiosqlite.connect(self.path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._db.executescript(SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        assert self._db is not None, "Database.connect() لم تُستدعَ بعد"
        return self._db

    # ───────────────────────── المستخدمون ─────────────────────────

    async def upsert_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
    ) -> tuple[aiosqlite.Row, bool]:
        """يُنشئ المستخدم إن لم يوجد، ويحدّث آخر ظهور دائماً. يرجع (الصف, هل أُنشئ حديثاً)."""
        cur = await self.db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = await cur.fetchone()
        if row:
            await self.db.execute(
                "UPDATE users SET last_seen = ?, username = COALESCE(?, username), "
                "first_name = COALESCE(?, first_name) WHERE telegram_id = ?",
                (_utcnow(), username, first_name, telegram_id),
            )
            await self.db.commit()
            cur = await self.db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            return await cur.fetchone(), False

        await self.db.execute(
            "INSERT INTO users (telegram_id, username, first_name) VALUES (?, ?, ?)",
            (telegram_id, username, first_name),
        )
        await self.db.commit()
        cur = await self.db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        return await cur.fetchone(), True

    async def is_banned(self, telegram_id: int) -> bool:
        cur = await self.db.execute("SELECT is_banned FROM users WHERE telegram_id = ?", (telegram_id,))
        row = await cur.fetchone()
        return bool(row and row["is_banned"])

    async def download_count_today(self, telegram_id: int) -> int:
        cur = await self.db.execute(
            "SELECT COUNT(*) AS c FROM downloads d JOIN users u ON u.id = d.user_id "
            "WHERE u.telegram_id = ? AND date(d.created_at) = date('now')",
            (telegram_id,),
        )
        row = await cur.fetchone()
        return int(row["c"]) if row else 0

    # ───────────────────────── التنزيلات ─────────────────────────

    async def add_download(
        self,
        telegram_id: int,
        *,
        url: str,
        platform: str,
        media_type: str,
        quality: str,
        title: str | None,
        duration: int | None,
        file_size: int | None,
        status: str = "done",
        error: str | None = None,
    ) -> int:
        cur = await self.db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        row = await cur.fetchone()
        if not row:  # احتياط — يجب ألا يحدث
            await self.db.execute(
                "INSERT OR IGNORE INTO users (telegram_id) VALUES (?)", (telegram_id,)
            )
            cur = await self.db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            row = await cur.fetchone()
        await self.db.execute(
            "INSERT INTO downloads (user_id, url, platform, media_type, quality, title, duration, file_size, status, error) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (row["id"], url, platform, media_type, quality, title, duration, file_size, status, error),
        )
        await self.db.commit()
        cur = await self.db.execute("SELECT last_insert_rowid() AS id")
        return int((await cur.fetchone())["id"])

    # ───────────────────────── لوحة التحكم ─────────────────────────

    async def overview(self) -> dict[str, Any]:
        async def one(sql: str, params: tuple = ()):
            cur = await self.db.execute(sql, params)
            row = await cur.fetchone()
            return row

        users_total = (await one("SELECT COUNT(*) c FROM users"))["c"]
        users_today = (await one("SELECT COUNT(*) c FROM users WHERE date(joined_at) = date('now')"))["c"]
        banned = (await one("SELECT COUNT(*) c FROM users WHERE is_banned = 1"))["c"]
        active_today = (await one("SELECT COUNT(*) c FROM users WHERE date(last_seen) = date('now')"))["c"]

        dl_total = (await one("SELECT COUNT(*) c FROM downloads"))["c"]
        dl_today = (await one("SELECT COUNT(*) c FROM downloads WHERE date(created_at) = date('now')"))["c"]
        dl_yesterday = (await one("SELECT COUNT(*) c FROM downloads WHERE date(created_at) = date('now', '-1 day')"))["c"]
        done = (await one("SELECT COUNT(*) c FROM downloads WHERE status = 'done'"))["c"]
        failed = (await one("SELECT COUNT(*) c FROM downloads WHERE status = 'failed'"))["c"]
        bytes_sent = (await one("SELECT COALESCE(SUM(file_size), 0) s FROM downloads WHERE status = 'done'"))["s"]
        mp3_count = (await one("SELECT COUNT(*) c FROM downloads WHERE media_type = 'mp3'"))["c"]
        mp4_count = (await one("SELECT COUNT(*) c FROM downloads WHERE media_type = 'mp4'"))["c"]

        success_rate = round(done / (done + failed) * 100, 1) if (done + failed) else 100.0

        return {
            "users": users_total,
            "users_today": users_today,
            "banned": banned,
            "active_today": active_today,
            "downloads": dl_total,
            "downloads_today": dl_today,
            "downloads_yesterday": dl_yesterday,
            "done": done,
            "failed": failed,
            "success_rate": success_rate,
            "bytes_sent": bytes_sent,
            "mp3": mp3_count,
            "mp4": mp4_count,
        }

    async def timeseries(self, days: int = 30) -> list[dict[str, Any]]:
        cur = await self.db.execute(
            "SELECT date(created_at) AS day, COUNT(*) AS total, "
            "SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) AS done "
            "FROM downloads WHERE created_at >= date('now', ?) "
            "GROUP BY day ORDER BY day",
            (f"-{days - 1} days",),
        )
        rows = await cur.fetchall()
        return [{"day": r["day"], "total": r["total"], "done": r["done"] or 0} for r in rows]

    async def platform_distribution(self) -> list[dict[str, Any]]:
        cur = await self.db.execute(
            "SELECT platform, COUNT(*) c FROM downloads GROUP BY platform ORDER BY c DESC"
        )
        return [{"platform": r["platform"], "count": r["c"]} for r in await cur.fetchall()]

    async def quality_distribution(self) -> list[dict[str, Any]]:
        cur = await self.db.execute(
            "SELECT quality, COUNT(*) c FROM downloads GROUP BY quality ORDER BY c DESC"
        )
        return [{"quality": r["quality"], "count": r["c"]} for r in await cur.fetchall()]

    async def media_type_distribution(self) -> list[dict[str, Any]]:
        cur = await self.db.execute(
            "SELECT media_type, COUNT(*) c FROM downloads GROUP BY media_type"
        )
        return [{"media_type": r["media_type"], "count": r["c"]} for r in await cur.fetchall()]

    async def recent_downloads(
        self,
        limit: int = 10,
        offset: int = 0,
        platform: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        where, params = [], []
        if platform:
            where.append("d.platform = ?")
            params.append(platform)
        if status:
            where.append("d.status = ?")
            params.append(status)
        if search:
            where.append("(d.title LIKE ? OR u.first_name LIKE ? OR u.username LIKE ?)")
            params += [f"%{search}%", f"%{search}%", f"%{search}%"]
        clause = ("WHERE " + " AND ".join(where)) if where else ""

        cur = await self.db.execute(
            f"SELECT COUNT(*) c FROM downloads d JOIN users u ON u.id = d.user_id {clause}", params
        )
        total = (await cur.fetchone())["c"]

        cur = await self.db.execute(
            f"SELECT d.*, u.first_name, u.username, u.telegram_id "
            f"FROM downloads d JOIN users u ON u.id = d.user_id {clause} "
            f"ORDER BY d.created_at DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )
        rows = [dict(r) for r in await cur.fetchall()]
        return rows, total

    async def list_users(
        self,
        limit: int = 20,
        offset: int = 0,
        search: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        where, params = [], []
        if search:
            where.append("(u.first_name LIKE ? OR u.username LIKE ? OR CAST(u.telegram_id AS TEXT) LIKE ?)")
            params += [f"%{search}%", f"%{search}%", f"%{search}%"]
        clause = ("WHERE " + " AND ".join(where)) if where else ""

        cur = await self.db.execute(f"SELECT COUNT(*) c FROM users u {clause}", params)
        total = (await cur.fetchone())["c"]

        cur = await self.db.execute(
            f"SELECT u.*, (SELECT COUNT(*) FROM downloads d WHERE d.user_id = u.id) AS dl_count "
            f"FROM users u {clause} ORDER BY u.joined_at DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )
        rows = [dict(r) for r in await cur.fetchall()]
        return rows, total

    async def top_users(self, limit: int = 5) -> list[dict[str, Any]]:
        cur = await self.db.execute(
            "SELECT u.first_name, u.username, u.telegram_id, COUNT(d.id) AS dl_count "
            "FROM users u JOIN downloads d ON d.user_id = u.id "
            "GROUP BY u.id ORDER BY dl_count DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def set_banned(self, telegram_id: int, banned: bool) -> bool:
        cur = await self.db.execute(
            "UPDATE users SET is_banned = ? WHERE telegram_id = ?", (1 if banned else 0, telegram_id)
        )
        await self.db.commit()
        return cur.rowcount > 0

    # ───────────────────────── الإذاعة ─────────────────────────

    async def create_broadcast(self, text: str) -> int:
        total = (await (await self.db.execute(
            "SELECT COUNT(*) c FROM users WHERE is_banned = 0")).fetchone())["c"]
        await self.db.execute(
            "INSERT INTO broadcasts (text, total) VALUES (?, ?)", (text, total)
        )
        await self.db.commit()
        cur = await self.db.execute("SELECT last_insert_rowid() AS id")
        return int((await cur.fetchone())["id"])

    async def claim_next_broadcast(self) -> aiosqlite.Row | None:
        """يأخذ أول إذاعة معلّقة ويحوّلها إلى 'sending' — يُناديه البوت."""
        cur = await self.db.execute(
            "SELECT * FROM broadcasts WHERE status = 'pending' ORDER BY id LIMIT 1"
        )
        row = await cur.fetchone()
        if row:
            await self.db.execute("UPDATE broadcasts SET status = 'sending' WHERE id = ?", (row["id"],))
            await self.db.commit()
        return row

    async def broadcast_progress(self, broadcast_id: int, sent: int, failed: int) -> None:
        await self.db.execute(
            "UPDATE broadcasts SET sent = ?, failed = ? WHERE id = ?", (sent, failed, broadcast_id)
        )
        await self.db.commit()

    async def broadcast_done(self, broadcast_id: int) -> None:
        await self.db.execute(
            "UPDATE broadcasts SET status = 'done', finished_at = ? WHERE id = ?",
            (_utcnow(), broadcast_id),
        )
        await self.db.commit()

    async def active_user_ids(self) -> list[int]:
        cur = await self.db.execute("SELECT telegram_id FROM users WHERE is_banned = 0")
        return [r["telegram_id"] for r in await cur.fetchall()]

    async def list_broadcasts(self, limit: int = 10) -> list[dict[str, Any]]:
        cur = await self.db.execute(
            "SELECT * FROM broadcasts ORDER BY id DESC LIMIT ?", (limit,)
        )
        return [dict(r) for r in await cur.fetchall()]

    async def is_empty(self) -> bool:
        cur = await self.db.execute("SELECT COUNT(*) c FROM users")
        return (await cur.fetchone())["c"] == 0

    # ───────────────────────── المشرفون (RBAC) ─────────────────────────

    async def add_admin(self, telegram_id: int, added_by: int | None = None) -> bool:
        cur = await self.db.execute(
            "INSERT OR IGNORE INTO admins (user_id, added_by) VALUES (?, ?)",
            (telegram_id, added_by),
        )
        await self.db.commit()
        return cur.rowcount > 0

    async def remove_admin(self, telegram_id: int) -> bool:
        cur = await self.db.execute("DELETE FROM admins WHERE user_id = ?", (telegram_id,))
        await self.db.commit()
        return cur.rowcount > 0

    async def list_admin_ids(self) -> list[int]:
        cur = await self.db.execute("SELECT user_id FROM admins ORDER BY added_at")
        return [r["user_id"] for r in await cur.fetchall()]

    async def is_admin(self, telegram_id: int) -> bool:
        cur = await self.db.execute("SELECT 1 FROM admins WHERE user_id = ?", (telegram_id,))
        return await cur.fetchone() is not None
