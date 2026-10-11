"""Image requests assembled from a post's committed events and the character, without a model.

The image illustrates the same account the feed, chat and recall share (F1): the prompt names
only what the events already say, plus the character's appearance description.
"""
import random
import re

from companion.characters import require_current
from companion.clock import parse, zone
from companion.database import decode, one
from companion.errors import require
from companion.life import feed, home, traditions, wardrobe
from companion.life.clothing import GARMENTS
from companion.lora.appearance import current_for_images
from companion.world import looks

PROMPT_VERSION = 5
DEFAULT_STYLE = 'Candid, natural-light photograph'
NEGATIVE = 'text, watermark, logo, blurry, distorted hands, extra limbs, duplicate person'


def place_name(event) -> str:
    place = decode(event['details']).get('place') or {}
    return place.get('name', '') if isinstance(place, dict) else ''


def when(event) -> dict:
    """What the wardrobe and the picture line need: its activity, block kind, local date, weather and company."""
    details = decode(event['details'])
    return {key: details.get(key) for key in ('activity', 'block_kind', 'local_date', 'weather', 'with')}


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


# Krea 2 reads one descriptive paragraph (github.com/krea-ai/krea-2, docs/prompting.md): the medium
# first, each subject with what can be seen of them and what they do, then the setting, the light and
# the camera. A name, a backstory, a caption or a mood word gives the image model nothing to draw.
BACKSTORY = re.compile(r"\s+(?:in (?:college|high school|school)|as an? (?:kid|child|teen(?:ager)?)|growing up|"
                       r"since\b|(?:years|months) ago|back when|because\b|despite\b|after (?:a|an|her|his|their|the|years)\b|"
                       r"from (?:a|an|her|his|their|the|years)\b|when (?:she|he|they) (?:was|were)\b).*$", re.IGNORECASE)
IMPRESSION = re.compile(r"\b(?:looks like (?:someone|somebody|a person|the kind|the type)|the (?:kind|type|sort) of "
                        r"(?:person|woman|man|girl|guy)|seems|gives off|people (?:say|tell|think)|tends to|likes to|"
                        r"loves|hates|prefers|never|always says)\b", re.IGNORECASE)
VERBS = {'is': 'are', 'has': 'have', 'was': 'were'}
PRONOUNS = {'she': ('She', 'her'), 'he': ('He', 'his'), 'they': ('They', 'their')}
EXPRESSIONS = {
    'focused': 'a focused, concentrating expression', 'steady': 'a calm, steady expression',
    'tired': 'tired eyes and a weary half-smile', 'busy': 'a brisk, slightly harried look',
    'refreshed': 'a bright, rested look', 'satisfied': 'a quiet, satisfied smile', 'practical': 'a relaxed, matter-of-fact look',
    'content': 'a soft, contented smile', 'productive': 'a pleased, accomplished look', 'happy': 'a wide, easy smile',
    'warm': 'a warm smile', 'cheerful': 'a cheerful grin', 'excited': 'a bright, excited smile',
    'calm': 'a calm, peaceful expression', 'relaxed': 'a relaxed, easy expression', 'curious': 'a curious, absorbed look',
    'inspired': 'a lit-up, absorbed look', 'energized': 'flushed cheeks and a pleased grin', 'proud': 'a proud little smile',
    'cozy': 'a sleepy, cozy smile', 'rested': 'a rested, unhurried look', 'under the weather': 'a pale, sniffly, tired look',
}


def pronoun(appearance: str) -> str:
    """She, he or they, as the appearance itself speaks of them; 'they' when it never says."""
    words = re.findall(r"[a-z]+", appearance.lower())
    counts = {'she': sum(word in ('she', 'her', 'hers', 'woman', 'girl') for word in words),
              'he': sum(word in ('he', 'him', 'his', 'man', 'guy') for word in words)}
    best = max(counts, key=counts.get)
    return best if counts[best] and counts['she'] != counts['he'] else 'they'


def unnamed(text: str, name: str, who: str) -> str:
    """The text with the character's name (full or first) said as a pronoun: the image model cannot
    know who Kimberly is, and a name invites lettering."""
    subject, possessive = PRONOUNS[who]
    for form in sorted({name.strip(), name.strip().split(' ')[0]} - {''}, key=len, reverse=True):
        pattern = re.escape(form)
        text = re.sub(rf"(^|[.!?]\s+){pattern}'s\b", lambda m: m.group(1) + possessive.capitalize(), text)
        text = re.sub(rf"\b{pattern}'s\b", possessive, text)
        text = re.sub(rf"(^|[.!?]\s+){pattern}\b", lambda m: m.group(1) + subject, text)
        text = re.sub(rf"\b{pattern}\b", subject.lower(), text)
    if who == 'they':
        text = re.sub(r'\b(They|they) (is|has|was)\b', lambda m: f"{m.group(1)} {VERBS[m.group(2)]}", text)
    return text


