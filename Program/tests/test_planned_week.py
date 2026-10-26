"""Their week, planned by the model (companion/life/planned_week.py): off by default, once a week, checked."""
import asyncio
from datetime import timedelta

from conftest import reconcile, send, set_life
from test_chapters import mira  # noqa: F401 - fixture
from test_thoughts import linked  # noqa: F401 - fixture

from companion.life import planned_week
from companion.providers.chat import Chunk

LINES = ('- You keep sketching the harbor between meetings.\n'
         '- You want a long walk in Fells Point once work is done.\n'
         '- You are dreading the call with Thaddeus about the lease.\n'
         '- You keep thinking about the breakup rumors at work.\n'
         '- You sort out Sunday at 4 pm for the gym.')


def plan(client):
    asyncio.run(client.app.state.life.quietly_plan_week())


def weekly(provider) -> list[dict]:
    return [request for request in provider.requests if 'You plan the coming week' in request['system']]


def test_it_is_off_unless_the_user_turns_it_on(client, mira, linked, provider):  # noqa: F811
    assert client.get('/api/life/settings').json()['model_routines'] is False
    reconcile(client)
    plan(client)
    assert weekly(provider) == []


def test_the_lines_that_keep_to_the_week_reach_the_chat(client, mira, linked, provider):  # noqa: F811
    set_life(client, model_routines=True)
    reconcile(client)
    provider.replies = [[Chunk(LINES), Chunk('', 'stop')]]
    plan(client)
    [asked] = weekly(provider)
    assert 'Mira Lane' in asked['system'] and 'What the app decided for this week' in asked['system']
    assert 'Fells Point, Baltimore' in asked['system']  # Who they are, from the card.
    send(client, 'how is your week going?', 'planned-week-1')
    system = provider.requests[-1]['system']
    assert planned_week.HEADING in system
    assert 'sketching the harbor' in system and 'walk in Fells Point' in system
    assert 'call with Thaddeus' not in system  # Nobody the week has.
    assert 'breakup' not in system  # A big turn is the rules' to decide.
    assert 'Sunday at 4 pm' not in system  # A time the week does not have.


def test_once_a_week_and_again_the_next(client, mira, linked, provider, clock):  # noqa: F811
    set_life(client, model_routines=True)
    reconcile(client)
    provider.replies = [[Chunk(LINES), Chunk('', 'stop')]]
    plan(client)
    plan(client)
    assert len(weekly(provider)) == 1
    clock.advance(timedelta(days=7))
    reconcile(client)
    plan(client)
    assert len(weekly(provider)) == 2


def test_nothing_usable_is_tried_again_the_next_day(client, mira, linked, provider, clock):  # noqa: F811
    set_life(client, model_routines=True)
    reconcile(client)
    provider.replies = [[Chunk('- You argue with Thaddeus.'), Chunk('', 'stop')]]
    plan(client)
    plan(client)
    assert len(weekly(provider)) == 1
    clock.advance(timedelta(days=1, minutes=1))
    plan(client)
    assert len(weekly(provider)) == 2


def test_turning_it_off_drops_the_section_at_once(client, mira, linked, provider):  # noqa: F811
    set_life(client, model_routines=True)
    reconcile(client)
    provider.replies = [[Chunk(LINES), Chunk('', 'stop')]]
    plan(client)
    set_life(client, model_routines=False)
    send(client, 'hey', 'planned-week-2')
    assert planned_week.HEADING not in provider.requests[-1]['system']


def test_days_and_times_must_be_the_weeks_own():
    allowed = 'Identity: Dana studies photography at MICA.\n- Wednesday: Class 9:00 AM-3:00 PM.'
    text = ('- You print contact sheets before Wednesday.\n- You shoot on Friday.\n'
            '- You leave class at 3 p.m. for the light.\n- You meet at 6 pm.\n- You show MICA friends your prints.\n'
            'Not a line.')
    assert planned_week.checked(text, allowed, set()) == [
        '- You print contact sheets before Wednesday.', '- You leave class at 3 p.m. for the light.',
        '- You show MICA friends your prints.']
