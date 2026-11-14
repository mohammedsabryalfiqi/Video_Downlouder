"""لوحة التحكم — FastAPI + صفحة RTL عربية، تقرأ من نفس قاعدة بيانات البوت.

التشغيل:
    uvicorn dashboard.app:app --host 0.0.0.0 --port 8080

المصادقة (اختياري لكن موصى بها للنشر العام):
    DASHBOARD_PASSWORD=secret uvicorn dashboard.app:app ...
    ← بدونها اللوحة مفتوحة (مناسبة للمعاينة فقط).
"""

from __future__ import annotations

import hashlib
import hmac
import os
import sys
from pathlib import Path
from typing import Any

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot import __version__  # noqa: E402
from bot.config import settings  # noqa: E402
from bot.database import Database  # noqa: E402
from bot import permissions  # noqa: E402

STATIC_DIR = Path(__file__).resolve().parent / "static"

db = Database(settings.database_path)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await db.connect()
    if settings.seed_demo_data and await db.is_empty():
        from scripts.seed_demo import seed_demo_data

        await seed_demo_data(db)
    yield
    await db.close()


app = FastAPI(title="لوحة تحكم بوت تحميل الفيديوهات", version=__version__, docs_url=None, redoc_url=None, lifespan=lifespan)

COOKIE_NAME = "vd_auth"


def _auth_token() -> str:
    return hmac.new(settings.dashboard_password.encode(), b"vd-dashboard-v1", hashlib.sha256).hexdigest()


def _is_authed(request: Request) -> bool:
    cookie = request.cookies.get(COOKIE_NAME, "")
    return bool(cookie) and hmac.compare_digest(cookie, _auth_token())


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if not settings.dashboard_password:
        return await call_next(request)
    path = request.url.path
    if path.startswith(("/login", "/health")):
        return await call_next(request)
    if not _is_authed(request):
        if path.startswith("/api/"):
            return JSONResponse({"detail": "غير مصرح"}, status_code=401)
        return RedirectResponse("/login", status_code=303)
    return await call_next(request)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "version": __version__}

LOGIN_HTML = """<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>تسجيل الدخول | لوحة التحكم</title>
<style>
*{box-sizing:border-box;margin:0}
body{min-height:100vh;display:grid;place-items:center;background:#0b0f1a;font-family:'IBM Plex Sans Arabic','Segoe UI',Tahoma,sans-serif;color:#e8ecf8}
.card{width:min(400px,92vw);background:rgba(20,27,46,.85);border:1px solid rgba(124,140,255,.18);border-radius:22px;padding:38px 32px;text-align:center;backdrop-filter:blur(14px);box-shadow:0 30px 80px rgba(0,0,0,.5)}
.logo{font-size:52px;margin-bottom:6px}
h1{font-size:21px;margin-bottom:4px}
p{color:#8b93b8;font-size:13px;margin-bottom:22px}
input{width:100%;padding:13px 16px;border-radius:12px;border:1px solid rgba(124,140,255,.25);background:#0f1526;color:#fff;font-size:15px;outline:none}
input:focus{border-color:#7c3aed}
button{width:100%;margin-top:14px;padding:13px;border:none;border-radius:12px;background:linear-gradient(135deg,#7c3aed,#06b6d4);color:#fff;font-size:15px;font-weight:700;cursor:pointer}
.err{color:#f87171;font-size:13px;margin-top:10px;min-height:18px}
</style></head><body>
<form class="card" method="post" action="/login">
  <div class="logo">🎬</div>
  <h1>لوحة تحكم البوت</h1>
  <p>أدخل كلمة مرور المشرف للمتابعة</p>
  <input type="password" name="password" placeholder="كلمة المرور" autofocus required>
  <button type="submit">دخول 🔐</button>
  <div class="err" id="err"></div>
</form>
<script>if(location.search.includes('fail=1'))document.getElementById('err').textContent='❌ كلمة المرور غير صحيحة'</script>
</body></html>"""


