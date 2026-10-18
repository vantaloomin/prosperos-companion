"""Loss and grief (companion/life/loss.py): the switch and the Loss slider, who can pass away, the odds, a death and what
it changes, grief over the weeks, the funeral, bringing someone back and the obituary."""
import re
import string
from datetime import date, timedelta

import pytest

from companion import consequences, moods
from companion.characters import current
from companion.database import decode, encode, one, optional
from companion.life import big_days, circle, loss, openers, outings
from companion.world import paper, turnover

ROLES = ['dad', 'sister', 'close friend', 'friend', 'cousin']


@pytest.fixture(autouse=True)
def on(monkeypatch):
    monkeypatch.setattr(big_days, 'ACTIVE', True)
    monkeypatch.setattr(big_days, 'FIRST_TEXTS', True)


def make(client):
    response = client.post('/api/companion', json={'name': 'Mira Costa', 'timezone': 'UTC', 'home_city': 'Baltimore',
                                                     'relationship': 'romance'})
    assert response.status_code == 200, response.text
    assert client.get('/api/life/circle').status_code == 200
    with client.app.state.database.connect(write=True) as connection:
        rows = circle.people(connection, current(connection)['active_timeline_id'])
        for row, role in zip(rows, ROLES, strict=False):
            details = {key: value for key, value in decode(row['details']).items() if key != 'sheet'}
            connection.execute('UPDATE circle_people SET role=?, details=? WHERE id=?',
                               (role, encode({**details, 'local': True, 'age': 40}), row['id']))
        for row in rows[len(ROLES):]:
            connection.execute("UPDATE circle_people SET status='removed' WHERE id=?", (row['id'],))


def switch(client, on=True, level=2):
    response = client.put('/api/life/settings', json={'people_pass_away': on, 'loss': level})
    assert response.status_code == 200, response.text
    return response.json()


def person(client, role, everyone=False):
    with client.app.state.database.connect() as connection:
        return next(row for row in circle.people(connection, current(connection)['active_timeline_id'], everyone)
                    if row['role'] == role)


def set_details(client, person_id, **values):
    with client.app.state.database.connect(write=True) as connection:
        row = one(connection, 'SELECT details FROM circle_people WHERE id=?', (person_id,))
        connection.execute('UPDATE circle_people SET details=? WHERE id=?',
                           (encode({**decode(row['details']), **values}), person_id))


def advance(client, clock):
    with client.app.state.database.connect(write=True) as connection:
        loss.advance(connection, current(connection), clock.now())
        big_days.advance(connection, current(connection), clock.now())


def losses(client):
    with client.app.state.database.connect() as connection:
        return [loss.view(row) for row in connection.execute('SELECT * FROM losses').fetchall()]


def dies(monkeypatch, who=None):
    """The engine's dice say they pass away (only for `who`'s first name, when given)."""
    real = consequences.roll

    def roll(seed, found):
        return 1 if ':loss:' in seed and (who is None or who in seed) else real(seed, found)
    monkeypatch.setattr(consequences, 'roll', roll)


def lines(client, clock):
    with client.app.state.database.connect() as connection:
        return [text for _key, text in loss.context_lines(connection, current(connection), clock.now())]


def test_the_banks_have_enough_lines_with_their_places():
    bank = loss.bank()
    wanted = {'news': ({'who', 'when'}, set()), 'obituaries': ({'name'}, {'their'})}
    for key, (names, maybe) in wanted.items():
        assert len(bank[key]) >= 100 and len(set(bank[key])) == len(bank[key]), key
        for line in bank[key]:
            found = {name for _text, name, _spec, _conv in string.Formatter().parse(line) if name}
            assert names <= found <= names | maybe, line
    assert len(bank['memories']) >= 100 and len(set(bank['memories'])) == len(bank['memories'])
    for line in bank['memories']:
        assert {name for _t, name, _s, _c in string.Formatter().parse(line) if name} <= {'they', 'them', 'their'}
        assert not re.search(r'\{they\} (?!always\b|sometimes\b|perhaps\b)(?:is|was|were|are|has|does|\w+s)\b', line), line
    found = big_days.bank()
    assert 'funeral' not in found['gifts']
    assert not [line for line in bank['obituaries'] if re.search(r'\b(?:mill|shop|market|bakery|harvest|forge)\b', line)]
    assert len(found['invite_funeral']) >= 100
    for line in found['invite_funeral']:
        assert {name for _t, name, _s, _c in string.Formatter().parse(line) if name} == {'event', 'day', 'time', 'place'}
    # Grief is sadness and missing someone: nothing in the banks reads as self-harm.
    words = re.compile(r'suicid|self[- ]harm|kill (?:my|me)|want to die|end it|can.?t go on|hopeless|overdos', re.I)
    for key in ('news', 'memories', 'obituaries'):
        assert not any(words.search(line) for line in bank[key]), key
    for rules in bank['customs'].values():
        assert {'word', 'service', 'after', 'days', 'at', 'until', 'wear', 'words', 'venue'} <= set(rules)


