import asyncio

import httpx
import pytest

from companion import updates


@pytest.fixture(autouse=True)
def fresh():
    updates._last.clear()
    yield
    updates._last.clear()


def answering(tag: str, calls: list | None = None, status: int = 200):
    def handler(request: httpx.Request):
        if calls is not None:
            calls.append(request.url)
        return httpx.Response(status, json={'tag_name': tag, 'name': 'Such People In\'t',
                                            'html_url': f'https://github.com/{updates.REPOSITORY}/releases/tag/{tag}',
                                            'published_at': '2026-10-26T14:58:00Z'})
    return httpx.MockTransport(handler)


def test_versions_compare_by_number():
    assert updates.newer('v1.1.10', '1.1.9')
    assert updates.newer('v1.2', '1.1.5')
    assert not updates.newer('v1.1.5', '1.1.5')
    assert not updates.newer('v1.1.5.0', '1.1.5')
    assert not updates.newer('v1.1.4', '1.1.5')
    assert not updates.newer('nightly', '1.1.5')


def test_a_newer_release_is_offered_with_its_page(monkeypatch):
    monkeypatch.setattr(updates, 'VERSION', '1.1.5')
    found = asyncio.run(updates.check(answering('v1.1.6'), now=0))
    assert found['status'] == 'newer'
    assert found['latest'] == '1.1.6' and found['current'] == '1.1.5'
    assert found['page'].endswith('/releases/tag/v1.1.6')
    assert found['install'] in {'installer', 'folder'}


def test_the_same_release_is_up_to_date(monkeypatch):
    monkeypatch.setattr(updates, 'VERSION', '1.1.5')
    assert asyncio.run(updates.check(answering('v1.1.5'), now=0))['status'] == 'current'


def test_a_repeat_press_reuses_the_answer_for_a_while():
    calls = []
    asyncio.run(updates.check(answering('v9.0.0', calls), now=0))
    asyncio.run(updates.check(answering('v9.0.0', calls), now=60))
    assert len(calls) == 1
    asyncio.run(updates.check(answering('v9.0.0', calls), now=updates.REUSE_SECONDS + 1))
    assert len(calls) == 2


def test_a_failed_lookup_says_so_and_is_not_kept():
    calls = []
    found = asyncio.run(updates.check(answering('v9.0.0', calls, status=403), now=0))
    assert found['status'] == 'unavailable' and found['latest'] is None
    assert found['page'] == updates.RELEASES_PAGE
    asyncio.run(updates.check(answering('v9.0.0', calls), now=1))
    assert len(calls) == 2


def test_the_installer_copy_is_told_apart(tmp_path, monkeypatch):
    monkeypatch.setattr(updates, 'APP_FOLDER', tmp_path)
    assert updates.install_kind() == 'folder'
    (tmp_path / updates.BUNDLE_MANIFEST).write_text('{}')
    assert updates.install_kind() == 'installer'


def test_the_route_answers_without_reaching_github(client, monkeypatch):
    real = updates.fetch_latest
    monkeypatch.setattr(updates, 'fetch_latest', lambda transport=None: real(answering('v99.0.0')))
    found = client.post('/api/updates/check').json()
    assert found['status'] == 'newer' and found['latest'] == '99.0.0'
