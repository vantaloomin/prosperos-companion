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
    assert young < 0.002 and 0.04 < old < 0.07 and oldest > 0.15
    # True to life is about real rates (v0.15): about 1% a year at 60, 2% at 70, 5% at 80 and 15% at 90.
    for age, low, high in ((60, 0.007, 0.013), (70, 0.017, 0.03), (80, 0.04, 0.07), (90, 0.1, 0.18)):
        assert low < chance(age=age)['odds'] < high, age
    # The other levels scale with it.
    assert chance(age=80, loss=0)['odds'] < chance(age=80, loss=1)['odds'] < old < chance(age=80, loss=3)['odds']
    # Old eras (1895, Camelot): about twice as likely, and said why.
    then = chance(age=80, old_era=1)
    assert 1.8 * old < then['odds'] < 2.1 * old and 'people die younger in these times' in then['reasons']
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
    dad = person(client, 'dad')
    dies(monkeypatch, dad['id'])  # Only the dad, so no one else's news falls on the same day.
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
        assert mood['reason'].endswith(f"'s dad {dad['name'].split()[0]} died"), mood['reason']
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
    assert row['details']['cause'] == 'long illness'
    clock.advance(date.fromisoformat(row['died_on']) - clock.now().date() + timedelta(hours=2))
    advance(client, clock)
    found = details(client, chapter['id'])
    assert found['stage'] == 'ended' and found['why'] == 'passed'


def test_someone_who_died_leaves_the_living_and_their_plans_with_the_companion(client, clock, monkeypatch, provider):
    from companion.database import identifier
    make(client)
    switch(client)
    dies(monkeypatch, person(client, 'dad')['id'])
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


def test_a_branch_after_a_death_keeps_one_funeral(client, clock, monkeypatch, provider):
    make(client)
    switch(client)
    dies(monkeypatch)
    advance(client, clock)
    row = next(row for row in losses(client) if row['role'] == 'dad')
    clock.advance(date.fromisoformat(row['died_on']) - clock.now().date() + timedelta(hours=2))
    advance(client, clock)
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    sent = client.post('/api/conversation/messages', json={'text': 'I am so sorry.', 'client_id': 'loss-fork-1'})
    response = client.post('/api/timelines', json={'message_id': sent.json()['message']['id']})
    assert response.status_code == 200, response.text
    assert client.post(f"/api/timelines/{response.json()['id']}/activate").status_code == 200
    advance(client, clock)
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        copied = optional(connection, "SELECT id FROM losses WHERE timeline_id=? AND role='dad'",
                          (companion['active_timeline_id'],))
        funerals = [item for item in big_days.rows(connection, companion['active_timeline_id'])
                    if item['kind'] == 'funeral' and item['status'] != 'called_off' and item['details']['role'] == 'dad']
    assert len(funerals) == 1 and funerals[0]['source'] == f"loss:{copied['id']}", funerals


def test_the_funeral_is_never_at_a_food_hall_a_bar_or_a_library(monkeypatch):
    place = {'neighborhood': 'n', 'summary': '', 'cost': '', 'cuisine': ''}
    data = {'id': 'c', 'name': 'Town', 'era': None, 'neighborhoods': [{'id': 'n', 'name': 'North'}],
            'places': [{**place, 'id': 'f', 'name': 'Umeda food hall', 'kind': 'market'},
                       {**place, 'id': 'a', 'name': 'Osaka-jo Hall', 'kind': 'venue'},
                       {**place, 'id': 'p', 'name': 'Central Public Hall', 'kind': 'landmark'},
                       {**place, 'id': 'b', 'name': 'The Churchill Arms', 'kind': 'bar'},
                       {**place, 'id': 'l', 'name': 'the abbey library', 'kind': 'library'}]}
    day = date(2026, 10, 20)
    for culture in ('japan', 'uk', 'medieval-england'):
        monkeypatch.setattr(loss, 'customs', lambda connection, companion, key=culture: loss.bank()['customs'][key])
        assert loss.venue_for(None, {}, data, 's', day)['id'] == '~funeral', culture
    data['places'].append({**place, 'id': 't', 'name': 'Shitennoji', 'kind': 'temple'})
    assert loss.venue_for(None, {}, data, 's', day)['id'] == 't'


