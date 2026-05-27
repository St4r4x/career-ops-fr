#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-dashboard}"

if [ "$MODE" = "dashboard" ]; then
    cd /app/dashboard
    exec uvicorn app:app --host 0.0.0.0 --port 8000
elif [ "$MODE" = "pipeline" ]; then
    cd /app
    exec python scripts/daily_report.py "$@"
else
    echo "Unknown mode: $MODE. Use 'dashboard' or 'pipeline'."
    exit 1
fi
