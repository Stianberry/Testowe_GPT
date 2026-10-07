import json
import shutil
import subprocess

from fastapi.testclient import TestClient
from PIL import Image
from playwright.sync_api import sync_playwright
import pytest

from studio.app import app
from studio.browser import executable
from studio.openmontage import execute
from studio.sources import public_url


def test_server_project_flow_and_conflict(store):
    client = TestClient(app)
    assert client.get("/health").json()["ok"]
    assert "Studio redakcyjne" in client.get("/").text
    response = client.post("/api/projects", json={"id": "api-test", "title": "Temat", "angle": "Pytanie redakcyjne"})
    assert response.status_code == 201
    data = client.get("/api/projects/api-test").json()
    assert not data["quality"]["ok"]
    assert client.post("/api/projects/api-test/approve", json={"reviewer": "Redaktor"}).status_code == 400
    data["project"]["angle"] = "Nowa oś narracji"
    assert client.put("/api/projects/api-test", json={"revision": 1, "project": data["project"]}).status_code == 200
    assert client.put("/api/projects/api-test", json={"revision": 1, "project": data["project"]}).status_code == 400


def test_browser_real_pixels_and_polish_typography(tmp_path):
    # Offline rendering fixture verifies browser plumbing; live capture is separately exercised.
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=executable(), args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        page.set_content('<html lang="pl"><body style="background:#152018;color:white"><h1>Źródło, rzetelność, montaż</h1><article>Pełny kontekst wypowiedzi</article></body></html>')
        assert page.locator("h1").inner_text() == "Źródło, rzetelność, montaż"
        target = tmp_path / "screenshot.png"
        page.screenshot(path=str(target))
        browser.close()
    image = Image.open(target)
    assert image.size == (1080, 1920)
    assert image.getextrema()[0][0] != image.getextrema()[0][1]


def test_upstream_openmontage_cuts_real_video(tmp_path):
    source, target = tmp_path / "source.mp4", tmp_path / "clip.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=180x320:rate=30", "-f", "lavfi", "-i", "sine=frequency=440", "-t", "3", "-c:v", "libx264", "-c:a", "aac", str(source)], check=True)
    result = execute("video_trimmer", {"operation": "cut", "input_path": str(source), "output_path": str(target), "start_seconds": 1, "end_seconds": 2, "codec": "libx264"})
    assert result["success"], result
    probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(target)], text=True))
    assert 0.9 <= float(probe["format"]["duration"]) <= 1.2
    assert {s["codec_type"] for s in probe["streams"]} == {"video", "audio"}


@pytest.mark.parametrize("url", ["file:///etc/passwd", "http://127.0.0.1/a", "http://169.254.169.254/", "https://localhost/", "https://user:pass@example.com/"])
def test_source_import_rejects_nonpublic_destinations(url):
    with pytest.raises(ValueError):
        public_url(url)
