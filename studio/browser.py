import os
from pathlib import Path
import shutil


def executable() -> str | None:
    configured = os.environ.get("STUDIO_BROWSER_PATH")
    if configured:
        if not Path(configured).is_file():
            raise ValueError("STUDIO_BROWSER_PATH nie wskazuje istniejącej przeglądarki")
        return configured
    system = shutil.which("chromium") or shutil.which("chromium-browser")
    if system:
        return system
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        path = pw.chromium.executable_path
    return path if Path(path).is_file() else None


if __name__ == "__main__":
    path = executable()
    if not path:
        raise SystemExit("Brakuje Chromium: uruchom .venv/bin/python -m playwright install chromium")
    print(path)
