"""Heading home after a meetup (Vanta, 2026-11-02): once an outing with the user ends, the companion is on their way
home for a while before their day picks up again, instead of jumping straight back to where their agenda has them.

Rules decide, no model: how far the place is from their home (the neighbourhoods' coordinates in the city data), and
how they get around there (the city's own `speeds`: on foot when it is close, else a way of getting about that city
has, picked steadily per outing). The chat strip and header say they are heading home and when they will be back,
and the chat context says they are texting from the road.
"""
from datetime import datetime, timedelta

from companion.clock import zone
from companion.life import onward, outings
from companion.world import catalog, generators

WALKABLE_KM = 1.2  # Closer than this, they walk.
UNKNOWN_KM = 2.5  # When a neighbourhood is not on the map.
SETTING_OFF = 5  # Minutes to say goodbye, pay, find the stop or the car.
SHORTEST, LONGEST = 10, 75  # Minutes.
# Ways of getting home across town, by the city's speeds keys; the first that city has, in this order, are the ones
# picked between.
LOCAL = ('car', 'rideshare', 'subway', 'tram', 'streetcar', 'light-rail', 'monorail', 'bus', 'bike-share', 'carriage',
         'horse', 'ferry', 'water-taxi', 'boat')
# How the chat context and the strip say it.
BY = {'walk': 'walking home', 'car': 'driving home', 'rideshare': 'in a cab home', 'subway': 'on the subway home',
      'tram': 'on the tram home', 'streetcar': 'on the streetcar home', 'light-rail': 'on the train home',
      'monorail': 'on the monorail home', 'bus': 'on the bus home', 'bike-share': 'cycling home',
      'carriage': 'in a carriage home', 'horse': 'riding home', 'ferry': 'on the ferry home',
      'water-taxi': 'on the water taxi home', 'boat': 'on the boat home'}
# Away from home, driving or riding: no texting until they are in.
HANDS_BUSY = ('car', 'horse')
# Their own place: they are already home. Turned away at the door: they never really left.
NO_TRIP = ('home',)


def hood_of(data: dict | None, name: str | None) -> dict | None:
    return next((hood for hood in (data or {}).get('neighborhoods') or [] if name and name in (hood['name'], hood['id'])
                 and 'lat' in hood), None)


def start_hood(connection, outing: dict, data: dict | None) -> dict | None:
    """Where they set off from: the place's neighbourhood, or the user's own at the user's place."""
    if outing['place']['kind'] == 'your-home':
        from companion.life import where
        found = where.your_home(connection)
        return found[1] if found and found[1] and 'lat' in found[1] else None
    return hood_of(data, outing['place'].get('neighborhood'))


def trip(connection, companion: dict, outing: dict) -> dict | None:
    """{'minutes', 'by'} for their way home from this outing, or None when there is none (at their own place)."""
    outing = onward.final(outing, companion['version']['timezone'])  # From the second place, when they moved on.
    # Dropping by at work (companion/life/drop_by.py): they stay at work.
    if outing['place']['kind'] in NO_TRIP or outing['activity'] == 'visit-work':
        return None
    definition = companion['version']['definition']
    data = outings.city_data(connection, definition)
    from companion.life import moving_in
    day = datetime.fromisoformat(outing['local_date']).date()
    home = hood_of(data, (moving_in.their_home(connection, companion, day) or {}).get('neighborhood'))
    start = start_hood(connection, outing, data)
    km = catalog.distance_km(start, home) if start and home else UNKNOWN_KM
    speeds = (data or {}).get('speeds') or {'walk': 4.5}
    ways = [way for way in LOCAL if way in speeds]
    by = 'walk' if km <= WALKABLE_KM or not ways else ways[int(generators.unit(f"home:{outing['id']}") * len(ways))]
    minutes = SETTING_OFF + km / max(speeds.get(by) or 4.5, 1) * 60
    return {'minutes': round(min(max(minutes, SHORTEST), LONGEST)), 'by': by}


def heading(connection, companion: dict, now: datetime) -> dict | None:
    """The outing they are on their way home from right now: {'outing', 'by', 'back_at' (UTC), 'back' ('18:10')}."""
    from companion.life import together
    timezone = companion['version']['timezone']
    since = (now.astimezone(zone(timezone)).date() - timedelta(days=1)).isoformat()
    for outing in reversed(outings.in_force(connection, companion['active_timeline_id'], since)):
        if outings.state(outing, timezone, now) != 'done' or outings.undoable_home(outing, now) or \
                together.turned_away(outing, timezone):
            continue
        found = trip(connection, companion, outing)
        end = outings.window(outing, timezone)[1]
        if found and end <= now < end + timedelta(minutes=found['minutes']):
            back = end + timedelta(minutes=found['minutes'])
            return {'outing': outing, 'by': found['by'], 'back_at': back,
                    'back': back.astimezone(zone(timezone)).strftime('%H:%M')}
        return None  # Only the latest outing that is over counts.
    return None


def view(connection, companion: dict, now: datetime) -> dict | None:
    """For the chat strip and header: how and until when."""
    found = heading(connection, companion, now)
    if not found:
        return None
    return {'outing_id': found['outing']['id'], 'place': found['outing']['place']['name'], 'by': found['by'],
            'words': BY.get(found['by'], 'on the way home'), 'back': found['back']}


def context_line(connection, companion: dict, now: datetime) -> tuple[str, str] | None:
    """The chat context while they are on their way home: what they are doing, and how they would text."""
    found = heading(connection, companion, now)
    if not found:
        return None
    outing = found['outing']
    place = 'your place' if outing['place']['kind'] == 'your-home' else outing['place']['name']
    words = BY.get(found['by'], 'on the way home')
    texting = ' You answer once you are in: write this as just home.' if found['by'] in HANDS_BUSY and \
        paced(connection) else \
        ' Any text you send now is from the road: short and on the go, not in person anymore.'
    line = (f"- You said goodbye to the user at {place} a little while ago and are {words} now, back around "
            f"{found['back']}.{texting}")
    return f"outing:{outing['id']}:heading", line


def paced(connection) -> bool:
    from companion.database import optional
    from companion.life import pacing
    life = optional(connection, 'SELECT paced_replies FROM life_settings WHERE id=1')
    return bool(pacing.ACTIVE and life and life['paced_replies'])


def held_until(connection, companion: dict, now: datetime) -> datetime | None:
    """Driving or riding home, a reply shows once they are in (companion/life/pacing.py)."""
    found = heading(connection, companion, now)
    return found['back_at'] if found and found['by'] in HANDS_BUSY and paced(connection) else None
