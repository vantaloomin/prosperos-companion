"""What a companion says about their people sticks (Hit List #103, companion/life/said_events.py): "my mom just retired"
in chat changes her record and her diary, unless anything about it is unclear, the user set it, or a recent event
says otherwise; and it is taken back with Undo, the fact's Remove, or the reply leaving the timeline."""
import json

import pytest
from conftest import send

from companion.characters import require_current
from companion.database import decode, encode
from companion.life import agenda, circle, circle_love, families, happenings, said_events
from companion.providers.chat import Chunk

WORKDAY = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00', 'days': [0, 1, 2, 3, 4]},
           {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]
PEOPLE = [{'id': 'mom', 'name': 'Lestara', 'role': 'mom', 'details': json.dumps({'pronouns': 'she/her'})},
          {'id': 'sis', 'name': 'Mara', 'role': 'sister', 'details': json.dumps({'pronouns': 'she/her'})},
          {'id': 'aunt', 'name': 'Dot', 'role': 'aunt', 'details': json.dumps({'pronouns': 'she/her'})},
          {'id': 'aunt2', 'name': 'Bea', 'role': 'aunt', 'details': json.dumps({'pronouns': 'she/her'})},
          {'id': 'kai', 'name': 'Kaito', 'role': 'close friend', 'details': json.dumps({'pronouns': 'he/him'})}]


def found(text, lowercase=False):
    return [(person, kind) for person, _area, kind, _given, _sentence in said_events.read(text, PEOPLE, lowercase)]


def test_every_kind_has_a_bank_of_at_least_a_hundred_phrases():
    for area, kinds in said_events.bank().items():
        assert sum(len(texts) for texts in kinds.values()) >= 100, area
        assert set(kinds) <= set(said_events.AREAS[area]) | {'moved'}, area
        for kind in kinds:
            assert kind in happenings.EFFECTS, kind


@pytest.mark.parametrize('text, expected', [
    ('my mom just retired!', [('mom', 'retired')]),
    ("Mara's been promoted at last.", [('sis', 'promoted')]),
    ('Kaito got laid off today.', [('kai', 'laid_off')]),
    ('my sister is dating a guy named Ren', [('sis', 'picked')]),
    ("My sister's engaged!!", [('sis', 'engaged')]),
    ('mara and her boyfriend broke up', [('sis', 'broke_up')]),
    ('my mom moved across town', [('mom', 'moved')]),
    ('my friend Kaito is in the hospital', [('kai', 'in_hospital')]),
    ('my sister had a baby girl named Lily', [('sis', 'had_baby')]),
    ("my sister's pregnant", [('sis', 'expecting')]),
])
def test_plain_news_about_one_person_is_found(text, expected):
    assert found(text) == expected


@pytest.mark.parametrize('text', [
    'my mom might retire next year', 'my mom is thinking about retiring', 'Did you know my mom retired?',
    'my mom retired years ago', "my mom isn't retired", 'my mom is basically retired lol', 'my aunt got married',
    'my mom and dad got married', 'my parents got married', 'my brother got engaged', 'my sister got a job interview',
    'I got promoted and my mom is proud', 'my mom is sick of my sister', 'if my sister got engaged i would scream',
    'my sister said Kaito got engaged', '"my mom retired," she said in the movie', 'my friend got engaged',
])
def test_anything_unclear_changes_nothing(text):
    assert found(text) == []


def test_lowercase_texting_names_people_in_lowercase():
    assert found('omg kaito got engaged', lowercase=True) == [('kai', 'engaged')]


def test_what_comes_with_the_news():
    (_who, _area, _kind, given, _sentence), = said_events.read('my sister is engaged to Ren Ito', PEOPLE)
    assert given['partner_name'] == 'Ren Ito'
    (_who, _area, _kind, given, _sentence), = said_events.read('my sister had a baby boy named Leo', PEOPLE)
    assert given == {'child': 'Leo', 'pronouns': 'he/him'}


# In the app ---------------------------------------------------------------------------------------------------------

@pytest.fixture
def world(client, provider):
    response = client.post('/api/companion', json={'name': 'Sett', 'timezone': 'UTC', 'schedule': WORKDAY,
                                                     'location': 'Fells Point, Baltimore', 'home_city': 'baltimore',
                                                     'identity': 'Sett works as an accountant.'})
    assert response.status_code == 200, response.text
    response = client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                                   'api_key': 'secret-key'})
    assert response.status_code == 200, response.text
    with client.app.state.database.connect(write=True) as connection:
        circle.ensure(connection, require_current(connection), client.app.state.life.world,
                      client.app.state.database.clock.now())
    client.fake = provider
    return client


