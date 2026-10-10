"""Dreams (companion/life/dreams.py): some nights, the companion's day turns into a short, odd dream."""
import random
from datetime import timedelta

import pytest

from companion.characters import require_current
from companion.life import dreams, openers
from companion.memory import context

DAY = {'people': ['Ana', 'Theo'], 'places': ['Harbor Cafe'], 'user': False}


@pytest.fixture
def dreamer(client, companion, monkeypatch):
    monkeypatch.setattr(dreams, 'ACTIVE', True)
    monkeypatch.setitem(dreams.data(), 'chance', 100)
    monkeypatch.setattr(dreams, 'fragments', lambda *_args: DAY)
    return companion


def today(client):
    response = client.get('/api/today')
    assert response.status_code == 200, response.text
    return response.json()['dreams']


def morning(clock, days=1):
    """The next morning, 08:00 in Lisbon (the companion's city in these tests)."""
    now = clock.now() + timedelta(days=days)
    clock.advance(now.replace(hour=7, minute=0) - clock.now())


def test_no_dream_on_the_first_night_before_it_has_happened(client, dreamer):
    assert today(client) == []


def test_a_night_brings_a_dream_from_the_day(client, dreamer, clock):
    morning(clock)
    found = today(client)
    assert len(found) == 1 and found[0]['day'] == clock.now().date().isoformat()
    text = found[0]['text']
    assert text.startswith('Mira dreamed') and ('Ana' in text or 'Theo' in text or 'Harbor Cafe' in text)
    assert today(client) == found


def test_every_template_reads_right():
    chooser = random.Random(1)
    for template in dreams.data()['templates']:
        for found in (DAY, {**DAY, 'people': ['Ana'], 'user': True}):
            if template in dreams.fitting(found):
                dream = dreams.fill(template, found, 'Mira', chooser)
                assert '{' not in ''.join(dream.values())
                assert dream['told'].startswith('Last night you dreamed')
                if 'you' in dream['text'].split():
                    assert 'the user' in dream['told']


def test_the_user_only_turns_up_as_a_second_person():
    alone = {'people': [], 'places': [], 'user': True}
    assert dreams.fitting(alone) == []
    found = {'people': ['Ana'], 'places': [], 'user': True}
    for template in dreams.fitting(found):
        told = dreams.fill(template, found, 'Mira', random.Random(2))['told']
        assert ('the user' in told) == (template['people'] == 2)


def test_dreams_stay_rare(client, dreamer, clock, monkeypatch):
    monkeypatch.setitem(dreams.data(), 'chance', 100)
    morning(clock, days=8)
    assert len(today(client)) == dreams.data()['per_week']


def test_the_companion_remembers_it_and_may_text_about_it(client, dreamer, clock, monkeypatch):
    morning(clock)
    today(client)
    monkeypatch.setattr(dreams, 'TEXT_LEVEL', 1)
    database = client.app.state.database
    with database.connect() as connection:
        companion = require_current(connection)
        packet = context.build(connection, companion, database.clock.now(), 6000)
        triggers = openers.dream_news(connection, companion, database.clock.now())
    assert '## Last night (a dream you had' in packet['system'] and '- Last night you dreamed' in packet['system']
    assert len(triggers) == 1 and triggers[0].key.startswith('dream:')
    clock.advance(timedelta(hours=6))  # After noon: no more morning text.
    with database.connect() as connection:
        assert openers.dream_news(connection, require_current(connection), database.clock.now()) == []


def test_strangers_get_no_dream_texts(client, dreamer, clock):
    morning(clock)
    today(client)
    database = client.app.state.database
    with database.connect() as connection:
        assert openers.dream_news(connection, require_current(connection), database.clock.now()) == []


def test_a_secret_never_turns_up_in_a_dream(client, dreamer, clock, monkeypatch):
    monkeypatch.setattr(dreams.deck, 'kept_quiet', lambda *_args: True)
    morning(clock)
    assert today(client) == []


def test_a_dream_is_not_dreamed_again_for_weeks(client, dreamer, clock, monkeypatch):
    monkeypatch.setitem(dreams.data(), 'per_week', 7)
    for _night in range(20):
        morning(clock)
        today(client)
    with client.app.state.database.connect() as connection:
        used = [row[0] for row in connection.execute('SELECT template FROM dreams WHERE template IS NOT NULL')]
    assert len(used) >= 15 and len(used) == len(set(used))


def test_people_and_places_a_secret_is_about_are_left_out(client, companion, monkeypatch):
    from companion.memory import pairs
    secret = {'knowers': [pairs.companion_key(companion['id'])], 'subjects': [{'name': 'Ana Silva'}],
              'keys': ['Harbor Cafe', 'ring']}
    monkeypatch.setattr(dreams.secrets, 'active', lambda _connection: [secret])
    with client.app.state.database.connect() as connection:
        hidden = dreams.secret_words(connection, companion)
    assert dreams.touches('Ana', {'ana'}) and dreams.touches('Harbor Cafe', hidden)
    assert dreams.touches('Ana Silva', hidden) and not dreams.touches('Theo', hidden)
    assert not dreams.touches('Riverside Park', hidden)


def test_dreams_are_never_romantic_or_sexual():
    banned = {'kiss', 'kissed', 'kissing', 'bed', 'naked', 'date', 'romantic', 'lover', 'sex', 'sexy', 'married'}
    texts = [template[field] for template in dreams.data()['templates'] for field in ('text', 'told', 'share')]
    texts += dreams.data()['odd'] + dreams.data()['object']
    assert not {word.strip('.,!?') for text in texts for word in text.lower().split()} & banned


def test_a_night_waits_until_the_day_has_been_lived(client, dreamer, clock):
    """Opening Today before the day's life is settled must not fix the night as dreamless for good."""
    morning(clock)
    database = client.app.state.database
    yesterday = (clock.now() - timedelta(days=1)).date().isoformat()
    with database.connect(write=True) as connection:
        timeline_id = require_current(connection)['active_timeline_id']
        connection.execute("INSERT INTO life_agenda (id, timeline_id, subject, slot_key, starts_at, ends_at, "
                           "local_date, block, basis, created_at) VALUES ('late', ?, 'companion', 'late', ?, ?, ?, "
                           "'{}', 'b', ?)", (timeline_id, yesterday, yesterday, yesterday, yesterday))
    assert today(client) == []
    with database.connect(write=True) as connection:
        connection.execute("UPDATE life_agenda SET status='happened' WHERE id='late'")
    assert len(today(client)) == 1
