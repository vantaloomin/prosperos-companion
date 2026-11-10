"""Image requests assembled from a post's committed events and the character, without a model.

The image illustrates the same account the feed, chat and recall share (F1): the prompt names
only what the events already say, plus the character's appearance description.
"""
import random
import re
from functools import wraps

from companion import prompt_library
from companion.characters import require_current
from companion.clock import parse, zone
from companion.database import decode, one
from companion.errors import require
from companion.images import places
from companion.life import (
    composer,
    families,
    feed,
    grooming,
    hobbies,
    home,
    pets,
    pronouns,
    traditions,
    upkeep,
    wardrobe,
)
from companion.life.clothing import GARMENTS
from companion.lora.appearance import current_for_images
from companion.world import decades, looks, newcomers, ships

PROMPT_VERSION = 10
DEFAULT_STYLE = 'Candid, natural-light photograph'
NEGATIVE = 'text, watermark, logo, blurry, distorted hands, extra limbs, duplicate person'


def negative() -> str:
    """The negative prompt in use: the user's wording (Settings > Advanced > Prompts > Pictures), else `NEGATIVE`."""
    return prompt_library.line('image-negative')


def own_words(builder):
    """Runs a request builder with the user's wording of the picture pieces (companion/prompt_library.py, Pictures);
    the constants here are the defaults."""
    @wraps(builder)
    def run(connection, *args, **kwargs):
        with prompt_library.reading(connection):
            return builder(connection, *args, **kwargs)
    return run


def place_name(event) -> str:
    place = decode(event['details']).get('place') or {}
    return place.get('name', '') if isinstance(place, dict) else ''


def place_id(event) -> str | None:
    place = decode(event['details']).get('place') or {}
    return place.get('id') if isinstance(place, dict) else None


def when(event) -> dict:
    """What the wardrobe and the picture line need: its activity, block kind, local date, weather and company."""
    details = decode(event['details'])
    return {key: details.get(key) for key in ('activity', 'block_kind', 'local_date', 'weather', 'with', 'pet_photo',
                                                 'hobby', 'outing')}


def scene(connection, post_id) -> list[dict]:
    result = []
    for link in connection.execute('SELECT event_id FROM feed_post_events WHERE post_id=? ORDER BY position',
                                   (post_id,)).fetchall():
        event = feed.current_revision(connection, link['event_id'])
        if event and event['status'] == 'committed':
            result.append({**feed.event_view(event), 'place': place_name(event), 'place_id': place_id(event),
                           'moment': when(event)})
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
# "They", an optional adverb, then a verb: "Mira always wears" said as "They always wears" needs "wear".
ADVERBS = ('always', 'usually', 'often', 'never', 'mostly', 'still', 'also', 'sometimes', 'rarely', 'typically',
           'normally')
THEY_VERB = re.compile(rf"\b(They|they) ((?:{'|'.join(ADVERBS)}) )?([a-z]+s)\b")
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
        text = THEY_VERB.sub(lambda m: f"{m.group(1)} {m.group(2) or ''}{plural_verb(m.group(3))}", text)
    return text


def plural_verb(verb: str) -> str:
    """The verb as "they" says it: "is" -> "are", "wears" -> "wear", "carries" -> "carry", "dresses" -> "dress"."""
    if verb in VERBS or verb in ADVERBS:
        return VERBS.get(verb, verb)
    if verb.endswith('ies') and len(verb) > 4:
        return verb[:-3] + 'y'
    if verb.endswith(('sses', 'shes', 'ches', 'xes', 'zes', 'oes')):
        return verb[:-2]
    return verb[:-1] if verb.endswith('s') and not verb.endswith(('ss', 'us')) else verb


# The age the looks sheet opens with ("A tall man in his mid twenties"), left out when the user's own In photos line
# says one: two ages read as two people.
SHEET_AGE = re.compile(r' in (?:his|her|their) (?:early|mid|late) [a-z]+ies\b')


# A sheet that leaves the person to the In photos line ("He has tan skin ...", looks.picture) follows it.
HAS = re.compile(r'(?:She|He) has |They have ')


def one_age(sheet: str, look: str) -> str:
    return SHEET_AGE.sub('', sheet, count=1) if sheet and look and looks.LOOKS_AGE.search(look) else sheet


def visible(appearance: str, name: str, who: str) -> str:
    """What a camera can show of them: impressions ("looks like someone who...") are dropped and
    backstory is cut off a clause ("a scar on her chin from a derby fall" keeps the mark), and old injuries are said
    as what they look like now (looks.seen)."""
    kept = []
    for sentence in re.split(r'(?<=[.!?])\s+', looks.seen(unnamed(appearance.strip(), name, who))):
        if IMPRESSION.search(sentence):
            continue
        clauses = [BACKSTORY.sub('', clause).strip() for clause in CLAUSE.split(sentence.rstrip('.!? ')) if clause]
        if clauses := [clause for clause in clauses if clause]:
            kept.append(', '.join(clauses))
    return '. '.join(f'{sentence[:1].upper()}{sentence[1:]}' for sentence in kept)


