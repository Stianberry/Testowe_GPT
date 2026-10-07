import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

from PIL import Image
import pytest

from studio import local_avatar
from studio.store import artifact, content_hash, file_hash


def media(tmp_path, seconds=1):
    photo, audio = tmp_path / "portrait.png", tmp_path / "voice.wav"
    Image.new("RGB", (600, 800), (110, 130, 90)).save(photo)
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=22050",
                    "-t", str(seconds), str(audio)], check=True)
    return photo, audio


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_local_pipeline_registers_real_fixture_media_and_invalidates_approval(store, ready, tmp_path, monkeypatch, device):
    # The upstream inference is a fixture; normalization, MP4 validation, hashing,
    # project storage and invalidation run for real. This is not an AI quality test.
    store.approve(ready.id, "Fixture redaktora")
    photo, audio = media(tmp_path)
    home = tmp_path / "model"; home.mkdir()
    monkeypatch.setattr(local_avatar, "installation", lambda backend: (home, Path(sys.executable), {"entrypoint": "inference.py", "commit": "fixture-commit"}))
    monkeypatch.setattr(local_avatar, "doctor", lambda backend: {"ready_for_inference": True, "device": device, "runtime": {"cuda": device == "cuda"}})
    real_run = subprocess.run
    calls = []
    def run(command, **kwargs):
        if len(command) > 1 and command[1].endswith("inference.py"):
            calls.append(command)
            assert ("--cpu" in command) == (device == "cpu")
            assert command[command.index("--batch_size") + 1] == "1"
            assert "--enhancer" not in command
            wave = command[command.index("--driven_audio") + 1]
            target = Path(command[command.index("--result_dir") + 1]) / "fixture.mp4"
            real_run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=green:size=256x256:rate=25",
                      "-i", wave, "-t", "1", "-c:v", "libx264", "-c:a", "aac", str(target)], check=True)
            return SimpleNamespace(returncode=0)
        return real_run(command, **kwargs)
    monkeypatch.setattr(local_avatar.subprocess, "run", run)
    monkeypatch.setattr("studio.providers.create_photo_avatar", lambda *a, **k: pytest.fail("Local inference must not call HeyGen"))
    record = local_avatar.generate(store, ready.id, photo, audio)
    project, _ = store.load(ready.id)
    assert len(calls) == 1 and not record["api_used"]
    asset = project.assets[-1]
    assert asset.kind == "avatar" and not asset.context_reviewed and not asset.usage_reviewed
    assert file_hash(artifact(ready.id, asset.path)) == asset.sha256
    assert record["duration"] == 1 and record["review_required"]
    with pytest.raises(ValueError, match="akceptacja"):
        store.require_approval(project)


def test_long_audio_is_rejected_before_model_initialization(store, ready, tmp_path, monkeypatch):
    photo, audio = media(tmp_path, seconds=16)
    monkeypatch.setattr(local_avatar, "doctor", lambda *a: pytest.fail("Long input must not load model"))
    with pytest.raises(ValueError, match="do 15 sekund"):
        local_avatar.generate(store, ready.id, photo, audio)
    assert content_hash(store.load(ready.id)[0]) == content_hash(ready)


def test_apple_selects_cpu_and_rejects_infinitetalk(tmp_path, monkeypatch):
    home = tmp_path / "model"; home.mkdir()
    (home / "inference.py").touch(); (home / "generate_infinitetalk.py").touch(); (home / ".git").mkdir()
    python = tmp_path / "python"; python.touch()
    monkeypatch.setattr(local_avatar.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(local_avatar, "installation", lambda backend: (home, python, {"entrypoint": "inference.py", "commit": "fixture"}))
    monkeypatch.setattr(local_avatar, "required_models", lambda *a: [])
    def run(command, **kwargs):
        return SimpleNamespace(returncode=0, stdout="fixture\n" if command[0] == "git" else json.dumps({"cuda": False, "mps": True, "gpu": None}))
    monkeypatch.setattr(local_avatar.subprocess, "run", run)
    sad = local_avatar.doctor("sadtalker")
    assert sad["ready_for_inference"] and sad["device"] == "cpu"
    infinite = local_avatar.doctor("infinitetalk")
    assert not infinite["ready_for_inference"]
    assert any("GPU Apple" in issue for issue in infinite["issues"])


def test_inference_is_serialized_and_lock_released(store):
    with local_avatar.inference_lock():
        with pytest.raises(ValueError, match="Trwa inne"):
            with local_avatar.inference_lock():
                pytest.fail("Concurrent model execution")
    with local_avatar.inference_lock():
        pass


def test_infinitetalk_uses_low_vram_profile_and_real_fixture_output(store, ready, tmp_path, monkeypatch):
    photo, audio = media(tmp_path)
    home = tmp_path / "model"; home.mkdir()
    monkeypatch.setattr(local_avatar, "installation", lambda backend: (home, Path(sys.executable), {"entrypoint": "generate_infinitetalk.py", "commit": "fixture"}))
    monkeypatch.setattr(local_avatar, "doctor", lambda backend: {"ready_for_inference": True, "device": "cuda", "runtime": {"cuda": True}})
    real_run = subprocess.run
    def run(command, **kwargs):
        if len(command) > 1 and command[1].endswith("generate_infinitetalk.py"):
            assert command[command.index("--size") + 1] == "infinitetalk-480"
            assert command[command.index("--num_persistent_param_in_dit") + 1] == "0"
            assert "--t5_cpu" in command and command[command.index("--offload_model") + 1] == "True"
            inputs = json.loads(Path(command[command.index("--input_json") + 1]).read_text())
            assert Path(inputs["cond_video"]).is_file()
            target = command[command.index("--save_file") + 1] + ".mp4"
            real_run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=size=480x480:rate=25",
                      "-i", inputs["cond_audio"]["person1"], "-t", "1", "-c:v", "libx264", "-c:a", "aac", target], check=True)
            return SimpleNamespace(returncode=0)
        return real_run(command, **kwargs)
    monkeypatch.setattr(local_avatar.subprocess, "run", run)
    result = local_avatar.generate(store, ready.id, photo, audio, backend="infinitetalk")
    assert result["backend"] == "infinitetalk" and result["duration"] == 1
