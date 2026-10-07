#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/video-studio-uv}"
export UV_LINK_MODE=copy
export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-/tmp/video-studio-npm}"
export HYPERFRAMES_NO_TELEMETRY=1
export HEYGEN_NO_ANALYTICS=1
export XDG_CACHE_HOME="$PWD/.cache"
mkdir -p .cache data
for tool in uv node npm ffmpeg ffprobe git; do
  command -v "$tool" >/dev/null || { echo "Brakuje narzędzia: $tool" >&2; exit 1; }
done
node -e 'if (Number(process.versions.node.split(".")[0]) < 22) { console.error("Potrzebny Node.js >=22"); process.exit(1); }'
uv sync --frozen
npm ci --no-audit --no-fund
.venv/bin/python scripts/bootstrap_tools.py
.venv/bin/python scripts/prepare_demo.py
studio_browser_path="$(.venv/bin/python -m studio.browser)"
if [[ -n "$studio_browser_path" && -x "$studio_browser_path" ]]; then
  export HYPERFRAMES_BROWSER_PATH="$studio_browser_path"
  .venv/bin/python -c 'import os; from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(executable_path=os.environ["HYPERFRAMES_BROWSER_PATH"], headless=True, args=["--no-sandbox"]); page=b.new_page(); page.set_content("<p>browser-ready</p>"); assert page.inner_text("p")=="browser-ready"; b.close(); p.stop()'
else
  echo "Brakuje Chromium; dodaj przeglądarkę przez manager pakietów środowiska lub STUDIO_BROWSER_PATH." >&2
  exit 1
fi
.venv/bin/studio status
.venv/bin/pytest -q
HYPERFRAMES_NO_TELEMETRY=1 node_modules/.bin/hyperframes check examples/quality-demo --json > data/demo-check.json
echo "Instalacja, testy i kontrola kompozycji zakończone. Uruchom scripts/start.sh."
