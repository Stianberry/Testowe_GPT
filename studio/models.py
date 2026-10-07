from datetime import datetime, timezone
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


def now() -> datetime:
    return datetime.now(timezone.utc)


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Source(Record):
    id: str
    url: str
    title: str
    publisher: str
    # Shared upstream report = same origin_group, even on different domains.
    origin_group: str
    published_at: AwareDatetime
    captured_at: AwareDatetime = Field(default_factory=now)
    original: bool = False
    text_path: str | None = None
    screenshot_path: str | None = None
    sha256: str | None = None


class Evidence(Record):
    source_id: str
    excerpt: str
    relation: Literal["supports", "contradicts", "context"] = "supports"
    timestamp: str | None = None
    # What this source actually establishes; a quote is not proof of its allegation.
    verifies: Literal["substance", "statement"] = "substance"


class Claim(Record):
    id: str
    text: str
    kind: Literal["fact", "allegation", "opinion", "unconfirmed"]
    important: bool = True
    evidence: list[Evidence] = Field(default_factory=list)
    attribution: str | None = None
    allowed_wording: str
    checked_at: AwareDatetime | None = None
    counter_search: str | None = None
    counter_search_at: AwareDatetime | None = None
    contradiction_resolution: str | None = None


class Asset(Record):
    id: str
    kind: Literal["source_clip", "article_capture", "photo", "stock", "generated", "chart", "avatar", "own_footage"]
    path: str
    source_id: str | None = None
    source_url: str | None = None
    creator: str | None = None
    usage_basis: str
    usage_reviewed: bool = False
    purpose: Literal["evidence", "illustration", "explanation", "presenter"]
    # Machine acquisition is followed by actual inspection of the selected crop/clip.
    context_reviewed: bool = False
    in_seconds: float | None = None
    out_seconds: float | None = None
    context_in_seconds: float | None = None
    context_out_seconds: float | None = None
    sha256: str | None = None
    display_label: str | None = None


class Scene(Record):
    id: str
    duration: float = Field(gt=0, le=120)
    narration: str
    purpose: str
    layout: str
    claim_ids: list[str] = Field(default_factory=list)
    asset_ids: list[str] = Field(default_factory=list)
    # Candidates and selection rationale force a deliberate visual decision.
    candidates: list[str] = Field(default_factory=list)
    selection_reason: str
    data_source_ids: list[str] = Field(default_factory=list)


class CreativeReview(Record):
    reviewer: str
    reviewed_at: AwareDatetime = Field(default_factory=now)
    reviewed_render_sha256: str
    originality: int = Field(ge=1, le=5)
    specificity: int = Field(ge=1, le=5)
    visual_storytelling: int = Field(ge=1, le=5)
    pacing: int = Field(ge=1, le=5)
    natural_voice: int = Field(ge=1, le=5)
    mobile_legibility: int = Field(ge=1, le=5)
    sound_mix: int = Field(ge=1, le=5)
    notes: str


class Project(Record):
    id: str
    title: str
    angle: str
    created_at: AwareDatetime = Field(default_factory=now)
    demo: bool = False
    sources: list[Source] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    assets: list[Asset] = Field(default_factory=list)
    scenes: list[Scene] = Field(default_factory=list)
    creative_review: CreativeReview | None = None
    rendered_path: str | None = None
    render_sha256: str | None = None
    render_story_sha256: str | None = None
