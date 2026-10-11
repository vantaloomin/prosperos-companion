"""Our year so far (Hit List #13): a scrapbook of the user's time with the companion.

A few swipeable pages for one stretch of time: the year so far (since the first talk or the last anniversary of
it), each full year before it, and each calendar year, shown at New Year. Every page is built from what really
happened on the active timeline and written by templates, never by a model:

- the cover: the dates, the days talked, the messages and pictures;
- the first thing the user said that year, and the reply;
- pictures the companion sent;
- how they got closer (the closeness stages reached, companion/memory/closeness.py);
- running jokes and the nickname, then the other shared moments remembered;
- the companion's own year: life chapters, the family holidays they kept and new things at home;
- a closing line.

A page with nothing to show is left out. In the week of an anniversary and the first week of January, Today points to
the scrapbook (`featured`) until the user opens it or puts it away (`seen`).
"""
from calendar import monthrange
from datetime import date, datetime, time, timedelta

from companion.clock import parse, stamp, zone
from companion.database import decode, many, optional, settings
from companion.errors import require
from companion.images import photos
from companion.life import occasions
from companion.memory import closeness

QUOTE_LIMIT = 280
PHOTO_LIMIT = 9
MOMENT_LIMIT = 6
YEAR_LIMIT = 8
NEW_YEAR_DAYS = 7
ORDINALS = ('first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth')
HOME_KINDS = {'new-pet': 'new', 'new-favorite': 'new', 'new-plant': 'new'}


def anniversary(first: date, years: int) -> date:
    """The day `years` years after the first talk; 29 February falls on the 28th in other years."""
    year = first.year + years
    return date(year, first.month, min(first.day, monthrange(year, first.month)[1]))


def ordinal(years: int) -> str:
    return ORDINALS[years - 1] if years <= len(ORDINALS) else f'{years}th'


def periods(first: date, today: date) -> list[dict]:
    """The stretches a scrapbook can cover, newest first: the year so far, full years, then calendar years."""
    done = 0
    while anniversary(first, done + 1) <= today:
        done += 1
    result = [{'key': 'so-far', 'title': 'Our year so far', 'start': anniversary(first, done), 'end': today}]
    result += [{'key': f'year-{years}', 'title': f'Our {ordinal(years)} year',
                'start': anniversary(first, years - 1), 'end': anniversary(first, years) - timedelta(days=1)}
               for years in range(done, max(0, done - YEAR_LIMIT), -1)]
    result += [{'key': f'cal-{year}', 'title': f'{year} together', 'start': max(first, date(year, 1, 1)),
                'end': date(year, 12, 31)} for year in range(today.year - 1, max(first.year - 1, today.year - 1 - YEAR_LIMIT), -1)]
    return result


def view(period: dict) -> dict:
    return {'key': period['key'], 'title': period['title'], 'start': period['start'].isoformat(),
            'end': period['end'].isoformat()}


def user_today(connection, now) -> tuple[date, object]:
    timezone = zone(settings(connection)['user_timezone'])
    return now.astimezone(timezone).date(), timezone


def listing(connection, companion: dict, now) -> dict:
    """The scrapbooks there are, and the one Today points to with its days talked, until the user opens it or puts
    it away."""
    today, timezone = user_today(connection, now)
    timeline_id = companion['active_timeline_id']
    first = occasions.first_talk(connection, timeline_id, timezone)
    if not first:
        return {'periods': [], 'featured': None, 'featured_days': 0}
    found = periods(first, today)
    key = featured(found, first, today)
    if key and optional(connection, 'SELECT 1 FROM scrapbook_seen WHERE timeline_id=? AND key=?', (timeline_id, key)):
        key = None
    period = next((item for item in found if item['key'] == key), None)
    return {'periods': [view(item) for item in found], 'featured': key,
            'featured_days': len(talked(connection, timeline_id, period, timezone)) if period else 0}


def seen(connection, companion: dict, key: str, now):
    """The user opened or put away the scrapbook Today pointed to."""
    connection.execute('INSERT OR IGNORE INTO scrapbook_seen (timeline_id, key, seen_at) VALUES (?, ?, ?)',
                       (companion['active_timeline_id'], key[:20], stamp(now)))


