"""A whole character the user already has, split into the form's fields, and the fields the sidecar may change.

`split` takes a pasted character (or one read from a character card) and splits it into the form's fields
with one model call, when the user asks. Their text wins over the drafting guidance; fields it says
nothing about are filled in and named, so the form can show which ones to check. It reuses the drafting
checks in companion/drafting.py: the Character drafting job, the one-retry repair, the field shaping and
the invented-name check. The world stays the app's: a city is only ever one from the catalogue that the
pasted text names. Nothing is saved. See docs/character-drafting.md; the sidecar is companion/sidecar.py.
"""
import re
from dataclasses import dataclass

from companion import drafting
from companion.database import identifier
from companion.errors import DomainError
from companion.world import catalog, custom

HELPER_TOKENS = 3000
# Fields the helper may change. Relationship, home city and emotional traits are the user's own picks.
HELPER_FIELDS = ('name', 'identity', 'personality', 'voice', 'skills', 'flaws', 'interests', 'background',
                 'appearance', 'routine', 'location', 'life_themes', 'schedule', 'seen_as', 'sees_self')
EXTRA_GUIDES = {'name': ('their full name.', 'a string'), 'location': ('where they live, in general terms.', 'a string'),
                # Left empty, the app fills these from its phrase bank (companion/world/perception.py); write them
                # only when the user asks.
                'seen_as': ('how others see them, one line: "<how they come across>; <a habit people notice>; '
                            '<what sets them off>." Change it only when the user asks.', 'a string'),
                'sees_self': ('how they see themselves, private: 3 to 6 short first-person lines, one per line, '
                              'which may differ from how others see them. Change it only when the user asks.',
                              'a string')}
FREE_TEXT = {'name': 120, 'location': 200, 'seen_as': 400, 'sees_self': 1200}
SPLIT_FIELDS = set(HELPER_FIELDS) - set(FREE_TEXT)
# Aliases shorter than this ("LV", "SD") match too much ordinary text.
ALIAS_LENGTH = 4


@dataclass
class SplitBody:
    """The parts of a quick-start request `drafting.Draft` reads, for a pasted character."""
    idea: str
    relationship: str
    timezone: str
    emotional_edges: bool
    name: str = ''
    vibe: str = ''


def mentioned_city(text: str, cities: dict[str, dict]) -> dict | None:
    """The catalogue city the text names first, by name or a distinctive alias, if any."""
    found = []
    for data in cities.values():
        for word in {data['name'], *[alias for alias in data.get('aliases', []) if len(alias) >= ALIAS_LENGTH]}:
            if match := re.search(rf'(?<!\w){re.escape(word)}(?!\w)', text):
                found.append((match.start(), data['id'], data))
    return min(found)[2] if found else None


class Split(drafting.Draft):
    """A pasted character shaped like a quick-start draft, plus which fields the model had to fill in."""

    def __call__(self, raw: dict, final: bool) -> dict:
        if raw.get('under_18') is True:
            raise DomainError('Companions are always adults, and this character reads as younger than 18. '
                              'Change their age in the text, or start from the quick start.', 422, 'under_18')
        result = super().__call__(raw, final)
        filled = raw.get('filled_in') if isinstance(raw.get('filled_in'), list) else []
        result['filled_in'] = [key for key in dict.fromkeys(filled) if key in SPLIT_FIELDS]
        return result


async def split(state, body) -> dict:
    """A whole pasted character split into the form's fields, for review; nothing is saved."""
    config = drafting.connection_config(state.database)
    data = mentioned_city(body.text, catalog.cities() | custom.read(state.database))
    seed = identifier()
    offered = drafting.careers(data)
    request = SplitBody(idea=body.text, relationship=body.relationship, timezone=body.timezone,
                        emotional_edges=body.emotional_edges)
    system = drafting.fill(
        drafting.template('character-split.md', state.database),
        rules=drafting.template('character-rules.md', state.database),
        city=drafting.city_text(data), careers=drafting.careers_text(offered), names=drafting.names_text(data, seed),
        emotional=drafting.EDGES if drafting.edges_allowed(request) else drafting.NO_EDGES,
        # Last, so braces in the user's own text are never read as placeholders.
        pasted=body.text)
    result = await drafting.ask(state, config, system, drafting.DRAFT_TOKENS, Split(request, data, offered, seed))
    return result | {'home_city': data['name'] if data else ''}


# --- The fields the sidecar may change ---------------------------------------------------

def fields_text() -> str:
    guides = drafting.field_guides() | {key: {'guide': guide, 'shape': shape} for key, (guide, shape) in EXTRA_GUIDES.items()}
    return '\n'.join(f"- {key} ({guides[key]['shape']}): {guides[key]['guide']}" for key in HELPER_FIELDS)


def helper_value(field: str, value, final: bool):
    if field in FREE_TEXT:
        found = drafting.text_value(value, FREE_TEXT[field])
        if not found:
            raise drafting.Unusable(f'"{field}" was empty.')
        return found
    return drafting.field_value(field, {'value': value}, final)
