"""Lifespans for elves and other long-lived people (companion/world/lifespans.py): a life age beside the real one."""
import copy
from datetime import date

from conftest import reconcile

from companion.database import decode, encode
from companion.life import ages, big_turns, circle, loss, parenthood
from companion.world import catalog, couples, dating, generators, intimacy, lifespans, looks, townsfolk, turnover

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


def test_an_elf_sibling_of_three_hundred_is_married_or_not_by_their_life_age():
    name = {'given': 'Tunde', 'pronouns': 'he/him'}
    assert isinstance(circle.married_sibling(None, 't1', name, 300, 'Fernwhisper'), dict)
    assert circle.married_sibling(None, 't1', name, 20, 'Fernwhisper') == {}


def test_milestone_birthdays_are_round_hundreds_and_fifties_for_a_long_lived_kind():
    assert [age for age in range(18, 120) if lifespans.milestone(age)] == [30, 40, 50, 60, 70, 80, 90, 100, 110]
    assert [age for age in range(18, 420) if lifespans.milestone(age, 600)] == [100, 150, 200, 250, 300, 350, 400]
    assert lifespans.milestone(40, 110) and not lifespans.milestone(40, 180) and lifespans.milestone(150, None)


def test_a_three_digit_age_is_read_only_for_a_long_lived_kind_and_drawn_the_age_they_look():
    assert looks.age_of({'identity': 'Aerin is an elf, 312. A bookbinder.'}, 's') == 312
    assert looks.age_of({'identity': 'A 450-year-old dwarf smith.'}, 's') == 450
    assert looks.age_of({'identity': 'She is 312 days sober, a 34-year-old nurse.'}, 's') == 34
    elf = looks.picture({'age': 312, 'looks_age': 48, 'pronouns': 'they/them'}, 'Aerin')
    assert 'forties' in elf and 'three hundred' not in elf


def test_an_elf_hears_their_age_in_human_terms_and_a_human_hears_nothing_new(client, clock):
    companion = make(client, identity='Aerin is an elf, 312. A quiet bookbinder. They/them.')
    definition = companion['version']['definition']
    today = clock.now().date()
    with connect(client) as connection:
        assert ages.age_line(connection, companion['id'], definition, today) == 'You are 312, about 49 in human terms.'
        human = {**definition, 'identity': 'Aerin is 34. A quiet bookbinder. They/them.'}
        assert ages.age_line(connection, companion['id'], human, today) is None


def test_the_user_picks_a_circle_persons_kind_and_their_life_age_follows(client):
    make(client)
    reconcile(client)
    people = client.get('/api/life/circle').json()
    person = next(item for item in people if item.get('folk') == 'elf' and (item.get('age') or 0) >= 30)
    assert person['kind']['kind'] == 'elf'  # Aerin's relatives share Aerin's kind.
    changed = client.put(f"/api/life/circle/{person['id']}/kind", json={'kind': 'dwarf', 'lifespan': 1000})
    assert changed.status_code == 200, changed.text
    shown = changed.json()['kind']
    assert shown['kind'] == 'dwarf' and shown['own'] == 1000 and shown['years'] == 1000 and shown['kind_years'] == 300
    assert client.put(f"/api/life/circle/{person['id']}/kind", json={'kind': 'dragon', 'lifespan': None}).status_code == 422
    assert client.put(f"/api/life/circle/{person['id']}/kind", json={'kind': '', 'lifespan': 123}).status_code == 422
    back = client.put(f"/api/life/circle/{person['id']}/kind", json={'kind': '', 'lifespan': 0}).json()['kind']
    assert back['kind'] == 'elf' and back['years'] is None
    kinds = client.get('/api/life/kinds').json()
    assert {'human', 'elf', 'half-elf', 'dwarf', 'halfling', 'orc', 'ageless'} <= {item['id'] for item in kinds['kinds']}
    assert kinds['spans'] == [80, 150, 300, 600, 1000]