# Snow, fog and storms (companion/world/skies.py) in the picture's light, by day and by night.
SKY_LIGHT = {'snow': ('a snowy day, falling snow and white rooftops', 'snow falling through the streetlights'),
             'storm': ('a dark, stormy sky and driving rain', 'a stormy night, rain lashing the streets'),
             'fog': ('thick fog, soft muted light', 'fog haloing the streetlights'),
             'rain': ('a grey, rainy day with wet surfaces', 'rain-wet streets')}


def light(hour, weather, indoor=None) -> str:
    """The light of the moment's hour and weather, or '' when neither is known. Indoors (`indoor`, from the place's
    city entry, companion/images/places.py) a night is lamplight with no streetlights, and the weather stays outside."""
    weather = {} if indoor else weather or {}
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
        parts = ['night, lit by warm lamps' if indoor else 'night, lit by warm lamps and streetlights']
    parts += weather_light(hour, weather)
    return f"{', '.join(parts)[:1].upper()}{', '.join(parts)[1:]}." if parts else ''


def weather_light(hour, weather: dict) -> list[str]:
    """The day's weather in the picture: its sky (snow, storms, fog, rain), else a hard cold or heat."""
    daytime = hour is None or 6 <= hour < 20
    high = weather.get('high_f')
    if weather.get('sky') in SKY_LIGHT:
        return [SKY_LIGHT[weather['sky']][0 if daytime else 1]]
    if weather.get('rain'):
        return [SKY_LIGHT['rain'][0 if daytime else 1]]
    if isinstance(high, (int, float)) and high <= 38:
        return ['a cold winter day']
    if isinstance(high, (int, float)) and high >= 90:
        return ['a hot, hazy summer day']
    return []


# Aboard a ship or station (companion/world/ships.py) the light is the ship's own, on its day and night cycle.
SHIP_LIGHT = ((5, "corridor lights brightening for ship's morning"), (8, "bright, even ship's-morning light from the "
              'ceiling panels'), (11, 'even white light from the overhead panels'), (15, 'warm late-shift light from '
              'the overhead panels'), (18, "corridor lights warming toward ship's evening"), (20, "corridor lights "
              "dimmed for ship's night, a soft glow from the wall panels"))


def ship_light(hour) -> str:
    """The ship's light at the moment's hour, or '' when the hour is not known; there is no weather aboard."""
    if hour is None:
        return ''
    found = next((text for start, text in reversed(SHIP_LIGHT) if hour >= start), SHIP_LIGHT[-1][1])
    return f'{found[:1].upper()}{found[1:]}.'


# Outdoor wording said as what it is aboard, in visible words: whole phrases first.
ABOARD_WORDS = (
    (r'walking outdoors along a path', "walking along a wide ship's corridor"),
    (r'outdoors in a festival crowd', 'in a festival crowd in a big indoor hall'),
    (r'down a quiet street', 'along a quiet corridor'),
    (r'on a city street', "on a busy ship's concourse"),
    (r'along a park path', 'along the running track of the park deck'),
    (r'(?:a )?clear night sky full of stars', 'a wide viewport full of stars'),
    (r'a sky full of stars', 'a wide viewport full of stars'),
    (r'in the sunshine', 'under the grow lights'),
    (r'on a sunny windowsill', 'on a bright ledge by a viewport'),
    (r'among trees in a quiet park', 'among the trees of the arboretum deck'),
    (r'\boutdoors\b', 'in a big indoor hall'),
    (r'\bstreetlights\b', 'corridor lights'),
)


def aboard_words(text: str) -> str:
    for pattern, said in ABOARD_WORDS:
        text = re.sub(pattern, said, text, flags=re.IGNORECASE)
    return text


CAMERAS = {'moment': 'Shot at eye level on a phone camera, natural colours, realistic skin texture, shallow depth of field.',
           'selfie': 'Slight wide-angle phone-camera look, natural colours, realistic skin texture.',
           'view': 'Phone-camera look, natural colours, everything in the scene in focus.',
           'scene': 'Shot at eye level from a few steps away, natural colours, realistic skin texture, the place in sharp '
                    'focus around them.'}
CAMERAS['scene_both'] = CAMERAS['scene']
CAMERAS['things'] = 'Phone-camera look, natural colours, sharp focus on the things themselves.'
CAMERAS['photo'] = 'Phone-camera look, natural colours, everything in the scene in focus.'


# A style that is not a photograph, though it may say the word ("non-photorealistic", "photo-bashed concept art").
NOT_PHOTO = re.compile(r'non-?photo|\b(?:illustrat\w*|paint\w*|drawn|drawing|sketch\w*|anime|manga|cartoon\w*|comic|'
                       r'cel[- ]shaded|watercolou?r|oil on|ink|digital art|concept art|splash art|render\w*|3d|pixel art|'
                       r'stylized|stylised)\b', re.IGNORECASE)


