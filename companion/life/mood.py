"""Absence mood: a visible, resettable relationship state (PRD C6, M4).

When the user comes back after a long gap and the character has an absence trait (guilt over
absence, neediness or sulking), a mood record says so, with the trait's own intensity. The
length of the absence never raises the intensity above the trait, never adds work and never
touches product controls. Without such a trait nothing is recorded and the return is warm.
A mood applies only while the active character still has a qualifying trait, so removing the
trait stops it from the next reply. The user can reset it at any time.
"""
from datetime import timedelta

from companion.characters import require_current
from companion.clock import parse, stamp
from companion.database import decode, encode, identifier, one, optional
from companion.traits import ABSENCE_TRAITS, TRAIT_NAMES

ABSENCE_HOURS = 24
LASTS = timedelta(days=2)


def absence_traits(definition) -> list[dict]:
    return [trait for trait in definition.get('emotional_traits') or [] if trait['trait'] in ABSENCE_TRAITS]


def last_presence(connection, timeline_id) -> str | None:
    """The user's latest message or resume, whichever is later; a pause is not an absence."""
    message = optional(connection, "SELECT MAX(created_at) AS at FROM messages WHERE timeline_id=? AND role='user'",
                       (timeline_id,))
    resumed = optional(connection, 'SELECT MAX(ended_at) AS at FROM pauses')
    times = [value['at'] for value in (message, resumed) if value and value['at']]
    return max(times) if times else None


def note_return(connection, now) -> dict | None:
    """Called when the user returns. Idempotent per absence, so repeated calls never stack."""
    companion = require_current(connection)
    version, timeline_id = companion['version'], companion['active_timeline_id']
    traits = absence_traits(version['definition'])
    since = last_presence(connection, timeline_id)
    if not traits or since is None or now - parse(since) < timedelta(hours=ABSENCE_HOURS):
        return None
    if one(connection, 'SELECT paused_at FROM workspace_settings WHERE id=1')['paused_at']:
        return None
    timestamp = stamp(now)
    connection.execute(
        'INSERT OR IGNORE INTO relationship_moods (id, timeline_id, kind, away_from, away_until, intensity, traits, '
        "character_version_id, created_at, expires_at) VALUES (?, ?, 'absence', ?, ?, ?, ?, ?, ?, ?)",
        (identifier(), timeline_id, since, timestamp, max(trait['intensity'] for trait in traits), encode(traits),
         version['id'], timestamp, stamp(now + LASTS)))
    return active(connection, companion, now)


def active(connection, companion, now) -> dict | None:
    traits = absence_traits(companion['version']['definition'])
    if not traits:
        return None
    row = optional(connection, "SELECT * FROM relationship_moods WHERE timeline_id=? AND cleared_at IS NULL "
                   'AND expires_at>? ORDER BY created_at DESC LIMIT 1', (companion['active_timeline_id'], stamp(now)))
    if row is None:
        return None
    # The current traits decide the intensity, so lowering a trait softens an existing mood too.
    intensity = min(row['intensity'], max(trait['intensity'] for trait in traits))
    hours = (parse(row['away_until']) - parse(row['away_from'])).total_seconds() / 3600
    return {'id': row['id'], 'kind': row['kind'], 'intensity': intensity, 'away_from': row['away_from'],
            'away_until': row['away_until'], 'away_hours': round(hours), 'traits': [
                trait['trait'] for trait in traits], 'created_at': row['created_at'], 'expires_at': row['expires_at'],
            'recorded_traits': decode(row['traits'])}


def mood_text(mood) -> str:
    names = ' and '.join(TRAIT_NAMES[trait] for trait in mood['traits'])
    days = mood['away_hours'] / 24
    gap = f'about {round(days)} days' if days >= 1.5 else 'about a day'
    return (f'The user was away for {gap} and has just come back. Because of your {names}, you feel it '
            f"(intensity {mood['intensity']}/5): you may show it in character, briefly and in proportion. You do "
            'not know what they did while away and must not guess or accuse.')


def reset(database, mood_id) -> dict:
    with database.connect(write=True) as connection:
        one(connection, 'SELECT id FROM relationship_moods WHERE id=?', (mood_id,))
        connection.execute('UPDATE relationship_moods SET cleared_at=COALESCE(cleared_at, ?) WHERE id=?',
                           (database.now(), mood_id))
        return {'mood': active(connection, require_current(connection), database.clock.now())}
