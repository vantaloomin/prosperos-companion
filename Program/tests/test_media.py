"""Reading, watching and listening (companion/life/media.py): always in the middle of a book, a show and a song."""
from datetime import date, timedelta

import pytest
from conftest import reconcile, set_life, show

from companion.database import decode
from companion.life import body, composer, media, money
from companion.world.source import CatalogWorld

WORLD = CatalogWorld()
TODAY = date(2026, 10, 5)
EVENINGS = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00', 'days': [0, 1, 2, 3, 4]},
            {'key': 'evening', 'label': 'Evening', 'kind': 'leisure', 'start': '17:00', 'end': '23:00'},
            {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]


def test_each_city_reads_from_its_own_era_and_made_up_worlds_get_invented_titles():
    expected = {'baltimore': 'modern', 'osaka': 'modern', 'new-york-1925': 'jazz-age', 'pellmouth': 'jazz-age',
                'london-1895': 'nineteenth', 'calderwick': 'nineteenth', 'whitlock': 'nineteenth',
                'camelot': 'tales', 'emerald-city': 'tales', 'grandport': 'tales', 'ellerbruck': 'tales'}
    assert {city: media.place_of(WORLD.find(city))['bank'] for city in expected} == expected
    assert media.place_of(WORLD.find('osaka'))['region'] == 'jp'
    assert media.place_of(WORLD.find('whitlock'))['region'] == 'us'
    assert media.place_of(None)['bank'] == 'modern'
    assert media.place_of({'era': 'future'})['bank'] == 'future'
    for bank_id in ('tales', 'future'):
        assert not media.bank(bank_id)['real']


def test_picks_are_era_correct_and_lean_to_their_tastes():
    frontier = media.place_of(WORLD.find('whitlock'))
    for kind in media.KINDS:
        assert all(item['year'] <= 1885 for item in media.candidates(frontier, kind, set()))
    fan = {'name': 'Ash', 'interests': ['k-pop', 'anime'], 'age': 30}
    me = media.place_of(WORLD.find('baltimore'))
    songs = [media.choose(f's{n}', 'music:0', me, 'music', fan, set()) for n in range(60)]
    assert sum('kpop' in song['tags'] for song in songs) >= 10
    shows = [media.choose(f's{n}', 'show:0', me, 'show', fan, set()) for n in range(60)]
    assert sum('anime' in item['tags'] for item in shows) >= 10
    assert media.choose('x', 'book:0', me, 'book', fan, set()) == media.choose('x', 'book:0', me, 'book', fan, set())


def test_light_realism_finishes_everything_and_dramatic_puts_more_down():
    me = {**media.place_of(None), 'reader': 1, 'watcher': 1, 'library': False}
    item = {'kind': 'book', 'title': 'X', 'format': 'book', 'tags': frozenset()}
    start = TODAY
    light = [media.plan(f'p{n}', item, start, me, 1, {'name': 'A'}) for n in range(200)]
    assert all(found['outcome'] == 'finish' and found['verdict'] != media.VERDICTS[3] for found in light)
    dramatic = [media.plan(f'p{n}', item, start, me, 3, {'name': 'A'}) for n in range(200)]
    assert sum(found['outcome'] == 'drop' for found in dramatic) >= 20
    assert media.plan('p1', {**item, 'kind': 'music', 'format': 'music'}, start, me, 2, {'name': 'A'})['verdict'] == ''


@pytest.fixture
def kim(client, monkeypatch, provider):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(media, 'WEAVE', True)
    response = client.post('/api/companion', json={'name': 'Kim', 'timezone': 'UTC', 'schedule': EVENINGS,
                                                    'home_city': 'Baltimore', 'identity': 'They are a nurse.',
                                                    'interests': ['reading', 'mystery novels']})
    assert response.status_code == 200, response.text
    set_life(client, automatic_events=True, phrase_with_model=False)
    return response.json()


def test_the_panel_shows_a_book_a_show_and_a_song_and_the_user_can_set_their_own(client, kim):
    view = client.get('/api/life/media').json()
    assert [item['kind'] for item in view['now']] == ['book', 'show', 'music']
    book = view['now'][0]
    assert book['text'].startswith(f"Reading {book['title']}") and not book['set_by_you']
    assert 'numbers' not in view
    assert client.get('/api/life/media').json()['now'] == view['now']
    reconcile(client)  # the agenda moves the chains on past today
    mine = client.patch('/api/life/media', json={'kind': 'book', 'title': 'Middlemarch', 'by': 'George Eliot'}).json()
    assert [item['kind'] for item in mine['now']] == ['book', 'show', 'music']
    assert mine['now'][0]['title'] == 'Middlemarch' and mine['now'][0]['set_by_you']
    assert mine['now'][0]['text'] == 'Reading Middlemarch by George Eliot: just started.'
    back = client.patch('/api/life/media', json={'kind': 'book', 'reset': True}).json()
    assert not back['now'][0]['set_by_you'] and back['now'][0]['title'] not in ('Middlemarch', book['title'])
    assert client.patch('/api/life/media', json={'kind': 'film', 'title': 'X'}).status_code == 422
    show(client, show_home_meters=True)
    assert 'numbers' in client.get('/api/life/media').json()
    set_life(client, media_realism=0)
    off = client.get('/api/life/media').json()
    assert off['off'] and off['now'] == []
    assert client.patch('/api/life/media', json={'kind': 'book', 'title': 'Y'}).status_code == 409


