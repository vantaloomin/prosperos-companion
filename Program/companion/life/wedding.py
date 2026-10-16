"""Engagement and wedding (Hit List #66, v0.13 Life Together): the proposal, the ring, planning the wedding and the day
itself.

The app decides, the user overrides ("the world exists outside of User", Vanta 2026-10-08):

- Once a romance has been living together long enough, the consequence engine decides when the companion proposes
  (the "engaged" step's `steps:when`, companion/life/steps.py, by the Relationship pace slider). It is a scripted
  evening, never a text: on the day they invite the user out to one of their favourite places (the place the two of
  them have been to most, else a date spot they like), without giving anything away (a first text,
  companion/life/openers.py, which books the outing), buy a ring from their own money (the city's customs and their pay
  set it) and ask over that evening, in person by v0.12's rules. The user's answer is read from the chat the way every
  step's is: yes, they are engaged; no keeps things where they were, with a rough spell; no answer counts as not yet.
  The user can propose too ("will you marry me?"); the engine decides their answer (`steps:answer`).
- The engagement plans a wedding with no question asked (`plan`): how big (the engine's `wedding:size`, from their pay,
  how outgoing they are and how many people they have), the day (months ahead by the city's customs and the pace, on
  its usual weekday), a venue in their city, a budget in its money (their share is paid from savings on the day), and
  a guest list from both circles: their family and friends, the people the user has told them about, and the user's
  other companions. It shows on the Character page's Life admin panel, where the user can move the day, pick another
  venue, change the size or leave a guest off; the planning (booking the venue, the invitations, the fittings) goes on
  the Life admin calendar as it comes up.
- The wedding is a big outing with the guests (companion/life/outings.py), in person, through the customs of the city's
  culture and era ("Customs" in companion/world/data/wedding.json): the order of the day, what they wear and the words.
  Once it is over they are married (the "married" step, an anniversary from then on); the user's best friends among
  their other companions have stood up at a wedding; there is a wedding photo on the feed (safe wording, the usual
  checks), a scrapbook page, and a notice in the town paper. Names never change unless the user edits them.

No new slider: the Relationship pace slider decides. No model decides anything: the model only puts it in words. Odds
show under Hidden values ("Why it went this way").
"""
import json
import random
import re
from datetime import date, datetime, timedelta
from functools import cache

from companion import consequences
from companion.clock import stamp, zone
from companion.database import decode, encode, identifier, many, one, optional
from companion.errors import require
from companion.life import admin, circle, money, outings, steps
from companion.life.upkeep import days_ago
from companion.world import catalog, generators

ACTIVE = True
# The invitation to the evening they propose, as a first text; off in most tests (tests/conftest.py).
FIRST_TEXTS = True
STEP = 'engaged'
INVITE_HOURS = (10, 21)
# A planned proposal that could not go out in this long gives way: the ask lapses and comes back weeks later.
LAPSE_DAYS = 30
# Where they propose: a favourite place of these kinds, and the outing it makes there.
PROPOSE_KINDS = {'restaurant': 'dinner', 'inn': 'dinner', 'tavern': 'dinner', 'park': 'walk', 'garden': 'walk',
                 'landmark': 'walk', 'beach': 'walk', 'trail': 'walk'}
PROPOSE_AT = {'dinner': '19:30', 'walk': '18:00'}
# The preferred evening: a Friday or a Saturday at least two days on.
PROPOSE_DAYS = (4, 5)
SIZES = ('small', 'proper', 'big')
SIZE_WORDS = {'small': 'a small wedding', 'proper': 'a proper wedding', 'big': 'a big wedding'}
SIZE_LABELS = {'small': 'Small', 'proper': 'A proper wedding', 'big': 'Big'}
# The engagement is at least this long, whatever the customs say, and the wedding moves at most this far for a clash.
SOONEST = 30
CLASH_WEEKS = 8
# The pace slider stretches or shortens the engagement (0 and 1 slow, 2 true to life, 3 fast).
PACE_STRETCH = (1.25, 1.25, 1.0, 0.75)
# Who in their circle comes: family always, friends by the size of it.
PARTNERS = {'partner', 'wife', 'husband', 'girlfriend', 'boyfriend', 'fiancée', 'fiancé', 'ex', 'spouse'}
SMALL_FRIENDS = 3
# Places nobody marries at, whatever their kind (a concert or music hall is a "hall" by name only).
NOT_VENUES = re.compile(r'\b(?:station|hospital|clinic|campus|transit|airport|stadium|arena|gym|fitness|library|'
                        r'prison|jail|court|police|school|office|parking|mall|outlet|pizza|burger|pancake|sandwich|'
                        r'taco|hot dog|diner|deli|food hall|murals?|street|avenue|paseo|surgical|music hall|symphony|concert|'
                        r'festival hall)\b', re.IGNORECASE)
# Words in a place's description that mark it as somewhere people marry ("Victorian glass houses", "a 1926 ballroom").
WEDDING_WORDS = re.compile(r'\b(?:chapel|church|cathedral|garden|conservatory|ballroom|mansion|manor|estate|winery|'
                           r'pavilion|terrace|lighthouse|temple|shrine|great hall|opera hall|castle|palace|glass ?houses?)',
                           re.IGNORECASE)
# Restaurants and taverns host a wedding only now and then, whatever their name says ("Crab House").
EATERIES = {'restaurant', 'tavern'}
# How likely each kind of place is when nothing in its words says weddings: a park or a garden often, a restaurant or
# a music club hardly ever.
VENUE_KINDS = {'garden': 1.0, 'park': 0.8, 'landmark': 0.8, 'temple': 1.0, 'inn': 0.8, 'museum': 0.5, 'beach': 0.4,
               'restaurant': 0.08, 'venue': 0.08, 'tavern': 0.3}
# Outdoor places, kept out of a wedding in a month whose typical high is below COLD_F (a park in a Chicago February).
OUTDOOR = {'garden', 'park', 'beach'}
OUTDOOR_NAMES = re.compile(r'\b(?:gate|lighthouse|fountain|statue|bridge|plaza|square|pier|monument|beach|park|'
                           r'gardens?|lawn|meadow|trail|lakefront|waterfront|promenade|fort|harbou?r)\b', re.IGNORECASE)
COLD_F = 55
VENUE = '~venue'
SHOWN_GUESTS = 8
# How long the ceremony takes at the start of the day, in minutes.
CEREMONY = 40
MARRIED = 'married'


@cache
def bank() -> dict:
    return json.loads((catalog.DATA / 'wedding.json').read_text(encoding='utf-8'))


def local_today(companion: dict, now: datetime) -> date:
    return now.astimezone(zone(companion['version']['timezone'])).date()


def first(name: str) -> str:
    return name.split()[0] if name.split() else name


def long_date(day: str, year: bool = True) -> str:
    found = date.fromisoformat(day)
    return f"{found:%A}, {found.day} {found:%B}" + (f' {found.year}' if year else '')


# Customs ------------------------------------------------------------------------------------------------------------

def culture_of(data: dict | None) -> str:
    """The customs a wedding follows: the city's calendar (us, uk, japan ...), else its era group."""
    found = bank()['customs']
    key = catalog.calendar_id(data) if data else None
    return key if key in found else admin.era_group(data)


