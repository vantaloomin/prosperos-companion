"""Notifications on a paired phone while the app is closed: Web Push (RFC 8030, 8291, 8292).

The phone's browser gives an address at its push service (Apple's or Google's) and a key. Each
notification is encrypted for that phone before it leaves the PC, so the push service carries it without
being able to read it. What a notification says, and when, is decided by companion/notifications.py as for
the PC (quiet hours, the daily cap, the preview setting); this only carries it. The signing key that names
this Companion to push services is kept in the OS credential vault.
"""
import asyncio
import base64
import contextlib
import hashlib
import hmac
import json
import os
import struct
import time
from datetime import timedelta
from urllib.parse import urlsplit

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from companion import notifications
from companion.clock import parse
from companion.database import identifier, many
from companion.errors import require

VAPID_REFERENCE = 'phone-push-vapid'
# Push services want a contact for the sender; this names the app rather than the user.
CONTACT = 'https://github.com/vantaloomin/prosperos-companion'
EVERY = 60
# While the Companion is open and focused on the PC, phones stay quiet, as the PC's own notifications do.
PC_FOCUS = timedelta(minutes=2, seconds=30)
RECORD_SIZE = 4096
TTL = 24 * 3600


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + '=' * (-len(text) % 4))


def public_bytes(key: ec.EllipticCurvePrivateKey) -> bytes:
    return key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)


def signing_key(vault) -> ec.EllipticCurvePrivateKey:
    saved = vault.get(VAPID_REFERENCE)
    if saved:
        return ec.derive_private_key(int.from_bytes(unb64(saved), 'big'), ec.SECP256R1())
    key = ec.generate_private_key(ec.SECP256R1())
    vault.put(VAPID_REFERENCE, b64(key.private_numbers().private_value.to_bytes(32, 'big')))
    return key


def vapid_header(key: ec.EllipticCurvePrivateKey, endpoint: str, now: float) -> str:
    parts = urlsplit(endpoint)
    claims = {'aud': f'{parts.scheme}://{parts.netloc}', 'exp': int(now) + 12 * 3600, 'sub': CONTACT}
    unsigned = '.'.join(b64(json.dumps(item, separators=(',', ':')).encode()) for item in
                        ({'typ': 'JWT', 'alg': 'ES256'}, claims))
    r, s = decode_dss_signature(key.sign(unsigned.encode('ascii'), ec.ECDSA(hashes.SHA256())))
    token = f'{unsigned}.{b64(r.to_bytes(32, "big") + s.to_bytes(32, "big"))}'
    return f'vapid t={token}, k={b64(public_bytes(key))}'


def hkdf(salt: bytes, secret: bytes, info: bytes, length: int) -> bytes:
    """HKDF-SHA256 with a single expand block, which covers every length used here."""
    prk = hmac.new(salt, secret, hashlib.sha256).digest()
    return hmac.new(prk, info + b'\x01', hashlib.sha256).digest()[:length]


def encrypt(payload: bytes, p256dh: str, auth: str, salt: bytes | None = None,
            sender: ec.EllipticCurvePrivateKey | None = None) -> bytes:
    """One aes128gcm record (RFC 8188) for the phone's key (RFC 8291)."""
    phone_public = unb64(p256dh)
    phone_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), phone_public)
    sender = sender or ec.generate_private_key(ec.SECP256R1())
    sender_public = public_bytes(sender)
    shared = sender.exchange(ec.ECDH(), phone_key)
    ikm = hkdf(unb64(auth), shared, b'WebPush: info\x00' + phone_public + sender_public, 32)
    salt = salt or os.urandom(16)
    key = hkdf(salt, ikm, b'Content-Encoding: aes128gcm\x00', 16)
    nonce = hkdf(salt, ikm, b'Content-Encoding: nonce\x00', 12)
    body = AESGCM(key).encrypt(nonce, payload + b'\x02', None)
    return salt + struct.pack('!IB', RECORD_SIZE, len(sender_public)) + sender_public + body