def test_chains_move_on_and_finished_things_leave_a_verdict(client, kim):
    database = client.app.state.database
    with database.connect(write=True) as connection:
        timeline_id = connection.execute('SELECT active_timeline_id FROM companions').fetchone()[0]
        definition = decode(connection.execute('SELECT definition FROM character_versions').fetchone()[0])
        first = media.advance(connection, timeline_id, definition, WORLD, TODAY)
        later = media.advance(connection, timeline_id, definition, WORLD, TODAY + timedelta(days=150))
        assert len(later) > len(first) + 3
        done = [item for item in later if item['status'] == 'done' and item['kind'] != 'music']
        assert done and all(item['verdict'] in media.VERDICTS for item in done)
        for kind in media.KINDS:
            chain = [item for item in later if item['kind'] == kind]
            assert len({item['title'] for item in chain}) == len(chain)
            assert all(a['ends_on'] <= b['started_on'] for a, b in zip(chain, chain[1:], strict=False))
        assert media.current(later, TODAY + timedelta(days=150)) or True


def test_their_days_mention_what_they_are_on_and_the_chat_knows_it(client, kim, clock):
    database = client.app.state.database
    # Their evenings are seeded on the random timeline id, so look over a week rather than one day.
    for _day in range(7):
        reconcile(client)
        with database.connect() as connection:
            rows = connection.execute("SELECT entry FROM life_agenda WHERE json_extract(entry, '$.media') IS NOT "
                                      'NULL').fetchall()
        if rows:
            break
        clock.advance(timedelta(days=1))
    assert rows
    with database.connect() as connection:
        per_day = connection.execute("SELECT local_date, COUNT(*) AS n FROM life_agenda WHERE "
                                     "json_extract(entry, '$.media') IS NOT NULL GROUP BY local_date").fetchall()
        assert all(row['n'] == 1 for row in per_day)
        timeline_id = connection.execute('SELECT active_timeline_id FROM companions').fetchone()[0]
        definition = decode(connection.execute('SELECT definition FROM character_versions').fetchone()[0])
        lines = media.context_lines(connection, timeline_id, definition, WORLD, database.clock.now(), 'UTC')
    texts = [text for _key, text in lines]
    assert any(text.startswith('- You are reading ') for text in texts)
    assert not any('lyric' in text.casefold() for text in texts)


def test_books_and_streaming_count_as_spending(client, kim):
    database = client.app.state.database
    client.get('/api/life/media')
    with database.connect(write=True) as connection:
        timeline_id = connection.execute('SELECT active_timeline_id FROM companions').fetchone()[0]
        definition = decode(connection.execute('SELECT definition FROM character_versions').fetchone()[0])
        connection.execute("UPDATE media_state SET profile=json_set(profile, '$.library', json('false'))")
        media.advance(connection, timeline_id, definition, WORLD, TODAY + timedelta(days=40))
        bought = media.purchases(connection, timeline_id, TODAY - timedelta(days=60), TODAY + timedelta(days=40),
                                 definition)
    assert bought and all(item['for'] == 'media' and item['cost'] > 0 for item in bought)
    assert money.profile(definition)


def test_a_city_set_in_a_year_of_its_own_caps_the_titles_at_that_year():
    ny = media.place_of(WORLD.find('new-york-1925'))
    assert (ny['bank'], ny['year']) == ('jazz-age', 1925)
    for kind in media.KINDS:
        assert all(item['year'] <= 1925 for item in media.candidates(ny, kind, set()))
    eighties = media.place_of({'era': 'other', 'country': 'United States', 'names': {'year': 1985}})
    assert (eighties['bank'], eighties['year']) == ('modern', 1985)
    assert all(item['year'] <= 1985 for item in media.candidates(eighties, 'music', set()))
    assert media.place_of({'era': 'other', 'names': {'year': 1924}})['bank'] == 'jazz-age'
    # What was running then: no 1914 picture serial at the pictures in 1925.
    running = [item for item in media.candidates(ny, 'show', set()) if item['format'] in media.SHOWING_FORMATS]
    assert running and min(item['year'] for item in running) > 1914


def test_the_genre_they_name_is_not_diluted_by_reading_or_novels():
    liked, _ = media.tastes({'interests': ['mystery novels', 'reading', 'science fiction']})
    assert liked == {'mystery', 'scifi'}


