"""Looks that change (companion/life/grooming.py)."""
import json
import re
from datetime import date, timedelta

import pytest
from conftest import reconcile

from companion.database import decode
from companion.images import content, prompts
from companion.life import composer, grooming, money
from companion.world import looks

DAYS = [{'key': 'day', 'label': 'Day', 'kind': 'leisure', 'start': '09:00', 'end': '17:00'},
        {'key': 'chores', 'label': 'Chores', 'kind': 'errand', 'start': '18:00', 'end': '20:00'},
        {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]
# Nothing in her description speaks of hair, nails or skin, so all of it is the app's.
ROSA = {'name': 'Rosa', 'identity': 'She is a 31-year-old florist in Fells Point. Her friends call her bold.',
        'personality': 'Warm and a little restless; she loves hiking and the beach.',
        'location': 'Fells Point, Baltimore', 'home_city': 'baltimore', 'timezone': 'America/New_York'}


@pytest.fixture
def rosa(client, monkeypatch):
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(composer, 'PLAN_SHARE', 0)
    monkeypatch.setattr(composer, 'THREAD_SHARE', 0)
    response = client.post('/api/companion', json={**ROSA, 'schedule': DAYS})
    assert response.status_code == 200, response.text
    return response.json()


def connect(client, write=True):
    return client.app.state.database.connect(write=write)


def ids(client) -> tuple[str, str]:
    with connect(client, False) as connection:
        row = connection.execute('SELECT id, active_timeline_id FROM companions').fetchone()
    return row[0], row[1]


def history(client, through: date) -> list[dict]:
    _, tid = ids(client)
    client.get('/api/life/grooming')
    with connect(client) as connection:
        # Her habits, fixed so the draws are the same whatever her random id: nails usually done, a cut every six weeks.
        connection.execute("UPDATE grooming_state SET profile=json_set(profile, '$.nails', 2, '$.trim_days', 42, "
                           "'$.tier', 1) WHERE timeline_id=?", (tid,))
        grooming.evolve(connection, tid, ROSA, through, client.app.state.database.clock.now())
        return [dict(row) for row in connection.execute(
            'SELECT * FROM grooming_log WHERE timeline_id=? ORDER BY local_date, track', (tid,))]


def test_banks_hold_at_least_a_hundred_specific_entries_and_only_visible_words():
    found = grooming.bank()
    damage = r'\b(?:broken|healed|scars?|cleft|chipped|crooked|ripped|scuffed|torn|split ends|damaged|frayed)\b'
    for category in ('colours', 'cuts', 'nails', 'frames', 'beards'):
        entries = [entry['text'] if isinstance(entry, dict) else entry for entry in found[category]]
        assert len(entries) >= 100 and len(set(entries)) == len(entries), category
        for text in entries:
            assert not re.search(damage, text, re.IGNORECASE), text
            assert content.classify({'prompt': f'A woman with {text}.'}).tier == content.SAFE, text
    assert {entry['length'] for entry in found['cuts']} <= set(range(len(grooming.LENGTHS)))


def test_drawn_hair_is_read_into_parts_and_said_back():
    for text in ('shoulder-length dark brown hair', 'black hair, in a bob', 'wavy blond hair',
                 'dark brown hair, always up in a bun', 'greying brown hair, neatly parted'):
        hair = grooming.parse_hair(text, 'seed')
        assert hair, text
        so_far = {'cut_on': date(2026, 10, 1)}
        said = grooming.hair_text(hair, so_far, date(2026, 10, 20), 60, False)
        assert hair['colour'] in said and 'hair' in said
    for gone in ('a shaved head', 'thinning hair', 'a receding hairline', 'Curly red hair she hates.'):
        assert grooming.parse_hair(gone, 'seed') is None


def test_hair_grows_shows_roots_and_freshly_cut_after_a_trim():
    hair = grooming.parse_hair('chin-length dark brown hair', 'seed') or grooming.parse_hair('dark brown hair, in a bob',
                                                                                             'seed')
    dyed = {'cut_on': date(2026, 1, 1), 'colour': 'copper red', 'colour_on': date(2026, 1, 1)}
    later = grooming.hair_text(hair, dyed, date(2026, 6, 1), 60, True)
    assert later == 'copper red hair past the shoulders with dark brown roots growing in'
    fresh = grooming.hair_text(hair, {**dyed, 'cut_on': date(2026, 5, 29)}, date(2026, 6, 1), 60, True)
    assert fresh.startswith('freshly cut ')
    # The Codex reference sheet follows the colour, not the roots or the growing out.
    assert grooming.hair_text(hair, dyed, date(2026, 6, 1), 60, False) == 'copper red hair, in a bob'


def test_only_looks_the_app_filled_in_change():
    assert grooming.editable(ROSA) == set(grooming.FIELDS)
    wrote = {**ROSA, 'looks': {'hair': 'a silver pixie cut'}, 'appearance': 'Freckles and dark red nails.'}
    assert 'hair' not in grooming.editable(wrote)  # written on the form
    assert 'nails' not in grooming.editable(wrote) and 'feature' not in grooming.editable(wrote)  # Appearance says
    photos = {**ROSA, 'in_photos': 'Long braids and gold hoops.'}
    assert 'hair' not in grooming.editable(photos)  # the In photos line says
    assert 'skin' not in grooming.editable({**ROSA, 'in_photos': 'Curly hair and a deep tan.'})
    # A townsperson's looks copied when they became a companion stay the app's until the user edits one.
    drawn = {'hair': 'black hair, in a bob', 'skin': 'olive'}
    town = {**ROSA, 'looks': {**drawn, 'drawn': drawn}}
    assert {'hair', 'skin'} <= grooming.editable(town)
    edited = {**ROSA, 'looks': {**drawn, 'hair': 'a shaved head', 'drawn': drawn}}
    assert 'hair' not in grooming.editable(edited) and 'skin' in grooming.editable(edited)


def test_changes_come_slowly_and_the_same_in_steps_or_at_once(client, rosa):
    _, tid = ids(client)
    end = date(2027, 10, 1)
    stepped = history(client, end)
    with connect(client) as connection:
        connection.execute('DELETE FROM grooming_log')
        connection.execute('UPDATE grooming_state SET next_period=0')
        now = client.app.state.database.clock.now()
        for step in range(1, 360, 11):
            grooming.evolve(connection, tid, ROSA, date(2026, 10, 5) + timedelta(days=step), now)
        grooming.evolve(connection, tid, ROSA, end, now)
        again = [dict(row) for row in connection.execute(
            'SELECT * FROM grooming_log WHERE timeline_id=? ORDER BY local_date, track', (tid,))]
    key = [(row['local_date'], row['kind'], row['text']) for row in stepped]
    assert key == [(row['local_date'], row['kind'], row['text']) for row in again]
    kinds = [row['kind'] for row in stepped]
    assert kinds.count('trim') + kinds.count('touch-up') >= 3
    bold = [row for row in stepped if row['bold']]
    assert 1 <= len(bold) <= 5  # every few months, not every week
    assert all((date.fromisoformat(b['local_date']) - date.fromisoformat(a['local_date'])).days >= 80
               for a, b in zip(bold, bold[1:]))


def test_the_realism_setting_scales_changes_and_never_stops_them(client, rosa):
    def count(setting: int) -> int:
        _, tid = ids(client)
        client.put('/api/life/settings', json={'looks_realism': setting})
        with connect(client) as connection:
            connection.execute('DELETE FROM grooming_log')
            connection.execute('UPDATE grooming_state SET next_period=0')
        return len(history(client, date(2027, 10, 1)))
    client.get('/api/life/grooming')
    often, real, rarely, never = count(3), count(2), count(1), count(0)
    # Often draws more changes than real life, but a bold cut can save a trim or two, so it is not strictly more.
    assert often >= real * 0.8 and real > rarely > never == 0
    client.put('/api/life/settings', json={'looks_realism': 2})
    history(client, date(2027, 10, 1))
    client.put('/api/life/settings', json={'looks_realism': 0})
    rosa_id, _ = ids(client)
    with connect(client, False) as connection:
        drawn = looks.for_companion(rosa_id, ROSA)
        assert grooming.sheet(connection, rosa_id, ROSA, '2027-09-30') == drawn


def test_easy_life_keeps_bold_colours_out(client, rosa):
    client.get('/api/life/grooming')
    client.put('/api/life/settings', json={'looks_realism': 1})
    mild = {entry['text'] for entry in grooming.bank()['colours'] if entry['tone'] == 'mild'}
    for row in history(client, date(2030, 1, 1)):
        if row['kind'] == 'colour':
            assert set(filter(None, decode(row['change']).values())) <= mild


def test_kept_looks_stay_as_they_are(client, rosa):
    client.get('/api/life/grooming')
    kept = client.put('/api/life/grooming', json={'kept': True}).json()
    assert kept['kept'] is True
    assert [row for row in history(client, date(2027, 10, 1)) if row['local_date'] > kept['today']] == []
    assert client.put('/api/life/grooming', json={'kept': False}).json()['kept'] is False


def test_pictures_and_their_own_prompt_follow_the_looks_of_that_day(client, rosa):
    rows = history(client, date(2027, 10, 1))
    rosa_id, tid = ids(client)
    colour = next((row for row in rows if row['kind'] == 'colour'), None)
    nails = next(row for row in rows if row['kind'] in ('nails', 'nails-home'))
    nail_day = nails['local_date']
    with connect(client, False) as connection:
        companion = {'id': rosa_id, 'active_timeline_id': tid}
        that_day = prompts.sheet_for(companion, ROSA, connection, nail_day)[0]
        month_on = prompts.sheet_for(companion, ROSA, connection,
                                     (date.fromisoformat(nail_day) + timedelta(days=30)).isoformat())[0]
        before = prompts.sheet_for(companion, ROSA)[0]
        assert decode(nails['change'])['nails'] in that_day and decode(nails['change'])['nails'] not in before
        assert 'nails' not in month_on or month_on != that_day
        if colour:
            after = grooming.sheet(connection, rosa_id, ROSA, colour['local_date'], bold_only=True)
            assert after['hair'] != looks.for_companion(rosa_id, ROSA)['hair']
    assert content.classify({'prompt': that_day}).tier == content.SAFE


def test_haircuts_cost_money_and_are_appointments(client, rosa):
    rows = history(client, date(2027, 4, 1))
    _, tid = ids(client)
    paid = [row for row in rows if row['spend']]
    assert paid
    with connect(client, False) as connection:
        start, end = date(2026, 10, 1), date(2027, 4, 1)
        bought = grooming.purchases(connection, tid, start, end)
        listed = grooming.appointments(connection, tid, start, end)
    assert {item['for'] for item in bought} == {'looks'} and all(item['spend'] in money.PURCHASES for item in bought)
    assert listed and {item['title'] for item in listed} <= set(grooming.APPOINTMENTS.values())


def test_an_appointment_takes_a_free_slot_and_a_bold_one_is_posted(client, rosa, monkeypatch):
    monkeypatch.setattr(grooming, 'WEAVE', True)
    client.get('/api/life/grooming')
    _, tid = ids(client)
    with connect(client) as connection:
        connection.execute("INSERT INTO grooming_log (id, timeline_id, period, track, local_date, kind, change, text, "
                           "spend, bold, created_at) VALUES ('g1', ?, 99, 'bold', '2026-10-06', 'colour', ?, "
                           "'dyed her hair copper red', '$$', 1, '2026-10-05')",
                           (tid, json.dumps({'colour': 'copper red'})))
    reconcile(client)
    with connect(client, False) as connection:
        told = [decode(row[0]) for row in connection.execute(
            "SELECT entry FROM life_agenda WHERE subject='companion' AND json_extract(entry, '$.looks.change')='g1'")]
        posted = connection.execute(
            "SELECT COUNT(*) FROM life_agenda WHERE json_extract(entry, '$.looks.bold')=1").fetchone()[0]
    assert len(told) == 1 and told[0]['activity'] == 'salon'
    assert told[0]['summary'] == 'Rosa dyed her hair copper red.' and told[0]['post'] in grooming.bank()['posts']['colour']
    assert posted == 1


def test_the_character_page_says_it_in_words(client, rosa):
    history(client, date(2026, 10, 6))
    view = client.get('/api/life/grooming').json()
    assert view['level'] == 2 and view['kept'] is False and view['numbers'] is None
    assert view['lines'][0]['label'] == 'Hair' and 'Last cut' in view['lines'][0]['text']
    client.put('/api/settings', json={'show_home_meters': True})
    shown = client.get('/api/life/grooming').json()
    assert any(item['label'] == 'Days since a haircut' for item in shown['numbers'])


def test_a_fork_keeps_the_looks_history_as_it_was(client, rosa):
    history(client, date(2027, 4, 1))
    _, tid = ids(client)
    with connect(client) as connection:
        connection.execute("INSERT INTO timelines (id, companion_id, status, created_at) "
                           "SELECT 'fork', companion_id, 'frozen', created_at FROM timelines WHERE id=?", (tid,))
        grooming.copy(connection, tid, 'fork', '2026-12-15T12:00:00Z', {})
        latest = connection.execute("SELECT MAX(local_date) FROM grooming_log WHERE timeline_id='fork'").fetchone()[0]
        parent = connection.execute("SELECT COUNT(*) FROM grooming_log WHERE timeline_id=? AND local_date<='2026-12-15'",
                                    (tid,)).fetchone()[0]
        forked = connection.execute("SELECT COUNT(*) FROM grooming_log WHERE timeline_id='fork'").fetchone()[0]
    assert forked == parent and (latest is None or latest <= '2026-12-15')
