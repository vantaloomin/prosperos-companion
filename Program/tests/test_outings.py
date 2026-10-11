"""Go somewhere together: asked out, the companion says when and picks a real place, and it happens."""
from datetime import date, timedelta

import pytest
from conftest import reconcile, send, set_life

from companion.database import decode
from companion.life import body, composer, outings
from companion.providers.chat import Chunk
from companion.world import catalog

TODAY = date(2026, 10, 5)  # A Monday.
EVENINGS = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00', 'days': [0, 1, 2, 3, 4]},
            {'key': 'evening', 'label': 'Evening', 'kind': 'leisure', 'start': '17:00', 'end': '23:00'},
            {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]


def asked(text, firm=False):
    found = outings.proposal(text, TODAY, {}, catalog.city('baltimore'), firm)
    return found and (found['activity'], found['day'] and found['day'].isoformat(), found['at'],
                      found['place'] and found['place']['id'])


def test_asking_out_is_read_from_the_message():
    assert asked('Want to get dinner Friday?') == ('dinner', '2026-10-09', None, None)
    assert asked("Let's go for a walk this weekend!") == ('walk', '2026-10-10', None, None)
    assert asked('Drinks with me Thursday at 8?') == ('drinks', '2026-10-08', '20:00', None)
    assert asked('How about a date sometime?') == ('dinner', None, None, None)
    # The map's "Suggest going together" line names the place.
    assert asked('Want to go to Ouzo Bay one night this week?') == ('dinner', None, None, 'ouzo-bay')


def test_questions_about_their_plans_the_past_and_refusals_are_not_asking():
    for text in ('Are you going to dinner with Dana Friday?', 'Did you have dinner Friday?',
                 "I don't want to get dinner Friday.", 'Dinner was great.', 'What did you do this weekend?'):
        assert asked(text) is None, text


def test_staying_in_a_call_a_story_or_a_vague_wish_is_not_going_out():
    for text in ("Want to come over to my place for dinner tomorrow? I'll cook", 'Want to watch a movie together on facetime?',
                 'Would you like a cup of tea?', 'You want to hear about my coffee disaster?',
                 'We should grab coffee sometime soon.'):
        assert asked(text) is None, text
    assert asked("Next time we should get drinks at the Owl Bar", firm=True) is None
    assert asked('Want to grab some tea Sunday?') == ('coffee', '2026-10-11', None, None)


def test_a_date_with_its_weekday_is_the_date_and_the_place_fits_the_word():
    assert asked('Want to go to the aquarium on Saturday, November 14?')[:2] == ('museum', '2026-11-14')
    data = catalog.city('baltimore')
    picks = {outings.pick_place(data, 'museum', date(2026, 11, 14), '14:00', {}, f's{n}', False, 'aquarium')['name']
             for n in range(5)}
    assert picks == {'National Aquarium'}


def test_the_companion_only_makes_firm_plans_themselves():
    assert asked("We should get drinks Saturday!", firm=True) == ('drinks', '2026-10-10', None, None)
    assert asked('Should we get drinks Saturday?', firm=True) is None
    assert asked('Want to get drinks Saturday?', firm=True) is None


@pytest.fixture
def mira(client, monkeypatch, provider):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(composer, 'PLAN_SHARE', 0)
    monkeypatch.setattr(composer, 'THREAD_SHARE', 0)
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'schedule': EVENINGS,
                                                    'home_city': 'Baltimore', 'interests': ['seafood', 'jazz']})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    set_life(client, automatic_events=True, phrase_with_model=False, catch_up_max_events=6,
             catch_up_lookback_hours=168)
    return response.json()


def says(provider, text):
    provider.replies.append([Chunk(text), Chunk('', 'stop')])


def listing(client):
    response = client.get('/api/life/outings')
    assert response.status_code == 200, response.text
    return response.json()


def agenda_entry(client, slot_key):
    with client.app.state.database.connect() as connection:
        row = connection.execute("SELECT block, entry FROM life_agenda WHERE subject='companion' AND slot_key=?",
                                 (slot_key,)).fetchone()
    return (decode(row['block']), decode(row['entry']) if row['entry'] else None) if row else (None, None)


def test_asked_out_they_pick_a_place_and_the_reply_is_told_before_it_is_written(client, mira, provider, clock):
    reconcile(client)  # The week ahead is already composed before the plan is made.
    says(provider, 'Yes! I know just the place.')
    send(client, 'Want to get dinner Thursday?', 'client-out-01')
    [outing] = listing(client)['outings']
    assert (outing['local_date'], outing['at_time'], outing['until_time'], outing['activity']) == (
        '2026-10-08', '19:00', '21:00', 'dinner')
    place = outing['place']
    assert place['city'] == 'Baltimore' and place['kind'] in {'restaurant', 'tavern', 'inn'} and place['spots']
    notes = provider.requests[-1]['prompt']
    assert 'Going out with the user' in notes and f"dinner at {place['name']}" in notes
    assert 'You just said yes; tell them where and when.' in notes
    # The next reply still knows the plan, but no longer announces it.
    send(client, 'See you then!', 'client-out-02')
    assert 'You just said yes' not in provider.requests[-1]['prompt']
    assert f"Thursday October 8 at 19:00: dinner at {place['name']}" in provider.requests[-1]['prompt']
    reconcile(client)
    block, entry = agenda_entry(client, 'evening@2026-10-08')
    assert block['with_user'] and entry['outing']['id'] == outing['id']
    assert entry['summary'].startswith(f"Mira went out for dinner at {place['name']}")


