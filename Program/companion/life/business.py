"""Starting a business (Hit List #68, v0.14 Years Go By): one of Life's big turns, part 2 (companion/life/big_turns.py).

The engine picks it like any chapter (`chapter:next`, likelier for the driven and with money coming in). The app picks
the business from the bank (world/data/life_chapters.json `businesses`, by era) and when it opens; until then they
keep their job. On opening day what it took to set up comes out of their savings (`purchases`), their working hours
become the business's (the overlay's `business`, applied by companion/characters.py), Work life steps aside
(companion/life/work.py `works`) and their pay is what the business makes (`pay`, a share of their old pay that starts
lean). Every three months the consequence engine says how it went (`business:how`): it grows, ticks along, stalls or
folds. Growing and stalling move what it makes; folding closes it, they live on a little while they look for work, then
go back to their old line of work. On Gentle a business never folds (Vanta 2026-10-18: good turns only on an easy life).
After two years open it is simply how they make a living, and the turn ends there. Nothing here calls a model.
"""
import random
from datetime import date, timedelta

from companion import consequences
from companion.clock import stamp
from companion.database import decode, many
from companion.life import big_turns, money
from companion.memory import pairs

CHOICE = 'business:how'
OPEN_DAYS = (30, 90)  # From deciding until opening day.
CHECK_DAYS = 91  # How it is going, every three months.
CHECKS = 8  # After two years open the turn ends.
HUNT_DAYS = (21, 60)  # After it folds, until they are back at work.
YOUNGEST, OLDEST = 23, 62
# What it makes, as a share of their old pay: lean at first, then up or down with each check.
START, GROW, STALL, LOWEST, HIGHEST, BETWEEN = 0.7, 0.25, 0.2, 0.4, 1.8, 0.4
OUTCOMES = ('grows', 'steady', 'stalls', 'folds')


def noun(entry: dict) -> str:
    """'small bakery' from 'a small bakery', 'bookkeeping practice' from 'a bookkeeping practice of their own'."""
    return entry['business'].split(' ', 1)[1].removesuffix(' of their own')


def own(entry: dict) -> str:
    return f'your {noun(entry)}'


def plan(connection, companion, world, day, seed) -> dict | None:
    age = big_turns.free(connection, companion, day)
    definition = companion['version']['definition']
    city = money.city_for(definition)
    found = money.profile(definition)
    if age is None or not YOUNGEST <= age < OLDEST or not big_turns.works(definition) or not found or not city \
            or not money.has_money(city) or definition.get('business'):
        return None
    entry = random.Random(f'{seed}:business').choice(big_turns.data()['businesses'][big_turns.era(city)])
    opens = day + timedelta(days=random.Random(f'{seed}:opens').randint(*OPEN_DAYS))
    cost = round(money.monthly_share(found) * entry['cost'], 2)
    name, when = big_turns.first(definition), big_turns.day_text(opens)
    return {'title': f"{name} is starting {entry['business']}",
            'told': f"You decided to start {entry['business']} of your own; you keep your job until it opens on {when}.",
            'share': f"I'm doing it. I'm opening {entry['business']}! Opening day is {when}.",
            'details': {'stage': 'planning', 'next_on': opens.isoformat(), 'opens_on': opens.isoformat(),
                        'business': entry, 'startup': {'on': opens.isoformat(), 'cost': cost}, 'factor': START,
                        'checks': 0}}


def opening(connection, companion, row, details, day, now) -> dict:
    name, entry = big_turns.first(companion['version']['definition']), details['business']
    return {'title': f"{name} opened {entry['business']}", 'changes': changes(entry),
            'told': f"You opened {entry['business']} on {big_turns.day_text(day)} and left your job; it is your work "
                    'now, and the first months are lean.',
            'share': f"We're open!! Day one of the {noun(entry)}.",
            'details': {'stage': 'open', 'next_on': (day + timedelta(days=CHECK_DAYS)).isoformat(),
                        'opens_on': day.isoformat(), 'startup': {**details['startup'], 'on': day.isoformat()}}}


def changes(entry: dict) -> dict:
    return {'business': {'label': entry['label'], 'short': entry['short'], 'business': entry['business']}}


def check(connection, companion, row, details, day, now) -> dict:
    """Three months on: the engine says how it went."""
    definition = companion['version']['definition']
    names = {'name': big_turns.first(definition), 'a': f"the {noun(details['business'])}", 'b': ''}
    facts = {'turns': big_turns.level(connection), 'checks': details['checks'], 'factor': round(details['factor'] * 10),
             'sheet': {group for group in consequences.WORDS if consequences.sheet_has(definition, group)},
             'money': consequences.total(connection, row['timeline_id'], pairs.companion_key(companion['id']), 'money',
                                         day.isoformat())}
    labels = [option['label'].format(**names) for option in consequences.tables()[CHOICE]['options']]
    outcome = consequences.decide(connection, timeline_id=row['timeline_id'], choice=CHOICE,
                                  subject=f"business:{row['id']}:{details['checks']}", facts=facts, names=names,
                                  labels=labels, day=day.isoformat(), timestamp=stamp(now),
                                  holders={'me': pairs.companion_key(companion['id'])}, now=now)
    picked = OUTCOMES[outcome['picked']]
    update = folded(companion, details, day) if picked == 'folds' else going(companion, details, day, picked)
    return {**update, 'undo': {'decided': [outcome['id']]}}