def visible(appearance: str, name: str, who: str) -> str:
    """What a camera can show of them: impressions ("looks like someone who...") are dropped and
    backstory is cut off a clause ("a scar on her chin from a derby fall" keeps the scar)."""
    kept = []
    for sentence in re.split(r'(?<=[.!?])\s+', unnamed(appearance.strip(), name, who)):
        if IMPRESSION.search(sentence):
            continue
        clauses = [BACKSTORY.sub('', clause).strip() for clause in CLAUSE.split(sentence.rstrip('.!? ')) if clause]
        if clauses := [clause for clause in clauses if clause]:
            kept.append(', '.join(clauses))
    return '. '.join(f'{sentence[:1].upper()}{sentence[1:]}' for sentence in kept)


def light(hour, weather) -> str:
    """The light of the moment's hour and weather, or '' when neither is known."""
    weather = weather or {}
    if hour is None:
        parts = []
    elif 5 <= hour < 8:
        parts = ['soft early-morning light']
    elif 8 <= hour < 11:
        parts = ['bright morning daylight']
    elif 11 <= hour < 15:
        parts = ['even midday daylight']
    elif 15 <= hour < 18:
        parts = ['warm late-afternoon light']
    elif 18 <= hour < 20:
        parts = ['low golden evening light']
    else:
        parts = ['night, lit by warm lamps and streetlights']
    if weather.get('rain'):
        parts.append('a grey, rainy day with wet surfaces' if hour is None or 6 <= hour < 20 else 'rain-wet streets')
    elif isinstance(weather.get('high_f'), (int, float)) and weather['high_f'] <= 38:
        parts.append('a cold winter day')
    elif isinstance(weather.get('high_f'), (int, float)) and weather['high_f'] >= 90:
        parts.append('a hot, hazy summer day')
    return f"{', '.join(parts)[:1].upper()}{', '.join(parts)[1:]}." if parts else ''


CAMERAS = {'moment': 'Shot at eye level on a phone camera, natural colours, realistic skin texture, shallow depth of field.',
           'selfie': 'Slight wide-angle phone-camera look, natural colours, realistic skin texture.',
           'view': 'Phone-camera look, natural colours, everything in the scene in focus.'}


def camera(style: str, framing='moment') -> str:
    """Camera details for a photographic style the user left plain; a painted or drawn style keeps its own."""
    style = style.lower()
    if 'photo' not in style or any(word in style for word in ('lens', 'mm', 'depth of field', 'shot on', 'film')):
        return ''
    return CAMERAS.get(framing, CAMERAS['moment'])


def restyle(inputs: dict, own: str | None) -> dict:
    """The request with the backend's own style (Settings > Images, per backend) in place of the one it
    was built with, or back to the general style for a backend without one: the opening style line
    and the camera details that follow from it. `general_style` keeps the general one, so a retry or
    fallback on another backend starts from it. A prompt that does not open with its style (a meme)
    is left as it is."""
    general = inputs.get('general_style', inputs.get('style'))
    old = (inputs.get('style') or DEFAULT_STYLE).strip().rstrip('.')
    style = ((own or '').strip() or general or DEFAULT_STYLE).strip().rstrip('.')
    prompt = inputs['prompt']
    if style == old or not prompt.startswith((f'{old} ', f'{old},')):
        return inputs
    framing = inputs.get('framing') or 'moment'
    before, after = camera(old, framing), camera(style, framing)
    if before and prompt.endswith(before):
        prompt = prompt[:-len(before)].rstrip()
    prompt = f"{style}{prompt[len(old):]}{' ' + after if after else ''}"
    return {**inputs, 'prompt': prompt, 'style': style, 'general_style': general}


