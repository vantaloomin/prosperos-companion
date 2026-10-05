"""Deterministic event composition (PRD T2, T3).

A routine slot becomes an ordinary event without any model call: the block's kind selects an
activity, the world source supplies a real place for it, and fixed templates write the summary,
caption and mood. The same slot always composes the same event, so a resumed batch is stable.
A model may later rephrase the wording, but never chooses the place, activity or facts.

Some slots are deliberately quiet: an uneventful stretch is a valid outcome, not a failure.
"""
import random
from dataclasses import dataclass
from datetime import date, timedelta

COMPOSER_VERSION = 'compose-5'
QUIET_SHARE = 0.2
OUTDOOR = {'park', 'waterfront', 'beach'}
RAINY_CAPTIONS = ('Rain on the window all day.', 'Good day to stay in.', 'Listening to the rain.')


@dataclass(frozen=True)
class Activity:
    key: str
    place_kinds: tuple[str, ...]
    summaries: tuple[str, ...]
    captions: tuple[str, ...]
    moods: tuple[str, ...]
    generic: str = ''
    together: tuple[str, ...] = ()


def activity(key, place_kinds, summaries, captions, moods, generic='', together=()) -> Activity:
    """`generic` stands in for " at <place>" when the world has no matching place. `together` are
    summaries naming a circle member ({friend}) who is free at the time."""
    return Activity(key, tuple(place_kinds), tuple(summaries), tuple(captions), tuple(moods), generic,
                    tuple(together))


# {name} is the companion, {label} the routine block, {at} " at <place>" or "", {place} the place
# name or a generic word, {area} " in <neighborhood>" or "".
CATALOG = {
    'work': (
        activity('steady-shift', (), ['{name} worked through the {label} at a steady pace.',
                                      '{name} spent the {label} getting through the usual work.'],
                 ['Head down, list done.', 'A good, ordinary day of work.'], ['focused', 'steady']),
        activity('busy-shift', (), ['{name} had a busy {label}, with one rush after another.',
                                    'Work got hectic during the {label}, but {name} kept up.'],
                 ['That was a lot. Feet up now.', 'Survived the rush.'], ['tired', 'busy']),
        activity('lunch-out', ('cafe', 'restaurant'), ['{name} took a proper lunch break{at} during the {label}.'],
                 ['Lunch away from the desk, for once.', 'Worth stepping out for.'], ['refreshed'], ' nearby'),
    ),
    'study': (
        activity('library', ('library', 'college'), ['{name} studied{at} through the {label}.',
                                                     '{name} worked through readings{at}.'],
                 ['Quiet corner, long notes.', 'Finally made sense of it.'], ['focused', 'satisfied'], ' at the library'),
        activity('study-cafe', ('cafe',), ['{name} studied{at}, nursing one coffee for hours.'],
                 ['Office for the afternoon.', 'Caffeine and flashcards.'], ['focused'], ' at a café'),
    ),
    'errand': (
        activity('groceries', ('grocery', 'market'), ['{name} did the grocery run{at}.',
                                                      '{name} stocked up on food{at}.'],
                 ['Fridge: full. Me: proud.', 'Found the good bread.'], ['practical', 'content'], ' at the store'),
        activity('chores', (), ['{name} spent the {label} on laundry and small chores.',
                                '{name} caught up on chores around home.'],
                 ['Small wins.', 'Everything folded, for now.'], ['productive']),
        activity('browse', ('shop', 'bookstore'), ['{name} ran errands and browsed{at} on the way back.'],
                 ['Just looking. Mostly.', 'Came home with one more book than planned.'], ['content'], ' at a few shops'),
    ),
    'social': (
        activity('dinner', ('restaurant',), ['{name} met an old friend for dinner{at}.',
                                             '{name} caught up with friends over food{at}.'],
                 ['Good food, better company.', 'We closed the place down.'], ['happy', 'warm'], '',
                 ['{name} had dinner with {friend}{at}.', '{name} caught up with {friend} over food{at}.']),
        activity('drinks', ('bar',), ['{name} met a couple of friends for drinks{at}.'],
                 ['One drink turned into three stories.', 'Laughed too much.'], ['cheerful'], '',
                 ['{name} met {friend} for drinks{at}.']),
        activity('show', ('venue',), ['{name} went to see a show{at} with a friend.'],
                 ['Still humming it.', 'Live music hits different.'], ['excited'], '',
                 ['{name} went to see a show{at} with {friend}.']),
    ),
    'leisure': (
        activity('walk', ('park', 'waterfront', 'beach'), ['{name} went for a long walk{at}.',
                                                           '{name} spent the {label} walking{at}{area}.'],
                 ['Needed that air.', 'The light was perfect today.'], ['calm', 'content'], ' around the neighborhood'),
        activity('coffee', ('cafe',), ['{name} read for a while{at} with a coffee.',
                                       '{name} sat{at} people-watching over a coffee.'],
                 ['Best seat in the house.', 'Coffee and a chapter.'], ['relaxed'], ' at a café'),
        activity('museum', ('museum', 'attraction'), ['{name} spent the {label}{at}.',
                                                      '{name} wandered around{at} for a couple of hours.'],
                 ['Could have stayed all day.', 'Saw something new.'], ['curious', 'inspired'], ' at a museum'),
        activity('market', ('market',), ['{name} browsed the stalls{at}.'],
                 ['Came for one thing, left with five.', 'Market finds.'], ['cheerful'], ' at the market'),
        activity('workout', ('gym', 'park'), ['{name} fit in a workout{at}.'],
                 ['Sore tomorrow, worth it today.', 'Done and dusted.'], ['energized'], ''),
        activity('home-cooking', (), ['{name} cooked something new at home during the {label}.',
                                      '{name} stayed in and tried a new recipe.'],
                 ['It mostly worked!', 'Kitchen chaos, tasty result.'], ['proud', 'cozy']),
        activity('reading', (), ['{name} stayed in and read through most of the {label}.'],
                 ['Couldn\'t put it down.', 'Blanket, book, done.'], ['cozy']),
    ),
    'rest': (
        activity('nap', (), ['{name} took it easy and napped through part of the {label}.'],
                 ['Recharged.', 'Zero regrets.'], ['rested']),
        activity('slow', (), ['{name} had a slow, lazy {label} at home.'],
                 ['Doing nothing, beautifully.', 'Slow day.'], ['relaxed']),
    ),
}


