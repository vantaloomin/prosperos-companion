"""What happens to someone in a storyline is written into their own life (companion/life/happenings.py): a diary line,
the change on their record, and taking it back (tester 2026-11-10: Lestara's promotion and Kaito's breakup were in
nobody's diary, and Kaito still had his girlfriend)."""
import json
from datetime import timedelta

import pytest
from conftest import send

from companion.characters import require_current
from companion.database import decode, encode, identifier
from companion.life import agenda, circle, circle_love, happenings, network, storylines
from companion.memory import context

WORKDAY = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00', 'days': [0, 1, 2, 3, 4]},
           {'key': 'evening', 'label': 'Evening', 'kind': 'social', 'start': '18:00', 'end': '22:00'},
           {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]


@pytest.fixture
def world(client):
    response = client.post('/api/companion', json={'name': 'Sett', 'timezone': 'UTC', 'schedule': WORKDAY,
                                                     'location': 'Fells Point, Baltimore', 'home_city': 'baltimore',
                                                     'identity': 'Sett works as an accountant.',
                                                     'personality': 'Outgoing, a social butterfly.'})
    assert response.status_code == 200, response.text
    with client.app.state.database.connect(write=True) as connection:
        companion = require_current(connection)
        circle.ensure(connection, companion, client.app.state.life.world, client.app.state.database.clock.now())
    return client


def connect(client):
    return client.app.state.database.connect(write=True)


def companion_of(connection):
    return require_current(connection)


def row_of(connection, person_id):
    return dict(connection.execute('SELECT * FROM circle_people WHERE id=?', (person_id,)).fetchone())


def someone(connection, companion, role, seed_partner=None, **details):
    """A circle person made into `role`, with these details; `seed_partner` picks a seed that gives them (True) or
    does not give them (False) a seeded partner."""
    people = circle.people(connection, companion['active_timeline_id'])
    row = next(person for person in people if person['role'] == role) if any(
        person['role'] == role for person in people) else people[0]
    seed = row['seed']
    if seed_partner is not None:
        seed = next(f"{row['seed']}:{index}" for index in range(300)
                    if (circle_love.seeded_partner({'id': 'x', 'seed': f"{row['seed']}:{index}"}) is not None)
                    == seed_partner)
    found = {key: value for key, value in (decode(row['details']) or {}).items() if key != 'works_with_companion'}
    connection.execute('UPDATE circle_people SET role=?, seed=?, details=? WHERE id=?',
                       (role, seed, encode(found | details), row['id']))
    return row_of(connection, row['id'])


def start_story(connection, companion, key, cast, days_ago=2, outcome=0, story_status='running'):
    """A storyline that started `days_ago`, every beat already happened, each decided by `outcome`."""
    story = storylines.find_story(key)
    today = storylines.local_today(companion, connection_now(connection))
    stages = []
    for index, alternatives in enumerate(story.stages):
        chosen = alternatives[outcome if len(alternatives) > 1 else 0]
        on = today - timedelta(days=days_ago) + timedelta(days=index)
        stages.append({'on': min(on, today - timedelta(days=1)).isoformat(), 'text': chosen.text, 'share': chosen.share,
                       'tone': chosen.tone})
    story_id = identifier()
    connection.execute('INSERT INTO storylines (id, timeline_id, story, level, cast_ids, stages, started_on, status, '
                       "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '2026-01-01T00:00:00Z')",
                       (story_id, companion['active_timeline_id'], key, story.level, json.dumps(cast),
                        encode(stages), stages[0]['on'], story_status))
    return story_id


NOW = {}


def connection_now(_connection):
    return NOW['now']


@pytest.fixture(autouse=True)
def now_of(client):
    NOW['now'] = client.app.state.database.clock.now()


def test_a_promotion_goes_into_their_diary_and_ending_it_takes_it_back(world):
    with connect(world) as connection:
        companion = companion_of(connection)
        mom = someone(connection, companion, 'mom', career='Accountant', employer='Harbor Bank')
        story_id = start_story(connection, companion, 'parent_promotion', [mom['id']])
        before = row_of(connection, mom['id'])
        assert storylines.record_due(connection, companion, NOW['now']) == 1
        assert storylines.record_due(connection, companion, NOW['now']) == 0  # Once only.
        timeline = companion['active_timeline_id']
        diary = agenda.diary(connection, timeline, mom['id'])
        line = f"{mom['name']} got a promotion at work."
        assert any(item['entry']['summary'] == line for item in diary)
        view = next(person for person in agenda.circle_view(connection, timeline, NOW['now']) if person['id'] == mom['id'])
        assert view['recent'][0]['entry']['summary'] == line or any(
            item['entry']['summary'] == line for item in view['recent'])
        assert decode(row_of(connection, mom['id'])['details'])['promoted_on']
    response = world.post(f'/api/life/storylines/{story_id}/end')
    assert response.status_code == 200, response.text
    with connect(world) as connection:
        after = row_of(connection, mom['id'])
        assert (after['details'], after['career'], after['schedule']) == \
            (before['details'], before['career'], before['schedule'])
        assert not any(item['entry']['summary'] == line for item in agenda.diary(connection, timeline, mom['id']))


