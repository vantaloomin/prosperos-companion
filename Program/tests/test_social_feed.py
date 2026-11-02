"""The social side of the feed: the circle's posts, likes and comments, and the companion's own non-event posts."""
import re
from datetime import UTC, date, datetime, timedelta

import pytest
from conftest import life_reply, reconcile, set_life
from fastapi.testclient import TestClient

from companion import logs
from companion.characters import current
from companion.clock import stamp, zone
from companion.identity import CLIENT_HEADER
from companion.life import body, circle, composer, social, user_posts
from companion.life import feed as feed_module


@pytest.fixture
def city(client, provider, monkeypatch):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'America/New_York',
                                                     'location': 'Fells Point, Baltimore', 'interests': ['Jazz']})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    provider.respond = life_reply
    set_life(client, automatic_events=True)
    return response.json()


def feed(client, **params):
    response = client.get('/api/feed', params={'limit': 100, **params})
    assert response.status_code == 200, response.text
    return response.json()


def live_days(client, clock, days=4):
    for _ in range(days):
        clock.advance(timedelta(days=1))
        reconcile(client)


def test_friends_post_from_their_diary_and_people_react(client, city, clock, monkeypatch):
    # Seeds depend on the random timeline id, so the chances are raised to make the counts certain.
    monkeypatch.setattr(social, 'COMMENT_CHANCE', 1)
    monkeypatch.setattr(social, 'COMPANION_LIKES', 1)
    live_days(client, clock)
    posts = feed(client)['posts']
    friends = [post for post in posts if post['kind'] == 'friend']
    assert friends and all(post['author']['kind'] == 'person' and post['text'] and post['context'] for post in friends)
    assert any(post['source'] == 'life' and post['author']['name'] == 'Mira' for post in posts)
    reactions = [post['audience'] for post in posts]
    assert any(item['likes'] for item in reactions) and any(item['comments'] for item in reactions)
    assert all(len(item['comments']) <= social.MAX_COMMENTS for item in reactions)
    # The companion joins in on friends' posts, and nobody comments on their own.
    assert any('Mira' in post['audience']['likes'] for post in friends)
    assert all(comment['name'] != post['author']['name'] for post in friends for comment in post['audience']['comments'])
    # Reading again posts nothing new.
    assert [post['id'] for post in feed(client)['posts']] == [post['id'] for post in posts]
    # Each post says what happened in its writer's own words, never their name.
    for post in friends:
        first = post['author']['name'].split()[0]
        # As a word: a neighbor named Mark can browse the stalls at a Market.
        assert not re.search(rf'\b{re.escape(first)}\b', post['context'] + ' ' + post['text']), post
    own = [event for post in posts if post['source'] == 'life' for event in post['events']]
    assert own and all('Mira' not in event['mine']['summary'] for event in own)
    assert all('Mira' in event['summary'] for event in own if event['summary'].startswith('Mira '))


@pytest.mark.parametrize(('summary', 'said'), [
    ('Work got hectic during the shift, but Bradley kept up.', 'Work got hectic during the shift, but I kept up.'),
    ('Bradley had a busy shift, with one rush after another.', 'I had a busy shift, with one rush after another.'),
    ('Bradley and Jess Moore joined the crowds for Pride.', 'Jess Moore and I joined the crowds for Pride.'),
    ('Bradley Shaw treated themselves at Lou\'s for their birthday.', "I treated myself at Lou's for my birthday."),
    ('Bradley took Sam out at Lou\'s for their birthday.', "I took Sam out at Lou's for their birthday."),
    ("Bradley spent Easter at their aunt Rose's, the way they always do.",
     "I spent Easter at my aunt Rose's, the way I always do."),
    ("The landlord finally sent someone to fix Bradley's sink.", 'The landlord finally sent someone to fix my sink.'),
    ('Ava got a job offer and keeps asking Bradley whether to take it.',
     'Ava got a job offer and keeps asking me whether to take it.'),
    ('The pottery class filled up, so Bradley is on the list.', 'The pottery class filled up, so I am on the list.'),
    # Present tense: the verb after "I" drops its -s, and "my" is capitalized only to start a sentence.
    ('Bradley goes to the market.', 'I go to the market.'),
    ("Bradley watches the game; Bradley's team wins.", 'I watch the game; my team wins.'),
    ('Bradley has a cold and Bradley is staying in.', 'I have a cold and I am staying in.'),
    ('Bradley does the dishes, then Bradley tries a new recipe.', 'I do the dishes, then I try a new recipe.'),
    ('Bradley often fixes bikes. Bradley\'s brother misses the bus.', "I often fix bikes. My brother misses the bus."),
    ("Bradley's dog runs off, but Bradley was ready.", 'My dog runs off, but I was ready.'),
    # Bank lines (hobby milestones) speak of anyone as "their": with only the poster in the sentence, that is "my".
    ('Bradley went to ballet. Bradley found a favourite spot of their own.',
     'I went to ballet. I found a favourite spot of my own.'),
    ('Bradley filled their first logbook and was proud of themselves.', 'I filled my first logbook and was proud of myself.'),
    ("Bradley gave a talk about their favourite places at Lou's.", "I gave a talk about my favourite places at Lou's."),
    ('Bradley drove Ana to their new flat.', 'I drove Ana to their new flat.'),
])
def test_a_post_says_what_happened_as_i(summary, said):
    assert composer.mine(summary, 'Bradley Shaw') == said


