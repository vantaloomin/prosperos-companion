"""Townsfolk life details: facts and stories drawn by seed from a bank (companion/world/life_details.py)."""
import re
from collections import Counter
from datetime import date

from test_perception import GENDERED

from companion import cast
from companion.life import encounters
from companion.world import catalog, life_details, townsfolk

PLACEHOLDER = re.compile(r'\{(\w+)\}')
ALLOWED = {'origins': {'hood', 'city'}, 'pets': {'pet'}}


def every_phrase(bank: dict):
    for kind, entries in bank.items():
        if kind == 'about':
            continue
        for entry in entries:
            if isinstance(entry, str):
                yield kind, entry
                continue
            for field in ('seen', 'told'):
                for text in [*entry.get(field, []), *(entry.get('period') or {}).get(field, [])]:
                    yield kind, text


def test_the_bank_is_big_and_safe_to_say_about_anyone():
    bank = life_details.bank()
    assert len(bank['anecdotes']) >= 100 and len(bank['origins']) >= 40 and len(bank['likes']) >= 60
    assert len(bank['family']) >= 50 and len(bank['pets']) >= 20 and len(bank['leaving']) >= 40
    phrases = list(every_phrase(bank))
    repeated = [text for text, count in Counter(text for _kind, text in phrases).items() if count > 1]
    assert not repeated, repeated[:5]
    for kind, text in phrases:
        assert not GENDERED.search(text), (kind, text)
        assert '"' not in text and text == text.strip() and not text.endswith('.'), (kind, text)
        assert kind == 'pet_names' or text[:1].islower(), (kind, text)
        assert set(PLACEHOLDER.findall(text)) <= ALLOWED.get(kind, set()), (kind, text)
    for entry in bank['pets']:
        assert all('{pet}' in text for text in entry['seen']), entry['id']
    for entry in [*bank['origins'], *bank['family'], *bank['pets'], *bank['likes'], *bank['anecdotes']]:
        for field, texts in (entry.get('period') or {}).items():
            assert len(texts) == len(entry[field]), entry['id']


def test_the_same_person_always_has_the_same_life():
    data = catalog.city('baltimore')
    sheet = townsfolk.at_place(data, data['places'][0]['id'])[0]
    found = life_details.for_sheet(data, sheet)
    assert found == life_details.for_sheet(data, sheet)
    assert found['origin'] and '{' not in found['origin'] and len(found['likes']) == 2
    assert len(found['stories']) == life_details.STORIES and found['family']


def test_work_history_fits_their_age_and_job():
    data = catalog.city('baltimore')
    people = [sheet for place in data['places'][:40] for sheet in townsfolk.at_place(data, place['id'])]
    people += townsfolk.residents(data, data['neighborhoods'][0]['id'])
    for sheet in people:
        lines = life_details.work(data, sheet, townsfolk.drawn(sheet))
        if sheet['occupation'] == 'retired':
            assert lines[0].startswith('retired after'), lines
        if sheet['staff']:
            assert lines[0].startswith(f"has worked at {sheet['place']['name']}"), lines
        if sheet['age'] < 21 and not sheet['staff']:
            assert lines == [], (sheet['age'], lines)


def test_a_companion_learns_their_life_meeting_by_meeting():
    data = catalog.city('baltimore')
    sheet = townsfolk.at_place(data, data['places'][0]['id'])[0]
    found = life_details.for_sheet(data, sheet)
    assert life_details.revealed(data, sheet, 0) == {'facts': [], 'stories': []}
    assert life_details.revealed(data, sheet, 1) == {'facts': [found['origin']], 'stories': []}
    second = life_details.revealed(data, sheet, 2)['facts']
    assert found['likes'][0] in second and found['family'][0] not in second
    assert found['family'][0] in life_details.revealed(data, sheet, 3)['facts']
    assert life_details.revealed(data, sheet, 4)['stories'] == found['stories'][:1]
    assert life_details.revealed(data, sheet, 20)['stories'] == found['stories']
    assert life_details.newly_told(data, sheet, 3) is None
    assert life_details.newly_told(data, sheet, 5) == found['stories'][1]
    assert life_details.newly_told(data, sheet, 20) is None
    person = {'key': sheet['key'], 'full': sheet['full'], 'age': sheet['age'], 'kind': sheet['kind'],
              'role': sheet['role'], 'staff': sheet['staff'], 'place': sheet['place'], 'neighborhood': 'Canton',
              'temperament': sheet['temperament'], 'quirk': sheet['quirk'], 'times': 4, 'last_met': '2026-03-02',
              'last_place': sheet['place']['name'], 'goal': None, 'flaw': None,
              **life_details.revealed(data, sheet, 4)}
    text = encounters.text(person)
    assert found['origin'] in text and f"the time they {found['stories'][0]}" in text


def test_nobody_at_one_place_or_on_one_street_tells_the_same_story():
    data = catalog.city('baltimore')
    groups = [townsfolk.at_place(data, place['id']) for place in data['places'][:30]]
    groups.append(townsfolk.residents(data, data['neighborhoods'][0]['id'])[:20])
    for people in groups:
        told = [story for sheet in people for story in life_details.for_sheet(data, sheet)['stories']]
        assert len(told) == len(set(told)), people[0]['key']


def test_period_towns_and_new_main_characters_get_their_life_too():
    data = catalog.city('london-1895')
    sheet = townsfolk.at_place(data, data['places'][0]['id'])[0]
    found = life_details.for_sheet(data, sheet)
    assert found['origin'] and found['stories']
    modern = catalog.city('baltimore')
    sheet = townsfolk.at_place(modern, modern['places'][0]['id'])[0]
    definition = cast.profile(modern, sheet, {'meetings': [], 'in_story': None, 'match': None,
                                              'focus': {'version': {'name': 'Mira'}}}, date(2026, 3, 2))
    assert life_details.for_sheet(modern, sheet)['origin'] in definition['background']
    assert life_details.for_sheet(modern, {**sheet, 'cast': 'someone'}) == {}


def test_goals_are_a_big_bank_the_town_can_use():
    bank = townsfolk.GOAL_BANK
    assert len(bank) >= 100 and len({goal['id'] for goal in bank}) == len(bank)
    lines = [goal[field] for goal in bank for field in ('text', 'period', 'progress', 'done')]
    assert len(lines) == len(set(lines))
    for goal in bank:
        assert 2 <= goal['steps'] <= 8 and goal['interest'], goal['id']
        assert goal['practice'] is None or (goal['practice'][0] in townsfolk.GOAL_KINDS
                                            and goal['practice'][1] in ('morning', 'afternoon', 'evening')), goal['id']
        for field in ('text', 'period', 'progress', 'done', 'interest'):
            assert not GENDERED.search(goal[field]) and '"' not in goal[field], (goal['id'], field)
            assert not goal[field].endswith('.'), (goal['id'], field)
        assert goal['progress'].startswith('{name}') and goal['done'].startswith('{name}'), goal['id']
        assert goal['bio'][-1] in '.!?' and not GENDERED.search(goal['bio']), goal['id']
    for quirk in townsfolk.QUIRK_BANK:
        assert quirk['text'][:1].islower() and not quirk['text'].endswith('.'), quirk['text']
        assert quirk['bio'][-1] in '.!?' and not GENDERED.search(quirk['text'] + ' ' + quirk['bio']), quirk['text']
