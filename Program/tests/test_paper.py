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
