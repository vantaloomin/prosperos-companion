"""Storylines you are part of (companion/life/shared_storylines.py): the world starts something that involves the
user, and what the user does about each beat decides the next."""
import re
from datetime import date, datetime, timedelta

import pytest
from conftest import reconcile, send, set_life

from companion import consequences, news
from companion.characters import current
from companion.database import decode, encode, optional
from companion.life import circle, openers, outings, shared_storylines, storylines, their_people

ROLES = ['mom', 'dad', 'brother', 'close friend', 'friend']
FAMILIES = {'their people', 'favors', 'their work', 'around town', 'a third person', 'growing closer', 'their goal'}
TEXT_ANSWERS = {'answered', 'said_yes', 'said_no', 'dropped_by', 'passed', 'any'}
PLAN_ANSWERS = {'went', 'called_off', 'passed', 'any'}


@pytest.fixture(autouse=True)
def on(monkeypatch):
    monkeypatch.setattr(shared_storylines, 'ACTIVE', True)


@pytest.fixture
def only(monkeypatch):
    """Leaves one story in the bank, so a test knows which starts."""
    def keep(*keys):
        found = {key: story for key, story in shared_storylines.bank().items() if key in keys}
        monkeypatch.setattr(shared_storylines, 'bank', lambda: found)
    return keep


def make(client, relationship='friendship', roles=ROLES, **values):
    response = client.post('/api/companion', json={'name': 'Mira Costa', 'timezone': 'UTC', 'home_city': 'Baltimore',
                                                     'relationship': relationship, **values})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    assert client.get('/api/life/circle').status_code == 200
    with client.app.state.database.connect(write=True) as connection:
        people = circle.people(connection, current(connection)['active_timeline_id'])
        for row, role in zip(people, roles, strict=False):
            details = {**decode(row['details']), 'local': True}
            connection.execute('UPDATE circle_people SET role=?, details=? WHERE id=?', (role, encode(details), row['id']))
        for row in people[len(roles):]:
            connection.execute("UPDATE circle_people SET status='removed' WHERE id=?", (row['id'],))


def advance(client, clock):
    with client.app.state.database.connect(write=True) as connection:
        return shared_storylines.advance(connection, current(connection), clock.now())


SENT = iter(range(10 ** 6))


def talk(client, clock, text='Hey, how was your day?'):
    send(client, text, f'user-message-{next(SENT)}')


def settled_in(client, clock):
    """The two have talked, and enough days have passed for something to start."""
    talk(client, clock)
    clock.advance(timedelta(days=shared_storylines.SETTLE_IN))
    talk(client, clock)


def started(client, clock, days=30):
    """Moves on a day at a time, the user writing each morning, until a storyline starts; returns its row."""
    for _day in range(days):
        if advance(client, clock):
            return rows(client)[-1]
        clock.advance(timedelta(days=1))
        talk(client, clock)
    return None


def rows(client):
    with client.app.state.database.connect() as connection:
        return shared_storylines.rows(connection, current(connection)['active_timeline_id'])


def beats(row):
    return [stage.get('beat') for stage in decode(row['stages']) if not stage.get('pending')]


def text_out(client, clock, kind='storyline'):
    """Sends the first text the storyline has ready, the way openers.py saves one; returns (trigger, message id)."""
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        found = [trigger for trigger in openers.candidates(connection, companion, clock.now())
                 if trigger.kind == kind and trigger.key.startswith('storyline:')]
        if not found:
            return None, None
        trigger, now = found[0], clock.now().isoformat()
        message_id = f'opener-{trigger.key}'
        seq = connection.execute('SELECT COALESCE(MAX(seq), 0) + 1 FROM messages WHERE timeline_id=?',
                                 (companion['active_timeline_id'],)).fetchone()[0]
        connection.execute("INSERT INTO messages (id, timeline_id, seq, role, text, status, active, character_version_id, "
                           "memory_revision, created_at, completed_at) VALUES (?, ?, ?, 'companion', ?, 'complete', 1, ?, "
                           '0, ?, ?)', (message_id, companion['active_timeline_id'], seq, trigger.template,
                                        companion['active_version_id'], now, now))
        connection.execute("INSERT INTO openers (id, timeline_id, trigger_key, kind, facts, message_id, wording, "
                           "created_at) VALUES (?, ?, ?, ?, '{}', ?, 'template', ?)",
                           (f'row-{message_id}', companion['active_timeline_id'], trigger.key, trigger.kind, message_id, now))
        openers.settle(connection, companion, {'id': message_id}, trigger, now)
        return trigger, message_id


def to_morning(clock, days=1):
    """The morning `days` on, 09:00."""
    target = datetime.combine(clock.now().date() + timedelta(days=days), datetime.min.time(), clock.now().tzinfo)
    clock.advance(target + timedelta(hours=9) - clock.now())


# The bank ---------------------------------------------------------------------------------------------------------

def every_beat():
    for story in shared_storylines.bank().values():
        for beat_id, beat in story['beats'].items():
            yield story, beat_id, beat


