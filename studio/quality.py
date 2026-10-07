"""Editorial checks are heuristics; human creative judgement remains explicit."""
from collections import Counter
from datetime import datetime, timedelta, timezone
import re

from .models import Project


GENERIC = re.compile(r"w dzisiejszym (?:świecie|filmie)|przyjrzyjmy się bliżej|to zmienia wszystko|szokujące kulisy|nie uwierzysz|zagłębmy się", re.I)


def evaluate(project: Project, *, at: datetime | None = None) -> dict:
    at = at or datetime.now(timezone.utc)
    issues: list[dict] = []

    def add(code: str, message: str, ref: str = "", severity: str = "error"):
        issues.append(dict(code=code, message=message, ref=ref, severity=severity))

    sources = {s.id: s for s in project.sources}
    claims = {c.id: c for c in project.claims}
    assets = {a.id: a for a in project.assets}
    for label, records in [("source", project.sources), ("claim", project.claims), ("asset", project.assets), ("scene", project.scenes)]:
        if len({x.id for x in records}) != len(records):
            add("duplicate_id", f"Powtórzone identyfikatory: {label}.")
    if not project.angle.strip():
        add("missing_angle", "Brakuje własnej tezy lub pytania redakcyjnego.")
    if not project.scenes:
        add("empty_story", "Brakuje scen.")
    for source in project.sources:
        if source.published_at > at or source.captured_at > at:
            add("future_source", "Data źródła znajduje się w przyszłości.", source.id)
        if not source.origin_group.strip():
            add("missing_origin", "Źródło nie ma ustalonego pierwotnego pochodzenia.", source.id)
    for claim in project.claims:
        for evidence in claim.evidence:
            if evidence.source_id not in sources:
                add("missing_source", "Nie istnieje wskazane źródło.", claim.id)
            if not evidence.excerpt.strip():
                add("empty_evidence", "Potrzebny jest konkretny fragment potwierdzający twierdzenie.", claim.id)
        supporting = [e for e in claim.evidence if e.relation == "supports" and e.verifies == "substance" and e.source_id in sources]
        origins = {sources[e.source_id].origin_group for e in supporting}
        if claim.important and claim.kind == "fact" and len(origins) < 2:
            add("independent_sources", "Kluczowy fakt potrzebuje co najmniej dwóch niezależnych źródeł; cytat potwierdza wypowiedź, nie jej treść.", claim.id)
        if claim.kind in {"allegation", "opinion", "unconfirmed"} and not claim.attribution:
            add("missing_attribution", "Przypisz zarzut, opinię lub doniesienie do autora i zaznacz jego status.", claim.id)
        if claim.kind != "opinion" and not claim.evidence:
            add("missing_evidence", "Twierdzenie nie ma materiału źródłowego.", claim.id)
        if not claim.allowed_wording.strip():
            add("missing_wording", "Brakuje zaakceptowanego sformułowania twierdzenia.", claim.id)
        if any(e.relation == "contradicts" for e in claim.evidence) and not claim.contradiction_resolution:
            add("contradiction", "Rozstrzygnij sprzeczne doniesienia lub zaznacz spór w scenariuszu.", claim.id)
        if claim.important:
            if not claim.counter_search or not claim.counter_search_at:
                add("counter_search", "Zapisz sprawdzenie dementi, sprostowań i stanowiska drugiej strony.", claim.id)
            if claim.checked_at is None or claim.checked_at < at - timedelta(hours=24):
                add("stale_check", "Ponownie sprawdź informację przed przekazaniem do publikacji (24 h).", claim.id)
            if claim.checked_at and claim.checked_at > at:
                add("future_check", "Data weryfikacji znajduje się w przyszłości.", claim.id)
            if claim.counter_search_at and (claim.counter_search_at > at or claim.counter_search_at < at - timedelta(hours=24)):
                add("stale_counter_search", "Sprawdzenie dementi wymaga aktualnej daty (24 h).", claim.id)
    for asset in project.assets:
        if not asset.usage_basis.strip() or not asset.usage_reviewed:
            add("usage_unreviewed", "Ustal podstawę użycia konkretnego materiału.", asset.id)
        if asset.purpose == "evidence" and asset.kind in {"stock", "generated", "avatar"}:
            add("illustration_as_evidence", "Stock, ilustracja AI i awatar nie potwierdzają zdarzenia.", asset.id)
        if asset.kind in {"generated", "stock"} and not asset.display_label:
            add("missing_label", "Materiał ilustracyjny wymaga jawnego opisu w planie i oznaczenia, gdy może zmylić widza.", asset.id)
        if asset.kind in {"source_clip", "article_capture", "photo"}:
            if asset.source_id not in sources:
                add("asset_source", "Materiał źródłowy musi wskazywać rzeczywistą publikację.", asset.id)
            if not asset.context_reviewed:
                add("context_unreviewed", "Obejrzyj materiał i szerszy kontekst przed wyborem.", asset.id)
        if asset.kind == "source_clip":
            valid = all(x is not None for x in [asset.in_seconds, asset.out_seconds, asset.context_in_seconds, asset.context_out_seconds])
            if not valid or not (0 <= asset.context_in_seconds <= asset.in_seconds < asset.out_seconds <= asset.context_out_seconds):
                add("clip_context", "Zapisz prawidłowe czasy fragmentu i szerszego kontekstu.", asset.id)
    consecutive = 1
    for index, scene in enumerate(project.scenes):
        if len(scene.narration.split()) / scene.duration > 3.5:
            add("rushed_voice", "Tekst jest zbyt gęsty na naturalną polską narrację.", scene.id)
        if GENERIC.search(scene.narration):
            add("generic_script", "Zastąp ogólnik konkretną obserwacją lub informacją.", scene.id)
        if not scene.purpose.strip() or not scene.selection_reason.strip():
            add("visual_intent", "Każda scena potrzebuje celu i uzasadnienia doboru obrazu.", scene.id)
        if not scene.asset_ids:
            add("missing_visual", "Scena nie ma wybranego materiału.", scene.id)
        for claim_id in scene.claim_ids:
            if claim_id not in claims:
                add("scene_claim", "Scena odnosi się do nieistniejącego twierdzenia.", scene.id)
        for asset_id in scene.asset_ids:
            if asset_id not in assets:
                add("scene_asset", "Scena odnosi się do nieistniejącego materiału.", scene.id)
            elif assets[asset_id].kind == "chart" and not scene.data_source_ids:
                add("unsourced_chart", "Wykres potrzebuje źródła liczb, jednostek i okresu w opisie sceny.", scene.id)
        for source_id in scene.data_source_ids:
            if source_id not in sources:
                add("chart_source", "Nie istnieje źródło danych wykresu.", scene.id)
        if index and scene.layout == project.scenes[index - 1].layout:
            consecutive += 1
        else:
            consecutive = 1
        if consecutive == 3:
            add("repeated_layout", "Trzy takie same układy z rzędu wymagają zmiany inscenizacji.", scene.id)
    used = Counter(a for s in project.scenes for a in s.asset_ids)
    for aid, count in used.items():
        if count > 2 and aid in assets and assets[aid].kind in {"stock", "generated"}:
            add("recycled_visual", "Ten sam materiał ilustracyjny wraca zbyt często.", aid)
    if project.scenes:
        illustrative = sum(any(assets[a].kind in {"stock", "generated"} for a in s.asset_ids if a in assets) for s in project.scenes)
        if illustrative / len(project.scenes) > 0.5:
            add("generic_visual_majority", "Większość scen opiera się na stockach lub obrazach AI; wybierz więcej materiałów konkretnych dla tematu.")
    review = project.creative_review
    if review is None:
        add("creative_review", "Film wymaga obejrzenia i oceny redakcyjnej po renderze.")
    else:
        if review.reviewed_render_sha256 != project.render_sha256:
            add("unreviewed_render", "Ocena redakcyjna dotyczy innego pliku filmu.")
        for name in ("originality", "specificity", "visual_storytelling", "pacing", "natural_voice", "mobile_legibility", "sound_mix"):
            if getattr(review, name) < 4:
                add("creative_score", f"Ocena {name} poniżej 4/5: popraw film.")
        if not review.notes.strip() or not review.reviewer.strip():
            add("review_notes", "Zapisz autora i uzasadnienie oceny, także konkretne słabości.")
    if not project.rendered_path or not project.render_sha256:
        add("missing_render", "Brakuje zweryfikowanego pliku wideo.")
    else:
        from .store import story_hash
        if project.render_story_sha256 != story_hash(project):
            add("outdated_render", "Scenariusz lub materiały zmieniły się od renderowania filmu.")
    if project.demo:
        add("demo_only", "Przykład techniczny nie jest materiałem do publikacji.")
    return {"ok": not any(i["severity"] == "error" for i in issues), "issues": issues,
            "note": "Automatyczne reguły wykrywają część problemów. Naturalność i jakość wymagają obejrzenia filmu."}
