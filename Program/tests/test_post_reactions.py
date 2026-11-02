"""Who reacts to a post, and how, follows how they know the poster (companion/life/social.py stance), and rivals keep
quiet or get in a dig as Settings > Realism > Trolls and snark on posts says (life_settings.trolls_realism)."""
import json

import pytest

from companion.life import post_snark, social

OCCURS, NOW = '2026-10-30T12:00:00Z', '2026-10-31T12:00:00Z'


def person(person_id, name, role, ties=None, knowing='both', rival=False):
    return {'id': person_id, 'name': name, 'role': role, 'ties': ties or {}, 'knowing': knowing, 'rival': rival}


# Sett's circle, as the tester had it: Nari is a fan Sett hasn't met, Kaito his rival who has known Nari for years,
# and Lestara his mother, who has never met Nari.
PEOPLE = {
    'nari': person('nari', 'Nari', 'enthusiastic fangirl', {'kaito': 'known for years', 'lestara': 'knows of'},
                   knowing='they'),
    'kaito': person('kaito', 'Kaito', 'rival', {'nari': 'known for years', 'lestara': 'friends'}, rival=True),
    'lestara': person('lestara', 'Lestara', 'mother', {'nari': 'known by', 'kaito': 'friends'}),
}


@pytest.fixture
def certain(monkeypatch):
    """Everyone who could react does: the usual chances at their highest."""
    monkeypatch.setattr(social, 'LIKELY', {role: 1 for role in ('enthusiastic fangirl', 'rival', 'mother')})
    monkeypatch.setattr(social, 'COMMENT_CHANCE', 1)
    monkeypatch.setattr(social, 'COMPANION_LIKES', 1)


def reactions(post_id, author, level=social.DEFAULT_TROLLS, kind='friend', content=None):
    return social.audience(post_id, kind, author, content or {'text': 'Came for one thing, left with five.'},
                           OCCURS, NOW, PEOPLE, 'Sett', level=level)


def everyone_over(posts=60, **kwargs):
    found = [reactions(f'post-{index}', **kwargs) for index in range(posts)]
    return [name for item in found for name in item['likes']], [c for item in found for c in item['comments']]


def test_strangers_to_the_poster_seldom_see_it_and_never_comment(certain):
    likes, comments = everyone_over(author='nari')
    speakers = {comment['name'] for comment in comments}
    # Lestara has never met Nari, and Sett only knows of her as a fan: neither gushes under her post.
    assert 'Lestara' not in speakers and 'Sett' not in speakers
    assert likes.count('Lestara') < 15 and likes.count('Sett') < 15
    # Kaito has known her for years: he sees it, likes it and says something kind (he is Sett's rival, not hers).
    assert likes.count('Kaito') > 50
    assert speakers == {'Kaito'} and all(comment['text'] not in post_snark.RIVAL + post_snark.TROLL
                                         for comment in comments)


def test_family_and_friends_of_the_poster_still_join_in(certain):
    likes, comments = everyone_over(author='kaito')
    # Lestara and Kaito are friends; Nari has known him for years.
    assert likes.count('Lestara') > 50 and likes.count('Nari') > 50
    assert {'Lestara', 'Nari'} <= {comment['name'] for comment in comments}


@pytest.mark.parametrize(('level', 'bank'), [(1, post_snark.RIVAL), (2, post_snark.RIVAL + post_snark.TROLL),
                                             (3, post_snark.TROLL)])
def test_a_rival_gets_in_a_dig_on_the_companions_posts(certain, level, bank):
    _likes, comments = everyone_over(author=social.COMPANION, level=level, content={'mood': ''})
    digs = [comment['text'] for comment in comments if comment['name'] == 'Kaito']
    assert digs and all(text in bank for text in digs)
    # Everyone else is as kind as ever.
    assert all(comment['text'] not in post_snark.RIVAL + post_snark.TROLL for comment in comments
               if comment['name'] != 'Kaito')


