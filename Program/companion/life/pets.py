"""Pets with lives of their own (Hit List #15): sick days, vet visits, growing old and, rarely, dying.

Everyone can have pets: the companion (their home's pets, companion/life/home.py), the people in their circle
and the townsfolk (seeded, so the same person always has the same pet) and the user's persona (only the pets
the user writes in, never invented). Rules decide everything from a seed and the bank in world/data/pets.json,
with no model: what kind of pet suits the city's era, its name and looks, when it was born, how long its kind
lives, and day by day whether it falls sick, sees the vet for that or for its yearly checkup, or dies.

A pet's life is written to `pet_log` once as the days pass (`evolve`), so the past stays put when a Realism
setting changes. The Realism tab scales it: `pets_realism` (0 off, 1 light, 2 true to life, 3 dramatic) sets how
often pets fall ill and for how long, and `pets_can_die` lets a pet die of old age, or of a serious illness late
in life. A young pet never dies, and on I want an easy life none do. A pet the user brings back after it died is
spared from then on.

Other modules read pets through this module: home.py weaves sick days, vet visits and deaths into the
companion's days and chat context, trips.py asks who minds the pets (`minders`), money.py counts vet bills and
sitters (`purchases`), Life admin lists vet visits (`vet_visits`), and the image prompts draw a pet with its
looks line (`picture_line`), never with words about illness.
"""
import json
import re
from datetime import date, timedelta
from functools import cache

from companion.clock import parse, stamp, zone
from companion.database import identifier, many, optional
from companion.world import catalog, generators

MODERN = {'modern', 'future'}
# Eras with a vet to take a pet to; elsewhere a sick pet just rests.
VET_ERAS = {'modern', 'jazz-age', 'victorian', 'steampunk'}
# How likely a pet falls ill on a given day, by the pets_realism setting, before age raises it.
DAILY_SICK = {0: 0.0, 1: 0.012 / 7, 2: 0.025 / 7, 3: 0.045 / 7}
# How long a sick spell lasts compared with the bank's range.
SPELL_LENGTH = {1: 0.7, 2: 1.0, 3: 1.25}
# The share of serious illnesses late in life that end in death, by pets_realism.
FATAL = {1: 0.15, 2: 0.3, 3: 0.45}
OLD = 0.7
VERY_OLD = 0.8
SPEND = {'checkup': '$', 'vet': '$$'}
# A pet's age as a share of its kind's lifespan, at the start of the companion's story: young to middle-aged.
START_AGE = 0.6
# Townsfolk pets have no start date of their own: they are this old on this day, and age from there.
TOWN_ANCHOR = date(2026, 1, 1)
RECENT_DAYS = 21
REMEMBERED_DAYS = 90
TRAVELS_ALONG = 0.6
# Moments at work, where pet news is not woven (companion/life/home.py WORKING_ACTIVITIES).
WORKING = {'steady-shift', 'busy-shift', 'library', 'study-cafe'}
LEGACY_AGE = re.compile(r',? about (\d+) years? old$')
# How likely someone in the circle has a pet: about one in three on Earth (many share one with family there), and
# about one in ten aboard a ship or station (companion/world/ships.py), where only a cabin-sized pet fits.
CIRCLE_OWNS = 0.33
CIRCLE_OWNS_ABOARD = 0.1
CABIN = ('cat', 'fish', 'bird', 'hamster', 'guinea-pig', 'lizard', 'tortoise')


@cache
def bank() -> dict:
    return json.loads((catalog.DATA / 'pets.json').read_text(encoding='utf-8'))


def kinds() -> dict:
    return bank()['kinds']


def era_of(data: dict | None) -> str:
    """The era a city's pets come from: 'modern' for today's cities and any city the world does not know."""
    era = (data or {}).get('era') or 'modern'
    return 'modern' if era in MODERN else era


def fits(item: dict, kind: str | None, era: str) -> bool:
    return (kind is None or 'any' in item['kinds'] or kind in item['kinds']) and \
        ('any' in item['eras'] or era in item['eras'])


def label(kind: str) -> str:
    return kinds().get(kind, {}).get('label', kind)


def kind_phrase(kind: str) -> str:
    """'a cat', 'an African grey', 'a few backyard chickens': the kind with an article."""
    words = label(kind)
    if kind == 'chickens':
        return f'a few {words}'
    return f"{'an' if words[:1] in 'aeiou' else 'a'} {words}"


def drawable(era: str, aboard=False) -> list[str]:
    """The kinds a pet is drawn from in this era; aboard a ship or station, only cabin-sized ones."""
    return [kind for kind, value in kinds().items() if value['weight'] > 0 and era in value['eras'] and
            (not aboard or kind in CABIN)]


def lifespan_days(seed: str, kind: str) -> int:
    low, high = kinds().get(kind, kinds()['cat'])['lifespan']
    return int((low + (high - low) * generators.unit(seed, 'lifespan')) * 365)


# Words in a looks line that say how old a pet is, for one the user adds without an age.
OLD_WORDS = re.compile(r'\b(elderly|old|senior|ageing|aging|grey-muzzled|gray-muzzled|white-muzzled)\b', re.I)
YOUNG_WORDS = re.compile(r'\b(kitten|puppy|young|baby|bunny|chick|foal|hatchling)\b', re.I)


