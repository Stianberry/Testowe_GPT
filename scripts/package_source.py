"""Build a portable source ZIP from an explicit allowlist, never runtime data."""
import hashlib
import json
from pathlib import Path
import stat
import zipfile

ROOT = Path(__file__).resolve().parent.parent
FILES = ["README.md", "START_TUTAJ.md", "AGENTS.md", ".gitignore", ".env.example",
         "pyproject.toml", "uv.lock", "package.json", "package-lock.json"]
DIRECTORIES = ["studio", "scripts", "config", "docs", "tests", ".agents/skills/editorial-video", ".agents/skills/local-avatar"]
EXAMPLE_FILES = ["examples/quality-demo/index.html"]
EXCLUDED = {"__pycache__", ".pytest_cache", "node_modules", ".venv", ".tools", ".cache", ".git", "data", "dist"}


def build(output: Path | None = None) -> Path:
    output = output or ROOT / "dist/Testowe_GPT-local.zip"
    paths = [ROOT / p for p in FILES + EXAMPLE_FILES]
    for folder in DIRECTORIES:
        paths.extend(p for p in (ROOT / folder).rglob("*") if p.is_file() and not p.is_symlink()
                     and not set(p.relative_to(ROOT).parts) & EXCLUDED and p.suffix not in {".pyc", ".log"})
    paths = sorted(set(paths))
    if any(not p.is_file() or p.is_symlink() for p in paths):
        raise ValueError("Brakuje pliku źródłowego albo lista zawiera symlink")
    output.parent.mkdir(parents=True, exist_ok=True)
    hashes = {}
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in paths:
            relative = path.relative_to(ROOT).as_posix()
            if path.name == ".env" or set(path.relative_to(ROOT).parts) & EXCLUDED:
                raise ValueError("Plik spoza dozwolonego zakresu paczki")
            body = path.read_bytes()
            hashes[relative] = hashlib.sha256(body).hexdigest()
            archive.write(path, "Testowe_GPT/" + relative)
        archive.writestr("Testowe_GPT/PACKAGE_MANIFEST.json", json.dumps({"format": 1, "files": hashes}, indent=2))
    with zipfile.ZipFile(output) as archive:
        if archive.testzip():
            raise ValueError("Błąd CRC paczki")
        for info in archive.infolist():
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError("Paczka nie może zawierać symlinków")
            if Path(info.filename).is_absolute() or ".." in Path(info.filename).parts:
                raise ValueError("Nieprawidłowa ścieżka w ZIP")
        for name, expected in hashes.items():
            if hashlib.sha256(archive.read("Testowe_GPT/" + name)).hexdigest() != expected:
                raise ValueError("Błąd integralności źródeł")
    output.with_suffix(".zip.sha256").write_text(hashlib.sha256(output.read_bytes()).hexdigest() + "  " + output.name + "\n")
    print(json.dumps({"path": str(output), "bytes": output.stat().st_size, "source_files": len(hashes)}))
    return output


if __name__ == "__main__":
    build()
