"""The town paper: a weekly local paper written from what happened in the world (companion/world/paper.py)."""
from datetime import date

from test_small_world import fellows, live, neighbor, one_haunt, steady  # noqa: F401 - fixtures
from test_social_circle import make

from companion.world import paper


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def test_issues_come_out_on_sundays():
    assert paper.issue_date(date(2026, 10, 11)) == date(2026, 10, 11)
    assert paper.issue_date(date(2026, 10, 14)) == date(2026, 10, 11)
    assert paper.issue_date(date(2026, 10, 17)) == date(2026, 10, 11)


def test_this_weeks_paper_reports_on_the_town(client, clock, fellows, one_haunt):  # noqa: F811
    mira = make(client, 'Warm and curious.', home_city='baltimore')
    sam = neighbor(client, 'Sam Ortiz')
    live(client, clock, [mira['id'], sam], 4)
    from conftest import reconcile
    reconcile(client)
    found = ok(client.get('/api/life/paper'))
    print('\nPAPER', found)
    assert found['title'] == 'The Baltimore Weekly'
    assert date.fromisoformat(found['date']).weekday() == 6 and found['next'] is None
    assert found['ahead']['weather'].startswith('Highs around')
    older = ok(client.get('/api/life/paper', params={'day': found['previous']}))
    assert older['date'] == found['previous'] and older['next'] == found['date']
    # The same issue reads the same every time.
    assert ok(client.get('/api/life/paper', params={'day': found['previous']})) == older
    assert client.get('/api/life/paper', params={'day': 'soon'}).status_code == 422


def test_goal_stories_are_one_an_issue_public_and_say_how_long_they_really_took():
    """A Gazette once ran three hobby wins a week, each 'had been trying to ... for weeks' whatever it took."""
    from datetime import timedelta

    from companion.world import catalog, townsfolk
    data = catalog.city('baltimore')
    day, spans, shapes = paper.issue_date(date(2026, 11, 8)), set(), set()
    for back in range(30):
        sunday = day - timedelta(weeks=back)
        items = paper.townsfolk_news(data, sunday)
        assert len(items) <= paper.MOST_GOAL_STORIES == 1
        for item in items:
            sheet = next(sheet for sheet in paper.sample(data, sunday) if sheet['key'] == item['key'])
            state = townsfolk.story(sheet, data, sunday)
            assert townsfolk.newsworthy(data, state['done_id'])
            assert state['done_id'] in townsfolk.GOAL_NEWS
            assert paper.span(state['took'])[1] in item['text']
            spans.add(paper.span(state['took'])[1])
            shapes.add(item['text'].split(' ')[0])
    assert len(spans) > 2 and len(shapes) > 2


def test_private_goals_stay_out_of_the_paper():
    from companion.world import catalog, townsfolk
    assert not townsfolk.newsworthy({}, 'bird-list') and not townsfolk.newsworthy({}, 'emergency-fund')
    assert townsfolk.newsworthy({}, 'mural')
    pellmouth = catalog.city('pellmouth')
    assert townsfolk.newsworthy(pellmouth, 'pellmouth-chowder')
    assert not townsfolk.newsworthy(pellmouth, 'pellmouth-boston-job')


def test_how_long_a_goal_took_reads_plainly():
    assert paper.span(1) == ('for a week', 'a week', 'a week ago')
    assert paper.span(4)[0] == 'for four weeks'
    assert paper.span(10)[1] == 'about two months'
    assert paper.span(52)[1] == 'about a year'
    assert paper.span(200)[0] == 'for years'
