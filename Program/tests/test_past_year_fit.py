"""What the 1.2 end-to-end run found in worlds started in a past year (scripts/sim/past_years.py): an employer, a
pantry swap, a bill, the dating app and anime-model tags from after the world's year."""
import pytest

from companion import dating
from companion.images import tags
from companion.life import kitchen, media
from companion.world import catalog, decades, generators


@pytest.fixture
def year(monkeypatch):
    """Run the world in a past year: year(1995)."""
    def set_year(value):
        monkeypatch.setattr(decades, 'world_year', lambda: value)
    return set_year


def employers(career: str, count: int = 120) -> set[str]:
    city = catalog.cities()['chicago']
    return {generators.job(city, career, seed=f'sim-{index}')['employer']['name'] for index in range(count)}


def test_nobody_gets_a_job_at_a_company_from_after_the_year(year):
    assert 'Google Chicago' in employers('software-engineer')
    year(1995)
    assert 'Google Chicago' not in employers('software-engineer')
    year(2016)
    assert 'Google Chicago' in employers('software-engineer')


def test_a_job_already_held_there_stays(year):
    year(1995)
    city = catalog.cities()['chicago']
    held = generators.job(city, 'software-engineer', seed='kept', employer='google-chicago')
    assert held['employer']['name'] == 'Google Chicago'


def test_every_employer_year_is_a_founding_year():
    for city in catalog.cities().values():
        for employer in city.get('employers') or ():
            if employer.get('years'):
                start, until = employer['years']
                assert 1800 <= start <= 2026 and until is None, employer['name']


def test_a_vegan_buys_soy_milk_before_oat_milk(year):
    assert kitchen.swap_then('oat milk') == 'oat milk'
    year(1995)
    assert kitchen.swap_then('oat milk') == 'soy milk' and kitchen.swap_then('vegan kimchi') == 'vegan kimchi'
    year(2018)
    assert kitchen.swap_then('oat milk') == 'oat milk'


def test_shows_are_on_cable_before_streaming(year):
    assert media.series_bill() == 'paid for a month of streaming'
    year(2005)
    assert media.series_bill() == 'paid the cable bill'


def test_matchlight_is_a_dating_site_before_apps(year):
    city = catalog.cities()['chicago']
    assert dating.words(city)['noun'] == 'a dating app' and dating.words(city)['app']
    year(2005)
    words = dating.words(city)
    assert words['noun'] == 'a dating site' and words['get'] == 'Sign up' and words['title'] == dating.APP_NAME
    assert not words['app']  # No app store: no Download glyph.
    assert dating.met_on(city) == f'Matched on {dating.APP_NAME}'
    year(1995)
    assert dating.words(city)['noun'] == 'the personals'
    # A period city keeps its own way of meeting people.
    assert dating.words(catalog.cities()['london-1895'])['noun'] == dating.SURFACES['column']['noun']
    assert not dating.words(catalog.cities()['london-1895'])['app']


def test_anime_tags_take_the_year_as_its_decade_and_see_a_past_view():
    picture = decades.table()['decades']['1990s']['picture']
    scene = picture['scene'].format(year=1995, part='mid')
    moment, _ = tags.convert(f'{tags.ILLUSTRIOUS} of a fictional everyday moment, a medium shot. A tall man with '
                             f'short black hair. Having coffee at a diner. He is the only person in the picture. '
                             f'{scene}', '', 'Theo')
    assert moment.endswith('1990s fashion') and 'it is 1995' not in moment and '1boy' in moment
    framing = picture['framings']['view'].format(subject='he')
    view, negative = tags.convert(f'{tags.ILLUSTRIOUS}, {framing}. A diner counter with a jukebox. {scene}', '',
                                  'Theo')
    assert 'scenery, no humans' in view and '1boy' not in view + negative and 'theo' not in view
    selfie = picture['framings']['selfie']
    shot, _ = tags.convert(f'{tags.ILLUSTRIOUS}, {selfie}. A tall man. He is the only person in the picture.', '',
                           'Theo')
    assert 'looking at viewer' in shot and 'holding phone' not in shot
    today, _ = tags.convert(f"{tags.ILLUSTRIOUS}, a fictional selfie taken at arm's length with a phone's front "
                            'camera, face and shoulders in frame. A tall man. He is the only person in the picture.',
                            '', 'Theo')
    assert 'selfie' in today and 'holding phone' in today


def test_errands_and_work_projects_name_nothing_newer(year):
    from companion.life import admin, work
    has = {'car', 'pet', 'kids', 'home', 'garden', 'rent', 'own'}
    today = [item['title'] for item in admin.bank('paperwork', 'modern', has, True)]
    year(1995)
    then = [item['title'] for item in admin.bank('paperwork', 'modern', has, True)]
    assert len(then) < len(today) and all(decades.fits(admin.wording(item), 1995)
                                          for item in admin.bank('paperwork', 'modern', has, True))
    assert not any('online' in title.lower() for title in then)
    assert all(decades.fits(title, 1995) for title in work.projects('tech', 'modern'))
    assert decades.fits('renewed the car registration online', 2001)
    assert not decades.fits('renewed the car registration online', 1995)
    year(None)
    assert decades.fits('paid with the bank app')


def test_no_cracked_phone_screen_before_smartphones(year):
    from companion.life import disruptions
    block = {'kind': 'social'}
    def reasons():
        return {(disruptions.roll(f'seed-{index}', block) or {}).get('reason') for index in range(600)}
    assert 'the phone screen cracked' in reasons()
    year(1995)
    found = reasons()
    assert 'the phone screen cracked' not in found and 'the car battery died' in found


def test_a_done_errand_is_not_adulting_in_1995(year):
    from companion.life import admin
    year(1995)
    assert 'Adulting.' in admin.CAPTIONS and not decades.fits('Adulting.')
    year(2016)
    assert decades.fits('Adulting.')


def test_no_emoji_before_emoji(year):
    from companion.life import feed
    posts = [{'text': 'Happy birthday! 🎂', 'author': {'kind': 'person'},
              'audience': {'comments': [{'text': '😂'}, {'text': 'Thank you!! ❤️'}]}},
             {'text': 'my own 🎉', 'author': {'kind': 'user'}, 'audience': {'comments': []}}]
    assert feed.of_the_year([dict(post) for post in posts])[0]['text'] == 'Happy birthday! 🎂'
    year(1999)
    shown = feed.of_the_year(posts)
    assert shown[0]['text'] == 'Happy birthday!' and [c['text'] for c in shown[0]['audience']['comments']] == \
        ['Ha!', 'Thank you!!']
    assert shown[1]['text'] == 'my own 🎉'


def test_a_1995_status_is_not_just_vibing(year):
    from companion.life import status
    companion = {'version': {'definition': {'interests': []}}}
    year(1995)
    lines = {status.everyday(companion, f'seed-{index}') for index in range(200)}
    assert 'just vibing' not in lines and 'coffee first ☕' in lines  # The emoji goes when it is shown.
    assert decades.without_emoji('coffee first ☕') == 'coffee first'
    assert not decades.fits('out, phone in pocket')