def test_the_character_page_reads_their_kind_from_their_words_until_the_user_picks(client):
    companion = make(client)
    definition = companion['version']['definition']
    found = client.post('/api/companion/looks', json={'definition': definition}).json()['kind']
    assert found['found'] == 'elf' and found['kind'] == 'elf' and found['years'] == 600 and found['own'] is None
    picked = client.post('/api/companion/looks', json={'definition': {**definition, 'kind': 'orc'}}).json()['kind']
    assert picked['found'] == 'elf' and picked['kind'] == 'orc' and picked['years'] == 55


def test_a_child_of_an_elf_and_a_human_is_a_half_elf_until_the_user_picks(client, clock, monkeypatch):
    from test_expecting import stage, started, to
    from test_our_child import ours
    row = started(client, monkeypatch, identity='She is an elf and a 31-year-old nurse.')
    to(client, clock, stage(row, 'born')['on'])
    [child] = ours(client)['children']
    assert child['kind']['kind'] == 'half-elf' and child['kind']['found'] == 'half-elf' and child['kind']['picked'] == ''
    assert child['kind']['from_parents']
    changed = client.put(f"/api/life/steps/ours/{child['id']}/kind", json={'kind': 'elf', 'lifespan': None})
    assert changed.status_code == 200, changed.text
    [child] = changed.json()['children']
    assert child['kind']['kind'] == 'elf' and child['kind']['picked'] == 'elf' and child['kind']['found'] == 'half-elf'


def test_doesnt_age_on_the_character_page_is_a_lifespan_of_its_own_beside_keeps_their_age(client):
    companion = make(client)
    definition = companion['version']['definition']
    assert lifespans.ageless({**definition, 'lifespan': 0}) and not lifespans.ageless({**definition, 'lifespan': 1000})
    shown = client.post('/api/companion/looks', json={'definition': {**definition, 'lifespan': 0}}).json()['kind']
    assert shown['years'] is None and shown['own'] == 0
    assert client.post('/api/companion', json={**ELF, 'lifespan': 20}).status_code == 422


def test_an_elfs_other_parent_is_a_human_near_their_age_in_human_terms(client):
    from companion.characters import current
    from companion.life import kids
    make(client, identity='Aerin is an elf, 312. A quiet bookbinder with two children. They/them.')
    with connect(client) as connection:
        companion = current(connection)
        person_id = kids.add_other(connection, companion, client.app.state.life.world, {}, client.app.state.database.clock.now())
        details = decode(connection.execute('SELECT details FROM circle_people WHERE id=?', (person_id,)).fetchone()['details'])
    assert 40 <= details['age'] <= 60 and not details.get('folk')


def test_a_city_file_whose_kinds_block_is_the_wrong_shape_still_loads():
    for block in ({'elf': 750}, [{'elf': {'lifespan': 750}}], 'elves'):
        raw = copy.deepcopy(catalog.city('grandport'))
        for key in ('data_version', 'import_notes', 'builtin', 'origin'):
            raw.pop(key, None)
        raw['kinds'] = block
        data = catalog.prepare(raw, mend=True)
        assert 'kinds' not in data and any('kind' in note for note in data['import_notes'])
        assert lifespans.lifespan_of('elf', data) == 600


def test_a_city_file_cannot_change_how_long_humans_live_or_make_doesnt_age_age():
    raw = copy.deepcopy(catalog.city('grandport'))
    for key in ('data_version', 'import_notes', 'builtin', 'origin'):
        raw.pop(key, None)
    raw['kinds'] = {'human': {'lifespan': 120}, 'ageless': {'lifespan': 500}, 'elf': {'lifespan': 750}}
    data = catalog.prepare(raw, mend=True)
    assert data['kinds'] == {'elf': {'lifespan': 750}}
    notes = ' '.join(data['import_notes'])
    assert '"human"' in notes and '"ageless"' in notes
    assert lifespans.lifespan_of('human', data) == 80 and lifespans.lifespan_of('ageless', data) is None
    assert lifespans.sheet_lifespan({'identity': 'A baker.'}, data) == 80


