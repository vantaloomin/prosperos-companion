"""Birthdays and anniversaries (realism: real people remember the date).

Three kinds of day, all from saved state and the calendar, never from a model:

- the companion's own birthday: the definition's `birthday` ("MM-DD") or, when it is empty, a date
  seeded by the companion's id. On the day a free evening goes to celebrating, with a friend from
  the circle when one is free (companion/life/composer.py). A milestone (30, 40, 50 ...: companion/life/ages.py)
  is a bigger one: the line names it, Today says it and the evening is a party.
- the user's birthday: the Life setting `user_birthday`, filled in the first time the user says it
  in their own words ("my birthday is March 3rd", "it's my birthday today") and editable or
  clearable in Settings. It is never guessed.
- a circle member's birthday (companion/life/circle.py, seeded by their id): their mom, sister or friends.
  It is the companion's news, not the user's, so it carries no hint to wish anyone and opens no conversation;
  on the day the companion may celebrate with them (companion/life/composer.py).
- a family tradition (companion/life/traditions.py): a holiday their family keeps, with how they keep it.
- a step in the relationship (companion/life/steps.py): a year since they became exclusive, two since moving in.
- the day someone in their circle died, a year or more on (companion/life/loss.py): on the day only, with no first text.
- how long the two have been talking: a month, three months, six months, a hundred days, then each
  year, counted from the timeline's first message. For a romance it is their anniversary.

The chat context gets the day itself and what is coming within a week; on the day, the companion
can open the conversation with it (companion/life/openers.py).
"""
import re
from calendar import monthrange
from datetime import date, timedelta

from companion.clock import parse, zone
from companion.database import decode, optional, settings
from companion.life import ages, circle, loss, steps, traditions
from companion.world import generators

SOON = 7
# Off in tests, where a seeded birthday would land on a simulated day by chance.
SEEDED = True
MONTH_MILESTONES = {1: 'a month', 3: 'three months', 6: 'six months'}
MONTH_NAMES = ('january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october',
               'november', 'december')
MONTH = r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|' \
        r'oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
DAY = r'(\d{1,2})(?:st|nd|rd|th)?'
MINE = r"\bmy (?:birthday|bday|b-day)(?: is|'s| falls on)?(?: on)?(?: the)? "
SAID = (re.compile(MINE + MONTH + r'\.? ' + DAY + r'\b', re.IGNORECASE),
        re.compile(MINE + DAY + r'(?: of)? ' + MONTH + r'\b', re.IGNORECASE))
TODAY = re.compile(r"\b(?:(?:today|it)(?: is|'s) my (?:birthday|bday)|my (?:birthday|bday)(?: is|'s) today)\b",
                   re.IGNORECASE)
TOMORROW = re.compile(r"\b(?:tomorrow(?: is|'s) my (?:birthday|bday)|my (?:birthday|bday)(?: is|'s) tomorrow)\b",
                      re.IGNORECASE)
NOT_MINE = re.compile(r"\b(?:if|when|what if|imagine|pretend|suppose|wish)\b", re.IGNORECASE)
TEMPLATES = {'user_birthday': 'Happy birthday!! I hope today is a really good one.',
             'own_birthday': "Guess who's a year older today.",
             'anniversary': "Okay, random, but it's been {span} since we started talking. Just saying.",
             'step_anniversary': "Can you believe it's been {span} since we {did}?"}
MILESTONE_TEMPLATE = "Guess who's {age} today."
KEPT_TEMPLATE = "Guess whose birthday it is today."  # Keeps their age (companion/life/ages.py): no year older.


def month_day(month: str, day: str) -> str | None:
    number = next(index for index, name in enumerate(MONTH_NAMES, 1) if name.startswith(month.lower()[:3]))
    value = int(day)
    return f'{number:02d}-{value:02d}' if 1 <= value <= monthrange(2001, number)[1] else None


def said_birthday(text: str, today: date) -> str | None:
    """The user's birthday ("MM-DD") when a message says it plainly, else None."""
    if '?' in text or NOT_MINE.search(text):
        return None
    for pattern in SAID:
        if match := pattern.search(text):
            groups = match.groups()
            month, day = (groups[0], groups[1]) if pattern is SAID[0] else (groups[1], groups[0])
            return month_day(month, day)
    if TODAY.search(text):
        return today.strftime('%m-%d')
    if TOMORROW.search(text):
        return (today + timedelta(days=1)).strftime('%m-%d')
    return None