# A city's annual event, on the day it is held, can draw the companion out for part of a leisure or
# social block. The event comes from the world data; the wording names it and nothing else.
FESTIVAL = activity('festival', (), ['{name} joined the crowds for {event}{area}.',
                                     '{name} spent a few hours out for {event}{area}.'],
                    ['The whole city came out.', 'Worth the crowds.', 'Already looking forward to next year.'],
                    ['excited', 'happy'], '', ['{name} and {friend} joined the crowds for {event}{area}.',
                                               '{name} went out for {event}{area} with {friend}.'])
FESTIVAL_SHARE = 0.5
FESTIVAL_KINDS = {'leisure', 'social'}


# A circle member's birthday: the companion celebrates with them when both are free, or calls a
# relative who lives out of town.
BIRTHDAY = activity('birthday', ('restaurant', 'bar'), [],
                    ['Happy birthday to the best.', 'Cake was had.', 'Another year, same favorite person.'],
                    ['warm', 'happy'], '', ["{name} celebrated {friend}'s birthday{at}.",
                                            "{name} took {friend} out{at} for their birthday."])
CALL = ("{name} called {friend} to wish them a happy birthday.",
        "{name} spent a while on the phone with {friend}, who turned a year older today.")
BIRTHDAY_KINDS = {'leisure', 'social'}


