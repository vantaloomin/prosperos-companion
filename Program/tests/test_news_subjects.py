"""News has a subject (companion/news.py, world consistency part E): what happens to someone in the circle is their
own news. Tester 2026-11-10: "Word getting around" listed Kaito as having heard of his own breakup a day later."""
import json
from datetime import timedelta

from test_happenings import companion_of, connect, now_of, someone, start_story  # noqa: F401 - now_of is a fixture
from test_happenings import world as world  # noqa: F401 - the fixture

from companion import news
from companion.database import identifier
from companion.memory import pairs


def breakup(connection):
    companion = companion_of(connection)
    kaito = someone(connection, companion, 'close friend', seed_partner=True)
    start_story(connection, companion, 'friend_breakup', [kaito['id']], days_ago=3)
    return companion, kaito


def holder(connection, news_id, key):
    return connection.execute('SELECT * FROM news_holders WHERE news_id=? AND holder=?', (news_id, key)).fetchone()


def test_the_person_it_happened_to_knows_from_the_start_and_never_hears_it(world):
    with connect(world) as connection:
        companion, kaito = breakup(connection)
        now = world.app.state.database.clock.now()
        item = next(found for found in news.found(connection, companion, now) if found['source'].startswith('storyline:'))
        assert item['subjects'] == [kaito['seed']]
        news.register(connection, companion, now)
        row = connection.execute('SELECT * FROM news WHERE source=?', (item['source'],)).fetchone()
        assert json.loads(row['subjects']) == [kaito['seed']]
        own = holder(connection, row['id'], kaito['seed'])
        assert (own['hop'], own['via'], own['told_by']) == (0, 'origin', None)
        # Spread for days: he is never told it, and it is never news he "heard".
        news.sync(connection, now + timedelta(days=4))
        assert holder(connection, row['id'], kaito['seed'])['hop'] == 0
        assert news.heard(connection, kaito['seed'], '2000-01-01') == []
        listed = next(found for found in news.listing(connection, companion, now) if found['id'] == row['id'])
        assert kaito['name'] not in [heard['name'] for heard in listed['heard']]


def test_their_own_news_is_theirs_to_tell_in_a_group(world):
    with connect(world) as connection:
        companion, kaito = breakup(connection)
        now = world.app.state.database.clock.now()
        news.register(connection, companion, now)
        row = connection.execute("SELECT * FROM news WHERE source LIKE 'storyline:%'").fetchone()
        mira = pairs.companion_key(companion['id'])
        guest = 'circle:someone-else'
        lines = news.group_lines(connection, 'circle:teller', [mira, kaito['seed'], guest],
                                 {kaito['seed']: 'Kaito', guest: 'Ana', mira: 'Sett'}, now)
        assert lines == []  # The teller has not heard it.
        news.hear(connection, row['id'], 'circle:teller', mira, 1, row['happened_on'], 'word', 'x')
        lines = news.group_lines(connection, 'circle:teller', [mira, kaito['seed'], guest],
                                 {kaito['seed']: 'Kaito', guest: 'Ana', mira: 'Sett'}, now)
        assert lines[0][1].endswith("It is Kaito's news, so let them tell it.")
        assert news.own_news(dict(row), kaito['seed']) and news.own_news(dict(row), mira)
        assert not news.own_news(dict(row), guest)


def test_news_from_before_it_had_subjects_is_put_right(world):
    with connect(world) as connection:
        companion, kaito = breakup(connection)
        now = world.app.state.database.clock.now()
        item = next(found for found in news.found(connection, companion, now) if found['source'].startswith('storyline:'))
        news_id, mira = identifier(), pairs.companion_key(companion['id'])
        connection.execute("INSERT INTO news (id, timeline_id, source, about, text, happened_on, created_at) VALUES "
                           "(?, ?, ?, ?, ?, ?, 'x')", (news_id, companion['active_timeline_id'], item['source'], mira,
                                                       item['text'], item['happened_on']))
        news.hear(connection, news_id, mira, None, 0, item['happened_on'], 'origin', 'x')
        news.hear(connection, news_id, kaito['seed'], mira, 1, item['happened_on'], 'word', 'x')
        news.register(connection, companion, now)
        assert json.loads(connection.execute('SELECT subjects FROM news WHERE id=?', (news_id,)).fetchone()[0]) == \
            [kaito['seed']]
        own = holder(connection, news_id, kaito['seed'])
        assert (own['hop'], own['via'], own['told_by']) == (0, 'origin', None)


def test_the_circle_line_says_their_love_life_once_an_event_changed_it(world):
    from companion.life import storylines
    from companion.memory import context
    with connect(world) as connection:
        companion, kaito = breakup(connection)
        now = world.app.state.database.clock.now()
        today = storylines.local_today(companion, now).isoformat()
        assert context.love_lines(connection, companion, today) == {}  # Seeded: nothing said.
        storylines.record_due(connection, companion, now)
        line = context.love_lines(connection, companion, today)[kaito['id']]
        assert line.startswith('Single since a breakup in ')
        sister = someone(connection, companion, 'sister', seed_partner=False)
        start_story(connection, companion, 'sibling_engaged', [sister['id']], days_ago=3)
        storylines.record_due(connection, companion, now)
        engaged = context.love_lines(connection, companion, today)[sister['id']]
        assert engaged.startswith('Engaged to ') and engaged.endswith('.')
        assert context.person_text({'name': 'Mara', 'role': 'sister', 'career': '', 'employer': '', 'married': True,
                                    'love': engaged}).endswith(engaged)  # Not also "Married."


def test_a_circle_guest_knows_their_own_news(world):
    from companion import group_guests
    from companion.life import storylines
    with connect(world) as connection:
        companion, kaito = breakup(connection)
        now = world.app.state.database.clock.now()
        storylines.record_due(connection, companion, now)
        person = group_guests.from_circle(dict(connection.execute('SELECT * FROM circle_people WHERE id=?',
                                                                   (kaito['id'],)).fetchone()),
                                          f"companion:{companion['id']}", 'Sett')
        found = group_guests.own_news(connection, person, companion, now)
        assert found[0].endswith('broke up.') and 'doing better' in found[1]  # In the order it happened.
        assert found[0].split(': ')[0].split(' ')[0] in ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
