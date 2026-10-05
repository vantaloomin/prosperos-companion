"""The chat style is a saved presentation choice; it never touches permissions or memory."""


def test_chat_style_defaults_to_feed_and_saves(client):
    settings = client.get('/api/settings').json()
    assert (settings['chat_style'], settings['chat_sounds']) == ('feed', False)
    saved = client.put('/api/settings', json={'chat_style': 'retro', 'chat_sounds': True})
    assert saved.status_code == 200, saved.text
    assert (saved.json()['chat_style'], saved.json()['chat_sounds']) == ('retro', True)
    assert saved.json()['permission_revision'] == settings['permission_revision']
    assert client.get('/api/settings').json()['chat_style'] == 'retro'


def test_unknown_chat_style_is_refused(client):
    assert client.put('/api/settings', json={'chat_style': 'neon'}).status_code == 422