def customs(culture: str) -> dict:
    found = bank()['customs']
    return found.get(culture) or found['modern']


def pronoun_key(definition: dict) -> str:
    from companion.world import looks
    return {'she/her': 'she', 'he/him': 'he'}.get(looks.pronouns_of(definition), 'they')


def attire(definition: dict, culture: str) -> str:
    """What they wear on the day, for the wedding photo: 'a white wedding dress'."""
    return customs(culture)['attire'][pronoun_key(definition)]


# The proposal ---------------------------------------------------------------------------------------------------------

def proposals(connection, timeline_id: str, statuses: tuple[str, ...]) -> list[dict]:
    marks = ','.join('?' * len(statuses))
    return many(connection, f'SELECT * FROM proposals WHERE timeline_id=? AND status IN ({marks}) ORDER BY created_at',
                (timeline_id, *statuses))


def ring_for(companion: dict, culture: str) -> tuple[str, float]:
    """(the ring in words, what it costs in the city's money): the customs' ring for their pay tier, priced in months
    of their take-home. Nothing where money does not apply."""
    found = money.profile(companion['version']['definition'])
    ring = customs(culture)['ring']
    tier = found.tier if found else 1
    words = ring['rings'][min(tier, len(ring['rings']) - 1)]
    return words, round(money.monthly_share(found) * ring['months'], 2) if found else 0.0


def follow_proposals(connection, companion: dict, now: datetime) -> None:
    """A proposal for each "engaged" ask they planned; one whose ask moved on gives way, one that couldn't go out in
    a month lapses (they bring it up again weeks later), a called-off evening lapses, and an evening that ended with
    no reply written during it still had the question asked."""
    timeline_id, timestamp, today = companion['active_timeline_id'], stamp(now), local_today(companion, now)
    taken = {row['ask_id'] for row in many(connection, 'SELECT ask_id FROM proposals WHERE timeline_id=?', (timeline_id,))}
    for ask in steps.asks(connection, timeline_id, ('planned',)):
        if ask['step'] == STEP and ask['side'] == 'them' and ask['id'] not in taken:
            data = outings.city_data(connection, companion['version']['definition'])
            ring, cost = ring_for(companion, culture_of(data))
            connection.execute('INSERT INTO proposals (id, timeline_id, ask_id, due_on, ring, ring_cost, created_at) '
                               'VALUES (?, ?, ?, ?, ?, ?, ?)',
                               (identifier(), timeline_id, ask['id'], ask['due_on'] or today.isoformat(), ring, cost,
                                timestamp))
    for row in proposals(connection, timeline_id, ('planned', 'booked')):
        ask = optional(connection, 'SELECT * FROM step_asks WHERE id=?', (row['ask_id'],))
        if ask is None or ask['status'] != 'planned':
            drop(connection, row, None, timestamp)
            continue
        if row['status'] == 'planned':
            if (today - date.fromisoformat(row['due_on'])).days > LAPSE_DAYS:
                drop(connection, row, ask, timestamp)
            continue
        outing = optional(connection, 'SELECT * FROM outings WHERE id=?', (row['outing_id'],))
        state = outings.state(outings.view(outing), companion['version']['timezone'], now) if outing else 'cancelled'
        if state == 'cancelled':
            drop(connection, row, ask, timestamp)
        elif state == 'done':
            asked(connection, companion, row, None, outings.window(outings.view(outing),
                                                                  companion['version']['timezone'])[1])


def drop(connection, row: dict, ask: dict | None, timestamp: str) -> None:
    """The proposal gives way; its ask (when still planned) lapses, so they wait before bringing it up again."""
    connection.execute("UPDATE proposals SET status='dropped', settled_at=? WHERE id=?", (timestamp, row['id']))
    if ask and ask['status'] == 'planned':
        connection.execute("UPDATE step_asks SET status='lapsed', settled_at=? WHERE id=?", (timestamp, ask['id']))


def asked(connection, companion: dict, row: dict, message_id: str | None, when: datetime) -> None:
    """They asked: the ask is open for the user's answer and the ring is bought that day."""
    connection.execute("UPDATE step_asks SET status='open', message_id=NULL, created_at=? WHERE id=? AND "
                       "status='planned'", (stamp(when), row['ask_id']))
    connection.execute("UPDATE proposals SET status='asked', asked_on=?, asked_message_id=?, settled_at=? WHERE id=?",
                       (local_today(companion, when).isoformat(), message_id, stamp(when), row['id']))


def evening(connection, companion: dict, row: dict, local: datetime) -> tuple | None:
    """(activity, day, at, place) for the evening they propose: a favourite place, a free evening near a Friday or a
    Saturday."""
    definition = companion['version']['definition']
    data = outings.city_data(connection, definition)
    if not data:
        return None
    start = local.date() + timedelta(days=2)
    item = favourite(connection, companion, data, row['id'], start)
    if item is None:
        return None
    activity = PROPOSE_KINDS[item['kind']]
    day = min(start + timedelta(days=(weekday - start.weekday()) % 7) for weekday in PROPOSE_DAYS)
    found = outings.when_free(connection, companion, {'activity': activity, 'day': day, 'at': PROPOSE_AT[activity],
                                                      'firm': False}, local)
    if not found:
        return None
    return activity, found[0], found[1], outings.place_view(item, data)


def favourite(connection, companion: dict, data: dict, seed: str, day: date | None = None) -> dict | None:
    """One of their favourite places: where the two of them have been most, else a date spot they like; one that is
    open in the evening and the season, when there is one (a conservatory closes at five)."""
    places = {item['id']: item for item in data['places'] if item['kind'] in PROPOSE_KINDS
              and not NOT_VENUES.search(item['name'])}
    if day is not None:
        places = {key: item for key, item in places.items()
                  if outings.fits(item, day, PROPOSE_AT[PROPOSE_KINDS[item['kind']]])} or places
    counts: dict[str, int] = {}
    for row in many(connection, "SELECT place FROM outings WHERE companion_id=? AND status='done'", (companion['id'],)):
        place_id = (decode(row['place']) or {}).get('id')
        if place_id in places:
            counts[place_id] = counts.get(place_id, 0) + 1
    if counts:
        most = max(counts.values())
        return places[generators.pick(seed, 'favourite', sorted(key for key, count in counts.items() if count == most))]
    options = [item for item in places.values() if 'date' in item.get('good_for', ())] or list(places.values())
    if not options:
        return None
    likes = outings.likes_of(companion['version']['definition'])
    return generators.pick(seed, 'favourite', options, [outings.leaning(item, likes) for item in options])


