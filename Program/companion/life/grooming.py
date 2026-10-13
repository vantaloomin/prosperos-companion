"""Looks that change: a companion's hair grows and gets cut, nails get done and grow out, a tan comes and fades, and
every few months something bold happens (a new colour, a big cut, new glasses, a beard grown or shaved off).

Only looks the app filled in change (Vanta, 2026-10-12): a field the user wrote on the form, one their Appearance or
In photos line already speaks of, and anything they edited after a townsperson became a companion stay exactly as
written. A townsperson's looks copied at casting are recorded in `looks.drawn`, so they count as the app's until
the user changes them. Nothing here calls a model, and only companions are tracked.

Like the wardrobe (companion/life/wardrobe.py), changes are seeded per two-week period and logged once on the day
they happen, so evolving in steps or all at once gives the same history. Each period has four tracks: hair (a
trim, with a colour touch-up for dyed hair), nails, sun (a summer or sunny-trip tan) and bold. Gradual state is
worked out from dates when it is read: hair grows a length stage about every ten weeks and dyed hair shows its
roots after six, polish is gone after about two weeks and a tan fades over six. Haircuts, colour, salon nails and
glasses are spending (`purchases`) and appointments (`appointments`, for the Life admin calendar); the day one
happens it takes a free slot of their day as a salon visit, and a bold change is always made a life event, so it
reaches the feed and they mention it.

Settings > Realism sets how often (`life_settings.looks_realism`: 0 never, 1 now and then, 2 like real life,
3 often); never also hides changes already made. A companion pictured with a LoRA gets gradual changes only, since
the LoRA holds their face and hair, and the Codex reference sheet follows bold changes only (`sheet`), so it is
remade after a bold change but not after every trim.
"""
import functools
import json
import re
from datetime import date, timedelta

from companion.clock import parse, stamp, zone
from companion.database import decode, encode, identifier, many, one, optional
from companion.errors import require
from companion.life import circle, composer, money, pronouns
from companion.world import catalog, generators, looks

COMPANION = 'companion'
PERIOD_DAYS = 14
RECENT_DAYS = 60
TRACKS = ('hair', 'nails', 'sun', 'bold')
FIELDS = ('hair', 'facial_hair', 'skin', 'feature', 'nails')
MODERN = {'modern', 'future'}
# Hair length stages, shortest first; a cut in the bank names its stage.
LENGTHS = ('shaved', 'buzzed', 'cropped', 'short', 'ear-length', 'chin-length', 'shoulder-length',
           'past the shoulders', 'long', 'very long')
GROW_DAYS = 75
# How long someone growing their hair out skips trims.
GROWING_DAYS = 180
FRESH_DAYS = 8
ROOTS_DAYS = 42
POLISH_DAYS = 16
TAN_DAYS = (21, 42)
WARM_F = 75
# Skins a tan shows on, from the looks bank.
TANNING = {'very fair', 'fair', 'light', 'light olive', 'olive', 'warm beige', 'tan', 'warm tan'}
TAN_WORDS = {1: 'a light summer tan', 2: 'a deep summer tan'}
# How often, by the Realism setting: (share of a due change that happens, days between bold changes).
LEVELS = {1: (0.5, 2.0), 2: (1.0, 1.0), 3: (1.4, 0.6)}
LEVEL_NAMES = {0: 'Never', 1: 'Now and then', 2: 'Like real life', 3: 'Often'}
# What each drawn hair style (companion/world/dating.HAIR_STYLES) is: (length stage, texture, cut, how it is worn).
STYLES = {
    'long': (8, '', '', ''), 'shoulder-length': (6, '', '', ''), 'in a bob': (5, '', 'a bob', ''),
    'cropped short': (2, '', '', ''), 'curly': (6, 'curly', '', ''), 'always up in a bun': (8, '', '', 'always up in a bun'),
    'in a ponytail': (7, '', '', 'in a ponytail'), 'wavy': (6, 'wavy', '', ''), 'short': (3, '', '', ''),
    'cropped': (2, '', '', ''), 'buzzed': (1, '', '', ''), 'a little messy': (3, '', '', 'a little messy'),
    'longish': (4, '', '', ''), 'neatly parted': (3, '', '', 'neatly parted'), 'shaved at the sides': (3, '', '', 'shaved at the sides'),
}
WHO = {'she/her': 'f', 'he/him': 'm', 'they/them': 'n'}
APPOINTMENTS = {'trim': 'Haircut', 'touch-up': 'Haircut and color', 'colour': 'Hair color', 'cut': 'Haircut',
                'nails': 'Nails', 'glasses': 'New glasses'}
# Free time a salon visit can take the place of; plans, work, occasions and anything with someone else stay.
KEPT_ACTIVITIES = {'birthday', 'own-birthday', 'festival', 'tradition', 'gathering', 'sick-day'}
OPEN_BLOCKS = {'errand', 'leisure', 'rest'}
WORKING = {'steady-shift', 'busy-shift', 'library', 'study-cafe', 'lunch-out'}
PICTURE_ACTIVITY = {'nails': 'nail-salon'}
# Tests turn weaving into the day off.
WEAVE = True


