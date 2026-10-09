"""Who may use the Companion from a phone, and what a phone may change.

The server only ever listens on this PC. `tailscale serve` forwards a private https address on the user's
tailnet to it, so a request came from a phone when it arrived through that proxy: it carries forwarded
headers, or names a host other than this PC. Such a request needs phone access turned on and the cookie
of a paired device. Even then a few things stay on the PC: anything that runs a program or reads a file
there, restores a backup, starts the companion over or deletes them, or could send a saved API key to a
new address. A lost phone is revoked in Settings > Phone access.

With "Use on home Wi-Fi" on, a second listener answers on the home network (companion/phone/lan.py). Every request
through it is a phone's, needs that switch on and a paired device, and must come from and name a home-network
address.
"""
import hashlib
import ipaddress
import secrets
from datetime import timedelta

from fastapi import Request
from fastapi.responses import JSONResponse, PlainTextResponse

from companion.clock import parse, stamp
from companion.database import identifier, many, one, optional
from companion.errors import DomainError, require
from companion.phone import lan

LOCAL_HOSTS = {'localhost', '127.0.0.1', '::1', 'testserver'}
# Headers a proxy in front of the server adds; the PC's own browser never sends them.
FORWARDED = ('x-forwarded-for', 'x-forwarded-host', 'forwarded', 'tailscale-user-login')
TAILNET_SUFFIX = '.ts.net'
# The addresses Tailscale gives devices: the backup address is the PC's own (companion/phone/tailscale.py).
TAILNET_ADDRESSES = (ipaddress.ip_network('100.64.0.0/10'), ipaddress.ip_network('fd7a:115c:a1e0::/48'))
COOKIE = 'companion_device'
COOKIE_AGE = 400 * 24 * 3600  # the longest browsers keep a cookie
PAIRING_LIFETIME = timedelta(minutes=10)
# Wrong codes in a row before every outstanding code is withdrawn, so codes cannot be guessed.
PAIRING_TRIES = 10
CODE_LETTERS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
SEEN_EVERY = timedelta(minutes=5)
# What an unpaired phone may ask for, besides the app's own files.
OPEN = {('GET', '/api/health'), ('GET', '/api/phone/status'), ('POST', '/api/phone/pair')}
# What a paired phone may do under /api/phone: everything else there manages phones, from the PC.
PHONE_SELF = OPEN | {('POST', '/api/phone/sign-out'), ('GET', '/api/phone/push'), ('PUT', '/api/phone/push'),
                     ('DELETE', '/api/phone/push')}
PC_ONLY = ('/api/phone', '/api/backups', '/api/import/study', '/api/companion/start-over', '/api/companion/delete',
           '/api/models/builtin-recall', '/api/logs', '/api/model-calls')
# Changes here name programs, folders or addresses on the PC, or where a saved key is sent; debug time
# backs up and can replace the workspace.
PC_ONLY_CHANGES = ('/api/connection', '/api/models', '/api/context/services', '/api/images/backends',
                   '/api/lora/settings', '/api/lora/runs', '/api/lora/adapters', '/api/debug-time')

# Where on the PC each refused change is made, so a phone says where to go instead of only "no".
PC_PLACES = (
    (('/api/images/backends',), 'Image backends are added and changed on your PC, in Settings > Images. They hold '
     'API keys and addresses on the PC, so a phone can use them but not change them.'),
    (('/api/connection', '/api/models'), 'Models are set up on your PC, in Settings > Models. They hold API keys '
     'and programs on the PC, so a phone can use them but not change them.'),
    (('/api/context/services',), 'Real-world lookup tools are set up on your PC, in Settings > Real-world lookups.'),
    (('/api/lora',), 'LoRA training is set up on your PC, in Appearance.'),
    (('/api/backups',), 'Backups are made and restored on your PC, in Settings > Backups.'),
)


def pc_only_reason(path: str) -> str:
    return next((reason for prefixes, reason in PC_PLACES if under(path, prefixes)),
                'This can only be changed on your PC.')


def host_name(request: Request) -> str:
    host = request.headers.get('host', '').strip().lower()
    if host.startswith('['):
        return host[1:].partition(']')[0]
    return host.rpartition(':')[0] if host.count(':') == 1 else host


def via_lan(request: Request) -> bool:
    return bool(request.scope.get(lan.SCOPE_KEY))


def is_remote(request: Request) -> bool:
    return (via_lan(request) or any(name in request.headers for name in FORWARDED)
            or host_name(request) not in LOCAL_HOSTS)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def phone_settings(connection) -> dict:
    return one(connection, 'SELECT * FROM phone_settings WHERE id=1')


def under(path: str, prefixes) -> bool:
    return any(path == prefix or path.startswith(prefix + '/') for prefix in prefixes)


def pc_only(method: str, path: str) -> bool:
    if (method, path) in PHONE_SELF:
        return False
    return under(path, PC_ONLY) or (method not in {'GET', 'HEAD'} and under(path, PC_ONLY_CHANGES))


def tailnet_address(name: str) -> bool:
    try:
        found = ipaddress.ip_address(name)
    except ValueError:
        return False
    return any(found in network for network in TAILNET_ADDRESSES)


