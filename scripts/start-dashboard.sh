#!/usr/bin/env bash
# تشغيل لوحة التحكم فقط على المنفذ الذي تعطيه Railway ($PORT) أو 8080 افتراضياً
set -euo pipefail
exec uvicorn dashboard.app:app --host 0.0.0.0 --port "${PORT:-8080}"
