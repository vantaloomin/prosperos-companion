"""Decade rules (companion/world/decades.py): a modern city takes on the decade of a world that runs in a past year."""
from datetime import date

import pytest

from companion.images import prompts
from companion.life import hobbies, media, money
from companion.world import catalog, decades, era_words, naming, politics


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def year(monkeypatch):
    """Run the world in a past year: year(2009)."""
    def set_year(value):
        monkeypatch.setattr(decades, 'world_year', lambda: value)
    return set_year


def test_a_year_has_a_decade_and_a_part_of_it():
    assert decades.decade(1994) == '1990s' and decades.decade(2009) == '2000s' and decades.decade(2020) == '2020s'
    assert [decades.part(year) for year in (2000, 2003, 2005, 2006, 2007, 2009)] == \
        ['early', 'early', 'mid', 'mid', 'late', 'late']


def test_years_are_from_and_until_either_open():
    assert decades.in_years({}, 1990)
    assert decades.in_years({'years': [2012, None]}, 2012) and not decades.in_years({'years': [2012, None]}, 2011)
    assert decades.in_years({'years': (None, 2005)}, 1990) and not decades.in_years({'years': [None, 2005]}, 2006)


def test_the_present_changes_nothing():
    assert decades.world_year() is None
    city = catalog.cities()['baltimore']
    assert catalog.city('baltimore') is city
    assert decades.picture(city) is None and decades.decade_of(city) is None
    assert 'subscription-creator' in catalog.careers_for(city)
    assert media.place_of(city)['year'] == media.ERA_YEARS['modern']
    assert era_words.words(city)['selfie'] == 'selfie'


def test_prices_follow_each_currency_back():
    assert decades.factor('USD', 2026) == 1.0
    assert decades.factor('USD', 2000) == pytest.approx(172.2 / 330.0)
    # Between two listed years, a steady rate: 2002 sits between 2000 and 2005.
    assert decades.level('USD', 2000) < decades.level('USD', 2002) < decades.level('USD', 2005)
    assert decades.factor('JPY', 2009) > decades.factor('KRW', 2009)  # Japan's prices barely moved.
    assert decades.factor('XYZ', 2009) == decades.factor('USD', 2009)
    assert decades.factor('USD', 1980) == decades.factor('USD', 1990)


def test_a_modern_city_has_that_years_rents_and_prices(year):
    year(2009)
    today = catalog.cities()['baltimore']
    then = catalog.city('baltimore')
    share = decades.factor('USD', 2009)
    assert then['price_year'] == 2009 and 'price_year' not in today
    assert then['neighborhoods'][0]['rent']['studio'] == [round(value * share) for value in
                                                          today['neighborhoods'][0]['rent']['studio']]
    coffee = next(item for item in then['prices'] if item['id'] == 'coffee')
    assert coffee['high'] == round(3.5 * share, 2)
    assert decades.price_share(then) == pytest.approx(share) and decades.price_share(today) == 1.0
    # Pay is that year's too, and the share of it rent takes stays the same.
    assert money.take_home(then, 2) == pytest.approx(money.take_home(today, 2) * share, rel=1e-3)  # Rents are rounded.
    # A period city keeps its own money.
    assert catalog.city('new-york-1925') is catalog.cities()['new-york-1925']


def test_careers_and_hobbies_with_years_are_offered_only_then(year, monkeypatch):
    city = catalog.cities()['baltimore']
    year(2009)
    assert 'subscription-creator' not in catalog.careers_for(city)
    assert 'subscription-creator' not in catalog.careers_for(city, needs_met=False)
    year(2016)
    assert 'subscription-creator' in catalog.careers_for(city)
    # One that ended is not offered today either.
    year(None)
    ended = {**catalog.careers()['barista'], 'years': (1990, 2005)}
    assert 'barista' not in catalog.of_the_year({'barista': ended}, city)
    year(1999)
    assert 'barista' in catalog.of_the_year({'barista': ended}, city)
    # Hobbies the same way: the app never hands out one before its time.
    late = [{**item, 'years': [2015, None]} if item['id'] == 'video-games' else item
            for item in hobbies.catalogue()['hobbies']]
    shipped = hobbies.catalogue()
    monkeypatch.setattr(hobbies, 'catalogue', lambda: {**shipped, 'hobbies': late})
    definition = {'name': 'Sam', 'interests': [], 'identity': 'A gamer.'}
    picks = {hobbies.choose_new('seed', f'pick{index}', definition, city, [])['id'] for index in range(200)}
    assert 'video-games' not in picks
    found = {item['id'] for item in decades.current(late, city)}
    assert 'video-games' not in found and 'climbing' in found
    year(2020)
    assert 'video-games' in {item['id'] for item in decades.current(late, city)}


