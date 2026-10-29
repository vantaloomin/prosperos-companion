"""Words that fit the era (Hit List #82): what the in-world screens and the app's own lines call things in a city of
another era. A letter instead of a message in Camelot, a note in 1895 London, the telephone in 1925 New York, comms
aboard a ship.

One table (world/data/era_words.json) gives every word for each era group: modern (today's words), historical
(Victorian, steampunk, frontier and the 1920s), fantasy (medieval and fantasy) and future (ships and stations). The
app picks the group from the city's era, and a city file's optional `words` block renames any word. Rules only: no
model reads or writes these, and the chat prompt is unchanged, since the companion already speaks in the city's era.

In a modern city of a world that runs in a past year, the table's `decades` block puts that decade's words over
today's (a snapshot, not a selfie, in the 1990s), under the same switch.

Only what the characters and the world say and show changes. Settings, setup, help and error messages keep today's
words, so help and bug reports stay readable. Settings > Appearance turns it off ("Period words in period cities").
"""
import json
import re
from functools import cache

from companion.world import catalog, decades

LONGEST = 80


@cache
def table() -> dict:
    return json.loads((catalog.DATA / 'era_words.json').read_text(encoding='utf-8'))


def group(city: dict | None) -> str:
    """The city's era group: modern, historical, fantasy or future."""
    return table()['groups'].get((city or {}).get('era') or 'modern', 'modern')


def words(city: dict | None, on: bool = True) -> dict[str, str]:
    """Every word for this city: today's, the era group's over them, the decade's in a modern city of a past year
    (Back when, companion/world/decades.py), then the city's own. Off, today's words."""
    found = table()['words']
    if not on:
        return dict(found['modern'])
    return found['modern'] | found[group(city)] | decades.words(table().get('decades') or {}, city) | \
        ((city or {}).get('words') or {})


def say(found: dict[str, str], key: str, **values: str) -> str:
    """One word or line, with its {name} filled in."""
    text = found[key]
    for name, value in values.items():
        text = text.replace('{' + name + '}', value)
    return text


def clean(data: dict) -> list[str]:
    """Check a city's `words` block in place: an unknown word, or a line that drops the {name} it needs, is left out
    with a note, and the city still loads."""
    block = data.get('words')
    if block is None:
        data.pop('words', None)
        return []
    if not isinstance(block, dict):
        data.pop('words', None)
        return ['Dropped the words block: it needs to map each word to what this city calls it.']
    notes, own = [], {}
    modern = table()['words']['modern']
    for key, value in block.items():
        if key not in modern:
            notes.append(f'Dropped the word "{key}": the app has no word by that name.')
        elif not isinstance(value, str) or not value.strip() or len(value.strip()) > LONGEST:
            notes.append(f'Dropped the word "{key}": it needs some text, at most {LONGEST} characters.')
        elif set(re.findall(r'\{\w+\}', modern[key])) - set(re.findall(r'\{\w+\}', value)):
            notes.append(f'Dropped the word "{key}": it needs {{name}} where the name goes.')
        else:
            own[key] = value.strip()
    if own:
        data['words'] = own
    else:
        data.pop('words', None)
    return notes


def for_world(connection) -> dict:
    """The words where the user lives in this world (their home city, else their companion's, else the first
    city), and whether period words are on (workspace_settings.period_words)."""
    from companion.characters import current
    from companion.database import settings
    from companion.life import where
    from companion.world import newcomers
    home = where.your_home(connection)
    companion = current(connection) if not home else None
    city = home[0] if home else newcomers.city_for(connection, companion['version']['definition']) if companion \
        else None
    on = bool(settings(connection).get('period_words', 1))
    return {'group': group(city) if on else 'modern', 'decade': decades.decade_of(city) if on else None, 'on': on,
            'words': words(city, on)}