@functools.lru_cache(maxsize=1)
def bank() -> dict:
    return json.loads((catalog.DATA / 'grooming.json').read_text(encoding='utf-8'))


# --- What may change ---

def user_text(definition: dict) -> str:
    return ' '.join(str(definition.get(key) or '') for key in ('appearance', 'in_photos'))


def editable(definition: dict) -> set[str]:
    """The looks fields the app filled in, so they may change: not one the user set on the form (a townsperson's
    copied value counts as the app's until edited), nor one Appearance or the In photos line speaks of."""
    own = looks.written(definition)
    drawn = (definition.get('looks') or {}).get('drawn') or {}
    user = {field for field, value in own.items() if drawn.get(field) != value}
    text = user_text(definition)
    fields = set(FIELDS) - user - looks.covered(text)
    if re.search(r'\b(?:nails?|manicure|polish)\b', text, re.IGNORECASE):
        fields.discard('nails')
    if re.search(r'\b(?:tan|suntan|sun-?kissed|sunburnt|sunburned)\b', text, re.IGNORECASE):
        fields.discard('skin')  # "a deep tan" they wrote stays; no summer tan comes and fades over it.
    return fields


def parse_hair(text: str, seed: str) -> dict | None:
    """The drawn hair line as parts: 'shoulder-length wavy...' or 'dark brown hair, in a bob'. None for hair that does
    not grow back or change here (a shaved head, thinning hair, a receding hairline) or a line not drawn by the app."""
    text = (text or '').strip()
    if not text.endswith('hair') and ', ' not in text or text in ('thinning hair', 'a shaved head'):
        return None
    if ', ' in text:
        colour, style = text.split(', ', 1)
        colour = colour.removesuffix(' hair')
    else:
        style = next((style for style in STYLES if text.startswith(f'{style} ')), None)
        if style is None:
            return None
        colour = text[len(style) + 1:].removesuffix(' hair')
    if style not in STYLES:
        return None
    length, texture, cut, worn = STYLES[style]
    if texture and style in ('curly', 'wavy'):
        length = 5 + int(generators.unit(seed, 'hair-length') * 4)
    return {'colour': colour, 'texture': texture, 'length': length, 'cut': cut, 'worn': worn}


# --- Who they are ---

def city_months(data: dict | None) -> list[int]:
    months = ((data or {}).get('climate') or {}).get('months') or []
    warm = [number for number, month in enumerate(months, 1) if month.get('high_f', 0) >= WARM_F]
    return warm if months else [6, 7, 8]


def words_hit(definition: dict, words: tuple[str, ...]) -> int:
    text = ' '.join(str(definition.get(key) or '') for key in ('identity', 'personality', 'appearance'))
    text += ' ' + ' '.join(definition.get('interests') or ())
    return sum(bool(re.search(rf'\b{word}', text, re.IGNORECASE)) for word in words)


OUTDOORSY = ('outdoor', 'hik', 'surf', 'beach', 'garden', 'run', 'cycl', 'sail', 'climb', 'swim', 'farm', 'tennis')
DARING = ('edgy', 'punk', 'artist', 'artsy', 'goth', 'bold', 'colorful', 'colourful', 'rebel', 'musician', 'tattoo',
          'fashion', 'stylist', 'spontaneous', 'restless')
POLISHED = ('glamor', 'glamour', 'polished', 'put-together', 'fashion', 'makeup', 'beauty', 'manicure', 'nail', 'stylish')


def profile(seed: str, definition: dict, data: dict | None) -> dict:
    """Their habits: the same for the same seed, description and city."""
    who = WHO[looks.pronouns_of(definition)]
    budget = money.profile(definition)
    tier = budget.tier if budget else money.DEFAULT_TIER
    era = 'modern' if not data or data.get('era') in MODERN else data['era']
    nail_odds = {'f': 0.65, 'n': 0.35, 'm': 0.07}[who] + 0.15 * words_hit(definition, POLISHED)
    roll = generators.unit(seed, 'nails')
    nails = 0 if era not in MODERN or roll >= min(nail_odds, 0.95) else 2 if roll < nail_odds * 0.45 else 1
    sun = min(2, words_hit(definition, OUTDOORSY) + (generators.unit(seed, 'sun') < 0.4))
    trim = {'f': (42, 84), 'n': (35, 70), 'm': (21, 42)}[who]
    return {'who': who, 'tier': tier, 'era': era, 'nails': nails, 'sun': sun,
            'trim_days': trim[0] + round(generators.unit(seed, 'trim-days') * (trim[1] - trim[0])),
            'bold_days': 90 + round(generators.unit(seed, 'bold-days') * 90),
            'daring': min(2, words_hit(definition, DARING)), 'warm_months': city_months(data),
            'first_cut': round(generators.unit(seed, 'first-cut') * trim[0])}


# --- State ---

def started_on(connection, timeline_id, timezone: str | None) -> date:
    row = one(connection, 'SELECT created_at FROM timelines WHERE id=?', (timeline_id,))
    return parse(row['created_at']).astimezone(zone(timezone or 'UTC')).date()


