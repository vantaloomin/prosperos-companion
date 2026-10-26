"""Books, shows and songs that belong to a made-up world (companion/life/media.py).

The shared banks for made-up worlds (tales.json, future.json) are invented but generic: the same titles in Camelot,
Oz and a fan-made Runeterra. So a city can carry its own `media` block, and one that has none gets titles built
from the city itself: its quarters, places, notables, festivals, food and drink, and lore. Picks lean on the city's
own block first, then on built titles, then on the shared bank (media.options).

A `media` block is {credit, book, show, music}, each a list of [title, by, year, tags] as in the shared banks (or
{title, by, year, tags}); `clean` checks it when the city loads and drops a bad entry with a note. Built titles come
from fixed templates, seeded per city, with authors named from the city's own name bank: no model call. Cities in
our world (a real-titles bank) only use a block of their own.
"""
import re

from companion.world import catalog, generators

KINDS = ('book', 'show', 'music')
MAX_ITEMS = 300
MAX_TITLE = 120
MAX_BY = 80
# How many of a slot's values (a city's notables, say) one template is filled with.
PER_TEMPLATE = 5
SMALL = {'a', 'an', 'and', 'at', 'by', 'for', 'from', 'in', 'of', 'on', 'or', 'the', 'to', 'with'}
TAG = re.compile(r'[a-z][a-z0-9-]{0,24}')
SHOW_FORMATS = ('series', 'serial', 'film-serial', 'radio', 'play', 'broadway', 'cycle')

