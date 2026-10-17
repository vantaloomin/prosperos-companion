"""Engagement and wedding (companion/life/wedding.py): the proposal, planning the wedding, the day and after."""
import re
from datetime import date, datetime, timedelta

import pytest
from conftest import send, show

from companion import consequences
from companion.characters import current
from companion.database import many, optional
from companion.life import money, outings, scrapbook, steps, wedding
from companion.providers.chat import Chunk
from companion.world import paper


def make(client, **values):
    response = client.post('/api/companion', json={'name': 'Mira Costa', 'timezone': 'UTC', 'relationship': 'romance',
                                                     'home_city': 'Baltimore', **values})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    assert client.get('/api/life/circle').status_code == 200


def set_step(client, step):
    response = client.put('/api/life/steps', json={'step': step})
    assert response.status_code == 200, response.text


def step_now(client, clock):
    with client.app.state.database.connect() as connection:
        return steps.state(connection, current(connection), clock.now(), write=False)['step']


def advance(client, clock):
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        outings.finish_due(connection, companion, clock.now())
        wedding.advance(connection, companion, clock.now())


def plan_proposal(client, clock):
    """An "engaged" ask they planned for today, the way steps.plan_next makes one."""
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        steps.insert_ask(connection, companion['active_timeline_id'], 'romance', 'engaged', 'them', 'planned',
                         clock.now().isoformat(), due_on=clock.now().date())


def proposals(client):
    with client.app.state.database.connect() as connection:
        return many(connection, 'SELECT * FROM proposals ORDER BY created_at')


def invite(client, clock, key='propose-message'):
    """The invitation a proposal due today sends, saved the way openers.py saves it."""
    from companion.life import openers
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        found = [trigger for trigger in openers.candidates(connection, companion, clock.now()) if trigger.kind == 'propose']
        if not found:
            return None, None
        trigger = found[0]
        connection.execute("INSERT INTO messages (id, timeline_id, seq, role, text, status, active, character_version_id, "
                           "memory_revision, created_at, completed_at) VALUES (?, ?, 99, 'companion', ?, 'complete', 1, ?, "
                           '0, ?, ?)', (key, companion['active_timeline_id'], trigger.template,
                                        companion['active_version_id'], clock.now().isoformat(), clock.now().isoformat()))
        return trigger, wedding.settle(connection, companion, {'id': key}, trigger, clock.now().isoformat())


def at(clock, day, hour_minute):
    hours, minutes = map(int, hour_minute.split(':'))
    target = datetime.combine(date.fromisoformat(day), datetime.min.time(), clock.now().tzinfo)
    clock.advance(target + timedelta(hours=hours, minutes=minutes) - clock.now())


def says(provider, text='Okay!'):
    provider.replies.append([Chunk(text), Chunk('', 'stop')])


def prompt(provider):
    request = provider.requests[-1]
    return request['prompt'] + ''.join(message['content'] for message in request.get('messages', ()))


def panel(client):
    response = client.get('/api/life/admin')
    assert response.status_code == 200, response.text
    return response.json()['wedding']


@pytest.fixture
def invites(monkeypatch):
    monkeypatch.setattr(wedding, 'FIRST_TEXTS', True)


def proposed(client, clock, provider):
    """Living together, they plan the evening, invite the user, and ask over dinner: the ask is open."""
    make(client)
    set_step(client, 'moving_in')
    plan_proposal(client, clock)
    advance(client, clock)
    at(clock, clock.now().date().isoformat(), '12:00')
    trigger, outing = invite(client, clock)
    assert trigger is not None and outing is not None
    at(clock, outing['local_date'], outing['at_time'])
    clock.advance(timedelta(minutes=20))
    says(provider, 'There is something I have wanted to ask you all evening...')
    send(client, 'this place is lovely', 'client-wed-1')
    return trigger, outing