def ensure(connection, timeline_id: str, definition: dict, world, now) -> dict:
    state = optional(connection, 'SELECT * FROM grooming_state WHERE timeline_id=?', (timeline_id,))
    if state:
        return state
    seed, start = f'grooming:{timeline_id}', started_on(connection, timeline_id, definition.get('timezone'))
    found = profile(seed, definition, circle.city_data(definition, world))
    connection.execute('INSERT INTO grooming_state (timeline_id, seed, started, profile, next_period, kept, created_at, '
                       'updated_at) VALUES (?, ?, ?, ?, 0, 0, ?, ?)',
                       (timeline_id, seed, start.isoformat(), encode(found), stamp(now), stamp(now)))
    return one(connection, 'SELECT * FROM grooming_state WHERE timeline_id=?', (timeline_id,))


def level(connection) -> int:
    row = optional(connection, 'SELECT looks_realism FROM life_settings WHERE id=1')
    return 2 if row is None else int(row['looks_realism'])


def logs(connection, timeline_id: str, through: date) -> list[dict]:
    return many(connection, 'SELECT * FROM grooming_log WHERE timeline_id=? AND local_date<=? ORDER BY local_date, '
                'created_at', (timeline_id, through.isoformat()))


def fold(state: dict, rows: list[dict]) -> dict:
    """What the logged changes add up to: the hair's cut and colour, nails, tan, glasses and facial hair, with the day
    of each, starting from the seeded day of their last cut before the timeline began."""
    found = decode(state['profile'])
    start = date.fromisoformat(state['started'])
    result = {'cut_on': start - timedelta(days=found['first_cut']), 'bold_on': start}
    for row in rows:
        day, change = date.fromisoformat(row['local_date']), decode(row['change'])
        for key, value in change.items():
            result[key] = value
            result[f'{key}_on'] = day
        if row['kind'] in ('trim', 'touch-up', 'cut'):
            result['cut_on'] = day
        if row['bold']:
            result['bold_on'] = day
    return result


# --- Slow change ---

def change_day(state: dict, period: int, track: str) -> date:
    start = date.fromisoformat(state['started']) + timedelta(days=PERIOD_DAYS * period)
    return start + timedelta(days=int(generators.unit(state['seed'], 'day', track, period) * PERIOD_DAYS))


def companion_of(connection, timeline_id: str) -> str:
    return one(connection, 'SELECT companion_id FROM timelines WHERE id=?', (timeline_id,))['companion_id']


def busy(connection, companion: dict, day: date) -> bool:
    """A plan with the user, a trip or a family tradition that day: an appointment waits for another day."""
    from companion.life import outings
    return outings.taken(connection, companion, day)


def free_day(connection, companion: dict, day: date) -> date:
    for offset in range(4):
        if not busy(connection, companion, day + timedelta(days=offset)):
            return day + timedelta(days=offset)
    return day


def lora_pictured(connection, companion_id: str) -> bool:
    from companion.lora.appearance import current_version
    return current_version(connection, companion_id)['method'] == 'lora'


def evolve(connection, timeline_id: str, definition: dict, through: date, now) -> int:
    """Apply the seeded changes due on or before `through`, once each. With looks set never to change, or kept as
    they are, periods pass with nothing drawn, so turning changes back on never brings a flurry of old ones."""
    state = one(connection, 'SELECT * FROM grooming_state WHERE timeline_id=?', (timeline_id,))
    setting, applied, period, draw = level(connection), 0, state['next_period'], None
    while date.fromisoformat(state['started']) + timedelta(days=PERIOD_DAYS * period) <= through:
        if setting and not state['kept']:
            draw = draw or Draw(connection, state, definition, setting, now)
            # In the order of their days, so a track sees what the others did earlier in the period.
            ordered = sorted(TRACKS, key=lambda track: (change_day(state, period, track), track))
            applied += sum(draw.track(period, track, through) for track in ordered)
        if max(change_day(state, period, track) for track in TRACKS) > through:
            break  # Some of this period is still ahead: it is looked at again next time.
        period += 1
    connection.execute('UPDATE grooming_state SET next_period=?, updated_at=? WHERE timeline_id=?',
                       (period, stamp(now), timeline_id))
    return applied