def age_from_looks(looks: str, kind: str, today: date) -> str | None:
    """A birth date that fits the looks the user wrote ("an elderly grey tabby" is old), or None to let it be seeded."""
    low, high = kinds().get(kind, kinds()['cat'])['lifespan']
    if OLD_WORDS.search(looks or ''):
        return (today - timedelta(days=int((low + high) / 2 * 0.8 * 365))).isoformat()
    if YOUNG_WORDS.search(looks or ''):
        return (today - timedelta(days=120)).isoformat()
    return None


def name_for(seed: str, label_: str, era: str) -> str:
    return generators.pick(seed, f'{label_}:name', bank()['names']['modern' if era == 'modern' else 'period'])


def looks_for(seed: str, label_: str, kind: str, era: str) -> str:
    found = [item['text'] for item in bank()['looks'] if fits(item, kind, era)]
    return generators.pick(seed, f'{label_}:look', found) or kind_phrase(kind)


def draw(seed: str, label_: str, era: str, day: date, young=False, aboard=False) -> dict:
    """A pet suited to the era (and to a cabin, aboard), as a home item: its name, kind, looks, birth and lifespan."""
    choices = drawable(era, aboard) or ['cat']
    kind = generators.pick(seed, f'{label_}:kind', choices, [kinds()[choice]['weight'] for choice in choices])
    lifespan = lifespan_days(f'{seed}:{label_}', kind)
    share = 0.02 + generators.unit(seed, label_, 'age') * (0.08 if young else START_AGE)
    age = max(60, int(share * kinds()[kind]['lifespan'][0] * 365))
    return {'kind': 'pet', 'name': name_for(seed, label_, era), 'variety': kind,
            'details': {'description': looks_for(seed, label_, kind, era), 'born': (day - timedelta(days=age)).isoformat(),
                        'lifespan_days': lifespan}}


