"""Fetch immutable dependencies, verify HEAD, register curated agent skills."""
import json
import os
from pathlib import Path
import subprocess
import hashlib
import tarfile
import urllib.request
import platform

ROOT = Path(__file__).resolve().parent.parent


def git(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args], text=True, env=os.environ | {"GIT_LFS_SKIP_SMUDGE": "1"}).strip()


def link(name, target):
    destination = ROOT / ".agents/skills" / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink():
        if destination.resolve() != target.resolve():
            raise RuntimeError(f"Istniejący skill ma inną lokalizację: {name}")
    elif destination.exists():
        if destination != target:
            raise RuntimeError(f"Nie nadpisano istniejącego skilla: {name}")
    else:
        destination.symlink_to(os.path.relpath(target, destination.parent), target_is_directory=True)


def main():
    manifest = json.loads((ROOT / "config/tools.lock.json").read_text())
    for name, spec in manifest.items():
        target = ROOT / ".tools" / name
        if not target.exists():
            target.mkdir(parents=True)
            git(target, "init", "-q")
            git(target, "remote", "add", "origin", "https://github.com/" + spec["repo"] + ".git")
            git(target, "fetch", "-q", "--depth=1", "origin", spec["commit"])
            git(target, "checkout", "-q", "--detach", "FETCH_HEAD")
        head = git(target, "rev-parse", "HEAD")
        # A manifest commit can be an annotated tag object: compare its peeled commit.
        expected = git(target, "rev-parse", spec["commit"] + "^{commit}")
        if head != expected:
            raise RuntimeError(f"Wersja zależności {name} różni się od tools.lock.json; nie zmieniono istniejącego checkoutu")
        print(name, head[:12])
        if "binary" in spec:
            if (platform.system(), platform.machine()) != ("Linux", "x86_64"):
                print("HeyGen CLI: pominięto binarkę Linux; opcjonalnie zainstaluj oficjalne CLI dla swojej platformy")
                continue
            binary = ROOT / ".tools/bin/heygen"
            locked = spec["binary"]
            if binary.exists():
                if hashlib.sha256(binary.read_bytes()).hexdigest() != locked["binary_sha256"]:
                    raise RuntimeError("HeyGen CLI checksum differs from the pinned release")
            else:
                archive = ROOT / ".cache/heygen-cli.tar.gz"
                archive.parent.mkdir(exist_ok=True)
                with urllib.request.urlopen(locked["url"], timeout=60) as response:
                    archive.write_bytes(response.read())
                if hashlib.sha256(archive.read_bytes()).hexdigest() != locked["archive_sha256"]:
                    raise RuntimeError("HeyGen CLI archive checksum mismatch")
                with tarfile.open(archive) as package:
                    member = next(m for m in package.getmembers() if m.isfile() and Path(m.name).name == "heygen")
                    data = package.extractfile(member).read()
                if hashlib.sha256(data).hexdigest() != locked["binary_sha256"]:
                    raise RuntimeError("HeyGen CLI binary checksum mismatch")
                binary.parent.mkdir(exist_ok=True)
                binary.write_bytes(data)
                binary.chmod(0o755)
            subprocess.run([str(binary), "--version"], check=True, env=os.environ | {"HEYGEN_NO_ANALYTICS": "1"})
    hf = ROOT / ".tools/hyperframes/skills"
    for name in ["hyperframes", "hyperframes-core", "hyperframes-cli", "hyperframes-animation", "hyperframes-creative", "hyperframes-registry", "media-use"]:
        if (hf / name / "SKILL.md").exists():
            link(name, hf / name)
    for name in ["heygen-avatar", "heygen-video"]:
        link(name, ROOT / ".tools/heygen-skills" / name)
    for name in ["short-form-video", "caption-animation", "lower-thirds"]:
        link(name, ROOT / ".tools/short-form-skills/skills" / name)
    link("video-use", ROOT / ".tools/video-use")
    link("create-video", ROOT / ".tools/openmontage/.agents/skills/create-video")
    link("remotion-best-practices", ROOT / ".tools/remotion-skills/skills/remotion-best-practices")


if __name__ == "__main__":
    main()