def test_the_news_the_memories_and_the_invitation_fit_the_era():
    bank, invites = loss.bank(), big_days.bank()['invite_funeral']
    for era in ('victorian', 'medieval', 'fantasy'):
        for line in [*loss.fitting(bank['news'], era), *loss.fitting(invites, era)]:
            assert not re.search(r'\btext|\bcall|\bphone', line, re.I), (era, line)
        assert not [line for line in loss.fitting(bank['memories'], era) if re.search(r'\bradio\b', line)]
    assert not [line for line in loss.fitting(bank['memories'], 'medieval') if re.search(r'photograph|coffee', line)]
    assert loss.fitting(bank['news'], 'modern') == bank['news']
    assert loss.fitting(bank['news'], 'jazz-age') != bank['news']  # No texting in 1925 either.
    row = {'id': 'x', 'kind': 'funeral', 'details': {'name': 'Ray', 'role': 'dad', 'word': 'funeral'},
           'place': {'name': 'the parish church'}}
    for index in range(40):
        line = big_days.invitation({**row, 'id': f'x{index}'}, 'Saturday', '11', 'victorian')
        assert not re.search(r'\bcall\b|coffee', line), line


def test_the_news_of_a_death_goes_out_before_the_funeral_invitation(client, clock, monkeypatch):
    make(client)
    switch(client)
    dies(monkeypatch, person(client, 'cousin')['id'])
    monkeypatch.setattr(loss, 'FIRST_TEXTS', True)
    advance(client, clock)
    row = next(row for row in losses(client) if row['role'] == 'cousin')
    clock.advance(date.fromisoformat(row['died_on']) - clock.now().date() + timedelta(hours=2))
    advance(client, clock)
    with client.app.state.database.connect(write=True) as connection:
        connection.execute("UPDATE big_days SET invite=1, invite_on=? WHERE kind='funeral'",
                           (clock.now().date().isoformat(),))
        # The circle's own big days are random; one asked to near the funeral would hold its invitation back.
        connection.execute("UPDATE big_days SET invite=0 WHERE kind!='funeral'")
        kinds = [trigger.key.split(':')[0] for trigger in openers.candidates(connection, current(connection),
                                                                            clock.now())]
    assert 'bigday' in kinds and kinds.index('loss') < kinds.index('bigday'), kinds


def test_a_funeral_in_1895_is_for_their_mother_not_their_mom(client, clock, monkeypatch):
    response = client.post('/api/companion', json={'name': 'Eliza Thorne', 'timezone': 'Europe/London',
                                                     'home_city': 'london-1895', 'relationship': 'romance'})
    assert response.status_code == 200, response.text
    client.get('/api/life/circle')
    with client.app.state.database.connect(write=True) as connection:
        row = circle.people(connection, current(connection)['active_timeline_id'])[0]
        details = {key: value for key, value in decode(row['details']).items() if key != 'sheet'}
        connection.execute("UPDATE circle_people SET role='mom', details=? WHERE id=?",
                           (encode({**details, 'local': True, 'age': 70}), row['id']))
    switch(client)
    dies(monkeypatch, row['id'])
    advance(client, clock)
    died = next(item for item in losses(client) if item['person_id'] == row['id'])['died_on']
    clock.advance(date.fromisoformat(died) - clock.now().date() + timedelta(hours=2))
    advance(client, clock)
    with client.app.state.database.connect() as connection:
        funeral = next(item for item in big_days.rows(connection, current(connection)['active_timeline_id'])
                       if item['kind'] == 'funeral')
    assert big_days.said(funeral).startswith('your mother ') and 'mom' not in big_days.invitation(funeral, 'Monday', '11')


def test_retro_im_keeps_the_plain_mood_line_while_they_grieve(client, clock, monkeypatch):
    from companion.life import status
    make(client)
    switch(client)
    dies(monkeypatch, person(client, 'dad')['id'])
    advance(client, clock)
    row = next(row for row in losses(client) if row['role'] == 'dad')
    clock.advance(date.fromisoformat(row['died_on']) - clock.now().date() + timedelta(hours=2))
    advance(client, clock)
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        assert status.grieving(connection, companion, clock.now())
        for index in range(20):
            line = status.mood_line(connection, companion, clock.now(), f'seed-{index}', retro=True)
            assert line in status.MOODS['sad'], line
    clock.advance(timedelta(days=60))  # Lifting: they are mostly themselves again.
    with client.app.state.database.connect() as connection:
        assert not status.grieving(connection, current(connection), clock.now())