def test_off_by_default_on_every_preset_and_nobody_passes_away(client, clock, monkeypatch):
    make(client)
    found = client.get('/api/life/settings').json()
    assert found['people_pass_away'] is False and found['loss'] == 2
    dies(monkeypatch)
    advance(client, clock)
    assert losses(client) == []
    found = switch(client)
    assert found['people_pass_away'] is True and turnover.STATE.loss == 3


def test_the_odds_rise_steeply_with_age_and_with_a_parent_in_treatment():
    names = {'a': 'Ray', 'name': 'Mira', 'role': 'dad'}

    def chance(**facts):
        return consequences.odds(loss.CHOICE, {'age': 40, 'loss': 2, 'frail': 0, 'treatment': 0, **facts}, names)[1]

    young, old, oldest = chance(age=30)['odds'], chance(age=80)['odds'], chance(age=95)['odds']
    assert young < 0.001 and 0.01 < old < 0.03 and oldest > 0.05
    assert chance(age=70, treatment=1)['odds'] > 5 * chance(age=70)['odds']
    frail = chance(age=80, frail=1)
    assert frail['odds'] > 0.2 and 'caring for Ray has been getting harder' in frail['reasons']
    assert chance(age=80, loss=0)['odds'] < chance(age=80, loss=3)['odds']


def test_who_is_spared_the_young_partners_and_people_the_sheet_names(client, clock, monkeypatch):
    make(client)
    switch(client)
    dies(monkeypatch)
    sister, friend = person(client, 'sister'), person(client, 'friend')
    set_details(client, sister['id'], sheet='Ana')  # Written into the character's description.
    set_details(client, friend['id'], age=12)
    advance(client, clock)
    planned = {row['person_id'] for row in losses(client)}
    assert sister['id'] not in planned and friend['id'] not in planned
    assert person(client, 'dad')['id'] in planned
    # The user says the sister can pass away after all.
    response = client.post(f"/api/life/circle/{sister['id']}/spared", json={'spared': False})
    assert response.status_code == 200 and response.json()['spared'] is False
    advance(client, clock)
    assert sister['id'] in {row['person_id'] for row in losses(client)}
    # Spared again: the death to come is gone.
    client.post(f"/api/life/circle/{sister['id']}/spared", json={'spared': True})
    assert sister['id'] not in {row['person_id'] for row in losses(client)}


def test_a_death_on_its_day_grief_the_news_and_fewer_plans(client, clock, monkeypatch):
    make(client)
    switch(client)
    dies(monkeypatch)
    dad = person(client, 'dad')
    advance(client, clock)
    row = next(row for row in losses(client) if row['person_id'] == dad['id'])
    assert row['happened'] == 0 and row['details']['depth'] == 3
    assert date.fromisoformat(row['died_on']) >= clock.now().date() + timedelta(days=loss.SOONEST)
    clock.advance(date.fromisoformat(row['died_on']) - clock.now().date() + timedelta(hours=2))
    advance(client, clock)
    late = person(client, 'dad', everyone=True)
    assert late['status'] == 'removed' and decode(late['details'])['late'] == row['died_on']
    shown = next(item for item in client.get('/api/life/circle').json() if item['id'] == dad['id'])
    assert shown['loss']['died_on'] == row['died_on']
    found = lines(client, clock)
    assert any(text.startswith(f"- Your dad {dad['name'].split()[0]} died on") and "it's still raw" in text
               for text in found), found
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        mood = moods.current(connection, f"companion:{companion['id']}", clock.now())
        assert mood['feeling'] == 'sad' and mood['intensity'] == 2
        news = loss.news_due(connection, companion, clock.now())
        assert len(news) == 1 and 'died today' in news[0].reason
        assert loss.holds_back(connection, companion, clock.now())
        held = [trigger for trigger in openers.candidates(connection, companion, clock.now())
                if trigger.kind in ('together', 'kitchen')]
        assert held == []
    # Weeks on it lifts, and after that a plain line keeps the fact.
    clock.advance(timedelta(days=60))
    assert any("it's lifting slowly" in text for text in lines(client, clock))
    clock.advance(timedelta(days=60))
    assert any('You still miss' in text for text in lines(client, clock))
    with client.app.state.database.connect() as connection:
        assert not loss.holds_back(connection, current(connection), clock.now())


