"""بذر بيانات عرض (Demo) في قاعدة البيانات — للمعاينة والاختبار فقط.

⚠️ لا تُشغّل هذا على قاعدة بيانات حقيقية يستخدمها البوت.
الاستخدام:
    python -m scripts.seed_demo            # يبذر ./data/bot.db لو فاضية
    SEED_DEMO_DATA=true python -m dashboard.app   # البذور تلقائياً عند أول تشغيل
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta, timezone

from bot.config import settings
from bot.database import Database

random.seed(20261113)

FIRST_NAMES = [
    "أحمد", "محمد", "محمود", "يوسف", "عمر", "كريم", "مصطفى", "حسن", "حسين", "علي",
    "إسلام", "عبد الله", "زياد", "طارق", "مروان", "أدهم", "سارة", "فاطمة", "مريم", "آية",
    "ليلى", "هدى", "نور", "جنى", "ياسمين", "سلمى", "رنا", "دينا", "منة", "شهد",
    "خالد", "حسام", "أمير", "شادي", "ريان", "ملك", "جنة", "تالا", "تولين", "ليان",
]
LAST_NAMES = [
    "محمد", "علي", "حسن", "إبراهيم", "سعيد", "عبد العزيز", "الشريف", "النجار", "فؤاد", "زكي",
    "عرفة", "الشاذلي", "قنديل", "البحيري", "زيدان", "الشامي", "الحربي", "النجار", "سليم", "فواز",
    "العوضي", "الدقن", "مرعي", "الشيخ", "جودة",
]

YOUTUBE_TITLES = [
    "شرح بايثون من الصفر حتى الاحتراف 🐍", "مراجعة آيفون 17 برو ماكس", "أجمل 10 أماكن في مصر تستحق الزيارة",
    "ملخص مباراة الأهلي والزمالك كاملة ⚽", "وصفة رز بلبن أشهى من الحلواني", "تعلم الإنجليزية في 30 يوم — خطة عملية",
    "فيصل العيسى | سيطرة (Official Video)", "عمرو دياب | نور العين — Live from Cairo", "طريقة عمل كيكة الشوكولاتة في الخلاط",
    "أفضل لابتوب للبرمجة في 2026 💻", "قناة وثائقية: داخل أهرامات الجيزة", "تمارين البطن في البيت بدون معدات",
    "محمود الليثي | يا سهران (حصري)", "وداعاً للنسيان: طريقة للمذاكرة تثبت المعلومات", "تجربة تشغيل ويندوز على هاتف أندرويد",
]
TIKTOK_TITLES = [
    "ترند الرقصة الأخيرة 😱🔥", "لحظة طريفة لا تُفوت في الشارع", "وصفة كيتو في 5 دقائق فقط",
    "كبف تتكلم إنجليزي بطلاقة في سنة", "مشهد من مسلسل قيامة عثمان يثير الجدل", "حيل ذكية للموبايل ماحدش يعرفها",
    "مقلب جامد في صاحبي", "أم تطبخ أروع كشري في العالم", "تقنية رسم ثلاثي الأبعاد بالقلم",
]
INSTAGRAM_TITLES = [
    "ريلز: غروب الشمس على البحر 🌅", "خروجة القاهرة مع الأصحاب", "وصفات سريعة قبل النوم",
    "ستوري يومية — روتين الصباح", "تصوير احترافي بالموبايل فقط", "إطلالة اليوم ✨",
]
FACEBOOK_TITLES = [
    "بث مباشر: حلقة برنامج الحكاية مع عمرو أديب", "مباراة الهلال السعودي كاملة بدوري الأبطال",
    "مؤتمر صحفي كامل: تصريحات المدرب بعد الفوز", "فيديو انتشر كالنار: قطة تنقذ طفل",
]
X_TITLES = [
    "لحظة انتشار قطة تقفز في الهواء 🐈", "تصريح غامض من الوزير يربك الشارع", "تسريب مواصفات الهاتف القادم",
]
SONG_TITLES = [
    "فيروز | نسم علينا الهوى", "أم كلثوم | الأطلال", "عمرو دياب | نور العين", "شيرين | بتكلم عنك",
    "تامر حسني | حياتي ملهاش طعم", "كاظم الساهر | إني مخيّرتك", "نانسي عجرم | يا طبطب",
    "إليسا | بتمنى تشوف", "رابح صقر | يا ليت", "عبد المجيد عبد الله | أحلى إحساس",
    "محمد عبد الوهاب | إنت عمري", "صباح | يا حلو صبح", "فايزة أحمد | فين الحبيب",
    "محمد منير | الليلة يا سمرا", "عزيزة جلال | ليالينا",
]

PLATFORM_TITLES = {
    "youtube": (YOUTUBE_TITLES, 0.34),
    "tiktok": (TIKTOK_TITLES, 0.22),
    "instagram": (INSTAGRAM_TITLES, 0.14),
    "facebook": (FACEBOOK_TITLES, 0.08),
    "x": (X_TITLES, 0.05),
    "spotify": (SONG_TITLES, 0.09),
    "anghami": (SONG_TITLES, 0.06),
    "soundcloud": (SONG_TITLES, 0.02),
}

QUALITIES_MP4 = ["360p", "720p", "1080p"]
QUALITIES_MP3 = ["128k", "192k", "320k"]
QUALITY_WEIGHTS_MP4 = [0.3, 0.5, 0.2]
QUALITY_WEIGHTS_MP3 = [0.2, 0.45, 0.35]

ERRORS = [
    "Video unavailable", "Sign in to confirm your age", "HTTP Error 429: Too Many Requests",
    "This content is private", "Request timed out", "Unsupported URL",
]


def _weighted_platform() -> str:
    r = random.random()
    acc = 0.0
    for platform, (_, weight) in PLATFORM_TITLES.items():
        acc += weight
        if r <= acc:
            return platform
    return "youtube"


async def seed_demo_data(db: Database) -> None:
    cur = await db.db.execute("SELECT COUNT(*) c FROM users")
    if (await cur.fetchone())["c"] > 0:
        return  # لا نكرر البذر

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_span = max(int((now - today_start).total_seconds()), 60)

    # ── المستخدمون ──────────────────────────────────────────────
    users: list[tuple[int, str | None, str, datetime, datetime]] = []
    seen_names: set[str] = set()
    for i in range(420):
        while True:  # noqa: PERF203 - وضوح أكثر من الأداء هنا
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            full = f"{first} {last}"
            if full not in seen_names:
                seen_names.add(full)
                break
        username = f"user{random.randint(10000, 999999)}"
        telegram_id = 100_000_000 + i * 7919 + random.randint(1, 5000)
        days_ago = random.triangular(0, 60, 55)
        joined = now - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        seen = joined + timedelta(hours=random.randint(1, 400))
        seen = min(seen, now)
        users.append((telegram_id, username, first, joined, seen))

    # مستخدمون جدُد اليوم/أمس صراحةً حتى تُقرأ المؤشرات حية
    for idx in [3, 17, 42, 108, 173, 251, 305, 389]:
        telegram_id, username, first, _, _ = users[idx]
        users[idx] = (telegram_id, username, first, now - timedelta(seconds=random.randint(0, today_span)), now)
    for idx in [7, 61, 130, 224, 298]:
        telegram_id, username, first, _, _ = users[idx]
        users[idx] = (telegram_id, username, first, now - timedelta(days=1, minutes=random.randint(5, 800)), now)

    for telegram_id, username, first, joined, seen in users:
        await db.db.execute(
            "INSERT INTO users (telegram_id, username, first_name, is_banned, joined_at, last_seen) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                telegram_id,
                username,
                first,
                1 if random.random() < 0.015 else 0,
                joined.strftime("%Y-%m-%d %H:%M:%S"),
                seen.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
    await db.db.commit()

    cur = await db.db.execute("SELECT id FROM users")
    user_ids = [r["id"] for r in await cur.fetchall()]

    # ── التنزيلات ───────────────────────────────────────────────
    def build_row(created: datetime) -> tuple:
        platform = _weighted_platform()
        titles, _ = PLATFORM_TITLES[platform]
        title = random.choice(titles)
        is_audio = platform in {"spotify", "anghami", "soundcloud"} or random.random() < 0.35
        media_type = "mp3" if is_audio else "mp4"
        quality = (
            random.choices(QUALITIES_MP3, QUALITY_WEIGHTS_MP3)[0]
            if is_audio
            else random.choices(QUALITIES_MP4, QUALITY_WEIGHTS_MP4)[0]
        )
        duration = random.randint(45, 900)
        if media_type == "mp3":
            bitrate = int(quality.rstrip("k"))
            file_size = int(duration * bitrate * 1000 / 8 * random.uniform(0.95, 1.05))
        else:
            mb_per_sec = {"360p": 0.06, "720p": 0.17, "1080p": 0.32}[quality]
            file_size = int(duration * mb_per_sec * 1024 * 1024 * random.uniform(0.7, 1.3))

        failed = random.random() < 0.045
        return (
            random.choice(user_ids),
            f"https://example.com/watch/{random.randint(10**8, 10**9)}",
            platform,
            media_type,
            quality,
            title,
            duration,
            None if failed else file_size,
            "failed" if failed else "done",
            random.choice(ERRORS) if failed else None,
            created.strftime("%Y-%m-%d %H:%M:%S"),
        )

    rows = []
    for _ in range(1650):
        created = now - timedelta(
            days=random.triangular(0, 30, 2),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )
        rows.append(build_row(created))

    # ضمان نشاط حي لليوم ولأمس حتى تُقرأ مؤشرات اللوحة بشكل واقعي
    for _ in range(30):
        rows.append(build_row(now - timedelta(seconds=random.randint(0, today_span))))
    for _ in range(22):
        rows.append(build_row(now - timedelta(days=1, minutes=random.randint(0, 1400))))

    await db.db.executemany(
        "INSERT INTO downloads (user_id, url, platform, media_type, quality, title, duration, file_size, status, error, created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    await db.db.commit()


async def main() -> None:
    db = Database(settings.database_path)
    await db.connect()
    if await db.is_empty():
        await seed_demo_data(db)
        cur = await db.db.execute("SELECT COUNT(*) c FROM downloads")
        users = (await (await db.db.execute("SELECT COUNT(*) c FROM users")).fetchone())["c"]
        dls = (await cur.fetchone())["c"]
        print(f"✅ تم بذر البيانات: {users} مستخدم، {dls} تحميل في {settings.database_path}")
    else:
        print("ℹ️ قاعدة البيانات غير فاضية — لم يتم تغيير شيء.")
    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
