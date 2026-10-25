"""Model polish for Prospero's Draft Table: the user's text model rewrites one section's names and summaries in the
place's own voice, at the user's request. Everything else stays the rules': ids, kinds, where each thing is, its
months, careers, prices and links. A reply that names an item it wasn't given, or leaves one out, changes nothing for
that item, so the place always still loads. Rows the user changed by hand (`keep`) are not sent. The prompt was chosen by an A/B run
(/mnt/project-files/companion-draft-table/polish-ab/report.md).
"""
import json

from companion.errors import DomainError
from companion.world import ships

PROMPT_VERSION = 'draft-polish-1'
# A long list goes over in parts: thinking models run out of room on sixty places at once (the A/B).
CHUNK = 12
# Section (as the Draft Table names it) -> the city file's list.
LISTS = {'hoods': 'neighborhoods', 'places': 'places', 'employers': 'employers', 'transit': 'transit',
         'events': 'annual_events', 'colour': 'local_color'}
WHAT = {'hoods': 'neighborhoods', 'places': 'places', 'employers': 'employers', 'transit': 'ways of getting about',
        'events': 'yearly events', 'colour': 'pieces of local color (dishes, sayings, customs and rumors)'}
NAME_LIMIT, SUMMARY_LIMIT = 120, 300
ERAS = {'modern': 'the present day', 'future': 'its future (keep its technology, nothing from today)',
        'fantasy': 'its fantasy world (no modern technology)', 'jazz-age': 'the 1920s', 'victorian': 'the Victorian era', 'other': 'its own time'}
# Room for a part of a list, and a thinking model's thoughts before it.
TOKENS = 8000

PROMPT = """You are helping someone build a place for a life-simulation app. The app has already drawn the place up from rules; your job is to make one part of it sound like it belongs there.

The place: {about}
{what_line}
Below are its {what}, one JSON object per line. Rewrite each one's "name" and "summary" in this place's own voice, so they could only belong to {name} and not to any other {kind}.

Generic is the failure here. Tie each one to this place: its water or land, its weather, its trades, its neighborhoods, its people and its history. A name can carry the town, a street or a local nickname; a summary can say what locals call it, who works there or what the weather does to it.

Keep every fact:
- what each one is (its "kind"), where it is ("where"), and anything its summary says about price, hours, who goes there or what happens there;
- the era: nothing that couldn't exist in {when};
- names may change to suit the place better, or stay as they are when they already fit. Keep each name short, the way locals would say it.

Write each summary as one or two plain sentences, under 200 characters, in American English. No em-dashes, no lists, no new named people, and do not mention the app, players or the rules.

{items}

Answer with JSON only, no other words: {{"items": [{{"id": "...", "name": "...", "summary": "..."}}]}} with every id above exactly once."""


def about(definition: dict, line: str) -> str:
    """One sentence on the whole place, from its name, summary and the user's line."""
    where = ', '.join(part for part in (definition.get('region'), definition.get('country')) if part and part != 'Unknown')
    parts = [f'{definition.get("name", "")}{f" ({where})." if where else "."}']
    if definition.get('summary'):
        parts.append(definition['summary'])
    if line.strip():
        parts.append(f'(Drawn up from: "{line.strip()}".)')
    return ' '.join(parts)


def item_line(item: dict, hoods: dict[str, str]) -> str:
    shown = {'id': item['id'], 'name': item.get('name', ''), 'summary': item.get('summary', '')}
    kind = item.get('kind') or item.get('sector')
    if kind:
        shown['kind'] = kind
    if item.get('neighborhood') in hoods:
        shown['where'] = hoods[item['neighborhood']]
    if item.get('months'):
        shown['months'] = item['months']
    return json.dumps(shown, ensure_ascii=False)


def items_of(definition: dict, section: str) -> list[dict]:
    return [item for item in definition.get(LISTS[section]) or [] if isinstance(item, dict) and item.get('id')]


