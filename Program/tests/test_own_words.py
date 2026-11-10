"""Their own words (Hit List #97): stock wording named from its first use, a three-step ladder worked out from the
transcript, and the user's list of words to drop or swap, with Keep and Dismiss for what was caught."""
import json

import pytest
from conftest import send

from companion.memory import own_words
from companion.providers.chat import Chunk


def ok(response):
    assert response.status_code < 300, response.text
    return response.json()


def replies(texts):
    return [{'id': f'own-{index}', 'text': text, 'role': 'companion'} for index, text in enumerate(texts)]


def test_the_bank_has_at_least_a_hundred_of_each_kind_with_no_repeats():
    data = json.loads(own_words.BANK.read_text(encoding='utf-8'))
    assert len(data['phrases']) >= 100
    assert len(data['openers']) + len(data['closers']) >= 100
    for kind in ('phrases', 'openers', 'closers'):
        assert len(set(data[kind])) == len(data[kind]), kind
        assert all(entry == entry.lower() and entry.strip() for entry in data[kind]), kind


def test_stock_wording_is_found_in_its_place():
    assert set(own_words.stock_in("*chuckles softly* Long shift. I'm all ears, though. What do you think?")) == {
        '*chuckles softly*', "i'm all ears", 'what do you think?'}
    # Openers only open a reply and closers only close one; their punctuation counts.
    assert own_words.stock_in('I said what do you think? and she laughed. Anyway, bed.') == ()
    assert own_words.stock_in('Absolutely love that place.') == ()
    assert own_words.stock_in('Absolutely! Love that place.') == ('absolutely!',)
    # Curly apostrophes and asterisks around actions don't hide it.
    assert own_words.stock_in('Sure. I’m *all ears*.') == ("i'm all ears",)


def test_one_use_names_stock_wording_but_not_names_the_users_words_or_their_voice():
    texts = replies(['Rough day. I can’t help but laugh though.', 'Nap time.'])
    assert [item['phrase'] for item in own_words.found(texts, own_words.Protected())] == ["i can't help but"]
    said = own_words.Protected(said=own_words.plain("lol I can't help but stare at it"))
    assert own_words.found(texts, said) == []
    named = own_words.Protected(names=frozenset({'sweet'}))
    assert own_words.found(replies(['Oh, how sweet of you.']), named) == []


def test_the_ladder_climbs_when_a_named_phrase_comes_back():
    protected = own_words.Protected()
    once = replies(["Busy, but I'm all ears.", 'Tea first.'])
    assert own_words.ladder(once, protected)[0]['step'] == 1
    twice = replies(["Busy, but I'm all ears.", "Sure, I'm all ears."])
    assert own_words.ladder(twice, protected)[0]['step'] == 2
    thrice = replies(["Busy, but I'm all ears.", "Sure, I'm all ears.", "Go on, I'm all ears."])
    assert own_words.ladder(thrice, protected)[0]['step'] == 3
    note = own_words.line(own_words.ladder(twice, protected), 2)
    assert note == ('You were asked not to write "i\'m all ears" and wrote it again. Do not use "i\'m all ears" in '
                    'this reply, or anything close to it.')
    # Off (the A/B's today arm), only repeats are named, at step 1.
    own_words.ACTIVE = False
    try:
        assert own_words.ladder(thrice, protected) == [{'phrase': "i'm all ears", 'kind': 'repeat', 'count': 3, 'words': 3,
                                                        'step': 1}]
    finally:
        own_words.ACTIVE = True


def test_the_ladder_forgets_once_the_uses_leave_the_window():
    plain = ['Tea.', 'Gym was packed.', 'Rain again!', 'My sister called.', 'Pizza tonight?', 'Long shift.',
             'Reading on the couch.', 'Sunday market.', 'Bus was late.', 'New plant!', 'Cat knocked a cup over.',
             'Laundry day.', 'Movie was fine.', 'Early night.', 'Coffee first.', 'Back at work.']
    texts = ["Busy, but I'm all ears.", "Sure, I'm all ears.", *plain]
    assert own_words.ladder(replies(texts), own_words.Protected()) == []