def camera(style: str, framing='moment', period: dict | None = None) -> str:
    """Camera details for a photographic style the user left plain; a painted or drawn style keeps its own. In a past
    year (`period`, decades.picture) the camera is one of its decade: a film snapshot in the 1990s."""
    style = style.lower()
    if 'photo' not in style or NOT_PHOTO.search(style) or \
            any(word in style for word in ('lens', 'mm', 'depth of field', 'shot on', 'film')):
        return ''
    cameras = prompt_library.words('image-cameras')
    cameras['scene_both'] = cameras['scene']
    return ((period or {}).get('cameras') or {}).get(framing) or cameras.get(framing, cameras['moment'])


def restyle(inputs: dict, own: str | None) -> dict:
    """The request with the backend's own style (Settings > Pictures, per backend) in place of the one it
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
    before, after = camera(old, framing, inputs.get('period')), camera(style, framing, inputs.get('period'))
    if before and prompt.endswith(before):
        prompt = prompt[:-len(before)].rstrip()
    prompt = f"{style}{prompt[len(old):]}{' ' + after if after else ''}"
    return {**inputs, 'prompt': prompt, 'style': style, 'general_style': general}


def compose(name, appearance, events, style, setting='', dressed=False, framing='moment', who=None, sheet='',
            look=None, aboard=False, period=None) -> str:
    """A digest is illustrated by its first event; one picture of several outings would invent a
    moment that never happened. `dressed` means `setting` says what they wear, so the appearance's
    usual clothes are left out. The event may carry the local `hour` and `weather` for the light;
    its caption is never drawn (the feed shows it under the picture). A chat photo's `framing` opens
    the paragraph in place of the plain moment; `who` overrides the pronoun read from the appearance.
    `sheet` is their looks in words (`sheet_for`), ahead of the free-text appearance; `look` is the In photos
    line (`in_photos`), which stands in for the appearance when given. `aboard` (a ship or station) gives the ship's
    light and says outdoor scenes as indoor ones. `period` (decades.picture) says the year of a world that runs in a
    past one, with a camera and framing of its decade."""
    event = events[0]
    who = who or pronoun(appearance)
    subject, possessive = PRONOUNS[who]
    where = f" at {event['place']}" if event['place'] and event['place'] not in event['summary'] else ''
    if look is None:
        look = visible(without_clothes(appearance) if dressed else appearance, name, who)
    sheet = one_age(sheet, look)
    style = (style or DEFAULT_STYLE).strip().rstrip('.')
    setting = re.sub(r'(^|\.\s+)Wearing\b', lambda m: f"{m.group(1)}{subject} {'are' if who == 'they' else 'is'} wearing",
                     setting)
    action = doing(event, subject, possessive, who) or unnamed(f"{told(event['summary'], who).strip().rstrip('.')}{where}.",
                                                               name, who)
    expression = prompt_library.words('image-moods').get((event.get('mood') or '').strip().lower()) or \
        (f"a {event['mood'].strip().lower()} expression" if event.get('mood') else '')
    openings = prompt_library.words('image-openings')
    framings = openings | {'moment': ''} | ((period or {}).get('framings') or {})
    if framing == 'scene' and event.get('user'):
        framing = 'scene_both'  # The user is drawn beside them (companion/persona_pictures.py), not as the eyes.
    opening = framings[framing].format(subject=subject.lower(), possessive=possessive, object=OBJECT[who]) \
        if framings[framing] else ''
    plain = openings['moment'].format(possessive=possessive)
    parts = [f'{style}, {opening}.' if opening else f"{style} of a fictional everyday moment{', ' + plain if plain else ''}.",
             *((f'{look}.', sheet) if look and HAS.match(sheet) else (sheet, f'{look}.' if look else '')), setting,
             WITH_YOU.sub('', action) if event.get('user') else action,
             alone(event, action, subject, who, framing),
             beside(event, subject, who), event.get('place_look') or '',
             f'{possessive.capitalize()} face shows {expression}.' if expression and framing != 'view' else '',
             ship_light(event.get('hour')) if aboard else light(event.get('hour'), event.get('weather'), event.get('indoor')),
             (period or {}).get('scene') or '', camera(style, framing, period)]
    if aboard:
        parts[3:5] = [aboard_words(part) for part in parts[3:5]]
    return looks.seen(' '.join(part for part in parts if part))


# Moments with other people in them, where "the only person in the picture" would be wrong.
CROWDED = {'busy-shift', 'dinner', 'drinks', 'show', 'market', 'dinner-in', 'festival', 'birthday', 'own-birthday',
           'gathering', 'tradition', 'wedding', 'big-day', 'own-wedding-day'}
COMPANY = re.compile(r'\b(?:with|together|friends?|family|date|partner|everyone|crowd|guests|kids?|children)\b',
                     re.IGNORECASE)


def alone(event, action, subject, who, framing) -> str:
    """Says they are the only one in a moment of their own, so the picture shows them once (adapters/comfyui.py
    turns it into a tag-model's "solo"); nothing for a view or company. In a crowded activity (a rush at work, a show)
    there are other people, but never a second of them: told nothing, Krea drew the same face again behind them."""
    if framing in ('view', 'photo') or event.get('with') or event.get('user') or COMPANY.search(action or ''):
        return ''
    if event.get('activity') in CROWDED:
        return f"{subject} {'appear' if who == 'they' else 'appears'} only once in the picture."
    return f"{subject} {'are' if who == 'they' else 'is'} the only person in the picture."


def beside(event, subject, who) -> str:
    """The user beside them, in a moment they share (companion/persona_pictures.py): who the second person in the
    picture is, so it shows two people and never draws the companion twice."""
    if not event.get('user'):
        return ''
    verb = 'are' if who == 'they' else 'is'
    return (f"Beside {OBJECT.get(who, 'them')} is one other person, {event['user']}. {subject} {verb} the main "
            'subject; there are exactly two people in the picture.')

# "with you" in a moment's own words: the picture says who "you" are (`beside`).
WITH_YOU = re.compile(r',? with you\b', re.IGNORECASE)


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
    # Time at a parent's they care for (companion/life/health_turns.py).
    'care-dinner': "cooking at the stove in a parent's homey kitchen, filling containers to leave in the fridge",
    'care-chores': "in a parent's tidy living room, folding laundry and sorting a weekly pill organizer",
    'care-company': "sitting on a parent's old sofa with a cup of tea, family photos on the wall behind",
    'care-errands': 'carrying a bag of groceries and a pharmacy bag down a quiet street',
    'dinner-in': 'at a dinner table set for two at home, a home-cooked meal on the plates, candles lit',
    'reading': 'curled up at home reading a book under a blanket',
    'nap': 'lying on a sofa at home under a blanket, just waking from a nap',
    'slow': 'lounging on the sofa at home with a mug',
    'sick-day': 'on the sofa at home with a cold, wrapped in a blanket, tea and tissues nearby',
    'festival': 'outdoors in a festival crowd, stalls and banners around',
    'birthday': 'at a table celebrating a birthday, a cake with candles in front of them',
    'own-birthday': 'celebrating {possessive} own birthday at a table, a cake with candles in front of {possessive}',
    'gathering': 'gathered around a table with family and friends',
    'tradition': 'at a holiday table with family, the dishes passed around',
    # A visit for their looks (companion/life/grooming.py): the new look is in the sheet that opens the picture.
    'salon': 'just out of the salon, showing off a fresh new look',
    'hobby': 'absorbed in a favorite pastime',
    'nail-salon': 'holding up freshly done nails to show them off',
    # Their wedding with the user (companion/life/wedding.py): what they wear is the moment's own.
    'wedding': 'smiling among the guests on {possessive} wedding day',
    # A big day in their circle (companion/life/big_days.py) with the user: dressed up, a guest among guests.
    'big-day': 'dressed up and smiling among the guests at a celebration',
    # Their own wedding to their partner, with the user standing up at it (big_days.PICTURED).
    'own-wedding-day': 'smiling in wedding clothes at {possessive} own wedding',
}
CALLS = ('called', 'phone')


def picture_of(event) -> str | None:
    """The activity's picture line; a pastime's own (companion/life/hobbies.py), with visible wording only."""
    if event.get('activity') == 'hobby':
        hobby = event.get('hobby') or {}
        if hobby.get('name') and hobby.get('picture') == f"absorbed in {hobby['name']} at home":
            # A pastime added by hand used to be pictured at home whatever it was; it follows its own words now.
            return hobbies.custom(hobby['name'])['picture']
        return hobby.get('picture') or prompt_library.words('image-activities')['hobby']
    return prompt_library.words('image-activities').get(event.get('activity') or '') or None


def told(summary: str, who: str) -> str:
    """An event's summary with the pictured person's own pronouns in its stored phrases, as the chat and the feed read
    it (companion/life/composer.said): "Rosa had their nails done" is "Rosa had her nails done" for a "she"."""
    return composer.said(summary, {}, pronouns.FORMS.get({'she': 'she/her', 'he': 'he/him'}.get(who, ''))) or summary


def doing(event, subject, possessive, who) -> str:
    """The picture line for the event's activity, or '' when there is none or the event was
    corrected (a correction's own words win over what the activity usually looks like)."""
    line = picture_of(event)
    if not line or (event.get('revision') or 1) > 1:
        return ''
    if event.get('activity') == 'birthday' and any(word in event['summary'].lower() for word in CALLS):
        line, place = 'at home on the phone, smiling', ''
    else:
        place = f" at {event['place']}" if event.get('place') and ' at home' not in line else ''
    company = ', with a friend' if event.get('with') and event['activity'] not in ('birthday', 'gathering', 'tradition') else ''
    verb = 'are' if who == 'they' else 'is'
    return f"{subject} {verb} {line.format(possessive=possessive)}{place}{company}."


def drawn_as(definition) -> str:
    """The pronoun to draw them with: the appearance's own, else the one the rest of their description uses."""
    who = pronoun(definition.get('appearance', ''))
    if who == 'they':
        who = {'she/her': 'she', 'he/him': 'he'}.get(looks.pronouns_of(definition), 'they')
    return who


def sheet_for(companion, definition, connection=None, day=None, bold_only=False) -> tuple[str, str]:
    """Their looks sheet (companion/world/looks.py) in words, and the pronoun to draw them with. With a connection it
    is their looks on that local day (companion/life/grooming.py: haircuts, nails, a tan, bold changes), the latest
    day of their life without one; `bold_only` keeps to the bold changes (the Codex reference sheet)."""
    who = drawn_as(definition)
    said = in_photos(definition, who)  # What follows the sheet in every prompt: the sheet leaves out what it says.
    return looks.picture(grooming.sheet(connection, companion['id'], definition, day, bold_only), who, said), who


def in_photos(definition, who=None, dressed=False) -> str:
    """The "In photos" line: what pictures say about them besides the looks sheet. The user's own line on the
    character form is used as written, with only their name said as a pronoun (a signature detail like cat hair on
    a dark sweater is theirs to keep). Left empty, it is the appearance with impressions and backstory filtered out
    (`visible`), and its usual clothes give way to a moment's outfit."""
    who = who or drawn_as(definition)
    own = (definition.get('in_photos') or '').strip()
    if own:
        # "Sett, tall muscular man..." names who the line is about; the picture already opens with them.
        for form in sorted({definition['name'].strip(), definition['name'].strip().split(' ')[0]} - {''}, key=len,
                           reverse=True):
            own = re.sub(rf'^{re.escape(form)}\s*[,:;–—-]\s*', '', own)
        own = unnamed(own, definition['name'], who).rstrip('.')
        own = featureless(sceneless(own), definition)
        return f'{own[:1].upper()}{own[1:]}'
    appearance = definition.get('appearance', '')
    return featureless(visible(without_clothes(appearance) if dressed else appearance, definition['name'], who),
                       definition)


def featureless(line: str, definition) -> str:
    """The line without the clauses about a feature the user set on the looks form, which the sheet says: Sett's
    form says "vastayan ears on top of his head, covered in pink fur", his In photos line "pointed pink furry ears".
    Said twice, the ears were in the prompt twice; said only as "pointed ears", they came back elf ears (A/B
    2026-11-03), so the form's own words, the more exact ones, are the ones kept."""
    parts = looks.parts_of(looks.written(definition).get('feature') or '')
    if not parts or not line:
        return line
    kept = []
    for sentence in re.split(r'(?<=[.!?])\s+', line.strip()):
        clauses = [clause for clause in CLAUSE.split(sentence.rstrip('.!? ')) if clause and
                   not looks.parts_of(clause) & parts]
        if clauses:
            kept.append(', '.join(clauses))
    return '. '.join(f'{sentence[:1].upper()}{sentence[1:]}' for sentence in kept)


# A clause of an In photos line that sets a scene ("Ionian fighting pit with hanging lamps") rather than describing them.
SCENE = re.compile(r"\b(?:pit|arena|room|hall|street|alley|tavern|bar|pub|inn|kitchen|bedroom|office|forest|woods|beach|"
                   r"city|town|village|temple|dojo|gym|studio|market|garden|park|background|lamps?|lanterns?|interior|"
                   r"indoors|outdoors|landscape|skyline|scenery|backdrop)\b", re.IGNORECASE)


def sceneless(line: str) -> str:
    """The user's In photos line without the scene it sets: a line written for one portrait ("fighting pit with hanging
    lamps") next to the moment's own place made the image model draw them twice."""
    kept = []
    for sentence in re.split(r'(?<=[.!?])\s+', line.strip()):
        clauses = [clause for clause in CLAUSE.split(sentence.rstrip('.!? ')) if clause and not SCENE.search(clause)]
        if clauses:
            kept.append(', '.join(clauses))
    return '. '.join(kept)


def own_outfit(definition) -> bool:
    """Whether the user's own In photos line says what they wear ("open fur-collared coat"). It is theirs to keep, so
    the moment's outfit gives way to it rather than the picture showing two outfits, and so two people."""
    own = (definition.get('in_photos') or '').strip()
    return any(clothing(clause) for clause in CLAUSE.split(own) if clause.strip())


def local_hour(stamp_text, timezone) -> int | None:
    if not stamp_text:
        return None
    try:
        return parse(stamp_text).astimezone(zone(timezone)).hour
    except (ValueError, TypeError):
        return None


@own_words
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
             'with': events[0]['moment'].get('with'), 'hobby': events[0]['moment'].get('hobby')}
    first.update(places.scene(connection, companion, first))
    sheet, who = sheet_for(companion, definition, connection, (events[0].get('moment') or {}).get('local_date'))
    likeness = current_for_images(connection)
    prompt, period = pet_prompt(connection, post['timeline_id'], events, image_settings), period_of(connection, definition)
    things = not prompt and len(events) == 1 and errand(events[0])
    if things:
        prompt = errand_prompt(definition, first, image_settings['style'], who, ships.aboard(connection, definition),
                               period)
    shown = '' if prompt or not shared(connection, companion, first) else user_shown(connection)
    if shown:
        first['user'] = shown
    if prompt:
        # A photo of their pet alone (companion/life/pets.py) or an errand's things: nobody in it, so no likeness.
        likeness = {**likeness, 'lora': None}
    return {'prompt_version': PROMPT_VERSION,
            'prompt': prompt or feed_prompt(definition, first, image_settings,
                                            setting(connection, post['timeline_id'], events[0],
                                                    not own_outfit(definition)), who, sheet,
                                            ships.aboard(connection, definition), period),
            'negative': negative(), 'style': image_settings['style'], 'aspect': image_settings['aspect'],
            'seed': seed if seed is not None else random.SystemRandom().randrange(1, 2**31),
            'appearance': definition.get('appearance', ''), 'relationship': definition.get('relationship', ''),
            'character_name': definition['name'], 'character_version_id': companion['version']['id'],
            'events': [{key: event[key] for key in ('id', 'revision', 'summary', 'caption', 'label', 'mood', 'place')}
                       for event in events],
            'marked_nsfw': bool(marked_nsfw), 'pictured': not prompt, 'period': period, 'with_user': bool(shown),
            **({'framing': 'things'} if things else {}),
            'name_in_pictures': bool(definition.get('name_in_pictures')), **likeness,
            **children(connection, post['timeline_id'], [event[key] for event in events
                                                          for key in ('summary', 'caption', 'label', 'place')],
                       [(event['moment'].get('outing') or {}).get('id') for event in events])}


def errand(event) -> bool:
    """Whether the moment is an errand or a piece of paperwork (companion/life/admin.py, source 'admin'): resoled boots
    picked up, a bill paid. Its picture is of the things it was about, not a portrait of them."""
    return ((event.get('moment') or {}).get('admin') or {}).get('source') == 'admin'


def errand_prompt(definition, event, style, who, aboard=False, period=None) -> str:
    """The things an errand was about, up close, with nobody in the picture: a portrait of Sett smiling at the camera
    for "picked up the resoled boots" said "the only person in the picture" and how his face looked, and showed no
    boots. Their looks, the expression and the one-person line belong to pictures of them."""
    subject, possessive = PRONOUNS[who]
    done = unnamed(told(event['summary'], who).strip(), definition['name'], who)
    done = re.split(r'(?<=[.!?])\s+', done)[-1].rstrip('.!? ')  # the entry's own line, when it has one, comes first
    done = f'{done[:1].lower()}{done[1:]}' if done.startswith(subject) else done
    style = (style or DEFAULT_STYLE).strip().rstrip('.')
    parts = [f'{style}, a fictional everyday close-up of the things from {possessive} errand, just after '
             f'{done}.', 'The things fill the frame, set down on a counter or a table. No people in the picture, '
             'nobody in focus.', event.get('place_look') or '',
             ship_light(event.get('hour')) if aboard else light(event.get('hour'), event.get('weather'), event.get('indoor')),
             (period or {}).get('scene') or '', camera(style, 'things', period)]
    return looks.seen(' '.join(part for part in parts if part))


def shared(connection, companion, event) -> bool:
    """Whether the user is in the moment: an outing or visit with them, or an evening at the home they share
    (companion/life/moving_in.py), when the moment happens at home."""
    moment = event.get('moment') or {}
    if moment.get('outing'):
        return True
    if not at_home(event) or not event.get('starts_at'):
        return False
    from companion.life import moving_in  # the life modules build on the image ones
    try:
        return bool(moving_in.home_state(connection, companion, parse(event['starts_at'])))
    except Exception:  # noqa: BLE001 - a moment that cannot be placed is drawn as their own.
        return False


def pet_prompt(connection, timeline_id, events, image_settings) -> str:
    """A pet-only photo's fixed prompt, or '' for any other post: a digest of several moments is drawn as a whole,
    not as the pet photo one of them carries."""
    if len(events) != 1:
        return ''
    shot = (events[0].get('moment') or {}).get('pet_photo')
    found = shot and pets.find_home(connection, timeline_id, shot.get('item'))
    return pets.photo_prompt(found, shot['shows'], image_settings['style']) if found else ''


def feed_prompt(definition, first, image_settings, worn: tuple[str, bool], who, sheet, aboard=False,
                period=None) -> str:
    look = in_photos(definition, who, worn[1])
    return compose(definition['name'], definition.get('appearance', ''), [first], image_settings['style'], *worn, who=who,
                   sheet=sheet, look=look, aboard=aboard, period=period)


def period_of(connection, definition) -> dict | None:
    """How a picture shows the year of a world that runs in a past one, from their city (decades.picture); None in
    the present."""
    return decades.picture(newcomers.city_for(connection, definition))


def at_home(event) -> bool:
    """Whether the moment happens at their home: no place of its own, and an activity that is done at home (its picture
    line says so) or none at all. Combat training before a show has no place but is not at home."""
    line = picture_of(event)
    return not event.get('place') and (line is None or 'at home' in line or 'home' in (event.get('activity') or ''))


def setting(connection, timeline_id, event, outfit=True) -> tuple[str, bool]:
    """Their home where the moment is at home, and what they are wearing (companion/life/wardrobe.py),
    with whether it says what they wear."""
    wearing = wardrobe.image_hint(connection, timeline_id, event.get('moment') or {}) if outfit else ''
    parts = [home.image_hint(connection, timeline_id, event, at_home(event)), upkeep.image_hint(connection, timeline_id, event),
             traditions.image_hint(connection, timeline_id, event), wearing]
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
    # In person with the user (companion/life/together.py) nobody texts a photo to the person beside them: the picture
    # is the moment as the user sees it. A selfie there drew them twice, once at the lens and once walking behind.
    'scene': 'a wide, atmospheric candid scene of the place, seen through the eyes of the person spending time with '
             '{object}, {object} a few steps away and unposed, with the place all around',
    'scene_both': 'a wide, atmospheric candid scene of two people spending time together, seen from a little way off, '
                  'unposed, with the place all around',
    # The photo they said they took ("quick photo: two crates by the closed stall, my hands around a cup",
    # `build_said`): taken by them, so it shows what they saw and only as much of them as they said.
    # Said "phone photo", the image model drew the phone and its screen around the picture.
    'photo': 'a fictional snapshot {subject} just took, seen through {possessive} own eyes, showing exactly what '
             '{subject} described, with no phone or screen in the picture',
}
OBJECT = {'she': 'her', 'he': 'him', 'they': 'them'}
# The openings as Settings > Advanced > Prompts lists them: a plain moment's own words in place of its empty framing.
OPENINGS = {'moment': MOMENT, **{key: value for key, value in FRAMINGS.items() if key != 'moment'}}