def test_the_funeral_is_a_quiet_big_day_by_the_citys_customs(client, clock, monkeypatch):
    make(client)
    switch(client)
    dies(monkeypatch)
    advance(client, clock)
    row = next(row for row in losses(client) if row['role'] == 'dad')
    clock.advance(date.fromisoformat(row['died_on']) - clock.now().date() + timedelta(hours=2))
    advance(client, clock)
    with client.app.state.database.connect() as connection:
        funeral = next(item for item in big_days.rows(connection, current(connection)['active_timeline_id'])
                       if item['source'] == f"loss:{row['id']}")
        companion = current(connection)
        scene = big_days.scene(connection, companion, {'place': {'big_day': funeral['id']}, 'until_time': '15:00'},
                               clock.now())
    assert funeral['source'] == f"loss:{row['id']}" and funeral['details']['word'] == 'funeral'
    assert funeral['outfit'] == 'dark, simple clothes' and funeral['at_time'] == '11:00' and funeral['gift'] == ''
    assert loss.flowers({'kind': 'circle', 'role': 'close friend'}) == 'flowers'
    assert loss.flowers({'kind': 'town', 'role': ''}) == 'flowers'
    assert big_days.title(funeral).endswith("'s funeral") and 'sad, quiet day' in scene
    assert big_days.buzz_line({**funeral, 'local_date': clock.now().date().isoformat()}, clock.now().date()) == ''
    entry = outings.entry({'outing': {'id': 'o', 'message_id': 'm', 'at_time': '11:00', 'until_time': '15:00', 'rolls': 0,
                                      'activity': 'big-day', 'place': {**funeral['place'], 'quiet': True,
                                                                         'title': big_days.title(funeral)}}},
                          {}, {'name': 'Mira Costa'})
    assert entry['mood'] == 'sad' and entry['post'] == 'Said goodbye today.'


def test_bringing_them_back_undoes_it_all(client, clock, monkeypatch):
    make(client)
    switch(client)
    dies(monkeypatch)
    advance(client, clock)
    row = next(row for row in losses(client) if row['role'] == 'dad')
    clock.advance(date.fromisoformat(row['died_on']) - clock.now().date() + timedelta(hours=2))
    advance(client, clock)
    room = client.get('/api/life/circle/room').json()
    assert room['people'] == len(ROLES), room
    response = client.post(f"/api/life/circle/{row['person_id']}/bring-back")
    assert response.status_code == 200, response.text
    assert response.json()['status'] == 'active' and 'late' not in response.json()
    assert all(item['id'] != row['id'] for item in losses(client))
    with client.app.state.database.connect() as connection:
        assert one(connection, 'SELECT picked FROM consequences WHERE id=?', (row['consequence_id'],))['picked'] == 0
        assert optional(connection, "SELECT id FROM big_days WHERE source=? AND status IN ('planned', 'invited')",
                        (f"loss:{row['id']}",)) is None
    assert not any(row['name'].split()[0] in text for text in lines(client, clock))


def test_turning_the_switch_off_cancels_deaths_to_come(client, clock, monkeypatch):
    make(client)
    switch(client)
    dies(monkeypatch)
    advance(client, clock)
    assert losses(client)
    switch(client, on=False)
    assert losses(client) == [] and turnover.STATE.loss == 0
    advance(client, clock)
    assert losses(client) == []


def test_the_paper_runs_an_obituary_for_someone_who_passed():
    sheet = {'key': 'town:baltimore:x:1', 'name': 'Ada', 'full': 'Ada Fenwick', 'kind': 'resident', 'home': 'hampden',
             'pronouns': 'she/her'}
    data = {'neighborhoods': [{'id': 'hampden', 'name': 'Hampden'}]}
    item = paper.departure(data, sheet, 'passed', 87)
    assert item['headline'] == 'Ada Fenwick has died.' and item['obituary']
    assert item['text'].startswith('Ada Fenwick, of Hampden, died this week at 87. ')
    assert '{' not in item['text']


