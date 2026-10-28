"""Local politics in this world: the city's issues and factions as they stand today, with the user's changes, and
where the companion and the people they know stand (companion/world/politics.py has the rules).

The Realism slider "Local politics" (life_settings.politics_realism) sets how much goes on: 0 off, 1 quiet (one big
question, few local quarrels), 2 true to life, 3 lively; this world's drama level ("How much happens",
companion/life/world_drama.py) makes local quarrels likelier and factions' fortunes swing harder.

The user can change any of it afterwards, kept per city in this world: add an issue or put one away, rename its sides,
say how one settled, set anyone's view, add a faction, rename one, change its pull or members, and set how two
factions stand. A local issue settles by seeded dice (`outcome`), with its odds and why kept in the answer the way
"Why it went this way" shows a storyline's.
"""
from datetime import date, timedelta

from companion import consequences
from companion.database import decode, encode, identifier, many, optional
from companion.errors import DomainError, require
from companion.life import circle, world_drama
from companion.memory import pairs
from companion.world import politics, townsfolk
from companion.world.generators import pick, unit

DEFAULT_LEVEL = 2
# Tests turn politics off where it would change unrelated chats and papers (tests/conftest.py).
ACTIVE = True
# Fizzling out, by drama: an easy world lets more quarrels die down.
FIZZLE = (0.5, 0.3, 0.18, 0.1)
# A win or a loss moves a faction's pull for this long; issues settled this recently warm or cool factions.
PULL_DAYS, RELATION_DAYS = 180, 90
# Closeness from which someone's strong view rubs off on a companion (memory/pairs.py stages).
CLOSE = 4
TEMPERAMENTS = sorted(townsfolk.TEMPERAMENTS)


def level(connection) -> int:
    row = optional(connection, 'SELECT politics_realism FROM life_settings WHERE id=1')
    return row['politics_realism'] if row and row['politics_realism'] is not None else DEFAULT_LEVEL


# --- Stored changes ---

def stored(connection, table: str, column: str, city_id: str) -> dict[str, dict]:
    return {row[column]: {**decode(row['data']), 'origin': row['origin'], 'dismissed': bool(row['dismissed'])}
            for row in many(connection, f'SELECT * FROM {table} WHERE city_id=?', (city_id,))}


def view_overrides(connection, city_id: str) -> dict[tuple[str, str], int]:
    return {(row['issue_id'], row['person']): row['view']
            for row in many(connection, 'SELECT * FROM politics_views WHERE city_id=?', (city_id,))}


def relation_overrides(connection, city_id: str) -> dict[tuple[str, str], int]:
    return {(row['first'], row['second']): row['stance']
            for row in many(connection, 'SELECT * FROM politics_relations WHERE city_id=?', (city_id,))}


# --- Issues as they stand ---

def edited(issue: dict, edit: dict | None) -> dict:
    """A seeded issue with the user's changes: its title, its sides' names, how it settled, or ended early."""
    if not edit:
        return issue
    found = {**issue, 'edited': True}
    if edit.get('title'):
        found['title'] = edit['title']
    if edit.get('question'):
        found['question'] = edit['question']
    names = edit.get('sides') or []
    found['sides'] = [{**side, 'name': names[index] if index < len(names) and names[index] else side['name']}
                      for index, side in enumerate(issue['sides'])]
    for key in ('outcome', 'ended'):
        if edit.get(key) is not None:
            found[key] = edit[key]
    if edit.get('stage') and 'dates' in issue:
        found['dates'] = staged(issue['dates'], edit['stage'], date.fromisoformat(edit['stage_on']))
        found['stage_by'] = 'you'
    return found


NEVER = '9999-12-31'


def staged(dates: dict, stage: str, day: date) -> dict:
    """An issue's dates with `stage` reached by `day` and the stages after it pushed back, keeping their gaps."""
    at = politics.STAGES.index(stage)
    found = {key: min(value, day.isoformat()) if politics.STAGES.index(key) <= at else value
             for key, value in dates.items()}
    later = politics.STAGES[at + 1:]
    if later and found[later[0]] <= day.isoformat():
        shift = day + timedelta(days=1) - date.fromisoformat(found[later[0]])
        for key in later:
            if found[key] < NEVER:
                found[key] = (date.fromisoformat(found[key]) + shift).isoformat()
    return found