class Draw:
    """The seeded draws of one evolve: what each track does in a period, given everything logged before its day."""

    def __init__(self, connection, state, definition, setting, now):
        self.connection, self.state, self.definition, self.now = connection, state, definition, now
        self.found = decode(state['profile'])
        self.share, self.spacing = LEVELS[setting]
        self.setting = setting
        self.timeline_id = state['timeline_id']
        self.companion_id = companion_of(connection, self.timeline_id)
        self.sheet = looks.for_companion(self.companion_id, definition)
        self.fields = editable(definition)
        self.parsed = parse_hair(self.sheet.get('hair') or '', state['seed']) if 'hair' in self.fields else None
        self.lora = lora_pictured(connection, self.companion_id)

    def companion(self) -> dict:
        from companion.characters import by_id
        return by_id(self.connection, self.companion_id)

    def track(self, period: int, track: str, through: date) -> int:
        day = change_day(self.state, period, track)
        if day > through or optional(self.connection, 'SELECT id FROM grooming_log WHERE timeline_id=? AND period=? '
                                     'AND track=?', (self.timeline_id, period, track)):
            return 0
        seed = f"{self.state['seed']}:{period}:{track}"
        so_far = fold(self.state, logs(self.connection, self.timeline_id, day - timedelta(days=1)))
        made = getattr(self, track)(seed, day, so_far, period)
        if not made:
            return 0
        if made.get('spend') and not self.affordable(made['spend'], day):
            return 0
        if made['kind'] in APPOINTMENTS:
            day = free_day(self.connection, self.companion(), day)
        self.connection.execute(
            'INSERT INTO grooming_log (id, timeline_id, period, track, local_date, kind, change, text, spend, bold, '
            'created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (identifier(), self.timeline_id, period, track, day.isoformat(), made['kind'], encode(made['change']),
             made['text'], made.get('spend', ''), int(track == 'bold'), stamp(self.now)))
        return 1

    def affordable(self, spend: str, day: date) -> bool:
        budget = money.profile(self.definition)
        return not budget or money.left_on(budget, day) >= money.PURCHASES[spend] * money.monthly_share(budget)

    def price(self, low: str, high: str) -> str:
        return high if self.found['tier'] >= 3 else low

    def hair(self, seed, day, so_far, period):
        if not self.parsed:
            return None
        since = (day - so_far['cut_on']).days
        if since < self.found['trim_days'] or generators.unit(seed, 'go') >= min(1.0, 0.85 * self.share):
            return None
        place = 'the barber' if self.found['who'] == 'm' else 'the salon'
        if so_far.get('growing'):
            if (day - so_far['growing_on']).days < GROWING_DAYS:
                return None
            return {'kind': 'trim', 'change': {'length': length_now(self.parsed, so_far, day), 'growing': False},
                    'spend': self.price('$', '$$'), 'text': f'had the grown-out hair tidied up at {place}'}
        if so_far.get('colour') and (day - so_far['colour_on']).days >= ROOTS_DAYS:
            colour = so_far['colour']
            return {'kind': 'touch-up', 'change': {'colour': colour}, 'spend': self.price('$$', '$$$'),
                    'text': f'got a trim and had the {colour} color touched up at {place}'}
        return {'kind': 'trim', 'change': {}, 'spend': self.price('$', '$$'), 'text': f'got a trim at {place}'}

    def nails(self, seed, day, so_far, period):
        habit = self.found['nails']
        if 'nails' not in self.fields or not habit:
            return None
        if so_far.get('nails') and (day - so_far['nails_on']).days < POLISH_DAYS - 4:
            return None
        if generators.unit(seed, 'go') >= (0.8 if habit == 2 else 0.35) * self.share:
            return None
        style = generators.pick(seed, 'look', bank()['nails'])
        salon = habit == 2 and self.found['tier'] >= 1
        text = f"had {pronouns.their(self.definition)} nails done: {style}" if salon else \
            f"painted {pronouns.their(self.definition)} nails at home: {style}"
        return {'kind': 'nails' if salon else 'nails-home', 'change': {'nails': style}, 'spend': '$' if salon else '',
                'text': text}

    def sun(self, seed, day, so_far, period):
        if 'skin' not in self.fields or (self.sheet.get('skin') or '') not in TANNING:
            return None
        trip = self.sunny_trip(day)
        if trip:
            return {'kind': 'tan', 'change': {'tan': 2}, 'text': f"came back from {trip} with a tan"}
        if day.month not in self.found['warm_months'] or not self.found['sun']:
            return None
        if generators.unit(seed, 'go') >= 0.35 * self.found['sun'] * self.share:
            return None
        deep = self.found['sun'] == 2 and generators.unit(seed, 'deep') < 0.5
        return {'kind': 'tan', 'change': {'tan': 2 if deep else 1},
                'text': 'has caught a deep tan from all the time outside' if deep else 'has caught a little sun'}

    def sunny_trip(self, day: date) -> str | None:
        row = optional(self.connection, "SELECT city_name FROM trips WHERE timeline_id=? AND status='planned' AND "
                       'sunny=1 AND end_date<=? AND end_date>?', (self.timeline_id, day.isoformat(),
                                                                  (day - timedelta(days=PERIOD_DAYS)).isoformat()))
        return row['city_name'] if row else None

    def bold(self, seed, day, so_far, period):
        if self.lora or (day - so_far['bold_on']).days < self.found['bold_days'] * self.spacing:
            return None
        if generators.unit(seed, 'go') >= 0.5 * min(self.share, 1.0):
            return None
        options = [(kind, weight) for kind, weight in self.bold_options(so_far, day) if weight]
        kind = generators.pick(seed, 'kind', [kind for kind, _ in options], [weight for _, weight in options])
        return kind and BOLD[kind](self, seed, day, so_far)

    def bold_options(self, so_far, day) -> list[tuple[str, float]]:
        modern, hair = self.found['era'] in MODERN, bool(self.parsed)
        grow = hair and not so_far.get('growing') and length_now(self.parsed, so_far, day) < 7
        wears = bool(so_far.get('glasses')) or 'glasses' in (self.sheet.get('feature') or '')
        age = self.sheet.get('age') or 30
        beard = self.found['who'] == 'm' or self.found['who'] == 'n' and bool(self.sheet.get('facial_hair'))
        return [('colour', 3.0 + self.found['daring'] if modern and hair else 0), ('cut', 3.0 if hair else 0),
                ('glasses', (2.0 if wears else 0.5 if age >= 40 else 0) if 'feature' in self.fields else 0),
                ('beard', 1.5 if beard and 'facial_hair' in self.fields else 0), ('grow', 1.5 if grow else 0)]

    def colour(self, seed, day, so_far):
        tones = ('mild',) if self.setting == 1 else ('mild', 'bold')
        current = so_far.get('colour') or so_far.get('highlights') or so_far.get('over')
        choices = [entry for entry in bank()['colours'] if entry['tone'] in tones and entry['text'] != current]
        weights = [1.0 + (self.found['daring'] if entry['tone'] == 'bold' else 0) for entry in choices]
        entry = generators.pick(seed, 'colour', choices, weights)
        change = {'colour': None, 'highlights': None, 'over': None, entry['kind']: entry['text']}
        said = {'colour': f"dyed {pronouns.their(self.definition)} hair {entry['text']}",
                'highlights': f"got {entry['text']} put in at the salon",
                'over': f"had {pronouns.their(self.definition)} hair {entry['text']}"}[entry['kind']]
        return {'kind': 'colour', 'change': change, 'spend': self.price('$$', '$$$'), 'text': said}

    def cut(self, seed, day, so_far):
        """A cut a salon can give hair this long: much shorter, a new style at about the same length, or braids,
        twists or locs, which can add length."""
        length = length_now(self.parsed, so_far, day)
        era = 'modern' if self.found['era'] in MODERN else 'any'
        current = (so_far.get('cut') or {}).get('text')

        def fits(entry):
            added = re.search(r'\b(?:braids?|twists|locs)\b', entry['text'])
            return entry['length'] <= length - 2 or abs(entry['length'] - length) <= 1 or added
        choices = [entry for entry in bank()['cuts'] if entry['who'] in (self.found['who'], 'any') and
                   (era == 'modern' or entry.get('era') == 'any') and entry['text'] != current and fits(entry)]
        entry = generators.pick(seed, 'cut', choices)
        if entry is None:
            return None
        their = pronouns.their(self.definition)
        text = f"had {their} hair put in {entry['text']}" if re.search(r'\b(?:braids?|twists|locs)\b', entry['text']) \
            else f"had {their} hair cut into {entry['text']}" if entry['length'] < length \
            else f"had {their} hair restyled into {entry['text']}"
        return {'kind': 'cut', 'change': {'cut': {'text': entry['text'], 'length': entry['length']}},
                'spend': self.price('$$', '$$$'), 'text': text}

    def grow(self, seed, day, so_far):
        return {'kind': 'grow', 'change': {'cut': None, 'length': length_now(self.parsed, so_far, day), 'growing': True},
                'text': f'decided to grow {pronouns.their(self.definition)} hair out'}

    def glasses(self, seed, day, so_far):
        era = self.found['era'] in MODERN
        frames = [frame for frame in bank()['frames'] if era or 'spectacles' in frame]
        frame = generators.pick(seed, 'frames', [frame for frame in frames if frame != so_far.get('glasses')])
        wears = so_far.get('glasses') or 'glasses' in (self.sheet.get('feature') or '')
        return {'kind': 'glasses', 'change': {'glasses': frame}, 'spend': self.price('$$$', '$$$$'),
                'text': f'picked out new glasses: {frame}' if wears else f'started wearing glasses: {frame}'}

    def beard(self, seed, day, so_far):
        has = so_far.get('facial_hair', self.sheet.get('facial_hair') or '')
        if has and has != 'a clean-shaven face' and generators.unit(seed, 'shave') < 0.5:
            return {'kind': 'shave', 'change': {'facial_hair': 'a clean-shaven face'}, 'text': 'shaved off the beard'}
        style = generators.pick(seed, 'beard', [beard for beard in bank()['beards'] if beard != has])
        return {'kind': 'beard', 'change': {'facial_hair': style}, 'text': f'has been growing {style}'}


