"""Earlier in this talk (companion/memory/earlier.py, Feature Hit List #99): a rule-built bridge of the turns that left
the conversation window, so things said only in chat (a nickname, two films, a riddle answer) are still known."""
from datetime import UTC, datetime, timedelta

from conftest import send

from companion.characters import require_current
from companion.memory import context, earlier, look_back
from companion.providers.chat import Chunk

START = datetime(2026, 11, 10, 18, 0, tzinfo=UTC)


def turns(texts: list[str], gap=timedelta(minutes=1), first: int = 0) -> list[dict]:
    """Messages alternating user and companion, `gap` apart."""
    return [{'id': f'm{first + index}', 'seq': first + index, 'role': 'user' if index % 2 == 0 else 'companion',
             'text': text, 'created_at': (START + gap * (first + index)).isoformat()}
            for index, text in enumerate(texts)]


def test_the_users_key_sentences_are_picked_by_rule():
    known = {'mira', 'sam'}
    step = turns(['ok so my day was long. lol ok new rule, from now on you have to call me Captain Crumbs',
                  'Haha deal. *salutes* What movie for saturday?',
                  'I vote Paddington 2, or Arrival if you insist. the weather is nice',
                  '*grins* Arrival it is.'])
    said = earlier.picked(step, known)
    assert len(said) == earlier.PICKED
    assert 'Captain Crumbs' in said[0][1] and said[0][0] == 'm0'
    assert 'Paddington 2' in said[1][1], 'a number, a name the app does not know and an answer to their question'
    assert all('weather' not in text and 'day was long' not in text for _id, text in said)
    assert earlier.picked(turns(['how was your shift today?', 'Long!', 'ok same']), known) == []
    long = earlier.picked(turns(['My favourite thing is ' + 'very ' * 60 + 'long']), known)
    assert len(long[0][1]) <= earlier.CUT and long[0][1].endswith('…')


def test_known_names_do_not_count_and_actions_are_the_first_and_last():
    step = turns(['Sam said hi', '*waves* hey. *sits down* ok. *laughs*', 'Mira you are funny', '*blushes*'])
    assert earlier.picked(step, {'sam', 'mira'}) == []
    assert [text for _id, text in earlier.actions(step)] == ['waves', 'blushes']


def test_the_talk_stops_at_a_long_gap_and_after_a_dates_opening():
    older = turns(['a b'] * 6, gap=timedelta(minutes=10))
    older[2]['created_at'] = (START - timedelta(hours=5)).isoformat()
    first_recent = {'created_at': (START + timedelta(hours=1)).isoformat()}
    assert [message['id'] for message in earlier.talk(older, first_recent)] == ['m3', 'm4', 'm5']
    assert [message['id'] for message in earlier.talk(older, first_recent, older[3:5])] == ['m5']
    late = {'created_at': (START + timedelta(hours=9)).isoformat()}
    assert earlier.talk(older, late) == [], 'a new talk began with the conversation sent'
    many = turns(['a b'] * 200)
    assert len(earlier.talk(many, None)) == earlier.TALK_TURNS


def test_one_entry_per_step_with_saved_memories_and_the_budget_shrinks_the_oldest_first():
    texts = [f'call me Captain {index}' if index % 2 == 0 else f'*nods {index}* sure' for index in range(48)]
    talk = turns(texts)
    memories = [{'id': 'k1', 'subject': 'Nickname', 'value': 'Captain 0', 'source_message_ids': ['m0']},
                {'id': 'k2', 'subject': 'Rule', 'value': 'none', 'source_message_ids': ['m30'], 'boundary': True}]
    built = earlier.bridge(talk, 48, 12, set(), memories, 'UTC', budget=10_000)
    assert [identity for identity, _text in built.shown] == ['earlier:m0', 'earlier:m12', 'earlier:m24',
                                                             'earlier:m36']
    first = built.shown[0][1].splitlines()
    assert first[0].startswith('- Tue 18:00: The user said: "call me Captain 0"') and len(first) == 3
    assert first[1] == '  You: *nods 1* … *nods 11*' and first[2] == '  Saved: Nickname: Captain 0'
    assert 'none' not in '\n'.join(text for _id, text in built.shown), 'boundaries are in the prompt already'
    assert built.spare == []
    tight = earlier.bridge(talk, 48, 12, set(), memories, 'UTC', budget=120)
    assert tight.shown[-1] == built.shown[-1], 'the newest entry keeps all its lines'
    assert sum(context.token_estimate(text) for _id, text in tight.shown) <= 120
    assert len(tight.shown) < 4 or len(tight.shown[0][1].splitlines()) == 1
    assert {item['id'] for item in tight.spare} and all(item['text'] for item in tight.spare), 'left out for recall'