def user_issue(issue_id: str, edit: dict) -> dict:
    """An issue the user added: open from the day they added it until they end it or say how it went."""
    sides = [{'name': name, 'stand': stand, 'backers': [], 'jobs': [], 'words': []}
             for name, stand in zip(edit['sides'], edit['stands'], strict=True)]
    return {'id': issue_id, 'kind': 'local', 'template': None, 'title': edit['title'], 'question': edit['question'],
            'sides': sides, 'origin': 'user', 'real': False, 'hood': None, 'place': None, 'person': None,
            'started': edit['started'], 'outcome': edit.get('outcome'), 'ended': edit.get('ended'),
            'beats_text': {}, 'dates': user_dates(edit), 'stage_by': 'you' if edit.get('stage') else None}


def user_dates(edit: dict) -> dict:
    dates = {'whispers': edit['started'], 'open': edit['started'], 'heated': NEVER, 'settled': edit.get('ended') or NEVER}
    return staged(dates, edit['stage'], date.fromisoformat(edit['stage_on'])) if edit.get('stage') else dates


def ended(issue: dict) -> bool:
    return issue.get('outcome') is not None or bool(issue.get('ended'))


def city_issues(connection, data: dict, day: date, level_: int, drama: int) -> list[dict]:
    """Every issue live in the city on `day`, the era's first, then local ones newest first."""
    if not level_:
        return []
    edits = stored(connection, 'politics_issues', 'issue_id', data['id'])
    found = [edited(issue, edits.get(issue['id'])) for issue in politics.era_issues(data, day, level_)]
    found = [issue for issue in found if not edits.get(issue['id'], {}).get('dismissed')]
    seeded = [edited(issue, edits.get(issue['id'])) for issue in politics.seeded_locals(data, day, level_, drama)]
    own = [user_issue(issue_id, edit) for issue_id, edit in edits.items() if edit['origin'] == 'user'
           and edit.get('started', '9999') <= day.isoformat()]
    local = [issue for issue in [*seeded, *own] if not edits.get(issue['id'], {}).get('dismissed')
             and politics.live(issue, day)]
    return found + sorted(local, key=lambda issue: issue['started'], reverse=True)


# --- Factions as they stand ---

def city_factions(connection, data: dict) -> list[dict]:
    """The city's factions with the user's changes, and the ones the user added; put-away ones left out."""
    edits = stored(connection, 'politics_factions', 'faction_id', data['id'])
    found = []
    for faction in politics.factions(data):
        edit = edits.get(faction['id']) or {}
        if not edit.get('dismissed'):
            found.append(faction_edited(faction, edit))
    for faction_id, edit in edits.items():
        if edit['origin'] == 'user' and not edit.get('dismissed'):
            found.append(faction_edited({'id': faction_id, 'name': edit['name'], 'kind': edit.get('kind') or 'faction',
                                         'tags': [], 'pull': 2, 'about': '', 'jobs': [], 'members': [], 'places': [],
                                         'allies': [], 'rivals': [], 'origin': 'user'}, edit))
    return found


def faction_edited(faction: dict, edit: dict) -> dict:
    found = {**faction, 'added': list(edit.get('added', [])), 'removed': list(edit.get('removed', [])),
             'sides': dict(edit.get('lines', {}))}
    for key in ('name', 'kind', 'about', 'pull'):
        if edit.get(key) not in (None, ''):
            found[key] = edit[key]
    found['base_pull'] = found['pull']
    return found


def belongs(person: dict, faction: dict) -> bool:
    if person['key'] in faction.get('removed', ()):
        return False
    return person['key'] in faction.get('added', ()) or politics.joins(person, faction)


def member_of(person: dict, factions: list[dict]) -> list[dict]:
    return [faction for faction in factions if belongs(person, faction)]


def faction_line(faction: dict, issue: dict) -> int | None:
    """The side a faction takes: the user's say-so, else its kinds' (world/politics.py `line`)."""
    if issue['id'] in faction.get('sides', {}):
        return faction['sides'][issue['id']]
    return politics.line(faction, issue)


# --- How the town splits and how an issue settles ---

def split(issue: dict, people: list[dict], factions: list[dict], beats: list[dict], overrides: dict) -> dict:
    """How the townsfolk who stand for the town see an issue: counts for each side and of those who don't care."""
    counts = {'first': 0, 'second': 0, 'neither': 0}
    for person in people:
        view = overrides.get((issue['id'], person['key']))
        if view is None:
            view = politics.view_of(person, with_lines(issue, factions), member_of(person, factions), beats)
        counts['first' if view > 0 else 'second' if view < 0 else 'neither'] += 1
    return counts


