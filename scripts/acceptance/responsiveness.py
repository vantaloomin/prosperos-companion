"""Responsiveness acceptance run (docs/product-requirements.md, "Acceptance and measurement").

Seeds a workspace with a long relationship (10,000 messages, 1,000+ committed life events and
1,000 feed posts) and times the UI and the endpoints it uses. Model first-token and image times
are excluded: replies come from a stand-in model server.

    python scripts/acceptance/responsiveness.py seed --url http://127.0.0.1:8781 --db <data dir>/companion.sqlite3
    python scripts/acceptance/responsiveness.py backend --url http://127.0.0.1:8781
    python scripts/acceptance/responsiveness.py ui --url http://127.0.0.1:8781 --chromium /opt/pw-browsers/chromium

Seeding uses only the standard library and writes rows the way the app does: complete user/reply
turns with one active reply each, committed events (a few corrected into a second revision), and
posts that reference those events. `ui` needs Playwright for Python, and a model that streams
slowly enough (about 0.1 s a word) that Stop lands while the reply is still being written.
Every figure is in milliseconds; P95 is nearest-rank over the samples (30 by default).
"""
import argparse
import json
import random
import sqlite3
import statistics
import time
import urllib.request
from datetime import UTC, datetime, timedelta
from uuid import uuid4

HEADERS = {'Content-Type': 'application/json', 'X-Companion-Client': 'workspace'}
TURNS = 5000
EVENT_POSTS = 950
DIGESTS, DIGEST_SIZE = 50, 5
CORRECTED = 25
MEMORIES = 150
SEARCH_WORD = 'lighthouse'
RARE_WORD = 'midsummer'  # In every 250th user turn, so search results reach back through history.

TOPICS = ['work', 'the garden', 'your sister', 'the new apartment', 'running', 'that book', 'the rain',
          'dinner plans', 'the weekend', 'your cough', 'the concert', 'coffee', 'the train strike', 'music']
OPENERS = ['Honestly,', 'So', 'Okay,', 'Hey,', 'Well,', 'You know,', 'Funny thing:', 'Guess what,']
FILLER = ['it was a long day', 'I kept thinking about what you said', 'nothing went to plan', 'the light was lovely',
          'I finally slept properly', 'I burned the rice again', 'the bus was late twice', 'we laughed for ages',
          'I am a bit tired but happy', 'there was a {word} on the postcard', 'I walked past the {word} again']
KINDS = ['routine', 'ordinary', 'ordinary', 'ordinary', 'plan', 'thread']
MOODS = ['content', 'tired', 'cheerful', 'restless', 'calm', 'proud']
LAYERS = ['user_fact', 'shared_experience', 'plan', 'relationship', 'companion_life']


def call(url, path, body=None, method=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url + '/api' + path, data=data, headers=HEADERS,
                                     method=method or ('GET' if body is None else 'POST'))
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read() or b'{}')


def stamp(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec='microseconds')


def sentence(rng: random.Random) -> str:
    words = [rng.choice(OPENERS), rng.choice(FILLER).format(word=SEARCH_WORD if rng.random() < 0.3 else 'cafe')]
    words += [f'and then {rng.choice(FILLER).format(word="harbour")}' for _ in range(rng.randint(0, 3))]
    return ' '.join(words) + f'. What about {rng.choice(TOPICS)}?'


def ensure_companion(url, model_url):
    current = call(url, '/companion').get('companion')
    if current is None:
        current = call(url, '/companion', {'name': 'Mira', 'personality': 'Warm and curious',
                                           'timezone': 'Europe/Lisbon'})
    call(url, '/connection', {'base_url': model_url, 'model': 'stand-in'}, 'PUT')
    return current


def seed_memories(url, rng):
    for index in range(MEMORIES):
        layer = rng.choice(LAYERS)
        body = {'layer': layer, 'subject': f'{rng.choice(TOPICS).title()} note {index}',
                'value': sentence(rng), 'reality': 'fiction' if layer == 'companion_life' else 'real'}
        if layer == 'plan':
            body['plan_status'] = 'agreed'
        call(url, '/memories', body)


