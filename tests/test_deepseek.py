import json

import httpx
import pytest

from studio import deepseek
from studio.store import artifact, content_hash


def api_client(proposal, *, finish="stop", inspect=None):
    def handle(request):
        assert request.url == "https://api.deepseek.com/chat/completions"
        payload = json.loads(request.content)
        assert payload["response_format"] == {"type": "json_object"}
        if inspect:
            inspect(payload)
        return httpx.Response(200, json={"model": "fixture-model", "choices": [{"finish_reason": finish, "message": {"content": json.dumps(proposal)}}],
                                       "usage": {"prompt_tokens": 100, "completion_tokens": 50}})
    return httpx.Client(base_url="https://api.deepseek.com/", transport=httpx.MockTransport(handle))


def test_script_is_source_bound_and_saved_as_proposal_only(store, ready, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fixture-not-a-real-key")
    proposal = {"hook": "Co wynika ze źródeł?", "scenes": [ready.scenes[0].model_dump(mode="json")], "editorial_notes": ["Potrzebny przegląd narracji."]}
    def inspect(payload):
        material = json.loads(payload["messages"][1]["content"])
        assert material["claims"][0]["evidence"][0]["source_id"] == "s1"
        assert material["claims"][0]["allowed_wording"] == ready.claims[0].allowed_wording
        assert "fixture-not-a-real-key" not in json.dumps(payload)
    with api_client(proposal, inspect=inspect) as client:
        result = deepseek.propose(store, ready.id, client=client)
    saved = json.loads(artifact(ready.id, result["path"]).read_text())
    assert saved["review_required"] and saved["usage"]["completion_tokens"] == 50
    assert content_hash(store.load(ready.id)[0]) == content_hash(ready)


@pytest.mark.parametrize("case", ["unknown_claim", "truncated"])
def test_invalid_or_incomplete_script_is_not_saved(store, ready, monkeypatch, case):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fixture")
    scene = ready.scenes[0].model_dump(mode="json")
    if case == "unknown_claim":
        scene["claim_ids"] = ["invented"]
    proposal = {"hook": "Hook", "scenes": [scene], "editorial_notes": []}
    with api_client(proposal, finish="length" if case == "truncated" else "stop") as client:
        with pytest.raises(ValueError):
            deepseek.propose(store, ready.id, client=client)
    assert not list(artifact(ready.id, "proposals").glob("*.json"))


def test_missing_key_does_not_contact_service(store, ready, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(deepseek.httpx, "Client", lambda **kwargs: pytest.fail("No network call without credentials"))
    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        deepseek.propose(store, ready.id)
