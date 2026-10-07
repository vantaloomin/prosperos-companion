"""Plans the companion makes in chat ("my bout is Saturday the 24th at 6") happen in their life.

Rule-based capture, no model: after each completed companion message, first-person statements
about something they will do on a day that resolves to one date (a weekday, "the 24th", "November
14", "tomorrow", or a holiday in their city's calendar) are pinned with the time when one is given.
Questions, maybes, conditionals, negations, past tense and plans about the user or "we" are skipped.

A plan belongs to its message the way a self fact does (companion/self_facts.py): it applies on every
timeline holding that message or a copy, and goes when the reply is replaced or deleted. The agenda
(companion/life/agenda.py) gives the plan the free slot that overlaps its time, or with no time the
free slot around the evening, and with no time the day's other free slots stay quiet. Work and study
are never overridden.
"""
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from companion.clock import parse, zone
from companion.database import identifier, many
from companion.memory import dates
from companion.memory.extraction import HYPOTHETICAL, QUESTION_START, QUOTED, SENTENCE
from companion.world import catalog, custom, generators

ACTIONS = re.compile(r'\*[^*\n]+\*')
MAYBE = re.compile(r"\b(?:if|unless|maybe|might|probably|perhaps|possibly|wish|hopefully)\b", re.IGNORECASE)
NOT_MINE = re.compile(r"\b(?:you|your|you're|u|ur|we|we're|we'll|us|our|let's)\b", re.IGNORECASE)
PAST = re.compile(r"\b(?:was|were|went|had|did|yesterday|last|ago|used to)\b", re.IGNORECASE)
NEGATED = re.compile(r"n't\b|\b(?:not|never|no|cannot|cancel\w*|skip\w*)\b", re.IGNORECASE)
HEDGED = re.compile(r"\b(?:should|could|would|wanna|want to|wants to|hope|hoping|thinking|considering|trying to|"
                    r"plan to|planning|supposed to|might|maybe)\b", re.IGNORECASE)
CLAUSES = re.compile(r",|\s+[-–—]\s+|\s+(?:and|but|so|then)\s+(?=(?:you|we|i|i'm|i'll|my|it|it's|that)\b)",
                     re.IGNORECASE)
LEAD = r"^(?:(?:oh|so|and|but|well|also|anyway|ok|okay|yeah|plus|then|honestly|lol|haha|btw)\b[, ]*)*"
MONTH_AFTER = r'(?!(?:\s+of)?\s+(?:' + '|'.join(dates.MONTHS) + r')\b)'
ORDINAL = re.compile(rf"\b(?:on |this |next )?(?:{dates.DAY},? )?the (\d{{1,2}})(?:st|nd|rd|th)\b{MONTH_AFTER}",
                     re.IGNORECASE)
CLOCK = re.compile(r"\b(?:(?:at|around|from)\s+(\d{1,2})(?::(\d{2}))?|(\d{1,2})(?::(\d{2}))?(?=\s*[ap]\.?m))"
                   r"\s*([ap])?\.?m?\.?(?![\w:])|\b(?:at\s+)?(noon|midnight)\b", re.IGNORECASE)
PARTS = {'this morning': '10:00', 'this afternoon': '15:00'}
PART = re.compile(r'\b(?:in the )?(morning|afternoon)\b', re.IGNORECASE)
# The word after "going to" that makes it a trip ("going to my grandma's"), not an intention ("going to bake").
TRIP = {'my', 'the', 'a', 'an', 'this', 'that', 'church', 'brunch', 'dinner', 'lunch', 'work'}
NOT_DOING = {'thinking', 'hoping', 'trying', 'wondering', 'considering', 'feeling', 'working', 'sleeping',
             'kidding', 'dying', 'being', 'getting', 'planning', 'starting', 'off', 'on', 'here', 'there', 'free',
             'busy', 'around', 'done', 'sure', 'so', 'just', 'really', 'still', 'also', 'not', 'gonna', 'going'}
NOT_PLANS = re.compile(r'\b(?:work|shift|shifts|overtime|on call|nothing|sleep|asleep|class|classes|it|that|this)$',
                       re.IGNORECASE)
TRAILING = re.compile(r"[\s!.,]+$|\s+(?:on|at|for|this|next|over|the|from|around|by|with|too|lol|haha|again|"
                      r"first whistle|starts?|it's|is)$", re.IGNORECASE)
