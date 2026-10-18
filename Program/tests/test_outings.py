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
    # "Next Friday" said on a Monday is next week's.
    assert asked('Dinner next Friday?') == ('dinner', '2026-10-16', None, None)
    assert asked('Want to see a movie next Thursday?')[:2] == ('show', '2026-10-15')
    assert asked("Let's go for a walk this weekend!") == ('walk', '2026-10-10', None, None)
    # Asked on the Saturday itself, this weekend is the Sunday still ahead, not that evening; on the Sunday, that day.
    for day, meant in ((date(2026, 10, 10), date(2026, 10, 11)), (date(2026, 10, 11), date(2026, 10, 11))):
        assert outings.day_in('wanna do something this weekend?', day, {}) == meant
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


def test_a_holiday_mentioned_in_passing_does_not_set_the_day():
    holidays = {'thanksgiving': date(2026, 11, 26)}
    data = catalog.city('baltimore')
    found = outings.proposal("Let's go for a walk Sunday also my sister just texted me a seating chart for thanksgiving",
                             TODAY, holidays, data)
    assert (found['activity'], found['day']) == ('walk', date(2026, 10, 11))
    found = outings.proposal('Dinner Friday? btw what are you doing for thanksgiving', TODAY, holidays, data)
    assert found['day'] == date(2026, 10, 9)
    # Asked for the holiday itself, the holiday is the day.
    assert outings.proposal('Want to get dinner on thanksgiving?', TODAY, holidays, data)['day'] == date(2026, 11, 26)
    assert outings.proposal('Dinner, on thanksgiving?', TODAY, holidays, data)['day'] == date(2026, 11, 26)


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
    assert 'Just agreed with the user (confirm it in your reply)' in notes and 'You agreed to go' in notes
    assert notes.index('Just agreed') < notes.index('Going out with the user')
    # The next reply still knows the plan, but no longer announces it.
    send(client, 'See you then!', 'client-out-02')
    assert 'Just agreed' not in provider.requests[-1]['prompt']
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


def test_an_outing_still_finishes_after_a_long_absence(client, mira, provider, clock):
    send(client, 'Want to go to Ouzo Bay Wednesday?', 'client-out-long')
    clock.advance(timedelta(days=20))  # Back three weeks later: the outing was long over.
    reconcile(client)
    with client.app.state.database.connect() as connection:
        [done] = connection.execute('SELECT status, memory_id FROM outings').fetchall()
        memory = connection.execute('SELECT stated_at FROM memories WHERE id=?', (done['memory_id'],)).fetchone()
    assert done['status'] == 'done' and done['memory_id']
    assert memory['stated_at'].startswith('2026-10-07')  # Dated the evening it happened, for the scrapbook.


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


def test_by_the_harbor_means_on_the_water_not_a_name_that_says_harbor():
    data = catalog.city('haddon-harbor')
    wanted = outings.proposal('Want to get dinner by the harbor on Friday?', date(2026, 10, 12), {}, data)
    assert wanted['place'] is None and wanted['waterside']
    picks = {outings.pick_place(data, 'dinner', date(2026, 7, 17), '19:00', {}, f's{n}', False, 'dinner', True)['name']
             for n in range(30)}
    assert 'Golden Harbor Chinese Restaurant' not in picks
    assert all(outings.waterside(item, data) for item in data['places'] if item['name'] in picks)


def test_an_invitation_over_two_sentences_is_dinner_at_their_place():
    data = catalog.city('baltimore')
    for text in ("Want to come over Saturday? I'll cook.", "Come over Saturday. I'll cook."):
        found = outings.proposal(text, TODAY, {}, data, firm=True)
        assert found and (found['activity'], found['day']) == ('dinner-in', date(2026, 10, 10)), text
    # Without food it is not dinner, and the user cooking is never the companion having them over.
    assert outings.proposal('Want to come over Saturday? We could watch a movie.', TODAY, {}, data, firm=True) is None
    assert outings.proposal("Want to come over Saturday? I'll cook.", TODAY, {}, data) is None