def test_the_bank_holds_together():
    tables = consequences.tables()
    for story in shared_storylines.bank().values():
        assert story['family'] in FAMILIES and story['level'] in range(4), story['key']
        assert story.get('cast') in (None, 'work', 'friend', 'family') or story['cast'] in storylines.casting.SINGLE
        reached = {next(iter(story['beats']))}
        for beat_id, beat in story['beats'].items():
            plan = beat['via'] == 'plan'
            assert beat['via'] in ('text', 'plan') and beat.get('tone', 'mixed') in ('good', 'bad', 'mixed')
            assert not plan or beat['plan']['activity'] in outings.ACTIVITIES
            assert not plan or beat.get('then'), f"{story['key']}:{beat_id}: a plan with nothing after it"
            for answer, found in (beat.get('then') or {}).items():
                assert answer in (PLAN_ANSWERS if plan else TEXT_ANSWERS), (story['key'], beat_id, answer)
                if isinstance(found, str):
                    ways = [found]
                elif 'impression' in found:
                    assert plan and beat['plan'].get('with') and 'any' in found['impression']
                    assert set(found['impression']) <= {*their_people.IMPRESSIONS, 'any'}
                    ways = list(found['impression'].values())
                else:
                    ways = found['beats']
                    assert len(tables[found['choice']]['options']) == len(ways), found['choice']
                    assert all('label' in option for option in tables[found['choice']]['options'])
                assert all(way in story['beats'] for way in ways), (story['key'], beat_id)
                reached |= set(ways)
            # No beat waits: whatever the user does, or does not do, something is written for it.
            assert not beat.get('then') or 'any' in beat['then'] or 'passed' in beat['then'], (story['key'], beat_id)
        assert reached == set(story['beats']), f"{story['key']}: a beat nothing leads to"


def test_every_beat_fills_in_for_the_screens_and_for_the_companion():
    names = {'p1': {'name': 'Kaito', 'role': 'friend', 'pronouns': 'he/him'}}
    row = {'cast_ids': '["p1"]'}
    for _story, _beat_id, beat in every_beat():
        shown = storylines.fill(beat['text'], row, names, {'name': 'Mira'})
        told = storylines.fill(beat['text'], row, names, {'name': 'Mira'}, you=True)
        assert '{' not in shown + told and shown[0].isupper() and told[0].isupper()
        # Told to the companion, they are "you" (never named, never "you wants") and the user is "the user".
        assert 'Mira' not in told and 'the user' not in shown
        assert not re.search(r"\b[Yy]ou (?:wants|says|is|has|keeps|was|asks|goes|plans)\b", told), told
        # "An ex of {name}'s got back in touch" was told as "An ex of your got back in touch".
        assert not re.search(r"\byour (?:got|is|was|has|had|and|who|did|came|went)\b", told), told
        share = beat.get('share', '')
        for word in ('{day}', '{time}', '{place}'):
            assert word not in share or beat['via'] == 'plan'
            share = share.replace(word, 'x')
        assert '{' not in storylines.fill(share, row, names, {'name': 'Mira'}) if share else True


def test_the_bank_is_big_enough_in_every_family_and_at_every_drama_level():
    bank = shared_storylines.bank().values()
    assert len(bank) >= 100  # The data bank rule: at least 100 entries.
    for family in FAMILIES:
        assert sum(story['family'] == family for story in bank) >= 10, family
    # Plenty can start in the quietest world, and in one where the two never meet in person (texts only).
    assert sum(story['level'] == 0 for story in bank) >= 50
    assert sum(not shared_storylines.plans(story) for story in bank) >= 50
    # "A third person" needs a dramatic world.
    assert all(story['level'] >= 2 for story in bank if story['family'] == 'a third person')


def test_every_turning_of_the_bank_has_its_odds_table_and_no_table_is_left_over():
    used = {found['choice'] for _story, _beat_id, beat in every_beat() for found in (beat.get('then') or {}).values()
            if isinstance(found, dict) and 'choice' in found}
    tables = consequences.tables()
    assert used == {key for key in tables if key.startswith('shared:')}
    for key in used:
        for option in tables[key]['options']:
            option['label'].format(name='Mira', a='Ana')
            for rule in option['rules']:
                rule['why'].format(name='Mira', a='Ana')


def test_the_words_of_the_bank_keep_to_the_writing_rules():
    family_casts = ('family', 'parent', 'employed parent', 'independent parent', 'unmarried sibling')
    for story, beat_id, beat in every_beat():
        where, text, share = (story['key'], beat_id), beat['text'], beat.get('share', '')
        # The companion is only ever {name} (the context turns it into "you"), never at the start of a later
        # sentence, and the share is in their own voice.
        assert not re.search(r'[.;:!?] \{name\}', text) and '{name}' not in share and '{user' not in share.lower(), where
        # "You" and "the user" take the same verb only in the past tense.
        assert not re.search(r'\{[uU]ser\} (?:is|was|has|does|needs|wants|says|likes|hopes|knows|thinks)\b', text), where
        assert not re.search(r"\{name\} (?:was|wants|says|asks|goes|plans|needs|knows|thinks|feels|does|isn't|hasn't|"
                             r"doesn't)\b", text), where
        # Someone has to be in the cast to be named.
        assert '{a' not in text + share or story.get('cast') not in (None, 'work'), where
        # A city of another era gets no story that names a phone or the internet.
        assert story.get('modern') or not re.search(r'\b(phone|online|text(?:ed|ing|s)?|internet|messaged|alarm|quiz)\b',
                                                    text + ' ' + share), where
        if beat['via'] != 'plan':
            continue
        plan = beat['plan']
        assert '{day}' in share and '{time}' in share, where
        if plan['activity'] == 'visit-in':
            assert story.get('apart'), where  # Asked over to their place: only while the two live apart.
        elif plan.get('with') and story['cast'] in family_casts:
            assert plan['activity'] == 'dinner' and 'dinner' in text, where  # With a relative it is dinner at theirs.
        else:
            assert '{place}' in share, where
            assert not plan.get('with') or plan['activity'] == 'drinks', where  # With a friend it is drinks.


