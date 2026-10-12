"""American wording for the shared banks in American settings (companion/world/wording.py)."""
from datetime import date

from companion.world import catalog, dating, life_details, perception, townsfolk, wording

BRITISH = ('neighbour', 'favourite', 'colour', 'realis', 'prize marrow', 'parish vestry', 'parish rolls', 'queue')


def test_american_cities_get_american_wording_and_british_ones_keep_theirs():
    maine, london = catalog.city('haddon-harbor'), catalog.city('london')
    assert wording.regional(maine, 'Running for the neighbourhood council.') == 'Running for the neighborhood council.'
    assert wording.regional(london, 'Running for the neighbourhood council.') == 'Running for the neighbourhood council.'
    assert wording.americanize('Nobody realises; I am realistic about the museum, Mum.') == \
        'Nobody realizes; I am realistic about the museum, Mom.'
    assert wording.regional(catalog.city('pellmouth'), 'grow the prize marrow at the harvest fair') == \
        'grow the prize pumpkin at the harvest fair'


def test_townsfolk_in_american_towns_read_american():
    for city_id in ('haddon-harbor', 'pellmouth'):
        data = catalog.city(city_id)
        for place in data['places'][:30]:
            for sheet in townsfolk.at_place(data, place['id']):
                goals = [townsfolk.goal(sheet, data, number) for number in range(len(sheet['goals']))]
                text = ' '.join([sheet['quirk'], townsfolk.quirk_bio(data, sheet['quirk']),
                                 dating.bio(sheet, data, '', date(2026, 3, 2)), str(perception.for_sheet(data, sheet)),
                                 str(life_details.for_sheet(data, sheet)),
                                 *(goal[field] for goal in goals for field in ('text', 'bio', 'progress', 'done'))])
                text = text.lower().replace(place['name'].lower(), '')  # A real First Parish Vestry stays.
                assert not [word for word in BRITISH if word in text], (city_id, sheet['key'])
