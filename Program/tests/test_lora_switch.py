# ruff: noqa: F811 - the image test fixtures are reused by name.
"""The LoRA creator is hidden unless COMPANION_LORA_MAKER is set; profile pictures work either way."""
import pytest
from fastapi.testclient import TestClient

from companion.identity import CLIENT_HEADER
from companion.lora import MAKER_ENV
from companion.main import create_app
from companion.providers.vault import MemoryVault
from tests.test_images import add_backend, ok, png
from tests.test_lora import adapters  # noqa: F401
from tests.test_portraits import plan, wait_portraits

MAKER_ROUTES = [('get', '/api/lora/settings'), ('get', '/api/lora/trainer'), ('get', '/api/lora/runs'),
                ('get', '/api/lora/adapters'), ('get', '/api/lora/appearance'), ('get', '/api/lora/evaluations'),
                ('get', '/api/lora/generations'), ('get', '/api/lora/generations/draft'),
                ('post', '/api/lora/references'), ('post', '/api/lora/references/captions')]


def make_client(tmp_path, clock, provider, adapters):
    app = create_app(tmp_path / 'workspace' / 'companion.sqlite3', clock=clock, vault=MemoryVault(),
                     provider=provider, life_tasks=False, image_adapters=adapters)
    return TestClient(app, headers={CLIENT_HEADER: 'workspace'})


@pytest.fixture
def client(tmp_path, clock, provider, adapters, monkeypatch):
    monkeypatch.delenv(MAKER_ENV, raising=False)
    with make_client(tmp_path, clock, provider, adapters) as test_client:
        yield test_client


def test_the_creator_is_off_by_default_and_its_routes_are_not_served(client, companion):
    assert ok(client.get('/api/settings'))['lora_maker'] is False
    assert ok(client.put('/api/settings', json={'chat_sounds': True}))['lora_maker'] is False
    for method, path in MAKER_ROUTES:
        assert getattr(client, method)(path).status_code in {404, 405}, path


def test_profile_pictures_still_work_with_the_creator_off(client, companion, adapters):
    add_backend(client, kind='codex')
    adapters['codex'].outcomes = [png(1024, 1536), png(1024, 1535), png(1024, 1024)]
    draft = ok(client.get('/api/lora/portraits/draft'))
    ok(client.post('/api/lora/portraits', json=plan(draft)))
    done = wait_portraits(client)
    kept = ok(client.post(f"/api/lora/generation-images/{done['images'][0]['id']}/keep"))
    reference = kept['images'][0]['reference_id']
    ok(client.put('/api/lora/portrait', json={'reference_id': reference}))
    assert ok(client.get('/api/companion'))['companion']['portrait_reference_id'] == reference
    assert [item['id'] for item in ok(client.get('/api/lora/references'))['references']] == [reference]
    assert client.get(f'/api/lora/references/{reference}/file').status_code == 200


@pytest.mark.parametrize('value', ['1', 'true', 'ON'])
def test_the_environment_switch_turns_it_back_on(tmp_path, clock, provider, adapters, monkeypatch, value):
    monkeypatch.setenv(MAKER_ENV, value)
    with make_client(tmp_path, clock, provider, adapters) as client:
        assert ok(client.get('/api/settings'))['lora_maker'] is True
        assert client.get('/api/lora/trainer').status_code == 200
