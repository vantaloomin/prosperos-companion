"""Voice notes: now and then a companion's first text is a short voice note instead (docs/voice-notes.md).

Rules decide everything; the model writes the words as it does for any first text and an engine only reads them
aloud. A note is sent only for a first text (companion/life/openers.py), so quiet hours, her sleep, the daily cap
on first texts and the away allowance all apply before this is asked. Then, by rules:

- Voice notes are on (the default) and the chosen engine can speak: the built-in voice is downloaded, or the hosted
  engine has a key.
- Seeded dice on the trigger: about one first text in three, so it stays a small surprise and a retry rolls the
  same.
- At most `daily_limit` notes (3 by default) per companion in 24 hours.
- The message is short and has no link (a link should stay something you can tap).

If reading it aloud fails, the message goes as a plain text instead; a voice note is never the reason a message
is lost. The transcript is the message text itself, so memory, search and replies read it like any other.
"""
import hashlib
import logging
import os
import re
import wave
from datetime import timedelta
from pathlib import Path

from companion.characters import by_id
from companion.clock import stamp
from companion.database import identifier, many, one, optional
from companion.errors import DomainError, require
from companion.providers.vault import credential_for
from companion.voice import hosted, voices
from companion.voice.kokoro import Kokoro

FOLDER = 'voice-notes'
ENGINES = ('builtin', 'openai', 'elevenlabs', 'google')
HOSTED = ('openai', 'elevenlabs', 'google')
CHANCE = 0.3
MAX_CHARACTERS = 320
URL = re.compile(r'https?://\S+|www\.\S+', re.IGNORECASE)
ACTION = re.compile(r'\*[^*\n]{1,200}\*')
# Emoji and pictographs, which a voice cannot say.
EMOJI = re.compile('[\U0001F000-\U0001FAFF☀-➿️‍⬀-⯿]')
ENV = {'openai': 'OPENAI_API_KEY', 'elevenlabs': 'ELEVENLABS_API_KEY', 'google': 'GOOGLE_TTS_API_KEY'}
PREVIEW = "Hey, it's {name}. This is what I sound like when I send you a voice note."
INSTRUCTION = ('This message is a voice note: you say it out loud instead of typing it. Write only the words you '
               'say, the way people talk in a quick voice message, with no emoji, links or actions, in under 50 '
               'words.')
log = logging.getLogger('companion')


def key_ref(engine: str) -> str:
    return f'voice-{engine}'


def read(connection) -> dict:
    row = one(connection, 'SELECT * FROM voice_settings WHERE id=1')
    return {'voice_notes': bool(row['voice_notes']), 'engine': row['engine'], 'daily_limit': row['daily_limit']}


def spoken(text: str) -> str:
    """The words to read aloud: no emoji, *actions* or links, and plain spacing."""
    return ' '.join(EMOJI.sub('', URL.sub('', ACTION.sub('', text))).split())


def rolled(key: str) -> bool:
    return int(hashlib.sha256(f'voice-note:{key}'.encode('utf-8')).hexdigest()[:8], 16) / 0xFFFFFFFF < CHANCE


def sent_today(connection, companion_id: str, now) -> int:
    return one(connection, 'SELECT COUNT(*) AS n FROM voice_notes v JOIN messages m ON m.id=v.message_id '
               'JOIN timelines t ON t.id=m.timeline_id WHERE t.companion_id=? AND v.created_at>=?',
               (companion_id, stamp(now - timedelta(hours=24))))['n']


def files_of(connection, companion_id: str | None = None) -> list[str]:
    mine = (' WHERE message_id IN (SELECT id FROM messages WHERE timeline_id IN '
            '(SELECT id FROM timelines WHERE companion_id=?))') if companion_id else ''
    rows = many(connection, f'SELECT DISTINCT file FROM voice_notes{mine}',  # noqa: S608
                (companion_id,) if companion_id else ())
    return [f"{FOLDER}/{row['file']}" for row in rows]


