"""On her mind (companion/life/thoughts.py): one private thought a day from what happened, folded on Today."""
import asyncio
from datetime import timedelta

import pytest
from conftest import reconcile, send, set_life
from test_chapters import (
    arrange,
    current,
    mira,  # noqa: F401 - fixture
)

from companion.life import thoughts
from companion.providers.chat import Chunk


@pytest.fixture
def linked(client, mira):  # noqa: F811
    response = client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                                   'api_key': 'secret-key'})
    assert response.status_code == 200, response.text


def mind(client):
    response = client.get('/api/today')
    assert response.status_code == 200, response.text
    return response.json()['mind']


def evening(clock):
    """Move the clock to 19:00 UTC today (Mira lives in UTC in these tests)."""
    now = clock.now()
    clock.advance(now.replace(hour=19, minute=0) - now)


def test_nothing_shows_before_their_first_evening(client, mira):  # noqa: F811
    assert mind(client) == {'thoughts': []}


def test_an_evening_brings_a_thought_that_is_kept(client, mira, clock):  # noqa: F811
    evening(clock)
    first = mind(client)['thoughts']
    assert len(first) == 1 and first[0]['day'] == clock.now().date().isoformat() and 'Mira' in first[0]['text']
    assert mind(client)['thoughts'] == first


def test_talking_with_you_is_on_their_mind(client, mira, clock, linked):  # noqa: F811
    send(client, 'Hey, how was your morning?', 'client-thought')
    evening(clock)
    mind(client)
    with client.app.state.database.connect() as connection:
        topic = connection.execute('SELECT topic FROM thoughts').fetchone()[0]
    assert topic == 'talked'
    assert mind(client)['thoughts'][0]['text'] in [line.format(first='Mira') for line in thoughts.TALKED]


def test_a_new_chapter_is_what_they_think_about(client, mira, clock, monkeypatch):  # noqa: F811
    arrange(client, monkeypatch, clock, 'hobby')
    reconcile(client)
    title = client.get('/api/life/chapters').json()[0]['title']
    evening(clock)
    assert mind(client)['thoughts'][0]['text'].startswith(f'{title}.')


def test_the_week_is_kept_newest_first_and_ends_after_seven_days(client, mira, clock):  # noqa: F811
    for _day in range(9):
        clock.advance(timedelta(days=1))
        evening(clock)
        mind(client)
    days = [item['day'] for item in mind(client)['thoughts']]
    assert len(days) == thoughts.WEEK and days == sorted(days, reverse=True)
    assert days[0] == clock.now().date().isoformat()


def test_a_topic_steps_aside_for_anything_fresh(client, mira, clock, monkeypatch):  # noqa: F811
    monkeypatch.setattr(thoughts, 'FINDERS', tuple(
        (lambda *_args, weight=weight, topic=topic: [(weight, topic, f'Mira thought about {topic}.')])
        for weight, topic in ((5, 'big'), (3, 'middle'), (1, 'small'))))
    for _day in range(5):
        clock.advance(timedelta(days=1))
        evening(clock)
        mind(client)
    with client.app.state.database.connect() as connection:
        topics = [row[0] for row in connection.execute('SELECT topic FROM thoughts ORDER BY day')]
    assert topics == ['big', 'middle', 'small'] * 2


def test_a_secret_they_keep_never_shows(client, mira, clock, monkeypatch):  # noqa: F811
    monkeypatch.setattr(thoughts, 'FINDERS', (lambda *_args: [(9, 'secret', 'Mira is hiding the affair.')],))
    monkeypatch.setattr(thoughts, 'kept_quiet', lambda _connection, _companion, text: 'affair' in text)
    evening(clock)
    assert 'affair' not in mind(client)['thoughts'][0]['text']


def test_switched_off_shows_nothing(client, mira, clock):  # noqa: F811
    assert set_life(client, on_her_mind=False)['on_her_mind'] is False
    evening(clock)
    assert mind(client) is None
    with client.app.state.database.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM thoughts').fetchone()[0] == 0


def test_the_model_polishes_wording_only_in_the_background(client, mira, clock, linked, provider):  # noqa: F811
    evening(clock)
    template = mind(client)['thoughts'][0]['text']
    provider.replies = [[Chunk('Mira is quietly content tonight.'), Chunk('', 'stop')]]
    asyncio.run(client.app.state.life.think())
    assert mind(client)['thoughts'][0]['text'] == 'Mira is quietly content tonight.'
    assert provider.requests[-1]['messages'][-1]['content'] == template


def test_a_polish_that_drops_the_name_is_thrown_away(client, mira, clock, linked, provider):  # noqa: F811
    evening(clock)
    template = mind(client)['thoughts'][0]['text']
    provider.replies = [[Chunk('She is content.'), Chunk('', 'stop')]]
    asyncio.run(client.app.state.life.think())
    assert mind(client)['thoughts'][0]['text'] == template
    asyncio.run(client.app.state.life.think())
    assert len(provider.requests) == 1


def test_no_polish_without_model_phrasing(client, mira, clock, linked, provider):  # noqa: F811
    set_life(client, phrase_with_model=False)
    evening(clock)
    mind(client)
    asyncio.run(client.app.state.life.think())
    assert provider.requests == []
    assert current(client)
