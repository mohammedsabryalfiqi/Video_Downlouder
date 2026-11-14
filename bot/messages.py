"""رسائل البوت بالعربية — كل النصوص في مكان واحد لتسهيل التعديل والترجمة."""

from __future__ import annotations

from bot.constants import PLATFORM_EMOJI, PLATFORM_LABELS_AR, fmt_duration, fmt_views
from bot.services.downloader import MediaInfo

WELCOME = """🎬🎧 <b>أهلاً بيك في بوت تحميل الفيديوهات والأغاني!</b>

✨ <b>المميزات المتاحة:</b>

• تحميل فيديو MP4 من أي منصة (يوتيوب، تيك توك بدون علامة مائية، إنستجرام، فيسبوك، إكس…)
• استخراج الصوت MP3 بجودات متعددة (128k ، 192k ، 320k)
• تحميل أغاني من منصة سبوتيفاي 🟢
• تحميل أغاني من منصة أنجامي 🟣

📎 <b>أرسل الآن أي رابط أو مقطع فيديو للبدء!</b> 🚀"""

HELP = """📖 <b>طريقة الاستخدام</b>

1️⃣ انسخ رابط الفيديو أو الأغنية من أي منصة
2️⃣ الصقه هنا في المحادثة
3️⃣ هيظهرلك معاينة + أزرار الصيغ والجودات
4️⃣ اضغط الجودة اللي تعجبك وانتظر ثوانٍ ⚡

<b>المنصات المدعومة:</b>
يوتيوب ▶️ | تيك توك 🎵 (بدون علامة مائية) | إنستجرام 📸 | فيسبوك 📘 | إكس 𝕏 | ساوند كلاود 🟠 | سبوتيفاي 🟢 | أنجامي 🟣

<b>الأوامر:</b>
/start — الرسالة الترحيبية
/help — طريقة الاستخدام
/about — عن البوت
/stats — إحصائيات (للمشرفين)
/admins — قائمة المشرفين (للمشرفين)

🔞 <i>يوتيوب حظر السيرفر وبيطلب تحقق «مش روبوت»؟ أضف كوكيز حسابك (YTDLP_COOKIES_TEXT) — الخطوات في README.</i>"""

OWNER_NOTE = "👑 <b>أهلاً بعودتك أيها المالك!</b>\nأوامرك: /stats · /broadcast · /addadmin · /deladmin · /admins"

ABOUT = """ℹ️ <b>عن البوت</b>

أنا بوت عربي لتحميل الفيديوهات والصوتيات من كل المنصات المشهورة — مجاني وسريع وبدون علامة مائية.

💡 ملاحظة: التحميل للاستخدام الشخصي فقط — يُرجى احترام حقوق الملكية الفكرية لأصحاب المحتوى.

👨‍💻 إذا عجبتك الفكرة شارك البوت مع أصحابك ❤️"""

NOT_A_LINK = "🤔 مش لاقي رابط في رسالتك…\nانسخ الرابط من أي منصة والصقه هنا وأنا أتكفل بالباقي ✨"

LINK_SEEN = "🔍 جاري تحليل الرابط… ثوانٍ فقط"
FETCH_AUDIO = "🎶 جاري قراءة بيانات الأغنية من {platform}…"
CANCELLED = "❌ تم الإلغاء."
BANNED = "⛔ عذراً، تم حظرك من استخدام هذا البوت."
DOWNLOADING = "⬇️ جاري التحميل…"
CONVERTING_MP3 = "🎚 جاري استخراج الصوت بجودة {quality}…"
PROCESSING_MP4 = "🎬 جاري تجهيز الفيديو بجودة {quality}…"
UPLOADING = "⬆️ تم التحميل! جاري الرفع إلى تيليجرام…"
TOO_BIG = "📦 الملف أكبر من الحد الأقصى ({limit} م.بايت). جرّب جودة أقل — أو فعّل خادم Bot API المحلي (بلا حدود فعلياً حتى 2GB) كما في قسم Railway بالـ README."
DAILY_LIMIT = "⏳ وصلت للحد اليومي ({limit} تحميل). عد بكرة وأنا في انتظارك 🌟"
COOLDOWN = "🐢 شوية هدوء! انتظر لحظات ثم أرسل الرابط التالي."
SOMETHING_WRONG = "⚠️ حصل خطأ غير متوقع. حاول تاني، ولو استمرت المشكلة تواصل مع المشرف."
ERROR_PREFIX = "⚠️"


def preview_caption(info: MediaInfo) -> str:
    emoji = PLATFORM_EMOJI.get(info.platform, "🔗")
    platform = PLATFORM_LABELS_AR.get(info.platform, info.platform)
    duration = fmt_duration(info.duration)
    views = fmt_views(info.views)
    uploader = info.uploader or "—"

    lines = [f"{emoji} <b>{info.title}</b>", ""]
    lines.append(f"👤 {uploader}")
    if info.duration:
        lines.append(f"⏱ المدة: {duration}")
    if info.views is not None:
        lines.append(f"👁 المشاهدات: {views}")
    lines.append(f"🌐 المنصة: {platform}")
    lines += ["", "👇 <b>اختار الصيغة والجودة:</b>"]
    return "\n".join(lines)


QUALITY_DISPLAY = {"max": "🚀 بلا حدود (أفضل جودة)"}


def display_quality(quality: str) -> str:
    return QUALITY_DISPLAY.get(quality, quality)


def download_caption(info: MediaInfo, quality: str, media_type: str) -> str:
    if media_type == "mp3":
        head = f"🎧 <b>{info.title}</b>"
        sub = f"🎚 الجودة: MP3 · {display_quality(quality)}"
    else:
        head = f"🎬 <b>{info.title}</b>"
        sub = f"📹 الجودة: MP4 · {display_quality(quality)}"
    return (
        f"{head}\n{sub}\n\n"
        "✅ تم التحميل بنجاح! بالهنا والشفا 🌟\n"
        "<i>شاركنا رأيك، وأرسل أي رابط آخر للبدء من جديد 🚀</i>"
    )
