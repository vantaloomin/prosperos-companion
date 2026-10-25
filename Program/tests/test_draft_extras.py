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
    assert changed == [first['id'], second['id']]
    one, two = polished['places'][:2]
    assert one == {**first, 'name': 'The Harbor Memorial', 'summary': 'Bronze , and granite.'}
    assert two['name'] == second['name'] and len(two['summary']) == polish.SUMMARY_LIMIT
    assert [item['id'] for item in polished['places']] == [item['id'] for item in city['places']]
    assert polished['employers'] == city['employers']
    assert polish.apply(city, 'places', {'items': 'nope'}) == (city, [])


def test_polish_needs_a_text_model(client):
    assert client.get('/api/world/draft/polish').json() == {'ready': False}
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
    assert client.get('/api/world/draft/polish').json() == {'ready': True}
    assert body['changed'] == 1 and body['ids'] == [event['id']]
    assert body['definition']['annual_events'][0]['name'] == 'The Bramby Marathon'
    assert body['definition']['annual_events'][0]['months'] == event['months']
    assert event['id'] in provider.requests[-1]['messages'][-1]['content']
    assert client.post('/api/world/draft/check', json=body['definition']).json()['warnings'] == []


def test_a_world_map_opens_as_a_city_file_to_change_and_nothing_is_saved(client):
    before = client.get('/api/world/cities').json()
    response = client.post('/api/world/draft/marinara', json=sample())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['definition']['neighborhoods'] and body['definition']['places']
    assert any('Settings > Life & cities' in note for note in body['notes'])
    assert not any('editor' in note for note in body['notes'])
    # The app picks the weather itself (Mild when nothing in the map says otherwise) and says so.
    assert body['definition']['climate']['months'] and 'Weather set to Mild; change it on Overview.' in body['notes']
    assert not any('neighbourhood' in note for note in body['notes'])
    warnings = client.post('/api/world/draft/check', json=body['definition']).json()['warnings']
    assert not any('weather' in warning for warning in warnings)
    assert body['definition']['climate']['source'] in body['definition']['sources']
    assert client.post('/api/world/draft/check', json=body['definition']).json()['notes'] == []
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


def test_rows_the_user_changed_are_not_polished(client, provider):
    connect(client)
    city = built()
    mine, other = city['places'][:2]
    provider.respond = lambda system, messages: [Chunk(json.dumps({'items': [
        {'id': place['id'], 'name': 'Polished ' + place['name'], 'summary': place['summary']} for place in city['places']]})),
        Chunk('', 'stop')]
    body = client.post('/api/world/draft/polish', json={'definition': city, 'section': 'places', 'keep': [mine['id']]}).json()
    assert json.dumps(mine['id']) not in ''.join(request['messages'][-1]['content'] for request in provider.requests)
    assert body['definition']['places'][0] == mine and mine['id'] not in body['ids']
    assert body['definition']['places'][1]['name'] == 'Polished ' + other['name'] and other['id'] in body['ids']


def test_the_weather_choices_are_the_drawn_climates(client):
    found = client.get('/api/world/draft/weather').json()
    assert [item['name'] for item in found] == ['Mild', 'Cold', 'Dry', 'Tropical', 'Warm', 'Mountains']
    assert all(len(item['climate']['months']) == 12 for item in found)
    city, name = draft.weather_for({'name': 'Frostholm', 'summary': 'A snowy harbor.', 'era': 'modern'})
    assert name == 'Cold' and city['climate']['summary'].startswith('Long hard winters')
    assert draft.weather_for({'name': 'Dry Gulch', 'era': 'frontier'})[1] == 'Dry'
    assert draft.weather_for({'name': 'Hollow', 'era': 'frontier'})[1] == 'Dry'
    assert draft.weather_for({'name': 'Hollow', 'era': 'fantasy'})[1] == 'Mild'


def test_an_unusable_polish_reply_is_said_plainly(client, provider):
    connect(client)
    provider.respond = replying('Sorry, I cannot do that.', 'Still no.')
    response = client.post('/api/world/draft/polish', json={'definition': built(), 'section': 'events'})
    assert response.status_code == 502 and response.json()['detail'] == polish.UNUSABLE
