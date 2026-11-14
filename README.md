<div align="center">

# 🎬🎧 Video Downloader — بوت تحميل الفيديوهات MP4 والأغاني MP3

**بوت تيليجرام كامل بالعربية** لتحميل الفيديوهات من أي منصة واستخراج الصوت MP3 —
**بلا حدود** للحجم والعدد — مع **لوحة تحكم ويب** لإدارة البوت، وجاهز للنشر على **Railway** بأمر واحد.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-2AABEE?logo=telegram&logoColor=white)](https://docs.aiogram.dev)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-2026.x-FF0000?logo=youtube&logoColor=white)](https://github.com/yt-dlp/yt-dlp)
[![FastAPI](https://img.shields.io/badge/FastAPI-لوحة_التحكم-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Railway](https://img.shields.io/badge/Railway-جاهز_للنشر-0B0D0E?logo=railway&logoColor=white)](https://railway.app)

</div>

---

## ✨ المميزات

| الميزة | التفاصيل |
|---|---|
| 🎬 **تحميل MP4 من أي منصة** | يوتيوب، تيك توك **بدون علامة مائية**، إنستجرام، فيسبوك، إكس، ساوند كلاود… |
| 🚀 **بلا حدود** | لا حد لعدد التحميلات ولا لليومية، وأحجام حتى **2GB** مع خادم Bot API المحلي |
| 🎧 **استخراج MP3** | 128k / 192k / 320k عبر ffmpeg |
| 🟢 **سبوتيفاي** | الصق رابط الأغنية — يقرأ اسمها وفنانها تلقائياً ← MP3 بأي جودة |
| 🟣 **أنجامي** | نفس الفكرة: رابط أنجامي ← MP3 عالي الجودة |
| 👀 **معاينة حية** | غلاف + عنوان + مدة + مشاهدات + أزرار الجودة داخل المحادثة |
| 👑 **نظام صلاحيات كامل** | مالك (5231453921) + مشرفون من `.env` + مشرفون يُضافون من داخل البوت |
| 📊 **لوحة تحكم عربية RTL** | إحصائيات حية، سجل تنزيلات قابل للفلترة والتصدير CSV، إدارة مستخدمين + حظر، إذاعة جماعية، معاينة تفاعلية للبوت نفسه |
| 🗄 **قاعدة بيانات مشتركة** | SQLite واحدة يتشاركها البوت ولوحة التحكم — بدون خوادم خارجية |

---

## 🚂 النشر على Railway (خطوة بخطوة — مجاني)

> المشروع مُعدّ بالكامل لـ Railway: `Dockerfile` + `railway.json` + سكربت تشغيل يجمع البوت واللوحة في خدمة واحدة تتشارك Volume واحدة.

### 1) ارفع الكود على GitHub
```bash
git add .
git commit -m "🚀 Video Downloader Bot + لوحة التحكم — جاهز لـ Railway"
git push origin main
```

### 2) أنشئ المشروع على Railway
1. ادخل [railway.app](https://railway.app) ← **New Project** ← **Deploy from GitHub repo**
2. اختر المستودع `Video_Downlouder` ← اضغط **Deploy**
3. Railway سيكتشف `Dockerfile` و`railway.json` تلقائياً (لا تحتاج تغيير أي شيء)

### 3) متغيرات البيئة (تبويب Variables في خدمتك)
| المتغير | القيمة | مطلوب؟ |
|---|---|---|
| `BOT_TOKEN` | التوكن من [@BotFather](https://t.me/BotFather) | ✅ إجباري |
| `OWNER_ID` | `5231453921` (مُعدّ مسبقاً — المالك 👑) | ✅ جاهز |
| `ADMIN_IDS` | معرفات مشرفين إضافيين مفصولة بفواصل | اختياري |
| `DASHBOARD_PASSWORD` | كلمة مرور لوحة التحكم | ✅ **إجباري للنشر** وإلا أي حد يتحكم في البوت |
| `DATABASE_PATH` | `/app/data/bot.db` | ✅ (للـ Volume) |
| `SEED_DEMO_DATA` | `false` | افتراضي |
| `LOG_LEVEL` | `INFO` | افتراضي |

### 4) Volume للحفاظ على البيانات (مهم!)
Railway يمسح الملفات مع كل نشر — لحفظ المستخدمين والإحصائيات:
1. خدمتك ← **Settings** ← **Volumes** ← **New Volume**
2. **Mount Path**: `/app/data`
3. احفظ — بعدها `DATABASE_PATH=/app/data/bot.db` (مضبوط في الجدول أعلاه) سيعيش بين النشرات والنشر من جديد

### 5) دومين اللوحة
خدمتك ← **Settings** ← **Networking** ← **Generate Domain** ← يفتح لوحة التحكم على `https://xxxx.up.railway.app`

> ⚠️ **خدمة واحدة فقط** تشغّل البوت + اللوحة معاً (`scripts/start-all.sh` عبر `railway.json`).
> لا ترفع عدد النسخ (Replicas) عن **1** — البوت يستخدم long polling ونسختان = رد مزدوج.

### 6) 🚀 رفع بلا حدود (حتى 2GB للملف) — خادم Bot API محلي
تيليجرام يحدّ رفع البوت من الخادم العام بـ 50MB. **الحل الرسمي** هو خادم Bot API على نفس Railway:

1. **New Service** ← **Docker Image** ← ضع: `aiogram/telegram-bot-api:latest` ← **Deploy**
2. متغيرات تلك الخدمة:
   | المتغير | القيمة |
   |---|---|
   | `API_ID` و `API_HASH` | من [my.telegram.org](https://my.telegram.org) ← API development tools ← Create application (مجاني، دقيقة واحدة) |
   | `TELEGRAM_HTTP_PORT` | `8081` |
   | `TELEGRAM_LOCAL` | `true` |
   | `TELEGRAM_VERBOSITY` | `2` |
3. ارجع للخدمة الرئيسية ← Variables ← أضف:
   ```
   TELEGRAM_LOCAL_API=http://<اسم-خدمة-api>.railway.internal:8081
   ```
   *(اسم الخدمة من Settings ← أو Networking — استخدم الرابط الداخلي `.railway.internal`)*
4. أعد النشر — البوت سيكتشف الوضع المحلي تلقائياً ويرفع حتى **2000 م.بايت** لكل ملف ✅

> بدونه: الملفات حتى 50 م.بايت فقط (حد تيليجرام العام) — كل شيء آخر (بلا حدود للعدد/اليومية) يعمل كما هو.

---

## 🤖 «يوتيوب يطلب تسجيل الدخول / Sign in to confirm you're not a bot»

**السبب:** Railway (وداتا سنترز السحابة عموماً) IPs بيحظرها يوتيوب بـ bot-check — حتى من غير ما تحتاج تسجيل دخول حقيقي.
كان هذا الخطأ يظهر قديماً برسالة مضللة («المنصة تطلب تسجيل الدخول») رغم إن المشكلة من يوتيوب نفسه أثناء البحث عن أغنية سبوتيفاي/أنجامي — دلوقتي البوت:
1. **يجرب عملاء يوتيوب بدائل تلقائياً**: `android/ios ← tv ← web_safari ← الافتراضي` — في أغلب الحالات ينجح التحميل بدون أي تدخل منك
2. لو لسه محظور، **الرسالة بقت واضحة** وبتدل على الحل (كوكيز)

### ✅ الحل النهائي خلال دقيقة: كوكيز حسابك (دقيقة — مرة واحدة)
1. على الكمبيوتر، ثبّت إضافة Chrome المجانية: **Get cookies.txt LOCALLY**
2. افتح [youtube.com](https://www.youtube.com) وأنت مسجل دخول بحسابك ← اضغط الإضافة ← **Export** ← هيحمّل ملف `cookies.txt` *(محتواه سري — لا تشاركه مع أحد)*
3. حوّل الملف لـ base64 سطر واحد:
   - **Linux/macOS:** `base64 -w0 cookies.txt`
   - **Windows (PowerShell):** `[Convert]::ToBase64String([IO.File]::ReadAllBytes("cookies.txt"))`
4. على Railway ← خدمتك ← تبويب **Variables** ← أضف:
   ```
   YTDLP_COOKIES_TEXT=base64:<الناتج من الخطوة 3>
   ```
   *(أو الصق محتوى cookies.txt الخام مباشرة — Railway يدعم الأسطر الجديدة)*
5. اضغط **Deploy** ← أي تحميل (سبوتيفاي / أنجامي / يوتيوب) هينجح من ساعتها ✅

> ⚠️ الكوكيز = جلسة حسابك — احتفظ بيها سرية، وممكن متغيرات Railway تبقى Private تلقائياً.
> صلاحيتها تمتد لشهور، وبتتجدد بإعادة التصدير لو غيّرت باسورد حسابك.
> بديل بدون كوكيز: `YTDLP_PROXY=socks5://…` (بروكسي من منطقة غير محظورة).
> نفس الحل ينطبق لو نفس الحظر طال تيك توك أو إنستجرام.
>
> 💡 **البوت يصلح ملف الكوكيز تلقائياً** (يرويسة ناقصة، خطأ إملائي مثل «Notscape»، base64 بدون بادئة، علامات اقتباس زائدة، لصق بأحرف `\n` حرفية…)
> وبعد إعادة النشر ستجد في **Deploy Logs** السطر: `🍪 كوكيز يوتيوب: 8 سجل صالح (youtube.com)` —
> لو لم تجده، فالقيمة لم تُقرأ أو الملف غير مكتمل.
>
> 🔍 **أي خطأ غير معروف بيظهر في اللوجات كاملاً** تحت السطر `❌ yt-dlp raw error:` —
> افتح Deploy Logs وابحث عنه عند أي فشل مفاجئ لتشخيص السبب الحقيقي (429 / محتوى غير متاح / فيديو خاص…).

## 💻 التشغيل محلياً

### المتطلبات
- **Python 3.11+**
- **ffmpeg** (لتحويل MP3): `sudo apt install ffmpeg` أو `brew install ffmpeg`

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # ثم ضع BOT_TOKEN

python -m bot                                      # البوت
uvicorn dashboard.app:app --host 0.0.0.0 --port 8080   # اللوحة على :8080
```

### Docker محلياً (البوت + اللوحة معاً)
```bash
cp .env.example .env   # املأ القيم
docker compose up -d --build
```

---

## ⚙️ متغيرات البيئة الكاملة

| المتغير | الافتراضي | الوصف |
|---|---|---|
| `BOT_TOKEN` | — | **مطلوب** توكن البوت من @BotFather |
| `OWNER_ID` | `5231453921` | 👑 المالك — دائماً صلاحية كاملة (لا يُحظر ولا تُسحب صلاحياته) |
| `ADMIN_IDS` | *(فاضي)* | مشرفون إضافيون مفصولون بفواصل — المالك مشرف تلقائياً |
| `REQUEST_COOLDOWN` | `0` | الفاصل بين الطلبات (ثوانٍ) — 0 = بلا فاصل |
| `DAILY_DOWNLOAD_LIMIT` | `0` | الحد اليومي لكل مستخدم — **0 = بلا حدود ∞** |
| `MAX_FILE_SIZE_MB` | `0` | 0 = تلقائي: **2000** مع الخادم المحلي / **49** بدونه |
| `DATABASE_PATH` | `./data/bot.db` | مسار قاعدة SQLite المشتركة |
| `DOWNLOAD_DIR` | `./downloads` | مجلد مؤقت (يُنظف تلقائياً) |
| `TELEGRAM_LOCAL_API` | *(فاضي)* | رابط خادم Bot API المحلي (`http://host:8081`) — يفعّل حتى 2GB/ملف |
| `YTDLP_PROXY` | *(فاضي)* | وكيل لو المنصة محجوبة (`socks5://…`) |
| `YTDLP_COOKIES_FILE` | *(فاضي)* | مسار ملف كوكيز (Netscape) للمحتوى المحظور |
| `YTDLP_COOKIES_TEXT` | *(فاضي)* | محتوى الكوكيز نفسه (أو `base64:…`) — **الحل النهائي لحظر يوتيوب على Railway** |
| `DASHBOARD_PASSWORD` | *(فاضي=مفتوحة)* | كلمة مرور اللوحة — **عيّنها على Railway حتماً** |
| `SEED_DEMO_DATA` | `false` | بذر بيانات تجريبية لو كانت اللوحة فاضية (معاينة) |
| `LOG_LEVEL` | `INFO` | مستوى اللوجات |

---

## ⌨️ أوامر البوت

### للجميع
| الأمر | الوصف |
|---|---|
| `/start` | الرسالة الترحيبية + أزرار القائمة |
| `/help` | شرح الاستخدام والمنصات المدعومة |
| `/about` | نبذة عن البوت |

### 🛡 للمشرفين (المالك + ADMIN_IDS + مشرفون مضافون)
| الأمر | الوصف |
|---|---|
| `/stats` | إحصائيات فورية (مستخدمون، تحميلات، معدل النجاح، الحجم المرسل…) |
| `/admins` | قائمة المشرفين الحاليين ومصدرهم |
| `/ban <id>` | حظر مستخدم (لا يمكن حظر المالك) |
| `/unban <id>` | إلغاء حظر مستخدم |
| `/broadcast <نص>` | إذاعة لكل المستخدمين |

### 👑 للمالك فقط (`5231453921`)
| الأمر | الوصف |
|---|---|
| `/addadmin <id>` | تعيين مشرف جديد من داخل تيليجرام |
| `/deladmin <id>` | إزالة مشرف (لا يمكن إزالة المالك أو مشرف من `.env`) |

---

## 🧠 كيف يعمل؟

```
المستخدم يلصق رابطاً
        │
        ▼
 اكتشاف المنصة (Regex)
        │
        ├─ يوتيوب/تيك توك/إنستجرام/فيسبوك/إكس/ساوند كلاود
        │      └─► yt-dlp ← العنوان + المدة + الغلاف + المشاهدات
        ├─ سبوتيفاي  → قراءة صفحة التضمين (JSON-LD)
        └─ أنجامي    → قراءة وسوم Open Graph
                │
                ▼
   📱 معاينة حية + أزرار: MP4 (360p · 720p · 1080p · 🚀 بلا حدود) | MP3 (128k · 192k · 320k)
                │
                ▼
   التحميل في خيط منفصل (asyncio.to_thread)
   • MP3: bestaudio ← ffmpeg ← بالجودة المختارة
   • MP4: أفضل ملف MP4 جاهز بالطول المطلوب (تيك توك دائماً بدون علامة مائية)
   • «🚀 بلا حدود»: أفضل جودة على الإطلاق بدون أي سقف
                │
                ▼
   إرسال الملف (حتى 2GB مع الخادم المحلي / 50MB بدونه)
   + تسجيل العملية في SQLite (تظهر فوراً بلوحة التحكم)
```

التنسيق مع لوحة التحكم عبر **جدول `broadcasts`**: اللوحة تكتب إذاعة معلّقة ← عامل الإذاعة داخل البوت يلتقطها ويرسلها تدريجياً (~20 رسالة/ثانية) مع تحديث عدادات التسليم لحظياً في اللوحة.

---

## 📁 بنية المشروع

```
Video_Downlouder/
├── railway.json             # إعدادات Railway (Dockerfile + restart تلقائي)
├── Dockerfile               # python:3.11-slim + ffmpeg + bash
├── .dockerignore
├── docker-compose.yml       # محلياً: bot + dashboard يتشاركان ./data
├── requirements.txt
├── scripts/
│   ├── start-all.sh         # Railway: البوت + اللوحة معاً (يوقف الكل لو أي واحد كراش)
│   ├── start-dashboard.sh   # اللوحة فقط على $PORT
│   └── seed_demo.py         # بذر بيانات عرض للمعاينة فقط
├── bot/
│   ├── __main__.py          # نقطة التشغيل + بناء البوت (محلي/عام)
│   ├── config.py            # كل الإعدادات + المالك 👑 + حدود تلقائية
│   ├── permissions.py       # RBAC: مالك ← مشرف .env/DB ← الجميع
│   ├── database.py          # SQLite المشتركة (users/downloads/broadcasts/admins)
│   ├── handlers/            # start · media · admin
│   └── services/            # downloader · spotify · anghami · broadcaster
└── dashboard/               # لوحة FastAPI + صفحة RTL (HTML/CSS/JS خالص)
```

---

## ❓ استكشاف الأخطاء على Railway

| المشكلة | الحل |
|---|---|
| **«Application failed to respond»** على دومين Railway | الحاوية تموت عند الإقلاع. افتح **Deploy Logs** وتأكد بالترتيب: (1) `BOT_TOKEN` صحيح ومن @BotFather، (2) لا توجد نسخة أخرى من البوت تعمل بنفس التوكن (خطأ `Conflict`) — أوقفها من الجهاز/الخدمة الأخرى، (3) Target port في إعدادات الدومين = `8080` بالظبط وطابق `PORT` في Variables، (4) قاعدة `DATABASE_PATH` تشير داخل `/app/data` |
| البوت لا يرد لكن اللوحة تفتح | نسخة أخرى من البوت تعمل بنفس التوكن (Conflict) أو خطأ عابر في الشبكة — البوت يعيد المحاولة تلقائياً كل 15–20 ثانية، فقط أوقف النسخة الأخرى |
| `Conflict: terminated by other getUpdates request` | Telegram يسمح بنسخة polling واحدة لكل توكن — أوقف كل عملية `python -m bot` أخرى أو اصنع بوت جديد من @BotFather |
| اللوحة 502 | تأكد أن نموذج التشغيل هو `bash scripts/start-all.sh` (من railway.json) وليس `python -m bot` فقط |
| البناء فشل (`pip install` timeout) | أعد الـ Deploy — أو تأكد من فروع متغيرات البيئة |
| البوت لا يرد | **Deploy Logs** — غالباً `BOT_TOKEN` خطأ أو ناقص |
| `file is too big` عند إرسال ملفات 50–2000MB | فعّل خادم Bot API المحلي (القسم 6 في Railway أعلاه) |
| المستخدمون/الإحصائيات بتختفي بعد كل نشر | لم تركب Volume على `/app/data` — راجع الخطوة 4 |
| خطأ `429 Too Many Requests` | المنصة تحد من الطلبات من IP الخادم — فعّل `YTDLP_PROXY` أو انتظر |
| المحتوى محظور عمرياً | ضع `YTDLP_COOKIES_FILE` بكوكيز حسابك وصدّر ملف `cookies.txt` |
| رابط سبوتيفاي ألبوم/بلاي ليست | المدعوم: **الأغاني المفردة (tracks)** فقط |
| **«يوتيوب بيحظر سيرفر Railway» / Sign in to confirm you're not a bot** | البوت يجرب عملاء بدائل تلقائياً؛ الحل النهائي = `YTDLP_COOKIES_TEXT` — راجع قسم «يوتيوب يطلب تسجيل الدخول» أعلاه |
| إشعار `Flood control exceeded` عند الإذاعة | طبيعي — العامل يحترم حدود تيليجرام تلقائياً (retry_after) |

---

## ⚖️ إخلاء مسؤولية

البوت أداة للتحميل **للاستخدام الشخصي فقط**. يُرجى احترام حقوق الملكية الفكرية
وشروط استخدام كل منصة، وعدم إعادة نشر المحتوى دون إذن صاحبه.
المطورون غير مسؤولين عن أي سوء استخدام.

---

<div align="center">

صُنع بـ ❤️ للمستخدم العربي — **المالك: `5231453921`** — لو عجبك المشروع اعمل ⭐

</div>