def propose_due(connection, companion: dict, now: datetime) -> list:
    """The day they planned to propose has come: they invite the user out, giving nothing away."""
    from companion.life import long_distance
    from companion.life.openers import Trigger
    if not ACTIVE or not FIRST_TEXTS or not companion.get('active_timeline_id'):
        return []
    local = now.astimezone(zone(companion['version']['timezone']))
    if not INVITE_HOURS[0] <= local.hour < INVITE_HOURS[1]:
        return []
    row = next((item for item in proposals(connection, companion['active_timeline_id'], ('planned',))
                if item['due_on'] <= local.date().isoformat()), None)
    if row is None or long_distance.far(connection, companion):
        return []
    found = evening(connection, companion, row, local)
    if found is None:
        return []
    activity, day, at, place = found
    reason = (f"You've planned a special evening with the user: {outings.ACTIVITIES[activity][5]} at {place['name']} on "
              f"{day:%A} at {at}. Secretly, you're going to ask them to marry you that evening, but don't give it "
              'away: just invite them in your own words, naming the place, the day and the time.')
    from companion.life.their_people import clock_text
    template = random.Random(f"{row['id']}:line").choice(bank()['invite']).format(
        place=place['name'], day=f'{day:%A}', time=clock_text(at))
    return [Trigger(f"propose:{row['id']}", 'propose', reason, template,
                    (row['id'], activity, day.isoformat(), at, place['id']))]


SETTLES = ('propose',)


def settle(connection, companion: dict, message: dict, trigger, timestamp: str) -> dict | None:
    """The invitation went out: the evening is booked as an outing, marked as the proposal's."""
    from companion.life import together
    proposal_id, activity, day_text, at, place_id = trigger.sources
    row = optional(connection, "SELECT * FROM proposals WHERE id=? AND status='planned'", (proposal_id,))
    day = date.fromisoformat(day_text)
    if row is None or outings.taken(connection, companion, day):
        return None
    definition = companion['version']['definition']
    data = outings.city_data(connection, definition)
    item = next((place for place in (data or {}).get('places', ()) if place['id'] == place_id), None)
    if item is None:
        return None
    place = {**outings.place_view(item, data), 'proposal': proposal_id}
    outing = together.insert(connection, companion, message['id'], activity, place, day, at,
                             outings.until(at, activity), None, timestamp)
    bill, affordable = outings.bill(definition, activity, day)
    connection.execute('UPDATE outings SET cost=? WHERE id=?', (bill if affordable else round(bill * 0.6, 2), outing['id']))
    connection.execute("UPDATE proposals SET status='booked', outing_id=? WHERE id=?", (outing['id'], proposal_id))
    return outings.get(connection, outing['id'])


def proposal_of(connection, outing: dict) -> dict | None:
    proposal_id = outing['place'].get('proposal')
    return optional(connection, 'SELECT * FROM proposals WHERE id=?', (proposal_id,)) if proposal_id else None


def after_reply(connection, message: dict, companion: dict, now: datetime) -> None:
    """A reply written while the evening they propose is under way asks the question (the scene told them to)."""
    if not ACTIVE or message['role'] != 'companion' or not companion.get('active_timeline_id'):
        return
    for row in proposals(connection, companion['active_timeline_id'], ('booked',)):
        outing = optional(connection, 'SELECT * FROM outings WHERE id=?', (row['outing_id'],))
        if outing and outings.state(outings.view(outing), companion['version']['timezone'], now) == 'now':
            asked(connection, companion, row, message['id'], now)


def proposal_lines(connection, outing: dict) -> str:
    """What the evening they propose adds to its scene: ask in this reply, or wait for the answer."""
    row = proposal_of(connection, outing)
    if row is None:
        return ''
    ask = optional(connection, 'SELECT status FROM step_asks WHERE id=?', (row['ask_id'],))
    ring = f" ({row['ring']})" if row['ring'] else ''
    if row['status'] == 'booked' and ask and ask['status'] == 'planned':
        return (f' Tonight you are asking the user to marry you: you have the ring with you{ring}. In this reply, find '
                'your moment and ask them, in your own words. It is a surprise to them. Then let them answer; do not '
                'answer for them.')
    if row['status'] == 'asked' and ask and ask['status'] == 'open':
        return (f' A little while ago you asked the user to marry you and showed them the ring{ring}. You are waiting '
                'for their answer: do not ask again.')
    return ''


def answered(connection, companion: dict, ask: dict, said: str, now: datetime) -> None:
    """The user answered their proposal (companion/life/steps.py settles the step): yes plans the wedding; no keeps things where
    they were, and can start a rough patch (companion/life/rough_patches.py, sized by its slider)."""
    if said == 'yes':
        plan(connection, companion, now)
        return
    if said != 'no' or ask['side'] != 'them':
        return
    from companion.life import rough_patches
    rough_patches.consider(connection, companion, 'proposal_no', f"proposal:{ask['id']}",
                           'the user said no when you asked them to marry you', now,
                           shown='over you saying no when they asked you to marry them')


# Planning the wedding -------------------------------------------------------------------------------------------------

def current(connection, timeline_id: str) -> dict | None:
    """The wedding planned or held on this timeline (the latest one)."""
    row = optional(connection, "SELECT * FROM weddings WHERE timeline_id=? AND status IN ('planned', 'done') "
                   'ORDER BY created_at DESC LIMIT 1', (timeline_id,))
    return view(row) if row else None


def view(row: dict) -> dict:
    return {**row, 'venue': decode(row['venue']) if row['venue'] else None, 'guests': decode(row['guests']) or []}


def engaged_step(found: dict | None) -> dict | None:
    if not found or found['ladder'] != 'romance':
        return None
    return next((item for item in found['steps'] if item['step'] == STEP), None)


def plan(connection, companion: dict, now: datetime) -> dict | None:
    """Plan the wedding an engagement makes, with no question asked: its size, day, venue, budget and guests."""
    timeline_id = companion['active_timeline_id']
    found = steps.state(connection, companion, now, write=False)
    reached = engaged_step(found)
    if reached is None or found['step'] != STEP or current(connection, timeline_id):
        return None
    definition = companion['version']['definition']
    data = outings.city_data(connection, definition)
    culture = culture_of(data)
    rules = customs(culture)
    seed = f"wedding:{timeline_id}:{reached['on']}"
    size = SIZES[decide_size(connection, companion, seed, now)['picked']]
    outcome = consequences.recorded(connection, seed, 'wedding:size')
    day = wedding_day(rules, date.fromisoformat(reached['on']), local_today(companion, now), size, steps.pace(connection),
                      seed)
    budget, share = budget_for(definition, rules, size)
    guests = guest_list(connection, companion, size)
    low, high = rules['guests'][size]
    count = max(low + int(generators.unit(seed, 'guests') * (high - low)), sum(guest['invited'] for guest in guests) + 2)
    row_id, timestamp = identifier(), stamp(now)
    connection.execute(
        'INSERT INTO weddings (id, timeline_id, engaged_on, size, consequence_id, local_date, at_time, until_time, venue, '
        'culture, budget, share, guests, guest_count, created_at, updated_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (row_id, timeline_id, reached['on'], size, outcome['id'] if outcome else None, day.isoformat(), rules['at'],
         rules['until'], encode(venue_for(data, rules, size, seed, day=day)), culture, budget, share, encode(guests), count,
         timestamp, timestamp))
    row = view(one(connection, 'SELECT * FROM weddings WHERE id=?', (row_id,)))
    book(connection, companion, row, now)
    prepare(connection, companion, row, now)
    return current(connection, timeline_id)


