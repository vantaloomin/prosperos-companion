"""Image requests assembled from a post's committed events and the character, without a model.

The image illustrates the same account the feed, chat and recall share (F1): the prompt names
only what the events already say, plus the character's appearance description.
"""
import random
import re

from companion.characters import require_current
from companion.database import decode, one
from companion.errors import require
from companion.life import feed, home, wardrobe
from companion.life.clothing import GARMENTS
from companion.lora.appearance import current_for_images

PROMPT_VERSION = 2
DEFAULT_STYLE = 'Candid, natural-light photograph'
NEGATIVE = 'text, watermark, logo, blurry, distorted hands, extra limbs, duplicate person'


def place_name(event) -> str:
    place = decode(event['details']).get('place') or {}
    return place.get('name', '') if isinstance(place, dict) else ''


def when(event) -> dict:
    """What the wardrobe needs to dress the moment: its activity, block kind, local date and weather."""
    details = decode(event['details'])
    return {key: details.get(key) for key in ('activity', 'block_kind', 'local_date', 'weather')}


def scene(connection, post_id) -> list[dict]:
    result = []
    for link in connection.execute('SELECT event_id FROM feed_post_events WHERE post_id=? ORDER BY position',
                                   (post_id,)).fetchall():
        event = feed.current_revision(connection, link['event_id'])
        if event and event['status'] == 'committed':
            result.append({**feed.event_view(event), 'place': place_name(event), 'moment': when(event)})
    return result


# Clothing words in an appearance description; accessories (a scarf, a ring) and glasses stay.
CLOTHES = {word for word, kind in GARMENTS.items() if kind != 'accessory'} | {
    'flats', 'shoes', 'scrubs', 'pants', 'leggings', 'shorts', 'uniform', 'outfit', 'clothes', 'clothing',
    'tank', 'jumpsuit', 'romper', 'slacks', 'chinos', 'joggers', 'sweatpants', 'pumps', 'clogs', 'mules'}
WEARS = {'wears', 'wear', 'wearing', 'dressed', 'dresses'}
KEEP = {'glasses', 'spectacles', 'piercing', 'piercings', 'tattoo', 'tattoos'} | {
    word for word, kind in GARMENTS.items() if kind == 'accessory'}
CLAUSE = re.compile(r'\s*[,;]\s*|\s+(?:and|with)\s+(?=(?:a|an|her|his|their|usually|often|always|mostly)\b)')


def clothing(clause: str) -> bool:
    words = {word.rstrip('s') if word.rstrip('s') in CLOTHES else word for word in re.findall(r"[a-z'-]+", clause.lower())}
    return bool(words & CLOTHES) or bool(words & WEARS and not words & KEEP)


def without_clothes(appearance: str) -> str:
    """The appearance without what it says they usually wear, for a picture whose moment has its own
    outfit; otherwise the model draws both (one flat and one sneaker)."""
    kept = []
    for sentence in re.split(r'(?<=[.!?])\s+', appearance.strip()):
        clauses = [clause for clause in CLAUSE.split(sentence.rstrip('.!? ')) if clause and not clothing(clause)]
        if clauses:
            kept.append(', '.join(clauses))
    return '. '.join(kept)


def compose(name, appearance, events, style, setting='', dressed=False) -> str:
    """A digest is illustrated by its first event; one picture of several outings would invent a
    moment that never happened. `dressed` means `setting` says what they wear, so the appearance's
    usual clothes are left out."""
    event = events[0]
    where = f" at {event['place']}" if event['place'] and event['place'] not in event['summary'] else ''
    if dressed:
        appearance = without_clothes(appearance)
    person = f'{name}, {appearance.strip().rstrip(".")}' if appearance.strip() else name
    parts = [f"{(style or DEFAULT_STYLE).strip().rstrip('.')}. A fictional everyday moment.", f'{person}.',
             f"{event['summary'].rstrip('.')}{where}.", setting, event['caption'].strip()]
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
            'prompt': compose(definition['name'], definition.get('appearance', ''), events, image_settings['style'],
                              *setting(connection, post['timeline_id'], events[0])),
            'negative': NEGATIVE, 'style': image_settings['style'], 'aspect': image_settings['aspect'],
            'seed': seed if seed is not None else random.SystemRandom().randrange(1, 2**31),
            'appearance': definition.get('appearance', ''), 'relationship': definition.get('relationship', ''),
            'character_name': definition['name'], 'character_version_id': companion['version']['id'],
            'events': [{key: event[key] for key in ('id', 'revision', 'summary', 'caption', 'label', 'mood', 'place')}
                       for event in events],
            'marked_nsfw': bool(marked_nsfw), **current_for_images(connection)}


