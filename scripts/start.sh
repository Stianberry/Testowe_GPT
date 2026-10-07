#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export HYPERFRAMES_NO_TELEMETRY=1
export HEYGEN_NO_ANALYTICS=1
export XDG_CACHE_HOME="$PWD/.cache"
export HYPERFRAMES_BROWSER_PATH="$(.venv/bin/python -m studio.browser)"
exec .venv/bin/uvicorn studio.app:app --host 127.0.0.1 --port "${STUDIO_PORT:-8080}"