def visit_words(scene_text: dict, neighborhood: str | None) -> dict:
    """A visit at the user's place or theirs in words a picture can show (companion/life/outings.photo_words): the
    moment's own wording, which the chat reads, is left as it is."""
    from companion.life import outings
    if scene_text.get('activity') not in outings.VISIT_DOING or not scene_text.get('summary'):
        return scene_text
    return {**scene_text, **outings.photo_words(scene_text['summary'], scene_text['activity'], neighborhood)}


@own_words
def build_moment(connection, moment, image_settings, framing='moment') -> dict:
    """The frozen inputs of a chat photo: the companion's current slot as the simulation composes
    it, before it is an event. The moment's wording goes into `captions`, so classification covers
    it (F6), and `events` stays empty: there is no event yet to go stale. A view leaves the
    companion out of the picture, so it carries no likeness."""
    companion = require_current(connection)
    definition = companion['version']['definition']
    scene_text = visit_words({key: moment.get(key) for key in ('summary', 'caption', 'mood', 'place', 'hour',
                                                                'weather', 'activity', 'with', 'hobby')},
                             moment.get('neighborhood'))
    scene_text = {**scene_text, 'label': moment.get('label'), 'place_id': moment.get('place_id')}
    scene_text.update(places.scene(connection, companion, scene_text))
    shown = None if framing == 'view' or not moment.get('with_user') else user_shown(connection)
    if shown:
        scene_text['user'] = shown
    appearance = '' if framing == 'view' else definition.get('appearance', '')
    # A moment's own outfit (a wedding's) is kept; their everyday one gives way to an In photos line that says one.
    wearing = '' if framing == 'view' else moment.get('wearing') or ('' if own_outfit(definition) else wardrobe.image_hint(
        connection, companion['active_timeline_id'], moment))
    sheet, who = sheet_for(companion, definition, connection, moment.get('local_date'))
    look = '' if framing == 'view' else in_photos(definition, who, bool(wearing))
    period = period_of(connection, definition)
    prompt = compose(definition['name'], appearance, [scene_text], image_settings['style'], wearing, bool(wearing),
                     framing, who, '' if framing == 'view' else sheet, look, ships.aboard(connection, definition), period)
    likeness = current_for_images(connection)
    if framing == 'view':
        likeness = {**likeness, 'lora': None}
    return {**base_inputs(companion, definition, image_settings), 'prompt': prompt, 'framing': framing,
            'pictured': framing != 'view', 'period': period, 'with_user': bool(shown),
            'captions': [moment[key] for key in ('summary', 'caption', 'label', 'mood', 'place')],
            'moment': moment, **likeness,
            **children(connection, companion['active_timeline_id'],
                       [moment.get(key) for key in ('summary', 'caption', 'label', 'place')])}


