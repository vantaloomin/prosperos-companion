"""Prospero's Draft Table (companion/world/draft): one line builds a whole place that loads like any other city, with
no fixes and no thin spots, the same way every time."""
import itertools
import json

import pytest

from companion.world import catalog, check, draft
from companion.world.draft import banks, brief

LINES = ['a cold fishing town on a northern coast, 1920s', 'an elven forest city', 'a generation ship',
         'a mining boomtown in the wild west', 'a steampunk canal town', 'a gaslit victorian port',
         'a medieval market town by a river', 'a beach town in Maine', '', 'a colony city on Mars',
         'a sleepy mountain village', 'a busy tropical island city', 'a tiny hamlet by a lake', 'a starbase',
         'a huge desert metropolis', 'a quiet suburb near Osaka']
ERAS = ('medieval', 'fantasy', 'victorian', 'steampunk', 'frontier', 'jazz-age', 'modern')
TODAY = '2026-10-25'


def loaded(line: str, seed: str = '1', **extra) -> dict:
    city = draft.build(line, seed, today=TODAY, **extra)['city']
    return catalog.prepare(json.loads(json.dumps(city)), mend=True)


@pytest.mark.parametrize(('line', 'seed'), list(itertools.product(LINES, ('1', '2', '3'))))
def test_every_line_builds_a_place_that_loads_with_nothing_to_mend_and_no_thin_spots(line, seed):
    data = loaded(line, seed)
    assert not data.get('import_notes')
    assert check.warnings(data) == []
    by_hood = {hood['id']: [place for place in data['places'] if place['neighborhood'] == hood['id']]
               for hood in data['neighborhoods']}
    assert all(len(places) >= 4 for places in by_hood.values())
    assert data['employers'] and data['career_hubs'] and data['annual_events'] and data['local_color']


def test_the_same_line_and_seed_give_the_same_place_and_another_seed_another():
    first = draft.build('a cold fishing town, 1920s', '7', today=TODAY)
    assert draft.build('a cold fishing town, 1920s', '7', today=TODAY) == first
    other = draft.build('a cold fishing town, 1920s', '8', today=TODAY)['city']
    assert other['name'] != first['city']['name'] or other['places'] != first['city']['places']


def test_redrawing_a_section_leaves_the_rest_as_it_was():
    base = draft.build('a cold fishing town, 1920s', '1', today=TODAY)['city']
    for section, keys in (('places', {'places'}), ('employers', {'employers', 'career_hubs'}),
                          ('events', {'annual_events'}), ('colour', {'local_color'})):
        again = draft.build('a cold fishing town, 1920s', '1', rolls={section: 1}, today=TODAY)['city']
        assert {key for key in base if base[key] != again[key]} == keys, section


@pytest.mark.parametrize(('line', 'expected'), [
    ('a cold fishing town on a northern coast, 1920s', {'era': 'jazz-age', 'water': 'sea', 'biome': 'cold'}),
    ('a railway station town in 1880', {'era': 'victorian', 'aboard': False}),
    ('a frontier town out west, 1882', {'era': 'frontier'}),
    ('a space station called Halcyon Reach', {'era': 'future', 'aboard': True, 'name': 'Halcyon Reach'}),
    ('an elven city by a lake', {'era': 'fantasy', 'water': 'lake', 'size': 'large'}),
    ('a tiny village in the mountains', {'era': 'modern', 'biome': 'highland', 'size': 'tiny'}),
    ('a beach town in Maine', {'anchor': 'haddon-harbor', 'water': 'sea'}),
    ('a fishing ship port', {'aboard': False}),
])
def test_the_line_picks_era_water_climate_size_name_and_where(line, expected):
    read = brief.read(line, 'seed')
    assert {key: read[key] for key in expected} == expected


def test_a_line_that_says_nothing_still_builds_and_an_empty_one_picks_an_era():
    assert brief.read('a nice place', 's')['era'] == 'modern'
    eras = {brief.read('', str(seed))['era'] for seed in range(40)}
    assert len(eras) > 3


def test_a_place_in_our_world_sits_near_the_city_it_names_and_keeps_its_money_and_holidays():
    data = loaded('a quiet suburb near Osaka')
    osaka = catalog.city('osaka')
    assert data['country'] == osaka['country'] and data['currency'] == osaka['currency']
    assert 30 <= catalog.distance_km(data, osaka) <= 160
    assert all(item['source'] in data['sources'] for item in data['prices'])


def test_a_ship_is_enclosed_and_docks_at_port_vesper_and_a_future_city_stays_on_the_ground():
    ship = loaded('a generation ship')
    assert ship['enclosed'] is True and ship['neighbours'][0]['city'] == 'port-vesper'
    assert not {'car', 'rideshare', 'horse'} & set(ship['speeds'])
    ground = loaded('a colony city on Mars')
    assert ground['enclosed'] is False and ground['climate']


