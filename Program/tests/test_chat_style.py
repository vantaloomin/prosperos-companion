"""The chat style is a saved presentation choice; it never touches permissions or memory."""


def test_chat_style_defaults_to_feed_and_saves(client):
    settings = client.get('/api/settings').json()
    assert (settings['chat_style'], settings['chat_sounds']) == ('feed', False)
    saved = client.put('/api/settings', json={'chat_style': 'retro', 'chat_sounds': True})
    assert saved.status_code == 200, saved.text
    assert (saved.json()['chat_style'], saved.json()['chat_sounds']) == ('retro', True)
    assert saved.json()['permission_revision'] == settings['permission_revision']
    assert client.get('/api/settings').json()['chat_style'] == 'retro'


def test_retro_dark_mode_is_off_until_turned_on(client):
    assert client.get('/api/settings').json()['chat_retro_dark'] is False
    saved = client.put('/api/settings', json={'chat_retro_dark': True})
    assert saved.status_code == 200, saved.text
    assert client.get('/api/settings').json()['chat_retro_dark'] is True


def test_unknown_chat_style_is_refused(client):
    assert client.put('/api/settings', json={'chat_style': 'neon'}).status_code == 422


def test_color_scheme_is_ink_until_another_is_picked(client):
    settings = client.get('/api/settings').json()
    assert (settings['color_scheme'], settings['custom_palette']) == ('ink', None)
    assert client.put('/api/settings', json={'color_scheme': 'moss'}).json()['color_scheme'] == 'moss'
    palette = {'accent': '#c5a46d', 'background': '#101010', 'surface': '#202020', 'text': '#f0f0f0'}
    saved = client.put('/api/settings', json={'color_scheme': 'custom', 'custom_palette': palette})
    assert saved.status_code == 200, saved.text
    assert client.get('/api/settings').json()['custom_palette'] == palette
    assert saved.json()['permission_revision'] == settings['permission_revision']


def test_unknown_scheme_or_bad_color_is_refused(client):
    assert client.put('/api/settings', json={'color_scheme': 'neon'}).status_code == 422
    bad = {'accent': 'red', 'background': '#101010', 'surface': '#202020', 'text': '#f0f0f0'}
    assert client.put('/api/settings', json={'custom_palette': bad}).status_code == 422