def going(companion, details, day, picked: str) -> dict:
    name, entry, checks = big_turns.first(companion['version']['definition']), details['business'], details['checks'] + 1
    factor = {'grows': min(details['factor'] + GROW, HIGHEST), 'steady': details['factor'],
              'stalls': max(details['factor'] - STALL, LOWEST)}[picked]
    yours, short = own(entry), noun(entry)
    told = {'grows': f'{yours.capitalize()} is doing well: more customers every month, and more money coming in.',
            'steady': f'{yours.capitalize()} is ticking along: steady customers, steady money.',
            'stalls': f'Business is slow at {yours}: fewer customers lately, and money is tighter.'}[picked]
    share = {'grows': f'Best month yet at the {short}!', 'steady': f'The {short} is ticking along nicely.',
             'stalls': f'Slow month at the {short}. Trying not to panic.'}[picked]
    title = {'grows': f"{name}'s {short} is growing", 'steady': f"{name}'s {short} is ticking along",
             'stalls': f"Business is slow at {name}'s {short}"}[picked]
    settled = checks >= CHECKS
    if settled:
        title, told = f"{name}'s {short} is two years old", f'{told} {yours.capitalize()} made it through its first ' \
            'two years; it is how you make your living now.'
    return {'title': title, 'told': told, 'share': share, 'changes': changes(entry),
            'details': {'stage': 'established' if settled else 'open', 'checks': checks, 'factor': round(factor, 2),
                        'how': picked,
                        'next_on': None if settled else (day + timedelta(days=CHECK_DAYS)).isoformat()}}


def folded(companion, details, day) -> dict:
    name, entry = big_turns.first(companion['version']['definition']), details['business']
    back = day + timedelta(days=random.Random(f"{details['opens_on']}:back").randint(*HUNT_DAYS))
    return {'title': f"{name} closed {own(entry).replace('your', 'their', 1)}", 'changes': {},
            'told': f'You closed {own(entry)}: it never made enough to keep going. You are looking for work in your old '
                    'line again.',
            'share': f"I closed the {noun(entry)}. It hurts, but it was the right call.",
            'details': {'stage': 'folded', 'how': 'folds', 'checks': details['checks'] + 1,
                        'back_on': back.isoformat(), 'next_on': back.isoformat()}}


def back_at_work(connection, companion, row, details, day, now) -> dict:
    definition = companion['version']['definition']
    name, job = big_turns.first(definition), big_turns.job_of(definition).removeprefix(' from your job as ')
    work = f' as {job}' if job else ''
    return {'title': f'{name} went back to work{work}', 'changes': {},
            'told': f"You went back to work{work} on {big_turns.day_text(day)}, after closing {own(details['business'])}.",
            'share': 'Back at a regular job today. Steady paycheck, at least.',
            'details': {'stage': 'back', 'next_on': None}}


PLANS = {'business': plan}
STAGES = {('business', 'planning'): opening, ('business', 'open'): check, ('business', 'folded'): back_at_work}


# Money ---------------------------------------------------------------------------------------------------------

def latest(connection, timeline_id: str) -> dict | None:
    rows = many(connection, "SELECT * FROM life_chapters WHERE timeline_id=? AND kind='business' AND "
                          'undone_at IS NULL ORDER BY started_on DESC, created_at DESC LIMIT 1', (timeline_id,))
    return rows[0] if rows else None


def pay(connection, timeline_id: str, day: date, found: dict | None) -> dict | None:
    """Open, what the business makes as a share of their old pay; after it folds, a little to live on until they are
    back at work; otherwise their pay as Work life has it."""
    row = latest(connection, timeline_id)
    details = decode(row['details']) if row else {}
    if details.get('stage') in ('open', 'established') and details['opens_on'] <= day.isoformat():
        return {'factor': details['factor'], 'between_jobs': False, 'business': noun(details['business'])}
    if details.get('stage') == 'folded' and day.isoformat() < details['back_on']:
        return {'factor': BETWEEN, 'between_jobs': True}
    return found


def purchases(connection, timeline_id: str, start: date, end: date) -> list[dict]:
    """What opening the business took, from savings, on opening day."""
    found = []
    for row in many(connection, "SELECT details FROM life_chapters WHERE timeline_id=? AND kind='business' "
                              'AND undone_at IS NULL', (timeline_id,)):
        details = decode(row['details'])
        startup = details.get('startup')
        if startup and details['stage'] != 'planning' and start.isoformat() <= startup['on'] <= end.isoformat():
            found.append({'text': f"put your savings into opening {details['business']['business']}",
                          'shown': f"put their savings into opening {details['business']['business']}",
                          'date': startup['on'], 'cost': startup['cost'], 'spend': '', 'for': 'business',
                          'savings': True})
    return found


# The Character page -------------------------------------------------------------------------------------------

def line(row: dict, details: dict) -> str:
    entry = details['business']
    if details['stage'] == 'planning':
        return f"Starting {entry['business']}; it opens {big_turns.short_day(details['opens_on'])}."
    if details['stage'] == 'open':
        how = {'grows': ' and growing', 'stalls': ', though business is slow'}.get(details.get('how'), '')
        return f"Running {entry['business']}, open since {big_turns.short_day(details['opens_on'])}{how}."
    if details['stage'] == 'folded':
        return f"Closed {own(entry).replace('your', 'their', 1)}; looking for work again."
    return row['title'] + '.'


LINES = {'business': line}
