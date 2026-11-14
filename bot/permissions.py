"""RBAC: المالك 👑 ← المشرفون (ADMIN_IDS + جدول admins) ← الجميع."""

from __future__ import annotations

from bot.config import settings
from bot.database import Database


def is_owner(user_id: int | None) -> bool:
    return bool(user_id) and user_id == settings.owner_id


async def is_admin(db: Database, user_id: int | None) -> bool:
    if not user_id:
        return False
    if user_id == settings.owner_id or user_id in settings.admin_ids:
        return True
    return await db.is_admin(user_id)


async def all_admin_ids(db: Database) -> list[int]:
    """القائمة الكاملة الفعلية: المالك + ADMIN_IDS + جدول admins."""
    extra = await db.list_admin_ids()
    return sorted(set(settings.admin_ids) | set(extra))