def check_subscription(endpoint: str, p256dh: str, auth: str):
    require(urlsplit(endpoint).scheme == 'https', 'This browser gave an address that is not https.', 422)
    try:
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), unb64(p256dh))
        require(len(unb64(auth)) == 16, 'This browser gave a key that does not fit.', 422)
    except ValueError:
        require(False, 'This browser gave a key that does not fit.', 422)


def subscribe(database, device_id: str, endpoint: str, p256dh: str, auth: str):
    check_subscription(endpoint, p256dh, auth)
    with database.connect(write=True) as connection:
        connection.execute('DELETE FROM phone_push WHERE device_id=? OR endpoint=?', (device_id, endpoint))
        connection.execute('INSERT INTO phone_push (id, device_id, endpoint, p256dh, auth, created_at) '
                           'VALUES (?, ?, ?, ?, ?, ?)', (identifier(), device_id, endpoint, p256dh, auth,
                                                         database.now()))


def unsubscribe(database, device_id: str):
    with database.connect(write=True) as connection:
        connection.execute('DELETE FROM phone_push WHERE device_id=?', (device_id,))


def subscribed(database, device_id: str) -> bool:
    with database.connect() as connection:
        return bool(many(connection, 'SELECT id FROM phone_push WHERE device_id=?', (device_id,)))


def payload(notification: dict) -> bytes:
    view = 'conversation' if notification['kind'] == 'message' else 'feed'
    return json.dumps({'title': notification['title'], 'body': notification['body'], 'tag': notification['id'],
                       'view': view}).encode('utf-8')


class Pusher:
    """Sends each notification to subscribed phones, and checks for one once a minute when no window does."""

    def __init__(self, database, vault, transport: httpx.BaseTransport | None = None):
        self.database = database
        self.vault = vault
        self.transport = transport
        self.pc_focused_at: str | None = None

    def pc_checked(self, focused: bool):
        if focused:
            self.pc_focused_at = self.database.now()

    def pc_focused(self) -> bool:
        return self.pc_focused_at is not None and \
            self.database.clock.now() - parse(self.pc_focused_at) < PC_FOCUS

    def targets(self) -> list[dict]:
        with self.database.connect() as connection:
            return many(connection, 'SELECT phone_push.* FROM phone_push JOIN phone_devices ON '
                        'phone_devices.id=phone_push.device_id WHERE phone_devices.revoked_at IS NULL')

    def tick(self) -> dict | None:
        """Takes the next notification for phones, unless the PC is in use or no phone listens."""
        if not self.targets():
            return None
        result = notifications.deliver(self.database, self.pc_focused())
        if result['notification']:
            self.send(result['notification'])
        return result['notification']

    def send(self, notification: dict) -> int:
        targets = self.targets()
        if not targets:
            return 0
        key, body, sent, gone = signing_key(self.vault), payload(notification), 0, []
        with httpx.Client(timeout=15, transport=self.transport) as client:
            for target in targets:
                try:
                    response = client.post(target['endpoint'], content=encrypt(body, target['p256dh'], target['auth']),
                                           headers={'TTL': str(TTL), 'Urgency': 'normal',
                                                    'Content-Encoding': 'aes128gcm',
                                                    'Content-Type': 'application/octet-stream',
                                                    'Authorization': vapid_header(key, target['endpoint'],
                                                                                  time.time())})
                except httpx.HTTPError:
                    continue
                if response.status_code in (404, 410):
                    gone.append(target['id'])
                sent += response.is_success
        if gone:
            with self.database.connect(write=True) as connection:
                connection.executemany('DELETE FROM phone_push WHERE id=?', [(item,) for item in gone])
        return sent

    async def run_forever(self):
        while True:
            await asyncio.sleep(EVERY)
            with contextlib.suppress(Exception):
                await asyncio.to_thread(self.tick)
