"""Townsfolk personality sliders (companion/world/personality.py) and the user's changes to them.

Every townsperson's sliders are rolled from their sheet; the user can change any of them on the person's profile
(Today > Around town > Edit). Changes are kept per town (a companion's own town seed, '' for the city's shared
townsfolk), so every companion living in that town meets the same person, and carry over when the townsperson
becomes a companion (companion/cast.py).
"""
from companion.database import decode, encode, many, optional
from companion.world import personality, townsfolk


def town_of(companion: dict | None) -> str:
    return (companion or {}).get('town_seed') or ''


def edited(connection, town: str, key: str) -> dict:
    row = optional(connection, 'SELECT sliders FROM townsfolk_personality WHERE town=? AND key=?', (town, key))
    return decode(row['sliders']) if row else {}


def all_edited(connection, town: str) -> dict[str, dict]:
    rows = many(connection, 'SELECT key, sliders FROM townsfolk_personality WHERE town=?', (town,))
    return {row['key']: decode(row['sliders']) for row in rows}


def sliders(sheet: dict, changed: dict | None) -> dict[str, dict]:
    return personality.for_sheet(townsfolk.drawn(sheet), sheet, changed)


def view(sheet: dict, changed: dict | None) -> dict:
    """What their profile shows: the summary chips, and the sliders Edit opens."""
    return {**personality.view(sliders(sheet, changed)), 'traits': personality.form_traits()}


def save(connection, town: str, key: str, changed: dict, timestamp: str):
    """Keep only the sliders the user set; the rest go back to the roll."""
    mine = {trait: value for trait, value in personality.clean(changed).items() if value['source'] == 'you'}
    if not mine:
        connection.execute('DELETE FROM townsfolk_personality WHERE town=? AND key=?', (town, key))
        return
    connection.execute('INSERT INTO townsfolk_personality (town, key, sliders, updated_at) VALUES (?, ?, ?, ?) '
                       'ON CONFLICT(town, key) DO UPDATE SET sliders=excluded.sliders, updated_at=excluded.updated_at',
                       (town, key, encode(mine), timestamp))