def test_the_banks_have_enough_lines_and_every_culture_its_customs():
    found = wedding.bank()
    for kind in ('invite', 'engaged', 'married'):
        assert len(found[kind]) >= 100 and len(set(found[kind])) == len(found[kind]), kind
    for line in found['invite']:
        assert all(part in line for part in ('{place}', '{day}', '{time}')), line
        assert not any(word in line.lower() for word in ('marry', 'ring', 'propos')), line
    for key, rules in found['customs'].items():
        for field in ('ceremony', 'moments', 'venues', 'day', 'at', 'until', 'months', 'guests', 'budget', 'share',
                      'ring', 'attire', 'prep'):
            assert field in rules, (key, field)
        assert set(rules['months']) == set(rules['guests']) == set(rules['budget']) == set(wedding.SIZES)
        assert set(rules['attire']) == {'she', 'he', 'they'}


def test_they_plan_an_evening_out_and_ask_over_it(client, clock, provider, invites):
    trigger, outing = proposed(client, clock, provider)
    assert '{' not in trigger.template and 'marry' not in trigger.template.lower()
    assert 'marry' in trigger.reason and "don't give it away" in trigger.reason
    assert outing['activity'] in ('dinner', 'walk') and outing['place']['proposal']
    assert 'ask them' in prompt(provider) and 'marry you' in prompt(provider)
    [row] = proposals(client)
    assert row['status'] == 'asked' and row['ring'] and row['ring_cost'] > 0
    with client.app.state.database.connect() as connection:
        ask = optional(connection, "SELECT * FROM step_asks WHERE step='engaged'")
    assert ask['status'] == 'open'


def test_yes_makes_them_engaged_and_plans_the_wedding(client, clock, provider, invites):
    proposed(client, clock, provider)
    says(provider, 'You said yes!')
    send(client, 'Yes! Of course yes!', 'client-wed-2')
    assert step_now(client, clock) == 'engaged'
    assert 'just said yes to getting engaged' in prompt(provider)
    found = panel(client)
    assert found['status'] == 'planned' and found['size'] in wedding.SIZES and found['venue']['name']
    assert found['date'] > clock.now().date().isoformat()
    assert found['guest_count'] >= 2 and found['customs']
    assert found['budget_text'].startswith('$') and found['consequence_id'] is None
    # The ring came from savings: it is in this pay period's spending but leaves what is left alone.
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        home = money.household(connection, companion['active_timeline_id'], companion['version']['definition'],
                               clock.now().date())
    if home:
        assert any(item.get('for') == 'ring' and item['savings'] for item in home['purchases'])


def test_no_keeps_things_where_they_were_with_a_rough_patch(client, clock, provider, invites, monkeypatch):
    from companion.life import rough_patches
    monkeypatch.setattr(rough_patches, 'ACTIVE', True)
    monkeypatch.setattr(consequences, 'roll', lambda _seed, found: found[-1]['option'])
    proposed(client, clock, provider)
    says(provider, 'Oh.')
    send(client, "No, I'm sorry, I can't.", 'client-wed-3')
    assert step_now(client, clock) == 'moving_in'
    assert panel(client) is None
    with client.app.state.database.connect() as connection:
        patch = optional(connection, "SELECT * FROM rough_patches WHERE cause='proposal_no'")
    assert patch is not None and patch['size'] == 'big' and 'marry' in patch['shown']


def test_the_user_can_propose_and_the_engine_answers(client, clock, provider, monkeypatch):
    make(client)
    set_step(client, 'moving_in')
    monkeypatch.setattr(consequences, 'roll', lambda _seed, found: found[0]['option'])
    says(provider, 'Yes!')
    send(client, 'Will you marry me?', 'client-wed-4')
    assert step_now(client, clock) == 'engaged'
    assert panel(client)['status'] == 'planned'


