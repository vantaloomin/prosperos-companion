"""Rough patches and making up (companion/life/rough_patches.py): what starts one, how it colors the chat, and how it
mends."""
import json
from datetime import timedelta
from pathlib import Path

import pytest
from conftest import reconcile, send, set_life, show
from test_openers import check, history
from test_together import mira, notes, says

from companion import consequences, moods
from companion.characters import current, insert_version
from companion.database import identifier
from companion.life import breakups, love_life, openers, rough_patches
from companion.models import CharacterDefinition

BANKS = Path(__file__).resolve().parents[1] / 'companion' / 'world' / 'data' / 'rough_patches'


@pytest.fixture
def patches(client, monkeypatch):
    """Rough patches on, every roll landing on a rough patch, and Mira in Baltimore with evenings free."""
    monkeypatch.setattr(rough_patches, 'ACTIVE', True)
    monkeypatch.setattr(consequences, 'roll', lambda seed, found: found[-1]['option'])
    mira(client, monkeypatch)


def patch(client):
    response = client.get('/api/life/rough-patch')
    assert response.status_code == 200, response.text
    return response.json()


def test_every_bank_has_a_hundred_entries_and_no_gendered_words():
    for name in ('apologies', 'gestures', 'accepting', 'stand_up_reasons', 'companion_apologies', 'companion_confessions'):
        data = json.loads((BANKS / f'{name}.json').read_text(encoding='utf-8'))
        entries = data.get('phrases') or data.get('reasons') or data['templates']
        assert len(entries) >= 100 and len(set(entries)) == len(entries), name
        for entry in entries:
            assert not any(word in f' {entry.lower()} ' for word in (' he ', ' she ', ' his ', ' her ', ' him ')), entry


def test_apologies_gestures_and_words_are_read_from_the_message():
    assert rough_patches.says('apologies', "I'm sorry about earlier, I didn’t mean it")
    assert rough_patches.says('apologies', 'ok my bad')
    assert not rough_patches.says('apologies', "I'm not sorry")
    assert not rough_patches.says('apologies', "I'm sorry you feel that way")
    assert not rough_patches.says('apologies', "I don't think I was wrong")
    assert rough_patches.says('gestures', '*hands you a coffee* peace offering?')
    assert rough_patches.says('gestures', "let me make it up to you, dinner's on me")
    assert rough_patches.says('accepting', "it's okay, these things happen")
    assert rough_patches.stings('Ugh, shut up.') == 'Ugh, shut up.'
    assert rough_patches.stings("you're so annoying lol") is None
    assert rough_patches.stings('this game is annoying') is None
    assert rough_patches.stings("I'd never say you're useless") is None


def test_words_that_sting_start_one_and_an_apology_mends_it(client, patches, provider):
    says(provider)
    send(client, "you're so annoying. go away", 'client-patch-1')
    found = patch(client)
    assert found['open'] and found['text'] == 'Things are a bit tense' and found['about'] is None
    says(provider)
    send(client, 'so what are you up to?', 'client-patch-2')
    assert 'Things are tense between you and the user right now. What happened: the user said to you: "you' in notes(provider)
    with client.app.state.database.connect() as connection:
        assert rough_patches.cool(connection, current(connection), client.app.state.database.clock.now())
    says(provider)
    send(client, "I'm really sorry, I shouldn't have said that", 'client-patch-3')
    assert 'They just apologised, and that is enough for you' in notes(provider)
    assert not patch(client)['open']


def test_it_shows_what_about_with_moods_shown_and_can_be_let_go(client, patches, provider):
    show(client, show_moods=True)
    says(provider)
    send(client, 'shut up', 'client-patch-4')
    found = patch(client)
    assert found['about'] == 'over what you said: "shut up"'
    response = client.post(f"/api/life/rough-patch/{found['id']}/let-go")
    assert response.status_code == 200 and not response.json()['open']
    assert client.post(f"/api/life/rough-patch/{found['id']}/undo").json()['open']
    assert rough_patches.quoted('x' * 80) == 'x' * 59 + '…'