# v0.15 follow-ups ---------------------------------------------------------------------------------------------------

def late(client, role, died_on, kind='circle', **details):
    """A death that already happened, written straight in."""
    from companion.database import identifier
    found = person(client, role)
    with client.app.state.database.connect(write=True) as connection:
        loss_id = identifier()
        connection.execute(
            'INSERT INTO losses (id, timeline_id, kind, person_id, name, role, details, died_on, happened, created_at, '
            "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, '2026-01-01', '2026-01-01')",
            (loss_id, current(connection)['active_timeline_id'], kind, found['id'], found['name'], role,
             encode({'pronouns': 'she/her', 'depth': loss.depth(role), 'cause': 'sudden', **details}),
             died_on.isoformat()))
    return {'id': loss_id, 'name': found['name']}


def test_old_eras_double_the_odds_for_the_circle_from_the_rate_table(client, clock, monkeypatch):
    assert loss.death_factor('victorian') == loss.death_factor('medieval') == 2.0
    assert loss.death_factor('modern') == loss.death_factor('jazz-age') == 1.0
    make(client)
    dad = person(client, 'dad')
    seen = []
    real = consequences.decide

    def decide(connection, **kwargs):
        if kwargs['choice'] == loss.CHOICE:
            seen.append(kwargs['facts'])
        return real(connection, **kwargs)
    monkeypatch.setattr(consequences, 'decide', decide)
    monkeypatch.setattr(loss, 'era_of', lambda connection, companion: 'victorian')
    switch(client)
    advance(client, clock)
    assert seen and all(facts['old_era'] == 1 for facts in seen)
    with client.app.state.database.connect() as connection:
        assert loss.facts_for(connection, dad, clock.now().date(), None, 2)['old_era'] == 0


def test_the_town_dies_at_real_rates_when_true_to_life():
    for age, low, high in ((60, 0.007, 0.013), (70, 0.017, 0.03), (80, 0.04, 0.07), (90, 0.1, 0.18)):
        assert low < turnover.chances('resident', age, 2, 3)['passed'] < high, age
    assert turnover.chances('resident', 80, 2, 1)['passed'] < turnover.chances('resident', 80, 2, 4)['passed']


@pytest.mark.parametrize(('drama', 'on', 'level', 'expected'),
                         [(0, 0, 2, 0), (1, 0, 2, 2), (3, 0, 2, 3), (0, 1, 2, 2), (0, 0, 1, 1), (3, 0, 0, 0)])
def test_an_older_world_gets_the_loss_slider_by_its_preset_unless_the_user_moved_it(tmp_path, drama, on, level,
                                                                                       expected):
    import sqlite3

    from companion.database import add_columns, initialize
    connection = sqlite3.connect(tmp_path / 'old.sqlite3')
    initialize(connection, '2026-10-01T00:00:00Z')
    connection.execute('ALTER TABLE life_settings DROP COLUMN loss_by_preset')
    connection.execute('UPDATE life_settings SET drama=?, people_pass_away=?, loss=?', (drama, on, level))
    add_columns(connection)
    assert connection.execute('SELECT loss FROM life_settings').fetchone() == (expected,)
    connection.close()


def test_the_settings_hide_the_upgrade_marker(client):
    make(client)
    assert 'loss_by_preset' not in client.get('/api/life/settings').json()


