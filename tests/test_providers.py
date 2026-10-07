import json

import httpx
import pytest

from studio.providers import Postiz


def test_postiz_draft_never_publishes_and_deduplicates(store, ready, monkeypatch):
    monkeypatch.setenv("POSTIZ_API_KEY", "test-only-placeholder")
    requests = []
    def transport(request):
        requests.append(request)
        if request.url.path.endswith("/upload"):
            assert b"fixture-not-a-real-video" in request.content
            return httpx.Response(200, json={"id": "m1", "path": "https://uploads.postiz.com/test.mp4"})
        payload = json.loads(request.content)
        assert payload["type"] == "draft"
        assert payload["posts"][0]["settings"] == {"__type": "youtube", "title": "Film testowy", "type": "private"}
        return httpx.Response(200, json=[{"postId": "p1"}])
    client = httpx.Client(base_url="https://api.postiz.com/public/v1/", transport=httpx.MockTransport(transport))
    postiz = Postiz(client)
    with pytest.raises(ValueError, match="akceptacja"):
        postiz.draft(store, ready.id, "channel-1", "Opis", {"__type": "youtube"})
    assert not requests
    store.approve(ready.id, "Redaktor")
    settings = {"__type": "youtube", "title": "Film testowy", "type": "private"}
    first = postiz.draft(store, ready.id, "channel-1", "Opis", settings)
    assert postiz.draft(store, ready.id, "channel-1", "Opis", settings) == first
    assert len(requests) == 2


def test_uncertain_api_submission_is_not_retried(store, ready, monkeypatch):
    monkeypatch.setenv("POSTIZ_API_KEY", "test-only-placeholder")
    requests = []
    def transport(request):
        requests.append(request)
        raise httpx.ReadTimeout("Ambiguous network result")
    provider = Postiz(httpx.Client(base_url="https://api.postiz.com/public/v1/", transport=httpx.MockTransport(transport)))
    store.approve(ready.id, "Redaktor")
    with pytest.raises(httpx.ReadTimeout):
        provider.draft(store, ready.id, "channel", "Opis", {"__type": "threads"})
    with pytest.raises(ValueError, match="duplikat"):
        provider.draft(store, ready.id, "channel", "Opis", {"__type": "threads"})
    assert len(requests) == 1