def test_a_breakup_leaves_them_single_with_an_ex(world):
    with connect(world) as connection:
        companion = companion_of(connection)
        friend = someone(connection, companion, 'close friend', seed_partner=True)
        assert circle_love.state(connection, friend)['state'] == 'seeing'
        partner_key = f"{friend['seed']}/0"
        partner = network.find(connection, companion, partner_key)
        assert partner['relation'] in ('girlfriend', 'boyfriend', 'partner')
        start_story(connection, companion, 'friend_breakup', [friend['id']], days_ago=3)
        storylines.record_due(connection, companion, NOW['now'])
        row = row_of(connection, friend['id'])
        found = circle_love.state(connection, row)
        assert found['state'] == 'single' and found['exes'][0]['key'] == partner_key
        people = network.people_of(connection, companion, friend['seed'])
        assert people[-1]['key'] == partner_key and people[-1].get('ex')
        assert people[-1]['relation'] in ('ex-girlfriend', 'ex-boyfriend', 'ex')
        assert people[-1]['name'] == partner['name']  # The same person, by name and key.
        lines = [item['entry']['summary'] for item in agenda.diary(connection, companion['active_timeline_id'],
                                                                     friend['id'])]
        assert f"{friend['name']} and {partner['name']} broke up." in lines
        # The acquaintance line follows: met as his girlfriend, she is his ex-girlfriend now.
        snapshot = {**partner, 'met_at': '2026-01-01T00:00:00Z', 'occasion': 'a party'}
        refreshed = network.refreshed(connection, [snapshot], circle.people(connection, companion['active_timeline_id']))
        assert refreshed[0]['how'].endswith(people[-1]['relation']) and refreshed[0].get('ex')


def test_a_new_job_moves_them_and_the_other_outcome_moves_them_back(world):
    with connect(world) as connection:
        companion = companion_of(connection)
        friend = someone(connection, companion, 'close friend', career='Barista')
        if not friend['career']:
            pytest.skip('No matched career for this person in this city.')
        before = row_of(connection, friend['id'])
        story_id = start_story(connection, companion, 'friend_new_job', [friend['id']], outcome=0)
        storylines.record_due(connection, companion, NOW['now'])
        moved = decode(row_of(connection, friend['id'])['details'])
        assert moved['job_since'] and moved.get('employer') != decode(before['details']).get('employer')
        happenings.take_back(connection, companion['active_timeline_id'], f'storyline:{story_id}:1', NOW['now'],
                             forget=True)
        after = row_of(connection, friend['id'])
        assert (after['details'], after['schedule']) == (before['details'], before['schedule'])


def test_a_coworker_who_leaves_no_longer_works_with_the_companion(world):
    with connect(world) as connection:
        companion = companion_of(connection)
        coworker = someone(connection, companion, 'coworker', works_with_companion=True, career='Works with Sett')
        start_story(connection, companion, 'coworker_leaving', [coworker['id']], days_ago=5)
        storylines.record_due(connection, companion, NOW['now'])
        row = row_of(connection, coworker['id'])
        details = decode(row['details'])
        assert row['role'] == 'former coworker' and not details.get('works_with_companion')
        assert row['revision'] > coworker['revision']
        person = circle.view(row)
        assert 'works with you' not in context.person_text(person)


def test_a_secret_couple_made_official_are_each_others(world):
    with connect(world) as connection:
        companion = companion_of(connection)
        people = circle.people(connection, companion['active_timeline_id'])
        first, second = people[0], people[1]
        start_story(connection, companion, 'secret_couple', [first['id'], second['id']], outcome=0)
        storylines.record_due(connection, companion, NOW['now'])
        first, second = row_of(connection, first['id']), row_of(connection, second['id'])
        assert circle.tie(first, second) == 'partners'
        found = circle_love.state(connection, first)
        assert found['state'] == 'seeing' and found['partner']['circle_id'] == second['id']
        for row in (first, second):
            listed = network.people_of(connection, companion, row['seed'])
            assert not any(person['relation'] in ('girlfriend', 'boyfriend', 'partner') for person in listed)


def test_married_people_have_a_spouse_and_the_companions_partner_has_nobody(world):
    with connect(world) as connection:
        companion = companion_of(connection)
        sister = someone(connection, companion, 'sister', seed_partner=True, married=True)
        listed = network.people_of(connection, companion, sister['seed'])
        assert listed[0]['relation'] in ('wife', 'husband', 'spouse')
        assert not any(person['relation'] in ('girlfriend', 'boyfriend') for person in listed)
        unseeded = someone(connection, companion, 'brother', seed_partner=False, married=True)
        listed = network.people_of(connection, companion, unseeded['seed'])
        assert listed[0]['relation'] in ('wife', 'husband', 'spouse') and listed[0]['key'].endswith('/p0')
        assert network.find(connection, companion, listed[0]['key'])['name'] == listed[0]['name']
        girlfriend = someone(connection, companion, 'girlfriend', seed_partner=True, love=True)
        listed = network.people_of(connection, companion, girlfriend['seed'])
        assert not any(person['relation'] in network.TAKEN for person in listed)


