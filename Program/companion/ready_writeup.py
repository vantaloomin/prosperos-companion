"""A companion made while "Set it up for me" downloads (Iris, v09-appearance-first-launch.md): the user saves what
they filled in, and once the model is ready it writes the rest, as the quick start would have.

Only fields still empty are filled, so anything the user wrote, before or during the download, stays theirs; the
result is a new version of the character, so it can be undone from the version list like any other edit.
"""
import logging

from companion import characters, drafting
from companion.errors import DomainError
from companion.models import CharacterDefinition, CharacterDraftRequest

log = logging.getLogger('companion')
NOTE = 'Written by your new chat model'
KEPT = ('name', 'relationship', 'home_city', 'timezone', 'starting_closeness')


def filled(saved: dict, drafted: dict) -> dict:
    """The saved definition with each field it left at its default taken from the draft."""
    empty = CharacterDefinition().model_dump()
    found = dict(saved)
    for key, value in drafted.items():
        if key not in KEPT and saved.get(key, empty.get(key)) == empty.get(key):
            found[key] = value
    return found


async def write_up(state, queued: dict) -> str:
    """Drafts the queued companion and saves the filled-in sheet; returns their name."""
    request = CharacterDraftRequest.model_validate(queued['request'])
    drafted = (await drafting.draft(state, request))['definition']
    with state.database.connect(write=True) as connection:
        companion = characters.by_id(connection, queued['companion_id'])
        if companion is None:
            raise DomainError('That companion is no longer here.', 404)
        version = companion['version']
        definition = CharacterDefinition.model_validate(filled(version['definition'], drafted))
        version_id = characters.insert_version(connection, companion['id'], version['number'] + 1, definition, NOTE,
                                               state.database.now())
        connection.execute('UPDATE companions SET active_version_id=? WHERE id=?', (version_id, companion['id']))
    return definition.name
