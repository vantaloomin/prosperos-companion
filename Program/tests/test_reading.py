"""Reading texts while free: a seeded little while before the reply starts, and texts in a row answered together."""
import asyncio
from datetime import timedelta

import pytest
from conftest import set_life

from companion.clock import parse
from companion.conversation import Conversation
from companion.life import reading
from companion.models import MessageCreate


@pytest.fixture
def chat(app, connected, provider, monkeypatch):
    monkeypatch.setattr(reading, 'ACTIVE', True)
    monkeypatch.setattr(reading, 'POLL_SECONDS', 0.01)
    return Conversation(app.state.database, app.state.vault, provider)


def text(body, client_id):
    return MessageCreate(text=body, client_id=client_id)


def waits(result, clock) -> float:
    return (parse(result['reply']['held_until']) - clock.now()).total_seconds()


async def read_and_finish(chat, clock, reply_id):
    await asyncio.sleep(0.05)
    clock.instant = parse(chat.reply(reply_id)['held_until']) + timedelta(seconds=1)
    await chat.running[reply_id].task
    return chat.reply(reply_id)


def test_a_free_companion_reads_a_text_a_little_later_and_the_model_waits(chat, provider, clock):
    async def scenario():
        result = await chat.send(text('Hey you', 'reading-01'), wait=False)
        await asyncio.sleep(0.05)
        assert provider.requests == []  # Nothing asked of the model while the text is unread.
        return result, await read_and_finish(chat, clock, result['reply']['id'])

    start = clock.now()
    result, reply = asyncio.run(scenario())
    held = (parse(result['reply']['held_until']) - start).total_seconds()
    assert reading.GOING[2][0] * (1 - 4 * reading.CLOSER) <= held <= reading.PICK_UP[2][1] * reading.AWAY
    assert result['reply']['status'] == 'streaming'
    assert reply['status'] == 'complete' and reply['text'] == 'Hello again.' and len(provider.requests) == 1
    assert reading.SEVERAL not in provider.requests[0]['prompt']


def test_texts_in_a_row_get_one_reply_that_answers_them_all(chat, provider, clock):
    async def scenario():
        first = await chat.send(text('So guess what', 'reading-02'), wait=False)
        clock.advance(timedelta(seconds=3))
        second = await chat.send(text('I got the job!!', 'reading-03'), wait=False)
        clock.advance(timedelta(seconds=3))
        third = await chat.send(text('starting monday', 'reading-04'), wait=False)
        reply = await read_and_finish(chat, clock, third['reply']['id'])
        return first, second, third, reply

    start = clock.now()
    first, second, third, reply = asyncio.run(scenario())
    assert second['dropped'] == [first['reply']['id']] and third['dropped'] == [second['reply']['id']]
    assert chat.reply(first['reply']['id'])['superseded_at'] and chat.reply(first['reply']['id'])['status'] == 'cancelled'
    assert len(provider.requests) == 1 and reading.SEVERAL in provider.requests[0]['prompt']
    said = [message['content'] for message in provider.requests[0]['messages']]
    assert any('So guess what' in part for part in said) and 'starting monday' in said[-1]
    held = parse(third['reply']['held_until'])
    assert held >= parse(first['reply']['held_until'])
    assert held >= start + timedelta(seconds=6 + reading.QUIET[2])
    assert held <= start + timedelta(seconds=reading.CAP[2])
    assert reply['status'] == 'complete'


def test_the_wait_never_runs_past_the_cap_from_the_first_text(chat, clock):
    async def scenario():
        results = []
        for index in range(12):
            results.append(await chat.send(text(f'and {index}', f'reading-1{index:02}'), wait=False))
            clock.advance(timedelta(seconds=15))
        for task in [live.task for live in chat.running.values()]:
            task.cancel()
        return results

    start = clock.now()
    results = asyncio.run(scenario())
    assert parse(results[-1]['reply']['held_until']) <= start + timedelta(seconds=reading.CAP[2])


def test_a_companion_quick_to_reply_reads_at_the_quick_pace(app, client, chat, clock):
    version = client.get('/api/companion').json()['companion']['version']
    definition = {**version['definition'], 'texting': {'quick': True}}
    made = client.post('/api/companion/versions', json={'definition': definition, 'expected_version_id': version['id']})
    assert made.status_code == 200, made.text
    set_life(client, read_pace=3)

    async def scenario():
        result = await chat.send(text('Hi', 'reading-20'), wait=False)
        chat.running[result['reply']['id']].task.cancel()
        return result

    assert waits(asyncio.run(scenario()), clock) <= reading.PICK_UP[1][1] * reading.AWAY


def test_at_once_off_out_of_character_and_another_reply_start_right_away(chat, client, provider, clock):
    async def scenario():
        ooc = await chat.send(text('((how are you doing this?))', 'reading-30'), wait=False)
        await chat.running[ooc['reply']['id']].task
        again = await chat.alternative(ooc['message']['id'], wait=False)
        await chat.running[again['reply']['id']].task
        set_life(client, read_pace=0)
        plain = await chat.send(text('Hi', 'reading-31'), wait=False)
        await chat.running[plain['reply']['id']].task
        return ooc, again, plain

    for result in asyncio.run(scenario()):
        assert result['reply']['held_until'] is None
    assert client.get('/api/life/settings').json()['read_pace'] == 0
