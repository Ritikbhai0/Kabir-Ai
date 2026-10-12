#!/usr/bin/env bash
set -euo pipefail
python -m backend.storage
exec python -m uvicorn backend.app:app --host 0.0.0.0 --port "${PORT:-7860}" --workers 1 --no-proxy-headers
