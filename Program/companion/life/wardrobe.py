"""The companion's wardrobe: the clothes they own, what they wear today, and how it changes.

Assembled once per timeline without a model, from who they are: their pay tier and spending style
(companion/life/money.py) set how many pieces they own and how fine they are, their job sets what
they wear to work (scrubs, chef whites, a suit or their own clothes), and words in their
personality, interests and appearance pick one to three styles (classic, sporty, bohemian, edgy,
cozy, preppy, vintage, minimal) and their colours. Clothing their appearance names, such as "a
battered leather jacket", becomes a favourite they wear often. The city's era and climate decide
what exists and how many warm coats they need.

What they wear on a given day is drawn, not stored: the same timeline, date, kind of moment and
weather always give the same outfit (`outfit`), so a picture, the chat and the panel agree. Every
two weeks a seeded draw may buy something (if the budget allows that day), wear something out, clear
out a few things or mend one, logged once on the day it happens; purchases count as spending in the
budget through `purchases`. The user can rename, redescribe, remove, restore or add pieces and mark
favourites; upcoming days are then drawn again.
"""
import re
from datetime import date, timedelta

from companion.clock import stamp, zone
from companion.database import decode, encode, identifier, many, one, optional
from companion.errors import require
from companion.life import circle, money
from companion.life.clothing import (
    CAREER_CODES,
    CODES,
    FASHION_WORDS,
    GARMENTS,
    KIT_COLORS,
    MODERN_PIECES,
    OTHER_PIECES,
    PALETTES,
    PLAIN_WORDS,
    SECTOR_CODES,
    STYLE_WORDS,
)
from companion.world import generators

COMPANION = 'companion'
PERIOD_DAYS = 14
RECENT_DAYS = 21
MODERN = {'modern', 'future'}
# New clothes are woven into the companion's agenda on the day they arrive; tests turn this off.
WEAVE = True

CATEGORIES = ('top', 'bottom', 'dress', 'suit', 'layer', 'outerwear', 'shoes', 'accessory', 'active', 'lounge',
              'sleep', 'work')
LABELS = {'top': 'Tops', 'bottom': 'Bottoms', 'dress': 'Dresses', 'suit': 'Suits', 'layer': 'Jackets and layers',
          'outerwear': 'Coats', 'shoes': 'Shoes', 'accessory': 'Accessories', 'active': 'Workout clothes',
          'lounge': 'Loungewear', 'sleep': 'Sleepwear', 'work': 'Work clothes'}
# Occasions: c casual, w work, o going out, h at home, a working out, s sleep. Coats instead say
# when they are needed: k cold, l cool, r rain.
DEFAULT_OCCASIONS = {'top': 'cw', 'bottom': 'cw', 'dress': 'co', 'suit': 'wo', 'layer': 'cwo', 'outerwear': 'kl',
                     'shoes': 'cw', 'accessory': 'co', 'active': 'a', 'lounge': 'h', 'sleep': 's', 'work': 'w'}
STYLES = ('classic', 'sporty', 'boho', 'edgy', 'cozy', 'preppy', 'vintage', 'minimal')
STYLE_NAMES = {'boho': 'bohemian'}

# Suits are always a neutral; bottoms and coats usually are.
NEUTRALS = ('navy', 'charcoal', 'black', 'grey', 'camel', 'khaki', 'brown', 'olive', 'cream')
NEUTRAL_SHARE = {'suit': 1.0, 'bottom': 0.65, 'outerwear': 0.6}
# A few words about quality, by pay tier: thrifted at the bottom, designer at the top.
QUALITY = {0: ('thrifted', 'secondhand', 'well-worn', 'hand-me-down'), 3: ('designer', 'beautifully cut')}
QUALITY_SHARE = 0.3
QUALITY_CATEGORIES = {'top', 'bottom', 'dress', 'layer', 'outerwear', 'shoes'}

FEMININE = {'she', 'her', 'hers', 'herself', 'woman', 'girl', 'lady'}
MASCULINE = {'he', 'him', 'his', 'himself', 'man', 'guy', 'gentleman'}

# Pieces owned by pay tier, before spending style and love of clothes.
BASE_SIZE = (22, 30, 42, 58)
MONEY_STYLE = {'careful': 0.85, 'balanced': 1.0, 'spender': 1.2}
FASHION_SIZE = {-1: 0.75, 0: 1.0, 1: 1.3, 2: 1.6}
SIZE_WORDS = ((24, 'a small, practical wardrobe'), (36, 'a modest wardrobe'), (52, 'a full wardrobe'),
              (999, 'a big wardrobe'))
# Each category's share of the pieces, and at least how many there are.
SHARES = {'top': 0.3, 'bottom': 0.14, 'dress': 0.1, 'suit': 0.0, 'layer': 0.06, 'outerwear': 0.07, 'shoes': 0.12,
          'accessory': 0.09, 'active': 0.05, 'lounge': 0.04, 'sleep': 0.03}
MINIMUM = {'top': 3, 'bottom': 2, 'outerwear': 1, 'shoes': 2, 'lounge': 1, 'sleep': 1}

# Dress codes worn head to toe on the job: nothing of their own goes with them.
WHOLE = {'water', 'lifeguard'}
SIGNATURE = re.compile(r"\b(?:a|an|her|his|their|the)\s+((?:[a-z'-]+\s+){0,3}?(?:%s))\b" % '|'.join(
    sorted((re.escape(word) for word in GARMENTS), key=len, reverse=True)), re.IGNORECASE)
FILLER = {'favorite', 'favourite', 'usual', 'signature', 'trademark', 'ever-present', 'beloved', 'trusty', 'own',
          'always', 'often', 'sometimes', 'usually'}
MAX_SIGNATURES = 3