def note(connection, message: dict, timestamp: str):
    """Fill in the user's birthday the first time they say it; a value they set is never replaced."""
    row = optional(connection, 'SELECT user_birthday FROM life_settings WHERE id=1')
    if not row or row['user_birthday']:
        return
    today = parse(timestamp).astimezone(zone(settings(connection)['user_timezone'])).date()
    if found := said_birthday(message['text'], today):
        connection.execute('UPDATE life_settings SET user_birthday=?, updated_at=? WHERE id=1', (found, timestamp))


def own_birthday(companion: dict) -> str | None:
    """The companion's birthday: set in their definition, else seeded by their id (never 29 February)."""
    chosen = companion['version']['definition'].get('birthday')
    if chosen or not SEEDED:
        return chosen or None
    return (date(2001, 1, 1) + timedelta(days=int(generators.unit(companion['id'], 'birthday') * 365))).strftime('%m-%d')


def on(day: date, month_day_text: str) -> bool:
    """Whether a "MM-DD" falls on this day; 29 February falls on the 28th in other years."""
    month, value = map(int, month_day_text.split('-'))
    if month == 2 and value == 29 and monthrange(day.year, 2)[1] == 28:
        value = 28
    return (day.month, day.day) == (month, value)


def days_until(day: date, month_day_text: str) -> int:
    for ahead in range(366):
        if on(day + timedelta(days=ahead), month_day_text):
            return ahead
    return 366


def milestone(first: date, day: date) -> str | None:
    """"three months", "100 days", "a year"…: when `day` marks one since `first`."""
    if (day - first).days == 100:
        return '100 days'
    months = (day.year - first.year) * 12 + day.month - first.month
    last = monthrange(day.year, day.month)[1]
    if months <= 0 or day.day != min(first.day, last):
        return None
    if months in MONTH_MILESTONES:
        return MONTH_MILESTONES[months]
    if months % 12 == 0:
        return 'a year' if months == 12 else f'{months // 12} years'
    return None


def first_talk(connection, timeline_id, tz) -> date | None:
    """The day they first talked here. An old chat brought in (companion/imports/chats.py) is history before that,
    so its dates never make an anniversary, a scrapbook year or a forgotten-occasion sting."""
    row = optional(connection, "SELECT MIN(created_at) AS first FROM messages WHERE timeline_id=? AND status='complete' "
                   'AND import_id IS NULL', (timeline_id,))
    return parse(row['first']).astimezone(tz).date() if row and row['first'] else None