def for_messages(connection, ids: list[str]) -> dict[str, dict]:
    if not ids:
        return {}
    marks = ','.join('?' * len(ids))
    rows = many(connection, f'SELECT message_id, duration_ms, engine FROM voice_notes WHERE message_id IN ({marks})',  # noqa: S608
                tuple(ids))
    return {row['message_id']: {'url': f"/api/voice/notes/{row['message_id']}", 'duration_ms': row['duration_ms'],
                                'engine': row['engine']} for row in rows}


def decorate(connection, messages: list[dict]) -> list[dict]:
    """Message views with the voice note each companion message was sent as, if any."""
    found = for_messages(connection, [message['id'] for message in messages if message['role'] == 'companion'])
    return [{**message, 'voice': found.get(message['id'])} for message in messages]


def copy(connection, ids: dict[str, str]):
    """A forked timeline's copies of messages stay voice notes; the files are shared."""
    for row in many(connection, 'SELECT * FROM voice_notes'):
        if row['message_id'] in ids:
            connection.execute('INSERT OR IGNORE INTO voice_notes (message_id, file, media_type, duration_ms, engine, '
                               'voice, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                               (ids[row['message_id']], row['file'], row['media_type'], row['duration_ms'],
                                row['engine'], row['voice'], row['created_at']))


def wav_length(path: Path) -> int | None:
    try:
        with wave.open(str(path)) as audio:
            return round(audio.getnframes() * 1000 / audio.getframerate())
    except (OSError, wave.Error, ZeroDivisionError):
        return None


