"""Pictures under memes that need no image model (Hit List #50, "Memes without a picture model").

Three sources, all on this computer when a meme is sent:
- the starter pack in meme_data/pack: public-domain and CC0 pictures shipped with the app (pack.json
  credits each one);
- classic formats (meme_data/formats.json), downloaded from memegen.link the first time memes are
  sent and kept in the data folder, never in the repository. Only the format's name leaves the PC;
  the captions are drawn by the interface. Settings > Images can turn the download off;
- the user's own "Meme templates" folder in the data folder. A picture there may have a JSON file of
  the same name beside it: {"about": "...", "moods": [...], "boxes": [{"x", "y", "w", "h"}, ...]},
  boxes as fractions of the picture, top to bottom; without one the text goes top and bottom.

Each picture has moods (memes.py); a meme takes a picture with its caption's mood, and the user's
own pictures fit any mood unless their JSON says otherwise. Downloads run in the background, so
sending a meme never waits on the network.
"""
import json
import random
import threading
import time
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import httpx

from companion.images import storage
from companion.images.adapters.base import AdapterError
from companion.images.memes import DATA

FOLDER = 'Meme templates'
CACHE = 'meme-formats'
TYPES = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.gif': 'image/gif'}
MOST_BYTES = 8_000_000
MOST_MINE = 500
# Off in tests (tests/conftest.py), which never reach the network.
FETCH = True
RETRY_AFTER = 3600


@dataclass(frozen=True)
class Picture:
    id: str  # 'pack:<name>', 'classic:<format>' or 'mine:<file name>'
    about: str
    moods: tuple
    width: int
    height: int
    boxes: tuple = ()

    def view(self) -> dict:
        return {'id': self.id, 'width': self.width, 'height': self.height, 'boxes': list(self.boxes)}


def size(data: bytes) -> tuple[int, int]:
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return int.from_bytes(data[6:8], 'little'), int.from_bytes(data[8:10], 'little')
    try:
        _kind, width, height = storage.sniff(data)
    except AdapterError as error:
        raise ValueError(error.message) from error
    return width, height


@cache
def pack() -> tuple:
    found = []
    for entry in json.loads((DATA / 'pack.json').read_text(encoding='utf-8'))['pictures']:
        width, height = size((DATA / 'pack' / entry['file']).read_bytes())
        found.append(Picture(f"pack:{entry['id']}", entry['about'], tuple(entry['moods']), width, height))
    return tuple(found)


@cache
def formats() -> dict:
    return json.loads((DATA / 'formats.json').read_text(encoding='utf-8'))


def folder(root: Path) -> Path:
    return root / FOLDER


def cached(root: Path, format_id: str) -> Path:
    return root / CACHE / f'{format_id}.jpg'


def classic(root: Path) -> list[Picture]:
    found = []
    for entry in formats()['formats']:
        path = cached(root, entry['id'])
        if path.is_file():
            try:
                width, height = size(path.read_bytes())
            except (OSError, ValueError):
                continue
            found.append(Picture(f"classic:{entry['id']}", entry['about'], tuple(entry['moods']), width, height))
    return found


def boxes(raw) -> tuple:
    """A sidecar's text boxes, kept only when each is a box inside the picture."""
    try:
        kept = tuple({key: round(float(box[key]), 4) for key in ('x', 'y', 'w', 'h')} for box in raw[:6])
    except (TypeError, KeyError, ValueError):
        return ()
    inside = all(0 <= box['x'] < 1 and 0 <= box['y'] < 1 and 0 < box['w'] <= 1 and 0 < box['h'] <= 1 for box in kept)
    return kept if inside else ()


def sidecar(path: Path) -> dict:
    try:
        found = json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return found if isinstance(found, dict) else {}