def test_step_three_takes_out_the_sentence_only_with_two_others_left():
    plan = {'remove': ["i'm all ears"]}
    assert own_words.tidy("Long day. I'm all ears though. Tell me everything about it.", plan) == \
        'Long day. Tell me everything about it.'
    assert own_words.tidy("I'm all ears. Tell me.", plan) == "I'm all ears. Tell me."
    # Held back until two others are known, so it never shows and then vanishes.
    tidy = own_words.Tidy(plan)
    assert tidy.feed("I'm all ears. ") == ''
    assert tidy.feed('Tell me. ') == ''
    assert tidy.feed('Now.') == ''
    assert tidy.flush() == 'Tell me. Now.' and tidy.removed == 1
    # Out of character, nothing is taken out.
    assert own_words.tidy("I'm all ears. Tell me. Now.", plan, in_character=False) == "I'm all ears. Tell me. Now."
    # A paragraph break that ended the sentence stays.
    assert own_words.tidy("One.\n\nI'm all ears.\n\nTwo. Three.", plan) == 'One.\n\n\n\nTwo. Three.'


def test_swaps_and_drops_tidy_the_sentence():
    plan = {'swaps': [('—', ','), ('honestly', '')]}
    assert own_words.tidy('Long day — so long. Honestly, I need a nap. i honestly do.', plan) == \
        'Long day, so long. I need a nap. i do.'
    assert own_words.Tidy({}).active is False and own_words.Tidy({}).feed('as is') == 'as is'


def test_settings_list_keep_dismiss_and_the_cap(client, connected, provider):
    provider.respond = lambda system, messages: [Chunk("Long shift. I'm all ears, though."), Chunk('', 'stop')]
    send(client, 'Hey you', 'own-words-1')
    data = ok(client.get('/api/own-words'))
    assert data['rules'] == [] and data['limit'] == own_words.MAX_RULES
    assert [item['phrase'] for item in data['caught']] == ["i'm all ears"]
    kept = ok(client.post('/api/own-words', json={'phrase': "i'm all ears", 'action': 'keep'}))
    assert kept['caught'] == [] and kept['rules'][0]['action'] == 'keep'
    # Kept is never named in a reply's notes.
    send(client, 'And then?', 'own-words-2')
    assert "i'm all ears" not in provider.requests[-1]['prompt']
    dismissed = ok(client.post('/api/own-words', json={'phrase': "i'm all ears", 'action': 'dismiss'}))
    assert dismissed['rules'] == [] and dismissed['caught'] == []
    for number in range(own_words.MAX_RULES):
        ok(client.post('/api/own-words', json={'phrase': f'word{number}', 'action': 'drop'}))
    full = client.post('/api/own-words', json={'phrase': 'one more', 'action': 'drop'})
    assert full.status_code == 409
    first = ok(client.get('/api/own-words'))['rules'][0]
    assert len(ok(client.delete(f"/api/own-words/{first['id']}"))['rules']) == own_words.MAX_RULES - 1


def test_a_swap_changes_the_saved_reply_and_the_ladder_reaches_the_prompt(client, connected, provider):
    ok(client.post('/api/own-words', json={'phrase': '—', 'action': 'swap', 'replacement': ','}))
    provider.respond = lambda system, messages: [Chunk("Long day — so long. "), Chunk("I'm all ears."), Chunk('', 'stop')]
    send(client, 'Hey', 'own-words-swap-1')
    messages = ok(client.get('/api/conversation'))['messages']
    assert messages[-1]['text'] == "Long day, so long. I'm all ears."
    send(client, 'Hey again', 'own-words-swap-2')
    assert 'Stock wording that reads as written, not said: "i\'m all ears"' in provider.requests[-1]['prompt']
    send(client, 'And again', 'own-words-swap-3')
    assert 'You were asked not to write "i\'m all ears"' in provider.requests[-1]['prompt']


@pytest.mark.parametrize('everyone', [True, False])
def test_rules_for_every_world_follow_the_user(client, connected, everyone):
    ok(client.post('/api/own-words', json={'phrase': 'literally', 'action': 'drop', 'everyone': everyone}))
    made = ok(client.post('/api/worlds', json={'name': 'Elsewhere'}))
    ok(client.post(f"/api/worlds/{made['id']}/switch"))
    phrases = [rule['phrase'] for rule in ok(client.get('/api/own-words'))['rules']]
    assert phrases == (['literally'] if everyone else [])


def test_a_single_word_habit_is_only_ever_pointed_out():
    texts = replies(['Pulls the hoodie on.', 'Hoodie again, sorry.', 'Still in the hoodie.', 'Hoodie forever.',
                     'Hoodie weather.', 'Washing the hoodie.'])
    items = own_words.ladder(texts, own_words.Protected())
    assert [(item['phrase'], item['step']) for item in items] == [('hoodie', 1)]