@pytest.mark.parametrize(('summary', 'own', 'said'), [
    # A model-phrased line starts with the companion's pronoun; the post says it as "I" all the way through.
    ('Sett made steady progress on the rush. He settled down in a booth at Hillside Noodle House for a while.', 'he/him',
     'I made steady progress on the rush. I settled down in a booth at Hillside Noodle House for a while.'),
    ("Sett ate early. He's tired, so he finally went to bed with his book.", 'he/him',
     "I ate early. I'm tired, so I finally went to bed with my book."),
    ('Rosa took a long walk. She found her favourite bench, and a neighbour walked her home.', 'she/her',
     'I took a long walk. I found my favourite bench, and a neighbour walked me home.'),
    ('Sam read for hours. They were pleased with themselves.', 'they/them', 'I read for hours. I was pleased with myself.'),
    # Someone else's pronoun stays: "They" after two people is both of them, and Henry is not the companion.
    ('Sam met Ava at the bar. They talked for hours.', 'they/them', 'I met Ava at the bar. They talked for hours.'),
    ('Sett ate. Henry came by and he stayed.', 'he/him', 'I ate. Henry came by and he stayed.'),
    ('Rosa ate. He came by.', 'she/her', 'I ate. He came by.'),
    ('Sett ate. He settled in.', None, 'I ate. He settled in.'),
])
def test_a_post_says_the_companions_own_pronoun_as_i(summary, own, said):
    assert composer.mine(summary, summary.split()[0], own) == said


def test_the_feed_can_show_only_the_companion_or_only_the_circle(client, city, clock):
    live_days(client, clock)
    everyone = feed(client)['posts']
    mine, theirs = feed(client, source='companion')['posts'], feed(client, source='circle')['posts']
    assert mine and theirs and len(mine) + len(theirs) == len(everyone)
    assert all(post['author']['kind'] == 'companion' for post in mine)
    assert all(post['author']['kind'] == 'person' for post in theirs)


def test_comments_arrive_after_the_post(client, city, clock):
    live_days(client, clock)
    for post in feed(client)['posts']:
        assert all(post['occurs_at'] <= comment['at'] <= client.get('/api/today').json()['now']
                   for comment in post['audience']['comments'])


def first_friend_post(client, clock) -> dict:
    """A friend's post, living on a few more days when the circle's seeded week brought none yet."""
    live_days(client, clock)
    for _ in range(8):
        post = next((post for post in feed(client)['posts'] if post['kind'] == 'friend'), None)
        if post:
            return post
        live_days(client, clock, 1)
    raise AssertionError('No friend posted in twelve days.')


def test_renamed_and_removed_friends(client, city, clock):
    post = first_friend_post(client, clock)
    person = post['author']['id']
    client.patch(f'/api/life/circle/{person}', json={'name': 'Renamed'})
    shown = next(item for item in feed(client)['posts'] if item['id'] == post['id'])
    assert shown['author']['name'] == 'Renamed'
    client.post(f'/api/life/circle/{person}/remove')
    posts = feed(client)['posts']
    assert all(item['author']['id'] != person for item in posts)
    assert all(comment['name'] != 'Renamed' for item in posts for comment in item['audience']['comments'])


def test_read_react_hide_and_remove_a_social_post(client, city, clock):
    live_days(client, clock)
    page = feed(client)
    post = next(post for post in page['posts'] if post['source'] == 'social')
    assert client.get('/api/today').json()['feed_unread'] == page['unread'] > 0
    assert client.post('/api/feed/read', json={'post_ids': [post['id']]}).json()['unread'] == page['unread'] - 1
    assert client.post(f"/api/feed/{post['id']}/reaction", json={'reaction': 'heart'}).json()['reaction'] == 'heart'
    client.post(f"/api/feed/{post['id']}/hide")
    assert post['id'] not in [item['id'] for item in feed(client)['posts']]
    assert post['id'] in [item['id'] for item in feed(client, hidden=True)['posts']]
    removed = client.post(f"/api/feed/{post['id']}/remove").json()
    assert removed['status'] == 'removed' and removed['text'] == ''
    assert client.post(f"/api/feed/{post['id']}/unhide").status_code == 409
    exported = client.get('/api/feed/export').json()
    assert any(item['source'] == 'social' for item in exported['posts'])


