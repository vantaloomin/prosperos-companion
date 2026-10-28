"""How eventful one world is: its own drama level, apart from the one in Settings > Realism.

Life settings follow the user from world to world (companion/worlds.py SHARED), so the Realism slider "Drama in your
world" is the same in all of them. A tester wanted more going on for Sett, alone in his League world, and less for
Spock on the Enterprise (2026-10-28). Each world can now keep a level of its own in `world_life`, a table that stays
in its own database and never travels. With none set, the world follows Realism, as before.

A companion alone in their world has nobody else's news to share the user's attention with, so storylines start
for them a little more often (`ALONE`, companion/life/storylines.py); the cap on how many run at once stays.
"""
from companion.database import optional

LEVELS = range(4)  # Quiet, realistic, dramatic, soap opera (companion/life/storylines.py LEVELS).
ALONE = 1.5


def own(connection) -> int | None:
    """This world's own level, or None when it follows Settings > Realism."""
    row = optional(connection, 'SELECT drama FROM world_life WHERE id=1')
    return row['drama'] if row else None


def level(connection) -> int:
    """The drama level life in this world runs at."""
    found = own(connection)
    if found is not None:
        return found
    row = optional(connection, 'SELECT drama FROM life_settings WHERE id=1')
    return row['drama'] if row else 1


def alone(connection) -> bool:
    row = optional(connection, 'SELECT COUNT(*) AS count FROM companions WHERE active_version_id IS NOT NULL')
    return bool(row) and row['count'] == 1


def change(connection, drama: int | None, timestamp: str):
    """Give this world its own level, or None to follow Realism again."""
    connection.execute('INSERT INTO world_life (id, drama, updated_at) VALUES (1, ?, ?) ON CONFLICT(id) '
                       'DO UPDATE SET drama=excluded.drama, updated_at=excluded.updated_at', (drama, timestamp))
