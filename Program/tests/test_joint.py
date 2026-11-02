"""Outings two people share are in both their days (companion/life/joint.py), at a time of day that fits them."""
from datetime import timedelta

from test_groups import companion_named

from companion.characters import by_id, require_current
from companion.clock import parse, stamp
from companion.database import decode, encode, identifier, many
from companion.life import agenda, circle, composer, joint, routine
from companion.world.source import CatalogWorld

DEFINITION = {'name': 'Mira', 'location': 'Fells Point, Baltimore'}


def social(start: str, end: str) -> dict:
    return {'key': 'out', 'label': 'Out with friends', 'kind': 'social', 'start': start, 'end': end}


def test_dinner_drinks_and_shows_wait_for_the_evening(monkeypatch):
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    world, friend = CatalogWorld(), [{'id': 'p1', 'name': 'Lestara'}]

    def picks(block):
        return [composer.compose({'key': f'out@2026-11-{day:02d}', 'local_date': f'2026-11-{day:02d}', 'block': block},
                                 DEFINITION, world, f'seed-{day}-{block["start"]}', company=friend)
                for day in range(1, 29)]

    morning = picks(social('10:00', '12:00'))
    assert {item['activity'] for item in morning} <= {'coffee', 'walk', 'festival'}
    assert any(item['with'] and 'Lestara' in item['summary'] for item in morning)
    evening = {item['activity'] for item in picks(social('19:00', '23:00'))}
    assert 'dinner' in evening and not evening & {'coffee', 'walk'}
    # A leisure block at night never goes to the museum or the market.
    night = {'key': 'late', 'label': 'Late', 'kind': 'leisure', 'start': '21:00', 'end': '23:30'}
    assert not {item['activity'] for item in picks(night)} & {'museum', 'market'}


def test_a_plan_for_the_morning_is_never_dinner():
    future = [{'key': f'out@2026-11-{day:02d}', 'local_date': f'2026-11-{day:02d}', 'block': social('10:00', '12:00'),
               'starts_at': f'2026-11-{day:02d}T10:00:00Z', 'ends_at': f'2026-11-{day:02d}T12:00:00Z'}
              for day in range(2, 9)]
    planned = [composer.plan_ahead(DEFINITION, CatalogWorld(), f'seed-{n}', future) for n in range(300)]
    assert {plan['activity'] for plan in planned if plan} <= {'coffee', 'walk'}


def test_the_same_name_is_the_same_person():
    def person(name, **details):
        return {'name': name, 'details': encode(details)}
    assert joint.is_them(person('Lestara Vey'), 'lestara  vey')
    assert joint.is_them(person('Lestara', sheet='Lestara'), 'Lestara Vey')  # The user wrote her in.
    assert not joint.is_them(person('Lestara'), 'Lestara Vey')  # The app's own Lestara is someone else.
    assert not joint.is_them(person('Sam Ortiz', by_hand=True), 'Mira')


def evening_slot(connection, companion, now):
    schedule, _default = routine.blocks(companion['version']['definition'])
    return next(slot for slot in routine.slots(schedule, companion['version']['timezone'], now + timedelta(days=1),
                                               now + timedelta(days=3)) if slot.block.key == 'evening')


def dinner_with(connection, companion: dict, person: dict, starts_at, ends_at) -> str:
    """Mira's upcoming dinner with someone from her circle, as the composer would have written it."""
    row_id = identifier()
    entry = {'summary': f"Mira had dinner with {person['name']} at Cloud Step Inn.", 'post': 'Good food.',
             'mood': 'warm', 'activity': 'dinner', 'place': {'name': 'Cloud Step Inn', 'kind': 'restaurant'},
             'with': {'id': person['id'], 'name': person['name']}, 'composer_version': composer.COMPOSER_VERSION}
    connection.execute(
        'INSERT INTO life_agenda (id, timeline_id, subject, slot_key, starts_at, ends_at, local_date, block, entry, '
        "basis, created_at) VALUES (?, ?, 'companion', ?, ?, ?, ?, ?, ?, ?, ?)",
        (row_id, companion['active_timeline_id'], f'dinner@{starts_at.date()}', stamp(starts_at), stamp(ends_at), str(starts_at.date()),
         encode(social('19:00', '22:00')), encode(entry), companion['version']['id'], stamp(starts_at)))
    return row_id


