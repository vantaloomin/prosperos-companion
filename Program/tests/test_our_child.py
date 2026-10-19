"""Our child (companion/life/our_child.py): the pair's own child growing up in real time, their sheet, milestones and
the family life that shapes the companion's days, the second child as its own step, and the child grown at 18."""
import re
import string
from datetime import date, timedelta

import pytest
from conftest import intimate, reconcile, send, set_life
from test_expecting import likeliest, stage, started, to  # noqa: F401 - likeliest is a fixture
from test_parenthood import family, planned, set_family
from test_steps import prompt, says

from companion import group_guests
from companion.characters import current
from companion.life import families, our_child, work
from companion.world import intimacy

FORBIDDEN = re.compile(r'\b(?:kiss\w*|naked|nude|bath\w*|bed|body|skin|lips|touch\w*|cuddl\w*|snuggl\w*|undress\w*|'
                       r'shower\w*|sexy|hot|crush\w*|dating|flirt\w*|puberty)\b', re.IGNORECASE)
# The engine lands on the likeliest option every time (tests/test_expecting.py).
pytestmark = pytest.mark.usefixtures('likeliest')
TOKENS = {'child', 'they', 'them', 'their', 'theyre', 'are', 'were', 'They', 'Their', 'who', 'holiday'}


def connect(client):
    return client.app.state.database.connect()


def born(client, clock, monkeypatch, **values):
    """A baby born to the pair and home: the journey, and the clock on the day of the birth."""
    row = started(client, monkeypatch, identity='She is a 31-year-old nurse.', **values)
    to(client, clock, stage(row, 'born')['on'])
    with connect(client) as connection:
        companion = current(connection)
        [child] = our_child.children(connection, companion['active_timeline_id'])
    return row, child


def ours(client, **values):
    response = client.put('/api/life/steps/ours', json=values) if values else client.get('/api/life/steps/ours')
    assert response.status_code == 200, response.text
    return response.json()


def aged(client, child: dict, days: int, home: bool = True) -> None:
    """Makes the child `days` old today (and home since birth)."""
    with connect(client) as connection:
        today = our_child.steps.local_today(current(connection), client.app.state.database.clock.now())
        born_on = (today - timedelta(days=days)).isoformat()
        connection.execute('UPDATE circle_children SET born_on=? WHERE id=?', (born_on, child['id']))
        if home:
            connection.execute('UPDATE family_journeys SET arrived_on=? WHERE id=?', (born_on, child['storyline_id']))
        connection.commit()


def test_the_bank_has_a_hundred_lines_a_category_fit_for_children():
    bank = our_child.bank()
    categories = [key for key in bank if key not in ('_about', 'tags')]
    assert {f'{kind}_{band}' for kind in ('likes', 'quirks') for band, _low, _high in our_child.BANDS} <= set(categories)
    texts = set()
    for key in categories:
        assert len(bank[key]) >= 100, key
        for line in bank[key]:
            assert not FORBIDDEN.search(line['text']), line['text']
            assert {field for _literal, field, _spec, _conversion in string.Formatter().parse(line['text'])
                    if field} <= TOKENS, line['text']
            texts.add(line['text'])
    assert set(bank['tags']['older']) | set(bank['tags']['modern']) <= texts
    assert all(0 <= line['ages'][0] <= line['ages'][1] <= 17 for line in bank['holiday_part'])
    # The companion reads these as notes about their own family: "you", never "I" or "me".
    assert not [line['text'] for key in ('grandparents', 'aunts_uncles', 'holiday_part') for line in bank[key]
                if re.search(r"\b(?:I|I'm|me|my)\b", line['text'])]