def own(path: Path) -> Picture | None:
    try:
        if path.stat().st_size > MOST_BYTES:
            return None
        width, height = size(path.read_bytes())
    except (OSError, ValueError, IndexError):
        return None
    extra = sidecar(path)
    moods = tuple(mood for mood in extra.get('moods') or () if isinstance(mood, str)) or ('any',)
    about = extra['about'][:200] if isinstance(extra.get('about'), str) else 'a picture from your meme templates'
    return Picture(f'mine:{path.name}', about, moods, width, height, boxes(extra.get('boxes') or []))


def mine(root: Path) -> list[Picture]:
    """The user's own templates; the folder is made the first time it is looked at, so it is there to fill."""
    place = folder(root)
    try:
        place.mkdir(parents=True, exist_ok=True)
        files = sorted(path for path in place.iterdir() if path.suffix.lower() in TYPES and path.is_file())
    except OSError:
        return []
    return [picture for path in files[:MOST_MINE] if (picture := own(path))]


def available(root: Path, classics: bool) -> list[Picture]:
    return [*pack(), *(classic(root) if classics else ()), *mine(root)]


def has_choice(root: Path, classics: bool) -> bool:
    return any('choice' in picture.moods for picture in available(root, classics))


def pick(meme: dict, seed: str, root: Path, classics: bool) -> Picture | None:
    """A picture for this meme's mood, varied by seed; a "this, not that" pair only on its own format."""
    pictures = available(root, classics)
    if meme['mood'] == 'choice':
        fits = [picture for picture in pictures if 'choice' in picture.moods]
    else:
        fits = [picture for picture in pictures if meme['mood'] in picture.moods or 'any' in picture.moods]
    return random.Random(seed + ':picture').choice(fits) if fits else None


def path_of(root: Path, picture_id: str) -> Path | None:
    """The file behind a picture id, or None: only pictures this module lists are ever served."""
    source, _, name = picture_id.partition(':')
    if source == 'pack':
        entry = next((entry for entry in json.loads((DATA / 'pack.json').read_text(encoding='utf-8'))['pictures']
                      if entry['id'] == name), None)
        return DATA / 'pack' / entry['file'] if entry else None
    if source == 'classic' and any(entry['id'] == name for entry in formats()['formats']):
        path = cached(root, name)
        return path if path.is_file() else None
    if source == 'mine' and name and Path(name).name == name and Path(name).suffix.lower() in TYPES:
        path = folder(root) / name
        return path if path.is_file() else None
    return None


def media_type(path: Path) -> str:
    return TYPES.get(path.suffix.lower(), 'application/octet-stream')


# Classic formats -----------------------------------------------------------------------------------

WARMING = threading.Lock()
FAILED: dict[str, float] = {}  # format id -> when its download last failed


def missing(root: Path) -> list[str]:
    now = time.monotonic()
    return [entry['id'] for entry in formats()['formats'] if not cached(root, entry['id']).is_file()
            and now - FAILED.get(entry['id'], -RETRY_AFTER) >= RETRY_AFTER]


def warm(root: Path) -> threading.Thread | None:
    """Download the classic formats not on this computer yet, in the background, one run at a time."""
    if not FETCH or not (wanted := missing(root)) or not WARMING.acquire(blocking=False):
        return None
    thread = threading.Thread(target=download, args=(root, wanted), name='meme-formats', daemon=True)
    thread.start()
    return thread


def download(root: Path, wanted: list[str]):
    try:
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            for format_id in wanted:
                if not fetch(client, root, format_id):
                    FAILED[format_id] = time.monotonic()
    finally:
        WARMING.release()


def fetch(client, root: Path, format_id: str) -> bool:
    """One blank format, kept only when it is a JPEG of a sensible size."""
    try:
        response = client.get(formats()['source'].format(id=format_id))
        data = response.content
        if response.status_code != 200 or len(data) > MOST_BYTES or data[:3] != b'\xff\xd8\xff':
            return False
        size(data)
        target = cached(root, format_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix('.part')
        partial.write_bytes(data)
        partial.replace(target)
        return True
    except (httpx.HTTPError, OSError, ValueError):
        return False