def test_a_busy_day_moves_to_the_nearest_free_one(client, mira, provider):
    send(client, 'Lunch together Tuesday?', 'client-out-03')
    [outing] = listing(client)['outings']
    # Weekday lunches are work: Saturday is the first free 12:30.
    assert (outing['asked_date'], outing['local_date'], outing['at_time']) == ('2026-10-06', '2026-10-10', '12:30')
    send(client, 'Ok!', 'client-out-04')
    send(client, 'Coffee with me Saturday too?', 'client-out-05')
    # Saturday already has an outing, so coffee goes to Sunday.
    assert [item['local_date'] for item in listing(client)['outings']] == ['2026-10-10', '2026-10-11']


def test_a_named_place_is_kept_and_the_bill_comes_out_of_their_budget(client, mira, provider, clock):
    send(client, 'Want to go to Ouzo Bay Wednesday?', 'client-out-06')
    [outing] = listing(client)['outings']
    assert outing['place']['id'] == 'ouzo-bay' and outing['named'] and outing['local_date'] == '2026-10-07'
    clock.advance(timedelta(days=2, hours=7, minutes=30))  # Wednesday 19:30.
    reconcile(client)
    assert listing(client)['outings'][0]['state'] == 'now'
    preview = client.get('/api/context/preview').json()['prompt']
    assert 'Right now you are out with the user, in person: dinner at Ouzo Bay' in preview
    assert 'Talk as if you are there together' in preview
    clock.advance(timedelta(hours=2))
    reconcile(client)
    [done] = listing(client)['outings']
    assert done['state'] == 'done' and done['status'] == 'done' and done['memory_id']
    memories = client.get('/api/memories').json()
    memories = memories['memories'] if isinstance(memories, dict) else memories
    shared = [item for item in memories if item['layer'] == 'shared_experience']
    assert shared and 'Ouzo Bay' in shared[0]['value']
    money = client.get('/api/today/money').json()
    if money['available'] and done['cost']:
        assert any(item['for'] == 'outing' and 'Ouzo Bay' in item['label'] for item in money['bought'])
    assert 'Earlier you and the user had dinner at Ouzo Bay' in client.get('/api/context/preview').json()['prompt']


def test_the_user_can_call_it_off_send_them_elsewhere_or_head_home(client, mira, provider, clock):
    send(client, 'Drinks Friday?', 'client-out-07')
    [outing] = listing(client)['outings']
    reconcile(client)
    assert agenda_entry(client, 'evening@2026-10-09')[1]['outing']
    moved = client.post(f"/api/life/outings/{outing['id']}/elsewhere").json()
    assert moved['place']['id'] != outing['place']['id'] and moved['rolls'] == 1
    assert agenda_entry(client, 'evening@2026-10-09')[1]['place']['id'] == moved['place']['id']
    response = client.post(f"/api/life/outings/{outing['id']}/home")
    assert response.status_code == 409  # Not under way yet.
    client.post(f"/api/life/outings/{outing['id']}/cancel")
    [cancelled] = listing(client)['outings']
    assert cancelled['state'] == 'cancelled' and cancelled['undo']
    assert not (agenda_entry(client, 'evening@2026-10-09')[1] or {}).get('outing')
    assert 'Going out with the user' not in client.get('/api/context/preview').json()['prompt']
    # Calling it off can be taken back the same day.
    back = client.post(f"/api/life/outings/{outing['id']}/undo").json()
    assert back['status'] == 'planned' and agenda_entry(client, 'evening@2026-10-09')[1]['outing']
    client.post(f"/api/life/outings/{outing['id']}/cancel")
    clock.advance(timedelta(days=1))
    assert not listing(client)['outings'][0]['undo']
    assert client.post(f"/api/life/outings/{outing['id']}/undo").status_code == 409


def test_heading_home_early_ends_it_now(client, mira, provider, clock):
    send(client, 'Dinner tonight?', 'client-out-08')
    [outing] = listing(client)['outings']
    assert outing['local_date'] == '2026-10-05'
    clock.advance(timedelta(hours=7, minutes=15))  # 19:15.
    ended = client.post(f"/api/life/outings/{outing['id']}/home").json()
    assert ended['ended_at'] and not ended['memory_id']
    [home] = listing(client)['outings']
    assert home['state'] == 'done' and home['undo']
    # For a minute or two it can be taken back; nothing is kept until then.
    back = client.post(f"/api/life/outings/{outing['id']}/undo").json()
    assert back['ended_at'] is None and listing(client)['outings'][0]['state'] == 'now'
    client.post(f"/api/life/outings/{outing['id']}/home")
    clock.advance(timedelta(minutes=3))
    reconcile(client)
    [kept] = listing(client)['outings']
    assert kept['status'] == 'done' and kept['memory_id'] and not kept['undo']


def test_replies_are_not_held_while_out_together():
    from companion.life import pacing
    assert pacing.busy_kind({'kind': 'social', 'with_user': True}) is None
    assert pacing.busy_kind({'kind': 'social'}) == 'social'
