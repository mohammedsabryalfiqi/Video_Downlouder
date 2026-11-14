#!/usr/bin/env bash
# يشتغل البوت + لوحة التحكم في نفس الحاوية (مثالي لـ Railway — خدمة واحدة، Volume واحدة على /app/data)
set -euo pipefail

PORT="${PORT:-8080}"
echo "🚀 تشغيل البوت + لوحة التحكم — اللوحة على المنفذ ${PORT}"

python -m bot & BOT_PID=$!
uvicorn dashboard.app:app --host 0.0.0.0 --port "${PORT}" & DASH_PID=$!

trap 'echo "🛑 إيقاف…"; kill "${BOT_PID}" "${DASH_PID}" 2>/dev/null || true' TERM INT

# لو أي عملية خلصت (كراش) نوقف الباقي عشان Railway يعيد تشغيل الحاوية كلها
wait -n "${BOT_PID}" "${DASH_PID}"
EXIT_CODE=$?
echo "⚠️ عملية توقفت بكود ${EXIT_CODE} — إيقاف الخدمة لإعادة التشغيل"
kill "${BOT_PID}" "${DASH_PID}" 2>/dev/null || true
wait || true
exit "${EXIT_CODE}"
