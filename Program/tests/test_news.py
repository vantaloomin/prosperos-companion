"""News travels (companion/news.py): word of a companion's news gets around, one hop a day."""
from datetime import timedelta

import pytest
from conftest import reconcile
from test_groups import by_speaker, companion_named, ok, say, start

from companion import consequences, news, secrets
from companion.characters import by_id
from companion.life import circle, openers
from companion.memory import pairs

TEXT = 'Mira took up pottery for real'


@pytest.fixture
def cast(client, companion, connected, provider, monkeypatch):
    """Mira (main character, in Lisbon) has news today; Billy knows her well, Sally knows only Billy."""
    provider.respond = by_speaker
    found = {'Mira': companion['id'], 'Billy': companion_named(client, 'Billy Hart'),
             'Sally': companion_named(client, 'Sally Moss')}
    reconcile(client)  # Mira's circle
    database = client.app.state.database
    with database.connect(write=True) as connection:
        pairs.tell(connection, key(found['Mira']), key(found['Billy']), 4, 'Old friends', database.now())
        pairs.tell(connection, key(found['Billy']), key(found['Sally']), 4, 'Coworkers', database.now())
    today = database.clock.now().date().isoformat()
    monkeypatch.setattr(news, 'found', lambda _connection, companion_, _now: [
        {'source': 'chapter:pottery', 'text': TEXT, 'happened_on': today}] if companion_['id'] == found['Mira'] else [])
    return found


def key(companion_id):
    return pairs.companion_key(companion_id)


def sync(client):
    database = client.app.state.database
    with database.connect(write=True) as connection:
        return news.sync(connection, database.clock.now())


def holders(client) -> dict[str, dict]:
    with client.app.state.database.connect() as connection:
        return {row['holder']: row for row in connection.execute('SELECT * FROM news_holders')}


def evening(clock):
    """20:30 in Lisbon (19:30 UTC in October) today."""
    now = clock.now()
    clock.advance(now.replace(hour=19, minute=30) - now)


def test_closer_tellers_own_news_and_gossips_pass_it_on_more(client):
    names = {'name': 'they', 'a': 'them', 'b': ''}

    def chance(**facts):
        return consequences.odds(news.CHOICE, {'own': 0, 'gossip': 0, **facts}, names)[0]['odds']
    assert chance(closeness_a=1) == 0
    assert chance(closeness_a=2) < chance(closeness_a=3) < chance(closeness_a=4) < chance(closeness_a=5)
    assert chance(closeness_a=3, own=1) > chance(closeness_a=3)
    assert chance(closeness_a=3, gossip=1) > chance(closeness_a=3)


def test_news_spreads_one_hop_each_evening_and_everyone_remembers_who_told_them(client, cast, clock, monkeypatch):
    monkeypatch.setattr(news, 'passes', lambda *_args: True)
    sync(client)
    assert list(holders(client)) == [key(cast['Mira'])]  # Not evening yet: only Mira knows.

    evening(clock)
    sync(client)
    found = holders(client)
    billy = found[key(cast['Billy'])]
    assert (billy['told_by'], billy['hop'], billy['via']) == (key(cast['Mira']), 1, 'word')
    assert key(cast['Sally']) not in found  # Sally doesn't know Mira: she hears tomorrow, from Billy.
    with client.app.state.database.connect() as connection:
        family = [person['seed'] for person in circle.people(connection, by_id(connection, cast['Mira'])
                                                             ['active_timeline_id'])]
    assert family and all(found[seed]['told_by'] == key(cast['Mira']) for seed in family)

    clock.advance(timedelta(days=1))
    sync(client)
    sally = holders(client)[key(cast['Sally'])]
    assert (sally['told_by'], sally['hop'], sally['heard_on']) == (key(cast['Billy']), 2, clock.now().date().isoformat())


