import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import base64
import platform
from urllib.parse import quote

import httpx

from .models import now
from .store import Store, artifact, content_hash


def capabilities() -> dict:
    from .local_avatar import doctor, settings
    return {"research": {"configured": bool(os.environ.get("TAVILY_API_KEY")), "alternative": "RSS / source URLs"},
            "deepseek": {"configured": bool(os.environ.get("DEEPSEEK_API_KEY")), "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"), "role": "script_proposals", "tested_live": False},
            "local_avatar": {**doctor(probe_runtime=False), "preferred": True, "default_backend": settings().default_backend},
            "stock": {"configured": bool(os.environ.get("PEXELS_API_KEY"))},
            "heygen": {"configured": bool(os.environ.get("HEYGEN_API_KEY")), "cli_installed": bool(heygen_binary()), "tested_live": False},
            "postiz": {"configured": bool(os.environ.get("POSTIZ_API_KEY")), "tested_live": False},
            "openmontage": {"installed": (Path(__file__).resolve().parent.parent / ".tools/openmontage/tools").exists()},
            "hyperframes": {"installed": (Path(__file__).resolve().parent.parent / "node_modules/.bin/hyperframes").exists()}}


def heygen_binary() -> str | None:
    root = Path(__file__).resolve().parent.parent
    local = root / ".tools/bin/heygen"
    return str(local) if local.is_file() and (platform.system(), platform.machine()) == ("Linux", "x86_64") else shutil.which("heygen")


def create_photo_avatar(name: str, photo_url: str, *, group_id: str | None = None) -> dict:
    from .sources import public_url
    if photo_url.startswith(("https://", "http://")):
        public_url(photo_url)
        file_input = {"type": "url", "url": photo_url}
    else:
        from PIL import Image
        path = Path(photo_url).resolve()
        if path.stat().st_size > 10 * 1024 * 1024:
            raise ValueError("Zdjęcie przekracza 10 MB; przygotuj mniejszy JPEG/PNG")
        with Image.open(path) as image:
            if image.format not in {"JPEG", "PNG"} or min(image.size) < 512:
                raise ValueError("Potrzebny JPEG lub PNG, co najmniej 512×512")
            mime = "image/jpeg" if image.format == "JPEG" else "image/png"
        file_input = {"type": "base64", "media_type": mime, "data": base64.b64encode(path.read_bytes()).decode()}
    binary = heygen_binary()
    if not binary:
        raise ValueError("Brakuje oficjalnego HeyGen CLI; instrukcja i wymagania są w docs/integrations.md")
    if not os.environ.get("HEYGEN_API_KEY"):
        raise ValueError("Dodaj HEYGEN_API_KEY w ustawieniach środowiska")
    payload = {"type": "photo", "name": name, "file": file_input}
    if group_id:
        payload["avatar_group_id"] = group_id
    # Official CLI applies the v3 workflow; do not substitute deprecated raw API calls.
    result = subprocess.run([binary, "avatar", "create", "-d", "-"], input=json.dumps(payload), text=True, capture_output=True,
                            env=os.environ | {"HEYGEN_NO_ANALYTICS": "1", "HEYGEN_CONFIG_DIR": str(Path(__file__).resolve().parent.parent / ".cache/heygen")})
    if result.returncode:
        raise ValueError("HeyGen nie utworzył awatara; sprawdź konto, wymagania zdjęcia i dostęp sieciowy")
    return json.loads(result.stdout)


class Postiz:
    def __init__(self, client: httpx.Client | None = None):
        key = os.environ.get("POSTIZ_API_KEY")
        if not key:
            raise ValueError("Dodaj POSTIZ_API_KEY w ustawieniach środowiska")
        self.client = client or httpx.Client(base_url="https://api.postiz.com/public/v1/", headers={"Authorization": key}, timeout=120)

    def integrations(self):
        response = self.client.get("integrations")
        response.raise_for_status()
        return response.json()

    def analytics(self, integration_id: str, days: int = 7):
        response = self.client.get("analytics/" + quote(integration_id, safe=""), params={"date": days})
        response.raise_for_status()
        return response.json()

    def draft(self, store: Store, project_id: str, integration_id: str, caption: str, settings: dict) -> dict:
        project, revision = store.load(project_id)
        store.require_approval(project)
        if not settings.get("__type") or not integration_id.strip() or not caption.strip():
            raise ValueError("Podaj kanał, opis i ustawienia konkretnej platformy (__type)")
        fingerprint = hashlib.sha256(json.dumps([content_hash(project), integration_id, caption, settings], sort_keys=True).encode()).hexdigest()
        target = artifact(project_id, "exports/" + fingerprint + ".json")
        target.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive create prevents double submission by concurrent workers. An ambiguous
        # network failure remains 'submitting' and requires reconciliation with Postiz.
        try:
            with target.open("x", encoding="utf-8") as output:
                json.dump({"state": "submitting", "revision": revision, "started_at": now().isoformat()}, output)
        except FileExistsError:
            record = json.loads(target.read_text())
            if record.get("state") == "draft":
                return record
            raise ValueError("Wcześniejsze wysłanie wymaga sprawdzenia w Postiz; automatyczna próba mogłaby utworzyć duplikat")
        video = artifact(project_id, project.rendered_path)
        with video.open("rb") as stream:
            response = self.client.post("upload", files={"file": (video.name, stream, "video/mp4")})
        response.raise_for_status()
        media = response.json()
        if not media.get("id") or not media.get("path"):
            raise ValueError("Nieprawidłowa odpowiedź uploadu Postiz")
        # Recheck after the slow upload, before creation of the draft.
        current, _ = store.load(project_id)
        if content_hash(current) != content_hash(project):
            raise ValueError("Projekt zmienił się podczas uploadu")
        store.require_approval(current)
        payload = {"type": "draft", "date": now().isoformat(), "shortLink": False, "tags": [],
                   "posts": [{"integration": {"id": integration_id}, "value": [{"content": caption,
                              "image": [{"id": media["id"], "path": media["path"]}]}], "settings": settings}]}
        response = self.client.post("posts", json=payload)
        response.raise_for_status()
        record = {"state": "draft", "revision": revision, "result": response.json(), "created_at": now().isoformat()}
        target.write_text(json.dumps(record, ensure_ascii=False, indent=2))
        store.event(project_id, "postiz_draft", record)
        return record
