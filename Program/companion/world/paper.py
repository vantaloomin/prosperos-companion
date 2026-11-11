"""The town paper: a short local paper for the companion's city, out every Sunday (the town paper, 2026-10-09).

It reports only what already happened or is already planned in the world, so it costs no model calls and two
reads of the same issue say the same thing: changes to the city (companion/world/changes.py), townsfolk who
reached a goal that week (companion/world/townsfolk.py), who left town, retired or took over a place's work and
which couples had a baby (companion/world/turnover.py, companion/world/couples.py), companions seen out at the city's venues, a gossip
column about companions who crossed paths with no names given (companion/life/encounters.py), and what's coming
up: annual events, holidays and the typical weather. Someone in a companion's circle who lived in the city and passed
away gets an obituary, as anyone in town would (companion/life/loss.py). Nothing else private goes in: no storylines,
no other circle news, no chat, nothing from the secrets ledger, and companions only by where anyone could have seen
them.

A period or fantasy city gets a gazette instead of a weekly; the wording stays plain either way.
"""
from datetime import date, timedelta

from companion.database import decode, many
from companion.world import changes, couples, generators, skies, temperature, townsfolk, turnover

TOWNSFOLK_PER_HOOD, MOST_GOAL_STORIES, MOST_COMINGS = 12, 1, 3
MOST_NEWS, MOST_SEEN, MOST_GOSSIP, MOST_COUPLES, MOST_POLITICS = 5, 4, 2, 3, 5
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
    """The issue out on the Sunday `day`, for the city `data`: the week up to it, and the week after. Engagements and
    weddings lead with the user's own (companion/life/wedding.py)."""
    from companion.life import ages, loss, politics, wedding
    week = (day - timedelta(days=6), day)
    # Townsfolk are as old as Around town says: from the day the town started getting older (companion/life/ages.py).
    data = {**data, 'began': ages.town_began(connection)}
    talk = gossip(connection, data, week)
    mine = {**data, 'companions': companion_keys(connection)}
    return {'title': title(data), 'city': data['name'], 'date': day.isoformat(),
            'news': city_news(connection, data, week),
            'townsfolk': [*loss.paper_items(connection, data, week), *townsfolk_news(data, day),
                          *comings_and_goings(mine, week)],
            'couples': [*wedding.paper_items(connection, data, week), *couples_news(mine, week)][:MOST_COUPLES + 1],
            'seen': seen_around(connection, data, week, {(item['date'], item['place']) for item in talk}),
            'gossip': [{'text': item['text']} for item in talk],
            # Local politics (companion/life/politics.py): what happened in each issue, factions falling out.
            'politics': politics.paper_items(connection, data, week)[:MOST_POLITICS],
            'ahead': coming_up(data, world, day, skies.level_of(connection), temperature.chosen(connection))}


def companion_keys(connection) -> tuple[str, ...]:
    """The townsfolk keys companions were made from: no engagement, wedding or baby of theirs is announced
    (companion/world/couples.py)."""
    return tuple(row['townsfolk_key'] for row in many(
        connection, "SELECT townsfolk_key FROM companions WHERE COALESCE(townsfolk_key, '')!=''"))


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


def sample(data: dict, day: date | None = None) -> list[dict]:
    """The townsfolk the paper keeps an eye on: the first residents of every neighborhood."""
    people = []
    for hood in data['neighborhoods']:
        people += townsfolk.residents(data, hood['id'], day=day)[:TOWNSFOLK_PER_HOOD]
    return people


def townsfolk_news(data: dict, day: date) -> list[dict]:
    """A townsperson who reached a goal that week, picked in a seeded order: one story an issue, so the paper reads
    like a paper and not a list of hobby wins, and only a goal the town could see (`townsfolk.newsworthy`): a race or a
    mural, not a bird list or a rainy-day fund. It says how long the goal really took (`span`) and its wording is
    drawn from a few shapes (`GOAL_STORIES`) so week after week doesn't read the same."""
    if not data.get('neighborhoods'):
        return []
    reached = []
    for sheet in sample(data, day):
        state = townsfolk.story(sheet, data, day)
        if state['beat'] == 'achieved' and townsfolk.newsworthy(data, state['done_id']):
            reached.append((sheet, state))
    reached.sort(key=lambda item: generators.unit(item[0]['key'], 'paper', day.isoformat()))
    return [{'key': sheet['key'], 'headline': sentence(state['line']), 'text': goal_text(data, sheet, state, day)}
            for sheet, state in reached[:MOST_GOAL_STORIES]]


# How a goal story reads: {full}, {role}, {hood}, {goal}, {span} ("for about two months"), {took} ("about two months").
GOAL_STORIES = (
    '{full} ({role}, {hood}) had been trying to {goal} {span}.',
    'It took {full} ({role}, {hood}) {took} to {goal}.',
    '{full} ({role}, {hood}) set out to {goal} {ago}.',
    'Neighbors in {hood} say {full} ({role}) had been working to {goal} {span}.',
)