# Which outfit a moment calls for, from the agenda entry's activity and the block's kind.
ACTIVE_TOPS = ('moisture-wicking tee', 'track jacket')
ACTIVE_BOTTOMS = ('leggings', 'running shorts')
LOUNGE_BOTTOMS = ('sweatpants', 'worn-in joggers')
LOUNGE_EXTRAS = ('fuzzy socks', 'soft slippers')
ATHLETIC_SHOES = ('running shoes', 'white sneakers', 'cross-training shoes')
WORK_ACTIVITIES = {'steady-shift', 'busy-shift', 'lunch-out'}
OUT_ACTIVITIES = {'dinner', 'drinks', 'show', 'birthday', 'own-birthday', 'gathering'}
HOME_ACTIVITIES = {'sick-day', 'nap', 'slow', 'reading', 'home-cooking', 'chores'}
OUTDOOR_ACTIVITIES = {'walk', 'market', 'festival', 'groceries', 'browse', 'workout'}
COLD_F, COOL_F = 50, 64
OCCASION_WORDS = {'casual': 'out and about', 'work': 'at work', 'out': 'going out', 'home': 'at home',
                  'active': 'working out', 'sleep': 'in bed'}


# --- Who they are ---

def modern(data: dict | None) -> bool:
    return data is None or data['era'] in MODERN


def words_of(definition: dict) -> set[str]:
    phrases = [definition.get(key) or '' for key in ('personality', 'identity', 'voice', 'appearance')]
    phrases += [*definition.get('interests', ()), *definition.get('life_themes', ())]
    return {word.strip('.,;:!?()"\'').casefold() for phrase in phrases for word in phrase.split()}


def hits(words: set[str], stems) -> int:
    """How many of the stems their words carry ("tattoo" finds "tattoos"; short stems match whole words)."""
    return sum(any(word == stem or len(stem) > 4 and word.startswith(stem) for word in words) for stem in stems)


def presentation(definition: dict) -> str:
    """'f', 'm' or 'n' from the pronouns and nouns their description uses most."""
    text = ' '.join(definition.get(key) or '' for key in ('identity', 'personality', 'appearance', 'background'))
    tokens = re.findall(r"[a-z]+", text.casefold())
    feminine, masculine = sum(token in FEMININE for token in tokens), sum(token in MASCULINE for token in tokens)
    return 'f' if feminine > masculine else 'm' if masculine > feminine else 'n'


def dress_code(career: dict | None, era_modern: bool) -> str:
    if not era_modern or not career:
        return 'casual'
    return CAREER_CODES.get(career['id']) or SECTOR_CODES.get(career.get('sector', ''), 'casual')


def styles_for(seed: str, definition: dict, code: str, breadth: int) -> list[str]:
    """Their styles, strongest first: words in who they are, a nudge from their job, a seeded rest."""
    words = words_of(definition)
    nudges = {'business': 'classic', 'trainer': 'sporty', 'water': 'sporty', 'lifeguard': 'sporty',
              'creative': 'boho', 'fashion': 'classic', 'trades': 'minimal', 'scrubs': 'cozy'}
    scores = {style: hits(words, STYLE_WORDS[style]) * 2 + (style == nudges.get(code)) +
              generators.unit(seed, 'style', style) for style in STYLES}
    return sorted(STYLES, key=lambda style: -scores[style])[:breadth]


def career_of(definition: dict, data: dict | None, budget) -> dict | None:
    if budget:
        return budget.career
    if not data:
        return None
    try:
        return money.career_for(definition, data)[0]
    except (KeyError, TypeError):
        return None


def profile(seed: str, definition: dict, data: dict | None) -> dict:
    """How big and what kind of wardrobe they have: the same for the same seed, definition and city."""
    era_modern = modern(data)
    budget = money.profile(definition) if data and data['id'] == (money.city_for(definition) or {}).get('id') else None
    tier = budget.tier if budget else money.DEFAULT_TIER
    spending = budget.style if budget else 'balanced'
    career = career_of(definition, data, budget)
    code = dress_code(career, era_modern)
    words = words_of(definition)
    fashion = hits(words, FASHION_WORDS) - hits(words, PLAIN_WORDS) + (code == 'fashion' or (career or {}).get(
        'id') in ('actor', 'performer'))
    fashion = max(-1, min(2, fashion))
    breadth = max(1, min(3, 1 + (tier >= 2) + (fashion > 0) - (fashion < 0)))
    size = round(BASE_SIZE[tier] * MONEY_STYLE[spending] * FASHION_SIZE[fashion])
    months = ((data or {}).get('climate') or {}).get('months') or []
    coldest = min((month['high_f'] for month in months), default=45)
    rainy = max((month.get('rain_days', 0) for month in months), default=8)
    return {'tier': tier, 'spending': spending, 'fashion': fashion, 'size': size, 'code': code,
            'career': career['name'] if career else '', 'styles': styles_for(seed, definition, code, breadth),
            'who': presentation(definition), 'coldest_f': coldest, 'rainy': rainy >= 8,
            'era': 'modern' if era_modern else data['era']}


# --- Assembly ---

def plural(piece: str) -> bool:
    last = piece.split(' ')[-1]
    return last.endswith('s') and not last.endswith('ss')


def article(text: str) -> str:
    if plural(text) or text.startswith(('a ', 'an ', 'the ', 'pair of ')):
        return text if not text.startswith('pair of ') else f'a {text}'
    return f"{'an' if text[:1] in 'aeiou' else 'a'} {text}"


def fits(piece: tuple, found: dict, tier: int | None = None) -> bool:
    who, lowest = piece[4], piece[5]
    tier = found['tier'] if tier is None else tier
    return lowest <= tier and who in ('*', found['who'])


def catalog_for(found: dict) -> tuple:
    return MODERN_PIECES if found['era'] == 'modern' else OTHER_PIECES


def piece_weight(piece: tuple, found: dict) -> float:
    styles = piece[3].split()
    if piece[3] == '*':
        return 1.0
    return 3.0 if set(styles) & set(found['styles']) else 0.25


