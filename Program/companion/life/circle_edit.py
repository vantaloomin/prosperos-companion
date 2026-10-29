"""The user's own changes to the people in the companion's life (PRD T8), after the app has made them.

The app still decides first: everyone in the circle is seeded (companion/life/circle.py), and the people the
character sheet names take their places with the relation, job and age it gives (companion/life/named.py). From the
circle list the user can then change anyone's name, how they know the companion, pronouns, job and workplace, age,
whether they live in town, and a note the chat reads, or add someone by hand, giving as little as a name; the app
fills in the rest the way it would for someone the sheet names. Someone the user adds or makes a mom, dad or spouse
takes that place from the one the app made, who steps aside as for someone shared in (companion/life/shared_people.py)
and comes back if the user takes them out again. A job is kept in the user's own words; the career it
matches (companion/life/job_words.py) gives their week its hours. What the user set is listed in the person's
`edited`, so the app's later passes (family names) leave it be. What already happened keeps what it said.
"""
import re

from companion.clock import stamp
from companion.database import decode, encode, one
from companion.errors import require
from companion.life import circle, job_words, named, shared_people
from companion.world import catalog, generators

FIELDS = ('name', 'role', 'pronouns', 'job', 'employer', 'age', 'local', 'note', 'start_stage', 'knowing')
NOTE_MAX = 300


def words_person(change: dict) -> dict:
    """Someone the user names in words, in the shape the sheet's people have (named.people): their relation word
    gives their kind and the generator's role, as it does for the sheet's."""
    role = ' '.join((change.get('role') or 'friend').split()).casefold()
    kind, pronouns, generator_role = named.RELATIONS.get(role, (role, '', 'friend'))
    return {'name': ' '.join(change['name'].split()), 'relation': role, 'kind': kind,
            'pronouns': change.get('pronouns') or pronouns, 'role': named.ROLE_WORDS.get(role, role),
            'generator_role': generator_role, 'local': change.get('local', True), 'job': change.get('job') or '',
            'employer': change.get('employer') or '', 'sure': True, 'age': change.get('age'), 'by_hand': True}


def add(connection, companion: dict, world, change: dict, now) -> dict:
    """Someone the user adds by hand, after everyone else; anything left out the app picks. Spared from passing away
    unless the user says otherwise, like someone written into the character."""
    definition, timeline_id = companion['version']['definition'], companion['active_timeline_id']
    rows = circle.people(connection, timeline_id, include_removed=True)
    ordinal = max((row['ordinal'] for row in rows), default=-1) + 1
    person, seed = words_person(change), f'circle:{timeline_id}:by-hand:{ordinal}'
    data = circle.city_data(definition, world)
    made = circle.city_named(data, definition, timeline_id, person, seed) if data else \
        circle.plain_named(definition, person, seed, ordinal)
    note = (change.get('note') or '').strip()[:NOTE_MAX]
    made['details'] = made['details'] | {'by_hand': True, 'spared': True, 'edited': sorted(
        key for key in FIELDS if change.get(key) not in (None, ''))} | ({'note': note} if note else {}) | (
        {'start_stage': change['start_stage']} if change.get('start_stage') else {}) | (
        {'knowing': change['knowing']} if change.get('knowing') else {})
    circle.insert(connection, timeline_id, [made], ordinal, now)
    added = one(connection, 'SELECT * FROM circle_people WHERE timeline_id=? AND ordinal=?', (timeline_id, ordinal))
    connection.execute('INSERT OR IGNORE INTO agenda_cursors (timeline_id, subject, through) VALUES (?, ?, ?)',
                       (timeline_id, added['id'], stamp(now)))
    shared_people.step_aside(connection, companion, added['seed'], added['role'], now)
    return added


def edit(connection, companion: dict, world, person_id: str, change: dict, now) -> dict:
    """The user's changes to one person: only the fields given change. A new job or workplace, or moving into town,
    gives them a new week to match; moving away clears it."""
    row = circle.person(connection, person_id)
    require(row['status'] == 'active', 'Restore this person before changing them.', 409)
    definition = companion['version']['definition']
    data = circle.city_data(definition, world)
    details, given = decode(row['details']), {key: value for key, value in change.items() if value is not None}
    made = {'name': row['name'], 'role': row['role'], 'career': row['career'], 'details': dict(details),
            'schedule': decode(row['schedule']) or []}
    made = basics(made, given)
    seed = f"{row['seed']}:edit:{row['revision'] + 1}"
    moved = 'local' in given and given['local'] != details.get('local', True)
    if moved:
        made = move(made, given['local'], data, seed)
    if moved or 'job' in given or 'employer' in given:
        made = new_job(made, given, data, seed)
    made['details']['edited'] = sorted(set(details.get('edited', ())) | set(given))
    connection.execute('UPDATE circle_people SET name=?, role=?, career=?, details=?, schedule=?, revision=revision+1, '
                       'updated_at=? WHERE id=?',
                       (made['name'], made['role'], made['career'], encode(made['details']),
                        encode(made['schedule']), stamp(now), person_id))
    if 'role' in given:
        shared_people.step_aside(connection, companion, row['seed'], made['role'], now)
    return one(connection, 'SELECT * FROM circle_people WHERE id=?', (person_id,))