def test_a_visit_to_their_place_only_fits_while_the_two_live_apart(client, clock):
    make(client)
    settled_in(client, clock)
    bank = shared_storylines.bank()
    with client.app.state.database.connect(write=True) as connection:
        companion, today = current(connection), clock.now().date()
        fits = lambda key: shared_storylines.fits(connection, companion, bank[key], today, clock.now())  # noqa: E731
        assert fits('flat_pack') and fits('hang_a_shelf') and fits('found_a_spot')
        connection.execute("INSERT INTO moving_in (id, timeline_id, plan, status, decided_on, moved_on, created_at) "
                           "VALUES ('m1', ?, 'theirs', 'moved', ?, ?, 'x')",
                           (companion['active_timeline_id'], today.isoformat(), today.isoformat()))
        assert not fits('flat_pack') and not fits('hang_a_shelf') and fits('found_a_spot')


def test_the_user_is_you_on_the_screens_and_the_user_to_the_companion():
    story = shared_storylines.bank()['curious_friend']
    names, row = {'p1': {'name': 'Kaito', 'role': 'friend', 'pronouns': 'he/him'}}, {'cast_ids': '["p1"]'}
    text = story['beats']['hit_it_off']['text']
    assert storylines.fill(text, row, names, {'name': 'Mira'}) == 'You came along for drinks, and Kaito took to you right away.'
    assert storylines.fill(text, row, names, {'name': 'Mira'}, you=True) == \
        'The user came along for drinks, and Kaito took to the user right away.'
    assert storylines.fill(story['beats']['asks']['text'], row, names, {'name': 'Mira'}, you=True) == \
        'Kaito keeps asking who you are always texting.'
    assert storylines.fill(story['beats']['polite']['text'], row, names, {'name': 'Mira'}).endswith('making up his mind.')


# Starting one -----------------------------------------------------------------------------------------------------

def test_nothing_starts_before_the_two_have_talked_or_while_the_user_is_away(client, clock, monkeypatch):
    monkeypatch.setattr(shared_storylines, 'CHANCE', (0, 1, 1, 1))
    make(client)
    assert not advance(client, clock) and not rows(client)
    talk(client, clock)
    clock.advance(timedelta(days=1))
    assert not advance(client, clock)  # Still settling in.
    clock.advance(timedelta(days=shared_storylines.AWAY_DAYS + 3))
    assert not advance(client, clock)  # The user has not written for days: nobody is there for it.
    talk(client, clock)
    clock.advance(timedelta(days=1))
    assert advance(client, clock) and len(rows(client)) == 1


def test_the_quiet_spell_floor_starts_one_for_sure(client, clock, monkeypatch):
    monkeypatch.setattr(shared_storylines, 'CHANCE', (0, 0, 0, 0))  # The dice never start one.
    make(client)
    settled_in(client, clock)
    days = 0
    while not advance(client, clock):
        clock.advance(timedelta(days=1))
        talk(client, clock)
        days += 1
        assert days <= shared_storylines.FLOOR[2]
    assert days == shared_storylines.FLOOR[2] - shared_storylines.REST[2]
    row = rows(client)[0]
    assert row['story'].startswith('shared:') and row['status'] == 'running'


def test_off_starts_none_and_often_starts_sooner(client, clock, monkeypatch):
    monkeypatch.setattr(shared_storylines, 'CHANCE', (0, 0, 0, 0))
    make(client)
    assert set_life(client, shared_storylines=0)['shared_storylines'] == 0
    settled_in(client, clock)
    assert started(client, clock, days=30) is None
    set_life(client, shared_storylines=3)
    assert started(client, clock, days=2) is not None


def test_the_roll_is_made_once_a_day(client, clock, monkeypatch):
    monkeypatch.setattr(shared_storylines, 'CHANCE', (0, 1, 1, 1))
    make(client)
    settled_in(client, clock)
    assert advance(client, clock)
    with client.app.state.database.connect(write=True) as connection:
        connection.execute("UPDATE storylines SET status='ended'")
    assert not advance(client, clock)  # Today's roll is spent.


def test_one_at_a_time_and_only_what_fits_the_world(client, clock, monkeypatch):
    monkeypatch.setattr(shared_storylines, 'CHANCE', (0, 1, 1, 1))
    make(client)
    settled_in(client, clock)
    row = started(client, clock)
    assert row is not None
    # Quiet to realistic drama: nothing from "a third person", which needs a dramatic world, and no romance-only one.
    assert shared_storylines.bank()[shared_storylines.key_of(row)]['level'] <= 1
    clock.advance(timedelta(days=1))
    talk(client, clock)
    advance(client, clock)
    assert len(rows(client)) == 1  # The one under way holds the next back.


