"""Your picture: how the user's persona looks, for pictures of moments they share with a companion (Vanta,
2026-11-02).

A persona may say how they look ("How you look", a few words) and have a picture: one the user uploads, or one
made from those words with "Make one". Both belong to the persona in worlds.json, so every world of theirs uses
them; the picture's file is kept in the data folder's `persona-pictures`, named by its content, so a copied persona
shares it.

A picture of a moment the user is in (an outing or a visit with the companion, their wedding, a big day) shows
them beside the companion: in words from their looks, and on a backend that takes reference pictures, following
their picture as a second reference (images/runner.py). Settings > Pictures can turn that off per world (`show_me`).

"Make one" is a fixed fill-in template, never written by a model, classified and routed like every other image
(images/content.py, images/routing.py: NSFW only to a backend that accepts it, prohibited nowhere) and made in the
world the user is in, sharing the image runner's backend limits, as Matchlight's photos do (companion/dating_photos.py).
"""
import asyncio
import contextlib
import hashlib
import random
from pathlib import Path

from companion.database import Database, decode, identifier, optional
from companion.errors import DomainError, require
from companion.images import backends, storage
from companion.images.adapters.base import AdapterError, ImageRequest, size_for
from companion.images.content import classify
from companion.images.routing import eligible, route
from companion.world import looks as appearance

FOLDER = 'persona-pictures'
MAX_BYTES = 30 * 1024 * 1024
TYPES = {'png': 'image/png', 'jpg': 'image/jpeg', 'webp': 'image/webp'}
NEGATIVE = 'text, watermark, logo, blurry, distorted hands, extra limbs, duplicate person, cartoon'
WHO = {'woman': 'woman', 'man': 'man', 'nonbinary': 'person'}
DEFAULT_STYLE = 'Natural photograph'
SHOT = ('waist-up portrait facing the camera, wearing everyday clothes, a relaxed, natural smile, plain softly lit '
        'background. A fictional person; they are the only person in the picture.')
NO_LOOKS = 'Say how you look first, so the picture has something to follow.'


def folder(database: Database) -> Path:
    path = Path(database.root) / FOLDER
    path.mkdir(parents=True, exist_ok=True)
    return path


def path_of(database: Database, name: str) -> Path | None:
    if not name:
        return None
    base = folder(database).resolve()
    path = (base / name).resolve()
    return path if path.parent == base and path.is_file() else None


def checked(data: bytes) -> str:
    require(len(data) <= MAX_BYTES, 'This picture is larger than 30 MB.', 413)
    try:
        kind, width, height = storage.sniff(data)
    except AdapterError as error:
        raise DomainError('Add a PNG, JPEG or WebP picture.', 422) from error
    require(64 <= width <= 12000 and 64 <= height <= 12000, 'This picture is too small or too large to use.', 422)
    return kind


def keep(database: Database, data: bytes) -> str:
    """The picture's file in the persona folder, named by what is in it; one already there is reused."""
    name = f'{hashlib.sha256(data).hexdigest()[:32]}.{checked(data)}'
    target = folder(database) / name
    if not target.is_file():
        partial = target.with_name(name + '.partial')
        partial.write_bytes(data)
        partial.replace(target)
    return name


def set_picture(database: Database, persona_id: str, name: str) -> dict:
    """The persona's picture ('' for none), saved in worlds.json and in the world the user is in when it is theirs."""
    from companion import worlds
    data = worlds.registry(database)
    persona = worlds.found(data['personas'], persona_id, 'persona')
    persona['picture'] = name
    worlds.save(database.root, data)
    active = worlds.found(data['worlds'], data['active'], 'world')
    if active['persona_id'] == persona_id:
        with database.connect(write=True) as connection:
            connection.execute('UPDATE persona SET picture=? WHERE id=1', (name,))
    return worlds.view(database)


def save_looks(database: Database, persona_id: str, looks: str):
    """How you look as typed, saved before a picture is made from it."""
    from companion import worlds
    data = worlds.registry(database)
    persona = worlds.found(data['personas'], persona_id, 'persona')
    persona['looks'] = looks.strip()[:600]
    worlds.save(database.root, data)
    active = worlds.found(data['worlds'], data['active'], 'world')
    if active['persona_id'] == persona_id:
        with database.connect(write=True) as connection:
            connection.execute('UPDATE persona SET looks=? WHERE id=1', (persona['looks'],))