def test_the_plan_can_be_changed_on_the_life_admin_panel(client, clock, provider):
    make(client)
    says(provider)
    send(client, 'hey you', 'client-wed-6')  # The wedding outing is kept on a message of the chat.
    show(client, show_odds=True)
    set_step(client, 'engaged')
    advance(client, clock)
    found = panel(client)
    assert found and found['consequence_id']
    day = (clock.now().date() + timedelta(days=200)).isoformat()
    response = client.put('/api/life/admin/wedding', json={'day': day})
    assert response.status_code == 200, response.text
    assert response.json()['wedding']['date'] == day and response.json()['wedding']['moved_by_user']
    venue = found['venue']['id']
    response = client.put('/api/life/admin/wedding', json={'venue': True})
    assert response.status_code == 200, response.text
    assert response.json()['wedding']['venue']['id'] != venue
    response = client.put('/api/life/admin/wedding', json={'size': 'big'})
    assert response.json()['wedding']['size'] == 'big'
    guest = response.json()['wedding']['guests'][0]
    response = client.put('/api/life/admin/wedding', json={'guest': guest['key'], 'invited': False})
    assert not response.json()['wedding']['guests'][0]['invited']
    assert client.put('/api/life/admin/wedding', json={'day': clock.now().date().isoformat()}).status_code == 422
    response = client.post(f"/api/life/consequences/{found['consequence_id']}/change", json={'option': 0})
    assert response.status_code == 200, response.text
    assert panel(client)['size'] == 'small'
    # The wedding outing follows the plan, and can't be called off or moved from Today.
    with client.app.state.database.connect() as connection:
        outing = optional(connection, "SELECT * FROM outings WHERE activity='wedding'")
    assert outing['local_date'] == panel(client)['date']
    assert client.post(f"/api/life/outings/{outing['id']}/cancel").status_code in (404, 405, 409)


def test_the_wedding_day_makes_them_married(client, clock, provider):
    make(client)
    says(provider)
    send(client, 'hey you', 'client-wed-7')
    set_step(client, 'engaged')
    advance(client, clock)
    found = panel(client)
    at(clock, found['date'], '10:00')
    advance(client, clock)  # The planning on the calendar comes up as it nears.
    at(clock, found['date'], found['at'])
    clock.advance(timedelta(hours=1))
    says(provider, 'We did it.')
    send(client, 'I can not believe it', 'client-wed-5')
    text = prompt(provider)
    assert 'your wedding day' in text and 'Your guests are here' in text
    at(clock, found['date'], found['until'])
    clock.advance(timedelta(minutes=10))
    where = client.get('/api/life/where').json()  # "Married today at ..." stays on the strip for the rest of the day.
    assert where['outing']['activity'] == 'wedding' and where['outing']['state'] == 'done'
    at(clock, found['date'], '23:59')
    clock.advance(timedelta(hours=2))
    advance(client, clock)
    assert step_now(client, clock) == 'married'
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        row = wedding.current(connection, companion['active_timeline_id'])
        assert row['status'] == 'done'
        page = wedding.scrapbook_page(connection, companion, found['date'], found['date'])
        data = outings.city_data(connection, companion['version']['definition'])
        week = (date.fromisoformat(found['date']) - timedelta(days=1), date.fromisoformat(found['date']) + timedelta(days=5))
        items = wedding.paper_items(connection, data, week)
        memory = optional(connection, "SELECT * FROM memories WHERE subject='Your wedding'")
    assert page['kind'] == 'wedding' and page['items']
    assert any(item['key'].endswith(':married') for item in items)
    assert memory is not None and memory['value'].startswith('You and Mira got married at ')  # Not "You married the user".
    assert paper.title(data)


def test_moving_the_step_back_calls_the_wedding_off(client, clock, provider):
    make(client)
    says(provider)
    send(client, 'hey you', 'client-wed-8')
    set_step(client, 'engaged')
    advance(client, clock)
    assert panel(client)['status'] == 'planned'
    set_step(client, 'moving_in')
    advance(client, clock)
    assert panel(client) is None or panel(client)['status'] != 'planned'
    with client.app.state.database.connect() as connection:
        outing = optional(connection, "SELECT status FROM outings WHERE activity='wedding'")
    assert outing['status'] == 'cancelled'


def test_customs_follow_the_city_and_era():
    assert wedding.culture_of(None) in wedding.bank()['customs']
    assert wedding.customs('nowhere') == wedding.bank()['customs']['modern']
    assert wedding.attire({'name': 'Ana', 'pronouns': 'she/her'}, 'us')
    assert scrapbook  # The page joins the scrapbook (companion/life/scrapbook.py).


def test_a_winter_wedding_in_a_cold_city_is_held_indoors():
    from companion.world import catalog
    data = catalog.city(catalog.resolve('Chicago', [])['city'], [])
    rules = wedding.customs(wedding.culture_of(data))
    assert wedding.cold(data, date(2027, 2, 20)) and not wedding.cold(data, date(2027, 7, 20))
    for seed in range(30):
        for size in wedding.SIZES:
            found = wedding.venue_for(data, rules, size, f'winter-{seed}', day=date(2027, 2, 20))
            assert found['kind'] not in wedding.OUTDOOR and not wedding.OUTDOOR_NAMES.search(found['name']), found['name']


