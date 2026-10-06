"""Phone access over Tailscale: pairing, what a phone may do, and the Tailscale command line."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from companion import backup
from companion.identity import CLIENT_HEADER
from companion.phone import access, tailscale

PHONE_HOST = 'home-vanta.tail1234.ts.net'


@pytest.fixture
def net(monkeypatch):
    """A signed-in Tailscale that serves whatever it is asked to."""
    calls = []
    monkeypatch.setattr(tailscale, 'status', lambda: {'installed': True, 'running': True, 'name': PHONE_HOST,
                                                      'install_url': tailscale.INSTALL_URL})
    monkeypatch.setattr(tailscale, 'serving', lambda port: bool(calls) and calls[-1] == ('serve', port))
    monkeypatch.setattr(tailscale, 'serve', lambda port: calls.append(('serve', port)))
    monkeypatch.setattr(tailscale, 'stop', lambda: calls.append(('stop',)))
    return calls


@pytest.fixture
def phone(app):
    """The phone's browser: https on the tailnet name, through the proxy, with its own cookie jar."""
    return TestClient(app, base_url=f'https://{PHONE_HOST}',
                      headers={CLIENT_HEADER: 'workspace', 'x-forwarded-for': '100.101.102.103'})


@pytest.fixture
def enabled(client, net):
    response = client.post('/api/phone/enable')
    assert response.status_code == 200, response.text
    return response.json()


def pair(client, phone, name='Pixel'):
    code = client.post('/api/phone/pairings').json()['code']
    return phone.post('/api/phone/pair', json={'code': code, 'name': name})


def test_this_pc_works_as_before_and_other_hosts_are_refused(client, companion):
    assert client.get('/api/companion').status_code == 200
    assert client.get('/api/phone/status').json() == {'remote': False, 'paired': False, 'device': None}
    assert client.get('/api/companion', headers={'host': 'evil.example'}).status_code == 400


def test_a_phone_is_refused_while_phone_access_is_off(phone, companion):
    response = phone.get('/api/companion')
    assert response.status_code == 403 and response.json()['code'] == 'phone_off'


def test_turning_phone_access_on_shares_this_port_on_the_tailnet(client, net, enabled):
    assert enabled['enabled'] and enabled['address'] == f'https://{PHONE_HOST}'
    assert enabled['tailscale']['serving'] and net == [('serve', 80)]
    off = client.post('/api/phone/disable').json()
    assert not off['enabled'] and net[-1] == ('stop',)


def test_turning_on_needs_tailscale_installed_and_signed_in(client, monkeypatch):
    monkeypatch.setattr(tailscale, 'status', lambda: {'installed': False, 'running': False, 'name': None,
                                                      'install_url': tailscale.INSTALL_URL})
    assert client.post('/api/phone/enable').status_code == 409
    assert client.post('/api/phone/pairings').status_code == 409


def test_an_unpaired_phone_can_only_pair(phone, companion, enabled):
    assert phone.get('/api/phone/status').json() == {'remote': True, 'paired': False, 'device': None}
    response = phone.get('/api/companion')
    assert response.status_code == 401 and response.json()['code'] == 'phone_unpaired'
    assert phone.post('/api/conversation/messages', json={'text': 'hi', 'client_id': 'abcdefgh'}).status_code == 401


def test_a_paired_phone_uses_the_companion(client, phone, companion, enabled):
    response = pair(client, phone)
    assert response.status_code == 200, response.text
    cookie = response.headers['set-cookie']
    assert 'HttpOnly' in cookie and 'Secure' in cookie and 'samesite=lax' in cookie.lower()
    status = phone.get('/api/phone/status')
    assert status.json()['paired'], status.text
    assert phone.get('/api/companion').json()['companion']['version']['name'] == 'Mira'
    assert phone.put('/api/settings', json={'chat_style': 'bubbles'}).status_code == 200
    devices = client.get('/api/phone').json()['devices']
    assert [device['name'] for device in devices] == ['Pixel'] and 'token_hash' not in devices[0]


@pytest.mark.parametrize(('method', 'path'), [
    ('get', '/api/phone'), ('post', '/api/phone/pairings'), ('get', '/api/backups'), ('post', '/api/backups'),
    ('post', '/api/import/study/inspect'), ('put', '/api/connection'), ('post', '/api/models/profiles'),
    ('post', '/api/context/services'), ('post', '/api/images/backends'), ('put', '/api/lora/settings'),
    ('post', '/api/lora/runs'), ('post', '/api/lora/adapters/import'),
])
def test_a_paired_phone_cannot_change_what_runs_on_the_pc(client, phone, companion, enabled, method, path):
    pair(client, phone)
    response = getattr(phone, method)(path) if method == 'get' else phone.request(method.upper(), path, json={})
    assert response.status_code == 403 and response.json()['code'] == 'pc_only'


