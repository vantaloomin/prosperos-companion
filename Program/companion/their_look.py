"""Their look in chat (Feature Hit List #80, v1.1): each companion's own colour and name font in their chat
(/mnt/project-files/companion-themes/findings.md).

The app gives every companion a taste, never asking: one colour family and one name font from
world/data/their_looks.json, scored from their personality sliders, their home city's era, words about their work and
their age, with a seeded nudge so two alike people still differ. The user can change either, keep it steady or use
their own colours for them on the Character page (`their_looks`), and Settings can turn it off.

How it moves (Settings > Realism > Their days, life_settings.their_look):
- 0 Off: the app's colours everywhere.
- 1 Steady: their own colour and font, and nothing moves.
- 2 True to life: the shade drifts within the family at visible life moments (a new season, their birthday), a mood
  of 2 or more moves the shade when Moods are shown, and now and then, about one season in six, their taste moves to
  another family that suits them.
- 3 Expressive: any mood moves the shade, and their taste changes about one season in three.
With Moods hidden (the default) a mood is only a fuzzy hint, the way you can read someone a little without being told
(Vanta, 2026-10-25): only a strong one, half the shift, a while after it starts, and about one in three never shows,
so the colour never reads out a hidden value. Mood moves the shade quietly, with no line, at most `MOOD_CHANGES` times
a day.

Each other change the app makes leaves one muted line in their chat ("Dana changed their colors."), kept in
`their_look_changes`; what the user changes leaves none. Only ids leave here: the chat works out the colours against its
own background (src/features/conversation/theirLook.ts), so the name always reads at 4.5:1 or more.
"""
import json
import random
import re
from datetime import date, timedelta
from functools import cache

from companion.clock import parse, stamp
from companion.database import identifier, many, optional, settings
from companion.errors import require
from companion.life import ages, families, storylines
from companion.world import catalog, perception

LEVELS = (0, 1, 2, 3)
USUAL = 2
# A change of taste, a season's chance, by level.
TASTE_CHANCE = {2: 1 / 6, 3: 1 / 3}
# The lowest mood intensity that moves the shade, by level.
MOOD_FROM = {2: 2, 3: 1}
MOOD_CHANGES = 2
# With Moods hidden a strong mood only hints: from this intensity, after this long, and one in HINT_SKIP never shows.
HINT_FROM = {2: 3, 3: 2}
HINT_LAG = timedelta(hours=2)
HINT_SKIP = 3
# Happy or excited is brighter and warmer, sad or hurt muted and cooler, annoyed or angry deeper, anxious paler.
MOOD_SHADES = {'happy': 'bright', 'excited': 'bright', 'sad': 'muted', 'hurt': 'muted', 'annoyed': 'deep',
               'angry': 'deep', 'anxious': 'pale'}
DRIFTS = 3
# Two members of one group never get hues closer than this; the later one is nudged.
NEAR_HUE = 24
# How far back a change of taste is looked for, in seasons.
SEASONS_BACK = 40
CHANGES_SHOWN = 30
JOB_FIELDS = ('identity', 'background', 'routine')


@cache
def bank() -> dict:
    return json.loads((catalog.DATA / 'their_looks.json').read_text(encoding='utf-8'))


def family_ids() -> tuple[str, ...]:
    return tuple(item['id'] for item in bank()['families'])


def font_ids() -> tuple[str, ...]:
    return tuple(item['id'] for item in bank()['fonts'])


def hue(family: str) -> int:
    return next(item['hue'] for item in bank()['families'] if item['id'] == family)


def label(family: str) -> str:
    return next(item['label'] for item in bank()['families'] if item['id'] == family)


# The taste the app picks ------------------------------------------------------------------------------------

def facts(connection, companion: dict, today: date) -> set[str]:
    """What a taste leans on: `trait:level` for each personality slider, the home city's era, and young or older."""
    definition, companion_id = companion['version']['definition'], companion['id']
    found = {f'{trait}:{level}' for trait, level in perception.sliders_of(definition, companion_id).items()}
    found.add(families.era_of(connection, definition))
    age = ages.companion_age(connection, companion_id, definition, today)
    if age is not None:
        found.add('young' if age < 30 else 'older' if age >= 55 else 'adult')
    return found


def score(item: dict, known: set[str], words: str) -> int:
    leans = item['leans']
    found = sum(weight for key, weight in leans.items() if key != 'jobs' and key in known)
    return found + 2 * any(re.search(rf'\b{pattern}', words) for pattern in leans.get('jobs', ()))


def ranked(kind: str, known: set[str], words: str, seed: str) -> list[str]:
    """A bank's ids best first: the leans, plus a seeded nudge under one point so a tie goes the companion's own way."""
    rolled = random.Random(f'{seed}:{kind}')
    scored = [(score(item, known, words) + rolled.random() * 0.9, item['id']) for item in bank()[kind]]
    return [item for _, item in sorted(scored, reverse=True)]


