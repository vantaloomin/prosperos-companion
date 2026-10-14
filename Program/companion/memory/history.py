"""Our history at a glance (Hit List #16): the shape of the whole relationship, one line at a time.

One line a week lately, one a month further back and one a year before that, oldest first, from the first talk to
the end of last week. Every line is built from what really happened on the active timeline, by rules and templates,
never by a model: the days they talked, the user's own words (the day summaries, companion/memory/consolidation.py),
the shared moments remembered and how they got closer (companion/memory/closeness.py), then the companion's own big
turns (life chapters and trips). A stretch with only talking in it (or none) says just that, and such stretches in a
row share one line.

The same lines go two places: the chat context, with the sections that rarely change so the start of the prompt
stays cacheable (they change once a week, when a week is over), and the scrapbook's "All of it" view, where the user
reads them and corrects any line in their own words or leaves it out. A correction replaces the line in both, and
when a week has become part of a month (or a month part of a year) the user's words come along into that line.

The size is fixed: at most WEEKS_BACK weeks plus the rest of their month, MONTHS_BACK months, then one line a year,
each line at most LINE_LIMIT characters for its stretch. Deleted, declined or blocked memories and messages never
show.
"""
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from companion import prompt_library
from companion.clock import parse, stamp, zone
from companion.database import many, settings
from companion.errors import require
from companion.life import occasions
from companion.memory import closeness
from companion.memory.consolidation import excluded_sources, usable_summaries
from companion.world import newcomers, wording

WEEKS_BACK = 12
MONTHS_BACK = 12
# The longest a line gets, by its stretch: a longer stretch has more to say.
LINE_LIMIT = {'week': 220, 'month': 300, 'year': 360}
QUOTE_LIMIT = 90
CORRECTION_LIMIT = 300
SAY = {'week': 1, 'month': 2, 'year': 3}
MOMENTS = {'week': 2, 'month': 3, 'year': 4}
# The shorter stretches whose corrections come along into a longer one's line.
FINER = {'week': '', 'month': 'w', 'year': 'wm'}
KEY = re.compile(r'^(w\d{4}-\d{2}-\d{2}|m\d{4}-\d{2}|y\d{4})$')
QUOTED = re.compile(r'“(.+?)”')
MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
          'November', 'December')

# The section's opening line, editable in Settings > Advanced > Prompts (companion/prompt_library.py).
INTRO = ('One line a week lately, one a month or a year further back, oldest first, from what really happened between '
         'you. It is true: let it shape how you talk about your time together, the way someone who was there would. '
         'Bring a line up only when it fits, never recite the list or count the days aloud, and never contradict it. '
         "A line in the user's words is how the user remembers that time.")


@dataclass
class Stretch:
    """One line's stretch of time and what happened in it."""
    key: str
    kind: str
    start: date
    end: date
    days: int = 0
    said: list[tuple[str, str]] = field(default_factory=list)  # (day, the user's sentence)
    moments: list[str] = field(default_factory=list)
    closer: list[str] = field(default_factory=list)
    life: list[tuple[str, str]] = field(default_factory=list)  # (in the companion's words, in the user's)
    until: date | None = None  # the last stretch of bare ones in a row that share this line

    def bare(self) -> bool:
        """Nothing happened but talking (or not)."""
        return not (self.said or self.moments or self.closer or self.life)


def instant(day: date, timezone) -> str:
    return stamp(datetime.combine(day, time(), timezone))


def happened(memory: dict, timezone) -> str:
    """The local day a moment happened (when it applies from, else when it was said), as the scrapbook dates it."""
    return parse(memory['applies_from'] or memory['stated_at']).astimezone(timezone).date().isoformat()


def first_name(companion: dict) -> str:
    return (companion['version']['name'].split() or ['They'])[0]


def monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def add_months(day: date, months: int) -> date:
    index = day.year * 12 + day.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def stretches(first: date, today: date) -> list[Stretch]:
    """The stretches from the first talk to the end of last week: weeks lately, then months, then years, oldest
    first. Weekly lines start at the week holding the first of a month, so a month is never half weeks."""
    end = monday(today) - timedelta(days=1)
    if end < first:
        return []
    back = monday(today) - timedelta(weeks=WEEKS_BACK)
    weekly = monday(date(back.year, back.month, 1))
    # When the first weekly line starts in the month before, that month's line ends the day before it.
    monthly = add_months(date(weekly.year, weekly.month, 1), (weekly.day != 1) - MONTHS_BACK)
    found = []
    year = first.year
    while date(year, 1, 1) < monthly:
        found.append(Stretch(f'y{year}', 'year', max(first, date(year, 1, 1)), min(date(year, 12, 31),
                                                                                  monthly - timedelta(days=1))))
        year += 1
    month = max(monthly, date(first.year, first.month, 1))
    while month < weekly:
        found.append(Stretch(f'm{month:%Y-%m}', 'month', max(first, month),
                             min(add_months(month, 1), weekly) - timedelta(days=1)))
        month = add_months(month, 1)
    week = max(weekly, monday(first))
    while week <= end:
        found.append(Stretch(f'w{week.isoformat()}', 'week', max(first, week), week + timedelta(days=6)))
        week += timedelta(weeks=1)
    return [item for item in found if item.start <= item.end]


def holding(found: list[Stretch], day: str, skip: tuple = ()) -> Stretch | None:
    """The stretch a day falls in, or None when it is in a shorter stretch the user left out."""
    if any(low <= day <= high for low, high in skip):
        return None
    for item in found:
        if item.start.isoformat() <= day <= item.end.isoformat():
            return item
    return None


def gather(connection, companion: dict, now, found: list[Stretch], timezone, skip: tuple = ()):
    """What happened in each stretch, from the timeline's own records. Days in `skip` (weeks or months the user left
    out, now part of a longer line) add nothing but the days talked."""
    if not found:
        return
    timeline_id, name = companion['active_timeline_id'], first_name(companion)
    low, high = found[0].start, found[-1].end
    talked_days(connection, timeline_id, found, low, high, timezone)
    words(connection, companion, found, skip)
    current = closeness.state(connection, companion, now)
    for step in current['history']:
        if step.get('on') and (item := holding(found, step['on'], skip)):
            item.closer.append(current['stages'][step['level'] - 1])
    for memory in closeness.shared_moments(connection, companion, timeline_id, now, None):
        if item := holding(found, happened(memory, timezone), skip):
            item.moments.append(memory['subject'])
    for row in many(connection, 'SELECT started_on, title, told FROM life_chapters WHERE timeline_id=? AND '
                    'undone_at IS NULL AND started_on>=? AND started_on<=? ORDER BY started_on',
                    (timeline_id, low.isoformat(), high.isoformat())):
        if item := holding(found, row['started_on'], skip):
            item.life.append((row['told'].rstrip('.'), row['title']))
    for row in many(connection, "SELECT start_date, city_name FROM trips WHERE timeline_id=? AND status='planned' "
                    'AND start_date>=? AND end_date<=? ORDER BY start_date',
                    (timeline_id, low.isoformat(), high.isoformat())):
        if item := holding(found, row['start_date'], skip):
            item.life.append((f"You went away to {row['city_name']}", f"{name} went away to {row['city_name']}"))


def talked_days(connection, timeline_id, found, low, high, timezone):
    rows = many(connection, "SELECT created_at FROM messages WHERE timeline_id=? AND role='user' AND active=1 AND status='complete' AND "
                'redacted_at IS NULL AND import_id IS NULL AND created_at>=? AND created_at<?',
                (timeline_id, instant(low, timezone), instant(high + timedelta(days=1), timezone)))
    for day in sorted({parse(row['created_at']).astimezone(timezone).date().isoformat() for row in rows}):
        if item := holding(found, day):
            item.days += 1


def words(connection, companion, found, skip=()):
    """The user's own sentences from the day summaries: the longest of each day's, a few a stretch, in order."""
    summaries = usable_summaries(connection, companion['active_timeline_id'],
                                 excluded_sources(connection, companion['id']))
    picked: dict[str, list[tuple[str, str]]] = {}
    for row in summaries:
        said = QUOTED.findall(row['text'])
        if said and (item := holding(found, row['day'], skip)):
            picked.setdefault(item.key, []).append((row['day'], max(said, key=len)))
    for item in found:
        best = sorted(picked.get(item.key, []), key=lambda pair: -len(pair[1]))[:SAY[item.kind]]
        item.said = sorted(best)


def merged(found: list[Stretch], fixed: dict[str, str]) -> list[Stretch]:
    """Bare stretches of the same kind in a row share one line: "6 Jul to 2 Aug 2026, 9 days". The user's words for
    such a line are kept on each of its stretches, so it stays one line with them."""
    result: list[Stretch] = []
    for item in found:
        last = result[-1] if result else None
        if last and last.kind == item.kind and plain(last, fixed) and plain(item, fixed) and \
                fixed.get(last.key) == fixed.get(item.key):
            last.until, last.days = item.end, last.days + item.days
            continue
        result.append(item)
    return result


