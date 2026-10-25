"""Take a companion to another world: one file with who they are and everything that happened between you.

A world is a database of its own (companion/worlds.py), so a companion cannot simply walk from one to the next. Saving
them to a file copies their rows out of this world, the same rows Delete would remove (companion/start_over.py:
CHARACTER and HISTORY, found the way `clear_own` finds one companion's rows), with the files those rows name: chat
pictures, voice notes, finished images, reference pictures and character sheets. Opening the file in another world
(Bring your characters) puts the rows back there, so their chats, memories, Closeness and relationship, kids, home,
wardrobe, look and voice arrive as they were.

What stays behind: work that was only queued (memory and self-fact jobs, notifications, unread marks, held replies),
the real-world lookups made for this world's city, the observer's notes, and LoRA training (runs, test pictures and
trained adapters, which run to hundreds of megabytes each; reference pictures come along, so an adapter can be trained
again). A row pointing at something that stayed behind loses that pointer when it may, or stays behind with it.

"The world exists outside of User" (Vanta, 2026-10-08): nothing is asked. They arrive as the main character, as an
imported character does, and when the new world is in another city they move there, with a job, home and routine
from that city's people (companion/imports/characters.py `life`) and its clock. Their friends and family stay where
they were, as people do when someone moves.

The file is a zip: `manifest.json` (a format marker, the app and schema it came from, who they are), `rows.json`
(each table's columns and rows) and `files/` at their workspace paths. Rows go back by column name, so a file from an
older or newer app loses only what the other side has no column for.
"""
import json
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from companion import characters, start_over, worlds
from companion.cast import step_back
from companion.clock import zone
from companion.database import many, optional
from companion.errors import DomainError, require
from companion.identity import APP_ID, SCHEMA_VERSION, VERSION
from companion.imports import characters as imported
from companion.life import home, moving_in
from companion.lora import files
from companion.models import CharacterDefinition

FORMAT = 'prospero-companion-carry'
FORMAT_VERSION = 1
SUFFIX = '.companion'
MANIFEST, ROWS = 'manifest.json', 'rows.json'
MAX_BYTES = 4 * 1024 * 1024 * 1024
# Rows that stay in the world they were made in (see the module's notes).
STAYS = frozenset({
    'memory_jobs', 'self_fact_jobs', 'notifications', 'chat_reads', 'away_messages', 'context_uses',
    'context_observations', 'observer_entries', 'lora_runs', 'lora_evaluations', 'lora_eval_images', 'lora_generations',
    'lora_gen_images', 'lora_adapters',
})
TABLES = tuple(table for table in start_over.HISTORY + start_over.CHARACTER if table not in STAYS)
# Folders a file in the archive may land in, as the workspace keeps them.
FOLDERS = ('images', 'pictures', 'voice-notes', 'lora/references')
# Their agenda is composed ahead from their city's places; in another city it is composed again.
AGENDA = ('life_agenda', 'agenda_cursors')


# Saving ---------------------------------------------------------------------------------------------

def columns_of(connection, table: str) -> list[str]:
    return [row[1] for row in connection.execute(f'PRAGMA table_info({table})')]


def gathered(connection, companion_id: str) -> dict[str, dict]:
    """Every table's rows of this companion, as {table: {'columns': [...], 'rows': [[...]]}}."""
    values = {'companion': companion_id}
    for name, select in start_over.SCOPE:
        connection.execute(f'CREATE TEMP TABLE {name} AS {select}', values)
    try:
        found = {}
        for table in TABLES:
            columns = columns_of(connection, table)
            where = start_over.OWN[table] if table in start_over.OWN else \
                'timeline_id IN gone_timelines' if 'timeline_id' in columns else 'companion_id=:companion'
            rows = [list(row) for row in connection.execute(f'SELECT * FROM {table} WHERE {where}', values)]  # noqa: S608
            if rows:
                found[table] = {'columns': columns, 'rows': rows}
        return pruned(connection, found)
    finally:
        for name, _select in start_over.SCOPE:
            connection.execute(f'DROP TABLE temp.{name}')


def pruned(connection, found: dict[str, dict]) -> dict[str, dict]:
    """Rows that point at a row the file does not carry lose that pointer, or stay behind when they need it; until
    nothing changes, since a row left behind can strand the rows that point at it."""
    links = {table: [(link[3], link[2], link[4] or 'id') for link in connection.execute(
        f'PRAGMA foreign_key_list({table})')] for table in found}
    required = {table: {row[1] for row in connection.execute(f'PRAGMA table_info({table})') if row[3]}
                for table in found}
    changed = True
    while changed:
        changed = False
        for table, data in found.items():
            before = (len(data['rows']), sum(value is None for row in data['rows'] for value in row))
            data['rows'] = [row for row in data['rows'] if still_pointing(found, table, row, links[table], required[table])]
            changed |= before != (len(data['rows']), sum(value is None for row in data['rows'] for value in row))
    return {table: data for table, data in found.items() if data['rows']}


