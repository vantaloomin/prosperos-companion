"""Our child (companion/life/our_child.py): the pair's own child growing up in real time, their sheet, milestones and
the family life that shapes the companion's days, the second child as its own step, and the child grown at 18."""
import re
import string
from datetime import date, timedelta

import pytest
from conftest import intimate, reconcile, send, set_life
from test_expecting import likeliest, stage, started, to  # noqa: F401 - likeliest is a fixture
from test_parenthood import family, planned, set_family
from test_steps import prompt, says

from companion import group_guests
from companion.characters import current
from companion.life import families, money, our_child, work
from companion.memory import context, sides
from companion.world import intimacy

FORBIDDEN = re.compile(r'\b(?:kiss\w*|naked|nude|bath\w*|bed|body|skin|lips|touch\w*|cuddl\w*|snuggl\w*|undress\w*|'
                       r'shower\w*|sexy|hot|crush\w*|dating|flirt\w*|puberty)\b', re.IGNORECASE)
# The engine lands on the likeliest option every time (tests/test_expecting.py).
pytestmark = pytest.mark.usefixtures('likeliest')
TOKENS = {'child', 'they', 'them', 'their', 'theyre', 'are', 'were', 'They', 'Their', 'who', 'holiday'}


def connect(client):
    return client.app.state.database.connect()


def born(client, clock, monkeypatch, **values):
    """A baby born to the pair and home: the journey, and the clock on the day of the birth."""
    row = started(client, monkeypatch, identity='She is a 31-year-old nurse.', **values)
    to(client, clock, stage(row, 'born')['on'])
    with connect(client) as connection:
        companion = current(connection)
        [child] = our_child.children(connection, companion['active_timeline_id'])
    return row, child


def ours(client, **values):
    response = client.put('/api/life/steps/ours', json=values) if values else client.get('/api/life/steps/ours')
    assert response.status_code == 200, response.text
    return response.json()


def aged(client, child: dict, days: int, home: bool = True) -> None:
    """Makes the child `days` old today (and home since birth)."""
    with connect(client) as connection:
        today = our_child.steps.local_today(current(connection), client.app.state.database.clock.now())
        born_on = (today - timedelta(days=days)).isoformat()
        connection.execute('UPDATE circle_children SET born_on=? WHERE id=?', (born_on, child['id']))
        if home:
            connection.execute('UPDATE family_journeys SET arrived_on=? WHERE id=?', (born_on, child['storyline_id']))
        connection.commit()


def test_the_bank_has_a_hundred_lines_a_category_fit_for_children():
    bank = our_child.bank()
    categories = [key for key in bank if key not in ('_about', 'tags')]
    assert {f'{kind}_{band}' for kind in ('likes', 'quirks') for band, _low, _high in our_child.BANDS} <= set(categories)
    texts = set()
    for key in categories:
        assert len(bank[key]) >= 100, key
        for line in bank[key]:
            assert not FORBIDDEN.search(line['text']), line['text']
            assert {field for _literal, field, _spec, _conversion in string.Formatter().parse(line['text'])
                    if field} <= TOKENS, line['text']
            texts.add(line['text'])
    assert set(bank['tags']['older']) | set(bank['tags']['modern']) <= texts
    assert all(0 <= line['ages'][0] <= line['ages'][1] <= 17 for line in bank['holiday_part'])
    # The companion reads these as notes about their own family: "you", never "I" or "me".
    assert not [line['text'] for key in ('grandparents', 'aunts_uncles', 'holiday_part') for line in bank[key]
                if re.search(r"\b(?:I|I'm|me|my)\b", line['text'])]