# (kind, slot, title, tags, by): by is 'person' (a name from the city's bank), 'company' (a troupe of the city),
# 'teller' (a storyteller of the city) or '' (no one in particular). {x} is the slot's value at the start of a
# title, {in} the same value inside one ("the Great Pit" rather than "The Great Pit") and {bare} the value with no
# "The" ("The Lantern Fair Song").
OLD_WORLD = (
    ('book', 'city', 'A History of {in}', 'history', 'person'),
    ('book', 'city', 'The Old Tales of {in}', 'folk family', ''),
    ('book', 'city', 'Proverbs and Sayings of {in}', 'humor folk', ''),
    ('book', 'city', 'Letters from {in}', 'romance', 'person'),
    ('book', 'city', 'Ghosts of {in}', 'horror folk', 'person'),
    ('book', 'city', 'A Traveller\'s Guide to {in}', 'travel', 'person'),
    ('book', 'hood', 'Death Comes to {in}', 'mystery', 'person'),
    ('book', 'hood', 'A Summer in {in}', 'romance', 'person'),
    ('book', 'hood', 'Growing Up in {in}', 'memoir family', 'person'),
    ('book', 'hood', 'Walks Through {in}', 'travel nature', 'person'),
    ('book', 'place', 'A Mystery at {in}', 'mystery', 'person'),
    ('book', 'place', 'The Keeper of {in}', 'literary', 'person'),
    ('book', 'notable', '{x}: A Life', 'biography history', 'person'),
    ('book', 'notable', 'The Deeds of {in}', 'adventure history', 'person'),
    ('book', 'lore', 'A True Account of {in}', 'history', 'person'),
    ('book', 'lore', 'Those Who Remember {in}', 'memoir history', 'person'),
    ('book', 'feast', 'A {bare} Romance', 'romance', 'person'),
    ('book', 'feast', 'Murder at {in}', 'mystery', 'person'),
    ('book', 'dish', 'The {bare} Cookbook', 'cooking', 'person'),
    ('book', 'arena', 'Blood and Sand at {in}', 'sports adventure', 'person'),
    ('show', 'city', 'The Merry Wives of {in}', 'play comedy', 'company'),
    ('show', 'city', 'Tales of Old {bare}', 'cycle folk', 'teller'),
    ('show', 'hood', 'The Mysteries of {in}', 'serial mystery', 'person'),
    ('show', 'hood', 'Lovers of {in}', 'play romance', 'company'),
    ('show', 'place', 'A Night at {in}', 'play comedy', 'company'),
    ('show', 'place', 'Whispers at {in}', 'serial thriller', 'person'),
    ('show', 'notable', 'The Rise of {in}', 'play drama history', 'company'),
    ('show', 'notable', 'The Adventures of {in}', 'serial adventure', 'person'),
    ('show', 'notable', 'Tales of {in}', 'cycle adventure', 'teller'),
    ('show', 'lore', '{x}', 'play drama history', 'company'),
    ('show', 'lore', 'Stories of {in}', 'cycle history', 'teller'),
    ('show', 'feast', 'The {bare} Revel', 'play comedy', 'company'),
    ('show', 'arena', 'Champions of {in}', 'serial sports', 'person'),
    ('music', 'city', 'Farewell to {in}', 'lament folk', ''),
    ('music', 'city', 'The Streets of {in}', 'folk', 'person'),
    ('music', 'hood', '{x} Lullaby', 'family folk', ''),
    ('music', 'hood', 'My Love in {in}', 'ballad love', 'person'),
    ('music', 'bells', 'The Bells of {in}', 'folk', ''),
    ('music', 'place', 'Down at {in}', 'dance folk', 'person'),
    ('music', 'tavern', 'Last Round at {in}', 'drinking humor', ''),
    ('music', 'notable', 'The Ballad of {in}', 'ballad adventure', 'person'),
    ('music', 'notable', 'A Song for {in}', 'ballad', 'person'),
    ('music', 'feast', 'The {bare} Song', 'dance folk', ''),
    ('music', 'feast', 'Dancing at {in}', 'dance', 'person'),
    ('music', 'drink', 'A Cup of {in}', 'drinking humor', ''),
    ('music', 'lore', 'Lament for {in}', 'lament history', 'person'),
)
WORLD_TO_COME = (
    ('book', 'city', 'A History of {in}', 'history', 'person'),
    ('book', 'city', 'Letters from {in}', 'romance', 'person'),
    ('book', 'hood', 'Death Comes to {in}', 'mystery', 'person'),
    ('book', 'hood', 'Growing Up in {in}', 'memoir family', 'person'),
    ('book', 'place', 'A Mystery at {in}', 'mystery', 'person'),
    ('book', 'notable', '{x}: A Life', 'biography', 'person'),
    ('book', 'lore', 'The Truth About {in}', 'history', 'person'),
    ('book', 'dish', 'Cooking {in}', 'cooking', 'person'),
    ('show', 'city', '{x} General', 'series medical drama', ''),
    ('show', 'city', 'Real Lives of {in}', 'series reality', ''),
    ('show', 'hood', '{x} Nights', 'series drama', ''),
    ('show', 'hood', 'The {bare} Precinct', 'series crime drama', ''),
    ('show', 'place', 'Behind the Doors of {in}', 'series documentary', ''),
    ('show', 'notable', 'The {bare} Story', 'series documentary biography', ''),
    ('show', 'lore', '{x}', 'series drama history', ''),
    ('show', 'feast', 'A Very {bare} Special', 'series comedy family', ''),
    ('music', 'city', 'Skyline of {in}', 'pop', 'person'),
    ('music', 'hood', '{x} After Dark', 'electronic dance', 'person'),
    ('music', 'hood', 'Back to {in}', 'indie', 'person'),
    ('music', 'place', 'Neon Over {in}', 'electronic', 'person'),
    ('music', 'notable', 'Ballad for {in}', 'ballad pop', 'person'),
    ('music', 'feast', '{x} Anthem', 'pop dance', 'person'),
    ('music', 'drink', '{x} on the Rocks', 'rock', 'person'),
)
TEMPLATES = {'tales': OLD_WORLD, 'future': WORLD_TO_COME}
COMPANY = ('the {bare} Players', 'the Players of {in}', 'the {bare} Company')
TELLER = ('Old {given} the Teller', '{given} of {in}')
ARENA_KINDS = {'stadium', 'arena'}
TAVERN_KINDS = {'tavern', 'inn', 'bar', 'pub', 'nightlife'}
BELL_KINDS = {'temple', 'church', 'landmark', 'square'}