def test_a_paired_phone_can_still_read_those_settings(client, phone, connected, enabled):
    pair(client, phone)
    assert phone.get('/api/connection').status_code == 200
    assert phone.get('/api/models').status_code == 200


def test_a_code_works_once_and_expires(client, phone, companion, enabled, clock):
    code = client.post('/api/phone/pairings').json()['code']
    assert phone.post('/api/phone/pair', json={'code': code.lower().replace('-', ''), 'name': ''}).status_code == 200
    other = TestClient(phone.app, base_url=f'https://{PHONE_HOST}', headers={'x-forwarded-for': '100.1.1.1',
                                                                             CLIENT_HEADER: 'workspace'})
    assert other.post('/api/phone/pair', json={'code': code}).json()['code'] == 'pairing_code'
    late = client.post('/api/phone/pairings').json()['code']
    clock.advance(access.PAIRING_LIFETIME + timedelta(seconds=1))
    assert other.post('/api/phone/pair', json={'code': late}).status_code == 403


def test_wrong_guesses_withdraw_every_code(client, phone, companion, enabled):
    code = client.post('/api/phone/pairings').json()['code']
    for _ in range(access.PAIRING_TRIES):
        assert phone.post('/api/phone/pair', json={'code': 'AAAA-AAAA'}).status_code == 403
    assert phone.post('/api/phone/pair', json={'code': code}).status_code == 403


def test_pairing_happens_on_the_phone(client, companion, enabled):
    code = client.post('/api/phone/pairings').json()['code']
    assert client.post('/api/phone/pair', json={'code': code}).status_code == 409


def test_a_removed_or_signed_out_phone_must_pair_again(client, phone, companion, enabled):
    device = pair(client, phone).json()['device']
    assert client.delete(f"/api/phone/devices/{device['id']}").json() == {'devices': []}
    assert phone.get('/api/companion').status_code == 401
    pair(client, phone, 'Second')
    assert phone.post('/api/phone/sign-out').json() == {'paired': False}
    assert phone.get('/api/companion').status_code == 401
    assert client.get('/api/phone').json()['devices'] == []


def test_only_tailnet_names_reach_the_app(phone, companion, enabled):
    response = phone.get('/api/phone/status', headers={'host': 'evil.example'})
    assert response.status_code == 400


def test_a_restored_workspace_turns_phone_access_off_and_unpairs(client, phone, app, companion, enabled):
    pair(client, phone)
    backup.hold_for_review(app.state.database)
    assert phone.get('/api/companion').json()['code'] == 'phone_off'
    assert client.get('/api/phone').json()['devices'] == []


def test_serve_passes_on_the_link_to_allow_https(monkeypatch):
    monkeypatch.setattr(tailscale, 'binary', lambda: 'tailscale')
    link = 'https://login.tailscale.com/f/serve?node=abc123'
    monkeypatch.setattr(tailscale, 'run', lambda args, timeout=10: (-1, f'Serve is not enabled.\nTo enable, visit:\n\n'
                                                                        f'         {link}\n'))
    with pytest.raises(Exception) as raised:
        tailscale.serve(8775)
    assert raised.value.code == 'tailscale_approval' and link in raised.value.message


def test_serve_retries_without_yes_on_older_tailscale(monkeypatch):
    monkeypatch.setattr(tailscale, 'binary', lambda: 'tailscale')
    calls = []

    def run(args, timeout=10):
        calls.append(args)
        return (1, 'flag provided but not defined: -yes') if '--yes' in args else (0, '')
    monkeypatch.setattr(tailscale, 'run', run)
    tailscale.serve(8775)
    assert calls[-1] == ['tailscale', 'serve', '--bg', 'http://127.0.0.1:8775']


def test_status_and_serving_read_the_json(monkeypatch):
    monkeypatch.setattr(tailscale, 'binary', lambda: 'tailscale')
    replies = {
        'status': '{"BackendState": "Running", "Self": {"DNSName": "home-vanta.tail1234.ts.net."}}',
        'serve': '{"Web": {"home-vanta.tail1234.ts.net:443": {"Handlers": {"/": {"Proxy": "http://127.0.0.1:8775"}}}}}',
    }
    monkeypatch.setattr(tailscale, 'run', lambda args, timeout=10: (0, replies[args[1]]))
    assert tailscale.status()['name'] == PHONE_HOST and tailscale.status()['running']
    assert tailscale.serving(8775) and not tailscale.serving(9000)
