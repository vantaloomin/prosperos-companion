"""Settings > General > Updates: asks GitHub for the newest published release and compares it with this copy.

Only runs when the user presses "Check for updates"; nothing checks in the background. The request carries no
user data, and a failure is reported as "could not check", never as an error that stops the page.
"""
import logging
import re
import sys
import time

import httpx
from fastapi import APIRouter

from companion.identity import APP_FOLDER, VERSION
from companion.providers.urls import network

log = logging.getLogger('companion')

REPOSITORY = 'vantaloomin/prosperos-companion'
LATEST_URL = f'https://api.github.com/repos/{REPOSITORY}/releases/latest'
RELEASES_PAGE = f'https://github.com/{REPOSITORY}/releases/latest'
SECONDS = 10
# GitHub allows 60 unsigned requests an hour; a repeat press within this window reuses the last answer.
REUSE_SECONDS = 300
# The Windows installer's folder holds the bundle manifest (scripts/package/build_bundle.py MANIFEST).
BUNDLE_MANIFEST = 'bundle.json'

router = APIRouter(prefix='/api/updates')
_last: dict = {}


def version_parts(text: str) -> tuple[int, ...] | None:
    """(1, 1, 5) for "v1.1.5" or "1.1.5"; None when the tag is not a plain version."""
    found = re.fullmatch(r'v?(\d+(?:\.\d+)*)', text.strip())
    return tuple(int(part) for part in found.group(1).split('.')) if found else None


def newer(latest: str, current: str = VERSION) -> bool:
    theirs, ours = version_parts(latest), version_parts(current)
    if theirs is None or ours is None:
        return False
    width = max(len(theirs), len(ours))
    return theirs + (0,) * (width - len(theirs)) > ours + (0,) * (width - len(ours))


def install_kind() -> str:
    """'installer' for the Windows installer's copy, 'folder' for a download or clone updated by its update script."""
    return 'installer' if (APP_FOLDER / BUNDLE_MANIFEST).exists() else 'folder'


def system() -> str:
    """Which update script the folder copy has: Windows/update.bat or Mac/update.command."""
    return 'windows' if sys.platform == 'win32' else 'mac' if sys.platform == 'darwin' else 'other'


async def fetch_latest(transport=None) -> dict:
    async with httpx.AsyncClient(transport=transport, timeout=SECONDS, follow_redirects=True,
                                 **({} if transport else network(LATEST_URL))) as client:
        response = await client.get(LATEST_URL, headers={'Accept': 'application/vnd.github+json',
                                                         'User-Agent': f'ProsperoCompanion/{VERSION}'})
    response.raise_for_status()
    return response.json()


async def check(transport=None, now: float | None = None) -> dict:
    now = time.monotonic() if now is None else now
    result = {'current': VERSION, 'install': install_kind(), 'system': system(), 'page': RELEASES_PAGE}
    if _last and now - _last['at'] < REUSE_SECONDS:
        return {**result, **_last['found']}
    try:
        release = await fetch_latest(transport)
        tag = str(release.get('tag_name') or '')
        found = {'status': 'newer' if newer(tag) else 'current', 'latest': tag.lstrip('v') or None,
                 'title': release.get('name') or None, 'published': release.get('published_at'),
                 'page': release.get('html_url') or RELEASES_PAGE}
    except (httpx.HTTPError, ValueError) as error:
        log.info('Update check failed: %s', type(error).__name__)
        return {**result, 'status': 'unavailable', 'latest': None, 'title': None, 'published': None}
    _last.update(at=now, found=found)
    return {**result, **found}


@router.post('/check')
async def check_now():
    return await check()