def birthday(slot: dict, definition: dict, world, seed: str, recent_activities, celebrants, conditions):
    """On a circle member's birthday, a leisure or social slot goes to them. `celebrants` are those
    having a birthday ({id, name, local}); local ones are only passed when free at the slot."""
    if not celebrants or slot['block']['kind'] not in BIRTHDAY_KINDS or BIRTHDAY.key in set(recent_activities):
        return None
    rng = random.Random(f'{seed}:birthday')
    friend = celebrants[0]
    who = {'id': friend['id'], 'name': friend['name']}
    if not friend.get('local', True):
        summary, place = rng.choice(CALL).format(name=definition['name'], friend=friend['name']), None
    else:
        places = find_places(world, definition, slot, BIRTHDAY.place_kinds)
        place = rng.choice(places) if places else None
        summary = rng.choice(BIRTHDAY.together).format(name=definition['name'], friend=friend['name'],
                                                      at=f' at {place.name}' if place else '')
    return {'summary': summary, 'post': rng.choice(BIRTHDAY.captions), 'mood': rng.choice(BIRTHDAY.moods),
            'activity': BIRTHDAY.key, 'place': place.view() if place else None, 'with': who,
            'weather': conditions, 'composer_version': COMPOSER_VERSION}


def happenings(world, definition: dict, local_date: str) -> list[dict]:
    """The city's annual events held on this date, from the world data. [] when the world has none."""
    lookup, city = getattr(world, 'happenings', None), home_city(definition)
    found = lookup(city, date.fromisoformat(local_date)) if lookup and city else []
    return [{key: item[key] for key in ('id', 'name', 'neighborhood', 'city')} for item in found]


def festival(slot: dict, definition: dict, world, seed: str, recent_activities, company, conditions) -> dict | None:
    """Sometimes, the slot is spent at one of the day's annual events."""
    block = slot['block']
    if block['kind'] not in FESTIVAL_KINDS or FESTIVAL.key in set(recent_activities):
        return None
    events = block.get('happenings') or happenings(world, definition, slot['local_date'])
    rng = random.Random(f'{seed}:festival')
    if not events or rng.random() >= FESTIVAL_SHARE / (2 if harsh(conditions) else 1):
        return None
    event = rng.choice(events)
    values = {'name': definition['name'], 'event': event['name'],
              'area': f" in {event['neighborhood']}" if event['neighborhood'] and event['neighborhood'] not in
              event['name'] else ''}
    friend = company[int(rng.random() * len(company))] if company else None
    summary = rng.choice(FESTIVAL.together).format(**values, friend=friend['name']) if friend else \
        rng.choice(FESTIVAL.summaries).format(**values)
    return {'summary': summary, 'post': rng.choice(FESTIVAL.captions), 'mood': rng.choice(FESTIVAL.moods),
            'activity': FESTIVAL.key, 'place': {**event, 'kind': 'event'}, 'with': friend, 'weather': conditions,
            'composer_version': COMPOSER_VERSION}


# Words in the character's interests or life themes that make an activity more likely (PRD T3).
# A word matches a stem it starts with ("reading", "books"); stems of three letters or fewer ("art",
# "tea") must match the whole word.
LEANINGS = {
    'reading': ('read', 'book', 'novel', 'poetry', 'literature'), 'browse': ('book', 'shopping', 'vintage', 'thrift'),
    'library': ('read', 'book', 'study', 'research', 'history'), 'coffee': ('coffee', 'cafe', 'café', 'tea'),
    'museum': ('art', 'museum', 'history', 'science', 'painting', 'gallery'),
    'show': ('music', 'concert', 'theater', 'theatre', 'gig', 'band', 'comedy', 'jazz'),
    'workout': ('fitness', 'gym', 'running', 'run', 'yoga', 'climbing', 'sport', 'lifting'),
    'home-cooking': ('cook', 'cooking', 'baking', 'bake', 'recipe', 'food'), 'market': ('food', 'market', 'cooking'),
    'walk': ('nature', 'hiking', 'walk', 'walking', 'outdoors', 'beach', 'birds', 'photography'),
    'dinner': ('food', 'restaurant', 'dining'), 'drinks': ('cocktail', 'wine', 'beer', 'bar'),
}
LEANING_WEIGHT = 3