# The companion's own words, said of them: "my hands around a cup" is "his hands around a cup".
FIRST_PERSON = re.compile(r"\b(I'm|I am|I've|I'd|I'll|I|me|my|mine|myself)\b", re.IGNORECASE)
TOLD = {'he': {"i'm": "he's", 'i am': 'he is', "i've": "he's", "i'd": "he'd", "i'll": "he'll", 'i': 'he', 'me': 'him',
               'my': 'his', 'mine': 'his', 'myself': 'himself'},
        'she': {"i'm": "she's", 'i am': 'she is', "i've": "she's", "i'd": "she'd", "i'll": "she'll", 'i': 'she',
                'me': 'her', 'my': 'her', 'mine': 'hers', 'myself': 'herself'},
        'they': {"i'm": "they're", 'i am': 'they are', "i've": "they've", "i'd": "they'd", "i'll": "they'll",
                 'i': 'they', 'me': 'them', 'my': 'their', 'mine': 'theirs', 'myself': 'themselves'}}
# Words that put them in their own picture, which then is a selfie: "me and kaito at the stall".
IN_IT = re.compile(r"\b(?:selfies?|me|myself|us|we|my face)\b", re.IGNORECASE)


def told_of(said: str, who: str) -> str:
    """Their words about the photo said of them, for the image model."""
    forms = TOLD.get(who, TOLD['they'])
    return FIRST_PERSON.sub(lambda m: forms[m.group(1).lower()], said)