def test_their_own_feed_posts_only_a_quiet_status_while_grief_is_raw_or_heavy(client, clock, monkeypatch):
    from companion.life import social
    make(client)
    today = clock.now().date()
    late(client, 'dad', today - timedelta(days=2))
    monkeypatch.setattr(social, 'unit', lambda *_args: 0.0)  # Every post that could go up does.
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        posts = social.day_posts(connection, companion, {}, clock.now() - timedelta(days=1), clock.now())
        assert posts and all(post['kind'] == 'status' and post['content']['text'] in social.STATUS['grief']
                             and post['content']['tone'] == 'down' for post in posts), posts
        assert loss.raw_or_heavy(connection, companion['active_timeline_id'], today)
        # Weeks on, once it lifts, the feed is itself again.
        later = clock.now() + timedelta(days=60)
        posts = social.day_posts(connection, companion, {}, later - timedelta(days=1), later)
        assert any(post['kind'] == 'question' for post in posts)
        assert not any(post['content']['text'] in social.STATUS['grief'] for post in posts)


def test_life_posts_are_held_back_while_grief_is_raw_or_heavy(client, clock):
    from companion.database import identifier
    from companion.life import feed
    make(client)
    now = clock.now()
    late(client, 'dad', now.date() - timedelta(days=2))
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        timeline = companion['active_timeline_id']
        for days, summary in ((0, 'Sore tomorrow, worth it today.'), (5, 'Market finds.'), (60, 'Lifting again.')):
            at = (now - timedelta(days=days) if days < 60 else now + timedelta(days=days)).isoformat()
            event_id = identifier()
            connection.execute(
                'INSERT INTO life_events (id, companion_id, timeline_id, idempotency_key, kind, status, summary, '
                'starts_at, ends_at, character_version_id, permission_revision, created_at, decided_at) '
                "VALUES (?, ?, ?, ?, 'ordinary', 'committed', ?, ?, ?, ?, 1, ?, ?)",
                (event_id, companion['id'], timeline, identifier(), summary, at, at, companion['active_version_id'],
                 at, at))
            feed.create(connection, timeline, 'event', f'event:{event_id}', [event_id], at, at)
        shown = [post['events'][0]['summary'] for post in feed.visible_posts(connection, timeline)]
    # Two days after the death is held back; five days before it and weeks after, once grief lifts, are not.
    assert shown == ['Lifting again.', 'Market finds.'], shown


def test_a_post_already_read_stays_on_show_through_grief(client, clock):
    """A workspace from v0.14 showed every post on the days after a death: one the user read stays."""
    from companion.database import identifier
    from companion.life import feed
    make(client)
    now = clock.now()
    late(client, 'dad', now.date() - timedelta(days=2))
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        timeline = companion['active_timeline_id']
        for summary, read in (('Read already.', True), ('Not read yet.', False)):
            at, event_id = now.isoformat(), identifier()
            connection.execute(
                'INSERT INTO life_events (id, companion_id, timeline_id, idempotency_key, kind, status, summary, '
                'starts_at, ends_at, character_version_id, permission_revision, created_at, decided_at) '
                "VALUES (?, ?, ?, ?, 'ordinary', 'committed', ?, ?, ?, ?, 1, ?, ?)",
                (event_id, companion['id'], timeline, identifier(), summary, at, at, companion['active_version_id'],
                 at, at))
            feed.create(connection, timeline, 'event', f'event:{event_id}', [event_id], at, at)
            if read:
                connection.execute('UPDATE feed_posts SET read_at=? WHERE idempotency_key=?', (at, f'event:{event_id}'))
        shown = [post['events'][0]['summary'] for post in feed.visible_posts(connection, timeline)]
    assert shown == ['Read already.'], shown


def test_friends_answer_a_quiet_grief_status_gently():
    from companion.life import social
    for text in social.STATUS['grief']:
        pool = social.comment_pool('status', {'text': text, 'tone': 'down'}, 'friend', False)
        assert pool == social.COMMENTS['grief'] and 'Rest up!' not in pool and 'You deserve a nap.' not in pool
    assert social.comment_pool('status', {'text': 'Coffee first.', 'tone': 'down'}, 'friend', False) == \
        social.COMMENTS['down']


