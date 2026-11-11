"""World consistency part E, other sources (companion/life/happenings.py): life events that do not come from a
storyline go through the same door. Coworkers stay at the old place when the companion leaves their job, a friend's
engagement and wedding have a partner of record, a death in the circle leaves their partner widowed, someone just
single is not expecting, and a job change shows on the companion's partner's card."""
from datetime import date, timedelta

import pytest

from companion.characters import require_current
from companion.database import decode, encode, identifier
from companion.life import (
    agenda,
    big_days,
    big_turns,
    chapters,
    circle,
    circle_love,
    families,
    happenings,
    loss,
    love_life,
    network,
    work,
)

WORKDAY = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00', 'days': [0, 1, 2, 3, 4]},
           {'key': 'evening', 'label': 'Evening', 'kind': 'social', 'start': '18:00', 'end': '22:00'},
           {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]


@pytest.fixture
def world(client):
    response = client.post('/api/companion', json={'name': 'Sett', 'timezone': 'UTC', 'schedule': WORKDAY,
                                                     'location': 'Fells Point, Baltimore', 'home_city': 'baltimore',
                                                     'identity': 'Sett works as an accountant.',
                                                     'personality': 'Outgoing, a social butterfly.'})
    assert response.status_code == 200, response.text
    with client.app.state.database.connect(write=True) as connection:
        companion = require_current(connection)
        circle.ensure(connection, companion, client.app.state.life.world, client.app.state.database.clock.now())
    return client


def connect(client):
    return client.app.state.database.connect(write=True)


def row_of(connection, person_id):
    return dict(connection.execute('SELECT * FROM circle_people WHERE id=?', (person_id,)).fetchone())


def someone(connection, companion, index, role, **details):
    """The circle's `index`th person made into `role`, with these details and no seeded partner of their own."""
    row = circle.people(connection, companion['active_timeline_id'])[index]
    seed = next(f"{row['seed']}:{n}" for n in range(300)
                if circle_love.seeded_partner({'id': 'x', 'seed': f"{row['seed']}:{n}"}) is None)
    found = {key: value for key, value in (decode(row['details']) or {}).items()
             if key not in ('works_with_companion', 'married', 'love', 'partner')}
    connection.execute('UPDATE circle_people SET role=?, seed=?, details=? WHERE id=?',
                       (role, seed, encode(found | details), row['id']))
    return row_of(connection, row['id'])


def seeing(name='Rae'):
    return {'state': 'seeing', 'key': f'test/{name}', 'name': name, 'pronouns': 'she/her', 'source': 'test'}


def lines_of(connection, companion, person_id):
    return [item['entry']['summary'] for item in agenda.diary(connection, companion['active_timeline_id'], person_id)]


def today_of(world):
    return world.app.state.database.clock.now().date()


# A friend's engagement and wedding ----------------------------------------------------------------------------------

def wedding_people(connection, companion):
    return {row['id']: row for row in circle.people(connection, companion['active_timeline_id'])}


def test_only_a_friend_seeing_someone_gets_engaged_and_it_goes_in_their_diary(world, monkeypatch):
    monkeypatch.setattr(big_days, 'FRIEND_RATE', (0.0, 1.0, 1.0, 1.0))
    now = world.app.state.database.clock.now()
    with connect(world) as connection:
        companion = require_current(connection)
        alone = someone(connection, companion, 0, 'close friend', age=30)
        taken = someone(connection, companion, 1, 'old friend from school', age=30, partner=seeing())
        # In March every engagement for this year's spring and summer weddings has come, and no wedding has.
        spring = date(now.year + 1, 3, 20)
        found = big_days.friend_weddings(connection, companion, spring, wedding_people(connection, companion), now)
        whose = {item['person_id'] for item in found}
        assert alone['id'] not in whose and taken['id'] in whose
        state = circle_love.state(connection, row_of(connection, taken['id']))
        assert state['state'] == 'engaged' and state['partner']['name'] == 'Rae'
        lines = [item['text'] for item in happenings.for_person(connection, companion['active_timeline_id'],
                                                                 taken['id'])]
        assert lines == [f"{taken['name']} and Rae got engaged."]
        listed = network.people_of(connection, companion, taken['seed'])
        assert listed[0]['relation'] == 'fiancée'
        # Once only, whatever the days bring.
        big_days.friend_weddings(connection, companion, spring, wedding_people(connection, companion), now)
        assert connection.execute("SELECT COUNT(*) FROM person_events WHERE subject=? AND kind='engaged'",
                                  (taken['id'],)).fetchone()[0] == 1


