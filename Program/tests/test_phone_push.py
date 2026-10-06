"""Notifications on a paired phone while the app is closed (Web Push)."""
# ruff: noqa: F811 - the phone fixtures come from test_phone_access
import json

import httpx
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from test_phone_access import enabled, net, pair, phone  # noqa: F401 - fixtures

from companion.phone import push
from companion.phone.push import b64, unb64

# RFC 8291 Appendix A.
PHONE_PUBLIC = 'BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4'
AUTH = 'BTBZMqHH6r4Tts7J_aSIgg'
ENDPOINT = 'https://push.example.net/send/abc'


def subscription(endpoint=ENDPOINT):
    return {'endpoint': endpoint, 'expirationTime': None, 'keys': {'p256dh': PHONE_PUBLIC, 'auth': AUTH}}


@pytest.fixture
def sent(app):
    """Push service stand-in: records each request and answers with the next status (201 by default)."""
    requests, statuses = [], []

    def handle(request):
        requests.append(request)
        return httpx.Response(statuses.pop(0) if statuses else 201)
    app.state.push.transport = httpx.MockTransport(handle)
    return requests, statuses


@pytest.fixture
def subscribed(client, phone, companion, enabled):
    pair(client, phone)
    response = phone.put('/api/phone/push', json=subscription())
    assert response.status_code == 200, response.text
    return response.json()


def notice(kind='message'):
    return {'id': 'delivery-1', 'kind': kind, 'title': 'Mira', 'body': 'Are you up?', 'post_ids': []}


def test_encryption_matches_the_rfc_example():
    sender = ec.derive_private_key(int.from_bytes(unb64('yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw'), 'big'),
                                   ec.SECP256R1())
    body = push.encrypt(b'When I grow up, I want to be a watermelon', PHONE_PUBLIC, AUTH,
                        salt=unb64('DGv6ra1nlYgDCS1FRnbzlw'), sender=sender)
    assert b64(body) == ('DGv6ra1nlYgDCS1FRnbzlwAAEABBBP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInm'
                         'YWAmS6TlzAC8wEqKK6PBru3jl7A_yl95bQpu6cVPTpK4Mqgkf1CXztLVBSt2Ks3oZwbuwXPXLWyouBWLVWGNWQexS'
                         'gSxsj_Qulcy4a-fN')


def test_the_vapid_header_is_signed_by_the_kept_key(app):
    key = push.signing_key(app.state.vault)
    assert push.public_bytes(push.signing_key(app.state.vault)) == push.public_bytes(key)
    header = push.vapid_header(key, ENDPOINT, 1_000_000)
    token, public = header.removeprefix('vapid t=').split(', k=')
    head, claims, signature = token.split('.')
    assert json.loads(unb64(claims)) == {'aud': 'https://push.example.net', 'exp': 1_000_000 + 12 * 3600,
                                         'sub': push.CONTACT}
    raw = unb64(signature)
    verifier = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), unb64(public))
    verifier.verify(encode_dss_signature(int.from_bytes(raw[:32], 'big'), int.from_bytes(raw[32:], 'big')),
                    f'{head}.{claims}'.encode(), ec.ECDSA(hashes.SHA256()))


def test_a_paired_phone_subscribes_and_unsubscribes(client, phone, subscribed):
    assert phone.get('/api/phone/push').json()['subscribed']
    assert len(unb64(phone.get('/api/phone/push').json()['public_key'])) == 65
    assert phone.delete('/api/phone/push').json() == {'subscribed': False}
    assert not phone.get('/api/phone/push').json()['subscribed']


def test_only_a_paired_phone_subscribes(client, phone, companion, enabled):
    assert client.put('/api/phone/push', json=subscription()).status_code == 409
    assert phone.put('/api/phone/push', json=subscription()).status_code == 401
    pair(client, phone)
    assert phone.put('/api/phone/push', json=subscription('http://10.0.0.1/inside')).status_code == 422
    bad = {**subscription(), 'keys': {'p256dh': b64(b'x' * 65), 'auth': AUTH}}
    assert phone.put('/api/phone/push', json=bad).status_code == 422


def test_a_notification_goes_to_each_subscribed_phone(app, subscribed, sent):
    requests, _statuses = sent
    assert app.state.push.send(notice()) == 1
    request = requests[0]
    assert str(request.url) == ENDPOINT and request.headers['content-encoding'] == 'aes128gcm'
    assert request.headers['authorization'].startswith('vapid t=') and int(request.headers['ttl']) > 0
    assert b'Are you up?' not in request.content


def test_a_phone_the_push_service_forgot_is_dropped(app, phone, subscribed, sent):
    _requests, statuses = sent
    statuses.append(410)
    assert app.state.push.send(notice()) == 0
    assert not phone.get('/api/phone/push').json()['subscribed']


def test_removing_a_phone_stops_its_notifications(app, client, phone, subscribed, sent):
    device = client.get('/api/phone').json()['devices'][0]
    client.delete(f"/api/phone/devices/{device['id']}")
    assert app.state.push.send(notice()) == 0 and not sent[0]


def test_phones_wait_while_the_companion_is_in_use_on_the_pc(app, client, subscribed, sent, monkeypatch, clock):
    asked = []
    monkeypatch.setattr(push.notifications, 'deliver',
                        lambda _database, focused: asked.append(focused) or {'notification': notice('post')})
    client.post('/api/notifications/next', json={'focused': True})
    app.state.push.tick()
    clock.advance(push.PC_FOCUS)
    app.state.push.tick()
    assert asked == [True, True, False]
    # Each delivery, the PC's own included, also went to the phone; posts open the Feed.
    assert len(sent[0]) == 3


def test_nothing_is_taken_for_phones_when_none_listen(app, monkeypatch):
    monkeypatch.setattr(push.notifications, 'deliver', lambda *_args: pytest.fail('nothing should be delivered'))
    assert app.state.push.tick() is None


def test_the_payload_says_where_a_tap_goes():
    assert json.loads(push.payload(notice('message')))['view'] == 'conversation'
    assert json.loads(push.payload(notice('digest'))) == {'title': 'Mira', 'body': 'Are you up?', 'tag': 'delivery-1',
                                                          'view': 'feed'}