def test_an_elf_starts_a_family_by_their_age_in_human_terms(client, monkeypatch):
    from companion.life import families, own_family
    companion = make(client, identity='Aerin is an elf, 150. A quiet bookbinder. He/him.', relationship='friendship')
    monkeypatch.setattr(own_family, 'pair', lambda *_args: {'how': 'married'})
    today = date(2026, 10, 19)
    elder = {'id': 'p9', 'role': 'sister', 'details': '{"age": 150, "folk": "elf"}'}
    with connect(client) as connection:
        assert own_family.ready(connection, companion, today)  # 150 is 32 in human terms.
        # Their elf partner of 200 (37 in human terms) can carry; a human partner of 50 can't.
        for age, folk, carries in ((200, 'elf', True), (50, None, False)):
            details = {'pronouns': 'she/her', 'age': age} | ({'folk': folk} if folk else {})
            found = own_family.route(connection, companion, {'details': encode(details)}, 's', 'medieval', today)
            assert (found == 'partner') == carries, (age, found)
        # A sister of 150 in their circle could be expecting.
        assert [person['id'] for person, _how in families.eligible(connection, 't', [elder], today)] == ['p9']


def test_an_elven_townsperson_who_takes_over_stays_an_elf_of_their_age():
    from companion import cast
    data = catalog.city('grandport')
    sheet = next(found for hood in data['neighborhoods'] for index in range(400)
                 if (found := townsfolk.resident(data, hood['id'], index)).get('folk') == 'elf' and found['age'] > 120)
    definition = cast.profile(data, sheet, {'meetings': [], 'in_story': None, 'focus': None, 'match': None},
                              date(2026, 10, 19))
    assert definition['kind'] == 'elf' and lifespans.sheet_kind(definition, data) == 'elf'
    assert looks.age_of(definition, 's') == sheet['age']


def test_an_elf_on_the_dating_app_is_drawn_the_age_they_look():
    from companion import dating_photos
    data = catalog.city('grandport')
    sheet = {**townsfolk.resident(data, 'gran-porte', 3), 'age': 300, 'folk': 'elf'}
    prompt = dating_photos.inputs(sheet, data)['prompt']
    assert '48 years old' in prompt and '300' not in prompt


def test_a_citys_own_kind_shows_on_a_persons_page_and_can_be_picked(client):
    raw = copy.deepcopy(catalog.city('grandport'))
    for key in ('data_version', 'import_notes', 'builtin', 'origin'):
        raw.pop(key, None)
    raw |= {'id': 'tiefport', 'name': 'Tiefport',
            'kinds': {'elf': {'lifespan': 750}, 'tiefling': {'label': 'Tiefling', 'lifespan': 200, 'words': ['tiefling']}}}
    assert client.post('/api/world/cities', json=raw).status_code == 200
    make(client, identity='Aerin is a tiefling, 100. A bard. They/them.', home_city='tiefport',
         location='Gran Porte, Tiefport')
    reconcile(client)
    people = client.get('/api/life/circle').json()
    relatives = [person for person in people if person.get('folk')]
    assert relatives and all(person['kind']['label'] == 'Tiefling' and person['kind']['years'] == 200
                             for person in relatives)
    friend = next(person for person in people if not person.get('folk'))
    picked = client.put(f"/api/life/circle/{friend['id']}/kind", json={'kind': 'tiefling', 'lifespan': None})
    assert picked.status_code == 200, picked.text
    assert picked.json()['kind']['kind'] == 'tiefling'
    elf = client.put(f"/api/life/circle/{friend['id']}/kind", json={'kind': 'elf', 'lifespan': None}).json()['kind']
    assert elf['years'] == 750


