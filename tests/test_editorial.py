from datetime import timedelta

import pytest

from studio.models import Asset, Evidence
from studio.quality import evaluate
from studio.store import artifact


def codes(project):
    return {i["code"] for i in evaluate(project)["issues"]}


def test_syndicated_domains_are_not_independent(ready):
    assert evaluate(ready)["ok"]
    ready.sources[1].origin_group = ready.sources[0].origin_group
    assert "independent_sources" in codes(ready)


def test_quote_does_not_prove_allegation(ready):
    ready.claims[0].evidence[1].verifies = "statement"
    assert "independent_sources" in codes(ready)


def test_counter_evidence_and_freshness_block_delivery(ready):
    ready.claims[0].evidence.append(Evidence(source_id="s2", excerpt="Doniesienie sprzeczne", relation="contradicts"))
    ready.claims[0].checked_at -= timedelta(days=2)
    assert {"contradiction", "stale_check"} <= codes(ready)


def test_slop_and_fake_evidence_are_rejected(ready):
    ready.assets = [Asset(id="a1", kind="generated", path="assets/fake.png", purpose="evidence", usage_basis="Generacja testowa", usage_reviewed=True, display_label="Ilustracja AI")]
    ready.scenes[0].narration = "W dzisiejszym świecie to zmienia wszystko."
    ready.scenes.extend([ready.scenes[0].model_copy(update={"id": "two"}), ready.scenes[0].model_copy(update={"id": "three"})])
    assert {"illustration_as_evidence", "generic_script", "repeated_layout", "recycled_visual", "generic_visual_majority"} <= codes(ready)


def test_clip_requires_wider_context(ready):
    ready.assets[0] = Asset(id="a1", kind="source_clip", source_id="s1", path="clip.mp4", purpose="evidence", usage_basis="Komentarz do cytatu testowego", usage_reviewed=True, context_reviewed=True, in_seconds=10, out_seconds=14)
    assert "clip_context" in codes(ready)
    ready.assets[0].context_in_seconds = 5
    ready.assets[0].context_out_seconds = 20
    assert "clip_context" not in codes(ready)


def test_approval_invalidated_by_edit_and_media_mutation(store, ready):
    store.approve(ready.id, "Redaktor")
    store.require_approval(ready)
    artifact(ready.id, ready.rendered_path).write_bytes(b"different-video")
    with pytest.raises(ValueError, match="zmienił"):
        store.require_approval(ready)
    ready.angle = "Nowa teza"
    store.save(ready)
    with pytest.raises(ValueError, match="akceptacja"):
        store.require_approval(ready)


def test_stale_creative_review_does_not_approve_new_render(ready):
    ready.render_sha256 = "another-render"
    assert "unreviewed_render" in codes(ready)


def test_replaced_source_asset_blocks_export(store, ready):
    store.approve(ready.id, "Redaktor")
    artifact(ready.id, ready.assets[0].path).write_bytes(b"replaced-material")
    with pytest.raises(ValueError, match="Materiał"):
        store.require_approval(ready)


def test_optimistic_save_protects_parallel_editors(store, ready):
    project, revision = store.load(ready.id)
    project.title = "Pierwsza zmiana"
    store.save(project, expected_revision=revision)
    project.title = "Druga zmiana"
    with pytest.raises(ValueError, match="zmienił"):
        store.save(project, expected_revision=revision)