def test_a_friend_just_out_of_a_breakup_or_with_a_partner_the_user_set_does_not_get_engaged(world, monkeypatch):
    monkeypatch.setattr(big_days, 'FRIEND_RATE', (0.0, 1.0, 1.0, 1.0))
    now = world.app.state.database.clock.now()
    with connect(world) as connection:
        companion = require_current(connection)
        parted = someone(connection, companion, 0, 'close friend', age=30, partner={
            'state': 'single', 'since': (now.date() - timedelta(days=20)).isoformat(), 'source': 'test',
            'exes': [{'key': 'test/Rae', 'name': 'Rae'}]})
        told = someone(connection, companion, 1, 'old friend from school', age=30,
                       partner={**seeing(), 'source': 'user'}, edited=['partner'])
        found = big_days.friend_weddings(connection, companion, now.date(), wedding_people(connection, companion), now)
    assert not {parted['id'], told['id']} & {item['person_id'] for item in found}


def test_a_wedding_held_marries_them_to_their_fiance_and_says_so(world):
    now = world.app.state.database.clock.now()
    with connect(world) as connection:
        companion = require_current(connection)
        friend = someone(connection, companion, 0, 'close friend', age=30,
                         partner={**seeing(), 'state': 'engaged'})
        row = {'id': identifier(), 'person_id': friend['id'], 'local_date': now.date().isoformat(), 'at_time': '14:00'}
        big_days.married(connection, companion, row, False, now)
        after = row_of(connection, friend['id'])
        state = circle_love.state(connection, after)
        assert state['state'] == 'married' and state['partner']['name'] == 'Rae'
        assert decode(after['details'])['married'] is True
        assert f"{friend['name']} and Rae got married." in lines_of(connection, companion, friend['id'])
        # The user's word on their love life stays theirs: married, and nothing else changes.
        told = someone(connection, companion, 1, 'sister', partner={**seeing('Ana'), 'source': 'user'},
                       edited=['partner'])
        big_days.married(connection, companion, {**row, 'id': identifier(), 'person_id': told['id']}, False, now)
        details = decode(row_of(connection, told['id'])['details'])
        assert details['married'] is True and details['partner']['state'] == 'seeing'


# The companion leaves their job -------------------------------------------------------------------------------------

def coworker(connection, companion, index=0):
    return someone(connection, companion, index, 'coworker', works_with_companion=True, career='Works with Sett',
                   employer='')


def test_coworkers_stay_at_the_old_place_when_the_companion_leaves_and_come_back_with_an_undo(world):
    now = world.app.state.database.clock.now()
    with connect(world) as connection:
        companion = require_current(connection)
        before = coworker(connection, companion)
        assert happenings.coworkers_moved_on(connection, companion, 'test:left', now.date(), now) >= 1
        after = row_of(connection, before['id'])
        details = decode(after['details'])
        assert after['role'] == 'former coworker' and not details.get('works_with_companion')
        assert details['career'] and details['career'] != 'Works with Sett'
        assert after['schedule'] == before['schedule']  # The hours they had.
        assert happenings.for_person(connection, companion['active_timeline_id'], before['id']) == []  # No line.
        happenings.take_back(connection, companion['active_timeline_id'], 'test:left', now)
        back = row_of(connection, before['id'])
        assert (back['role'], back['details'], back['career']) == (before['role'], before['details'], before['career'])


def test_a_new_job_chapter_moves_coworkers_on_and_undoing_it_brings_them_back(world):
    now = world.app.state.database.clock.now()
    with connect(world) as connection:
        companion = require_current(connection)
        before = coworker(connection, companion)
        chapter_id = identifier()
        connection.execute("INSERT INTO life_chapters (id, timeline_id, kind, started_on, title, told, share, "
                           "created_at) VALUES (?, ?, 'new_job', ?, '', '', '', ?)",
                           (chapter_id, companion['active_timeline_id'], now.date().isoformat(), now.isoformat()))
        chapters.make(connection, companion, None, chapter_id, 'new_job',
                      {'title': 'Sett has a new job', 'told': 'You started a new job.', 'share': 'New job!',
                       'changes': {}}, now)
        assert row_of(connection, before['id'])['role'] == 'former coworker'
    chapters.undo(world.app.state.database, chapter_id)
    with connect(world) as connection:
        assert row_of(connection, before['id'])['details'] == before['details']


