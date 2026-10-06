"""The configured model drafts a character from a short idea; the app checks and shapes what comes back."""
import json
import re

from conftest import send

from companion import drafting
from companion.providers.chat import Chunk

GOOD = {
    'name': 'Dana Whitfield', 'career': 'registered-nurse',
    'identity': '34, a night-shift nurse who shares a rowhouse with her brother.',
    'personality': 'Steady at work, scattered at home.', 'voice': 'Short texts, lowercase, dry.',
    'skills': ['Starts an IV on the first try', 'Parallel parks a van', 'Starts an IV on the first try'],
    'flaws': ['Forgets to reply for days', 'Gets prickly when she is wrong'],
    'interests': ['crosswords', 'minor league baseball'], 'background': 'Grew up outside the city.',
    'appearance': 'Short, sturdy, scrubs or a hoodie.', 'location': 'Somewhere invented',
    'routine': 'I sleep till two.', 'life_themes': ['her brother', 'the night shift'],
    'schedule': [{'label': 'Night shift', 'kind': 'work', 'days': [0, 2, 4], 'start': '19:00', 'end': '07:00',
                  'themes': ['patients']},
                 {'label': 'Asleep', 'kind': 'sleep', 'days': [0, 1, 2, 3, 4, 5, 6], 'start': '08:00', 'end': '14:00'},
                 {'label': 'Broken', 'kind': 'nap', 'days': [9], 'start': '25:00', 'end': '01:00'}],
    'emotional_traits': [{'name': 'Jealousy', 'intensity': 'strong', 'note': 'sulks'}],
    'absence_reaction': 'Guilt-trips you.',
}


def replying(*replies):
    queue = list(replies)

    def respond(system, messages):
        return [Chunk(queue.pop(0)), Chunk('', 'stop')]
    return respond


def connect(client):
    response = client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model'})
    assert response.status_code == 200, response.text


def test_drafting_needs_a_connected_model(client):
    response = client.post('/api/companion/draft', json={'idea': 'a nurse'})
    assert response.status_code == 409 and response.json()['code'] == 'no_connection'


def test_a_draft_is_shaped_to_the_definition_and_the_users_picks(client, provider):
    connect(client)
    provider.respond = replying('Sure! ```json\n' + json.dumps(GOOD) + '\n```')
    response = client.post('/api/companion/draft', json={'idea': 'a tired nurse', 'home_city': 'baltimore',
                                                          'relationship': 'mentor', 'timezone': 'UTC'})
    assert response.status_code == 200, response.text
    result = response.json()
    definition = result['definition']
    assert definition['name'] == 'Dana Whitfield'
    assert definition['skills'] == ['Starts an IV on the first try', 'Parallel parks a van']
    assert definition['flaws'][0] == 'Forgets to reply for days'
    # The world and the relationship are the user's, never the model's.
    assert definition['home_city'] == 'baltimore' and definition['timezone'] == 'America/New_York'
    assert definition['location'] == 'Baltimore, Maryland' and definition['relationship'] == 'mentor'
    assert [block['label'] for block in definition['schedule']] == ['Night shift', 'Asleep']
    # Emotional traits stay off unless asked for.
    assert definition['emotional_traits'] == [] and definition['absence_reaction'] == ''
    assert result['career']['id'] == 'registered-nurse'
    [request] = provider.requests
    assert request['config']['max_output_tokens'] >= drafting.DRAFT_TOKENS
    assert 'registered-nurse' in request['system'] and 'Baltimore' in request['system']
    assert '{{' not in request['system']


def test_asking_for_emotional_edges_lets_the_model_add_them(client, provider):
    connect(client)
    provider.respond = replying(json.dumps(GOOD))
    definition = client.post('/api/companion/draft', json={'idea': 'a jealous ex'}).json()['definition']
    assert definition['emotional_traits'] == [{'name': 'Jealousy', 'intensity': 'strong', 'note': 'sulks'}]
    assert definition['absence_reaction'] == 'Guilt-trips you.'


def test_a_named_character_keeps_the_users_name(client, provider):
    connect(client)
    provider.respond = replying(json.dumps(GOOD))
    assert client.post('/api/companion/draft', json={'name': 'Rosa'}).json()['definition']['name'] == 'Rosa'


def test_an_unusable_draft_is_retried_once_with_the_problem(client, provider):
    connect(client)
    provider.respond = replying('<think>{"plan": 1}</think> I could not decide.', json.dumps(GOOD))
    response = client.post('/api/companion/draft', json={'idea': 'someone'})
    assert response.status_code == 200, response.text
    retry = provider.requests[1]['messages']
    assert retry[-1]['role'] == 'user' and 'could not be used' in retry[-1]['content']


def test_a_second_failure_sends_the_user_to_the_form(client, provider):
    connect(client)
    provider.respond = replying('{"name": "Dana"}', 'still nothing')
    response = client.post('/api/companion/draft', json={'idea': 'someone'})
    assert response.status_code == 502 and response.json()['code'] == 'draft_unusable'
    assert len(provider.requests) == 2


def test_a_missing_schedule_falls_back_to_the_careers_own_week(client, provider):
    connect(client)
    empty = json.dumps({**GOOD, 'schedule': [], 'life_themes': []})
    provider.respond = replying(empty, empty)
    definition = client.post('/api/companion/draft', json={'home_city': 'baltimore'}).json()['definition']
    kinds = {block['kind'] for block in definition['schedule']}
    assert {'work', 'sleep'} <= kinds and 'patients' in definition['life_themes']