def test_a_story_fits_by_drama_relationship_and_who_has_met_the_user(client, clock):
    make(client)
    settled_in(client, clock)
    bank = shared_storylines.bank()
    with client.app.state.database.connect(write=True) as connection:
        companion, today = current(connection), clock.now().date()
        fits = lambda key: shared_storylines.fits(connection, companion, bank[key], today, clock.now())  # noqa: E731
        assert not fits('ex_gets_in_touch')  # Dramatic and up, and a romance.
        friends = fits('curious_friend')
        assert len(friends) == 2 and not fits('bring_them_along')  # Nobody has met the user yet.
        assert fits('found_a_spot') == [()]
        connection.execute("INSERT INTO people_impressions (id, timeline_id, person_id, impression, warmth, met_on, "
                           "created_at, updated_at) VALUES ('i1', ?, ?, 'warm', 2, '2026-10-01', 'x', 'x')",
                           (companion['active_timeline_id'], friends[0][0]))
        assert fits('bring_them_along') == [friends[0]] and fits('curious_friend') == [friends[1]]
        assert not fits('what_were_you_like')  # They have only known each other a couple of days.


# A text, and what the user does about it --------------------------------------------------------------------------

def test_a_text_answered_goes_one_way(client, clock, only, monkeypatch):
    monkeypatch.setattr(shared_storylines, 'CHANCE', (0, 1, 1, 1))
    only('big_presentation')
    make(client, schedule=[{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00',
                            'days': [0, 1, 2, 3, 4]}])
    settled_in(client, clock)
    row = started(client, clock)
    assert beats(row) == ['nervous'] and decode(row['stages'])[-1]['pending'] == 'shared'
    trigger, _message = text_out(client, clock)
    assert trigger.key == f"storyline:{row['id']}:0" and 'nervous' in trigger.template
    assert 'You have a big presentation at work in a few days and told the user about the nerves.' in trigger.reason
    talk(client, clock, "You'll be great, you always are.")
    due = date.fromisoformat(decode(rows(client)[0]['stages'])[-1]['on'])
    to_morning(clock, (due - clock.now().date()).days)
    advance(client, clock)
    row = rows(client)[0]
    stages = decode(row['stages'])
    assert stages[0]['response'] == 'answered' and beats(row)[1] in ('went_well', 'went_fine')
    assert not stages[-1].get('pending')  # It ends there.
    # The consequence engine picked, with its odds and reasons, and the user can make it go the other way.
    outcome = client.get(f"/api/life/consequences/{stages[1]['consequence']}").json()
    assert outcome['choice'] == 'shared:steadied' and len(outcome['options']) == 2
    other = 1 - outcome['picked']
    changed = client.post(f"/api/life/consequences/{stages[1]['consequence']}/change", json={'option': other})
    assert changed.status_code == 200, changed.text
    assert beats(rows(client)[0])[1] == ('went_well', 'went_fine')[other]


def test_a_text_let_go_by_is_an_answer_too(client, clock, only, monkeypatch):
    monkeypatch.setattr(shared_storylines, 'CHANCE', (0, 1, 1, 1))
    only('big_presentation')
    make(client, schedule=[{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00',
                            'days': [0, 1, 2, 3, 4]}])
    settled_in(client, clock)
    row = started(client, clock)
    text_out(client, clock)
    due = date.fromisoformat(decode(row['stages'])[-1]['on'])
    to_morning(clock, (due - clock.now().date()).days)
    advance(client, clock)
    row = rows(client)[0]
    assert decode(row['stages'])[0]['response'] == 'passed' and beats(row) == ['nervous', 'got_through']


def test_a_text_just_sent_waits_for_its_answer(client, clock, only, monkeypatch):
    monkeypatch.setattr(shared_storylines, 'CHANCE', (0, 1, 1, 1))
    monkeypatch.setattr(shared_storylines, 'GAP', (1, 1))
    only('what_were_you_like')
    make(client)
    talk(client, clock)
    clock.advance(timedelta(days=15))
    talk(client, clock)
    row = started(client, clock)
    assert beats(row) == ['asks']
    with client.app.state.database.connect(write=True) as connection:  # Due tomorrow, whatever the dice gave.
        stages = decode(row['stages'])
        stages[-1]['on'] = (clock.now().date() + timedelta(days=1)).isoformat()
        shared_storylines.save(connection, row, stages)
    clock.advance(timedelta(hours=10))
    text_out(client, clock)  # Sent late in the day.
    clock.advance(timedelta(hours=5))
    advance(client, clock)
    assert beats(rows(client)[0]) == ['asks']  # The next day has come, but they have had five hours to answer.
    talk(client, clock, 'A menace. I climbed everything.')
    advance(client, clock)
    assert beats(rows(client)[0]) == ['asks', 'turning_it_over']


# A plan, and whether the user went --------------------------------------------------------------------------------

def plan_started(client, clock, only, monkeypatch, key='curious_friend'):
    monkeypatch.setattr(shared_storylines, 'CHANCE', (0, 1, 1, 1))
    only(key)
    make(client)
    settled_in(client, clock)
    return started(client, clock)


def invited(client, clock):
    """Goes on to the invitation and sends it; returns (trigger, the outing it booked)."""
    row = rows(client)[0]
    if beats(row) == ['asks'] and shared_storylines.key_of(row) == 'curious_friend':
        text_out(client, clock)
        due = date.fromisoformat(decode(row['stages'])[-1]['on'])
        to_morning(clock, (due - clock.now().date()).days + 1)
        advance(client, clock)
    trigger, message_id = text_out(client, clock, 'shared_plan')
    with client.app.state.database.connect() as connection:
        outing = optional(connection, 'SELECT * FROM outings WHERE message_id=?', (message_id,))
    return trigger, outings.view(outing) if outing else None