def test_retiring_moves_coworkers_on(world):
    now = world.app.state.database.clock.now()
    with connect(world) as connection:
        companion = require_current(connection)
        before = coworker(connection, companion)
        today = now.date().isoformat()
        connection.execute(
            "INSERT INTO life_chapters (id, timeline_id, kind, started_on, title, told, share, details, created_at) "
            "VALUES (?, ?, 'retire', ?, 'Sett is retiring', '', '', ?, ?)",
            (identifier(), companion['active_timeline_id'], today, encode({
                'stage': 'leaving', 'next_on': today, 'last_day': today,
                'pursuit': {'label': 'Gardening', 'pursuit': 'gardening'}}), now.isoformat()))
        assert big_turns.progress(connection, companion, None, now.date(), now) == 1
        assert row_of(connection, before['id'])['role'] == 'former coworker'
    assert ('retire', 'leaving') in big_turns.LEAVING_WORK and ('business', 'planning') in big_turns.LEAVING_WORK


def test_losing_the_job_moves_coworkers_on(world, monkeypatch):
    now = world.app.state.database.clock.now()
    monkeypatch.setattr(work, 'LAYOFF_WEEKLY', 1.0)
    with connect(world) as connection:
        companion = require_current(connection)
        before = coworker(connection, companion)
        lost = work.lose_job(connection, companion, {'pay': 1.0}, now.date(), 0, now)
        assert lost and lost['status'] == 'hunting'
        assert row_of(connection, before['id'])['role'] == 'former coworker'


def test_a_job_change_shows_on_the_companions_partners_card_and_goes_back_with_it(world):
    now = world.app.state.database.clock.now()
    with connect(world) as connection:
        companion = require_current(connection)
        partner = coworker(connection, companion)
        card_id = love_life.insert(connection, companion, partner['name'], {'career': 'Works with Sett'},
                                   now.date(), now, person_id=partner['id'])
        happenings.coworkers_moved_on(connection, companion, 'test:left', now.date(), now)
        card = decode(connection.execute('SELECT details FROM love_partners WHERE id=?', (card_id,)).fetchone()[0])
        assert card['career'] == decode(row_of(connection, partner['id'])['details'])['career'] != 'Works with Sett'
        happenings.take_back(connection, companion['active_timeline_id'], 'test:left', now)
        card = decode(connection.execute('SELECT details FROM love_partners WHERE id=?', (card_id,)).fetchone()[0])
        assert card == {'career': 'Works with Sett'}


# A death in the circle --------------------------------------------------------------------------------------------

def test_a_death_leaves_their_spouse_widowed_and_bringing_them_back_undoes_it(world):
    now = world.app.state.database.clock.now()
    with connect(world) as connection:
        companion = require_current(connection)
        timeline = companion['active_timeline_id']
        mom = someone(connection, companion, 0, 'mom', age=70)
        dad = someone(connection, companion, 1, 'dad', age=72)
        circle_love.tie_between(connection, mom, dad, 'married', now)
        before = row_of(connection, mom['id'])
        assert circle_love.state(connection, before, circle.people(connection, timeline))['state'] == 'married'
        loss_id = identifier()
        connection.execute("INSERT INTO losses (id, timeline_id, kind, person_id, name, role, died_on, created_at, "
                           "updated_at) VALUES (?, ?, 'circle', ?, ?, 'dad', ?, ?, ?)",
                           (loss_id, timeline, dad['id'], dad['name'], now.date().isoformat(), now.isoformat(),
                            now.isoformat()))
        loss.happen(connection, companion, dict(connection.execute('SELECT * FROM losses WHERE id=?',
                                                                   (loss_id,)).fetchone()), now)
        after = row_of(connection, mom['id'])
        state = circle_love.state(connection, after, circle.people(connection, timeline))
        assert state['state'] == 'widowed' and state['partner'] is None and state['exes'] == []
        assert not decode(after['details']).get('married')
        loss.undo(connection, companion, loss_id, now)
        assert row_of(connection, mom['id'])['details'] == before['details']
        assert not connection.execute('SELECT 1 FROM person_events WHERE source=?', (f'loss:{loss_id}',)).fetchone()


# Someone just single is not expecting -----------------------------------------------------------------------------

def test_someone_single_by_a_breakup_is_not_expecting_for_a_while(world):
    day = date(2026, 6, 1)
    with connect(world) as connection:
        companion = require_current(connection)
        timeline = companion['active_timeline_id']
        sister = someone(connection, companion, 0, 'sister', age=30, married=True)
        assert sister['id'] in {row['id'] for row, _how in families.eligible(connection, timeline, [sister], day)}
        parted = {'state': 'single', 'since': (day - timedelta(days=30)).isoformat(), 'source': 'test'}
        sister = someone(connection, companion, 0, 'sister', age=30, partner=parted)
        assert families.eligible(connection, timeline, [sister], day) == []
        later = day + timedelta(days=families.PARTED_DAYS)
        assert families.eligible(connection, timeline, [sister], later)
