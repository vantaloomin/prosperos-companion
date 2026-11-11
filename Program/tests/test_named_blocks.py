"""A free block named for what it holds ("Bathhouse and cards") keeps to it, and a planned item in a slot is never
replaced by a pastime (Vanta, 2026-11-09: Sett said he was at the bathhouse playing cards, then that he had spent the
afternoon on business strategy, a pastime session that had taken the slot over a late night at work)."""
from companion.life import agenda, composer, grooming, hobbies

BATHHOUSE = {'key': 'bathhouse-and-cards', 'label': 'Bathhouse and cards', 'kind': 'leisure', 'start': '14:00',
             'end': '20:00', 'themes': ['rest', 'gambling']}


def test_a_block_named_for_an_activity_is_named_and_a_stretch_of_time_is_not():
    assert composer.named(BATHHOUSE)
    assert composer.named({**BATHHOUSE, 'label': 'Sunday with ma', 'kind': 'social'})
    assert composer.named({**BATHHOUSE, 'label': 'Training yard'})
    for label in ('Free time after work', 'Day off', 'Evening', 'Morning', 'Free time', 'Quiet night in', 'Retired',
                  'Out with friends', 'Seeing people'):
        assert not composer.named({**BATHHOUSE, 'label': label}), label
    # Work, a holiday, a sick day, an outing with the user and a changed plan keep their own accounts.
    assert not composer.named({**BATHHOUSE, 'kind': 'work'})
    for key in ('holiday', 'sick_day', 'with_user', 'trip', 'planned'):
        assert not composer.named({**BATHHOUSE, key: 'x'}), key


def test_a_named_block_is_spent_as_its_label_and_notes_say():
    entry = composer.own_block({'block': BATHHOUSE, 'local_date': '2026-11-09'}, {'name': 'Sett'})
    assert entry['summary'] == 'Sett spent the afternoon as usual: Bathhouse and cards (rest, gambling).'
    assert entry['activity'] == 'own-block'
    assert composer.usual({**BATHHOUSE, 'start': '10:00', 'themes': []}) == 'morning as usual: Bathhouse and cards.'
    assert composer.usual({**BATHHOUSE, 'start': '19:00'}).startswith('evening as usual')


def test_a_pastime_or_a_salon_visit_never_takes_a_planned_slot_or_a_named_one():
    late = {'summary': 'Sett stayed late at work.', 'activity': 'staying-late-at-work', 'admin': {'id': 'x'},
            'planned': True}
    own = composer.own_block({'block': BATHHOUSE, 'local_date': '2026-11-09'}, {'name': 'Sett'})
    for entry in (late, own):
        assert not hobbies.swappable(entry, BATHHOUSE)
        assert not grooming.swappable(entry, BATHHOUSE)
    assert hobbies.swappable({'summary': 'Sett read.', 'activity': 'reading'}, {**BATHHOUSE, 'label': 'Free time'})


def test_a_late_night_that_takes_the_start_of_a_named_block_is_followed_by_it():
    entry = {'summary': 'Sett stayed late at work on settling a dispute over a contested bout.',
             'admin': {'id': 'x', 'at': '14:00', 'until': '17:00'}}
    plan = {'admin': {}}
    assert agenda.rest_of(entry, plan, BATHHOUSE)['summary'] == (
        'Sett stayed late at work on settling a dispute over a contested bout. After that, the rest of the afternoon '
        'as usual: Bathhouse and cards (rest, gambling).')
    # One that runs to the block's end, or in a block that is only a stretch of time, is all there is.
    assert agenda.rest_of({**entry, 'admin': {'until': '20:00'}}, plan, BATHHOUSE)['summary'] == entry['summary']
    assert agenda.rest_of(entry, plan, {**BATHHOUSE, 'label': 'Free time'}) == entry
    assert agenda.rest_of(entry, {'outing': {}}, BATHHOUSE) == entry
