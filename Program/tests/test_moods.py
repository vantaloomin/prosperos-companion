"""Moods (companion/moods.py): how a companion's day and the user's words leave them, ignoring someone in a group,
and walking out."""
from datetime import timedelta
from types import SimpleNamespace

import pytest
from conftest import send, show
from test_groups import by_speaker, companion_named, messages, ok, say, speaker, start

from companion import moods
from companion.memory import pairs
from companion.providers.chat import Chunk


@pytest.fixture
def cast(client, companion, connected, provider):
    """Mira (the main character); Billy, who has a temper; Sally, who doesn't."""
    provider.respond = by_speaker
    return {'Mira': companion['id'], 'Billy': companion_named(client, 'Billy Hart', 'Hot-tempered and loyal.'),
            'Sally': companion_named(client, 'Sally Moss', 'Easygoing and kind.')}


def key(companion_id):
    return pairs.companion_key(companion_id)


def mood_of(client, companion_id):
    database = client.app.state.database
    with database.connect() as connection:
        return moods.current(connection, key(companion_id), database.clock.now())


def set_mood(client, companion_id, feeling, intensity, target=None, reason='testing'):
    database = client.app.state.database
    with database.connect(write=True) as connection:
        moods.save(connection, key(companion_id), feeling, intensity, target and key(target), reason,
                   database.clock.now())


def scripted(lines: dict[str, list[str]]):
    """Each named speaker says their lines in turn, then just says who they are."""
    def respond(system, history):
        name = speaker(history)
        if name in lines and lines[name]:
            return [Chunk(lines[name].pop(0)), Chunk('', 'stop')]
        return by_speaker(system, history)
    return respond


def requests_of(provider, name):
    return [request for request in provider.requests if speaker(request['messages']) == name]


def test_only_someone_with_a_temper_gets_angry(client, cast):
    database = client.app.state.database
    with database.connect() as connection:
        assert moods.temper(connection, key(cast['Billy'])) > 0
        assert moods.temper(connection, key(cast['Sally'])) == 0
    set_mood(client, cast['Sally'], 'angry', 3, cast['Billy'])
    assert (mood_of(client, cast['Sally'])['feeling'], mood_of(client, cast['Sally'])['intensity']) == ('hurt', 2)
    set_mood(client, cast['Billy'], 'angry', 3, cast['Sally'])
    assert moods.furious(mood_of(client, cast['Billy']))


def test_a_reply_nudges_a_feeling_one_step_but_never_to_furious(client, cast, provider):
    members = [{'member': key(cast['Billy']), 'name': 'Billy'}, {'member': key(cast['Sally']), 'name': 'Sally'}]
    database = client.app.state.database

    def nudge(text):
        with database.connect(write=True) as connection:
            return moods.nudge(connection, key(cast['Billy']), text, members, database.clock.now())
    assert not nudge('lol I am so mad at Sally')
    assert not nudge("I'm not mad at Sally.")
    assert nudge('Honestly I am so mad at Sally right now.')
    assert (mood_of(client, cast['Billy'])['feeling'], mood_of(client, cast['Billy'])['intensity']) == ('angry', 1)
    assert nudge("I'm still mad at Sally.")
    assert not nudge('Seriously, I am mad at Sally.')
    assert mood_of(client, cast['Billy'])['intensity'] == 2


def test_moods_fade_and_reset_overnight(client, cast, clock):
    set_mood(client, cast['Sally'], 'hurt', 2, cast['Billy'])
    clock.advance(moods.FADE)
    assert mood_of(client, cast['Sally'])['intensity'] == 1
    clock.advance(moods.FADE)
    assert mood_of(client, cast['Sally']) is None
    set_mood(client, cast['Sally'], 'sad', 3)
    clock.advance(timedelta(hours=14))  # The next morning in New York.
    assert mood_of(client, cast['Sally']) is None


def test_hurt_means_not_speaking_to_them(client, cast, provider):
    set_mood(client, cast['Billy'], 'hurt', 2, cast['Sally'])
    provider.respond = scripted({'Sally': ['Billy, what do you think?'], 'Billy': ['Sally is wrong about that.']})
    group = start(client, [cast['Billy'], cast['Sally']])
    ok(client.patch(f"/api/groups/{group['id']}", json={'reply_cap': 1}))
    say(client, group['id'], 'Sally, how was your day?', 'mood-group-1')
    # Sally named Billy, but Billy isn't speaking to her, so he doesn't answer.
    assert [line['name'] for line in messages(client, group['id']) if line['kind'] == 'companion'] == ['Sally']

    say(client, group['id'], 'Billy, how about you?', 'mood-group-2')
    billy = requests_of(provider, 'Billy')
    assert "You're not speaking to Sally right now; talk to the others, not to Sally." in billy[0]['prompt']
    # His first draft named Sally, so it was written once more without her.
    assert len(billy) == 2 and "Billy isn't speaking to Sally right now" in billy[1]['messages'][-1]['content']
    view = ok(client.get(f"/api/groups/{group['id']}"))['group']['members']
    assert all(item['mood'] is None for item in view)  # Hidden values: unseen unless turned on.
    show(client, show_moods=True)
    view = ok(client.get(f"/api/groups/{group['id']}"))['group']['members']
    assert next(item['mood'] for item in view if item['label'] == 'Billy')['text'] == 'Seems hurt by Sally'