def seed_messages(connection, companion, start, rng):
    timeline, version = companion['active_timeline_id'], companion['active_version_id']
    seq = connection.execute('SELECT COALESCE(MAX(seq), 0) FROM messages WHERE timeline_id=?', (timeline,)).fetchone()[0]
    rows, moment = [], start
    receipt = json.dumps({'budget_tokens': 15200, 'estimated_tokens': 900, 'included': {}, 'omitted': {}})
    for _turn in range(TURNS):
        moment += timedelta(minutes=rng.randint(5, 180))
        user_id, reply_id = uuid4().hex, uuid4().hex
        text = sentence(rng) + (f' Remember the {RARE_WORD} lantern walk?' if _turn % 250 == 0 else '')
        rows.append((user_id, timeline, seq + 1, 'user', text, uuid4().hex, None, 'complete', 1, version,
                     None, None, stamp(moment), stamp(moment)))
        later = moment + timedelta(seconds=rng.randint(4, 40))
        reply = ' '.join(sentence(rng) for _ in range(rng.randint(1, 3)))
        rows.append((reply_id, timeline, seq + 2, 'companion', reply, None, user_id, 'complete', 1, version, 0,
                     receipt, stamp(moment), stamp(later)))
        seq += 2
    connection.executemany(
        'INSERT INTO messages (id, timeline_id, seq, role, text, client_id, reply_to, status, active, '
        'character_version_id, memory_revision, receipt, created_at, completed_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', rows)


def insert_event(connection, companion, moment, rng, revision=1, supersedes=None, status='committed'):
    event_id, kind = uuid4().hex, rng.choice(KINDS)
    details = {'post': sentence(rng), 'mood': rng.choice(MOODS), 'label': rng.choice(TOPICS)}
    if kind == 'thread':
        details |= {'state': rng.choice(['open', 'settled']), 'thread_key': f'thread-{rng.randint(1, 60)}'}
    ends = moment + timedelta(minutes=rng.randint(20, 120))
    connection.execute(
        'INSERT INTO life_events (id, companion_id, timeline_id, idempotency_key, kind, status, summary, details, '
        'starts_at, ends_at, character_version_id, permission_revision, revision, supersedes_id, created_at, '
        'decided_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)',
        (event_id, companion['id'], companion['active_timeline_id'], f'seed:{event_id}', kind, status,
         f'Mira spent time on {rng.choice(TOPICS)}', json.dumps(details), stamp(moment), stamp(ends),
         companion['active_version_id'], revision, supersedes, stamp(ends), stamp(ends)))
    return event_id, ends


def insert_post(connection, timeline, kind, event_ids, occurs, rng):
    post_id = uuid4().hex
    read_at = None if rng.random() < 0.05 else stamp(occurs + timedelta(hours=2))
    connection.execute(
        'INSERT INTO feed_posts (id, timeline_id, kind, idempotency_key, intro, occurs_at, created_at, read_at, '
        'reaction) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (post_id, timeline, kind, f'seed-post:{post_id}', 'While you were away:' if kind == 'digest' else '',
         stamp(occurs), stamp(occurs), read_at, rng.choice([None, None, 'heart', 'laugh'])))
    connection.executemany('INSERT INTO feed_post_events (post_id, event_id, position) VALUES (?, ?, ?)',
                           [(post_id, event_id, index) for index, event_id in enumerate(event_ids)])


def seed_life(connection, companion, start, rng):
    timeline, moment = companion['active_timeline_id'], start
    singles, corrected = [], 0
    for _index in range(EVENT_POSTS):
        moment += timedelta(hours=rng.randint(4, 12))
        event_id, ends = insert_event(connection, companion, moment, rng)
        if corrected < CORRECTED and rng.random() < 0.05:
            connection.execute("UPDATE life_events SET status='superseded' WHERE id=?", (event_id,))
            insert_event(connection, companion, moment, rng, revision=2, supersedes=event_id)
            corrected += 1
        singles.append((event_id, ends))
    for event_id, ends in singles:
        insert_post(connection, timeline, 'event', [event_id], ends, rng)
    for _digest in range(DIGESTS):
        moment += timedelta(hours=rng.randint(6, 30))
        ids = [insert_event(connection, companion, moment + timedelta(hours=hour), rng)[0] for hour in range(DIGEST_SIZE)]
        insert_post(connection, timeline, 'digest', ids, moment + timedelta(hours=DIGEST_SIZE + 1), rng)


