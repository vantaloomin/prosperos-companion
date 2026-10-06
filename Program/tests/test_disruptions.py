"""Days that do not go to plan: seeded shifts rolled with Prospero's Study's dice."""
import pytest
from conftest import set_life

from companion.characters import require_current
from companion.clock import parse
from companion.database import decode
from companion.life import agenda, body, chance, disruptions
from companion.memory import context

DAY = [{'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '08:00'},
       {'key': 'work', 'label': 'Office', 'kind': 'work', 'start': '08:00', 'end': '17:00'},
       {'key': 'evening', 'label': 'Evening out', 'kind': 'social', 'start': '17:00', 'end': '23:00'}]


@pytest.fixture
def mira(client, monkeypatch):
    monkeypatch.setattr(disruptions, 'ACTIVE', True)
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'schedule': DAY})
    assert response.status_code == 200, response.text
    return response.json()


def only(monkeypatch, kind, key):
    """Make every `kind` slot roll `key`."""
    row = next(row for row in disruptions.TABLES[kind] if row['id'] == key)
    monkeypatch.setitem(disruptions.TABLES, kind, [{**row, 'low': 1, 'high': 1}])


def build(client):
    with client.app.state.database.connect() as connection:
        companion = require_current(connection)
        agenda.extend(connection, companion, client.app.state.life.world, client.app.state.database.clock.now())
        rows = connection.execute("SELECT * FROM life_agenda WHERE subject='companion' ORDER BY starts_at").fetchall()
    return [{**dict(row), 'block': decode(row['block']), 'entry': decode(row['entry']) if row['entry'] else None}
            for row in rows]


def test_the_dice_are_studys_and_repeat():
    first, again = chance.Draws('seed'), chance.Draws('seed')
    rolls = [first.die(100, 'shift', 'test') for _ in range(50)]
    assert rolls == [again.die(100, 'shift', 'test') for _ in range(50)]
    assert all(1 <= roll <= 100 for roll in rolls) and len(set(rolls)) > 20
    assert first.log[0] == {'stream': 'shift', 'counter': 1, 'purpose': 'test', 'sides': 100, 'result': rolls[0]}
    tables = {'top': disruptions.table(('none', 1, None, ''), ('go', 1, 'next', 'went')),
              'next': disruptions.reasons('because')}
    chains = [chance.resolve(tables, 'top', chance.Draws(str(seed)), 's') for seed in range(40)]
    assert [] in chains and [row['id'] for row in next(chain for chain in chains if chain)] == ['go', 'reason-0']


def test_most_slots_go_to_plan_and_each_roll_is_fixed():
    block = {'kind': 'work', 'label': 'Office'}
    shifts = [disruptions.roll(f'slot:{index}', block) for index in range(2000)]
    share = sum(1 for shift in shifts if shift) / len(shifts)
    assert 0.08 < share < 0.25
    assert shifts[:50] == [disruptions.roll(f'slot:{index}', block) for index in range(50)]
    late = next(shift for shift in shifts if shift and shift['key'] == 'late')
    assert 10 <= late['minutes'] <= 45 and late['text'].startswith(f"ran {late['minutes']} minutes late (")
    assert disruptions.roll('slot:1', {'kind': 'sleep', 'label': 'Asleep'}) is None
    assert disruptions.roll('slot:1', {**block, 'holiday': 'Labor Day'}) is None


def test_a_friend_drops_by_only_when_one_is_free(monkeypatch):
    only(monkeypatch, 'leisure', 'drop_by')
    block = {'kind': 'leisure', 'label': 'Evening'}
    assert disruptions.roll('slot', block, []) is None
    shift = disruptions.roll('slot', block, [{'id': 'p1', 'name': 'Ana'}])
    assert shift['friend']['name'] == 'Ana' and shift['text'] == 'had Ana drop by unannounced'
    turned = disruptions.shifted(block, shift)
    assert turned['kind'] == 'social' and turned['label'] == 'Ana dropped by' and turned['planned'] == 'Evening'


def test_running_late_starts_later_and_the_night_runs_on(client, mira, monkeypatch):
    only(monkeypatch, 'work', 'late')
    rows = build(client)
    nights = {row['ends_at']: row for row in rows if row['block']['key'] == 'night'}
    work = next(row for row in rows if row['block']['key'] == 'work' and row['starts_at'] in nights)
    night = nights[work['starts_at']]
    late = (parse(work['starts_at']) - parse(work['starts_at']).replace(hour=8, minute=0)).seconds // 60
    assert 10 <= late <= 45 and late == work['block']['shift']['minutes']
    assert parse(work['ends_at']).hour == 17
    assert night['block']['kind'] == 'sleep'
    if work['entry']:
        assert work['entry']['summary'].startswith(f'Mira ran {late} minutes late (')


def test_staying_late_pushes_the_evening(client, mira, monkeypatch):
    only(monkeypatch, 'work', 'over')
    rows = build(client)
    work = next(row for row in rows if row['block']['key'] == 'work')
    evening = next(row for row in rows if row['block']['key'] == 'evening' and row['local_date'] == work['local_date'])
    assert parse(work['ends_at']) > parse(work['ends_at']).replace(hour=17, minute=0)
    assert evening['starts_at'] == work['ends_at'] and parse(evening['ends_at']).hour == 23


def test_cancelled_plans_become_a_night_in_and_the_companion_knows(client, mira, monkeypatch, clock):
    only(monkeypatch, 'social', 'cancelled')
    rows = build(client)
    evening = next(row for row in rows if row['block']['key'] == 'evening')
    assert evening['block']['kind'] == 'leisure' and evening['block']['label'] == 'Quiet night in'
    assert evening['block']['planned'] == 'Evening out'
    clock.instant = parse(evening['starts_at'])
    with client.app.state.database.connect() as connection:
        lines = disruptions.context_lines(connection, evening['timeline_id'], agenda.COMPANION, evening['local_date'],
                                          clock.now())
    # Earlier slots today (work) still roll their own seeded shifts, so the evening's line is one of them.
    assert (evening['id'], f"- Today, evening out: you {evening['block']['shift']['text']}.") in lines
    assert 'day_shifts' in context.HEADINGS


def test_turning_it_off_keeps_new_days_as_planned(client, mira, monkeypatch):
    only(monkeypatch, 'work', 'late')
    set_life(client, day_shifts=False)
    assert all('shift' not in row['block'] for row in build(client))
    assert client.get('/api/life/settings').json()['day_shifts'] is False
