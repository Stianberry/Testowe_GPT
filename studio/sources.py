"""Research returns candidates; acquisition never fabricates source metadata."""
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
from urllib.parse import urlparse

from defusedxml.ElementTree import fromstring
import httpx
from playwright.sync_api import sync_playwright

from .models import now
from .store import artifact, file_hash


def public_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Potrzebny publiczny URL HTTP(S), bez danych uwierzytelniających")
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Adres lokalny jest niedozwolony")
    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        # Cloud egress resolves destinations in the managed proxy. Local DNS is
        # unavailable there; the proxy enforces its destination policy.
        if os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy"):
            return url
        try:
            addresses = [ipaddress.ip_address(row[4][0]) for row in socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)]
        except OSError as error:
            raise ValueError("Nie można rozwiązać adresu źródła; sprawdź połączenie lub proxy") from error
    if not addresses or any(not addr.is_global for addr in addresses):
        raise ValueError("Adres musi prowadzić do publicznej strony")
    return url


def browser_proxy() -> dict | None:
    value = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if not value:
        return None
    parsed = urlparse(value)
    config = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port or 80}", "bypass": "localhost,127.0.0.1"}
    if parsed.username:
        config["username"] = parsed.username
    if parsed.password:
        config["password"] = parsed.password
    return config


def fetch(url: str) -> httpx.Response:
    for _ in range(6):
        public_url(url)
        response = httpx.get(url, timeout=30, follow_redirects=False, headers={"User-Agent": "EvidenceVideoStudio/0.1"})
        if response.is_redirect:
            url = str(response.url.join(response.headers["location"]))
            continue
        response.raise_for_status()
        return response
    raise ValueError("Zbyt wiele przekierowań")


def research(query: str, *, days: int = 7) -> dict:
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        raise ValueError("Dodaj TAVILY_API_KEY w ustawieniach środowiska albo użyj RSS i importu URL")
    response = httpx.post("https://api.tavily.com/search", headers={"Authorization": f"Bearer {key}"}, json={
        "query": query, "topic": "news", "days": days, "max_results": 10,
        "search_depth": "advanced", "include_raw_content": True,
    }, timeout=60)
    response.raise_for_status()
    return {"query": query, "searched_at": now().isoformat(), "candidates": response.json().get("results", []),
            "status": "Candidates require source/date/independence verification; search snippets are not evidence."}


def rss(url: str) -> list[dict]:
    root = fromstring(fetch(url).content)
    items = root.findall(".//item")
    atom = "{http://www.w3.org/2005/Atom}"
    if items:
        return [{"title": i.findtext("title"), "url": i.findtext("link"), "published_at": i.findtext("pubDate"), "feed": url} for i in items]
    return [{"title": i.findtext(atom + "title"), "url": (i.find(atom + "link").get("href") if i.find(atom + "link") is not None else None),
             "published_at": i.findtext(atom + "published") or i.findtext(atom + "updated"), "feed": url} for i in root.findall(atom + "entry")]