FORMS = (
    ('doing', re.compile(rf"{LEAD}(?:i'm|i am|im)\s+(?:going to|gonna)\s+(?!be\b)(\w+)(.*)$", re.IGNORECASE)),
    ('doing', re.compile(rf"{LEAD}(?:i'll be|i will be|i'm gonna be|i'm going to be|i'm|i am|im)\s+(\w+ing)\b(.*)$",
                         re.IGNORECASE)),
    ('doing', re.compile(rf"{LEAD}(?:i'll|i will|i'm gonna|i'm going to)\s+(\w+)(.*)$", re.IGNORECASE)),
    ('thing', re.compile(rf"{LEAD}(?:i've got|i have|i got)\s+((?:a|an|my)\s+.+)$", re.IGNORECASE)),
    ('thing', re.compile(rf"{LEAD}(my\s+.+?)\s+(?:is|'s|are)\b(.*)$", re.IGNORECASE)),
    ('scene', re.compile(r"^(?:is|'s|will be)\s+(?:just\s+)?(?:going to be|gonna be|be)\s+(.+)$", re.IGNORECASE)),
)


@dataclass(frozen=True)
class Plan:
    local_date: str
    at: str | None
    activity: str
    form: str
    statement: str


def gerund(verb: str) -> str:
    verb = verb.lower()
    if verb.endswith('ing'):
        return verb
    if verb.endswith('e') and not verb.endswith(('ee', 'ye', 'oe')) and len(verb) > 2:
        return verb[:-1] + 'ing'
    if len(verb) <= 4 and re.fullmatch(r'[^aeiou]*[aeiou][bdgklmnprt]', verb):
        return verb + verb[-1] + 'ing'
    return verb + 'ing'


def holiday_dates(connection, definition: dict, today: date) -> dict[str, date]:
    """Holiday names and ids from the companion's city calendar (the US one when the city is unknown), each with
    its next date from today."""
    extra = custom.all_cities(connection)
    data = None
    for text in (definition.get('home_city'), definition.get('location')):
        if text and (found := catalog.resolve(text, extra)):
            data = catalog.city(found['city'], extra)
            break
    items = generators.city_holidays(data) if data else catalog.holiday_calendars().get('us', {}).get('holidays', [])
    result = {}
    for item in items:
        day = next((found for found in (generators.holiday_date(item, today.year),
                                        generators.holiday_date(item, today.year + 1)) if found and found >= today),
                   None)
        if day:
            for name in (item['id'].replace('-', ' '), plain(item['name'])):
                result.setdefault(name, day)
    return result


def plain(text: str) -> str:
    return ' '.join(re.sub(r"[^a-z0-9 ]+", '', text.lower().replace('’', "'").replace("'", '')).split())


def when(clause: str, today: date, holidays: dict[str, date]) -> tuple[date, str, str | None] | None:
    """(date, the words that said it, a time those words imply) for the one day a clause names."""
    for name in sorted(holidays, key=len, reverse=True):
        words = r'\s+'.join("'?".join(map(re.escape, word)) + "'?" for word in name.split())
        if match := re.search(rf"\b(?:on |for |this |over )?{words}\b(?: day)?", clause, re.IGNORECASE):
            return holidays[name], match.group(0), None
    if match := ORDINAL.search(clause):
        day = nth_day(today, int(match.group(2)), match.group(1))
        return (day, match.group(0), None) if day else None
    span = dates.resolve(clause, datetime.combine(today, time(12), UTC), 'UTC')
    if span and span.certain and span.end - span.start == timedelta(days=1):
        words = re.search(rf"\b(?:on |this |for )?{re.escape(span.phrase)}\b", clause, re.IGNORECASE)
        return span.start, words.group(0) if words else span.phrase, PARTS.get(span.phrase)
    return None


def nth_day(today: date, number: int, weekday: str | None) -> date | None:
    """`the 24th` is the next 24th; with a weekday the two must agree."""
    for months in (0, 1, 2):
        month = dates.add_months(today.replace(day=1), months)
        try:
            day = month.replace(day=number)
        except ValueError:
            continue
        if day >= today and (not weekday or dates.WEEKDAYS[day.weekday()] == weekday.lower()):
            return day
    return None


