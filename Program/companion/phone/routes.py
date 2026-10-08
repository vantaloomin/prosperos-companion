"""Settings > Phone access on the PC, and pairing and signing out on the phone (companion/phone/access.py)."""
import segno
from fastapi import APIRouter, Request, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import Field

from companion.errors import require
from companion.models import Input
from companion.phone import access, lan, push, tailscale

router = APIRouter(prefix='/api/phone')


class Pairing(Input):
    code: str = Field(min_length=4, max_length=20)
    name: str = Field(default='', max_length=80)


def gate(request: Request) -> access.Gate:
    return request.app.state.phone


def port(request: Request) -> int:
    return request.scope['server'][1]


def state(request: Request) -> dict:
    database = request.app.state.database
    with database.connect() as connection:
        config = access.phone_settings(connection)
        devices = access.devices(connection)
    net = tailscale.status()
    shared = tailscale.served(port(request)) if net['running'] else {'https': False, 'http': False}
    return {'enabled': bool(config['enabled']), 'address': config['address'], 'devices': devices,
            'backup_address': backup_address(net, shared, port(request)) if config['enabled'] else None,
            'tailscale': {**net, 'serving': shared['https']},
            'lan': {'enabled': bool(config['lan_enabled']), 'port': lan.port(),
                    'running': request.app.state.lan.running, 'addresses': lan_addresses()}}


def lan_addresses() -> list[str]:
    return [f'http://{address}:{lan.port()}' for address in lan.addresses()]


def backup_address(net: dict, shared: dict, number: int) -> str | None:
    """The PC's tailnet address over plain http (companion/phone/tailscale.py), when Tailscale shares it."""
    return f"http://{net['ip']}:{number}" if shared['http'] and net['ip'] else None


@router.get('/status')
def phone_status(request: Request):
    """What the interface needs before anything else: is this a phone, and is it paired."""
    device = request.state.device
    return {'remote': access.is_remote(request), 'paired': device is not None, 'device': device}


@router.post('/pair')
def pair(request: Request, response: Response, body: Pairing):
    require(access.is_remote(request), 'Open the pairing link on your phone.', 409)
    device, token = access.pair(request.app.state.database, gate(request), body.code, body.name)
    response.set_cookie(access.COOKIE, token, max_age=access.COOKIE_AGE, httponly=True,
                        secure=access.secure(request), samesite='lax')
    return {'device': device}


@router.post('/sign-out')
def sign_out(request: Request, response: Response):
    device = request.state.device
    require(device is not None, 'This phone is not paired.', 409)
    access.revoke(request.app.state.database, device['id'])
    response.delete_cookie(access.COOKIE, httponly=True, secure=access.secure(request), samesite='lax')
    return {'paired': False}


@router.get('')
def read_phone_access(request: Request):
    return state(request)


@router.post('/enable')
def enable(request: Request):
    net = tailscale.status()
    require(net['installed'], 'Install Tailscale on this PC first, then sign in.', 409)
    require(net['running'], 'Open Tailscale on this PC and sign in first.', 409)
    tailscale.serve(port(request))
    database = request.app.state.database
    with database.connect(write=True) as connection:
        connection.execute('UPDATE phone_settings SET enabled=1, address=?, updated_at=? WHERE id=1',
                           (f"https://{net['name']}", database.now()))
    return state(request)


@router.post('/disable')
def disable(request: Request):
    """Stops forwarding and turns phone access off. Paired phones stay paired for next time."""
    tailscale.stop(port(request))
    database = request.app.state.database
    with database.connect(write=True) as connection:
        connection.execute('UPDATE phone_settings SET enabled=0, updated_at=? WHERE id=1', (database.now(),))
    return state(request)


@router.post('/lan/enable')
async def enable_lan(request: Request):
    """Opens the home-network listener (companion/phone/lan.py); it stays on across restarts until turned off."""
    await request.app.state.lan.start(lan.port())
    database = request.app.state.database
    with database.connect(write=True) as connection:
        connection.execute('UPDATE phone_settings SET lan_enabled=1, updated_at=? WHERE id=1', (database.now(),))
    return await run_in_threadpool(state, request)


@router.post('/lan/disable')
async def disable_lan(request: Request):
    database = request.app.state.database
    with database.connect(write=True) as connection:
        connection.execute('UPDATE phone_settings SET lan_enabled=0, updated_at=? WHERE id=1', (database.now(),))
    await request.app.state.lan.stop()
    return await run_in_threadpool(state, request)


@router.post('/pairings')
def new_pairing(request: Request):
    database = request.app.state.database
    with database.connect() as connection:
        config = access.phone_settings(connection)
    tailnet = bool(config['enabled']) and bool(config['address'])
    home = lan_addresses() if config['lan_enabled'] else []
    require(tailnet or bool(home), 'Turn phone access on first.', 409)
    code, expires = gate(request).new_code()
    backup = None
    if tailnet:
        net = tailscale.status()
        backup = backup_address(net, tailscale.served(port(request)), port(request)) if net['running'] else None
    # The QR code opens the Tailscale address when there is one, as it works away from home too.
    links = [f'{address}/?pair={code}' for address in ([config['address']] if tailnet else []) + home]
    qr = segno.make(links[0], error='m').svg_inline(border=2, dark='#1b1916', light='#ffffff', omitsize=True)
    return {'code': code, 'link': links[0], 'backup_link': backup and f'{backup}/?pair={code}',
            'lan_link': f'{home[0]}/?pair={code}' if home else None, 'expires_at': expires, 'qr_svg': qr}


@router.delete('/devices/{device_id}')
def remove_device(request: Request, device_id: str):
    access.revoke(request.app.state.database, device_id)
    with request.app.state.database.connect() as connection:
        return {'devices': access.devices(connection)}


class PushKeys(Input):
    p256dh: str = Field(min_length=10, max_length=200)
    auth: str = Field(min_length=10, max_length=100)


class PushSubscription(Input):
    model_config = Input.model_config | {'extra': 'ignore'}
    endpoint: str = Field(min_length=10, max_length=2000)
    keys: PushKeys


def this_phone(request: Request) -> dict:
    device = request.state.device
    require(device is not None, 'Turn on notifications from your paired phone.', 409)
    return device


@router.get('/push')
def read_push(request: Request):
    """The key the phone's browser needs to subscribe, and whether this phone already has."""
    device = this_phone(request)
    key = push.public_bytes(push.signing_key(request.app.state.vault))
    return {'public_key': push.b64(key), 'subscribed': push.subscribed(request.app.state.database, device['id'])}


@router.put('/push')
def save_push(request: Request, body: PushSubscription):
    device = this_phone(request)
    push.subscribe(request.app.state.database, device['id'], body.endpoint, body.keys.p256dh, body.keys.auth)
    return {'subscribed': True}


@router.delete('/push')
def remove_push(request: Request):
    push.unsubscribe(request.app.state.database, this_phone(request)['id'])
    return {'subscribed': False}
