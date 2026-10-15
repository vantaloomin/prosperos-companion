"""Shifts and gigs (Hit List #74): a weekly rota for service jobs, freelance gigs with busy and dry spells.

Every career is staff, rota or freelance (its `employment` in the world data; a career without one, such as a user
city's own, is read from its words). Staff keep the same days every week, as written. Rota jobs (a bartender, a nurse,
a taxi driver) get each week's shifts rolled from their job's pattern: as many as the pattern has, one more in a
slammed week and one fewer in a slow one (companion/life/work.py), with evening and night work leaning to Fridays and
Saturdays. Freelancers (a photographer, a musician, a tour guide) have no fixed days: each week brings a few gigs, in
busy, steady and dry spells of a few weeks. The user can pin it on the character form (Work and money > Hours).

The week's days reach everything that reads their routine through the companion's definition: characters.py adds this
week and the weeks around it as `rota`, and routine.py's blocks follow it, so the agenda, outings, Life admin's clashes,
trips and the rest see the same shifts. A shift holds its time against plans with the user like work always has; it is
never cancelled for them. Weeks are written down once they are planned (table work_weeks), so a past week stays as it
was. Pay follows the shifts worked and gigs landed, with tips making a tipped job's pay swing a little
(money.household, through work.pay). It follows the Work life slider: Off keeps the days as written, Light swings
less, Dramatic more. Only the companion; circle and townsfolk keep their fixed days. No model is involved.
"""
import re
from datetime import date, datetime, timedelta

from companion.clock import stamp, zone
from companion.database import decode, encode, many, optional
from companion.world import generators

