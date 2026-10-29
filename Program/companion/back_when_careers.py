"""Work in a Back when world (companion/back_when.py): everyone's job drawn again for the age they were then.

Someone a lawyer at 34 wasn't one at 19, and nobody drove for a ride app in 2005. In the new world, once ages are
rolled back (companion/back_when_rollback.py), a job that doesn't fit is drawn again by rule, the way the city draws
its townsfolk's (generators.town_career), for their age then and the jobs of that year (catalog.careers_for reads
the world's year, companion/world/decades.py):

- a job that wasn't offered that year, or isn't done at their age then (Career.ages), goes;
- so does well-paid work (DEGREE_PAY) before DEGREE_AGE, which takes a degree or years to reach: at 18 to 22 they
  were at college then, if the city has one;
- someone in the circle retired now and younger than retiring age then was still working.

A job that fits stays as it was. Townsfolk need none of this: they are drawn on demand, at their age then
(companion/world/townsfolk.py). No model decides anything.
"""
from companion import characters
from companion.database import decode, encode, optional
from companion.life import circle
from companion.life.outings import city_data
from companion.world import catalog, generators, lifespans

DEGREE_PAY = ('$$$', '$$$$')
DEGREE_AGE = 23
STUDENT = 'undergraduate'
RETIRED = 'Retired'


def fits(career: dict | None, age: int) -> bool:
    """Whether someone this age (in human terms) did this job, out of the jobs offered that year."""
    return career is not None and generators.fits_age(career, age) and \
        not (age < DEGREE_AGE and career.get('pay') in DEGREE_PAY)


def drawn(city: dict, seed: str, age: int, degree: bool) -> dict | None:
    """A job for someone this age that year: college for a young one headed for well-paid work, else one the city
    draws, as for its townsfolk; None when the city has nothing for that age."""
    offered = catalog.careers_for(city)
    student = offered.get(STUDENT)
    if degree and student and generators.fits_age(student, age):
        return student
    return generators.town_career(city, seed, 'back-when', fits=lambda key: fits(offered[key], age), age=age)


def companion_then(connection, definition: dict, age: int | None, seed: str) -> dict:
    """Their definition with a job that fits their age then (`age`, None when it can't be told), and their week's
    work blocks named for it."""
    city = city_data(connection, definition)
    chosen = (definition.get('money') or {}).get('career') or ''
    if not city or not chosen or age is None:
        return definition
    offered = catalog.careers_for(city)
    if fits(offered.get(chosen), age):
        return definition
    was = catalog.careers_for(city, needs_met=False).get(chosen) or {}
    career = drawn(city, seed, age, was.get('pay') in DEGREE_PAY)
    if career is None:
        return definition
    found = {**definition, 'money': {**(definition.get('money') or {}), 'career': career['id']}}
    return {**found, 'schedule': characters.relabeled(connection, found)}


def circle_then(connection, timeline_id: str, definition: dict, year: int, now_stamp: str):
    """Everyone in the circle at a job that fits their age then; a partner's card says the same."""
    city = city_data(connection, definition)
    if not city:
        return
    offered = catalog.careers_for(city)
    for person in circle.people(connection, timeline_id):
        details = decode(person['details']) or {}
        span = lifespans.lifespan_of(details.get('folk') or lifespans.HUMAN, city)
        age = lifespans.life_age(details.get('age'), span) if isinstance(details.get('age'), int) else None
        if age is None or not needs_new(person, details, offered, age):
            continue
        was = catalog.careers_for(city, needs_met=False).get(person['career']) or {}
        career = drawn(city, f"{person['seed']}|back-when:{year}", age, was.get('pay') in DEGREE_PAY)
        if career:
            hire(connection, city, person, details, career, f"{person['seed']}|back-when:{year}", now_stamp)


def needs_new(person: dict, details: dict, offered: dict, age: int) -> bool:
    """A job that doesn't fit their age or year, or retired before retiring age."""
    if person['career']:
        return not fits(offered.get(person['career']), age)
    return details.get('career') == RETIRED and age < generators.RETIRED_AT and details.get('local', True)


def hire(connection, city: dict, person: dict, details: dict, career: dict, seed: str, now_stamp: str):
    job = generators.job(city, career['id'], seed=seed)
    found = {key: value for key, value in details.items() if key != 'retired_on'} | {
        'career': career['name'], 'employer': job['employer']['name'], 'neighborhood': job['neighborhood']['name']}
    connection.execute('UPDATE circle_people SET career=?, details=?, schedule=?, updated_at=? WHERE id=?',
                       (career['id'], encode(found), encode(job['schedule']), now_stamp, person['id']))
    partner = optional(connection, 'SELECT id, details FROM love_partners WHERE person_id=?', (person['id'],))
    if partner:
        card = decode(partner['details']) or {}
        connection.execute('UPDATE love_partners SET details=? WHERE id=?',
                           (encode(card | {'career': found['career'], 'employer': found['employer']}), partner['id']))
