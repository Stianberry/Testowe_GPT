"""Local photo + audio inference in isolated upstream environments; no API fallback."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import uuid
from typing import Literal

from PIL import Image, ImageOps
from pydantic import BaseModel, ConfigDict, Field

from .models import Asset, now
from .store import ROOT, Store, artifact, data_dir, file_hash


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default_backend: Literal["sadtalker", "infinitetalk"] = "sadtalker"
    device: Literal["auto", "cpu", "cuda"] = "auto"
    max_audio_seconds: float = Field(default=15, gt=0, le=60)
    timeout_seconds: int = Field(default=3600, ge=60, le=14400)
    sadtalker_size: Literal[256, 512] = 256
    infinitetalk_size: Literal["infinitetalk-480", "infinitetalk-720"] = "infinitetalk-480"
    infinitetalk_steps: int = Field(default=40, ge=1, le=100)


def settings() -> Settings:
    path = Path(os.environ.get("STUDIO_AVATAR_CONFIG", ROOT / "config/avatars.json"))
    return Settings.model_validate_json(path.read_text())


def installation(backend: str) -> tuple[Path, Path, dict]:
    lock = json.loads((ROOT / "config/avatar-tools.lock.json").read_text())
    if backend not in lock:
        raise ValueError("Wybierz sadtalker lub infinitetalk; HeyGen pozostaje osobną opcją")
    prefix = backend.upper()
    home = Path(os.environ.get(prefix + "_HOME", ROOT / ".tools" / backend)).expanduser().resolve()
    python = Path(os.environ.get(prefix + "_PYTHON", ROOT / ".tools/envs" / backend / "bin/python")).expanduser().absolute()
    return home, python, lock[backend]


def required_models(backend: str, home: Path, cfg: Settings) -> list[Path]:
    if backend == "sadtalker":
        return [home / "checkpoints" / f"SadTalker_V0.0.2_{cfg.sadtalker_size}.safetensors",
                home / "checkpoints/mapping_00229-model.pth.tar",
                home / "gfpgan/weights/alignment_WFLW_4HG.pth",
                home / "gfpgan/weights/detection_Resnet50_Final.pth"]
    weights = home / "weights"
    base = weights / "Wan2.1-I2V-14B-480P"
    return [base / "config.json", base / "Wan2.1_VAE.pth",
            base / "models_t5_umt5-xxl-enc-bf16.pth",
            base / "models_clip_open-clip-xlm-roberta-large-vit-huge-14.pth",
            *[base / f"diffusion_pytorch_model-{i:05d}-of-00007.safetensors" for i in range(1, 8)],
            base / "google/umt5-xxl/tokenizer_config.json",
            base / "xlm-roberta-large/tokenizer_config.json",
            weights / "chinese-wav2vec2-base/config.json",
            weights / "chinese-wav2vec2-base/model.safetensors",
            weights / "InfiniteTalk/single/infinitetalk.safetensors"]


RUNTIME_PROBE = """import json, torch
print(json.dumps({'torch': torch.__version__, 'cuda': torch.cuda.is_available(),
 'mps': bool(hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()),
 'gpu': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
 'vram_gib': round(torch.cuda.get_device_properties(0).total_memory / 2**30, 2) if torch.cuda.is_available() else None}))