def seed(args):
    rng = random.Random(7)
    companion = ensure_companion(args.url, args.model_url)
    seed_memories(args.url, rng)
    start = datetime.now(UTC) - timedelta(days=400)
    connection = sqlite3.connect(args.db, timeout=30, isolation_level=None)
    connection.execute('BEGIN IMMEDIATE')
    seed_messages(connection, companion, start, rng)
    seed_life(connection, companion, start, rng)
    connection.execute('COMMIT')
    counts = {table: connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]  # noqa: S608 - fixed names.
              for table in ('messages', 'life_events', 'feed_posts', 'memories')}
    print(json.dumps(counts))


def summary(samples: list[float]) -> dict:
    """Nearest-rank percentiles in milliseconds; a probe that timed out reports -1 and is counted apart."""
    ordered = sorted(sample for sample in samples if sample >= 0)
    p95 = ordered[min(len(ordered) - 1, round(0.95 * (len(ordered) - 1)))]
    return {'n': len(ordered), 'p50': round(statistics.median(ordered), 1), 'p95': round(p95, 1),
            'max': round(ordered[-1], 1), 'timeouts': len(samples) - len(ordered)}


def timed(fn, count) -> list[float]:
    samples = []
    for _ in range(count):
        began = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - began) * 1000)
    return samples


def backend(args):
    url, results = args.url, {}
    oldest = call(url, '/conversation?limit=100')['messages'][0]['seq']
    feed = call(url, '/feed?limit=20&hidden=false')
    probes = {
        'GET /conversation?limit=100': lambda: call(url, '/conversation?limit=100'),
        'GET /conversation (older page)': lambda: call(url, f'/conversation?limit=100&before_seq={oldest}'),
        'GET /conversation (jump page 500)': lambda: call(url, '/conversation?limit=500&before_seq=3000'),
        'GET /conversation/search (common)': lambda: call(url, f'/conversation/search?q={SEARCH_WORD}'),
        'GET /conversation/search (rare)': lambda: call(url, '/conversation/search?q=zzqx'),
        'GET /feed?limit=20': lambda: call(url, '/feed?limit=20&hidden=false'),
        'GET /feed (next page)': lambda: call(url, f"/feed?limit=20&hidden=false&before={feed['next_before']}"),
        'GET /today': lambda: call(url, '/today'),
        'GET /memories': lambda: call(url, '/memories?history=false'),
        'GET /context/preview': lambda: call(url, '/context/preview'),
        'POST /life/prepare': lambda: call(url, '/life/prepare', {}),
    }
    for name, probe in probes.items():
        probe()
        results[name] = summary(timed(probe, args.samples))
        print(name, results[name], flush=True)
    sends, stops = [], []
    for _ in range(args.samples):
        began = time.perf_counter()
        result = call(url, '/conversation/messages?wait=false', {'text': 'Timing check, please ignore.',
                                                                  'client_id': uuid4().hex})
        sends.append((time.perf_counter() - began) * 1000)
        began = time.perf_counter()
        call(url, f"/conversation/replies/{result['reply']['id']}/stop", {})
        stops.append((time.perf_counter() - began) * 1000)
        time.sleep(0.3)  # Let the stopped reply settle before the next turn.
    for name, values in (('POST /conversation/messages?wait=false', sends),
                         ('POST /conversation/replies/{id}/stop', stops)):
        results[name] = summary(values)
        print(name, results[name], flush=True)
    return results


