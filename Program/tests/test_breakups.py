"""Breaks and breakups (companion/life/breakups.py): warnings that grow out of rough patches, a break, exes, and
getting back together."""
import json
import re
from datetime import date, timedelta
from pathlib import Path

import pytest
from conftest import reconcile, send, set_life, show
from test_together import mira, notes, says

from companion import consequences
from companion.characters import current
from companion.life import breakups, moving_in, openers, rough_patches, steps

BANKS = Path(__file__).resolve().parents[1] / 'companion' / 'world' / 'data' / 'breakups'


@pytest.fixture
def couple(client, monkeypatch):
    """Mira as a romance in Baltimore, rough patches and breakups on, and every roll moving things on."""
    monkeypatch.setattr(rough_patches, 'ACTIVE', True)
    monkeypatch.setattr(breakups, 'ACTIVE', True)
    monkeypatch.setattr(consequences, 'roll', lambda seed, found: found[-1]['option'])
    mira(client, monkeypatch, relationship='romance')


def view(client):
    response = client.get('/api/life/breakup')
    assert response.status_code == 200, response.text
    return response.json()


def tick(client):
    """The agenda's daily pass, for rough patches and then breakups."""
    database = client.app.state.database
    with database.connect(write=True) as connection:
        companion = current(connection)
        rough_patches.daily(connection, companion, database.clock.now())
        breakups.daily(connection, companion, database.clock.now())


def triggers(client):
    database = client.app.state.database
    with database.connect() as connection:
        return [trigger for trigger in openers.candidates(connection, current(connection), database.clock.now())]


def test_every_bank_has_a_hundred_entries_and_no_gendered_words():
    for name in ('break_asks', 'ending', 'reaching_out', 'falling_out'):
        entries = json.loads((BANKS / f'{name}.json').read_text(encoding='utf-8'))['templates']
        assert len(entries) >= 100 and len(set(entries)) == len(entries), name
        for entry in entries:
            assert not any(word in f' {entry.lower()} ' for word in (' he ', ' she ', ' his ', ' her ', ' him ')), entry


def test_ending_it_a_break_and_trying_again_are_read_from_the_message():
    assert breakups.said(breakups.BREAK_UP, "I'm breaking up with you.")
    assert breakups.said(breakups.BREAK_UP, 'I think we should break up')
    assert breakups.said(breakups.BREAK_UP, "it's over between us")
    assert not breakups.said(breakups.BREAK_UP, "I don't want to break up")
    assert not breakups.said(breakups.BREAK_UP, 'my sister said we should break up lol')
    assert breakups.said(breakups.TAKE_BREAK, 'I think we should take a break')
    assert breakups.said(breakups.TAKE_BREAK, 'I need some space from us')
    assert not breakups.said(breakups.TAKE_BREAK, 'I need a break from work')
    assert breakups.said(breakups.COME_BACK, 'can we try again?')
    assert breakups.said(breakups.COME_BACK, 'I want you back')
    assert breakups.said(breakups.FRIENDS_END, "I don't want to be friends anymore")


def test_a_rough_patch_that_drags_on_strains_things_then_a_break_then_it_ends(client, couple, provider, clock):
    set_life(client, rough_patches_realism=3)
    says(provider)
    send(client, 'shut up', 'client-break-1')
    tick(client)
    assert view(client)['stage'] is None
    clock.advance(timedelta(days=2, hours=1))
    tick(client)
    found = view(client)
    assert found['stage'] == 'strained' and found['text'] == 'Things are strained' and found['strip']
    says(provider)
    send(client, 'hey', 'client-break-2')
    assert 'Things have been strained between you and the user lately' in notes(provider)
    clock.advance(timedelta(days=3, hours=1))
    tick(client)
    assert view(client)['text'] == "They're thinking about a break"
    clock.advance(timedelta(days=3, hours=1))
    tick(client)
    assert view(client)['stage'] == 'break'
    asks = [trigger for trigger in triggers(client) if trigger.kind == 'breakup']
    assert asks and asks[0].template in breakups.bank('break_asks')
    assert not any(trigger.kind == 'check_in' for trigger in triggers(client))
    says(provider)
    send(client, 'are you there?', 'client-break-3')
    assert 'You have decided you need a break from the user' in notes(provider)
    says(provider)
    send(client, 'ok', 'client-break-4')
    assert 'You and the user have been on a break since' in notes(provider)
    clock.advance(timedelta(days=21, hours=1))
    tick(client)
    found = view(client)
    assert found['stage'] == 'ended' and found['text'] == 'Broke up' and found['by'] == 'them'
    says(provider)
    send(client, 'hi', 'client-break-5')
    prompt = notes(provider)
    assert 'you have decided to end things with the user for good' in prompt
    assert 'Keep to where things stand' not in prompt  # The steps line gives way to the breakup.


