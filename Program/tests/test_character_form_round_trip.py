"""The Character page sends back the definition it was given, life chapters and all (companion/characters.py)."""


def test_a_definition_with_what_chapters_add_saves_without_keeping_it(client, companion):
    version = client.get('/api/companion').json()['companion']['version']
    added = {'near': '', 'business': {'label': 'Owner, Crumb & Co', 'short': 'bakery', 'business': 'bakery'},
             'health': {'condition': 'mild asthma', 'short': 'Asthma', 'avoid': None, 'checkup': 'Inhaler review'}}
    response = client.post('/api/companion/versions', json={
        'definition': {**version['definition'], **added, 'keeps_age': True}, 'expected_version_id': version['id']})
    assert response.status_code == 200, response.text
    saved = client.get('/api/companion').json()['companion']['version']['definition']
    assert saved['keeps_age'] is True and not set(added) & set(saved)