def upload(database: Database, persona_id: str, data: bytes) -> dict:
    return set_picture(database, persona_id, keep(database, data))


def remove(database: Database, persona_id: str) -> dict:
    """The picture is taken off the persona; its file stays, since a copied persona may share it."""
    return set_picture(database, persona_id, '')


def file(database: Database, persona_id: str) -> Path:
    from companion import worlds
    persona = worlds.found(worlds.registry(database)['personas'], persona_id, 'persona')
    path = path_of(database, persona.get('picture') or '')
    require(path is not None, 'There is no picture of you yet.', 404)
    return path


# In pictures ----------------------------------------------------------------------------------------------

def described(persona: dict, age: int | None = None) -> str:
    """The user in words a picture can show: "a woman in her early thirties, short dark curls and freckles"."""
    who = WHO.get(persona.get('gender') or '', 'person')
    possessive = {'woman': 'her', 'man': 'his'}.get(who, 'their')
    age = persona.get('age') if age is None else age
    words = appearance.article(who) + (f' in {possessive} {appearance.age_words(age)}' if age else '')
    own = (persona.get('looks') or '').strip().rstrip('.')
    return f'{words}, {own}' if own else words


def here(connection) -> dict | None:
    """The persona of the world the user is in, as pictures read them, or None when Settings > Pictures shows the
    user in no pictures."""
    shown = optional(connection, 'SELECT show_me FROM image_settings WHERE id=1')
    if not shown or not shown['show_me']:
        return None
    persona = optional(connection, 'SELECT name, gender, age, looks, picture FROM persona WHERE id=1')
    # Shown once they said how they look or have a picture: until then the picture stays the companion's own.
    return persona if persona and ((persona['looks'] or '').strip() or persona['picture']) else None


def reference(database: Database, connection) -> bytes | None:
    """The user's picture, for a picture they are in (images/runner.py), or None."""
    persona = here(connection)
    path = persona and path_of(database, persona['picture'])
    if path is None:
        return None
    with contextlib.suppress(OSError):
        return path.read_bytes()
    return None


# Make one -------------------------------------------------------------------------------------------------

def prompt_for(persona: dict, style: str | None) -> str:
    return f"{(style or DEFAULT_STYLE).strip().rstrip('.')}. {described(persona).capitalize()}, {SHOT}"


