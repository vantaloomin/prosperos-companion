"""The dating app: townsfolk dating details by rule, the user's profile, swipes, matches becoming companions and
dates in Story mode (companion/world/dating.py, companion/dating.py)."""
from collections import Counter
from datetime import date

from conftest import Chunk, send
from test_drafting import connect
from test_social_circle import make

from companion import dating as app
from companion.world import changes, dating, townsfolk

PROFILE = {'name': 'Sam', 'age': 30, 'gender': 'man', 'interested_in': ['woman'], 'looking_for': 'serious',
           'age_min': 22, 'age_max': 40, 'bio': ''}


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def everyone(city: str) -> tuple[dict, list[dict]]:
    data = changes.resolve(city, []) | {'kin': [], 'town': ''}
    people = [sheet for place in data['places'] for sheet in townsfolk.at_place(data, place['id'])]
    people += [sheet for hood in data['neighborhoods'] for sheet in townsfolk.residents(data, hood['id'])]
    # With the neighbors who only turn up on the app.
    people += [townsfolk.find(data, f"town:{city}:~{hood['id']}:{townsfolk.resident_count(data, hood['id']) + n}")
               for hood in data['neighborhoods'] for n in range(0, townsfolk.APP_MEMBERS, 25)]
    return data, people


def test_townsfolk_dating_details_are_seeded_adult_and_at_realistic_rates():
    data, people = everyone('baltimore')
    found = [dating.details(sheet, data) for sheet in people]
    assert found == [dating.details(sheet, data) for sheet in people]  # The same every time.
    orientation = Counter(item['orientation'] for item in found if item['gender'] != 'nonbinary')
    binary = sum(orientation.values())
    assert orientation['straight'] / binary > 0.85 and 0.02 < (binary - orientation['straight']) / binary < 0.12
    status = Counter(item['status'] for item in found)
    assert 0.3 < status['married'] / len(found) < 0.6 and status['single'] > status['seeing someone']
    # Only single people are on the app, and nobody would date anyone under 18.
    assert all(item['looking'] == 'no' for item in found if item['status'] in ('married', 'seeing someone'))
    assert all(sheet['age'] >= 18 and item['age_range'][0] >= 18 for sheet, item in zip(people, found, strict=True))
    looking = Counter(item['looking'] for item in found)
    assert looking['no'] > looking['serious'] > looking['friends'] > 0
    card = dating.card(people[0], data, date(2026, 10, 7))
    assert card['name'] == people[0]['name'] and people[0]['full'].split()[-1] not in card['bio']
    assert '"' in card['looks'] and card['bio'] and not card['notice']


def test_older_eras_have_a_personal_column_with_initials():
    data, people = everyone('london-1895')
    sheet = next(sheet for sheet in people if dating.details(sheet, data)['looking'] == 'serious')
    card = dating.card(sheet, data, date(1895, 10, 7))
    assert card['notice'].endswith('.') and 'Box' in card['notice'] and sheet['full'] not in card['notice']
    assert 'with a view to matrimony' in card['notice']
    assert app.surface(data) == 'column'
    assert app.surface(changes.resolve('camelot', [])) == 'matchmaker'
    assert all(not item['looks']['style'].startswith(('streetwear', 'athleisure'))
               for item in (dating.details(sheet, data) for sheet in people[:200]))


def test_the_deck_shows_only_single_compatible_adults_and_likes_need_a_yes_back(client, clock):
    assert ok(client.get('/api/dating'))['profile'] is None
    assert ok(client.get('/api/dating/status')) == {'installed': False, 'name': 'Matchlight'}
    assert client.put('/api/dating/profile', json=PROFILE | {'age': 17}).status_code == 422
    assert client.put('/api/dating/profile', json=PROFILE | {'age_min': 16}).status_code == 422
    opened = ok(client.put('/api/dating/profile', json=PROFILE))
    assert opened['surface'] == 'app' and opened['city']['name'] == 'Baltimore' and opened['remaining'] > 20
    data = changes.resolve('baltimore', []) | {'kin': [], 'town': ''}
    for card in opened['deck']:
        sheet = townsfolk.find(data, card['key'])
        found = dating.details(sheet, data)
        assert found['gender'] == 'woman' and 'man' in found['drawn_to'] and found['status'] in ('single', 'widowed')
        assert 22 <= sheet['age'] <= 40 and found['age_range'][0] <= 30 <= found['age_range'][1]
        assert sheet['full'] not in str(card)

    # Swipe through until there is a match and a like that was not returned.
    state, matched, unreturned = opened, None, 0
    while (not matched or not unreturned) and state['deck']:
        key = state['deck'][0]['key']
        state = ok(client.post('/api/dating/swipes', json={'key': key, 'like': True}))
        if state['matched']:
            matched = matched or state['matched']
        else:
            unreturned += 1
        assert key not in [card['key'] for card in state['deck']]
    assert matched and unreturned and any(item['key'] == matched['key'] for item in state['matches'])
    assert client.post('/api/dating/swipes', json={'key': matched['key'], 'like': True}).status_code == 409
    # Their rules say yes or no the same way for the same user.
    sheet = townsfolk.find(data, matched['key'])
    mine = {**PROFILE, 'seed': ok_seed(client)}
    assert dating.says_yes(sheet, dating.details(sheet, data), mine)

    passed = state['deck'][0]['key']
    state = ok(client.post('/api/dating/swipes', json={'key': passed, 'like': False}))
    assert passed not in [card['key'] for card in state['deck']] and not state['matched']
    again = ok(client.delete('/api/dating/swipes/passed'))
    assert again['remaining'] == state['remaining'] + 1

    moved = ok(client.put('/api/dating/city', json={'city_id': 'new-york'}))
    assert moved['city']['name'] == 'New York' and all(card['key'].startswith('town:new-york:') for card in moved['deck'])
    assert client.put('/api/dating/city', json={'city_id': 'atlantis'}).status_code == 404

    assert ok(client.get('/api/dating/status'))['installed'] is True
    removed = ok(client.delete('/api/dating/profile'))
    assert removed['profile'] is None and removed['matches'] == []
    assert ok(client.get('/api/dating/status'))['installed'] is False


