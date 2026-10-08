"""One focal companion per workspace, with versioned definitions (PRD C1)."""
import re

from companion.clock import zone
from companion.database import decode, encode, identifier, one, optional
from companion.errors import DomainError, require


def view(version: dict) -> dict:
    return {**version, 'definition': decode(version['definition'])}


def current(connection) -> dict | None:
    companion = optional(connection, 'SELECT * FROM companions WHERE slot=1')
    if companion is None:
        return None
    version = one(connection, 'SELECT * FROM character_versions WHERE id=?', (companion['active_version_id'],))
    return {**companion, 'version': view(version)}


def by_id(connection, companion_id: str) -> dict | None:
    """Any companion in the workspace, main or stepped back, with their active version (as `current`)."""
    companion = optional(connection, 'SELECT * FROM companions WHERE id=?', (companion_id,))
    if companion is None or companion['active_version_id'] is None:
        return None
    version = one(connection, 'SELECT * FROM character_versions WHERE id=?', (companion['active_version_id'],))
    return {**companion, 'version': view(version)}


def for_timeline(connection, timeline_id: str) -> dict | None:
    """The companion a timeline belongs to."""
    row = optional(connection, 'SELECT companion_id FROM timelines WHERE id=?', (timeline_id,))
    return by_id(connection, row['companion_id']) if row else None


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
