import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import subprocess
import httpx

from . import deepseek, local_avatar, openmontage, production, sources
from .models import Project
from .providers import Postiz, capabilities, create_photo_avatar
from .quality import evaluate
from .store import Store, artifact, data_dir


def output(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def main():
    from .runtime import load_environment
    load_environment()
    parser = argparse.ArgumentParser(description="Studio wideo — research, materiały i kontrola redakcyjna")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("list")
    p = sub.add_parser("new"); p.add_argument("id"); p.add_argument("title"); p.add_argument("--angle", required=True)
    p = sub.add_parser("import"); p.add_argument("file", type=Path); p.add_argument("--revision", type=int)
    for cmd in ["export", "quality", "brief", "agent"]:
        p = sub.add_parser(cmd); p.add_argument("id")
    p = sub.add_parser("research"); p.add_argument("query"); p.add_argument("--days", type=int, default=7)
    p = sub.add_parser("rss"); p.add_argument("url")
    p = sub.add_parser("stock"); p.add_argument("query")
    p = sub.add_parser("capture"); p.add_argument("id"); p.add_argument("source_id"); p.add_argument("url"); p.add_argument("--selector")
    p = sub.add_parser("download"); p.add_argument("id"); p.add_argument("url")
    p = sub.add_parser("clip"); p.add_argument("id"); p.add_argument("input"); p.add_argument("output"); p.add_argument("--start", type=float, required=True); p.add_argument("--end", type=float, required=True)
    p = sub.add_parser("render"); p.add_argument("id"); p.add_argument("--quality", choices=["draft", "looks", "delivery"], default="looks")
    p = sub.add_parser("record-render"); p.add_argument("id"); p.add_argument("path")
    p = sub.add_parser("approve"); p.add_argument("id"); p.add_argument("--reviewer", required=True)
    p = sub.add_parser("om-tools")
    p = sub.add_parser("om-run"); p.add_argument("tool"); p.add_argument("inputs", type=Path)
    p = sub.add_parser("avatar-photo"); p.add_argument("name"); p.add_argument("url"); p.add_argument("--group-id")
    p = sub.add_parser("avatar-doctor"); p.add_argument("--backend", choices=["sadtalker", "infinitetalk"])
    p = sub.add_parser("avatar-local"); p.add_argument("id"); p.add_argument("photo", type=Path); p.add_argument("audio", type=Path); p.add_argument("--backend", choices=["sadtalker", "infinitetalk"])
    p = sub.add_parser("propose-script"); p.add_argument("id")
    sub.add_parser("postiz-channels")
    p = sub.add_parser("postiz-draft"); p.add_argument("id"); p.add_argument("integration_id"); p.add_argument("--caption", type=Path, required=True); p.add_argument("--settings", type=Path, required=True)
    p = sub.add_parser("analytics"); p.add_argument("integration_id"); p.add_argument("--days", type=int, default=7)
    p = sub.add_parser("discover"); p.add_argument("--config", type=Path, default=Path("config/research.json"))
    args = parser.parse_args()
    store = Store()
    try:
        match args.command:
            case "status": output(capabilities())
            case "list": output(store.list())
            case "new": output({"revision": store.save(Project(id=args.id, title=args.title, angle=args.angle), expected_revision=0)})
            case "import": output({"revision": store.save(Project.model_validate_json(args.file.read_text()), expected_revision=args.revision)})
            case "export": output(store.load(args.id)[0].model_dump(mode="json"))
            case "quality":
                result = evaluate(store.load(args.id)[0]); output(result)
                if not result["ok"]: sys.exit(2)
            case "brief": print(production.brief(store.load(args.id)[0]))
            case "agent": production.run_agent(args.id)
            case "research": output(sources.research(args.query, days=args.days))
            case "rss": output(sources.rss(args.url))
            case "stock": output(sources.stock(args.query))
            case "capture": output(sources.capture(args.id, args.source_id, args.url, selector=args.selector))
            case "download": output(sources.download_video(args.id, args.url))
            case "clip": output(sources.clip(args.id, args.input, args.output, args.start, args.end))
            case "render": output(production.render(args.id, quality=args.quality))
            case "record-render": output(production.record_render(store, args.id, args.path))
            case "approve": store.approve(args.id, args.reviewer); output({"approved": True})
            case "om-tools": output(openmontage.describe())
            case "om-run":
                result = openmontage.execute(args.tool, json.loads(args.inputs.read_text())); output(result)
                if not result["success"]: sys.exit(2)
            case "avatar-photo": output(create_photo_avatar(args.name, args.url, group_id=args.group_id))
            case "avatar-doctor":
                result = local_avatar.doctor(args.backend); output(result)
                if not result["configured"]: sys.exit(2)
            case "avatar-local": output(local_avatar.generate(store, args.id, args.photo, args.audio, backend=args.backend))
            case "propose-script": output(deepseek.propose(store, args.id))
            case "postiz-channels": output(Postiz().integrations())
            case "postiz-draft": output(Postiz().draft(store, args.id, args.integration_id, args.caption.read_text(), json.loads(args.settings.read_text())))
            case "analytics": output(Postiz().analytics(args.integration_id, args.days))
            case "discover":
                config = json.loads(args.config.read_text())
                records, errors = [], []
                for query in config.get("queries", []):
                    try: records.append(sources.research(query, days=config.get("days", 7)))
                    except (ValueError, OSError, httpx.HTTPError) as error: errors.append({"query": query, "error": str(error)})
                for url in config.get("feeds", []):
                    try: records.append({"feed": url, "candidates": sources.rss(url)})
                    except (ValueError, OSError, httpx.HTTPError) as error: errors.append({"feed": url, "error": str(error)})
                folder = data_dir() / "inbox"; folder.mkdir(exist_ok=True)
                target = folder / (datetime.now().strftime("%Y%m%dT%H%M%S") + ".json")
                target.write_text(json.dumps({"results": records, "errors": errors}, ensure_ascii=False, indent=2))
                output({"path": str(target), "groups": len(records), "errors": errors})
                if errors: sys.exit(2)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError, httpx.HTTPError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    finally:
        store.close()


if __name__ == "__main__":
    main()
