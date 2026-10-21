"""Words that fit the era (Hit List #82, companion/world/era_words.py)."""
from companion import notifications
from companion.world import catalog, era_words


def live_in(client, city_id: str):
    with client.app.state.database.connect(write=True) as connection:
        connection.execute('UPDATE persona SET home_city_id=? WHERE id=1', (city_id,))


def test_every_era_has_every_word_and_each_era_picks_its_group():
    table = era_words.table()
    modern = set(table['words']['modern'])
    for group, found in table['words'].items():
        assert set(found) == modern, group
        assert all(value.strip() for value in found.values()), group
    groups = {city['id']: era_words.group(city) for city in catalog.cities().values()}
    assert groups['baltimore'] == 'modern' and groups['london-1895'] == groups['new-york-1925'] == 'historical'
    assert groups['camelot'] == groups['emerald-city'] == groups['grandport'] == 'fantasy'
    assert groups['long-meridian'] == groups['port-vesper'] == 'future'
    assert era_words.group(None) == 'modern'


def test_a_city_renames_words_over_its_era_and_period_words_can_be_off():
    camelot = catalog.cities()['camelot']
    assert era_words.say(era_words.words(camelot), 'message_to', name='Gwen') == 'Write a letter to Gwen'
    assert era_words.say(era_words.words(camelot), 'call_on', name='Gwen') == 'Speaking with Gwen in the scrying glass'
    assert era_words.words(catalog.cities()['london-1895'])['sent_you'] == '{name} sent a note round.'
    assert era_words.words(catalog.cities()['whitlock'])['messages_tab'] == 'Letters'
    assert era_words.words(catalog.cities()['long-meridian'])['messages'] == 'comms'
    assert era_words.words(camelot, on=False) == era_words.table()['words']['modern']
    # Every built-in city's own words are words the app has, each keeping the name it needs.
    for city in catalog.cities().values():
        assert era_words.clean(dict(city)) == [], city['id']


def test_a_city_files_unknown_or_broken_words_are_dropped_with_a_note_and_the_city_still_loads():
    raw = {key: value for key, value in catalog.cities()['camelot'].items() if key not in ('data_version', 'builtin',
                                                                                             'origin')}
    raw['words'] = {'message': 'scroll', 'spaceship': 'longboat', 'message_to': 'Write', 'posts': ''}
    data = catalog.prepare(raw, mend=True)
    assert data['words'] == {'message': 'scroll'}
    assert len(data['import_notes']) == 3 and 'spaceship' in data['import_notes'][0]
    raw['words'] = 'letters please'
    data = catalog.prepare(raw, mend=True)
    assert 'words' not in data and data['import_notes'] == [
        'Dropped the words block: it needs to map each word to what this city calls it.']
    # A city without the block keeps the same data_version it had before words existed.
    raw.pop('words')
    assert 'words' not in catalog.prepare(raw)


def test_the_words_follow_where_the_user_lives_and_the_appearance_switch(client, companion):
    found = client.get('/api/world/words').json()
    assert found['group'] == 'modern' and found['words']['messages_tab'] == 'Messages' and found['on'] is True
    live_in(client, 'camelot')
    found = client.get('/api/world/words').json()
    assert found['group'] == 'fantasy' and found['words']['dating_tab'] == 'Matchmaker'
    assert client.get('/api/settings').json()['period_words'] is True
    assert client.put('/api/settings', json={'period_words': False}).json()['period_words'] is False
    found = client.get('/api/world/words').json()
    assert found == {'group': 'modern', 'on': False, 'words': era_words.table()['words']['modern']}


def test_a_notification_says_letter_in_camelot():
    config = {'preview': 'name'}
    words = era_words.words(catalog.cities()['camelot'])
    assert notifications.message_notice(config, 'Gwen', [{'text': 'hi'}], words)['body'] == 'Gwen sent you a letter.'
    both = notifications.message_notice(config, 'Gwen', [{'text': 'a', 'name': 'Gwen'}, {'text': 'b', 'name': 'Bors'}],
                                        words)
    assert both['body'] == '2 new letters from Gwen and Bors.'
    assert notifications.message_notice(config, 'Sam', [{'text': 'hi'}])['body'] == 'Sam sent you a message.'