def decide_size(connection, companion: dict, seed: str, now: datetime) -> dict:
    from companion.world import personality
    definition = companion['version']['definition']
    found = money.profile(definition)
    levels = personality.levels_of(definition.get('personality_sliders') or {})
    facts = {'tier': found.tier if found else 1, 'social': levels.get('social', 1), 'drama': steps.drama(connection),
             'pace': steps.pace(connection), 'people': len(circle.people(connection, companion['active_timeline_id'])),
             'sheet': {group for group in consequences.WORDS if consequences.sheet_has(definition, group)}}
    names = {'name': first(definition['name']), 'a': 'you', 'b': ''}
    table = consequences.tables()['wedding:size']
    return consequences.decide(connection, timeline_id=companion['active_timeline_id'], choice='wedding:size',
                               subject=seed, facts=facts, names=names,
                               labels=[option['label'].format(**names) for option in table['options']],
                               day=local_today(companion, now).isoformat(), timestamp=stamp(now))


def on_weekday(day: date, weekday: int) -> date:
    return day + timedelta(days=(weekday - day.weekday()) % 7)


def wedding_day(rules: dict, engaged: date, today: date, size: str, pace: int, seed: str) -> date:
    """Months after the engagement by the customs and the size, shorter at a fast pace, on the customs' weekday."""
    low, high = rules['months'][size]
    months = (low + generators.unit(seed, 'months') * (high - low)) * PACE_STRETCH[pace]
    day = max(engaged + timedelta(days=round(months * 30.44)), today + timedelta(days=SOONEST))
    return on_weekday(day, rules['day'])


def budget_for(definition: dict, rules: dict, size: str) -> tuple[float, float]:
    """(the whole budget, their share of it) in the city's money: months of their take-home by the size."""
    found = money.profile(definition)
    if not found:
        return 0.0, 0.0
    total = round(money.monthly_share(found) * rules['budget'][size], 2)
    return total, round(total * rules['share'], 2)


def cold(data: dict | None, day: date | None) -> bool:
    """Whether the day falls in a month too cold for an outdoor wedding there, by the city's climate."""
    climate = (data or {}).get('climate')
    return bool(day and climate) and climate['months'][day.month - 1]['high_f'] < COLD_F


def venue_for(data: dict | None, rules: dict, size: str, seed: str, without: tuple = (), day: date | None = None) -> dict:
    """A venue in their city that fits the customs, the size and the budget; words like chapel or garden count most,
    and nowhere outdoors in a cold month. Somewhere unnamed when the city isn't known."""
    if not data:
        return {'id': VENUE, 'name': 'the wedding venue', 'kind': 'venue', 'neighborhood': '', 'summary': '', 'cost': '',
                'cuisine': '', 'city': '', 'city_id': '', 'spots': []}
    words = re.compile(rf"\b(?:{rules['venues']['words']})", re.IGNORECASE)
    kinds = rules['venues']['kinds']
    options = [item for item in data['places'] if item['kind'] in kinds and item['id'] not in without
               and not NOT_VENUES.search(item['name'])]
    if not options:
        options = [item for item in data['places'] if item['id'] not in without] or data['places']
    if cold(data, day):
        options = [item for item in options if item['kind'] not in OUTDOOR and not OUTDOOR_NAMES.search(item['name'])
                   ] or options
    dear = {'small': {'free', '', '$', '$$'}, 'proper': {'$$', '$$$'}, 'big': {'$$$', '$$$$'}}[size]

    def weight(item: dict) -> float:
        if item['kind'] in EATERIES:
            named = 1.0 if words.search(item['name']) or WEDDING_WORDS.search(item.get('summary', '')) else 0.08
        elif words.search(item['name']) or WEDDING_WORDS.search(item['name']):
            named = 8.0
        elif WEDDING_WORDS.search(item.get('summary', '')):
            named = 4.0
        else:
            named = VENUE_KINDS.get(item['kind'], 0.3)
        return named * (1.5 if item.get('cost', '') in dear else 1.0) * (1.3 if 'date' in item.get('good_for', ()) else 1.0)
    item = generators.pick(seed, 'venue', options, [weight(item) for item in options])
    return outings.place_view(item, data)


def guest_list(connection, companion: dict, size: str) -> list[dict]:
    """Their family (always), their friends (the closest few for a small wedding), the people the user has told them
    about and the user's other companions who are friends or family to them."""
    from companion.characters import by_id
    timeline_id, name = companion['active_timeline_id'], first(companion['version']['definition']['name'])
    guests, friends = [], 0
    for person in circle.people(connection, timeline_id):
        kind = circle.role_kind(person['role'])
        if person['role'] in PARTNERS or kind in PARTNERS:
            continue
        family = kind in circle.FAMILY
        if not family:
            friends += 1
            if size == 'small' and friends > SMALL_FRIENDS:
                continue
        guests.append({'key': f"circle:{person['id']}", 'name': person['name'], 'who': f"{name}'s {person['role']}",
                       'side': 'theirs', 'invited': True})
    for person in many(connection, 'SELECT * FROM user_people WHERE companion_id=? ORDER BY created_at',
                       (companion['id'],)):
        if not person['name'] and not person['relation']:
            continue
        who = f"your {person['relation']}" if person['relation'] else 'someone you know'
        guests.append({'key': f"you:{person['id']}", 'name': person['name'] or '', 'who': who, 'side': 'yours',
                       'invited': True})
    for row in many(connection, 'SELECT id FROM companions WHERE id!=? ORDER BY created_at', (companion['id'],)):
        other = by_id(connection, row['id'])
        relationship = (other or {}).get('version', {}).get('definition', {}).get('relationship')
        if other and relationship in ('friendship', 'family', 'mentor'):
            word = {'friendship': 'friend', 'family': 'family', 'mentor': 'mentor'}[relationship]
            guests.append({'key': f"companion:{other['id']}", 'name': other['version']['definition']['name'],
                           'who': f'your {word}', 'side': 'yours', 'invited': True})
    return guests


# Keeping the wedding in step ----------------------------------------------------------------------------------------

def advance(connection, companion: dict, now: datetime) -> None:
    """Once a day: proposals follow their asks and evenings; an engagement gets its wedding planned, the planning goes
    on the calendar as it comes up, the outing stays booked, and a wedding that is over makes them married. A step
    moved back, a break or a breakup (companion/life/breakups.py) calls the wedding off. Cheap: no model."""
    if not ACTIVE or not companion.get('active_timeline_id'):
        return
    follow_proposals(connection, companion, now)
    timeline_id = companion['active_timeline_id']
    found = steps.state(connection, companion, now, write=False)
    row = current(connection, timeline_id)
    from companion.life import breakups
    apart = breakups.holds(connection, companion) in ('break', 'ended')  # A break or a breakup calls the wedding off.
    if row and row['status'] == 'planned':
        if engaged_step(found) is None or apart:
            call_off(connection, companion, row, now)
            return
        outing = optional(connection, 'SELECT * FROM outings WHERE id=?', (row['outing_id'] or '',))
        if outing and outings.state(outings.view(outing), companion['version']['timezone'], now) == 'done' and \
                outing['status'] == 'done':
            finish(connection, companion, row, outing, now)
            return
        book(connection, companion, row, now)
        prepare(connection, companion, row, now)
        return
    if row is None and found and found['step'] == STEP and not apart:
        plan(connection, companion, now)


