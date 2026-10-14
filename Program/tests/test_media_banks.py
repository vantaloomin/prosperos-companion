"""The title banks behind Reading, watching and listening (companion/world/data/media/*.json)."""
import json
import re

import pytest

from companion.life import media

FORMATS = set(media.SHOW_DAYS)
# Each era's bank and the years a city of that era sees: at least 100 titles of every kind in each.
ERAS = (('modern', 2026), ('nineteenth', 1885), ('nineteenth', 1890), ('nineteenth', 1895), ('jazz-age', 1925), ('jazz-age', 1926),
        ('tales', None), ('future', None))


@pytest.mark.parametrize(('bank_id', 'year'), ERAS)
def test_every_era_has_at_least_100_specific_titles_of_each_kind(bank_id, year):
    for kind in media.KINDS:
        found = media.candidates({'bank': bank_id, 'year': year}, kind, set())
        assert len(found) >= 100, (bank_id, year, kind, len(found))


@pytest.mark.parametrize('bank_id', ['modern', 'nineteenth', 'jazz-age', 'tales', 'future'])
def test_banks_are_well_formed(bank_id):
    raw = json.loads((media.BANKS / f'{bank_id}.json').read_text(encoding='utf-8'))
    found = media.bank(bank_id)
    assert found['real'] is (bank_id in ('modern', 'nineteenth', 'jazz-age'))
    for kind in media.KINDS:
        titles = [item['title'].casefold() for item in found[kind]]
        assert len(titles) == len(set(titles)), kind
        for title, by, year, tags in raw[kind]:
            assert title.strip() == title and len(title) <= 120 and len(by) <= 80
            assert (year > 0) is found['real'], title
            assert tags.split(), title
        if kind == 'show':
            assert all(item['format'] in FORMATS for item in found[kind])


def test_no_lyrics_or_quotes_ship_only_titles():
    for bank_id in ('modern', 'nineteenth', 'jazz-age', 'tales', 'future'):
        text = (media.BANKS / f'{bank_id}.json').read_text(encoding='utf-8')
        assert '\\n' not in text
        for kind in media.KINDS:
            for item in media.bank(bank_id)[kind]:
                assert len(item['title'].split()) <= 16 and not re.search(r'[\n♪♫]', item['title'])