def test_a_child_born_is_in_their_life_with_a_sheet_and_a_routine(client, provider, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    says(provider)
    send(client, 'how is everyone?', 'client-ours-1')
    text = prompt(provider)
    assert f"- {child['name']} (your daughter, a newborn): yours and the user's." in text or \
        f"- {child['name']} (your son, a newborn): yours and the user's." in text
    assert f"{child['name'].split()[0]} is " in text and 'Lately ' not in text  # A newborn: only a temperament yet.
    assert 'bedtime is around 7 in the evening' in text
    view = ours(client)
    assert view['shown'] and view['children'][0]['name'] == child['name'] and view['care'] in our_child.CARE
    assert view['children'][0]['temperament'] and view['children'][0]['likes'] is None
    aged(client, child, 400)
    assert ours(client)['children'][0]['likes']
    today = client.get('/api/today').json()
    assert today['family'][0]['name'] == child['name']


def test_milestones_come_in_real_time_and_stay_in_the_scrapbook(client, provider, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    with connect(client) as connection:
        companion = current(connection)
        planned = our_child.milestones(connection, companion, child)
    smile = next(item for item in planned if item['key'] == 'smile')
    assert [item['key'] for item in planned][:2] == ['smile', 'laugh'] or planned[0]['key'] == 'smile'
    to(client, clock, smile['on'])
    says(provider)
    send(client, 'good morning', 'client-ours-2')
    assert f"{child['name'].split()[0]} smiled for the first time today." in prompt(provider)
    assert ours(client)['children'][0]['latest']['label'] == 'First smile'
    with connect(client) as connection:
        items = our_child.scrapbook_items(connection, current(connection), date(2000, 1, 1), date(2100, 1, 1))
    assert any(item['text'].endswith('first smile') for item in items)


def test_who_stays_home_shapes_their_workdays_and_money(client, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    aged(client, child, 200)
    ours(client, care='them_home')
    with connect(client) as connection:
        companion = current(connection)
        today = our_child.steps.local_today(companion, clock.now())
        off = our_child.days_off(connection, companion, today, today + timedelta(days=13))
        assert set(off.values()) <= {our_child.HOME_DAY, our_child.SICK_DAY}
        assert len(off) >= len([day for day in range(14) if (today + timedelta(days=day)).weekday() in
                                work.workdays(companion['version']['definition'])]) - 1
        assert our_child.pay(connection, companion['active_timeline_id'], today) == our_child.PAY['them_home']
    ours(client, care='both_work')
    with connect(client) as connection:
        companion = current(connection)
        bought = our_child.purchases(connection, companion['active_timeline_id'], today, today + timedelta(days=40))
        care = next(item for item in bought if item['for'] == 'childcare')
        assert care['text'] == 'paid your half of the childcare' and care['shown'] == 'paid their half of the childcare'
        definition = companion['version']['definition']
        found = money.snapshot(definition, today.isoformat(), {'costs': {}, 'purchases': [care]})
        assert ('- This pay period you spent money for the family: you paid your half of the childcare.' in
                [line for _key, line in money.context_lines(definition, today.isoformat(),
                                                            {'costs': {}, 'purchases': [care]})])
        assert found['bought'][0]['shown'] == 'paid their half of the childcare'
        assert our_child.pay(connection, companion['active_timeline_id'], today) == 1.0
    assert ours(client, care='auto')['care_how'] == 'seeded'


def test_family_life_sets_how_hard_the_nights_are(client, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    aged(client, child, 20)
    with connect(client) as connection:
        timeline_id = current(connection)['active_timeline_id']
        today = our_child.steps.local_today(current(connection), clock.now())
        nights = [today + timedelta(days=offset) for offset in range(60)]
    set_life(client, family_life=3)
    with connect(client) as connection:
        assert sum(bool(our_child.broken_night(connection, timeline_id, day)) for day in nights) > 10
    set_life(client, family_life=0)
    with connect(client) as connection:
        assert not any(our_child.broken_night(connection, timeline_id, day) for day in nights)
        assert not any(our_child.sick_on(connection, child, day) for day in nights)


def named(name: str, text: str) -> bool:
    """Whether a name is in the text as a word ("Ren" is not in "Rent is about")."""
    return bool(re.search(rf'\b{re.escape(name)}\b', text))


def test_the_adult_side_and_the_family_never_share_a_reply(client, provider, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    says(provider)
    send(client, 'how was the day?', 'client-ours-3')
    assert child['name'] in prompt(provider) and intimacy.SETTING not in prompt(provider)
    intimate(client)
    says(provider)
    send(client, 'come here you', 'client-ours-4')
    assert not named(child['name'], prompt(provider))
    with connect(client) as connection:
        assert families.pictured(connection, current(connection)['active_timeline_id'], [f"A day out with {child['name']}"])


def test_a_family_day_out_is_an_outing_with_no_photo(client, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    send(client, 'hi', 'client-ours-5')
    aged(client, child, 500)
    reconcile(client)
    with connect(client) as connection:
        companion = current(connection)
        found = our_child.family_outings(connection, companion)
    if found:  # A city with a park or a museum open on the day.
        place = found[0]['place']
        assert place['no_photo'] and place['family'] == [child['name'].split()[0]]
        assert our_child.doing(found[0]).startswith(f"took {child['name'].split()[0]} to ")


def test_another_child_comes_as_its_own_step(client, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    assert family(client)['can_decide_another'] is False  # Not a year and a half yet.
    aged(client, child, 600)
    assert family(client)['can_decide_another'] is True
    set_family(client, another=True)
    reconcile(client)
    with connect(client) as connection:
        companion = current(connection)
        second = our_child.steps.local_today(companion, clock.now())
        journey = connection.execute("SELECT * FROM family_journeys WHERE timeline_id=? AND status NOT IN ('home', "
                                     "'called_off')", (companion['active_timeline_id'],)).fetchone()
    assert journey and journey['started_on'] == second.isoformat()
    assert family(client)['another_on'] == second.isoformat()


def test_at_eighteen_the_child_is_a_grown_person_in_their_circle(client, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    aged(client, child, 18 * 366)
    reconcile(client)
    with connect(client) as connection:
        companion = current(connection)
        person = connection.execute("SELECT * FROM circle_people WHERE json_extract(details, '$.our_child')=?",
                                    (child['id'],)).fetchone()
        assert person and person['role'] in ('daughter', 'son') and person['name'] == child['name'].split()[0]
        assert our_child.context_lines(connection, companion, clock.now()) == []
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    with connect(client) as connection:
        assert all(row['id'] != person['id'] for row in group_guests.circle_people(connection, current(connection)))


def test_a_year_and_a_half_on_they_bring_up_another_child(client, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    aged(client, child, 600)
    reconcile(client)
    asks = [ask for ask in planned(client) if ask['step'] == 'sibling']
    assert asks and asks[0]['side'] == 'them'
    with connect(client) as connection:
        assert 'a brother or sister for' in our_child.steps.reason_for(connection, current(connection), 'sibling')


def test_another_child_comes_up_only_while_the_youngest_is_under_ten(client, provider, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    aged(client, child, 9 * 366)
    assert family(client)['can_decide_another']
    aged(client, child, 10 * 366)
    reconcile(client)
    assert not [ask for ask in planned(client) if ask['step'] == 'sibling']
    assert not family(client)['can_decide_another']
    says(provider)
    send(client, 'should we have another baby?', 'client-ours-ten')
    with connect(client) as connection:
        assert not connection.execute("SELECT * FROM step_asks WHERE step='sibling'").fetchall()
    assert client.put('/api/life/steps/family', json={'another': True}).status_code == 409


def test_the_user_can_bring_up_another_child(client, provider, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    aged(client, child, 600)
    says(provider)
    send(client, 'should we have another baby?', 'client-ours-6')
    with connect(client) as connection:
        asked = connection.execute("SELECT * FROM step_asks WHERE step='sibling' AND side='you'").fetchone()
    assert asked and asked['status'] in ('yes', 'not_yet', 'no')
    if asked['status'] == 'yes':
        assert family(client)['another_on']


def test_the_sheet_fits_the_childs_age():
    bank = our_child.bank()
    for band, low, _high in our_child.BANDS:
        for kind in ('likes', 'quirks'):
            for era in ('modern', 'medieval', 'victorian', 'jazz-age'):
                days = max(low * 365, our_child.NEWBORN_DAYS)
                found = our_child.for_age(bank[f'{kind}_{band}'], era, days)
                assert found, (kind, band, era)
                assert all(line.get('from', 0) * 365 <= days for line in found)
    one = our_child.for_age(bank['quirks_toddler'], 'modern', 400)
    assert not any('groceries' in line['text'] for line in one)
    assert any('groceries' in line['text'] for line in our_child.for_age(bank['quirks_toddler'], 'modern', 3 * 365))
    assert not any(our_child.FOOD.search(line['text']) for line in our_child.for_age(bank['quirks_baby'], 'modern', 100))


def test_a_reply_reads_its_side_from_many_wordings():
    for text in ('fuck me tonight', 'f*ck me', 'make love to me', 'ride me', 'strip for me', 'sleep with me',
                 'netflix and chill?', 's3x', 'seggs tonight?', 'kis me', 'bésame', "i'm wet", 'sext me',
                 'go down on me', 'take it off', 'shower together?', 'feeling frisky', '🍆💦', 'wanna come over 😏',
                 "wanna see what i'm wearing under this", 'kiiiissss me', 'n-u-d-e-s'):
        assert sides.reads_intimate([text]), text
    for text in ('how was your day?', 'Ayla laughed so hard at the dog', 'want to do dinner friday, just the two of us?',
                 'morning love. how did you sleep?', 'the shaggy dog got into the garden', 'that sucks, sorry',
                 'it is so hot today', 'ugh, the sextant order is late', 'pass the cumin'):
        assert not sides.reads_intimate([text]), text


def whole(provider) -> str:
    request = provider.requests[-1]
    return request['system'] + '\n' + '\n'.join(str(message['content']) for message in request['messages'])


def test_a_style_note_is_read_for_its_plain_words(client, provider, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    first = child['name'].split()[0]
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    companion = client.get('/api/companion').json()['companion']
    note = f"/api/authors-notes/companion:{companion['id']}"
    recent = [{'text': f'how is {first} doing this morning?'}]
    for text, kept in (('Keep replies short and teasing.', True), ('Keep it light, with eye contact and leather.', True),
                         ('Slow, sensual, the two of you alone in the bedroom.', False), ('Keep it sexy.', False)):
        assert client.put(note, json={'text': text}).status_code == 200
        with connect(client) as connection:
            assert sides.family_reply(connection, current(connection), recent, None, None) is kept, text
    assert client.put(note, json={'text': 'Keep replies short and teasing.'}).status_code == 200
    says(provider)
    send(client, recent[0]['text'], 'client-ours-note')
    assert first in provider.requests[-1]['system']


def test_a_reply_whose_conversation_says_a_child_carries_one_kind_of_line_or_none(client, provider, clock,
                                                                                  monkeypatch):
    row, child = born(client, clock, monkeypatch)
    first = child['name'].split()[0]
    send(client, f'how is {first} doing today?', 'client-ours-7')
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    send(client, 'come to bed and kiss me', 'client-ours-8')
    assert intimacy.SETTING not in whole(provider)
    with connect(client) as connection:
        companion = current(connection)
        own = intimacy.prompt_text(connection, companion['version'])
        assert own and own not in whole(provider)
        recent = [{'text': 'come to bed and kiss me'}]
        assert sides.adult_lines(connection, companion, recent, None, None, False)
        assert not sides.adult_lines(connection, companion, [{'text': 'the kids are finally asleep'}], None,
                                               None, False)
        group = {'shared': f'Sam: how is {first}?'}
        assert not sides.adult_lines(connection, companion, recent, group, None, False)
        assert not sides.adult_lines(connection, companion, recent, None, None, True)
        assert sides.names_child([f'{first} is asleep'], sides.every_name(connection))


def test_the_characters_own_words_count_toward_a_replys_side(client, provider, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch, background='Loves slow kisses and lazy mornings.')
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    send(client, 'how was the day?', 'client-ours-9')
    assert not named(child['name'].split()[0], prompt(provider))


def test_a_reply_without_the_family_lines_leaves_out_lines_about_a_child_however_named(client, provider, clock,
                                                                                       monkeypatch):
    row, child = born(client, clock, monkeypatch)
    aged(client, child, 18 * 366)
    reconcile(client)
    with connect(client) as connection:
        person = connection.execute("SELECT id FROM circle_people WHERE json_extract(details, '$.our_child')=?",
                                    (child['id'],)).fetchone()
    assert client.patch(f"/api/life/circle/{person['id']}", json={'name': 'Zephyrine'}).status_code == 200
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    with connect(client) as connection:
        timeline_id = current(connection)['active_timeline_id']
        found = sides.hidden(connection, timeline_id, False)
        assert found.search('- Zephyrine (daughter): works at the bakery.')
        assert found.search('- Your daughter started at the new school.') and found.search('the kids were up early')
        assert not found.search('- Sana (close friend): financial analyst.')
        assert families.pictured(connection, timeline_id, ['Zephyrine and Mira at the beach'])
    intimate(client)
    send(client, 'come here you', 'client-ours-10')
    assert 'Zephyrine' not in whole(provider)


def test_a_second_look_through_memory_keeps_to_the_replys_side(client, provider, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    first = child['name'].split()[0]
    for subject, value in (('Picnic', f'{first} loved the picnic at the lake'),
                           ('Picnic night', 'After the picnic we made love by the lake')):
        assert client.post('/api/memories', json={'layer': 'shared_experience', 'subject': subject,
                                                  'value': value}).status_code == 200
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    with connect(client) as connection:
        companion = current(connection)
        other = ' '.join(context.looked_back(connection, companion, clock.now(), 'the picnic'))
        family = ' '.join(context.looked_back(connection, companion, clock.now(), 'the picnic',
                                                                 family=True))
    assert first not in other and 'made love' in other
    assert first in family and 'made love' not in family


def test_another_companion_in_the_chat_keeps_to_one_kind_of_line_too(client, provider, clock, monkeypatch):
    from test_groups import by_speaker, companion_named, say, start
    row, child = born(client, clock, monkeypatch)
    first = child['name'].split()[0]
    own = client.get('/api/companion').json()['companion']['id']
    other = companion_named(client, 'Billy Hart', 'Easygoing. 34 years old.')
    provider.respond = by_speaker
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    group = start(client, [own, other])
    say(client, group['id'], f'how is little {first}? billy come kiss me', 'client-ours-11')
    for request in provider.requests:
        text = request['system'] + '\n'.join(str(message['content']) for message in request['messages'])
        assert not (first in text and intimacy.SETTING in text)
    with connect(client) as connection:
        timeline_id = connection.execute('SELECT active_timeline_id FROM companions WHERE id=?',
                                         (other,)).fetchone()['active_timeline_id']
        billy = our_child.companion_of(connection, timeline_id)
        assert not sides.adult_lines(connection, billy, [{'text': f'{first} took her first steps'}], None, None, False)
        assert sides.hidden(connection, timeline_id, False).search(f'- Mira says {first} is walking now.')
        assert families.pictured(connection, timeline_id, [f'Billy and {first} at the park'])


def test_the_childs_lines_fit_an_older_city():
    bank = our_child.bank()
    for era, words in (('medieval', ('newspaper', 'telescope', 'piano', 'grocery', 'flashlight', 'homework')),
                       ('victorian', ('flashlight',))):
        texts = ' '.join(line['text'] for key, lines in bank.items() if isinstance(lines, list)
                         for line in our_child.fitting(lines, era))
        assert not any(word in texts for word in words), era
    assert any('piano' in line['text'] for line in our_child.fitting(bank['likes_teen'], 'victorian'))


def test_a_sick_day_and_a_holiday_read_right_for_the_child(client, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    aged(client, child, 6 * 365)
    monkeypatch.setattr(our_child, 'sick_on', lambda connection, kid, day: True)
    with connect(client) as connection:
        companion = current(connection)
        today = our_child.steps.local_today(companion, clock.now())
        monkeypatch.setattr('companion.life.traditions.upcoming', lambda *args: [
            {'date': today, 'holiday': 'easter', 'name': 'Easter Day'}])
        whole = our_child.bank()
        monkeypatch.setattr(our_child, 'bank', lambda: {**whole, 'holiday_part': [
            {'text': '{child} made up a {holiday} treasure hunt for the cousins.', 'ages': [4, 12]}]})
        child = dict(connection.execute('SELECT * FROM circle_children WHERE id=?', (child['id'],)).fetchone())
        found = dict(our_child.today_lines(connection, companion, clock.now() if today.weekday() < 5 else
                                           clock.now() + timedelta(days=2)))
        [holiday] = our_child.holiday_line(connection, companion, child, today)
    them = {'she/her': 'her', 'he/him': 'him'}.get(child['pronouns'], 'them')
    assert found[f"ours:sick:{child['id']}"].endswith(f'is home to look after {them}.')
    assert 'made up an Easter Day treasure hunt' in holiday[1]


def test_sick_days_come_as_many_a_year_as_family_life_says(client, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    for level, count in enumerate(our_child.SICK_DAYS):
        set_life(client, family_life=level)
        with connect(client) as connection:
            for year in (2030, 2031):
                days = [date(year, 1, 1) + timedelta(days=offset) for offset in range(365)]
                kid = {**child, 'born_on': f'{year - 5}-06-01'}
                assert sum(our_child.sick_on(connection, kid, day) for day in days) == count


def test_renaming_a_grown_child_renames_them_in_the_circle_too(client, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    aged(client, child, 18 * 366)
    reconcile(client)
    ours(client, child=child['id'], name='Robin Vale')
    with connect(client) as connection:
        person = connection.execute("SELECT name FROM circle_people WHERE json_extract(details, '$.our_child')=?",
                                    (child['id'],)).fetchone()
    assert person['name'] == 'Robin'


def test_another_child_never_comes_sooner_than_a_year_and_a_half_however_it_is_raised(client, provider, clock,
                                                                                      monkeypatch):
    row, child = born(client, clock, monkeypatch)
    aged(client, child, 100)
    says(provider)
    send(client, 'should we have another baby?', 'client-ours-12')
    assert client.put('/api/life/steps/family', json={'another': True}).status_code == 409
    with connect(client) as connection:
        assert not connection.execute("SELECT * FROM step_asks WHERE step='sibling'").fetchall()
        assert not connection.execute("SELECT * FROM relationship_steps WHERE step='sibling'").fetchall()


def test_an_evening_out_shows_who_is_watching_the_child(client, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    aged(client, child, 600)
    first = child['name'].split()[0]
    with connect(client) as connection:
        companion = current(connection)
        today = our_child.steps.local_today(companion, clock.now()).isoformat()
        evening = {'activity': 'dinner', 'at_time': '19:30', 'local_date': today}
        assert our_child.sitter_view(connection, companion, {**evening, 'at_time': '12:00'}) is None
        found = our_child.sitter_view(connection, companion, evening)
        assert found['text'].split(' is watching ')[1].startswith(first)
        assert 'your ' not in found['text']
        monkeypatch.setattr(our_child, 'relatives', lambda *args: [])
        paid = our_child.sitter_view(connection, companion, evening)
        assert paid['text'].startswith(f'A sitter is watching {first}, about ') and paid['cost'] > 0


def test_the_childs_line_gives_months_until_two_then_years(client, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    with connect(client) as connection:
        today = our_child.steps.local_today(current(connection), clock.now())
    for days, told in ((200, 'a baby, 6 months old'), (430, '14 months old'), (15 * 365 + 40, '15')):
        found = {**child, 'born_on': (today - timedelta(days=days)).isoformat()}
        assert our_child.how_old(found, today) == told
    aged(client, child, 430)
    with connect(client) as connection:
        line = our_child.child_text(connection, dict(connection.execute(
            'SELECT * FROM circle_children WHERE id=?', (child['id'],)).fetchone()), today)
    assert ', 14 months old): yours and the user' in line and 'a child' not in line


def test_in_an_older_city_the_school_run_is_a_walk_to_school(client, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch, home_city='london-1895', location='Marylebone, London')
    aged(client, child, 6 * 365 + 100)
    with connect(client) as connection:
        companion = current(connection)
        today = our_child.steps.local_today(companion, clock.now())
        kids = our_child.at_home(connection, companion['active_timeline_id'], today)
        text = ' '.join(line for _key, line in our_child.days_lines(connection, companion, kids, today))
    first = child['name'].split()[0]
    assert f'weekday mornings start with walking {first} to school;' in text and 'school run' not in text


def test_gift_lines_only_go_with_a_holiday_for_presents(client, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    aged(client, child, 6 * 365)
    whole = our_child.bank()
    gift = {'text': '{child} handed out the {holiday} gifts, reading every name out loud.', 'ages': [5, 10]}
    lantern = {'text': '{child} made a paper lantern for {holiday} and hung it in the window.', 'ages': [5, 10]}
    monkeypatch.setattr(our_child, 'bank', lambda: {**whole, 'holiday_part': [gift, lantern]})
    with connect(client) as connection:
        companion = current(connection)
        today = our_child.steps.local_today(companion, clock.now())
        child = dict(connection.execute('SELECT * FROM circle_children WHERE id=?', (child['id'],)).fetchone())
        for holiday, name in (('midsummer-eve', "St John's Eve"), ('shrove-tuesday', 'Shrove Tuesday')):
            monkeypatch.setattr('companion.life.traditions.upcoming', lambda *args, key=holiday, label=name: [
                {'date': today, 'holiday': key, 'name': label}])
            [(_key, line)] = our_child.holiday_line(connection, companion, child, today)
            assert 'lantern' in line and 'gifts' not in line
        monkeypatch.setattr(our_child, 'bank', lambda: {**whole, 'holiday_part': [gift]})
        monkeypatch.setattr('companion.life.traditions.upcoming', lambda *args: [
            {'date': today, 'holiday': 'christmas', 'name': 'Christmas Day'}])
        assert 'Christmas Day gifts' in our_child.holiday_line(connection, companion, child, today)[0][1]
