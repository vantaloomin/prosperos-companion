"""Where the companion stands at work (companion/life/position.py, v1.5.0): runs the place, manages people, or works
for someone. Tester 2026-11-25: Sett runs the fighting pits and still heard "There are rumors of layoffs at Sett's
work"."""
from datetime import date, timedelta

import pytest
from conftest import reconcile, set_life

from companion.characters import require_current
from companion.database import encode, identifier
from companion.life import body, casting, composer, pacing, position, shared_storylines, status, storylines, work
from companion.world import catalog

WORKDAY = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '16:00', 'end': '23:30', 'days': [2, 3, 4, 5, 6]},
           {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '02:00', 'end': '10:00'}]

# Card phrasings, the way people write them: what each says of the companion's own place at work.
PHRASINGS = {
    # Owners.
    'Sett is the Boss: the man who runs the underground fighting pits.': 'owner',
    'He owns the operation, makes the big decisions and manages his fighters.': 'owner',
    'Now he owns the Great Pit and the dice dens under the city.': 'owner',
    "He is the Boss of the Boss's Office, the biggest fighting venue in town.": 'owner',
    'She runs a small bakery on Elm Street.': 'owner',
    'She co-owns a bookshop with her partner.': 'owner',
    'She is the proprietor of the Green Dragon.': 'owner',
    'She works out of her own studio.': 'owner',
    'She runs her own business from home.': 'owner',
    'Noodle bar owner': 'owner',
    # Managers.
    "He is the head chef at Luca's.": 'lead',
    'She is a shift supervisor at the warehouse.': 'lead',
    'She manages the bar staff at the Ritz.': 'lead',
    'He runs the kitchen at a busy diner.': 'lead',
    'She is head of marketing at a startup.': 'lead',
    'Detective sergeant at Scotland Yard.': 'lead',
    "She's in charge of the night shift crew.": 'lead',
    'Guesthouse manager': 'lead',
    # Nothing about where they stand: someone else's place, the past, a hope, a hobby, a pet.
    'She runs a marathon every spring.': '',
    'Her mother runs the family bakery.': '',
    'She dreams of owning her own bakery one day.': '',
    'He is saving up to open his own bar.': '',
    'She used to run a bar in Lisbon.': '',
    'She is a former bar owner.': '',
    'He is a proud dog owner.': '',
    'She owns a cat named Biscuit.': '',
    'She owns a studio apartment downtown.': '',
    'She owns a gym membership she never uses.': '',
    'She works as a bartender. Her manager is a jerk.': '',
    'She manages her anxiety with yoga.': '',
    'He has a thick head of hair.': '',
    "She's in charge of the kids on weekends.": '',
    'He works as a barista at a busy cafe.': '',
    "Innkeeper's hand": '',
    'Pit boss': '',
}


@pytest.mark.parametrize('text', PHRASINGS)
def test_the_card_words_say_where_they_stand(text):
    assert position.from_words(text) == PHRASINGS[text]


def test_the_users_pick_then_a_business_then_the_career_then_the_words():
    careers = catalog.careers_for(catalog.city('baltimore'))
    owner_words = {'identity': 'She runs a small bakery on Elm Street.'}
    assert position.of({'identity': 'She bakes bread.'}, None) == 'staff'
    assert position.of(owner_words, None) == 'owner'
    assert position.of({**owner_words, 'money': {'position': 'staff'}}, None) == 'staff'
    assert position.of({'business': {'business': 'a small bakery'}}, None) == 'owner'
    # A tagged career wins over the words; an untagged one leaves it to them, then to its own name.
    assert position.of(owner_words, {'name': 'Head chef', 'position': 'lead'}) == 'lead'
    assert position.of(owner_words, careers['barista']) == 'owner'
    assert position.of({}, {'name': 'Tavern owner'}) == 'owner'
    assert position.of({}, careers['barista']) == 'staff'
    # What the app would pick stays readable under the user's own.
    assert position.guess({**owner_words, 'money': {'position': 'lead'}}, None) == 'owner'


def test_the_built_in_owners_and_managers_are_tagged():
    future = catalog.careers_for(catalog.city('long-meridian'))
    assert future['noodle-bar-owner']['position'] == 'owner' and future['head-chef']['position'] == 'lead'
    tagged = {career_id: career['position'] for career_id, career in catalog.careers().items()
              if career.get('position')}
    assert tagged['grocer'] == 'owner' and 'barista' not in tagged
    assert catalog.careers_for(catalog.city('haddon-harbor'))['innkeeper']['position'] == 'owner'
    # Camelot's innkeeper is the innkeeper's hand: works for someone.
    assert not catalog.careers_for(catalog.city('camelot'))['innkeeper'].get('position')


def work_stories(held: str) -> set[str]:
    known = casting.Facts(position=held)
    return {story.key for story in storylines.STORIES if story.cast == 'work'
            and storylines.casts(story, [], {'schedule': WORKDAY}, known)}


