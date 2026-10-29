"""Rolling a companion's life back to a day in a past year, for a Back when world (companion/back_when.py).

The new world holds a copy of their rows from the present (who they are, their circle, family, kids, home and love
life). Everything here runs in that world, by rules, on the day it opens in:

- Life chapters that began later are taken back the way Undo takes one back (companion/life/chapters.py): the job,
  the move, the pet, the friend who moved away.
- People who passed away later are alive again; kids born later aren't born yet; partners met later haven't been met,
  and a partner they split from later is still with them.
- People who came into their life after the app met them (a new friend, today's coworkers) aren't in it yet, and
  everyone left is younger by their stored birth date. Someone who would be under 18 then steps out of the circle.
- Home items from later go, and a home they moved out of later is still theirs; with no home left from back then, the
  app assembles one for them again (companion/life/home.py).
- Steps between the two of them go: the world starts with the two of you as strangers, unless "Work it out from our
  history" is on, which keeps the steps reached by then, with dates worked out for steps written as history
  (`pair_dates`).
- They are younger: their age, the age in their own words, and a new character version saying how the two of them
  stand.
- Every bookkeeping stamp from later (created_at and the rest) becomes the world's own now, so nothing stored knows
  the future.

No model decides anything.
"""
import re
from datetime import date, timedelta

from companion import characters
from companion.clock import parse, stamp
from companion.database import decode, encode, many, optional
from companion.life import ages, chapters, circle, home, steps
from companion.world_year import same_day

# Coworkers belong to the job they have now; people the app added this long after it met them came later.
LATER = timedelta(days=2)
NOW_ONLY = {'coworker', 'new friend'}
# "Married ten years", "together for a decade": how long ago a step written as history was reached.
NUMBERS = {'a': 1, 'an': 1, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8,
           'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12, 'fifteen': 15, 'twenty': 20, 'a couple of': 2,
           'a couple': 2, 'a few': 3, 'several': 5}
SPAN = re.compile(r'\b(\d{1,2}|' + '|'.join(sorted(NUMBERS, key=len, reverse=True)) + r')\s+years?\b|\b(a decade)\b',
                  re.IGNORECASE)
SINCE_YEAR = re.compile(r'\b(?:since|in|from|back in)\s+((?:19|20)\d\d)\b', re.IGNORECASE)
# How old they were when they met, for "since school" and the like.
MET_AT = ((re.compile(r'\b(?:childhood|grew up|kids|kindergarten|elementary|primary school)\b', re.IGNORECASE), 8),
          (re.compile(r'\b(?:high school|school|secondary)\b', re.IGNORECASE), 15),
          (re.compile(r'\b(?:college|university|uni|campus|dorm)\b', re.IGNORECASE), 19))
# A step written as history with no span in the words was reached about this many years before the anchor.
GUESSED_YEARS = 3
STRANGERS = 'You have never met the user. You are strangers.'


# Dates for the two of them ------------------------------------------------------------------------------------------

def years_in(text: str) -> int | None:
    found = SPAN.search(text or '')
    if not found:
        return None
    if found.group(2):
        return 10
    word = found.group(1).casefold()
    return int(word) if word.isdigit() else NUMBERS.get(word)


def pair_dates(connection, companion: dict, today: date, born: date | None) -> dict:
    """When the two of them met and when each step between them was reached, as far as the app can tell on `today`:
    {'met': date or None, 'steps': [{'ladder', 'step', 'on'}]}. A step with a real date keeps it; steps written as
    history ("married ten years", "best friends since school") get dates worked out from those words, spaced the way
    a true-to-life pace spaces them."""
    definition = companion['version']['definition']
    text = definition.get('history_together') or ''
    ladder = steps.ladder_of(definition)
    if ladder is None:
        return {'met': None, 'steps': []}
    rows = steps.reached(connection, companion['active_timeline_id'], ladder)
    if not rows:
        rows = [{'step': key, 'how': how, 'reached_on': today.isoformat()}
                for key, how in steps.start(connection, companion, ladder, parse(stamp_of(today)))]
    dated = written_dates(ladder, rows, text, today)
    met = min((item['on'] for item in dated), default=None)
    if (school := met_at(text, born)) and (met is None or school < met):
        met = school
    return {'met': met, 'steps': dated}


def stamp_of(day: date) -> str:
    return f'{day.isoformat()}T12:00:00+00:00'


def written_dates(ladder: str, rows: list[dict], text: str, today: date) -> list[dict]:
    """Each step's day: its own for a step reached in the app, worked back from the top step written as history for
    the rest."""
    history = [row for row in rows if row['how'] == 'history']
    found = {row['step']: date.fromisoformat(row['reached_on']) for row in rows if row['how'] != 'history'}
    if history:
        anchor = min(today, *(date.fromisoformat(row['reached_on']) for row in history))
        span = years_in(text)
        written = SINCE_YEAR.search(text)
        top = same_day(anchor, int(written.group(1))) if written and span is None and int(written.group(1)) <= \
            anchor.year else same_day(anchor, anchor.year - (span if span is not None else GUESSED_YEARS))
        keys = [row['step'] for row in sorted(history, key=lambda row: steps.index_of(ladder, row['step']))]
        day = top
        for key in reversed(keys):
            found[key] = day
            day -= timedelta(days=steps.step_of(ladder, key).after[1] or 30)
    return [{'ladder': ladder, 'step': key, 'on': on} for key, on in
            sorted(found.items(), key=lambda item: steps.index_of(ladder, item[0]))]