def test_a_grown_kid_of_an_elf_and_a_human_is_a_half_elf(client, clock, monkeypatch):
    from datetime import timedelta

    from companion.life import kids
    monkeypatch.setattr(kids, 'ACTIVE', True)
    make(client, identity='Aerin is an elf, 312. A quiet bookbinder. She/her.', relationship='romance',
         background='Her son Leo, 17, and her daughter Mia, 4.')
    reconcile(client)
    clock.advance(timedelta(days=370))
    reconcile(client)
    [leo] = [person for person in client.get('/api/life/circle').json() if person['name'] == 'Leo']
    assert leo['role'] == 'son' and leo['age'] == 18 and leo['kind']['kind'] == 'half-elf'


def test_a_child_of_two_of_a_citys_own_kind_is_that_kind(client, clock, monkeypatch):
    from test_expecting import stage, started, to
    from test_our_child import ours
    raw = copy.deepcopy(catalog.city('grandport'))
    for key in ('data_version', 'import_notes', 'builtin', 'origin'):
        raw.pop(key, None)
    raw |= {'id': 'tiefport', 'name': 'Tiefport',
            'kinds': {'tiefling': {'label': 'Tiefling', 'lifespan': 200, 'words': ['tiefling']}}}
    assert client.post('/api/world/cities', json=raw).status_code == 200
    client.put('/api/persona', json={'name': 'Sam', 'about': 'A tiefling smith.'})
    row = started(client, monkeypatch, identity='She is a tiefling and a 31-year-old nurse.', home_city='tiefport',
                  location='Gran Porte, Tiefport')
    to(client, clock, stage(row, 'born')['on'])
    [child] = ours(client)['children']
    assert (child['kind']['label'], child['kind']['years']) == ('Tiefling', 200)


def test_a_persona_can_be_an_elf_of_300_once_the_kind_is_picked_or_read_from_their_words(client):
    make(client)
    persona = client.get('/api/worlds').json()['persona']
    url = f"/api/worlds/personas/{persona['id']}"
    shown = persona['kind_shown']
    assert shown['kind'] == 'human' and shown['found_label'] == 'Human' and shown['picked'] == ''
    assert {'id': 'elf', 'label': 'Elf', 'lifespan': 600} in shown['kinds']
    # Past 120 only for a long-lived kind; a human or a halfling stays at 120 at most.
    refused = client.patch(url, json={'age': 300})
    assert refused.status_code == 422 and 'long-lived kind' in refused.text
    assert client.patch(url, json={'age': 300, 'kind': 'halfling'}).status_code == 422
    assert client.patch(url, json={'age': 120}).status_code == 200
    assert client.patch(url, json={'age': 5001, 'kind': 'elf'}).status_code == 422
    assert client.patch(url, json={'kind': 'sprite'}).status_code == 422
    assert client.patch(url, json={'lifespan': 250}).status_code == 422
    picked = client.patch(url, json={'age': 300, 'kind': 'elf'})
    assert picked.status_code == 200, picked.text
    shown = picked.json()['persona']['kind_shown']
    assert shown['kind'] == 'elf' and shown['picked'] == 'elf' and shown['life_age'] == 48
    with connect(client, write=False) as connection:
        row = connection.execute('SELECT * FROM persona WHERE id=1').fetchone()
        assert (row['kind'], row['age']) == ('elf', 300) and ages.persona_life_age(connection, dict(row)) == 48
        assert parenthood.persona(connection)['kind'] == 'elf'
        from companion import dating as matchlight
        assert matchlight.persona(connection)['age'] == 48  # Matchlight's profile starts in human terms.
    # "Doesn't age" is long-lived too; back to the app's pick with an age past 120 is refused.
    assert client.patch(url, json={'kind': '', 'lifespan': 0}).status_code == 200
    assert client.patch(url, json={'lifespan': None}).status_code == 422
    # Read from their words: an elf by About you may be 300 with no pick.
    words = client.patch(url, json={'about': 'An elf, a ranger from the old woods.', 'lifespan': None})
    assert words.status_code == 200, words.text
    shown = words.json()['persona']['kind_shown']
    assert shown['found'] == 'elf' and shown['picked'] == '' and shown['kind'] == 'elf'


