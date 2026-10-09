"""Which voice each companion speaks with (docs/voice-notes.md).

The app picks, so voice notes work without a setup step ("the world exists outside of User"): her pronouns give a
woman's or a man's voice, her home city's country (else her time zone) gives an American or a British accent, and
her id seeds the choice among the voices that fit, so two companions rarely share one and the choice never changes
by itself. The user can pick another in Settings > Models > Voice notes; that choice is kept for that engine.

Fantasy and historical cities have no accent of their own here: a city whose country reads as British or Irish
gets a British voice, and everything else an American one. Real people's voices are never cloned; every voice is
one of the engine's own stock voices.
"""
import hashlib
import re

from companion.database import optional

# Kokoro's English stock voices (speaker id, name, accent, gender), best rated first. Its other languages'
# voices are left out; "santa" voices too.
KOKORO = [
    (3, 'Heart', 'us', 'female'), (2, 'Bella', 'us', 'female'), (6, 'Nicole', 'us', 'female'),
    (1, 'Aoede', 'us', 'female'), (5, 'Kore', 'us', 'female'), (9, 'Sarah', 'us', 'female'),
    (7, 'Nova', 'us', 'female'), (10, 'Sky', 'us', 'female'),
    (16, 'Michael', 'us', 'male'), (14, 'Fenrir', 'us', 'male'), (18, 'Puck', 'us', 'male'),
    (12, 'Echo', 'us', 'male'), (15, 'Liam', 'us', 'male'), (17, 'Onyx', 'us', 'male'), (13, 'Eric', 'us', 'male'),
    (21, 'Emma', 'gb', 'female'), (22, 'Isabella', 'gb', 'female'), (20, 'Alice', 'gb', 'female'),
    (23, 'Lily', 'gb', 'female'),
    (26, 'George', 'gb', 'male'), (25, 'Fable', 'gb', 'male'), (27, 'Lewis', 'gb', 'male'),
    (24, 'Daniel', 'gb', 'male'),
]
# OpenAI's voices are not labelled; these are how they sound. Accents are all American.
OPENAI = [('marin', 'Marin', 'female'), ('coral', 'Coral', 'female'), ('nova', 'Nova', 'female'),
          ('sage', 'Sage', 'female'), ('shimmer', 'Shimmer', 'female'), ('cedar', 'Cedar', 'male'),
          ('ash', 'Ash', 'male'), ('ballad', 'Ballad', 'male'), ('echo', 'Echo', 'male'), ('onyx', 'Onyx', 'male'),
          ('verse', 'Verse', 'male'), ('fable', 'Fable', 'male'), ('alloy', 'Alloy', 'neutral')]
BRITISH = re.compile(r'\b(?:united kingdom|uk|england|scotland|wales|northern ireland|ireland|britain|great britain|'
                     r'australia|new zealand)\b', re.IGNORECASE)
BRITISH_ZONES = ('Europe/London', 'Europe/Dublin', 'Europe/Belfast', 'Australia/', 'Pacific/Auckland')
SHE, HE = {'she', 'her', 'hers', 'herself'}, {'he', 'him', 'his', 'himself'}
ACCENT_NAMES = {'us': 'American', 'gb': 'British'}


def gender(definition: dict) -> str:
    """'male' when the description says he more than she; otherwise 'female' (the companions are mostly women)."""
    words = re.findall(r'[a-z]+', ' '.join(str(definition.get(key) or '') for key in (
        'identity', 'personality', 'background')).lower())
    she, he = sum(word in SHE for word in words), sum(word in HE for word in words)
    return 'male' if he > she else 'female'


def accent(country: str, timezone: str) -> str:
    if country:
        return 'gb' if BRITISH.search(country) else 'us'
    return 'gb' if any(timezone.startswith(zone) for zone in BRITISH_ZONES) else 'us'


def traits(connection, definition: dict) -> dict:
    from companion.world import newcomers
    country = newcomers.city_for(connection, definition).get('country') or ''
    return {'gender': gender(definition), 'accent': accent(country, definition.get('timezone') or '')}


def seeded(seed: str, options: list):
    """The same option for the same seed, spread evenly across seeds."""
    return options[int(hashlib.sha256(seed.encode('utf-8')).hexdigest()[:8], 16) % len(options)]


def kokoro_voices() -> list[dict]:
    return [{'id': str(sid), 'name': name, 'gender': sex, 'accent': place,
             'label': f'{name} ({ACCENT_NAMES[place]}, {"woman" if sex == "female" else "man"})'}
            for sid, name, place, sex in KOKORO]


def openai_voices() -> list[dict]:
    return [{'id': voice, 'name': name, 'gender': sex, 'accent': 'us',
             'label': f'{name} ({"woman" if sex == "female" else "man" if sex == "male" else "either"})'}
            for voice, name, sex in OPENAI]


def fitting(voices: list[dict], wanted: dict) -> list[dict]:
    """The voices that fit her best: both traits, else her gender, else all of them."""
    both = [voice for voice in voices if voice['gender'] == wanted['gender'] and voice['accent'] == wanted['accent']]
    if both:
        return both
    return [voice for voice in voices if voice['gender'] == wanted['gender']] or voices


def pick(companion_id: str, voices: list[dict], wanted: dict) -> dict | None:
    """The app's choice. The best few that fit come first, so the top voices are shared out before the weaker."""
    options = fitting(voices, wanted)
    return seeded(companion_id, options[:4] if len(options) > 4 else options) if options else None


def chosen(connection, companion_id: str, engine: str) -> str | None:
    row = optional(connection, 'SELECT voice FROM companion_voices WHERE companion_id=? AND engine=?',
                   (companion_id, engine))
    return row['voice'] if row else None