def age_text(born: date, day: date) -> str:
    days = (day - born).days
    count, unit_ = (max(1, days // 7), 'week') if days < 60 else (days // 30, 'month') if days < 365 else \
        (days // 365, 'year')
    return f"{count} {unit_}{'' if count == 1 else 's'} old"


# --- Who has which pets ---

def pet(key: str, name: str, kind: str, looks: str, born: date, start: date, era: str, lifespan: int | None = None,
        **extra) -> dict:
    """A pet as this module sees it, whoever owns it. `start` is the first day its life is lived out here."""
    return {'key': key, 'name': name, 'kind': kind if kind in kinds() else 'other', 'looks': looks, 'born': born,
            'start': start, 'era': era, 'lifespan': lifespan or lifespan_days(key, kind), 'spared': False, **extra}


def from_home_item(item: dict, era: str, started: date) -> dict:
    """The companion's pet from its home item (companion/life/home.py). Pets from before lives were kept get a
    birth date from the "about 6 years old" their description carried, else a seeded one."""
    since = date.fromisoformat(item['since'])
    looks = LEGACY_AGE.sub('', item.get('description') or item['name'])
    born = item.get('born')
    if born:
        born = date.fromisoformat(born)
    else:
        legacy = LEGACY_AGE.search(item.get('description') or '')
        years = int(legacy.group(1)) if legacy else 1 + int(generators.unit(item['id'], 'age') * 6)
        born = since - timedelta(days=years * 365)
    return pet(f"home:{item['id']}", item['name'], item['variety'], looks, born, max(since, started), era,
               item.get('lifespan_days'), spared=bool(item.get('spared')), item_id=item['id'], owner='companion')


def circle_pets(person: dict, era: str, start: date, aboard=False) -> list[dict]:
    """The pets of someone in the companion's circle: about one in three have one (one in ten aboard), the same one
    every time."""
    seed = f"pets:{person.get('key') or person['id']}"
    if generators.unit(seed, 'has') >= (CIRCLE_OWNS_ABOARD if aboard else CIRCLE_OWNS):
        return []
    item = draw(seed, 'pet0', era, start, aboard=aboard)
    details = item['details']
    return [pet(f"circle:{person['id']}:0", item['name'], item['variety'], details['description'],
                date.fromisoformat(details['born']), start, era, details['lifespan_days'], owner='circle')]


def town_pets(sheet: dict, identity: tuple[str, str] | None, era: str) -> list[dict]:
    """The pet a townsperson's life details already give them (companion/world/life_details.py `pet_of`), with a
    kind, looks and a life. An animal they only feed or befriend (a neighbor's cat, a garden robin) has none here."""
    if not identity:
        return []
    pet_id, pet_name = identity
    known = bank()['townsfolk'].get(pet_id)
    if not known or not known['kind']:
        return []
    key = f"town:{sheet['key']}"
    kind = known['kind']
    lifespan = lifespan_days(key, kind)
    age = int((0.1 + generators.unit(key, 'age') * START_AGE) * lifespan)
    return [pet(key, pet_name, kind, known['looks'], TOWN_ANCHOR - timedelta(days=age), TOWN_ANCHOR, era, lifespan,
                owner='town')]


def persona_pets(entries: list[dict], era: str, start: date) -> list[dict]:
    """The pets the user wrote on their persona: their own words, with a life like everyone's."""
    result = []
    for entry in entries or []:
        name = (entry.get('name') or '').strip()
        if not name:
            continue
        kind = entry.get('kind') or 'cat'
        born = date.fromisoformat(entry['born']) if entry.get('born') else start - timedelta(days=3 * 365)
        added = date.fromisoformat(entry['added']) if entry.get('added') else start
        result.append(pet(f'persona:{name.casefold()}', name, kind, (entry.get('looks') or '').strip() or
                          kind_phrase(kind), born, added, era, owner='persona'))
    return result


# --- A life, day by day ---

def settings(connection) -> tuple[int, bool]:
    row = optional(connection, 'SELECT pets_realism, pets_can_die FROM life_settings WHERE id=1')
    return (row['pets_realism'], bool(row['pets_can_die'])) if row else (2, True)


def has_vets(found: dict) -> bool:
    return found['era'] in VET_ERAS and kinds().get(found['kind'], {}).get('vet', False)


def died_on(connection, key: str) -> date | None:
    row = optional(connection, "SELECT local_date FROM pet_log WHERE pet_key=? AND kind='died'", (key,))
    return date.fromisoformat(row['local_date']) if row else None


def sick_until(connection, key: str) -> date:
    row = optional(connection, "SELECT MAX(until) AS until FROM pet_log WHERE pet_key=? AND kind='sick'", (key,))
    return date.fromisoformat(row['until']) if row and row['until'] else date.min


def checkup_day(found: dict, year: int) -> date:
    offset = int(generators.unit(found['key'], 'checkup', year) * 365)
    return date(year, 1, 1) + timedelta(days=offset)


def sick_entry(found: dict, day: date, frac: float) -> dict | None:
    choices = [item for item in bank()['sick'] if fits(item, found['kind'], found['era'])
               and (frac >= OLD or not item['serious'])]
    return generators.pick(found['key'], f'sick:{day.isoformat()}', choices)


def vet_entry(found: dict, day: date) -> str:
    """Why they take the pet in for its yearly checkup: nothing that needs a past it doesn't have, and talk of
    growing old only once it is old."""
    old = (day - found['born']).days / max(found['lifespan'], 1) >= OLD
    choices = [item['text'] for item in bank()['vet'] if fits(item, found['kind'], found['era'])
               and (old or not item.get('old'))]
    return generators.pick(found['key'], f'vet:{day.isoformat()}', choices) or 'a checkup'


def falls_ill(found: dict, day: date, realism: int, frac: float) -> list[tuple]:
    """A sick spell starting today, the vet visit it needs and, late in a long life, sometimes death."""
    entry = sick_entry(found, day, frac)
    if entry is None:
        return []
    low, high = entry['days']
    days = max(1, round((low + (high - low) * generators.unit(found['key'], 'spell', day)) * SPELL_LENGTH[realism]))
    until = day + timedelta(days=days)
    happened = [('sick', day, until, entry['text'], entry['serious'], '')]
    if entry['vet'] and has_vets(found):
        visit = day + timedelta(days=int(generators.unit(found['key'], 'vet-day', day) * 2))
        happened.append(('vet', visit, None, entry['text'], entry['serious'], '$$$' if entry['serious'] else '$$'))
    return happened


def fatal(found: dict, spell: tuple, realism: int, can_die: bool, frac: float) -> tuple | None:
    if not (spell[4] and can_die and not found['spared'] and frac >= VERY_OLD):
        return None
    if generators.unit(found['key'], 'fatal', spell[1]) >= FATAL[realism]:
        return None
    return ('died', spell[2], None, f'after {spell[3]}', True, '')


def day_of_life(found: dict, day: date, realism: int, can_die: bool, resting_until: date) -> list[tuple]:
    """What happens to the pet on this day: (kind, date, until, text, serious, spend) tuples."""
    age = (day - found['born']).days
    frac = age / max(found['lifespan'], 1)
    if can_die and not found['spared'] and age >= found['lifespan']:
        return [('died', day, None, 'of old age', False, '')]
    happened = []
    if has_vets(found) and day == checkup_day(found, day.year) and day > resting_until:
        happened.append(('checkup', day, None, vet_entry(found, day), False, SPEND['checkup']))
    if day > resting_until and generators.unit(found['key'], 'ill', day) < DAILY_SICK[realism] * (
            1 + 3 * max(0.0, frac - 0.6)):
        spell = falls_ill(found, day, realism, frac)
        happened += spell
        if spell and (death := fatal(found, spell[0], realism, can_die, frac)):
            happened.append(death)
    return happened


def evolve(connection, found: dict, through: date, now) -> None:
    """Write what happens to the pet up to `through`, once: evolving in steps or all at once gives the same life
    under the same settings, and what is written stays when a setting changes later."""
    key = found['key']
    state = optional(connection, 'SELECT through FROM pet_state WHERE pet_key=?', (key,))
    day = date.fromisoformat(state['through']) + timedelta(days=1) if state else found['start']
    if day > through:
        return
    realism, can_die = settings(connection)
    dead, resting = died_on(connection, key), sick_until(connection, key)
    death = None
    while day <= through and dead is None and realism:
        for kind, on, until, text, serious, spend in day_of_life(found, day, realism, can_die, resting):
            if kind == 'sick':
                resting = until
            row_id = identifier()
            if kind == 'died':
                dead, death = on, {'id': row_id, 'local_date': on.isoformat(), 'kind': kind, 'text': text}
            connection.execute(
                'INSERT INTO pet_log (id, pet_key, local_date, kind, until, text, serious, spend, created_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', (row_id, key, on.isoformat(), kind,
                                                       until.isoformat() if until else None, text, int(serious), spend,
                                                       stamp(now)))
        day += timedelta(days=1)
    connection.execute('INSERT INTO pet_state (pet_key, through) VALUES (?, ?) ON CONFLICT (pet_key) DO UPDATE SET '
                       'through=excluded.through', (key, max(through, day - timedelta(days=1)).isoformat()))
    if dead and found.get('item_id'):
        # The companion's home no longer has the pet from the day after it died (companion/life/home.py).
        connection.execute('UPDATE home_items SET until=? WHERE id=? AND until IS NULL',
                           ((dead + timedelta(days=1)).isoformat(), found['item_id']))
        if death:
            tell_late(connection, found, death)


TOLD_WITHIN = 3


def tell_late(connection, found: dict, death: dict) -> None:
    """A death written for a day whose agenda was already drawn (after a pet was added or a setting changed) is told
    on the first upcoming moment that day or soon after, so they still say goodbye. A day not drawn yet tells it
    as it is drawn (`untold`)."""
    item = optional(connection, 'SELECT timeline_id FROM home_items WHERE id=?', (found['item_id'],))
    day = date.fromisoformat(death['local_date'])
    if not item or not optional(connection, "SELECT id FROM life_agenda WHERE timeline_id=? AND subject='companion' "
                                'AND local_date=? LIMIT 1', (item['timeline_id'], death['local_date'])):
        return
    rows = many(connection, "SELECT id, entry FROM life_agenda WHERE timeline_id=? AND subject='companion' AND "
                "status='upcoming' AND entry IS NOT NULL AND local_date>=? AND local_date<=? ORDER BY starts_at",
                (item['timeline_id'], death['local_date'], (day + timedelta(days=TOLD_WITHIN)).isoformat()))
    target = next((row for row in rows if json.loads(row['entry']).get('activity') not in WORKING), None)
    who = optional(connection, 'SELECT v.name FROM companions c JOIN character_versions v ON '
                   'v.id=c.active_version_id WHERE c.active_timeline_id=?', (item['timeline_id'],))
    if target is None or who is None:
        return
    entry = json.loads(target['entry'])
    sentence = news_sentence(death, found['name'], who['name'].split()[0])
    note = {'items': [found['item_id']], 'change': None, 'sentence': sentence, **(entry.get('home') or {}),
            'pet_event': death['id']}
    entry = {**entry, 'summary': f"{entry['summary'].rstrip()} {sentence}", 'mood': 'heartbroken', 'home': note}
    connection.execute('UPDATE life_agenda SET entry=? WHERE id=?', (json.dumps(entry), target['id']))


def forget_ahead(connection, keys: list[str], day: date) -> None:
    """Forget what was written for these pets after `day` (their agenda is planned a few days ahead, and their
    lives with it), so the days ahead follow a changed pet or a changed Realism setting; up to `day` stays put."""
    for key in keys:
        died = died_on(connection, key)
        if died and died > day and key.startswith('home:'):
            connection.execute('UPDATE home_items SET until=NULL WHERE id=? AND until=?',
                               (key.removeprefix('home:'), (died + timedelta(days=1)).isoformat()))
        connection.execute('DELETE FROM pet_log WHERE pet_key=? AND local_date>?', (key, day.isoformat()))
        connection.execute('UPDATE pet_state SET through=? WHERE pet_key=? AND through>?',
                           (day.isoformat(), key, day.isoformat()))


def settings_changed(connection, now) -> None:
    """The Pets slider or "Pets can die" changed: the days ahead are lived again under the new settings, and the
    upcoming agenda entries about their home are drawn again, so they tell what happens now (a pet that can die
    again may die today). Days up to each companion's today stay put."""
    rows = many(connection, 'SELECT c.active_timeline_id AS timeline_id, v.timezone FROM companions c '
                'JOIN character_versions v ON v.id=c.active_version_id')
    days = []
    for row in rows:
        today = now.astimezone(zone(row['timezone'] or 'UTC')).date()
        days.append(today)
        forget_ahead(connection, [f"home:{item['id']}" for item in home_rows(connection, row['timeline_id'])], today)
        removed = connection.execute(
            "DELETE FROM life_agenda WHERE timeline_id=? AND subject='companion' AND status='upcoming' "
            "AND json_extract(entry, '$.home') IS NOT NULL", (row['timeline_id'],)).rowcount
        if removed:
            connection.execute("UPDATE agenda_cursors SET through=MIN(through, ?) WHERE timeline_id=? AND "
                               "subject='companion'", (stamp(now), row['timeline_id']))
    # Everyone else's pets (the circle's, the townsfolk's and the user's own) from the earliest of those days.
    day = min(days, default=now.astimezone(zone('UTC')).date())
    others = many(connection, "SELECT pet_key FROM pet_state WHERE through>? AND pet_key NOT LIKE 'home:%'",
                  (day.isoformat(),))
    forget_ahead(connection, [row['pet_key'] for row in others], day)


def log(connection, key: str, start: date, end: date) -> list[dict]:
    return many(connection, 'SELECT * FROM pet_log WHERE pet_key=? AND local_date>=? AND local_date<=? '
                'ORDER BY local_date, kind', (key, start.isoformat(), end.isoformat()))


def spare(connection, key: str, now) -> None:
    """The user brought a pet back after it died: the death is forgotten and it will not die again (the caller
    marks the pet spared)."""
    connection.execute("DELETE FROM pet_log WHERE pet_key=? AND kind='died'", (key,))


# --- In words ---

def status_on(connection, found: dict, day: date) -> dict:
    """{state, text}: well, sick, at the vet or died, in plain words."""
    name = found['name']
    died = died_on(connection, found['key'])
    if died and died <= day:
        return {'state': 'died', 'text': f"{name} died on {died:%B} {died.day}, {died.year}."}
    rows = many(connection, "SELECT * FROM pet_log WHERE pet_key=? AND local_date<=? AND (local_date=? OR until>?) "
                'ORDER BY local_date DESC', (found['key'], day.isoformat(), day.isoformat(), day.isoformat()))
    vet = next((row for row in rows if row['kind'] in ('vet', 'checkup') and row['local_date'] == day.isoformat()),
               None)
    if vet:
        return {'state': 'vet', 'text': f"{name} is at the vet today for {vet['text']}."}
    sick = next((row for row in rows if row['kind'] == 'sick'), None)
    if sick:
        worse = 'seriously ill' if sick['serious'] else 'under the weather'
        return {'state': 'sick', 'text': f"{name} is {worse}: {sick['text']}.", 'serious': bool(sick['serious'])}
    return {'state': 'well', 'text': ''}


def event_text(row: dict, name: str) -> str:
    """One logged moment as a phrase after the owner's name: "took Biscuit to the vet for a yearly checkup"."""
    if row['kind'] == 'checkup':
        return f"took {name} to the vet for {row['text']}"
    if row['kind'] == 'vet':
        return f"took {name} to the vet for {row['text']}"
    if row['kind'] == 'sick':
        return f"found {name} poorly with {row['text']}"
    return f"lost {name}, who died {row['text']}"


def health(connection, found: dict, day: date) -> int:
    """A hidden number (Settings > Realism > Hidden values): 100 is a young pet in the pink of health."""
    status = status_on(connection, found, day)
    if status['state'] == 'died':
        return 0
    frac = (day - found['born']).days / max(found['lifespan'], 1)
    value = 100 - int(45 * max(0.0, frac - 0.5) / 0.5)
    sick = optional(connection, "SELECT serious FROM pet_log WHERE pet_key=? AND kind='sick' AND local_date<=? AND "
                    'until>?', (found['key'], day.isoformat(), day.isoformat()))
    if sick:
        value -= 45 if sick['serious'] else 20
    return max(5, min(100, value))


def picture_line(found: dict) -> str:
    """How the pet looks in a picture: its looks line, with its kind when the line does not say it."""
    looks = found['looks']
    word = label(found['kind']).split()[-1].rstrip('s')
    return looks if word.casefold() in looks.casefold() or found['kind'] in ('other', 'farm') else f'{looks} ({word})'


def view(connection, found: dict, day: date, numbers: bool) -> dict:
    """A pet as the interface shows it: plain words, and the numbers only when Hidden values are on."""
    died = died_on(connection, found['key'])
    status = status_on(connection, found, day)
    end = died if died and died <= day else day
    recent = [{'date': row['local_date'], 'kind': row['kind'], 'text': event_text(row, found['name'])}
              for row in log(connection, found['key'], day - timedelta(days=60), day)]
    result = {'key': found['key'], 'name': found['name'], 'kind': found['kind'], 'kind_label': label(found['kind']),
              'looks': found['looks'], 'born': found['born'].isoformat(), 'age': age_text(found['born'], end),
              'state': status['state'], 'status': status['text'], 'serious': status.get('serious', False), 'died_on': died.isoformat() if died and
              died <= day else None, 'recent': list(reversed(recent)), 'health': None, 'lifespan_years': None}
    if numbers:
        result['health'] = health(connection, found, day)
        result['lifespan_years'] = round(found['lifespan'] / 365)
    return result


def show_numbers(connection) -> bool:
    row = optional(connection, 'SELECT show_home_meters FROM workspace_settings WHERE id=1')
    return bool(row and row['show_home_meters'])


# --- For other modules ---

# Aboard a ship or station (companion/world/ships.py) there is no sun, sky, weather or wildlife outside.
EARTHBOUND = re.compile(r'\b(?:sun\w*|bird\w*|squirrels?|rain\w*|puddles?|snow\w*|mud\w*|leaves|fire|frost\w*|storms?|'
                        r'thunder\w*|fence post|dandelions?|outside)\b', re.IGNORECASE)


def fits_home(item: dict, found: dict, text: str) -> bool:
    return fits(item, found['kind'], found['era']) and not (found.get('aboard') and EARTHBOUND.search(text))


def moment(found: dict, seed: str, walking=False) -> str | None:
    """A sentence about the pet for an agenda entry at home or on a walk."""
    lines = [item['text'] for item in bank()['walks' if walking else 'home'] if fits_home(item, found, item['text'])]
    line = generators.pick(seed, 'pet-moment', lines)
    return line.format(pet=found['name']) if line else None


def photo(found: dict, seed: str) -> dict | None:
    """A pet-only photo for the owner's feed, taken at home: what it shows and their caption."""
    shots = [item for item in bank()['photos'] if fits_home(item, found, item['shows']) and not item.get('out')]
    shot = generators.pick(seed, 'pet-photo', shots)
    if shot is None:
        return None
    return {'shows': shot['shows'], 'caption': shot['caption'].format(pet=found['name'])}


def photo_prompt(found: dict, shows: str, style: str) -> str:
    """A fixed template: the pet alone, in visible words only (no illness or injury), nobody in focus."""
    style = (style or 'Candid phone photo').strip().rstrip('.')
    return (f'{style}, a fictional everyday photo of a pet at home: {picture_line(found)}, {shows}. '
            'The pet fills the frame. Nobody in focus, no people. Natural light, sharp focus on the animal.')


def minder(found: dict, trip: dict, local: list[dict], ahead=False) -> dict:
    """Who looks after a pet while the companion is away: a dog often comes along; fish, reptiles and a horse at
    its stable need nobody; else someone local from their circle, or a paid sitter or kennel. `ahead` words it for
    a trip still to come ("Pepper is coming along")."""
    info = kinds().get(found['kind'], {})
    seed = f"care:{trip['id']}:{found['key']}"
    name = found['name']
    if info.get('travels') and generators.unit(seed, 'along') < TRAVELS_ALONG:
        return {'how': 'along', 'who': None, 'text': f"{name} is coming along" if ahead else f"{name} came along"}
    if not info.get('minder'):
        return {'how': 'none', 'who': None, 'text': ''}
    if local:
        person = generators.pick(seed, 'who', local)
        staying = info['minder'] == 'staying'
        verb = ('will stay with' if staying else 'will be fed by') if ahead else \
            ('is staying with' if staying else 'is being fed by')
        return {'how': 'circle', 'who': person['name'], 'text': f"{name} {verb} {person['name']}"}
    where = 'at a kennel' if found['kind'] == 'dog' else 'with a paid sitter'
    return {'how': 'sitter', 'who': None, 'text': f"{name} {'will be' if ahead else 'is'} {where}"}


# --- The companion's own pets (their home's pet items) ---

def home_rows(connection, timeline_id: str) -> list[dict]:
    rows = many(connection, "SELECT * FROM home_items WHERE timeline_id=? AND kind='pet' ORDER BY since, created_at",
                (timeline_id,))
    return [{'id': row['id'], 'name': row['name'], 'variety': row['variety'], 'since': row['since'],
             'until': row['until'], 'edited': bool(row['edited']), **json.loads(row['details'] or '{}')}
            for row in rows]


def of_home(connection, timeline_id: str, day: date | None = None) -> list[dict]:
    """The companion's pets: those alive and at home on `day` (all ever kept when no day is given), oldest first."""
    state = optional(connection, 'SELECT era, started FROM home_state WHERE timeline_id=?', (timeline_id,))
    if not state:
        return []
    era, started = era_of({'era': state['era']}), date.fromisoformat(state['started'])
    aboard = state['era'] == 'future' and afloat(connection, timeline_id)
    result = []
    for row in home_rows(connection, timeline_id):
        if day and not (row['since'] <= day.isoformat() and (row['until'] is None or row['until'] > day.isoformat())):
            continue
        found = from_home_item(row, era, started)
        # The home keeps a pet through the day it died (its `until` is the day after), but from that day it is
        # remembered, not one of the pets they have now.
        if day and (died := died_on(connection, found['key'])) and died <= day:
            continue
        result.append({**found, 'until': row['until'], 'edited': row['edited'], 'aboard': aboard})
    return result


def afloat(connection, timeline_id: str) -> bool:
    from companion.characters import for_timeline
    from companion.world import ships
    companion = for_timeline(connection, timeline_id)
    return bool(companion) and ships.aboard(connection, companion['version']['definition'])


def evolve_home(connection, timeline_id: str, through: date, now) -> None:
    for found in of_home(connection, timeline_id):
        if found['until'] is None or died_on(connection, found['key']):
            evolve(connection, found, through, now)


def remembered(connection, timeline_id: str, day: date) -> list[dict]:
    """The companion's pets that have died, most recent first."""
    gone = [(died, found) for found in of_home(connection, timeline_id)
            if (died := died_on(connection, found['key'])) and died <= day]
    return [found for _died, found in sorted(gone, key=lambda pair: pair[0], reverse=True)]


def keys_of_home(connection, timeline_id: str) -> dict[str, dict]:
    return {found['key']: found for found in of_home(connection, timeline_id)}


def home_log(connection, timeline_id: str, start: date, end: date, kinds_=None) -> list[tuple[dict, dict]]:
    """(pet, logged row) for the companion's pets between two local dates, oldest first."""
    result = []
    for key, found in keys_of_home(connection, timeline_id).items():
        result += [(found, row) for row in log(connection, key, start, end) if not kinds_ or row['kind'] in kinds_]
    return sorted(result, key=lambda pair: pair[1]['local_date'])


def vet_visits(connection, timeline_id: str, start: date, end: date) -> list[dict]:
    """The companion's vet visits between two local dates inclusive, for the Life admin calendar: checkups (which
    could move) and visits for a sick pet (which cannot)."""
    return [{'date': row['local_date'], 'pet': found['name'], 'variety': found['kind'], 'reason': row['text'],
             'kind': row['kind'], 'pet_id': found['item_id'], 'movable': row['kind'] == 'checkup'}
            for found, row in home_log(connection, timeline_id, start, end, ('vet', 'checkup'))]


def purchases(connection, timeline_id: str, start: date, end: date) -> list[dict]:
    """Vet bills for the companion's pets, as money.household purchases ({date, kind, text, spend})."""
    return [{'date': row['local_date'], 'kind': 'vet', 'text': event_text(row, found['name']), 'spend': row['spend']}
            for found, row in home_log(connection, timeline_id, start, end) if row['spend']]


def sick_today(connection, timeline_id: str, day: date) -> set[str]:
    """Names of the companion's pets that are poorly on this day (Home upkeep can mention it)."""
    return {found['name'] for found in of_home(connection, timeline_id, day)
            if status_on(connection, found, day)['state'] in ('sick', 'vet')}


def context_lines(connection, timeline_id: str, day: date) -> list[tuple[str, str]]:
    """(identity, line) pairs about the companion's pets for chat: each pet and how they are today, what happened
    lately, and a pet they lost in the last few months."""
    lines = []
    for found in of_home(connection, timeline_id, day):
        status = status_on(connection, found, day)
        text = f"- Pet: {found['name']}, your {label(found['kind'])} ({found['looks']}, {age_text(found['born'], day)})."
        if status['text'] and status['state'] != 'died':
            text += f" Right now: {status['text']}"
        lines.append((found['key'], text))
    for found, row in home_log(connection, timeline_id, day - timedelta(days=RECENT_DAYS), day):
        if row['kind'] != 'died':
            lines.append((row['id'], f"- Recently ({row['local_date']}): you {event_text(row, found['name'])}."))
    for found in remembered(connection, timeline_id, day):
        died = died_on(connection, found['key'])
        if (day - died).days <= REMEMBERED_DAYS:
            how = optional(connection, "SELECT text FROM pet_log WHERE pet_key=? AND kind='died'", (found['key'],))
            lines.append((f"{found['key']}:died", f"- On {died.isoformat()} your {label(found['kind'])} "
                                                  f"{found['name']} died {how['text']}. You still miss them."))
    return lines


def copy(connection, ids: dict, day: str) -> None:
    """A fork keeps its pets' lives up to the fork day; `ids` maps the parent's home item ids to the fork's."""
    for old, new in ids.items():
        for row in many(connection, 'SELECT * FROM pet_log WHERE pet_key=? AND local_date<=?', (f'home:{old}', day)):
            connection.execute('INSERT INTO pet_log (id, pet_key, local_date, kind, until, text, serious, spend, '
                               'created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                               (identifier(), f'home:{new}', row['local_date'], row['kind'], row['until'], row['text'],
                                row['serious'], row['spend'], row['created_at']))
        state = optional(connection, 'SELECT through FROM pet_state WHERE pet_key=?', (f'home:{old}',))
        if state:
            connection.execute('INSERT OR IGNORE INTO pet_state (pet_key, through) VALUES (?, ?)',
                               (f'home:{new}', min(state['through'], day)))


# --- In the companion's days (companion/life/home.py `touch`) ---

PHOTO_SHARE = 0.08


def untold(connection, timeline_id: str, day: date, first_name: str) -> dict | None:
    """Something that happened to one of the companion's pets today that no agenda entry mentions yet, as
    {item, sentence, extra}: a vet visit, falling ill or, rarely, dying."""
    for found, row in home_log(connection, timeline_id, day, day):
        told = optional(connection, "SELECT id FROM life_agenda WHERE timeline_id=? AND subject='companion' "
                        "AND json_extract(entry, '$.home.pet_event')=?", (timeline_id, row['id']))
        if told:
            continue
        extra = {'pet_event': row['id']}
        if row['kind'] == 'died':
            extra['mood'] = 'heartbroken'
        return {'item': found['item_id'], 'sentence': news_sentence(row, found['name'], first_name), 'extra': extra}
    return None


def news_sentence(row: dict, name: str, first_name: str) -> str:
    if row['kind'] == 'died':
        return f"{first_name} said goodbye to {name}, who died {row['text']}."
    if row['kind'] == 'sick':
        return f"{name} was poorly with {row['text']}, so {first_name} kept a close eye on them."
    return f"{first_name} {event_text(row, name)}."


def losses(connection, timeline_id: str, day: date, days: int = TOLD_WITHIN) -> list[tuple[dict, date]]:
    """The companion's pets that died in the last few days up to `day`, for their mood (companion/moods.py)."""
    return [(found, died) for found in of_home(connection, timeline_id)
            if (died := died_on(connection, found['key'])) and 0 <= (day - died).days < days]


def at_home(connection, found: dict, day: date, seed: str, first_name: str) -> str | None:
    """A sentence about the pet while the companion is at home: a sick pet rests, a well one does its thing."""
    state = status_on(connection, found, day)['state']
    if state == 'died':
        return None
    if state in ('sick', 'vet'):
        return f"{found['name']} rested, still poorly, and {first_name} checked on them often."
    return moment(found, seed)


def photo_moment(connection, timeline_id: str, day: date, seed: str, first_name: str) -> dict | None:
    """Now and then, a pet-only photo for the feed: {item, sentence, extra} with the caption as the entry's post
    and what the picture shows (companion/images/prompts.py draws only the pet)."""
    if generators.unit(seed, 'pet-photo-roll') >= PHOTO_SHARE:
        return None
    well = [found for found in of_home(connection, timeline_id, day) if found['kind'] != 'horse'
            and status_on(connection, found, day)['state'] == 'well']
    found = generators.pick(seed, 'pet-photo-who', well)
    shot = found and photo(found, seed)
    if not shot:
        return None
    return {'item': found['item_id'], 'sentence': f"{first_name} took a photo of {found['name']} {shot['shows']}.",
            'extra': {'post': shot['caption'], 'pet_photo': {'item': found['item_id'], 'shows': shot['shows']}}}


def find_home(connection, timeline_id: str, item_id: str) -> dict | None:
    return next((found for found in of_home(connection, timeline_id) if found['item_id'] == item_id), None)


def drawable_any() -> list[str]:
    """Every kind a pet can be when the user adds or edits one."""
    return [kind for kind, value in kinds().items() if value['weight'] > 0]


def offered(connection, timeline_id: str) -> list[str]:
    """The kinds "Add a pet" offers: those kept in the city's era, and any kind they already have."""
    state = optional(connection, 'SELECT era FROM home_state WHERE timeline_id=?', (timeline_id,))
    era = era_of({'era': state['era']} if state else None)
    have = {found['kind'] for found in of_home(connection, timeline_id)}
    return [kind for kind in drawable_any() if era in kinds()[kind]['eras'] or kind in have]


def lived(connection, found: list[dict], day: date, now) -> list[dict]:
    """Views of other people's pets (circle, townsfolk, the persona's) after living them out through `day`."""
    numbers = show_numbers(connection)
    for each in found:
        evolve(connection, each, day, now)
    return [view(connection, each, day, numbers) for each in found]


def timeline_start(connection, timeline_id: str, timezone: str | None) -> date:
    """The first local day of the timeline: when the lives of the circle's pets start being written."""
    row = optional(connection, 'SELECT created_at FROM timelines WHERE id=?', (timeline_id,))
    return parse(row['created_at']).astimezone(zone(timezone or 'UTC')).date() if row else TOWN_ANCHOR


# --- The user's own pets (their persona) ---

def persona_entries(previous: list[dict], given: list[dict], today: date) -> list[dict]:
    """The persona's pets as saved: the user's words, with a birth date from the age they gave, else the one the
    pet already had, else about three years ago; and the day it was added, from when its life is lived out."""
    before = {entry['name'].casefold(): entry for entry in previous if entry.get('name')}
    result = []
    for entry in given:
        name = entry['name'].strip()
        kind = entry.get('kind') if entry.get('kind') in kinds() else 'other'
        old = before.get(name.casefold(), {})
        if entry.get('age') is not None:
            born = today - timedelta(days=int(entry['age']) * 365 + 180)
        else:
            fits_looks = age_from_looks(entry.get('looks') or '', kind, today)
            born = date.fromisoformat(old.get('born') or fits_looks or (today - timedelta(days=3 * 365)).isoformat())
        result.append({'name': name, 'kind': kind, 'looks': (entry.get('looks') or '').strip(),
                       'born': born.isoformat(), 'added': old.get('added') or today.isoformat()})
    return result


def of_persona(connection) -> list[dict]:
    """The persona's pets in this world, living their lives in the companion's city era."""
    row = optional(connection, 'SELECT pets FROM persona WHERE id=1')
    entries = json.loads(row['pets'] or '[]') if row else []
    if not entries:
        return []
    state = optional(connection, 'SELECT era FROM home_state ORDER BY created_at LIMIT 1')
    era = era_of({'era': state['era']} if state else None)
    return persona_pets(entries, era, TOWN_ANCHOR)


def persona_lines(connection, day: date) -> list[str]:
    """The user's pets for the persona section of chat context, with how each is today."""
    lines = []
    for found in of_persona(connection):
        status = status_on(connection, found, day)
        text = f"{found['name']} ({label(found['kind'])}: {found['looks']}, {age_text(found['born'], day)})"
        lines.append(text + (f"; {status['text']}" if status['text'] else ''))
    return lines


def evolve_persona(connection, through: date, now) -> None:
    for found in of_persona(connection):
        evolve(connection, found, through, now)


WORDS = {'kitten': 'cat', 'tabby': 'cat', 'puppy': 'dog', 'pup': 'dog', 'mutt': 'dog', 'bunny': 'rabbit',
         'budgie': 'bird', 'canary': 'bird', 'parakeet': 'bird', 'cockatiel': 'bird', 'goldfish': 'fish',
         'turtle': 'tortoise', 'gecko': 'lizard', 'pony': 'horse', 'hen': 'chickens', 'chicken': 'chickens',
         'guinea pig': 'guinea-pig'}


def kind_for_word(word: str) -> str:
    """The pet kind a word names ("kitten" is a cat), or 'cat' when it names none we keep."""
    word = (word or '').casefold().strip()
    kind = WORDS.get(word, word.replace(' ', '-'))
    return kind if kind in drawable_any() else 'cat'
