"""The companion's wardrobe (companion/life/wardrobe.py)."""
from datetime import date, timedelta

import pytest
from conftest import reconcile

from companion.database import decode
from companion.images import content, prompts
from companion.life import composer, money, wardrobe
from companion.world.source import CatalogWorld

DAYS = [{'key': 'day', 'label': 'Day', 'kind': 'leisure', 'start': '09:00', 'end': '17:00'},
        {'key': 'chores', 'label': 'Chores', 'kind': 'errand', 'start': '18:00', 'end': '20:00'},
        {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]
KIM = {'name': 'Kim', 'identity': 'She is a registered nurse who lives in Fells Point.',
       'personality': 'A cozy homebody; she loves knitting.', 'location': 'Fells Point, Baltimore',
       'appearance': 'Curly red hair. She is never without her battered leather jacket.'}
BALTIMORE = CatalogWorld().find('baltimore')


def with_career(career: str, **extra) -> dict:
    return {'name': 'Sam', 'identity': 'She lives in Baltimore.', 'location': 'Baltimore',
            'money': {'career': career, **extra.pop('money', {})}, **extra}


def views(items: list[dict]) -> list[dict]:
    """Assembled pieces as items_on returns them."""
    return [{**item, 'id': str(index), 'description': '', 'occasions': item['details']['occasions'],
             'favorite': item['details']['signature'], 'slot': item['details'].get('slot')}
            for index, item in enumerate(items)]


@pytest.fixture
def baltimore(client, monkeypatch):
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(composer, 'PLAN_SHARE', 0)
    monkeypatch.setattr(composer, 'THREAD_SHARE', 0)
    response = client.post('/api/companion', json={**KIM, 'timezone': 'America/New_York', 'schedule': DAYS})
    assert response.status_code == 200, response.text
    return response.json()


def connect(client, write=True):
    return client.app.state.database.connect(write=write)


def timeline(client) -> str:
    with connect(client, False) as connection:
        return connection.execute('SELECT active_timeline_id FROM companions').fetchone()[0]


def test_assembly_is_deterministic():
    first = wardrobe.assemble('wardrobe:t1', KIM, BALTIMORE)
    assert wardrobe.assemble('wardrobe:t1', KIM, BALTIMORE) == first
    assert any(wardrobe.assemble(f'wardrobe:t{n}', KIM, BALTIMORE)[1] != first[1] for n in range(2, 6))
    assert {item['category'] for item in first[1]} <= set(wardrobe.CATEGORIES)
    assert len({item['name'] for item in first[1]}) == len(first[1])


def test_pay_spending_and_love_of_clothes_set_the_size():
    def size(definition):
        return sum(len(wardrobe.assemble(f'wardrobe:{n}', definition, BALTIMORE)[1]) for n in range(5))
    barista, banker = size(with_career('barista')), size(with_career('finance-banker'))
    assert barista < banker
    careful = size(with_career('registered-nurse', money={'style': 'careful'}))
    spender = size(with_career('registered-nurse', money={'style': 'spender'}))
    assert careful < spender
    fashionable = size(with_career('registered-nurse', personality='Stylish and trendy; shopping is her hobby.'))
    assert fashionable > size(with_career('registered-nurse'))
    poor = wardrobe.assemble('wardrobe:q', with_career('barista'), BALTIMORE)[0]
    rich = wardrobe.assemble('wardrobe:q', with_career('finance-banker'), BALTIMORE)[0]
    assert poor['tier'] == 0 and rich['tier'] == 3


def test_the_job_sets_what_they_wear_to_work():
    found, items = wardrobe.assemble('wardrobe:k', KIM, BALTIMORE)
    assert found['code'] == 'scrubs' and found['career'] == 'Registered nurse'
    work = wardrobe.phrase(wardrobe.outfit(views(items), 'work', 'w', {'high_f': 75}, found['code']))
    assert 'scrubs' in work and 'nursing clogs' in work
    chef_found, chef = wardrobe.assemble('wardrobe:k', with_career('line-cook'), BALTIMORE)
    assert 'chef jacket' in wardrobe.phrase(wardrobe.outfit(views(chef), 'work', 'w', None, chef_found['code']))
    suited_found, suited = wardrobe.assemble('wardrobe:k', with_career('financial-analyst'), BALTIMORE)
    assert suited_found['code'] == 'business' and any(item['category'] == 'suit' for item in suited)


def test_personality_picks_the_style_and_appearance_adds_a_favourite():
    edgy = wardrobe.assemble('wardrobe:s', with_career('barista', personality='Punk, rebellious and tattooed.'),
                             BALTIMORE)[0]
    assert edgy['styles'][0] == 'edgy'
    sporty = wardrobe.assemble('wardrobe:s', with_career('barista', interests=['running', 'yoga', 'hiking']),
                               BALTIMORE)[0]
    assert sporty['styles'][0] == 'sporty'
    items = wardrobe.assemble('wardrobe:s', KIM, BALTIMORE)[1]
    jacket = next(item for item in items if item['details']['signature'])
    assert jacket['name'] == 'a battered leather jacket' and jacket['category'] == 'layer'


def test_presentation_and_era_decide_what_exists():
    him = wardrobe.assemble('wardrobe:p', with_career('teacher', identity='He teaches history. His students like him.'),
                            BALTIMORE)
    assert him[0]['who'] == 'm' and not any(item['category'] == 'dress' for item in him[1])
    camelot = CatalogWorld().find('camelot')
    for n in range(10):
        found, items = wardrobe.assemble(f'wardrobe:{n}', {'name': 'Gwen', 'identity': 'She weaves.',
                                                           'location': 'Camelot'}, camelot)
        names = ' '.join(item['name'] for item in items)
        assert found['era'] != 'modern' and 'sneakers' not in names and 'hoodie' not in names


def test_outfits_follow_the_moment_and_the_weather():
    found, items = wardrobe.assemble('wardrobe:o', KIM, BALTIMORE)
    owned = views(items)
    cold = wardrobe.outfit(owned, 'casual', 'seed', {'high_f': 35}, found['code'])
    assert cold == wardrobe.outfit(owned, 'casual', 'seed', {'high_f': 35}, found['code'])
    assert cold[0]['category'] == 'outerwear'
    assert not any(item['category'] == 'outerwear' for item in wardrobe.outfit(owned, 'casual', 'seed', {'high_f': 80}))
    assert [item['category'] for item in wardrobe.outfit(owned, 'sleep', 'seed')] == ['sleep']
    assert any(item['category'] == 'lounge' for item in wardrobe.outfit(owned, 'home', 'seed'))
    active = wardrobe.outfit(owned, 'active', 'seed')
    assert [item['category'] for item in active][:2] == ['active', 'active']
    assert wardrobe.occasion_for('dinner', 'social') == 'out'
    assert wardrobe.occasion_for('steady-shift', 'work') == 'work'
    assert wardrobe.occasion_for('reading', 'leisure') == 'home'
    assert wardrobe.occasion_for(None, 'sleep') == 'sleep'


def test_every_outfit_is_safe_for_any_image_backend():
    """Clothing words never trip the NSFW check, which would send a picture to the local backend only."""
    for n in range(25):
        for definition in (KIM, with_career('bartender', personality='Edgy and stylish.'),
                           with_career('lifeguard', identity='He guards the pool.')):
            found, items = wardrobe.assemble(f'wardrobe:{n}', definition, BALTIMORE)
            for occasion in wardrobe.OCCASION_WORDS:
                text = wardrobe.phrase(wardrobe.outfit(views(items), occasion, f'{n}', {'high_f': 40, 'rain': True},
                                                       found['code']))
                assert text and content.classify({'prompt': f'Wearing {text}.'}).tier == content.SAFE, text


def test_reading_the_wardrobe_assembles_it_once(client, baltimore):
    first = client.get('/api/life/wardrobe').json()
    assert first['profile']['work'] == 'scrubs' and first['profile']['count'] == len(first['items'])
    assert any(item['favorite'] and item['name'] == 'a battered leather jacket' for item in first['items'])
    again = client.get('/api/life/wardrobe').json()
    assert [item['id'] for item in again['items']] == [item['id'] for item in first['items']]


def test_changes_come_slowly_and_the_same_in_steps_or_at_once(client, baltimore, clock):
    client.get('/api/life/wardrobe')
    tid = timeline(client)
    end = date(2027, 6, 1)
    definition = {**KIM, 'timezone': 'America/New_York'}
    with connect(client) as connection:
        connection.execute("UPDATE wardrobe_state SET seed='steady-wardrobe' WHERE timeline_id=?", (tid,))
        for step in range(1, 235, 9):
            wardrobe.evolve(connection, tid, definition, date(2026, 10, 5) + timedelta(days=step), clock.now())
        wardrobe.evolve(connection, tid, definition, end, clock.now())
        stepped = [(row['local_date'], row['kind'], row['text']) for row in connection.execute(
            'SELECT * FROM wardrobe_log WHERE timeline_id=? ORDER BY local_date', (tid,)).fetchall()]
        connection.execute("DELETE FROM wardrobe_items WHERE origin='change'")
        connection.execute('UPDATE wardrobe_items SET until=NULL')
        connection.execute('DELETE FROM wardrobe_log')
        connection.execute('UPDATE wardrobe_state SET next_period=1')
        wardrobe.evolve(connection, tid, definition, end, clock.now())
        once = [(row['local_date'], row['kind'], row['text']) for row in connection.execute(
            'SELECT * FROM wardrobe_log WHERE timeline_id=? ORDER BY local_date', (tid,)).fetchall()]
    assert stepped == once
    assert 3 <= len(once) <= (end - date(2026, 10, 5)).days // wardrobe.PERIOD_DAYS + 1


def test_new_clothes_count_as_spending_and_are_told_once(client, baltimore, clock, monkeypatch):
    monkeypatch.setattr(wardrobe, 'WEAVE', True)
    client.get('/api/life/home')
    client.get('/api/life/wardrobe')
    tid = timeline(client)
    with connect(client) as connection:
        connection.execute("INSERT INTO wardrobe_log (id, timeline_id, period, local_date, kind, item_id, text, spend, "
                           "created_at) VALUES ('w1', ?, 99, '2026-10-06', 'bought', NULL, "
                           "'bought a mustard raincoat', '$$', '2026-10-05')", (tid,))
        bought = money.household(connection, tid, KIM, date(2026, 10, 6))['purchases']
    assert {'date': '2026-10-06', 'kind': 'bought', 'text': 'bought a mustard raincoat', 'spend': '$$',
            'for': 'clothes'} in bought
    lines = dict(money.context_lines(KIM, '2026-10-06', {'costs': {'rent': None}, 'purchases': bought}))
    assert any(line.endswith('spent money on clothes: you bought a mustard raincoat.') for line in lines.values())
    reconcile(client)
    with connect(client, False) as connection:
        told = [decode(row[0]) for row in connection.execute(
            "SELECT entry FROM life_agenda WHERE subject='companion' AND json_extract(entry, '$.wardrobe.change')='w1'")]
    assert len(told) == 1 and told[0]['summary'].endswith('Kim bought a mustard raincoat.')


def test_edits_show_in_context_and_forget_changes_ahead(client, baltimore, clock):
    view = client.get('/api/life/wardrobe').json()
    tid = timeline(client)
    added = client.post('/api/life/wardrobe/items', json={'category': 'outerwear', 'name': 'a yellow vintage raincoat',
                                                          'favorite': True})
    assert added.status_code == 200, added.text
    coat = next(item for item in added.json()['items'] if item['name'] == 'a yellow vintage raincoat')
    assert coat['origin'] == 'user' and coat['favorite']
    assert client.post('/api/life/wardrobe/items', json={'category': 'cape', 'name': 'x'}).status_code == 422
    system = client.get('/api/context/preview').json()['system']
    assert '## Your clothes' in system and 'a yellow vintage raincoat' in system and 'Your style is mostly' in system
    with connect(client) as connection:
        wardrobe.evolve(connection, tid, KIM, date(2027, 3, 1), clock.now())
    piece = view['items'][-1]
    renamed = client.patch(f"/api/life/wardrobe/items/{piece['id']}", json={'name': 'a moth-eaten jumper'}).json()
    assert any(item['name'] == 'a moth-eaten jumper' for item in renamed['items'])
    with connect(client, False) as connection:
        assert connection.execute("SELECT COUNT(*) FROM wardrobe_log WHERE local_date>'2026-10-05'").fetchone()[0] == 0
    removed = client.post(f"/api/life/wardrobe/items/{coat['id']}/remove").json()
    assert coat['id'] in [item['id'] for item in removed['removed']]
    restored = client.post(f"/api/life/wardrobe/items/{coat['id']}/restore").json()
    assert coat['id'] in [item['id'] for item in restored['items']]


def test_pictures_show_what_they_are_wearing(client, baltimore):
    client.get('/api/life/wardrobe')
    tid = timeline(client)
    moment = {'activity': 'walk', 'block_kind': 'leisure', 'local_date': '2026-10-05', 'weather': {'high_f': 40}}
    with connect(client, False) as connection:
        hint = wardrobe.image_hint(connection, tid, moment)
        again = prompts.setting(connection, tid, {'summary': 'Kim went for a walk.', 'place': 'Patterson Park',
                                                  'moment': moment})
        indoors = wardrobe.image_hint(connection, tid, {**moment, 'activity': 'dinner'})
        undated = wardrobe.image_hint(connection, tid, {'activity': 'walk'})
    assert hint.startswith('Wearing ') and hint in again
    assert ' over ' in hint  # a coat for a cold walk
    assert indoors.startswith('Wearing ') and undated == ''


def test_a_fork_keeps_the_wardrobe_as_it_was(client, baltimore, clock):
    client.get('/api/life/wardrobe')
    tid = timeline(client)
    with connect(client) as connection:
        wardrobe.evolve(connection, tid, KIM, date(2027, 1, 1), clock.now())
        connection.execute("INSERT INTO timelines (id, companion_id, status, created_at) "
                           "SELECT 'fork', companion_id, 'frozen', created_at FROM timelines WHERE id=?", (tid,))
        wardrobe.copy(connection, tid, 'fork', '2026-11-15T12:00:00Z', {})
        parent = {row[0] for row in connection.execute(
            "SELECT name FROM wardrobe_items WHERE timeline_id=? AND since<='2026-11-15'", (tid,))}
        forked = {row[0] for row in connection.execute("SELECT name FROM wardrobe_items WHERE timeline_id='fork'")}
        logged = connection.execute("SELECT MAX(local_date) FROM wardrobe_log WHERE timeline_id='fork'").fetchone()[0]
    assert forked == parent
    assert logged is None or logged <= '2026-11-15'