BOLD = {'colour': Draw.colour, 'cut': Draw.cut, 'glasses': Draw.glasses, 'beard': Draw.beard, 'grow': Draw.grow}


# --- Looks on a day ---

def hair_text(hair: dict, so_far: dict, day: date, trim_days: int, gradual: bool) -> str:
    """Their hair in words: its colour (dyed, with highlights or a two-tone look), cut and length, and with `gradual`
    how long since a cut and whether roots show."""
    colour = so_far.get('colour') or hair['colour']
    words = ' '.join(part for part in (hair['texture'], colour, 'hair') if part)
    cut = so_far.get('cut')
    since = (day - so_far['cut_on']).days
    grown = length_now(hair, so_far, day) - length_now(hair, so_far, so_far['cut_on']) if gradual else 0
    if cut and cut['length'] == 0:
        text = cut['text']
    elif cut and re.search(r'\bhair\b', cut['text']):
        text = re.sub(r'\bhair\b', words, cut['text'], count=1)
    elif cut:
        text = f"{words} in {cut['text']}"
    else:
        shape = {**hair, 'length': so_far['length'], 'cut': ''} if 'length' in so_far else hair
        text = with_length(words, length_now(hair, so_far, day) if gradual else shape['length'], {**shape, 'worn': ''})
    extras = [f"with {so_far['highlights']}" if so_far.get('highlights') else '', so_far.get('over') or '']
    if gradual and so_far.get('colour') and (day - so_far['colour_on']).days >= ROOTS_DAYS \
            and so_far['colour'] != hair['colour']:
        extras.append(f"{'and' if so_far.get('highlights') else 'with'} {hair['colour']} roots growing in")
    if gradual and cut and (grown or since > trim_days + 21):
        extras.append('grown out a little')
    text = ' '.join([text, *(extra for extra in extras if extra)])
    if hair['worn'] and not cut:
        text = f"{text}, {hair['worn']}"
    return f'freshly cut {text}' if gradual and since < FRESH_DAYS and not text.startswith('a ') else text


