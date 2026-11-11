"""Places the user names that the city's data doesn't have (1.4.1, from the 1.4 E2E): "Dinner tonight at 7 at
Woodberry Kitchen?" in a city whose map has no Woodberry Kitchen.

The app adds the place itself and the outing happens there; nothing asks first ("The world exists outside of User").
Rules fill it in, with no model: its kind from words in its name ("Kitchen", "Tavern", "Roasters") and else from what
the ask is for (dinner is a restaurant, drinks a bar), and a neighborhood that fits, one the sentence names or else one
where the city has places of that kind. Its hours, setting and price level come from one of the city's places of that
kind (`changes.new_place`). Once added it is a place like any other in this world: on the map, in their days, for the
next outing. The user can rename it, change its kind, neighborhood or description on the map's place card, or take it
off the map.

Kept per world, by city, in `added_places`; `merge` adds them to a city's data wherever this world reads it
(outings, the map, the life simulation, Story mode).
"""
import re

from companion.database import decode, encode, many, optional
from companion.errors import require
from companion.world import catalog, changes, generators

PREFIX = 'named-'
# The words after "at" or "to" that name it: capitalised words, with small joining words between them.
NAMED = re.compile(r"\b(?:at|to)\s+(?:the\s+)?((?:[A-Z][\w'’&.-]*)(?:\s+(?:[A-Z][\w'’&.-]*|&|of|and|on|de|la|del|"
                   r"di|du|le|the))*)")
JOINING = {'&', 'of', 'and', 'on', 'de', 'la', 'del', 'di', 'du', 'le', 'the'}
# Capitalised words that say when, never part of a name at either end ("at Woodberry Kitchen Friday").
WHEN = re.compile(
    r"^(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|tues|wed|thu|thurs|fri|sat|sun|"
    r"january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|"
    r"jul|aug|sep|sept|oct|nov|dec|today|tonight|tomorrow|noon|midnight|night|morning|evening|afternoon|weekend|"
    r"christmas|xmas|easter|thanksgiving|halloween|new|year|years|eve|valentine)$", re.IGNORECASE)
# Other capitalised words that never start a place's name: people, everyday destinations, the meal itself.
NOT_PLACES = re.compile(
    r"^(?:i|i'm|i'll|me|you|my|your|our|we|us|home|work|school|church|mass|bed|lunch|dinner|brunch|breakfast|"
    r"coffee|drinks|the|a|an|it|this|that|there|here|ok|okay|please|lol|haha|god|omg|mom|mum|dad|ma|pa)$",
    re.IGNORECASE)
# Words in a name that say what kind of place it is, first match wins (a "Kitchen & Bar" is a restaurant).
NAME_KINDS = (
    (r"kitchen|grill|grille|bistro|trattoria|osteria|diner|steakhouse|chophouse|restaurant|eatery|pizzeria|pizza|"
     r"sushi|taqueria|tacos?|brasserie|cantina|noodles?|ramen|bbq|barbecue|smokehouse|crab|oyster|seafood|burgers?|"
     r"deli|dumplings?|curry|thai|pho|bistrot|table|supper club", 'restaurant'),
    (r"caf[eé]|coffee|roasters?|espresso|tea ?room|teahouse|bakery|patisserie|creamery", 'cafe'),
    (r"bar|pub|tavern|taproom|tap house|brewery|brewing|saloon|lounge|alehouse|beer garden|wine|cocktails?|"
     r"speakeasy|inn", 'bar'),
    (r"nightclub|club|disco", 'nightlife'),
    (r"museum|gallery|exhibit", 'museum'),
    (r"aquarium|zoo|observatory", 'attraction'),
    (r"theat(?:er|re)|cinema|playhouse|opera|concert hall|music hall|arena|amphitheat(?:er|re)|auditorium", 'venue'),
    (r"stadium|ballpark|field", 'stadium'),
    (r"gardens?|arboretum|conservatory", 'garden'),
    (r"park|commons?|green|square|woods", 'park'),
    (r"trail|path|falls", 'trail'),
    (r"beach", 'beach'),
    (r"market|bazaar|farmers", 'market'),
    (r"mall|shops|boutique|outlet|bookshop|bookstore|books", 'shopping'),
    (r"library", 'library'),
    (r"gym|fitness|yoga|climbing", 'fitness'),
)
LABELS = changes.LABELS | {'nightlife': 'club', 'fitness': 'studio', 'trail': 'trail'}
EDITABLE_KINDS = ('restaurant', 'cafe', 'bar', 'nightlife', 'museum', 'attraction', 'venue', 'stadium', 'park',
                  'garden', 'trail', 'beach', 'market', 'shopping', 'library', 'fitness', 'landmark', 'tavern', 'inn')


def stored(connection, city_id: str) -> list[dict]:
    return [decode(row['place']) | {'added': row['origin']} for row in many(
        connection, 'SELECT place, origin FROM added_places WHERE city_id=? AND removed=0 ORDER BY created_at, place_id',
        (city_id,))]


def merge(connection, data: dict | None) -> dict | None:
    """The city with the places added in this world. The cached city is not changed."""
    if not data:
        return data
    known = {place['id'] for place in data['places']}
    extra = [place for place in stored(connection, data['id']) if place['id'] not in known]
    return data | {'places': [*data['places'], *extra]} if extra else data


def name_in(sentence: str, data: dict) -> str | None:
    """The name of a place the sentence asks to go to that the city does not have ("Woodberry Kitchen"), or None."""
    hoods = {hood['name'].casefold() for hood in data['neighborhoods']}
    for found in NAMED.finditer(sentence):
        words = found.group(1).rstrip(".'’").split()
        while words and (words[-1].casefold() in JOINING or bare(words[-1], WHEN)):
            words.pop()
        while words and (bare(words[0], WHEN) or bare(words[0], NOT_PLACES)):
            words.pop(0)
        name = ' '.join(words).strip(".,!?'’")
        if plausible(name, words) and name.casefold() not in hoods and not a_city(name):
            return name
    return None