def span(weeks: int) -> tuple[str, str, str]:
    """('for about two months', 'about two months', 'about two months ago') for a goal that took `weeks` weeks."""
    if weeks <= 1:
        took = 'a week'
    elif weeks <= 2:
        took = 'a couple of weeks'
    elif weeks <= 5:
        took = f"{('three', 'four', 'five')[weeks - 3]} weeks"
    elif weeks <= 7:
        took = 'about a month and a half'
    elif weeks <= 11:
        took = 'about two months'
    elif weeks <= 15:
        took = 'about three months'
    elif weeks <= 30:
        took = 'about half a year'
    elif weeks <= 70:
        took = 'about a year'
    else:
        took = 'years'
    return (f'for {took}', took, f'{took} ago')


def goal_text(data: dict, sheet: dict, state: dict, day: date) -> str:
    """The story under a goal headline, in one of the shapes from `GOAL_STORIES`, seeded by person and issue."""
    shape = GOAL_STORIES[int(generators.unit(sheet['key'], 'paper-goal-shape', day.isoformat()) * len(GOAL_STORIES))]
    lasted, took, ago = span(state.get('took', 4))
    return shape.format(full=sheet['full'], role=sheet['role'], hood=townsfolk.neighborhood_name(data, sheet['home']),
                        goal=state['reached'][-1], span=lasted, took=took, ago=ago)


def couples_news(data: dict, week: tuple[date, date]) -> list[dict]:
    """Townsfolk who got engaged or married that week (companion/world/couples.py), in a seeded order."""
    if not data.get('neighborhoods'):
        return []
    found = [(sheet, item) for sheet in sample(data, week[1]) for item in couples.events(sheet, data, week)]
    found.sort(key=lambda pair: generators.unit(pair[0]['key'], 'paper-couple', week[1].isoformat()))
    # "got married" today; "were wed" in older eras ("got wed" reads wrong).
    wed, were = ('married', 'got married') if townsfolk.modern(data) else ('wed', 'were wed')
    result = []
    for sheet, item in found[:MOST_COUPLES]:
        hood = townsfolk.neighborhood_name(data, sheet['home'])
        if item['what'] == 'engaged':
            headline, text = (f"{sheet['name']} and {item['partner']['name']} are engaged.",
                              f"{sheet['full']} ({sheet['role']}, {hood}) and {item['partner']['full']} announced "
                              'their engagement.')
        else:
            headline, text = (f"{sheet['name']} and {item['partner']['name']} {were}.",
                              f"{sheet['full']} ({sheet['role']}, {hood}) and {item['partner']['full']} {wed} on "
                              f"{WEEKDAYS[item['day'].weekday()]}.")
        result.append({'key': f"{sheet['key']}:{item['what']}", 'headline': headline, 'text': text})
    return result


def comings_and_goings(data: dict, week: tuple[date, date]) -> list[dict]:
    """Who left their place or their street that week, who took over, and the couples who had a baby, in a seeded
    order: the staff at every place and the residents the paper keeps an eye on."""
    if not data.get('neighborhoods'):
        return []
    weeks = range(townsfolk.week_of(week[0]), townsfolk.week_of(week[1]) + 1)
    found = [item for place in data['places'] for slot in range(townsfolk.everyone(data, place))
             if townsfolk.staffed(data, place, slot)
             for item in moves(data, townsfolk.place_terms(data, place, slot, weeks[-1]), weeks,
                               lambda generation, slot=slot, place=place:
                               townsfolk.person(data, place, slot + turnover.STRIDE * generation))]
    for hood in data['neighborhoods']:
        for slot in range(min(TOWNSFOLK_PER_HOOD, townsfolk.resident_count(data, hood['id']))):
            found += moves(data, townsfolk.hood_terms(data, hood['id'], slot, weeks[-1]), weeks,
                           lambda generation, slot=slot, hood=hood:
                           townsfolk.resident(data, hood['id'], slot + turnover.STRIDE * generation))
    found += [baby_item(data, sheet, item) for sheet in sample(data, week[1]) for item in couples.babies(sheet, data, week)]
    found.sort(key=lambda item: generators.unit(item['key'], 'paper-comings', week[1].isoformat()))
    return found[:MOST_COMINGS]


def moves(data: dict, terms: list, weeks: range, sheet_of) -> list[dict]:
    """Each departure and arrival in a spot during these weeks, as paper items. Never the user's own townsperson."""
    result = []
    for term in terms:
        if term.left in weeks and (sheet := sheet_of(term.generation))['key'] != data.get('you'):
            result.append(departure(data, sheet, term.why, couples.age_on(sheet, data, turnover.week_day(term.left))))
        if term.arrived in weeks and (sheet := sheet_of(term.generation))['key'] != data.get('you'):
            result.append(arrival(data, sheet))
    return result