def length_now(hair: dict, so_far: dict, day: date) -> int:
    """The length stage their hair has grown to: a cut's or their usual length, plus a stage about every ten weeks
    since the last cut, up to two (four while they grow it out)."""
    cut = so_far.get('cut')
    base = cut['length'] if cut else so_far['length'] if 'length' in so_far else hair['length']
    grown = max(0, (day - so_far['cut_on']).days) // GROW_DAYS
    return min(len(LENGTHS) - 1, base + min(grown, 4 if so_far.get('growing') else 2))


def with_length(words: str, length: int, hair: dict) -> str:
    if hair['cut'] and length == hair['length']:
        text = f"{words}, in {hair['cut']}"
    elif LENGTHS[length] == 'past the shoulders':
        text = f'{words} past the shoulders'
    else:
        text = f'{LENGTHS[length]} {words}'
    return f"{text}, {hair['worn']}" if hair['worn'] else text


def tan_level(so_far: dict, day: date) -> int:
    if not so_far.get('tan'):
        return 0
    since = (day - so_far['tan_on']).days
    return so_far['tan'] if since < TAN_DAYS[0] else so_far['tan'] - 1 if since < TAN_DAYS[1] else 0


def changes_on(connection, timeline_id: str, definition: dict, sheet: dict, day: date, bold_only=False) -> dict:
    """What has changed on their sheet by this day, as sheet fields: hair, facial hair, glasses (`feature` when their
    feature is glasses), nails and tan. Empty before anything changed, with looks set never to change, or kept."""
    state = optional(connection, 'SELECT * FROM grooming_state WHERE timeline_id=?', (timeline_id,))
    if not state or state['kept'] or not level(connection):
        return {}
    rows = [row for row in logs(connection, timeline_id, day) if row['bold'] or not bold_only]
    so_far, found, fields = fold(state, rows), decode(state['profile']), editable(definition)
    result = {}
    hair = parse_hair(sheet.get('hair') or '', state['seed']) if 'hair' in fields else None
    if hair:  # The reference sheet keeps the length the pictures use, before any bold change too.
        result['hair'] = hair_text(hair, so_far, day, found['trim_days'], not bold_only)
    if so_far.get('facial_hair') and 'facial_hair' in fields:
        result['facial_hair'] = so_far['facial_hair']
    if so_far.get('glasses') and 'feature' in fields:
        key = 'feature' if (sheet.get('feature') or '') == 'glasses' else 'glasses'
        result[key] = so_far['glasses']
    if not bold_only and so_far.get('nails') and 'nails' in fields and (day - so_far['nails_on']).days < POLISH_DAYS:
        result['nails'] = so_far['nails']
    if not bold_only and 'skin' in fields and (tan := tan_level(so_far, day)):
        result['tan'] = TAN_WORDS[tan]
    return result


def timeline_of(connection, companion_id: str) -> str | None:
    row = optional(connection, 'SELECT active_timeline_id FROM companions WHERE id=?', (companion_id,))
    return row['active_timeline_id'] if row else None


def today_of(connection, timeline_id: str) -> date | None:
    """The latest day of their life that has happened, for a picture or prompt with no date of its own."""
    row = optional(connection, "SELECT MAX(local_date) AS day FROM life_agenda WHERE timeline_id=? AND subject=? AND "
                   "status='happened'", (timeline_id, COMPANION))
    return date.fromisoformat(row['day']) if row and row['day'] else None