def test_answering_a_question_replies_in_chat(client, city, clock, provider, monkeypatch):
    monkeypatch.setattr(social, 'QUESTION_CHANCE', 1)
    live_days(client, clock, 1)
    question = next(post for post in feed(client)['posts'] if post['kind'] == 'question')
    assert len(question['options']) == 2
    assert client.post(f"/api/feed/{question['id']}/answer", json={'option': 'Nope', 'client_id': 'answer-001'}
                       ).status_code == 422
    option = question['options'][0]
    response = client.post(f"/api/feed/{question['id']}/answer", json={'option': option, 'client_id': 'answer-002'})
    assert response.status_code == 200, response.text
    assert next(post for post in feed(client)['posts'] if post['id'] == question['id'])['answer'] == option
    system = provider.requests[-1]['prompt']
    assert question['text'] in system and f'The user picked: {option}.' in system


def test_a_friends_birthday_gets_a_shout_out(client, city, clock, monkeypatch):
    today = clock.now().astimezone(zone('America/New_York')).date() + timedelta(days=1)
    monkeypatch.setattr(circle, 'birthday', lambda _person_id: today.strftime('%m-%d'))
    reconcile(client)
    clock.instant = datetime.combine(today, datetime.min.time(), tzinfo=UTC) + timedelta(hours=23)
    shout_outs = [post for post in feed(client)['posts'] if post['kind'] == 'birthday']
    people = client.get('/api/life/circle').json()
    assert len(shout_outs) == len(people)
    assert all(any(person['name'] in post['text'] for person in people) for post in shout_outs)


def test_status_posts_fit_the_day_and_claim_nothing():
    rainy = {'weather': {'high_f': 60, 'rain': True}, 'body': None}
    assert all(social.status_text(f'seed-{n}', date(2026, 10, 7), rainy, {})[0] in
               (*social.STATUS['rain'], *social.STATUS['any']) for n in range(20))
    text, tone = social.status_text('seed', date(2026, 10, 7), {'weather': None, 'body': {'state': 'sick'}}, {})
    assert text in social.STATUS['sick'] and tone == 'sick'
    assert social.comment_pool('status', {'tone': 'sick'}, 'someone', False) == social.COMMENTS['sick']


def test_city_news_reads_naturally():
    today = date(2026, 10, 7)
    opening = {'kind': 'opening', 'name': 'Bloom Cafe', 'summary': '', 'starts': '2026-10-10'}
    assert social.change_text(opening, 'Fells Point', today) == \
        "Bloom Cafe is opening in Fells Point on Saturday, October 10. Who's coming with me?"
    assert social.change_text({**opening, 'starts': '2026-10-01'}, '', today) == \
        'Bloom Cafe just opened. Who wants to try it?'


def test_a_branch_keeps_the_social_posts_from_before_it_split_off(client, city, clock, monkeypatch):
    monkeypatch.setattr(social, 'QUESTION_CHANCE', 1)
    live_days(client, clock, 2)
    sent = client.post('/api/conversation/messages', json={'text': 'Hi', 'client_id': 'branch-0001'}).json()['message']
    before = [post for post in feed(client)['posts'] if post['source'] == 'social']
    # Friends can post the same words at the same moment, so a post is found again on the branch by its
    # kind, words and moment together: react to one whose key no other post shares.
    keys = [(post['kind'], post['text'], post['occurs_at']) for post in before]
    question = next(post for post in before if post['kind'] == 'question')
    reacted = next(post for post, key in zip(before, keys) if keys.count(key) == 1 and post is not question)
    client.post(f"/api/feed/{question['id']}/answer", json={'option': question['options'][1], 'client_id': 'branch-0002'})
    client.post(f"/api/feed/{reacted['id']}/reaction", json={'reaction': 'wow'})
    live_days(client, clock, 2)
    after = {(post['kind'], post['text'], post['occurs_at']) for post in feed(client)['posts']
             if post['source'] == 'social' and post['occurs_at'] > sent['created_at']}
    branch = client.post('/api/timelines', json={'message_id': sent['id'], 'text': 'Hello'}).json()
    client.post(f"/api/timelines/{branch['id']}/activate")
    copied = [post for post in feed(client)['posts'] if post['source'] == 'social']
    # Posts at the same moment are ordered by id, and the copies have new ids, so compare them sorted.
    assert sorted((post['kind'], post['text'], post['occurs_at']) for post in copied
                  if post['occurs_at'] <= sent['created_at']) \
        == sorted((post['kind'], post['text'], post['occurs_at']) for post in before)
    # What the parent posted after the split stays on the parent.
    assert after and not after & {(post['kind'], post['text'], post['occurs_at']) for post in copied
                                  if post['occurs_at'] > sent['created_at']}
    shown = {(post['kind'], post['text'], post['occurs_at']): post for post in copied}
    assert shown[(question['kind'], question['text'], question['occurs_at'])]['answer'] == question['options'][1]
    assert shown[(reacted['kind'], reacted['text'], reacted['occurs_at'])]['reaction'] == 'wow'
    # Reading again on the branch does not post the copied ones a second time.
    assert len([post for post in feed(client)['posts'] if post['source'] == 'social']) == len(copied)