def talked(connection, timeline_id: str, period: dict, timezone) -> set[str]:
    """The local days the user wrote in a stretch of time."""
    rows = many(connection, "SELECT created_at FROM messages WHERE timeline_id=? AND role='user' AND active=1 AND "
                'created_at>=? AND created_at<?', (timeline_id, instant(period['start'], timezone),
                                                    instant(period['end'] + timedelta(days=1), timezone)))
    return {parse(row['created_at']).astimezone(timezone).date().isoformat() for row in rows}


def featured(found: list[dict], first: date, today: date) -> str | None:
    """In the week from an anniversary of the first talk, the year just finished; in January's first week, last
    year."""
    years = next((int(period['key'][5:]) for period in found if period['key'].startswith('year-')), 0)
    if years and (today - anniversary(first, years)).days < NEW_YEAR_DAYS:
        return f'year-{years}'
    if today.month == 1 and today.day <= NEW_YEAR_DAYS and any(period['key'] == f'cal-{today.year - 1}'
                                                                for period in found):
        return f'cal-{today.year - 1}'
    return None


def instant(day: date, timezone) -> str:
    return stamp(datetime.combine(day, time(), timezone))


def quote(text: str) -> str:
    text = ' '.join(text.split())
    return text if len(text) <= QUOTE_LIMIT else text[:QUOTE_LIMIT - 1].rstrip() + '…'


def plural(count: int, word: str) -> str:
    return f"{count:,} {word}{'' if count == 1 else 's'}"


def build(connection, companion: dict, key: str, now) -> dict:
    """One scrapbook's pages."""
    today, timezone = user_today(connection, now)
    timeline_id, name = companion['active_timeline_id'], companion['version']['name']
    first = occasions.first_talk(connection, timeline_id, timezone)
    period = next((item for item in periods(first, today) if item['key'] == key), None) if first else None
    require(period is not None, 'There is no scrapbook for that stretch of time yet.', 404)
    start, end = instant(period['start'], timezone), instant(period['end'] + timedelta(days=1), timezone)
    messages = many(connection, "SELECT id, role, text, created_at FROM messages WHERE timeline_id=? AND active=1 "
                    "AND status='complete' AND redacted_at IS NULL AND created_at>=? AND created_at<? ORDER BY seq",
                    (timeline_id, start, end))
    found = photos.for_messages(connection, [row['id'] for row in messages if row['role'] == 'companion'])
    sent = [found[row['id']] for row in messages if row['id'] in found and found[row['id']]['ref']
            and found[row['id']]['kind'] != 'meme']
    days = sorted({parse(row['created_at']).astimezone(timezone).date().isoformat() for row in messages
                   if row['role'] == 'user'})
    pages = [cover(period, name, days, messages, sent), opening(period, first, messages, timezone),
             pictures(name, sent, messages, timezone), *together(connection, companion, now, period, timezone),
             their_year(connection, companion, period, name), closing(period, days, name)]
    return {**view(period), 'name': name, 'pages': [page for page in pages if page]}


def cover(period, name, days, messages, sent) -> dict:
    stats = [(len(days), 'Day talked', 'Days talked'), (len(messages), 'Message', 'Messages'),
             (len(sent), f'Picture from {name}', f'Pictures from {name}')]
    return {'kind': 'cover', 'title': period['title'], 'subtitle': f'You and {name}',
            'stats': [{'value': f'{count:,}', 'label': one if count == 1 else many_}
                      for count, one, many_ in stats if count]}


def opening(period, first: date, messages, timezone) -> dict | None:
    said = next((row for row in messages if row['role'] == 'user'), None)
    if not said:
        return None
    reply = next((row for row in messages if row['role'] == 'companion' and row['created_at'] >= said['created_at']),
                 None)
    beginning = period['start'] == first
    return {'kind': 'first', 'title': 'The first thing you said' if beginning else 'How the year started',
            'date': parse(said['created_at']).astimezone(timezone).date().isoformat(),
            'said': quote(said['text']), 'reply': quote(reply['text']) if reply else None}