def name_piece(seed: str, label: str, piece: tuple, found: dict) -> str:
    """"a mustard cable-knit sweater", "thrifted dark-wash straight-leg jeans"."""
    name, category, _occasions, styles, _who, _lowest, palette = piece
    color = ''
    if palette == 'style' and found['era'] != 'modern':
        color = generators.pick(seed, f'{label}:color', list(PALETTES['other']))
    elif palette == 'style' and generators.unit(seed, label, 'neutral') < NEUTRAL_SHARE.get(category, 0):
        color = generators.pick(seed, f'{label}:color', list(NEUTRALS[:4] if category == 'suit' else NEUTRALS))
    elif palette == 'style':
        own = [style for style in found['styles'] if style in styles.split()] or found['styles']
        color = generators.pick(seed, f'{label}:color', list(PALETTES[generators.pick(seed, f'{label}:palette', own)]))
    elif palette:
        color = generators.pick(seed, f'{label}:color', list(PALETTES[palette]))
    quality = ''
    if category in QUALITY_CATEGORIES and found['tier'] in QUALITY and \
            generators.unit(seed, label, 'quality') < QUALITY_SHARE:
        quality = generators.pick(seed, f'{label}:quality', list(QUALITY[found['tier']]))
    elif 'vintage' in found['styles'] and category in ('top', 'dress', 'layer', 'outerwear') and \
            generators.unit(seed, label, 'vintage') < 0.15:
        quality = 'vintage'
    return article(' '.join(part for part in (quality, color, name) if part))


def piece_item(seed: str, label: str, piece: tuple, found: dict) -> dict:
    return {'category': piece[1], 'name': name_piece(seed, label, piece, found), 'variety': piece[0],
            'details': {'occasions': piece[2], 'signature': False}}


def quotas(found: dict) -> dict[str, int]:
    shares = dict(SHARES)
    if found['who'] != 'f':
        shares['top'] += shares.pop('dress')
    if found['code'] == 'business' or found['tier'] >= 2:
        shares['suit'] = 0.03
    # Mild winters need one coat; hard ones several.
    shares['outerwear'] *= 0.5 if found['coldest_f'] >= 60 else 1.4 if found['coldest_f'] <= 38 else 1.0
    if found['era'] != 'modern':
        shares.pop('active', None)
    counts = {category: max(MINIMUM.get(category, 0), round(found['size'] * share)) for category, share in shares.items()}
    if found['code'] == 'business':
        counts['suit'] = max(counts.get('suit', 0), 2)
    return counts


def kit_items(seed: str, found: dict) -> list[dict]:
    if found['era'] != 'modern':
        return []
    _reads, kit, _own = CODES[found['code']]
    items, colors = [], list(KIT_COLORS)
    for index, (name, slot) in enumerate(kit):
        if '{c}' in name:
            color = generators.pick(seed, f'kit{index}', colors)
            colors.remove(color)
            name = name.format(c=color)
        items.append({'category': 'work', 'name': name, 'variety': slot,
                      'details': {'occasions': 'w', 'signature': False, 'slot': slot}})
    return items


def signatures(definition: dict) -> list[dict]:
    """Clothing their appearance (or identity) names, as favourites they wear often."""
    text = ' '.join(definition.get(key) or '' for key in ('appearance', 'identity'))
    found, seen = [], set()
    for match in SIGNATURE.finditer(text):
        words = [word for word in match.group(1).split() if word.casefold() not in FILLER]
        phrase = ' '.join(words)
        noun = words[-1].casefold() if words else ''
        key = GARMENTS.get(noun) or GARMENTS.get(noun.rstrip('s'))
        if not key or phrase.casefold() in seen:
            continue
        seen.add(phrase.casefold())
        occasions = 'cwoh' if key == 'accessory' else 'cwo' if key != 'outerwear' else 'kl'
        found.append({'category': key, 'name': article(phrase), 'variety': noun,
                      'details': {'occasions': occasions, 'signature': True}})
    return found[:MAX_SIGNATURES]


def assemble(seed: str, definition: dict, data: dict | None) -> tuple[dict, list[dict]]:
    """(profile, pieces) they start with: the same for the same seed, definition and city data."""
    found = profile(seed, definition, data)
    items = signatures(definition) + kit_items(seed, found)
    pieces = [piece for piece in catalog_for(found) if fits(piece, found)]
    for category, count in quotas(found).items():
        choices = [piece for piece in pieces if piece[1] == category]
        have = sum(item['category'] == category for item in items)
        for index in range(count - have):
            item = new_piece(seed, f'{category}{index}', choices, found, items)
            if item is None:
                break
            items.append(item)
    return found, items + basics(seed, found, items)


def basics(seed: str, found: dict, items: list[dict]) -> list[dict]:
    """What every modern wardrobe has whatever the draw: something to work out in and shoes for
    it, and shoes for a night out."""
    if found['era'] != 'modern':
        return []
    pieces = {piece[0]: piece for piece in MODERN_PIECES}
    have = {item['variety'] for item in items}
    wanted = []
    if not have & set(ACTIVE_TOPS):
        wanted.append('moisture-wicking tee')
    if not have & set(ACTIVE_BOTTOMS):
        wanted.append('leggings' if found['who'] == 'f' else 'running shorts')
    if not have & set(ATHLETIC_SHOES):
        wanted.append('running shoes')
    if not any(item['category'] == 'shoes' and 'o' in item['details']['occasions'] for item in items):
        wanted.append('ankle boots')
    if not have & set(LOUNGE_BOTTOMS):
        wanted.append('sweatpants')
    return [piece_item(seed, f'basic:{name}', pieces[name], found) for name in wanted]


def new_piece(seed: str, label: str, choices: list[tuple], found: dict, owned: list[dict], need=()) -> dict | None:
    """A piece not yet owned, leaning to their styles; a second colour of the same piece is fine but
    each one they already have makes another less likely."""
    names = {plain_name(item['name']) for item in owned}
    counts: dict[str, int] = {}
    for item in owned:
        counts[item['variety']] = counts.get(item['variety'], 0) + 1
    weights = [piece_weight(piece, found) * (2.5 if piece[1] in need else 1.0) / (1 + 2 * counts.get(piece[0], 0))
               for piece in choices]
    for attempt in range(6):
        piece = generators.pick(seed, f'{label}:{attempt}', choices, weights)
        if piece is None:
            return None
        item = piece_item(seed, f'{label}:{attempt}', piece, found)
        if plain_name(item['name']) not in names:
            return item
    return None


def plain_name(name: str) -> str:
    """The name without words about quality, so "a vintage mustard tea dress" is the same as "a mustard tea dress"."""
    extra = {word for words in QUALITY.values() for word in words} | {'vintage', 'a', 'an'}
    return ' '.join(word for word in name.split(' ') if word not in extra)


