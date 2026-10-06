"""Time-aware recall and near-duplicate spreading (PRD M10)."""
from datetime import UTC, datetime, timedelta

from conftest import send

from companion.memory import context, time_recall
from companion.memory.chunks import compile_chunks
from companion.memory.retrieval import Hit

MONDAY = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)


def day(text):
    span = time_recall.query_span(text, MONDAY, 'UTC')
    return None if span is None else (span[0].date().isoformat(), span[1].date().isoformat())


def test_a_named_time_in_the_question_becomes_a_span():
    assert day('what did I tell you last Monday?') == ('2026-10-05', '2026-10-06')
    assert day('how was your weekend? last weekend was wild') == ('2026-10-10', '2026-10-12')
    assert day('remember what we said on Friday') == ('2026-10-09', '2026-10-10'), 'a question looks back'
    assert day("what's the plan for Friday") == ('2026-10-16', '2026-10-17'), 'plans look ahead'
    assert day('the trip in March') == ('2026-03-01', '2026-04-01')


def test_today_and_no_time_add_nothing():
    assert day("I'm so tired today") is None
    assert day('tell me about your sister') is None


def memory(identity, value, **extra):
    return {'id': identity, 'subject': 'Moment', 'value': value, 'layer': 'shared_experience', 'boundary': False,
            'pinned': False, 'plan_status': None, 'applies_from': None, 'applies_until': None,
            'stated_at': '2026-09-01T12:00:00+00:00', **extra}


def test_memories_from_the_named_time_are_recalled_without_shared_words():
    quilt = memory('quilt', 'Finished the blue quilt', stated_at='2026-10-05T09:00:00+00:00')
    exam = memory('exam', 'Passed the driving exam')
    concert = memory('concert', 'Saw a band together', applies_from='2026-10-05T19:00:00+00:00',
                     applies_until='2026-10-05T23:00:00+00:00')
    query = 'what did I tell you last Monday?'
    when = (time_recall.query_span(query, MONDAY, 'UTC'), 'UTC')
    assert context.recalled([quilt, exam, concert], [], query) == []
    assert sorted(item[0] for item in context.recalled([quilt, exam, concert], [], query, when=when)) == \
        ['concert', 'quilt']


def hit(identity, text, score):
    [chunk] = compile_chunks(f'message:{identity}', 'user', text)
    return Hit(chunk, score, ())


def test_near_repeats_wait_behind_different_items():
    hits = [hit('a', 'my cat knocked the plant over again', 3), hit('b', 'my cat knocked the plant over again!', 2),
            hit('c', 'work was long today', 1)]
    assert [item.chunk.source_id for item in time_recall.spread(hits, 3)] == ['message:a', 'message:c', 'message:b']
    assert [item.chunk.source_id for item in time_recall.spread(hits, 2)] == ['message:a', 'message:c']


def test_an_older_turn_comes_back_when_its_day_is_asked_about(client, connected, provider, clock):
    send(client, 'I finally finished the blue quilt', 'client-0000')
    clock.advance(timedelta(days=1))
    for index in range(1, 14):
        send(client, f'Small talk number {index}', f'client-{index:04d}')
    clock.advance(timedelta(days=6))
    send(client, 'What did I tell you last Monday?', 'client-0099')
    assert 'finished the blue quilt' in provider.requests[-1]['system']
