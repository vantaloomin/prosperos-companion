def test_companion_defaults_to_friendship(companion):
    assert companion['version']['relationship'] == 'friendship'
    assert companion['version']['number'] == 1
    assert companion['active_timeline_id']


def test_one_focal_companion_per_workspace(client, companion):
    assert client.post('/api/companion', json={'name': 'Other'}).status_code == 409


def test_revision_creates_a_version_and_rejects_stale_edits(client, companion):
    definition = {**companion['version']['definition'], 'personality': 'Dry humour'}
    body = {'definition': definition, 'note': 'Sharper wit', 'expected_version_id': companion['active_version_id']}
    revised = client.post('/api/companion/versions', json=body)
    assert revised.status_code == 200
    assert revised.json()['version']['number'] == 2
    assert client.post('/api/companion/versions', json=body).status_code == 409
    assert [item['number'] for item in client.get('/api/companion/versions').json()] == [1, 2]


def test_unknown_timezone_is_rejected(client):
    assert client.post('/api/companion', json={'name': 'Mira', 'timezone': 'Mars/Olympus'}).status_code == 422


def test_a_companion_made_without_a_name_gets_one_from_their_city(client):
    made = client.post('/api/companion', json={'home_city': 'baltimore', 'identity': 'She runs a bakery.'})
    assert made.status_code == 200, made.text
    name = made.json()['version']['name']
    assert len(name.split()) >= 2 and made.json()['version']['definition']['name'] == name


def test_a_revision_still_needs_a_name(client, companion):
    definition = {**companion['version']['definition'], 'name': ' '}
    body = {'definition': definition, 'expected_version_id': companion['active_version_id']}
    assert client.post('/api/companion/versions', json=body).status_code == 422