def with_lines(issue: dict, factions: list[dict]) -> dict:
    """The issue as views read it, with any side a faction was told to take counted as backing it."""
    sides = [{**side, 'backers': list(side.get('backers', []))} for side in issue['sides']]
    told = [(faction, faction['sides'][issue['id']]) for faction in factions if issue['id'] in faction.get('sides', {})]
    for faction, side in told:
        sides[side]['backers'] += faction['tags'] or [f"faction:{faction['id']}"]
    return {**issue, 'sides': sides}


def outcome_odds(issue: dict, counts: dict, factions: list[dict], drama: int) -> list[dict]:
    """Odds for the three ways a local issue can go, with the reasons that moved them."""
    texts = issue['beats_text']
    viewed = counts['first'] + counts['second'] or 1
    weights = [max(counts['first'] / viewed, 0.05), max(counts['second'] / viewed, 0.05)]
    reasons = [[f"{round(100 * counts['first'] / viewed)}% of people with a view wanted to {issue['sides'][0]['stand']}"],
               [f"{round(100 * counts['second'] / viewed)}% of people with a view wanted to {issue['sides'][1]['stand']}"]]
    for faction in factions:
        side = faction_line(faction, issue)
        if side is not None:
            weights[side] *= 1 + 0.12 * faction['pull']
            reasons[side].append(f"{faction['name']} backed it")
    total_people = sum(counts.values()) or 1
    fizzle = FIZZLE[drama] + 0.4 * counts['neither'] / total_people
    fizzle_reasons = ['most people did not much care'] if counts['neither'] * 2 > total_people else []
    weights.append(fizzle)
    reasons.append(fizzle_reasons)
    labels = [texts.get('won') or f"It went the way of those who wanted to {issue['sides'][0]['stand']}.",
              texts.get('lost') or f"It went the way of those who wanted to {issue['sides'][1]['stand']}.",
              texts.get('fizzled') or 'It fizzled out.']
    total = sum(weights)
    return [{'option': index, 'odds': round(weight / total, 3), 'reasons': why,
             'moves': ['more' if index < 2 else 'possible'] * len(why), 'label': label}
            for index, (weight, why, label) in enumerate(zip(weights, reasons, labels, strict=True))]


def settle(issue: dict, counts: dict, factions: list[dict], drama: int) -> dict:
    options = outcome_odds(issue, counts, factions, drama)
    picked = consequences.roll(f"politics:{issue['id']}", options)
    if issue.get('outcome') is not None:
        return {'options': options, 'picked': issue['outcome'], 'picked_by': 'user'}
    return {'options': options, 'picked': picked, 'picked_by': 'dice'}


# --- Faction fortunes ---

def results(issues: list[dict], day: date, days: int) -> list[tuple[dict, int]]:
    """Issues settled one way or the other within `days` of `day`, with the side that won."""
    since = (day - timedelta(days=days)).isoformat()
    found = []
    for issue in issues:
        settled = issue.get('settled')
        if settled and settled['picked'] < 2 and since <= issue['settled_on'] <= day.isoformat():
            found.append((issue, settled['picked']))
    return found


def fortunes(factions: list[dict], issues: list[dict], day: date) -> None:
    """Pull rises with a recent win and falls with a recent loss, one step at most either way."""
    won = results(issues, day, PULL_DAYS)
    for faction in factions:
        score = sum((1 if side == faction_line(faction, issue) else -1) for issue, side in won
                    if faction_line(faction, issue) is not None)
        faction['pull'] = min(max(faction['base_pull'] + max(min(score, 1), -1), 1), 5)
        faction['change'] = faction['pull'] - faction['base_pull']


def stance(data: dict, first: dict, second: dict, day: date, drama: int, won: list, overrides: dict) -> dict:
    a, b = sorted((first['id'], second['id']))
    if (a, b) in overrides:
        return {'stance': overrides[(a, b)], 'by': 'you'}
    found = politics.drifted(data, first, second, day, drama)
    together = sum(1 if faction_line(first, issue) == faction_line(second, issue) else -1 for issue, _ in won
                   if faction_line(first, issue) is not None and faction_line(second, issue) is not None)
    return {'stance': min(max(found + max(min(together, 1), -1), -2), 2), 'by': 'world'}


def relations(data: dict, factions: list[dict], issues: list[dict], day: date, drama: int, overrides: dict) -> list:
    won = results(issues, day, RELATION_DAYS)
    found = []
    for index, first in enumerate(factions):
        for second in factions[index + 1:]:
            found.append({'a': first['id'], 'b': second['id'],
                          **stance(data, first, second, day, drama, won, overrides)})
    return found


# --- The whole picture ---