def anchor(connection, timeline_id: str) -> str | None:
    """A message on the timeline to book the wedding outing to (outings follow their message): the latest one shown
    that no other outing has."""
    row = optional(connection, "SELECT id FROM messages WHERE timeline_id=? AND active=1 AND status='complete' AND "
                   'redacted_at IS NULL AND id NOT IN (SELECT message_id FROM outings) ORDER BY seq DESC LIMIT 1',
                   (timeline_id,))
    return row['id'] if row else None


def wedding_place(row: dict) -> dict:
    return {**(row['venue'] or {}), 'wedding': row['id'], 'guests': row['guest_count']}


def book(connection, companion: dict, row: dict, now: datetime) -> dict | None:
    """The wedding as an outing on the timeline, kept in step with the plan (its day, hours and venue). A wedding whose
    day another plan, a trip or a family tradition already has moves on a week."""
    from companion.life import together
    timeline_id, timestamp = companion['active_timeline_id'], stamp(now)
    shown = {item['id']: item for item in outings.in_force(connection, timeline_id, '0000-01-01')}
    outing = shown.get(row['outing_id'] or '')
    if outing and outing['status'] == 'cancelled':
        outing = None
    if outing:
        if (outing['local_date'], outing['at_time'], outing['until_time'], outing['place']) != (
                row['local_date'], row['at_time'], row['until_time'], wedding_place(row)):
            connection.execute('UPDATE outings SET local_date=?, at_time=?, until_time=?, place=? WHERE id=?',
                               (row['local_date'], row['at_time'], row['until_time'], encode(wedding_place(row)),
                                outing['id']))
        return outings.get(connection, outing['id'])
    message_id = anchor(connection, timeline_id)
    if message_id is None:
        return None
    day = date.fromisoformat(row['local_date'])
    for _week in range(CLASH_WEEKS):
        if not outings.taken(connection, companion, day):
            break
        day += timedelta(days=7)
    if day.isoformat() != row['local_date']:
        connection.execute('UPDATE weddings SET local_date=?, updated_at=? WHERE id=?', (day.isoformat(), timestamp,
                                                                                       row['id']))
        row = {**row, 'local_date': day.isoformat()}
    made = together.insert(connection, companion, message_id, 'wedding', wedding_place(row), day, row['at_time'],
                           row['until_time'], None, timestamp)
    connection.execute('UPDATE weddings SET outing_id=?, updated_at=? WHERE id=?', (made['id'], timestamp, row['id']))
    return made


def prepare(connection, companion: dict, row: dict, now: datetime) -> int:
    """The planning that comes up in the next three weeks, on the Life admin calendar (each added once)."""
    today = local_today(companion, now)
    engaged, wedding = date.fromisoformat(row['engaged_on']), date.fromisoformat(row['local_date'])
    added = 0
    for task in customs(row['culture'])['prep']:
        day = engaged + timedelta(days=task['after']) if 'after' in task else wedding - timedelta(days=task['before'])
        day = max(day, engaged + timedelta(days=1))
        if day >= wedding or not today <= day <= today + timedelta(days=admin.AHEAD):
            continue
        place = (row['venue'] or {}) if task['key'] == 'venue' and (row['venue'] or {}).get('id') != VENUE else None
        added += bool(admin.add(connection, companion, key=f"wedding:{row['id']}:{task['key']}", source='admin',
                                kind='wedding', title=task['title'], done=task['done'], day=day,
                                minutes=task['minutes'], out=task['out'], place_item=place, now=now))
    return added


def call_off(connection, companion: dict, row: dict, now: datetime) -> None:
    """The engagement was taken back (the step moved back on the Character page, or a breakup): no wedding."""
    timestamp = stamp(now)
    connection.execute("UPDATE weddings SET status='called_off', updated_at=? WHERE id=?", (timestamp, row['id']))
    if row['outing_id']:
        connection.execute("UPDATE outings SET status='cancelled', cancelled_at=? WHERE id=? AND status='planned'",
                           (timestamp, row['outing_id']))
    connection.execute("UPDATE life_admin SET status='removed', updated_at=? WHERE timeline_id=? AND key LIKE ? AND "
                       "status='planned'", (timestamp, companion['active_timeline_id'], f"wedding:{row['id']}:%"))


def finish(connection, companion: dict, row: dict, outing: dict, now: datetime) -> None:
    """The wedding is over: they are married, and the user's best friends among their companions stood up at it."""
    from companion.characters import by_id
    timestamp, day = stamp(now), date.fromisoformat(outing['local_date'])
    connection.execute("UPDATE weddings SET status='done', updated_at=? WHERE id=?", (timestamp, row['id']))
    found = steps.state(connection, companion, now, write=False)
    if found and found['ladder'] == 'romance' and found['step'] == STEP:
        steps.insert_step(connection, companion['active_timeline_id'], 'romance', MARRIED, day, 'them', timestamp)
    for guest in row['guests']:
        if not guest['invited'] or not guest['key'].startswith('companion:'):
            continue
        other = by_id(connection, guest['key'].split(':', 1)[1])
        theirs = steps.state(connection, other, now, write=False) if other and other.get('active_timeline_id') else None
        if theirs and theirs['ladder'] == 'friendship' and theirs['step'] in ('best_friends', 'trip'):
            steps.insert_step(connection, other['active_timeline_id'], 'friendship', 'wedding_party', day, 'them',
                              timestamp)


# What the user can change (the Life admin panel) --------------------------------------------------------------------

def owned(connection, companion: dict) -> dict:
    row = current(connection, companion['active_timeline_id'])
    require(row is not None and row['status'] == 'planned', 'There is no wedding being planned.', 404)
    return row


def change(connection, companion: dict, now: datetime, *, day: date | None = None, venue: bool = False,
           size: str | None = None, guest: str | None = None, invited: bool | None = None) -> dict:
    """The user moves the day, has the venue picked again, changes the size or leaves a guest off (or back on)."""
    row = owned(connection, companion)
    today, timestamp = local_today(companion, now), stamp(now)
    fields: dict = {}
    if day is not None:
        require(day > today, 'Pick a day after today.', 422)
        require(day <= today + timedelta(days=3 * 365), 'Pick a day within three years.', 422)
        fields |= {'local_date': day.isoformat(), 'moved_by_user': 1}
    if size is not None:
        require(size in SIZES, 'Pick one of the sizes.', 422)
        rules = customs(row['culture'])
        budget, share = budget_for(companion['version']['definition'], rules, size)
        guests = guest_list(connection, companion, size)
        left_off = {item['key'] for item in row['guests'] if not item['invited']}
        guests = [{**item, 'invited': item['key'] not in left_off} for item in guests]
        low, high = rules['guests'][size]
        seed = f"wedding:{row['timeline_id']}:{row['engaged_on']}"
        fields |= {'size': size, 'budget': budget, 'share': share, 'guests': encode(guests),
                   'guest_count': max(low + int(generators.unit(seed, 'guests') * (high - low)),
                                      sum(item['invited'] for item in guests) + 2)}
    data = outings.city_data(connection, companion['version']['definition']) if venue or day else None
    # Moving the day into a cold month takes the wedding indoors.
    place = row['venue'] or {}
    outdoors = day is not None and cold(data, day) and (place.get('kind') in OUTDOOR
                                                         or bool(OUTDOOR_NAMES.search(place.get('name', ''))))
    if venue or outdoors:
        rolls = row['venue_rolls'] + 1
        seed = f"wedding:{row['timeline_id']}:{row['engaged_on']}:{rolls}"
        found = venue_for(data, customs(row['culture']), fields.get('size', row['size']), seed,
                          without=((row['venue'] or {}).get('id'),), day=day or date.fromisoformat(row['local_date']))
        require(not venue or found['id'] != (row['venue'] or {}).get('id'), 'There is nowhere else like it in their city.',
                409)
        fields |= {'venue': encode(found), 'venue_rolls': rolls}
    if guest is not None:
        guests = row['guests']
        require(any(item['key'] == guest for item in guests), 'That guest is not on the list.', 404)
        guests = [{**item, 'invited': bool(invited)} if item['key'] == guest else item for item in guests]
        change_by = (1 if invited else -1) if any(item['key'] == guest and item['invited'] != bool(invited)
                                                  for item in row['guests']) else 0
        fields |= {'guests': encode(guests), 'guest_count': max(row['guest_count'] + change_by, 2)}
    if fields:
        sets = ', '.join(f'{key}=?' for key in fields)
        connection.execute(f'UPDATE weddings SET {sets}, updated_at=? WHERE id=?', (*fields.values(), timestamp, row['id']))
    updated = current(connection, companion['active_timeline_id'])
    book(connection, companion, updated, now)
    follow_plan(connection, updated, timestamp)
    return panel(connection, companion, now, False)