def met_at(text: str, born: date | None) -> date | None:
    """"Friends since school": the day they met, from how old they were then."""
    if born is None:
        return None
    for pattern, age in MET_AT:
        if pattern.search(text or ''):
            return same_day(born, born.year + age)
    return None


# Rolling back --------------------------------------------------------------------------------------------------------

def roll_back(connection, companion_id: str, day: date, real: date, pair: dict | None, now) -> dict:
    """Their life as it stood on `day` (`real` is the same day in the present). `pair` is how the two of them stood (from `pair_dates`, worked out in the
    world they came from), None to start as strangers. Returns how the two of them stand."""
    companion = characters.by_id(connection, companion_id)
    timeline_id = companion['active_timeline_id']
    undo_chapters(connection, timeline_id, day, now)
    revive(connection, timeline_id, day, now)
    not_born(connection, timeline_id, day)
    partners(connection, timeline_id, day)
    later_people(connection, timeline_id, companion['created_at'], now)
    circle_ages(connection, timeline_id, day, real, now)
    homes(connection, timeline_id, day)
    connection.execute("DELETE FROM relationship_steps WHERE timeline_id=? AND (other=? OR reached_on>?)",
                       (timeline_id, steps.USER, day.isoformat()))
    stand = standing(pair, day)
    for item in stand['steps']:
        steps.insert_step(connection, timeline_id, item['ladder'], item['step'], item['on'], 'history', stamp(now))
    return stand


def undo_chapters(connection, timeline_id: str, day: date, now):
    for row in many(connection, 'SELECT * FROM life_chapters WHERE timeline_id=? AND started_on>? '
                    'ORDER BY started_on DESC, created_at DESC', (timeline_id, day.isoformat())):
        if row['undone_at'] is None:
            chapters.reverse(connection, decode(row['undo']), now)
        connection.execute('DELETE FROM life_chapters WHERE id=?', (row['id'],))


def revive(connection, timeline_id: str, day: date, now):
    """Whoever passed away later is in the circle again."""
    for row in many(connection, 'SELECT * FROM losses WHERE timeline_id=? AND died_on>?', (timeline_id, day.isoformat())):
        person = optional(connection, 'SELECT * FROM circle_people WHERE id=?', (row['person_id'] or '',))
        if person and (decode(person['details']) or {}).get('late'):
            details = {key: value for key, value in decode(person['details']).items() if key != 'late'}
            connection.execute("UPDATE circle_people SET status='active', details=?, updated_at=? WHERE id=?",
                               (encode(details), stamp(now), person['id']))
        connection.execute('DELETE FROM losses WHERE id=?', (row['id'],))


def not_born(connection, timeline_id: str, day: date):
    connection.execute('DELETE FROM circle_children WHERE timeline_id=? AND born_on>?', (timeline_id, day.isoformat()))


def partners(connection, timeline_id: str, day: date):
    """Someone they met later hasn't been met; someone they split from later is still with them."""
    for row in many(connection, 'SELECT id, person_id FROM love_partners WHERE timeline_id=? AND met_on>?',
                    (timeline_id, day.isoformat())):
        forget(connection, timeline_id, row)
    for row in many(connection, 'SELECT id, person_id FROM love_partners WHERE timeline_id=? AND ended_on>?',
                    (timeline_id, day.isoformat())):
        connection.execute('UPDATE love_partners SET ended_on=NULL, ended_how=NULL WHERE id=?', (row['id'],))
        if row['person_id']:
            connection.execute("UPDATE circle_people SET status='active' WHERE id=?", (row['person_id'],))


def forget(connection, timeline_id: str, partner: dict):
    """A partner who isn't one that year: their steps go, and they leave the circle."""
    connection.execute('DELETE FROM relationship_steps WHERE timeline_id=? AND other=?',
                       (timeline_id, f"love:{partner['id']}"))
    if partner['person_id']:
        connection.execute("UPDATE circle_people SET status='removed' WHERE id=?", (partner['person_id'],))
    connection.execute('DELETE FROM love_partners WHERE id=?', (partner['id'],))


def later_people(connection, timeline_id: str, met_at_: str, now):
    """Today's coworkers, and friends who came into their life after the app met them, aren't in it yet. Family
    stays, whenever the app added them."""
    since = parse(met_at_) + LATER
    for person in circle.people(connection, timeline_id):
        role = person['role'].casefold()
        joined = parse(person['created_at']) if person['created_at'] else since
        if role in NOW_ONLY or (joined > since and not set(re.findall(r'\w+', role)) & circle.KIN):
            connection.execute("UPDATE circle_people SET status='removed', updated_at=? WHERE id=?",
                               (stamp(now), person['id']))