def capture(project_id: str, source_id: str, url: str, *, selector: str | None = None) -> dict:
    # The screenshot is captured from the real page. A selected crop never replaces context.
    public_url(url)
    name = hashlib.sha256(source_id.encode()).hexdigest()[:16]
    folder = artifact(project_id, "sources/" + name)
    folder.mkdir(parents=True, exist_ok=True)
    from .browser import executable
    browser_path = executable()
    if not browser_path:
        raise ValueError("Brakuje Chromium; zainstaluj przeglądarkę Playwright lub ustaw STUDIO_BROWSER_PATH")
    with sync_playwright() as pw, httpx.Client(timeout=30, follow_redirects=False) as client:
        browser = pw.chromium.launch(executable_path=browser_path, headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        failed_domains = set()
        def route_resource(route):
            if route.request.url.startswith(("data:", "blob:", "about:")):
                route.continue_()
                return
            try:
                public_url(route.request.url)
                if route.request.method not in {"GET", "HEAD"}:
                    route.abort()
                    return
                # Route original URLs through the managed HTTPS proxy with httpx's
                # verified CA trust. The browser renders the real document at its
                # real origin; no certificate validation is disabled.
                response = client.request(route.request.method, route.request.url, headers=route.request.headers)
                headers = {k: v for k, v in response.headers.items() if k.lower() not in {"content-encoding", "content-length", "transfer-encoding"}}
                route.fulfill(status=response.status_code, headers=headers, body=response.content)
                if response.status_code >= 400:
                    failed_domains.add(urlparse(route.request.url).hostname)
            except (ValueError, OSError, httpx.HTTPError):
                failed_domains.add(urlparse(route.request.url).hostname)
                route.abort()
        page.route("**/*", route_resource)
        response = page.goto(url, wait_until="domcontentloaded", timeout=45000)
        if response is None or response.status >= 400:
            raise ValueError("Strona nie zwróciła poprawnego dokumentu; nie zapisano jej jako dowodu")
        page.evaluate("document.fonts.ready")
        title = page.title()
        text = page.locator("body").inner_text()
        if len(text.strip()) < 80:
            raise ValueError("Za mało treści; sprawdź blokadę, logowanie lub paywall")
        page.screenshot(path=str(folder / "context.png"), full_page=True)
        if selector:
            page.locator(selector).first.screenshot(path=str(folder / "crop.png"))
        (folder / "page.txt").write_text(text, encoding="utf-8")
        metadata = {"url": url, "final_url": page.url, "title": title, "captured_at": now().isoformat(),
                    "text_path": f"sources/{name}/page.txt", "screenshot_path": f"sources/{name}/context.png",
                    "crop_path": f"sources/{name}/crop.png" if selector else None,
                    "failed_resource_domains": sorted(d for d in failed_domains if d),
                    "network_transport": "TLS-verified managed HTTP proxy; original browser document and resource URLs",
                    "sha256": file_hash(folder / "context.png"), "status": "needs human context and date verification"}
        browser.close()
    (folder / "capture.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def download_video(project_id: str, url: str) -> dict:
    from yt_dlp import YoutubeDL
    public_url(url)
    folder = artifact(project_id, "downloads")
    folder.mkdir(exist_ok=True)
    options = {"outtmpl": str(folder / "%(id)s.%(ext)s"), "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
               "merge_output_format": "mp4", "writesubtitles": True, "writeautomaticsub": True,
               "subtitleslangs": ["pl", "en"], "noplaylist": True, "quiet": True,
               "match_filter": lambda info, **kw: "Wideo przekracza limit 30 minut" if (info.get("duration") or 0) > 1800 else None}
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
    if not info or "id" not in info:
        raise ValueError("Nie pobrano materiału")
    files = sorted(folder.glob(info["id"] + ".*"))
    if not any(p.suffix in {".mp4", ".webm", ".mkv"} for p in files):
        raise ValueError("Brakuje pliku wideo")
    metadata = {"url": url, "title": info.get("title"), "uploader": info.get("uploader"), "upload_date": info.get("upload_date"),
                "duration": info.get("duration"), "license": info.get("license"),
                "files": [str(p.relative_to(artifact(project_id, "."))) for p in files], "captured_at": now().isoformat()}
    (folder / (info["id"] + ".json")).write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    return metadata


def clip(project_id: str, input_file: str, output_file: str, start: float, end: float) -> dict:
    if not 0 <= start < end:
        raise ValueError("Nieprawidłowy zakres fragmentu")
    source, target = artifact(project_id, input_file), artifact(project_id, output_file)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Re-encode for accurate time cuts, instead of seeking only to preceding keyframes.
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-i", str(source), "-t", str(end-start),
                    "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-movflags", "+faststart", str(target)], check=True)
    return {"path": output_file, "sha256": file_hash(target), "in_seconds": start, "out_seconds": end}


def stock(query: str) -> dict:
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        raise ValueError("Dodaj opcjonalny PEXELS_API_KEY do wyszukiwania B-roll")
    response = httpx.get("https://api.pexels.com/videos/search", headers={"Authorization": key},
                         params={"query": query, "orientation": "portrait", "per_page": 5}, timeout=30)
    response.raise_for_status()
    return {"query": query, "candidates": response.json().get("videos", []),
            "usage_terms": "https://www.pexels.com/license/", "status": "illustrations; inspect each asset and usage terms"}
