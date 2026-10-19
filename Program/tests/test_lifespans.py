"""Lifespans for elves and other long-lived people (companion/world/lifespans.py): a life age beside the real one."""
import copy
from datetime import date

from conftest import reconcile

from companion.database import decode
from companion.life import ages, big_turns, circle, loss, parenthood
from companion.world import catalog, couples, dating, generators, intimacy, lifespans, townsfolk, turnover

ELF = {'name': 'Aerin Leafmantle', 'identity': 'Aerin is an elf, 90. A quiet bookbinder. They/them.',
       'personality': 'Patient and dry.', 'timezone': 'UTC', 'home_city': 'baltimore'}


def connect(client, write=True):
    return client.app.state.database.connect(write=write)


def make(client, **changes) -> dict:
    response = client.post('/api/companion', json={**ELF, **changes})
    assert response.status_code == 200, response.text
    return client.get('/api/companion').json()['companion']


def test_life_age_is_the_real_age_for_a_human_and_stretched_after_childhood_for_others():
    assert [lifespans.life_age(age, 80) for age in (0, 9, 18, 34, 80, 101)] == [0, 9, 18, 34, 80, 101]
    assert [lifespans.life_age(age, 600) for age in (5, 17, 18, 100, 300, 550)] == [5, 17, 18, 27, 48, 75]
    assert lifespans.life_age(40, 55) == 55  # An orc is older at 40.
    assert lifespans.life_age(312, None) == 312 and lifespans.life_age(None, 600) is None
    for span in (55, 110, 180, 600, 1000):
        assert all(abs(lifespans.life_age(lifespans.real_age(life, span), span) - life) <= 1 for life in range(18, 90))
    assert lifespans.real_age(48, 600) == 300 and lifespans.real_age(12, 600) == 12


def test_kinds_come_from_their_own_words_never_from_a_word_inside_another_or_said_with_not():
    words = lifespans.from_words
    assert words('A half-elf ranger with a scar.') == 'half-elf' and words('Her elven ears twitch.') == 'elf'
    assert words('Stout, bearded, a dwarf of the iron hills.') == 'dwarf'
    assert words('She is not an elf, whatever her ears say.') == 'human'
    assert words('Keeps herself to a shelf of books.') == 'human' and words('') == 'human'
    assert lifespans.sheet_kind({'identity': 'An accountant.', 'kind': 'orc'}) == 'orc'
    assert lifespans.sheet_kind({'identity': 'An elf.', 'kind': 'nonsense'}) == 'elf'
    assert lifespans.sheet_lifespan({'identity': 'An elf.', 'lifespan': 1000}) == 1000
    assert lifespans.ageless({'identity': 'An immortal scholar.'}) and not lifespans.ageless(ELF)


def test_a_child_of_two_kinds_takes_a_listed_blend_else_the_longer_lived_parent():
    assert lifespans.blend('elf', 'human') == 'half-elf' and lifespans.blend('human', 'elf') == 'half-elf'
    assert lifespans.blend('dwarf', 'dwarf') == 'dwarf' and lifespans.blend('dwarf', 'halfling') == 'dwarf'
    assert lifespans.blend('orc', None) == 'human' and lifespans.blend('ageless', 'elf') == 'ageless'


def test_an_elf_of_300_has_the_odds_of_a_human_of_48(client):
    companion = make(client)
    definition = companion['version']['definition']
    with connect(client) as connection:
        elf = {'id': 'p1', 'role': 'mom', 'details': '{"age": 300, "folk": "elf"}'}
        human = {'id': 'p2', 'role': 'mom', 'details': '{"age": 48}'}
        today = date(2026, 10, 19)
        assert loss.facts_for(connection, elf, today, None, 2, definition=definition) == \
            loss.facts_for(connection, human, today, None, 2, definition=definition)
        assert loss.facts_for(connection, elf, today, None, 2)['age'] == 48
        # The companion's own: an elf of 90 is 26 in human terms, for big turns and the family odds alike.
        assert ages.companion_age(connection, companion['id'], definition, today) == 90
        assert big_turns.life_age_of(connection, companion, today) == 26
        assert big_turns.facts(connection, companion, today)['age'] == 26
        assert parenthood.age_of(connection, companion, None) == 26


def test_a_sheet_that_reads_as_a_minor_stays_one_whatever_its_kind(client):
    young = {**ELF, 'identity': 'An elf of 300 who is 15, an apprentice.'}
    assert intimacy.reads_as_minor(young)
    companion = make(client, identity=young['identity'])
    with connect(client, False) as connection:
        assert big_turns.age_of(connection, companion, date(2026, 10, 19)) is None
        assert big_turns.life_age_of(connection, companion, date(2026, 10, 19)) is None