class VoiceNotes:
    """Decides on voice notes, picks each companion's voice and reads notes aloud with the chosen engine."""

    def __init__(self, database, vault, transport=None, runner=None):
        self.database = database
        self.vault = vault
        self.transport = transport
        self.folder = Path(database.path).parent / FOLDER
        self.kokoro = Kokoro(Path(database.path).parent / 'voice', transport, runner)
        self.catalogs: dict[tuple[str, str], list[dict]] = {}

    # --- keys and engines ----------------------------------------------------------------------

    def key(self, engine: str) -> tuple[str | None, str | None]:
        """The key for a hosted engine and where it came from: saved here, an OpenAI text profile, or the environment."""
        saved = self.vault.get(key_ref(engine))
        if saved:
            return saved, 'saved'
        if engine == 'openai':
            with self.database.connect() as connection:
                profile = optional(connection, "SELECT credential_ref FROM model_profiles WHERE "
                                   "json_extract(config, '$.provider')='openai' AND credential_ref IS NOT NULL "
                                   'ORDER BY created_at LIMIT 1')
            found = credential_for(self.vault, profile['credential_ref'], 'openai') if profile else None
            if found:
                return found, 'profile'
        found = os.environ.get(ENV[engine])
        return (found, 'environment') if found else (None, None)

    def can_speak(self, engine: str) -> bool:
        return self.kokoro.ready() if engine == 'builtin' else self.key(engine)[0] is not None

    async def catalog(self, engine: str) -> list[dict]:
        """The engine's stock voices; the services' own lists are fetched once per key."""
        if engine == 'builtin':
            return voices.kokoro_voices()
        if engine == 'openai':
            return voices.openai_voices()
        key = self.key(engine)[0]
        require(key is not None, f'Add a {hosted.ENGINE_NAMES[engine]} key first.', 409)
        cached = (engine, hashlib.sha256(key.encode('utf-8')).hexdigest())
        if cached not in self.catalogs:
            fetch = hosted.elevenlabs_voices if engine == 'elevenlabs' else hosted.google_voices
            self.catalogs[cached] = await fetch(key, self.transport)
        return self.catalogs[cached]

    async def voice_for(self, companion: dict, engine: str) -> tuple[str, str]:
        """(voice id, 'user' or 'app') for this companion on this engine."""
        with self.database.connect() as connection:
            picked = voices.chosen(connection, companion['id'], engine)
            wanted = voices.traits(connection, companion['version']['definition'])
        if picked:
            return picked, 'user'
        found = voices.pick(companion['id'], await self.catalog(engine), wanted)
        require(found is not None, 'This voice service has no voices to choose from.', 502)
        return found['id'], 'app'

    # --- deciding ------------------------------------------------------------------------------

    def plan(self, companion: dict, trigger_key: str, now) -> str | None:
        """The engine to send this first text as a voice note with, or None for a plain text."""
        with self.database.connect() as connection:
            current = read(connection)
            if not current['voice_notes'] or not rolled(f"{companion['id']}:{trigger_key}"):
                return None
            if sent_today(connection, companion['id'], now) >= current['daily_limit']:
                return None
        return current['engine'] if self.can_speak(current['engine']) else None

    def fits(self, text: str) -> bool:
        words = spoken(text)
        return bool(words) and len(text) <= MAX_CHARACTERS and not URL.search(text)

    # --- speaking ------------------------------------------------------------------------------

    async def audio(self, engine: str, voice: str, text: str) -> tuple[Path, str]:
        """Read the text aloud into a new file in the voice-notes folder: (path, media type)."""
        self.folder.mkdir(parents=True, exist_ok=True)
        name = identifier()
        if engine == 'builtin':
            return await self.kokoro.speak(text, voice, self.folder / f'{name}.wav'), 'audio/wav'
        data = await hosted.speak(engine, self.key(engine)[0], voice, text, self.transport)
        require(len(data) > 0, f'{hosted.ENGINE_NAMES[engine]} sent back an empty voice note.', 502)
        path = self.folder / f'{name}.mp3'
        path.write_bytes(data)
        return path, 'audio/mpeg'

    async def record(self, companion: dict, engine: str, text: str) -> dict | None:
        """A voice note for a first text about to be sent, or None to send it as text."""
        if not self.fits(text):
            return None
        try:
            voice, _who = await self.voice_for(companion, engine)
            path, media_type = await self.audio(engine, voice, spoken(text))
        except DomainError as error:
            log.warning('A voice note went as a text instead: %s', error.message)
            return None
        return {'file': path.name, 'media_type': media_type, 'engine': engine, 'voice': voice,
                'duration_ms': wav_length(path) if media_type == 'audio/wav' else None}

    def attach(self, connection, message_id: str, note: dict, timestamp: str):
        connection.execute('INSERT INTO voice_notes (message_id, file, media_type, duration_ms, engine, voice, '
                           'created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                           (message_id, note['file'], note['media_type'], note['duration_ms'], note['engine'],
                            note['voice'], timestamp))

    def discard(self, note: dict | None):
        if note:
            (self.folder / note['file']).unlink(missing_ok=True)

    async def preview(self, companion_id: str, voice: str | None, engine: str | None) -> tuple[bytes, str]:
        """A short sample of a companion's voice (or another voice), read now and not kept."""
        with self.database.connect() as connection:
            companion = by_id(connection, companion_id)
            engine = engine or read(connection)['engine']
        require(companion is not None, 'That companion was not found.', 404)
        require(engine in ENGINES, 'Choose a voice engine.', 422)
        require(self.can_speak(engine), 'The built-in voice is not downloaded yet.' if engine == 'builtin' else
                f'Add a {hosted.ENGINE_NAMES[engine]} key first.', 409)
        voice = voice or (await self.voice_for(companion, engine))[0]
        path, media_type = await self.audio(engine, voice, PREVIEW.format(name=companion['version']['name'].split()[0]))
        try:
            return path.read_bytes(), media_type
        finally:
            path.unlink(missing_ok=True)

    def file(self, message_id: str) -> tuple[Path, str]:
        with self.database.connect() as connection:
            row = optional(connection, 'SELECT file, media_type FROM voice_notes WHERE message_id=?', (message_id,))
        require(row is not None, 'That voice note was not found.', 404)
        path = self.folder / row['file']
        require(Path(row['file']).name == row['file'] and path.is_file(), 'That voice note file is missing.', 404)
        return path, row['media_type']