def test_a_break_calls_the_wedding_off(client, clock, provider, monkeypatch):
    from companion.life import breakups
    make(client)
    says(provider)
    send(client, 'hey you', 'client-wed-9')
    set_step(client, 'engaged')
    advance(client, clock)
    assert panel(client)['status'] == 'planned'
    monkeypatch.setattr(breakups, 'holds', lambda _connection, _companion: 'break')
    advance(client, clock)
    assert panel(client) is None
    monkeypatch.setattr(breakups, 'holds', lambda _connection, _companion: None)
    advance(client, clock)  # Back together and still engaged: the wedding is planned again.
    assert panel(client)['status'] == 'planned'


def test_the_yes_does_not_read_as_agreeing_to_an_outing_and_the_day_has_its_year(client, clock, provider, invites):
    proposed(client, clock, provider)
    says(provider, 'You said yes!')
    send(client, 'Yes! Of course yes!', 'client-wed-10')
    text = prompt(provider)
    assert 'You agreed to go' not in text and 'Confirm where and when' not in text
    found = panel(client)
    day = date.fromisoformat(found['date'])
    assert f"{day:%A %B} {day.day}, {day.year} at" in text


def test_the_wedding_takes_every_block_it_runs_through(client, clock, provider):
    """Its later blocks are quiet time with the user: no errand or evening of their own during the reception."""
    from companion.characters import require_current
    from companion.database import decode
    from companion.life import admin, agenda, routine
    make(client)
    says(provider)
    send(client, 'hey you', 'client-wed-11')
    set_step(client, 'engaged')
    advance(client, clock)
    found = panel(client)
    at(clock, (date.fromisoformat(found['date']) - timedelta(days=2)).isoformat(), '10:00')
    with client.app.state.database.connect(write=True) as connection:
        companion = require_current(connection)
        agenda.extend(connection, companion, client.app.state.life.world, clock.now())
        rows = many(connection, "SELECT * FROM life_agenda WHERE subject='companion' AND local_date=? ORDER BY starts_at",
                    (found['date'],))
        day = date.fromisoformat(found['date'])
        taken = admin.Taken(connection, companion, day, 2)
        evening = [block for block in admin.free_blocks(routine.blocks(companion['version']['definition'])[0], day)
                   if found['at'] < block['start'] < found['until']]
    blocks = [(decode(row['block']), decode(row['entry']) if row['entry'] else None) for row in rows]
    during = [(block, entry) for block, entry in blocks if block['kind'] not in routine.RESTING
              and found['at'] < block['start'] < found['until']]
    assert any((entry or {}).get('activity') == 'wedding' for _block, entry in blocks)
    assert during and all(entry is None and block.get('with_user') for block, entry in during)
    assert evening and all(taken.held(day, block, by_user_only=True) for block in evening)


def test_at_the_wedding_they_wear_their_wedding_clothes(client, clock, provider):
    """In the chat's "Wearing right now" and in a picture of the wedding, not the day's everyday outfit."""
    from companion.characters import require_current
    from companion.life import agenda, wardrobe
    make(client)
    says(provider)
    send(client, 'hey you', 'client-wed-12')
    set_step(client, 'engaged')
    advance(client, clock)
    found = panel(client)
    at(clock, found['date'], found['at'])
    clock.advance(timedelta(hours=4))  # The reception, past the block the ceremony started in.
    with client.app.state.database.connect(write=True) as connection:
        companion = require_current(connection)
        agenda.extend(connection, companion, client.app.state.life.world, clock.now())
        timeline_id = companion['active_timeline_id']
        row = wedding.current(connection, timeline_id)
        lines = dict(wardrobe.context_lines(connection, timeline_id, date.fromisoformat(found['date']), clock.now()))
        hint = wardrobe.image_hint(connection, timeline_id, {'local_date': found['date'], 'activity': 'wedding'})
    worn = wedding.attire(companion['version']['definition'], row['culture'])
    assert any(f'(at your wedding): {worn}.' in line for line in lines.values())
    assert not any('Wearing right now (' in line and 'at your wedding' not in line for line in lines.values())
    assert hint == f'Wearing {worn}.'