def leanings(definition: dict) -> set[str]:
    """Activity keys the character's interests and life themes point toward."""
    words = set()
    for phrase in [*definition.get('interests', ()), *definition.get('life_themes', ())]:
        words |= {word.strip('.,;:!?()"\'').casefold() for word in phrase.split()}
    return {key for key, stems in LEANINGS.items()
            if any(word == stem or len(stem) > 3 and word.startswith(stem) for word in words for stem in stems)}


def choose(rng, options, definition: dict):
    """An activity, with the character's interests weighing in. Without a matching interest the
    choice is uniform, exactly as before interests counted."""
    favored = leanings(definition)
    if not favored & {option.key for option in options}:
        return rng.choice(options)
    weights = [LEANING_WEIGHT if option.key in favored else 1 for option in options]
    return rng.choices(options, weights)[0]


def day_part(start: str) -> str:
    """The world data's part of the day for a block starting at this local "HH:MM"."""
    hour = int(start.split(':')[0])
    if 5 <= hour < 12:
        return 'morning'
    if 12 <= hour < 17:
        return 'afternoon'
    if 17 <= hour < 22:
        return 'evening'
    return 'late'


def home_city(definition: dict) -> str:
    return definition.get('home_city') or definition.get('location') or ''


def weather(world, definition: dict, local_date: str) -> dict | None:
    """Typical weather in the character's city on this date, from the world's climate data (the same
    for everyone in the city). None when the world or city has no climate."""
    lookup, city = getattr(world, 'weather', None), home_city(definition)
    found = lookup(city, date.fromisoformat(local_date)) if lookup and city else None
    return found and {key: found[key] for key in ('season', 'high_f', 'low_f', 'rain', 'note')}


def harsh(conditions: dict | None) -> bool:
    """Rain or extreme heat or cold, when outdoor plans give way to indoor ones."""
    return bool(conditions) and (conditions['rain'] or conditions['high_f'] >= 93 or conditions['high_f'] <= 38)


def find_places(world, definition: dict, slot: dict, kinds) -> list:
    """Places in the character's home city, or the city its location names, that are open at the
    slot's time of day and in season on its date; a circle member's haunts first."""
    city = home_city(definition)
    if not city or not kinds:
        return []
    found = world.places(city, kinds, day_part=day_part(slot['block']['start']),
                        day=date.fromisoformat(slot['local_date']))
    # A circle member's regular haunts come first when one fits.
    haunts = set(definition.get('haunts') or ())
    return [place for place in found if place.name in haunts] or found


def compose(slot: dict, definition: dict, world, seed: str, recent_activities=(), company=(),
            celebrants=()) -> dict | None:
    """The event for one slot, or None when the slot stays quiet. `company` are circle members
    free at the time ({id, name}); a social activity may name one of them. `celebrants` are circle
    members whose birthday it is."""
    rng = random.Random(seed)
    block = slot['block']
    options = CATALOG.get(block['kind'])
    if not options or rng.random() < QUIET_SHARE:
        return None
    # Prefer activities that did not just happen, so variety comes from the routine, not drama.
    conditions = block.get('weather') or weather(world, definition, slot['local_date'])
    if outing := birthday(slot, definition, world, seed, recent_activities, celebrants, conditions):
        return outing
    if outing := festival(slot, definition, world, seed, recent_activities, company, conditions):
        return outing
    if harsh(conditions):
        # Bad weather moves the day indoors: no walks, and no workout in the park.
        options = [option for option in options if not option.place_kinds or set(option.place_kinds) - OUTDOOR] \
            or options
    fresh = [option for option in options if option.key not in set(recent_activities)] or list(options)
    chosen = choose(rng, fresh, definition)
    places = find_places(world, definition, slot, chosen.place_kinds)
    if harsh(conditions):
        places = [place for place in places if place.kind not in OUTDOOR]
    place = rng.choice(places) if places else None
    values = {'name': definition['name'], 'label': block['label'].lower(),
              'at': f' at {place.name}' if place else chosen.generic, 'place': place.name if place else '',
              'area': f' in {place.neighborhood}' if place and place.neighborhood and place.neighborhood not in
              place.name else ''}
    friend = company[int(rng.random() * len(company))] if company and chosen.together else None
    if friend:
        summary = rng.choice(chosen.together).format(**values, friend=friend['name'])
    else:
        summary = rng.choice(chosen.summaries).format(**values)
    post = rng.choice(chosen.captions)
    if conditions and conditions['rain'] and not chosen.place_kinds and random.Random(f'{seed}:rain').random() < 0.5:
        post = random.Random(f'{seed}:rain').choice(RAINY_CAPTIONS)
    return {'summary': summary[0].upper() + summary[1:], 'post': post,
            'mood': rng.choice(chosen.moods), 'activity': chosen.key, 'place': place.view() if place else None,
            'with': friend, 'weather': conditions, 'composer_version': COMPOSER_VERSION}