def sheet(connection, companion_id: str, definition: dict, day: date | str | None = None, bold_only=False) -> dict:
    """Their looks sheet (companion/world/looks.for_companion) as it is on this local day: what the user wrote never
    changes; the rest follows their haircuts, nails, tan and bold changes. `bold_only` leaves out the gradual ones
    (the Codex reference sheet). Without a connection or a day it is the sheet as drawn."""
    base = looks.for_companion(companion_id, definition)
    timeline_id = timeline_of(connection, companion_id) if connection is not None else None
    if not timeline_id:
        return base
    day = date.fromisoformat(day) if isinstance(day, str) else day or today_of(connection, timeline_id)
    if day is None:
        return base
    return {**base, **changes_on(connection, timeline_id, definition, base, day, bold_only)}


# --- Their day ---

def touch(connection, timeline_id: str, subject: str, entry: dict | None, block: dict, local_date: str,
          definition: dict, world, now) -> dict | None:
    """The companion's agenda entry with a looks change that happens that day woven in, once: an appointment takes the
    place of free time as a salon visit (a bold one is always made a life event); the rest is a sentence added on."""
    if subject != COMPANION:
        return entry
    day = date.fromisoformat(local_date)
    ensure(connection, timeline_id, definition, world, now)
    evolve(connection, timeline_id, definition, day, now)
    if not WEAVE or (entry or {}).get('looks') or (entry or {}).get('activity') in WORKING:
        return entry
    change = untold(connection, timeline_id, day)
    if not change:
        return entry
    if change['kind'] in APPOINTMENTS and swappable(entry, block):
        return visit(change, entry, block, definition)
    if not entry or change['kind'] in APPOINTMENTS and entry.get('activity') == 'sick-day':
        return entry
    sentence = f"{definition['name']} {change['text']}."
    return {**entry, 'summary': f"{entry['summary'].rstrip()} {sentence[0].upper()}{sentence[1:]}",
            'looks': {'change': change['id'], 'bold': bool(change['bold']), 'sentence': sentence}}


def swappable(entry: dict | None, block: dict) -> bool:
    if block.get('kind') not in OPEN_BLOCKS:
        return False
    if entry is None:
        return True
    planned = any(entry.get(key) for key in ('outing', 'own_plan', 'trip', 'recommendation', 'with', 'hobby'))
    return not planned and entry.get('activity') not in KEPT_ACTIVITIES


def untold(connection, timeline_id: str, day: date) -> dict | None:
    for row in many(connection, 'SELECT * FROM grooming_log WHERE timeline_id=? AND local_date=? ORDER BY bold DESC',
                    (timeline_id, day.isoformat())):
        told = optional(connection, "SELECT id FROM life_agenda WHERE timeline_id=? AND subject=? "
                        "AND json_extract(entry, '$.looks.change')=?", (timeline_id, COMPANION, row['id']))
        if not told:
            return row
    return None


def visit(change: dict, entry: dict | None, block: dict, definition: dict) -> dict:
    """A salon (or barber, or optician) visit in place of a free slot, posted with a caption of its own."""
    kind = change['kind']
    summary = f"{definition['name']} {change['text']}."
    posts = (bank()['posts'].get(kind) or bank()['posts']['cut']) if change['bold'] else None
    post = generators.pick(change['id'], 'post', posts) if posts else summary
    return {'summary': summary[0].upper() + summary[1:], 'post': post, 'mood': 'pleased' if change['bold'] else 'relaxed',
            'activity': PICTURE_ACTIVITY.get(kind, 'salon'), 'place': None, 'with': None,
            'weather': (entry or {}).get('weather') or block.get('weather'), 'composer_version': composer.COMPOSER_VERSION,
            'looks': {'change': change['id'], 'bold': bool(change['bold']), 'sentence': summary}}


# --- For other modules ---

def purchases(connection, timeline_id: str, start: date, end: date) -> list[dict]:
    """Haircuts, colour, salon nails and glasses between two local dates inclusive, as money.household purchases."""
    rows = many(connection, "SELECT * FROM grooming_log WHERE timeline_id=? AND spend!='' AND local_date>=? AND "
                'local_date<=? ORDER BY local_date', (timeline_id, start.isoformat(), end.isoformat()))
    return [{'date': row['local_date'], 'kind': row['kind'], 'text': row['text'], 'spend': row['spend'],
             'for': 'looks'} for row in rows]


def appointments(connection, timeline_id: str, start: date, end: date) -> list[dict]:
    """Haircut, colour, nail and glasses appointments between two local dates inclusive, for the Life admin calendar:
    {date, kind, title, text, spend}. Read-only there: they follow the seeded draw and the Realism setting."""
    rows = many(connection, 'SELECT * FROM grooming_log WHERE timeline_id=? AND local_date>=? AND local_date<=? '
                'ORDER BY local_date', (timeline_id, start.isoformat(), end.isoformat()))
    return [{'date': row['local_date'], 'kind': row['kind'], 'title': APPOINTMENTS[row['kind']], 'text': row['text'],
             'spend': row['spend']} for row in rows if row['kind'] in APPOINTMENTS]


# --- View and edits ---

