"""Matchlight's "Show photo": one portrait of a townsperson, made the first time the user asks (docs/dating.md).

Nobody gets a picture until the user asks for theirs, one person at a time, so the app never makes pictures in
bulk. The prompt is a fixed fill-in template from the person's seeded looks (companion/world/dating.py), with
no model rewriting it. It is classified and routed like every other image (images/content.py,
images/routing.py: NSFW only to a backend that accepts it, prohibited nowhere) and sent through the same adapters as the
image runner, sharing its backend limits and waiting while a chat reply is written. The picture is saved, so
the person looks the same every time afterwards.
"""
import asyncio
import contextlib

from companion import dating
from companion.database import decode, identifier, optional
from companion.errors import DomainError, require
from companion.images import backends, storage
from companion.images.adapters.base import AdapterError, ImageRequest, size_for
from companion.images.content import classify
from companion.images.routing import eligible, route
from companion.world import dating as rules
from companion.world import generators

NEGATIVE = 'text, watermark, logo, blurry, distorted hands, extra limbs, duplicate person, cartoon'
WHO = {'woman': 'a woman', 'man': 'a man', 'nonbinary': 'a person'}
# The kind of picture, by how the era meets people (dating.surface).
FRAMES = {
    'app': 'A candid smartphone photo for a dating profile',
    'column': 'A studio cabinet-card portrait photograph from the era',
    'matchmaker': 'A small painted portrait miniature',
}
SETTINGS = {'cafe': 'sitting in a cafe', 'restaurant': 'at a restaurant table', 'bar': 'in a dim bar',
            'tavern': 'in a busy tavern', 'park': 'outdoors in a park', 'garden': 'outdoors in a garden',
            'library': 'between library shelves', 'fitness': 'at the gym', 'market': 'at a market stall',
            'beach': 'on a beach boardwalk', 'trail': 'on a hiking trail', 'square': 'in a city square'}
PROMPT = ('{frame}: {who}, {age} years old, {build} build, {hair}, {eyes}{beard}, {detail}, dressed in {style}, '
          '{setting}. Head and shoulders, looking at the camera with a {smile}, natural light, real skin texture, '
          'fully clothed.')
SMILES = ('warm smile', 'shy smile', 'easy grin', 'half smile', 'confident smile')


def view(row: dict | None) -> dict:
    if row is None:
        return {'status': 'none'}
    return {'status': row['status'], 'error': row['error'],
            'url': f"/api/dating/photos/{row['person_key']}/file" if row['status'] == 'completed' else None}


def inputs(sheet: dict, data: dict) -> dict:
    """The fixed prompt for this person's portrait."""
    found = rules.details(sheet, data)
    looks, seed = found['looks'], sheet.get('seed', sheet['key'])
    setting = SETTINGS.get(sheet['place'].get('kind'), 'at home') if dating.surface(data) == 'app' else \
        'plain studio backdrop'
    prompt = PROMPT.format(frame=FRAMES[dating.surface(data)], who=WHO[found['gender']], age=max(sheet['age'], 18),
                           build=looks['build'], hair=looks['hair'], eyes=looks['eyes'],
                           beard=f", {looks['beard']}" if looks.get('beard') else '', detail=looks['detail'],
                           style=looks['style'], setting=setting, smile=generators.pick(seed, 'smile', list(SMILES)))
    return {'prompt': prompt, 'negative': NEGATIVE, 'aspect': 'portrait',
            'seed': int(generators.unit(seed, 'photo') * 2 ** 31)}


def find(connection, key: str) -> tuple[dict, dict, str]:
    """Someone on the app the user may see: a match, or anyone in the city they are looking in."""
    row = optional(connection, 'SELECT town FROM dating_swipes WHERE person_key=? AND matched=1', (key,))
    if row is not None:
        sheet, data = dating.person(connection, key, row['town'])
        return sheet, data, row['town']
    mine = dating.profile(connection)
    require(mine is not None, 'Set up your profile first.', 409)
    data = dating.looking_in(connection, mine)
    found = next(((sheet, details) for sheet, details in dating.people(connection, data) if sheet['key'] == key), None)
    require(found is not None and rules.suits(found[0], found[1], mine), 'This person is not in your deck.', 404)
    return found[0], data, data.get('town', '')


def available(connection) -> bool:
    return bool(backends.ordered(connection, enabled_only=True))


