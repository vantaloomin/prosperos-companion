"""Decade banks (Back when, part 3): the jobs, pastimes, words and memes of a world that runs in a past year."""
import pytest

from companion.images import content, memes, photos
from companion.life import hobbies
from companion.world import catalog, decades, era_words

DECADES = ('1990s', '2000s', '2010s')
ENDED_CAREERS = ('video-store-clerk', 'photo-lab-tech', 'music-store-clerk', 'web-designer',
                 'word-processor-operator', 'film-projectionist')
ENDED_HOBBIES = ('rollerblading', 'step-aerobics', 'lan-parties', 'dance-games', 'scrapbooking', 'mixtapes',
                 'blogging')


@pytest.fixture
def year(monkeypatch):
    """Run the world in a past year: year(2009)."""
    def set_year(value):
        monkeypatch.setattr(decades, 'world_year', lambda: value)
    return set_year


def test_jobs_of_past_decades_are_offered_then_and_never_today(year):
    city = catalog.cities()['baltimore']
    year(1998)
    then = catalog.careers_for(city, needs_met=False)
    assert set(ENDED_CAREERS) <= set(then)
    year(None)
    today = catalog.careers_for(city, needs_met=False)
    assert not set(ENDED_CAREERS) & set(today)
    assert all(career['years'][1] < 2026 for key, career in catalog.careers().items() if key in ENDED_CAREERS)


def test_pastimes_of_past_decades_are_offered_then_and_never_today(year):
    city = catalog.cities()['baltimore']
    year(2001)
    assert set(ENDED_HOBBIES) <= {item['id'] for item in decades.current(hobbies.catalogue()['hobbies'], city)}
    year(None)
    assert not set(ENDED_HOBBIES) & {item['id'] for item in decades.current(hobbies.catalogue()['hobbies'], city)}


def test_each_past_decade_keeps_the_profile_tabs_on_a_phone():
    modern = era_words.table()['words']['modern']
    for name, found in era_words.table()['decades'].items():
        words = {**modern, **found}
        assert len(words['messages_tab'] + words['posts_tab'] + 'MemoriesCharacter') <= 34, name


@pytest.mark.parametrize('name', DECADES)
def test_each_decade_has_a_hundred_memes_of_its_own(name):
    bank = memes.bank()
    rows = bank['decades'][name]
    assert len(rows) >= 100
    assert len({row[0] + row[1] for row in rows}) == len(rows)
    assert {row[2] for row in rows} <= set(bank['moods'])
    for row in rows:
        for line in row[:2]:
            assert '—' not in line and '–' not in line, line
            assert not content.matches(content.normalize(line)) & photos.NOT_FOR_MEMES, line
    # Every one fits by the end of its own decade.
    last = int(name[:4]) + 9
    assert all(memes.fits(row, last) for row in rows), [row for row in rows if not memes.fits(row, last)]


def test_a_meme_never_names_something_from_after_the_world_s_year():
    found = memes.rows_of('anytime', 1995)
    assert not [row for row in found if 'text' in (row[0] + row[1]).lower().split()]
    assert {tuple(row) for row in memes.bank()['decades']['1990s']} <= {tuple(row) for row in found}
    assert not {tuple(row) for row in memes.bank()['decades']['2000s']} & {tuple(row) for row in found}
    assert not [row for row in memes.rows_of('social', 2009) if 'group chat' in row[0] + row[1]]
    assert [row for row in memes.rows_of('social', 2015) if 'group chat' in row[0] + row[1]]
    # The present keeps the bank as it was.
    assert memes.rows_of('anytime', None) == memes.bank()['situations']['anytime']
    for situation in memes.bank()['situations']:
        assert len(memes.rows_of(situation, 1990)) >= 50, situation


def test_a_meme_in_a_past_year_comes_from_that_year():
    for index in range(60):
        meme = memes.choose(None, 14, f'seed-{index}', choice=True, year=1993)
        assert memes.fits([meme['top'], meme['bottom']], 1993), meme