def test_an_invitation_books_a_plan_with_their_friend(client, clock, only, monkeypatch):
    row = plan_started(client, clock, only, monkeypatch)
    with client.app.state.database.connect() as connection:
        friend = optional(connection, 'SELECT * FROM circle_people WHERE id=?', (decode(row['cast_ids'])[0],))
    trigger, outing = invited(client, clock)
    first = friend['name'].split()[0]
    assert beats(rows(client)[0]) == ['asks', 'invite']
    assert outing['activity'] == 'meet-friends' and outing['status'] == 'planned'
    assert outing['place']['people'][0]['id'] == friend['id'] and outing['place']['first'] is True
    # The text names who, where, when; the prompt's reason has the same facts.
    assert first in trigger.template and outing['place']['name'] in trigger.template
    assert f"drinks at {outing['place']['name']} with your" in trigger.reason and first in trigger.reason
    assert outing['at_time'] in trigger.reason and '{' not in trigger.template + trigger.reason
    # What follows waits until the day after the plan.
    stages = decode(rows(client)[0]['stages'])
    assert stages[1]['outing'] == outing['id'] and stages[-1]['on'] > outing['local_date']
    # It is on Today's "Out together" like any plan.
    told = client.get('/api/life/storylines').json()[0]['beats']  # Today tells the invitation as a beat.
    assert len(told) == 2 and told[1]['share'] == '' and 'asked you along for drinks with' in told[1]['text']
    listed = client.get('/api/life/outings').json()['outings']
    assert any(item['id'] == outing['id'] and item['state'] == 'planned' for item in listed)


def test_going_makes_them_someone_who_knows_the_user(client, clock, only, monkeypatch):
    row = plan_started(client, clock, only, monkeypatch)
    friend_id = decode(row['cast_ids'])[0]
    _trigger, outing = invited(client, clock)
    to_morning(clock, (date.fromisoformat(outing['local_date']) - clock.now().date()).days + 1)
    advance(client, clock)
    row = rows(client)[0]
    stages = decode(row['stages'])
    assert stages[1]['response'] == 'went' and beats(row)[2] in ('hit_it_off', 'polite')
    with client.app.state.database.connect() as connection:
        made = optional(connection, 'SELECT * FROM people_impressions WHERE person_id=?', (friend_id,))
    assert made['met_on'] == outing['local_date']
    assert (beats(row)[2] == 'hit_it_off') == (made['impression'] in ('warm', 'smitten'))
    assert stages[2]['on'] == clock.now().date().isoformat() and not stages[-1].get('pending')


def test_calling_it_off_goes_another_way(client, clock, only, monkeypatch):
    row = plan_started(client, clock, only, monkeypatch)
    friend_id = decode(row['cast_ids'])[0]
    _trigger, outing = invited(client, clock)
    assert client.post(f"/api/life/outings/{outing['id']}/cancel").status_code == 200
    to_morning(clock, (date.fromisoformat(outing['local_date']) - clock.now().date()).days + 1)
    advance(client, clock)
    row = rows(client)[0]
    assert decode(row['stages'])[1]['response'] == 'called_off' and beats(row) == ['asks', 'invite', 'alone']
    with client.app.state.database.connect() as connection:  # They never met, so they have no opinion of the user.
        assert optional(connection, 'SELECT id FROM people_impressions WHERE person_id=?', (friend_id,)) is None


def test_an_invitation_that_never_went_out_passes(client, clock, only, monkeypatch):
    row = plan_started(client, clock, only, monkeypatch, 'found_a_spot')
    assert beats(row) == ['asks']
    due = date.fromisoformat(decode(row['stages'])[-1]['on'])
    to_morning(clock, (due - clock.now().date()).days)
    with client.app.state.database.connect() as connection:  # Too late to ask now.
        assert not shared_storylines.beats_due(connection, current(connection), clock.now())
    advance(client, clock)
    row = rows(client)[0]
    assert decode(row['stages'])[0]['response'] == 'passed' and beats(row) == ['asks', 'saved']


# The plan they kept without the user ------------------------------------------------------------------------------

def kept_plans(client, clock):
    with client.app.state.database.connect() as connection:
        return shared_storylines.as_plans(connection, current(connection), '0001-01-01', clock.now())


def slot_at(client, day, at):
    """The companion's agenda row that holds this local time (the tests run in UTC)."""
    moment = f'{day}T{at}:00'
    with client.app.state.database.connect() as connection:
        row = optional(connection, "SELECT * FROM life_agenda WHERE subject='companion' AND starts_at<=? AND ends_at>?",
                       (moment + 'Z', moment + 'Z')) or optional(
            connection, "SELECT * FROM life_agenda WHERE subject='companion' AND starts_at<=? AND ends_at>?",
            (moment + '+00:00', moment + '+00:00'))
    return row and {**row, 'entry': decode(row['entry']) if row['entry'] else None}


