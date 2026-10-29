"""Observer mode (companion/observer.py, companion/life/narrator.py): just watch the world go on."""
import asyncio
import json
import re
from datetime import date, timedelta

import pytest
from conftest import reconcile, send, set_life, show
from test_expecting import likeliest, to  # noqa: F401 - likeliest is a fixture
from test_loss import advance, dies, losses, make, person, switch
from test_our_child import born

from companion import moods, observer
from companion.characters import require_current
from companion.clock import stamp
from companion.life import big_days, deck, narrator, openers, our_child
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
    assert kinds == {'companion', 'circle', 'townsperson'}  # Their people in town and a few lively townsfolk too.
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
        assert not inner and not thoughts and not [line for line in found if line['kind'] in ('mood', 'dream')]
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


def test_a_line_naming_someone_in_the_family_is_held_to_the_stricter_check(client, companion):
    close = narrator.item('d', '2026-10-05T22:00:00Z', 'day', 'Mira and Theo had sex after Ivy fell asleep.')
    plain = narrator.item('e', '2026-10-05T12:00:00Z', 'day', 'Mira took Ivy to the park.')
    names = re.compile(r'\bIvy\b')
    assert narrator.told(close, 'Mira', 'she', True, names) is None
    assert narrator.told(plain, 'Mira', 'she', True, names) == plain


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


def test_true_to_life_only_follows_a_line_that_stirred_something():
    assert narrator.thought_after(2, True, 'k', None, 'Mira') is None  # Nothing to say: no filler.
    assert narrator.thought_after(2, True, 'k', 'good', 'Mira')
    assert narrator.thought_after(2, False, 'k', 'good', 'Mira') is None
    assert narrator.thought_after(3, False, 'k', None, 'Mira')


def test_a_townsperson_routine_does_not_read_word_for_word_each_day(client):
    client.put('/api/observer', json={'watching': True})
    found = [line['text'] for line in lines(feed(client)) if line['id'].startswith('where:')]
    assert found and len(set(found)) > len(found) // 2
    for day, before in zip(feed(client)['days'], feed(client)['days'][1:]):
        assert not {line['text'] for line in day['items']} & {line['text'] for line in before['items']}


@pytest.mark.usefixtures('likeliest')
def test_their_childs_milestones_are_told_on_the_day(client, clock, monkeypatch):
    _row, child = born(client, clock, monkeypatch)
    with client.app.state.database.connect() as connection:
        planned = our_child.milestones(connection, require_current(connection), child)
    smile = next(found for found in planned if found['key'] == 'smile')
    to(client, clock, smile['on'])
    assert client.put('/api/observer', json={'watching': True}).status_code == 200
    first = child['name'].split()[0]
    told = [line for line in lines(feed(client)) if line['kind'] == 'family']
    assert [line['text'] for line in told] == [f'{first} smiled for the first time.']



def test_the_narrator_reads_their_pronouns_from_the_description():
    assert narrator.companion_pronouns({'name': 'Dana', 'identity': '34. Works as an ER nurse. She/her.'}) == 'she/her'
    assert narrator.companion_pronouns({'name': 'Sam', 'pronouns': 'he/him'}) == 'he/him'
    assert narrator.companion_pronouns({'name': 'Rue'}) == 'they/them'


def test_a_townspersons_day_is_told_in_the_past_with_their_own_pronouns():
    assert narrator.doing_text({'doing': 'at work (biomedical researcher)'}) == 'at work as a biomedical researcher'
    assert narrator.doing_text({'doing': 'at work (archivist)'}) == 'at work as an archivist'
    place = {'name': 'Remington'}
    assert narrator.doing_text({'doing': 'out front, chatting with whoever passes', 'place': place}) == \
        'out front, chatting with whoever passed at Remington'
    assert narrator.doing_text({'doing': 'at their usual spot at Remington', 'place': place}, 'she/her') == \
        'at her usual spot at Remington'


def test_a_death_in_their_family_is_told_on_the_day(client, clock, monkeypatch):
    monkeypatch.setattr(big_days, 'ACTIVE', True)
    make(client)
    switch(client)
    dad = person(client, 'dad')
    dies(monkeypatch, dad['id'])
    advance(client, clock)
    row = next(row for row in losses(client) if row['person_id'] == dad['id'])
    assert client.put('/api/observer', json={'watching': True}).status_code == 200
    clock.advance(date.fromisoformat(row['died_on']) - clock.now().date() + timedelta(hours=14))
    advance(client, clock)
    told = [line for line in lines(feed(client)) if line['kind'] == 'loss']
    assert [line['text'] for line in told] == [f"Mira's dad, {dad['name'].split()[0]}, died."]
    assert not told[0].get('inner')  # No inner voice bank is written for grief.


def test_a_line_set_later_today_is_told_as_of_now(clock):
    now = clock.now()
    later = {'key': 'moment:x', 'at': stamp(now + timedelta(hours=3)), 'text': 'A jar lid would not open.'}
    earlier = {**later, 'at': stamp(now - timedelta(hours=3))}
    assert narrator.told_by(later, now)['at'] == stamp(now - timedelta(seconds=1))  # Just under how they feel now.
    assert narrator.told_by(earlier, now) == earlier


def test_the_day_of_a_death_is_told_quietly_from_then_on():
    def line(key, hour, kind, inner=None):
        return {'id': key, 'at': f'2026-10-20T{hour:02d}:00:00.000000+00:00', 'kind': kind, 'text': key, 'inner': inner,
                'numbers': []}
    lines = [line('morning', 13, 'moment', 'Mira is still smiling about it.'), line('died', 16, 'loss'),
             line('joke', 16, 'moment', 'Mira wants to tell someone.'), line('plan', 18, 'thought'), line('museum', 17, 'day', 'Mira grins.'),
             line('next day', 16, 'day', 'Mira grins.') | {'at': '2026-10-21T16:00:00.000000+00:00'}]
    told = {found['id']: found for found in narrator.hushed(lines, 'America/New_York')}
    assert list(told) == ['morning', 'died', 'museum', 'next day']
    assert told['museum']['inner'] is None and told['morning']['inner'] and told['next day']['inner']



def test_the_companions_people_in_town_can_be_watched_too(client, companion, watching):
    circle = [choice for choice in watching['choices'] if choice['kind'] == 'circle']
    assert circle, watching['choices']  # Their mom, their friends: everyone in the circle who lives in town.
    assert all(choice['owner'] == 'Mira' and choice['line'].startswith("Mira's ") for choice in circle)
    found = client.put('/api/observer', json={'focus': circle[0]['key']}).json()
    assert found['focus']['kind'] == 'circle' and found['focus']['why'] == 'Lives in town.'
    told = feed(client)
    assert told['focus']['key'] == circle[0]['key'] and lines(told)
    first = circle[0]['name'].split()[0]
    assert all(first in line['text'] for line in lines(told) if line['kind'] == 'day')


def test_townsfolk_say_why_they_are_offered(client, companion, watching):
    town = [choice for choice in watching['choices'] if choice['kind'] == 'townsperson']
    assert town and all(choice['source'] in ('met', 'busy') and choice['why'] for choice in town)
    busy = [choice for choice in town if choice['source'] == 'busy']
    assert busy and all(choice['why'] == f"Nobody you know has met {choice['name'].split()[0]} yet. Picked for a busy week."
                        for choice in busy)