def where(data: dict, sheet: dict) -> str:
    """'the baker at Crumb & Co' or 'of Canton'."""
    if sheet['kind'] == 'resident':
        return f"of {townsfolk.neighborhood_name(data, sheet['home'])}"
    return f"the {sheet['role']} at {sheet['place']['name']}"


def departure(data: dict, sheet: dict, why: str, age: int | None = None) -> dict:
    """A townsperson who left this week; one who passed away gets an obituary (companion/life/loss.py)."""
    from companion.life import loss
    headline = {'retired': f"{sheet['name']} retires.", 'passed': f"{sheet['full']} has died.",
                'new job': f"{sheet['name']} moves on.", 'moved': f"Farewell to {sheet['name']}."}[why]
    if why == 'passed':
        return {'key': f"{sheet['key']}:left", 'headline': headline, 'obituary': True,
                'text': loss.obituary(sheet['full'], where(data, sheet), age, sheet['key'], sheet.get('pronouns', ''))}
    return {'key': f"{sheet['key']}:left", 'headline': headline,
            'text': sentence(f"{sheet['full']}, {where(data, sheet)}, {turnover.gone_text(why, '')} this week")}


def arrival(data: dict, sheet: dict) -> dict:
    if sheet['kind'] == 'resident':
        hood = townsfolk.neighborhood_name(data, sheet['home'])
        job = f" ({sheet['occupation']})" if sheet['occupation'] else ''
        return {'key': f"{sheet['key']}:arrived", 'headline': f'A new neighbor in {hood}.',
                'text': f"{sheet['full']}{job} has moved to {hood}."}
    return {'key': f"{sheet['key']}:arrived", 'headline': f"New {sheet['role']} at {sheet['place']['name']}.",
            'text': f"{sheet['full']} has taken over as the {sheet['role']} there."}


def baby_item(data: dict, sheet: dict, item: dict) -> dict:
    hood = townsfolk.neighborhood_name(data, sheet['home'])
    return {'key': f"{sheet['key']}:baby:{item['day'].isoformat()}",
            'headline': f"A baby for {sheet['name']} and {item['partner']['name']}.",
            'text': f"{sheet['full']} ({sheet['role']}, {hood}) and {item['partner']['full']} welcomed a baby."}


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


def coming_up(data: dict, world, day: date, level: int = skies.TRUE_TO_LIFE, unit: str = 'F') -> dict:
    """The week after the issue: annual events and holidays by day, and the weather (at this world's Weather step)."""
    days = [day + timedelta(days=offset) for offset in range(1, 8)]
    events = [{'date': when.isoformat(), 'name': item['name'], 'text': sentence(item['summary'])}
              for when in days for item in world.happenings(data['id'], when)]
    holidays = [{'date': item['date'].isoformat() if isinstance(item['date'], date) else item['date'],
                 'name': item['name']} for item in generators.holidays(data, days[0], days[-1])]
    return {'events': events, 'holidays': holidays, 'weather': weather(data, days, level, unit)}


# The week's weather in the paper: the wet and foggy days by name, in this order.
OUTLOOK = (('rain', 'Rain'), ('storm', 'Storms'), ('snow', 'Snow'), ('fog', 'Fog'))


def weather(data: dict, days: list[date], level: int = skies.TRUE_TO_LIFE, unit: str = 'F') -> str | None:
    """'Highs around 64°F, lows near 48°F. Rain Tuesday and Wednesday. Storms Thursday.'"""
    found = [(when, generators.conditions(data, when, level)) for when in days]
    found = [(when, item) for when, item in found if item]
    if not found:
        return None
    high = temperature.text(sum(item['high_f'] for _when, item in found) / len(found), unit)
    low = temperature.text(sum(item['low_f'] for _when, item in found) / len(found), unit)
    spells = [f' {label} {named([WEEKDAYS[when.weekday()] for when, item in found if item["sky"] == sky])}.'
              for sky, label in OUTLOOK if any(item['sky'] == sky for _when, item in found)]
    dry = '' if any(item['rain'] for _when, item in found) else ' Dry all week.'
    return f"Highs around {high}, lows near {low}.{''.join(spells)}{dry}"


def named(days: list[str]) -> str:
    """'Tuesday', 'Tuesday and Thursday', 'Monday, Tuesday and Friday'."""
    return ' and '.join([', '.join(days[:-1]), days[-1]]) if len(days) > 1 else days[0]


def weekday(value: str) -> str:
    return WEEKDAYS[date.fromisoformat(value).weekday()]


def sentence(text: str) -> str:
    text = (text or '').strip()
    text = text[:1].upper() + text[1:]
    return text if not text or text[-1] in '.!?»' else f'{text}.'