def compose(name, appearance, events, style, setting='', dressed=False, framing='moment', who=None, sheet='') -> str:
    """A digest is illustrated by its first event; one picture of several outings would invent a
    moment that never happened. `dressed` means `setting` says what they wear, so the appearance's
    usual clothes are left out. The event may carry the local `hour` and `weather` for the light;
    its caption is never drawn (the feed shows it under the picture). A chat photo's `framing` opens
    the paragraph in place of the plain moment; `who` overrides the pronoun read from the appearance.
    `sheet` is their looks in words (`sheet_for`), ahead of the free-text appearance."""
    event = events[0]
    who = who or pronoun(appearance)
    subject, possessive = PRONOUNS[who]
    where = f" at {event['place']}" if event['place'] and event['place'] not in event['summary'] else ''
    if dressed:
        appearance = without_clothes(appearance)
    look = visible(appearance, name, who)
    style = (style or DEFAULT_STYLE).strip().rstrip('.')
    setting = re.sub(r'(^|\.\s+)Wearing\b', lambda m: f"{m.group(1)}{subject} {'are' if who == 'they' else 'is'} wearing",
                     setting)
    action = doing(event, subject, possessive, who) or unnamed(f"{event['summary'].strip().rstrip('.')}{where}.", name, who)
    expression = EXPRESSIONS.get((event.get('mood') or '').strip().lower()) or \
        (f"a {event['mood'].strip().lower()} expression" if event.get('mood') else '')
    opening = FRAMINGS[framing].format(subject=subject.lower(), possessive=possessive) if FRAMINGS[framing] else \
        ''
    parts = [f'{style}, {opening}.' if opening else f'{style} of a fictional everyday moment, {MOMENT.format(possessive=possessive)}.',
             sheet, f'{look}.' if look else '', setting, action,
             f'{possessive.capitalize()} face shows {expression}.' if expression and framing != 'view' else '',
             light(event.get('hour'), event.get('weather')), camera(style, framing)]
    return ' '.join(part for part in parts if part)


# What each activity of the life sim (companion/life/composer.py and the circle's gatherings) looks
# like in a picture, in the present tense, with {possessive} for her/his/their. The place, when the
# event has one, follows as " at <place>"; company as ", with a friend".
PICTURES = {
    'steady-shift': 'at work, absorbed in the task in front of {possessive}',
    'busy-shift': 'at work in the middle of a rush, moving quickly',
    'lunch-out': 'on a lunch break, sitting at a small table with a plate of food',
    'library': 'studying at a library table, notes and an open laptop spread out',
    'study-cafe': 'studying at a café table with flashcards, a laptop and one cup of coffee',
    'groceries': 'pushing a shopping cart down a grocery aisle, picking out food',
    'chores': 'at home folding a pile of fresh laundry',
    'browse': 'browsing shelves in a shop, holding one item up to look at it',
    'dinner': 'sitting at a restaurant table over dinner, mid-conversation',
    'drinks': 'standing at a bar with a drink in hand, laughing',
    'show': 'in a crowd at a live show, stage lights in the background',
    'walk': 'walking outdoors along a path, hands in {possessive} pockets',
    'coffee': 'sitting at a café table with a coffee and an open book',
    'museum': 'standing in a gallery, looking closely at an exhibit',
    'market': 'browsing the stalls of a busy market',
    'workout': 'mid-workout, slightly out of breath',
    'home-cooking': 'cooking at the stove at home, stirring a pan, ingredients on the counter',
    'reading': 'curled up at home reading a book under a blanket',
    'nap': 'lying on a sofa at home under a blanket, just waking from a nap',
    'slow': 'lounging on the sofa at home with a mug',
    'sick-day': 'on the sofa at home with a cold, wrapped in a blanket, tea and tissues nearby',
    'festival': 'outdoors in a festival crowd, stalls and banners around',
    'birthday': 'at a table celebrating a birthday, a cake with candles in front of them',
    'own-birthday': 'celebrating {possessive} own birthday at a table, a cake with candles in front of {possessive}',
    'gathering': 'gathered around a table with family and friends',
    'tradition': 'at a holiday table with family, the dishes passed around',
}
CALLS = ('called', 'phone')


def doing(event, subject, possessive, who) -> str:
    """The picture line for the event's activity, or '' when there is none or the event was
    corrected (a correction's own words win over what the activity usually looks like)."""
    line = PICTURES.get(event.get('activity') or '')
    if not line or (event.get('revision') or 1) > 1:
        return ''
    if event.get('activity') == 'birthday' and any(word in event['summary'].lower() for word in CALLS):
        line, place = 'at home on the phone, smiling', ''
    else:
        place = f" at {event['place']}" if event.get('place') and ' at home' not in line else ''
    company = ', with a friend' if event.get('with') and event['activity'] not in ('birthday', 'gathering', 'tradition') else ''
    verb = 'are' if who == 'they' else 'is'
    return f"{subject} {verb} {line.format(possessive=possessive)}{place}{company}."


