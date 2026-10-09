"""Small world: companions run into each other where their own days take them (companion/life/encounters.py)."""
from datetime import timedelta

import pytest
from test_social_circle import WORKDAY, make

from companion.characters import by_id, insert_version
from companion.clock import parse
from companion.database import decode, identifier
from companion.life import agenda, body, encounters, openers
from companion.models import CharacterDefinition
from companion.world.source import CatalogWorld


@pytest.fixture(autouse=True)
def steady(monkeypatch):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)


@pytest.fixture
def fellows(monkeypatch):
    """Townsfolk meetings on, strangers off, and another companion there is always talked to."""
    monkeypatch.setattr(encounters, 'ACTIVE', True)
    monkeypatch.setattr(encounters, 'CHANCE', 0)
    monkeypatch.setattr(encounters, 'FELLOW_CHANCE', 1)


@pytest.fixture
def one_haunt(monkeypatch):
    """Everyone in town goes to the first place that fits, so two companions' evenings out overlap."""
    original = CatalogWorld.places

    def first(self, *args, **kwargs):
        return original(self, *args, **kwargs)[:1]

    monkeypatch.setattr(CatalogWorld, 'places', first)


def neighbor(client, name: str) -> str:
    """Another companion living in Fells Point on the same kind of week, out of focus."""
    database = client.app.state.database
    with database.connect(write=True) as connection:
        companion_id, timeline_id, now = identifier(), identifier(), database.now()
        connection.execute('INSERT INTO companions (id, slot, stepped_back_at, created_at) VALUES (?, NULL, ?, ?)',
                           (companion_id, now, now))
        version_id = insert_version(connection, companion_id, 1, CharacterDefinition(
            name=name, personality='Warm and curious.', timezone='America/New_York', home_city='baltimore',
            location='Fells Point, Baltimore', schedule=WORKDAY), '', now)
        connection.execute("INSERT INTO timelines (id, companion_id, status, created_at) VALUES (?, ?, 'active', ?)",
                           (timeline_id, companion_id, now))
        connection.execute('UPDATE companions SET active_version_id=?, active_timeline_id=? WHERE id=?',
                           (version_id, timeline_id, companion_id))
    return companion_id


def live(client, clock, ids, weeks):
    database = client.app.state.database
    for _week in range(weeks):
        with database.connect(write=True) as connection:
            for companion_id in ids:
                agenda.extend(connection, by_id(connection, companion_id), client.app.state.life.world,
                              clock.now())
        clock.instant = clock.now() + timedelta(days=7)


def settle(client, clock, ids):
    """Go on until the last meeting so far is over, and bring the agenda up to then, so the meetings counted
    have happened rather than still being ahead (the week ahead can hold the only ones)."""
    database = client.app.state.database
    with database.connect(write=True) as connection:
        last = connection.execute("SELECT MAX(a.ends_at) AS at FROM townsfolk_encounters met JOIN life_agenda a ON "
                                  "a.timeline_id=met.timeline_id AND a.slot_key=met.slot_key AND a.subject='companion' "
                                  "WHERE met.key LIKE 'cast:%'").fetchone()['at']
        if last and parse(last) > clock.now():
            clock.instant = parse(last)
        for companion_id in ids:
            agenda.extend(connection, by_id(connection, companion_id), client.app.state.life.world, clock.now())


def cast_meetings(connection) -> list[dict]:
    rows = connection.execute("SELECT met.*, c.id AS companion_id FROM townsfolk_encounters met JOIN companions c "
                              "ON c.active_timeline_id=met.timeline_id WHERE met.key LIKE 'cast:%' "
                              'ORDER BY met.local_date').fetchall()
    return [dict(row) for row in rows]


def slot(connection, timeline_id, slot_key) -> dict:
    row = connection.execute("SELECT * FROM life_agenda WHERE timeline_id=? AND slot_key=? AND subject='companion'",
                             (timeline_id, slot_key)).fetchone()
    return {**dict(row), 'entry': decode(row['entry']) if row['entry'] else None}