# Browser timing: each probe starts the clock in the page right before the click and stops it when
# the expected element is in the DOM, so Playwright's own round trips are not counted.
WAIT_FOR = """async ([selector, clickSelector, minCount, timeout]) => {
  const count = () => document.querySelectorAll(selector).length
  const began = performance.now()
  document.querySelector(clickSelector).click()
  while (count() < minCount) {
    if (performance.now() - began > timeout) return -1
    await new Promise((resolve) => requestAnimationFrame(resolve))
  }
  return performance.now() - began
}"""


# Type the query the way React sees typing, then wait for results in the page (Playwright's own
# polling backs off to 500 ms steps, which would swamp the measurement).
TYPE_SEARCH = """async (query) => {
  const input = document.querySelector('#conversation-search')
  const began = performance.now()
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, query)
  input.dispatchEvent(new Event('input', { bubbles: true }))
  while (!document.querySelector('.search-results li')) {
    if (performance.now() - began > 20000) return -1
    await new Promise((resolve) => requestAnimationFrame(resolve))
  }
  return performance.now() - began
}"""


def ui_probe(page, selector, click_selector, min_count=1, timeout=20000):
    return page.evaluate(WAIT_FOR, [selector, click_selector, min_count, timeout])


def nav(label):
    return f'nav.app-nav button:nth-child({["Chat", "Today", "Feed", "Memories"].index(label) + 1})'


def ui(args):
    from playwright.sync_api import sync_playwright  # noqa: PLC0415 - only this command needs a browser.
    results = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.chromium)
        page = browser.new_page(viewport={'width': 1280, 'height': 900})
        page.goto(args.url + '/#today')
        page.wait_for_selector('h1')
        sections = {'navigation': navigation, 'chat': chat, 'search': search, 'feed': feed_pages}
        for key in args.only.split(','):
            section = sections[key]
            found = section(page, args)
            for name, value in found.items():
                print(name, value, flush=True)
            results |= found
        browser.close()
    return results


def navigation(page, args) -> dict:
    samples = {key: [] for key in ('Open Chat (cold, full history)', 'Switch to Feed (cold)',
                                   'Switch to Today (cold)', 'Switch to Memories (cold)', 'Switch to Chat (warm)',
                                   'Switch to Feed (warm)', 'Switch to Today (warm)', 'Switch to Memories (warm)')}
    targets = {'Chat': ('article.message', 100), 'Feed': ('article.post', 1), 'Today': ('.today-section', 1),
               'Memories': ('.memory-subject', 1)}
    for index in range(args.samples):
        for label, (selector, count) in targets.items():
            page.goto(f'{args.url}/?fresh={index}{label}#settings')  # A new document: nothing cached.
            page.wait_for_selector('h1')
            key = 'Open Chat (cold, full history)' if label == 'Chat' else f'Switch to {label} (cold)'
            samples[key].append(ui_probe(page, selector, nav(label), count))
        for label, (selector, count) in [*targets.items()][1:] + [('Chat', targets['Chat'])]:
            page.click(nav('Today') if label != 'Today' else nav('Chat'))
            page.wait_for_timeout(50)
            samples[f'Switch to {label} (warm)'].append(ui_probe(page, selector, nav(label), count))
    return {key: summary(values) for key, values in samples.items()}


SEND = """async (text) => { const began = performance.now()
  document.querySelector('form.composer button[type=submit]').click()
  while (![...document.querySelectorAll('article.message-user')].some((node) => node.textContent.includes(text))) {
    if (performance.now() - began > 20000) return -1
    await new Promise((resolve) => requestAnimationFrame(resolve)) }
  return performance.now() - began }"""
# Times the Stop request itself and the moment the composer offers Send again.
STOP = """async () => { const began = performance.now()
  const response = new Promise((resolve) => { const original = window.fetch
    window.fetch = async (...args) => { const result = await original(...args)
      if (String(args[0]).includes('/stop')) { resolve(performance.now() - began); window.fetch = original }
      return result } })
  document.querySelector('form.composer button.button:not(.primary)').click()
  const posted = await response
  while (!document.querySelector('form.composer button[type=submit]')) {
    if (performance.now() - began > 20000) return [posted, -1]
    await new Promise((resolve) => requestAnimationFrame(resolve)) }
  return [posted, performance.now() - began] }"""