def follow_plan(connection, row: dict, timestamp: str) -> None:
    """The planning on the calendar follows a changed plan: booking the venue names the new one, and what would now
    fall on or after the day is dropped."""
    venue = row['venue'] if (row['venue'] or {}).get('id') not in (None, VENUE) else None
    connection.execute("UPDATE life_admin SET place=?, updated_at=? WHERE timeline_id=? AND key=? AND status='planned'",
                       (encode(venue) if venue else None, timestamp, row['timeline_id'], f"wedding:{row['id']}:venue"))
    connection.execute("UPDATE life_admin SET status='removed', updated_at=? WHERE timeline_id=? AND key LIKE ? AND "
                       "status='planned' AND local_date>=?",
                       (timestamp, row['timeline_id'], f"wedding:{row['id']}:%", row['local_date']))


def change_size(connection, companion: dict, consequence_id: str, option: int, now: datetime) -> dict:
    """"Change how it went" on the size: the plan follows."""
    outcome = consequences.change(connection, consequence_id, option, stamp(now))
    require(outcome['timeline_id'] == companion['active_timeline_id'], 'That outcome is not on this timeline.', 404)
    row = current(connection, companion['active_timeline_id'])
    if row and row['status'] == 'planned' and row['consequence_id'] == consequence_id:
        change(connection, companion, now, size=SIZES[option])
    return consequences.by_id(connection, consequence_id)


# The Life admin panel -----------------------------------------------------------------------------------------------

def panel(connection, companion: dict, now: datetime, show_odds: bool) -> dict | None:
    """The wedding plan for the Life admin panel: when, where, how big, the budget and the guests. None while there is
    no wedding being planned (and for a while after it, the day it was)."""
    row = current(connection, companion['active_timeline_id'])
    if row is None:
        return None
    definition = companion['version']['definition']
    found = money.profile(definition)
    currency = found.city['currency'] if found else None
    venue = row['venue'] or {}
    prep = {item['key']: item['done'] for item in customs(row['culture'])['prep']}
    tasks = many(connection, "SELECT key, title, local_date, status FROM life_admin WHERE timeline_id=? AND key LIKE ? AND "
                 "status!='removed' ORDER BY local_date", (row['timeline_id'], f"wedding:{row['id']}:%"))
    return {'id': row['id'], 'status': row['status'], 'engaged_on': row['engaged_on'], 'date': row['local_date'],
            'at': row['at_time'], 'until': row['until_time'], 'size': row['size'], 'size_label': SIZE_LABELS[row['size']],
            'sizes': [{'key': key, 'label': SIZE_LABELS[key]} for key in SIZES],
            'venue': {'id': venue.get('id'), 'name': venue.get('name', ''), 'kind': venue.get('kind', ''),
                      'neighborhood': venue.get('neighborhood', ''), 'mapped': venue.get('id') not in (None, VENUE)},
            'budget_text': money.amount(row['budget'], currency) if currency and row['budget'] else '',
            'share_text': money.amount(row['share'], currency) if currency and row['share'] else '',
            'guest_count': row['guest_count'], 'guests': row['guests'], 'moved_by_user': bool(row['moved_by_user']),
            'customs': customs(row['culture'])['ceremony'],
            'tasks': [{'title': task['title'], 'date': task['local_date'], 'done': task['status'] == 'done',
                       'done_text': prep.get(task['key'].rsplit(':', 1)[-1], '').capitalize()} for task in tasks],
            'consequence_id': row['consequence_id'] if show_odds else None}


# Money (money.household) --------------------------------------------------------------------------------------------

def purchases(connection, timeline_id: str, start: date, day: date) -> list[dict]:
    """The ring they bought and their share of the wedding, this pay period: both from their savings."""
    low, high = start.isoformat(), day.isoformat()
    result = [{'text': f"bought an engagement ring ({row['ring']})" if row['ring'] else 'bought an engagement ring',
               'date': row['asked_on'], 'spend': '', 'cost': row['ring_cost'], 'for': 'ring', 'savings': True}
              for row in many(connection, "SELECT * FROM proposals WHERE timeline_id=? AND status='asked' AND "
                              'asked_on>=? AND asked_on<=? AND ring_cost>0', (timeline_id, low, high))]
    result += [{'text': 'paid your share of the wedding', 'date': row['local_date'], 'spend': '', 'cost': row['share'],
                'for': 'wedding', 'savings': True}
               for row in many(connection, "SELECT * FROM weddings WHERE timeline_id=? AND status='done' AND "
                               'local_date>=? AND local_date<=? AND share>0', (timeline_id, low, high))]
    return result


# The outing (companion/life/outings.py) -------------------------------------------------------------------------------

def is_wedding(outing: dict) -> bool:
    return outing['activity'] == 'wedding'


def of_outing(connection, outing: dict) -> dict | None:
    row = optional(connection, 'SELECT * FROM weddings WHERE id=?', (outing['place'].get('wedding') or '',))
    return view(row) if row else None


def what(outing: dict) -> str:
    """'your wedding at The Belvedere (a hotel in Mount Vernon)'."""
    place = outing['place']
    area = f" in {place['neighborhood']}" if place.get('neighborhood') else ''
    kind = f" ({place['kind']}{area})" if place.get('kind') and place.get('id') != VENUE else ''
    return f"your wedding at {place['name']}{kind}"


def doing(outing: dict) -> str:
    return f"married you at {outing['place']['name']}"


def named_guests(row: dict, limit: int = SHOWN_GUESTS) -> list[str]:
    """'your mom Ana', 'the user's sister Bea': who is there, as the companion says it."""
    result = []
    for guest in row['guests']:
        if not guest['invited']:
            continue
        if guest['side'] == 'theirs':
            role = guest['who'].split("'s ", 1)[1] if "'s " in guest['who'] else guest['who']
            result.append(f"your {role} {guest['name']}")
        else:
            who = guest['who'].replace('your ', "the user's ", 1)
            result.append(f"{who} {guest['name']}".strip())
    return result[:limit]