def test_a_child_born_is_in_their_life_with_a_sheet_and_a_routine(client, provider, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    says(provider)
    send(client, 'how is everyone?', 'client-ours-1')
    text = prompt(provider)
    assert f"- {child['name']} (your daughter, a newborn): yours and the user's." in text or \
        f"- {child['name']} (your son, a newborn): yours and the user's." in text
    assert f"{child['name'].split()[0]} is " in text and 'Lately ' not in text  # A newborn: only a temperament yet.
    assert 'bedtime is around 7 in the evening' in text
    view = ours(client)
    assert view['shown'] and view['children'][0]['name'] == child['name'] and view['care'] in our_child.CARE
    assert view['children'][0]['temperament'] and view['children'][0]['likes'] is None
    aged(client, child, 400)
    assert ours(client)['children'][0]['likes']
    today = client.get('/api/today').json()
    assert today['family'][0]['name'] == child['name']


def test_milestones_come_in_real_time_and_stay_in_the_scrapbook(client, provider, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    with connect(client) as connection:
        companion = current(connection)
        planned = our_child.milestones(connection, companion, child)
    smile = next(item for item in planned if item['key'] == 'smile')
    assert [item['key'] for item in planned][:2] == ['smile', 'laugh'] or planned[0]['key'] == 'smile'
    to(client, clock, smile['on'])
    says(provider)
    send(client, 'good morning', 'client-ours-2')
    assert f"{child['name'].split()[0]} smiled for the first time today." in prompt(provider)
    assert ours(client)['children'][0]['latest']['label'] == 'First smile'
    with connect(client) as connection:
        items = our_child.scrapbook_items(connection, current(connection), date(2000, 1, 1), date(2100, 1, 1))
    assert any(item['text'].endswith('first smile') for item in items)


def test_who_stays_home_shapes_their_workdays_and_money(client, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    aged(client, child, 200)
    ours(client, care='them_home')
    with connect(client) as connection:
        companion = current(connection)
        today = our_child.steps.local_today(companion, clock.now())
        off = our_child.days_off(connection, companion, today, today + timedelta(days=13))
        assert set(off.values()) <= {our_child.HOME_DAY, our_child.SICK_DAY}
        assert len(off) >= len([day for day in range(14) if (today + timedelta(days=day)).weekday() in
                                work.workdays(companion['version']['definition'])]) - 1
        assert our_child.pay(connection, companion['active_timeline_id'], today) == our_child.PAY['them_home']
    ours(client, care='both_work')
    with connect(client) as connection:
        companion = current(connection)
        bought = our_child.purchases(connection, companion['active_timeline_id'], today, today + timedelta(days=40))
        assert any(item['for'] == 'childcare' for item in bought)
        assert our_child.pay(connection, companion['active_timeline_id'], today) == 1.0
    assert ours(client, care='auto')['care_how'] == 'seeded'


def test_family_life_sets_how_hard_the_nights_are(client, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    aged(client, child, 20)
    with connect(client) as connection:
        timeline_id = current(connection)['active_timeline_id']
        today = our_child.steps.local_today(current(connection), clock.now())
        nights = [today + timedelta(days=offset) for offset in range(60)]
    set_life(client, family_life=3)
    with connect(client) as connection:
        assert sum(bool(our_child.broken_night(connection, timeline_id, day)) for day in nights) > 10
    set_life(client, family_life=0)
    with connect(client) as connection:
        assert not any(our_child.broken_night(connection, timeline_id, day) for day in nights)
        assert not any(our_child.sick_on(connection, child, day) for day in nights)


def test_the_adult_side_and_the_family_never_share_a_reply(client, provider, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    says(provider)
    send(client, 'how was the day?', 'client-ours-3')
    assert child['name'] in prompt(provider) and intimacy.SETTING not in prompt(provider)
    intimate(client)
    says(provider)
    send(client, 'come here you', 'client-ours-4')
    assert child['name'] not in prompt(provider)
    with connect(client) as connection:
        assert families.pictured(connection, current(connection)['active_timeline_id'], [f"A day out with {child['name']}"])


def test_a_family_day_out_is_an_outing_with_no_photo(client, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    send(client, 'hi', 'client-ours-5')
    aged(client, child, 500)
    reconcile(client)
    with connect(client) as connection:
        companion = current(connection)
        found = our_child.family_outings(connection, companion)
    if found:  # A city with a park or a museum open on the day.
        place = found[0]['place']
        assert place['no_photo'] and place['family'] == [child['name'].split()[0]]
        assert our_child.doing(found[0]).startswith(f"took {child['name'].split()[0]} to ")


def test_another_child_comes_as_its_own_step(client, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    assert family(client)['can_decide_another'] is False  # Not a year and a half yet.
    aged(client, child, 600)
    assert family(client)['can_decide_another'] is True
    set_family(client, another=True)
    reconcile(client)
    with connect(client) as connection:
        companion = current(connection)
        second = our_child.steps.local_today(companion, clock.now())
        journey = connection.execute("SELECT * FROM family_journeys WHERE timeline_id=? AND status NOT IN ('home', "
                                     "'called_off')", (companion['active_timeline_id'],)).fetchone()
    assert journey and journey['started_on'] == second.isoformat()
    assert family(client)['another_on'] == second.isoformat()


def test_at_eighteen_the_child_is_a_grown_person_in_their_circle(client, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    aged(client, child, 18 * 366)
    reconcile(client)
    with connect(client) as connection:
        companion = current(connection)
        person = connection.execute("SELECT * FROM circle_people WHERE json_extract(details, '$.our_child')=?",
                                    (child['id'],)).fetchone()
        assert person and person['role'] in ('daughter', 'son') and person['name'] == child['name'].split()[0]
        assert our_child.context_lines(connection, companion, clock.now()) == []
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    with connect(client) as connection:
        assert all(row['id'] != person['id'] for row in group_guests.circle_people(connection, current(connection)))


def test_a_year_and_a_half_on_they_bring_up_another_child(client, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    aged(client, child, 600)
    reconcile(client)
    asks = [ask for ask in planned(client) if ask['step'] == 'sibling']
    assert asks and asks[0]['side'] == 'them'
    with connect(client) as connection:
        assert 'a brother or sister for' in our_child.steps.reason_for(connection, current(connection), 'sibling')


def test_the_user_can_bring_up_another_child(client, provider, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    aged(client, child, 600)
    says(provider)
    send(client, 'should we have another baby?', 'client-ours-6')
    with connect(client) as connection:
        asked = connection.execute("SELECT * FROM step_asks WHERE step='sibling' AND side='you'").fetchone()
    assert asked and asked['status'] in ('yes', 'not_yet', 'no')
    if asked['status'] == 'yes':
        assert family(client)['another_on']