def test_outing_memories_are_worded_for_the_user_and_turned_round_for_the_companion():
    """The user reads outing memories on Memories and the scrapbook ("Mira came over to your place"), never "the user"
    (E2E v0.13: "You married the user at ..." on the scrapbook); the companion reads them the other way round."""
    from companion.memory import records

    def text(activity, **place):
        return outings.memory_text({'id': 'o1', 'local_date': '2026-03-07', 'activity': activity,
                                    'place': {'name': 'Home', 'kind': 'home', 'neighborhood': '', **place}}, 'Mira')

    def told(memory, origin='automatic'):
        row = {**memory, 'layer': 'shared_experience', 'origin': origin}
        found = records.as_told(row, 'Mira')
        return f"{found['subject']}: {found['value']}"
    people = [{'role': 'mom', 'name': 'Ana Moreno'}, {'role': 'dad', 'name': 'Rui Moreno'}]
    found = {
        'visit-in': text('visit-in'), 'visit-yours': text('visit-yours'), 'dinner-yours': text('dinner-yours'),
        'knock': text('visit-yours', knock=True), 'dinner-in': text('dinner-in', menu={'dish': 'risotto'}),
        'met': text('meet-family', name="Ana and Rui's place", people=people, first=True),
        'saw': text('meet-family', name="Ana and Rui's place", people=people),
        'wedding': text('wedding', name="St Paul's Church", kind='church'),
    }
    assert found['visit-in'] == {'subject': "Over at Mira's place",
                                 'value': "You came over to Mira's place on Saturday, March 7."}
    assert found['visit-yours']['value'] == 'Mira came over to your place on Saturday, March 7.'
    assert found['dinner-yours']['value'] == 'Mira came over to your place for dinner on Saturday, March 7.'
    assert found['knock']['value'] == 'Mira dropped by your place on Saturday, March 7.'
    assert found['dinner-in']['value'] == "Had dinner, risotto, at Mira's place on Saturday, March 7."
    assert found['met'] == {'subject': "Meeting Mira's mom Ana and dad Rui",
                            'value': "You met Mira's mom Ana and dad Rui over dinner at Ana and Rui's place on "
                                     'Saturday, March 7.'}
    assert found['saw']['value'].startswith("You saw Mira's mom Ana and dad Rui again over dinner")
    assert found['wedding'] == {'subject': 'Your wedding',
                                'value': "You and Mira got married at St Paul's Church on Saturday, March 7, 2026."}
    for memory in found.values():
        assert 'the user' not in f"{memory['subject']} {memory['value']}".lower(), memory
    # To Mira, "you" is Mira.
    assert told(found['visit-in']) == "Over at your place: The user came over to your place on Saturday, March 7."
    assert told(found['visit-yours']) == "You came over: You came over to the user's place on Saturday, March 7."
    assert told(found['met']).startswith("Meeting your mom Ana and dad Rui: The user met your mom Ana and dad Rui")
    assert told(found['wedding']) == \
        "Your wedding: The user and you got married at St Paul's Church on Saturday, March 7, 2026."
    # Older memories were written Mira's way already, and a memory the user wrote is left as they wrote it.
    assert told({'subject': 'Your wedding', 'value': 'You married the user at Lupa.'}) == \
        'Your wedding: You married the user at Lupa.'
    assert told(found['visit-yours'], origin='user') == 'Mira came over: Mira came over to your place on Saturday, March 7.'