def test_no_comment_repeats_on_a_post_or_the_posts_just_before(client, city, clock, monkeypatch):
    monkeypatch.setattr(social, 'COMMENT_CHANCE', 1)
    live_days(client, clock)
    posts = list(reversed(feed(client)['posts']))
    said = [[comment['text'] for comment in post['audience']['comments']] for post in posts]
    assert any(said)
    for index, lines in enumerate(said):
        assert len(lines) == len(set(lines))
        earlier = {line for before in said[max(0, index - social.NEARBY):index] for line in before}
        assert not earlier & set(lines)
    # A filter shows the same comments the full feed does.
    everyone = {post['id']: post['audience'] for post in posts}
    assert all(post['audience'] == everyone[post['id']] for post in feed(client, source='circle')['posts'])


def test_reacting_returns_the_post_as_the_feed_shows_it(client, city, clock):
    live_days(client, clock)
    for post in feed(client)['posts'][:4]:
        reacted = client.post(f"/api/feed/{post['id']}/reaction", json={'reaction': 'hug'}).json()
        assert reacted['author'] == post['author'] and reacted['audience'] == post['audience']


def test_an_interest_reads_naturally_mid_sentence():
    """A long run posted "Fell down a the history of medicine museum rabbit hole again."""
    assert social.interest_text('the History of Medicine museum') == 'History of Medicine museum'
    assert social.interest_text('Roller derby matches') == 'roller derby matches'
    assert social.interest_text('Baltimore Orioles games') == 'Baltimore Orioles games'
    assert social.interest_text('a good thriller') == 'good thriller'


def test_a_timeline_that_starts_after_now_still_opens_the_feed(client, city, clock):
    """After Debug time's "keep what happened", a companion met during the jump has a timeline that starts later
    than real time. Posts and Today still open instead of failing (a tester's Posts tab showed only an error)."""
    with client.app.state.database.connect(write=True) as connection:
        connection.execute('UPDATE timelines SET created_at=?', (stamp(clock.now() + timedelta(days=3)),))
    assert feed(client)['posts'] == []
    assert client.get('/api/today').status_code == 200


def test_new_posts_that_cannot_be_written_leave_the_feed_readable(app, client, city, clock, monkeypatch):
    live_days(client, clock, 2)
    shown = feed(client)['posts']
    monkeypatch.setattr(social, 'write', lambda *_args: 1 / 0)
    assert feed(client)['posts'] == shown
    # Any other failure reaches the page as a message it can show, not a bare "Internal Server Error".
    monkeypatch.setattr(feed_module, 'listing', lambda *_args: 1 / 0)
    with TestClient(app, headers={CLIENT_HEADER: 'workspace'}, raise_server_exceptions=False) as failing:
        response = failing.get('/api/feed')
    assert response.status_code == 500 and response.json()['code'] == 'server_error'
    # It names the log by its full path, and the page's "Open the log folder" button shows that folder.
    assert str(logs.file_path()) in response.json()['detail'] and response.json()['log'] == str(logs.file_path())
    opened = []
    monkeypatch.setattr(logs, 'open_folder', opened.append)
    assert client.post('/api/logs/open-folder').json() == {'folder': str(logs.file_path().parent)}
    assert opened == [logs.file_path().parent]


def known_companion(client, name: str, personality: str, level: int | None = 5) -> str:
    """Another companion in the workspace; with `level`, Mira and they know each other at that stage."""
    from test_groups import companion_named

    from companion.characters import require_current
    from companion.memory import pairs
    other = companion_named(client, name, personality)
    if level:
        database = client.app.state.database
        with database.connect(write=True) as connection:
            assert pairs.tell(connection, pairs.companion_key(require_current(connection)['id']), pairs.companion_key(other), level, 'Old friends.',
                              database.now())
    return other