def bare(word: str, pattern: re.Pattern) -> bool:
    return bool(pattern.match(re.sub(r"['’]s$", '', word.strip(".,!?"))))


def plausible(name: str, words: list[str]) -> bool:
    """Long enough, and not one person's name with an "'s" (Sam's is Sam's place)."""
    return len(name) >= 4 and not (len(words) == 1 and re.search(r"['’]s$", name))


def a_city(name: str) -> bool:
    """A city by its own name or another it goes by ("Paris", "Charm City"), not a place named after one."""
    found = catalog.resolve(name)
    if not found:
        return False
    data = catalog.cities().get(found['city']) or {}
    return name.casefold() in {item.casefold() for item in (data.get('name', ''), *data.get('aliases', ()))}


def said_kind(name: str) -> str | None:
    return next((kind for pattern, kind in NAME_KINDS if re.search(rf'\b(?:{pattern})\b', name, re.IGNORECASE)), None)


def kind_for(name: str, activity_kinds: tuple[str, ...], data: dict) -> str:
    """What the name says it is, else what the outing is for, kept to kinds this city has where it can."""
    have = {place['kind'] for place in data['places']}
    said = said_kind(name)
    if said and (said in have or not activity_kinds):
        return said
    return next((kind for kind in activity_kinds if kind in have), said or (activity_kinds or ('restaurant',))[0])


def hood_for(name: str, kind: str, sentence: str, data: dict) -> dict:
    """A neighborhood the sentence names ("in Hampden"), else one where the city has places of this kind, the more
    the likelier, the same one every time for this name."""
    named = next((hood for hood in sorted(data['neighborhoods'], key=lambda item: -len(item['name']))
                  if re.search(rf"\b{re.escape(hood['name'])}\b", sentence, re.IGNORECASE)), None)
    if named:
        return named
    counts = {}
    for place in data['places']:
        if place['kind'] == kind:
            counts[place['neighborhood']] = counts.get(place['neighborhood'], 0) + 1
    hoods = [hood for hood in data['neighborhoods'] if hood['id'] in counts] or data['neighborhoods']
    return generators.pick(f"named:{data['id']}:{changes.slug(name)}", 'hood', hoods,
                           [counts.get(hood['id'], 1) for hood in hoods])


def guess(sentence: str, data: dict | None, activity_kinds: tuple[str, ...] = ()) -> dict | None:
    """A new place for a name the sentence gives that the city does not have, filled in by rules; not stored yet."""
    if not data or not data.get('neighborhoods') or not (name := name_in(sentence, data)):
        return None
    if not activity_kinds and not said_kind(name):
        return None  # "Want to go to Italy?": neither the name nor the ask says what kind of place it is.
    kind = kind_for(name, activity_kinds, data)
    hood = hood_for(name, kind, sentence, data)
    place_id = f'{PREFIX}{changes.slug(name)}'
    found = catalog.find(data, place_id)
    if found:
        return found
    # No description: "A restaurant in The Quays" would only repeat the card's subtitle (Iris, 2026-11-11).
    place = changes.new_place(data, kind, name, hood['id'], '', place_id, place_id)
    return place | {'tags': [tag for tag in place['tags'] if tag != 'new'], 'cuisine': '', 'source': 'named',
                    'added': 'named'}


def add(connection, data: dict, place: dict, message_id: str | None, now: str) -> None:
    """Keep a guessed place in this world (once per name; named again after it was taken off the map, it is back as
    it was)."""
    fields = {key: value for key, value in place.items() if key != 'added'}
    connection.execute(
        "INSERT INTO added_places (city_id, place_id, origin, place, message_id, created_at, updated_at) "
        "VALUES (?, ?, 'named', ?, ?, ?, ?) ON CONFLICT(city_id, place_id) DO UPDATE SET removed=0",
        (data['id'], place['id'], encode(fields), message_id, now, now))


def edit(connection, data: dict, place_id: str, change: dict, now: str) -> dict:
    """The user's own details for an added place: its name, kind, neighborhood and description."""
    row = optional(connection, 'SELECT place FROM added_places WHERE city_id=? AND place_id=? AND removed=0',
                   (data['id'], place_id))
    require(row is not None, 'Only places added to this map can be changed here.', 404)
    place = decode(row['place'])
    if change.get('name') is not None:
        require(bool(change['name'].strip()), 'A place needs a name.', 422)
        place['name'] = change['name'].strip()
    if change.get('kind') is not None:
        require(change['kind'] in EDITABLE_KINDS, 'Choose a kind of place from the list.', 422)
        place['kind'] = change['kind']
    if change.get('neighborhood') is not None:
        place['neighborhood'] = catalog.neighborhood(data, change['neighborhood'])['id']
    if change.get('about') is not None:
        place['summary'] = change['about'].strip()
    connection.execute("UPDATE added_places SET place=?, origin='edited', updated_at=? WHERE city_id=? AND place_id=?",
                       (encode(place), now, data['id'], place_id))
    return place


def remove(connection, data: dict, place_id: str, removed: bool = True) -> None:
    """Take an added place off the map, or put it back (Undo). Outings and days already there keep it by name."""
    require(connection.execute('UPDATE added_places SET removed=? WHERE city_id=? AND place_id=?',
                               (int(removed), data['id'], place_id)).rowcount > 0,
            'Only places added to this map can be removed.', 404)