def taste(connection, companion: dict, today: date) -> dict:
    """Their seeded family (best first) and font. The same sheet always gives the same taste."""
    definition = companion['version']['definition']
    words = ' '.join(str(definition.get(field) or '') for field in JOB_FIELDS).casefold()
    known = facts(connection, companion, today)
    return {'families': ranked('families', known, words, companion['id']),
            'font': ranked('fonts', known, words, companion['id'])[0]}


# Seasons, drift and changes of taste --------------------------------------------------------------------------

def season(day: date) -> int:
    """A count of seasons: December starts the next year's winter."""
    return (day.year * 12 + day.month) // 3


def season_start(index: int) -> date:
    months = index * 3
    return date((months - 1) // 12, (months - 1) % 12 + 1, 1)


def family_for(companion: dict, picks: list[str], level: int, today: date) -> tuple[str, int]:
    """Their family this season, and the season it last changed (0 if it never has). Each season since they came along
    rolls once for a change of taste; a change moves to another of their four best."""
    chance = TASTE_CHANCE.get(level, 0)
    began = parse(companion.get('created_at'))
    first = max(season(began.date()) + 1 if began else season(today), season(today) - SEASONS_BACK)
    place, changed = 0, 0
    for index in range(first, season(today) + 1):
        rolled = random.Random(f"{companion['id']}:taste:{index}")
        if rolled.random() < chance:
            place, changed = (place + 1 + rolled.randrange(3)) % 4, index
    return picks[place], changed


def drift(companion: dict, today: date) -> int:
    """Which of the family's everyday shades: it moves with a new season and with their birthday, never in between."""
    birthday = ages.own_birthday(companion['id'], companion['version']['definition'])
    last = ages.last_birthday(birthday, today)
    return random.Random(f"{companion['id']}:drift:{season(today)}:{last.year}").randrange(DRIFTS)


# What the user set ----------------------------------------------------------------------------------------

def own(connection, companion_id: str) -> dict:
    row = optional(connection, 'SELECT * FROM their_looks WHERE companion_id=?', (companion_id,))
    return row or {'companion_id': companion_id, 'family': None, 'font': None, 'steady': 0, 'use_mine': 0,
                   'shown': None, 'mood_day': None, 'mood_changes': 0}


def level_of(connection) -> int:
    row = optional(connection, 'SELECT their_look FROM life_settings WHERE id=1')
    return row['their_look'] if row and row['their_look'] in LEVELS else USUAL


def everywhere_off(connection) -> bool:
    return bool(settings(connection).get('keep_my_colours'))


# The look now ----------------------------------------------------------------------------------------------

def mood_shade(connection, companion: dict, level: int, now) -> tuple[str | None, bool]:
    """The shade a mood moves to, and whether it is only a hint. With Moods shown, from the level's intensity. With
    them hidden (Vanta, 2026-10-25: you can read someone's mood a little without being told), a fuzzy hint: only a
    strong mood (HINT_FROM), half the shift (the chat halves it), once it has lasted HINT_LAG, and a seeded one in
    HINT_SKIP strong moods never shows at all."""
    if level < 2:
        return None, False
    from companion import moods
    key = f"companion:{companion['id']}"
    if settings(connection)['show_moods']:
        found = moods.current(connection, key, now)
        if not found or found['intensity'] < MOOD_FROM[level]:
            return None, False
        return MOOD_SHADES.get(found['feeling']), False
    row = optional(connection, 'SELECT * FROM moods WHERE holder=?', (key,))
    if (row is None or row['intensity'] < HINT_FROM[level] or moods.stored(connection, key, now) is None
            or now - parse(row['updated_at']) < HINT_LAG
            or random.Random(f"{key}:hint:{row['updated_at']}").randrange(HINT_SKIP) == 0):
        return None, False
    return MOOD_SHADES.get(row['feeling']), True


def worked_out(connection, companion: dict, now, with_mood: bool = True) -> dict | None:
    """Their look now ({family, font, shade, mood}), or None where the app's colours apply."""
    level, mine = level_of(connection), own(connection, companion['id'])
    if level == 0 or mine['use_mine'] or everywhere_off(connection):
        return None
    today = storylines.local_today(companion, now)
    picked = taste(connection, companion, today)
    moving = level >= 2 and not mine['steady']
    family = mine['family'] or (family_for(companion, picked['families'], level, today)[0] if moving
                                else picked['families'][0])
    mood, hint = mood_shade(connection, companion, level, now) if moving and with_mood else (None, False)
    return {'family': family, 'font': mine['font'] or picked['font'], 'shade': drift(companion, today) if moving else 0,
            'mood': mood, 'hint': hint and mood is not None, 'level': level}


def first_of(companion: dict) -> str:
    return companion['version']['name'].split()[0]


def change_text(companion: dict, before: dict, after: dict) -> str:
    name = first_of(companion)
    if before['family'] != after['family']:
        return f"{name} changed their colors to {label(after['family'])}."
    return f'{name} changed their colors.'


def settle(connection, companion: dict, now) -> dict | None:
    """The look now, after noting what changed since it was last shown: a change the app made leaves its line, except
    a mood's, which moves the shade quietly and at most MOOD_CHANGES times a day (past that it stays as it was)."""
    look = worked_out(connection, companion, now)
    mine = own(connection, companion['id'])
    shown = json.loads(mine['shown']) if mine['shown'] else None
    if look is None:
        if mine['shown']:
            keep(connection, companion['id'], now, shown=None)  # Coming back later starts quietly.
        return None
    today = storylines.local_today(companion, now).isoformat()
    used = mine['mood_changes'] if mine['mood_day'] == today else 0
    moodless = {**look, 'mood': None, 'hint': False}
    mood_only = bool(shown) and moodless == {**shown, 'mood': None, 'hint': False}
    if mood_only and (look['mood'], look['hint']) != (shown.get('mood'), shown.get('hint', False)):
        if used >= MOOD_CHANGES:
            look = {**look, 'mood': shown.get('mood'), 'hint': shown.get('hint', False)}
        else:
            used += 1
    if shown == look:
        return look
    # The first look, one after the user moved the Realism slider, and a mood's are taken quietly.
    if shown is not None and shown.get('level') == look['level'] and not mood_only:
        connection.execute('INSERT INTO their_look_changes (id, companion_id, text, created_at) VALUES (?, ?, ?, ?)',
                           (identifier(), companion['id'], change_text(companion, shown, look), stamp(now)))
    keep(connection, companion['id'], now, shown=json.dumps(look, sort_keys=True), mood_day=today, mood_changes=used)
    return look


def keep(connection, companion_id: str, now, **values):
    """Writes the companion's row, making it the first time."""
    connection.execute('INSERT OR IGNORE INTO their_looks (companion_id, updated_at) VALUES (?, ?)', (companion_id, stamp(now)))
    columns = ', '.join(f'{key}=?' for key in values)
    connection.execute(f'UPDATE their_looks SET {columns}, updated_at=? WHERE companion_id=?',  # noqa: S608
                       (*values.values(), stamp(now), companion_id))


# Changes the user makes -------------------------------------------------------------------------------------

def change(connection, companion: dict, now, family: str | None = None, font: str | None = None,
           steady: bool | None = None, use_mine: bool | None = None) -> None:
    """The Character page's "Their look": '' hands a family or font back to the app. The look shown afterwards is
    taken as already seen, so the user's own change leaves no line in the chat."""
    values = {}
    if family is not None:
        require(family == '' or family in family_ids(), 'That color is not one of theirs to pick.', 422)
        values['family'] = family or None
    if font is not None:
        require(font == '' or font in font_ids(), 'That font is not one of theirs to pick.', 422)
        values['font'] = font or None
    if steady is not None:
        values['steady'] = int(steady)
    if use_mine is not None:
        values['use_mine'] = int(use_mine)
    if values:
        keep(connection, companion['id'], now, **values)
    look = worked_out(connection, companion, now)
    keep(connection, companion['id'], now, shown=json.dumps(look, sort_keys=True) if look else None)


# What the screens read --------------------------------------------------------------------------------------

def changes(connection, companion_id: str) -> list[dict]:
    rows = many(connection, 'SELECT text, created_at FROM their_look_changes WHERE companion_id=? '
                            'ORDER BY created_at DESC LIMIT ?', (companion_id, CHANGES_SHOWN))
    return [{'text': row['text'], 'at': row['created_at']} for row in reversed(rows)]


def view(connection, companion: dict, now) -> dict:
    """The chat's look and the Character page's section."""
    look = settle(connection, companion, now)
    mine = own(connection, companion['id'])
    today = storylines.local_today(companion, now)
    picked = taste(connection, companion, today)
    return {'level': level_of(connection), 'everywhere_off': everywhere_off(connection), 'look': look,
            'picked': {'family': picked['families'][0], 'font': picked['font']},
            'own': {'family': mine['family'], 'font': mine['font']}, 'steady': bool(mine['steady']),
            'use_mine': bool(mine['use_mine']), 'changes': changes(connection, companion['id'])}


def near(left: str, right: str) -> bool:
    distance = abs(hue(left) - hue(right)) % 360
    return min(distance, 360 - distance) < NEAR_HUE


def group(connection, companions: list[dict], now) -> dict[str, dict | None]:
    """Each member's look in a group chat, in the order given (who joined first keeps theirs): a member whose family is
    near one already taken moves to the next of their own picks that isn't, or keeps theirs when none is free. No mood:
    a group chat keeps the app's colours and only tints names."""
    found, taken = {}, []
    for companion in companions:
        look = worked_out(connection, companion, now, with_mood=False)
        if look is not None:
            picks = [look['family'], *taste(connection, companion, storylines.local_today(companion, now))['families']]
            look = {**look, 'family': next((family for family in picks if not any(near(family, other) for other in taken)),
                                           look['family'])}
            taken.append(look['family'])
        found[companion['id']] = look
    return found
