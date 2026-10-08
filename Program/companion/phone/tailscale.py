"""Talks to the Tailscale command line on this PC: is it installed and signed in, and is it forwarding a
private https address on the user's tailnet to the Companion (`tailscale serve`).

It also forwards plain http on the PC's tailnet address (http://100.x.y.z:<port>) as a backup. That one needs
neither the tailnet's name lookup (MagicDNS), which a phone's private DNS setting can bypass, nor an https
certificate, which Tailscale fetches on the first visit. Tailscale encrypts the traffic between devices either
way; only phone notifications need the https address."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from companion.errors import DomainError

WINDOWS_PATHS = (r'C:\Program Files\Tailscale\tailscale.exe', r'C:\Program Files (x86)\Tailscale\tailscale.exe')
# The Mac app (App Store or standalone) keeps its command line inside the bundle and only links it onto
# PATH when the user asks it to.
MAC_PATHS = ('/Applications/Tailscale.app/Contents/MacOS/Tailscale',)
INSTALL_URL = 'https://tailscale.com/download'
APPROVAL_LINK = re.compile(r'https://login\.tailscale\.com/\S+')
SERVE_WAIT = 20
# What `tailscale status` calls the systems a phone or tablet runs.
PHONE_SYSTEMS = {'ios', 'android'}


def binary() -> str | None:
    found = shutil.which('tailscale')
    if found:
        return found
    paths = {'win32': WINDOWS_PATHS, 'darwin': MAC_PATHS}.get(sys.platform, ())
    return next((path for path in paths if Path(path).exists()), None)


def run(args: list[str], timeout: float = 10) -> tuple[int, str]:
    """The exit code and everything printed. A command still waiting at the timeout returns -1."""
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    try:
        done = subprocess.run(args, capture_output=True, text=True, timeout=timeout, creationflags=flags,
                              env={**os.environ, 'TS_NOTERM': '1'})
        return done.returncode, (done.stdout or '') + (done.stderr or '')
    except subprocess.TimeoutExpired as waiting:
        return -1, text(waiting.stdout) + text(waiting.stderr)
    except OSError as error:
        return -2, str(error)


def text(value) -> str:
    return value.decode('utf-8', 'replace') if isinstance(value, bytes) else (value or '')


def status() -> dict:
    """installed, running (signed in and connected), this PC's name and address on the tailnet, whether the
    tailnet has name lookup (MagicDNS) and https certificates, and the phones signed in to it."""
    program = binary()
    if not program:
        return {'installed': False, 'running': False, 'name': None, 'ip': None, 'magic_dns': False,
                'https': False, 'phones': [], 'install_url': INSTALL_URL}
    code, output = run([program, 'status', '--json'])
    try:
        state = json.loads(output) if code == 0 else {}
    except ValueError:
        state = {}
    me = state.get('Self') or {}
    name = (me.get('DNSName') or '').rstrip('.') or None
    # Versions too old to report MagicDNS are taken to have it, as it has been on by default since 2022.
    magic_dns = (state.get('CurrentTailnet') or {}).get('MagicDNSEnabled', True)
    return {'installed': True, 'running': state.get('BackendState') == 'Running' and bool(name), 'name': name,
            'ip': next((ip for ip in me.get('TailscaleIPs') or () if '.' in ip), None),
            'magic_dns': bool(magic_dns), 'https': bool(state.get('CertDomains')), 'phones': phones(state),
            'install_url': INSTALL_URL}


def phones(state: dict) -> list[dict]:
    """Phones and tablets on the tailnet, and whether each is connected now, so the PC can say when the phone
    has no Tailscale, or has it switched off."""
    found = [{'name': peer.get('HostName') or (peer.get('DNSName') or '').partition('.')[0] or 'Phone',
              'online': bool(peer.get('Online'))}
             for peer in (state.get('Peer') or {}).values() if (peer.get('OS') or '').lower() in PHONE_SYSTEMS]
    return sorted(found, key=lambda phone: (not phone['online'], phone['name'].lower()))


def served(port: int) -> dict:
    """Whether `tailscale serve` forwards https (port 443), and plain http on this same port, to the app."""
    program = binary()
    if not program:
        return {'https': False, 'http': False}
    code, output = run([program, 'serve', 'status', '--json'])
    try:
        config = json.loads(output) if code == 0 else {}
    except ValueError:
        config = {}
    sites = {site.rpartition(':')[2] for site, handlers in (config.get('Web') or {}).items()
             if any((handler.get('Proxy') or '').rstrip('/').endswith(f':{port}')
                    for handler in (handlers.get('Handlers') or {}).values())}
    return {'https': '443' in sites, 'http': str(port) in sites}


def serving(port: int) -> bool:
    """Whether `tailscale serve` already forwards https to this port."""
    return served(port)['https']


def share(program: str, port: int, *flags: str) -> tuple[int, str]:
    target = f'http://127.0.0.1:{port}'
    code, output = run([program, 'serve', '--bg', '--yes', *flags, target], timeout=SERVE_WAIT)
    if code != 0 and 'flag provided but not defined' in output:
        code, output = run([program, 'serve', '--bg', *flags, target], timeout=SERVE_WAIT)
    return code, output


def serve(port: int):
    """Forwards https on the tailnet to this PC's port, in the background so it survives a restart, and plain
    http on the PC's tailnet address as a backup. The first time, Tailscale may ask the tailnet's owner to allow
    https; that link is passed on. A Tailscale too old for the backup still gets the https address."""
    program = binary()
    code, output = share(program, port)
    if code == 0:
        share(program, port, f'--http={port}')
        return
    link = APPROVAL_LINK.search(output)
    if link:
        raise DomainError(f'Tailscale needs you to allow https for your tailnet first. Open {link.group(0)}, '
                          'allow it, then turn phone access on again.', 409, 'tailscale_approval')
    raise DomainError(f'Tailscale could not share the Companion: {last_line(output)}', 502, 'tailscale_serve')


def stop(port: int):
    program = binary()
    if program:
        run([program, 'serve', '--https=443', 'off'])
        run([program, 'serve', f'--http={port}', 'off'])


def last_line(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return lines[-1] if lines else 'it did not say why.'