def test_a_branch_from_the_proposal_can_still_be_answered(client, clock, provider, invites, monkeypatch):
    """Branch from here on the reply that asked: the question is still open on the branch, and no keeps things where they
    were with a rough patch."""
    from companion.life import rough_patches
    monkeypatch.setattr(rough_patches, 'ACTIVE', True)
    monkeypatch.setattr(consequences, 'roll', lambda _seed, found: found[-1]['option'])
    proposed(client, clock, provider)
    asked = client.get('/api/conversation').json()['messages'][-1]
    assert asked['role'] == 'companion'
    clock.advance(timedelta(minutes=2))
    says(provider, 'You said yes!')
    send(client, 'Yes! Of course yes!', 'client-wed-13')
    assert step_now(client, clock) == 'engaged'
    branch = client.post('/api/timelines', json={'message_id': asked['id'], 'label': 'Say no'}).json()
    assert client.post(f"/api/timelines/{branch['id']}/activate").status_code == 200
    assert step_now(client, clock) == 'moving_in'
    says(provider, 'Oh.')
    send(client, "No, I'm sorry, I can't.", 'client-wed-14')
    assert step_now(client, clock) == 'moving_in'
    with client.app.state.database.connect() as connection:
        ask = optional(connection, "SELECT * FROM step_asks WHERE timeline_id=? AND step='engaged'", (branch['id'],))
        patch = optional(connection, "SELECT * FROM rough_patches WHERE timeline_id=? AND cause='proposal_no'",
                         (branch['id'],))
        ring = optional(connection, "SELECT * FROM proposals WHERE timeline_id=? AND status='asked'", (branch['id'],))
    assert ask['status'] == 'no' and patch is not None and ring['ring_cost'] > 0


def test_they_propose_somewhere_open_in_the_evening(client, clock, provider):
    """Not a walk at six in a conservatory that closes in the afternoon."""
    from companion.characters import require_current
    make(client)
    with client.app.state.database.connect() as connection:
        companion = require_current(connection)
        data = outings.city_data(connection, companion['version']['definition'])
        for seed in range(40):
            day = date(2027, 1, 20) + timedelta(days=seed * 9)
            item = wedding.favourite(connection, companion, data, f"p{seed}", day)
            assert outings.fits(item, day, wedding.PROPOSE_AT[wedding.PROPOSE_KINDS[item['kind']]]), item['name']


def test_no_wedding_at_a_concert_or_music_hall():
    """'Hall' is a wedding word, but not in Symphony Hall or a Victorian music hall."""
    from companion.world import catalog
    for city, day in (('baltimore', date(2027, 1, 16)), ('london-1895', date(2027, 6, 12))):
        data = catalog.city(city, [])
        rules = wedding.customs(wedding.culture_of(data))
        for seed in range(60):
            found = wedding.venue_for(data, rules, 'proper', f'hall-{seed}', day=day)
            assert not re.search(r'symphony|music hall', found['name'], re.IGNORECASE), found['name']


def test_the_planning_follows_a_new_venue_and_day(client, clock, provider):
    from companion.database import decode

    def venue_task():
        with client.app.state.database.connect() as connection:
            return optional(connection, "SELECT * FROM life_admin WHERE key LIKE 'wedding:%:venue'")
    make(client)
    says(provider)
    send(client, 'hey you', 'client-wed-15')
    set_step(client, 'engaged')
    advance(client, clock)
    assert venue_task()['status'] == 'planned'
    venue = client.put('/api/life/admin/wedding', json={'venue': True}).json()['wedding']['venue']
    assert decode(venue_task()['place'])['name'] == venue['name']
    soon = (date.fromisoformat(venue_task()['local_date']) - timedelta(days=1)).isoformat()
    assert client.put('/api/life/admin/wedding', json={'day': soon}).status_code == 200
    assert venue_task()['status'] == 'removed'