def test_grandport_elves_are_often_centuries_old_and_the_same_seed_gives_the_same_person():
    data = catalog.city('grandport')
    assert data['names']['groups']['elven']['kind'] == 'elf' and not data.get('import_notes')
    elves = [seed for seed in (f'town:grandport:test:{n}' for n in range(4000)) if townsfolk.folk_of(data, seed) == 'elf']
    assert elves and all(townsfolk.folk_of(data, seed) == 'human' for seed in ('a', 'b') if seed not in elves)
    real = [townsfolk.seeded_real_age(data, seed, True) for seed in elves]
    assert max(real) > 100 and real == [townsfolk.seeded_real_age(data, seed, True) for seed in elves]
    # Their job and retiring follow their age in human terms: nobody's turned away for being 300.
    assert all(lifespans.life_age(age, 600) <= 84 for age in real)
    # A city with no long-lived people never pays for working out kinds in turnover.
    assert townsfolk.lifespan_of_seed(catalog.city('baltimore')) is None
    assert townsfolk.lifespan_of_seed(data)(elves[0]) == 600


def test_a_long_lived_townsperson_seldom_retires_or_passes_away():
    old_human = turnover.chances('staff', 70, 2, 3)
    elf_of_400 = turnover.chances('staff', lifespans.life_age(400, 600), 2, 3)
    assert elf_of_400['passed'] < old_human['passed'] / 2 and elf_of_400['retired'] == 0.0
    levels = ((), 2, 3, 2)
    left = [turnover.tenure(f's{n}', 'staff', 70, turnover.START_WEEK, levels) for n in range(300)]
    stayed = [turnover.tenure(f's{n}', 'staff', 400, turnover.START_WEEK, levels, 'modern', 600) for n in range(300)]
    passed = sum(1 for item in left if item and item[1] in ('passed', 'retired'))
    assert sum(1 for item in stayed if item and item[1] in ('passed', 'retired')) < passed / 3


def test_relatives_share_the_companions_kind_and_their_ages_follow_it():
    data = catalog.city('baltimore')
    made = generators.circle(data, seed='lifespans', size=8, folk='elf')
    parents = [person for person in made['people'] if person['role'] in ('parent', 'sibling')]
    assert parents and all(person['folk'] == 'elf' and person['age'] > 100 for person in parents)
    friends = [person for person in made['people'] if person['role'] in ('close-friend', 'friend', 'coworker')]
    assert friends and all('folk' not in person and person['age'] < 100 for person in friends)
    assert generators.circle(data, seed='lifespans', size=8) == generators.circle(data, seed='lifespans', size=8)
    people = circle.from_city(data, ELF, 'timeline-1', 8)
    relatives = [person for person in people if circle.role_kind(person['role']) in ('parent', 'sibling')]
    assert relatives and all(person['details']['folk'] == 'elf' for person in relatives)


def test_dating_and_town_couples_go_by_age_in_human_terms():
    data = catalog.city('grandport')
    sheet = {**townsfolk.resident(data, 'gran-porte', 3), 'age': 300, 'folk': 'elf'}
    found = dating.details(sheet, data)
    assert found['life'] == 48 and found['age_range'][1] <= 60
    profile = {'age': 47, 'age_min': 40, 'age_max': 55, 'interested_in': [found['gender']],
               'looking_for': found['looking'], 'gender': (found['drawn_to'] or ['woman'])[0], 'seed': 'me'}
    assert dating.suits(sheet, found, profile) == (found['looking'] != 'no')
    partner = couples.partner(sheet, data, 0, found)
    assert 38 <= lifespans.life_age(partner['age'], lifespans.lifespan_of(partner.get('folk'), data)) <= 58


def test_a_city_file_can_change_a_lifespan_and_add_a_kind_and_a_bad_entry_is_dropped():
    raw = copy.deepcopy(catalog.city('grandport'))
    for key in ('data_version', 'import_notes'):
        raw.pop(key, None)
    raw['kinds'] = {'elf': {'lifespan': 750}, 'tiefling': {'label': 'Tiefling', 'lifespan': 110, 'words': ['tiefling']},
                    'giant': {'label': 'Giant', 'lifespan': 9000, 'words': ['giant']},
                    'sprite': {'lifespan': 30}, 'nameless': {'lifespan': 200}}
    raw['names']['groups']['pictish']['kind'] = 'tiefling'
    raw['names']['groups']['far-voyagers']['kind'] = 'troll'
    data = catalog.prepare(raw, mend=True)
    assert data['kinds'] == {'elf': {'lifespan': 750},
                             'tiefling': {'label': 'Tiefling', 'lifespan': 110, 'words': ['tiefling']}}
    notes = ' '.join(data['import_notes'])
    assert all(word in notes for word in ('giant', 'sprite', 'nameless', 'troll'))
    assert 'kind' not in data['names']['groups']['far-voyagers']
    assert lifespans.lifespan_of('elf', data) == 750 and lifespans.lifespan_of('elf') == 600
    assert lifespans.from_words('A tiefling bard.', data) == 'tiefling' and lifespans.from_words('A tiefling.') == 'human'
    assert lifespans.of_group(data, 'pictish') == 'tiefling'
    # The user's own pick wins over the city's.
    assert lifespans.lifespan_of('elf', data, 300) == 300


def test_the_companions_relatives_carry_their_kind(client):
    companion = make(client)
    reconcile(client)
    with connect(client, False) as connection:
        rows = circle.people(connection, companion['active_timeline_id'])
    relatives = [row for row in rows if circle.role_kind(row['role']) in ('parent', 'sibling')]
    assert relatives and all(decode(row['details']).get('folk') == 'elf' for row in relatives)