def test_memories_saved_in_the_old_wording_read_the_new_way_after_an_upgrade(client, companion):
    """Memories outings and stays saved before v0.14 said "You married the user at ..." (E2E v0.13 left them as they
    were): opening the workspace rewords them, but never one the user corrected or one already in today's wording."""
    from companion.characters import current
    from companion.conversation import next_seq
    from companion.database import encode, identifier, settings
    from companion.memory import records
    database = client.app.state.database
    stamp = '2026-08-01T12:00:00+00:00'

    def outing(connection, mira, activity, place, subject, value, day='2026-06-12'):
        message_id = identifier()
        connection.execute(
            'INSERT INTO messages (id, timeline_id, seq, role, text, status, active, character_version_id, '
            "memory_revision, created_at, completed_at) VALUES (?, ?, ?, 'user', 'see you then', 'complete', 1, ?, ?, "
            '?, ?)', (message_id, mira['active_timeline_id'], next_seq(connection, mira['active_timeline_id']),
                      mira['active_version_id'], settings(connection)['memory_revision'], stamp, stamp))
        memory = saved(connection, mira, subject, value)
        connection.execute(
            'INSERT INTO outings (id, companion_id, message_id, local_date, at_time, until_time, activity, place, '
            "status, memory_id, created_at) VALUES (?, ?, ?, ?, '18:30', '21:00', ?, ?, 'done', ?, ?)",
            (identifier(), mira['id'], message_id, day, activity, encode({'neighborhood': '', **place}), memory,
             stamp))
        return memory

    def saved(connection, mira, subject, value):
        memory, _created = records.insert(connection, mira, {'subject': subject, 'value': value,
                                                              'layer': 'shared_experience', 'stated_at': stamp},
                                          now=stamp, origin='automatic')
        return memory['id']

    with database.connect(write=True) as connection:
        mira = current(connection)
        wedding = outing(connection, mira, 'wedding', {'name': "St Paul's Church", 'kind': 'church'}, 'Your wedding',
                         "You married the user at St Paul's Church on Friday, June 12, 2026.")
        dinner = outing(connection, mira, 'dinner-in', {'name': 'Your place', 'kind': 'home', 'menu': {'dish': 'risotto'}},
                        'Dinner at their place together at Your place',
                        'Went out together for dinner (they cooked risotto) at your place on Saturday, April 4.',
                        day='2026-04-04')
        corrected = outing(connection, mira, 'visit-yours', {'name': "The user's place", 'kind': 'your-home'},
                           "You went over to the user's place", "You went over to the user's place on Friday, June 12.")
        records.revise(connection, records.get(connection, corrected), stamp, value='Mira came round for tea.')
        stay = saved(connection, mira, 'You stayed with the user in Baltimore',
                     'You stayed with the user in Baltimore, Friday July 10 to Sunday July 12.')
        connection.execute(
            'INSERT INTO trips (id, companion_id, timeline_id, start_date, end_date, city_id, city_name, kind, visit, '
            "memory_id, created_at) VALUES (?, ?, ?, '2026-07-10', '2026-07-12', 'baltimore', 'Baltimore', 'getaway', "
            "'to-you', ?, ?)", (identifier(), mira['id'], mira['active_timeline_id'], stay, stamp))
        revision = settings(connection)['memory_revision']
    from companion import upgrade
    upgrade.migrate(database.path, stamp)  # The upgrade's own connection, without a row factory.
    with database.connect() as connection:
        def text(memory_id):
            row = records.get(connection, memory_id)
            return row['subject'], row['value']
        assert text(wedding) == ('Your wedding', "You and Mira got married at St Paul's Church on Friday, June 12, 2026.")
        assert text(dinner) == ("Dinner at Mira's place", "Had dinner, risotto, at Mira's place on Saturday, April 4.")
        assert text(stay) == ("Mira's visit to Baltimore",
                              'Mira came to stay with you in Baltimore, Friday July 10 to Sunday July 12.')
        # The correction made a new revision; the outing's own one stays as history, as it was.
        assert text(corrected)[1] == "You went over to the user's place on Friday, June 12."
        assert settings(connection)['memory_revision'] > revision
        # Once reworded, nothing changes on the next start.
        assert outings.reword_memories(connection, stamp) == 0


def test_a_cuisine_named_after_a_place_is_capitalized():
    assert [outings.proper(cuisine) for cuisine in ('spanish', 'tex-mex', 'modern-british', 'soul-food', 'southern')] \
        == ['Spanish', 'Tex-Mex', 'modern-British', 'soul-food', 'southern']