class PersonaPictures:
    """"Make one": a picture of the persona from how they look, one request at a time."""

    def __init__(self, database, vault, images):
        self.database = database
        self.vault = vault
        self.images = images
        self.tasks: dict[str, tuple[asyncio.Task, dict]] = {}
        images.sharing.append(lambda: [meta for _task, meta in self.tasks.values()])
        images.others.append(self.dispatch)

    def status(self, persona_id: str) -> dict:
        """The last picture asked for, and whether this world has a backend that can make one (`can_make`)."""
        with self.database.connect() as connection:
            row = optional(connection, 'SELECT status, error, backend_id FROM persona_pictures WHERE persona_id=?',
                           (persona_id,))
            can_make = bool(backends.ordered(connection, enabled_only=True))
        return {'status': row['status'] if row else None, 'error': row['error'] if row else None,
                'can_make': can_make}

    def request(self, persona_id: str, looks: str | None = None) -> dict:
        """Make one from How you look: `looks`, as the form has it, is saved to the persona first."""
        from companion import worlds
        from companion.images.jobs import image_settings
        if looks is not None:
            save_looks(self.database, persona_id, looks)
        persona = worlds.found(worlds.registry(self.database)['personas'], persona_id, 'persona')
        require(bool((persona.get('looks') or '').strip()), NO_LOOKS, 422)
        with self.database.connect(write=True) as connection:
            row = optional(connection, 'SELECT status FROM persona_pictures WHERE persona_id=?', (persona_id,))
            require(not row or row['status'] not in ('queued', 'running'), 'Your picture is already being made.', 409)
            pool = backends.ordered(connection, enabled_only=True)
            general = image_settings(connection)['style']
            built = {'prompt': prompt_for(persona, general), 'negative': NEGATIVE, 'appearance': persona['looks']}
            decision = route(classify(built), pool)
            if decision.refusal:
                raise DomainError(decision.refusal, 409, decision.code or 'refused')
            prompt = prompt_for(persona, backends.style_for(decision.target, general))
            connection.execute(
                'INSERT INTO persona_pictures (persona_id, status, prompt, negative, seed, backend_id, created_at) '
                "VALUES (?, 'queued', ?, ?, ?, ?, ?) ON CONFLICT(persona_id) DO UPDATE SET status='queued', "
                'prompt=excluded.prompt, negative=excluded.negative, seed=excluded.seed, backend_id=excluded.backend_id, '
                'error=NULL, file=NULL, created_at=excluded.created_at, finished_at=NULL',
                (persona_id, prompt, NEGATIVE, random.SystemRandom().randrange(1, 2**31), decision.target['id'],
                 self.database.now()))
        self.images.wake()
        return self.status(persona_id)

    def recover(self):
        """A picture cut off when the app closed can be asked for again."""
        with self.database.connect(write=True) as connection:
            connection.execute("UPDATE persona_pictures SET status='failed', error=? WHERE status IN ('queued', "
                               "'running')", ('The app closed before your picture was made. Try again.',))

    def dispatch(self) -> list[asyncio.Task]:
        started = []
        with self.database.connect() as connection:
            for row in connection.execute("SELECT * FROM persona_pictures WHERE status='queued' ORDER BY created_at"):
                row = dict(row)
                backend = optional(connection, 'SELECT * FROM image_backends WHERE id=?', (row['backend_id'],))
                if row['persona_id'] in self.tasks or backend and (backend['blocked_reason'] or
                                                                   self.images.busy(backend)):
                    continue
                task = asyncio.get_running_loop().create_task(self.run(row, backend))
                self.tasks[row['persona_id']] = (task, {'id': row['backend_id'], 'kind': backend and backend['kind']})
                task.add_done_callback(lambda _task, key=row['persona_id']: self.tasks.pop(key, None))
                started.append(task)
        return started

    async def drain(self):
        """Run until nothing more can start; for tests."""
        while True:
            started = self.dispatch()
            pending = [task for task, _meta in list(self.tasks.values()) if not task.done()]
            if not started and not pending:
                return
            await asyncio.gather(*pending, return_exceptions=True)

    def finish(self, persona_id: str, status: str, **fields):
        assignments = {'status': status, 'finished_at': self.database.now(), **fields}
        with self.database.connect(write=True) as connection:
            connection.execute(f"UPDATE persona_pictures SET {', '.join(f'{name}=?' for name in assignments)} "
                               'WHERE persona_id=?', (*assignments.values(), persona_id))

    async def run(self, row: dict, backend: dict | None):
        persona_id = row['persona_id']
        if backend is None or not backend['enabled'] or not eligible(classify(
                {'prompt': row['prompt'], 'negative': row['negative']}), backend):
            self.finish(persona_id, 'failed', error='That image backend can no longer make this picture. Try again.')
            return
        self.finish(persona_id, 'running')
        width, height = size_for(backend['kind'], 'portrait')
        image = ImageRequest(f'persona-{identifier()}', row['prompt'], row['negative'], row['seed'], width, height,
                             backend, decode(backend['config']), backends.backend_key(self.database, self.vault, backend),
                             storage.raw_directory(self.database))
        try:
            result = await self.images.adapters[backend['kind']].generate(image)
            name = keep(self.database, result.data)
        except AdapterError as error:
            if error.code == 'auth':
                backends.block(self.database, backend['id'], error.message)
            self.finish(persona_id, 'failed', error=error.message)
            return
        except DomainError as error:
            self.finish(persona_id, 'failed', error=error.message)
            return
        except Exception as error:  # noqa: BLE001 - a backend bug fails this picture, not the app.
            self.finish(persona_id, 'failed', error=f'The image backend failed ({error}).')
            return
        if result.raw_path:
            with contextlib.suppress(OSError):
                result.raw_path.unlink()
        try:
            set_picture(self.database, persona_id, name)
        except DomainError as error:
            self.finish(persona_id, 'failed', error=error.message)
            return
        self.finish(persona_id, 'completed', file=name)