def test_companions_who_know_each_other_react_to_their_posts(client, city, clock, monkeypatch):
    monkeypatch.setattr(social, 'KNOWN_LIKES', (1,) * 5)
    monkeypatch.setattr(social, 'KNOWN_COMMENTS', (1,) * 5)
    monkeypatch.setattr(social, 'MANNERS', {**social.MANNERS, 'reserved': (1, 1)})
    monkeypatch.setattr(social, 'KNOWN_MOST', (1, 1))
    # Around before Mira's first posts (which go back a few days).
    clock.advance(-social.LOOKBACK)
    known_companion(client, 'Spock', 'Reserved, logical and private.')
    known_companion(client, 'Billy Hart', 'Easygoing.', level=None)
    clock.advance(social.LOOKBACK)
    live_days(client, clock)
    posts = feed(client)['posts']
    # Likes come within eight hours of a post.
    settled = stamp(clock.now() - social.REACTION_WINDOW)
    own = [post for post in posts if post['author']['kind'] == 'companion' and post['occurs_at'] <= settled]
    assert own and all('Spock' in post['audience']['likes'] for post in own)
    # Spock says little, and in few words: none of the chatty lines.
    chatty = {*social.COMMENTS['general'], *social.COMMENTS['from_companion']}
    said = [comment for post in own for comment in post['audience']['comments'] if comment['name'] == 'Spock']
    assert said and all(comment['author'] == 'companion' and comment['text'] not in chatty for comment in said)
    # Billy has never met Mira, and nobody but the circle joins in on a friend's post.
    assert not any('Billy Hart' in post['audience']['likes'] for post in posts)
    assert not any('Spock' in post['audience']['likes'] for post in posts if post['author']['kind'] == 'person')


def test_a_companion_does_not_react_to_posts_from_before_they_were_around(client, city, clock, monkeypatch):
    monkeypatch.setattr(social, 'KNOWN_LIKES', (1,) * 5)
    monkeypatch.setattr(social, 'KNOWN_MOST', (1, 1))
    live_days(client, clock)
    known_companion(client, 'Spock', 'Reserved.')
    assert not any('Spock' in post['audience']['likes'] for post in feed(client)['posts'])


@pytest.mark.parametrize(('personality', 'expected'), [
    ('Reserved, logical, keeps his emotions in check.', 'reserved'),
    ('A stoic Vulcan of few words.', 'reserved'),
    ('Warm, chatty and affectionate.', 'warm'),
    ('An outgoing people person.', 'warm'),
    ('Easygoing.', 'usual'),
])
def test_how_reserved_or_warm_a_companion_is(personality, expected):
    assert social.manner({'personality': personality}) == expected


def test_closer_and_warmer_companions_join_in_more():
    def chances(manner: str, stage: int) -> tuple[float, float]:
        likes, comments = social.MANNERS[manner]
        return social.KNOWN_LIKES[stage - 1] * likes, social.KNOWN_COMMENTS[stage - 1] * comments

    assert chances('reserved', 5) < chances('usual', 5) < chances('warm', 5)
    assert chances('usual', 1) < chances('usual', 3) < chances('usual', 5)


# The user's own posts (companion/life/user_posts.py) ------------------------------------------------


def post(client, text: str) -> dict:
    response = client.post('/api/feed/mine', json={'text': text})
    assert response.status_code == 200, response.text
    return response.json()


class Certain(dict):
    """Everyone in the circle is sure to like a post, whatever their role."""
    def get(self, *_args):
        return 1


@pytest.fixture
def everyone_joins_in(monkeypatch):
    monkeypatch.setattr(user_posts, 'LIKES', (1,) * 5)
    monkeypatch.setattr(user_posts, 'COMMENTS', (1,) * 5)
    monkeypatch.setattr(user_posts, 'REACH', (1,) * 5)
    monkeypatch.setattr(user_posts, 'TIE', (1,) * 5)
    monkeypatch.setattr(user_posts, 'FAR', 0)
    monkeypatch.setattr(social, 'KNOWN_MOST', (1, 1))
    monkeypatch.setattr(social, 'MANNERS', {name: (1, 1) for name in social.MANNERS})
    monkeypatch.setattr(social, 'LIKELY', Certain())
    monkeypatch.setattr(social, 'COMMENT_CHANCE', 1)


