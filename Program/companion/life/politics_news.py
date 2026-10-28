"""Real local headlines in Talk of the town (companion/life/politics.py), when the user lets the news lookup run for
the companion's city (Settings > Context tools, 2026-10-28; Vanta asked for it the day local politics shipped).

A news lookup for a real, present-day city (the built-in local pulse, or any news tool the user mapped with
"For the companion's city") keeps its political headlines: the ones that match a topic in world/data/politics_news.json,
first match first ("Council votes to rezone the waterfront" is housing, "Transit fares going up" is getting around).
They are deleted with the lookup.

A topic that matches a big question the city is already arguing about adds the headlines to it as its latest news.
Any other topic with headlines in the last month becomes its own issue, as many as the city has big questions of its
era (Realism > Local politics): people take sides on it by their work and character, the same as on the app's own,
and like a real question of its year it never settles. No model is involved; only the city's name is sent, and only by
a lookup the user turned on.
"""
import json
import re
from datetime import date, datetime, timedelta
from functools import cache

from companion.database import many
from companion.world import catalog, politics
from companion.world.changes import headlines
from companion.world.generators import unit

DATA = catalog.DATA / 'politics_news.json'
# How long a headline keeps an issue going, and how recent the last one must be for it to count as heated.
KEPT, HEATED = timedelta(days=30), timedelta(days=7)
BEATS = 6
# Headlines read from one lookup.
MOST = 12
# "Council votes to rezone the waterfront (The City Paper, Oct 26)": the source and date the news tool adds.
SOURCE = re.compile(r'\s*\([^()]*\)\s*$')
STAMP = re.compile(r'\s*\((?:(?P<source>[^()]*?),\s*)?(?P<month>[A-Z][a-z]{2}) (?P<day>\d{1,2})\)\s*$')


@cache
def topics() -> list[dict]:
    found = json.loads(DATA.read_text(encoding='utf-8'))['topics']
    return [{**topic, 'pattern': re.compile(topic['match'], re.I)} for topic in found]


def topic_of(text: str) -> str | None:
    """The first topic a headline matches, without the source and date at its end, or None for any other news."""
    plain = SOURCE.sub('', text)
    return next((topic['id'] for topic in topics() if topic['pattern'].search(plain)), None)


def real_and_now(data: dict) -> bool:
    return data.get('setting') == 'real' and (data.get('era') or 'modern') == 'modern'


def remember(database, observation: dict) -> None:
    """Keep the political headlines from a readable news lookup made for the companion's city."""
    location = observation.get('location') or {}
    if (observation.get('category') != 'news' or observation.get('purpose') != 'companion_city'
            or observation.get('status') != 'ok' or not location.get('city')):
        return
    day = date.fromisoformat((observation.get('retrieved_at') or database.now())[:10])
    with database.connect(write=True) as connection:
        for line in lines_of(observation):
            topic = topic_of(line)
            if topic:
                text, on = dated(line, day)
                connection.execute(
                    'INSERT INTO politics_headlines (city_id, text, topic, on_day, observation_id, created_at) '
                    'VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(city_id, text) DO NOTHING',
                    (location['city'], text, topic, on.isoformat(), observation['id'], database.now()))


def dated(line: str, day: date) -> tuple[str, date]:
    """A headline without the date the news tool put after its source, and that date (the day it was read when
    there is none): "Strike vote at the port (WBAL, Oct 26)" is "Strike vote at the port (WBAL)" on October 26."""
    found = STAMP.search(line)
    if not found:
        return line, day
    try:
        on = datetime.strptime(f"{found['month']} {found['day']} {day.year}", '%b %d %Y').date()
    except ValueError:
        return line, day
    if on > day:
        on = on.replace(year=day.year - 1)
    source = found['source']
    return line[:found.start()] + (f' ({source})' if source else ''), on


def lines_of(observation: dict) -> list[str]:
    """The news tool's own list of headlines when it gives one (the local pulse also lists what Reddit and
    Wikipedia readers are on, which is not news), else the list lines of its text."""
    found = (observation.get('structured') or {}).get('headlines')
    if isinstance(found, list) and found:
        return [str(item).strip()[:200] for item in found if isinstance(item, str) and item.strip()][:MOST]
    return headlines(observation.get('content', ''), MOST)


def recent(connection, city_id: str, day: date) -> dict[str, list[dict]]:
    """The last month's headlines by topic, oldest first within each, newest topic first."""
    rows = many(connection, 'SELECT text, topic, on_day FROM politics_headlines WHERE city_id=? AND on_day>? AND '
                'on_day<=? ORDER BY on_day, rowid', (city_id, (day - KEPT).isoformat(), day.isoformat()))
    found: dict[str, list[dict]] = {}
    for row in rows:
        found.setdefault(row['topic'], []).append(
            {'on': row['on_day'], 'text': row['text'], 'favors': int(unit(city_id, row['text'], 'favors') < 0.5),
             'real': True})
    return dict(sorted(found.items(), key=lambda item: item[1][-1]['on'], reverse=True))


def issues(connection, data: dict, day: date, level: int, era: list[dict]) -> list[dict]:
    """Add the news to the big questions it is about, and make issues of the rest, as many as the city has big
    questions (`era` is changed in place)."""
    if not level or not real_and_now(data):
        return []
    by_id = {issue['id']: issue for issue in era}
    found = []
    for topic_id, beats in recent(connection, data['id'], day).items():
        topic = next(item for item in topics() if item['id'] == topic_id)
        known = by_id.get(f"era-{topic.get('question')}")
        if known:
            known['beats'] = sorted([*known['beats'], *beats], key=lambda beat: beat['on'])[-BEATS:]
            known['stage'] = stage(known['beats'], day)
        elif len(found) < politics.ERA_COUNT[level]:
            found.append(issue(topic, beats, day))
    return found


def issue(topic: dict, beats: list[dict], day: date) -> dict:
    base = next((item for item in politics.bank()['questions']['modern'] if item['id'] == topic.get('question')),
                None)
    title = base['title'] if base else topic['title']
    question = base['question'] if base else topic['question_text']
    sides = base['sides'] if base else topic['sides']
    return {'id': f"news-{topic['id']}", 'kind': 'era', 'title': title, 'question': question,
            'sides': [dict(side) for side in sides], 'real': True, 'stage': stage(beats, day), 'beats': beats[-BEATS:],
            'hood': None, 'origin': 'news', 'settled': None, 'started': beats[0]['on']}


def stage(beats: list[dict], day: date) -> str:
    return 'heated' if beats and beats[-1]['on'] >= (day - HEATED).isoformat() else 'open'

