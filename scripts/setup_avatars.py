"""Optional model environments for WSL2/NVIDIA or SadTalker/macOS CPU."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parent.parent


def run(*command, **kwargs):
    subprocess.run([str(c) for c in command], check=True, **kwargs)


def checkout(name, spec):
    home = ROOT / ".tools" / name
    environment = os.environ | {"GIT_LFS_SKIP_SMUDGE": "1"}
    if not home.exists():
        home.mkdir(parents=True)
        run("git", "-C", home, "init", "-q")
        run("git", "-C", home, "remote", "add", "origin", "https://github.com/" + spec["repo"] + ".git")
        run("git", "-C", home, "fetch", "--depth=1", "origin", spec["commit"], env=environment)
        run("git", "-C", home, "checkout", "--detach", "FETCH_HEAD", env=environment)
    head = subprocess.check_output(["git", "-C", str(home), "rev-parse", "HEAD"], text=True).strip()
    if head != spec["commit"]:
        raise ValueError("Nie zmieniono istniejącego checkoutu: commit różni się od avatar-tools.lock.json")
    return home


def download(url, target, records):
    # HTTPS verification stays enabled. This manifest detects later cache changes;
    # the local hash is not represented as a publisher-provided checksum.
    name = str(target.relative_to(ROOT))
    if target.is_file():
        with target.open("rb") as existing:
            digest = hashlib.file_digest(existing, "sha256").hexdigest()
        if name not in records or records[name]["sha256"] != digest:
            raise ValueError(f"Istniejący plik bez zgodnego manifestu pobrania: {name}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    digest = hashlib.sha256()
    count = 0
    try:
        with urllib.request.urlopen(url, timeout=60) as response, temporary.open("wb") as output:
            expected = response.headers.get("Content-Length")
            while block := response.read(1024 * 1024):
                output.write(block); digest.update(block); count += len(block)
        if not count or (expected and count != int(expected)):
            raise ValueError("Niekompletne pobranie wag modelu")
        temporary.replace(target)
        records[name] = {"url": url, "sha256": digest.hexdigest(), "bytes": count}
    finally:
        temporary.unlink(missing_ok=True)


def sadtalker_models(home, size):
    cache = ROOT / ".cache/avatar-downloads.json"
    records = json.loads(cache.read_text()) if cache.exists() else {}
    release = "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/"
    models = [(release + f"SadTalker_V0.0.2_{size}.safetensors", home / "checkpoints" / f"SadTalker_V0.0.2_{size}.safetensors"),
              (release + "mapping_00229-model.pth.tar", home / "checkpoints/mapping_00229-model.pth.tar")]
    for filename in ["alignment_WFLW_4HG.pth", "detection_Resnet50_Final.pth"]:
        models.append(("https://github.com/xinntao/facexlib/releases/download/v0.1.0/" + filename, home / "gfpgan/weights" / filename))
    cache.parent.mkdir(exist_ok=True)
    for url, target in models:
        print("Wagi:", target.name, flush=True)
        download(url, target, records)
        cache.write_text(json.dumps(records, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", choices=["sadtalker", "infinitetalk"])
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    parser.add_argument("--download-models", action="store_true")
    parser.add_argument("--size", choices=[256, 512], type=int, default=256)
    args = parser.parse_args()
    os.environ.setdefault("UV_CACHE_DIR", str(ROOT / ".cache/uv"))
    os.environ.setdefault("UV_PYTHON_INSTALL_DIR", str(ROOT / ".tools/python"))
    os.environ.setdefault("PIP_CACHE_DIR", str(ROOT / ".cache/pip"))
    for name in ["uv", "git", "ffmpeg", "ffprobe"]:
        if not shutil.which(name):
            parser.error("Brakuje narzędzia: " + name)
    if platform.system() == "Windows":
        parser.error("Użyj WSL2 zamiast natywnego Windows")
    if args.backend == "infinitetalk" and (args.device != "cuda" or platform.system() != "Linux"):
        parser.error("InfiniteTalk wymaga Linux/WSL2 z NVIDIA CUDA; nie obsługuje GPU Apple")
    if args.device == "cuda":
        if not shutil.which("nvidia-smi"):
            parser.error("Brakuje NVIDIA w tym systemie. W WSL2 sprawdź sterownik Windows i nvidia-smi")
        run("nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader")
    if args.backend == "infinitetalk" and not shutil.which("nvcc"):
        parser.error("Flash Attention wymaga CUDA Toolkit/nvcc w WSL2; instrukcja w docs/local-avatars.md")
    spec = json.loads((ROOT / "config/avatar-tools.lock.json").read_text())[args.backend]
    home = checkout(args.backend, spec)
    environment = ROOT / ".tools/envs" / args.backend
    python = environment / "bin/python"
    if not python.exists():
        run("uv", "venv", "--python", spec["python"], "--seed", environment)
    pip = [str(python), "-m", "pip", "install"]
    if args.backend == "sadtalker":
        suffix = "" if platform.system() == "Darwin" else ("+cu121" if args.device == "cuda" else "+cpu")
        torch = ["torch==2.1.2" + suffix, "torchvision==0.16.2" + suffix, "torchaudio==2.1.2" + suffix]
        index = [] if platform.system() == "Darwin" else ["--index-url", "https://download.pytorch.org/whl/" + ("cu121" if args.device == "cuda" else "cpu")]
        run(*pip, *torch, *index)
        run(*pip, "setuptools<81", "wheel", "numpy==1.23.5", "cython")
        # BasicSR's isolated build otherwise downloads an unrelated latest Torch.
        run(*pip, "--no-build-isolation", "-r", ROOT / "config/sadtalker-requirements.txt")
        if args.download_models:
            sadtalker_models(home, args.size)
    else:
        constraint = ROOT / "config/infinitetalk-constraints.txt"
        run(*pip, "torch==2.4.1+cu121", "torchvision==0.19.1+cu121", "torchaudio==2.4.1+cu121", "xformers==0.0.28", "--index-url", "https://download.pytorch.org/whl/cu121")
        run(*pip, "setuptools<81", "wheel", "ninja", "packaging", "psutil")
        # Build against the selected Torch/CUDA, preserving upstream package sources.
        run(*pip, "flash-attn==2.7.4.post1", "--no-build-isolation", env=os.environ | {"MAX_JOBS": "2"})
        run(*pip, "-r", home / "requirements.txt", "-c", constraint, "misaki[en]")
        if args.download_models:
            downloader = "from huggingface_hub import snapshot_download; import sys; snapshot_download(repo_id=sys.argv[1], local_dir=sys.argv[2])"
            for repo, destination in [("Wan-AI/Wan2.1-I2V-14B-480P", "Wan2.1-I2V-14B-480P"),
                                      ("TencentGameMate/chinese-wav2vec2-base", "chinese-wav2vec2-base"),
                                      ("MeiGen-AI/InfiniteTalk", "InfiniteTalk")]:
                run(python, "-c", downloader, repo, home / "weights" / destination)
            run(python, "-c", "from huggingface_hub import hf_hub_download; import sys; hf_hub_download('TencentGameMate/chinese-wav2vec2-base', 'model.safetensors', revision='refs/pr/1', local_dir=sys.argv[1])",
                home / "weights/chinese-wav2vec2-base")
    run(python, "-m", "pip", "check")
    (environment / "requirements.resolved.txt").write_text(subprocess.check_output([str(python), "-m", "pip", "freeze"], text=True))
    run(python, "-c", "import torch; print('PyTorch:', torch.__version__, 'CUDA:', torch.cuda.is_available()); " + ("assert torch.cuda.is_available(), 'CUDA niedostępne'" if args.device == "cuda" else ""))
    run(python, home / spec["entrypoint"], "--help", cwd=home)
    print("Środowisko modelu sprawdzone. Uruchom .venv/bin/studio avatar-doctor --backend", args.backend)


if __name__ == "__main__":
    main()