def test_an_owner_never_draws_the_stories_that_need_a_boss():
    staff, owner = work_stories('staff'), work_stories('owner')
    assert len(staff) == 27
    assert {'layoff_rumors', 'promotion_chance', 'work_review', 'work_new_boss', 'work_raise', 'work_boss_clash',
            'work_poached', 'work_changing_hands', 'work_the_books', 'work_party'}.isdisjoint(owner)
    assert {'work_thank_you', 'work_short_handed', 'work_breakdown', 'work_inspection', 'work_gossip',
            'work_missing_money', 'work_back_room'} <= owner
    # Stories the user is part of follow the same rule.
    bossed = {key for key, story in shared_storylines.bank().items() if story.get('positions')}
    assert bossed == {'ask_for_more', 'new_at_work', 'what_would_you_do', 'proud_of_this'}
    assert all(set(shared_storylines.bank()[key]['positions']) == set(position.BOSSED) for key in bossed)


def test_nobody_in_charge_has_a_thinner_bank_than_staff():
    staff, lead, owner = work_stories('staff'), work_stories('lead'), work_stories('owner')
    assert len(owner) >= len(staff) and len(lead) >= len(staff)
    # Their own versions: thin takings for an owner and a cut to the team for a manager, never layoff rumors.
    assert 'owner_thin_takings' in owner and 'lead_cut_team' in lead and 'layoff_rumors' in staff
    assert 'layoff_rumors' not in lead and 'lead_cut_team' not in staff and not owner & lead - staff
    assert all(key.startswith('owner_') for key in owner - staff)
    assert all(key.startswith('lead_') for key in lead - staff)
    # Each level of drama has something for someone in charge.
    levels = {story.key: story.level for story in storylines.STORIES}
    assert {levels[key] for key in owner} == {0, 1, 2, 3} and {levels[key] for key in lead} == {0, 1, 2, 3}


def test_their_own_staff_have_an_owners_stories():
    staff_member = {'id': 'kai', 'seed': 'circle:t:kai', 'name': 'Kai', 'role': 'coworker', 'career': '',
                    'status': 'active', 'details': '{"works_with_companion": true}'}

    def drawn(held):
        known = casting.Facts(people=[staff_member], position=held)
        return {story.key for story in storylines.STORIES if story.cast == 'coworker'
                and storylines.casts(story, [staff_member], {'schedule': WORKDAY}, known)}
    assert 'coworker_leaving' in drawn('staff') and 'staff_leaving' not in drawn('staff')
    assert 'staff_leaving' in drawn('owner') and 'coworker_leaving' not in drawn('owner')
    assert 'coworker_lunches' in drawn('owner')


def test_a_business_the_app_started_gets_the_stories_of_whoever_runs_a_place():
    companion = {'active_timeline_id': 't', 'version': {'definition': {
        'schedule': WORKDAY, 'business': {'business': 'a small bakery', 'label': 'At the bakery'}}}}
    assert casting.companion_employed(None, companion)
    assert position.companion_position(None, companion) == 'owner'


def test_boss_lines_are_left_out_for_whoever_runs_the_place():
    assert 'brb, boss is here' in position.lines_for(pacing.LINES['work'], 'staff')
    assert 'brb, boss is here' not in position.lines_for(pacing.LINES['work'], 'owner')
    owner = {'identity': 'She owns a small bakery.', 'home_city': 'Baltimore'}
    lines = status.retro_away(owner, 'work')
    assert lines and not any('boss' in line for line in lines)
    assert any('boss' in line for line in status.retro_away({'identity': 'A clerk.', 'home_city': 'Baltimore'},
                                                            'work'))


@pytest.fixture
def sett(client, monkeypatch, provider):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(work, 'ACTIVE', True)
    response = client.post('/api/companion', json={
        'name': 'Sett', 'timezone': 'UTC', 'schedule': WORKDAY, 'home_city': 'Baltimore',
        'identity': 'Sett is the Boss: the man who runs the underground fighting pits.',
        'personality': 'Proud and loud'})
    assert response.status_code == 200, response.text
    set_life(client, automatic_events=True, phrase_with_model=False, work_realism=3)
    return response.json()


def revise(client, change):
    companion = client.get('/api/companion').json()['companion']
    definition = companion['version']['definition']
    response = client.post('/api/companion/versions', json={'definition': {**definition, **change(definition)},
                                                             'expected_version_id': companion['version']['id']})
    assert response.status_code == 200, response.text


def connect(client, write=True):
    return client.app.state.database.connect(write=write)