def basics(made: dict, given: dict) -> dict:
    """Name, relation, pronouns, age and note: what changes nothing else about their week."""
    details = made['details']
    if 'name' in given:
        name = ' '.join(given['name'].split())
        if details.get('note') and 'note' not in given:
            details['note'] = renamed_note(details['note'], made['name'], name)
        made['name'] = name
        if ' ' in name:
            details['full_name'] = name
    if 'role' in given:
        made['role'] = ' '.join(given['role'].split()).casefold()
    if given.get('pronouns'):
        details['pronouns'] = given['pronouns']
    if 'age' in given:
        details['age'] = given['age']
    # Where they start with the companion (memory/pairs.py) and whether they know each other (circle.knowing); 0 or ''
    # is the app's pick again.
    for key in ('start_stage', 'knowing'):
        picked(details, given, key)
    if 'note' in given:
        note = given['note'].strip()[:NOTE_MAX]
        details |= {'note': note} if note else {}
        if not note:
            details.pop('note', None)
    return made


def picked(details: dict, given: dict, key: str):
    """The user's pick for one of `details` when given; an empty one hands it back to the app."""
    if key in given:
        details.pop(key, None)
        details |= {key: given[key]} if given[key] else {}


def renamed_note(note: str, old: str, new: str) -> str:
    """The note with their old first name swapped for the new one, so it doesn't speak of someone else."""
    before, after = old.split()[0] if old.split() else '', new.split()[0]
    if not before or before == after:
        return note
    return re.sub(rf"\b{re.escape(before)}\b", after, note)


def move(made: dict, local: bool, data: dict | None, seed: str) -> dict:
    """Out of town: no home, haunts or week here. Into town: a home and haunts in the city, as a seeded resident
    would have (their job follows in new_job)."""
    details = made['details'] | {'local': local}
    if not local:
        return made | {'schedule': [], 'details': details | {'city': '', 'neighborhood': '', 'haunts': []}}
    if data:
        member = generators.resident(data, seed=seed, role='friend', age=details.get('age') or None)
        details |= {'city': data['name'], 'neighborhood': member['home']['neighborhood']['name'],
                    'haunts': [spot['name'] for spot in member['haunts']]}
    return made | {'details': details}


def new_job(made: dict, given: dict, data: dict | None, seed: str) -> dict:
    """Their job in the user's words (or as it was, for a new workplace or a move): the matched career's week at the
    workplace they name when the city has it, else circle.with_job's."""
    details = made['details']
    if 'job' not in given and details.get('works_with_companion'):
        return made | {'details': details | {'employer': given.get('employer', details.get('employer', ''))}}
    words = given['job'] if 'job' in given else details.get('career') or ''
    employer = given['employer'] if 'employer' in given else details.get('employer') or ''
    offered = catalog.everyday(catalog.careers_for(data) if data else catalog.careers())
    career = offered.get(made['career']) if 'job' not in given and made['career'] else None
    career = career or (None if job_words.no_job(words) else job_words.career_match(words, offered))
    local = details.get('local', True)
    if career and local and data:
        home = next((hood['id'] for hood in data['neighborhoods'] if hood['name'] == details.get('neighborhood')), None)
        record = circle.place_named(data, employer)
        work = generators.job(data, career['id'], seed=seed, home=home, employer=record)
        made = made | {'schedule': work['schedule']}
        employer = employer if employer and not record else work['employer']['name']
    elif career and local:
        made = made | {'schedule': generators.schedule(career, seed, employer)}
    elif not local:
        made = made | {'schedule': []}
    shown = job_words.no_job(words)[0] if job_words.no_job(words) else job_words.label(words)
    made = circle.with_job(made | {'details': {**details, 'employer': ''}}, shown, career, employer, seed)
    return made