def test_companions_meet_where_their_own_days_take_them(client, clock, fellows, one_haunt):
    mira = make(client, 'Warm and curious.', home_city='baltimore')
    sam = neighbor(client, 'Sam Ortiz')
    live(client, clock, [mira['id'], sam], 3)
    settle(client, clock, [mira['id'], sam])
    with client.app.state.database.connect() as connection:
        met = cast_meetings(connection)
        assert met, 'Two companions with the same evenings in Fells Point never crossed paths in six weeks.'
        names = {mira['id']: 'Mira', sam: 'Sam'}
        for meeting in met:
            other = meeting['key'][len('cast:'):]
            mine = slot(connection, meeting['timeline_id'], meeting['slot_key'])
            assert mine['entry']['townsfolk']['key'] == meeting['key'] and names[other] in mine['entry']['summary']
            # The other companion really was there: their own day had them at the same place then.
            theirs = connection.execute(
                "SELECT block, entry FROM life_agenda a JOIN companions c ON c.active_timeline_id=a.timeline_id "
                "WHERE c.id=? AND a.subject='companion' AND a.local_date=? AND a.entry IS NOT NULL",
                (other, meeting['local_date'])).fetchall()
            assert any((decode(row['entry']).get('place') or {}).get('name') == meeting['place'] for row in theirs)
        # Both diaries tell the meeting, and a day counts once for each of them.
        days = {}
        for meeting in met:
            days.setdefault(meeting['local_date'], set()).add(meeting['companion_id'])
        assert any(len(who) == 2 for who in days.values())
        mine = {person['key']: person for person in encounters.known(connection, by_id(connection, mira['id']),
                                                                       clock.now())}
        his = {person['key']: person for person in encounters.known(connection, by_id(connection, sam), clock.now())}
    # Meetings still ahead on the agenda don't count yet.
    assert 1 <= mine[f'cast:{sam}']['times'] == his[f"cast:{mira['id']}"]['times'] <= len(days)


def test_another_companion_is_only_where_their_own_days_put_them(client, clock):
    mira = make(client, 'Warm and curious.', home_city='baltimore')
    sam, dana = neighbor(client, 'Sam Ortiz'), neighbor(client, 'Dana Reyes')
    live(client, clock, [sam], 1)
    with client.app.state.database.connect() as connection:
        companion = by_id(connection, mira['id'])
        cast = encounters.town_cast(connection, companion, encounters.network.city(connection, companion))
        later = clock.now().replace(tzinfo=None) + timedelta(days=30)
        plans = encounters.cast_plans(connection, cast, [later])
    # Sam has lived, so a day his agenda doesn't reach yet finds him nowhere; Dana never has, so the town's
    # rules still place her.
    assert plans == {f'cast:{sam}': []} and f'cast:{dana}' in cast['sheets']
    assert encounters.planned(plans[f'cast:{sam}'], later)['place'] is None


def test_meeting_another_companion_is_news_for_the_user(client, clock, fellows, one_haunt):
    mira = make(client, 'Warm and curious.', home_city='baltimore')
    sam = neighbor(client, 'Sam Ortiz')
    database = client.app.state.database
    for _week in range(8):  # Usually within three weeks; now and then a quiet stretch takes longer.
        live(client, clock, [mira['id'], sam], 1)
        with database.connect() as connection:
            if any(meeting['companion_id'] == mira['id'] for meeting in cast_meetings(connection)):
                break
    with database.connect(write=True) as connection:
        first = next(meeting for meeting in cast_meetings(connection) if meeting['companion_id'] == mira['id'])
        connection.execute("UPDATE life_agenda SET status='happened' WHERE timeline_id=? AND slot_key=?",
                           (first['timeline_id'], first['slot_key']))
        when = parse(first['met_at']) + timedelta(hours=1)
        triggers = openers.crossed_paths(connection, by_id(connection, mira['id']), when)
        later = openers.crossed_paths(connection, by_id(connection, mira['id']), when + timedelta(days=3))
    assert [trigger.key for trigger in triggers] == [f'crossed:cast:{sam}']
    assert 'Sam' in triggers[0].template and first['place'] in triggers[0].template
    assert 'Sam Ortiz' in triggers[0].reason and later == []