def test_parents_who_separate_are_separated_in_the_prompt(world):
    with connect(world) as connection:
        companion = companion_of(connection)
        timeline = companion['active_timeline_id']
        people = circle.people(connection, timeline)
        mom, dad = people[0], people[1]
        connection.execute("UPDATE circle_people SET role='mom' WHERE id=?", (mom['id'],))
        connection.execute("UPDATE circle_people SET role='dad' WHERE id=?", (dad['id'],))
        start_story(connection, companion, 'parents_separating', [mom['id'], dad['id']])
        storylines.record_due(connection, companion, NOW['now'])
        mom, dad = row_of(connection, mom['id']), row_of(connection, dad['id'])
        assert circle.tie(mom, dad) == 'separated' and circle.tie(dad, mom) == 'separated'
        assert circle_love.state(connection, mom, [mom, dad])['state'] == 'separated'
        lines = [item['entry']['summary'] for item in agenda.diary(connection, timeline, dad['id'])]
        assert f"{dad['name']} and {mom['name']} separated." in lines


def test_what_the_user_set_is_never_changed(world):
    with connect(world) as connection:
        companion = companion_of(connection)
        friend = someone(connection, companion, 'close friend', seed_partner=True, edited=['partner'])
        before = row_of(connection, friend['id'])
        start_story(connection, companion, 'friend_breakup', [friend['id']])
        storylines.record_due(connection, companion, NOW['now'])
        assert row_of(connection, friend['id'])['details'] == before['details']
        worker = someone(connection, companion, 'longtime friend', career='Barista', edited=['job'])
        before = row_of(connection, worker['id'])
        start_story(connection, companion, 'friend_new_job', [worker['id']])
        storylines.record_due(connection, companion, NOW['now'])
        after = row_of(connection, worker['id'])
        assert (after['details'], after['schedule']) == (before['details'], before['schedule'])


def test_an_old_storyline_past_two_months_is_not_filled_in(world):
    with connect(world) as connection:
        companion = companion_of(connection)
        mom = someone(connection, companion, 'mom', career='Accountant', employer='Harbor Bank')
        start_story(connection, companion, 'parent_promotion', [mom['id']], days_ago=90)
        assert storylines.record_due(connection, companion, NOW['now']) == 0


def test_a_fork_keeps_the_events_before_it(world, provider):
    with connect(world) as connection:
        companion = companion_of(connection)
        mom = someone(connection, companion, 'mom', career='Accountant', employer='Harbor Bank')
        start_story(connection, companion, 'parent_promotion', [mom['id']], days_ago=3)
        storylines.record_due(connection, companion, NOW['now'])
        parent = companion['active_timeline_id']
    sent = send(world, 'How was your week?', 'client-happenings-fork')['message']
    fork = world.post('/api/timelines', json={'message_id': sent['id']}).json()
    assert world.post(f"/api/timelines/{fork['id']}/activate").status_code == 200
    with connect(world) as connection:
        rows = connection.execute('SELECT * FROM person_events WHERE timeline_id=?', (fork['id'],)).fetchall()
        assert len(rows) == 1 and rows[0]['subject'] != mom['id']
        copy_story = connection.execute('SELECT id FROM storylines WHERE timeline_id=?', (fork['id'],)).fetchone()
        assert rows[0]['source'] == f"storyline:{copy_story['id']}:0"
        diary = agenda.diary(connection, fork['id'], rows[0]['subject'])
        assert any(item['entry']['summary'].endswith('got a promotion at work.') for item in diary)
    assert parent != fork['id']


def test_happenings_fill_names_when_read(world):
    with connect(world) as connection:
        companion = companion_of(connection)
        people = circle.people(connection, companion['active_timeline_id'])
        first, second = people[0], people[1]
        start_story(connection, companion, 'friends_feud', [first['id'], second['id']], outcome=1)
        storylines.record_due(connection, companion, NOW['now'])
        connection.execute("UPDATE circle_people SET name='Renamed' WHERE id=?", (second['id'],))
        lines = [item['text'] for item in happenings.for_person(connection, companion['active_timeline_id'],
                                                                 first['id'])]
        assert f"{first['name']} and Renamed still aren't speaking." in lines
        assert circle.tie(row_of(connection, first['id']), row_of(connection, second['id'])) is None


def test_no_model_is_called(world, monkeypatch):
    from companion import model_calls
    monkeypatch.setattr(model_calls, 'complete', lambda *args, **kwargs: pytest.fail('a model was called'),
                        raising=False)
    with connect(world) as connection:
        companion = companion_of(connection)
        friend = someone(connection, companion, 'close friend', seed_partner=True)
        start_story(connection, companion, 'friend_breakup', [friend['id']])
        assert storylines.record_due(connection, companion, NOW['now']) == 2