def test_with_trolls_off_a_rival_keeps_out_of_it(certain):
    likes, comments = everyone_over(author=social.COMPANION, level=0, content={'mood': ''})
    assert 'Kaito' not in likes and 'Kaito' not in {comment['name'] for comment in comments}


@pytest.mark.parametrize(('kind', 'content'), [('status', {'tone': 'sick', 'text': 'Down with a cold.'}),
                                               ('status', {'mood': 'tired'}), ('question', {'options': ['Tea', 'Coffee']}),
                                               ('city', {'change': 'closing'})])
def test_nobody_snipes_at_someone_sick_or_at_a_question(certain, kind, content):
    _likes, comments = everyone_over(author=social.COMPANION, level=3, kind=kind, content=content)
    assert all(comment['text'] not in post_snark.RIVAL + post_snark.TROLL for comment in comments)


def test_the_companion_digs_at_a_rivals_post_and_an_ex_snipes_only_with_trolls(certain):
    people = {**PEOPLE, 'kaito': {**PEOPLE['kaito'], 'ties': {**PEOPLE['kaito']['ties'], 'lestara': 'divorced'}},
              'lestara': {**PEOPLE['lestara'], 'ties': {**PEOPLE['lestara']['ties'], 'kaito': 'divorced'}}}

    def said(level):
        return [comment for index in range(60) for comment in social.audience(
            f'post-{index}', 'friend', 'kaito', {'text': 'Won again.'}, OCCURS, NOW, people, 'Sett', level=level)
            ['comments']]
    assert all(comment['text'] in post_snark.RIVAL for comment in said(1) if comment['name'] == 'Sett')
    assert any(comment['name'] == 'Sett' for comment in said(1))
    assert not any(comment['name'] == 'Lestara' for comment in said(2))
    assert any(comment['name'] == 'Lestara' and comment['text'] in post_snark.TROLL for comment in said(3))


def test_the_stance_reads_ties_both_ways():
    assert social.stance('kaito', 'nari', PEOPLE) == 'friendly'
    assert social.stance('lestara', 'nari', PEOPLE) == 'stranger'
    assert social.stance('nari', 'lestara', PEOPLE) == 'knows of'
    assert social.stance(social.COMPANION, 'nari', PEOPLE) == 'stranger'
    assert social.stance('kaito', social.COMPANION, PEOPLE) == 'rival'
    assert social.stance('lestara', social.COMPANION, PEOPLE) == 'usual'
    # A circle person who has never met the companion doesn't see their posts as anyone close would.
    assert social.stance('x', social.COMPANION, {'x': person('x', 'X', 'stranger', knowing='companion')}) == 'stranger'


@pytest.mark.parametrize(('role', 'note', 'rival'), [
    ('rival', '', True), ('old rival', '', True), ('fighter', 'His nemesis from the Pits.', True),
    ('arch-enemy', '', True), ('close friend', '', False), ('fighter', 'They spar for fun.', False),
])
def test_a_rival_is_read_from_the_role_and_note(role, note, rival):
    row = {'role': role, 'details': json.dumps({'note': note})}
    assert social.rival_of_companion(row) is rival


def test_the_banks_are_big_and_never_repeat():
    for bank in (post_snark.RIVAL, post_snark.TROLL):
        assert len(bank) >= 100 and len(set(bank)) == len(bank)
    assert not set(post_snark.RIVAL) & set(post_snark.TROLL)


def test_the_setting_saves_and_defaults_to_rivals_only(client):
    database = client.app.state.database
    with database.connect() as connection:
        assert social.trolls(connection) == 1
    response = client.put('/api/life/settings', json={'trolls_realism': 3})
    assert response.status_code == 200 and response.json()['trolls_realism'] == 3
    with database.connect() as connection:
        assert social.trolls(connection) == 3
    assert client.put('/api/life/settings', json={'trolls_realism': 4}).status_code == 422