def said_framing(said: str, kind: str) -> str:
    """A selfie when they asked for one or the words put them in it, else the photo as they took it."""
    return 'selfie' if kind == 'selfie' or IN_IT.search(said) else 'photo'


@own_words
def build_said(connection, moment, said, image_settings, kind='moment') -> dict:
    """The frozen inputs of the chat photo the companion described in their reply (`photos.described`): what they said
    it shows, not the routine slot it was first meant to show, which the chat may have moved on from (they were out
    at a drink stall with a friend while the day had them reading at home). The slot gives only the hour, the weather
    and the year; a selfie keeps their looks, and a photo they took leaves them out but for what they said of
    themselves."""
    companion = require_current(connection)
    definition = companion['version']['definition']
    framing = said_framing(said, kind)
    sheet, who = sheet_for(companion, definition, connection, moment.get('local_date'))
    selfie = framing == 'selfie'
    wearing = '' if not selfie else moment.get('wearing') or ('' if own_outfit(definition) else wardrobe.image_hint(
        connection, companion['active_timeline_id'], moment))
    look = in_photos(definition, who, bool(wearing)) if selfie else ''
    words = told_of(said.strip().rstrip('.'), who)
    event = {'summary': f"The {'selfie' if selfie else 'photo'} shows {words}.", 'place': '', 'with': 'said',
             'hour': moment.get('hour'), 'weather': moment.get('weather')}
    period = period_of(connection, definition)
    prompt = compose(definition['name'], '', [event], image_settings['style'], wearing, bool(wearing), framing, who,
                     sheet if selfie else '', look, ships.aboard(connection, definition), period)
    likeness = current_for_images(connection)
    if not selfie:
        likeness = {**likeness, 'lora': None}
    return {**base_inputs(companion, definition, image_settings), 'prompt': prompt, 'framing': framing,
            'pictured': selfie, 'period': period, 'with_user': False, 'captions': [said], 'said': said,
            'moment': moment, **likeness,
            **children(connection, companion['active_timeline_id'], [said])}