def still_pointing(found: dict[str, dict], table: str, row: list, links: list, required: set) -> bool:
    """False when the row needs something left behind; a pointer it can do without is cleared in place."""
    columns = found[table]['columns']
    for column, parent, key in links:
        number = columns.index(column)
        if row[number] is None or row[number] in carried(found, parent, key):
            continue
        if column in required:
            return False
        row[number] = None
    return True


def carried(found: dict[str, dict], table: str, key: str) -> set:
    data = found.get(table)
    if not data or key not in data['columns']:
        return set()
    number = data['columns'].index(key)
    return {row[number] for row in data['rows']}


def file_names(connection, companion_id: str) -> list[str]:
    """The workspace files their rows name, as workspace-relative paths."""
    names = start_over.image_files(connection, companion_id)
    for row in many(connection, 'SELECT file, crop_file FROM lora_references WHERE companion_id=?', (companion_id,)):
        names += [f'lora/references/{name}' for name in (row['file'], row['crop_file']) if name]
    names += [f"images/sheets/{row['file']}" for row in many(
        connection, 'SELECT file FROM character_sheets WHERE companion_id=?', (companion_id,))]
    return sorted(set(names))


def save(database, companion_id: str) -> tuple[Path, str]:
    """Write their file to a temporary path; returns it and the name to download it as."""
    with database.connect() as connection:
        companion = characters.by_id(connection, companion_id)
        if companion is None:
            raise DomainError('That companion is no longer in this world.', 404)
        rows = gathered(connection, companion_id)
        names = file_names(connection, companion_id)
        city = companion['version']['definition'].get('home_city') or ''
    name = companion['version']['name']
    manifest = {'format': FORMAT, 'format_version': FORMAT_VERSION, 'app_id': APP_ID, 'app_version': VERSION,
                'schema_version': SCHEMA_VERSION, 'companion_id': companion_id, 'name': name, 'home_city': city,
                'saved_at': database.now(), 'counts': counts(rows)}
    workspace = database.path.parent
    handle = tempfile.NamedTemporaryFile(prefix='carry-', suffix=SUFFIX, dir=workspace, delete=False)
    handle.close()
    path = Path(handle.name)
    try:
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(MANIFEST, json.dumps(manifest, indent=1))
            archive.writestr(ROWS, json.dumps(rows, separators=(',', ':')))
            for relative in names:
                source = workspace / relative
                if source.is_file():
                    archive.write(source, f'files/{relative}', compress_type=zipfile.ZIP_STORED)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path, f'{safe_name(name)}{SUFFIX}'


def safe_name(name: str) -> str:
    kept = ''.join(char for char in name if char.isalnum() or char in ' -_').strip()
    return kept[:80] or 'companion'


def counts(rows: dict[str, dict]) -> dict[str, int]:
    """What the file holds, in the words the page uses."""
    def number(table, check=None):
        data = rows.get(table)
        if not data:
            return 0
        if check is None:
            return len(data['rows'])
        column, wanted = check
        index = data['columns'].index(column)
        return sum(row[index] == wanted for row in data['rows'])
    return {'messages': number('messages'), 'memories': number('memories', ('status', 'active')),
            'pictures': number('image_jobs', ('status', 'completed'))}


# Opening --------------------------------------------------------------------------------------------

async def receive(database, stream) -> dict:
    """The file as the request body, opened into this world."""
    workspace = database.path.parent
    handle = tempfile.NamedTemporaryFile(prefix='carry-in-', suffix=SUFFIX, dir=workspace, delete=False)
    handle.close()
    path = Path(handle.name)
    try:
        await files.receive(stream, path, MAX_BYTES)
        return bring(database, path)
    finally:
        path.unlink(missing_ok=True)


def read(path: Path) -> tuple[zipfile.ZipFile, dict, dict]:
    try:
        archive = zipfile.ZipFile(path)
        manifest = json.loads(archive.read(MANIFEST))
        require(isinstance(manifest, dict) and manifest.get('format') == FORMAT, 'This is not a saved companion.', 422)
        require(int(manifest.get('format_version', 0)) <= FORMAT_VERSION,
                'This companion was saved by a newer version of the app. Update the app to open it.', 422)
        rows = json.loads(archive.read(ROWS))
    except (zipfile.BadZipFile, KeyError, ValueError, TypeError) as error:
        raise DomainError('This is not a saved companion, or the file did not arrive whole.', 422) from error
    require(isinstance(rows, dict) and 'companions' in rows, 'This file holds no companion.', 422)
    return archive, manifest, rows


def bring(database, path: Path) -> dict:
    archive, manifest, rows = read(path)
    with archive:
        written = unpack(archive, database.path.parent)
        try:
            return arrive(database, manifest, rows)
        except BaseException:
            for target in written:
                target.unlink(missing_ok=True)
            raise


def unpack(archive: zipfile.ZipFile, workspace: Path) -> list[Path]:
    """Their files into this world's folders; a file already here by that name is the same file and stays."""
    written = []
    for entry in archive.infolist():
        relative = PurePosixPath(entry.filename)
        if entry.is_dir() or relative.parts[:1] != ('files',):
            continue
        inside = PurePosixPath(*relative.parts[1:])
        if '..' in inside.parts or inside.is_absolute() or not any(
                str(inside).startswith(f'{folder}/') for folder in FOLDERS):
            continue
        target = workspace / Path(*inside.parts)
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(target.name + '.partial')
        with archive.open(entry) as source, partial.open('wb') as out:
            while chunk := source.read(1024 * 1024):
                out.write(chunk)
        partial.replace(target)
        written.append(target)
    return written