# --- A city's own block ---

def clean(data: dict) -> list[str]:
    """Check a city's `media` block in place: a bad entry is dropped with a note and the city still loads."""
    block = data.pop('media', None)
    if block is None:
        return []
    if not isinstance(block, dict) or not any(isinstance(block.get(kind), list) for kind in KINDS):
        return ['Dropped the books, shows and songs: they need lists named book, show or music.']
    found, notes = {'credit': str(block.get('credit') or '')[:400]}, []
    for kind in KINDS:
        entries, seen, bad = [], set(), 0
        if block.get(kind) is not None and not isinstance(block[kind], list):
            notes.append(f'Left out the {kind} entries: they need to be a list.')
        for raw in (block.get(kind) if isinstance(block.get(kind), list) else [])[:MAX_ITEMS]:
            entry = clean_entry(raw)
            if not entry or entry[0].casefold() in seen:
                bad += 1
                continue
            seen.add(entry[0].casefold())
            entries.append(entry)
        if bad:
            notes.append(f'Left out {bad} {kind} {"entry" if bad == 1 else "entries"} with no title or a repeated one.')
        if entries:
            found[kind] = entries
    if any(kind in found for kind in KINDS):
        data['media'] = found
    return notes


def clean_entry(raw) -> list | None:
    """[title, by, year, tags], or None. Tags are lowercase words; a show without a format is a series."""
    if isinstance(raw, dict):
        raw = [raw.get('title'), raw.get('by'), raw.get('year'), raw.get('tags')]
    if not isinstance(raw, list | tuple) or not raw:
        return None
    title = ' '.join(str(raw[0] or '').split())[:MAX_TITLE]
    if not title:
        return None
    by = ' '.join(str(raw[1] or '').split())[:MAX_BY] if len(raw) > 1 else ''
    year = raw[2] if len(raw) > 2 and isinstance(raw[2], int) and 0 <= raw[2] <= 9999 else 0
    words = raw[3] if len(raw) > 3 else ''
    words = words.split() if isinstance(words, str) else words if isinstance(words, list) else []
    tags = [str(word).casefold() for word in words if TAG.fullmatch(str(word).casefold())][:8]
    return [title, by, year, ' '.join(tags) or 'general']


# --- Titles for the companion's city ---

def titles(data: dict | None, bank_id: str, real: bool) -> dict | None:
    """{own: {kind: items}, built: {kind: items}} for a city, or None when it has neither."""
    if not data:
        return None
    own = own_items(data)
    built = {} if real else built_items(data, bank_id)
    if not any(own.values()) and not any(built.values()):
        return None
    return {'own': own, 'built': built}


def mark(data: dict | None, bank_id: str, real: bool) -> str:
    """Where their titles come from ('own', 'built' or ''), saved so a change draws today's picks again."""
    found = titles(data, bank_id, real)
    return '' if not found else 'own' if any(found['own'].values()) else 'built'


def item(kind: str, title: str, by: str, year: int, tags: str) -> dict:
    words = tags.split()
    fmt = next((tag for tag in words if tag in SHOW_FORMATS), 'series') if kind == 'show' else kind
    return {'title': title, 'by': by, 'year': year, 'tags': frozenset(words), 'format': fmt}


def own_items(data: dict) -> dict:
    block = data.get('media') or {}
    return {kind: tuple(item(kind, *entry) for entry in block.get(kind) or ()) for kind in KINDS}


_BUILT: dict = {}


def built_items(data: dict, bank_id: str) -> dict:
    key = (data.get('id'), data.get('data_version'), bank_id)
    if key not in _BUILT:
        _BUILT[key] = build(data, bank_id)
    return _BUILT[key]