def plain(item: Stretch, fixed: dict[str, str]) -> bool:
    return item.bare() and not carried(item, fixed)


def day_label(day: date, american: bool, year: bool = True) -> str:
    """"Oct 5, 2026" in the United States, "5 Oct 2026" elsewhere (companion/world/wording.py)."""
    if american:
        return f'{day:%b} {day.day}' + (f', {day.year}' if year else '')
    return f'{day.day} {day:%b}' + (f' {day.year}' if year else '')


def label(item: Stretch, american: bool = False) -> str:
    """"Week of Oct 5, 2026", "September 2026", "2025", or the span of quiet ones in a row, dated the way the
    scrapbook dates them (src/features/year/yearText.ts stretchText)."""
    end = item.until or item.end
    if item.kind == 'week':
        if not item.until:
            return f'Week of {day_label(date.fromisoformat(item.key[1:]), american)}'
        return f'{day_label(item.start, american, item.start.year != end.year)} to {day_label(end, american)}'
    if item.kind == 'month':
        if item.until:
            return f'{MONTHS[item.start.month - 1]} to {MONTHS[end.month - 1]} {end.year}'
        return f'{MONTHS[item.start.month - 1]} {item.start.year}'
    return f'{item.start.year}' if not item.until else f'{item.start.year} to {end.year}'


def days_text(item: Stretch) -> str:
    if not item.days:
        return "You didn't talk"
    return f"You talked on {item.days} {'day' if item.days == 1 else 'days'}"


def parts(item: Stretch, for_prompt: bool, name: str) -> list[str]:
    """The line's sentences in order: the days talked, the user's own words, the shared moments, how they got closer,
    then the companion's own big turns."""
    found = [days_text(item)]
    who = 'The user said' if for_prompt else 'You said'
    found += [f'{who} “{quote_short(said)}”' for _day, said in item.said]
    found += list(dict.fromkeys(item.moments))[:MOMENTS[item.kind]]  # the same outing twice reads once
    found += [f"{'You two' if for_prompt else f'You and {name}'} got closer (now “{stage}”)" for stage in item.closer[-1:]]
    found += [own if for_prompt else theirs for own, theirs in item.life]
    return found


def quote_short(text: str) -> str:
    text = ' '.join(text.split())
    return text if len(text) <= QUOTE_LIMIT else text[:QUOTE_LIMIT - 1].rstrip() + '…'


def joined(sentences: list[str], limit: int) -> str:
    """As many sentences as fit in `limit` characters, the first always."""
    text = ''
    for sentence in sentences:
        piece = sentence if sentence.rstrip('”')[-1:] in ('.', '!', '?', '…') else f'{sentence}.'
        if text and len(text) + len(piece) + 1 > limit:
            break
        text = f'{text} {piece}'.strip()
    return text


def corrections(connection, timeline_id: str) -> dict[str, str]:
    return {row['period_key']: row['text'] for row in many(
        connection, 'SELECT period_key, text FROM history_corrections WHERE timeline_id=?', (timeline_id,))}


def carried(item: Stretch, fixed: dict[str, str]) -> list[str]:
    """The user's words for weeks or months that are now part of this longer stretch."""
    finer = FINER[item.kind]
    low, high = item.start.isoformat(), (item.until or item.end).isoformat()
    return [text for key, text in sorted(fixed.items())
            if key[0] in finer and text.strip() and low <= key_start(key) <= high]


def left_out(found: list[Stretch], fixed: dict[str, str]) -> tuple:
    """The days of weeks or months the user left out that are now part of a longer line: (first, last) each."""
    shown = {item.key for item in found}
    return tuple((key_start(key), key_end(key)) for key, text in fixed.items() if not text.strip() and key not in shown)


def key_end(key: str) -> str:
    start = date.fromisoformat(key_start(key))
    end = {'w': start + timedelta(days=6), 'm': add_months(start, 1) - timedelta(days=1),
           'y': date(start.year, 12, 31)}[key[0]]
    return end.isoformat()


def key_start(key: str) -> str:
    """The first day a line's key stands for: w2026-10-06, m2026-10 or y2026."""
    return {'w': key[1:], 'm': f'{key[1:]}-01', 'y': f'{key[1:]}-01-01'}[key[0]]


