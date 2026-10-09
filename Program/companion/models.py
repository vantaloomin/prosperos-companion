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


class TextingStyle(Input):
    """How the companion texts (companion/texting.py); all off is texting like anyone else."""
    bursts: bool = False
    lowercase: bool = False
    typos: bool = False


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
    # Empty when creating gives them a name that fits (companion/characters.py); a revision needs one.
    name: str = Field(default='', max_length=120)
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
    # How close they start (a closeness stage, 1 = Just met) and how the two of them know each other already.
    starting_closeness: int = Field(default=1, ge=1, le=5)
    history_together: str = Field(default='', max_length=2000)
    # How others see them and how they see themselves (companion/world/perception.py); empty fills itself in.
    seen_as: str = Field(default='', max_length=400)
    sees_self: str = Field(default='', max_length=1200)
    # Empty means neutral about absence. Jealousy, guilt or missing the user are opt-in traits.
    absence_reaction: str = Field(default='', max_length=2000)
    emotional_traits: list[EmotionalTrait] = Field(default_factory=list, max_length=12)
    timezone: str = Field(default='UTC', max_length=64)
    # Structured routine for the life simulation; empty uses a gentle default day.
    schedule: list[RoutineBlock] = Field(default_factory=list, max_length=24)
    # Themes automatic events may draw on (PRD T3).
    life_themes: list[str] = Field(default_factory=list, max_length=20)
    # "MM-DD"; empty picks a date from the companion's id (companion/life/occasions.py).
    texting: TextingStyle = Field(default_factory=TextingStyle)
    birthday: str = Field(default='', pattern=r'^(?:(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]))?$')
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


class PerceptionRequest(Input):
    """The character form as it stands, for suggestions for how others see them and how they see themselves."""
    definition: dict


class FieldDraftRequest(Input):
    """Rewrite one field of a character being edited, in keeping with the rest of it."""
    definition: dict
    field: DraftField
    request: str = Field(default='', max_length=500)


class CharacterSplitRequest(Input):
    """A whole character the user already has, pasted in, to be split into the form's fields."""
    text: str = Field(min_length=1, max_length=40000)
    relationship: Relationship = 'friendship'
    timezone: str = Field(default='UTC', max_length=64)
    emotional_edges: bool = False


class CharacterCardFile(Input):
    """A character card file (JSON or PNG) read into plain text for the paste box; nothing is saved."""
    filename: str = Field(min_length=1, max_length=260)
    data: str = Field(min_length=1, max_length=14_000_000)


class LoreSwitch(Input):
    """Turn an imported lorebook, or one of its entries, on or off (companion/lore.py)."""
    enabled: bool


class SidecarTurn(Input):
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=40000)


class SidecarRequest(Input):
    """One message to the sidecar. It reads the app's context; `definition` is the character form while it is open."""
    message: str = Field(min_length=1, max_length=40000)
    history: list[SidecarTurn] = Field(default_factory=list, max_length=12)
    view: str = Field(default='', max_length=60)
    definition: dict | None = None
    focus_message_id: str | None = Field(default=None, max_length=100)


class MessageEdit(Input):
    text: str = Field(min_length=1, max_length=8000)
    expected_text: str = Field(max_length=40000)


class PromptUpdate(Input):
    text: str = Field(min_length=1, max_length=20000)


class CharacterRevision(Input):
    definition: CharacterDefinition
    note: str = Field(default='', max_length=500)
    expected_version_id: str


class CastDraftRequest(Input):
    """A townsperson the main character has met (companion/cast.py)."""
    key: str = Field(min_length=1, max_length=200)


class Tie(Input):
    """How the new companion and one already here know each other, told once on the form that makes them one."""
    companion_id: str = Field(min_length=1, max_length=100)
    level: int | None = Field(None, ge=1, le=5)
    how: str = Field('', max_length=300)


class CastSwitch(Input):
    """Make that townsperson the main character, with the definition the user reviewed."""
    key: str = Field(min_length=1, max_length=200)
    definition: CharacterDefinition
    ties: list[Tie] = Field(default_factory=list, max_length=200)


class TownSeed(Input):
    """Seed new townsfolk for the companion, or go back to the city's shared ones."""
    fresh: bool


class CastFocus(Input):
    companion_id: str = Field(min_length=1, max_length=64)


class ChatRead(Input):
    thread_id: str = Field(min_length=1, max_length=64)
    seq: int | None = Field(default=None, ge=0)


class StartOverConfirm(Input):
    name: str = Field(max_length=200)


HEX = r'^#[0-9a-fA-F]{6}$'


class Palette(Input):
    """A custom color scheme, as Prospero's Study's custom palette."""
    accent: str = Field(pattern=HEX)
    background: str = Field(pattern=HEX)
    surface: str = Field(pattern=HEX)
    text: str = Field(pattern=HEX)