def says(client, text, client_id):
    client.fake.replies.append([Chunk(text), Chunk('', 'stop')])
    return send(client, 'what is new?', client_id)


def person(client, role, **details):
    """A circle person in `role` with a job and these details, the app's own pick in everything else."""
    with client.app.state.database.connect(write=True) as connection:
        companion = require_current(connection)
        people = circle.people(connection, companion['active_timeline_id'])
        row = next((row for row in people if row['role'] == role), people[-1])
        others = [other for other in people if other['id'] != row['id'] and other['role'] == role]
        for other in others:
            connection.execute("UPDATE circle_people SET role='neighbor' WHERE id=?", (other['id'],))
        pronouns = 'she/her' if role in ('mom', 'sister') else 'he/him'
        found_ = {key: value for key, value in (decode(row['details']) or {}).items()
                  if key not in ('works_with_companion', 'edited', 'partner', 'married', 'local')}
        found_ |= {'pronouns': pronouns, 'career': 'Nurse', 'employer': 'Harbor General', 'age': 60} | details
        connection.execute('UPDATE circle_people SET role=?, details=? WHERE id=?', (role, encode(found_), row['id']))
        return {**row, 'role': role}


def record_of(client, person_id):
    with client.app.state.database.connect() as connection:
        row = dict(connection.execute('SELECT * FROM circle_people WHERE id=?', (person_id,)).fetchone())
        return row, decode(row['details'])


def diary_lines(client, person_id):
    return [entry['entry'] for entry in client.get(f'/api/life/circle/{person_id}/diary').json()
            if entry['entry'].get('happening')]


def test_a_retirement_said_in_chat_changes_her_record_and_diary(world, provider):
    mom = person(world, 'mom')
    says(world, 'my mom just retired! she is already bored', 'client-said-01')
    assert len(provider.requests) == 1  # No model call of its own.
    _row, details = record_of(world, mom['id'])
    assert details['career'] == 'Retired' and details['employer'] == '' and details['retired_on']
    line, = diary_lines(world, mom['id'])
    assert line['summary'] == f"{mom['name']} retired." and line['said']['statement'].startswith('my mom just retired')
    fact, = [fact for fact in world.get('/api/self-facts').json()['facts'] if fact['category'] == 'news']
    assert fact['label'] == 'Their people' and fact['value'] == f"{mom['name']} retired."
    prompt = world.get('/api/context/preview').json()['prompt']
    assert 'Their people:' not in prompt and 'Retired' in prompt


def test_a_retirement_that_does_not_fit_their_age_does_not_stick(world):
    mom = person(world, 'mom', age=28)
    says(world, 'my mom just retired!', 'client-said-16')
    assert record_of(world, mom['id'])[1]['career'] == 'Nurse' and diary_lines(world, mom['id']) == []


def test_undo_puts_the_record_back_and_the_line_leaves(world):
    mom = person(world, 'mom')
    before, _details = record_of(world, mom['id'])
    says(world, 'my mom just retired!', 'client-said-02')
    line, = diary_lines(world, mom['id'])
    response = world.post(f"/api/life/said/{line['said']['fact_id']}/undo")
    assert response.status_code == 200, response.text
    after, _details = record_of(world, mom['id'])
    assert (after['details'], after['career'], after['schedule']) == (before['details'], before['career'],
                                                                      before['schedule'])
    assert diary_lines(world, mom['id']) == []
    assert not [fact for fact in world.get('/api/self-facts').json()['facts'] if fact['category'] == 'news']


def test_removing_the_fact_takes_the_change_back(world):
    mom = person(world, 'mom')
    says(world, 'my mom just retired!', 'client-said-03')
    fact, = [fact for fact in world.get('/api/self-facts').json()['facts'] if fact['category'] == 'news']
    world.post(f"/api/self-facts/{fact['id']}/remove")
    assert record_of(world, mom['id'])[1]['career'] == 'Nurse'


def test_a_replaced_reply_takes_its_news_with_it(world):
    mom = person(world, 'mom')
    sent = says(world, 'my mom just retired!', 'client-said-04')
    world.fake.replies.append([Chunk('nothing much, you?'), Chunk('', 'stop')])
    response = world.post(f"/api/conversation/messages/{sent['message']['id']}/alternatives")
    assert response.status_code == 200, response.text
    assert record_of(world, mom['id'])[1]['career'] == 'Nurse'
    assert diary_lines(world, mom['id']) == []


