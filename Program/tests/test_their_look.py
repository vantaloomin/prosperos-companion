"""Their look in chat (Hit List #80, companion/their_look.py): a seeded colour family and name font for each
companion, the Realism slider, the Character page's overrides, mood only with Moods shown, the muted lines in their
chat, and group chats that never give two members near-identical colours."""
import sqlite3
from datetime import timedelta

import pytest

from companion import moods, their_look
from companion.characters import require_current
from tests.conftest import set_life


def look(client):
    response = client.get('/api/their-look')
    assert response.status_code == 200, response.text
    return response.json()


def change(client, **values):
    response = client.put('/api/their-look', json=values)
    assert response.status_code == 200, response.text
    return response.json()


def with_connection(client, work):
    database = client.app.state.database
    with database.connect(write=True) as connection:
        return work(connection, require_current(connection), database.clock.now())


# The bank -------------------------------------------------------------------------------------------------------

def test_the_bank_is_whole():
    bank = their_look.bank()
    assert len(bank['families']) >= 8 and len(set(their_look.family_ids())) == len(bank['families'])
    assert set(their_look.font_ids()) == {'serif', 'sans', 'rounded', 'typewriter', 'handwritten'}
    traits = {'social', 'warmth', 'order', 'curiosity', 'stress'}
    eras = {'modern', 'fantasy', 'future', 'jazz-age', 'steampunk', 'medieval', 'victorian', 'frontier'}
    for item in bank['families'] + bank['fonts']:
        for key in item['leans']:
            assert key in eras | {'jobs', 'young', 'older'} or key.split(':')[0] in traits, (item['id'], key)
    for item in bank['families']:
        assert 0 <= item['hue'] < 360 and 20 <= item['sat'] <= 80


# The taste the app picks ------------------------------------------------------------------------------------

def test_a_punk_barista_and_a_retired_librarian_get_different_tastes(client):
    client.post('/api/companion', json={'name': 'Jett Vale', 'identity': '23, a punk barista who plays bass in a band.',
                                        'personality': 'Loud, messy, always late.', 'timezone': 'America/New_York'})
    punk = look(client)['picked']
    assert punk['family'] in ('magenta', 'teal', 'rust', 'violet')
    assert punk['font'] in ('typewriter', 'handwritten', 'rounded')


def test_a_retired_librarian_leans_to_moss_and_a_classic_serif(client):
    client.post('/api/companion', json={'name': 'Agnes Holt', 'identity': '68, a retired librarian and keen gardener.',
                                        'personality': 'Quiet, tidy, reserved.', 'timezone': 'Europe/London'})
    picked = look(client)['picked']
    assert picked['family'] == 'moss'
    assert picked['font'] in ('serif', 'handwritten')


def test_the_same_companion_always_gets_the_same_look(client, companion):
    first = look(client)
    assert first['look'] == look(client)['look']
    assert first['look']['family'] in their_look.family_ids() and first['look']['font'] in their_look.font_ids()
    assert first['changes'] == []


# The slider and the switches -------------------------------------------------------------------------------

def test_off_steady_and_the_users_own_colours(client, companion):
    assert look(client)['level'] == 2
    set_life(client, their_look=0)
    assert look(client)['look'] is None
    set_life(client, their_look=1)
    steady = look(client)['look']
    assert steady['shade'] == 0 and steady['mood'] is None
    assert steady['family'] == look(client)['picked']['family']
    set_life(client, their_look=2)
    assert change(client, use_mine=True)['look'] is None
    assert change(client, use_mine=False)['look'] is not None
    client.put('/api/settings', json={'keep_my_colours': True})
    assert look(client)['look'] is None and look(client)['everywhere_off'] is True


def test_the_user_can_pick_their_colour_and_font_and_hand_them_back(client, companion):
    picked = look(client)['picked']
    other = next(family for family in their_look.family_ids() if family != picked['family'])
    changed = change(client, family=other, font='typewriter')
    assert changed['look']['family'] == other and changed['look']['font'] == 'typewriter'
    assert changed['own'] == {'family': other, 'font': 'typewriter'}
    assert changed['changes'] == []  # What the user changes leaves no line.
    back = change(client, family='', font='')
    assert back['own'] == {'family': None, 'font': None}
    assert back['changes'] == []
    response = client.put('/api/their-look', json={'family': 'chartreuse'})
    assert response.status_code == 422


# Mood, only with Moods shown ------------------------------------------------------------------------------------

def feel(client, feeling, intensity):
    with_connection(client, lambda connection, companion, now: moods.save(
        connection, f"companion:{companion['id']}", feeling, intensity, None, 'a test', now))


