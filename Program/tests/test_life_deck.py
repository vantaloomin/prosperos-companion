"""The Life deck and random tables (companion/life/deck.py): small moments drawn into the companion's days."""
from datetime import timedelta

import pytest
from conftest import set_life, show

from companion.characters import require_current
from companion.life import deck, openers, thoughts
from companion.memory import context


@pytest.fixture
def dealt(client, companion, monkeypatch):
    monkeypatch.setattr(deck, 'ACTIVE', True)
    return companion


def moments(client):
    response = client.get('/api/today')
    assert response.status_code == 200, response.text
    return response.json()['moments']


def only(monkeypatch, card_id):
    """Make every day draw `card_id`."""
    found = deck.card(card_id)
    monkeypatch.setattr(deck, 'cards', lambda: (found,))
    monkeypatch.setitem(deck.deck(), 'chance', [100, 100, 100, 100])


def test_the_tables_join_the_deck_as_cards():
    ids = [item['id'] for item in deck.cards()]
    assert len(ids) == len(set(ids)) and len(ids) > 80
    tables = [item for item in deck.cards() if item['source'] != 'Life deck']
    assert {item['source'] for item in tables} >= {'Micro-friction', 'Complication', 'A small find'}
    # Their weights follow the dice: Micro-friction (16-50 on the top table) outweighs an odd day (96-100).
    friction = sum(item['weight'] for item in tables if item['source'] == 'Micro-friction')
    odd = sum(item['weight'] for item in tables if item['source'] == 'An odd little thing')
    assert friction > 4 * odd
    for item in deck.cards():
        assert item['text'].format(first='Mira', friend='Ana') and item['told'].format(first='Mira', friend='Ana')
        assert ('{friend}' in item['text'] + item['told']) <= ('friend' in item['needs'])


def test_draws_repeat_and_follow_the_drama_level():
    found = [deck.draw(f'seed:{index}', 1, {'friend', 'work'}, set()) for index in range(400)]
    assert found == [deck.draw(f'seed:{index}', 1, {'friend', 'work'}, set()) for index in range(400)]
    share = sum(1 for item, _odds in found if item) / len(found)
    assert 0.3 < share < 0.5  # Realistic: 40 in 100 days.
    quiet = [deck.draw(f'seed:{index}', 0, set(), set())[0] for index in range(400)]
    assert all(item['drama'] == 0 and not item['needs'] for item in quiet if item)
    assert any(item['drama'] == 1 for item, _odds in found if item)
    item, odds = next(pair for pair in found if pair[0])
    assert 0 < odds < 0.4


def test_a_day_draws_once_and_today_shows_it(client, dealt, monkeypatch):
    only(monkeypatch, 'old-pocket-cash')
    first = moments(client)
    assert first[0]['title'] == 'Money in an old pocket' and 'Mira found a forgotten twenty' in first[0]['text']
    assert 'odds' not in first[0]
    assert moments(client) == first
    show(client, show_odds=True)
    assert moments(client)[0]['odds'] == 1.0


def test_the_companion_is_told_and_may_text_about_it(client, dealt, monkeypatch):
    only(monkeypatch, 'old-pocket-cash')
    moments(client)
    database = client.app.state.database
    with database.connect() as connection:
        companion = require_current(connection)
        packet = context.build(connection, companion, database.clock.now(), 6000)
        triggers = openers.little_news(connection, companion, database.clock.now())
    assert '- You found a forgotten twenty in an old coat pocket.' in packet['system']
    assert triggers[0].template.startswith('Found twenty bucks')
    with database.connect() as connection:
        day = deck.storylines.local_today(companion, database.clock.now())
        assert thoughts.little_things(connection, companion, day, database.clock.now())[0][1] == \
            'moment:old-pocket-cash'


def test_cards_that_need_a_circle_or_a_job_wait_for_one():
    found = [deck.draw(f'need:{index}', 3, set(), set())[0] for index in range(300)]
    assert all(not item['needs'] for item in found if item)


def test_a_card_steps_aside_for_a_while(client, dealt, clock, monkeypatch):
    pair = (deck.card('old-pocket-cash'), deck.card('spilled-coffee'))
    monkeypatch.setattr(deck, 'cards', lambda: pair)
    monkeypatch.setitem(deck.deck(), 'chance', [100, 100, 100, 100])
    for _day in range(3):
        moments(client)
        clock.advance(timedelta(days=1))
    drawn = [item['title'] for item in moments(client)]
    # Two cards, four days: after both are drawn, the days stay quiet until the first can come back.
    assert sorted(drawn) == ['Money in an old pocket', 'Spilled coffee']


def test_making_it_go_another_way(client, dealt, monkeypatch):
    pair = (deck.card('old-pocket-cash'), deck.card('spilled-coffee'))
    monkeypatch.setattr(deck, 'cards', lambda: pair)
    monkeypatch.setitem(deck.deck(), 'chance', [100, 100, 100, 100])
    day = moments(client)[0]['day']
    before = moments(client)[0]['title']
    response = client.post(f'/api/life/moments/{day}/change', json={'way': 'another'})
    assert response.status_code == 200, response.text
    assert response.json()[0]['title'] != before and response.json()[0]['picked_by'] == 'user'
    response = client.post(f'/api/life/moments/{day}/change', json={'way': 'nothing'})
    assert response.json() == [] and moments(client) == []


def test_quiet_drama_keeps_to_gentle_cards(client, dealt, monkeypatch):
    set_life(client, drama=0)
    monkeypatch.setitem(deck.deck(), 'chance', [100, 100, 100, 100])
    with client.app.state.database.connect() as connection:
        companion = require_current(connection)
        drawn = [deck.decide(connection, companion, deck.storylines.local_today(companion, client.app.state.database
                                                                                 .clock.now()) - timedelta(days=index))
                 for index in range(60)]
    assert all(deck.card(item['card_id'])['drama'] == 0 for item in drawn if item['card_id'])
