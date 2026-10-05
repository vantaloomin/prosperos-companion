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

COMPOSER_VERSION = 'compose-1'
QUIET_SHARE = 0.2


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


def find_places(world, definition: dict, slot: dict, kinds) -> list:
    """Places in the character's home city, or the city its location names, that are open at the
    slot's time of day and in season on its date."""
    city = definition.get('home_city') or definition.get('location') or ''
    if not city or not kinds:
        return []
    return world.places(city, kinds, day_part=day_part(slot['block']['start']),
                        day=date.fromisoformat(slot['local_date']))


def compose(slot: dict, definition: dict, world, seed: str, recent_activities=(), company=()) -> dict | None:
    """The event for one slot, or None when the slot stays quiet. `company` are circle members
    free at the time ({id, name}); a social activity may name one of them."""
    rng = random.Random(seed)
    block = slot['block']
    options = CATALOG.get(block['kind'])
    if not options or rng.random() < QUIET_SHARE:
        return None
    # Prefer activities that did not just happen, so variety comes from the routine, not drama.
    fresh = [option for option in options if option.key not in set(recent_activities)] or list(options)
    chosen = rng.choice(fresh)
    places = find_places(world, definition, slot, chosen.place_kinds)
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
    return {'summary': summary[0].upper() + summary[1:], 'post': rng.choice(chosen.captions),
            'mood': rng.choice(chosen.moods), 'activity': chosen.key, 'place': place.view() if place else None,
            'with': friend, 'composer_version': COMPOSER_VERSION}


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