def test_a_post_of_your_own_shows_on_the_feed_as_yours(client, city):
    made = post(client, '  Finally finished the bookshelf.  ')
    assert made['text'] == 'Finally finished the bookshelf.'
    assert made['author'] == {'kind': 'user', 'id': None, 'name': 'You', 'role': ''}
    assert made['read'] and made['source'] == 'user'
    # Nobody has seen it yet the moment it goes up.
    assert made['audience'] == {'likes': [], 'comments': []}
    assert [found['id'] for found in feed(client, source='mine')['posts']] == [made['id']]
    assert made['id'] in {found['id'] for found in feed(client)['posts']}
    for source in ('companion', 'circle'):
        assert made['id'] not in {found['id'] for found in feed(client, source=source)['posts']}


def test_companions_and_their_circles_join_in(client, city, clock, everyone_joins_in):
    from test_groups import companion_named
    reconcile(client)
    companion_named(client, 'Spock', 'Reserved, logical and private.')
    clock.advance(timedelta(minutes=1))
    made = post(client, 'Went to the night market with my sister.')
    clock.advance(user_posts.CIRCLE_WINDOW)
    shown = next(found for found in feed(client)['posts'] if found['id'] == made['id'])
    people = [person['name'] for person in circle_people(client)]
    assert people
    assert 'Mira' in shown['audience']['likes'] and 'Spock' in shown['audience']['likes']
    assert set(people) <= set(shown['audience']['likes'])
    comments = shown['audience']['comments']
    assert len(comments) == user_posts.MAX_COMMENTS
    assert len({comment['text'] for comment in comments}) == len(comments)
    # Friends of friends say whose they are.
    for comment in comments:
        if comment['author'] == 'person':
            assert comment['role'].startswith("Mira's ")
    assert set(shown['audience']['likes']) <= {*people, 'Mira', 'Spock'}
    # Spock is reserved: few, dry words, never the chatty ones.
    chatty = {*user_posts.LINES['close'], *user_posts.LINES['friendly']}
    assert all(comment['text'] not in chatty for comment in comments if comment['name'] == 'Spock')


def test_the_same_people_join_in_whoever_is_the_main_companion(client, city, clock, everyone_joins_in):
    from test_groups import companion_named

    from companion import cast
    spock = companion_named(client, 'Spock')
    clock.advance(timedelta(minutes=1))
    made = post(client, 'Rainy Sunday, big pot of soup.')
    clock.advance(user_posts.CIRCLE_WINDOW)

    def audience():
        return next(found for found in feed(client)['posts'] if found['id'] == made['id'])['audience']
    before = audience()
    assert {'Mira', 'Spock'} <= set(before['likes'])
    cast.focus_on(client.app.state.database, spock)
    assert audience() == before


def test_nobody_joins_in_on_a_post_from_before_they_were_around(client, city, clock, everyone_joins_in):
    from test_groups import companion_named
    made = post(client, 'First post!')
    clock.advance(timedelta(minutes=5))
    companion_named(client, 'Billy Hart')
    clock.advance(user_posts.CIRCLE_WINDOW)
    shown = next(found for found in feed(client)['posts'] if found['id'] == made['id'])
    assert 'Mira' in shown['audience']['likes'] and 'Billy Hart' not in shown['audience']['likes']


def test_a_down_or_sick_post_gets_kind_words():
    companion = {'kind': 'companion', 'style': 'usual'}
    assert user_posts.pool('Home sick with the flu.', companion) == user_posts.LINES['sick']
    assert user_posts.pool('Rough day at work.', companion) == user_posts.LINES['down']
    assert user_posts.pool('Coffee or tea?', companion) == user_posts.LINES['question']
    assert user_posts.pool('New haircut!', companion) == user_posts.LINES['close']
    assert user_posts.pool('New haircut!', {'kind': 'person', 'style': ''}) == user_posts.LINES['friendly']
    assert user_posts.pool('Rough day.', {'kind': 'companion', 'style': 'reserved'}) == \
        social.RESERVED_COMMENTS['down']


def test_their_people_join_in_one_step_further_out(client, city, clock, everyone_joins_in, monkeypatch):
    monkeypatch.setattr(user_posts, 'FAR', 1)
    monkeypatch.setattr(user_posts, 'FAR_LIKE', 1)
    reconcile(client)
    made = post(client, 'New haircut!')
    clock.advance(user_posts.FAR_WINDOW)
    shown = next(found for found in feed(client)['posts'] if found['id'] == made['id'])
    people = {person['name'] for person in circle_people(client)}
    further = [name for name in shown['audience']['likes'] if name not in {*people, 'Mira'}]
    assert further
    with client.app.state.database.connect() as connection:
        crowd = user_posts.crowd(connection, clock.now())
    far = [who for who in crowd if who.get('far')]
    assert {who['name'] for who in far} == set(further)
    # They say whose people they are, and nothing that claims to know the user.
    assert all(who['friend'] in people and who['role'].startswith(f"{who['friend']}'s ") for who in far)
    assert user_posts.pool('New haircut!', far[0]) == user_posts.LINES['far']
    assert len({who['name'] for who in crowd}) == len(crowd)


