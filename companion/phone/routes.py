"""Settings > Phone access on the PC, and pairing and signing out on the phone (companion/phone/access.py)."""
import segno
from fastapi import APIRouter, Request, Response
from pydantic import Field

from companion.errors import require
from companion.models import Input
from companion.phone import access, tailscale

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
    return {'enabled': bool(config['enabled']), 'address': config['address'], 'devices': devices,
            'tailscale': {**net, 'serving': net['running'] and tailscale.serving(port(request))}}


@router.get('/status')
def phone_status(request: Request):
    """What the interface needs before anything else: is this a phone, and is it paired."""
    device = request.state.device
    return {'remote': access.is_remote(request), 'paired': device is not None, 'device': device}


@router.post('/pair')
def pair(request: Request, response: Response, body: Pairing):
    require(access.is_remote(request), 'Open the pairing link on your phone.', 409)
    device, token = access.pair(request.app.state.database, gate(request), body.code, body.name)
    response.set_cookie(access.COOKIE, token, max_age=access.COOKIE_AGE, httponly=True, secure=True,
                        samesite='lax')
    return {'device': device}


@router.post('/sign-out')
def sign_out(request: Request, response: Response):
    device = request.state.device
    require(device is not None, 'This phone is not paired.', 409)
    access.revoke(request.app.state.database, device['id'])
    response.delete_cookie(access.COOKIE, httponly=True, secure=True, samesite='lax')
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
    tailscale.stop()
    database = request.app.state.database
    with database.connect(write=True) as connection:
        connection.execute('UPDATE phone_settings SET enabled=0, updated_at=? WHERE id=1', (database.now(),))
    return state(request)


@router.post('/pairings')
def new_pairing(request: Request):
    database = request.app.state.database
    with database.connect() as connection:
        config = access.phone_settings(connection)
    require(bool(config['enabled']) and bool(config['address']), 'Turn phone access on first.', 409)
    code, expires = gate(request).new_code()
    link = f"{config['address']}/?pair={code}"
    qr = segno.make(link, error='m').svg_inline(border=2, dark='#1b1916', light='#ffffff', omitsize=True)
    return {'code': code, 'link': link, 'expires_at': expires, 'qr_svg': qr}


@router.delete('/devices/{device_id}')
def remove_device(request: Request, device_id: str):
    access.revoke(request.app.state.database, device_id)
    with request.app.state.database.connect() as connection:
        return {'devices': access.devices(connection)}