def test_a_job_the_user_set_wins_over_chat(world):
    mom = person(world, 'mom', edited=['job'])
    says(world, 'my mom just retired!', 'client-said-05')
    assert record_of(world, mom['id'])[1]['career'] == 'Nurse' and diary_lines(world, mom['id']) == []


def test_a_recent_event_about_the_same_part_of_their_life_wins(world):
    mom = person(world, 'mom')
    with world.app.state.database.connect(write=True) as connection:
        companion = require_current(connection)
        today = world.app.state.database.clock.now().date()
        happenings.record(connection, companion, subject=mom['id'], source='storyline:x:0', kind='promoted',
                          day=today.isoformat(), at='09:00', now=world.app.state.database.clock.now())
    says(world, 'my mom got laid off', 'client-said-06')
    assert record_of(world, mom['id'])[1]['career'] == 'Nurse'
    assert [line['happening'] for line in diary_lines(world, mom['id'])] == ['promoted']


def test_an_engagement_names_the_partner_they_said(world):
    sister = person(world, 'sister')
    says(world, "My sister's engaged to Ren Ito!", 'client-said-07')
    with world.app.state.database.connect() as connection:
        row = dict(connection.execute('SELECT * FROM circle_people WHERE id=?', (sister['id'],)).fetchone())
        state = circle_love.state(connection, row)
    assert state['state'] == 'engaged' and state['partner']['name'] == 'Ren'
    assert diary_lines(world, sister['id'])[0]['summary'] == f"{sister['name']} and Ren got engaged."


def test_moving_away_to_a_city_takes_them_out_of_town(world):
    sister = person(world, 'sister')
    says(world, 'my sister moved to Denver last week', 'client-said-08')
    row, details = record_of(world, sister['id'])
    assert details['local'] is False and details['city'] == 'Denver' and decode(row['schedule']) == []
    assert diary_lines(world, sister['id'])[0]['summary'] == f"{sister['name']} moved away, to Denver."


def test_hospital_then_home_again(world):
    sister = person(world, 'sister')
    says(world, 'my sister is in the hospital', 'client-said-09')
    assert record_of(world, sister['id'])[1]['health']['what'] == 'in_hospital'
    says(world, 'good news, my sister got out of the hospital', 'client-said-10')
    assert 'health' not in record_of(world, sister['id'])[1]
    assert sorted(line['happening'] for line in diary_lines(world, sister['id'])) == ['in_hospital', 'recovered']


def test_saying_it_twice_writes_it_once(world):
    mom = person(world, 'mom')
    says(world, 'my mom is in the hospital', 'client-said-11')
    says(world, 'ugh my mom is in the hospital', 'client-said-12')
    assert len(diary_lines(world, mom['id'])) == 1


def test_a_baby_born_joins_the_circle_with_the_name_they_gave(world, monkeypatch):
    monkeypatch.setattr(families, 'ACTIVE', True)
    sister = person(world, 'sister', age=31)
    says(world, 'my sister had a baby girl named Lily last night!!', 'client-said-13')
    with world.app.state.database.connect() as connection:
        children = families.children_of(connection, sister['id'])
    assert [(child['name'], child['pronouns'], child['status']) for child in children] == [('Lily', 'she/her', 'born')]
    line, = diary_lines(world, sister['id'])
    assert line['summary'] == f"{sister['name']} had a baby, Lily."
    world.post(f"/api/life/said/{line['said']['fact_id']}/undo")
    with world.app.state.database.connect() as connection:
        assert families.children_of(connection, sister['id']) == []


def test_a_pregnancy_starts_one_without_a_second_announcement(world, monkeypatch):
    monkeypatch.setattr(families, 'ACTIVE', True)
    sister = person(world, 'sister', age=31)
    says(world, "my sister's pregnant!!", 'client-said-14')
    with world.app.state.database.connect() as connection:
        companion = require_current(connection)
        story, = [row for row in connection.execute("SELECT * FROM storylines WHERE story='expecting'")]
        assert json.loads(story['cast_ids']) == [sister['id']]
        from companion.life import storylines
        assert storylines.fresh_beats(connection, companion, world.app.state.database.clock.now()) == []


def test_the_diary_keeps_its_other_entries(world):
    mom = person(world, 'mom')
    says(world, 'my mom just retired!', 'client-said-15')
    with world.app.state.database.connect() as connection:
        entries = agenda.diary(connection, require_current(connection)['active_timeline_id'], mom['id'])
    assert [entry['entry'].get('happening') for entry in entries if entry['entry'].get('happening')] == ['retired']
