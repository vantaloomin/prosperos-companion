"""SQLite access adapted from prosperos-study server/database.py at bbcbde4.

Opening a database checks the Companion identity marker first: a Study database or any
other non-empty SQLite file is refused rather than silently gaining Companion tables.
"""
import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from uuid import uuid4

from companion.clock import AppClock, Clock, stamp
from companion.errors import DomainError, require
from companion.identity import APP_ID, SCHEMA_VERSION, VERSION, database_path

SCHEMA = Path(__file__).with_name('schema.sql').read_text(encoding='utf-8')
# The world a piece of work belongs to (companion/worlds.py). A request, a background tick and every task they
# start read and write the world they began in, even when the user switches worlds while they wait on a model.
PINNED: ContextVar[tuple[int, Path] | None] = ContextVar('companion_world', default=None)


def identifier() -> str:
    return uuid4().hex


def encode(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def decode(value: str | None):
    return None if value is None else json.loads(value)


class Database:
    def __init__(self, path: str | Path | None = None, clock: Clock | None = None):
        self.active = Path(path or database_path())
        # The folder of the first world: what every world shares (downloaded models, worlds.json) lives there.
        # Another world's database is in its own folder below it (companion/worlds.py), and `use` switches to it.
        self.root = self.active.parent
        self.home = self.active
        self.world: str | None = None  # The open world's id, set by companion/worlds.py.
        # Tests hand in a FixedClock; debug time (companion/debug_time.py) shifts the app clock wrapped around it.
        self.clock = clock if isinstance(clock, AppClock) else AppClock(clock)
        self.open()

    @property
    def path(self) -> Path:
        """The open world's database, or the one the work under way was pinned to."""
        pinned = PINNED.get()
        return pinned[1] if pinned and pinned[0] == id(self) else self.active

    @contextmanager
    def pin(self):
        """Keep this work (and every task it starts) in the world open now, whatever is opened meanwhile."""
        token = PINNED.set((id(self), self.path))
        try:
            yield
        finally:
            PINNED.reset(token)

    def use(self, path: str | Path):
        """Every part of the app reads and writes through this object, so pointing it at another world's
        database moves all of them there; each connection opens the file anew. Work already pinned to the
        world being left stays there; the work doing the switch follows it."""
        previous, pinned = self.active, PINNED.get()
        self.active = Path(path)
        if pinned and pinned[0] == id(self):
            PINNED.set((id(self), self.active))
        try:
            self.open()
        except BaseException:
            self.active = previous
            if pinned and pinned[0] == id(self):
                PINNED.set(pinned)
            raise

    def open(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        inspect_existing(self.path)
        if upgrade_needed(self.path):
            from companion import upgrade
            upgrade.run(self.path, self.now())
        with self.connect(write=True) as connection:
            initialize(connection, self.now())
        from companion import debug_time
        from companion.world import turnover
        debug_time.load(self)
        turnover.load(self)

    def now(self) -> str:
        return stamp(self.clock.now())

    @contextmanager
    def connect(self, write: bool = False):
        connection = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA journal_mode=WAL')
        try:
            connection.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()


# Columns added after a table first shipped. CREATE TABLE IF NOT EXISTS leaves an existing table
# alone, so a workspace created earlier gains them here.
ADDED_COLUMNS = (
    ('life_settings', 'phrase_with_model', 'INTEGER NOT NULL DEFAULT 1 CHECK (phrase_with_model IN (0, 1))'),
    ('connection', 'embedding_model', 'TEXT'),
    ('memory_jobs', 'model_status', 'TEXT'),
    ('workspace_settings', 'model_memory_suggestions',
     'INTEGER NOT NULL DEFAULT 0 CHECK (model_memory_suggestions IN (0, 1))'),
    ('memories', 'subject_key', "TEXT NOT NULL DEFAULT ''"),
    ('memories', 'origin', "TEXT NOT NULL DEFAULT 'user' CHECK (origin IN ('user', 'automatic', 'suggestion'))"),
    ('memories', 'ended_by_id', 'TEXT'),
    ('memories', 'merged_into_id', 'TEXT'),
    ('memories', 'dates_uncertain', 'INTEGER NOT NULL DEFAULT 0 CHECK (dates_uncertain IN (0, 1))'),
    ('timelines', 'label', "TEXT NOT NULL DEFAULT ''"),
    ('timelines', 'fork_message_id', 'TEXT'),
    ('timelines', 'forked_at', 'TEXT'),
    ('timelines', 'draft', 'TEXT'),
    ('timelines', 'activated_at', 'TEXT'),
    ('messages', 'origin_id', 'TEXT'),
    ('workspace_settings', 'user_timezone_source',
     "TEXT NOT NULL DEFAULT 'default' CHECK (user_timezone_source IN ('default', 'pc', 'chosen'))"),
    ('context_settings', 'read_links', 'INTEGER NOT NULL DEFAULT 1 CHECK (read_links IN (0, 1))'),
    ('workspace_settings', 'chat_style',
     "TEXT NOT NULL DEFAULT 'feed' CHECK (chat_style IN ('feed', 'bubbles', 'community', 'retro', 'novel'))"),
    ('workspace_settings', 'chat_sounds', 'INTEGER NOT NULL DEFAULT 0 CHECK (chat_sounds IN (0, 1))'),
    ('life_settings', 'texts_first', 'INTEGER NOT NULL DEFAULT 1 CHECK (texts_first IN (0, 1))'),
    ('life_settings', 'texts_daily', 'INTEGER NOT NULL DEFAULT 2'),
    ('life_settings', 'texts_gap_hours', 'INTEGER NOT NULL DEFAULT 3'),
    ('life_settings', 'circle_size', 'INTEGER NOT NULL DEFAULT 0'),
    ('life_settings', 'drama', 'INTEGER NOT NULL DEFAULT 1'),
    ('life_settings', 'user_birthday', "TEXT NOT NULL DEFAULT ''"),
    ('life_settings', 'paced_replies', 'INTEGER NOT NULL DEFAULT 1'),
    ('life_settings', 'day_shifts', 'INTEGER NOT NULL DEFAULT 1 CHECK (day_shifts IN (0, 1))'),
    # On their mind (companion/life/thoughts.py): one private thought a day, shown folded on Today.
    # Who passed a secret on (companion/secrets.py): a person key or 'user'; NULL for those it started with.
    ('knowledge_holders', 'told_by', 'TEXT'),
    # Group chat moods (companion/moods.py): whether someone furious may walk out of this group.
    ('group_chats', 'walk_out', 'INTEGER NOT NULL DEFAULT 0 CHECK (walk_out IN (0, 1))'),
    ('life_settings', 'on_her_mind', 'INTEGER NOT NULL DEFAULT 1 CHECK (on_her_mind IN (0, 1))'),
    ('messages', 'held_until', 'TEXT'),
    ('messages', 'held_line', 'TEXT'),
    ('messages', 'held_notified', 'TEXT'),
    ('image_settings', 'chat_photos', 'INTEGER NOT NULL DEFAULT 1 CHECK (chat_photos IN (0, 1))'),
    ('image_settings', 'unprompted_photos', 'INTEGER NOT NULL DEFAULT 1 CHECK (unprompted_photos IN (0, 1))'),
    ('memories', 'person_id', 'TEXT'),
    ('workspace_settings', 'ask_about_people', 'INTEGER NOT NULL DEFAULT 1 CHECK (ask_about_people IN (0, 1))'),
    # A full reply after a holding text, dropped unseen because the user wrote again first (life/pacing.py).
    ('messages', 'superseded_at', 'TEXT'),
    ('workspace_settings', 'chat_retro_dark', 'INTEGER NOT NULL DEFAULT 0 CHECK (chat_retro_dark IN (0, 1))'),
    ('workspace_settings', 'story_mode', 'INTEGER NOT NULL DEFAULT 0 CHECK (story_mode IN (0, 1))'),
    # Launch buttons (companion/launcher.py): start the local programs in use with the Companion.
    ('workspace_settings', 'auto_launch', 'INTEGER NOT NULL DEFAULT 0 CHECK (auto_launch IN (0, 1))'),
    # Color schemes from Prospero's Study (Settings > General > Appearance).
    ('workspace_settings', 'color_scheme', "TEXT NOT NULL DEFAULT 'ink' CHECK (color_scheme IN "
     "('ink', 'slate', 'umber', 'moss', 'wine', 'ash', 'custom'))"),
    ('workspace_settings', 'custom_palette', "TEXT NOT NULL DEFAULT ''"),
    # Onboarding portraits (lora/portraits.py): a set whose later pictures follow the profile picture,
    # and the kept picture shown as the companion's profile picture.
    ('lora_generations', 'kind', "TEXT NOT NULL DEFAULT 'dataset' CHECK (kind IN ('dataset', 'portraits'))"),
    ('lora_gen_images', 'follows', 'INTEGER'),
    ('companions', 'portrait_reference_id', 'TEXT'),
    # Texts first became on by default; a workspace from before that is switched on once (see initialize).
    ('life_settings', 'texts_first_on_by_default', 'INTEGER NOT NULL DEFAULT 0'),
    # Memory is opt-out: every workspace gets automatic, sensitive and model memory turned on once (Vanta,
    # 2026-10-07: users can't be relied on to approve suggestions); turning them off afterwards sticks.
    ('workspace_settings', 'memory_on_by_default', 'INTEGER NOT NULL DEFAULT 0'),
    # Switching the main character (companion/cast.py): the townsperson a companion was made from, and
    # when they last stepped back from slot 1.
    ('companions', 'townsfolk_key', 'TEXT'),
    ('companions', 'stepped_back_at', 'TEXT'),
    # Townsfolk of the companion's own, once the user seeds new ones (companion/cast.py); empty keeps the
    # city's shared townsfolk.
    ('companions', 'town_seed', "TEXT NOT NULL DEFAULT ''"),
    # The routine slot still going when the life cursor last moved (companion/life/simulation.py).
    ('life_cursors', 'open_slot', 'TEXT'),
    ('prompt_overrides', 'default_text', 'TEXT'),
    # The user switched an image API backend to take NSFW requests too (images/backends.py).
    ('image_backends', 'allows_nsfw', 'INTEGER NOT NULL DEFAULT 0 CHECK (allows_nsfw IN (0, 1))'),
    # A closeness stage the user set, a ceiling and opt-in gentle cooling (memory/closeness.py).
    ('closeness_settings', 'head_start', 'INTEGER'),
    ('closeness_settings', 'set_on', 'TEXT'),
    ('closeness_settings', 'ceiling_level', 'INTEGER CHECK (ceiling_level BETWEEN 1 AND 5)'),
    ('closeness_settings', 'cooling_since', 'TEXT'),
    ('phone_settings', 'lan_enabled', 'INTEGER NOT NULL DEFAULT 0 CHECK (lan_enabled IN (0, 1))'),
    # One shared allowance for messages sent while the user is away, across every companion (companion/away.py).
    ('life_settings', 'away_daily', 'INTEGER NOT NULL DEFAULT 6'),
    # A group reply a secret check touched (companion/secrets.py): 'redrafted', 'revealed' or 'held'.
    ('group_messages', 'guard', 'TEXT'),
    ('workspace_settings', 'show_secret_slips', 'INTEGER NOT NULL DEFAULT 1 CHECK (show_secret_slips IN (0, 1))'),
    # Hidden values: moods and who heard the news stay unseen unless the user turns them on.
    ('workspace_settings', 'show_moods', 'INTEGER NOT NULL DEFAULT 0 CHECK (show_moods IN (0, 1))'),
    ('workspace_settings', 'show_news', 'INTEGER NOT NULL DEFAULT 0 CHECK (show_news IN (0, 1))'),
    ('workspace_settings', 'show_odds', 'INTEGER NOT NULL DEFAULT 0 CHECK (show_odds IN (0, 1))'),
    # The adult side of life (companion/world/intimacy.py): off unless the user turns it on in Settings > Realism.
    ('workspace_settings', 'adult_side', 'INTEGER NOT NULL DEFAULT 0 CHECK (adult_side IN (0, 1))'),
    ('workspace_settings', 'show_adult_side', 'INTEGER NOT NULL DEFAULT 0 CHECK (show_adult_side IN (0, 1))'),
    # Record model calls (companion/model_calls.py): off unless the user turns it on in Settings > Debug.
    ('workspace_settings', 'record_model_calls', 'INTEGER NOT NULL DEFAULT 0 CHECK (record_model_calls IN (0, 1))'),
    # 100% Matchlight matches (Settings > Debug): every like is liked back. Off unless the user turns it on.
    ('workspace_settings', 'debug_all_matches', 'INTEGER NOT NULL DEFAULT 0 CHECK (debug_all_matches IN (0, 1))'),
    # Everyday events became automatic ("the world exists outside of User", Vanta 2026-10-08); a workspace
    # from before that is switched on once (see initialize), and turning it off afterwards sticks.
    ('life_settings', 'events_on_by_default', 'INTEGER NOT NULL DEFAULT 0'),
    # A moment that keeps coming up becomes a running joke on its own; one the user removed stays out.
    ('closeness_jokes', 'removed', 'INTEGER NOT NULL DEFAULT 0 CHECK (removed IN (0, 1))'),
    # How a companion carries a mark about something the user did, told to them as "you" (companion/consequences.py).
    ('marks', 'told', 'TEXT'),
    # The names and mark holders an outcome was decided with, so changing how it went can redo its marks.
    ('consequences', 'names', 'TEXT'),
    ('consequences', 'holders', 'TEXT'),
    # When the user read the one-time notice that the characters are AI and confirmed they are 18 or older
    # (companion/workspace.py); the app asks once, before anything else, until then.
    ('workspace_settings', 'ai_notice_at', 'TEXT'),
    # Automatic backups of every world (companion/auto_backup.py): on by default, once a day.
    ('workspace_settings', 'auto_backups',
     "TEXT NOT NULL DEFAULT 'daily' CHECK (auto_backups IN ('off', 'daily', 'weekly'))"),
    # While you were away (companion/recap.py): days without a message before a catch-up shows; 0 is off.
    ('life_settings', 'recap_after_days', 'INTEGER NOT NULL DEFAULT 3'),
    # Become a townsperson (companion/worlds.py): the townsperson the user is in this world, and their town.
    ('persona', 'townsfolk_key', "TEXT NOT NULL DEFAULT ''"),
    ('persona', 'town_seed', "TEXT NOT NULL DEFAULT ''"),
    # They can ask to remember more (companion/memory/look_back.py).
    ('workspace_settings', 'recall_more', 'INTEGER NOT NULL DEFAULT 1 CHECK (recall_more IN (0, 1))'),
    # Out-of-character messages go to the helper (the composer and Settings > General): the switch and the markers.
    ('workspace_settings', 'ooc_to_helper', 'INTEGER NOT NULL DEFAULT 1 CHECK (ooc_to_helper IN (0, 1))'),
    ('workspace_settings', 'ooc_markers', "TEXT NOT NULL DEFAULT ''"),
    # A status line the user set for a companion, and when (companion/life/status.py); empty lets the app write it.
    ('companions', 'status_text', "TEXT NOT NULL DEFAULT ''"),
    ('companions', 'status_set_at', 'TEXT'),
    # Light or dark (Settings > General > Appearance): 'system' matches the computer (Paper or Ink), 'paper' is the light
    # profile and 'scheme' uses color_scheme. Workspaces from before keep the scheme they saved, so the column comes in
    # as 'scheme' here while new workspaces start on 'system' (schema.sql).
    ('workspace_settings', 'theme', "TEXT NOT NULL DEFAULT 'scheme' CHECK (theme IN ('system', 'scheme', 'paper'))"),
    # A message brought in from an old chat file (companion/imports/chats.py): older history, never new talk.
    ('messages', 'import_id', 'TEXT'),
    # A world lorebook that belongs to one of the user's cities (a Marinara world map's notes, companion/lore.py):
    # it comes along into new worlds in that city and goes when the city is deleted.
    ('lore_books', 'city_id', 'TEXT'),
    # When a lore entry applies besides its keywords (companion/lore_moments.py), as a JSON list of conditions; NULL
    # until the user sets one, while the app reads one from its keywords.
    ('lore_entries', 'moment', 'TEXT'),
    # Home upkeep (companion/life/upkeep.py, Settings > Realism > Home life): 0 off, 1 light, 2 true to life, 3 messy.
    ('life_settings', 'upkeep_realism', 'INTEGER NOT NULL DEFAULT 2 CHECK (upkeep_realism BETWEEN 0 AND 3)'),
    # Looks that change (companion/life/grooming.py): how often, from never (0) to often (3), set on the Realism tab.
    ('life_settings', 'looks_realism', 'INTEGER NOT NULL DEFAULT 2 CHECK (looks_realism BETWEEN 0 AND 3)'),
    # The numbers behind home life (upkeep meters and the like), under Settings > Realism > Hidden values.
    ('workspace_settings', 'show_home_meters', 'INTEGER NOT NULL DEFAULT 0 CHECK (show_home_meters IN (0, 1))'),
    # Pets with lives of their own (companion/life/pets.py), on Settings > Realism > Around the home: how often pets
    # fall ill (0 off, 1 light, 2 true to life, 3 dramatic) and whether they can die.
    ('life_settings', 'pets_realism', 'INTEGER NOT NULL DEFAULT 2 CHECK (pets_realism BETWEEN 0 AND 3)'),
    ('life_settings', 'pets_can_die', 'INTEGER NOT NULL DEFAULT 1 CHECK (pets_can_die IN (0, 1))'),
    # The pets on the user's persona (companion/worlds.py), as JSON: the user's own, given lives by pets.py.
    ('persona', 'pets', "TEXT NOT NULL DEFAULT '[]'"),
    # Kitchen and food (companion/life/kitchen.py, Settings > Realism > Around the home): 0 off, 1 light, 2 true to life,
    # 3 dramatic.
    ('life_settings', 'kitchen_realism', 'INTEGER NOT NULL DEFAULT 2 CHECK (kitchen_realism BETWEEN 0 AND 3)'),
    # Life admin calendar (companion/life/admin.py), on the home features' shared scale: 0 off, 1 light, 2 true to
    # life, 3 dramatic (Settings > Realism > Around the home).
    ('life_settings', 'admin_realism', 'INTEGER NOT NULL DEFAULT 2 CHECK (admin_realism BETWEEN 0 AND 3)'),
    # Work life (companion/life/work.py, Settings > Realism > Their days): 0 off, 1 steady, 2 true to life, 3 dramatic.
    ('life_settings', 'work_realism', 'INTEGER NOT NULL DEFAULT 2 CHECK (work_realism BETWEEN 0 AND 3)'),
    # Group chat guests (companion/group_guests.py): the member who knows a guest (their host), who they are to them
    # ("Sally's sister"), and whether the user kept them so they never slip out. NULL host: a member.
    ('group_members', 'host', 'TEXT'),
    ('group_members', 'relation', "TEXT NOT NULL DEFAULT ''"),
    ('group_members', 'kept', 'INTEGER NOT NULL DEFAULT 0 CHECK (kept IN (0, 1))'),
    # How often guests drop into group chats (Settings > Realism): 0 never on their own, 1 now and then, 2 true to
    # life, 3 often.
    ('life_settings', 'guests_realism', 'INTEGER NOT NULL DEFAULT 2 CHECK (guests_realism BETWEEN 0 AND 3)'),
    # Who brought a guest in: the member's key, or 'user' when the user added them (only pull-ins count toward the gap).
    ('group_members', 'brought_by', 'TEXT'),
    # Reading, watching and listening (companion/life/media.py, Settings > Realism > Their days): 0 off, 1 light,
    # 2 true to life, 3 dramatic.
    ('life_settings', 'media_realism', 'INTEGER NOT NULL DEFAULT 2 CHECK (media_realism BETWEEN 0 AND 3)'),
    # Hobbies that progress (companion/life/hobbies.py, Settings > Realism > Their days): 0 off, 1 light, 2 true to
    # life, 3 dramatic.
    ('life_settings', 'hobbies_realism', 'INTEGER NOT NULL DEFAULT 2 CHECK (hobbies_realism BETWEEN 0 AND 3)'),
    # Matchlight's Undo (companion/dating.py): the person just answered, until it is undone or anything else changes.
    ('dating_profile', 'last_answer', "TEXT NOT NULL DEFAULT ''"),
    # Where you live in this world (companion/life/where.py): a city id and a neighbourhood id in it.
    ('persona', 'home_city_id', "TEXT NOT NULL DEFAULT ''"),
    ('persona', 'home_neighbourhood', "TEXT NOT NULL DEFAULT ''"),
    # Getting together (companion/life/together.py, Settings > Realism): how often companions suggest meeting up,
    # invite the user over and drop by, 0 never on their own, 1 light, 2 true to life, 3 often.
    ('life_settings', 'together_realism', 'INTEGER NOT NULL DEFAULT 2 CHECK (together_realism BETWEEN 0 AND 3)'),
    # Long distance (companion/life/long_distance.py): a trip that is a weekend visit with the user, 'to-you' (they come
    # to stay with the user) or 'host' (the user comes to stay with them); the message that asked for it, the memory it
    # left, and when the user called it off.
    ('trips', 'visit', "TEXT NOT NULL DEFAULT '' CHECK (visit IN ('', 'to-you', 'host'))"),
    ('trips', 'message_id', 'TEXT'),
    ('trips', 'memory_id', 'TEXT'),
    ('trips', 'cancelled_at', 'TEXT'),
    # Rough patches (companion/life/rough_patches.py, Settings > Realism): 0 off, 1 easy (fades overnight), 2 true to
    # life (an apology, a gesture or a few calm days), 3 dramatic (lingers until you make up).
    ('life_settings', 'rough_patches_realism', 'INTEGER NOT NULL DEFAULT 2 CHECK (rough_patches_realism BETWEEN 0 AND 3)'),
    # Next steps (companion/life/steps.py, Settings > Realism): how soon companions bring up the next step, 0 only when
    # the user does, 1 slow, 2 true to life, 3 fast; and whether a close friend can fall for the user.
    ('life_settings', 'steps_pace', 'INTEGER NOT NULL DEFAULT 2 CHECK (steps_pace BETWEEN 0 AND 3)'),
    ('life_settings', 'friends_fall', 'INTEGER NOT NULL DEFAULT 1 CHECK (friends_fall IN (0, 1))'),
    # Their own love life (companion/life/love_life.py, Settings > Realism): 0 nothing new, 1 quiet, 2 true to life,
    # 3 lots going on.
    ('life_settings', 'love_life', 'INTEGER NOT NULL DEFAULT 2 CHECK (love_life BETWEEN 0 AND 3)'),
    # Breaks and breakups (companion/life/breakups.py, Settings > Realism): whether strained rough patches can lead to a
    # break and a breakup (or a falling out with a friend). On for real life and drama, off for an easy life.
    ('life_settings', 'breakups', 'INTEGER NOT NULL DEFAULT 1 CHECK (breakups IN (0, 1))'),
    # Sharing a home (companion/life/moving_in.py): the shared home a moving-in row belongs to, by the id of the row
    # that set it up. A second romance moving into it has the first one's household; NULL is a household of its own.
    ('moving_in', 'household', 'TEXT'),
    # Life's big turns (companion/life/big_turns.py, Settings > Realism > Their days): how often life chapters come,
    # 0 off, 1 gentle (good turns only), 2 true to life, 3 eventful. The town's turnover follows it too
    # (companion/world/turnover.py).
    ('life_settings', 'life_turns', 'INTEGER NOT NULL DEFAULT 2 CHECK (life_turns BETWEEN 0 AND 3)'),
    # A big turn's stages (companion/life/big_turns.py): what stage it is at, when the next one comes, and its plan.
    ('life_chapters', 'details', "TEXT NOT NULL DEFAULT '{}'"),
    # A fork's copy of a moving-in row (companion/life/moving_in.py `copy`): the row it was first copied from, so a home
    # set up before the fork stays one household with those who moved in on other timelines; NULL for the original.
    ('moving_in', 'origin', 'TEXT'),
    # Births and growing families (companion/life/families.py, Settings > Realism): how often babies arrive in the
    # circle and the town, 0 none, 1 now and then, 2 true to life, 3 lots.
    ('life_settings', 'growing_families', 'INTEGER NOT NULL DEFAULT 2 CHECK (growing_families BETWEEN 0 AND 3)'),
    # Loss and grief (companion/life/loss.py, Settings > Realism > Their days): whether people can pass away (off on
    # every preset) and how often, 0 rare, 1 now and then, 2 true to life, 3 often. The town follows both
    # (companion/world/turnover.py).
    ('life_settings', 'people_pass_away', 'INTEGER NOT NULL DEFAULT 0 CHECK (people_pass_away IN (0, 1))'),
    ('life_settings', 'loss', 'INTEGER NOT NULL DEFAULT 2 CHECK (loss BETWEEN 0 AND 3)'),
    # Added once (v0.15) to set the Loss slider by the world's preset (`UPGRADE_LOSS`); nothing reads it.
    ('life_settings', 'loss_by_preset', 'INTEGER NOT NULL DEFAULT 1'),
    # Companions' own babies (companion/life/own_family.py): whose child this is. '' someone in the circle's (v0.14),
    # 'companion' the companion's own with their partner (`parent_id`).
    ('circle_children', 'whose', "TEXT NOT NULL DEFAULT ''"),
    # Our child (companion/life/our_child.py, Settings > Realism > Their days): how much family life shapes their
    # days, 0 easy kids (only the good days), 1 gentle, 2 true to life, 3 true-to-life chaos.
    ('life_settings', 'family_life', 'INTEGER NOT NULL DEFAULT 2 CHECK (family_life BETWEEN 0 AND 3)'),
    # When families change (companion/life/custody.py): where the pair's children live after a breakup, when the user
    # set it ('with_them', 'shared' or 'with_you'; NULL leaves it to the engine's family:custody).
    ('our_family', 'custody', "TEXT CHECK (custody IS NULL OR custody IN ('with_them', 'shared', 'with_you'))"),
    # The breakup that choice was made in: it holds only while that one stands (not after getting back together and
    # splitting again).
    ('our_family', 'custody_for', 'TEXT'),
    # Lifespans (companion/world/lifespans.py): the kind and How long they live the user picked on a child's card ('' and
    # NULL: the app's pick, from their parents' kinds; lifespan 0: they don't age).
    ('circle_children', 'own_kind', "TEXT NOT NULL DEFAULT ''"),
    ('circle_children', 'lifespan', 'INTEGER'),
    # The user's kind and How long they live, picked on the Persona page (companion/worlds.py; '' and NULL: read from
    # their own words; lifespan 0: they don't age).
    ('persona', 'kind', "TEXT NOT NULL DEFAULT ''"),
    ('persona', 'lifespan', 'INTEGER'),
    # Memes without a picture model (companion/images/meme_pictures.py, gifs.py): where a meme's picture came from
    # ('' an image model, 'template' a picture on this computer, 'gif' a reaction GIF), the template picture
    # ({id, width, height, boxes}) and the GIF ({url, width, height, page, tag}).
    ('chat_photos', 'meme_source', "TEXT NOT NULL DEFAULT ''"),
    ('chat_photos', 'meme_picture', 'TEXT'),
    ('chat_photos', 'gif', 'TEXT'),
    # Whether classic meme formats are downloaded from memegen.link the first time memes are sent (Settings > Images).
    ('image_settings', 'meme_formats', 'INTEGER NOT NULL DEFAULT 1 CHECK (meme_formats IN (0, 1))'),
    # Memes and GIFs (Settings > Realism > Their days): 0 never, 1 now and then, 2 true to life, 3 often.
    ('life_settings', 'memes_realism', 'INTEGER NOT NULL DEFAULT 2 CHECK (memes_realism BETWEEN 0 AND 3)'),
    # Inner voice (Settings > Realism > Their days, companion/life/narrator.py): how much of what is on their mind
    # the Watching page tells, 0 just what happened, 1 a few thoughts, 2 true to life, 3 everything on their mind.
    ('life_settings', 'inner_voice', 'INTEGER NOT NULL DEFAULT 2 CHECK (inner_voice BETWEEN 0 AND 3)'),
    # Words that fit the era (companion/world/era_words.py, Settings > General > Appearance): on unless turned off.
    ('workspace_settings', 'period_words', 'INTEGER NOT NULL DEFAULT 1 CHECK (period_words IN (0, 1))'),
    # Their look in chat (companion/their_look.py, Settings > Realism > Their days): 0 off, 1 steady, 2 true to life,
    # 3 expressive; and Settings > General > Appearance's "Keep my colours everywhere".
    ('life_settings', 'their_look', 'INTEGER NOT NULL DEFAULT 2 CHECK (their_look BETWEEN 0 AND 3)'),
    ('workspace_settings', 'keep_my_colours', 'INTEGER NOT NULL DEFAULT 0 CHECK (keep_my_colours IN (0, 1))'),
    # Companions who already have kids (companion/life/kids.py): a child of theirs the user added by hand, kept when
    # the engine's kids:has is changed.
    ('circle_children', 'by_hand', 'INTEGER NOT NULL DEFAULT 0 CHECK (by_hand IN (0, 1))'),
    # Waking them (companion/life/waking.py, Settings > Realism > Their days): how fast being woken wears thin, 0 they
    # never mind, 1 easygoing, 2 true to life, 3 it wears thin fast.
    ('life_settings', 'waking_realism', 'INTEGER NOT NULL DEFAULT 2 CHECK (waking_realism BETWEEN 0 AND 3)'),
)

# CHECK constraints widened after a table first shipped, as (table, text the current definition
# contains). SQLite cannot alter a CHECK, so an older table is copied into the current definition.
WIDENED_CHECKS = (
    ('notification_deliveries', "'message')"),
    ('memory_vectors', "'storyline'))"),
    # Work life's late nights on the shared calendar (companion/life/work.py).
    ('life_admin', "'looks', 'work'"),
    # Exams for a course they went back to school for (companion/life/big_turns.py).
    ('life_admin', "'work', 'school'"),
    # Check-ups for a long-term condition and a parent's appointments (companion/life/health_turns.py).
    ('life_admin', "'school', 'health')"),
    # Starting a family, the step beside the romance ladder (companion/life/parenthood.py).
    ('relationship_steps', "'friendship', 'parenthood')"),
    # The pair's own child, born or home (companion/life/expecting.py).
    ('circle_children', "'friend', 'ours')"),
)


def schema_digest() -> str:
    """Changes whenever schema.sql or ADDED_COLUMNS does, so an upgrade is noticed without a version bump."""
    return hashlib.sha256((SCHEMA + repr(ADDED_COLUMNS) + repr(WIDENED_CHECKS)).encode('utf-8')).hexdigest()


def initialize(connection, timestamp: str):
    claim_identity(connection)
    connection.executescript(SCHEMA)
    add_columns(connection)
    widen_context_categories(connection)
    widen_checks(connection)
    connection.execute('CREATE INDEX IF NOT EXISTS life_admin_day ON life_admin(timeline_id, status, local_date)')
    connection.execute('CREATE INDEX IF NOT EXISTS relationship_steps_pair ON relationship_steps(timeline_id, other, ladder)')
    connection.execute('CREATE INDEX IF NOT EXISTS circle_children_timeline ON circle_children(timeline_id, status, born_on)')
    connection.execute('CREATE INDEX IF NOT EXISTS circle_children_parent ON circle_children(parent_id)')
    connection.execute('CREATE INDEX IF NOT EXISTS messages_origin ON messages(origin_id)')
    connection.execute('CREATE INDEX IF NOT EXISTS memories_person ON memories(person_id)')
    backfill_subject_keys(connection)
    from companion.imports.characters import card_sliders_upgrade
    card_sliders_upgrade(connection)
    from companion.text_models import adopt_legacy, split_recall
    adopt_legacy(connection, timestamp)
    split_recall(connection, timestamp)
    for table in ('workspace_settings', 'life_settings', 'image_settings', 'context_settings', 'lora_settings',
                  'notification_settings', 'phone_settings', 'builtin_recall', 'voice_settings'):
        connection.execute(f'INSERT OR IGNORE INTO {table} (id, updated_at) VALUES (1, ?)', (timestamp,))
    connection.execute('UPDATE life_settings SET texts_first=1, texts_first_on_by_default=1 '
                       'WHERE texts_first_on_by_default=0')
    connection.execute('UPDATE life_settings SET automatic_events=1, events_on_by_default=1 WHERE events_on_by_default=0')
    connection.execute('UPDATE workspace_settings SET automatic_memory=1, sensitive_memory=1, '
                       'model_memory_suggestions=1, memory_on_by_default=1 WHERE memory_on_by_default=0')
    from companion.life.outings import reword_memories
    reword_memories(connection, timestamp)
    connection.executemany('INSERT OR REPLACE INTO app_identity (key, value) VALUES (?, ?)',
                           (('schema_version', str(SCHEMA_VERSION)), ('schema_digest', schema_digest()),
                            ('app_version', VERSION)))


def stored_identity(path: Path) -> dict:
    connection = sqlite3.connect(f'{path.resolve().as_uri()}?mode=ro', uri=True)
    try:
        return dict(connection.execute('SELECT key, value FROM app_identity').fetchall())
    finally:
        connection.close()


def upgrade_needed(path: Path) -> bool:
    """An existing workspace whose schema differs from this version's goes through the safe upgrade."""
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        return stored_identity(path).get('schema_digest') != schema_digest()
    except sqlite3.DatabaseError:
        return False  # An empty database without an identity yet.


# Settings > Realism's sliders and switches from v0.13 on a world from before them, as its preset sets them
# (src/features/settings/presetChoices.ts), told apart by its drama: an easy life keeps breakups and friends falling for
# the user off, and a dramatic one stays dramatic. Any other world takes the columns' defaults (a real life).
UPGRADE_REALISM = {0: {'rough_patches_realism': 1, 'steps_pace': 1, 'love_life': 1, 'friends_fall': 0, 'breakups': 0},
                   3: {'rough_patches_realism': 3, 'steps_pace': 3, 'love_life': 3}}
# Life's big turns from v0.14 the same way: an easy life gets the gentle level (good turns only), a dramatic one eventful.
UPGRADE_TURNS = {0: {'life_turns': 1}, 3: {'life_turns': 3}}
# Growing families (v0.14) the same way: an easy life has babies now and then, a dramatic one lots.
UPGRADE_FAMILIES = {0: {'growing_families': 1}, 3: {'growing_families': 3}}
# The Loss slider (v0.15) the same way: an easy life rare, a dramatic one often, only while the switch is off and the
# slider still at its default, so a level the user chose stays.
UPGRADE_LOSS = {0: {'loss': 0}, 3: {'loss': 3}}
# Family life (v0.15) the same way: an easy life has easy kids, a dramatic one true-to-life chaos.
UPGRADE_FAMILY_LIFE = {0: {'family_life': 0}, 3: {'family_life': 3}}
# Memes and GIFs and Inner voice (v0.16) the same way: an easy life now and then and a few thoughts, a dramatic one
# often and everything on their mind.
UPGRADE_DREAMS = {0: {'memes_realism': 1, 'inner_voice': 1}, 3: {'memes_realism': 3, 'inner_voice': 3}}
# Their look in chat (v1.1) the same way: an easy life keeps it steady, a dramatic one expressive.
UPGRADE_LOOK = {0: {'their_look': 1}, 3: {'their_look': 3}}
# "I pull the strings" has a real life's drama but no paced replies, and hears everything on their mind.
STRINGS_VOICE = {1: {'inner_voice': 3}}


def add_columns(connection):
    added = set()
    for table, column, definition in ADDED_COLUMNS:
        existing = {row[1] for row in connection.execute(f'PRAGMA table_info({table})')}
        if column not in existing:
            connection.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')
            added.add((table, column))
    for column, upgrade in (('breakups', UPGRADE_REALISM), ('life_turns', UPGRADE_TURNS),
                           ('growing_families', UPGRADE_FAMILIES), ('family_life', UPGRADE_FAMILY_LIFE),
                           ('inner_voice', UPGRADE_DREAMS), ('their_look', UPGRADE_LOOK)):
        if ('life_settings', column) in added:
            preset_upgrade(connection, upgrade)
    if ('life_settings', 'inner_voice') in added:
        preset_upgrade(connection, STRINGS_VOICE, 'paced_replies=0 AND day_shifts=1')
    if ('life_settings', 'loss_by_preset') in added:
        preset_upgrade(connection, UPGRADE_LOSS, 'people_pass_away=0 AND loss=2')


def preset_upgrade(connection, upgrade: dict, unless_moved: str = '1'):
    row = connection.execute(f'SELECT drama FROM life_settings WHERE id=1 AND {unless_moved}').fetchone()  # noqa: S608
    picked = upgrade.get(row[0]) if row else None
    if picked:
        connection.execute(f"UPDATE life_settings SET {', '.join(f'{key}=?' for key in picked)} WHERE id=1",  # noqa: S608
                           tuple(picked.values()))


def widen_context_categories(connection):
    """Workspaces from before link reading limited lookup categories with a CHECK, which SQLite cannot alter:
    the table is copied into the current definition, keeping every mapping."""
    row = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='context_tools'").fetchone()
    if not row or "'local_events')" not in row[0]:
        return
    definition = re.search(r'CREATE TABLE IF NOT EXISTS context_tools \((.*?)\n\);', SCHEMA, re.S).group(1)
    columns = 'service_id, category, tool, arguments, run_in, enabled, approved, updated_at'
    connection.execute(f'CREATE TABLE context_tools_widened ({definition})')
    connection.execute(f'INSERT INTO context_tools_widened ({columns}) SELECT {columns} FROM context_tools')
    connection.execute('DROP TABLE context_tools')
    connection.execute('ALTER TABLE context_tools_widened RENAME TO context_tools')


def widen_checks(connection):
    for table, marker in WIDENED_CHECKS:
        row = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
        if not row or marker in row[0]:
            continue
        definition = re.search(rf'CREATE TABLE IF NOT EXISTS {table} \((.*?)\n\);', SCHEMA, re.S).group(1)
        columns = ', '.join(item[1] for item in connection.execute(f'PRAGMA table_info({table})'))
        connection.execute(f'CREATE TABLE {table}_widened ({definition})')
        # Columns added later (ADDED_COLUMNS, added above) are not in schema.sql's definition: add them here too, so
        # the copy keeps them.
        have = {item[1] for item in connection.execute(f'PRAGMA table_info({table}_widened)')}
        for added_table, column, added in ADDED_COLUMNS:
            if added_table == table and column not in have:
                connection.execute(f'ALTER TABLE {table}_widened ADD COLUMN {column} {added}')
        connection.execute(f'INSERT INTO {table}_widened ({columns}) SELECT {columns} FROM {table}')
        connection.execute(f'DROP TABLE {table}')
        connection.execute(f'ALTER TABLE {table}_widened RENAME TO {table}')


def free_companion_slot(connection):
    """Workspaces from before switching companions allowed only one companions row, by a CHECK that SQLite
    cannot alter. Other tables reference the table, so it is rebuilt with foreign keys off, outside any
    transaction, as SQLite's own procedure for table changes does; the caller turns them back on."""
    row = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='companions'").fetchone()
    if not row or 'NOT NULL UNIQUE DEFAULT 1' not in row[0]:
        return
    definition = re.search(r'CREATE TABLE IF NOT EXISTS companions \((.*?)\n\);', SCHEMA, re.S).group(1)
    columns = ', '.join(item[1] for item in connection.execute('PRAGMA table_info(companions)'))
    connection.execute('PRAGMA foreign_keys=OFF')
    connection.execute('BEGIN IMMEDIATE')
    try:
        connection.execute(f'CREATE TABLE companions_widened ({definition})')
        for table, column, added in ADDED_COLUMNS:
            if table == 'companions':
                connection.execute(f'ALTER TABLE companions_widened ADD COLUMN {column} {added}')
        connection.execute(f'INSERT INTO companions_widened ({columns}) SELECT {columns} FROM companions')
        connection.execute('DROP TABLE companions')
        connection.execute('ALTER TABLE companions_widened RENAME TO companions')
        if connection.execute('PRAGMA foreign_key_check').fetchone():
            raise DomainError('The companions table could not be upgraded.', 500)
        connection.execute('COMMIT')
    except BaseException:
        connection.execute('ROLLBACK')
        raise


def backfill_subject_keys(connection):
    from companion.memory.extraction import subject_key
    rows = connection.execute("SELECT id, subject FROM memories WHERE subject_key=''").fetchall()
    connection.executemany('UPDATE memories SET subject_key=? WHERE id=?',
                           [(subject_key(row[1]), row[0]) for row in rows])


FOREIGN = 'This database belongs to another application. Choose a Companion workspace.'


def inspect_existing(path: Path):
    """Read-only check, so a foreign file is refused before any pragma can change it."""
    if not path.exists() or path.stat().st_size == 0:
        return
    try:
        connection = sqlite3.connect(f'{path.resolve().as_uri()}?mode=ro', uri=True)
        try:
            validate_identity(connection)
        finally:
            connection.close()
    except sqlite3.DatabaseError as error:
        raise DomainError(FOREIGN, 409) from error


def validate_identity(connection):
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'app_identity' not in tables:
        require(not tables, FOREIGN, 409)
        return
    marker = dict(connection.execute('SELECT key, value FROM app_identity').fetchall())
    require(marker.get('app_id') == APP_ID, FOREIGN, 409)
    require(int(marker.get('schema_version', 0)) <= SCHEMA_VERSION,
            'This workspace was created by a newer Companion version.', 409)


def claim_identity(connection):
    validate_identity(connection)
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'app_identity' not in tables:
        connection.execute('CREATE TABLE app_identity (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        connection.executemany('INSERT INTO app_identity (key, value) VALUES (?, ?)',
                               (('app_id', APP_ID), ('schema_version', str(SCHEMA_VERSION))))


def one(connection, sql: str, values=()) -> dict:
    row = connection.execute(sql, values).fetchone()
    require(row is not None, 'This item could not be found.', 404)
    return dict(row)


def optional(connection, sql: str, values=()) -> dict | None:
    row = connection.execute(sql, values).fetchone()
    return None if row is None else dict(row)


def many(connection, sql: str, values=()) -> list[dict]:
    return [dict(row) for row in connection.execute(sql, values).fetchall()]


def settings(connection) -> dict:
    return one(connection, 'SELECT * FROM workspace_settings WHERE id=1')


def bump_memory_revision(connection, timestamp) -> int:
    connection.execute('UPDATE workspace_settings SET memory_revision=memory_revision+1, updated_at=? '
                       'WHERE id=1', (timestamp,))
    return settings(connection)['memory_revision']