def user_shown(connection) -> str:
    """The user in words, for a moment they share with the companion, or '' when Settings > Pictures leaves them out."""
    from companion import persona_pictures  # it builds on the image modules that import this one
    persona = persona_pictures.here(connection)
    return persona_pictures.described(persona) if persona else ''


@own_words
def build_meme(connection, meme, image_settings) -> dict:
    """The frozen inputs of a meme picture. Its captions are drawn over the picture by the interface,
    never asked of the image model, and they are classified with the rest (F6)."""
    companion = require_current(connection)
    definition = companion['version']['definition']
    if meme['subject']:
        prompt = f"Reaction-meme style photo, simple and centered: {meme['subject']}. A fictional scene."
        likeness = {**current_for_images(connection), 'lora': None}
    else:
        sheet, who = sheet_for(companion, definition, connection)
        look = in_photos(definition, who)
        prompt = (f"Reaction-meme style photo, simple and centered, of a fictional person with a {meme['expression']} "
                  f"expression{meme['where']}, room above and below the face. {sheet} {look}.").rstrip(' .') + '.'
        likeness = current_for_images(connection)
    prompt = looks.seen(prompt)
    return {**base_inputs(companion, definition, image_settings), 'prompt': prompt, 'framing': 'meme',
            'aspect': 'square', 'captions': [meme['top'], meme['bottom'], meme['subject'] or ''],
            'pictured': not meme['subject'],
            'meme': meme, **likeness}


def children(connection, timeline_id: str, texts, outing_ids=()) -> dict:
    """Marks a request whose words name a child in the circle, or that shows a child's big day however it was worded
    (companion/life/families.py), which nothing pictures."""
    found = families.named_child(connection, timeline_id, texts) or \
        (families.childs_day(connection, outing_ids) and "it shows a child's big day, and children are never pictured")
    return {'withheld': True, 'withheld_reason': found} if found else {}


def base_inputs(companion, definition, image_settings) -> dict:
    return {'prompt_version': PROMPT_VERSION, 'negative': negative(), 'style': image_settings['style'],
            'name_in_pictures': bool(definition.get('name_in_pictures')),
            'aspect': image_settings['aspect'], 'seed': random.SystemRandom().randrange(1, 2**31),
            'appearance': definition.get('appearance', ''), 'relationship': definition.get('relationship', ''),
            'character_name': definition['name'], 'character_version_id': companion['version']['id'],
            'events': [], 'marked_nsfw': False}