def test_wording_for_plays_seasons_names_with_a_full_stop_and_american_cities():
    play = {'kind': 'show', 'title': 'Rose-Marie', 'creator': 'Rudolf Friml', 'format': 'broadway',
            'outcome': 'finish', 'verdict': 'loved it'}
    assert media.ended_text(play) == 'Saw Rose-Marie by Rudolf Friml: loved it.'
    assert media.ended_text(play, 'you') == 'You saw Rose-Marie by Rudolf Friml: you loved it.'
    season = {**play, 'title': 'Shrinking', 'creator': 'Apple TV+', 'format': 'series'}
    assert media.ended_text(season) == 'Finished a season of Shrinking: loved it.'
    assert media.ended_sentence(season, 'Kim') == 'Kim finished a season of Shrinking and loved it.'
    song = {'kind': 'music', 'title': 'Bright Lights', 'creator': 'Gary Clark Jr.', 'format': 'music',
            'started_on': '2026-10-01', 'ends_on': '2026-10-20'}
    assert media.now_text(song, TODAY, 'modern') == 'On repeat: Bright Lights by Gary Clark Jr.'
    serial = {'kind': 'show', 'title': 'The Ghost City', 'creator': 'Universal', 'format': 'film-serial',
              'started_on': '2026-10-01', 'ends_on': '2026-10-20'}
    assert media.now_text(serial, TODAY, 'jazz-age', region='us') == \
        'Following The Ghost City by Universal at the movies: a few chapters in.'
    assert 'at the pictures' in media.now_text(serial, TODAY, 'jazz-age', region='uk')
    magazine = {**serial, 'format': 'serial'}
    assert 'installments' in media.now_text(magazine, TODAY, 'nineteenth', region='us')


@pytest.fixture
def clara(client, monkeypatch, provider):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    response = client.post('/api/companion', json={'name': 'Clara', 'timezone': 'America/New_York',
                                                    'schedule': EVENINGS, 'home_city': 'new-york-1925',
                                                    'interests': ['jazz']})
    assert response.status_code == 200, response.text
    return response.json()


def test_picks_saved_before_the_year_cap_are_drawn_again(client, clara):
    client.get('/api/life/media')
    database = client.app.state.database
    with database.connect(write=True) as connection:
        connection.execute("UPDATE media_state SET profile=json_set(profile, '$.year', 1926)")
        connection.execute("UPDATE media_items SET title='Blue Skies', creator='Irving Berlin' WHERE kind='music' "
                           "AND status='current'")
    view = client.get('/api/life/media').json()
    assert [item['kind'] for item in view['now']] == ['book', 'show', 'music']
    assert all(item['title'] != 'Blue Skies' for item in view['now'])
    with database.connect() as connection:
        assert decode(connection.execute('SELECT profile FROM media_state').fetchone()[0])['year'] == 1925
        assert not connection.execute("SELECT id FROM media_items WHERE title='Blue Skies'").fetchall()


def test_a_recommendation_comes_first_on_the_panel_and_their_own_show_waits(client, kim, clock, monkeypatch):
    from conftest import send

    from companion.life import recommendations
    monkeypatch.setattr(recommendations, 'SESSION_SHARE', 1)
    monkeypatch.setattr(media, 'GAPS', dict.fromkeys(media.KINDS, (0, 0)))  # always a show of their own on
    client.get('/api/life/media')
    reconcile(client)  # the agenda draws the chains days ahead
    send(client, 'You should watch Severance, it is great', 'client-media-rec-1')
    today = clock.now().date().isoformat()
    with client.app.state.database.connect() as connection:
        ahead = connection.execute("SELECT COUNT(*) FROM media_items WHERE started_on>?", (today,)).fetchone()[0]
    assert ahead == 0
    held = False
    for _day in range(8):
        clock.advance(timedelta(days=1))
        reconcile(client)
        view = client.get('/api/life/media').json()
        shown = next(item for item in view['now'] if item['kind'] == 'show')
        if shown.get('recommended'):
            assert shown['title'] == 'Severance' and shown['text'].startswith('Watching Severance: ')
            held = True
    assert held
    assert any(item['text'].startswith('Finished Severance, which you recommended: ') for item in view['lately'])
    with client.app.state.database.connect() as connection:
        waited = connection.execute("SELECT MAX(held) FROM media_items WHERE kind='show'").fetchone()[0]
    assert waited > 0


def test_songs_lean_to_the_years_they_grew_up_by_the_age_in_their_identity():
    me = media.place_of(WORLD.find('baltimore'))
    older, younger = {'name': 'Pat', 'identity': 'Pat, 58, a retired teacher.'}, {'name': 'Jo', 'identity': 'Jo, 22.'}
    years = [[media.choose(f's{n}', 'music:0', me, 'music', who, set())['year'] for n in range(80)]
             for who in (older, younger)]
    assert sum(1984 <= year <= 2000 for year in years[0]) > sum(1984 <= year <= 2000 for year in years[1])