def town(connection, data: dict, day: date) -> dict:
    """The city's politics on `day`: its live issues (with how the town splits and how settled ones went), its
    factions (with pull and who they stand with) and the levels it runs at."""
    level_, drama = level(connection), world_drama.level(connection)
    factions = city_factions(connection, data) if level_ else []
    overrides = view_overrides(connection, data['id'])
    people = politics.sample(data, day) if level_ else []
    issues = []
    for issue in city_issues(connection, data, day, level_, drama):
        issues.append(shown(issue, data, day, people, factions, overrides, drama))
    fortunes(factions, issues, day)
    links = relations(data, factions, issues, day, drama, relation_overrides(connection, data['id']))
    return {'level': level_, 'drama': drama, 'city': {'id': data['id'], 'name': data['name']}, 'issues': issues,
            'factions': factions, 'relations': links, 'people': people}


def shown(issue: dict, data: dict, day: date, people: list, factions: list, overrides: dict, drama: int) -> dict:
    """One issue with its stage, beats, split and, once settled, how it went."""
    if issue['kind'] == 'era':
        beats = issue['beats']
        found = {**issue, 'stage': 'ended' if ended(issue) else issue['stage']}
    else:
        beats = politics.local_beats(issue, day) if issue['origin'] != 'user' else []
        found = {**issue, 'stage': politics.stage_on(issue, day), 'beats': beats}
    found['split'] = split(issue, people, factions, beats, overrides)
    if issue['kind'] == 'local' and (found['stage'] == 'settled' or issue.get('outcome') is not None):
        at_heat = date.fromisoformat(min(issue['dates']['heated'], day.isoformat()))
        heat_beats = [beat for beat in beats if beat['on'] <= at_heat.isoformat()]
        counts = split(issue, people, factions, heat_beats, overrides)
        found['settled'] = settle(issue, counts, factions, drama)
        found['settled_on'] = issue.get('ended') or issue['dates']['settled']
        found['stage'] = 'settled'
        found['beats'] = [*beats, {'on': found['settled_on'], 'stage': 'settled', 'favors': None,
                                   'text': found['settled']['options'][found['settled']['picked']]['label']}]
    elif ended(issue):
        found['stage'] = 'settled'
        found['settled_on'] = issue.get('ended')
        found['settled'] = None
    return found


# --- People the companion knows ---

def companion_person(companion: dict) -> dict:
    definition = companion['version']['definition']
    text = consequences.sheet_text(definition)
    groups = politics.words_of(text)
    if consequences.sheet_has(definition, 'stubborn') or consequences.sheet_has(definition, 'assertive'):
        groups.add('strong')
    return {'key': pairs.companion_key(companion['id']), 'name': companion['version']['name'],
            'jobs': politics.jobs_of(text), 'groups': groups, 'text': text, 'age': None, 'home': None,
            'kind': 'companion', 'companion_id': companion['id']}


def circle_person(row: dict) -> dict:
    details = decode(row['details']) or {}
    return {'key': row['seed'], 'name': row['name'], 'role': row['role'], 'jobs': politics.jobs_of(details.get('career', '')),
            'groups': set(), 'temperament': pick(row['seed'], 'politics-temper', TEMPERAMENTS),
            'age': details.get('age'), 'home': details.get('neighborhood'), 'kind': 'circle',
            'close': pairs.role_default(row['role'], row['seed'])['level']}


def known(connection, companion: dict, now) -> list[dict]:
    """The people whose views a companion knows: their circle and the other companions they know."""
    rows = circle.people(connection, companion['active_timeline_id'])
    found = [circle_person(row) for row in rows]
    for key in pairs.known_companions(connection, companion, now):
        from companion.characters import by_id
        other = by_id(connection, pairs.companion_id(key))
        if other:
            found.append(companion_person(other) | {'close': pairs.closeness(connection, pairs.companion_key(
                companion['id']), key, now) or 1})
    return found


def view(person: dict, issue: dict, factions: list[dict], overrides: dict, pulled: list[dict] = ()) -> dict:
    """Someone's view on an issue: the user's say-so, else the rules', nudged toward close people who feel strongly."""
    set_by_you = overrides.get((issue['id'], person['key']))
    if set_by_you is not None:
        return {'view': set_by_you, 'by': 'you'}
    value = politics.score(person, with_lines(issue, factions), member_of(person, factions), issue.get('beats', []))
    for other in pulled:
        if other.get('close', 0) >= CLOSE and abs(other['view']) == 2 and unit(person['key'], other['key'], issue['id']) < 0.5:
            value += 0.35 if other['view'] > 0 else -0.35
    return {'view': politics.view_from(value), 'by': 'world'}


