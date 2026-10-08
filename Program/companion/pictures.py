"""Pictures the user sends in chat.

The interface shrinks a picture and re-encodes it before upload, which also drops its location and
camera data, and the server keeps the file as it arrives. A picture is the user's own: unlike the
pictures the app generates (companion/images/content.py), it is not classified, and it goes to the
model the user chose for Seeing pictures.

That model describes each picture once, before the reply. The description joins the message's text
wherever the conversation is read (the reply's context, recall, search vectors), so the companion
remembers what they were shown without the picture being sent again. A model that cannot see, or a
service that refuses the picture, leaves it unseen: the companion then says in character that it
would not load, as with a link, and the interface shows the real reason under the picture.
"""
import base64
import contextlib
from pathlib import Path

from companion import prompt_library
from companion.clock import parse
from companion.database import identifier, many, optional
from companion.errors import DomainError, require
from companion.images import storage
from companion.images.adapters.base import AdapterError
from companion.providers.scheduling import CONVERSATION
from companion.text_models import config_for, key_for

FOLDER = 'pictures'
MAX_BYTES = 10 * 1024 * 1024
MAX_SIDE = 8192
PER_MESSAGE = 4
UNATTACHED_SECONDS = 24 * 3600
JOB = 'vision'
# Providers whose API takes pictures with the text. Kobold and Codex CLI do not here.
VISION_PROVIDERS = {'openai', 'anthropic', 'google', 'openrouter', 'nanogpt', 'local', 'compatible'}
DESCRIBE = (
    'Someone sent this picture in a private chat. Describe it for a friend who cannot see it, in two to five '
    'plain sentences: the people (look, expression, clothes, what they are doing; never guess who they are), '
    'animals, objects, the place, the light or time of day, and any readable text, quoted. Be specific and '
    'factual, with no commentary and no warnings. Reply with the description only.')
UNSEEN = '[A photo that would not load for you]'


def folder(database):
    path = database.path.parent / FOLDER
    path.mkdir(parents=True, exist_ok=True)
    return path


def folder_of(connection):
    """The pictures folder beside the database this connection has open."""
    return Path(connection.execute('PRAGMA database_list').fetchone()[2]).parent / FOLDER


def save(database, data: bytes) -> dict:
    """Keep an uploaded picture until a message takes it."""
    require(0 < len(data) <= MAX_BYTES, 'Pictures can be up to 10 MB.', 413)
    try:
        kind, width, height = storage.sniff(data)
    except AdapterError as error:
        raise DomainError('Send a PNG, JPEG or WebP picture.', 415) from error
    require(0 < width <= MAX_SIDE and 0 < height <= MAX_SIDE, 'That picture is too large.', 413)
    picture_id = identifier()
    name = f'{picture_id}.{kind}'
    target = folder(database) / name
    partial = target.with_suffix('.partial')
    partial.write_bytes(data)
    partial.replace(target)
    with database.connect(write=True) as connection:
        forget_unattached(database.clock.now().timestamp(), connection)
        connection.execute('INSERT INTO message_pictures (id, file, media_type, width, height, status, created_at) '
                           "VALUES (?, ?, ?, ?, ?, 'pending', ?)",
                           (picture_id, name, storage.TYPES[kind], width, height, database.now()))
    return {'id': picture_id, 'width': width, 'height': height}


def forget_unattached(now: float, connection):
    """Uploads never sent within a day are removed."""
    cutoff = now - UNATTACHED_SECONDS
    rows = many(connection, 'SELECT id, created_at FROM message_pictures WHERE message_id IS NULL')
    remove(connection, [row['id'] for row in rows if parse(row['created_at']).timestamp() < cutoff])


def attach(connection, message_id: str, picture_ids: list[str]):
    """The pictures sent with a message. Each upload belongs to one message."""
    require(len(picture_ids) <= PER_MESSAGE, f'Send up to {PER_MESSAGE} pictures at once.', 422)
    for position, picture_id in enumerate(picture_ids):
        row = optional(connection, 'SELECT message_id FROM message_pictures WHERE id=?', (picture_id,))
        require(row is not None and row['message_id'] in (None, message_id),
                'That picture is no longer available. Add it again.', 409)
        connection.execute('UPDATE message_pictures SET message_id=?, position=? WHERE id=?',
                           (message_id, position, picture_id))


def for_messages(connection, message_ids) -> dict[str, list[dict]]:
    if not message_ids:
        return {}
    found: dict[str, list[dict]] = {}
    for start in range(0, len(message_ids), 500):
        batch = list(message_ids)[start:start + 500]
        marks = ','.join('?' * len(batch))
        for row in many(connection, f'SELECT * FROM message_pictures WHERE message_id IN ({marks}) '  # noqa: S608
                        'ORDER BY position', batch):
            found.setdefault(row['message_id'], []).append(row)
    return found


def view(row: dict) -> dict:
    return {'id': row['id'], 'width': row['width'], 'height': row['height'], 'status': row['status'],
            'reason': row['reason'] if row['status'] == 'unseen' else None}


def decorate(connection, messages: list[dict]) -> list[dict]:
    """Message views with the pictures each of the user's messages carried."""
    found = for_messages(connection, [message['id'] for message in messages if message['role'] == 'user'])
    return [{**message, 'pictures': [view(row) for row in found.get(message['id'], [])]} for message in messages]


def picture_line(row: dict) -> str:
    if row['status'] == 'seen' and row['description']:
        return f"[Photo: {row['description']}]"
    return UNSEEN


def with_pictures(text: str, rows: list[dict]) -> str:
    lines = [picture_line(row) for row in rows if row['status'] != 'pending']
    return '\n'.join([text, *lines]) if text and lines else text or '\n'.join(lines)