def test_a_plan_called_off_that_they_keep_is_in_their_day(client, clock, only, monkeypatch):
    row = plan_started(client, clock, only, monkeypatch)
    with client.app.state.database.connect() as connection:
        friend = optional(connection, 'SELECT * FROM circle_people WHERE id=?', (decode(row['cast_ids'])[0],))
    _trigger, outing = invited(client, clock)
    assert kept_plans(client, clock) == {}  # Still on: the evening is the outing's.
    assert client.post(f"/api/life/outings/{outing['id']}/cancel").status_code == 200
    # At once, not the morning after: the evening is theirs, with the friend, at the time it was booked for.
    [plan] = kept_plans(client, clock)[outing['local_date']]
    assert plan['at_time'] == outing['at_time'] and plan['kept']['with']['id'] == friend['id']
    reconcile(client)
    held = slot_at(client, outing['local_date'], outing['at_time'])
    first = friend['name'].split()[0]
    # A spot inside the place may follow (agenda.with_spot), as for any evening out.
    assert held['entry']['summary'].startswith(f'Mira Costa went for drinks with {first}.')
    assert held['entry']['storyline'] == {'id': row['id'], 'beat': 1} and held['entry']['with']['id'] == friend['id']
    assert held['entry']['activity'] == 'drinks' and held['entry']['place']['name'] == outing['place']['name']
    assert held['entry']['post'] is None and 'you' not in held['entry']['summary'].lower().split()
    # The morning after, the beat says the same evening, and the entry is still the one their day holds.
    to_morning(clock, (date.fromisoformat(outing['local_date']) - clock.now().date()).days + 1)
    reconcile(client)
    assert beats(rows(client)[0]) == ['asks', 'invite', 'alone']
    assert [item['id'] for item in kept_plans(client, clock)[outing['local_date']]] == [plan['id']]
    after = slot_at(client, outing['local_date'], outing['at_time'])
    assert after['id'] == held['id'] and after['entry']['summary'] == held['entry']['summary']
    with client.app.state.database.connect() as connection:
        [(_id, line)] = shared_storylines.context_lines(connection, current(connection), clock.now())
    assert f"on {outings.day_text(outing['local_date'])}: You went for drinks with {first} without the user" in line


def test_a_plan_the_user_came_to_is_not_kept_alone(client, clock, only, monkeypatch):
    plan_started(client, clock, only, monkeypatch)
    _trigger, outing = invited(client, clock)
    to_morning(clock, (date.fromisoformat(outing['local_date']) - clock.now().date()).days + 1)
    advance(client, clock)
    assert decode(rows(client)[0]['stages'])[1]['response'] == 'went' and kept_plans(client, clock) == {}


def test_a_plan_never_asked_is_kept_from_its_day_at_the_usual_time(client, clock, only, monkeypatch):
    row = plan_started(client, clock, only, monkeypatch, 'found_a_spot')
    planned = decode(row['stages'])[0]['plan_on']
    assert kept_plans(client, clock) == {}  # The invitation may still go out.
    to_morning(clock, (date.fromisoformat(planned) - clock.now().date()).days)
    [plan] = kept_plans(client, clock)[planned]
    assert plan['at_time'] == outings.ACTIVITIES['coffee'][2] and plan['kept']['with'] is None
    assert plan['kept']['summary'] == 'Mira Costa went to try the new place for coffee.' and plan['kept']['place'] is None
    entry = shared_storylines.entry(plan, {'weather': None}, {'name': 'Mira'})
    assert entry['place'] is None and entry['activity'] == 'coffee' and entry['storyline']['id'] == row['id']
    to_morning(clock)
    advance(client, clock)
    assert beats(rows(client)[0]) == ['asks', 'saved']
    assert [item['id'] for item in kept_plans(client, clock)[planned]] == [plan['id']]


def test_a_plan_they_drop_holds_nothing(client, clock, only, monkeypatch):
    plan_started(client, clock, only, monkeypatch, 'late_drink')
    _trigger, outing = invited(client, clock)
    assert client.post(f"/api/life/outings/{outing['id']}/cancel").status_code == 200
    assert kept_plans(client, clock) == {}  # "Skipped the drink and had an early night."


def test_every_kept_line_follows_a_plan_and_leaves_the_user_out():
    after_plan = {(story['key'], found) for story, _beat_id, beat in every_beat() if beat.get('via') == 'plan'
                  for answer, found in beat['then'].items() if answer != 'went' and isinstance(found, str)}
    kept = [(story, beat_id, beat) for story, beat_id, beat in every_beat() if 'kept' in beat]
    assert len(kept) >= 20
    for story, beat_id, beat in kept:
        where = f"{story['key']}.{beat_id}"
        assert (story['key'], beat_id) in after_plan, where
        assert beat['kept'].startswith('{name} ') and beat['kept'].endswith('.'), where
        assert set(re.findall(r'{(\w+)}', beat['kept'])) <= {'name', 'a'}, where
        assert not story['beats'][beat_id].get('then'), where
    # A beat that says they went, after a plan the user did not come to, has its line.
    for story, beat_id, beat in every_beat():
        if (story['key'], beat_id) in after_plan and re.match(r'{name} went (?!with)', beat['text']):
            assert 'kept' in beat, f"{story['key']}.{beat_id}"


def test_a_plan_at_their_place(client, clock, only, monkeypatch):
    plan_started(client, clock, only, monkeypatch, 'flat_pack')
    trigger, outing = invited(client, clock)
    assert outing['activity'] == 'visit-in' and 'Come over' in trigger.template and '{' not in trigger.template
    assert 'You are asking the user over to your place on' in trigger.reason


def test_never_two_beats_on_one_day(client, clock, monkeypatch):
    monkeypatch.setattr(shared_storylines, 'CHANCE', (0, 1, 1, 1))
    make(client)
    settled_in(client, clock)
    for _day in range(40):
        advance(client, clock)
        text_out(client, clock) or text_out(client, clock, 'shared_plan')
        clock.advance(timedelta(days=1))
        talk(client, clock)
    days = [stage['on'] for row in rows(client) for stage in decode(row['stages']) if not stage.get('pending')]
    assert len(rows(client)) >= 3 and len(days) == len(set(days))