def view(connection, companion: dict, day: date, show_numbers=False) -> dict:
    """How they look lately, in words, for the Character page; the numbers behind it only with Hidden values on."""
    timeline_id, definition = companion['active_timeline_id'], companion['version']['definition']
    state = one(connection, 'SELECT * FROM grooming_state WHERE timeline_id=?', (timeline_id,))
    found, fields = decode(state['profile']), editable(definition)
    now_sheet = sheet(connection, companion['id'], definition, day)
    so_far = fold(state, logs(connection, timeline_id, day))
    changes = many(connection, 'SELECT local_date, kind, text, bold FROM grooming_log WHERE timeline_id=? AND '
                   'local_date>? AND local_date<=? ORDER BY local_date DESC',
                   (timeline_id, (day - timedelta(days=RECENT_DAYS)).isoformat(), day.isoformat()))
    setting = level(connection)
    active = setting and not state['kept']
    return {'today': day.isoformat(), 'kept': bool(state['kept']), 'level': setting, 'level_name': LEVEL_NAMES[setting],
            'lines': lines(now_sheet, fields, so_far, found, day) if active else [],
            'fixed': sorted(set(FIELDS) - fields), 'lora': lora_pictured(connection, companion['id']),
            'changes': [{**row, 'bold': bool(row['bold'])} for row in changes],
            'numbers': numbers(so_far, found, day) if show_numbers and active else None}


LABELS = {'hair': 'Hair', 'facial_hair': 'Facial hair', 'feature': 'Something people notice', 'skin': 'Skin',
          'nails': 'Nails'}


def lines(now_sheet: dict, fields: set[str], so_far: dict, found: dict, day: date) -> list[dict]:
    """[{label, text}] in plain words: their hair and how long since a cut, nails, tan, glasses and facial hair."""
    result = []
    if 'hair' in fields and now_sheet.get('hair'):
        weeks = (day - so_far['cut_on']).days // 7
        when = 'this week' if weeks < 1 else f"{weeks} week{'s' if weeks != 1 else ''} ago"
        result.append({'label': 'Hair', 'text': f"{sentence(now_sheet['hair'])}. Last cut {when}."})
    if 'nails' in fields and found['nails']:
        text = f"{sentence(now_sheet['nails'])}." if now_sheet.get('nails') else 'Bare right now.'
        result.append({'label': 'Nails', 'text': text})
    if now_sheet.get('tan'):
        result.append({'label': 'Skin', 'text': f"{sentence(now_sheet['tan'])}, fading over the next few weeks."})
    if glasses := now_sheet.get('glasses') or (so_far.get('glasses') and now_sheet.get('feature')):
        result.append({'label': 'Glasses', 'text': f'{sentence(glasses)}.'})
    if so_far.get('facial_hair') and 'facial_hair' in fields:
        result.append({'label': 'Facial hair', 'text': f"{sentence(so_far['facial_hair'])}."})
    return result


def sentence(text: str) -> str:
    return text[:1].upper() + text[1:]


def numbers(so_far: dict, found: dict, day: date) -> list[dict]:
    """The values behind the words, for Hidden values."""
    result = [{'label': 'Days since a haircut', 'value': f"{(day - so_far['cut_on']).days} (they go about every "
                                                        f"{found['trim_days']})"},
              {'label': 'Tan', 'value': f"{('none', 'light', 'deep')[tan_level(so_far, day)]} ({tan_level(so_far, day)} of 2)"},
              {'label': 'Nail habit', 'value': ('never painted', 'now and then', 'usually done')[found['nails']]}]
    next_bold = so_far['bold_on'] + timedelta(days=found['bold_days'])
    when = 'Any time now' if next_bold <= day else f'From {next_bold:%B} {next_bold.day}'
    result.append({'label': 'Next bold change', 'value': when})
    return result


def set_kept(connection, timeline_id: str, kept: bool, now):
    require(optional(connection, 'SELECT timeline_id FROM grooming_state WHERE timeline_id=?', (timeline_id,))
            is not None, 'Their looks are not set up yet.', 404)
    connection.execute('UPDATE grooming_state SET kept=?, updated_at=? WHERE timeline_id=?',
                       (int(kept), stamp(now), timeline_id))


# --- Timelines ---

def copy(connection, parent_id: str, new_id: str, cutoff: str, ids: dict):
    """A fork keeps the looks history up to the fork point; what changes after that is drawn again."""
    state = optional(connection, 'SELECT * FROM grooming_state WHERE timeline_id=?', (parent_id,))
    if not state:
        return
    day = cutoff[:10]
    for row in many(connection, 'SELECT * FROM grooming_log WHERE timeline_id=? AND local_date<=?', (parent_id, day)):
        ids[row['id']] = identifier()
        connection.execute(
            'INSERT INTO grooming_log (id, timeline_id, period, track, local_date, kind, change, text, spend, bold, '
            'created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (ids[row['id']], new_id, row['period'], row['track'], row['local_date'], row['kind'], row['change'],
             row['text'], row['spend'], row['bold'], row['created_at']))
    elapsed = (date.fromisoformat(day) - date.fromisoformat(state['started'])).days
    connection.execute('INSERT INTO grooming_state (timeline_id, seed, started, profile, next_period, kept, '
                       'created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                       (new_id, state['seed'], state['started'], state['profile'], max(0, elapsed // PERIOD_DAYS),
                        state['kept'], state['created_at'], cutoff))