def test_the_funeral_is_in_a_chapel_or_temple_never_a_lighthouse(monkeypatch):
    monkeypatch.setattr(loss, 'customs', lambda connection, companion: loss.bank()['customs']['us'])
    place = {'neighborhood': 'n', 'summary': '', 'cost': '', 'cuisine': ''}
    data = {'id': 'c', 'name': 'Lakeside', 'era': None, 'neighborhoods': [{'id': 'n', 'name': 'North'}],
            'places': [{**place, 'id': 'l', 'name': 'Grosse Point Lighthouse', 'kind': 'landmark'},
                       {**place, 'id': 'p', 'name': 'Ping Tom Memorial Park', 'kind': 'park'}]}
    day = date(2026, 10, 20)
    assert loss.venue_for(None, {}, data, 's', day)['name'] == 'the funeral home'
    data['places'].append({**place, 'id': 't', 'name': 'Kotoku-in', 'kind': 'temple'})
    assert loss.venue_for(None, {}, data, 's', day)['id'] == 't'
    data['places'].append({**place, 'id': 'u', 'name': 'Unity Chapel', 'kind': 'landmark'})
    assert loss.venue_for(None, {}, data, 's', day)['id'] == 'u'


def test_a_parent_whose_care_went_harder_is_likelier_to_pass_and_their_care_ends(client, clock, monkeypatch):
    from conftest import reconcile
    from test_big_turns import begun, details, next_stage
    from test_big_turns_two import land, make, parent

    from companion.life import health_turns
    make(client, monkeypatch, 'Mira is 34, an accountant.')
    reconcile(client)
    mom = parent(client, 80)
    chapter = begun(client, monkeypatch, clock, 'caring')
    next_stage(client, clock, chapter['id'])
    land(monkeypatch, health_turns.HOW, 2)
    next_stage(client, clock, chapter['id'])
    today = clock.now().date()
    with client.app.state.database.connect() as connection:
        turns = loss.health_turns(connection, current(connection)['active_timeline_id'], today)
    assert [fact for _key, _since, fact in turns[mom['id']]] == ['frail']
    switch(client)
    dies(monkeypatch, mom['id'])
    advance(client, clock)
    row = next(row for row in losses(client) if row['person_id'] == mom['id'])
    assert row['details']['cause'] == 'illness'
    clock.advance(date.fromisoformat(row['died_on']) - clock.now().date() + timedelta(hours=2))
    advance(client, clock)
    found = details(client, chapter['id'])
    assert found['stage'] == 'ended' and found['why'] == 'passed'


def test_someone_who_died_leaves_the_living_and_their_plans_with_the_companion(client, clock, monkeypatch, provider):
    from companion.database import identifier
    make(client)
    switch(client)
    dies(monkeypatch)
    advance(client, clock)
    row = next(row for row in losses(client) if row['role'] == 'dad')
    clock.advance(date.fromisoformat(row['died_on']) - clock.now().date() + timedelta(hours=2))
    later = clock.now() + timedelta(days=2)
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        # A drop-in from them planned for after the day they die.
        connection.execute(
            "INSERT INTO life_agenda (id, timeline_id, subject, slot_key, local_date, starts_at, ends_at, block, entry, "
            "status, basis, created_at) VALUES (?, ?, 'companion', 'evening@later', ?, ?, ?, '{}', ?, 'upcoming', "
            "'seed', ?)", (identifier(), companion['active_timeline_id'], later.date().isoformat(), later.isoformat(),
                           (later + timedelta(hours=3)).isoformat(),
                           encode({'summary': 'Dinner with them.', 'with': {'id': row['person_id']}}),
                           clock.now().isoformat()))
    advance(client, clock)
    with client.app.state.database.connect() as connection:
        left = connection.execute("SELECT id FROM life_agenda WHERE status='upcoming' AND json_extract(entry, "
                                  "'$.with.id')=?", (row['person_id'],)).fetchall()
    assert left == []
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    client.post('/api/conversation/messages', json={'text': 'How is everyone?', 'client_id': 'loss-0001'})
    prompt = provider.requests[-1]['prompt']
    living = prompt.split('People in your life')[1].split('\n## ')[0]
    name = row['name'].split()[0]
    assert f'- {name} (' not in living and f'Your dad {name} died on' in prompt
