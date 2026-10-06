"""Talks to the Tailscale command line on this PC: is it installed and signed in, and is it forwarding a
private https address on the user's tailnet to the Companion (`tailscale serve`)."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from companion.errors import DomainError

WINDOWS_PATHS = (r'C:\Program Files\Tailscale\tailscale.exe', r'C:\Program Files (x86)\Tailscale\tailscale.exe')
INSTALL_URL = 'https://tailscale.com/download'
APPROVAL_LINK = re.compile(r'https://login\.tailscale\.com/\S+')
SERVE_WAIT = 20


def binary() -> str | None:
    found = shutil.which('tailscale')
    if found or sys.platform != 'win32':
        return found
    return next((path for path in WINDOWS_PATHS if Path(path).exists()), None)


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
    """installed, running (signed in and connected) and this PC's name on the tailnet."""
    program = binary()
    if not program:
        return {'installed': False, 'running': False, 'name': None, 'install_url': INSTALL_URL}
    code, output = run([program, 'status', '--json'])
    try:
        state = json.loads(output) if code == 0 else {}
    except ValueError:
        state = {}
    name = ((state.get('Self') or {}).get('DNSName') or '').rstrip('.') or None
    return {'installed': True, 'running': state.get('BackendState') == 'Running' and bool(name), 'name': name,
            'install_url': INSTALL_URL}


def serving(port: int) -> bool:
    """Whether `tailscale serve` already forwards https to this port."""
    program = binary()
    if not program:
        return False
    code, output = run([program, 'serve', 'status', '--json'])
    try:
        config = json.loads(output) if code == 0 else {}
    except ValueError:
        return False
    targets = {handler.get('Proxy', '') for site in (config.get('Web') or {}).values()
               for handler in (site.get('Handlers') or {}).values()}
    return any(target.rstrip('/').endswith(f':{port}') for target in targets)


def serve(port: int):
    """Forwards https on the tailnet to this PC's port, in the background so it survives a restart.
    The first time, Tailscale may ask the tailnet's owner to allow https; that link is passed on."""
    program = binary()
    target = f'http://127.0.0.1:{port}'
    code, output = run([program, 'serve', '--bg', '--yes', target], timeout=SERVE_WAIT)
    if code != 0 and 'flag provided but not defined' in output:
        code, output = run([program, 'serve', '--bg', target], timeout=SERVE_WAIT)
    if code == 0:
        return
    link = APPROVAL_LINK.search(output)
    if link:
        raise DomainError(f'Tailscale needs you to allow https for your tailnet first. Open {link.group(0)}, '
                          'allow it, then turn phone access on again.', 409, 'tailscale_approval')
    raise DomainError(f'Tailscale could not share the Companion: {last_line(output)}', 502, 'tailscale_serve')


def stop():
    program = binary()
    if program:
        run([program, 'serve', '--https=443', 'off'])


def last_line(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return lines[-1] if lines else 'it did not say why.'