def started_on(connection, timeline_id) -> date:
    row = one(connection, 'SELECT created_at FROM timelines WHERE id=?', (timeline_id,))
    return date.fromisoformat(row['created_at'][:10])


def ensure(connection, timeline_id: str, definition: dict, world, now) -> dict:
    """The timeline's wardrobe state, assembling the wardrobe the first time it is needed."""
    state = optional(connection, 'SELECT * FROM wardrobe_state WHERE timeline_id=?', (timeline_id,))
    if state:
        return state
    seed, start = f'wardrobe:{timeline_id}', started_on(connection, timeline_id)
    found, items = assemble(seed, definition, circle.city_data(definition, world))
    for item in items:
        insert_item(connection, timeline_id, item, 'generated', start, now)
    connection.execute('INSERT INTO wardrobe_state (timeline_id, seed, started, profile, next_period, created_at, '
                       'updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)',
                       (timeline_id, seed, start.isoformat(), encode(found), stamp(now), stamp(now)))
    return one(connection, 'SELECT * FROM wardrobe_state WHERE timeline_id=?', (timeline_id,))


def insert_item(connection, timeline_id, item: dict, origin: str, since: date, now) -> str:
    item_id = identifier()
    connection.execute(
        'INSERT INTO wardrobe_items (id, timeline_id, category, name, variety, details, origin, since, created_at, '
        'updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (item_id, timeline_id, item['category'], item['name'], item['variety'], encode(item['details']), origin,
         since.isoformat(), stamp(now), stamp(now)))
    return item_id


# --- On a date ---

def items_on(connection, timeline_id, day: date) -> list[dict]:
    """What they own on this local date, in category order."""
    rows = many(connection, 'SELECT * FROM wardrobe_items WHERE timeline_id=? AND since<=? AND (until IS NULL OR '
                'until>?) ORDER BY since, created_at', (timeline_id, day.isoformat(), day.isoformat()))
    return sorted((item_view(row) for row in rows), key=lambda item: CATEGORIES.index(item['category']))


def item_view(row: dict) -> dict:
    details = decode(row['details'])
    return {'id': row['id'], 'category': row['category'], 'name': row['name'], 'variety': row['variety'],
            'description': details.get('description') or '', 'occasions': details.get('occasions', ''),
            'favorite': bool(details.get('signature')), 'slot': details.get('slot'), 'origin': row['origin'],
            'since': row['since'], 'until': row['until'], 'edited': bool(row['edited']), 'revision': row['revision']}


def occasion_for(activity: str | None, block_kind: str | None) -> str:
    """Which outfit a moment calls for: 'work', 'out', 'home', 'active', 'sleep' or 'casual'."""
    if block_kind == 'sleep':
        return 'sleep'
    if activity in WORK_ACTIVITIES or block_kind == 'work' and activity not in OUT_ACTIVITIES:
        return 'work'
    if activity in OUT_ACTIVITIES:
        return 'out'
    if activity == 'workout':
        return 'active'
    if activity in HOME_ACTIVITIES:
        return 'home'
    return 'casual'


def outfit(items: list[dict], occasion: str, seed: str, weather: dict | None = None, code: str = 'casual',
           outdoors: bool = True) -> list[dict]:
    """What they wear for this occasion and weather, drawn from what they own: the same items and
    seed always give the same outfit. Favourites are four times likelier where they fit."""
    weather = weather or {}
    if occasion == 'active' and not any(item['category'] == 'active' for item in items):
        occasion = 'casual'
    if occasion in ('sleep', 'home', 'active'):
        return [item for item in SIMPLE[occasion](items, seed) if item]
    letter = {'casual': 'c', 'work': 'w', 'out': 'o'}[occasion]
    kit = {}
    if occasion == 'work':
        kit = {item['slot']: item for item in reversed(items) if item['category'] == 'work' and item['slot']}
        letter = CODES.get(code, CODES['casual'])[2]
    worn = [item for item in dressed(items, kit, letter, seed, weather, code) if item]
    if occasion == 'work' and code in WHOLE and worn:
        return worn
    worn.append(kit.get('shoes') or choose(items, ('shoes',), letter, seed, 'shoes', rain=weather.get('rain')))
    layer = kit.get('layer') or (choose(items, ('layer',), letter, seed, 'layer')
                                 if generators.unit(seed, 'layer?') < 0.4 else None)
    coat = coat_for(items, weather, seed) if outdoors else None
    if coat and layer and not kit.get('layer') and not layer['favorite']:
        layer = None
    accessory = choose(items, ('accessory',), 'k' if coat and (weather.get('high_f') or 99) <= COLD_F else letter,
                       seed, 'accessory') if generators.unit(seed, 'accessory?') < 0.45 else None
    return [item for item in (coat, layer, *worn, kit.get('extra'), accessory) if item]


def dressed(items, kit: dict, letter: str, seed: str, weather: dict, code: str) -> list:
    """The outfit's body: a work set, a kit top, or a dress, suit or top with a bottom."""
    sets = [item for item in items if item['category'] == 'work' and item['slot'] == 'set'] if kit else []
    if sets:
        return [generators.pick(seed, 'set', sets)]
    if 'top' in kit:
        return [kit['top'], kit.get('bottom') or choose(items, ('bottom',), letter, seed, 'bottom', warm=weather)]
    body = choose(items, ('dress', 'suit', 'top'), letter, seed, 'body',
                  {'dress': 0.35 if letter == 'o' else 0.2, 'suit': 0.6 if code == 'business' else 0.15})
    if body and body['category'] == 'top':
        return [body, kit.get('bottom') or choose(items, ('bottom',), letter, seed, 'bottom', warm=weather)]
    return [body]


def sleepwear(items, seed: str) -> list:
    return [choose(items, ('sleep',), 's', seed, 'sleep')]