def setting(connection, timeline_id, event) -> tuple[str, bool]:
    """Their home where the moment is at home, and what they are wearing (companion/life/wardrobe.py),
    with whether it says what they wear."""
    wearing = wardrobe.image_hint(connection, timeline_id, event.get('moment') or {})
    parts = [home.image_hint(connection, timeline_id, event), wearing]
    return ' '.join(part for part in parts if part), bool(wearing)


def stale(connection, inputs) -> bool:
    """True when an event the request was built from has been corrected or withdrawn since (M3)."""
    for frozen in inputs['events']:
        event = feed.current_revision(connection, frozen['id'])
        if event is None or event['status'] != 'committed' or event['id'] != frozen['id']:
            return True
    return False


# How a chat photo frames the moment: the default photo, a selfie, or what they can see.
FRAMINGS = {
    'moment': '',
    'selfie': "A selfie {name} is taking right now at arm's length with a phone's front camera, face and "
              'shoulders in frame, looking into the lens.',
    'view': 'A phone photo of what {name} can see right now, first-person point of view, nobody in focus.',
}


def build_moment(connection, moment, image_settings, framing='moment') -> dict:
    """The frozen inputs of a chat photo: the companion's current slot as the simulation composes
    it, before it is an event. The moment's wording goes into `captions`, so classification covers
    it (F6), and `events` stays empty: there is no event yet to go stale. A view leaves the
    companion out of the picture, so it carries no likeness."""
    companion = require_current(connection)
    definition = companion['version']['definition']
    scene_text = {key: moment[key] for key in ('summary', 'caption', 'mood', 'place')}
    appearance = '' if framing == 'view' else definition.get('appearance', '')
    wearing = '' if framing == 'view' else wardrobe.image_hint(connection, companion['active_timeline_id'], moment)
    prompt = compose(definition['name'], appearance, [scene_text], image_settings['style'], wearing, bool(wearing))
    if FRAMINGS[framing]:
        prompt = f"{FRAMINGS[framing].format(name=definition['name'])} {prompt}"
    likeness = current_for_images(connection)
    if framing == 'view':
        likeness = {**likeness, 'lora': None}
    return {**base_inputs(companion, definition, image_settings), 'prompt': prompt, 'framing': framing,
            'captions': [moment[key] for key in ('summary', 'caption', 'label', 'mood', 'place')],
            'moment': moment, **likeness}


def build_meme(connection, meme, image_settings) -> dict:
    """The frozen inputs of a meme picture. Its captions are drawn over the picture by the interface,
    never asked of the image model, and they are classified with the rest (F6)."""
    companion = require_current(connection)
    definition = companion['version']['definition']
    if meme['subject']:
        prompt = f"Reaction-meme style photo, simple and centered: {meme['subject']}. A fictional scene."
        likeness = {**current_for_images(connection), 'lora': None}
    else:
        person = f"{definition['name']}, {definition.get('appearance', '').strip().rstrip('.')}".rstrip(', ')
        prompt = (f"Reaction-meme style photo, simple and centered: {person}, with a {meme['expression']} "
                  f"expression{meme['where']}. A fictional moment, room above and below the face.")
        likeness = current_for_images(connection)
    return {**base_inputs(companion, definition, image_settings), 'prompt': prompt, 'framing': 'meme',
            'aspect': 'square', 'captions': [meme['top'], meme['bottom'], meme['subject'] or ''],
            'meme': meme, **likeness}


def base_inputs(companion, definition, image_settings) -> dict:
    return {'prompt_version': PROMPT_VERSION, 'negative': NEGATIVE, 'style': image_settings['style'],
            'aspect': image_settings['aspect'], 'seed': random.SystemRandom().randrange(1, 2**31),
            'appearance': definition.get('appearance', ''), 'relationship': definition.get('relationship', ''),
            'character_name': definition['name'], 'character_version_id': companion['version']['id'],
            'events': [], 'marked_nsfw': False}