def test_let_it_go_clears_the_air_over_everything_open(client, patches, provider):
    show(client, show_moods=True)
    for number, text in enumerate(('go away', 'leave me alone')):
        says(provider)
        send(client, f'{text}.', f'client-patch-4{number}')
    found = patch(client)
    assert found['about'] in ('over what you said: "go away"', 'over what you said: "leave me alone"')
    assert not client.post(f"/api/life/rough-patch/{found['id']}/let-go").json()['open']
    assert not patch(client)['open']  # Not the one before it instead.
    client.post(f"/api/life/rough-patch/{found['id']}/undo")
    assert patch(client)['id'] == found['id']
    with client.app.state.database.connect() as connection:
        assert len(rough_patches.open_rows(connection, current(connection), 2, client.app.state.database.clock.now())) == 2


def test_the_odds_can_be_changed_on_today(client, patches, provider):
    show(client, show_moods=True)
    says(provider)
    send(client, 'leave me alone', 'client-patch-5')
    [outcome] = [item for item in client.get('/api/life/reactions').json() if item['choice'] == 'user:rough_patch']
    assert outcome['picked'] == 1
    # Today reads it as "you", not the line the companion is told (E2E v0.13).
    assert outcome['label'] == 'Whether a rough patch starts with Mira over what you said: "leave me alone"'
    client.post(f"/api/life/consequences/{outcome['id']}/change", json={'option': 0})
    assert not patch(client)['open']


def test_one_let_go_can_still_be_made_to_start_on_today_after_the_daily_pass(client, patches, provider, monkeypatch):
    monkeypatch.setattr(consequences, 'roll', lambda seed, found: found[0]['option'])
    show(client, show_moods=True)
    says(provider)
    send(client, 'leave me alone', 'client-patch-30')
    reconcile(client)  # The daily pass must not close it while it could still be changed.
    [outcome] = [item for item in client.get('/api/life/reactions').json() if item['choice'] == 'user:rough_patch']
    assert outcome['picked'] == 0 and not patch(client)['open']
    assert outcome['label'] == 'Whether a rough patch starts with Mira over what you said: "leave me alone"'
    client.post(f"/api/life/consequences/{outcome['id']}/change", json={'option': 1})
    assert patch(client)['open']


def test_ordinary_chat_does_not_sting_or_count_as_an_apology():
    for text in ('I want to go away for the weekend, somewhere with a beach.', "This headache doesn't go away.",
                 "My kids wouldn't leave me alone all morning.", "Shut up, you got the job?! That's amazing!",
                 'Can we go away together sometime?', 'I hate you have to work tonight.',
                 'I just need everyone to leave me alone today, work was a lot'):
        assert rough_patches.stings(text) is None, text
        assert moods.hurtful(text) is None, text
    for text in ('Whatever you want is fine with me.', "I don't care what we eat, you pick.", 'My stupid phone died.',
                 'The new manager is an idiot honestly.', "I'll have whatever you're having."):
        assert moods.hurtful(text) is None, text
    for text in ('please just go away', 'go away for good', 'I hate you for that', "you're so stupid"):
        assert rough_patches.stings(text) and moods.hurtful(text), text
    assert moods.hurtful('ugh, whatever.') and moods.hurtful('stupid bot')
    assert not rough_patches.says('apologies', "I'm sorry to hear that, that sounds rough.")
    assert rough_patches.says('apologies', "oh no I'm so sorry, I forgot")
    assert rough_patches.says('apologies', "I'm sorry to hear you're upset, I'm sorry I forgot")


def test_off_starts_nothing_and_easy_fades_overnight(client, patches, provider, clock):
    set_life(client, rough_patches_realism=0)
    says(provider)
    send(client, 'shut up', 'client-patch-6')
    assert not patch(client)['open']
    set_life(client, rough_patches_realism=1)
    says(provider)
    send(client, 'go away', 'client-patch-7')
    assert patch(client)['open']
    clock.advance(timedelta(hours=13))  # Past midnight, their time.
    assert not patch(client)['open']


def test_real_life_mends_after_calm_days(client, patches, provider, clock):
    says(provider)
    send(client, 'shut up', 'client-patch-8')
    clock.advance(timedelta(days=2))
    assert patch(client)['open']
    clock.advance(timedelta(days=1, hours=1))
    assert not patch(client)['open']


