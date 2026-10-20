"""Observer mode (companion/observer.py, companion/life/narrator.py): just watch the world go on."""
import asyncio
import json
import re
from datetime import timedelta

import pytest
from conftest import reconcile, send, set_life, show

from companion import moods, observer
from companion.characters import require_current
from companion.life import big_days, deck, narrator, openers
from companion.providers.chat import Chunk


@pytest.fixture
def watching(client, companion, clock, monkeypatch):
    monkeypatch.setattr(deck, 'ACTIVE', True)
    for _ in range(3):
        clock.advance(timedelta(hours=20))
        reconcile(client)
    response = client.put('/api/observer', json={'watching': True})
    assert response.status_code == 200, response.text
    return response.json()


def feed(client, **params) -> dict:
    response = client.get('/api/observer/feed', params=params)
    assert response.status_code == 200, response.text
    return response.json()


def lines(found: dict) -> list[dict]:
    return [line for day in found['days'] for line in day['items']]


def test_the_app_picks_who_to_watch_and_their_days_read_as_a_narrator_tells_them(client, companion, watching):
    assert watching['watching'] and watching['focus']['name'] == 'Mira' and watching['focus']['kind'] == 'companion'
    kinds = {choice['kind'] for choice in watching['choices']}
    assert kinds == {'companion', 'townsperson'}  # A few lively townsfolk are offered too.
    found = feed(client)
    assert found['focus']['key'] == f"companion:{companion['id']}"
    days = [day['date'] for day in found['days']]
    assert days == sorted(days, reverse=True) and lines(found)
    assert all('Mira' in line['text'] for line in lines(found) if line['kind'] in ('day', 'moment'))
    assert found == feed(client)  # Seeded: the same days read the same way.


def test_without_anyone_to_talk_to_a_lively_townsperson_is_watched(client):
    response = client.put('/api/observer', json={'watching': True})
    assert response.status_code == 200, response.text
    focus = response.json()['focus']
    assert focus['kind'] == 'townsperson' and focus['key'].startswith('town:')
    found = feed(client)
    assert any(line['text'].startswith('In the ') for line in lines(found))
    first = focus['name'].split()[0]
    assert all(first in line['text'] for line in lines(found) if line['kind'] in ('day', 'thought'))


def test_switching_focus_shows_their_side(client, watching):
    town = next(choice for choice in watching['choices'] if choice['kind'] == 'townsperson')
    response = client.put('/api/observer', json={'focus': town['key']})
    assert response.status_code == 200, response.text
    assert response.json()['focus']['key'] == town['key']
    assert feed(client)['focus']['name'] == town['name']
    assert client.put('/api/observer', json={'focus': 'town:nowhere:nothing:0'}).status_code == 404


def test_the_persona_sits_out_while_watching(client, companion, watching):
    database = client.app.state.database
    with database.connect() as connection:
        found = require_current(connection)
        life = dict(connection.execute('SELECT * FROM life_settings WHERE id=1').fetchone())
        assert openers.held(connection, found, life, database.clock.now()) == 'watching'
        row = {'details': {'local': True}, 'kind': 'birthday', 'local_date': '2026-10-20', 'timeline_id': 'x', 'id': 'y'}
        assert big_days.invitable(connection, found, row) is False
    swiped = client.post('/api/dating/swipes', json={'key': 'town:baltimore:anywhere:0', 'like': True})
    assert swiped.status_code == 409 and 'watching' in swiped.text
    assert client.get('/api/dating').json()['watching'] is True


def test_writing_to_them_steps_back_in(client, connected, watching):
    send(client, 'hey, how was your week?', 'step-in-1')
    state = client.get('/api/observer').json()
    assert state['watching'] is False and state['focus']['name'] == 'Mira'  # The focus waits for the next watch.
    with client.app.state.database.connect() as connection:
        assert observer.watched_since(connection, '2026-10-01T00:00:00Z')


@pytest.mark.parametrize('voice', [0, 1, 2, 3])
def test_inner_voice_sets_how_much_of_their_mind_is_told(client, watching, voice):
    set_life(client, inner_voice=voice)
    found = lines(feed(client))
    inner = [line for line in found if line['inner']]
    thoughts = [line for line in found if line['kind'] == 'thought']
    if voice == 0:
        assert not inner and not thoughts
    if voice == 3:
        assert all(line['inner'] for line in found if line['kind'] == 'day')
    if voice < 3:
        assert not any(line['id'].startswith('wander:') for line in thoughts)


def test_feelings_come_through_in_words_and_numbers_only_with_hidden_values_shown(client, companion, watching):
    database = client.app.state.database
    with database.connect(write=True) as connection:
        moods.save(connection, f"companion:{companion['id']}", 'happy', 2, None, 'test', database.clock.now())
    mood = next(line for line in lines(feed(client)) if line['kind'] == 'mood')
    assert mood['text'] == 'Mira is properly happy.' and mood['numbers'] == []
    show(client, show_moods=True)
    mood = next(line for line in lines(feed(client)) if line['kind'] == 'mood')
    assert mood['numbers'] == ['happy 2 of 3']
    set_life(client, inner_voice=1)
    assert not [line for line in lines(feed(client)) if line['kind'] == 'mood']