def test_mood_moves_the_shade_only_when_moods_are_shown(client, companion):
    feel(client, 'sad', 2)
    assert look(client)['look']['mood'] is None  # Hidden values stay hidden.
    client.put('/api/settings', json={'show_moods': True})
    assert look(client)['look']['mood'] == 'muted'
    feel(client, 'happy', 1)
    assert look(client)['look']['mood'] is None  # True to life needs a strong mood.
    set_life(client, their_look=3)
    assert look(client)['look']['mood'] == 'bright'
    change(client, steady=True)
    assert look(client)['look']['mood'] is None


def test_mood_moves_the_shade_at_most_twice_a_day(client, companion):
    client.put('/api/settings', json={'show_moods': True})
    look(client)
    shades = []
    for feeling in ('sad', 'annoyed', 'anxious', 'happy'):
        feel(client, feeling, 3)
        shades.append(look(client)['look']['mood'])
    assert shades == ['muted', 'deep', 'deep', 'deep']
    assert len(look(client)['changes']) == 2


# Changes the app makes leave a line ---------------------------------------------------------------------------

def test_a_new_season_can_change_the_shade_and_leaves_a_line(client, companion, clock, monkeypatch):
    monkeypatch.setattr(their_look, 'drift', lambda companion, today: 2 if today.month >= 12 else 0)
    assert look(client)['look']['shade'] == 0
    clock.advance(timedelta(days=60))
    after = look(client)
    assert after['look']['shade'] == 2
    assert [line['text'] for line in after['changes']] == ['Mira changed their colours.']


def test_a_change_of_taste_names_the_new_colour(client, companion, monkeypatch):
    before = look(client)['look']
    other = next(family for family in their_look.family_ids() if family != before['family'])
    monkeypatch.setattr(their_look, 'family_for', lambda companion, picks, level, today: (other, 1))
    lines = look(client)['changes']
    assert lines[-1]['text'] == f'Mira changed their colours to {their_look.label(other)}.'


def test_changes_of_taste_are_rare_and_seeded(client, companion):
    companion_row = with_connection(client, lambda connection, companion, now: companion)
    picks = list(their_look.family_ids())
    from datetime import date
    seasons = [their_look.family_for({**companion_row, 'created_at': '2016-01-01T00:00:00Z'}, picks, level,
                                     date(2026, 10, 5)) for level in (1, 2, 3)]
    assert seasons[0] == (picks[0], 0)  # Steady never changes.
    assert seasons[1] == their_look.family_for({**companion_row, 'created_at': '2016-01-01T00:00:00Z'}, picks, 2,
                                               date(2026, 10, 5))


# Group chats -----------------------------------------------------------------------------------------------------

def test_two_members_never_get_near_identical_colours(client, companion, monkeypatch):
    member = with_connection(client, lambda connection, companion, now: companion)
    other = {**member, 'id': 'someone-else'}
    monkeypatch.setattr(their_look, 'worked_out', lambda connection, companion, now, with_mood=True: {
        'family': 'slate', 'font': 'sans', 'shade': 0, 'mood': None, 'level': 2})
    monkeypatch.setattr(their_look, 'taste', lambda connection, companion, today: {
        'families': ['slate', 'cobalt', 'rust'], 'font': 'sans'})
    found = with_connection(client, lambda connection, companion, now: their_look.group(connection, [member, other], now))
    assert found[member['id']]['family'] == 'slate'
    assert found['someone-else']['family'] == 'rust'  # Cobalt is too near slate.
    assert their_look.near('slate', 'cobalt') and not their_look.near('slate', 'rust')


def test_the_group_endpoint_reads_each_member(client, companion):
    response = client.get('/api/their-look/group', params={'ids': f"{companion['id']},nobody"})
    assert response.status_code == 200
    assert list(response.json()['looks']) == [companion['id']]


# Older worlds -----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize(('drama', 'expected'), [(0, 1), (1, 2), (3, 3)])
def test_an_older_world_gets_their_look_by_its_preset(tmp_path, drama, expected):
    from companion.database import add_columns, initialize
    connection = sqlite3.connect(tmp_path / 'old.sqlite3')
    initialize(connection, '2026-10-01T00:00:00Z')
    connection.execute('ALTER TABLE life_settings DROP COLUMN their_look')
    connection.execute('UPDATE life_settings SET drama=?', (drama,))
    add_columns(connection)
    assert connection.execute('SELECT their_look FROM life_settings').fetchone()[0] == expected
    connection.close()
