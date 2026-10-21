"""The Watching feed's love life (companion/life/narrator_love.py): steps, rough patches, breaks, breakups and getting
back together told on the day, and the line under the companion's name following where the two of them stand."""
import re
from datetime import timedelta

import pytest
from conftest import send
from test_breakups import couple, view  # noqa: F401 - couple is a fixture
from test_together import mira, says

from companion.characters import current
from companion.clock import stamp
from companion.life import breakups, love_life, narrator, narrator_love, rough_patches, steps


def watch(client) -> dict:
    response = client.put('/api/observer', json={'watching': True})
    assert response.status_code == 200, response.text
    response = client.get('/api/observer/feed')
    assert response.status_code == 200, response.text
    return response.json()


def love(found: dict) -> list[dict]:
    return [line for day in found['days'] for line in day['items'] if line['kind'] == 'love']


def bank_of(*path: str) -> list[str]:
    found = narrator_love.bank()
    for key in path:
        found = found[key]
    return [line.format(first='Mira', other='Theo', over='over you calling off dinner', plan='dinner')
            for line in found]


def test_a_breakup_is_told_on_the_day_and_they_read_as_your_ex(client, couple, provider, clock):  # noqa: F811
    client.put('/api/life/steps', json={'step': 'moving_in'})
    found = watch(client)
    # The step picker set every step up to living together at once: only the highest is told.
    assert [line['text'] for line in love(found)] in [[text] for text in bank_of('steps', 'romance', 'moving_in')]
    assert found['focus']['line'].startswith('Your companion')
    clock.advance(timedelta(hours=2))
    says(provider)
    send(client, "I'm breaking up with you.", 'client-watch-1')
    found = watch(client)
    ended = [line for line in love(found) if line['id'].startswith('ended:')]
    assert [line['text'] for line in ended] in [[text] for text in bank_of('ended', 'you')]
    # True to life: a thought after it, only ever from the heartache bank.
    assert ended[0]['inner'] in [line.format(first='Mira') for line in narrator.bank()['heartache']]
    assert not ended[0]['numbers']  # The odds stay hidden.
    assert found['focus']['line'].startswith('Your ex')
    picked = client.get('/api/observer').json()
    assert next(choice for choice in picked['choices'] if choice['kind'] == 'companion')['line'].startswith('Your ex')


def test_getting_back_together_is_told_and_they_are_your_companion_again(client, couple, provider, clock):  # noqa: F811
    client.put('/api/life/steps', json={'step': 'married'})
    says(provider)
    send(client, "I'm breaking up with you.", 'client-watch-2')
    clock.advance(timedelta(days=3))
    says(provider)
    send(client, 'can we try again?', 'client-watch-3')
    assert view(client)['stage'] is None
    found = watch(client)
    texts = {line['id'].split(':')[0]: line['text'] for line in love(found)}
    assert texts['ended'] in bank_of('ended', 'divorced')  # Married when it ended.
    assert texts['together'] in bank_of('together', 'romance')
    assert found['focus']['line'].startswith('Your companion')


def test_a_break_reads_on_a_break(client, couple, provider):  # noqa: F811
    says(provider)
    send(client, 'can we take a break from us', 'client-watch-4')
    assert view(client)['stage'] == 'break'
    found = watch(client)
    assert [line['text'] for line in love(found) if line['id'].startswith('break:')] in [
        [text] for text in bank_of('break', 'you')]
    assert found['focus']['line'].startswith('On a break')


def test_a_falling_out_between_friends(client, monkeypatch, provider):
    monkeypatch.setattr(breakups, 'ACTIVE', True)
    mira(client, monkeypatch, relationship='friendship')
    says(provider)
    send(client, "I don't want to be friends anymore", 'client-watch-5')
    found = watch(client)
    assert [line['text'] for line in love(found)] in [[text] for text in bank_of('ended', 'fell_out')]
    assert found['focus']['line'].startswith('Your old friend')


def test_a_big_rough_patch_starting_is_told_with_their_pronouns(client, couple, provider):  # noqa: F811
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        rough_patches.consider(connection, companion, 'secret_kept', 'secret-kept:x>y', 'the user kept something',
                               client.app.state.database.clock.now(),
                               shown='over them finding out you kept something from them')
    [line] = love(watch(client))
    assert line['text'] in [text.format(first='Mira', over='over them finding out you kept something from them')
                            for text in narrator_love.bank()['patch']['over']]
    assert line['inner'] in [found.format(first='Mira') for found in narrator.bank()['heartache']]


def test_the_rough_patch_says_the_companion_with_their_own_pronouns_but_never_changes_a_quote():
    row = {'shown': 'over you finding out they\'d been seeing Theo behind your back', 'cause': 'hidden_partner',
           'about': ''}
    assert "she'd been seeing Theo" in narrator_love.patch_text(row, 'patch:1', 'Mira', 'she/her')
    row = {'shown': 'over what you said: "leave them alone"', 'cause': 'words', 'about': ''}
    assert '"leave them alone"' in narrator_love.patch_text(row, 'patch:1', 'Mira', 'he/him')
    row = {'shown': 'dinner (a work thing came up)', 'cause': 'stood_up', 'about': 'dinner (a work thing came up)'}
    assert narrator_love.patch_text(row, 'patch:1', 'Mira', '') in bank_of('patch', 'called_off')


def test_their_own_love_life_is_told_but_a_secret_never_is(client, monkeypatch, clock):
    mira(client, monkeypatch, relationship='friendship')
    database = client.app.state.database
    now = clock.now()
    with database.connect(write=True) as connection:
        companion = current(connection)
        today = steps.local_today(companion, now)
        theo = love_life.insert(connection, companion, 'Theo Park', {}, today, now)
        steps.insert_step(connection, companion['active_timeline_id'], 'romance', 'exclusive', today, 'them',
                          stamp(now), other=f'love:{theo}')
        love_life.end(connection, love_life.partner(connection, theo), 'split', today)
        love_life.insert(connection, companion, 'Sam Hidden', {}, today, now, secret=True)
    texts = [line['text'] for line in love(watch(client))]
    assert any(text in bank_of('theirs', 'met') for text in texts)
    assert any(text in bank_of('theirs', 'exclusive') for text in texts)
    assert any(text in bank_of('theirs', 'split') for text in texts)
    assert not any('Sam' in text for text in texts)


def test_the_heartache_bank():
    found = narrator.bank()['heartache']
    assert len(found) >= 100 and len(set(found)) == len(found)
    for line in found:
        assert '{first}' in line and chr(0x2014) not in line, line
        assert not re.search(r"\b(?:she|he|her|his|him|they|their|them|themselves)\b", line, re.IGNORECASE), line
        assert narrator.reads(line.format(first='Mira')) == set(), line


@pytest.mark.parametrize('path', [('steps', 'romance'), ('steps', 'friendship'), ('theirs',), ('patch',), ('break',),
                                  ('ended',), ('together',)])
def test_every_feed_line_reads_cleanly(path):
    found = narrator_love.bank()
    for key in path:
        found = found[key]
    for key, options in found.items():
        assert len(options) >= 3, key
        for line in bank_of(*path, key):
            assert chr(0x2014) not in line and '{' not in line, line
            assert narrator.reads(line) == set(), line