def views_for(connection, companion: dict, picture: dict, now) -> dict:
    """The companion's own views and factions, and those of the people they know, for Today and their chat."""
    overrides = view_overrides(connection, picture['city']['id'])
    factions = picture['factions']
    me = companion_person(companion)
    people = known(connection, companion, now)
    result = {'companion': {**me, 'factions': [f['id'] for f in member_of(me, factions)], 'views': {}}, 'people': []}
    for person in people:
        person['factions'] = [faction['id'] for faction in member_of(person, factions)]
        person['views'] = {issue['id']: view(person, issue, factions, overrides) for issue in picture['issues']}
    for issue in picture['issues']:
        pulled = [{**person, 'view': person['views'][issue['id']]['view']} for person in people]
        result['companion']['views'][issue['id']] = view(me, issue, factions, overrides, pulled)
    result['people'] = people
    return result


# --- The user's changes ---

def require_issue(connection, data: dict, issue_id: str, day: date) -> dict:
    found = next((issue for issue in city_issues(connection, data, day, max(level(connection), 1),
                                                 world_drama.level(connection)) if issue['id'] == issue_id), None)
    if found is None:
        row = optional(connection, 'SELECT * FROM politics_issues WHERE city_id=? AND issue_id=?', (data['id'], issue_id))
        require(row is not None, 'That issue is not going on in this city.', 404)
        return user_issue(issue_id, decode(row['data'])) if row['origin'] == 'user' else {'id': issue_id}
    return found


def save_issue(connection, city_id: str, issue_id: str, origin: str, data: dict, timestamp: str, dismissed=False):
    connection.execute(
        'INSERT INTO politics_issues (city_id, issue_id, origin, data, dismissed, created_at, updated_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(city_id, issue_id) DO UPDATE SET data=excluded.data, '
        'dismissed=excluded.dismissed, updated_at=excluded.updated_at',
        (city_id, issue_id, origin, encode(data), int(dismissed), timestamp, timestamp))


def add_issue(connection, data: dict, body: dict, day: date, timestamp: str) -> str:
    """An issue of the user's own, open from today; sides need a name, and say what each side wants."""
    names = [name.strip() for name in body['sides']]
    require(len(names) == 2 and all(names) and names[0].casefold() != names[1].casefold(),
            'Give the two sides different names.', 422)
    stands = [(stand or '').strip() or f'side with {name}' for name, stand in zip(names, body.get('stands') or ['', ''],
                                                                                  strict=True)]
    issue_id = f'own-{identifier()[:12]}'
    save_issue(connection, data['id'], issue_id, 'user', {
        'title': body['title'].strip(), 'question': (body.get('question') or '').strip() or body['title'].strip(),
        'sides': names, 'stands': stands, 'started': day.isoformat()}, timestamp)
    return issue_id


def change_issue(connection, data: dict, issue_id: str, changes: dict, day: date, timestamp: str) -> None:
    """Rename an issue or its sides, say how it settled (0 or 1 for a side, 2 fizzled; None undoes it), end it, or put
    it away for good."""
    issue = require_issue(connection, data, issue_id, day)
    row = optional(connection, 'SELECT * FROM politics_issues WHERE city_id=? AND issue_id=?', (data['id'], issue_id))
    current = decode(row['data']) if row else {}
    origin = row['origin'] if row else 'edit'
    if 'outcome' in changes:
        require(changes['outcome'] is None or issue.get('kind') == 'local' or changes['outcome'] == 2 or origin == 'user',
                'A big question of the era does not settle; end it instead.', 422)
    for key in ('title', 'question', 'outcome'):
        if key in changes:
            current[key] = changes[key]
    if 'stage' in changes:
        require(issue.get('kind') == 'local', 'History sets how hot a big question of the era gets.', 422)
        current['stage'], current['stage_on'] = changes['stage'], day.isoformat()
    if changes.get('sides'):
        current['sides'] = [name.strip() for name in changes['sides']][:2]
    if 'ended' in changes:
        current['ended'] = day.isoformat() if changes['ended'] else None
    save_issue(connection, data['id'], issue_id, origin, current, timestamp,
               changes.get('dismissed', bool(row and row['dismissed'])))


