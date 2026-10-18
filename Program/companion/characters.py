"""One focal companion per workspace, with versioned definitions (PRD C1)."""
import re

from companion.clock import zone
from companion.database import decode, encode, identifier, many, one, optional
from companion.errors import DomainError, require


def view(version: dict) -> dict:
    return {**version, 'definition': decode(version['definition'])}


def current(connection) -> dict | None:
    companion = optional(connection, 'SELECT * FROM companions WHERE slot=1')
    if companion is None:
        return None
    version = one(connection, 'SELECT * FROM character_versions WHERE id=?', (companion['active_version_id'],))
    return with_chapters(connection, {**companion, 'version': view(version)})


def by_id(connection, companion_id: str) -> dict | None:
    """Any companion in the workspace, main or stepped back, with their active version (as `current`)."""
    companion = optional(connection, 'SELECT * FROM companions WHERE id=?', (companion_id,))
    if companion is None or companion['active_version_id'] is None:
        return None
    version = one(connection, 'SELECT * FROM character_versions WHERE id=?', (companion['active_version_id'],))
    return with_chapters(connection, {**companion, 'version': view(version)})


def with_chapters(connection, companion: dict) -> dict:
    """The companion with their life chapters on the active timeline applied to the definition (a new job, a move,
    a hobby: companion/life/chapters.py) and the weeks of shifts or gigs around now (companion/life/shifts.py), so
    everything that reads their life sees how it is now. The saved version itself is never rewritten, so a fork without
    the chapter or an undo brings the old life back."""
    from companion.life import shifts
    rows = many(connection, 'SELECT changes FROM life_chapters WHERE timeline_id=? AND undone_at IS NULL '
                'ORDER BY started_on, created_at', (companion.get('active_timeline_id') or '',))
    definition = companion['version']['definition']
    for row in rows:
        definition = apply_changes(definition, decode(row['changes']))
    if (definition.get('money') or {}).get('career') != (companion['version']['definition'].get('money') or {}).get('career'):
        definition = {**definition, 'schedule': relabeled(connection, definition)}
    # A move to another city (companion/life/moving_in.py) brings that city's clock.
    version = {**companion['version'], 'definition': definition, 'timezone': definition.get('timezone')
               or companion['version']['timezone']}
    # Their shifts or gigs week by week (companion/life/shifts.py), on top of the week as written.
    return shifts.with_rota(connection, {**companion, 'version': version} if rows else companion)


def relabeled(connection, definition: dict) -> list[dict]:
    """The schedule after a new job: a work block named for a career ("Software engineer") takes the new career's
    name; a block the user named themselves keeps it."""
    from companion.life.outings import city_data
    from companion.life.routine import slug
    from companion.world import catalog
    city = city_data(connection, definition)
    offered = catalog.careers_for(city) if city else {}
    career = offered.get((definition.get('money') or {}).get('career') or '')
    names = {item['name'].lower() for item in offered.values()}
    # The block keeps its key, so the days already planned stay its own.
    return [{**block, 'key': block.get('key') or slug(block['label']), 'label': career['name']}
            if career and block.get('kind') == 'work' and block.get('label', '').lower() in names else block
            for block in definition.get('schedule') or []]


def apply_changes(definition: dict, changes: dict) -> dict:
    found = dict(definition)
    if 'career' in changes:
        found['money'] = {**(found.get('money') or {}), 'career': changes['career']}
    if 'location' in changes:
        found['location'], found['near'] = changes['location'], ''
    for key in ('home_city', 'timezone'):  # Another city altogether (companion/life/moving_in.py).
        if key in changes:
            found[key] = changes[key]
    if 'interest' in changes and changes['interest'] not in (found.get('interests') or []):
        found['interests'] = [*(found.get('interests') or []), changes['interest']]
    for key in ('business', 'health'):  # Their own business, or a long-term condition (life/business.py, health_turns.py).
        if key in changes:
            found[key] = changes[key]
    # A class in their week, work gone from it or their own business's, evenings at a parent's (life/big_turns.py).
    if {'study', 'retired', 'business', 'caring'} & set(changes):
        from companion.life import big_turns
        found['schedule'] = big_turns.reshaped(found, changes)
    return found


