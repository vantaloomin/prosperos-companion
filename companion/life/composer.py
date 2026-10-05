"""Deterministic event composition (PRD T2, T3).

A routine slot becomes an ordinary event without any model call: the block's kind selects an
activity, the world source supplies a real place for it, and fixed templates write the summary,
caption and mood. The same slot always composes the same event, so a resumed batch is stable.
A model may later rephrase the wording, but never chooses the place, activity or facts.

Some slots are deliberately quiet: an uneventful stretch is a valid outcome, not a failure.
"""
import random
from dataclasses import dataclass
from datetime import date

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


def activity(key, place_kinds, summaries, captions, moods, generic='') -> Activity:
    """`generic` stands in for " at <place>" when the world has no matching place."""
    return Activity(key, tuple(place_kinds), tuple(summaries), tuple(captions), tuple(moods), generic)


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
                 ['Good food, better company.', 'We closed the place down.'], ['happy', 'warm'], ''),
        activity('drinks', ('bar',), ['{name} met a couple of friends for drinks{at}.'],
                 ['One drink turned into three stories.', 'Laughed too much.'], ['cheerful'], ''),
        activity('show', ('venue',), ['{name} went to see a show{at} with a friend.'],
                 ['Still humming it.', 'Live music hits different.'], ['excited'], ''),
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


def compose(slot: dict, definition: dict, world, seed: str, recent_activities=()) -> dict | None:
    """The event for one slot, or None when the slot stays quiet."""
    rng = random.Random(seed)
    block = slot['block']
    options = CATALOG.get(block['kind'])
    if not options or rng.random() < QUIET_SHARE:
        return None
    # Prefer activities that did not just happen, so variety comes from the routine, not drama.
    fresh = [option for option in options if option.key not in set(recent_activities)] or list(options)
    chosen = rng.choice(fresh)
    place = None
    city = definition.get('home_city') or ''
    if chosen.place_kinds and city:
        places = world.places(city, chosen.place_kinds)
        place = rng.choice(places) if places else None
    values = {'name': definition['name'], 'label': block['label'].lower(),
              'at': f' at {place.name}' if place else chosen.generic, 'place': place.name if place else '',
              'area': f' in {place.neighborhood}' if place and place.neighborhood and place.neighborhood not in
              place.name else ''}
    summary = rng.choice(chosen.summaries).format(**values)
    return {'summary': summary[0].upper() + summary[1:], 'post': rng.choice(chosen.captions),
            'mood': rng.choice(chosen.moods), 'activity': chosen.key, 'place': place.view() if place else None,
            'composer_version': COMPOSER_VERSION}


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


def plan_ahead(definition: dict, world, seed: str, future_slots: list[dict]) -> dict | None:
    """Sometimes, a plan for one upcoming leisure or social slot."""
    rng = random.Random(f'plan:{seed}')
    targets = [slot for slot in future_slots if slot['block']['kind'] in PLANNING_KINDS]
    if not targets or rng.random() >= PLAN_SHARE:
        return None
    target = rng.choice(targets)
    options = [option for option in CATALOG[target['block']['kind']] if option.key in PLANNABLE]
    chosen = rng.choice(options)
    city = definition.get('home_city') or ''
    places = world.places(city, chosen.place_kinds) if city and chosen.place_kinds else []
    place = rng.choice(places) if places else None
    at = f' at {place.name}' if place else chosen.generic
    day = date.fromisoformat(target['local_date']).strftime('%A')
    summary = f"{definition['name']} is planning to {PLANNABLE[chosen.key][0].format(at=at)} on {day} " \
              f"({target['block']['label'].lower()})."
    return {'summary': summary, 'activity': chosen.key, 'place': place.view() if place else None,
            'target': target, 'composer_version': COMPOSER_VERSION}


def fulfil(plan: dict, definition: dict) -> dict:
    """The outing a committed plan described, happening in its slot."""
    details = plan['details']
    place = details.get('place')
    chosen = find_activity(details['activity'])
    at = f" at {place['name']}" if place else chosen.generic
    summary = f"{definition['name']} {PLANNABLE[chosen.key][1].format(at=at)}, as planned."
    rng = random.Random(f"fulfil:{plan['id']}")
    return {'summary': summary, 'post': rng.choice(chosen.captions), 'mood': rng.choice(chosen.moods),
            'activity': chosen.key, 'place': place, 'composer_version': COMPOSER_VERSION, 'fulfils': plan['id']}