def test_on_drama_a_secret_needs_an_apology_and_a_gesture(client, patches, provider):
    set_life(client, rough_patches_realism=3)
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        now = client.app.state.database.clock.now()
        rough_patches.found_out(connection, {'id': 'k1', 'statement': 'You lost your job.',
                                             'subjects': [{'key': 'user', 'name': 'you'}]},
                                f"companion:{companion['id']}", now)
    says(provider)
    send(client, "I'm sorry I kept it from you", 'client-patch-9')
    assert patch(client)['open']
    says(provider)
    send(client, 'hey', 'client-patch-10')
    assert 'It helps, but you are not over it yet' in notes(provider)
    says(provider)
    send(client, 'I got you something, I hope you like it', 'client-patch-11')
    assert not patch(client)['open']
    assert 'They just made it up to you' in notes(provider)


def test_a_broken_promise_starts_one_when_the_user_comes_back(client, patches, provider, clock):
    says(provider)
    send(client, "gotta run, I'll call you tonight!", 'client-patch-12')
    clock.advance(timedelta(days=1))
    says(provider)
    send(client, 'morning!', 'client-patch-13')
    assert "What happened: the user said they'd call you tonight and didn't" in notes(provider)
    show(client, show_moods=True)
    assert patch(client)['about'] == "over you saying you'd call them tonight and not doing it"


def test_a_promise_kept_starts_nothing(client, patches, provider, clock):
    says(provider)
    send(client, "I'll text you after work", 'client-patch-14')
    clock.advance(timedelta(hours=5))
    says(provider)
    send(client, 'home now!', 'client-patch-15')
    clock.advance(timedelta(days=1))
    says(provider)
    send(client, 'morning', 'client-patch-16')
    assert not patch(client)['open']


def test_calling_off_on_the_day_is_small_friction(client, patches, provider, clock):
    says(provider)
    send(client, 'come over tonight?', 'client-patch-17')  # 12:00: a visit at 19:00.
    [visit] = client.get('/api/life/outings').json()['outings']
    client.post(f"/api/life/outings/{visit['id']}/cancel")
    assert not patch(client)['open']  # Small ones show only with moods shown.
    with client.app.state.database.connect() as connection:
        [label] = [row['label'] for row in connection.execute(
            "SELECT label FROM consequences WHERE choice='user:rough_patch'")]
    assert label == 'Whether a rough patch starts with Mira over you calling off the visit on the day'  # Read later.
    says(provider)
    send(client, 'sorry!', 'client-patch-18')
    assert 'A small thing is bugging you a little today: the user called off' in notes(provider)
    clock.advance(timedelta(days=1, minutes=1))
    says(provider)
    send(client, 'hi', 'client-patch-19')
    assert 'A small thing' not in notes(provider)


def test_they_can_stand_you_up_and_apologise_first(client, patches, provider, clock, monkeypatch):
    monkeypatch.setattr(rough_patches, 'STAND_UP', {2: 1.0, 3: 1.0})
    says(provider)
    send(client, 'come over tonight?', 'client-patch-20')  # A visit at 19:00.
    clock.advance(timedelta(hours=5))  # 17:00.
    reconcile(client)
    [visit] = client.get('/api/life/outings').json()['outings']
    assert visit['state'] == 'cancelled' and visit['undo']
    assert patch(client)['open']
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        [trigger] = rough_patches.apology_due(connection, companion, clock.now())
        assert trigger.kind == 'apology' and 'You called off' in trigger.reason
        assert 'the visit' in trigger.template and 'the user' not in trigger.template and ')' not in trigger.template
        assert not rough_patches.cool(connection, companion, clock.now())
        assert trigger.key in {item.key for item in openers.candidates(connection, companion, clock.now())}
    says(provider, "I'm so sorry about tonight, work ran late.")
    check(client)
    assert history(client)[-1]['text'] == "I'm so sorry about tonight, work ran late."
    says(provider)
    send(client, "it's okay, these things happen", 'client-patch-21')
    assert not patch(client)['open']
    assert 'The user forgave you for calling off' in notes(provider)


