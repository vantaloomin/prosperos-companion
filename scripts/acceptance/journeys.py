"""Cross-feature acceptance journeys against a running app (docs/acceptance-status.md).

Start the stand-ins and the app on a fresh workspace first:

    python scripts/acceptance/standins.py --log requests.jsonl
    COMPANION_DATA_DIR=<empty dir> COMPANION_API_KEY=k python scripts/acceptance/serve.py
    python scripts/acceptance/journeys.py --log requests.jsonl

Each journey prints PASS or FAIL with what it saw. The model and ComfyUI are stand-ins, so this
checks how features meet (what reaches the model, what the feed shows, what time does), not
reply quality, image identity or reference-hardware timing.
"""
import argparse
import json
import threading
import time

import httpx

APP = 'http://127.0.0.1:8775'
MODEL = 'http://127.0.0.1:1234'
COMFY = 'http://127.0.0.1:8188'
RESULTS = []


class Run:
    def __init__(self, log):
        self.log = log
        self.http = httpx.Client(base_url=APP, headers={'x-companion-client': 'workspace'}, timeout=60)
        self.sent = 0

    def call(self, method, path, **kwargs):
        response = self.http.request(method, path, **kwargs)
        if response.status_code >= 400:
            raise AssertionError(f'{method} {path}: {response.status_code} {response.text[:300]}')
        return response.json() if response.content else None

    def send(self, text, wait=True):
        self.sent += 1
        query = '' if wait else '?wait=false'
        return self.call('POST', f'/api/conversation/messages{query}', json={'text': text, 'client_id': f'journey-{self.sent:06d}'})

    def clock(self, hours):
        return self.call('POST', '/acceptance/clock', json={'hours': hours})

    def requests(self, since=0):
        with open(self.log, encoding='utf-8') as handle:
            lines = handle.readlines()[since:]
        return [json.loads(line) for line in lines]

    def mark(self):
        with open(self.log, encoding='utf-8') as handle:
            return sum(1 for _ in handle)

    def last_chat(self):
        chats = [item['body'] for item in self.requests() if item['kind'] == 'chat'
                 and 'Rephrase one ordinary moment' not in item['body']['messages'][0]['content']]
        return json.dumps(chats[-1]) if chats else ''

    def delay(self, seconds):
        httpx.post(f'{MODEL}/control', json={'delay': seconds})


def check(name, condition, seen):
    RESULTS.append((name, bool(condition)))
    print(f"{'PASS' if condition else 'FAIL'}  {name}: {seen}")


def setup(run):
    run.call('POST', '/api/companion', json={'name': 'Mira', 'personality': 'Warm and curious',
                                              'timezone': 'America/New_York', 'home_city': 'baltimore'})
    run.call('PUT', '/api/connection', json={'base_url': f'{MODEL}/v1', 'model': 'stand-in',
                                              'embedding_model': 'stand-in-embed'})
    run.call('PUT', '/api/settings', json={'automatic_memory': True, 'user_timezone': 'America/New_York'})
    run.send('My name is Sam and I live in Chicago. I work as a nurse.')
    time.sleep(2)


def coherence(run):
    """One event through post, image, conversation and correction (chat and feed coherence)."""
    run.clock(20)
    run.call('POST', '/api/life/reconcile', json={'mode': 'return'})
    proposed = [event for event in run.call('GET', '/api/events', params={'history': 'true'})
                if event['status'] == 'proposed' and (event['details'].get('place') or {}).get('name')]
    event = run.call('POST', f"/api/events/{proposed[0]['id']}/commit")
    place = event['details']['place']['name']
    post = run.call('GET', '/api/feed')['posts'][0]
    run.call('POST', '/api/images/backends', json={'kind': 'comfyui', 'base_url': COMFY, 'enabled': True})
    job = run.call('POST', '/api/images/jobs', json={'post_id': post['id']})
    for _ in range(30):
        if run.call('GET', f"/api/images/jobs/{job['id']}")['status'] == 'completed':
            break
        time.sleep(0.5)
    run.call('POST', f"/api/feed/{post['id']}/discuss", json={'text': 'Where was that?', 'client_id': 'journey-discuss-1'})
    check('chat knows the post being discussed', place in run.last_chat(), place)
    corrected = run.call('POST', f"/api/events/{event['id']}/correct",
                         json={'summary': 'Mira read at the library instead.', 'details': event['details']})
    shown = run.call('GET', f"/api/feed/{post['id']}")
    check('feed shows the corrected revision', shown['events'][0]['revision'] == corrected['revision'], shown['events'][0]['summary'])
    check('old picture is marked outdated', shown['image']['outdated'], shown['image'])
    preview = run.call('POST', '/api/images/preview', json={'post_id': post['id']})
    check('a new image prompt drops the corrected-away place', place not in preview['prompt'], preview['prompt'])
    run.call('POST', f"/api/feed/{post['id']}/discuss", json={'text': 'Where again?', 'client_id': 'journey-discuss-2'})
    system = json.loads(run.last_chat())['messages'][0]['content']
    check('chat uses only the corrected account', 'library' in system and place not in system, 'system prompt')
    history = run.call('GET', '/api/events', params={'history': 'true'})
    statuses = {item['id']: item['status'] for item in history}
    check('the earlier version is kept as history', statuses[event['id']] == 'superseded', statuses[event['id']])