# Told like any other storyline ------------------------------------------------------------------------------------

def test_today_lists_it_and_the_context_tells_it(client, clock, only, monkeypatch):
    row = plan_started(client, clock, only, monkeypatch)
    listed = client.get('/api/life/storylines').json()
    assert listed[0]['with_you'] is True and listed[0]['unfolding'] is True
    assert 'keeps asking who Mira Costa is always texting.' in listed[0]['beats'][0]['text']
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        lines = [line for _key, line in shared_storylines.context_lines(connection, companion, clock.now())]
        assert len(lines) == 1 and 'keeps asking who you are always texting.' in lines[0]
        # The storylines about other people leave it to that line (their heading says "never to the user").
        assert not storylines.context_lines(connection, companion, clock.now())
        # It is not the town's news, and the generic storyline text leaves it to this module's own.
        assert not news.found(connection, companion, clock.now())
        assert not storylines.fresh_beats(connection, companion, clock.now())
    assert client.post(f"/api/life/storylines/{row['id']}/end").status_code == 200
    advance(client, clock)
    assert rows(client)[0]['status'] == 'ended' and not client.get('/api/life/storylines').json()


# The chat context: the storyline, each beat's day and the user's part in it --------------------------------------

def told(client, clock):
    with client.app.state.database.connect() as connection:
        (_key, line), = shared_storylines.context_lines(connection, current(connection), clock.now())
    return line


def test_the_context_says_whether_the_user_has_heard_and_answered(client, clock, only, monkeypatch):
    row = plan_started(client, clock, only, monkeypatch)
    day = outings.day_text(row['started_on'])
    assert told(client, clock).startswith(f'- On {day}: ') and 'keeps asking who you are always texting.' in told(
        client, clock)
    assert told(client, clock).endswith(f'{shared_storylines.UNTOLD} {shared_storylines.OPEN}')
    text_out(client, clock)
    assert told(client, clock).endswith(f'{shared_storylines.TEXT_PART[None]} {shared_storylines.OPEN}')
    talk(client, clock, 'Ha, who is asking?')
    assert told(client, clock).endswith(f"{shared_storylines.TEXT_PART['answered']} {shared_storylines.OPEN}")


def test_the_context_says_when_a_text_was_let_go_by(client, clock, only, monkeypatch):
    monkeypatch.setattr(shared_storylines, 'CHANCE', (0, 1, 1, 1))
    only('what_were_you_like')
    make(client)
    talk(client, clock)
    clock.advance(timedelta(days=15))
    talk(client, clock)
    started(client, clock)
    text_out(client, clock)
    clock.advance(shared_storylines.WINDOW)
    assert told(client, clock).endswith(f"{shared_storylines.TEXT_PART['passed']} {shared_storylines.OPEN}")


def test_the_context_follows_an_invitation_to_how_it_went(client, clock, only, monkeypatch):
    plan_started(client, clock, only, monkeypatch)
    text_out(client, clock)
    row = rows(client)[0]
    to_morning(clock, (date.fromisoformat(decode(row['stages'])[-1]['on']) - clock.now().date()).days + 1)
    advance(client, clock)
    assert told(client, clock).endswith(f'{shared_storylines.UNASKED} {shared_storylines.OPEN}')
    _trigger, outing = invited(client, clock)
    when = f"it is set for {outings.day_text(outing['local_date'])} at {outing['at_time']}; it has not happened yet."
    assert told(client, clock).endswith(f'You asked the user, and {when} {shared_storylines.OPEN}')
    # The evening is over and the morning after has not come: they went, and what it led to is still open.
    clock.advance(datetime.combine(date.fromisoformat(outing['local_date']), datetime.max.time(), clock.now().tzinfo)
                  - clock.now())
    assert told(client, clock).endswith(f"{shared_storylines.PLAN_PART['went']} {shared_storylines.OPEN}")
    to_morning(clock)
    advance(client, clock)
    # Over: the last beat says how it went, dated to the evening itself, and nothing is left open.
    line = told(client, clock)
    assert f"Then, on {outings.day_text(outing['local_date'])}: The user came along for drinks" in line
    assert shared_storylines.OPEN not in line and line.count('Then, on ') == 2


def test_the_context_says_a_plan_was_called_off(client, clock, only, monkeypatch):
    plan_started(client, clock, only, monkeypatch)
    _trigger, outing = invited(client, clock)
    assert client.post(f"/api/life/outings/{outing['id']}/cancel").status_code == 200
    assert told(client, clock).endswith(f"{shared_storylines.PLAN_PART['called_off']} {shared_storylines.OPEN}")
    to_morning(clock, (date.fromisoformat(outing['local_date']) - clock.now().date()).days + 1)
    advance(client, clock)
    assert f"Then, on {outings.day_text(outing['local_date'])}: You went for drinks with" in told(client, clock)


def test_the_chat_prompt_tells_it_in_its_own_section(client, clock, only, monkeypatch, provider):
    plan_started(client, clock, only, monkeypatch)
    text_out(client, clock)
    talk(client, clock, 'Ha, who is asking?')
    prompt = provider.requests[-1]['prompt']
    assert f'## {shared_storylines.HEADING}\n{told(client, clock)}\n' in prompt
    assert 'never to the user' not in prompt  # No other storyline is running, so that section is not there.


