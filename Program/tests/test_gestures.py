"""Gestures that fit who they are (Hit List #96, companion/life/rough_patches.py): a make-up gesture in the chat has a
kind, big or small, and whether it wins them over is a roll their personality sliders weigh."""
import pytest
from conftest import send, show
from test_rough_patches import patch
from test_together import mira, says

from companion import consequences
from companion.life import rough_patches


@pytest.fixture
def patches(client, monkeypatch):
    """Rough patches on, every rough patch opening and every gesture missing (unless a test says otherwise)."""
    monkeypatch.setattr(rough_patches, 'ACTIVE', True)
    monkeypatch.setattr(consequences, 'roll', lambda seed, found: 0 if seed.endswith(':user:gesture') else found[-1]['option'])
    mira(client, monkeypatch)


def test_a_gesture_has_a_kind_and_big_wins_over_small():
    assert rough_patches.gesture_kind('*hands you a bouquet* I was an idiot') == 'big'
    assert rough_patches.gesture_kind('I booked us a table at that place') == 'big'
    assert rough_patches.gesture_kind('*hands you a coffee* peace offering?') == 'small'
    assert rough_patches.gesture_kind('I did the dishes for you') == 'small'
    assert rough_patches.gesture_kind('brought you coffee, and I got us tickets for Friday') == 'big'
    assert rough_patches.gesture_kind("I never brought you flowers, sorry") is None
    assert rough_patches.gesture_kind('what are you up to?') is None


def test_every_phrase_in_the_bank_reads_as_its_own_kind():
    for phrase, kind in rough_patches.gesture_kinds().items():
        found = rough_patches.gesture_kind(f'ok so {phrase}')
        assert found == kind or (kind == 'small' and found == 'big'), phrase


def lands(facts: dict) -> tuple[float, list[str]]:
    found = consequences.odds('user:gesture', {'level': 2, 'serious': 0, 'sheet': [], **facts},
                              {'name': 'Mira', 'gesture': 'your grand gesture', 'a': '', 'b': ''})
    return found[rough_patches.LANDS]['odds'], found[rough_patches.LANDS]['reasons']


def test_warm_open_people_take_a_big_gesture_at_face_value_and_guarded_proud_ones_less():
    middle, _ = lands({'big_warmth': 1, 'big_social': 1, 'big_proud': 0})
    warm, why = lands({'big_warmth': 2, 'big_social': 2, 'big_proud': 0})
    assert warm > middle and 'Mira is warm and takes a grand gesture at face value' in why
    wary, why = lands({'big_warmth': 0, 'big_social': 0, 'big_proud': 1})
    assert wary < 0.5 < middle
    assert 'Mira is wary of grand gestures' in why and "a grand gesture runs into Mira's pride" in why
    small, why = lands({'small_warmth': 0, 'small_social': 0, 'small_proud': 1})
    assert small > middle and 'a small, steady kindness means more to Mira than a big show' in why
    assert 'Mira is warm and takes a grand gesture at face value' in lands({'big_warmth': 2})[1]
    assert lands({'big_warmth': 1, 'big_social': 1, 'big_proud': 0, 'level': 1})[0] > middle
    assert lands({'big_warmth': 1, 'big_social': 1, 'big_proud': 0, 'serious': 1})[0] < middle


def test_the_row_says_what_was_done_when_the_phrase_says_it():
    assert rough_patches.gesture_act('brought you flowers') == 'the flowers you brought'
    assert rough_patches.gesture_act('hands you a bouquet') == 'the bouquet you handed over'
    assert rough_patches.gesture_act('made you soup') == 'the soup you made'
    for phrase in ('got you something', 'bought you the tickets you wanted', 'picked you up from work', 'fed your cat',
                   "let me make it up to you"):
        assert rough_patches.gesture_act(phrase) is None, phrase


def test_with_nothing_open_a_gesture_is_not_weighed(client, patches, provider):
    says(provider)
    send(client, 'brought you flowers', 'client-gesture-0')  # Nothing open: no gesture to weigh.
    with client.app.state.database.connect() as connection:
        assert not rough_patches.many(connection, "SELECT id FROM consequences WHERE choice='user:gesture'")


def test_a_gesture_that_doesnt_win_them_over_leaves_it_open_and_today_can_change_it(client, patches, provider):
    show(client, show_moods=True)
    says(provider)
    send(client, 'leave me alone', 'client-gesture-1')
    assert patch(client)['open']
    says(provider)
    send(client, '*hands you a bouquet*', 'client-gesture-2')
    assert patch(client)['open']
    [outcome] = [item for item in client.get('/api/life/reactions').json() if item['choice'] == 'user:gesture']
    assert outcome['label'] == 'How Mira took the bouquet you handed over to make up'
    assert outcome['options'][outcome['picked']]['label'] == "Mira isn't won over by the bouquet you handed over yet"
    # Another big one the same day isn't weighed again; a small kindness is.
    says(provider)
    send(client, 'I got us tickets to the show', 'client-gesture-3')
    says(provider)
    send(client, 'I did the dishes for you', 'client-gesture-4')
    took = [item for item in client.get('/api/life/reactions').json() if item['choice'] == 'user:gesture']
    assert len(took) == 2 and {item['options'][0]['label'] for item in took} == {
        "Mira isn't won over by the bouquet you handed over yet", "Mira isn't won over by your small kindness yet"}
    response = client.post(f"/api/life/consequences/{outcome['id']}/change", json={'option': rough_patches.LANDS})
    assert response.status_code == 200 and response.json()['picked'] == rough_patches.LANDS
    assert not patch(client)['open']
    client.post(f"/api/life/consequences/{outcome['id']}/change", json={'option': 0})
    assert patch(client)['open']


def test_a_gesture_that_wins_them_over_mends_it(client, patches, provider, monkeypatch):
    monkeypatch.setattr(consequences, 'roll', lambda seed, found: found[-1]['option'])
    says(provider)
    send(client, 'go away', 'client-gesture-5')
    assert patch(client)['open']
    says(provider)
    send(client, 'I did the dishes for you', 'client-gesture-6')
    assert not patch(client)['open']


def test_each_group_of_reasons_names_them_once(client, patches, provider):
    with client.app.state.database.connect(write=True) as connection:
        from companion.characters import current
        companion = current(connection)
        companion['version']['definition']['personality_sliders'] = {'warmth': {'level': 0, 'source': 'you'},
                                                                     'social': {'level': 0, 'source': 'you'}}
        companion['version']['definition']['personality'] = 'Proud.'
        now = client.app.state.database.clock.now()
        row = rough_patches.consider(connection, companion, 'words', 'words:x', 'the user said "go away"', now)
        outcome = rough_patches.gesture(connection, companion, row, 'big', {'id': 'm1'}, now, 'the flowers you sent')
        found = consequences.view(rough_patches.one(connection, 'SELECT * FROM consequences WHERE id=?',
                                                    (outcome['id'],)), connection)
    assert found['options'][rough_patches.LANDS]['reasons'] == [
        'Mira is wary of grand gestures', "a grand gesture doesn't get past their guard", 'a grand gesture runs into their pride']
