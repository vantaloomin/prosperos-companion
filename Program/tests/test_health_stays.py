"""A hospital stay fits its cause (companion/life/health_stays.py, after #103): what a companion says about someone's
health keeps them out of their days for as long as the words suggest, with seeded lengths, until someone says they're
better."""
from datetime import date, timedelta

import pytest
from test_said_events import PEOPLE, WORKDAY, person, record_of, says, world  # noqa: F401 (fixtures)

from companion.characters import require_current
from companion.database import decode
from companion.life import agenda, composer, health_stays, said_events

DAY = date(2026, 11, 11)  # A Wednesday.


def stay_of(text):
    (_person, _area, kind, given, _sentence), = said_events.read(text, PEOPLE)
    return kind, given.get('stay')


@pytest.mark.parametrize('text, expected', [
    ('my mom is in the hospital', ('in_hospital', 'days')),
    ('Kaito ended up in the ER last night', ('in_hospital', 'overnight')),
    ('my sister got stitches', ('hurt', 'overnight')),
    ('Mara sprained her ankle', ('hurt', 'overnight')),
    ('my mom had her appendix out', ('surgery', 'days')),
    ('my mom is in the hospital with pneumonia', ('in_hospital', 'days')),
    ('my mom had hip surgery', ('surgery', 'weeks')),
    ('my mom had a heart attack', ('in_hospital', 'weeks')),
    ('my mom is in the hospital after a fall, she broke her hip', ('in_hospital', 'weeks')),
    ('Kaito broke his leg', ('hurt', 'weeks')),
    ('Kaito threw out his back', ('hurt', 'days')),
    ('my mom is in the ICU', ('in_hospital', 'critical')),
    ('my mom is in a coma', ('in_hospital', 'critical')),
    ('my mom has cancer', ('diagnosed', 'treatment')),
    ('my mom started chemo', ('diagnosed', 'treatment')),
    ('my mom has arthritis', ('diagnosed', None)),
    ('Kaito has the flu', ('ill', 'ill')),
])
def test_the_words_pick_the_stay(text, expected):
    assert stay_of(text) == expected


def test_a_few_weeks_is_two_or_three_days_in_then_weeks_at_home():
    for seed in range(40):
        found = health_stays.plan('surgery', {'stay': 'weeks'}, DAY.isoformat(), str(seed))
        hospital = (date.fromisoformat(found['hospital_until']) - DAY).days
        off = (date.fromisoformat(found['home_until']) - DAY).days
        assert 2 <= hospital <= 3 and 14 <= off <= 42


def test_lengths_are_seeded_and_each_fits_its_kind():
    assert health_stays.plan('in_hospital', {'stay': 'days'}, DAY.isoformat(), 'a') == \
        health_stays.plan('in_hospital', {'stay': 'days'}, DAY.isoformat(), 'a')
    overnight = health_stays.plan('in_hospital', {'stay': 'overnight'}, DAY.isoformat(), 'a')
    assert overnight['hospital_until'] == overnight['home_until'] == (DAY + timedelta(days=1)).isoformat()
    for seed in range(40):
        ill = health_stays.plan('ill', {'stay': 'ill'}, DAY.isoformat(), str(seed))
        assert ill['hospital_until'] == DAY.isoformat() and 2 <= (date.fromisoformat(ill['home_until']) - DAY).days <= 5
        days = health_stays.plan('in_hospital', {'stay': 'days'}, DAY.isoformat(), str(seed))
        assert 2 <= (date.fromisoformat(days['hospital_until']) - DAY).days <= 4
    # A broken wrist, or someone already home after surgery: rest at home, no hospital.
    assert health_stays.plan('hurt', {'stay': 'days'}, DAY.isoformat(), 'a')['hospital_until'] == DAY.isoformat()
    home = health_stays.plan('surgery', {'stay': 'weeks', 'home_now': True}, DAY.isoformat(), 'a')
    assert home['hospital_until'] == DAY.isoformat()
    assert health_stays.plan('diagnosed', {'stay': None}, DAY.isoformat(), 'a') == {}
    assert health_stays.plan('in_hospital', {'stay': 'critical'}, DAY.isoformat(), 'a') == {'stay': 'critical'}


