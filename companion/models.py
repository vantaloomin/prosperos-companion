"""Request bodies. Input mirrors prosperos-study server/models.py at bbcbde4."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Relationship = Literal['friendship', 'romance', 'mentor', 'family', 'other']
Layer = Literal['user_fact', 'shared_experience', 'plan', 'temporary', 'relationship', 'companion_life']
PlanStatus = Literal['proposed', 'agreed', 'postponed', 'cancelled', 'completed']
EventKind = Literal['routine', 'plan', 'ordinary', 'thread']


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class CharacterDefinition(Input):
    name: str = Field(min_length=1, max_length=120)
    identity: str = Field(default='', max_length=4000)
    personality: str = Field(default='', max_length=8000)
    voice: str = Field(default='', max_length=4000)
    interests: list[str] = Field(default_factory=list, max_length=50)
    background: str = Field(default='', max_length=12000)
    appearance: str = Field(default='', max_length=4000)
    routine: str = Field(default='', max_length=8000)
    location: str = Field(default='', max_length=200)
    relationship: Relationship = 'friendship'
    # Empty means neutral about absence. Jealousy, guilt or missing the user are opt-in traits.
    absence_reaction: str = Field(default='', max_length=2000)
    timezone: str = Field(default='UTC', max_length=64)


class CharacterRevision(Input):
    definition: CharacterDefinition
    note: str = Field(default='', max_length=500)
    expected_version_id: str


class SettingsUpdate(Input):
    user_timezone: str | None = Field(default=None, max_length=64)
    automatic_memory: bool | None = None
    sensitive_memory: bool | None = None
    share_profile_across_timelines: bool | None = None
    background_activity: bool | None = None
    review_complete: bool | None = None


class ConnectionUpdate(Input):
    base_url: str = Field(min_length=1, max_length=500)
    model: str = Field(min_length=1, max_length=200)
    api_key: str | None = Field(default=None, max_length=4000)
    max_output_tokens: int = Field(default=800, ge=64, le=128000)
    context_tokens: int = Field(default=16000, ge=1024, le=2000000)
    timeout_seconds: int = Field(default=180, ge=10, le=1800)


class MessageCreate(Input):
    text: str = Field(min_length=1, max_length=40000)
    client_id: str = Field(min_length=8, max_length=100)


class MemoryCreate(Input):
    layer: Layer
    subject: str = Field(min_length=1, max_length=200)
    value: str = Field(min_length=1, max_length=4000)
    reality: Literal['real', 'fiction'] = 'real'
    boundary: bool = False
    sensitive: bool = False
    plan_status: PlanStatus | None = None
    applies_from: str | None = None
    applies_until: str | None = None
    source_message_ids: list[str] = Field(default_factory=list, max_length=20)
    tentative: bool = False


class MemoryCorrection(Input):
    value: str = Field(min_length=1, max_length=4000)
    plan_status: PlanStatus | None = None
    applies_from: str | None = None
    applies_until: str | None = None
    expected_revision: int


class MemoryDelete(Input):
    delete_sources: bool = False


class EventProposal(Input):
    idempotency_key: str = Field(min_length=8, max_length=200)
    kind: EventKind
    summary: str = Field(min_length=1, max_length=2000)
    details: dict = Field(default_factory=dict)
    starts_at: str
    ends_at: str
    inputs: dict = Field(default_factory=dict)


class EventCorrection(Input):
    summary: str = Field(min_length=1, max_length=2000)
    details: dict = Field(default_factory=dict)