def prompt(definition: dict, section: str, line: str = '', items: list[dict] | None = None) -> str:
    """The request for one section (or `items`, a part of it): the place, then its items, one per line."""
    hoods = {hood['id']: hood.get('name', hood['id']) for hood in definition.get('neighborhoods') or []}
    items = items_of(definition, section) if items is None else items
    aboard = ships.enclosed(definition)
    return PROMPT.format(
        about=about(definition, line), name=definition.get('name') or 'this place',
        kind='ship or station' if aboard else 'town', when=era_words(definition),
        what=WHAT[section], what_line='It is a ship or station, so its neighborhoods are decks.' if aboard else '',
        items='\n'.join(item_line(item, hoods) for item in items))


def era_words(definition: dict) -> str:
    era = str(definition.get('era') or 'modern')
    return ERAS.get(era) or f'the {era.replace("-", " ")} era'


def apply(definition: dict, section: str, reply: dict) -> tuple[dict, list[str]]:
    """(the definition with the reply's names and summaries in, the ids of the items that changed). Only items the
    section already has change, and only their name and summary."""
    rewritten = {}
    for found in reply.get('items') if isinstance(reply.get('items'), list) else []:
        if isinstance(found, dict) and isinstance(found.get('id'), str):
            rewritten[found['id']] = found
    changed, items = [], []
    for item in definition.get(LISTS[section]) or []:
        new = rewritten.get(item.get('id')) if isinstance(item, dict) else None
        merged = {**item, **cleaned(new)} if new else item
        if merged != item:
            changed.append(item['id'])
        items.append(merged)
    return {**definition, LISTS[section]: items}, changed


def cleaned(found: dict) -> dict:
    """The name and summary of one reply item, trimmed to what the city file takes; a blank one is left out."""
    out = {}
    for key, limit in (('name', NAME_LIMIT), ('summary', SUMMARY_LIMIT)):
        value = found.get(key)
        if isinstance(value, str) and value.strip():
            out[key] = ' '.join(value.replace('—', ', ').split())[:limit]
    return out


def ready(database) -> bool:
    """Whether the user has a text model set for drafting, which Polish uses."""
    from companion import drafting
    try:
        drafting.connection_config(database)
    except DomainError:
        return False
    return True


async def polish(state, definition: dict, section: str, line: str = '', keep: frozenset = frozenset()) -> dict:
    """{definition, changed, ids}: one section rewritten by the user's text model (the one set for drafting), leaving
    the items in `keep` as they are."""
    from companion import drafting  # The model plumbing loads only when someone polishes.
    try:
        config = drafting.connection_config(state.database)
    except DomainError as problem:
        raise DomainError('Polish uses a text model. Add one in Companion under Settings > Models.', problem.status,
                          problem.code) from problem
    system = 'You write names and short descriptions for places in a life-simulation app. You answer with JSON only.'

    def shape(raw: dict, final: bool) -> dict:
        if not isinstance(raw.get('items'), list) and not final:
            raise drafting.Unusable('it had no "items" list.')
        return raw

    items = [item for item in items_of(definition, section) if item['id'] not in keep]
    polished, changed = definition, []
    for start in range(0, len(items), CHUNK):
        messages = [{'role': 'user', 'content': prompt(definition, section, line, items[start:start + CHUNK])}]
        reply = await drafting.ask(state, config, system, TOKENS, shape, messages)
        polished, ids = apply(polished, section, reply)
        changed += [found for found in ids if found not in keep]
    # A reply naming a kept row changes nothing: the user's own wording stays.
    kept = {item['id']: item for item in items_of(definition, section) if item['id'] in keep}
    polished = {**polished, LISTS[section]: [kept.get(item.get('id'), item) if isinstance(item, dict) else item
                                             for item in polished.get(LISTS[section]) or []]}
    return {'definition': polished, 'changed': len(changed), 'ids': changed}