def test_where_each_day_of_a_stay_has_them():
    health = {'what': 'in_hospital', 'since': DAY.isoformat(), 'stay': 'days',
              'hospital_until': (DAY + timedelta(days=2)).isoformat(), 'home_until': (DAY + timedelta(days=5)).isoformat()}
    assert health_stays.on(health, DAY - timedelta(days=1)) is None
    assert health_stays.on(health, DAY)['label'] == 'In the hospital'
    assert health_stays.on(health, DAY + timedelta(days=2))['label'] == 'Home, resting'
    assert health_stays.on(health, DAY + timedelta(days=5)) is None
    critical = {'since': DAY.isoformat(), 'stay': 'critical'}
    assert health_stays.on(critical, DAY + timedelta(days=400))['label'] == 'In the hospital'
    treatment = {'since': DAY.isoformat(), 'stay': 'treatment'}
    week = [health_stays.on(treatment, DAY + timedelta(days=offset), 'p') for offset in range(5, 12)]  # Mon to Sun.
    assert sum(bool(day) for day in week) == 2 and not week[5] and not week[6]


def test_the_blocks_a_stay_takes():
    work = {'kind': 'work', 'label': 'Work', 'start': '09:00'}
    sleep = {'kind': 'sleep', 'label': 'Asleep', 'start': '23:00'}
    evening = {'kind': 'leisure', 'label': 'Evening', 'start': '18:00'}
    hospital, home, treatment = ({'where': where, 'label': label} for where, label in (
        ('hospital', 'In the hospital'), ('home', 'Home, recovering'), ('treatment', 'In treatment')))
    assert health_stays.apply(work, hospital) | {} == {**work, 'kind': 'rest', 'label': 'In the hospital',
                                                      'sick_day': True, 'stay': 'hospital'}
    assert health_stays.apply(sleep, hospital)['label'] == 'In the hospital'
    assert health_stays.apply(sleep, home) == sleep
    assert health_stays.apply(evening, home)['label'] == 'Home, recovering'
    assert health_stays.apply(evening, treatment) == evening
    assert health_stays.apply(work, treatment)['label'] == 'In treatment'
    entry = composer.compose({'block': health_stays.apply(evening, hospital), 'local_date': DAY.isoformat()},
                             {'name': 'Mara'}, None, 'seed-2')
    assert entry is None or 'hospital' in entry['summary']


def now_of(client, person_id):
    with client.app.state.database.connect(write=True) as connection:
        companion = require_current(connection)
        now = client.app.state.database.clock.now()
        agenda.extend(connection, companion, client.app.state.life.world, now)
        rows = connection.execute('SELECT local_date, block FROM life_agenda WHERE timeline_id=? AND subject=? AND '
                                  'ends_at>? ORDER BY starts_at', (companion['active_timeline_id'], person_id,
                                                                   now.isoformat())).fetchall()
    return [(row['local_date'], decode(row['block'])) for row in rows]


def test_a_hospital_stay_said_in_chat_changes_their_days_until_they_are_out(world):  # noqa: F811
    sister = person(world, 'sister')
    now_of(world, sister['id'])
    says(world, 'my sister is in the hospital', 'client-stay-01')
    health = record_of(world, sister['id'])[1]['health']
    assert health['stay'] == 'days'
    days = now_of(world, sister['id'])
    labels = {block['label'] for local_date, block in days if local_date < health['hospital_until']}
    assert labels == {'In the hospital'}
    assert all(block.get('stay') != 'hospital' for local_date, block in days if local_date >= health['hospital_until'])
    # Right now, in a block or between two, on Their people and in the companion's context.
    them = next(item for item in world.get('/api/life/circle').json() if item['id'] == sister['id'])
    assert them['now']['label'] == 'In the hospital' and them['now']['stay'] == 'hospital'
    says(world, 'good news, my sister got out of the hospital', 'client-stay-02')
    assert not any(block.get('stay') for _day, block in now_of(world, sister['id']))