def for_timeline(connection, timeline_id: str) -> dict | None:
    """The companion a timeline belongs to."""
    row = optional(connection, 'SELECT companion_id FROM timelines WHERE id=?', (timeline_id,))
    return by_id(connection, row['companion_id']) if row else None


def definition_for_timeline(connection, timeline_id: str) -> dict:
    """The active character definition of the companion a timeline belongs to, {} when there is none; a light read
    for wording (their pronouns), without their life chapters."""
    row = optional(connection, 'SELECT v.definition FROM timelines t JOIN companions c ON c.id=t.companion_id '
                   'JOIN character_versions v ON v.id=c.active_version_id WHERE t.id=?', (timeline_id,))
    return decode(row['definition']) if row else {}


def require_current(connection) -> dict:
    companion = current(connection)
    if companion is None:
        raise DomainError('Create a companion first.', 409)
    return companion


def create(database, definition) -> dict:
    with database.connect(write=True) as connection:
        return create_in(connection, database.now(), definition)


def create_in(connection, timestamp, definition, note='') -> dict:
    """The first companion, inside the caller's write transaction. One made without a name gets one that fits."""
    zone(definition.timezone)
    require(current(connection) is None, 'This workspace already has a companion.', 409)
    definition = named(connection, definition)
    companion_id, timeline_id = identifier(), identifier()
    connection.execute('INSERT INTO companions (id, created_at) VALUES (?, ?)', (companion_id, timestamp))
    version_id = insert_version(connection, companion_id, 1, definition, note, timestamp)
    connection.execute("INSERT INTO timelines (id, companion_id, status, created_at) VALUES (?, ?, 'active', ?)",
                       (timeline_id, companion_id, timestamp))
    connection.execute('UPDATE companions SET active_version_id=?, active_timeline_id=? WHERE id=?',
                       (version_id, timeline_id, companion_id))
    return current(connection)


def named(connection, definition):
    """The definition with a name: theirs, or one from their home city's names (the default city without one),
    matching the pronouns their description uses ("the world exists outside of User", Vanta 2026-10-08)."""
    if definition.name.strip():
        return definition
    from companion.world import generators, newcomers
    words = re.findall(r"[a-z]+", f'{definition.identity} {definition.personality} {definition.background}'.lower())
    she, he = sum(word in ('she', 'her', 'hers') for word in words), sum(word in ('he', 'him', 'his') for word in words)
    pronouns = 'she' if she > he else 'he' if he > she else None
    found = generators.name(newcomers.city_for(connection, definition.model_dump()), seed=identifier(), pronouns=pronouns)
    return definition.model_copy(update={'name': found['full']})


def revise(database, body) -> dict:
    """A new version applies from now on; earlier messages keep the version they used."""
    zone(body.definition.timezone)
    require(body.definition.name.strip(), 'Give them a name.', 422)
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        require(companion['active_version_id'] == body.expected_version_id,
                'The character changed since you opened it. Review the latest version.', 409)
        number = companion['version']['number'] + 1
        version_id = insert_version(connection, companion['id'], number, body.definition, body.note,
                                    database.now())
        connection.execute('UPDATE companions SET active_version_id=? WHERE id=?', (version_id, companion['id']))
        from companion.life import long_distance
        long_distance.settle_all(connection, database.clock.now())  # A move: visits planned for their old city.
        return current(connection)


def versions(database) -> list[dict]:
    with database.connect() as connection:
        companion = require_current(connection)
        rows = connection.execute('SELECT * FROM character_versions WHERE companion_id=? ORDER BY number',
                                  (companion['id'],)).fetchall()
        return [view(dict(row)) for row in rows]


def insert_version(connection, companion_id, number, definition, note, timestamp) -> str:
    version_id = identifier()
    connection.execute('INSERT INTO character_versions (id, companion_id, number, name, definition, relationship, '
                       'timezone, note, effective_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                       (version_id, companion_id, number, definition.name, encode(definition.model_dump()),
                        definition.relationship, definition.timezone, note, timestamp))
    return version_id