def test_once_exclusive_they_mind_another_romance(client, monkeypatch):
    monkeypatch.setattr(rough_patches, 'ACTIVE', True)
    monkeypatch.setattr(consequences, 'roll', lambda seed, found: found[-1]['option'])
    mira(client, monkeypatch, relationship='romance')
    database = client.app.state.database
    with database.connect(write=True) as connection:
        other, now = identifier(), database.now()
        connection.execute('INSERT INTO companions (id, slot, stepped_back_at, created_at) VALUES (?, NULL, ?, ?)',
                           (other, now, now))
        version = insert_version(connection, other, 1, CharacterDefinition(
            name='Theo', personality='Easygoing.', timezone='UTC', relationship='romance'), '', now)
        connection.execute('UPDATE companions SET active_version_id=? WHERE id=?', (version, other))
    with database.connect(write=True) as connection:
        rough_patches.seen_with_others(connection, current(connection), database.clock.now())
    assert not patch(client)['open']  # Only dating: nobody minds yet.
    assert client.put('/api/life/steps', json={'step': 'exclusive'}).status_code == 200
    show(client, show_moods=True)
    with database.connect(write=True) as connection, monkeypatch.context() as broken_up:
        broken_up.setattr(breakups, 'apart', lambda _connection, companion: 'ended' if companion['id'] == other else None)
        rough_patches.seen_with_others(connection, current(connection), database.clock.now())
    assert not patch(client)['open']  # An ex is not someone you're seeing.
    with database.connect(write=True) as connection:
        rough_patches.seen_with_others(connection, current(connection), database.clock.now())
    assert patch(client)['about'] == "over Mira finding out you're seeing Theo too"
    set_life(client, rough_patches_realism=1)
    with database.connect(write=True) as connection:
        connection.execute('DELETE FROM rough_patches')
        rough_patches.seen_with_others(connection, current(connection), database.clock.now())
    assert not patch(client)['open']  # Never on an easy life.
    set_life(client, rough_patches_realism=2)
    from companion.life import steps
    monkeypatch.setattr(steps, 'apart', lambda _connection, companion: 'ended' if companion['id'] == other else None)
    with database.connect(write=True) as connection:
        connection.execute('DELETE FROM rough_patches')
        connection.execute('DELETE FROM consequences')
        rough_patches.seen_with_others(connection, current(connection), database.clock.now())
    assert not patch(client)['open']  # An ex is not someone you're seeing (E2E v0.13).


def add_romance(database, name, created_at):
    with database.connect(write=True) as connection:
        other = identifier()
        connection.execute('INSERT INTO companions (id, slot, stepped_back_at, created_at) VALUES (?, NULL, ?, ?)',
                           (other, created_at, created_at))
        version = insert_version(connection, other, 1, CharacterDefinition(
            name=name, personality='Easygoing.', timezone='UTC', relationship='romance'), '', created_at)
        connection.execute('UPDATE companions SET active_version_id=? WHERE id=?', (version, other))


def test_a_pair_the_app_started_out_exclusive_only_minds_romances_that_came_later(client, monkeypatch):
    """An upgrade from v0.12 starts couples at the step their history says, with no question asked: the romances the
    user already had then are no news to them, so the first daily pass opens no rough patch over them."""
    monkeypatch.setattr(rough_patches, 'ACTIVE', True)
    monkeypatch.setattr(consequences, 'roll', lambda seed, found: found[-1]['option'])
    mira(client, monkeypatch, relationship='romance', history_together='We have been dating for a year.')
    database = client.app.state.database
    add_romance(database, 'Theo', '2026-01-01T00:00:00+00:00')  # Already there before the app started them.
    show(client, show_moods=True)
    with database.connect(write=True) as connection:
        rough_patches.seen_with_others(connection, current(connection), database.clock.now())
    assert not patch(client)['open']
    add_romance(database, 'Zed', database.now())
    with database.connect(write=True) as connection:
        rough_patches.seen_with_others(connection, current(connection), database.clock.now())
    assert patch(client)['about'] == "over Mira finding out you're seeing Zed too"


def test_their_secret_partner_coming_out_is_theirs_to_apologise_for(client, patches, provider, clock):
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        love_life.rough_patch(connection, companion, {'id': 'p1', 'name': 'Jordan Lee'}, clock.now())
        [trigger] = rough_patches.apology_due(connection, companion, clock.now())
        assert trigger.template in rough_patches.bank('companion_confessions')
    assert patch(client)['open']
    says(provider)
    send(client, 'hey', 'client-patch-30')
    assert 'You let the user down: the user found out you had been seeing Jordan behind their back.' in notes(provider)
    says(provider)
    send(client, "I forgive you", 'client-patch-31')
    assert not patch(client)['open']
    assert 'The user forgave you for seeing someone behind their back' in notes(provider)


