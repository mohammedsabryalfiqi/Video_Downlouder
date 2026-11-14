# ───────────────────────────────────────────────────────────
#  Video Downloader Bot
#  - مبنية على python:3.11-slim + ffmpeg (مطلوب لتحويل MP3)
#  - البوت:      python -m bot
#  - اللوحة:    uvicorn dashboard.app:app --host 0.0.0.0 --port 8080
# ───────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg bash \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY bot/ bot/
COPY dashboard/ dashboard/
COPY scripts/ scripts/
COPY README.md .

RUN mkdir -p data downloads && useradd --create-home botuser && chown -R botuser /app
USER botuser

EXPOSE 8080

# محلياً: البوت فقط. على Railway: railway.json يشغّل scripts/start-all.sh (بوت + لوحة)
CMD ["python", "-m", "bot"]