def clock(sentence: str) -> tuple[str | None, str]:
    """('HH:MM' or None, the words that said it). A bare hour without am/pm is an afternoon or evening one."""
    match = CLOCK.search(sentence)
    if not match:
        return None, ''
    if match.group(6):
        return ('12:00' if match.group(6).lower() == 'noon' else '00:00'), match.group(0)
    hour, minutes = int(match.group(1) or match.group(3)), int(match.group(2) or match.group(4) or 0)
    if hour > 23 or minutes > 59:
        return None, ''
    marker = (match.group(5) or '').lower()
    if marker == 'p' and hour < 12 or not marker and 1 <= hour <= 11 and not re.search(
            r'\b(?:morning|breakfast|brunch)\b', sentence, re.IGNORECASE):
        hour += 12
    elif marker == 'a' and hour == 12:
        hour = 0
    return f'{hour:02d}:{minutes:02d}', match.group(0)


def activity(rest: str) -> tuple[str, str] | None:
    """(form, activity in the companion's own words) for what is left of a clause once the day and time are out."""
    rest = ' '.join(rest.split())
    for index, (form, pattern) in enumerate(FORMS):
        match = pattern.match(rest)
        if not match:
            continue
        text = match.group(1)
        if form == 'doing':
            verb, tail = match.group(1).lower(), match.group(2)
            if index == 0 and verb in TRIP:
                text = f'going to {match.group(1)}{tail}'
            elif verb == 'going' and re.match(r'\s+\w+ing\b', tail):
                text = tail  # "going hiking"
            elif verb in NOT_DOING:
                continue
            else:
                text = tail if verb == 'be' else gerund(verb) + tail
        text = text.strip()
        while TRAILING.search(text):
            text = TRAILING.sub('', text)
        if form == 'scene' and not re.search(r'\b(?:me|my|i|myself)\b', text, re.IGNORECASE):
            continue  # "Saturday is going to be crazy" is not a plan.
        if 3 <= len(text) <= 80 and not NOT_PLANS.search(text):
            return form, text
    return None


def extract(text: str, today: date, holidays: dict[str, date] | None = None) -> list[Plan]:
    """The companion's own dated plans in one message, at most one per sentence."""
    holidays = holidays or {}
    text = QUOTED.sub(' ', ACTIONS.sub(' ', text)).replace('’', "'")
    found = []
    for sentence in (part.strip() for part in SENTENCE.findall(text)):
        if not sentence or sentence.endswith('?') or QUESTION_START.match(sentence) or HYPOTHETICAL.search(sentence) \
                or MAYBE.search(sentence):
            continue
        at, said = clock(sentence)
        for clause in CLAUSES.split(sentence):
            day = when(clause, today, holidays)
            if not day or day[0] < today or day[0] > today + timedelta(days=366):
                continue
            if NOT_MINE.search(clause) or PAST.search(clause) or NEGATED.search(clause) or HEDGED.search(clause):
                break
            rest = clause.replace(day[1], ' ')
            rest = rest.replace(said, ' ') if said else rest
            part = PART.search(rest)
            if part:
                rest = rest.replace(part.group(0), ' ')
                at = at or PARTS[f'this {part.group(1).lower()}']
            picked = activity(rest.strip(' ,.!'))
            if picked:
                found.append(Plan(day[0].isoformat(), at or day[2], picked[1], picked[0], sentence[:300]))
            break
    return found


def note(connection, message: dict, companion: dict, timestamp: str) -> list[str]:
    """Pin the plans in one completed companion message. Idempotent per message and date; the agenda
    picks them up the next time it extends (agenda.repin)."""
    if message['role'] != 'companion' or message['status'] != 'complete':
        return []
    version = companion['version']
    stated = parse(message['created_at']).astimezone(zone(version['timezone'])).date()
    added = []
    for plan in extract(message['text'], stated, holiday_dates(connection, version['definition'], stated)):
        row_id = identifier()
        if connection.execute(
                'INSERT OR IGNORE INTO companion_plans (id, companion_id, message_id, local_date, at_time, activity, '
                'form, statement, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (row_id, companion['id'], message['id'], plan.local_date, plan.at, plan.activity, plan.form,
                 plan.statement, timestamp)).rowcount:
            added.append(row_id)
    return added