def remove_issue(connection, data: dict, issue_id: str, day: date, timestamp: str) -> dict:
    """Delete the user's own issue, or put a seeded one away so it never comes back."""
    if connection.execute("DELETE FROM politics_issues WHERE city_id=? AND issue_id=? AND origin='user'",
                          (data['id'], issue_id)).rowcount:
        connection.execute('DELETE FROM politics_views WHERE city_id=? AND issue_id=?', (data['id'], issue_id))
        return {'deleted': issue_id}
    change_issue(connection, data, issue_id, {'dismissed': True}, day, timestamp)
    return {'dismissed': issue_id}


def set_view(connection, city_id: str, issue_id: str, person: str, value: int | None, timestamp: str) -> None:
    if value is None:
        connection.execute('DELETE FROM politics_views WHERE city_id=? AND issue_id=? AND person=?',
                           (city_id, issue_id, person))
        return
    require(value in politics.VIEWS, 'A view runs from -2 to 2.', 422)
    connection.execute('INSERT INTO politics_views (city_id, issue_id, person, view, updated_at) VALUES (?, ?, ?, ?, ?) '
                       'ON CONFLICT(city_id, issue_id, person) DO UPDATE SET view=excluded.view, '
                       'updated_at=excluded.updated_at', (city_id, issue_id, person, value, timestamp))


def save_faction(connection, city_id: str, faction_id: str, origin: str, data: dict, timestamp: str,
                 dismissed=False):
    connection.execute(
        'INSERT INTO politics_factions (city_id, faction_id, origin, data, dismissed, created_at, updated_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(city_id, faction_id) DO UPDATE SET data=excluded.data, '
        'dismissed=excluded.dismissed, updated_at=excluded.updated_at',
        (city_id, faction_id, origin, encode(data), int(dismissed), timestamp, timestamp))


def add_faction(connection, data: dict, body: dict, timestamp: str) -> str:
    name = body['name'].strip()
    require(bool(name), 'Give the faction a name.', 422)
    taken = {faction['name'].casefold() for faction in city_factions(connection, data)}
    require(name.casefold() not in taken, f'{data["name"]} already has {name}.', 409)
    faction_id = 'own-' + '-'.join(''.join(ch for ch in name.lower() if ch.isalnum() or ch == ' ').split())[:40]
    save_faction(connection, data['id'], faction_id, 'user', {
        'name': name, 'kind': (body.get('kind') or '').strip() or 'faction', 'about': (body.get('about') or '').strip(),
        'pull': body.get('pull') or 2}, timestamp)
    return faction_id


def change_faction(connection, data: dict, faction_id: str, changes: dict, timestamp: str) -> None:
    """Rename a faction, change what it is about or its pull, add or take away a member, say which side it takes on an
    issue, or put it away."""
    known_ids = {faction['id'] for faction in politics.factions(data)}
    row = optional(connection, 'SELECT * FROM politics_factions WHERE city_id=? AND faction_id=?', (data['id'], faction_id))
    if row is None and faction_id not in known_ids:
        raise DomainError('That faction is not in this city.', 404, 'unknown_faction')
    current = decode(row['data']) if row else {}
    for key in ('name', 'kind', 'about', 'pull'):
        if changes.get(key) not in (None, ''):
            current[key] = changes[key].strip() if isinstance(changes[key], str) else changes[key]
    members(current, changes)
    if changes.get('issue'):
        lines = dict(current.get('lines', {}))
        if changes.get('side') is None:
            lines.pop(changes['issue'], None)
        else:
            lines[changes['issue']] = changes['side']
        current['lines'] = lines
    save_faction(connection, data['id'], faction_id, row['origin'] if row else 'edit', current, timestamp,
                 changes.get('dismissed', bool(row and row['dismissed'])))


def members(current: dict, changes: dict) -> None:
    added, removed = set(current.get('added', [])), set(current.get('removed', []))
    if changes.get('add_member'):
        added.add(changes['add_member'])
        removed.discard(changes['add_member'])
    if changes.get('remove_member'):
        removed.add(changes['remove_member'])
        added.discard(changes['remove_member'])
    current['added'], current['removed'] = sorted(added), sorted(removed)


def remove_faction(connection, data: dict, faction_id: str, timestamp: str) -> dict:
    if connection.execute("DELETE FROM politics_factions WHERE city_id=? AND faction_id=? AND origin='user'",
                          (data['id'], faction_id)).rowcount:
        connection.execute('DELETE FROM politics_relations WHERE city_id=? AND (first=? OR second=?)',
                           (data['id'], faction_id, faction_id))
        return {'deleted': faction_id}
    change_faction(connection, data, faction_id, {'dismissed': True}, timestamp)
    return {'dismissed': faction_id}