def test_finding_out_a_secret_hurts(client, cast, provider):
    ok(client.post('/api/secrets', json={'statement': 'Billy is moving to Denver in May', 'about': ['Billy'],
                                         'knows': [cast['Billy']], 'kept_from': [cast['Sally']]}))
    group = start(client, [cast['Billy'], cast['Sally']])
    say(client, group['id'], 'Sally, Billy is moving to Denver in May.', 'mood-secret-1')
    mood = mood_of(client, cast['Sally'])
    assert (mood['feeling'], mood['intensity'], mood['target']) == ('hurt', 2, key(cast['Billy']))
    assert mood['reason'] == 'found out Billy is moving to Denver in May'


def test_someone_furious_walks_out_only_when_the_group_allows_it(client, cast, provider):
    group = start(client, [cast['Billy'], cast['Sally']])
    set_mood(client, cast['Billy'], 'angry', 3, cast['Sally'])
    for number in range(moods.WALK_OUT_REPLIES + 1):
        say(client, group['id'], f'Billy, talk to me {number}', f'mood-walk-{number}')
    assert 'Billy left the group.' not in [line['text'] for line in messages(client, group['id'])]

    ok(client.patch(f"/api/groups/{group['id']}", json={'walk_out': True}))
    say(client, group['id'], 'Billy, one more?', 'mood-walk-last')
    assert 'Billy left the group.' in [line['text'] for line in messages(client, group['id'])]
    assert [item['label'] for item in ok(client.get(f"/api/groups/{group['id']}"))['group']['members']] == ['Sally']
    refused = client.post(f"/api/groups/{group['id']}/members", json={'companion_id': cast['Billy']})
    assert refused.status_code == 409 and refused.json()['detail'] == 'Billy is still angry at Sally.'
    set_mood(client, cast['Billy'], 'annoyed', 1, cast['Sally'])
    ok(client.post(f"/api/groups/{group['id']}/members", json={'companion_id': cast['Billy']}))


def test_two_furious_at_each_other_means_the_stronger_temper_leaves_at_once(client, cast, provider):
    katie = companion_named(client, 'Katie Rowe', 'Hot-tempered, with a short temper and quick to anger.')
    group = start(client, [cast['Billy'], katie])
    ok(client.patch(f"/api/groups/{group['id']}", json={'walk_out': True}))
    set_mood(client, cast['Billy'], 'angry', 3, katie)
    set_mood(client, katie, 'angry', 3, cast['Billy'])
    say(client, group['id'], 'Hey both', 'mood-pair-1')
    assert 'Katie left the group.' in [line['text'] for line in messages(client, group['id'])]


def mira_prompt(provider) -> str:
    return next(request['prompt'] for request in reversed(provider.requests) if not speaker(request['messages']))


def bad_day(monkeypatch, clock):
    today = clock.now().date().isoformat()
    beat = {'on': today, 'tone': 'bad', 'text': 'Mira lost the promotion to Dana.'}
    monkeypatch.setattr(moods, 'storylines', SimpleNamespace(  # A storyline's bad turn today, as moods sees it.
        local_today=moods.storylines.local_today, visible=lambda *_args: [{'story': 'rivalry', 'beats': [beat]}]))


def test_a_bad_day_leaves_her_sullen_in_her_own_chat_and_kind_words_lift_it(client, cast, provider, clock,
                                                                            monkeypatch):
    bad_day(monkeypatch, clock)
    send(client, 'Hey, what are you up to?', 'mood-one-1')
    prompt = mira_prompt(provider)
    assert ("- You're subdued and a bit sullen: shorter, quieter replies, less joking, though you still answer and "
            'still care (why: Mira lost the promotion to Dana). Let it show in how you write (shorter, blunter, '
            'messier, whatever fits you), not just in what you say. Never explain it unless asked.') in prompt
    assert '## How you feel right now' in prompt

    send(client, "Oh no, I'm so sorry. I'm here for you.", 'mood-one-2')
    assert "- You're a little low today (why: Mira lost the promotion to Dana)" in mira_prompt(provider)
    send(client, 'Proud of you for trying anyway.', 'mood-one-3')
    assert mood_of(client, cast['Mira'])['feeling'] == 'calm'  # Cheered up for the rest of the day.
    assert "You're " not in mira_prompt(provider).split('## How you feel right now')[-1][:20]


def test_words_that_sting_cool_her_a_little_but_jokes_do_not(client, cast, provider):
    send(client, "You're so boring lol", 'mood-one-4')
    assert mood_of(client, cast['Mira']) is None
    send(client, "You're so boring.", 'mood-one-5')
    send(client, 'Whatever.', 'mood-one-6')
    mood = mood_of(client, cast['Mira'])
    # No temper: a little hurt, never more, never angry, never ignoring.
    assert (mood['feeling'], mood['intensity'], mood['target']) == ('hurt', 1, moods.USER)
    assert "- You're a little hurt with the user (why: something you said stung)" in mira_prompt(provider)


def test_how_she_feels_shows_on_today_only_when_turned_on(client, cast, clock, monkeypatch):
    bad_day(monkeypatch, clock)
    today = ok(client.get('/api/today'))
    assert today['feeling'] is None and today['day']['body'] is None
    assert ok(client.get('/api/life/reactions')) == []
    show(client, show_moods=True)
    feeling = ok(client.get('/api/today'))['feeling']
    assert (feeling['text'], feeling['reason']) == ('Seems sad', 'Mira lost the promotion to Dana')
