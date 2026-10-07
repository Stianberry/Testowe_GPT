import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3

from .models import Project, now


ROOT = Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    return Path(os.environ.get("STUDIO_DATA_DIR", str(ROOT / "data"))).resolve()


def content_hash(project: Project) -> str:
    return hashlib.sha256(project.model_dump_json().encode()).hexdigest()


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def story_hash(project: Project) -> str:
    body = project.model_dump(mode="json", include={"title", "angle", "claims", "assets", "scenes"})
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def project_dir(project_id: str) -> Path:
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", project_id):
        raise ValueError("Nieprawidłowy identyfikator projektu")
    path = data_dir() / "projects" / project_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def artifact(project_id: str, relative: str) -> Path:
    base = project_dir(project_id)
    path = (base / relative).resolve()
    if not path.is_relative_to(base):
        raise ValueError("Plik musi znajdować się w katalogu projektu")
    return path


class Store:
    def __init__(self):
        data_dir().mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(data_dir() / "studio.sqlite3")
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, revision INTEGER NOT NULL, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS approvals(project_id TEXT PRIMARY KEY, digest TEXT NOT NULL, reviewer TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, project_id TEXT, kind TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL);
        """)

    def close(self):
        self.db.close()

    def save(self, project: Project, *, expected_revision: int | None = None) -> int:
        project_dir(project.id)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            old = self.db.execute("SELECT revision, body FROM projects WHERE id=?", (project.id,)).fetchone()
            rev = old["revision"] if old else 0
            if expected_revision is not None and rev != expected_revision:
                raise ValueError("Projekt zmienił się; wczytaj aktualną wersję przed zapisem")
            body = project.model_dump_json()
            if old and old["body"] == body:
                return rev
            self.db.execute("INSERT OR REPLACE INTO projects VALUES(?,?,?)", (project.id, rev + 1, body))
            self.db.execute("DELETE FROM approvals WHERE project_id=?", (project.id,))
            self.event(project.id, "revision", {"revision": rev + 1}, commit=False)
        return rev + 1

    def load(self, project_id: str) -> tuple[Project, int]:
        row = self.db.execute("SELECT body, revision FROM projects WHERE id=?", (project_id,)).fetchone()
        if not row:
            raise KeyError(project_id)
        return Project.model_validate_json(row["body"]), row["revision"]

    def list(self) -> list[dict]:
        result = []
        for row in self.db.execute("SELECT * FROM projects ORDER BY rowid DESC"):
            project = Project.model_validate_json(row["body"])
            result.append({"id": project.id, "title": project.title, "revision": row["revision"], "demo": project.demo})
        return result

    def approve(self, project_id: str, reviewer: str):
        from .quality import evaluate
        if not reviewer.strip():
            raise ValueError("Podaj osobę akceptującą")
        project, _ = self.load(project_id)
        check = evaluate(project)
        if not check["ok"]:
            raise ValueError("Najpierw usuń problemy jakości i aktualności źródeł")
        if not project.rendered_path or file_hash(artifact(project.id, project.rendered_path)) != project.render_sha256:
            raise ValueError("Plik wideo zmienił się lub nie istnieje")
        self.verify_assets(project)
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO approvals VALUES(?,?,?,?)", (project_id, content_hash(project), reviewer, now().isoformat()))
            self.event(project_id, "approval", {"reviewer": reviewer}, commit=False)

    def require_approval(self, project: Project):
        from .quality import evaluate
        row = self.db.execute("SELECT digest FROM approvals WHERE project_id=?", (project.id,)).fetchone()
        if not row or row["digest"] != content_hash(project) or not evaluate(project)["ok"]:
            raise ValueError("Potrzebna aktualna akceptacja filmu oraz ponowne sprawdzenie źródeł")
        if file_hash(artifact(project.id, project.rendered_path)) != project.render_sha256:
            raise ValueError("Plik filmu zmienił się od akceptacji")
        self.verify_assets(project)

    def verify_assets(self, project: Project):
        for asset in project.assets:
            path = artifact(project.id, asset.path)
            if not path.is_file() or not asset.sha256 or file_hash(path) != asset.sha256:
                raise ValueError(f"Materiał {asset.id} nie istnieje lub zmienił się; ponownie sprawdź jego pochodzenie i montaż")

    def event(self, project_id: str | None, kind: str, body: dict, *, commit=True):
        self.db.execute("INSERT INTO events(project_id,kind,body,created_at) VALUES(?,?,?,?)", (project_id, kind, json.dumps(body, ensure_ascii=False), now().isoformat()))
        if commit:
            self.db.commit()