def set_relation(connection, city_id: str, a: str, b: str, value: int | None, timestamp: str) -> None:
    require(a != b, 'Pick two different factions.', 422)
    first, second = sorted((a, b))
    if value is None:
        connection.execute('DELETE FROM politics_relations WHERE city_id=? AND first=? AND second=?',
                           (city_id, first, second))
        return
    require(value in politics.STANCES, 'How two factions stand runs from -2 to 2.', 422)
    connection.execute('INSERT INTO politics_relations (city_id, first, second, stance, updated_at) VALUES (?, ?, ?, ?, ?) '
                       'ON CONFLICT(city_id, first, second) DO UPDATE SET stance=excluded.stance, '
                       'updated_at=excluded.updated_at', (city_id, first, second, value, timestamp))


# --- Chat ---

# Arm C of the A/B in /mnt/project-files/companion-politics-ab/report.md: as true to the views as the longer heading,
# and half as likely to bring politics into a talk about something else.
HEADING = ('Local politics people are arguing about (decided by the app: these are your own views and the views of '
           'people you know; keep to them, bring politics up only when it fits, and never invent how an open issue ends)')
# People whose views a companion mentions per issue, by the Realism level.
PEOPLE_PER_ISSUE = (0, 0, 2, 3)


def you_text(view: int, issue: dict) -> str:
    if view == 0:
        return "You don't much care either way."
    side = issue['sides'][0 if view > 0 else 1]
    return f"You want to {side['stand']}, and you say so." if abs(view) == 2 else f"You would rather {side['stand']}."


def leaning(issue: dict) -> str:
    counts = issue['split']
    first, second = counts['first'], counts['second']
    if not first + second:
        return 'Around town hardly anyone cares'
    if abs(first - second) <= 0.1 * (first + second):
        return 'Around town people are split down the middle'
    side = issue['sides'][0 if first > second else 1]['name']
    tail = ', though most people do not much care' if counts['neither'] > first + second else ''
    return f'Around town it leans {side}{tail}'


def latest(issue: dict) -> str:
    beat = issue['beats'][-1] if issue.get('beats') else None
    if not beat:
        return ''
    day = date.fromisoformat(beat['on'])
    return f" Latest ({day:%b} {day.day}): {beat['text'].rstrip('.')}."


def person_label(person: dict) -> str:
    return f"{person['name']} ({person['role']})" if person.get('role') else person['name']


def others_text(issue: dict, mine: int, people: list[dict], most: int) -> str:
    """People they know who feel strongly, the ones who disagree with them first."""
    strong = [person for person in people if abs(person['views'][issue['id']]['view']) == 2]
    strong.sort(key=lambda person: (person['views'][issue['id']]['view'] * mine > 0, -person.get('close', 0)))
    return ''.join(f" {person_label(person)} {politics.view_text(person['views'][issue['id']]['view'], issue)}."
                   for person in strong[:most])


def issue_line(issue: dict, mine: int, people: list[dict], most: int) -> str:
    if issue['stage'] == 'settled':
        how = issue['settled']['options'][issue['settled']['picked']]['label'] if issue.get('settled') else 'It is over.'
        return f"- {issue['title']} (settled): {how} {you_text(mine, issue)}"
    stage = {'whispers': ' (only a rumor so far)', 'heated': ' (it is getting heated)'}.get(issue['stage'], '')
    return (f"- {issue['title']}{stage}: {issue['question']} {leaning(issue)}. {you_text(mine, issue)}"
            f"{others_text(issue, mine, people, most)}{latest(issue)}")


def faction_line_text(faction_ids: list[str], picture: dict) -> str | None:
    names = {faction['id']: faction['name'] for faction in picture['factions']}
    mine = [names[faction_id] for faction_id in faction_ids if faction_id in names]
    if not mine:
        return None
    return f"- You belong to {', '.join(mine)}."


def context_lines(connection, companion: dict, now) -> list[tuple[str, str]]:
    """The 'politics' section: the city's live issues with their own view, and the people they know who feel
    strongly; the factions they belong to."""
    from companion.life import network, storylines
    level_ = level(connection) if ACTIVE else 0
    data = network.city(connection, companion) if level_ else {}
    if not level_ or not data.get('neighborhoods'):
        return []
    day = storylines.local_today(companion, now)
    picture = town(connection, data, day)
    views = views_for(connection, companion, picture, now)
    lines = []
    for issue in picture['issues']:
        mine = views['companion']['views'][issue['id']]['view']
        lines.append((f"politics:{issue['id']}:{issue['stage']}:{mine}:{len(issue.get('beats', []))}",
                      issue_line(issue, mine, views['people'], PEOPLE_PER_ISSUE[level_])))
    if text := faction_line_text(views['companion']['factions'], picture):
        lines.append(('politics:factions:' + ','.join(views['companion']['factions']), text))
    return lines