def test_the_closer_the_companion_is_to_someone_the_more_they_notice(client, city, clock, monkeypatch):
    reconcile(client)
    with client.app.state.database.connect() as connection:
        reaches = {}
        for level in range(1, 6):
            monkeypatch.setattr(user_posts, 'tie', lambda *_args, level=level: level)
            reaches[level] = user_posts.crowd(connection, clock.now())[1]['like']
    assert [reaches[level] for level in range(1, 6)] == sorted(reaches.values())
    assert reaches[1] < reaches[3] < reaches[5]


def test_closer_means_more_of_their_circle_notices():
    assert list(user_posts.TIE) == sorted(user_posts.TIE)
    assert 0 < user_posts.FAR < 1
    assert list(user_posts.REACH) == sorted(user_posts.REACH)
    assert list(user_posts.LIKES) == sorted(user_posts.LIKES)
    assert list(user_posts.COMMENTS) == sorted(user_posts.COMMENTS)


def test_your_own_post_can_be_removed_but_not_reacted_to_or_discussed(client, city):
    made = post(client, 'Hello, everyone.')
    assert client.post(f"/api/feed/{made['id']}/reaction", json={'reaction': 'heart'}).status_code == 409
    database = client.app.state.database

    def messages():
        with database.connect() as connection:
            return connection.execute('SELECT COUNT(*) FROM messages').fetchone()[0]
    before = messages()
    discuss = client.post(f"/api/feed/{made['id']}/discuss", json={'text': 'Hi', 'client_id': 'client-0001'})
    assert discuss.status_code == 409 and messages() == before
    removed = client.post(f"/api/feed/{made['id']}/remove")
    assert removed.status_code == 200 and removed.json()['text'] == ''
    assert made['id'] not in {found['id'] for found in feed(client, hidden=True)['posts']}


@pytest.mark.parametrize('text', ['', '   ', 'x' * (user_posts.TEXT_LIMIT + 1)])
def test_a_post_needs_some_words_and_not_too_many(client, city, text):
    assert client.post('/api/feed/mine', json={'text': text}).status_code == 422


def test_a_post_from_later_waits_after_going_back_in_time(client, city, clock):
    made = post(client, 'From the future.')
    clock.advance(timedelta(hours=-2))
    assert made['id'] not in {found['id'] for found in feed(client)['posts']}


def circle_people(client) -> list[dict]:
    database = client.app.state.database
    with database.connect() as connection:
        from companion.characters import require_current
        return list(social.active_people(connection, require_current(connection)['active_timeline_id']).values())


@pytest.mark.parametrize(('home', 'unfit'), [
    ('camelot', r'\b(?:TV|episode|Movie|pizza|Tacos|Ramen|coffee|Iced)\b'),
    ('long-meridian', r'\b(?:Beach|Sunrise|Sunset|outside)\b'),
])
def test_status_posts_and_questions_fit_the_world(client, clock, home, unfit):
    client.post('/api/companion', json={'name': 'Wren', 'timezone': 'UTC', 'home_city': home}).raise_for_status()
    database = client.app.state.database
    with database.connect() as connection:
        found = current(connection)
        fits = social.fits_world(connection, found['version']['definition'])
        posts = social.day_posts(connection, found, {}, clock.now() - timedelta(days=300), clock.now())
    texts = [' '.join([post['content']['text'], *post['content'].get('options', ())]) for post in posts
             if post['kind'] in ('status', 'question')]
    assert len(texts) > 100
    assert not [text for text in texts if re.search(unfit, text)]
    assert fits('Small wins today.') and not fits('Is pineapple on pizza okay?' if home == 'camelot' else
                                                  'Beach or mountains?')