def test_dinner_with_another_companion_is_in_both_their_days(client, companion):
    """Lestara is a companion of the user's and, under her own name, in Sett's circle: the dinner Sett had with her is
    in her day too, at the same time, and not her trip to the fish stalls."""
    billy_id = companion_named(client, 'Billy Hart')
    database, world = client.app.state.database, client.app.state.life.world
    with database.connect(write=True) as connection:
        mira, now = require_current(connection), database.clock.now()
        person = circle.ensure(connection, mira, world, now)[0]
        connection.execute("UPDATE circle_people SET name='Billy Hart' WHERE id=?", (person['id'],))
        person = {**person, 'name': 'Billy Hart'}
        billy = by_id(connection, billy_id)
        assert joint.twins(connection, mira['active_timeline_id']) == {
            person['id']: {'id': billy_id, 'timeline_id': billy['active_timeline_id'], 'name': 'Billy Hart'}}
        evening = evening_slot(connection, billy, now)
        # Billy is free in his evening, not while he sleeps.
        assert joint.free(connection, joint.twins(connection, mira['active_timeline_id'])[person['id']],
                          evening.starts_at, evening.ends_at, mira['active_timeline_id'])
        asleep = evening.ends_at + timedelta(hours=2)
        assert not joint.free(connection, {'id': billy_id, 'timeline_id': billy['active_timeline_id']}, asleep,
                              asleep + timedelta(hours=1), mira['active_timeline_id'])
        begins = evening.starts_at + timedelta(hours=1)
        dinner = dinner_with(connection, mira, person, begins, begins + timedelta(hours=2))
        agenda.extend(connection, billy, world, now)
        rows = many(connection, "SELECT * FROM life_agenda WHERE timeline_id=? AND subject='companion' AND starts_at<? "
                    'AND ends_at>?', (billy['active_timeline_id'], stamp(begins + timedelta(hours=2)), stamp(begins)))
        assert len(rows) == 1
        entry = decode(rows[0]['entry'])
        # Where inside the place he sat can follow (companion/world/inside.py).
        assert entry['summary'].startswith('Billy Hart had dinner with Mira at Cloud Step Inn.')
        assert entry['joint']['slot'] == f'dinner@{begins.date()}' and parse(rows[0]['starts_at']) == begins
        assert joint.holds(connection, entry)

        # The plan changed: Mira's dinner is gone, so Billy's evening is his own again.
        connection.execute('DELETE FROM life_agenda WHERE id=?', (dinner,))
        assert not joint.holds(connection, entry)
        agenda.extend(connection, billy, world, now)
        found = many(connection, "SELECT entry FROM life_agenda WHERE timeline_id=? AND subject='companion' "
                     'AND slot_key=?', (billy['active_timeline_id'], rows[0]['slot_key']))
        assert len(found) == 1 and not (decode(found[0]['entry']) or {}).get('joint')


def test_dinner_with_someone_in_the_circle_is_in_their_diary(client, companion):
    database, world = client.app.state.database, client.app.state.life.world
    with database.connect(write=True) as connection:
        mira, now = require_current(connection), database.clock.now()
        agenda.extend(connection, mira, world, now)
        timeline_id = mira['active_timeline_id']
        people = {row['id']: row for row in circle.people(connection, timeline_id)}
        # A free stretch of someone's day tomorrow.
        row = next(row for row in many(
            connection, "SELECT * FROM life_agenda WHERE timeline_id=? AND subject!='companion' AND status='upcoming' "
            'AND starts_at>? ORDER BY starts_at', (timeline_id, stamp(now + timedelta(days=1))))
            if row['subject'] in people and not joint.spoken_for(row)
            and parse(row['ends_at']) - parse(row['starts_at']) >= timedelta(hours=2))
        person = people[row['subject']]
        begins = parse(row['starts_at']) + timedelta(minutes=30)
        dinner_with(connection, mira, person, begins, begins + timedelta(hours=1, minutes=30))
        joint.make_room(connection, {'subject': 'companion', 'timeline_id': timeline_id}, begins,
                        begins + timedelta(hours=1, minutes=30), {'with': {'id': person['id']}})
        agenda.extend(connection, mira, world, now)
        theirs = many(connection, 'SELECT * FROM life_agenda WHERE timeline_id=? AND subject=? AND starts_at<? '
                      'AND ends_at>? AND entry IS NOT NULL', (timeline_id, person['id'],
                                                              stamp(begins + timedelta(hours=1, minutes=30)),
                                                              stamp(begins)))
        assert len(theirs) == 1
        assert decode(theirs[0]['entry'])['summary'].startswith(f"{person['name']} had dinner with Mira at Cloud Step Inn.")
        assert parse(theirs[0]['starts_at']) == begins