def in_force(connection, timeline_id, since: str = '') -> list[dict]:
    """Plans whose message, or a copy of it, is shown on this timeline, from `since` (a local date) on."""
    from companion.self_facts import shown
    rows = many(connection, 'SELECT companion_plans.*, messages.reply_to AS reply_to, messages.id AS shown_id FROM '
                'companion_plans JOIN messages ON (messages.id=companion_plans.message_id OR '
                'messages.origin_id=companion_plans.message_id) WHERE messages.timeline_id=? AND messages.active=1 '
                "AND messages.status='complete' AND messages.redacted_at IS NULL AND companion_plans.local_date>=? "
                'ORDER BY companion_plans.local_date, companion_plans.created_at', (timeline_id, since))
    return shown(connection, timeline_id, rows)


def by_date(plans: list[dict]) -> dict[str, list[dict]]:
    result = {}
    for plan in plans:
        result.setdefault(plan['local_date'], []).append(plan)
    return result


def assign(plans: list[dict], blocks: list[dict]) -> dict[str, dict | None]:
    """Which of one day's blocks each plan takes, by block key. Timed plans take the free block that holds
    their time; one without a time takes the free block around 7 pm (else the day's last free one), and the
    day's other free blocks map to None (quiet). A plan with no free block for it is kept but placed nowhere."""
    free = [block for block in blocks if block['kind'] not in {'work', 'study', 'sleep'}]
    result = {}
    for plan in sorted(plans, key=lambda item: item['at_time'] is None):
        if plan['at_time']:
            target = next((block for block in free if block['key'] not in result
                           and holds(block, plan['at_time'])), None)
        else:
            open_blocks = [block for block in free if block['key'] not in result]
            target = next((block for block in open_blocks if holds(block, '19:00')), None) or (
                open_blocks[-1] if open_blocks else None)
        if target:
            result[target['key']] = plan
    if any(not plan['at_time'] for plan in result.values()):
        result.update({block['key']: None for block in free if block['key'] not in result})
    return result


def holds(block: dict, at: str) -> bool:
    start, end = block['start'], block['end']
    return start <= at < end if start < end else at >= start or at < end


def part_of_day(block: dict) -> str:
    hour = int(block['start'][:2])
    return 'morning' if 5 <= hour < 12 else 'afternoon' if 12 <= hour < 17 else 'evening' if 17 <= hour < 23 \
        else 'night'


def third_person(text: str, name: str) -> str:
    text = re.sub(r"\bmy place\b|\bmy apartment\b|\bmy house\b|\bmy flat\b", 'home', text, flags=re.IGNORECASE)
    text = re.sub(r'\bmy\b', f"{name}'s", text, flags=re.IGNORECASE)
    text = re.sub(r'\b(?:me|myself|i)\b', name, text, flags=re.IGNORECASE)
    return text


def entry(plan: dict, block: dict, definition: dict) -> dict:
    """The agenda entry for a slot a plan takes: what they said they would do, happening."""
    name, part = definition['name'], part_of_day(block)
    doing = third_person(plan['activity'], name)
    if plan['form'] == 'doing':
        summary = f'{name} spent the {part} {doing}, as planned.'
    elif plan['form'] == 'thing':
        summary = f'The {part} went to {doing}, as planned.'
    else:
        summary = f'As planned: {doing}.'
    return {'summary': summary[0].upper() + summary[1:], 'post': 'As planned.', 'mood': 'content',
            'activity': 'own-plan', 'place': None, 'with': None,
            'own_plan': {'id': plan['id'], 'message_id': plan['message_id'], 'statement': plan['statement'],
                         'at': plan['at_time']}, 'composer_version': 'own-plan-1'}


def context_lines(connection, timeline_id, today: str) -> list[tuple[str, str]]:
    result = []
    for plan in in_force(connection, timeline_id, today):
        day = date.fromisoformat(plan['local_date']).strftime('%A %B %d').replace(' 0', ' ')
        at = f" at {plan['at_time']}" if plan['at_time'] else ''
        doing = re.sub(r'\bmy\b', 'your', re.sub(r'\b(?:me|myself)\b', 'you', plan['activity'], flags=re.I), flags=re.I)
        result.append((plan['id'], f'- {day}{at}: {doing}'))
    return result