def allowed_host(request: Request, address: str | None) -> bool:
    name = host_name(request)
    return (name.endswith(TAILNET_SUFFIX) or tailnet_address(name)
            or (address is not None and name == address.removeprefix('https://')))


def secure(request: Request) -> bool:
    """Whether the phone's browser reached the proxy over https; the backup address is plain http, and a browser
    drops a Secure cookie sent over http."""
    scheme = request.headers.get('x-forwarded-proto') or request.url.scheme
    return scheme.split(',')[0].strip().lower() == 'https'


class Gate:
    """Checks every request; requests from this PC pass untouched, as before phone access existed."""

    def __init__(self, database):
        self.database = database
        self.pairings: dict[str, str] = {}  # code hash -> expiry stamp
        self.failures = 0
        self.seen: dict[str, str] = {}

    async def __call__(self, request: Request, call_next):
        request.state.device = None
        if not is_remote(request):
            return await call_next(request)
        refusal = self.check(request)
        return refusal or await call_next(request)

    def check(self, request: Request):
        method, path = request.method, request.url.path
        token = request.cookies.get(COOKIE)
        with self.database.connect() as connection:
            config = phone_settings(connection)
            device = optional(connection, 'SELECT id, name FROM phone_devices WHERE token_hash=? AND revoked_at IS '
                              'NULL', (token_hash(token),)) if token else None
        if via_lan(request):
            client = request.client.host if request.client else None
            if not (lan.home_address(host_name(request)) and lan.home_address(client)):
                return PlainTextResponse('Invalid host header', status_code=400)
            if not config['lan_enabled']:
                return refuse(403, 'Home Wi-Fi access is off. Turn it on in Settings > Phone access on your PC.',
                              'lan_off')
        elif not allowed_host(request, config['address']):
            return PlainTextResponse('Invalid host header', status_code=400)
        elif not config['enabled']:
            return refuse(403, 'Phone access is off. Turn it on in Settings > Phone access on your PC.', 'phone_off')
        if device:
            request.state.device = device
            self.mark_seen(device['id'])
            if pc_only(method, path):
                return refuse(403, pc_only_reason(path), 'pc_only')
            return None
        if path.startswith('/api') and (method, path) not in OPEN:
            return refuse(401, 'Pair this phone first: scan the code in Settings > Phone access on your PC.',
                          'phone_unpaired')
        return None

    def mark_seen(self, device_id: str):
        now = self.database.clock.now()
        last = self.seen.get(device_id)
        if last and now - parse(last) < SEEN_EVERY:
            return
        self.seen[device_id] = stamp(now)
        with self.database.connect(write=True) as connection:
            connection.execute('UPDATE phone_devices SET last_seen_at=? WHERE id=?', (stamp(now), device_id))

    def new_code(self) -> tuple[str, str]:
        now = self.database.clock.now()
        self.pairings = {key: until for key, until in self.pairings.items() if parse(until) > now}
        raw = ''.join(secrets.choice(CODE_LETTERS) for _ in range(8))
        code = f'{raw[:4]}-{raw[4:]}'
        expires = stamp(now + PAIRING_LIFETIME)
        self.pairings[token_hash(raw)] = expires
        return code, expires

    def redeem(self, code: str) -> bool:
        key = token_hash(''.join(letter for letter in code.upper() if letter in CODE_LETTERS))
        expires = self.pairings.pop(key, None)
        if expires and parse(expires) > self.database.clock.now():
            self.failures = 0
            return True
        self.failures += 1
        if self.failures >= PAIRING_TRIES:
            self.pairings.clear()
            self.failures = 0
        return False


def refuse(status: int, detail: str, code: str):
    return JSONResponse({'detail': detail, 'code': code}, status_code=status)


def device_view(row: dict) -> dict:
    return {key: row[key] for key in ('id', 'name', 'created_at', 'last_seen_at')}


def devices(connection) -> list[dict]:
    return [device_view(row) for row in many(
        connection, 'SELECT * FROM phone_devices WHERE revoked_at IS NULL ORDER BY created_at')]


def pair(database, gate: Gate, code: str, name: str) -> tuple[dict, str]:
    if not gate.redeem(code):
        raise DomainError('That code did not work. Make a new one in Settings > Phone access on your PC.', 403,
                          'pairing_code')
    token = secrets.token_urlsafe(32)
    row = {'id': identifier(), 'name': name.strip() or 'Phone', 'token_hash': token_hash(token),
           'created_at': database.now(), 'last_seen_at': database.now()}
    with database.connect(write=True) as connection:
        connection.execute('INSERT INTO phone_devices (id, name, token_hash, created_at, last_seen_at) '
                           'VALUES (:id, :name, :token_hash, :created_at, :last_seen_at)', row)
    return device_view(row), token


def revoke(database, device_id: str):
    with database.connect(write=True) as connection:
        changed = connection.execute('UPDATE phone_devices SET revoked_at=? WHERE id=? AND revoked_at IS NULL',
                                     (database.now(), device_id)).rowcount
        connection.execute('DELETE FROM phone_push WHERE device_id=?', (device_id,))
    require(changed == 1, 'This phone is not paired.', 404)
