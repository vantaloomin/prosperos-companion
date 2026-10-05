"""Request bodies. Input mirrors prosperos-study server/models.py at bbcbde4."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Relationship = Literal['friendship', 'romance', 'mentor', 'family', 'other']
Layer = Literal['user_fact', 'shared_experience', 'plan', 'temporary', 'relationship', 'companion_life']
PlanStatus = Literal['proposed', 'agreed', 'postponed', 'cancelled', 'completed']
EventKind = Literal['routine', 'plan', 'ordinary', 'thread']
BlockKind = Literal['work', 'study', 'errand', 'leisure', 'social', 'rest', 'sleep']
ClockTime = Annotated[str, Field(pattern=r'^([01][0-9]|2[0-3]):[0-5][0-9]$')]
Intensity = Literal['mild', 'moderate', 'strong']


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class RoutineBlock(Input):
    """One recurring part of the companion's day, in the companion's timezone (PRD T2)."""
    key: str = Field(default='', max_length=60, pattern=r'^[a-z0-9-]*$')
    label: str = Field(min_length=1, max_length=120)
    kind: BlockKind = 'leisure'
    days: list[int] = Field(default_factory=lambda: list(range(7)), min_length=1, max_length=7)
    start: ClockTime
    end: ClockTime
    themes: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode='after')
    def check(self):
        if self.start == self.end:
            raise ValueError('A routine block must not start and end at the same time.')
        if any(day < 0 or day > 6 for day in self.days) or len(set(self.days)) != len(self.days):
            raise ValueError('Days are distinct weekday numbers from 0 (Monday) to 6 (Sunday).')
        return self


class EmotionalTrait(Input):
    """An opt-in trait such as jealousy or guilt over absence (PRD C6). None are enabled by default."""
    name: str = Field(min_length=1, max_length=60)
    intensity: Intensity = 'mild'
    note: str = Field(default='', max_length=500)


class MoneySetup(Input):
    """How the companion's money works (companion/life/money.py). Everything else comes from city data."""
    # A career id from the world data; empty guesses one from who they are, else an ordinary wage.
    career: str = Field(default='', max_length=60)
    style: Literal['careful', 'balanced', 'spender'] = 'balanced'
    # Empty lets the life simulation pick an everyday goal each half year.
    saving_for: str = Field(default='', max_length=120)
    goal: float = Field(default=0, ge=0, le=100_000_000)
    goal_since: str = Field(default='', pattern=r'^(\d{4}-\d{2}-\d{2})?$')


class CharacterDefinition(Input):
    name: str = Field(min_length=1, max_length=120)
    identity: str = Field(default='', max_length=4000)
    personality: str = Field(default='', max_length=8000)
    voice: str = Field(default='', max_length=4000)
    # What they are good at and what costs them, so the character reads as a person (both optional).
    skills: list[Annotated[str, Field(max_length=300)]] = Field(default_factory=list, max_length=20)
    flaws: list[Annotated[str, Field(max_length=300)]] = Field(default_factory=list, max_length=20)
    interests: list[str] = Field(default_factory=list, max_length=50)
    background: str = Field(default='', max_length=12000)
    appearance: str = Field(default='', max_length=4000)
    routine: str = Field(default='', max_length=8000)
    location: str = Field(default='', max_length=200)
    # City id in the installed world data (for example "baltimore"); events use its real places.
    home_city: str = Field(default='', max_length=60)
    relationship: Relationship = 'friendship'
    # Empty means neutral about absence. Jealousy, guilt or missing the user are opt-in traits.
    absence_reaction: str = Field(default='', max_length=2000)
    emotional_traits: list[EmotionalTrait] = Field(default_factory=list, max_length=12)
    timezone: str = Field(default='UTC', max_length=64)
    # Structured routine for the life simulation; empty uses a gentle default day.
    schedule: list[RoutineBlock] = Field(default_factory=list, max_length=24)
    # Themes automatic events may draw on (PRD T3).
    life_themes: list[str] = Field(default_factory=list, max_length=20)
    money: MoneySetup = Field(default_factory=MoneySetup)


DraftField = Literal['identity', 'personality', 'voice', 'skills', 'flaws', 'interests', 'background', 'appearance',
                     'routine', 'life_themes', 'schedule']


class CharacterDraftRequest(Input):
    """The quick start: a short idea and a few optional picks; the model drafts the rest."""
    idea: str = Field(default='', max_length=2000)
    name: str = Field(default='', max_length=120)
    relationship: Relationship = 'friendship'
    age: str = Field(default='', max_length=40)
    vibe: str = Field(default='', max_length=300)
    home_city: str = Field(default='', max_length=60)
    timezone: str = Field(default='UTC', max_length=64)
    # Jealousy, guilt over absence and similar traits stay off unless the user asks for them (PRD C6).
    emotional_edges: bool = False


class FieldDraftRequest(Input):
    """Rewrite one field of a character being edited, in keeping with the rest of it."""
    definition: dict
    field: DraftField
    request: str = Field(default='', max_length=500)


class PromptUpdate(Input):
    text: str = Field(min_length=1, max_length=20000)