def test_the_user_ends_it_and_asks_to_get_back_together(client, couple, provider, clock):
    client.put('/api/life/steps', json={'step': 'married'})
    says(provider)
    send(client, "I'm sorry but I'm breaking up with you.", 'client-end-1')
    assert 'The user just broke up with you' in notes(provider)
    found = view(client)
    assert found['stage'] == 'ended' and found['by'] == 'you'
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        assert steps.apart(connection, companion) == 'ended' and not steps.exclusive(connection, companion, clock.now())
    clock.advance(timedelta(days=20))
    says(provider)
    send(client, 'can we try again?', 'client-end-2')
    assert 'The user asked to get back together, and you want that too' in notes(provider)
    assert view(client)['stage'] is None
    stepped = client.get('/api/life/steps').json()
    assert stepped['step'] == 'key'  # Starting over: living together and the marriage are taken back.
    with client.app.state.database.connect() as connection:
        items = breakups.scrapbook_items(connection, current(connection), '2000-01-01', '2100-01-01')
    assert {'You broke up', 'You got back together', 'You got married'} <= {item['text'] for item in items}


def test_breaking_up_while_living_together_they_move_out(client, couple, provider, clock, monkeypatch):
    from test_moving_in import ask_to_move_in, moving_day
    monkeypatch.setattr(consequences, 'roll', lambda seed, found: found[0]['option'])  # Yes, at your place.
    ask_to_move_in(client, provider)
    moving_day(client, clock)
    says(provider)
    send(client, "I'm breaking up with you.", 'client-out-1')
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        found = moving_in.latest(connection, companion['active_timeline_id'])
        assert found['status'] == 'moved_out' and not moving_in.living(connection, companion)
    clock.advance(timedelta(days=1, hours=1))
    reconcile(client)  # The daily pass leaves them moved out: the step stands, but they moved out since.
    with client.app.state.database.connect() as connection:
        assert moving_in.latest(connection, current(connection)['active_timeline_id'])['status'] == 'moved_out'
    says(provider)
    send(client, 'hi', 'client-out-2')
    # Moving in is no longer how their life is now (the history section still says it happened).
    assert not re.search(r"You moved into the user's place in [^.]*\. This is how your life is now", notes(provider))


def test_asking_for_a_break_and_talking_them_round(client, couple, provider):
    says(provider)
    send(client, 'I think we should take a break.', 'client-pause-1')
    assert 'The user just asked for a break' in notes(provider)
    assert view(client)['stage'] == 'break'
    says(provider)
    send(client, 'I miss us. can we try again?', 'client-pause-2')
    assert 'The user asked to try again, and you want that too' in notes(provider)
    assert view(client)['stage'] is None


def test_switched_off_nothing_happens(client, couple, provider):
    set_life(client, breakups=False)
    says(provider)
    send(client, "I'm breaking up with you", 'client-off-1')
    assert view(client)['stage'] is None and view(client)['on'] is False