class DatingPhotos:
    def __init__(self, database, vault, images):
        self.database = database
        self.vault = vault
        self.images = images
        self.tasks: dict[str, tuple[asyncio.Task, dict]] = {}
        images.sharing.append(lambda: [meta for _task, meta in self.tasks.values()])
        images.others.append(self.dispatch)

    def get(self, key: str) -> dict:
        with self.database.connect() as connection:
            return view(optional(connection, 'SELECT * FROM dating_photos WHERE person_key=?', (key,)))

    def file(self, key: str):
        with self.database.connect() as connection:
            row = optional(connection, "SELECT file FROM dating_photos WHERE person_key=? AND status='completed'",
                           (key,))
        require(row is not None, 'There is no photo of them yet.', 404)
        return storage.path_of(self.database, row['file'])

    def request(self, key: str) -> dict:
        """Ask for their photo: the saved one if there is one, else one is queued (once)."""
        with self.database.connect(write=True) as connection:
            row = optional(connection, 'SELECT * FROM dating_photos WHERE person_key=?', (key,))
            if row and row['status'] != 'failed':
                return view(row)
            sheet, data, town = find(connection, key)
            built = inputs(sheet, data)
            decision = route(classify(built), backends.ordered(connection, enabled_only=True))
            if decision.refusal:
                raise DomainError(decision.refusal, 409, decision.code or 'refused')
            connection.execute(
                'INSERT INTO dating_photos (person_key, town, status, prompt, negative, seed, backend_id, created_at) '
                "VALUES (?, ?, 'queued', ?, ?, ?, ?, ?) ON CONFLICT(person_key) DO UPDATE SET status='queued', "
                'prompt=excluded.prompt, negative=excluded.negative, seed=excluded.seed, '
                'backend_id=excluded.backend_id, error=NULL, file=NULL, created_at=excluded.created_at',
                (key, town, built['prompt'], built['negative'], built['seed'], decision.target['id'],
                 self.database.now()))
            row = optional(connection, 'SELECT * FROM dating_photos WHERE person_key=?', (key,))
        self.images.wake()
        return view(row)

    def recover(self):
        """Photos cut off when the app closed can be asked for again."""
        with self.database.connect(write=True) as connection:
            connection.execute("UPDATE dating_photos SET status='failed', error=? WHERE status IN ('queued', 'running')",
                               ('The app closed before the photo was made. Ask again.',))

    def dispatch(self) -> list[asyncio.Task]:
        started = []
        with self.database.connect() as connection:
            for row in connection.execute("SELECT * FROM dating_photos WHERE status='queued' ORDER BY created_at"):
                row = dict(row)
                backend = optional(connection, 'SELECT * FROM image_backends WHERE id=?', (row['backend_id'],))
                if row['person_key'] in self.tasks or backend and (backend['blocked_reason'] or
                                                                   self.images.busy(backend)):
                    continue
                task = asyncio.get_running_loop().create_task(self.run(row, backend))
                self.tasks[row['person_key']] = (task, {'id': row['backend_id'], 'kind': backend and backend['kind']})
                task.add_done_callback(lambda _task, key=row['person_key']: self.tasks.pop(key, None))
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

    def finish(self, key: str, status: str, **fields):
        assignments = {'status': status, 'finished_at': self.database.now(), **fields}
        with self.database.connect(write=True) as connection:
            connection.execute(f"UPDATE dating_photos SET {', '.join(f'{name}=?' for name in assignments)} "
                               'WHERE person_key=?', (*assignments.values(), key))

    async def run(self, row: dict, backend: dict | None):
        key = row['person_key']
        request = {'prompt': row['prompt'], 'negative': row['negative']}
        if backend is None or not backend['enabled'] or not eligible(classify(request), backend):
            self.finish(key, 'failed', error='That image backend can no longer make this photo. Ask again.')
            return
        self.finish(key, 'running')
        width, height = size_for(backend['kind'], 'portrait')
        secret = self.vault.get(backend['credential_ref']) if backend['credential_ref'] else None
        job_id = f'dating-{identifier()}'
        image = ImageRequest(job_id, row['prompt'], row['negative'], row['seed'], width, height, backend,
                             decode(backend['config']), secret, storage.raw_directory(self.database))
        try:
            result = await self.images.adapters[backend['kind']].generate(image)
            stored = storage.store(self.database, job_id, result.data)
        except AdapterError as error:
            if error.code == 'auth':
                backends.block(self.database, backend['id'], error.message)
            self.finish(key, 'failed', error=error.message)
            return
        except Exception as error:  # noqa: BLE001 - a backend bug fails this photo, not the app.
            self.finish(key, 'failed', error=f'The image backend failed ({error}).')
            return
        if result.raw_path:
            with contextlib.suppress(OSError):
                result.raw_path.unlink()
        self.finish(key, 'completed', file=stored['file'])