class CharacterRevision(Input):
    definition: CharacterDefinition
    note: str = Field(default='', max_length=500)
    expected_version_id: str


class SettingsUpdate(Input):
    user_timezone: str | None = Field(default=None, max_length=64)
    # 'detected': the interface reporting this PC's zone; 'pc': Use this PC's timezone; otherwise chosen.
    user_timezone_source: Literal['detected', 'pc', 'chosen'] | None = None
    automatic_memory: bool | None = None
    sensitive_memory: bool | None = None
    share_profile_across_timelines: bool | None = None
    background_activity: bool | None = None
    model_memory_suggestions: bool | None = None
    chat_style: Literal['feed', 'bubbles', 'community', 'retro', 'novel'] | None = None
    chat_sounds: bool | None = None
    review_complete: bool | None = None


class ConnectionUpdate(Input):
    base_url: str = Field(min_length=1, max_length=500)
    model: str = Field(min_length=1, max_length=200)
    api_key: str | None = Field(default=None, max_length=4000)
    max_output_tokens: int = Field(default=800, ge=64, le=128000)
    context_tokens: int = Field(default=16000, ge=1024, le=2000000)
    timeout_seconds: int = Field(default=180, ge=10, le=1800)
    # Optional embedding model on the same connection; empty keeps recall keyword-only.
    embedding_model: str | None = Field(default=None, max_length=200)


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


class LifeSettingsUpdate(Input):
    """Catch-up and background limits (PRD T3–T5). Ceilings are the tested maximums."""
    automatic_events: bool | None = None
    phrase_with_model: bool | None = None
    catch_up_on_return: bool | None = None
    catch_up_max_events: int | None = Field(default=None, ge=0, le=6)
    catch_up_lookback_hours: int | None = Field(default=None, ge=6, le=336)
    return_gap_hours: int | None = Field(default=None, ge=1, le=48)
    background_interval_minutes: int | None = Field(default=None, ge=15, le=1440)
    background_daily_events: int | None = Field(default=None, ge=0, le=8)


class NotificationSettingsUpdate(Input):
    """Desktop notifications (PRD compute and job control). The cap's ceiling is the tested maximum."""
    enabled: bool | None = None
    quiet_start: str | None = Field(default=None, max_length=5)
    quiet_end: str | None = Field(default=None, max_length=5)
    preview: Literal['full', 'name', 'private'] | None = None
    daily_cap: int | None = Field(default=None, ge=1, le=6)
    min_gap_minutes: int | None = Field(default=None, ge=30, le=720)


class NotificationCheck(Input):
    focused: bool = False


class ContextLocation(Input):
    """The user's own city or region, typed by hand (PRD X1). Coordinates are optional."""
    user_place: str = Field(default='', max_length=120)
    user_latitude: float | None = Field(default=None, ge=-90, le=90)
    user_longitude: float | None = Field(default=None, ge=-180, le=180)


class ContextService(Input):
    name: str = Field(min_length=1, max_length=80)
    transport: Literal['stdio', 'http']
    # The program and its arguments, one item each (stdio only).
    command: list[Annotated[str, Field(max_length=1000)]] = Field(default_factory=list, max_length=40)
    url: str = Field(default='', max_length=2000)
    secret: str = Field(default='', max_length=4000)
    # The environment variable (stdio) or header (HTTP) that carries the key.
    secret_name: str = Field(default='', max_length=100)
    clear_secret: bool = False


class ContextLinks(Input):
    read_links: bool


class ContextPreset(Input):
    preset: Literal['parallel', 'exa', 'firecrawl']


class ContextBuiltin(Input):
    kind: Literal['weather']


class ToolArgument(Input):
    source: Literal['place', 'latitude', 'longitude', 'topic', 'date', 'literal', 'url']
    value: str | int | float | bool | None = None


class ToolMapping(Input):
    tool: str = Field(min_length=1, max_length=128)
    arguments: dict[Annotated[str, Field(max_length=100)], ToolArgument] = Field(default_factory=dict, max_length=12)
    run_in: list[Literal['conversation', 'companion_city']] = Field(default_factory=lambda: ['conversation'],
                                                                    min_length=1, max_length=2)


class ToolApproval(Input):
    digest: str = Field(min_length=64, max_length=64)


class ContextLookup(Input):
    """A lookup the user starts from Settings to try a mapping."""
    category: Literal['weather', 'news', 'local_events']
    purpose: Literal['conversation', 'companion_city'] = 'conversation'
    topic: str = Field(default='', max_length=80)


class TimelineFork(Input):
    message_id: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=40000)
    label: str = Field(default='', max_length=80)


class TimelineUpdate(Input):
    label: str | None = Field(default=None, max_length=80)
    clear_draft: bool | None = None


class StudyWorkspace(Input):
    """A Prospero's Study folder or its SQLite database file, opened read-only."""
    path: str = Field(min_length=1, max_length=2000)


class StudyCharacter(StudyWorkspace):
    character_id: str = Field(min_length=1, max_length=100)


class StudyImport(StudyCharacter):
    review_token: str = Field(min_length=64, max_length=64)