class OocMarker(Input):
    """An out-of-character marker: a starting word (`open` only, like OOC:) or an opening and closing pair."""
    open: str = Field(min_length=1, max_length=12, pattern=r'\S')
    close: str = Field(default='', max_length=12)


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
    chat_retro_dark: bool | None = None
    color_scheme: Literal['ink', 'slate', 'umber', 'moss', 'wine', 'ash', 'custom'] | None = None
    custom_palette: Palette | None = None
    ask_about_people: bool | None = None
    story_mode: bool | None = None
    show_secret_slips: bool | None = None
    show_moods: bool | None = None
    show_news: bool | None = None
    show_odds: bool | None = None
    # She can ask to remember more (companion/memory/look_back.py).
    recall_more: bool | None = None
    # Out-of-character messages go to the helper (Settings > Chat).
    ooc_to_helper: bool | None = None
    ooc_markers: list[OocMarker] | None = Field(default=None, max_length=12)
    # Automatic backups of every world (companion/auto_backup.py).
    auto_backups: Literal['off', 'daily', 'weekly'] | None = None
    review_complete: bool | None = None
    # The first-run notice: the characters are AI, and the user is 18 or older. Only ever confirmed.
    ai_notice_confirmed: Literal[True] | None = None


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
    text: str = Field(default='', max_length=40000)
    client_id: str = Field(min_length=8, max_length=100)
    # Pictures uploaded for this message (companion/pictures.py).
    picture_ids: list[str] = Field(default_factory=list, max_length=4)
    # The companion whose chat the window shows (conversation.in_focus).
    companion_id: str | None = Field(default=None, max_length=100)

    @model_validator(mode='after')
    def something_to_send(self):
        if not self.text.strip() and not self.picture_ids:
            raise ValueError('Write a message or add a picture.')
        return self


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
    # The companion whose Memories or chat the window shows, when no source message says it.
    companion_id: str | None = Field(default=None, max_length=100)


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
    texts_first: bool | None = None
    texts_daily: int | None = Field(default=None, ge=1, le=6)
    texts_gap_hours: int | None = Field(default=None, ge=1, le=24)
    # Messages sent while the user is away, from all companions together (companion/away.py); 0 for none.
    away_daily: int | None = Field(default=None, ge=0, le=40)
    # 0 sizes the circle by how sociable the companion is (companion/life/circle.py).
    circle_size: int | None = Field(default=None, ge=0, le=12)
    # Storylines from quiet (0) through realistic and dramatic to soap opera (3).
    drama: int | None = Field(default=None, ge=0, le=3)
    # "MM-DD", or empty to forget it (companion/life/occasions.py).
    # Replies wait while the companion is at work or asleep (companion/life/pacing.py).
    paced_replies: bool | None = None
    day_shifts: bool | None = None
    on_her_mind: bool | None = None
    # While you were away (companion/recap.py): days away before a catch-up shows; 0 turns it off.
    recap_after_days: int | None = Field(default=None, ge=0, le=60)
    user_birthday: str | None = Field(default=None, pattern=r'^(?:(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]))?$')


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
    kind: Literal['weather', 'pulse', 'culture']


class ToolArgument(Input):
    source: Literal['place', 'latitude', 'longitude', 'topic', 'date', 'literal', 'url']
    value: str | int | float | bool | None = None


class ToolMapping(Input):
    tool: str = Field(min_length=1, max_length=128)
    arguments: dict[Annotated[str, Field(max_length=100)], ToolArgument] = Field(default_factory=dict, max_length=12)
    run_in: list[Literal['conversation', 'companion_city', 'ambient']] = Field(
        default_factory=lambda: ['conversation'], min_length=1, max_length=3)


class ToolApproval(Input):
    digest: str = Field(min_length=64, max_length=64)


class ContextLookup(Input):
    """A lookup the user starts from Settings to try a mapping."""
    category: Literal['weather', 'news', 'local_events']
    purpose: Literal['conversation', 'companion_city'] = 'conversation'
    topic: str = Field(default='', max_length=80)


class TimelineFork(Input):
    """Branch from here without text; Edit from here (the user's own messages) with the edited words."""
    message_id: str = Field(min_length=1, max_length=64)
    text: str | None = Field(default=None, min_length=1, max_length=40000)
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


Gender = Literal['woman', 'man', 'nonbinary', '']
Birthday = Annotated[str, Field(pattern=r'^(?:(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]))?$')]


class PersonaInput(Input):
    """Who the user is in a persona's worlds (companion/worlds.py). Only the user says this; blanks stay blank."""
    name: str | None = Field(None, max_length=80)
    gender: Gender | None = None
    age: int | None = Field(None, ge=18, le=120)
    about: str | None = Field(None, max_length=2000)
    birthday: Birthday | None = None


class WorldChange(Input):
    """Rename a world, or give it to another persona."""
    name: str | None = Field(None, max_length=80)
    persona_id: str | None = Field(None, min_length=1, max_length=100)


class Become(Input):
    """Become a townsperson (companion/worlds.py): the key of someone met around town."""
    key: str = Field(min_length=1, max_length=200)


class NewWorld(Input):
    """A new world: for the active persona and in the current city unless these say otherwise."""
    persona_id: str | None = Field(None, min_length=1, max_length=100)
    name: str | None = Field(None, max_length=80)
    city_id: str | None = Field(None, min_length=1, max_length=120)


class RecapRead(Input):
    """The catch-up the user read, by the message it followed (companion/recap.py)."""
    since: str = Field(min_length=1, max_length=40)