# Plans (PRD T2): a planned outing is not a completed outing. A plan names a future routine slot;
# when that slot is simulated, the outing happens as planned and links back to the plan.
PLAN_SHARE = 0.15
PLANNABLE = {
    'walk': ('go for a walk{at}', 'went for a walk{at}'),
    'coffee': ('get coffee{at}', 'got coffee{at}'),
    'museum': ('spend a few hours{at}', 'spent a few hours{at}'),
    'market': ('browse the stalls{at}', 'browsed the stalls{at}'),
    'dinner': ('have dinner with an old friend{at}', 'had dinner with an old friend{at}'),
    'drinks': ('meet friends for drinks{at}', 'met friends for drinks{at}'),
    'show': ('see a show{at}', 'saw a show{at}'),
    'workout': ('fit in a workout{at}', 'fit in a workout{at}'),
}
PLANNING_KINDS = {'leisure', 'social'}


def find_activity(key) -> Activity:
    return next(option for options in CATALOG.values() for option in options if option.key == key)


PLANNABLE_TOGETHER = {
    'dinner': ('have dinner with {friend}{at}', 'had dinner with {friend}{at}'),
    'drinks': ('meet {friend} for drinks{at}', 'met {friend} for drinks{at}'),
    'show': ('see a show{at} with {friend}', 'saw a show{at} with {friend}'),
}


def outing_text(key: str, tense: int, at: str, friend: dict | None) -> str:
    if friend and key in PLANNABLE_TOGETHER:
        return PLANNABLE_TOGETHER[key][tense].format(at=at, friend=friend['name'])
    return PLANNABLE[key][tense].format(at=at)


def plan_ahead(definition: dict, world, seed: str, future_slots: list[dict], upcoming=None) -> dict | None:
    """Sometimes, a plan for one upcoming leisure or social slot. `upcoming` maps slot keys to the
    precomputed agenda entry (None when that slot is quiet), so a plan reveals what was already
    going to happen instead of contradicting it."""
    upcoming = upcoming or {}
    rng = random.Random(f'plan:{seed}')
    targets = [slot for slot in future_slots if slot['block']['kind'] in PLANNING_KINDS and (
        slot['key'] not in upcoming or (upcoming[slot['key']] or {}).get('activity') in PLANNABLE)]
    if not targets or rng.random() >= PLAN_SHARE:
        return None
    target = rng.choice(targets)
    entry = upcoming.get(target['key'])
    if entry:
        chosen, place, friend = find_activity(entry['activity']), entry['place'], entry.get('with')
    else:
        options = [option for option in CATALOG[target['block']['kind']] if option.key in PLANNABLE]
        chosen = rng.choice(options)
        places = find_places(world, definition, target, chosen.place_kinds)
        place = rng.choice(places).view() if places else None
        friend = None
    at = f" at {place['name']}" if place else chosen.generic
    day = date.fromisoformat(target['local_date']).strftime('%A')
    summary = f"{definition['name']} is planning to {outing_text(chosen.key, 0, at, friend)} on {day} " \
              f"({target['block']['label'].lower()})."
    return {'summary': summary, 'activity': chosen.key, 'place': place, 'with': friend,
            'target': target, 'composer_version': COMPOSER_VERSION}