def pictures(name, sent, messages, timezone) -> dict | None:
    if not sent:
        return None
    when = {row['id']: parse(row['created_at']).astimezone(timezone).date().isoformat() for row in messages}
    chosen = sent if len(sent) <= PHOTO_LIMIT else [sent[round(index * (len(sent) - 1) / (PHOTO_LIMIT - 1))]
                                                     for index in range(PHOTO_LIMIT)]
    return {'kind': 'photos', 'title': f'Pictures {name} sent',
            'photos': [{'ref': photo['ref'], 'summary': photo['summary'], 'date': when.get(photo['message_id'])}
                       for photo in chosen]}


def together(connection, companion, now, period, timezone) -> list[dict]:
    """How they got closer, then the running jokes and shared moments of the year."""
    state = closeness.state(connection, companion, now)
    low, high = period['start'].isoformat(), period['end'].isoformat()
    reached = [{'date': step['on'], 'text': state['stages'][step['level'] - 1] + (' (you set it)' if step.get('kind') == 'set' else '')}
               for step in state['history'] if step.get('on') and low <= step['on'] <= high]
    nickname = f"They call you “{state['nickname']}”." if state['nickname'] else None
    pages = []
    if reached:
        pages.append({'kind': 'closer', 'title': 'How you got closer', 'items': reached})
    if state['jokes'] or nickname:
        pages.append({'kind': 'jokes', 'title': 'Running jokes', 'note': nickname,
                      'items': [{'text': f"{joke['subject']}: {joke['value']}"} for joke in state['jokes']]})
    # A running joke is shown once, on its own page.
    told = {(joke['subject'], joke['value']) for joke in state['jokes']}
    moments = [memory for memory in closeness.shared_moments(connection, companion, companion['active_timeline_id'],
                                                             now, None)
               if (memory['subject'], memory['value']) not in told
               and low <= parse(memory['created_at']).astimezone(timezone).date().isoformat() <= high]
    moments.sort(key=lambda memory: (-memory['pinned'], memory['created_at']))
    if moments:
        pages.append({'kind': 'moments', 'title': 'Moments to remember',
                      'items': [{'date': parse(memory['created_at']).astimezone(timezone).date().isoformat(),
                                 'text': f"{memory['subject']}: {memory['value']}"}
                                for memory in moments[:MOMENT_LIMIT]]})
    return pages


def their_year(connection, companion, period, name) -> dict | None:
    """The companion's own year: life chapters, family holidays kept and new things at home."""
    timeline_id, low, high = companion['active_timeline_id'], period['start'].isoformat(), period['end'].isoformat()
    items = [{'date': row['started_on'], 'text': row['title']} for row in many(
        connection, 'SELECT started_on, title FROM life_chapters WHERE timeline_id=? AND undone_at IS NULL AND '
        'started_on>=? AND started_on<=?', (timeline_id, low, high))]
    items += [{'date': row['local_date'], 'text': decode(row['entry'])['summary']} for row in many(
        connection, "SELECT local_date, entry FROM life_agenda WHERE timeline_id=? AND subject='companion' AND "
        "status='happened' AND json_extract(entry, '$.activity')='tradition' AND local_date>=? AND local_date<=?",
        (timeline_id, low, high))]
    items += [{'date': row['local_date'], 'text': f"{name} {row['text']}"} for row in many(
        connection, 'SELECT local_date, kind, text FROM home_log WHERE timeline_id=? AND local_date>=? AND '
        'local_date<=?', (timeline_id, low, high)) if row['kind'] in HOME_KINDS]
    if not items:
        return None
    return {'kind': 'their-year', 'title': f"{name}'s year", 'items': sorted(items, key=lambda item: item['date'])}


def closing(period, days, name) -> dict | None:
    if not days:
        return None
    if period['key'] == 'so-far':
        text = f"{plural(len(days), 'day')} talked so far. Plenty more to come."
    else:
        text = f"{plural(len(days), 'day')} talked. Here's to the next {len(days):,}."
    return {'kind': 'closing', 'title': 'Here’s to the next one', 'text': text, 'name': name}