def loungewear(items, seed: str) -> list:
    """Something comfortable on top (loungewear or a cozy top) and lounge pants, maybe fuzzy socks."""
    lounge = [item for item in items if item['category'] == 'lounge']
    bottoms = [item for item in lounge if item['variety'] in LOUNGE_BOTTOMS]
    tops = [item for item in lounge if item not in bottoms and item['variety'] not in LOUNGE_EXTRAS] + \
        [item for item in items if item['category'] == 'top' and 'h' in item['occasions']]
    extras = [item for item in lounge if item['variety'] in LOUNGE_EXTRAS]
    worn = [generators.pick(seed, 'home-top', tops), generators.pick(seed, 'home-bottom', bottoms)]
    if extras and generators.unit(seed, 'home-extra') < 0.4:
        worn.append(generators.pick(seed, 'home-extra', extras))
    return worn if any(worn) else [choose(items, ('top',), 'c', seed, 'top')]


def workout(items, seed: str) -> list:
    """A workout top and bottom (from the bottoms, else any of their workout clothes) and athletic shoes."""
    active = [item for item in items if item['category'] == 'active']
    bottoms = [item for item in active if item['variety'] in ACTIVE_BOTTOMS]
    bottom = generators.pick(seed, 'active-bottom', bottoms)
    top = generators.pick(seed, 'active-top', [item for item in active if item is not bottom])
    shoes = [item for item in items if item['category'] == 'shoes' and item['variety'] in ATHLETIC_SHOES]
    return [top, bottom, generators.pick(seed, 'active-shoes', shoes) or choose(items, ('shoes',), 'ac', seed, 'shoes')]


SIMPLE = {'sleep': sleepwear, 'home': loungewear, 'active': workout}


def coat_for(items, weather: dict, seed: str) -> dict | None:
    high = weather.get('high_f')
    if weather.get('rain'):
        rain = [item for item in items if item['category'] == 'outerwear' and 'r' in item['occasions']]
        if rain:
            return generators.pick(seed, 'rain-coat', rain)
    if high is None or high > COOL_F:
        return None
    need = 'k' if high <= COLD_F else 'l'
    return choose(items, ('outerwear',), need, seed, 'coat') or choose(items, ('outerwear',), 'kl', seed, 'coat2')


def choose(items, categories, letters: str, seed: str, label: str, lean: dict | None = None, warm=None, rain=None):
    """A piece in these categories for any of these occasion letters (else any in the categories)."""
    within = [item for item in items if item['category'] in categories]
    if rain:
        boots = [item for item in within if 'r' in item['occasions']]
        if boots:
            return generators.pick(seed, f'{label}:rain', boots)
    if warm and (warm.get('high_f') or 0) < 70:
        within = [item for item in within if 'short' not in item['variety']] or within
    fitting = [item for item in within if set(letters) & set(item['occasions'])] or \
        [item for item in within if not set(item['occasions']) & set('ahs')]
    weights = [(4.0 if item['favorite'] else 1.0) * (lean or {}).get(item['category'], 1.0) for item in fitting]
    return generators.pick(seed, label, fitting, weights)


def phrase(worn: list[dict]) -> str:
    """"a navy peacoat over a cream cable-knit sweater, dark-wash jeans and ankle boots, with a wool scarf"."""
    if not worn:
        return ''
    over = [item for item in worn if item['category'] in ('outerwear',) or item.get('slot') == 'layer'
            or item['category'] == 'layer']
    accessories = [item for item in worn if item['category'] == 'accessory' or item.get('slot') == 'extra']
    core = [item for item in worn if item not in over and item not in accessories]
    text = listing([item['name'] for item in core])
    if over:
        text = f"{' over '.join(item['name'] for item in over[:2])} over {text}" if text else listing(
            [item['name'] for item in over])
    if accessories:
        text += f", with {listing([item['name'] for item in accessories])}"
    return text


def listing(names: list[str]) -> str:
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}" if names else ''


def worn_on(connection, timeline_id: str, local_date: str, activity: str | None, block_kind: str | None,
            weather: dict | None, outdoors=True) -> list[dict]:
    """The outfit for one moment of one local date, or [] before the wardrobe exists."""
    state = optional(connection, 'SELECT * FROM wardrobe_state WHERE timeline_id=?', (timeline_id,))
    if not state:
        return []
    occasion = occasion_for(activity, block_kind)
    items = items_on(connection, timeline_id, date.fromisoformat(local_date))
    found = decode(state['profile'])
    return outfit(items, occasion, f"{state['seed']}:{local_date}:{occasion}", weather, found.get('code', 'casual'),
                  outdoors)


# --- Slow change ---

def change_day(state: dict, period: int) -> date:
    start = date.fromisoformat(state['started']) + timedelta(days=PERIOD_DAYS * period)
    return start + timedelta(days=int(generators.unit(state['seed'], 'change-day', period) * PERIOD_DAYS))


def change_share(found: dict) -> float:
    """How likely a two-week period brings a change: shoppers and the well-paid change more."""
    share = 0.3 + 0.08 * found['tier'] + {'careful': -0.1, 'balanced': 0, 'spender': 0.15}[found['spending']]
    return max(0.15, min(0.85, share + 0.12 * found['fashion']))


def evolve(connection, timeline_id: str, definition: dict, through: date, now) -> int:
    """Apply the seeded changes due on or before `through`. Each two-week period has at most one,
    recorded once, so evolving in steps or all at once gives the same wardrobe."""
    state = one(connection, 'SELECT * FROM wardrobe_state WHERE timeline_id=?', (timeline_id,))
    found = decode(state['profile'])
    period, applied = state['next_period'], 0
    while (day := change_day(state, period)) <= through:
        done = optional(connection, 'SELECT id FROM wardrobe_log WHERE timeline_id=? AND period=?',
                        (timeline_id, period))
        if not done and generators.unit(state['seed'], 'change', period) < change_share(found):
            applied += apply_change(connection, state, found, definition, period, day, now)
        period += 1
    connection.execute('UPDATE wardrobe_state SET next_period=?, updated_at=? WHERE timeline_id=?',
                       (period, stamp(now), timeline_id))
    return applied