def build(data: dict, bank_id: str) -> dict:
    """Titles from fixed templates and the city's own words, seeded by the city."""
    slots, seed = slot_values(data), f"media-world:{data.get('id')}"
    found = {kind: [] for kind in KINDS}
    seen = set()
    for index, (kind, slot, template, tags, by) in enumerate(TEMPLATES.get(bank_id, ())):
        values = slots.get(slot) or []
        chosen = sorted(values, key=lambda value: generators.unit(seed, index, value))[:PER_TEMPLATE]
        for value in chosen:
            title = fill(template, value)
            if len(title) > MAX_TITLE or title.casefold() in seen:
                continue
            seen.add(title.casefold())
            found[kind].append(item(kind, title, author(seed, data, by, value, title), 0, tags))
    return {kind: tuple(items) for kind, items in found.items()}


def slot_values(data: dict) -> dict:
    places = data.get('places') or []
    color = data.get('local_color') or []
    # Lore of what happened (no `when`), not the moments that come up with the weather or a holiday.
    lore = [entry for entry in (data.get('lore') or {}).get('entries') or () if not entry.get('when')]
    return {
        'city': [data['name']] if data.get('name') else [],
        'hood': names(data.get('neighborhoods')),
        'place': names(place for place in places if place.get('kind') not in ('clinic', 'fitness', 'office')),
        'arena': names(place for place in places if place.get('kind') in ARENA_KINDS),
        'tavern': names(place for place in places if place.get('kind') in TAVERN_KINDS),
        'bells': names(place for place in places if place.get('kind') in BELL_KINDS),
        'notable': names(data.get('notables'), titled=False),
        'lore': names({'name': entry.get('title')} for entry in lore),
        'feast': names([*(data.get('holidays') or ()), *(data.get('annual_events') or ())]),
        'drink': names(entry for entry in color if entry.get('kind') == 'drink'),
        'dish': names(entry for entry in color if entry.get('kind') in ('dish', 'food')),
    }


def names(records, titled: bool = True) -> list[str]:
    """Short names (up to four words), as titles write them unless they are people's."""
    found = []
    for record in records or ():
        name = ' '.join(str(record.get('name') or '').split())
        name = heading(name) if titled else name
        if name and len(name) <= 40 and len(name.split()) <= 4 and ',' not in name and name not in found:
            found.append(name)
    return found


def heading(text: str) -> str:
    """A lore entry's title as a book's: 'The Noxian invasion' reads 'The Noxian Invasion'."""
    words = text.split()
    return ' '.join(word if index and word.casefold() in SMALL or word[:1].isupper() else word[:1].upper() + word[1:]
                    for index, word in enumerate(words))


def inside(value: str) -> str:
    """A name inside a title: 'The Great Pit' reads 'the Great Pit'."""
    return 'the' + value[3:] if value.startswith('The ') else value


def fill(template: str, value: str) -> str:
    title = template.format(x=value, bare=value.removeprefix('The '), **{'in': inside(value)})
    return title[:1].upper() + title[1:]


def author(seed: str, data: dict, by: str, value: str, title: str) -> str:
    """Who wrote, staged or sings it: a name from the city's own name bank, one of its troupes or tellers, or no one."""
    if by == 'company':
        name = data.get('name') or value
        return generators.pick(seed, f'company:{title}', list(COMPANY)).format(bare=name.removeprefix('The '),
                                                                                **{'in': inside(name)})
    if by == 'teller':
        given = person(seed, data, title).split(' ')[0]
        return generators.pick(seed, f'teller:{title}', list(TELLER)).format(given=given, **{'in': inside(
            data.get('name') or value)})
    return person(seed, data, title) if by == 'person' else ''


def person(seed: str, data: dict, title: str) -> str:
    groups, mix = catalog.name_groups(data)
    keys = sorted(mix)
    group = groups[generators.pick(seed, f'group:{title}', keys, [mix[key] for key in keys])]
    given = [*group.get('feminine', ()), *group.get('masculine', ()), *group.get('neutral', ())]
    first = generators.pick(seed, f'given:{title}', given) or ''
    family = generators.pick(seed, f'family:{title}', list(group.get('family') or ())) or ''
    return f'{first} {family}'.strip()