def sheet_for(companion, definition) -> tuple[str, str]:
    """Their looks sheet (companion/world/looks.py) in words, and the pronoun to draw them with: the
    appearance's own, else the one the rest of their description uses."""
    who = pronoun(definition.get('appearance', ''))
    if who == 'they':
        who = {'she/her': 'she', 'he/him': 'he'}.get(looks.pronouns_of(definition), 'they')
    return looks.picture(looks.for_companion(companion['id'], definition), who), who


def local_hour(stamp_text, timezone) -> int | None:
    if not stamp_text:
        return None
    try:
        return parse(stamp_text).astimezone(zone(timezone)).hour
    except (ValueError, TypeError):
        return None


def build(connection, post_id, image_settings, marked_nsfw=False, seed=None) -> dict:
    """The frozen inputs of one request (F3, F4)."""
    post = one(connection, 'SELECT * FROM feed_posts WHERE id=?', (post_id,))
    require(post['status'] != 'removed', 'This post was removed.', 409)
    companion = require_current(connection)
    require(post['timeline_id'] == companion['active_timeline_id'], 'This post is not on the active timeline.', 409)
    events = scene(connection, post_id)
    require(events, 'This post has no committed event to illustrate yet.', 409)
    definition = companion['version']['definition']
    first = {**events[0], 'hour': local_hour(events[0]['starts_at'], companion['version']['timezone']),
             'weather': events[0]['moment'].get('weather'), 'activity': events[0]['moment'].get('activity'),
             'with': events[0]['moment'].get('with')}
    sheet, who = sheet_for(companion, definition)
    return {'prompt_version': PROMPT_VERSION,
            'prompt': compose(definition['name'], definition.get('appearance', ''), [first], image_settings['style'],
                              *setting(connection, post['timeline_id'], events[0]), who=who, sheet=sheet),
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
    parts = [home.image_hint(connection, timeline_id, event), traditions.image_hint(connection, timeline_id, event), wearing]
    return ' '.join(part for part in parts if part), bool(wearing)


def stale(connection, inputs) -> bool:
    """True when an event the request was built from has been corrected or withdrawn since (M3)."""
    for frozen in inputs['events']:
        event = feed.current_revision(connection, frozen['id'])
        if event is None or event['status'] != 'committed' or event['id'] != frozen['id']:
            return True
    return False


# How a chat photo frames the moment: the default photo, a selfie, or what they can see. A plain
# moment says where the face is: left to itself, Krea 2 crops a candid shot at the chin or the
# shoulders as often as not, and a picture of someone with no face in it is no picture of them.
MOMENT = 'a medium shot with {possessive} whole head and face in the frame'
FRAMINGS = {
    'moment': '',
    'selfie': "a fictional selfie taken at arm's length with a phone's front camera, face and shoulders in "
              'frame, looking into the lens',
    'view': 'a fictional first-person phone photo of what {subject} can see right now, nobody in focus',
}


def build_moment(connection, moment, image_settings, framing='moment') -> dict:
    """The frozen inputs of a chat photo: the companion's current slot as the simulation composes
    it, before it is an event. The moment's wording goes into `captions`, so classification covers
    it (F6), and `events` stays empty: there is no event yet to go stale. A view leaves the
    companion out of the picture, so it carries no likeness."""
    companion = require_current(connection)
    definition = companion['version']['definition']
    scene_text = {key: moment.get(key) for key in ('summary', 'caption', 'mood', 'place', 'hour', 'weather',
                                                    'activity', 'with')}
    appearance = '' if framing == 'view' else definition.get('appearance', '')
    wearing = '' if framing == 'view' else wardrobe.image_hint(connection, companion['active_timeline_id'], moment)
    sheet, who = sheet_for(companion, definition)
    prompt = compose(definition['name'], appearance, [scene_text], image_settings['style'], wearing, bool(wearing),
                     framing, who, '' if framing == 'view' else sheet)
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
        appearance = definition.get('appearance', '')
        sheet, who = sheet_for(companion, definition)
        look = visible(appearance, definition['name'], who)
        prompt = (f"Reaction-meme style photo, simple and centered, of a fictional person with a {meme['expression']} "
                  f"expression{meme['where']}, room above and below the face. {sheet} {look}.").rstrip(' .') + '.'
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
