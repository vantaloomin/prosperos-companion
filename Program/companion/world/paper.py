"""The town paper: a short local paper for the companion's city, out every Sunday (the town paper, 2026-10-09).

It reports only what already happened or is already planned in the world, so it costs no model calls and two
reads of the same issue say the same thing: changes to the city (companion/world/changes.py), townsfolk who
reached a goal that week (companion/world/townsfolk.py), companions seen out at the city's venues, a gossip
column about companions who crossed paths with no names given (companion/life/encounters.py), and what's coming
up: annual events, holidays and the typical weather. Nothing private goes in: no storylines, no circle, no chat,
nothing from the secrets ledger, and companions only by where anyone could have seen them.

A period or fantasy city gets a gazette instead of a weekly; the wording stays plain either way.
"""
from datetime import date, timedelta

from companion.database import decode, many
from companion.world import changes, generators, townsfolk

TOWNSFOLK_PER_HOOD, MOST_TOWNSFOLK = 12, 3
MOST_NEWS, MOST_SEEN, MOST_GOSSIP = 5, 4, 2
# Places where being seen is public: a show, a festival, a game, a museum.
SEEN_KINDS = {'event', 'venue', 'stadium', 'museum', 'attraction', 'landmark', 'market', 'garden'}
WEEKDAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
HEADLINES = {
    'opening': ('{name} opens in {hood}', '{name} to open in {hood}'),
    'closing': ('{name} closes its doors', '{name} to close'),
    'renovation': ('{name} closes for work', '{name} to close for work'),
    'roadworks': ('Road works in {hood}', 'Road works coming to {hood}'),
    'news': ('Around the city', 'Around the city'),
}


def issue_date(today: date) -> date:
    """The Sunday on or before `today`: when this week's issue came out."""
    return today - timedelta(days=(today.weekday() + 1) % 7)


def title(data: dict) -> str:
    return f"The {data['name']} {'Weekly' if townsfolk.modern(data) else 'Gazette'}"


def issue(connection, data: dict, world, day: date) -> dict:
    """The issue out on the Sunday `day`, for the city `data`: the week up to it, and the week after."""
    week = (day - timedelta(days=6), day)
    talk = gossip(connection, data, week)
    return {'title': title(data), 'city': data['name'], 'date': day.isoformat(),
            'news': city_news(connection, data, week),
            'townsfolk': townsfolk_news(data, day),
            'seen': seen_around(connection, data, week, {(item['date'], item['place']) for item in talk}),
            'gossip': [{'text': item['text']} for item in talk],
            'ahead': coming_up(data, world, day)}


def in_week(value: str | None, week: tuple[date, date]) -> bool:
    return bool(value) and week[0].isoformat() <= value <= week[1].isoformat()


def city_news(connection, data: dict, week: tuple[date, date]) -> list[dict]:
    """Changes to the city announced, starting or ending that week, newest first."""
    hoods = {hood['id']: hood['name'] for hood in data['neighborhoods']}
    found = [change for change in changes.known(data, week[1], changes.stored(connection, data['id']))
             if any(in_week(change.get(key), week) for key in ('announced', 'starts', 'ends'))]
    found.sort(key=lambda change: (change['starts'], change['id']), reverse=True)
    result = []
    for change in found[:MOST_NEWS]:
        now, later = HEADLINES.get(change['kind'], HEADLINES['news'])
        headline = (later if change['starts'] > week[1].isoformat() else now).format(
            name=change['name'], hood=hoods.get(change['neighborhood'], data['name']))
        text = changes.change_text(change, data, week[1]).removeprefix('- ')
        result.append({'id': change['id'], 'headline': headline, 'text': sentence(text)})
    return result


def sample(data: dict) -> list[dict]:
    """The townsfolk the paper keeps an eye on: the first residents of every neighborhood."""
    people = []
    for hood in data['neighborhoods']:
        people += townsfolk.residents(data, hood['id'])[:TOWNSFOLK_PER_HOOD]
    return people


def townsfolk_news(data: dict, day: date) -> list[dict]:
    """Townsfolk who reached a goal that week, in a seeded order."""
    if not data.get('neighborhoods'):
        return []
    reached = []
    for sheet in sample(data):
        state = townsfolk.story(sheet, data, day)
        if state['beat'] == 'achieved':
            reached.append((sheet, state))
    reached.sort(key=lambda item: generators.unit(item[0]['key'], 'paper', day.isoformat()))
    return [{'key': sheet['key'], 'headline': sentence(state['line']),
             'text': f"{sheet['full']} ({sheet['role']}, {townsfolk.neighborhood_name(data, sheet['home'])}) had been "
                     f"trying to {state['reached'][-1]} for weeks."} for sheet, state in reached[:MOST_TOWNSFOLK]]


