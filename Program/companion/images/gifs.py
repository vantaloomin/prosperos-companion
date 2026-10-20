"""Reaction GIFs from GIPHY, only with the user's own key (Hit List #50; Vanta, 2026-10-10).

Off until a key is added in Settings > Images ("Reaction GIFs"). Only a short search word from a
fixed list, picked by the meme's mood, is ever sent to GIPHY, never the user's messages, and only
the G and PG ratings are asked for and kept. The interface shows GIPHY's credit beside each GIF,
as its terms require, and loads the GIF from GIPHY itself; nothing is stored but the link.

Searches are kept for a while, since a free key allows 100 an hour. A GIF nobody asked for is
picked only from searches already made, and a missing one is fetched in the background for next
time, so a reply never waits on GIPHY; an asked-for GIF waits a few seconds at most.
"""
import random
import re
import threading
import time
from urllib.parse import urlsplit

import httpx

from companion.errors import DomainError
from companion.images import content

SEARCH = 'https://api.giphy.com/v1/gifs/search'
CREDENTIAL = 'giphy'
RATINGS = {'g', 'pg'}
KEEP_FOR = 6 * 3600
ASKED_WAIT = 4
# Off in tests (tests/conftest.py), which never reach the network.
FETCH = True
# Search words by mood. Animals and things, not people.
TAGS = {
    'tired': ('sleepy cat', 'tired dog', 'sleepy sloth', 'yawning cat'),
    'stressed': ('stressed cat', 'panicking dog', 'cat freaking out', 'chaos cat'),
    'confused': ('confused dog', 'confused cat', 'dog head tilt', 'confused owl'),
    'smug': ('smug cat', 'cool dog sunglasses', 'smug seal'),
    'happy': ('happy dog', 'happy cat', 'dancing dog', 'happy otter'),
    'sad': ('sad dog', 'sad cat', 'rainy window cat'),
    'awkward': ('awkward penguin', 'awkward cat', 'cat fail'),
    'proud': ('proud cat', 'proud dog', 'cat high five'),
    'grumpy': ('grumpy cat', 'angry goose', 'annoyed cat'),
    'chill': ('relaxed cat', 'capybara relaxing', 'chill dog'),
    'sneaky': ('sneaky cat', 'sneaky raccoon', 'cat stealing food'),
    'regret': ('dog oops', 'cat oops', 'cat falls off table'),
    'hungry': ('hungry dog', 'cat eating', 'hamster eating'),
    'love': ('cat cuddle', 'otters holding hands', 'dog hug'),
    'suspicious': ('suspicious cat', 'side eye dog', 'suspicious owl'),
    'excited': ('excited dog', 'dog zoomies', 'excited cat'),
}
KEPT: dict[str, tuple[float, list[dict]]] = {}  # search word -> (when, GIFs found)
LOCK = threading.Lock()
# A GIF whose words name anyone young or anything adult is never shown.
NOT_SHOWN = {'minor', 'sexual', 'nudity', 'sexual_violence', 'uncertain', 'gore'}


def key(vault) -> str | None:
    try:
        return vault.get(CREDENTIAL) or None
    except DomainError:
        return None


def save_key(vault, value: str):
    if value:
        vault.put(CREDENTIAL, value)
    else:
        vault.delete(CREDENTIAL)
    with LOCK:
        KEPT.clear()


def fits(gif: dict) -> bool:
    words = content.normalize(' '.join(str(gif.get(field) or '') for field in ('title', 'slug', 'alt')))
    host = urlsplit(gif.get('url') or '').hostname or ''
    return gif.get('rating') in RATINGS and not content.matches(words) & NOT_SHOWN and \
        gif['url'].startswith('https://') and (host == 'giphy.com' or host.endswith('.giphy.com'))


def shown(item: dict) -> dict | None:
    """What a chat needs of one search result: the fixed-width rendition, its size and GIPHY's page."""
    try:
        image = item['images']['fixed_width']
        gif = {'url': image['url'], 'width': int(image['width']), 'height': int(image['height']),
               'page': item.get('url') or '', 'rating': item.get('rating'), 'title': item.get('title') or '',
               'slug': item.get('slug') or '', 'alt': item.get('alt_text') or ''}
    except (KeyError, TypeError, ValueError):
        return None
    return gif if fits(gif) else None


def search(api_key: str, tag: str, timeout: float) -> list[dict]:
    response = httpx.get(SEARCH, params={'api_key': api_key, 'q': tag, 'limit': 25, 'rating': 'pg', 'lang': 'en'},
                         timeout=timeout)
    response.raise_for_status()
    found = [gif for item in response.json().get('data') or [] if (gif := shown(item))]
    with LOCK:
        KEPT[tag] = (time.monotonic(), found)
    return found


def kept(tag: str) -> list[dict] | None:
    with LOCK:
        found = KEPT.get(tag)
    return found[1] if found and time.monotonic() - found[0] < KEEP_FOR else None


def fetch_later(api_key: str, tag: str):
    def run():
        try:
            search(api_key, tag, 15)
        except (httpx.HTTPError, ValueError):
            pass
    threading.Thread(target=run, name='gif-search', daemon=True).start()


def tag_for(mood: str, seed: str) -> str:
    return random.Random(seed + ':gif').choice(TAGS.get(mood) or TAGS['happy'])


def pick(vault, mood: str, seed: str, asked: bool = False) -> dict | None:
    """A reaction GIF for this mood, or None (no key, nothing found yet, or GIPHY not answering)."""
    api_key = key(vault) if FETCH else None
    if not api_key:
        return None
    tag = tag_for(mood, seed)
    found = kept(tag)
    if found is None and asked:
        try:
            found = search(api_key, tag, ASKED_WAIT)
        except (httpx.HTTPError, ValueError):
            found = None
    elif found is None:
        fetch_later(api_key, tag)
    if not found:
        return None
    gif = random.Random(seed + ':which').choice(found)
    return {**{field: gif[field] for field in ('url', 'width', 'height', 'page')}, 'tag': tag}


GIF_ASK = re.compile(r'\bgifs?\b', re.IGNORECASE)