def ok_seed(client) -> str:
    with client.app.state.database.connect() as connection:
        return app.profile(connection)['seed']


def match_someone(client, profile=PROFILE) -> dict:
    state = ok(client.put('/api/dating/profile', json=profile))
    while state['deck']:
        state = ok(client.post('/api/dating/swipes', json={'key': state['deck'][0]['key'], 'like': True}))
        if state['matched']:
            return state['matched']
    raise AssertionError('Nobody liked the user back.')


def test_a_match_becomes_a_companion_even_as_the_first_one(client, clock, provider):
    match = match_someone(client)
    draft = ok(client.get('/api/companion/cast/draft', params={'key': match['key']}))
    assert draft['matched'] is True and draft['stepping_back'] is None
    definition = draft['definition']
    assert definition['relationship'] == 'romance' and 'Matched with the user through a dating app' in definition['background']
    assert definition['home_city'] == 'baltimore'
    companion = ok(client.post('/api/companion/cast/switch', json={'key': match['key'], 'definition': definition}))
    assert companion['version']['name'] == definition['name'] and companion['townsfolk_key'] == match['key']
    shown = ok(client.get('/api/dating'))
    assert shown['matches'][0]['companion_id'] == companion['id']
    assert match['key'] not in [card['key'] for card in shown['deck']]
    assert client.get('/api/companion/cast/draft', params={'key': match['key']}).status_code == 409

    # They are chatted with like any companion, and never hear about the app.
    connect(client)
    send(client, 'Hi!', 'client-0001')
    assert 'swipe' not in provider.requests[-1]['system'].lower()


def test_a_friends_match_stays_a_friend_and_a_new_match_steps_the_main_character_back(client, clock):
    make(client, 'Warm and curious.')
    match = match_someone(client, PROFILE | {'looking_for': 'friends', 'interested_in': ['woman', 'man', 'nonbinary']})
    draft = ok(client.get('/api/companion/cast/draft', params={'key': match['key']}))
    assert draft['definition']['relationship'] == 'friendship' and draft['stepping_back'] == 'Mira'
    ok(client.post('/api/companion/cast/switch', json={'key': match['key'], 'definition': draft['definition']}))
    members = ok(client.get('/api/companion/cast'))['members']
    assert [member['main'] for member in members] == [True, False] and members[1]['name'] == 'Mira'


def test_a_match_can_be_met_on_a_date_in_story_mode(client, clock, provider):
    connect(client)
    match = match_someone(client)
    place = next(item for item in ok(client.get('/api/dating'))['matches'][0]['places'])
    # Only with Story mode switched on.
    assert ok(client.get('/api/dating'))['story'] is False
    assert client.post('/api/dating/dates', json={'key': match['key'], 'place_id': place['id']}).status_code == 409
    ok(client.put('/api/settings', json={'story_mode': True}))
    assert client.post('/api/dating/dates', json={'key': match['key'], 'place_id': 'nowhere'}).status_code == 404
    told = ok(client.post('/api/dating/dates', json={'key': match['key'], 'place_id': place['id']}))
    assert told['scene']['place']['id'] == place['id']
    assert told['messages'][-1]['text'] == f"You meet {match['name']} at {place['name']} for your date."
    assert f"your date, {match['name']}" in told['scene']['around']
    assert ok(client.get('/api/dating'))['date']['key'] == match['key']
    # The date joins the user's people-met list.
    assert any(person['key'] == match['key'] for person in ok(client.get('/api/story'))['people'])

    provider.replies = [[Chunk('They wave you over.'), Chunk('', 'stop')]]
    ok(client.post('/api/story/messages', json={'text': 'I look for my date.', 'client_id': 'story-0001'}))
    system = provider.requests[-1]['system']
    assert 'On a date with the user (Sam)' in system and match['name'] in system

    ended = ok(client.delete('/api/dating/dates/current'))
    assert ended['messages'][-1]['text'] == f"Your date with {match['name']} is over."
    assert ok(client.get('/api/dating'))['date'] is None
    assert client.delete('/api/dating/dates/current').status_code == 409
    # Going somewhere else ends a date too.
    ok(client.post('/api/dating/dates', json={'key': match['key'], 'place_id': place['id']}))
    ok(client.put('/api/story/scene', json={'city_id': 'new-york'}))
    assert ok(client.get('/api/dating'))['date'] is None