def described(connection, messages: list[dict]) -> list[dict]:
    """Messages whose text also says what their pictures show, for the reply and for recall."""
    found = for_messages(connection, [message['id'] for message in messages if message['role'] == 'user'])
    return [{**message, 'text': with_pictures(message['text'], found[message['id']])} if message['id'] in found
            else message for message in messages]


def unseen_note(doing: str | None) -> str:
    fits = f' that fits what you are doing right now ({doing})' if doing else ''
    return ('- The user just sent a photo that would not open for you. You have not seen it: do not guess or '
            f'pretend to know what it shows. In character, give a brief, natural reason{fits}, such as bad '
            'signal or it not loading, and ask what it is. Never mention the app or errors.')


def path_of(database, picture_id: str):
    with database.connect() as connection:
        row = optional(connection, 'SELECT file, media_type FROM message_pictures WHERE id=?', (picture_id,))
    require(row is not None, 'This picture could not be found.', 404)
    path = folder(database) / row['file']
    require(path.is_file(), 'This picture is missing from the workspace.', 404)
    return path, row['media_type']


def copy(connection, ids: dict[str, str]):
    """A forked timeline's copies of messages keep their pictures; the files are shared."""
    found = for_messages(connection, list(ids))
    for message_id, rows in found.items():
        for row in rows:
            connection.execute(
                'INSERT INTO message_pictures (id, message_id, position, file, media_type, width, height, status, '
                'description, reason, model, created_at, described_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (identifier(), ids[message_id], row['position'], row['file'], row['media_type'], row['width'],
                 row['height'], row['status'], row['description'], row['reason'], row['model'], row['created_at'],
                 row['described_at']))


def remove(connection, picture_ids: list[str]):
    """Delete pictures, and each file once no other copy uses it."""
    if not picture_ids:
        return
    marks = ','.join('?' * len(picture_ids))
    files = {row['file'] for row in many(connection, f'SELECT file FROM message_pictures WHERE id IN ({marks})',  # noqa: S608
                                         picture_ids)}
    connection.execute(f'DELETE FROM message_pictures WHERE id IN ({marks})', picture_ids)  # noqa: S608
    for name in files:
        if not optional(connection, 'SELECT 1 FROM message_pictures WHERE file=? LIMIT 1', (name,)):
            with contextlib.suppress(OSError):
                (folder_of(connection) / name).unlink(missing_ok=True)


def forget(connection, message_ids):
    """A deleted message takes its pictures and their descriptions with it."""
    found = for_messages(connection, list(message_ids))
    remove(connection, [row['id'] for rows in found.values() for row in rows])


def files_of(connection, companion_id: str | None = None) -> list[str]:
    mine = (' WHERE message_id IN (SELECT id FROM messages WHERE timeline_id IN '
            '(SELECT id FROM timelines WHERE companion_id=?))') if companion_id else ''
    rows = many(connection, f'SELECT DISTINCT file FROM message_pictures{mine}',  # noqa: S608
                (companion_id,) if companion_id else ())
    return [f"{FOLDER}/{row['file']}" for row in rows]


class Seer:
    """Describes a message's pictures with the Seeing pictures model, once."""

    def __init__(self, database, vault, provider, scheduler):
        self.database = database
        self.vault = vault
        self.provider = provider
        self.scheduler = scheduler

    async def look(self, user) -> list[dict]:
        """Describe any picture of this message not described yet; returns all its pictures."""
        with self.database.connect() as connection:
            rows = for_messages(connection, [user['id']]).get(user['id'], [])
            config = config_for(connection, JOB)
        for row in rows:
            if row['status'] == 'pending':
                await self.describe(row, config, user['text'])
        with self.database.connect() as connection:
            return for_messages(connection, [user['id']]).get(user['id'], [])

    async def describe(self, row, config, said: str):
        status, description, reason, model = 'unseen', None, None, None
        try:
            require(config is not None, 'No model is set up to look at pictures.', 409)
            model = config.get('model')
            require(config['provider'] in VISION_PROVIDERS,
                    f"{config.get('profile_name', 'This profile')} cannot look at pictures. Choose a model that can "
                    'see in Settings > Models > Seeing pictures.', 409)
            description = await self.ask(row, config, said)
            require(bool(description), 'The model did not describe the picture.', 502)
            status = 'seen'
        except DomainError as failure:
            reason = failure.message
        except Exception:  # noqa: BLE001 - a failed look leaves the picture unseen, never the reply failed.
            reason = 'The picture could not be described.'
        with self.database.connect(write=True) as connection:
            connection.execute('UPDATE message_pictures SET status=?, description=?, reason=?, model=?, '
                               "described_at=? WHERE id=? AND status='pending'",
                               (status, description, reason, model, self.database.now(), row['id']))

    async def ask(self, row, config, said: str) -> str:
        path, media_type = path_of(self.database, row['id'])
        data = base64.b64encode(path.read_bytes()).decode('ascii')
        words = f'Their message with it: «{said}»' if said.strip() else 'They sent it without a message.'
        content = [{'type': 'text', 'text': words}, {'type': 'image', 'media_type': media_type, 'data': data}]
        with self.database.connect() as connection:
            describe = prompt_library.text(connection, 'picture-description')
        text = []
        async with self.scheduler.reserve(config, CONVERSATION):
            async for chunk in self.provider.stream(config, key_for(self.vault, config), describe,
                                                    [{'role': 'user', 'content': content}]):
                text.append(chunk.text)
        return ''.join(text).strip()[:2000]