def correction_in_flight(run):
    """A memory correction while a reply is being written (immediate correction)."""
    work = next(memory for memory in run.call('GET', '/api/memories') if memory['subject'] == 'Work')
    run.delay(0.3)
    reply = run.send('Tell me a long story about my job.', wait=False)['reply']
    time.sleep(1)
    run.call('POST', f"/api/memories/{work['id']}/correct", json={'value': 'paramedic', 'expected_revision': work['revision']})
    for _ in range(60):
        messages = run.call('GET', '/api/conversation')['messages']
        status = next(message['status'] for message in messages if message['id'] == reply['id'])
        if status != 'streaming':
            break
        time.sleep(0.5)
    run.delay(0.01)
    check('the in-flight reply is withheld', status == 'withheld', status)
    run.send('And now?')
    system = json.loads(run.last_chat())['messages'][0]['content']
    check('the next reply uses the new revision', 'Work: paramedic' in system and 'Work: nurse' not in system, 'system prompt')


def forgetting(run):
    """Excluded and deleted facts never reach the model, including through the companion's replies."""
    fish = run.send('I love zebrafish aquariums.')['message']
    colour = run.send('My favourite color is ultramarine.')['message']
    time.sleep(2)
    memories = run.call('GET', '/api/memories')
    for memory in memories:
        if fish['id'] in memory['source_message_ids']:
            run.call('POST', f"/api/memories/{memory['id']}/exclude")
        if colour['id'] in memory['source_message_ids']:
            run.call('POST', f"/api/memories/{memory['id']}/delete", json={'delete_sources': True})
    start = run.mark()
    run.send('Which fish and colour do I like?')
    run.call('POST', '/api/memory/run')
    run.call('POST', '/api/memory/consolidate')
    time.sleep(2)
    leaks = [item['kind'] for item in run.requests(start)
             if 'zebrafish' in json.dumps(item['body']) or 'ultramarine' in json.dumps(item['body'])]
    check('no excluded or deleted words in any later model request', not leaks, leaks or 'none')


def time_reconciliation(run):
    def events():
        listing = run.call('GET', '/api/events', params={'history': 'true'})
        return len(listing), len({item['idempotency_key'] for item in listing})
    before = events()
    run.clock(-30)
    state = run.call('POST', '/api/life/reconcile', json={'mode': 'return'})['state']
    check('a clock moved back replays nothing', state == 'clock_behind' and events() == before, state)
    run.clock(30.5 + 336)
    result = run.call('POST', '/api/life/reconcile', json={'mode': 'return'})
    count, unique = events()
    check('14 days away is capped and unique', len(result['run']['results']) <= 3 and count == unique,
          f"{len(result['run']['results'])} slots, {count} events")
    check('a second reconcile is not due', run.call('POST', '/api/life/reconcile', json={'mode': 'return'})['state'] == 'not_due', '')


def shared_compute(run):
    """Message acceptance while prepared wording is written at background priority."""
    run.delay(0.3)
    timings = []
    for _ in range(4):
        time.sleep(4)
        worker = threading.Thread(target=lambda: run.call('POST', '/api/life/prepare', json={}))
        worker.start()
        time.sleep(0.8)
        started = time.perf_counter()
        run.send('Quick question', wait=False)
        timings.append(round((time.perf_counter() - started) * 1000))
        worker.join()
    run.delay(0.01)
    check('acceptance stays under 200 ms during background phrasing', max(timings) < 200, f'{timings} ms')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--log', required=True)
    parser.add_argument('--app', default=APP)
    parser.add_argument('--model', default=MODEL)
    parser.add_argument('--comfy', default=COMFY)
    arguments = parser.parse_args()
    globals().update(APP=arguments.app, MODEL=arguments.model, COMFY=arguments.comfy)
    run = Run(arguments.log)
    setup(run)
    for journey in (coherence, correction_in_flight, forgetting, shared_compute, time_reconciliation):
        try:
            journey(run)
        except AssertionError as error:
            check(journey.__name__, False, error)
    failed = [name for name, passed in RESULTS if not passed]
    print(f'{len(RESULTS) - len(failed)} passed, {len(failed)} failed')
    raise SystemExit(1 if failed else 0)


if __name__ == '__main__':
    main()