def occasions(connection, companion: dict, now) -> list[dict]:
    """Today's occasions and those within a week: {key, kind, days, text, template}."""
    user_tz = zone(settings(connection)['user_timezone'])
    user_today = now.astimezone(user_tz).date()
    own_today = now.astimezone(zone(companion['version']['timezone'])).date()
    life = optional(connection, 'SELECT user_birthday FROM life_settings WHERE id=1')
    found = []
    if life and life['user_birthday']:
        ahead = days_until(user_today, life['user_birthday'])
        if ahead <= SOON:
            found.append(occasion('user_birthday', user_today + timedelta(days=ahead), ahead,
                                  "the user's birthday", 'Wish them a happy birthday if you have not yet.'))
    mine = own_birthday(companion)
    ahead = days_until(own_today, mine) if mine else SOON + 1
    if ahead <= SOON:
        found.append(own_occasion(connection, companion, own_today + timedelta(days=ahead), ahead))
    for person in circle.people(connection, companion['active_timeline_id']) if SEEDED else ():
        ahead = days_until(own_today, circle.birthday(person['id']))
        if ahead <= SOON:
            day = own_today + timedelta(days=ahead)
            turns = turning(ages.person_age(connection, 'circle', person['id'], day),
                            ages.person_lifespan(connection, decode(person['details']) or {},
                                                 companion['version']['definition']))
            found.append(occasion('circle_birthday', day, ahead, f"your {person['role']} {person['name']}'s "
                                  f"{ages.ordinal(turns) + ' ' if turns else ''}birthday", '', person=person,
                                  turns=turns))
    for item in traditions.upcoming(connection, companion, own_today, SOON):
        found.append(occasion('tradition', item['date'], item['days'], item['name'], '', tradition=item))
    first = first_talk(connection, companion['active_timeline_id'], user_tz)
    for item in steps.anniversaries(connection, companion, own_today, SOON):
        years = 'a year' if item['years'] == 1 else f"{item['years']} years"
        found.append(occasion('step_anniversary', item['date'], item['days'],
                              f"{years} since you and the user {item['did']} ({steps.long_date(item['on'])})",
                              '', span=years, did=item['did'], step=item['step']))
    for item in loss.anniversaries(connection, companion, own_today):
        found.append(occasion('death_anniversary', own_today, 0, item['what'], item['hint'], span=item['span'],
                              person={'id': item['id'], 'name': item['name'], 'role': item['role']}))
    span = milestone(first, user_today) if first else None
    if span:
        from companion.life import breakups  # It reads this module's neighbours; imported when used.
        # Exes (companion/life/breakups.py) still know the day they met, but it is no longer "your anniversary".
        romance = companion['version']['definition'].get('relationship') == 'romance' and not breakups.ended(
            connection, companion)
        what = f"{span} since you and the user first talked ({steps.long_date(first.isoformat())})"
        found.append(occasion('anniversary', user_today, 0, f"your anniversary: {what}" if romance else what, '',
                              span=span))
    return found


def own_occasion(connection, companion: dict, day: date, ahead: int) -> dict:
    """Their own birthday; a milestone says which, and someone who keeps their age is not a year older."""
    definition = companion['version']['definition']
    turns = turning(ages.turns_on(connection, companion['id'], definition, day),
                    ages.companion_lifespan(connection, definition))
    found = occasion('own_birthday', day, ahead, f'your {ages.ordinal(turns)} birthday, a big one' if turns
                     else 'your birthday', '', turns=turns)
    if found['template'] and definition.get('keeps_age'):
        found['template'] = KEPT_TEMPLATE
    return found


def turning(age: int | None, lifespan: int | None = 80) -> int | None:
    """The age a birthday turns them, when it is a milestone (30, 40, 50 ..., an elf's 100, 150 ...:
    companion/life/ages.py)."""
    return age if ages.milestone(age, lifespan) else None


def occasion(kind, day: date, ahead: int, what: str, hint: str, span: str = '', person: dict | None = None,
             tradition: dict | None = None, did: str = '', step: str = '', turns: int | None = None) -> dict:
    when = 'Today' if ahead == 0 else 'Tomorrow' if ahead == 1 else f"In {ahead} days ({day:%A} {day.day} {day:%B})"
    text = f"- {when} is {what}." if kind not in ('anniversary', 'death_anniversary') else f'- Today it has been {what}.'
    if kind == 'step_anniversary':
        text = f"- {when} it will be {what}." if ahead else f'- Today it has been {what}.'
    if tradition:
        text += f" Your family's tradition: {tradition['text']}"
    whose = f"{person['id']}:" if person else f"{tradition['holiday']}:" if tradition else f'{step}:' if step else ''
    found = {'key': f'occasion:{kind}:{whose}{day.isoformat()}', 'kind': kind, 'date': day.isoformat(), 'days': ahead,
             'span': span, 'text': f'{text} {hint}'.strip() if ahead == 0 else text,
             'template': TEMPLATES[kind].format(span=span, did=did) if ahead == 0 and kind in TEMPLATES else None}
    if person:
        found |= {'person': person['name'], 'relation': person['role']}
    if tradition:
        found |= {'holiday': tradition['name'], 'tradition': tradition['shown'],
                  'teaser': tradition['short']}
    if did:
        found |= {'did': did, 'step': step}  # Today says which step it is (src/features/today/storyText.ts).
    if turns:  # A milestone birthday: Today and the first text say which.
        found['turns'] = turns
        if found['template'] and kind == 'own_birthday':
            found['template'] = MILESTONE_TEMPLATE.format(age=turns)
    return found