@pytest.mark.parametrize('era', ERAS)
def test_each_era_builds_from_its_own_banks(era):
    group = brief.GROUPS[era]
    data = loaded(f'a {era} town by the sea'.replace('jazz-age', '1920s'))
    assert data['era'] == era
    names = {entry_name for entry in banks.folder('places') if entry['group'] == group for entry_name in entry['names']}
    assert names


def entries_for(era: str, aboard: bool = False) -> list[dict]:
    fake = {'group': brief.GROUPS[era] if not aboard else 'future', 'era': era, 'aboard': aboard, 'water': None}
    # Water-only entries count too: a place by the water draws from them.
    return [entry for entry in banks.folder('places')
            if banks.fits(entry | {'water': None}, fake)]


@pytest.mark.parametrize(('era', 'aboard'), [(era, False) for era in (*ERAS, 'future')] + [('future', True)])
def test_every_era_has_a_hundred_places_to_draw_from(era, aboard):
    assert len(entries_for(era, aboard)) >= 100


def test_the_other_banks_have_a_hundred_entries_each():
    assert len(banks.folder('hoods')) >= 100
    for name in ('employers', 'events', 'colour'):
        assert len(banks.load(name)[name]) >= 100, name
    words = banks.words()
    for key in ('emblems', 'stems', 'town_starts', 'stars'):
        assert len(words[key]) >= 100, key


def test_every_bank_entry_is_well_formed():
    kinds = banks.kinds()
    for entry in banks.folder('places'):
        assert entry['kind'] in kinds and entry['names'] and entry['summary'], entry
    groups = set(brief.GROUPS.values())
    for entry in banks.folder('hoods'):
        assert entry['group'] in groups and entry['places'] and set(entry['places']) <= set(kinds), entry
    for name in ('employers', 'events', 'colour', 'transit'):
        for entry in banks.load(name)[name]:
            assert entry['group'] in groups and entry['names'], entry


def test_the_app_drafts_a_place_and_saves_it_like_any_other_city(client):
    response = client.post('/api/world/draft', json={'line': 'a cold fishing town, 1920s', 'seed': '4'})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['brief']['era'] == 'jazz-age' and body['notes'] == [] and body['warnings'] == []
    redrawn = client.post('/api/world/draft', json={'line': 'a cold fishing town, 1920s', 'seed': '4',
                                                    'rolls': {'places': 1}}).json()
    assert redrawn['definition']['employers'] == body['definition']['employers']
    assert redrawn['definition']['places'] != body['definition']['places']
    saved = client.post('/api/world/cities', json=body['definition'])
    assert saved.status_code == 200, saved.text
    assert client.get(f'/api/world/cities/{body["definition"]["id"]}').status_code == 200
    assert client.post('/api/world/draft', json={'line': 'x', 'rolls': {'nonsense': 1}}).status_code == 422


def test_the_check_panel_says_what_loading_a_changed_draft_would_mend_and_where_it_is_thin(client):
    definition = client.post('/api/world/draft', json={'line': 'a cold fishing town, 1920s', 'seed': '4'}).json()['definition']
    clean = client.post('/api/world/draft/check', json=definition).json()
    assert clean['notes'] == [] and clean['warnings'] == [] and clean['summary']['name'] == definition['name']
    hood = definition['neighborhoods'][0]['id']
    definition['places'] = [place for place in definition['places'] if place['neighborhood'] != hood]
    definition['places'][0].pop('cost')
    thin = client.post('/api/world/draft/check', json=definition).json()
    name = definition['neighborhoods'][0]['name']
    assert thin['warnings'] == [f'{name} has no places yet. Add one or two so days there do not repeat.']
    assert thin['notes']
    definition['neighborhoods'] = []
    assert client.post('/api/world/draft/check', json=definition).status_code in (400, 422)


def test_the_draft_table_page_is_served_with_the_app():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    page = (root / 'draft.html').read_text(encoding='utf-8')
    assert '/src/draft.tsx' in page and "Prospero's Draft Table" in page
    assert "draft: 'draft.html'" in (root / 'vite.config.ts').read_text(encoding='utf-8')


def test_getting_about_names_every_way_the_app_knows_in_plain_words():
    import re
    from pathlib import Path

    from companion.world.schema import TRANSIT_KINDS
    text = (Path(__file__).resolve().parent.parent / 'src/features/draft/draftText.ts').read_text(encoding='utf-8')
    block = text.split('export const TRANSIT_KINDS', 1)[1].split('}', 1)[0]
    named = {key.strip("'") for key in re.findall(r"([\w'-]+): '", block)}
    assert named == set(TRANSIT_KINDS)
