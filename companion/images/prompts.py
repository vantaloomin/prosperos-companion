"""Image requests assembled from a post's committed events and the character, without a model.

The image illustrates the same account the feed, chat and recall share (F1): the prompt names
only what the events already say, plus the character's appearance description.
"""
import random

from companion.characters import require_current
from companion.database import decode, one
from companion.errors import require
from companion.life import feed

PROMPT_VERSION = 1
DEFAULT_STYLE = 'Candid, natural-light photograph'
NEGATIVE = 'text, watermark, logo, blurry, distorted hands, extra limbs, duplicate person'


def place_name(event) -> str:
    place = decode(event['details']).get('place') or {}
    return place.get('name', '') if isinstance(place, dict) else ''


def scene(connection, post_id) -> list[dict]:
    result = []
    for link in connection.execute('SELECT event_id FROM feed_post_events WHERE post_id=? ORDER BY position',
                                   (post_id,)).fetchall():
        event = feed.current_revision(connection, link['event_id'])
        if event and event['status'] == 'committed':
            result.append({**feed.event_view(event), 'place': place_name(event)})
    return result


def compose(name, appearance, events, style) -> str:
    """A digest is illustrated by its first event; one picture of several outings would invent a
    moment that never happened."""
    event = events[0]
    where = f" at {event['place']}" if event['place'] and event['place'] not in event['summary'] else ''
    person = f'{name}, {appearance.strip().rstrip(".")}' if appearance.strip() else name
    parts = [f'{style or DEFAULT_STYLE}. A fictional everyday moment.', f'{person}.',
             f"{event['summary'].rstrip('.')}{where}.", event['caption'].strip()]
    if event['mood']:
        parts.append(f"Mood: {event['mood']}.")
    return ' '.join(part for part in parts if part)


def build(connection, post_id, image_settings, marked_nsfw=False, seed=None) -> dict:
    """The frozen inputs of one request (F3, F4)."""
    post = one(connection, 'SELECT * FROM feed_posts WHERE id=?', (post_id,))
    require(post['status'] != 'removed', 'This post was removed.', 409)
    companion = require_current(connection)
    require(post['timeline_id'] == companion['active_timeline_id'], 'This post is not on the active timeline.', 409)
    events = scene(connection, post_id)
    require(events, 'This post has no committed event to illustrate yet.', 409)
    definition = companion['version']['definition']
    return {'prompt_version': PROMPT_VERSION,
            'prompt': compose(definition['name'], definition.get('appearance', ''), events, image_settings['style']),
            'negative': NEGATIVE, 'style': image_settings['style'], 'aspect': image_settings['aspect'],
            'seed': seed if seed is not None else random.SystemRandom().randrange(1, 2**31),
            'appearance': definition.get('appearance', ''), 'relationship': definition.get('relationship', ''),
            'character_name': definition['name'], 'character_version_id': companion['version']['id'],
            'events': [{key: event[key] for key in ('id', 'revision', 'summary', 'caption', 'label', 'mood', 'place')}
                       for event in events],
            'marked_nsfw': bool(marked_nsfw)}


def stale(connection, inputs) -> bool:
    """True when an event the request was built from has been corrected or withdrawn since (M3)."""
    for frozen in inputs['events']:
        event = feed.current_revision(connection, frozen['id'])
        if event is None or event['status'] != 'committed' or event['id'] != frozen['id']:
            return True
    return False