def arrive(database, manifest: dict, rows: dict) -> dict:
    timestamp = database.now()
    companion_id = manifest.get('companion_id') or rows['companions']['rows'][0][0]
    with database.connect(write=True) as connection:
        require(optional(connection, 'SELECT id FROM companions WHERE id=?', (companion_id,)) is None,
                f"{manifest.get('name') or 'They'} already live in this world.", 409)
        connection.execute('PRAGMA defer_foreign_keys=ON')  # Checked at commit, once every row is in.
        focus = characters.current(connection)
        mine = rows['companions']
        if 'slot' in mine['columns']:  # Whoever is main character here stays so until they arrive.
            for row in mine['rows']:
                row[mine['columns'].index('slot')] = None
        skipped = insert(connection, rows)
        connection.execute('UPDATE companions SET slot=NULL, stepped_back_at=NULL, town_seed=? WHERE id=?',
                           ((focus or {}).get('town_seed') or '', companion_id))
        moved = settle(connection, database, companion_id, focus, timestamp)
        step_back(connection, timestamp, companion_id)
        return {'companion': characters.current(connection), 'name': manifest.get('name'), 'moved_to': moved,
                'stepped_back': focus['version']['name'] if focus else None,
                'counts': manifest.get('counts') or {}, 'left_out': skipped}


def insert(connection, rows: dict) -> list[str]:
    """Each table's rows by the columns both sides have. A table this app does not have, or whose required columns the
    file lacks, is left out; its name is returned."""
    skipped = []
    for table, data in rows.items():
        if table not in TABLES or not isinstance(data, dict):
            continue
        have = columns_of(connection, table)
        needed = {row[1] for row in connection.execute(f'PRAGMA table_info({table})') if row[3] and row[4] is None
                  and not row[5]}
        sent = [column for column in data.get('columns', []) if column in have]
        if not have or not needed <= set(sent):
            skipped.append(table)
            continue
        positions = [data['columns'].index(column) for column in sent]
        marks = ', '.join('?' for _ in sent)
        connection.executemany(f'INSERT INTO {table} ({", ".join(sent)}) VALUES ({marks})',  # noqa: S608
                               ([row[number] for number in positions] for row in data['rows']))
    return skipped


def settle(connection, database, companion_id: str, focus: dict | None, timestamp: str) -> str | None:
    """In another city they move to this world's, as a companion moving to the user's city does
    (companion/life/moving_in.py): its clock, the same job there or one like it, a neighborhood and a home there, and
    the coworkers left at the old job. Who they are stays as written. Returns the city's name, or None when they already
    live here."""
    companion = characters.by_id(connection, companion_id)
    definition = companion['version']['definition']
    here = worlds.city_of(connection)
    if definition.get('home_city') in (None, '', here['id'], here['name']):  # No city of their own: wherever the world is.
        return None
    connection.execute('UPDATE companions SET townsfolk_key=NULL WHERE id=?', (companion_id,))  # Nobody's sheet here.
    card = {'name': companion['version']['name'], 'description': definition.get('background') or '',
            'personality': definition.get('personality') or ''}
    hood = imported.life(connection, database, card, focus).get('location')  # A neighborhood their sort live in.
    changes = moving_in.moved_to(definition, here) | {'home_city': here['id']} | ({'location': hood} if hood else {})
    revised = CharacterDefinition.model_validate(characters.apply_changes(definition, changes))
    number = optional(connection, 'SELECT MAX(number) AS top FROM character_versions WHERE companion_id=?',
                      (companion_id,))['top']
    version_id = characters.insert_version(connection, companion_id, number + 1, revised,
                                           f"Moved to {here['name']} from another world.", timestamp)
    connection.execute('UPDATE companions SET active_version_id=? WHERE id=?', (version_id, companion_id))
    rehome(connection, characters.by_id(connection, companion_id), here, database.clock.now())
    for table in AGENDA:
        connection.execute(f'DELETE FROM {table} WHERE timeline_id IN '  # noqa: S608 - names from AGENDA
                           '(SELECT id FROM timelines WHERE companion_id=?)', (companion_id,))
    return here['name']


def rehome(connection, companion: dict, city: dict, now) -> None:
    """Their old home ends yesterday and one in the new city begins today; coworkers stay at the old job."""
    timeline_id = companion['active_timeline_id']
    day = now.astimezone(zone(city.get('timezone') or 'UTC')).date()
    for item in home.items_on(connection, timeline_id, day):
        if item['kind'] == 'home':
            connection.execute('UPDATE home_items SET until=? WHERE id=?', (day.isoformat(), item['id']))
    place = home.place_item(f'home:{timeline_id}:carried:{day.isoformat()}', companion['version']['definition'], city)
    home.insert_item(connection, timeline_id, place, 'change', day, now)
    moving_in.leave_behind(connection, companion, now)
