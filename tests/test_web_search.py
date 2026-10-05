"""Web search lookups (PRD X1-X3): asked for in chat, sending only what was asked, against the stand-in server."""
import sys
from pathlib import Path

import pytest

from companion.mcp import lookups
from companion.mcp.services import PRESETS, infer_arguments

STANDIN = str(Path(__file__).with_name('mcp_standin.py'))


@pytest.mark.parametrize('text, topic', [
    ('Can you google the best crab cakes in Fells Point?', 'the best crab cakes in Fells Point'),
    ('search reddit for opinions on the new bridge', 'opinions on the new bridge on Reddit'),
    ('Hey. Search twitter for the Ravens trade rumors!', 'the Ravens trade rumors on X (Twitter)'),
    ('please search the web for chess openings for beginners', 'chess openings for beginners'),
    ('Could you look up what time the market opens?', 'what time the market opens'),
    ('I work at Google now.', None),
    ('We should look up at the stars tonight.', None),
    ('my research for the paper', None),
    ('search https://example.com/page', None),
])
def test_search_requests(text, topic):
    assert lookups.search_topic(text) == topic


def test_a_search_tool_gets_the_request_in_every_field_that_takes_it():
    schema = {'properties': {'objective': {'type': 'string'}, 'search_queries': {'type': 'array'},
                             'session_id': {'type': 'string'}, 'location': {'type': 'string'}},
              'required': ['objective', 'search_queries']}
    arguments, missing = infer_arguments('web_search', schema)
    assert (arguments, missing) == ({'objective': {'source': 'topic'}, 'search_queries': {'source': 'topic'}}, [])
    mapping = {'tool': 'web_search', 'arguments': '{"objective": {"source": "topic"}, '
                                                  '"search_queries": {"source": "topic"}}'}
    where = {'place': 'Towson, MD', 'latitude': None, 'longitude': None, 'date': '2026-10-05'}
    sent = lookups.arguments_for(mapping, [{'name': 'web_search', 'input_schema': schema}], where, 'bridge news')
    assert sent == {'objective': 'bridge news', 'search_queries': ['bridge news']}


def test_presets_are_keyless_hosted_services(client, companion):
    created = client.post('/api/context/services/preset', json={'preset': 'parallel'})
    assert created.status_code == 200, created.text
    assert (created.json()['transport'], created.json()['url'], created.json()['has_key']) == (
        'http', PRESETS['parallel']['url'], False)
    assert client.post('/api/context/services/preset', json={'preset': 'parallel'}).status_code == 409
    assert client.post('/api/context/services/preset', json={'preset': 'bing'}).status_code == 422
    assert {spec['url'] for spec in PRESETS.values()} == {
        'https://search.parallel.ai/mcp', 'https://mcp.exa.ai/mcp', 'https://mcp.firecrawl.dev/v2/mcp'}


def test_searching_from_chat_sends_only_the_request(client, connected, provider):
    client.put('/api/context/location', json={'user_place': 'Towson, MD'})
    created = client.post('/api/context/services', json={'name': 'Searcher', 'transport': 'stdio',
                                                          'command': [sys.executable, STANDIN]}).json()
    service = client.post(f"/api/context/services/{created['id']}/check").json()
    suggestion = service['suggestions']['web_search']
    assert suggestion['tool'] == 'web_search'
    path = f"/api/context/services/{created['id']}/tools/web_search"
    leaky = client.put(path, json={'tool': 'web_search', 'arguments': {**suggestion['arguments'],
                                                                       'session_id': {'source': 'place'}},
                                   'run_in': ['conversation']})
    assert leaky.status_code == 422
    saved = client.put(path, json={'tool': 'web_search', 'arguments': suggestion['arguments'],
                                   'run_in': ['conversation']}).json()
    disclosure = next(item for item in saved['mappings'] if item['category'] == 'web_search')['disclosure']
    assert 'It runs when you ask in chat to search or look something up, with what you asked for.' in \
        disclosure['summary']
    client.post(f'{path}/enable', json={'digest': disclosure['digest']})
    sent = client.post('/api/conversation/messages', json={'text': 'Can you search reddit for bridge opinions?',
                                                           'client_id': 'client-search-1'}).json()
    [observation] = client.get(f"/api/context/messages/{sent['message']['id']}/observations").json()['observations']
    assert observation['arguments'] == {'objective': 'bridge opinions on Reddit',
                                        'search_queries': ['bridge opinions on Reddit']}
    assert observation['location']['label'] == 'bridge opinions on Reddit'
    system = provider.requests[-1]['system']
    assert '- Web search for bridge opinions on Reddit from Searcher, tool web_search' in system
    assert 'Most people like the new bridge, per r/baltimore.' in system
    assert 'Towson' not in observation['content']


def test_a_failed_search_is_never_invented():
    failed = {'id': 'o1', 'category': 'web_search', 'status': 'failed', 'location': {'label': 'chess openings'},
              'error': 'HTTP 429', 'service_name': 'Exa', 'tool': 'web_search_exa'}
    [(_, line)] = lookups.context_lines([failed], None, 'America/New_York')
    assert line == ('- The web search for chess openings did not work, so you have seen no results: do not invent '
                    'any. Say, in character, that you could not look it up just now, and carry on.')