def test_reasons_for_calling_off_fit_the_era(client):
    with client.app.state.database.connect() as connection:
        def drawn(city):
            return set(rough_patches.reasons(connection, {'version': {'definition': {'home_city': city}}}))
        camelot, london, new_york, baltimore = drawn('camelot'), drawn('london-1895'), drawn('new-york-1925'), drawn('baltimore')
    assert 'the car would not start' in baltimore and 'the car would not start' in new_york
    assert 'the train broke down halfway there' in london and 'the car would not start' not in london
    assert not {'the car would not start', 'the train broke down halfway there', 'the bank froze a card and it took hours to fix'} & camelot
    assert 'the bank froze a card and it took hours to fix' not in new_york and len(camelot) >= 60


def test_a_plan_is_named_as_the_user_would():
    assert rough_patches.plan_name({'activity': 'dinner', 'place': {'name': 'Lupa'}}) == 'dinner at Lupa'
    assert rough_patches.plan_name({'activity': 'walk', 'place': {'name': 'Patterson Park'}}) == 'a walk at Patterson Park'
    assert rough_patches.plan_name({'activity': 'visit-yours', 'place': {'name': 'Your place'}}) == 'the visit'
    assert rough_patches.plan_name({'activity': 'hobby', 'place': {'name': 'The Clay Room'}}) == 'the plan at The Clay Room'


# Stacking (Vanta 2026-10-17): a rough patch over the same thing as one already open weighs less.

def rolls(client):
    with client.app.state.database.connect() as connection:
        return [decode_options(row) for row in connection.execute(
            "SELECT options FROM consequences WHERE choice='user:rough_patch' ORDER BY created_at")]


def decode_options(row):
    return json.loads(row['options'])[1]


def test_more_stinging_words_while_one_is_open_weigh_less(client, patches, provider, clock):
    set_life(client, rough_patches_realism=3)
    for index, text in enumerate(('shut up', "you're so annoying", 'go away', "ugh you're useless")):
        says(provider)
        send(client, text, f'client-stack-{index}')
        clock.advance(timedelta(seconds=30))
    found = rolls(client)
    weights = [item['odds'] / (1 - item['odds']) for item in found]  # The rough patch's weight against letting it go.
    assert [weight / weights[0] for weight in weights] == pytest.approx([1, 0.5, 0.25, 0.125], abs=0.01)  # Weighting, not a cap.
    assert found[0]['reasons'] == ['rough patches are set to dramatic']
    assert found[1]['reasons'][-1] == "there's already a rough patch over the same thing"
    assert found[2]['reasons'][-1] == 'it would be the third over the same thing'
    assert found[1]['moves'][-1] == 'less'  # Today: "Less likely because there's already a rough patch over ..."
    with client.app.state.database.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM rough_patches').fetchone()[0] == 4  # The dice still decide.


def test_one_mended_on_an_earlier_day_or_over_something_else_does_not_stack(client, patches, provider, clock):
    says(provider)
    send(client, 'shut up', 'client-stack-5')
    says(provider)
    send(client, "I'm really sorry, I shouldn't have said that", 'client-stack-6')
    clock.advance(timedelta(days=1))
    with client.app.state.database.connect(write=True) as connection:
        rough_patches.consider(connection, current(connection), 'forgot_occasion', 'occasion:test', 'your birthday',
                               clock.now())
    says(provider)
    send(client, 'go away', 'client-stack-7')
    assert all("over the same thing" not in ' '.join(item['reasons']) for item in rolls(client))


def test_one_let_go_by_the_dice_does_not_count(client, patches, provider, clock, monkeypatch):
    monkeypatch.setattr(consequences, 'roll', lambda seed, found: found[0]['option'])  # They let it go.
    says(provider)
    send(client, 'shut up', 'client-stack-8')
    monkeypatch.setattr(consequences, 'roll', lambda seed, found: found[-1]['option'])
    says(provider)
    send(client, 'go away', 'client-stack-9')
    assert rolls(client)[1]['reasons'] == rolls(client)[0]['reasons']