def test_it_stops_travelling_after_a_few_days(client, cast, clock, monkeypatch):
    monkeypatch.setattr(news, 'passes', lambda *_args: False)
    evening(clock)
    clock.advance(timedelta(days=news.SPREAD_DAYS - 1))
    sync(client)  # Nobody passed it on, any evening it could travel.
    monkeypatch.setattr(news, 'passes', lambda *_args: True)
    clock.advance(timedelta(days=3))
    sync(client)
    assert list(holders(client)) == [key(cast['Mira'])]


def test_who_heard_shows_on_today_and_in_their_chats(client, cast, clock, monkeypatch):
    monkeypatch.setattr(news, 'passes', lambda *_args: True)
    evening(clock)
    listed = ok(client.get('/api/life/news'))
    assert listed[0]['text'] == TEXT
    billy = next(item for item in listed[0]['heard'] if item['companion_id'] == cast['Billy'])
    assert billy['name'] == 'Billy Hart' and billy['from'] is None

    with client.app.state.database.connect() as connection:
        lines = news.context_lines(connection, by_id(connection, cast['Billy']), clock.now())
        assert lines == [(lines[0][0], f'- Heard on {clock.now().date()} (Mira told you): {TEXT}.')]
        assert news.context_lines(connection, by_id(connection, cast['Mira']), clock.now()) == []
        trigger = openers.heard_news(connection, by_id(connection, cast['Billy']), clock.now())[0]
    assert trigger.template == f'Did you hear about Mira?? {TEXT}!' and "don't say how" in trigger.reason


def test_a_group_tells_who_has_not_heard_and_hearing_it_there_counts(client, cast, clock, provider, monkeypatch):
    monkeypatch.setattr(news, 'passes', lambda _connection, _ties, _item, _teller, listener, _day:
                        listener == key(cast['Billy']))
    evening(clock)
    sync(client)
    group = start(client, [cast['Billy'], cast['Sally']])
    say(client, group['id'], 'How was everyone\'s day?', 'news-group-01')
    billy = next(request['prompt'] for request in provider.requests if 'Write Billy' in request['messages'][-1]['content'])
    assert f"- You heard (Mira told you): {TEXT}. Sally hasn't heard yet." in billy

    say(client, group['id'], 'Guess what, Mira took up pottery for real!', 'news-group-02')
    sally = holders(client)[key(cast['Sally'])]
    assert (sally['told_by'], sally['via']) == ('user', 'group')


def test_a_secret_remembers_who_told_them(client, cast, provider):
    statement = 'Billy is moving to Denver in May'
    ok(client.post('/api/secrets', json={'statement': statement, 'about': ['Billy'], 'knows': [cast['Billy']],
                                         'kept_from': []}))
    group = start(client, [cast['Billy'], cast['Sally']])
    say(client, group['id'], 'Sally, Billy is moving to Denver in May!', 'news-secret-01')
    listed = ok(client.get('/api/secrets'))['secrets'][0]
    sally = next(person for person in listed['knows'] if person['name'] == 'Sally Moss')
    assert sally['told_by'] == 'the user' and sally['how'] == 'heard it from you in a group'
    database = client.app.state.database
    with database.connect(write=True) as connection:
        connection.execute('UPDATE workspace_settings SET automatic_memory=1')
        lines = secrets.context_lines(connection, by_id(connection, cast['Sally']))
    assert '(the user told you, since ' in lines[0][1]


def test_a_new_chapter_is_news_until_it_is_undone(client, clock, monkeypatch):
    from test_chapters import arrange

    client.post('/api/companion', json={'name': 'Mira Lane', 'timezone': 'UTC', 'location': 'Fells Point, Baltimore'})
    arrange(client, monkeypatch, clock, 'hobby')
    reconcile(client)
    chapter = ok(client.get('/api/life/chapters'))[0]
    sync(client)
    with client.app.state.database.connect() as connection:
        row = connection.execute('SELECT text, status FROM news').fetchone()
    assert (row['text'], row['status']) == (chapter['title'], 'active')
    client.post(f"/api/life/chapters/{chapter['id']}/undo")
    sync(client)
    with client.app.state.database.connect() as connection:
        assert connection.execute('SELECT status FROM news').fetchone()[0] == 'ended'