def lines(connection, companion: dict, now) -> list[dict]:
    """Every line, oldest first: its stretch, the app's line for the chat and for the user, and the user's own."""
    timezone = zone(settings(connection)['user_timezone'])
    timeline_id, name = companion['active_timeline_id'], first_name(companion)
    first = occasions.first_talk(connection, timeline_id, timezone)
    if not first:
        return []
    found = stretches(first, now.astimezone(timezone).date())
    fixed = corrections(connection, timeline_id)
    gather(connection, companion, now, found, timezone, left_out(found, fixed))
    american = wording.american(newcomers.city_for(connection, companion['version']['definition']))
    result = []
    for item in merged(found, fixed):
        own, theirs = parts(item, True, name), parts(item, False, name)
        extra = [f'In the user’s words: “{text}”' for text in carried(item, fixed)]
        mine = [f'In your words: “{text}”' for text in carried(item, fixed)]
        # The user sees the days talked beside the line, so their line starts with what happened (Iris).
        result.append({'key': item.key, 'kind': item.kind, 'start': item.start.isoformat(),
                       'end': (item.until or item.end).isoformat(), 'label': label(item, american), 'days': item.days,
                       'count': own[0], 'prompt': joined([*own[:1], *extra, *own[1:]], LINE_LIMIT[item.kind]),
                       'text': joined([*mine, *theirs[1:]], LINE_LIMIT[item.kind]) if len(theirs) > 1 or mine else '',
                       'corrected': fixed.get(item.key)})
    return result


def prompt_line(line: dict) -> str | None:
    if line['corrected'] is None:
        return f"- {line['label']}: {line['prompt']}"
    if not line['corrected'].strip():
        return None
    return f"- {line['label']}: {line['count']}. In the user's words: “{line['corrected']}”"


def context_text(connection, companion: dict, now) -> str | None:
    """The chat section: the opening line, then one line per stretch the user has not left out."""
    found = [text for line in lines(connection, companion, now) if (text := prompt_line(line))]
    if not found:
        return None
    return '\n'.join([prompt_library.text(connection, 'our-history'), *found])


def offer(packet, connection, companion, now):
    """Adds the 'history' section as one piece, so it is all there or not at all."""
    if text := context_text(connection, companion, now):
        packet.offer('history', 'history', text)


# The "All of it" view -----------------------------------------------------------------------------------------------

def view(connection, companion: dict, now) -> dict:
    return {'name': companion['version']['name'],
            'lines': [{key: line[key] for key in ('key', 'kind', 'start', 'end', 'label', 'days', 'text', 'corrected')}
                      for line in lines(connection, companion, now)]}


def correct(connection, companion: dict, key: str, text: str | None, timestamp: str, now=None):
    """The user's own words for a line (empty: leave it out), or None to put the app's line back. A line for quiet
    weeks or months in a row keeps the words on each of them."""
    require(bool(KEY.match(key)), 'There is no line for that stretch of time.', 404)
    timeline_id = companion['active_timeline_id']
    line = next((line for line in lines(connection, companion, now) if line['key'] == key), None) if now else None
    require(text is None or now is None or line is not None, 'There is no line for that stretch of time.', 404)
    keys = run(key, line['end']) if line else [key]
    if text is None:
        connection.executemany('DELETE FROM history_corrections WHERE timeline_id=? AND period_key=?',
                               [(timeline_id, each) for each in keys])
        return
    text = ' '.join(text.split())
    require(len(text) <= CORRECTION_LIMIT, f'Keep it under {CORRECTION_LIMIT} characters.', 422)
    connection.executemany('INSERT INTO history_corrections (timeline_id, period_key, text, updated_at) VALUES (?, ?, ?, ?) '
                           'ON CONFLICT(timeline_id, period_key) DO UPDATE SET text=excluded.text, '
                           'updated_at=excluded.updated_at', [(timeline_id, each, text, timestamp) for each in keys])


def run(key: str, end: str) -> list[str]:
    """The keys of the stretches a line stands for, from its first to `end`: one, or each of the quiet ones in a row."""
    found, day = [], date.fromisoformat(key_start(key))
    while day.isoformat() <= end:
        found.append({'w': f'w{day.isoformat()}', 'm': f'm{day:%Y-%m}', 'y': f'y{day.year}'}[key[0]])
        day = {'w': day + timedelta(weeks=1), 'm': add_months(day, 1), 'y': date(day.year + 1, 1, 1)}[key[0]]
    return found