def test_a_death_anniversary_is_an_occasion_on_its_day_and_no_first_text(client, clock):
    from companion.life import occasions
    make(client)
    today = clock.now().date()
    found = late(client, 'dad', today.replace(year=today.year - 1))
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        items = [item for item in occasions.occasions(connection, companion, clock.now())
                 if item['kind'] == 'death_anniversary']
        assert len(items) == 1 and items[0]['days'] == 0 and items[0]['span'] == 'a year', items
        first = found['name'].split()[0]
        assert items[0]['person'] == first and items[0]['relation'] == 'dad'
        assert items[0]['text'].startswith(f'- Today it has been a year since your dad {first} died (')
        assert "You're thinking of her today" in items[0]['text']
        assert not [item for item in openers.occasion(connection, companion, clock.now())
                    if 'death_anniversary' in item.key]
    # The loss section leaves the day to the occasion, and keeps the plain fact on other days.
    assert not any('died in' in text for text in lines(client, clock))
    clock.advance(timedelta(days=1))
    assert any('You still miss' in text for text in lines(client, clock))
    with client.app.state.database.connect() as connection:
        assert not [item for item in occasions.occasions(connection, current(connection), clock.now())
                    if item['kind'] == 'death_anniversary']


def test_a_family_funeral_is_asked_even_with_another_big_day_near(client, clock):
    from companion.database import identifier
    make(client)
    today = clock.now().date()
    dad, friend = late(client, 'dad', today), late(client, 'close friend', today)
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        found = {item['details']['loss_id']: item for item in loss.funerals(connection, companion, today, clock.now())}
        assert found[dad['id']]['details']['family'] is True and found[friend['id']]['details']['family'] is False
        timeline_id, day = companion['active_timeline_id'], (today + timedelta(days=6)).isoformat()
        connection.execute("INSERT INTO big_days (id, timeline_id, kind, source, status, local_date, at_time, until_time, "
                           "place, invite, details, created_at, updated_at) VALUES (?, ?, 'birthday', 'x', 'invited', ?, "
                           "'18:00', '22:00', '{}', 1, '{}', ?, ?)",
                           (identifier(), timeline_id, day, day, day))
        row = {'id': 'f', 'timeline_id': timeline_id, 'kind': 'funeral', 'local_date': day,
               'details': {'local': True, 'family': True}}
        assert big_days.invitable(connection, companion, row)
        assert not big_days.invitable(connection, companion, {**row, 'details': {'local': True, 'family': False}})


def test_obituaries_say_the_name_once_and_no_trade():
    for line in loss.bank()['obituaries']:
        assert line.count('{name}') == 1, line
        assert not re.search(r'whistle|their\} trade|quilts', line), line


def test_an_ordinary_funeral_is_at_a_parish_church_and_never_at_a_shrine(monkeypatch):
    from companion.world import catalog
    day = date(2026, 10, 20)
    monkeypatch.setattr(loss, 'customs', lambda connection, companion: loss.bank()['customs']['uk-victorian'])
    data = catalog.city('london-1895')
    picked = {loss.venue_for(None, {}, data, f's{index}', day)['name'] for index in range(60)}
    assert picked and not picked & {'Westminster Abbey', "St Paul's Cathedral"}, picked
    assert {'Westminster Abbey', "St Paul's Cathedral"} & {loss.venue_for(None, {}, data, f's{index}', day, True)['name']
                                                           for index in range(60)}
    monkeypatch.setattr(loss, 'customs', lambda connection, companion: loss.bank()['customs']['japan'])
    data = catalog.city('osaka')
    picked = {loss.venue_for(None, {}, data, f's{index}', day)['name'] for index in range(60)}
    assert not picked & {'Osaka Tenmangu', 'Sumiyoshi Taisha'}, picked
    monkeypatch.setattr(loss, 'customs', lambda connection, companion: loss.bank()['customs']['uk'])
    assert loss.venue_for(None, {}, catalog.city('london'), 's', day)['name'] == 'the crematorium chapel'


def test_the_news_says_an_illness_with_none_on_record_was_short(client, clock, monkeypatch):
    make(client)
    today = clock.now().date()
    late(client, 'dad', today, cause='illness')
    assert loss.CAUSES['illness'] == 'after a short illness' and loss.CAUSES['long illness'] == 'after a long illness'
    monkeypatch.setattr(loss, 'FIRST_TEXTS', True)
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        [news] = loss.news_due(connection, companion, clock.now())
        assert 'after a short illness' in news.reason
    assert any(', after a short illness.' in text for text in lines(client, clock))