def test_intimate_lines_are_never_told_and_fail_closed(client, companion):
    plain = narrator.item('a', '2026-10-05T12:00:00Z', 'day', 'Mira went for a walk.')
    close = narrator.item('b', '2026-10-05T22:00:00Z', 'day', 'Mira and Theo had sex after dinner.')
    young = narrator.item('c', '2026-10-05T22:00:00Z', 'day', 'Mira and the teen had sex.')
    assert narrator.told(plain, 'Mira', 'she', False) == plain
    assert narrator.told(close, 'Mira', 'she', False) is None
    private = narrator.told(close, 'Mira', 'she', True)
    assert private['kind'] == 'private' and private['text'] == 'Mira kept the rest of that to herself.'
    assert narrator.told(young, 'Mira', 'she', True) is None
    assert narrator.told({**plain, 'text': None}, 'Mira', 'she', True) is None  # Can't be checked: not told.


def test_the_inner_voice_banks():
    found = narrator.bank()
    for category in ('good', 'bad', 'mixed', 'calm', 'wander', 'goal'):
        lines_ = found[category]
        assert len(lines_) >= 100 and len(set(lines_)) == len(lines_), category
        for line in lines_:
            assert chr(0x2014) not in line and ('{first}' in line or category in ('good', 'bad', 'mixed', 'calm')), line
            # Pronoun-free, so any pronoun reads right.
            assert not re.search(r"\b(?:she|he|her|his|him|they|their|them|themselves)\b",
                                 line.replace('{goal}', ''), re.IGNORECASE), line
            assert line.format(first='Mira', goal='learn to swim')
            assert narrator.reads(line.format(first='Mira', goal='learn to swim')) == set(), line


def test_a_new_world_can_start_just_watching(client):
    response = client.post('/api/worlds', json={'city_id': 'baltimore', 'watch': True})
    assert response.status_code == 200, response.text
    assert response.json()['watching'] is True
    assert client.get('/api/worlds').json()['world']['watching'] is False


def test_the_watched_townsperson_can_be_become_without_being_met(client, watching):
    town = next(choice for choice in watching['choices'] if choice['kind'] == 'townsperson')
    client.put('/api/observer', json={'focus': town['key']})
    response = client.post('/api/worlds/become', json={'key': town['key']})
    assert response.status_code == 200, response.text
    assert response.json()['persona']['name'] == town['name']


def entries(provider) -> list[dict]:
    return [request for request in provider.requests if request['system'].startswith('Write the day')]


def test_the_model_writes_yesterday_in_a_few_lines_in_the_background(client, connected, watching, provider, clock):
    provider.replies = [[Chunk('Mira kept busy all day and took the long way home.'), Chunk('', 'stop')]]
    asyncio.run(client.app.state.life.quietly_narrate())
    assert len(entries(provider)) == 1
    sent = entries(provider)[0]['messages'][-1]['content']
    assert 'Mira' in sent and 'the user' not in sent
    assert 'call Mira they/them' in entries(provider)[0]['system']  # No pronouns on the sheet: they/them.
    yesterday = next(day for day in feed(client)['days'] if day['entry'])
    assert yesterday['entry'] == 'Mira kept busy all day and took the long way home.'
    asyncio.run(client.app.state.life.quietly_narrate())
    assert len(entries(provider)) == 1  # Once a day.


def test_no_entry_unless_watching_with_model_phrasing(client, connected, watching, provider):
    set_life(client, phrase_with_model=False)
    asyncio.run(client.app.state.life.quietly_narrate())
    set_life(client, phrase_with_model=True)
    client.put('/api/observer', json={'watching': False})
    asyncio.run(client.app.state.life.quietly_narrate())
    assert entries(provider) == []


def test_an_unusable_entry_is_dropped(client):
    assert narrator.usable('She had a good day.', 'Mira Costa') is None
    assert narrator.usable('Mira left at 17:30.', 'Mira Costa') is None
    assert narrator.usable('Mira and Theo had sex.', 'Mira Costa') is None
    assert narrator.usable('Mira had a good day.', 'Mira Costa') == 'Mira had a good day.'
    assert json.dumps(narrator.public({'key': 'k', 'kind': 'companion', 'name': 'Mira', 'companion': {}}))


def test_a_thought_already_told_or_kept_all_week_shows_once():
    told = [narrator.item('event:1', '2026-10-18T13:00:00Z', 'day', 'Mira had something come up (the laundry). Mira ran errands.')]
    thoughts = [narrator.item(f'thought:{day}', f'2026-10-{day}T21:00:00Z', 'thought', text) for day, text in
                ((18, 'Mira had something come up (the laundry).'), (19, 'Money is tight.'), (20, 'Money is tight.'))]
    assert [line['id'] for line in narrator.fresh(thoughts, told)] == ['thought:20']
