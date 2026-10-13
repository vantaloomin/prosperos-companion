"""Our history at a glance (companion/memory/history.py): a line a week lately, a month, then a year further back."""
from datetime import date, timedelta

from conftest import send

from companion.characters import require_current
from companion.memory import context, history

DAY_ONE = ['We finally went to the lighthouse at Cape Ann today',
           'The lighthouse keeper told us stories about shipwrecks and storms',
           'Afterwards we ate clam chowder by the harbour',
           'I want to go back to the lighthouse in spring']


def chat_day(client, prefix):
    for index, text in enumerate(DAY_ONE):
        send(client, text, f'{prefix}-{index:04d}')


def lines(client):
    response = client.get('/api/life/history')
    assert response.status_code == 200, response.text
    return response.json()['lines']


def system(app):
    database = app.state.database
    with database.connect() as connection:
        return context.build(connection, require_current(connection), database.clock.now(), 20_000)['system']


def test_weeks_lately_then_months_then_years_and_the_size_stays_fixed():
    today = date(2026, 10, 14)
    found = history.stretches(date(2026, 9, 10), today)
    assert [item.key for item in found] == ['w2026-09-07', 'w2026-09-14', 'w2026-09-21', 'w2026-09-28', 'w2026-10-05']
    assert found[0].start == date(2026, 9, 10), 'the first line starts at the first talk'
    assert history.stretches(date(2026, 10, 13), today) == [], 'nothing until a week is over'
    long = history.stretches(date(2019, 3, 2), today)
    kinds = [item.kind for item in long]
    assert kinds == sorted(kinds, key=['year', 'month', 'week'].index)
    assert kinds.count('month') == history.MONTHS_BACK and 12 <= kinds.count('week') <= 17
    assert all(earlier.end + timedelta(days=1) == later.start for earlier, later in zip(long, long[1:]))
    assert long[-1].end == date(2026, 10, 11), 'up to the end of last week'
    later = history.stretches(date(2019, 3, 2), date(2029, 10, 14))
    assert len(later) - len(long) == 3, 'only a line a year more, however long it runs'


def test_the_lines_come_from_what_happened_and_go_in_the_chat(client, app, connected, clock):
    chat_day(client, 'one')
    clock.advance(timedelta(days=1))
    assert client.post('/api/memory/consolidate').status_code == 200
    assert lines(client) == [], 'the week is not over yet'
    clock.advance(timedelta(days=21))
    send(client, 'Back again!', 'two-0001')
    found = lines(client)
    assert [line['key'] for line in found] == ['w2026-10-05', 'w2026-10-12']
    first, quiet = found
    assert first['text'].startswith('You talked on 1 day. You said “The lighthouse keeper told us stories')
    assert quiet['text'] == "You didn't talk." and quiet['label'] == '12 Oct to 25 Oct 2026', 'quiet weeks share one'
    prompt = system(app)
    assert '## Your history together' in prompt and history.INTRO in prompt
    assert '- Week of 5 Oct 2026: You talked on 1 day. The user said “The lighthouse keeper' in prompt
    assert prompt.index('## How close you two are') < prompt.index('## Your history together')


def test_the_user_corrects_a_line_or_leaves_it_out(client, app, connected, clock):
    chat_day(client, 'one')
    clock.advance(timedelta(days=8))
    send(client, 'Hello', 'two-0001')
    fixed = client.put('/api/life/history/w2026-10-05', json={'text': '  Our   first lighthouse trip. '}).json()
    assert fixed['lines'][0]['corrected'] == 'Our first lighthouse trip.'
    assert "- Week of 5 Oct 2026 (in the user's words): Our first lighthouse trip." in system(app)
    client.put('/api/life/history/w2026-10-05', json={'text': ''})
    assert 'Week of 5 Oct 2026' not in system(app)
    restored = client.delete('/api/life/history/w2026-10-05').json()
    assert restored['lines'][0]['corrected'] is None and 'Week of 5 Oct 2026: You talked' in system(app)
    assert client.put('/api/life/history/nonsense', json={'text': 'x'}).status_code == 404
    assert client.put('/api/life/history/w2026-10-05', json={'text': 'x' * 301}).status_code == 422


def test_a_corrected_week_comes_along_when_it_becomes_part_of_a_month(client, app, connected, clock):
    chat_day(client, 'one')
    clock.advance(timedelta(days=8))
    client.put('/api/life/history/w2026-10-05', json={'text': 'The lighthouse week.'})
    clock.advance(timedelta(weeks=20))
    send(client, 'Long time!', 'two-0001')
    [october] = [line for line in lines(client) if line['key'] == 'm2026-10']
    assert october['label'] == 'October 2026'
    assert october['text'].startswith('You talked on 1 day. In your words: “The lighthouse week.”')
    assert '- October 2026: You talked on 1 day. In the user’s words: “The lighthouse week.”' in system(app)


def test_a_line_never_runs_past_its_limit():
    item = history.Stretch('m2026-01', 'month', date(2026, 1, 1), date(2026, 1, 31), days=20,
                           said=[('2026-01-02', 'word ' * 60), ('2026-01-09', 'another ' * 40)],
                           moments=['Bowling together at Lucky Strike'] * 3, closer=['Close friends'])
    text = history.joined(history.parts(item, True, 'Mira'), history.LINE_LIMIT['month'])
    assert len(text) <= history.LINE_LIMIT['month'] and text.startswith('You talked on 20 days.')