def test_a_new_persona_can_be_made_an_elf(client):
    make(client)
    made = client.post('/api/worlds/personas', json={'name': 'Lorien', 'age': 250, 'kind': 'elf'})
    assert made.status_code == 200, made.text
    assert made.json()['kind'] == 'elf' and made.json()['age'] == 250
    assert client.post('/api/worlds/personas', json={'name': 'Tom', 'age': 250}).status_code == 422


def test_becoming_an_elven_townsperson_makes_an_elf_persona_of_their_real_age():
    from companion import worlds
    data = catalog.city('grandport')
    sheet = next(found for hood in data['neighborhoods'] for index in range(400)
                 if (found := townsfolk.resident(data, hood['id'], index)).get('folk') == 'elf' and found['age'] > 120)
    persona = worlds.persona_for(data, sheet, date(2026, 10, 19), '2026-10-19T00:00:00Z')
    assert persona['kind'] == 'elf' and persona['age'] == sheet['age'] and persona['lifespan'] is None
    assert lifespans.persona_kind(persona, data) == 'elf'
    assert lifespans.long_lived(lifespans.persona_lifespan(persona, data))
    human = next(found for index in range(50)
                 if (found := townsfolk.resident(data, data['neighborhoods'][0]['id'], index)).get('folk') in (None, 'human'))
    assert worlds.persona_for(data, human, date(2026, 10, 19), '2026-10-19T00:00:00Z')['kind'] == ''


def test_an_elven_townsperson_past_200_still_has_a_life_story_to_tell():
    from companion import cast
    from companion.world import life_details
    data = catalog.city('grandport')
    sheet = next(found for hood in data['neighborhoods'] for index in range(1200)
                 if (found := townsfolk.resident(data, hood['id'], index)).get('folk') == 'elf' and found['age'] > 200)
    found = life_details.for_sheet(data, sheet)
    assert found['origin'] and found['family'] and len(found['stories']) == life_details.STORIES
    assert life_details.revealed(data, sheet, 20)['stories']
    definition = cast.profile(data, sheet, {'meetings': [], 'in_story': None, 'focus': None, 'match': None},
                              date(2026, 10, 19))
    assert sheet['name'] in definition['background'] and definition['kind'] == 'elf'


def test_a_matchlight_card_for_an_elf_gives_their_age_in_human_terms():
    data = catalog.city('grandport')
    elf = {**townsfolk.resident(data, 'gran-porte', 3), 'age': 225, 'folk': 'elf'}
    card = dating.card(elf, data, date(2026, 10, 19))
    assert card['age'] == 225 and card['life_age'] == dating.life_of(elf, data) == 40
    human = {**townsfolk.resident(data, 'gran-porte', 3), 'age': 34, 'folk': 'human'}
    assert dating.card(human, data, date(2026, 10, 19))['life_age'] is None


def test_the_prompt_gives_an_elf_personas_age_in_human_terms(client):
    from companion.memory import context
    make(client)
    persona = client.get('/api/worlds').json()['persona']
    url = f"/api/worlds/personas/{persona['id']}"
    assert client.patch(url, json={'name': 'Sam', 'age': 34, 'about': 'A ranger.'}).status_code == 200
    with connect(client, write=False) as connection:
        assert '- Age: 34\n' in context.persona_text(connection)
    assert client.patch(url, json={'age': 312, 'kind': 'elf'}).status_code == 200
    with connect(client, write=False) as connection:
        assert '- Age: 312 (an elf; about 49 in human terms)\n' in context.persona_text(connection)
    assert client.patch(url, json={'kind': '', 'about': 'A dwarven smith.', 'age': 150}).status_code == 200
    with connect(client, write=False) as connection:
        assert '- Age: 150 (a dwarf; about 47 in human terms)\n' in context.persona_text(connection)
    assert client.patch(url, json={'lifespan': 0}).status_code == 200
    with connect(client, write=False) as connection:
        assert "- Age: 150 (doesn't age)\n" in context.persona_text(connection)
