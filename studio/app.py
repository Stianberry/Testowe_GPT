from contextlib import contextmanager
import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

from .models import Project
from .production import brief
from .providers import capabilities
from .quality import evaluate
from .store import ROOT, Store
from .runtime import load_environment


load_environment()
app = FastAPI(title="Studio redakcyjne", version="0.1.0")


@contextmanager
def database():
    store = Store()
    try:
        yield store
    finally:
        store.close()


@app.exception_handler(KeyError)
async def not_found(request, error):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=404, content={"detail": "Nie znaleziono projektu"})


@app.exception_handler(ValueError)
async def bad_input(request, error):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=400, content={"detail": str(error)})


@app.get("/")
def home():
    return FileResponse(ROOT / "studio/static/index.html")


@app.get("/health")
def health():
    with database() as store:
        store.list()
    return {"ok": True, "storage": "sqlite", "publication_mode": "draft"}


@app.get("/api/capabilities")
def status():
    return capabilities()


@app.get("/api/projects")
def projects():
    with database() as store:
        return store.list()


@app.post("/api/projects", status_code=201)
def create(project: Project):
    with database() as store:
        if any(p["id"] == project.id for p in store.list()):
            raise HTTPException(409, "Projekt już istnieje")
        revision = store.save(project, expected_revision=0)
    return {"id": project.id, "revision": revision}


@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    with database() as store:
        project, revision = store.load(project_id)
    return {"project": project.model_dump(mode="json"), "revision": revision, "quality": evaluate(project)}


class Replacement(BaseModel):
    revision: int = Field(ge=1)
    project: Project


@app.put("/api/projects/{project_id}")
def replace_project(project_id: str, change: Replacement):
    if change.project.id != project_id:
        raise ValueError("Identyfikator projektu nie zgadza się z adresem")
    with database() as store:
        return {"revision": store.save(change.project, expected_revision=change.revision)}


@app.get("/api/projects/{project_id}/brief", response_class=PlainTextResponse)
def project_brief(project_id: str):
    with database() as store:
        project, _ = store.load(project_id)
    return brief(project)


class Approval(BaseModel):
    reviewer: str = Field(min_length=1)


@app.post("/api/projects/{project_id}/approve")
def approve(project_id: str, body: Approval):
    with database() as store:
        store.approve(project_id, body.reviewer)
    return {"approved": True, "next": "Można przekazać szkic do Postiz"}