def test_sett_runs_the_place_and_has_a_good_or_flat_year_and_is_never_laid_off(client, sett, clock, monkeypatch):
    reconcile(client)
    with connect(client, write=False) as connection:
        assert position.companion_position(connection, require_current(connection)) == 'owner'
    monkeypatch.setattr(work, 'LAYOFF_WEEKLY', 1.0)
    today = clock.now().date()
    with connect(client) as connection:
        connection.execute("UPDATE work_life SET review_on=?, started_on='2020-01-01' WHERE timeline_id=?",
                           ((today + timedelta(days=1)).strftime('%m-%d'), sett['active_timeline_id']))
    clock.advance(timedelta(days=8))
    reconcile(client)
    view = client.get('/api/life/work').json()['work']
    assert view['status'] == 'working'
    kinds = {event['kind'] for event in view['events']}
    assert not kinds & {'raise', 'promotion', 'freeze', 'laid-off', 'quit'}
    [year] = [event for event in view['events'] if event['kind'] in ('good-year', 'flat-year')]
    assert year['text'].startswith(('a good year at the place: business up about ', 'a flat year at the place: business held steady'))
    # Not told in chat until its wording has been tried out.
    with connect(client, write=False) as connection:
        lines = work.context_lines(connection, require_current(connection), clock.now())
    assert lines and not any('takings' in text for _key, text in lines)


def test_someone_who_works_for_someone_still_has_their_review(client, sett, clock):
    revise(client, lambda _definition: {'identity': 'Sett fights in the pits for the house.'})
    reconcile(client)
    with connect(client) as connection:
        assert position.companion_position(connection, require_current(connection)) == 'staff'
        connection.execute("UPDATE work_life SET review_on=?, started_on='2020-01-01' WHERE timeline_id=?",
                           ((clock.now().date() + timedelta(days=1)).strftime('%m-%d'), sett['active_timeline_id']))
    clock.advance(timedelta(days=2))
    reconcile(client)
    kinds = {event['kind'] for event in client.get('/api/life/work').json()['work']['events']}
    assert kinds & {'raise', 'promotion', 'freeze'}


def test_a_running_layoff_story_ends_quietly_once_they_run_the_place(client, sett, clock):
    reconcile(client)
    today = clock.now().date()
    stages = [{'on': today.isoformat(), 'text': "There are rumors of layoffs at {name}'s work.", 'share': '',
               'tone': 'bad'},
              {'on': (today + timedelta(days=4)).isoformat(), 'text': '', 'share': '', 'tone': '',
               'pending': 'storyline:layoff_rumors:1'}]
    with connect(client) as connection:
        for key in ('layoff_rumors', 'work_breakdown'):
            connection.execute(
                'INSERT INTO storylines (id, timeline_id, story, level, cast_ids, stages, started_on, status, '
                "created_at) VALUES (?, ?, ?, 1, '[]', ?, ?, 'running', ?)",
                (identifier(), sett['active_timeline_id'], key, encode(stages), today.isoformat(),
                 clock.now().isoformat()))
        companion = require_current(connection)
        storylines.start_due(connection, companion, clock.now())
        found = {row['story']: row['status'] for row in connection.execute(
            'SELECT story, status FROM storylines WHERE timeline_id=?', (sett['active_timeline_id'],))}
    assert found['layoff_rumors'] == 'ended' and found['work_breakdown'] == 'running'


def test_a_year_of_storylines_for_an_owner_has_no_boss_in_it(client, sett, monkeypatch):
    monkeypatch.setattr(storylines, 'START', (1.0, 1.0, 1.0, 1.0))
    with connect(client) as connection:
        companion = require_current(connection)
        drawn = set()
        for offset in range(365):
            found = storylines.start(connection, companion, [], date(2026, 1, 1) + timedelta(days=offset), 3)
            if found:
                drawn.add(found['story'])
    work_keys = {story.key for story in storylines.STORIES if story.cast == 'work'}
    assert drawn & work_keys
    assert not drawn & {story.key for story in storylines.STORIES if not position.fits(story.positions, 'owner')}
    assert any(key.startswith('owner_') for key in drawn)


def test_the_form_shows_what_the_app_reads_them_as(client):
    # The Position picker's "Let the app decide: Runs the place" (PR 4): the app's read, whatever the user picked.
    def asked(identity, money=None):
        body = {'name': 'Sett', 'identity': identity, 'money': money or {}}
        return client.post('/api/world/cities/baltimore/position', json=body).json()['position']
    assert asked('Sett is the Boss: the man who runs the underground fighting pits.') == 'owner'
    assert asked('Sett is the Boss: the man who runs the pits.', {'position': 'staff'}) == 'owner'
    assert asked('Mara is the head chef at a bistro.') == 'lead'
    assert asked('Theo tends bar downtown.') == 'staff'
    assert asked('Theo is a freelance photographer.', {'employment': 'freelance'}) == ''
    assert asked('Theo studies.', {'career': 'undergraduate'}) == ''


def test_the_work_life_panel_says_who_runs_the_place(client, sett):
    reconcile(client)
    view = client.get('/api/life/work').json()['work']
    assert view['position'] == 'owner' and view['state'][0] == 'Runs the place.'
    revise(client, lambda definition: {'money': {**definition['money'], 'position': 'lead'}})
    view = client.get('/api/life/work').json()['work']
    assert view['position'] == 'lead' and view['state'][0] == 'Manages people.'
    revise(client, lambda definition: {'money': {**definition['money'], 'position': 'staff'}})
    view = client.get('/api/life/work').json()['work']
    assert view['position'] == 'staff' and view['state'][0] not in ('Runs the place.', 'Manages people.')