def options(items: list[dict], found: dict) -> list[tuple[str, float]]:
    own = [item for item in items if item['category'] != 'work']
    choices = [('mended', 0.6)]
    ratio = len(own) / max(found['size'], 1)
    choices.append(('bought', 3.0 if ratio < 0.9 else 1.5 if ratio < 1.15 else 0.4))
    if ratio > 0.8:
        choices.append(('worn-out', 1.5))
    if ratio > 1.1:
        choices.append(('clear-out', 2.0 if found['fashion'] < 1 else 1.0))
    return choices


def apply_change(connection, state, found, definition, period, day: date, now) -> int:
    timeline_id, seed = state['timeline_id'], f"{state['seed']}:{period}"
    items = items_on(connection, timeline_id, day)
    choices = options(items, found)
    kind = generators.pick(seed, 'kind', [key for key, _ in choices], [weight for _, weight in choices])
    made = CHANGES[kind](connection, state, found, definition, seed, day, items, now)
    if made is None:
        return 0
    kind, item_id, text, spend = made
    connection.execute('INSERT INTO wardrobe_log (id, timeline_id, period, local_date, kind, item_id, text, spend, '
                       'created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                       (identifier(), timeline_id, period, day.isoformat(), kind, item_id, text, spend, stamp(now)))
    return 1


def season_need(found: dict, day: date) -> list[str]:
    """What a shop trip leans toward: coats and scarves before winter, light things before summer."""
    if found['coldest_f'] < 60 and day.month in (9, 10, 11):
        return ['outerwear', 'accessory', 'top']
    if day.month in (4, 5, 6):
        return ['top', 'bottom', 'dress', 'shoes']
    return []


def spend_for(category: str, found: dict) -> str:
    big = category in ('outerwear', 'suit', 'shoes', 'dress')
    return ('$$$' if big else '$$') if found['tier'] >= 3 else '$$' if big else '$'


def bought(connection, state, found, definition, seed, day, items, now):
    pieces = [piece for piece in catalog_for(found) if fits(piece, found)]
    need = season_need(found, day)
    item = new_piece(seed, 'buy', pieces, found, items, need)
    if item is None:
        return None
    spend = spend_for(item['category'], found)
    budget = money.profile(definition)
    if budget and money.left_on(budget, day) < money.PURCHASES[spend] * money.monthly_share(budget):
        return 'wanted', None, f"had an eye on {item['name']}, but it will have to wait until money is less tight", ''
    item_id = insert_item(connection, state['timeline_id'], item, 'change', day, now)
    verb = 'thrifted' if found['tier'] == 0 and generators.unit(seed, 'thrift') < 0.5 else 'bought'
    return 'bought', item_id, f"{verb} {item['name']}", spend


def retire(connection, item_id, day: date, now):
    connection.execute('UPDATE wardrobe_items SET until=?, updated_at=? WHERE id=?', (day.isoformat(), stamp(now),
                                                                                     item_id))


def wearable(items):
    """What can wear out or go: not the work kit and not their favourites."""
    return [item for item in items if item['category'] not in ('work',) and not item['favorite']]


def worn_out(connection, state, found, definition, seed, day, items, now):
    choices = [item for item in wearable(items) if item['category'] in ('top', 'shoes', 'lounge', 'active', 'bottom')]
    item = generators.pick(seed, 'worn', choices)
    if item is None:
        return None
    retire(connection, item['id'], day, now)
    verb = 'wore holes through' if item['category'] == 'shoes' else 'finally retired'
    return 'worn-out', item['id'], f"{verb} {item['name']}", ''


def clear_out(connection, state, found, definition, seed, day, items, now):
    choices = wearable(items)
    first = generators.pick(seed, 'clear1', choices)
    if first is None:
        return None
    second = generators.pick(seed, 'clear2', [item for item in choices if item is not first])
    gone = [item for item in (first, second) if item]
    for item in gone:
        retire(connection, item['id'], day, now)
    return 'clear-out', first['id'], f"cleared out the closet and gave away {listing([i['name'] for i in gone])}", ''


def mended(connection, state, found, definition, seed, day, items, now):
    item = generators.pick(seed, 'mend', [item for item in items if item['category'] in ('top', 'bottom', 'layer',
                                                                                          'outerwear', 'dress')])
    if item is None:
        return None
    return 'mended', item['id'], f"mended {item['name']}", ''


CHANGES = {'bought': bought, 'worn-out': worn_out, 'clear-out': clear_out, 'mended': mended}


# --- Agenda ---

WORKING_ACTIVITIES = {'steady-shift', 'busy-shift', 'library', 'study-cafe'}


def touch(connection, timeline_id: str, subject: str, entry: dict | None, local_date: str, definition: dict, world,
          now) -> dict | None:
    """The companion's agenda entry with a wardrobe change that happens that day woven in, once.
    Circle members' entries, and moments at work, pass through unchanged."""
    if subject != COMPANION or not entry:
        return entry
    day = date.fromisoformat(local_date)
    ensure(connection, timeline_id, definition, world, now)
    evolve(connection, timeline_id, definition, day, now)
    if not WEAVE or entry.get('activity') in WORKING_ACTIVITIES or entry.get('wardrobe'):
        return entry
    change = untold_change(connection, timeline_id, day)
    if not change or change['kind'] == 'mended' and entry.get('activity') not in ('chores', 'slow', 'reading', None):
        return entry
    sentence = f"{definition['name']} {change['text']}."
    sentence = sentence[0].upper() + sentence[1:]
    return {**entry, 'summary': f"{entry['summary'].rstrip()} {sentence}",
            'wardrobe': {'change': change['id'], 'sentence': sentence}}


def untold_change(connection, timeline_id, day: date) -> dict | None:
    for row in many(connection, 'SELECT * FROM wardrobe_log WHERE timeline_id=? AND local_date=?',
                    (timeline_id, day.isoformat())):
        told = optional(connection, "SELECT id FROM life_agenda WHERE timeline_id=? AND subject=? "
                        "AND json_extract(entry, '$.wardrobe.change')=?", (timeline_id, COMPANION, row['id']))
        if not told:
            return row
    return None


# --- Images and chat ---

def image_hint(connection, timeline_id: str, moment: dict) -> str:
    """What they wear in a picture of this moment (an event's or a chat photo's: activity, block
    kind, local date and weather), or '' before the wardrobe exists or without a date."""
    local_date = moment.get('local_date')
    if not local_date:
        return ''
    outdoors = moment.get('activity') in OUTDOOR_ACTIVITIES
    worn = worn_on(connection, timeline_id, local_date, moment.get('activity'), moment.get('block_kind'),
                   moment.get('weather'), outdoors)
    text = phrase(worn)
    return f"Wearing {text}." if text else ''


def current_moment(connection, timeline_id: str, now) -> dict | None:
    """The companion's agenda slot right now, as image_hint and context_lines read it."""
    row = optional(connection, 'SELECT * FROM life_agenda WHERE timeline_id=? AND subject=? AND starts_at<=? AND '
                   'ends_at>? LIMIT 1', (timeline_id, COMPANION, stamp(now), stamp(now)))
    if not row:
        return None
    block, entry = decode(row['block']), decode(row['entry']) if row['entry'] else {}
    return {'local_date': row['local_date'], 'activity': (entry or {}).get('activity'), 'block_kind': block.get('kind'),
            'weather': block.get('weather')}


def summary_text(found: dict, count: int, person='you') -> str:
    """"Your style is mostly cozy: a modest wardrobe (about 34 pieces). For work you wear scrubs." for
    the chat, or the same about "their" for the panel."""
    size = next(text for limit, text in SIZE_WORDS if count <= limit)
    styles = [STYLE_NAMES.get(style, style) for style in found['styles']]
    money_note = {0: ', mostly bought cheap or secondhand', 3: ', with some expensive pieces'}.get(found['tier'], '')
    own, wear = ('Your', 'you wear') if person == 'you' else ('Their', 'they wear')
    work = ''
    if found['era'] == 'modern' and found.get('career'):
        work = f" For work {wear} {CODES[found['code']][0]}."
    return f"{own} style is mostly {listing(styles)}: {size} (about {count} pieces){money_note}.{work}"


def context_lines(connection, timeline_id: str, day: date, now) -> list[tuple[str, str]]:
    """(identity, line) pairs describing their clothes, what they have on now and recent changes."""
    state = optional(connection, 'SELECT * FROM wardrobe_state WHERE timeline_id=?', (timeline_id,))
    if not state:
        return []
    items = items_on(connection, timeline_id, day)
    found = decode(state['profile'])
    lines = [(f'wardrobe:{timeline_id}:summary', f'- {summary_text(found, len(items))}')]
    favourites = [item['name'] for item in items if item['favorite']]
    if favourites:
        lines.append((f'wardrobe:{timeline_id}:favorites', f"- Favourites you wear a lot: {listing(favourites)}."))
    moment = current_moment(connection, timeline_id, now)
    if moment:
        occasion = occasion_for(moment['activity'], moment['block_kind'])
        worn = outfit(items, occasion, f"{state['seed']}:{moment['local_date']}:{occasion}", moment['weather'],
                      found.get('code', 'casual'))
        if worn:
            lines.append((f"wardrobe:{timeline_id}:now:{moment['local_date']}:{occasion}",
                          f"- Wearing right now ({OCCASION_WORDS[occasion]}): {phrase(worn)}."))
    for category in CATEGORIES:
        names = [item['name'] for item in items if item['category'] == category and not item['favorite']]
        if names:
            shown = names[:8] + ([f'{len(names) - 8} more'] if len(names) > 8 else [])
            lines.append((f'wardrobe:{timeline_id}:{category}', f"- {LABELS[category]}: {'; '.join(shown)}."))
    since = (day - timedelta(days=RECENT_DAYS)).isoformat()
    for row in many(connection, 'SELECT * FROM wardrobe_log WHERE timeline_id=? AND local_date>? AND local_date<=? '
                    'ORDER BY local_date', (timeline_id, since, day.isoformat())):
        lines.append((row['id'], f"- Recently ({row['local_date']}): you {row['text']}."))
    return lines


# --- For other modules (money) ---

def purchases(connection, timeline_id: str, start: date, end: date) -> list[dict]:
    """Clothes bought between two local dates inclusive: {date, kind, text, spend, for}."""
    rows = many(connection, "SELECT * FROM wardrobe_log WHERE timeline_id=? AND spend!='' AND local_date>=? "
                'AND local_date<=? ORDER BY local_date', (timeline_id, start.isoformat(), end.isoformat()))
    return [{'date': row['local_date'], 'kind': row['kind'], 'text': row['text'], 'spend': row['spend'],
             'for': 'clothes'} for row in rows]


# --- View and edits ---

def today_for(version: dict, now) -> date:
    return now.astimezone(zone(version['timezone'])).date()


def view(connection, timeline_id: str, day: date, now, include_removed=False) -> dict:
    items = items_on(connection, timeline_id, day)
    state = one(connection, 'SELECT * FROM wardrobe_state WHERE timeline_id=?', (timeline_id,))
    found = decode(state['profile'])
    removed = []
    if include_removed:
        removed = [item_view(row) for row in many(
            connection, 'SELECT * FROM wardrobe_items WHERE timeline_id=? AND until IS NOT NULL AND until<=? '
            'ORDER BY until DESC', (timeline_id, day.isoformat()))]
    since = (day - timedelta(days=60)).isoformat()
    changes = many(connection, 'SELECT local_date, kind, text FROM wardrobe_log WHERE timeline_id=? AND local_date>? '
                   'AND local_date<=? ORDER BY local_date DESC', (timeline_id, since, day.isoformat()))
    moment = current_moment(connection, timeline_id, now)
    wearing = None
    if moment:
        occasion = occasion_for(moment['activity'], moment['block_kind'])
        worn = outfit(items, occasion, f"{state['seed']}:{moment['local_date']}:{occasion}", moment['weather'],
                      found.get('code', 'casual'))
        wearing = {'occasion': occasion, 'label': OCCASION_WORDS[occasion], 'text': phrase(worn),
                   'items': [item['id'] for item in worn]} if worn else None
    return {'today': day.isoformat(), 'items': items, 'removed': removed, 'changes': changes, 'wearing': wearing,
            'profile': {'styles': [STYLE_NAMES.get(style, style) for style in found['styles']],
                        'size': found['size'], 'count': len(items), 'tier': found['tier'],
                        'spending': found['spending'], 'work': CODES[found['code']][0] if found.get('career') and
                        found['era'] == 'modern' else None, 'career': found.get('career') or None,
                        'summary': summary_text(found, len(items), 'they')},
            'categories': list(CATEGORIES), 'labels': LABELS}


def item(connection, timeline_id: str, item_id: str) -> dict:
    row = optional(connection, 'SELECT * FROM wardrobe_items WHERE id=? AND timeline_id=?', (item_id, timeline_id))
    require(row is not None, 'That piece is not in their wardrobe.', 404)
    return row


def edit(connection, timeline_id: str, item_id: str, change: dict, day: date, now):
    """Rename or redescribe a piece, move it to another category, or mark it a favourite."""
    row = item(connection, timeline_id, item_id)
    details = decode(row['details'])
    category = change.get('category') or row['category']
    require(category in CATEGORIES, 'Pick one of the listed kinds of clothing.', 422)
    if change.get('description') is not None:
        details['description'] = change['description']
    if change.get('favorite') is not None:
        details['signature'] = bool(change['favorite'])
    if category != row['category']:
        details['occasions'] = DEFAULT_OCCASIONS[category]
        details.pop('slot', None)
    connection.execute('UPDATE wardrobe_items SET name=?, category=?, details=?, edited=1, revision=revision+1, '
                       'updated_at=? WHERE id=?', (change.get('name') or row['name'], category, encode(details),
                                                   stamp(now), item_id))
    rebuild(connection, timeline_id, day, now)


def add(connection, timeline_id: str, body: dict, day: date, now) -> str:
    require(body['category'] in CATEGORIES, 'Pick one of the listed kinds of clothing.', 422)
    details = {'occasions': DEFAULT_OCCASIONS[body['category']], 'signature': bool(body.get('favorite')),
               'description': body.get('description') or ''}
    if body['category'] == 'work':
        details['slot'] = 'set'
    item_id = insert_item(connection, timeline_id, {'category': body['category'], 'name': body['name'],
                                                    'variety': body['name'], 'details': details}, 'user', day, now)
    connection.execute('UPDATE wardrobe_items SET edited=1 WHERE id=?', (item_id,))
    rebuild(connection, timeline_id, day, now)
    return item_id


def set_removed(connection, timeline_id: str, item_id: str, removed: bool, day: date, now):
    item(connection, timeline_id, item_id)
    connection.execute('UPDATE wardrobe_items SET until=?, edited=1, revision=revision+1, updated_at=? WHERE id=?',
                       (day.isoformat() if removed else None, stamp(now), item_id))
    rebuild(connection, timeline_id, day, now)


def rebuild(connection, timeline_id: str, day: date, now):
    """After an edit: forget seeded changes still ahead (drawn from the old wardrobe) and the upcoming
    agenda entries that mention one, so both are drawn again from what is there now."""
    for row in many(connection, 'SELECT * FROM wardrobe_log WHERE timeline_id=? AND local_date>?',
                    (timeline_id, day.isoformat())):
        connection.execute('UPDATE wardrobe_items SET until=NULL WHERE timeline_id=? AND until=? AND origin!=?',
                           (timeline_id, row['local_date'], 'user'))
    connection.execute("DELETE FROM wardrobe_items WHERE timeline_id=? AND origin='change' AND since>?",
                       (timeline_id, day.isoformat()))
    connection.execute('DELETE FROM wardrobe_log WHERE timeline_id=? AND local_date>?', (timeline_id, day.isoformat()))
    state = one(connection, 'SELECT * FROM wardrobe_state WHERE timeline_id=?', (timeline_id,))
    elapsed = (day - date.fromisoformat(state['started'])).days
    connection.execute('UPDATE wardrobe_state SET next_period=MIN(next_period, ?) WHERE timeline_id=?',
                       (max(1, elapsed // PERIOD_DAYS), timeline_id))
    removed = connection.execute(
        "DELETE FROM life_agenda WHERE timeline_id=? AND subject=? AND status='upcoming' "
        "AND json_extract(entry, '$.wardrobe') IS NOT NULL", (timeline_id, COMPANION)).rowcount
    if removed:
        connection.execute('UPDATE agenda_cursors SET through=MIN(through, ?) WHERE timeline_id=? AND subject=?',
                           (stamp(now), timeline_id, COMPANION))


# --- Timelines ---

def copy(connection, parent_id: str, new_id: str, cutoff: str, ids: dict):
    """A fork keeps the wardrobe as it was at the fork point; what changes after that is drawn again."""
    state = optional(connection, 'SELECT * FROM wardrobe_state WHERE timeline_id=?', (parent_id,))
    if not state:
        return
    day = cutoff[:10]
    rows = many(connection, 'SELECT * FROM wardrobe_items WHERE timeline_id=? AND since<=?', (parent_id, day))
    logged = many(connection, 'SELECT * FROM wardrobe_log WHERE timeline_id=? AND local_date<=?', (parent_id, day))
    for row in [*logged, *rows]:
        ids[row['id']] = identifier()
    for row in rows:
        until = row['until'] if row['until'] and row['until'] <= day else None
        connection.execute(
            'INSERT INTO wardrobe_items (id, timeline_id, category, name, variety, details, origin, since, until, '
            'edited, revision, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (ids[row['id']], new_id, row['category'], row['name'], row['variety'], row['details'], row['origin'],
             row['since'], until, row['edited'], row['revision'], row['created_at'], row['updated_at']))
    for row in logged:
        connection.execute(
            'INSERT INTO wardrobe_log (id, timeline_id, period, local_date, kind, item_id, text, spend, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (ids[row['id']], new_id, row['period'], row['local_date'], row['kind'], ids.get(row['item_id']),
             row['text'], row['spend'], row['created_at']))
    elapsed = (date.fromisoformat(day) - date.fromisoformat(state['started'])).days
    connection.execute('INSERT INTO wardrobe_state (timeline_id, seed, started, profile, next_period, created_at, '
                       'updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (new_id, state['seed'], state['started'], state['profile'], max(1, elapsed // PERIOD_DAYS),
                        state['created_at'], cutoff))