def joined(items: list[str]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def moment_now(row: dict, outing: dict, timezone: str, now: datetime) -> str:
    """The part of the day under way: the ceremony's two moments take its first CEREMONY minutes, and the rest of the
    day's moments follow in order across the hours left."""
    moments = customs(row['culture'])['moments']
    start, end = outings.window(outing, timezone)
    minutes = (now - start).total_seconds() / 60
    if minutes < CEREMONY:
        return moments[0 if minutes < CEREMONY / 2 else 1]
    rest = moments[2:] or moments[-1:]
    share = (now - start - timedelta(minutes=CEREMONY)) / max(end - start - timedelta(minutes=CEREMONY), timedelta(minutes=1))
    return rest[min(int(share * len(rest)), len(rest) - 1)]


def scene(connection, companion: dict, outing: dict, now: datetime | None) -> str:
    """Being at the wedding together, in person, with the guests there and the part of the day under way."""
    row = of_outing(connection, outing)
    if row is None:
        return f"- Right now you and the user are at {what(outing)}, in person, until about {outing['until_time']}."
    rules = customs(row['culture'])
    names = named_guests(row)
    others = max(row['guest_count'] - len(names), 0)
    guests = joined([*names, f'about {others} others']) if names and others else joined(names) if names else \
        f"about {row['guest_count']} guests"
    parts = [f"Right now it is your wedding day, in person: you and the user are at your wedding at "
             f"{what(outing).removeprefix('your wedding at ')}, from {outing['at_time']} until about "
             f"{outing['until_time']}.", f"How the day goes: {rules['ceremony']}.",
             f"Right now: {moment_now(row, outing, companion['version']['timezone'], now)}." if now else '',
             f'Your guests are here: {guests}.',
             'It is a big, happy, busy day. Talk as if you are there together, face to face, not texting: what you say '
             'and do. The guests are around too: you can say briefly what they say or do, but you speak only as '
             'yourself.']
    return '- ' + ' '.join(part for part in parts if part)


def memory_text(outing: dict) -> dict:
    day = date.fromisoformat(outing['local_date'])
    return {'subject': 'Your wedding', 'value': f"You married the user at {outing['place']['name']} on "
                                                f"{day:%A, %B} {day.day}, {day.year}."}


def caption(outing: dict) -> str:
    return generators.pick(f"wedding:{outing['id']}", 'married', bank()['married'])


def dressed(connection, timeline_id: str, local_date: str, now: datetime | None = None) -> str:
    """What they wear at their wedding on this local date ('a white wedding dress'), else ''. With `now`, only while
    it is under way (companion/life/wardrobe.py: the chat's "Wearing right now" and the pictures)."""
    from companion.characters import by_id
    row = optional(connection, "SELECT * FROM weddings WHERE timeline_id=? AND local_date=? AND status IN ('planned', "
                   "'done') ORDER BY created_at DESC LIMIT 1", (timeline_id, local_date))
    timeline = optional(connection, 'SELECT companion_id FROM timelines WHERE id=?', (timeline_id,)) if row else None
    companion = by_id(connection, timeline['companion_id']) if timeline else None
    if companion is None:
        return ''
    if now is not None:
        outing = optional(connection, 'SELECT * FROM outings WHERE id=?', (row['outing_id'] or '',))
        if not outing or outings.state(outings.view(outing), companion['version']['timezone'], now) != 'now':
            return ''
    return attire(companion['version']['definition'], row['culture'])


def photo_wearing(connection, companion: dict, outing: dict) -> str:
    row = of_outing(connection, outing)
    culture = row['culture'] if row else 'modern'
    return f"Wearing {attire(companion['version']['definition'], culture)}."


# What the chat context says -----------------------------------------------------------------------------------------

def plan_line(row: dict, today: date) -> str:
    venue = row['venue'] or {}
    area = f", {venue['kind']} in {venue['neighborhood']}" if venue.get('neighborhood') and venue.get('kind') else ''
    names = named_guests(row, 6)
    who = f", including {joined(names)}" if names else ''
    rules = customs(row['culture'])
    when = 'today' if row['local_date'] == today.isoformat() else long_date(row['local_date'])
    return (f"- You and the user got engaged on {long_date(row['engaged_on'])} "
            f"({days_ago(date.fromisoformat(row['engaged_on']), today)}). Your wedding is planned for {when} at "
            f"{row['at_time']}, at {venue.get('name', 'the venue')}{area}: {SIZE_WORDS[row['size']]} with about "
            f"{row['guest_count']} guests{who}. {rules['ceremony'].capitalize()}. The app planned it with you: talk "
            'about it as your own plans, the way a couple planning a wedding does, and never contradict it.')


def money_words(companion: dict, row: dict) -> str:
    found = money.profile(companion['version']['definition'])
    if not found or not row['budget']:
        return ''
    currency = found.city['currency']
    return (f" The budget is about {money.amount(row['budget'], currency)} in all; your share is about "
            f"{money.amount(row['share'], currency)}, from your savings.")


def context_lines(connection, companion: dict, now: datetime) -> list[tuple[str, str]]:
    """(identity, line) for the 'wedding' section: a proposal waiting for its answer, the wedding being planned or
    held, and, for the user's other companions, the wedding they are invited to."""
    timeline_id = companion['active_timeline_id']
    today = local_today(companion, now)
    result = []
    for row in proposals(connection, timeline_id, ('asked',)):
        ask = optional(connection, 'SELECT status FROM step_asks WHERE id=?', (row['ask_id'],))
        outing = optional(connection, 'SELECT * FROM outings WHERE id=?', (row['outing_id'] or '',))
        under_way = outing and outings.state(outings.view(outing), companion['version']['timezone'], now) == 'now'
        if ask and ask['status'] == 'open' and not under_way:
            place = (decode(outing['place']) or {}).get('name') if outing else None
            where = f" at {place}" if place else ''
            ring = f" and showed them the ring ({row['ring']})" if row['ring'] else ''
            result.append((f"proposal:{row['id']}:open",
                           f"- On {long_date(row['asked_on'], False)} ({days_ago(date.fromisoformat(row['asked_on']), today)})"
                           f"{where} you asked the user to marry you{ring}. They have not answered yet: if they answer "
                           'now, take it as they mean it, and do not ask again.'))
    row = current(connection, timeline_id)
    if row and row['status'] == 'planned':
        result.append((f"wedding:{row['id']}:{row['updated_at']}", plan_line(row, today) + money_words(companion, row)))
    elif row and row['status'] == 'done':
        venue = (row['venue'] or {}).get('name', 'the venue')
        names = named_guests(row, 6)
        result.append((f"wedding:{row['id']}:done",
                       f"- You married the user on {long_date(row['local_date'])} "
                       f"({days_ago(date.fromisoformat(row['local_date']), today)}) at {venue}, with about "
                       f"{row['guest_count']} guests" + (f", among them {joined(names)}" if names else '') + '.'))
    return result + invited_lines(connection, companion, today)


def invited_lines(connection, companion: dict, today: date) -> list[tuple[str, str]]:
    """Another companion's wedding with the user, for a companion on its guest list."""
    from companion.characters import by_id
    result = []
    key = f"companion:{companion['id']}"
    for row in many(connection, "SELECT * FROM weddings WHERE status IN ('planned', 'done') ORDER BY created_at"):
        found = view(row)
        if not any(guest['key'] == key and guest['invited'] for guest in found['guests']):
            continue
        timeline = optional(connection, 'SELECT companion_id FROM timelines WHERE id=?', (found['timeline_id'],))
        other = by_id(connection, timeline['companion_id']) if timeline else None
        if other is None or other.get('active_timeline_id') != found['timeline_id']:
            continue
        name = other['version']['definition']['name']
        venue = (found['venue'] or {}).get('name', 'the venue')
        if found['status'] == 'planned':
            text = (f"- The user is engaged to {name}. Their wedding is on {long_date(found['local_date'])} at {venue}, "
                    'and you are invited.')
        else:
            text = f"- The user married {name} on {long_date(found['local_date'])} at {venue}; you were there."
        result.append((f"wedding-guest:{found['id']}:{found['status']}:{found['local_date']}", text))
    return result


def offer(packet, connection, companion: dict, now: datetime, group=None) -> None:
    """Adds the 'wedding' section, in a 1:1 chat."""
    if group is not None or not companion.get('active_timeline_id'):
        return
    for identity, text in context_lines(connection, companion, now):
        packet.offer('wedding', identity, text)


# The feed, the scrapbook and the town paper ----------------------------------------------------------------------------

def feed_posts(connection, companion: dict, days: list[date], timezone: str) -> list[dict]:
    """Their post on the day they got engaged (a step reached in the chat, not one the user set)."""
    from companion.life import social
    found = steps.state(connection, companion, steps.now_for(days[-1], companion), write=False) if days else None
    reached = engaged_step(found)
    if not reached or reached['how'] not in ('them', 'you'):
        return []
    day = date.fromisoformat(reached['on'])
    if day not in days:
        return []
    seed = f"engaged:{companion['active_timeline_id']}:{reached['on']}"
    text = generators.pick(seed, 'line', bank()['engaged'])
    return [social.own('status', f'wedding:{seed}', social.at(day, timezone, seed, 20, 23),
                       {'text': text, 'tone': 'good'})]


def scrapbook_page(connection, companion: dict, low: str, high: str) -> dict | None:
    """'Your wedding': where, when, who came, the order of the day and the photo, for a wedding in this stretch."""
    row = optional(connection, "SELECT * FROM weddings WHERE timeline_id=? AND status='done' AND local_date>=? AND "
                   'local_date<=? ORDER BY local_date DESC LIMIT 1', (companion['active_timeline_id'], low, high))
    if row is None:
        return None
    found = view(row)
    outing = optional(connection, 'SELECT photo_post_id FROM outings WHERE id=?', (found['outing_id'] or '',))
    post = optional(connection, "SELECT image_ref FROM feed_posts WHERE id=? AND image_status='completed'",
                    (outing['photo_post_id'] or '',)) if outing else None
    guests = [f"{guest['name']} ({guest['who']})" if guest['name'] else guest['who'].capitalize()
              for guest in found['guests'] if guest['invited']][:12]
    more = found['guest_count'] - len(guests) if guests else 0
    venue = (found['venue'] or {}).get('name', 'the venue')
    return {'kind': 'wedding', 'title': 'Your wedding', 'date': found['local_date'],
            'text': f"Married at {venue}, with about {found['guest_count']} guests.",
            'items': [{'text': moment.capitalize()} for moment in customs(found['culture'])['moments']],
            'guests': guests, 'more': max(more, 0), 'photo': post['image_ref'] if post and post['image_ref'] else None,
            'photo_alt': f"{companion['version']['name']} on your wedding day at {venue}"}


def paper_items(connection, data: dict, week: tuple[date, date]) -> list[dict]:
    """The user's own engagement and wedding with a companion in this city, for the paper's Engagements and weddings
    (companion/world/paper.py)."""
    from companion.world import paper, townsfolk
    persona = optional(connection, 'SELECT name FROM persona WHERE id=1')
    you = ((persona or {}).get('name') or '').strip()
    wed = 'married' if townsfolk.modern(data) else 'wed'
    result = []
    for person in paper.companions_in(connection, data):
        for row in many(connection, "SELECT * FROM weddings WHERE timeline_id=? AND status IN ('planned', 'done')",
                        (person['timeline_id'],)):
            # Without the user's name (Settings > About you), the paper names the companion alone.
            couple = f"{first(person['name'])} and {first(you)}" if you else first(person['name'])
            full = f"{person['name']} and {you}" if you else person['name']
            if paper.in_week(row['engaged_on'], week):
                result.append({'key': f"wedding:{row['id']}:engaged",
                               'headline': f"{couple} {'are' if you else 'is'} engaged.",
                               'text': f"{full} announced {'their' if you else 'an'} engagement."})
            if row['status'] == 'done' and paper.in_week(row['local_date'], week):
                venue = (decode(row['venue']) or {}).get('name', 'the venue')
                result.append({'key': f"wedding:{row['id']}:married", 'headline': f'{couple} got {wed}.',
                               'text': f"{full} {wed if you else 'got ' + wed} at {venue} on "
                                       f"{paper.WEEKDAYS[date.fromisoformat(row['local_date']).weekday()]}."})
    return result


def copy_proposals(connection, asks: dict[str, str], new_id: str) -> None:
    """Their proposal behind an ask a branch keeps open (steps.copy_open): asked, the ring bought."""
    for ask_id, copied in asks.items():
        row = optional(connection, "SELECT * FROM proposals WHERE ask_id=? AND status='asked'", (ask_id,))
        if row:
            connection.execute('INSERT INTO proposals (id, timeline_id, ask_id, status, due_on, outing_id, ring, ring_cost, '
                               "asked_on, created_at, settled_at) VALUES (?, ?, ?, 'asked', ?, ?, ?, ?, ?, ?, ?)",
                               (identifier(), new_id, copied, row['due_on'], row['outing_id'], row['ring'],
                                row['ring_cost'], row['asked_on'], row['created_at'], row['settled_at']))


def copy(connection, parent_id: str, new_id: str, cutoff_date: str) -> None:
    """A wedding planned by the fork carries over (re-booked on the copy); one held after it is the copy's own."""
    for row in many(connection, "SELECT * FROM weddings WHERE timeline_id=? AND engaged_on<=? AND status!='called_off'",
                    (parent_id, cutoff_date)):
        status = 'done' if row['status'] == 'done' and row['local_date'] <= cutoff_date else 'planned'
        connection.execute(
            'INSERT INTO weddings (id, timeline_id, status, engaged_on, size, consequence_id, local_date, at_time, '
            'until_time, venue, venue_rolls, culture, budget, share, guests, guest_count, outing_id, moved_by_user, '
            'created_at, updated_at) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)',
            (identifier(), new_id, status, row['engaged_on'], row['size'], row['local_date'], row['at_time'],
             row['until_time'], row['venue'], row['venue_rolls'], row['culture'], row['budget'], row['share'],
             row['guests'], row['guest_count'], row['moved_by_user'], row['created_at'], row['updated_at']))
