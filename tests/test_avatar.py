import base64
import json
from types import SimpleNamespace

from PIL import Image
import pytest

from studio.providers import create_photo_avatar


def test_local_photo_uses_private_stdin_and_no_analytics(tmp_path, monkeypatch):
    photo = tmp_path / "my-photo.png"
    Image.new("RGB", (600, 800), (100, 120, 90)).save(photo)
    monkeypatch.setenv("HEYGEN_API_KEY", "fixture-placeholder")
    monkeypatch.setattr("studio.providers.heygen_binary", lambda: "fixture-heygen-cli")
    calls = []
    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        assert command[-2:] == ["-d", "-"]
        payload = json.loads(kwargs["input"])
        assert payload["type"] == "photo"
        assert payload["file"]["media_type"] == "image/png"
        assert base64.b64decode(payload["file"]["data"]) == photo.read_bytes()
        assert kwargs["env"]["HEYGEN_NO_ANALYTICS"] == "1"
        return SimpleNamespace(returncode=0, stdout='{"data":{"avatar_id":"test-avatar","status":"processing"}}')
    monkeypatch.setattr("studio.providers.subprocess.run", fake_run)
    result = create_photo_avatar("Użytkownik testowy", str(photo))
    assert result["data"]["status"] == "processing"
    assert len(calls) == 1


def test_invalid_photo_is_rejected_before_service_request(tmp_path, monkeypatch):
    photo = tmp_path / "too-small.png"
    Image.new("RGB", (300, 500)).save(photo)
    monkeypatch.setattr("studio.providers.subprocess.run", lambda *args, **kwargs: pytest.fail("No service call for invalid photo"))
    with pytest.raises(ValueError, match="512"):
        create_photo_avatar("Użytkownik testowy", str(photo))