# Off in tests unless a test turns it on (tests/conftest.py), so other tests' days stay as written.
ACTIVE = True
KINDS = ('staff', 'rota', 'freelance')
# Weeks around this one the definition carries, so a look back or a plan a few weeks out sees the same days.
WEEKS_BACK, WEEKS_AHEAD = 9, 3
# Weeks written down ahead of today (the agenda reaches a week ahead; plans with the user up to two).
PLAN_WEEKS = 3
# Rota shifts in a week: the pattern's count, kept between these.
FEWEST, MOST = 2, 6
# The most days in a row a rota puts someone on, counting from last week's shifts: six of ordinary shifts, four of
# long ones (ten hours or more, a nurse's twelve-hour nights).
MOST_IN_A_ROW, LONG_IN_A_ROW, LONG_HOURS = 6, 4, 10
# The chance an ordinary week has one shift fewer or one more (picked up or given away), by the Work life slider.
SWAP = {1: 0.12, 2: 0.25, 3: 0.35}
# How much tips make a week's pay swing either way, for tipped work, by the slider.
TIPS = {1: 0.06, 2: 0.12, 3: 0.18}
# Freelance spells last SPELL_WEEKS; (busy, steady) chances by the slider, the rest dry.
SPELL_WEEKS = 3
SPELLS = {1: (0.2, 0.68), 2: (0.27, 0.48), 3: (0.32, 0.34)}
# Gigs in a week by the spell (fewest, most), and what an ordinary week has, for pay.
GIGS = {'busy': (3, 5), 'steady': (1, 3), 'dry': (0, 1)}
USUAL_GIGS = 2.3
# One gig pays more or less than another (low, high).
GIG_RATE = (0.8, 1.25)
# Blocks the week moves with the shifts: work itself, free time after work on those days, the rest days off.
AFTER_WORK, DAY_OFF = 'after-work', 'day-off'
DAY_NAMES = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
SHORT_DAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
COUNTS = ('No', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven')

# Words that tell a career's employment when the data does not say (a user city's careers, a job the user wrote).
FREELANCE_WORDS = ('freelance', 'freelancer', 'freelancing', 'freelances', 'self employed', 'gig', 'gigs', 'commissions',
                   'contract work', 'session musician', 'for hire', 'odd jobs', 'piecework', 'busker', 'busking',
                   'photographer', 'content creator', 'influencer', 'streamer', 'youtuber', 'tour guide', 'dj',
                   'rideshare', 'uber', 'lyft', 'doordash', 'dog walker', 'translator')
ROTA_WORDS = ('bartender', 'barmaid', 'barman', 'barista', 'server', 'waiter', 'waitress', 'waitstaff', 'line cook',
              'cook', 'dishwasher', 'hostess', 'retail', 'cashier', 'shop assistant', 'store clerk',
              'sales associate', 'front desk', 'hotel clerk', 'concierge', 'nurse', 'orderly', 'attendant',
              'paramedic', 'taxi', 'cab', 'cabman', 'dealer', 'porter', 'guard', 'constable', 'patrolman',
              'deputy', 'dispatcher', 'rota', 'roster', 'waits tables', 'tavern', 'pub', 'diner',
              'restaurant', 'cafe', 'café', 'call center', 'warehouse', 'lifeguard', 'shift', 'shifts', 'on call',
              'chef', 'firefighter', 'emt', 'caregiver', 'care worker', 'aide', 'security')
# The sentences of what they wrote that say what they do for work, so a hobby ("loves pub quizzes") never reads as
# a job.
WORK_CUE = re.compile(r"\b(?:work|works|worked|working|job|jobs|career|employed|shifts?|gigs?|freelanc\w*|"
                      r"self-employed|on[- ]call|drives|(?:is|was|as) an?)\b", re.IGNORECASE)
SENTENCE = re.compile(r'(?<=[.!?])\s+')
ROTA_SECTORS = ('hospitality', 'food', 'victualling', 'retail', 'transit', 'transport', 'healthcare', 'care',
                'healing', 'law-enforcement', 'public-safety', 'security', 'gates', 'services')
FREELANCE_SECTORS = ('creative', 'arts', 'music', 'entertainment', 'media')
# Tipped work: a week's tips swing its pay (bar and table service, cabs, hotel desks, dancers).
TIPPED = re.compile(r'bar|server|waiter|waitress|tavern|taxi|cab|dealer|hatcheck|cigarette|porter|hotel|front-desk|'
                    r'barista|soda|dancer|bootblack|elevator')


def plain(text: str) -> str:
    return ' '.join(re.findall(r"[a-z]+(?:[-'][a-z]+)*", (text or '').casefold()))


def has_words(text: str, words) -> bool:
    found = f' {plain(text)} '
    return any(f' {word} ' in found for word in words)


def employment_of(career: dict | None, text: str = '') -> str:
    """Staff, rota or freelance: the career's own tag, else read from its words (and the companion's own, for a
    job the user wrote): freelance words first, then shift work, then the kind of schedule it keeps."""
    if career and career.get('employment') in KINDS:
        return career['employment']
    words = ' '.join([text, *((career.get(key) or '') for key in ('id', 'name', 'summary') if career)]
                     if career else [text])
    if has_words(words.replace('-', ' '), FREELANCE_WORDS):
        return 'freelance'
    if has_words(words.replace('-', ' '), ROTA_WORDS):
        return 'rota'
    if career:
        sector = (career.get('sector') or '').lower()
        if career.get('schedule') == 'flexible' and sector in FREELANCE_SECTORS:
            return 'freelance'
        if career.get('schedule') in ('evening', 'rotating', 'shift-day', 'shift-night') and sector in ROTA_SECTORS:
            return 'rota'
    return 'staff'


def chosen_kind(definition: dict) -> str:
    """What the user set on the character form (Work and money > Hours), '' for the app's pick."""
    found = (definition.get('money') or {}).get('employment') or ''
    return found if found in KINDS else ''


def employment(definition: dict, career: dict | None) -> str:
    """The companion's employment: what the user set, else their career's, else read from what they wrote about
    their work (identity and routine, the way a written job is read elsewhere)."""
    if found := chosen_kind(definition):
        return found
    own = ' '.join(sentence for key in ('identity', 'routine') for sentence in SENTENCE.split(definition.get(key) or '')
                   if WORK_CUE.search(sentence))
    if career and career.get('employment') in KINDS:
        # A tagged career wins, unless they wrote that they freelance at it ("a freelance photographer").
        return 'freelance' if has_words(own, ('freelance', 'freelancer', 'self-employed')) else career['employment']
    return employment_of(career, own)


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def work_blocks(definition: dict) -> list[dict]:
    return [item for item in definition.get('schedule') or [] if item.get('kind') == 'work']


def pattern(definition: dict) -> tuple[list[int], str, str]:
    """The written week the shifts are rolled from: the work block's days and hours."""
    block = work_blocks(definition)[0]
    return sorted(block.get('days', range(7))), block['start'], block['end']


def evening_work(start: str, end: str) -> bool:
    return start >= '15:00' or end <= start


def weights(start: str, end: str, performer: bool, gigs: bool = False) -> list[float]:
    """How likely each weekday is to have a shift: evening and night work leans to Fridays and Saturdays, day work
    a little to the weekend (someone has to cover it), gigs for performers to the weekend, other gigs to weekdays."""
    if performer:
        return [0.5, 0.6, 0.8, 1.2, 2.0, 2.4, 1.0]
    if evening_work(start, end):
        return [0.7, 0.8, 0.9, 1.2, 2.2, 2.4, 1.2]
    if gigs:
        # A designer's or a photographer's clients book them in office hours, now and then a weekend.
        return [1.2, 1.2, 1.2, 1.2, 1.1, 0.4, 0.3]
    return [1.0, 1.0, 1.0, 1.0, 1.1, 1.4, 1.2]


def run_after(days: set[int], day: int, before: int) -> int:
    """The run of days in a row `day` would be part of, with `before` days worked in a row up to last Sunday."""
    taken = days | {day}
    start = day
    while start - 1 in taken:
        start -= 1
    end = day
    while end + 1 in taken:
        end += 1
    return end - start + 1 + (before if start == 0 else 0)


def draw_days(seed: str, count: int, weekday_weights: list[float], cap: int = 7, before: int = 0) -> list[int]:
    """`count` distinct weekdays, weighted, seeded, never more than `cap` in a row (with `before` days in a row
    worked up to last Sunday); fewer when no day is left that keeps to it."""
    left, chosen = list(range(7)), []
    for index in range(min(count, 7)):
        allowed = [day for day in left if run_after(set(chosen), day, before) <= cap]
        if not allowed:
            break
        day = generators.pick(seed, f'day:{index}', allowed, [weekday_weights[day] for day in allowed])
        chosen.append(day)
        left.remove(day)
    return sorted(chosen)


def in_a_row(start: str, end: str) -> int:
    """How many days in a row these hours allow."""
    minutes = (int(end[:2]) * 60 + int(end[3:5]) - int(start[:2]) * 60 - int(start[3:5])) % (24 * 60)
    return LONG_IN_A_ROW if minutes >= LONG_HOURS * 60 else MOST_IN_A_ROW


def trailing(days) -> int:
    """Days worked in a row up to the week's Sunday."""
    count = 0
    while 6 - count in days:
        count += 1
    return count


def spell(seed: str, monday: date, chosen: int) -> str:
    """Busy, steady or dry: freelance work comes in spells of a few weeks."""
    index = (monday - date(2000, 1, 3)).days // 7 // SPELL_WEEKS
    busy, steady = SPELLS[chosen]
    roll = generators.unit(seed, 'spell', index)
    return 'busy' if roll < busy else 'steady' if roll < busy + steady else 'dry'


def roll(seed: str, monday: date, kind: str, base: list[int], start: str, end: str, workload: str, chosen: int,
         tipped: bool = False, performer: bool = False, before: int = 0) -> dict:
    """One week: {days, spell, pay}. Seeded by the companion, the week and what shapes it, so the same week rolls
    the same however often it is asked. `before` is how many days in a row they worked up to last Sunday, so a rota
    never runs on past six days in a row (four of long shifts)."""
    week = f'{seed}:{monday.isoformat()}'
    swing = {'slammed': 1, 'slow': -1}.get(workload, 0)
    if kind == 'rota':
        count = len(base) + swing
        if not swing and (roll_swap := generators.unit(week, 'swap')) < SWAP[chosen]:
            count += 1 if roll_swap < SWAP[chosen] / 2 else -1
        count = max(FEWEST, min(MOST, count, len(base) + 2))
        days = draw_days(week, count, weights(start, end, False), in_a_row(start, end), before)
        pay = len(days) / max(len(base), 1)
        if tipped:
            pay *= 1 + (generators.unit(week, 'tips') * 2 - 1) * TIPS[chosen]
        return {'days': days, 'spell': '', 'pay': round(pay, 4)}
    found = spell(seed, monday, chosen)
    low, high = GIGS[found]
    count = max(0, min(6, low + int(generators.unit(week, 'gigs') * (high - low + 1)) + swing))
    days = draw_days(week, count, weights(start, end, performer, gigs=True))
    rate = GIG_RATE[0] + generators.unit(week, 'rate') * (GIG_RATE[1] - GIG_RATE[0])
    return {'days': days, 'spell': found, 'pay': round(count / USUAL_GIGS * rate, 4)}


# --- The companion's weeks ---

def setup(connection, companion: dict) -> dict | None:
    """What their weeks are rolled from, or None when their week stays as written: no shifts while the slider is
    Off, for staff, while between jobs or without a work block."""
    from companion.life import outings, work
    if not ACTIVE or not work.ACTIVE:
        return None
    definition, timeline_id = companion['version']['definition'], companion.get('active_timeline_id')
    if not timeline_id or len(work_blocks(definition)) != 1:
        # Several work blocks are a week the user shaped by hand: it stays as written.
        return None
    chosen = work.level(connection)
    if not chosen:
        return None
    career = work.career_of(definition, outings.city_data(connection, definition))
    kind = employment(definition, career)
    if kind == 'staff':
        return None
    found = work.state(connection, timeline_id)
    if found and found['status'] == 'hunting':
        return None
    base, start, end = pattern(definition)
    career_id = career['id'] if career else ''
    performer = bool(career) and (career.get('sector') or '') in ('music', 'entertainment')
    return {'kind': kind, 'level': chosen, 'base': base, 'start': start, 'end': end, 'state': found,
            'seed': f'shifts:{timeline_id}:{career_id}:{kind}', 'tipped': bool(TIPPED.search(career_id)),
            'performer': performer, 'timeline_id': timeline_id, 'career': career_id}


def stored(connection, timeline_id: str, first: date, last: date) -> dict[str, dict]:
    rows = many(connection, 'SELECT * FROM work_weeks WHERE timeline_id=? AND monday>=? AND monday<=?',
                (timeline_id, first.isoformat(), last.isoformat()))
    return {row['monday']: {**row, 'days': decode(row['days'])} for row in rows}


def rolled(found: dict, monday: date, before: int = 0) -> dict:
    from companion.life import work
    load = work.workload(found['state'], monday, found['level']) if found['state'] else 'normal'
    return {**roll(found['seed'], monday, found['kind'], found['base'], found['start'], found['end'], load,
                   found['level'], found['tipped'], found['performer'], before), 'workload': load}


def as_written(found: dict) -> dict:
    """A week lived before their weeks were first written down (before the upgrade that brought shifts, or before
    the job became shift work): the written pattern, as it was then."""
    return {'days': list(found['base']), 'spell': 'steady' if found['kind'] == 'freelance' else '', 'pay': 1.0,
            'workload': 'normal'}


def first_written(connection, timeline_id: str) -> str | None:
    row = optional(connection, 'SELECT MIN(monday) AS monday FROM work_weeks WHERE timeline_id=?', (timeline_id,))
    return row['monday'] if row else None


def weeks(connection, companion: dict, first: date, last: date, found: dict | None = None) -> dict[str, dict]:
    """{Monday: week} from the week of `first` through the week of `last`: as written down, else as it would roll.
    Weeks before the first one written down stay as they were lived, on the written pattern, so a past week never
    changes (an upgrade from before shifts and gigs rolls only from the week it is first planned)."""
    found = found or setup(connection, companion)
    if not found:
        return {}
    monday = monday_of(first)
    kept = {key: week for key, week in stored(connection, found['timeline_id'], monday - timedelta(weeks=1),
                                              last).items()
            if week['kind'] == found['kind'] and week['career'] == found['career']}
    # Each week starts from how many days in a row the week before ended on.
    start = first_written(connection, found['timeline_id'])

    def week_of(day: date, trailing_days: int = 0) -> dict:
        key = day.isoformat()
        return kept.get(key) or (as_written(found) if start and key < start else rolled(found, day, trailing_days))

    previous = week_of(monday - timedelta(weeks=1))
    result = {}
    while monday <= last:
        result[monday.isoformat()] = previous = week_of(monday, trailing(previous['days']))
        monday += timedelta(weeks=1)
    return result


def reference(connection, timeline_id: str) -> date:
    """The day the weeks on the definition are centred on, read from the database (a companion is read without the
    clock): the last week written down, else how far the agenda reaches, else when the timeline began. The agenda
    writes a week ahead and the weeks are written down before it (work.plan_ahead), so this is a little past today."""
    row = optional(connection, "SELECT MAX(day) AS day FROM (SELECT MAX(monday) AS day FROM work_weeks WHERE "
                   "timeline_id=? UNION ALL SELECT MAX(substr(through, 1, 10)) FROM agenda_cursors WHERE timeline_id=? "
                   "UNION ALL SELECT substr(COALESCE(activated_at, created_at), 1, 10) FROM timelines WHERE id=?)",
                   (timeline_id, timeline_id, timeline_id))
    return date.fromisoformat(row['day']) if row and row['day'] else date(2000, 1, 3)


def copy(connection, parent_id: str, new_id: str, cutoff: str):
    """A fork keeps the weeks already planned up to the fork, so its past shifts are the parent's; from the next week
    on it rolls its own."""
    connection.execute('INSERT INTO work_weeks (timeline_id, monday, kind, career, days, spell, workload, pay, created_at) '
                       'SELECT ?, monday, kind, career, days, spell, workload, pay, created_at FROM work_weeks '
                       'WHERE timeline_id=? AND monday<=?', (new_id, parent_id, cutoff[:10]))


def with_rota(connection, companion: dict) -> dict:
    """The companion with their shifts for the weeks around now on their definition, for routine.py (`rota`; the
    saved version never has it). Unchanged when their week stays as written."""
    found = setup(connection, companion)
    if not found:
        return companion
    middle = reference(connection, found['timeline_id'])
    span = weeks(connection, companion, middle - timedelta(weeks=WEEKS_BACK), middle + timedelta(weeks=WEEKS_AHEAD),
                 found)
    rota = {'kind': found['kind'], 'weeks': {monday: week['days'] for monday, week in span.items()}}
    definition = {**companion['version']['definition'], 'rota': rota}
    return {**companion, 'version': {**companion['version'], 'definition': definition}}


def minutes_of(clock: str) -> int:
    return int(clock[:2]) * 60 + int(clock[3:5])


def plans_in_the_way(connection, found: dict, monday: date) -> list[tuple[int, int]]:
    """Plans already made for this week that a shift must not land on, as (start, end) minutes from the Monday:
    outings with the user and trips (companion/life/trips.py), as Life admin keeps out of their way."""
    from companion.life import outings, trips
    last = (monday + timedelta(days=7)).isoformat()
    spans = []
    for outing in outings.in_force(connection, found['timeline_id'], monday.isoformat()):
        if outing['local_date'] <= last:
            start = (date.fromisoformat(outing['local_date']) - monday).days * 1440 + minutes_of(outing['at_time'] or
                                                                                                  '12:00')
            end = start + max(minutes_of(outing['until_time'] or '00:00') - (start % 1440), 60)
            spans.append((start, end))
    for trip in trips.planned(connection, found['timeline_id'], monday.isoformat()):
        first, final = date.fromisoformat(trip['start_date']), date.fromisoformat(trip['end_date'])
        spans.append(((first - monday).days * 1440, ((final - monday).days + 1) * 1440))
    return spans


def clear_of_plans(days: list[int], start: str, end: str, spans: list[tuple[int, int]]) -> list[int]:
    """The week's shifts moved off days where a plan already stands to free days of the same week, or dropped when
    no day is free: a shift never lands on a dinner with the user that was settled first."""
    length = (minutes_of(end) - minutes_of(start)) % 1440 or 1440
    def clashes(day: int) -> bool:
        begin = day * 1440 + minutes_of(start)
        return any(begin < until and since < begin + length for since, until in spans)
    if not spans or not any(clashes(day) for day in days):
        return days
    kept = [day for day in days if not clashes(day)]
    free = [day for day in range(7) if day not in days and not clashes(day)]
    return sorted(kept + free[:len(days) - len(kept)])


def plan_ahead(connection, companion: dict, today: date, now: datetime) -> int:
    """Write down this week and the next few, the first time each is planned, around plans already made. Returns how
    many were added."""
    found = setup(connection, companion)
    if not found:
        return 0
    span = weeks(connection, companion, today, today + timedelta(weeks=PLAN_WEEKS - 1), found)
    known = stored(connection, found['timeline_id'], monday_of(today), today + timedelta(weeks=PLAN_WEEKS - 1))
    added = 0
    for monday, week in span.items():
        if monday not in known or known[monday]['kind'] != found['kind'] or known[monday]['career'] != found['career']:
            week = {**week, 'days': clear_of_plans(week['days'], found['start'], found['end'],
                                                   plans_in_the_way(connection, found, date.fromisoformat(monday)))}
        added += connection.execute(
            'INSERT INTO work_weeks (timeline_id, monday, kind, career, days, spell, workload, pay, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (timeline_id, monday) DO UPDATE SET kind=excluded.kind, '
            'career=excluded.career, days=excluded.days, spell=excluded.spell, workload=excluded.workload, '
            'pay=excluded.pay, created_at=excluded.created_at '
            'WHERE work_weeks.kind!=excluded.kind OR work_weeks.career!=excluded.career',
            (found['timeline_id'], monday, found['kind'], found['career'], encode(week['days']), week['spell'],
             week.get('workload', 'normal'), week['pay'], stamp(now))).rowcount
    return added


def refresh_agenda(connection, companion: dict, now: datetime) -> bool:
    """Bring the agenda's upcoming days in line with the week as it is now (a new week of shifts, a new career, the
    slider moved, hours pinned on the form): slots of work, the free time after it and days off that the week no
    longer has go, and when a slot is gone or missing the agenda is written again from now. True when it changed."""
    from companion.life import agenda, routine
    timeline_id = companion['active_timeline_id']
    schedule, _default = routine.blocks(companion['version']['definition'])
    moving = {block.key: block for block in schedule if block.kind == 'work' or block.key in (AFTER_WORK, DAY_OFF)}
    cursor = optional(connection, 'SELECT through FROM agenda_cursors WHERE timeline_id=? AND subject=?',
                      (timeline_id, agenda.COMPANION))
    if not moving or not cursor or optional(
            connection, "SELECT id FROM life_agenda WHERE timeline_id=? AND subject=? AND status!='upcoming' AND "
            'ends_at>? LIMIT 1', (timeline_id, agenda.COMPANION, stamp(now))):
        # With the clock behind what already happened, nothing is written again (a clock moved back replays nothing).
        return False
    today, written, changed = now.astimezone(zone(companion['version']['timezone'])).date(), set(), False
    for row in many(connection, "SELECT id, slot_key FROM life_agenda WHERE timeline_id=? AND subject=? AND "
                    "status='upcoming'", (timeline_id, agenda.COMPANION)):
        key, _at, day = row['slot_key'].partition('@')
        written.add(row['slot_key'])
        if key in moving and day and not moving[key].on(date.fromisoformat(day)):
            connection.execute('DELETE FROM life_agenda WHERE id=?', (row['id'],))
            changed = True
    through = date.fromisoformat(cursor['through'][:10])
    day = today + timedelta(days=1)
    while not changed and day < through:
        changed = any(block.on(day) and f'{key}@{day.isoformat()}' not in written for key, block in moving.items())
        day += timedelta(days=1)
    if changed:
        connection.execute('UPDATE agenda_cursors SET through=? WHERE timeline_id=? AND subject=? AND through>?',
                           (stamp(now), timeline_id, agenda.COMPANION, stamp(now)))
    return changed


def pay(connection, timeline_id: str, day: date) -> float:
    """What the last two weeks' shifts or gigs paid against an ordinary week's, 1 without shifts or gigs written
    down: the pay that lands this payday."""
    monday = monday_of(day)
    rows = many(connection, 'SELECT pay FROM work_weeks WHERE timeline_id=? AND monday>=? AND monday<?',
                (timeline_id, (monday - timedelta(weeks=2)).isoformat(), monday.isoformat()))
    return sum(row['pay'] for row in rows) / len(rows) if rows else 1.0


# --- In plain words ---

def days_text(days: list, names=DAY_NAMES) -> str:
    named = [names[day] for day in days] if names else list(days)
    return named[0] if len(named) == 1 else ', '.join(named[:-1]) + ' and ' + named[-1]


def part_of_day(start: str, end: str) -> str:
    if end <= start or start >= '20:00':
        return ' nights'
    return ' evenings' if start >= '15:00' else ''


def week_text(kind: str, days: list[int], start: str, end: str, short: bool = True, old: bool = False) -> str:
    """'Tue, Thu and Sat nights' or 'Two gigs (Tuesday and Friday)' ('Two engagements' in an old era)."""
    if kind == 'rota':
        return days_text(days, SHORT_DAYS if short else DAY_NAMES) + part_of_day(start, end) if days else 'no shifts'
    count, word = len(days), 'engagement' if old else 'gig'
    gigs = f"{COUNTS[count]} {word}{'' if count == 1 else 's'}"
    return f'{gigs} ({days_text(days, SHORT_DAYS if short else DAY_NAMES)})' if days else f'No {word}s'


def old_era(connection, companion: dict) -> bool:
    """A city before the jazz age (Camelot, London 1895, the Emerald City, Grandport): no "gigs" or "freelance"."""
    from companion.life import outings, work
    return work.era_group(outings.city_data(connection, companion['version']['definition'])) not in ('modern',
                                                                                                    'jazz-age')


SPELL_WORDS = {'busy': 'a busy spell', 'steady': 'a steady spell', 'dry': 'a dry spell'}
SPELL_ORDER = {'dry': 0, 'steady': 1, 'busy': 2}


def off_days(connection, companion: dict, start: date, end: date) -> set[str]:
    """Local dates the agenda turns work into a day off (companion/life/agenda.py holiday_block): public holidays,
    the family's tradition days, vacation days and job-hunt days. A shift or gig rolled onto one of them isn't
    worked, so the lines below leave it out."""
    from companion.almanac.context import city_for
    from companion.life import outings, traditions, work
    definition = companion['version']['definition']
    off = set(work.days_off(connection, companion, start, end))
    if city := outings.city_data(connection, definition):
        off |= {item['date'] for item in generators.holidays(city, start, end) if item['kind'] == 'public'}
    off |= set(traditions.on_dates(connection, companion, city_for(connection, definition), start, end))
    return off


def working(days: list[int], monday: date, off: set[str]) -> list[int]:
    return [day for day in days if (monday + timedelta(days=day)).isoformat() not in off]


def overview_line(connection, companion: dict, today: date) -> str:
    """The Character page's line: 'This week: Tue, Thu and Sat nights.' or 'Two gigs this week (Tue and Fri), a busy
    spell.' Empty when their week stays as written."""
    found = setup(connection, companion)
    if not found:
        return ''
    monday = monday_of(today)
    week = weeks(connection, companion, today, today, found)[monday.isoformat()]
    off = off_days(connection, companion, monday, monday + timedelta(days=6))
    week = {**week, 'days': working(week['days'], monday, off)}
    if found['kind'] == 'rota':
        return f"This week: {week_text('rota', week['days'], found['start'], found['end'])}."
    old = old_era(connection, companion)
    if not week['days']:
        return f"No {'engagements' if old else 'gigs'} this week, {SPELL_WORDS[week['spell']]}."
    gigs = week_text('freelance', week['days'], found['start'], found['end'], old=old)
    return f"{gigs.replace(' (', ' this week (', 1)}, {SPELL_WORDS[week['spell']]}."


def dated(days: list[int], monday: date) -> str:
    """'Tuesday 6, Thursday 8 and Friday 9': each day with its date, so "Saturday" is never this week's or next's
    by guesswork."""
    return days_text([f'{DAY_NAMES[day]} {(monday + timedelta(days=day)).day}' for day in days], None)


def days_free(left: list[int], following: list[int], today: date, monday: date) -> str:
    """'Tuesday 13 and Friday 16 this week; Monday 19 and Sunday 25 next week': the days without work by date, so a
    free day is never worked out by elimination."""
    free_now = [day for day in range(today.weekday(), 7) if day not in left]
    free_then = [day for day in range(7) if day not in following]
    parts = [f'{dated(free_now, monday)} this week'] if free_now else []
    parts += [f'{dated(free_then, monday + timedelta(weeks=1))} next week'] if free_then else []
    return '; '.join(parts)


def gigs_line(this: dict, following: dict, left: list[int], monday: date, old: bool) -> str:
    """A freelancer's line: this week's gigs and next week's by date, next week's spell said apart from this week's
    so a dry week doesn't read as a dry next week too ('engagements' and 'arranged' in an old era)."""
    gigs, booked = ('engagements', 'arranged') if old else ('gigs', 'booked')
    now = f"{gigs} {dated(left, monday)} this week" if left else f'no more {gigs} this week'
    then = f'nothing {booked} next week yet'
    if following['days']:
        named = f"{gigs} {dated(following['days'], monday + timedelta(weeks=1))} {booked} so far"
        turn = SPELL_ORDER[following['spell']] - SPELL_ORDER[this['spell']]
        then = f"next week {'picks up' if turn > 0 else 'is quieter'}: {named}" if turn else f'{named} next week'
    opening = 'You take work where it comes, so it comes in spells' if old else 'You freelance, so work comes in spells'
    return f"- {opening}, and lately it is {SPELL_WORDS[this['spell']]}: {now} and {then}."


def context_line(connection, companion: dict, today: date) -> str:
    """The chat's line in the Work section: the rest of this week's shifts (or gigs) and next week's, by date, and
    the days off by date. The wording won its A/Bs (/mnt/project-files/companion-shifts/report.md,
    /mnt/project-files/companion-e2e-v12/ab/shifts/results.md)."""
    found = setup(connection, companion)
    if not found:
        return ''
    monday = monday_of(today)
    span = weeks(connection, companion, today, today + timedelta(weeks=1), found)
    this, following = span[monday.isoformat()], span[(monday + timedelta(weeks=1)).isoformat()]
    off = off_days(connection, companion, monday, monday + timedelta(days=13))
    following = {**following, 'days': working(following['days'], monday + timedelta(weeks=1), off)}
    left = [day for day in working(this['days'], monday, off) if day >= today.weekday()]
    free = days_free(left, following['days'], today, monday)
    if found['kind'] == 'rota':
        now = f"The rest of this week: {dated(left, monday)}, {found['start']} to {found['end']}." if left else \
            'No more shifts this week.'
        then = f"Next week: {dated(following['days'], monday + timedelta(weeks=1))}." if following['days'] else \
            'No shifts next week.'
        return f'- Your shifts change every week. {now} {then}' + (f' Days off: {free}.' if free else '')
    line = gigs_line(this, following, left, monday, old_era(connection, companion))
    return line + (f' Free days: {free}.' if free else '')