def test_a_week_without_sleep_every_day_is_retried_then_replaced(client, provider):
    connect(client)
    sleepless = {**GOOD, 'schedule': [GOOD['schedule'][0], {**GOOD['schedule'][1], 'days': [1, 3]}]}
    provider.respond = replying(json.dumps(sleepless), json.dumps(sleepless))
    definition = client.post('/api/companion/draft', json={'home_city': 'baltimore'}).json()['definition']
    assert 'sleep blocks that cover every day' in provider.requests[1]['messages'][-1]['content']
    sleep = {day for block in definition['schedule'] if block['kind'] == 'sleep' for day in block['days']}
    assert sleep == set(range(7))


def test_one_field_can_be_redone_in_keeping_with_the_rest(client, provider):
    connect(client)
    provider.respond = replying('{"value": ["Overpromises, then cancels", "Holds grudges"]}')
    character = {'name': 'Dana', 'identity': 'A nurse.', 'flaws': ['Cares too much'], 'home_city': 'nowhere'}
    response = client.post('/api/companion/draft/field', json={'definition': character, 'field': 'flaws',
                                                                'request': 'harsher'})
    assert response.status_code == 200, response.text
    assert response.json()['value'] == ['Overpromises, then cancels', 'Holds grudges']
    system = provider.requests[0]['system']
    assert '"flaws"' in system and 'harsher' in system and 'Cares too much' in system and '{{' not in system


def test_skills_and_flaws_reach_the_chat_context(client, provider, connected):
    current = client.get('/api/companion').json()['companion']
    definition = {**current['version']['definition'], 'skills': ['Fixes bikes'], 'flaws': ['Runs late']}
    client.post('/api/companion/versions', json={'definition': definition,
                                                  'expected_version_id': current['active_version_id']})
    send(client, 'Hello there', 'draft-0001')
    system = provider.requests[-1]['system']
    assert 'Skills: Fixes bikes' in system and 'Runs late' in system


def test_every_template_placeholder_is_filled():
    filled = {'character-draft.md': {'rules', 'picks', 'city', 'careers', 'names', 'emotional'},
              'character-field.md': {'rules', 'character', 'city', 'emotional', 'field', 'field_guide', 'request',
                                     'field_shape'},
              'character-repair.md': {'problem'}}
    for name, keys in filled.items():
        assert set(re.findall(r'\{\{(\w+)\}\}', drafting.template(name))) == keys, name
    assert set(drafting.field_guides()) == {'identity', 'personality', 'voice', 'skills', 'flaws', 'interests',
                                            'background', 'appearance', 'routine', 'life_themes', 'schedule'}


def test_prompts_can_be_reworded_in_settings_and_reset(client, provider):
    listed = client.get('/api/prompts').json()
    assert [item['name'] for item in listed] == list(drafting.EDITABLE)
    rules = next(item for item in listed if item['name'] == 'character-rules.md')
    assert not rules['customized'] and rules['text'] == rules['default'] and rules['placeholders'] == []
    saved = client.put('/api/prompts/character-rules.md', json={'text': 'Make them a retired sailor.'}).json()
    assert saved['customized']
    connect(client)
    provider.respond = replying(json.dumps(GOOD))
    client.post('/api/companion/draft', json={'idea': 'someone'})
    assert 'Make them a retired sailor.' in provider.requests[0]['system']
    assert 'none of the names chatbots overuse' not in provider.requests[0]['system']
    reset = client.delete('/api/prompts/character-rules.md').json()
    assert not reset['customized'] and 'none of the names chatbots overuse' in reset['text']


def test_a_reworded_prompt_must_keep_its_placeholders(client):
    response = client.put('/api/prompts/character-draft.md', json={'text': 'Draft someone. {{rules}}'})
    assert response.status_code == 422 and '{{picks}}' in response.json()['detail']
    assert client.put('/api/prompts/notes.md', json={'text': 'x'}).status_code == 404


def test_names_that_read_as_invented_are_retried_then_swapped(client, provider):
    connect(client)
    invented = {**GOOD, 'name': 'Elara Voss', 'background': 'Her sister Lyra still calls Elara every Sunday.'}
    provider.respond = replying(json.dumps(invented), json.dumps(invented))
    definition = client.post('/api/companion/draft', json={'idea': 'a nurse', 'age': 'thirties'}).json()['definition']
    retry = provider.requests[1]['messages'][-1]['content']
    assert 'Elara' in retry and 'Voss' in retry and 'made up' in retry
    first, last = definition['name'].split(' ', 1)
    assert 'Elara' not in definition['name'] and 'Voss' not in definition['name']
    assert f'calls {first} every Sunday' in definition['background'] and 'Lyra' not in definition['background']
    # The quick start offers names people in their thirties really have, from the city's data.
    assert 'commonly have where they live' in provider.requests[0]['system']


def test_a_name_the_user_chose_is_never_treated_as_invented(client, provider):
    connect(client)
    provider.respond = replying(json.dumps({**GOOD, 'name': 'Elara Voss'}))
    definition = client.post('/api/companion/draft', json={'idea': 'a nurse', 'name': 'Elara Voss'}).json()['definition']
    assert definition['name'] == 'Elara Voss' and len(provider.requests) == 1


def test_a_redone_field_cannot_bring_in_invented_names(client, provider):
    connect(client)
    provider.respond = replying(json.dumps({'value': 'Raised by her aunt Seraphina.'}),
                                json.dumps({'value': 'Raised by her aunt Seraphina.'}))
    response = client.post('/api/companion/draft/field', json={'field': 'background', 'definition': GOOD})
    assert response.status_code == 200, response.text
    assert 'Seraphina' not in response.json()['value'] and len(provider.requests) == 2


def test_quick_start_ages_are_read_from_the_pick():
    assert [drafting.age_value(text) for text in ('', 'twenties', 'thirties', '34', 'sixty or older')] == \
        [None, 25, 35, 34, 65]