def test_media_runs_to_the_world_year(year):
    city = catalog.cities()['baltimore']
    year(2009)
    me = media.place_of(city)
    assert me['year'] == 2009
    assert all(item['year'] <= 2009 for item in media.candidates(me, 'book', set()))
    assert media.place_of(catalog.cities()['new-york-1925'])['year'] == 1925


def test_era_words_take_the_decade_under_the_same_switch(year):
    city = catalog.cities()['baltimore']
    year(1996)
    found = era_words.words(city)
    assert found['dating_tab'] == 'Personals' and found['selfie'] == 'snapshot'
    assert era_words.say(found, 'sent_you', name='Sam') == 'Sam left you a message.'
    assert era_words.words(city, on=False)['dating_tab'] == 'Matchlight'
    year(2004)
    assert era_words.words(city)['selfie'] == 'photo' and era_words.words(city)['dating_tab'] == 'Matchlight'
    # A period city keeps its era's words.
    assert era_words.words(catalog.cities()['london-1895'])['selfie'] == 'portrait'


def test_every_decade_word_is_a_word_the_app_has():
    known = era_words.table()['words']['modern']
    for name, found in era_words.table()['decades'].items():
        assert set(found) <= set(known), name
        assert name in decades.table()['decades']


def test_politics_argues_the_questions_of_that_year(year):
    city = catalog.cities()['baltimore']
    year(2009)
    assert naming.present_year(city) == 2009
    ids = {item['id'] for item in politics.era_questions(city, date(2009, 10, 5))}
    assert {'smoking-ban', 'city-wifi', 'housing-crisis', 'bike-lanes'} <= ids
    assert not ids & {'short-lets', 'ride-hailing', 'y2k', 'climate'}
    # Real questions of the year come first.
    assert politics.era_questions(city, date(2009, 10, 5))[0]['id'] in {'smoking-ban', 'city-wifi'}
    year(None)
    ids = {item['id'] for item in politics.era_questions(city, date(2026, 10, 5))}
    assert {'short-lets', 'climate', 'housing-crisis'} <= ids and not ids & {'smoking-ban', 'y2k', 'skate-park'}


def test_every_decade_question_is_well_formed():
    bank = politics.bank()
    for item in bank['questions']['modern']:
        assert len(item['sides']) == 2 and item['beats'], item['id']
        for side in item['sides']:
            assert set(side['jobs']) <= set(bank['jobs']) and set(side['words']) <= set(bank['words']), item['id']
        assert all(favors in (0, 1) for _text, favors in item['beats']), item['id']
        if item.get('years'):
            assert len(item['years']) == 2, item['id']


EVENT = {'summary': 'Reading by the window', 'place': '', 'mood': '', 'hour': 15, 'weather': None}


def test_pictures_show_the_year_with_a_camera_of_its_decade(year):
    city = catalog.cities()['baltimore']
    style = 'Candid photo'
    plain = prompts.compose('Sam', 'short dark hair', [EVENT], style, framing='selfie')
    assert "phone's front camera" in plain and 'It is ' not in plain
    year(1996)
    period = decades.picture(city)
    assert period['decade'] == '1990s'
    shown = prompts.compose('Sam', 'short dark hair', [EVENT], style, framing='selfie', period=period)
    assert 'It is 1996: clothes, hair, phones, cars and shop fronts are from the mid 1990s' in shown
    assert 'disposable film camera' in shown and "phone's front camera" not in shown
    assert shown.endswith(period['cameras']['selfie'])
    # A backend's own style keeps the decade's camera.
    inputs = {'prompt': shown, 'style': style, 'framing': 'selfie', 'period': period}
    restyled = prompts.restyle(inputs, 'Grainy photo')
    assert restyled['prompt'].startswith('Grainy photo') and restyled['prompt'].endswith(period['cameras']['selfie'])
    assert restyled['prompt'].count(period['cameras']['selfie']) == 1
    # A drawn style keeps its own look, but still the year.
    drawn = prompts.compose('Sam', 'short dark hair', [EVENT], 'Watercolor painting', period=period)
    assert 'It is 1996' in drawn and 'film' not in drawn
    year(2021)
    assert prompts.compose('Sam', '', [EVENT], style, period=decades.picture(city)).endswith(prompts.CAMERAS['moment'])


def test_a_past_world_takes_on_its_decade(client, companion, app):
    ok(client.put('/api/settings', json={'period_words': True}))
    world = ok(client.post('/api/worlds', json={'year': 1997}))
    ok(client.post(f"/api/worlds/{world['id']}/switch"))
    assert decades.world_year() == 1997
    found = ok(client.get('/api/world/words'))
    assert found['decade'] == '1990s' and found['words']['dating_tab'] == 'Personals'
    assert catalog.city('baltimore')['price_year'] == 1997
    first = next(item for item in ok(client.get('/api/worlds'))['personas'][0]['worlds'] if item['first'])
    ok(client.post(f"/api/worlds/{first['id']}/switch"))
    assert decades.world_year() is None and 'price_year' not in catalog.city('baltimore')