def test_the_first_text_goes_out_through_the_openers(client, clock, only, monkeypatch):
    plan_started(client, clock, only, monkeypatch)
    with client.app.state.database.connect() as connection:
        found = [trigger for trigger in openers.candidates(connection, current(connection), clock.now())
                 if trigger.key.startswith('storyline:')]
    assert len(found) == 1 and found[0].kind == 'storyline' and 'smiled at my phone' in found[0].template


def test_a_fork_keeps_what_happened_and_decides_the_rest_itself(client, clock, only, monkeypatch):
    row = plan_started(client, clock, only, monkeypatch)
    with client.app.state.database.connect(write=True) as connection:
        stages = shared_storylines.fork_stages(connection, row, 'copy', row['timeline_id'], clock.now().date().isoformat())
    assert [stage.get('beat') for stage in stages] == ['asks', None] and stages[-1]['pending'] == 'shared'
    assert stages[-1]['on'] > clock.now().date().isoformat()


def test_the_slider_is_a_life_setting(client):
    assert client.get('/api/life/settings').json()['shared_storylines'] == 2
    assert client.put('/api/life/settings', json={'shared_storylines': 4}).status_code == 422
    assert set_life(client, shared_storylines=1)['shared_storylines'] == 1


# The screens: Today's "Things that involve you" and the scrapbook ------------------------------------------------

def shown(client):
    return client.get('/api/life/storylines').json()


def test_today_says_the_users_part_in_each_beat(client, clock, only, monkeypatch):
    plan_started(client, clock, only, monkeypatch)
    # Before the text is out the user has no part; once it is, it says so until they answer or let it go by.
    first, = shown(client)[0]['beats']
    assert first['via'] == 'text' and 'you' not in first
    text_out(client, clock)
    assert shown(client)[0]['beats'][0]['you'] == {'did': 'texted'}
    talk(client, clock, 'Ha, who is asking?')
    assert shown(client)[0]['beats'][0]['you'] == {'did': 'answered'}
    _trigger, outing = invited(client, clock)
    assert shown(client)[0]['beats'][1]['you'] == {'did': 'set', 'on': outing['local_date'], 'at': outing['at_time']}
    # The plan card on Today points back to the storyline.
    listed = client.get('/api/life/outings').json()['outings']
    assert next(item for item in listed if item['id'] == outing['id'])['place']['storyline'] == shown(client)[0]['id']
    to_morning(clock, (date.fromisoformat(outing['local_date']) - clock.now().date()).days + 1)
    advance(client, clock)
    told = shown(client)[0]
    assert told['beats'][1]['you'] == {'did': 'went'} and not told['unfolding']
    assert told['beats'][2]['via'] == 'text' and 'you' not in told['beats'][2]  # Nothing follows it: no part.


def test_a_plan_called_off_says_so_on_today(client, clock, only, monkeypatch):
    plan_started(client, clock, only, monkeypatch)
    _trigger, outing = invited(client, clock)
    assert client.post(f"/api/life/outings/{outing['id']}/cancel").status_code == 200
    assert shown(client)[0]['beats'][1]['you'] == {'did': 'called_off'}


def test_it_stays_on_today_a_week_and_then_the_scrapbook_keeps_it(client, clock, only, monkeypatch):
    row = plan_started(client, clock, only, monkeypatch)
    _trigger, outing = invited(client, clock)
    to_morning(clock, (date.fromisoformat(outing['local_date']) - clock.now().date()).days + 1)
    advance(client, clock)
    last = clock.now().date()

    def page():
        book = client.get('/api/life/year/so-far').json()
        return next((item for item in book['pages'] if item['kind'] == 'with-you'), None)
    clock.advance(timedelta(days=shared_storylines.STAYS))
    assert len(shown(client)) == 1
    clock.advance(timedelta(days=1))
    assert not shown(client) and len(client.get('/api/life/storylines?include_ended=true').json()) == 1
    found = page()
    assert found['title'] == 'Things you were part of' and len(found['items']) == 1
    entry = found['items'][0]
    assert entry['date'] == row['started_on'] and entry['until'] == last.isoformat()
    # Told beat by beat; a plan needs no line of its own, the beat after it says they came.
    assert 'keeps asking who Mira Costa is always texting.' in entry['text']
    assert 'who wants to meet you. You came along for drinks' in entry['text'] and 'You went.' not in entry['text']
    assert '{' not in entry['text']
    # One the user ended is not kept.
    assert client.post(f"/api/life/storylines/{row['id']}/end").status_code == 200
    assert page() is None


def test_the_scrapbook_waits_until_it_is_over(client, clock, only, monkeypatch):
    plan_started(client, clock, only, monkeypatch)
    book = client.get('/api/life/year/so-far').json()
    assert all(item['kind'] != 'with-you' for item in book['pages'])


def test_the_scrapbook_says_the_users_part_where_a_text_turned_the_story():
    story = shared_storylines.bank()['good_news_first']
    assert shared_storylines.turned(story, {'beat': 'tells', 'response': 'answered'}) == 'You wrote back.'
    assert shared_storylines.turned(story, {'beat': 'tells', 'response': 'passed'}) == ''  # Any other way: no line.
    assert shared_storylines.turned(story, {'beat': 'celebrate', 'response': 'went'}) == ''
    assert shared_storylines.turned(None, {'beat': 'tells', 'response': 'answered'}) == ''
    for found, beat_id, beat in every_beat():
        for response in beat.get('then') or {}:
            if beat.get('via') != 'plan' and response != 'any':
                assert shared_storylines.turned(found, {'beat': beat_id, 'response': response})
