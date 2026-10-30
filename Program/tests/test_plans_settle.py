"""Plans that are over close on their own; the user's word beats the guess (companion/memory/plans.py)."""
from datetime import timedelta

from test_memory import remember, system_prompt

from companion.clock import stamp


def settle(client):
    client.app.state.life.spread_news()


def current(client, subject):
    return next(item for item in client.get('/api/memories').json() if item['subject'] == subject)


def test_a_plan_whose_day_passed_is_taken_as_done(client, companion, clock):
    remember(client, layer='plan', subject='Dinner', value='Dinner at the pits', plan_status='agreed',
             applies_from=stamp(clock.now() + timedelta(hours=2)))
    settle(client)
    assert current(client, 'Dinner')['plan_status'] == 'agreed'
    clock.advance(timedelta(days=1, hours=3))
    settle(client)
    plan = current(client, 'Dinner')
    assert (plan['plan_status'], plan['settled_from']) == ('completed', 'agreed')
    prompt = system_prompt(client)
    assert '## Open plans and commitments' not in prompt
    assert 'outcome not confirmed' not in prompt


def test_an_unclear_date_gets_a_few_more_days(client, companion, clock):
    plan = remember(client, layer='plan', subject='Trip', value='Trip to Porto', plan_status='agreed',
                    applies_from=stamp(clock.now()))
    with client.app.state.database.connect(write=True) as connection:  # As a best guess found in a message would be.
        connection.execute('UPDATE memories SET dates_uncertain=1 WHERE id=?', (plan['id'],))
    clock.advance(timedelta(days=2))
    settle(client)
    assert current(client, 'Trip')['plan_status'] == 'agreed'
    clock.advance(timedelta(days=3))
    settle(client)
    assert current(client, 'Trip')['plan_status'] == 'completed'


def test_a_plan_with_no_date_closes_after_two_quiet_weeks(client, companion, clock):
    remember(client, layer='plan', subject='Festival', value='Go to the harvest festival', plan_status='proposed')
    remember(client, layer='plan', subject='Possible move', value='Might move to Denver', plan_status='proposed')
    clock.advance(timedelta(days=13))
    settle(client)
    assert current(client, 'Festival')['plan_status'] == 'proposed'
    clock.advance(timedelta(days=2))
    settle(client)
    assert current(client, 'Festival')['plan_status'] == 'completed'
    # Thinking about a move is not something that gets done.
    assert current(client, 'Possible move')['plan_status'] == 'proposed'


def test_saying_it_did_not_happen_sticks(client, companion, clock):
    remember(client, layer='plan', subject='Dinner', value='Dinner out', plan_status='agreed',
             applies_from=stamp(clock.now()))
    clock.advance(timedelta(days=2))
    settle(client)
    plan = current(client, 'Dinner')
    response = client.post(f"/api/memories/{plan['id']}/correct",
                           json={'value': plan['value'], 'plan_status': 'cancelled',
                                 'expected_revision': plan['revision']})
    assert response.status_code == 200, response.text
    settle(client)
    plan = current(client, 'Dinner')
    assert (plan['plan_status'], plan['settled_from']) == ('cancelled', None)


def test_a_plan_reopened_after_its_day_gets_two_weeks(client, companion, clock):
    remember(client, layer='plan', subject='Dinner', value='Dinner out', plan_status='agreed',
             applies_from=stamp(clock.now()))
    clock.advance(timedelta(days=2))
    settle(client)
    plan = current(client, 'Dinner')
    client.post(f"/api/memories/{plan['id']}/correct",
                json={'value': plan['value'], 'plan_status': 'agreed', 'expected_revision': plan['revision']})
    settle(client)
    assert current(client, 'Dinner')['plan_status'] == 'agreed'
    clock.advance(timedelta(days=15))
    settle(client)
    assert current(client, 'Dinner')['plan_status'] == 'completed'
