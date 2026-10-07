from datetime import timedelta
from pathlib import Path

import pytest

from studio.models import Asset, Claim, CreativeReview, Evidence, Project, Scene, Source, now
from studio.store import Store, artifact, file_hash, story_hash


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_DATA_DIR", str(tmp_path))
    value = Store()
    yield value
    value.close()


@pytest.fixture
def ready(store):
    timestamp = now()
    sources = [Source(id=f"s{i}", url=f"https://source{i}.example/article", title=f"Publikacja {i}", publisher=f"Redakcja {i}", origin_group=f"origin-{i}", published_at=timestamp-timedelta(hours=2), original=True) for i in (1, 2)]
    claim = Claim(id="c1", text="Potwierdzony fakt testowy", kind="fact", allowed_wording="Weryfikowalna informacja testowa",
                  evidence=[Evidence(source_id=s.id, excerpt="Konkretny fragment ustalenia testowego") for s in sources],
                  checked_at=timestamp, counter_search="Sprawdzono sprostowania i stanowisko strony; brak nowych doniesień w fixture", counter_search_at=timestamp)
    asset = Asset(id="a1", kind="own_footage", path="assets/recording.mp4", usage_basis="Własne nagranie testowe", usage_reviewed=True, context_reviewed=True, purpose="presenter")
    asset_path = artifact("test", asset.path); asset_path.parent.mkdir(); asset_path.write_bytes(b"fixture-own-footage")
    asset.sha256 = file_hash(asset_path)
    project = Project(id="test", title="Film testowy", angle="Konkretna własna obserwacja", sources=sources, claims=[claim], assets=[asset],
                      scenes=[Scene(id="one", duration=6, narration="Konkretna informacja i własne wyjaśnienie.", purpose="Wyjaśnienie mechanizmu", layout="presenter", claim_ids=["c1"], asset_ids=["a1"], selection_reason="Pokazuje autora komentarza.")])
    path = artifact(project.id, "renders/final.mp4"); path.parent.mkdir(); path.write_bytes(b"fixture-not-a-real-video")
    project.rendered_path = "renders/final.mp4"
    project.render_sha256 = file_hash(path)
    project.render_story_sha256 = story_hash(project)
    project.creative_review = CreativeReview(reviewer="Redaktor fixture", reviewed_render_sha256=project.render_sha256,
                                            originality=4, specificity=4, visual_storytelling=4, pacing=4, natural_voice=4, mobile_legibility=4, sound_mix=4,
                                            notes="Oceny testowe; ten fixture sprawdza wyłącznie bramki publikacji, nie jakość prawdziwego filmu.")
    store.save(project)
    return project
