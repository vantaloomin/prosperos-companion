"""Rule-based extraction and date resolution (PRD M7, M8)."""
from datetime import UTC, date, datetime

import pytest

from companion.memory import dates
from companion.memory.extraction import extract

# Monday 5 October 2026, 08:00 in New York.
STATED = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
ZONE = 'America/New_York'


def found(text):
    return [(item.layer, item.subject, item.value) for item in extract(text, STATED, ZONE)]


@pytest.mark.parametrize('text, expected', [
    ('I moved to Boston last week.', [('user_fact', 'Home city', 'Boston')]),
    ('I might move to Boston', [('plan', 'Possible move', 'Might move to Boston')]),
    ('I live in Rio de Janeiro now', [('user_fact', 'Home city', 'Rio de Janeiro')]),
    ('My name is Sam. Please don\'t call me Samuel.',
     [('user_fact', 'Preferred name', 'Sam'), ('user_fact', 'Boundary', "Don't call me Samuel")]),
    ('My nickname is qoncat', [('user_fact', 'Nickname', 'qoncat')]),
    ("My nick name's Q by the way", [('user_fact', 'Nickname', 'Q')]),
    ("That isn't my nickname anymore", []),
    ('I really love genmaicha tea', [('user_fact', 'Likes', 'genmaicha tea')]),
    ("I'm going to Lisbon on Saturday", [('plan', 'Trip to Lisbon', "I'm going to Lisbon on Saturday")]),
    ('I work nights as a 911 dispatcher', [('user_fact', 'Work', '911 dispatcher')]),
    ('I work part-time at Target', [('user_fact', 'Work', 'Target')]),
    ('I work nights', []),
    ('I love you', []),
    ('Do I live in Paris?', []),
    ('Hypothetically, I live on the moon', []),
    ('My friend said "I live in Rome"', []),
    ('*walks in* I live in Narnia', []),
    ('If I lived in Oslo I would be cold', []),
])
def test_statements(text, expected):
    assert found(text) == expected


def test_an_old_home_ends_in_the_past_with_uncertain_dates():
    [item] = extract('I lived in Seattle ten years ago', STATED, ZONE)
    assert item.applies_until < STATED and item.dates_uncertain


def test_temporary_circumstances_end_with_their_interval():
    [today] = extract("I'm exhausted today", STATED, ZONE)
    assert today.applies_until == datetime(2026, 10, 6, tzinfo=dates.zone(ZONE))
    [busy] = extract("I'm busy until Friday", STATED, ZONE)
    assert busy.applies_until == datetime(2026, 10, 10, tzinfo=dates.zone(ZONE))


def test_sensitive_statements_are_marked():
    [allergy] = extract("I'm allergic to peanuts", STATED, ZONE)
    assert allergy.sensitive


@pytest.mark.parametrize('phrase, start, certain', [
    ('tomorrow', date(2026, 10, 6), True),
    ('on Thursday', date(2026, 10, 8), True),
    ('next Thursday', date(2026, 10, 8), False),
    ('next week', date(2026, 10, 12), True),
    ('in three days', date(2026, 10, 8), True),
    ('the 20th of November', date(2026, 11, 20), True),
    ('2027-01-02', date(2027, 1, 2), True),
])
def test_relative_dates_resolve_against_the_statement(phrase, start, certain):
    span = dates.resolve(phrase, STATED, ZONE)
    assert (span.start, span.certain) == (start, certain)


def test_dates_use_the_users_local_day():
    # 02:00 UTC on Tuesday is still Monday evening in New York.
    late = datetime(2026, 10, 6, 2, 0, tzinfo=UTC)
    assert dates.resolve('tomorrow', late, ZONE).start == date(2026, 10, 6)


def test_vague_times_resolve_to_nothing():
    assert dates.resolve('sometime soon', STATED, ZONE) is None