def companions_in(connection, data: dict) -> list[dict]:
    """Every companion living in this city: {id, name, timeline_id}."""
    from companion.world import newcomers
    rows = many(connection, 'SELECT c.id, c.active_timeline_id, v.definition FROM companions c JOIN '
                'character_versions v ON v.id=c.active_version_id WHERE c.active_timeline_id IS NOT NULL '
                'ORDER BY c.created_at, c.id')
    result = []
    for row in rows:
        definition = decode(row['definition'])
        if newcomers.city_for(connection, definition)['id'] == data['id']:
            result.append({'id': row['id'], 'name': definition['name'].strip(), 'timeline_id': row['active_timeline_id']})
    return result


def short_name(name: str) -> str:
    """'Kimberly S.': how a local paper names someone in a crowd shot."""
    words = name.split()
    return f'{words[0]} {words[-1][0]}.' if len(words) > 1 else name


def seen_around(connection, data: dict, week: tuple[date, date], hushed: set = frozenset()) -> list[dict]:
    """One public outing that week for each companion in the city: a show, a festival, a museum. Never one the
    gossip column is hinting at (`hushed`, as (date, place name)), which would give its two locals away."""
    result = []
    for person in companions_in(connection, data):
        rows = many(connection, "SELECT local_date, entry FROM life_agenda WHERE timeline_id=? AND subject='companion' "
                    "AND status='happened' AND entry IS NOT NULL AND local_date BETWEEN ? AND ? ORDER BY starts_at",
                    (person['timeline_id'], week[0].isoformat(), week[1].isoformat()))
        outings = [(row['local_date'], place) for row in rows
                   if isinstance(place := (decode(row['entry']) or {}).get('place'), dict)
                   and place.get('kind') in SEEN_KINDS and place.get('name')
                   and (row['local_date'], place['name']) not in hushed]
        if outings:
            day, place = outings[int(generators.unit(person['id'], 'paper', week[1].isoformat()) * len(outings))]
            result.append({'companion_id': person['id'], 'text': f"{short_name(person['name'])} was spotted at "
                           f"{place['name']} on {weekday(day)}."})
    return result[:MOST_SEEN]


def gossip(connection, data: dict, week: tuple[date, date]) -> list[dict]:
    """Companions who crossed paths that week, with no names: one item a day and place."""
    timelines = [person['timeline_id'] for person in companions_in(connection, data)]
    if len(timelines) < 2:
        return []
    rows = many(connection, 'SELECT DISTINCT met.local_date, met.place FROM townsfolk_encounters met JOIN life_agenda '
                "agenda ON agenda.timeline_id=met.timeline_id AND agenda.slot_key=met.slot_key AND agenda.subject='companion' "
                f"WHERE met.key LIKE 'cast:%' AND agenda.status='happened' AND met.timeline_id IN "
                f"({','.join('?' * len(timelines))}) AND met.local_date BETWEEN ? AND ? ORDER BY met.local_date DESC",
                (*timelines, week[0].isoformat(), week[1].isoformat()))
    return [{'date': row['local_date'], 'place': row['place'], 'text': f"Which two locals were spotted deep in conversation at {row['place']} on {weekday(row['local_date'])}? "
                     'This column has its suspicions.'} for row in rows[:MOST_GOSSIP]]


def coming_up(data: dict, world, day: date) -> dict:
    """The week after the issue: annual events and holidays by day, and the typical weather."""
    days = [day + timedelta(days=offset) for offset in range(1, 8)]
    events = [{'date': when.isoformat(), 'name': item['name'], 'text': sentence(item['summary'])}
              for when in days for item in world.happenings(data['id'], when)]
    holidays = [{'date': item['date'].isoformat() if isinstance(item['date'], date) else item['date'],
                 'name': item['name']} for item in generators.holidays(data, days[0], days[-1])]
    return {'events': events, 'holidays': holidays, 'weather': weather(data, days)}


def weather(data: dict, days: list[date]) -> str | None:
    """'Highs around 64°F, lows near 48°F. Rain likely Tuesday and Thursday.'"""
    found = [(when, generators.conditions(data, when)) for when in days]
    found = [(when, item) for when, item in found if item]
    if not found:
        return None
    high = round(sum(item['high_f'] for _when, item in found) / len(found))
    low = round(sum(item['low_f'] for _when, item in found) / len(found))
    wet = [WEEKDAYS[when.weekday()] for when, item in found if item['rain']]
    rain = f" Rain likely {' and '.join([', '.join(wet[:-1]), wet[-1]] if len(wet) > 1 else wet)}." if wet else \
        ' Dry all week.'
    return f'Highs around {high}°F, lows near {low}°F.{rain}'


def weekday(value: str) -> str:
    return WEEKDAYS[date.fromisoformat(value).weekday()]


def sentence(text: str) -> str:
    text = (text or '').strip()
    text = text[:1].upper() + text[1:]
    return text if not text or text[-1] in '.!?»' else f'{text}.'
