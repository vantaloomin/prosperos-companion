"""Where a picture is: the place of a moment in words an image model can draw.

A moment names its place ("at The Great Pit"), but a name means nothing to an image model for a made-up world, and
left to itself it draws a street at night. So the picture says what the place looks like, from the world's own words:
a lore entry about it (the companion's own books first, then the world's and the city's, the order the chat reads
them in, companion/lore.py) and the city file's summary of it. A shift at work carries no place of its own, so the
picture puts it at the workplace their words name ("owns the Great Pit") in the city they live in. Rules only: no
model is asked anything, and nothing is invented when the world says nothing.
"""
import re

from companion.database import decode
from companion.life import outings

# Work moments, which happen at the workplace their words name.
WORKING = {'steady-shift', 'busy-shift'}
# A sentence that says where they work: "owns the Great Pit", "works at Blue Bottle", "runs the bakery".
WORK_WORDS = re.compile(r'\b(?:work(?:s|ed|ing)?|job|runs?|running|owns?|manag(?:es?|ing)|boss|shifts?|employ\w*|'
                        r'staff|hired|bartends?|tends? bar)\b', re.IGNORECASE)
SENTENCE = re.compile(r'(?<=[.!?])\s+')
# At most this much of the place's look goes into a picture, so the moment and the person stay the subject.
MAX_LOOK = 320
MACROS = re.compile(r'\{\{(?:char|user)\}\}|<(?:BOT|USER)>', re.IGNORECASE)


def short_name(name: str) -> str:
    """"The Great Pit" is also said "the Great Pit" and "Great Pit"."""
    return re.sub(r'^the\s+', '', name.strip(), flags=re.IGNORECASE)


def named_at(text: str, place: dict) -> int | None:
    """Where in `text` the place is named, or None."""
    name = short_name(place.get('name') or '')
    if len(name) < 4:
        return None
    found = re.search(rf'(?<!\w){re.escape(name)}(?!\w)', text, re.IGNORECASE)
    return found.start() if found else None


def first_named(text: str, city: dict) -> dict | None:
    """The city place `text` names first."""
    found = [(at, place) for place in city.get('places') or [] if (at := named_at(text, place)) is not None]
    return min(found, key=lambda item: (item[0], -len(item[1]['name'])))[1] if found else None


def workplace(definition: dict, city: dict | None, label: str = '') -> dict | None:
    """The city place they work at, as their words name it: the work block's own label ("Night at the Great Pit")
    first, then a sentence of their routine, identity or background that says they work there. None when nothing
    names one, so a café they love is never taken for their job."""
    if not city:
        return None
    if label and (place := first_named(label, city)):
        return place
    for key in ('routine', 'identity', 'background'):
        for sentence in SENTENCE.split(str(definition.get(key) or '')):
            if WORK_WORDS.search(sentence) and (place := first_named(sentence, city)):
                return place
    return None


def city_place(city: dict | None, place_id: str | None, name: str) -> dict | None:
    if not city:
        return None
    places = city.get('places') or []
    return next((place for place in places if place_id and place.get('id') == place_id), None) or \
        next((place for place in places if name and short_name(place['name']).casefold() == short_name(name).casefold()),
             None)


def first_sentence(text: str, words: list[str], name: str) -> str:
    """The entry's first sentence that names the place or one of its keywords, and not the companion (a sentence
    about them would put a second of them in the picture)."""
    for sentence in SENTENCE.split(text.strip()):
        said = sentence.casefold()
        if MACROS.search(sentence) or (name and re.search(rf'\b{re.escape(name.casefold())}\b', said)):
            continue
        if any(re.search(rf'(?<!\w){re.escape(word.casefold())}(?!\w)', said) for word in words if word.strip()):
            return sentence.strip()
    return ''


def lore_line(entries: list[dict], place_name: str, companion_name: str) -> str:
    """The first lore entry about the place (one of its keywords is in the place's name, or its title names the
    place), as its first sentence about it."""
    place = place_name.casefold()
    for entry in entries:
        keywords = [word for word in decode(entry['keywords']) or [] if len(word.strip()) >= 3]
        about = [word for word in keywords if re.search(rf'(?<!\w){re.escape(word.casefold().strip())}(?!\w)', place)]
        if not about and short_name(place_name).casefold() not in (entry.get('title') or '').casefold():
            continue
        if line := first_sentence(entry['text'], [*about, short_name(place_name)], companion_name):
            return line
    return ''


def summary_line(place: dict | None) -> str:
    return SENTENCE.split((place or {}).get('summary', '').strip())[0] if place else ''


def looks(lore: str, summary: str) -> str:
    """The lore sentence, else the city's summary. Not both: the more is said about a place, the more people it names
    ("a balcony for the Boss"), and the A/B drew a second Sett on that balcony."""
    text = next((line.rstrip('.!? ') + '.' for line in (lore, summary) if line), '')
    return text if len(text) <= MAX_LOOK else text[:MAX_LOOK].rsplit(' ', 1)[0].rstrip(',;:') + '.'


def scene(connection, companion: dict, event: dict) -> dict:
    """What a picture of `event` adds about its place: `place` (a workplace for a shift with none), `place_look` (what
    it looks like) and `indoor` (True, False or None when unknown). {} when there is nothing to add."""
    from companion import lore
    definition = companion['version']['definition']
    city = outings.city_data(connection, definition)
    place = city_place(city, event.get('place_id'), event.get('place') or '')
    added = {}
    if not event.get('place') and event.get('activity') in WORKING:
        place = workplace(definition, city, event.get('label') or '')
        if place:
            added['place'] = place['name']
    name = (place or {}).get('name') or event.get('place') or ''
    if not name:
        return added
    entries = lore.active_entries(connection, companion, lore.companion_city(connection, companion))
    look = looks(lore_line(entries, name, definition.get('name', '')), summary_line(place))
    if look:
        added['place_look'] = f'The setting is {name}. {look}'
    if place and place.get('setting') in ('indoor', 'outdoor'):
        added['indoor'] = place['setting'] == 'indoor'
    return added
