"""A storyline beat that says the companion spent the evening with someone takes that evening in both their days
(companion/life/storylines.py as_plans, companion/life/joint.py), and every other beat keeps to the companion's hours
outside work (v1.4.0, world consistency part D)."""
import json
import re
from datetime import date, timedelta

import pytest
from conftest import reconcile
from test_storylines import WORKDAY, stored

from companion.characters import require_current
from companion.database import decode, encode, identifier
from companion.life import agenda, body, joint, pronouns, routine, storylines

# Someone in Mira's circle, on a routine that leaves the evening free.
THEIR_DAY = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '08:00', 'end': '16:00', 'days': [0, 1, 2, 3, 4]},
             {'key': 'free', 'label': 'Free time', 'kind': 'leisure', 'start': '16:30', 'end': '22:00'},
             {'key': 'sleep', 'label': 'Asleep', 'kind': 'sleep', 'start': '22:30', 'end': '06:30'}]


def mira(client, monkeypatch, schedule):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'schedule': schedule,
                                                     'location': 'Fells Point, Baltimore',
                                                     'personality': 'Outgoing, a social butterfly.'})
    assert response.status_code == 200, response.text


def only(monkeypatch, key):
    monkeypatch.setattr(storylines, 'START', (1, 1, 1, 1))
    monkeypatch.setattr(storylines, 'STORIES', (storylines.find_story(key),))


def at(clock, hour, minute=0):
    clock.instant = clock.now().replace(hour=hour, minute=minute)


def started(client) -> tuple[dict, dict]:
    """The storyline and the person it takes Mira's evening with, on a routine of their own. Who is in the circle is
    seeded by the timeline's random id, so when the story found nobody to cast, it starts with someone today."""
    rows = stored(client)
    database = client.app.state.database
    with database.connect(write=True) as connection:
        if not rows:
            companion = require_current(connection)
            story = storylines.STORIES[0]
            person = connection.execute("SELECT id FROM circle_people WHERE status='active' AND timeline_id=? LIMIT 1",
                                        (companion['active_timeline_id'],)).fetchone()
            day = storylines.local_today(companion, database.clock.now())
            stages = [{'on': (day + timedelta(days=index * 2)).isoformat(), 'text': stage[0].text,
                       'share': stage[0].share, 'tone': stage[0].tone} for index, stage in enumerate(story.stages)]
            connection.execute("INSERT INTO storylines (id, timeline_id, story, level, cast_ids, stages, started_on, "
                               "status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'running', '2026-01-01T00:00:00Z')",
                               (identifier(), companion['active_timeline_id'], story.key, story.level,
                                json.dumps([person['id']]), encode(stages), stages[0]['on']))
            rows = [dict(connection.execute('SELECT * FROM storylines').fetchone())]
        person_id = json.loads(rows[0]['cast_ids'])[0]
        connection.execute("UPDATE circle_people SET schedule=?, revision=revision+1 WHERE id=?",
                           (encode(THEIR_DAY), person_id))
        person = dict(connection.execute('SELECT * FROM circle_people WHERE id=?', (person_id,)).fetchone())
    return rows[0], person


def rows_at(client, subject, moment) -> list[dict]:
    with client.app.state.database.connect() as connection:
        return [{**dict(row), 'entry': decode(row['entry']) if row['entry'] else None} for row in connection.execute(
            'SELECT * FROM life_agenda WHERE subject=? AND starts_at<=? AND ends_at>?', (subject, moment, moment))]


def test_the_evening_after_a_breakup_is_in_both_their_days(client, clock, monkeypatch):
    mira(client, monkeypatch, WORKDAY)
    only(monkeypatch, 'friend_breakup')
    at(clock, 7)
    reconcile(client)
    row, friend = started(client)
    reconcile(client)
    evening = clock.now().replace(hour=19).isoformat()
    [mine] = rows_at(client, 'companion', evening)
    assert mine['entry']['with']['id'] == friend['id'] and mine['entry']['storyline']['id'] == row['id']
    assert mine['entry']['summary'] == f"Mira spent the evening on the phone with {friend['name']} after the breakup."
    [theirs] = rows_at(client, friend['id'], evening)
    assert theirs['entry']['summary'] == f"{friend['name']} spent the evening on the phone with Mira after the breakup."
    assert theirs['entry']['joint'] and theirs['starts_at'][11:16] == '18:00'
    # Nothing tells it before it happens: not Today, and not the plans the chat hears about.
    assert client.get('/api/life/storylines').json() == []
    with client.app.state.database.connect() as connection:
        companion = require_current(connection)
        assert not [item for item in agenda.upcoming(connection, companion['active_timeline_id'],
                                                     companion['version']['id'], clock.now(), hours=24)
                    if item['entry'].get('storyline')]
    at(clock, 17, 59)
    assert client.get('/api/life/storylines').json() == []
    at(clock, 18)
    [listed] = client.get('/api/life/storylines').json()
    assert listed['beats'][0]['time'] == '18:00' and 'spent the evening on the phone' in listed['beats'][0]['text']
    at(clock, 22, 15)
    reconcile(client)
    lines = [item['entry']['summary'] for item in
             client.get(f"/api/life/circle/{friend['id']}/diary").json()]
    assert theirs['entry']['summary'] in lines