def send_and_stop(page, count, label='') -> dict:
    """Send, then Stop the reply while it streams. Needs a model slow enough to still be writing after 0.3 s."""
    samples = {f'Send: own message shown{label}': [], f'Stop: POST answered{label}': [],
               f'Stop: UI shows stopped{label}': []}
    for _ in range(count):
        text = f'Timing message {uuid4().hex[:8]}'
        page.fill('#composer-text', text)
        samples[f'Send: own message shown{label}'].append(page.evaluate(SEND, text))
        page.wait_for_selector('form.composer button:has-text("Stop")', timeout=10000)
        page.wait_for_timeout(300)
        posted, shown = page.evaluate(STOP)
        samples[f'Stop: POST answered{label}'].append(posted)
        samples[f'Stop: UI shows stopped{label}'].append(shown)
    return samples


def chat(page, args) -> dict:
    page.goto(args.url + '/#conversation')
    page.wait_for_selector('article.message')
    samples = send_and_stop(page, args.samples)
    earlier = samples['Show earlier messages (100)'] = []
    for _ in range(args.samples):
        before = page.locator('article.message').count()
        earlier.append(ui_probe(page, 'article.message', 'button.load-earlier', before + 100))
    # Again with the older pages still loaded, so every streamed piece of text meets a long transcript.
    samples |= send_and_stop(page, args.samples, f' ({page.locator("article.message").count():,} loaded)')
    return {key: summary(values) for key, values in samples.items() if values}


def search(page, args) -> dict:
    samples = {'Search: results shown': [], 'Search: jump to result': []}
    page.goto(f'{args.url}/?search=start#conversation')
    page.wait_for_selector('article.message')
    for index in range(args.samples):
        page.click('button[aria-label*="Search"], button[aria-label*="search"]')
        page.wait_for_selector('#conversation-search')
        query = [SEARCH_WORD, RARE_WORD, 'harbour', 'the rain', 'sister', 'concert'][index % 6]
        samples['Search: results shown'].append(page.evaluate(TYPE_SEARCH, query) - 250)  # Less the typing pause.
        # The middle result: for the rare word that is about 5,000 messages back.
        middle = page.locator('.search-results li').count() // 2 + 1
        samples['Search: jump to result'].append(ui_probe(page, 'article.message.found',
                                                          f'.search-results li:nth-child({middle}) button'))
        page.goto(f'{args.url}/?search={index}#conversation')
        page.wait_for_selector('article.message')
    return {key: summary(values) for key, values in samples.items()}


def feed_pages(page, args) -> dict:
    samples = []
    page.goto(args.url + '/#feed')
    page.wait_for_selector('article.post')
    for _ in range(args.samples):
        before = page.locator('article.post').count()
        samples.append(ui_probe(page, 'article.post', 'button.load-more', before + 20))
    return {'Feed: show older posts (20)': summary(samples)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['seed', 'backend', 'ui'])
    parser.add_argument('--url', default='http://127.0.0.1:8781')
    parser.add_argument('--db', help='companion.sqlite3 in the data directory (seed only)')
    parser.add_argument('--model-url', default='http://127.0.0.1:1234/v1',
                        help='an OpenAI-compatible stand-in model that streams slowly enough (about 0.1 s a word) to be stopped')
    parser.add_argument('--chromium', default=None)
    parser.add_argument('--samples', type=int, default=30)
    parser.add_argument('--only', default='navigation,chat,search,feed', help='ui sections to run')
    parser.add_argument('--out', help='also write the results as JSON here')
    args = parser.parse_args()
    result = {'seed': seed, 'backend': backend, 'ui': ui}[args.command](args)
    if args.out and result:
        with open(args.out, 'w', encoding='utf-8') as handle:
            json.dump(result, handle, indent=2)


if __name__ == '__main__':
    main()
