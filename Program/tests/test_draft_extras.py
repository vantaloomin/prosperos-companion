"""Prospero's Draft Table, step 3: model polish (companion/world/draft/polish.py), opening a Marinara world map,
and nearby places of the same world."""
import json

from test_drafting import connect, replying

from companion.providers.chat import Chunk
from companion.world import draft
from companion.world.draft import polish
from tests.test_marinara_world import sample

LINE = 'a cold fishing town on a northern coast, 1920s'


def built():
    return draft.build(LINE, 'polish')['city']


def test_the_prompt_names_the_place_its_era_and_every_item_with_where_it_is():
    city = built()
    text = polish.prompt(city, 'places', LINE)
    assert city['name'] in text and 'the 1920s' in text and LINE in text
    hoods = {hood['id']: hood['name'] for hood in city['neighborhoods']}
    for place in city['places']:
        shown = json.loads(polish.item_line(place, hoods))
        assert shown['id'] == place['id'] and shown['kind'] == place['kind'] and shown['where'] == hoods[place['neighborhood']]
        assert json.dumps(place['id']) in text
    assert 'decks' not in text
    ship = draft.build('a generation ship, far future', 'polish')['city']
    assert 'its neighborhoods are decks' in polish.prompt(ship, 'hoods')


def test_polish_changes_only_names_and_summaries_of_items_it_was_given():
    city = built()
    first, second = city['places'][:2]
    reply = {'items': [{'id': first['id'], 'name': '  The Harbor Memorial ', 'summary': 'Bronze — and granite.', 'kind': 'bar'},
                       {'id': second['id'], 'name': '', 'summary': 'x' * 900},
                       {'id': 'made-up', 'name': 'Nowhere', 'summary': 'Not here.'}, 'junk']}
    polished, changed = polish.apply(city, 'places', reply)
    assert changed == 2
    one, two = polished['places'][:2]
    assert one == {**first, 'name': 'The Harbor Memorial', 'summary': 'Bronze , and granite.'}
    assert two['name'] == second['name'] and len(two['summary']) == polish.SUMMARY_LIMIT
    assert [item['id'] for item in polished['places']] == [item['id'] for item in city['places']]
    assert polished['employers'] == city['employers']
    assert polish.apply(city, 'places', {'items': 'nope'}) == (city, 0)


def test_polish_needs_a_text_model(client):
    response = client.post('/api/world/draft/polish', json={'definition': built(), 'section': 'places'})
    assert response.status_code == 409 and 'Settings > Models' in response.json()['detail']
    assert client.post('/api/world/draft/polish', json={'definition': built(), 'section': 'name'}).status_code == 422


def test_polish_asks_the_model_and_the_place_still_loads(client, provider):
    connect(client)
    city = built()
    event = city['annual_events'][0]
    provider.respond = replying(json.dumps({'items': [{'id': event['id'], 'name': 'The Bramby Marathon', 'summary': 'Couples dance for days.'}]}))
    response = client.post('/api/world/draft/polish', json={'definition': city, 'section': 'events', 'line': LINE})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['changed'] == 1 and body['definition']['annual_events'][0]['name'] == 'The Bramby Marathon'
    assert body['definition']['annual_events'][0]['months'] == event['months']
    assert event['id'] in provider.requests[-1]['messages'][-1]['content']
    assert client.post('/api/world/draft/check', json=body['definition']).json()['warnings'] == []


def test_a_world_map_opens_as_a_city_file_to_change_and_nothing_is_saved(client):
    before = client.get('/api/world/cities').json()
    response = client.post('/api/world/draft/marinara', json=sample())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['definition']['neighborhoods'] and body['definition']['places']
    assert any('Settings > Cities' in note for note in body['notes'])
    assert client.get('/api/world/cities').json() == before
    assert client.post('/api/world/draft/marinara', json={'name': 'not a map'}).status_code == 422


def test_a_nearby_place_is_saved_with_the_city(client):
    city = {**built(), 'neighbours': [{'city': 'pellmouth', 'hours': 3, 'by': 'ferry'}]}
    assert client.post('/api/world/draft/check', json=city).json()['warnings'] == []
    saved = client.post('/api/world/cities', json=city)
    assert saved.status_code == 200, saved.text
    kept = client.get(f'/api/world/cities/{city["id"]}').json()['neighbours']
    assert [{key: item[key] for key in ('city', 'hours', 'by')} for item in kept] == city['neighbours']


def test_a_long_list_goes_to_the_model_in_parts(client, provider):
    connect(client)
    city = built()
    places = city['places']
    provider.respond = lambda system, messages: [Chunk(json.dumps({'items': [
        {'id': place['id'], 'name': place['name'].upper(), 'summary': place['summary']}
        for place in places if json.dumps(place['id']) in messages[-1]['content']]})), Chunk('', 'stop')]
    body = client.post('/api/world/draft/polish', json={'definition': city, 'section': 'places'}).json()
    assert len(provider.requests) == -(-len(places) // polish.CHUNK) > 1
    assert body['changed'] == len(places)
    assert all(place['name'] == place['name'].upper() for place in body['definition']['places'])