@app.get("/login", response_class=HTMLResponse)
async def login_page() -> HTMLResponse:
    if not settings.dashboard_password:
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(LOGIN_HTML)


@app.post("/login")
async def login_submit(request: Request) -> RedirectResponse:
    form = await request.form()
    password = str(form.get("password", ""))
    if settings.dashboard_password and hmac.compare_digest(password, settings.dashboard_password):
        resp = RedirectResponse("/", status_code=303)
        resp.set_cookie(COOKIE_NAME, _auth_token(), httponly=True, samesite="lax", max_age=60 * 60 * 12)
        return resp
    return RedirectResponse("/login?fail=1", status_code=303)


@app.get("/logout")
async def logout() -> RedirectResponse:
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(COOKIE_NAME)
    return resp


# ─────────────────────────────── الـ API ───────────────────────────────

@app.get("/api/overview")
async def api_overview() -> dict[str, Any]:
    kpis = await db.overview()
    recent, _ = await db.recent_downloads(limit=8)
    return {
        "kpis": kpis,
        "recent": recent,
        "top_users": await db.top_users(5),
        "timeseries": await db.timeseries(30),
        "platforms": await db.platform_distribution(),
        "qualities": await db.quality_distribution(),
        "media_types": await db.media_type_distribution(),
    }


@app.get("/api/timeseries")
async def api_timeseries(days: int = 30) -> list[dict[str, Any]]:
    return await db.timeseries(max(1, min(days, 90)))


@app.get("/api/downloads")
async def api_downloads(
    limit: int = 20,
    offset: int = 0,
    platform: str | None = None,
    status: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    rows, total = await db.recent_downloads(
        limit=max(1, min(limit, 100)), offset=max(0, offset),
        platform=platform or None, status=status or None, search=search or None,
    )
    return {"rows": rows, "total": total, "limit": limit, "offset": offset}


@app.get("/api/users")
async def api_users(limit: int = 20, offset: int = 0, search: str | None = None) -> dict[str, Any]:
    rows, total = await db.list_users(
        limit=max(1, min(limit, 100)), offset=max(0, offset), search=search or None
    )
    return {"rows": rows, "total": total, "limit": limit, "offset": offset}


class BanBody(BaseModel):
    banned: bool


@app.post("/api/users/{telegram_id}/ban")
async def api_ban(telegram_id: int, body: BanBody) -> dict[str, Any]:
    ok = await db.set_banned(telegram_id, body.banned)
    if not ok:
        raise HTTPException(404, "المستخدم غير موجود")
    return {"ok": True, "banned": body.banned}


class BroadcastBody(BaseModel):
    text: str = Field(min_length=3, max_length=4000)


@app.post("/api/broadcasts", status_code=201)
async def api_create_broadcast(body: BroadcastBody) -> dict[str, Any]:
    broadcast_id = await db.create_broadcast(body.text.strip())
    return {"ok": True, "id": broadcast_id}


@app.get("/api/broadcasts")
async def api_broadcasts() -> list[dict[str, Any]]:
    return await db.list_broadcasts(limit=10)


@app.get("/api/config")
async def api_config() -> dict[str, Any]:
    db_admins = await db.list_admin_ids()
    all_admins = await permissions.all_admin_ids(db)
    return {
        "version": __version__,
        "bot_token_configured": bool(settings.bot_token),
        "owner_id": settings.owner_id,
        "admins_env": len(settings.env_admin_ids),
        "admins_db": len(db_admins),
        "admin_count": len(all_admins),
        "max_file_size_mb": settings.effective_max_file_size_mb,
        "local_api_mode": settings.local_api_mode,
        "daily_download_limit": settings.daily_download_limit,
        "request_cooldown_seconds": settings.request_cooldown_seconds,
        "dashboard_protected": bool(settings.dashboard_password),
        "database": os.path.basename(settings.database_path),
    }


# الصفحة الرئيسية + الملفات الثابتة
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    index_file = STATIC_DIR / "index.html"
    return HTMLResponse(index_file.read_text(encoding="utf-8"))