def test_with_no_free_evening_the_beat_says_less(client, clock, monkeypatch):
    late = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '12:00', 'end': '22:30',
             'days': [0, 1, 2, 3, 4, 5, 6]},
            {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]
    mira(client, monkeypatch, late)
    only(monkeypatch, 'friend_breakup')
    at(clock, 7)
    reconcile(client)
    _row, friend = started(client)
    at(clock, 21, 30)
    reconcile(client)
    [listed] = client.get('/api/life/storylines').json()
    beat = listed['beats'][0]
    them = pronouns.person(decode(friend['details']).get('pronouns'))['them']
    assert beat['text'] == f"{friend['name']} went through a breakup, and Mira has been checking in on {them}."
    assert 'on the phone' not in beat['share'] and '18:00' <= beat['time'] <= '21:00'
    assert not [item for item in rows_at(client, 'companion', clock.now().replace(hour=19).isoformat())
                if (item['entry'] or {}).get('storyline')]


def test_ending_the_storyline_gives_the_evening_back(client, clock, monkeypatch):
    mira(client, monkeypatch, WORKDAY)
    only(monkeypatch, 'friend_breakup')
    at(clock, 7)
    reconcile(client)
    row, friend = started(client)
    reconcile(client)
    assert client.post(f"/api/life/storylines/{row['id']}/end").status_code == 200
    reconcile(client)
    evening = clock.now().replace(hour=19).isoformat()
    assert not [item for item in rows_at(client, 'companion', evening) if (item['entry'] or {}).get('storyline')]
    assert not [item for item in rows_at(client, friend['id'], evening)
                if (item['entry'] or {}).get('activity') == 'stood-by']


def test_beats_keep_to_the_hours_outside_work(monkeypatch):
    from datetime import time
    monkeypatch.setattr(storylines, 'BEAT_HOURS', (time(8, 30), time(21, 0)))
    schedule, _default = routine.blocks({'schedule': WORKDAY})
    monday, saturday = date(2026, 10, 5), date(2026, 10, 10)
    assert storylines.free_hours(schedule, monday) == [(8 * 60 + 30, 8 * 60 + 59), (17 * 60, 21 * 60)]
    assert storylines.free_hours(schedule, saturday) == [(8 * 60 + 30, 21 * 60)]
    times = storylines.Timing(schedule, {})
    found = []
    for number in range(300):
        row = {'id': f'story-{number}', 'story': 'credit_taker'}
        stage = {'on': monday.isoformat(), 'text': storylines.find_story('credit_taker').stages[0][0].text}
        found.append(storylines.beat_at(row, 0, stage, times))
    assert all(not '09:00' <= when < '17:00' for when in found) and len(set(found)) > 100
    # Spread over the evening, never piled on one minute (tester, 2026-10-31).
    assert max(found.count(when) for when in found) < 10


def test_every_evening_is_told_in_every_era():
    row, names = {'cast_ids': '["p1"]'}, {'p1': {'name': 'Kaito', 'role': 'friend'}}
    for era, definition in (('modern', {'name': 'Sett'}), ('older', {'name': 'Wren', 'home_city': 'camelot'})):
        for story in storylines.STORIES:
            for index, stage in enumerate(story.stages):
                for item in stage:
                    if not item.spent:
                        continue
                    plan = {'storyline': {'id': 's1', 'beat': index, 'story': story.key,
                                          'with': {'id': 'p1', 'name': 'Kaito'}}}
                    entry = storylines.entry(plan, {'weather': None}, definition)
                    theirs = joint.told(entry, 'Kaito', definition['name'])
                    short = [storylines.fill(said, row, names, definition, you) for said in
                             (item.spent.short, item.spent.short_share) for you in (False, True)]
                    for text in (entry['summary'], theirs, *short):
                        assert '{' not in text and 'Kaito' in text, text
                        if era == 'older':
                            assert not re.search(r'\b(phone|online|texted|internet)\b', text), text
                    assert definition['name'] in entry['summary'] and definition['name'] in theirs


@pytest.mark.parametrize('key', ['coworker_leaving', 'parents_separating'])
def test_other_evenings_are_pinned_on_their_day(key):
    story = storylines.find_story(key)
    spent = [(index, item) for index, stage in enumerate(story.stages) for item in stage if item.spent]
    assert spent and all(len(story.stages[index]) == 1 for index, _item in spent)


def test_the_short_way_uses_their_pronouns():
    row = {'cast_ids': '["p1"]'}
    short = storylines.find_story('friend_breakup').stages[0][0].spent.short
    for said, them in (('he/him', 'him'), ('she/her', 'her'), (None, 'them')):
        names = {'p1': {'name': 'Kaito', 'role': 'friend', 'pronouns': said}}
        assert storylines.fill(short, row, names, {'name': 'Sett'}).endswith(f'checking in on {them}.')


def test_a_last_day_comes_before_the_send_off(client, clock, monkeypatch):
    """Iris, 2026-11-11: the last day at the end of the shift, then the drinks in the evening, in that order."""
    mira(client, monkeypatch, WORKDAY)
    only(monkeypatch, 'coworker_leaving')
    at(clock, 7)
    reconcile(client)
    row, coworker = started(client)
    stages = json.loads(row['stages'])
    for _day in range(30):
        if clock.now().date().isoformat() > stages[1]['on']:
            break
        clock.advance(timedelta(days=1))
        reconcile(client)
    diary = client.get(f"/api/life/circle/{coworker['id']}/diary?limit=100").json()
    said = [item['entry']['summary'] for item in sorted(diary, key=lambda item: item['starts_at'])]
    last, drinks = f"It was {coworker['name']}'s last day at work.", f"{coworker['name']} had send-off drinks with Mira."
    assert last in said and drinks in said and said.index(last) < said.index(drinks)