"""


def doctor(backend: str | None = None, *, probe_runtime: bool = True) -> dict:
    cfg = settings()
    backend = backend or cfg.default_backend
    home, python, spec = installation(backend)
    issues = []
    if not (home / spec["entrypoint"]).is_file():
        issues.append("Brakuje przypiętego repozytorium modelu")
    elif not (home / ".git").exists():
        issues.append("Brakuje metadanych Git do sprawdzenia wersji modelu")
    else:
        head = subprocess.run(["git", "-C", str(home), "rev-parse", "HEAD"], capture_output=True, text=True)
        if head.returncode or head.stdout.strip() != spec["commit"]:
            issues.append("Wersja modelu różni się od avatar-tools.lock.json")
    if not python.is_file():
        issues.append("Brakuje oddzielnego środowiska Python modelu")
    missing = [str(p.relative_to(home)) for p in required_models(backend, home, cfg) if not p.is_file() or p.stat().st_size == 0]
    if missing:
        issues.append("Brakuje wag modelu; instalator ma opcję --download-models")
    for binary in ("ffmpeg", "ffprobe"):
        if not shutil.which(binary):
            issues.append(f"Brakuje {binary}")
    runtime = None
    if platform.system() == "Darwin" and backend == "infinitetalk":
        issues.append("InfiniteTalk wymaga NVIDIA/CUDA; GPU Apple nie obsługuje tego backendu")
    if probe_runtime and python.is_file():
        try:
            check = subprocess.run([str(python), "-c", RUNTIME_PROBE], capture_output=True, text=True, timeout=45)
            if check.returncode:
                issues.append("Nie udało się zaimportować PyTorch w środowisku modelu")
            else:
                runtime = json.loads(check.stdout)
        except (subprocess.TimeoutExpired, ValueError, OSError):
            issues.append("Nie udało się sprawdzić środowiska PyTorch")
    device = "cpu" if platform.system() == "Darwin" else cfg.device
    if device == "auto" and runtime:
        device = "cuda" if runtime["cuda"] else "cpu"
    if runtime and (backend == "infinitetalk" or device == "cuda") and not runtime["cuda"]:
        issues.append("CUDA niedostępne; sprawdź sterownik Windows, WSL2 i wersję PyTorch")
    return {"backend": backend, "configured": not issues, "runtime_checked": runtime is not None,
            "ready_for_inference": not issues and runtime is not None,
            "installation_present": python.is_file() and (home / spec["entrypoint"]).is_file(),
            "device": device, "runtime": runtime, "missing_models": missing, "issues": issues,
            "tested_inference": False, "automatic_api_fallback": False}


def probe_media(path: Path) -> dict:
    try:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                                capture_output=True, text=True, check=True, timeout=30)
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, ValueError, OSError, subprocess.TimeoutExpired) as error:
        raise ValueError("Nie udało się odczytać pliku audio/wideo przez ffprobe") from error


@contextmanager
def inference_lock():
    if sys.platform == "win32":
        raise ValueError("Na Windows uruchom lokalne modele w WSL2")
    import fcntl
    lockfile = data_dir() / ".avatar-inference.lock"
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    with lockfile.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("Trwa inne lokalne generowanie awatara; poczekaj na zakończenie") from error
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def generate(store: Store, project_id: str, photo: Path, audio: Path, *, backend: str | None = None,
             prompt: str = "A presenter speaking naturally to the camera, stable lighting and framing.") -> dict:
    cfg = settings()
    backend = backend or cfg.default_backend
    project, revision = store.load(project_id)
    photo, audio = photo.expanduser().resolve(), audio.expanduser().resolve()
    if not photo.is_file() or not audio.is_file():
        raise ValueError("Podaj istniejące lokalne zdjęcie i nagranie audio")
    if photo.stat().st_size > 10 * 1024 * 1024:
        raise ValueError("Zdjęcie przekracza 10 MB")
    with Image.open(photo) as image:
        if image.format not in {"PNG", "JPEG"} or min(image.size) < 256:
            raise ValueError("Potrzebny JPEG/PNG o wymiarach co najmniej 256×256")
        image.verify()
    media = probe_media(audio)
    if not any(s.get("codec_type") == "audio" for s in media["streams"]):
        raise ValueError("Plik nie ma ścieżki audio")
    duration = float(media["format"].get("duration", 0))
    if not 0 < duration <= cfg.max_audio_seconds:
        raise ValueError(f"Pierwszy test: audio musi trwać do {cfg.max_audio_seconds:g} sekund; podziel dłuższą narrację")
    status = doctor(backend)
    if not status["ready_for_inference"]:
        raise ValueError("; ".join(status["issues"]))
    home, python, spec = installation(backend)
    run_id = uuid.uuid4().hex
    relative = f"assets/avatar/{run_id}"
    folder = artifact(project_id, relative)
    folder.mkdir(parents=True)
    source = folder / "photo.png"
    with Image.open(photo) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((1024, 1024))
        image.save(source)
    wave = folder / "audio.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(audio), "-vn", "-ac", "1", "-ar", "16000", str(wave)], check=True)
    results = folder / "upstream"
    results.mkdir()
    if backend == "sadtalker":
        command = [str(python), str(home / spec["entrypoint"]), "--source_image", str(source),
                   "--driven_audio", str(wave), "--result_dir", str(results), "--checkpoint_dir", str(home / "checkpoints"),
                   "--size", str(cfg.sadtalker_size), "--batch_size", "1", "--preprocess", "crop", "--still"]
        if status["device"] == "cpu":
            command.append("--cpu")
    else:
        input_file = folder / "input.json"
        input_file.write_text(json.dumps({"prompt": prompt, "cond_video": str(source), "cond_audio": {"person1": str(wave)}}))
        weights = home / "weights"
        command = [str(python), str(home / spec["entrypoint"]), "--ckpt_dir", str(weights / "Wan2.1-I2V-14B-480P"),
                   "--wav2vec_dir", str(weights / "chinese-wav2vec2-base"),
                   "--infinitetalk_dir", str(weights / "InfiniteTalk/single/infinitetalk.safetensors"),
                   "--input_json", str(input_file), "--size", cfg.infinitetalk_size, "--sample_steps", str(cfg.infinitetalk_steps),
                   "--mode", "streaming", "--num_persistent_param_in_dit", "0", "--t5_cpu", "--offload_model", "True",
                   "--save_file", str(results / "generated")]
    environment = os.environ | {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "OMP_NUM_THREADS": "4", "MKL_NUM_THREADS": "4"}
    started = time.monotonic()
    with inference_lock(), (folder / "inference.log").open("w") as log:
        try:
            subprocess.run(command, cwd=home, env=environment, stdout=log, stderr=subprocess.STDOUT,
                           check=True, timeout=cfg.timeout_seconds)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as error:
            raise ValueError(f"Lokalne generowanie nie powiodło się; szczegóły w {relative}/inference.log. HeyGen nie został wywołany") from error
    outputs = list(results.glob("*.mp4"))
    if len(outputs) != 1:
        raise ValueError("Model nie zwrócił jednego filmu; sprawdź inference.log (np. niewykryta twarz)")
    result_probe = probe_media(outputs[0])
    types = {s.get("codec_type") for s in result_probe["streams"]}
    if not {"video", "audio"} <= types or abs(float(result_probe["format"].get("duration", 0)) - duration) > 0.6:
        raise ValueError("Wynik modelu nie ma obrazu, audio lub pełnej długości narracji")
    target = folder / "avatar.mp4"
    shutil.copyfile(outputs[0], target)
    record = {"backend": backend, "upstream_commit": spec["commit"], "device": status["device"],
              "runtime": status["runtime"], "path": f"{relative}/avatar.mp4", "sha256": file_hash(target),
              "photo_sha256": file_hash(source), "audio_sha256": file_hash(wave), "duration": duration,
              "elapsed_seconds": round(time.monotonic() - started, 2), "created_at": now().isoformat(),
              "review_required": True, "api_used": False}
    (folder / "generation.json").write_text(json.dumps(record, ensure_ascii=False, indent=2))
    project.assets.append(Asset(id="avatar-" + run_id, kind="avatar", path=record["path"], sha256=record["sha256"],
                                purpose="presenter", creator="Operator i lokalny model " + backend,
                                usage_basis="Zdjęcie i audio dostarczone przez operatora; prawa wymagają przeglądu",
                                display_label="Awatar AI"))
    store.save(project, expected_revision=revision)
    store.event(project_id, "local_avatar", record)
    return record