def test_a_friendship_falls_out_and_the_override_makes_up(client, monkeypatch, provider):
    monkeypatch.setattr(breakups, 'ACTIVE', True)
    mira(client, monkeypatch, relationship='friendship')
    says(provider)
    send(client, "I don't want to be friends anymore", 'client-friend-1')
    assert 'they do not want to be friends anymore' in notes(provider)
    found = view(client)
    assert found['stage'] == 'ended' and found['text'] == 'Fell out'
    response = client.post(f"/api/life/breakup/{found['id']}/mend")
    assert response.status_code == 200 and response.json()['stage'] is None
    assert client.post(f"/api/life/breakup/{found['id']}/undo").json()['stage'] == 'ended'


def test_a_warning_can_be_changed_on_today(client, couple, provider, clock):
    show(client, show_moods=True, show_odds=True)
    says(provider)
    send(client, 'go away', 'client-today-1')
    clock.advance(timedelta(days=2, hours=1))
    tick(client)
    found = view(client)
    assert found['stage'] == 'strained' and found['odds']
    [outcome] = [item for item in client.get('/api/life/reactions').json() if item['choice'] == 'user:strained']
    reasons = outcome['options'][1]['reasons']
    assert all(reason[0].islower() or reason.startswith('Mira') for reason in reasons)
    client.post(f"/api/life/consequences/{outcome['id']}/change", json={'option': 0})
    assert view(client)['stage'] is None


def test_an_ending_changed_on_today_moves_them_back_in_and_out_again(client, couple, provider, clock, monkeypatch):
    from test_moving_in import ask_to_move_in, moving_day
    monkeypatch.setattr(consequences, 'roll', lambda seed, found: found[0]['option'])  # Yes, at your place.
    ask_to_move_in(client, provider)
    moving_day(client, clock)
    says(provider)
    send(client, 'I think we should take a break.', 'client-back-1')
    monkeypatch.setattr(consequences, 'roll', lambda seed, found: found[-1]['option'])  # They end it.
    clock.advance(timedelta(days=21, hours=1))
    tick(client)
    database = client.app.state.database
    with database.connect() as connection:
        companion = current(connection)
        assert view(client)['stage'] == 'ended' and not moving_in.living(connection, companion)
        ended_id = breakups.rows(connection, companion['active_timeline_id'])[-1]['ended_id']
    response = client.post(f'/api/life/consequences/{ended_id}/change', json={'option': breakups.TOGETHER})
    assert response.status_code == 200, response.text
    assert view(client)['stage'] is None
    with database.connect() as connection:
        companion = current(connection)
        assert moving_in.living(connection, companion)
        homes = [item for item in moving_in.home.items_on(connection, companion['active_timeline_id'],
                                                          breakups.local_today(companion, clock.now()))
                 if item['kind'] == 'home']
        assert len(homes) == 1 and homes[0]['shared']  # Their own place is gone again: the shared home is back.
    client.post(f'/api/life/consequences/{ended_id}/change', json={'option': breakups.ENDS})
    assert view(client)['stage'] == 'ended'
    with database.connect() as connection:
        assert not moving_in.living(connection, current(connection))


def test_an_ex_writes_on_the_users_birthday_but_not_about_the_day_they_met(client, couple, provider, monkeypatch):
    from companion.life import occasions
    found = [occasions.occasion('anniversary', date.today(), 0, '100 days since you and the user first talked', '',
                                span='100 days'),
             occasions.occasion('user_birthday', date.today(), 0, "the user's birthday", ''),
             occasions.occasion('own_birthday', date.today(), 0, 'your birthday', '')]
    monkeypatch.setattr(occasions, 'occasions', lambda *_args: found)
    assert {trigger.key.split(':')[1] for trigger in triggers(client) if trigger.kind == 'occasion'} == {
        'anniversary', 'user_birthday', 'own_birthday'}
    says(provider)
    send(client, "I'm breaking up with you.", 'client-ex-1')
    assert [trigger.key.split(':')[1] for trigger in triggers(client) if trigger.kind == 'occasion'] == ['user_birthday']