def test_moving_away_keeps_the_wedding_in_their_city(client, clock, provider):
    """Long distance calls plans in person off, but not the wedding: it is in their city, and the user travels to it."""
    from companion.characters import require_current
    from companion.life import long_distance
    make(client)
    says(provider)
    send(client, 'hey you', 'client-wed-16')
    set_step(client, 'engaged')
    advance(client, clock)
    world = client.get('/api/worlds').json()['world']
    assert client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'chicago'}).status_code == 200
    for _day in range(3):
        clock.advance(timedelta(days=1))
        with client.app.state.database.connect(write=True) as connection:
            companion = require_current(connection)
            long_distance.settle_moves(connection, companion, clock.now().date(), clock.now())
        advance(client, clock)
    with client.app.state.database.connect() as connection:
        rows = many(connection, "SELECT status FROM outings WHERE activity='wedding'")
    assert [row['status'] for row in rows] == ['planned']


def test_a_church_service_is_held_in_a_church():
    """Where the customs say the church service (London 1895, New York 1925, Camelot), the venue is a church."""
    from companion.world import catalog
    for city in ('london-1895', 'new-york-1925', 'camelot'):
        data = catalog.city(city, [])
        rules = wedding.customs(wedding.culture_of(data))
        assert 'church' in rules['ceremony']
        for seed in range(40):
            found = wedding.venue_for(data, rules, wedding.SIZES[seed % 3], f'church-{seed}', day=date(2027, 6, 12))
            assert found['kind'] == 'temple', (city, found['name'])


def test_guests_at_the_wedding_are_not_shown_at_work(client, clock, provider):
    """While the wedding is under way the circle's invited guests are there, not at their jobs."""
    from companion.characters import require_current
    from companion.clock import stamp
    from companion.database import encode, identifier
    from companion.life import agenda
    make(client)
    says(provider)
    send(client, 'hey you', 'client-wed-guests')
    set_step(client, 'engaged')
    advance(client, clock)
    found = panel(client)
    at(clock, found['date'], found['at'])
    clock.advance(timedelta(hours=1))
    now = clock.now()
    with client.app.state.database.connect(write=True) as connection:
        companion = require_current(connection)
        agenda.extend(connection, companion, client.app.state.life.world, now)
        timeline_id = companion['active_timeline_id']
        invited = sorted(guest['key'].split(':', 1)[1] for guest in wedding.current(connection, timeline_id)['guests']
                         if guest['invited'] and guest['key'].startswith('circle:'))
        if not agenda.current(connection, timeline_id, invited[0], now):
            connection.execute(  # A shift their day would have put them on.
                'INSERT INTO life_agenda (id, timeline_id, subject, slot_key, starts_at, ends_at, local_date, block, '
                'entry, basis, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (identifier(), timeline_id, invited[0], 'shift', stamp(now - timedelta(minutes=30)),
                 stamp(now + timedelta(hours=2)), found['date'], encode({'label': 'bartender', 'kind': 'work'}), None,
                 'test', stamp(now)))
        during = {person['id']: person['now'] for person in agenda.circle_view(connection, timeline_id, now)}
        there = wedding.guests_there(connection, timeline_id, now)
        block = agenda.current(connection, timeline_id, invited[0], now)
    assert block  # Their own day still holds where they would have been.
    assert there == set(invited) and all(during[key] is None for key in invited)


def test_the_morning_after_the_wedding_was_yesterday(client, clock, provider):
    """The note on the wedding just over says it was yesterday once the day has turned, not "earlier today"."""
    from companion.characters import require_current
    make(client)
    says(provider)
    send(client, 'hey you', 'client-wed-after')
    set_step(client, 'engaged')
    advance(client, clock)
    found = panel(client)
    at(clock, found['date'], found['until'])
    clock.advance(timedelta(minutes=20))
    with client.app.state.database.connect() as connection:
        late = dict(outings.context_lines(connection, require_current(connection), clock.now(), set()))
    at(clock, (date.fromisoformat(found['date']) + timedelta(days=1)).isoformat(), '09:00')
    with client.app.state.database.connect() as connection:
        morning = dict(outings.context_lines(connection, require_current(connection), clock.now(), set()))
    done = [line for key, line in morning.items() if key.endswith(':done')]
    assert done and done[0].startswith('- Yesterday you and the user got married at ')
    assert [line for key, line in late.items() if key.endswith(':done')][0].startswith('- Earlier today ')
