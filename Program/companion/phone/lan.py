"""Phone access on the home network, without Tailscale: an opt-in second listener (off by default).

The app itself keeps listening only on this PC. Turning on "Use on home Wi-Fi" in Settings > Phone access opens a
second port (8776 unless COMPANION_LAN_PORT says otherwise) on every network the PC is on. Every request through
it counts as a phone's, whatever headers it carries, so it needs a paired device like a request through
Tailscale, and only addresses on a private home network are answered (companion/phone/access.py). It is plain
http, so anyone on the same network could read what passes; the switch says so.
"""
import asyncio
import contextlib
import ipaddress
import logging
import os
import socket
import sys

import uvicorn

from companion.errors import DomainError
from companion.identity import DEFAULT_PORT

PORT_ENV = 'COMPANION_LAN_PORT'
# Set on every request that came in through the home-network listener.
SCOPE_KEY = 'companion_lan'
# Home networks: private, link-local and unique-local addresses. Tailscale's own range is not one.
HOME_NETWORKS = tuple(ipaddress.ip_network(network) for network in (
    '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '169.254.0.0/16', 'fc00::/7', 'fe80::/10'))
TAILNET = (ipaddress.ip_network('100.64.0.0/10'), ipaddress.ip_network('fd7a:115c:a1e0::/48'))
STOP_WAIT = 5


def port() -> int:
    try:
        return int(os.environ.get(PORT_ENV) or DEFAULT_PORT + 1)
    except ValueError:
        return DEFAULT_PORT + 1


def home_address(value: str | None) -> bool:
    try:
        found = ipaddress.ip_address((value or '').split('%')[0])
    except ValueError:
        return False
    if getattr(found, 'ipv4_mapped', None):
        found = found.ipv4_mapped
    return any(found in network for network in HOME_NETWORKS) and not any(found in network for network in TAILNET)


def addresses() -> list[str]:
    """This PC's IPv4 addresses on a home network, the one used to reach other networks first."""
    found = []
    with contextlib.suppress(OSError), socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.connect(('192.168.255.255', 9))  # picks the outgoing interface; sends nothing
        found.append(probe.getsockname()[0])
    with contextlib.suppress(OSError):
        found += [info[4][0] for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)]
    return list(dict.fromkeys(address for address in found if home_address(address)))


def marked(app):
    async def through_lan(scope, receive, send):
        if scope['type'] in {'http', 'websocket'}:
            scope = {**scope, SCOPE_KEY: True}
        await app(scope, receive, send)
    return through_lan


class QuietServer(uvicorn.Server):
    """Leaves Ctrl+C and the window closing to the main server."""

    @contextlib.contextmanager
    def capture_signals(self):
        yield

    def install_signal_handlers(self):  # uvicorn before 0.29
        pass


class LanServer:
    def __init__(self, app):
        self.app = app
        self.server: QuietServer | None = None
        self.task: asyncio.Task | None = None

    @property
    def running(self) -> bool:
        return self.task is not None and not self.task.done()

    async def start(self, number: int):
        if self.running:
            return
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if sys.platform != 'win32':  # on Windows this would let a second program share the port
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind(('0.0.0.0', number))
        except OSError as error:
            listener.close()
            raise DomainError(f'Port {number} is in use by another program, so home Wi-Fi access could not start. '
                              f'Close that program, or set {PORT_ENV} to another port, then try again.',
                              409, 'lan_port') from error
        listener.setblocking(False)
        config = uvicorn.Config(marked(self.app), lifespan='off', proxy_headers=False, access_log=False,
                                log_level='warning')
        self.server = QuietServer(config)
        self.task = asyncio.create_task(self.server.serve(sockets=[listener]))

    async def stop(self):
        if not self.running:
            return
        self.server.should_exit = True
        try:
            await asyncio.wait_for(asyncio.shield(self.task), STOP_WAIT)
        except (TimeoutError, asyncio.CancelledError, Exception):
            logging.getLogger('companion').warning('Home Wi-Fi access did not stop cleanly')
            self.task.cancel()
        self.server = self.task = None