def test_a_question_is_never_asked_twice_answered_or_not(client, city, clock, monkeypatch):
    # Vanta 2026-11-01: Sett asked "Thinking about cutting my hair short. Yes or no?" again days after it was answered.
    monkeypatch.setattr(social, 'QUESTION_CHANCE', 1)
    live_days(client, clock, 1)
    first = next(post for post in feed(client)['posts'] if post['kind'] == 'question')
    client.post(f"/api/feed/{first['id']}/answer", json={'option': first['options'][0], 'client_id': 'answer-101'}
                ).raise_for_status()
    for _ in range(8):  # Read each day, as the feed only writes the last few days.
        live_days(client, clock, 1)
        feed(client)
    asked = [post['text'] for post in feed(client)['posts'] if post['kind'] == 'question']
    assert len(asked) >= 9 and len(set(asked)) == len(asked)
    # Reading again keeps each day's question as it was posted.
    assert [post['text'] for post in feed(client)['posts'] if post['kind'] == 'question'] == asked


def test_a_year_of_posts_keeps_finding_new_things_to_say(client, clock):
    client.post('/api/companion', json={'name': 'Wren', 'timezone': 'UTC', 'location': 'Fells Point, Baltimore'}
                ).raise_for_status()
    with client.app.state.database.connect() as connection:
        posts = social.day_posts(connection, current(connection), {}, clock.now() - timedelta(days=365), clock.now())
    questions = [post['content']['text'] for post in posts if post['kind'] == 'question']
    # About one day in five has a question, so a year never runs through the bank.
    assert len(questions) > 40 and len(set(questions)) == len(questions)
    statuses = [(post['occurs_at'], post['content']['text']) for post in posts if post['kind'] == 'status']
    last: dict[str, datetime] = {}
    for occurs_at, text in sorted(statuses):
        moment = datetime.fromisoformat(occurs_at)
        assert text not in last or moment - last[text] >= social.STATUS_GAP or text in social.STATUS['grief'], text
        last[text] = moment


@pytest.mark.parametrize('home', ['camelot', 'london-1895', 'long-meridian', None])
def test_every_world_has_a_hundred_questions_and_thoughts_that_fit_it(client, home):
    body = {'name': 'Wren', 'timezone': 'UTC', **({'home_city': home} if home else {'location': 'Baltimore'})}
    client.post('/api/companion', json=body).raise_for_status()
    with client.app.state.database.connect() as connection:
        fits = social.fits_world(connection, current(connection)['version']['definition'])
    asked = [text for text, options in social.QUESTIONS if fits(' '.join([text, *options]), text)]
    thoughts = [line for line in social.STATUS['any'] if fits(line)]
    assert len(asked) >= 100 and len(thoughts) >= 100
    allowed = {'camelot': {'anywhen'}, 'london-1895': {'anywhen', 'since_1850'}}.get(home)
    assert not allowed or {social.WHEN[text] for text in [*asked, *thoughts]} <= allowed
    # A knight never asks about tattoos or karaoke; a Victorian never about cereal or a movie night.
    assert ('Should I get bangs?' in asked) == (home != 'camelot')
    assert ('Movie night: something scary or something cozy?' in asked) == (home in ('long-meridian', None))


def test_a_back_when_year_never_hears_of_later_things(client, monkeypatch):
    from companion.world import decades
    client.post('/api/companion', json={'name': 'Wren', 'timezone': 'UTC', 'location': 'Baltimore'}).raise_for_status()
    monkeypatch.setattr(decades, 'world_year', lambda: 1995)
    with client.app.state.database.connect() as connection:
        fits = social.fits_world(connection, current(connection)['version']['definition'])
    assert not fits('Today I am mostly vibes.') and not fits('In my comfort era.')
    assert not fits('Honest question: is cereal a soup? Yes Absolutely not', 'Honest question: is cereal a soup?')
    assert fits('Should I try karaoke this week? Sing your heart out Spare us', 'Should I try karaoke this week?')


def test_the_feed_line_banks_are_big_enough():
    assert len(social.QUESTIONS) >= 100 and len(social.STATUS['any']) >= 100
    assert set(social.WHEN.values()) == {'anywhen', 'since_1850', 'modern'}
    assert len({text for text, _options in social.QUESTIONS}) == len(social.QUESTIONS)
    assert all(len(options) == 2 and all(0 < len(option) <= 24 for option in options)
               for _text, options in social.QUESTIONS)


def test_once_every_question_was_asked_the_oldest_come_back_first():
    questions = [('A?', ('Yes', 'No')), ('B?', ('Yes', 'No')), ('C?', ('Yes', 'No')), ('D?', ('Yes', 'No'))]
    asked = {'A?': '2026-01-04', 'B?': '2026-01-01', 'C?': '2026-01-02', 'D?': '2026-01-03'}
    assert {social.question_content(f'seed-{n}', questions, asked)['text'] for n in range(40)} == {'B?', 'C?'}
    assert social.question_content('seed', questions, {'A?': '2026-01-01'})['text'] != 'A?'