def offer(packet, connection, companion: dict, now, group=None) -> None:
    """Adds the 'politics' section, in a 1:1 chat and in a group (where their views can clash)."""
    if not companion.get('active_timeline_id'):
        return
    for identity, text in context_lines(connection, companion, now):
        packet.offer('politics', identity, text)


# --- The town paper ---

def paper_items(connection, data: dict, week: tuple[date, date]) -> list[dict]:
    """The week's political news for the town paper: what happened in each issue, and factions falling out or
    joining forces."""
    if not ACTIVE or not level(connection) or not data.get('neighborhoods'):
        return []
    picture = town(connection, data, week[1])
    found = []
    for issue in picture['issues']:
        for beat in issue.get('beats', []):
            if week[0].isoformat() <= beat['on'] <= week[1].isoformat():
                found.append({'key': f"{issue['id']}:{beat['on']}", 'headline': issue['title'],
                              'text': beat['text'], 'date': beat['on']})
    found += relation_news(connection, data, picture, week)
    return sorted(found, key=lambda item: item['date'])


RELATION_NEWS = {2: '{a} and {b} join forces', 1: '{a} and {b} make peace', -1: '{a} and {b} fall out',
                 -2: '{a} and {b} are at open odds'}


def relation_news(connection, data: dict, picture: dict, week: tuple[date, date]) -> list[dict]:
    before = {(link['a'], link['b']): link['stance'] for link in town(connection, data, week[0])['relations']}
    names = {faction['id']: faction['name'] for faction in picture['factions']}
    found = []
    for link in picture['relations']:
        was = before.get((link['a'], link['b']))
        if was is None or was == link['stance'] or link['by'] == 'you':
            continue
        warmer = link['stance'] > was
        key = link['stance'] if (warmer and link['stance'] > 0) or (not warmer and link['stance'] < 0) else None
        if key is None:
            continue
        text = RELATION_NEWS[key].format(a=names[link['a']], b=names[link['b']])
        found.append({'key': f"relation:{link['a']}:{link['b']}:{week[1]}", 'headline': text[0].upper() + text[1:],
                      'text': '', 'date': week[1].isoformat()})
    return found


# --- Today ---

def person_view(person: dict, issues: list[dict]) -> dict:
    return {'key': person['key'], 'name': person['name'], 'role': person.get('role') or '', 'kind': person['kind'],
            'factions': person['factions'], 'views': person['views']}


def today_view(connection, companion: dict, data: dict, now) -> dict:
    """Talk of the town on Today: the issues, the factions and where the companion and their people stand."""
    from companion.life import storylines
    day = storylines.local_today(companion, now)
    level_ = level(connection)
    if not level_ or not data.get('neighborhoods'):
        return {'level': level_, 'city': {'id': data.get('id'), 'name': data.get('name')}, 'issues': [], 'factions': [],
                'relations': [], 'companion': None, 'people': []}
    picture = town(connection, data, day)
    views = views_for(connection, companion, picture, now)
    me = views['companion']
    known_people = {person['key'] for person in [me, *views['people']]}
    factions = [{key: faction[key] for key in ('id', 'name', 'kind', 'about', 'pull', 'base_pull', 'change', 'origin')}
                | {'members': sorted(key for key in known_people if key in faction_member_keys(faction, me, views)),
                   'sides': faction.get('sides', {})} for faction in picture['factions']]
    issues = [{key: issue.get(key) for key in ('id', 'kind', 'title', 'question', 'sides', 'stage', 'beats', 'split',
                                                'settled', 'settled_on', 'real', 'origin', 'started', 'stage_by')}
              | {'lines': {faction['id']: faction_line(faction, issue) for faction in picture['factions']},
                 'edited': bool(issue.get('edited'))} for issue in picture['issues']]
    return {'level': level_, 'city': picture['city'], 'issues': issues, 'factions': factions,
            'relations': picture['relations'],
            'companion': {'key': me['key'], 'name': me['name'], 'factions': me['factions'], 'views': me['views']},
            'people': [person_view(person, picture['issues']) for person in views['people']]}


def faction_member_keys(faction: dict, me: dict, views: dict) -> set[str]:
    return {person['key'] for person in [me, *views['people']] if faction['id'] in person['factions']}