def fulfil(plan: dict, definition: dict) -> dict:
    """The outing a committed plan described, happening in its slot."""
    details = plan['details']
    place, friend = details.get('place'), details.get('with')
    chosen = find_activity(details['activity'])
    at = f" at {place['name']}" if place else chosen.generic
    summary = f"{definition['name']} {outing_text(chosen.key, 1, at, friend)}, as planned."
    rng = random.Random(f"fulfil:{plan['id']}")
    return {'summary': summary, 'post': rng.choice(chosen.captions), 'mood': rng.choice(chosen.moods),
            'activity': chosen.key, 'place': place, 'with': friend, 'composer_version': COMPOSER_VERSION,
            'fulfils': plan['id']}


# Unresolved threads (PRD T2): a small open question in the companion's life that settles a few days
# later, one way or the other. They stay ordinary in scale; nothing here is a major life change.
THREAD_SHARE = 0.1


@dataclass(frozen=True)
class Thread:
    key: str
    opening: str
    endings: tuple[str, ...]
    days: tuple[int, int] = (2, 5)


THREADS = (
    Thread('repair', '{name} reported a leaky faucet to the landlord and is waiting for the repair.',
           ('The landlord finally sent someone to fix {name}\'s leaky faucet.',
            '{name} gave up waiting and fixed the leaky faucet with the help of a video.')),
    Thread('parcel', '{name} ordered a secondhand record player and is waiting for it to arrive.',
           ('{name}\'s record player arrived, and it works.',
            'The record player arrived with a cracked lid, but it still plays.')),
    Thread('waitlist', '{name} joined the waitlist for an evening pottery class.',
           ('A spot opened up in the pottery class, and {name} took it.',
            'The pottery class filled up, so {name} is on the list for next term.')),
    Thread('novel', '{name} started a long novel for a friend\'s book club.',
           ('{name} finished the novel just in time for book club.',
            '{name} went to book club only halfway through the novel and enjoyed it anyway.')),
    Thread('friend-visit', 'An old friend of {name}\'s might come to visit, but nothing is settled yet.',
           ('The friend booked the trip, and {name} is already making a list of places to go.',
            'The friend\'s visit fell through for now; they promised to try again in the spring.')),
    Thread('plant', '{name} is trying to rescue a drooping houseplant.',
           ('{name}\'s houseplant perked up with new leaves.',
            'The houseplant did not make it; {name} kept a cutting just in case.')),
)


def find_thread(key) -> Thread:
    return next(thread for thread in THREADS if thread.key == key)


def open_thread(definition: dict, seed: str, local_date: str, used=()) -> dict | None:
    """Sometimes, a new open thread; never one of the keys in `used`."""
    rng = random.Random(f'thread:{seed}')
    options = [thread for thread in THREADS if thread.key not in set(used)]
    if not options or rng.random() >= THREAD_SHARE:
        return None
    chosen = rng.choice(options)
    settles = date.fromisoformat(local_date) + timedelta(days=rng.randint(*chosen.days))
    return {'summary': chosen.opening.format(name=definition['name']), 'thread': chosen.key,
            'settles_on': settles.isoformat(), 'composer_version': COMPOSER_VERSION}


def settle_thread(thread: dict, definition: dict) -> dict:
    """How a committed open thread turned out, seeded by the thread so a retry agrees."""
    details = thread['details']
    rng = random.Random(f"settle:{details['thread_key']}")
    ending = rng.choice(find_thread(details['thread']).endings)
    return {'summary': ending.format(name=definition['name']), 'thread': details['thread'],
            'composer_version': COMPOSER_VERSION}