def past_age(connection, kind: str, key: str, age: int, day: date, today: date) -> int:
    row = ages.stored(connection, kind, key)
    if row:
        return ages.age_on(date.fromisoformat(row['born_on']), row['birthday'], day)
    return age - (today.year - day.year)


def circle_ages(connection, timeline_id: str, day: date, real: date, now):
    """Everyone in the circle is younger by their stored date; their dates are worked out again from that age when
    the world next counts ages (companion/life/ages.py), so nobody's age is held at the one they have now. Someone who
    would be under 18 then steps out of the circle."""
    for person in circle.people(connection, timeline_id, include_removed=True):
        details = decode(person['details']) or {}
        age = details.get('age')
        if not isinstance(age, int) or details.get('late'):
            continue
        younger = past_age(connection, 'circle', person['id'], age, day, real)
        if younger < ages.ADULT:
            connection.execute("UPDATE circle_people SET status='removed' WHERE id=?", (person['id'],))
        connection.execute('UPDATE circle_people SET details=? WHERE id=?',
                           (encode({**details, 'age': max(younger, 0)}), person['id']))
    partner_ages(connection, timeline_id, day, real)
    connection.execute("DELETE FROM birth_dates WHERE kind IN ('circle', 'partner')")


def partner_ages(connection, timeline_id: str, day: date, real: date):
    """Partners are younger too; one who would be under 18 then isn't their partner in that year."""
    for partner in many(connection, 'SELECT id, person_id, details FROM love_partners WHERE timeline_id=?',
                        (timeline_id,)):
        details = decode(partner['details']) or {}
        if not isinstance(details.get('age'), int):
            continue
        younger = past_age(connection, 'partner', partner['id'], details['age'], day, real)
        if younger < ages.ADULT:
            forget(connection, timeline_id, partner)
        else:
            connection.execute('UPDATE love_partners SET details=? WHERE id=?',
                               (encode({**details, 'age': younger}), partner['id']))


def homes(connection, timeline_id: str, day: date):
    """Home items from later go and one they left later is theirs again; with no home left from then, the app
    assembles one again (companion/life/home.py `ensure`)."""
    connection.execute('DELETE FROM home_items WHERE timeline_id=? AND since>?', (timeline_id, day.isoformat()))
    connection.execute('UPDATE home_items SET until=NULL WHERE timeline_id=? AND until>?', (timeline_id, day.isoformat()))
    if not any(item['kind'] == 'home' for item in home.items_on(connection, timeline_id, day)):
        connection.execute('DELETE FROM home_items WHERE timeline_id=?', (timeline_id,))
        connection.execute('DELETE FROM home_state WHERE timeline_id=?', (timeline_id,))


def standing(pair: dict | None, day: date) -> dict:
    """How the two of them stand on `day`: strangers, people who know each other, or on a step of their ladder."""
    if not pair or pair['met'] is None or pair['met'] > day:
        return {'met': None, 'steps': []}
    reached = [item for item in pair['steps'] if item['on'] <= day]
    if not reached:  # They know each other, from before anything between them began.
        reached = [{'ladder': 'friendship', 'step': 'friends', 'on': pair['met']}]
    return {'met': pair['met'], 'steps': reached}


# Who they are then ---------------------------------------------------------------------------------------------------

AGE_FIELDS = ('identity', 'background', 'appearance', 'in_photos', 'seen_as', 'sees_self')


def age_words(old: int) -> re.Pattern:
    """Where their own words give the age they are now: "34-year-old", "34 years old", "aged 34", "Mira, 34,"."""
    return re.compile(rf'\b{old}(?=[- ]years?[- ]old\b)|(?<=\baged ){old}\b|(?<=\bage ){old}\b|(?<=, ){old}(?=[,.;])',
                      re.IGNORECASE)


def younger_words(definition: dict, old: int, new: int) -> dict:
    """Their own words with the age they are now changed to the age they were then."""
    pattern = age_words(old)
    return {**definition, **{field: pattern.sub(str(new), definition[field]) for field in AGE_FIELDS
                             if isinstance(definition.get(field), str)}}


def relationship_then(definition: dict, stand: dict) -> dict:
    """How the two of them stand that year, for a friendship or a romance (family and the rest stay as written):
    strangers, people who know each other, or on the step they had reached."""
    if definition.get('relationship') not in steps.LADDERS:
        return definition
    if not stand['steps']:
        return {**definition, 'relationship': 'friendship', 'starting_closeness': 1, 'history_together': STRANGERS}
    top = stand['steps'][-1]
    step = steps.step_of(top['ladder'], top['step'])
    return {**definition, 'relationship': 'romance' if top['ladder'] == 'romance' else 'friendship',
            'starting_closeness': min(int(definition.get('starting_closeness') or 1), step.closeness) or 1,
            'history_together': f"You and the user met in {stand['met'].year}."}