def test_the_steps_stay_put_as_the_window_moves():
    talk = turns(['call me X'] * 36)
    before = earlier.steps(talk[:24], 24, 12)
    after = earlier.steps(talk, 36, 12)
    assert after[:2] == before and [message['id'] for message in after[2]][0] == 'm24'


def test_the_wider_gate_points_back_at_things_said_only_in_chat():
    assert not look_back.points_back('what was the answer to that puzzle?')
    known = {'mira', 'sam', 'juniper'}
    for text in ('what was the answer to that puzzle?', 'which one was that film again', "what's the nickname?",
                 'who is Priyanka again?', 'what did Priyanka bring in'):
        assert look_back.points_back(text, known), text
    for text in ('What are you doing tonight?', 'How is Juniper?', 'I love you Mira', 'See you Friday', 'OK cool'):
        assert not look_back.points_back(text, known), text
    assert look_back.points_back('Do you remember the ferry?', known)


def chatting(system, messages):
    text = messages[-1]['content'].rsplit('\n', 1)[-1]
    return [Chunk(f'*smiles* You said {text[:12]}. Tell me more.'), Chunk('', 'stop')]


def system(app) -> str:
    database = app.state.database
    with database.connect() as connection:
        return context.build(connection, require_current(connection), database.clock.now(), 30_000)['system']


def section(prompt: str) -> str:
    heading = f'## {earlier.HEADING}\n'
    return prompt.split(heading, 1)[1] if heading in prompt else ''


def test_a_long_chat_carries_the_bridge_until_the_window_steps(client, app, connected, provider, clock):
    provider.respond = chatting
    send(client, 'lol new rule, from now on you have to call me Captain Crumbs', 'plant-0001')
    for index in range(8):
        send(client, f'filler message {index}', f'filler-{index:04d}')
    assert section(system(app)) == '', 'everything is still in the conversation'
    for index in range(8, 15):
        send(client, f'filler message {index}', f'filler-{index:04d}')
    found = section(system(app))
    assert '"lol new rule, from now on you have to call me Captain Crumbs"' in found
    assert system(app).endswith(found), 'last, right before the conversation'
    send(client, 'one more', 'one-more-0001')
    assert section(system(app)) == found, 'it holds until the window steps, so the prompt stays cacheable'
    with app.state.database.connect(write=True) as connection:
        connection.execute("UPDATE messages SET text='call me Admiral Toast' WHERE client_id='plant-0001'")
    assert 'Admiral Toast' in section(system(app)) and 'Crumbs' not in section(system(app)), 'an edit rebuilds it'


def test_lines_left_out_are_recalled_once_under_their_turns_identity():
    older = turns(['call me Captain Crumbs because I eat crackers in bed', '*laughs* deal'])
    spare = [{'id': 'm0', 'created_at': older[0]['created_at'], 'role': 'user',
              'text': 'The user said: "call me Captain Crumbs because I eat crackers in bed"'}]
    found = context.recalled([], older, 'Captain Crumbs crackers', spare=spare, timezone='UTC')
    assert [identity for identity, _text in found] == ['m0'], 'the turn comes up once'
    assert found[0][1].startswith('- Earlier in this talk (2026-11-10 18:00): The user said') or \
        found[0][1].startswith('- Earlier (2026-11-10 18:00, user)')
