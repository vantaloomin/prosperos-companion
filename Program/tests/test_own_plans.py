"""Plans the companion makes in chat for a date happen in their life on that date."""
from datetime import date, timedelta

import pytest
from conftest import reconcile, send, set_life

from companion.database import decode
from companion.life import body, composer, own_plans
from companion.providers.chat import Chunk

TODAY = date(2026, 10, 12)
HOLIDAYS = {'thanksgiving': date(2026, 11, 26), 'christmas': date(2026, 12, 25), 'christmas eve': date(2026, 12, 24),
            'new years eve': date(2026, 12, 31)}
EVENINGS = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00', 'days': [0, 1, 2, 3, 4]},
            {'key': 'evening', 'label': 'Evening', 'kind': 'leisure', 'start': '19:00', 'end': '22:00'},
            {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]


def plans(text):
    return [(plan.local_date, plan.at, plan.activity, plan.form) for plan in own_plans.extract(text, TODAY, HOLIDAYS)]


def test_dated_first_person_plans_are_captured():
    assert plans('My bout is Saturday the 24th, first whistle at 6!') == [('2026-10-24', '18:00', 'My bout', 'thing')]
    assert plans("I'm hosting a potluck at my place on Thanksgiving.") == [
        ('2026-11-26', None, 'hosting a potluck at my place', 'doing')]
    assert plans("I'm going to my grandma’s sunday.") == [('2026-10-18', None, "going to my grandma's", 'doing')]
    assert plans('Christmas is just going to be me and Juniper on the couch.') == [
        ('2026-12-25', None, 'me and Juniper on the couch', 'scene')]
    assert plans("I'm going hiking with Dana tonight.") == [('2026-10-12', None, 'hiking with Dana', 'doing')]
    assert plans("I'll be at my sister's on New Year's Eve.") == [('2026-12-31', None, "at my sister's", 'doing')]
    assert plans("I'll bake bread tomorrow morning. I have a dentist appointment on November 3 at 2:30pm.") == [
        ('2026-10-13', '10:00', 'baking bread', 'doing'), ('2026-11-03', '14:30', 'a dentist appointment', 'thing')]


def test_questions_maybes_the_user_the_past_and_vague_days_are_not_plans():
    for text in ('Are you going out Saturday?', 'Maybe I will go to the market Sunday.',
                 "If it's sunny I'm going to the beach Saturday.", "I'm thinking about going hiking Sunday.",
                 'You should come to my bout Saturday.', "We're getting dinner Friday.",
                 "Your interview is Tuesday, right.", "I went to my grandma's Sunday.",
                 "I'm not going to the party Friday.", "I'm working Saturday.", "I'm free Sunday.",
                 "I'm hosting a party this weekend.", 'I baked bread yesterday.', '*waves* "See you Friday!"',
                 'My bout is Friday the 24th.', 'Saturday is going to be crazy.'):
        assert plans(text) == [], text


def test_holidays_come_from_the_city_calendar(client, mira):
    with client.app.state.database.connect() as connection:
        found = own_plans.holiday_dates(connection, {'home_city': 'Baltimore'}, TODAY)
    assert found['thanksgiving'] == date(2026, 11, 26) and found['new years eve'] == date(2026, 12, 31)
    assert found['christmas'] == found['christmas day'] == date(2026, 12, 25)


def test_a_plan_takes_the_free_block_for_its_time_and_never_work():
    blocks = [{'key': 'work', 'kind': 'work', 'start': '09:00', 'end': '17:00'},
              {'key': 'lunch', 'kind': 'leisure', 'start': '12:00', 'end': '13:00'},
              {'key': 'evening', 'kind': 'social', 'start': '18:00', 'end': '23:00'}]
    timed = {'id': 'a', 'at_time': '18:30'}
    assert own_plans.assign([timed], blocks) == {'evening': timed}
    assert own_plans.assign([{'id': 'b', 'at_time': '10:00'}], blocks) == {}
    loose = {'id': 'c', 'at_time': None}
    assert own_plans.assign([loose], blocks) == {'evening': loose, 'lunch': None}


@pytest.fixture
def mira(client, monkeypatch, provider):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(composer, 'PLAN_SHARE', 0)
    monkeypatch.setattr(composer, 'THREAD_SHARE', 0)
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'schedule': EVENINGS})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    set_life(client, automatic_events=True, phrase_with_model=False, catch_up_max_events=6,
             catch_up_lookback_hours=168)
    return response.json()


def says(provider, text):
    provider.replies.append([Chunk(text), Chunk('', 'stop')])


def agenda_entry(client, slot_key):
    with client.app.state.database.connect() as connection:
        row = connection.execute("SELECT entry FROM life_agenda WHERE subject='companion' AND slot_key=?",
                                 (slot_key,)).fetchone()
    return decode(row['entry']) if row and row['entry'] else None


def test_a_plan_said_in_chat_becomes_that_days_entry_and_event(client, mira, clock, provider):
    reconcile(client)  # The week ahead is already composed before the plan is made.
    assert not (agenda_entry(client, 'evening@2026-10-10') or {}).get('own_plan')
    says(provider, "I'm hosting a potluck at my place on Saturday the 10th. I'm seeing the dentist Wednesday at 10am.")
    send(client, 'Plans this week?', 'client-plan-01')
    system = client.get('/api/context/preview').json()['system']
    assert 'Plans you have made in chat' in system and '- Saturday October 10: hosting a potluck at your place' in system
    assert '- Wednesday October 7 at 10:00: seeing the dentist' in system
    reconcile(client)
    entry = agenda_entry(client, 'evening@2026-10-10')
    assert entry['activity'] == 'own-plan'
    assert entry['summary'].startswith('Mira spent the evening hosting a potluck at home, as planned.')
    # The dentist is during work: noted, but the shift stays.
    assert agenda_entry(client, 'work@2026-10-07')['activity'] != 'own-plan'
    clock.advance(timedelta(days=6))
    reconcile(client)
    events = client.get('/api/events').json()
    happened = [event for event in events if event['details'].get('own_plan')]
    assert [event['details']['local_date'] for event in happened] == ['2026-10-10']
    assert 'hosting a potluck at home' in happened[0]['summary']


def test_a_replaced_reply_takes_its_plan_out_of_the_agenda(client, mira, clock, provider):
    says(provider, 'My bout is Friday the 9th at 7!')
    sent = send(client, 'Busy week?', 'client-plan-02')
    reconcile(client)
    assert agenda_entry(client, 'evening@2026-10-09')['summary'].startswith("The evening went to Mira's bout")
    says(provider, 'Just the usual.')
    response = client.post(f"/api/conversation/messages/{sent['message']['id']}/alternatives")
    assert response.status_code == 200, response.text
    reconcile(client)
    assert (agenda_entry(client, 'evening@2026-10-09') or {}).get('activity') != 'own-plan'