def test_an_ex_in_a_group_chat_knows_they_broke_up(client, couple, provider):
    from test_groups import by_speaker, companion_named, say, start
    says(provider)
    send(client, "I'm breaking up with you.", 'client-group-1')
    provider.respond = by_speaker
    with client.app.state.database.connect() as connection:
        mira_id = current(connection)['id']
    group = start(client, [mira_id, companion_named(client, 'Billy Hart')])
    say(client, group['id'], 'Hi both', 'client-group-2')
    prompts = [request['prompt'] for request in provider.requests if 'You are Mira' in request['prompt']]
    assert prompts and 'You and the user broke up on' in prompts[-1]
    assert 'The user just broke up with you' not in prompts[-1]  # Only where things stand, in a group.


def test_switched_off_after_a_breakup_the_ex_still_knows_it(client, couple, provider):
    says(provider)
    send(client, "I'm breaking up with you.", 'client-later-off-1')
    set_life(client, breakups=False)
    says(provider)
    send(client, 'hey', 'client-later-off-2')
    assert 'You and the user broke up on' in notes(provider)
    assert view(client)['stage'] == 'ended'


def test_a_roll_that_held_things_back_changed_on_today_moves_them_on_at_once(client, couple, provider, clock,
                                                                             monkeypatch):
    show(client, show_moods=True, show_odds=True)
    set_life(client, rough_patches_realism=3)
    says(provider)
    send(client, 'shut up', 'client-held-1')
    clock.advance(timedelta(days=2, hours=1))
    tick(client)
    assert view(client)['stage'] == 'strained'
    monkeypatch.setattr(consequences, 'roll', lambda seed, found: found[0]['option'])  # They work through it.
    clock.advance(timedelta(days=3, hours=1))
    tick(client)
    assert view(client)['stage'] == 'strained'
    [outcome] = [item for item in client.get('/api/life/reactions').json() if item['choice'] == 'user:thinking']
    response = client.post(f"/api/life/consequences/{outcome['id']}/change", json={'option': breakups.YES})
    assert response.status_code == 200, response.text
    assert view(client)['text'] == "They're thinking about a break"
    client.post(f"/api/life/consequences/{outcome['id']}/change", json={'option': 0})
    assert view(client)['stage'] == 'strained'


def test_a_branch_from_after_a_breakup_keeps_it_and_one_from_before_does_not(client, couple, provider, clock):
    says(provider)
    before = send(client, 'hello', 'client-fork-1')['message']
    clock.advance(timedelta(minutes=10))
    says(provider)
    send(client, "I'm breaking up with you.", 'client-fork-2')
    clock.advance(timedelta(minutes=10))
    says(provider)
    after = send(client, 'bye then', 'client-fork-3')['message']
    forks = {}
    for name, message in (('before', before), ('after', after)):
        response = client.post('/api/timelines', json={'message_id': message['id']})
        assert response.status_code == 200, response.text
        forks[name] = response.json()['id']
    for name, stage in (('after', 'ended'), ('before', None)):
        assert client.post(f'/api/timelines/{forks[name]}/activate').status_code == 200
        assert view(client)['stage'] == stage, name


def test_a_move_not_made_yet_waits_while_they_are_on_a_break(client, couple, provider, clock, monkeypatch):
    from test_moving_in import ask_to_move_in, row
    monkeypatch.setattr(consequences, 'roll', lambda seed, found: found[0]['option'])  # Yes, at your place.
    monkeypatch.setattr(breakups, 'BREAK_DAYS', {2: 60, 3: 60})  # The break lasts past moving day.
    ask_to_move_in(client, provider)
    days = (date.fromisoformat(row(client)['move_on']) - clock.now().date()).days
    says(provider)
    send(client, 'I think we should take a break.', 'client-wait-1')
    clock.advance(timedelta(days=days, hours=1))
    reconcile(client)
    assert row(client)['status'] == 'moving'
    says(provider)
    send(client, 'hi', 'client-wait-2')
    assert "moving into the user's place" not in notes(provider)
    monkeypatch.setattr(consequences, 'roll', lambda seed, found: found[-1]['option'])  # Yes, they try again.
    says(provider)
    send(client, 'can we try again?', 'client-wait-3')
    assert view(client)['stage'] is None
    clock.advance(timedelta(days=1, hours=1))
    reconcile(client)
    assert row(client)['status'] == 'moved'
