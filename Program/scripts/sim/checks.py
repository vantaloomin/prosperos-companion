"""Checks over what drive.py saved, one per bug class testers found (scripts/sim/README.md): worlds that are not
today's Earth showing Earth-only things, what the user set by hand read as fresh or app-made or lost, app-made and
user-made people clashing, companions not noticing each other, and errors the app gave."""
import json
import re
from collections import Counter
from pathlib import Path

import worlds as plan

SEVERITY = {'high': 0, 'medium': 1, 'low': 2}
# Words that belong to today's Earth, by what a world is: `tech` for any world before today's (medieval, fantasy),
# `earth` for any made-up world, `ground` for a ship or station.
WORDS = {
    'tech': r'smart ?phones?|iphone|instagram|tiktok|netflix|spotify|youtube|podcasts?|e-?mails?|laptops?|computers?|'
            r'wi-?fi|internet|online|uber|lyft|cars?|drove|driving|highways?|freeways?|subway|airports?|flights?|'
            r'airplanes?|television|tv|movies?|cinema|video games?|playstation|xbox|starbucks|mcdonald\'?s|walmart|'
            r'amazon|software|data analyst|credit cards?|selfies?|gym|yoga|jiu-?jitsu|photography|camera|'
            r'electricity|plastic|streaming|playlist|spreadsheets?|zoom call|pizza|sushi|tacos?|takeout|take-out',
    'earth': r'america|american|usa|united states|chicago|new york|california|texas|paris|tokyo|europe|european|'
             r'thanksgiving|halloween|fourth of july|valentine\'?s|black friday|super bowl|dollars?|nfl|nba',
    'ground': r'rain(?:ing|y)?|snow(?:ing|y)?|sunny|sunshine|weather|umbrella|winter coat|backyard|back yard|horses?|'
              r'cars?|drove|driving|highways?|barbecue|bbq|beach|forecast|thunder',
}
KINDS = {'town': (), 'ship': ('earth', 'ground'), 'camelot': ('tech',), 'grandport': ('tech', 'earth'),
         'own-city': ('tech', 'earth')}
# Keys whose strings are ids, dates or settings, not words a screen shows.
SKIP_KEYS = {'id', 'key', 'refs', 'sources', 'data_version', 'seed', 'created_at', 'updated_at', 'kinds', 'options',
             'choices', 'presets', 'url', 'path', 'image', 'avatar', 'timezone', 'schema_version', 'icon'}
# Settings, and what the stand-in model wrote (chats and groups).
SKIP_PATHS = ('/api/settings', '/api/life/settings', '/api/notifications/settings', '/api/conversation', '/api/chats',
              '/api/groups')
SLOTS = {'mother': {'mom', 'mother', 'mum'}, 'father': {'dad', 'father'}, 'spouse': {'wife', 'husband', 'spouse'}}
JUST_STARTED = re.compile(r'just (?:started|starting|took up|picked up)|new to|first (?:week|time)|starting out|'
                          r'first steps', re.IGNORECASE)


class Findings:
    def __init__(self):
        self.items = []

    def add(self, world, severity, kind, title, seen):
        self.items.append({'world': world, 'severity': severity, 'kind': kind, 'title': title, 'seen': seen})


def load(out: Path, name: str, label: str):
    path = out / name / f'{label}.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def strings(value, path=''):
    """Every string a screen could show, with where it came from."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key not in SKIP_KEYS:
                yield from strings(item, f'{path}.{key}')
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from strings(item, f'{path}[{index}]')
    elif isinstance(value, str) and ' ' in value.strip():
        yield path, value


def named(snapshot, companion_id):
    companion = ((snapshot['companions'].get(companion_id) or {}).get('/api/companion') or {}).get('companion') or {}
    return (companion.get('version') or {}).get('name') or companion_id[:6]


def own_words(name: str) -> set[str]:
    """Words the world's own companions were written with, which never count against it."""
    text = ' '.join(str(value) for definition in plan.WORLDS[name]['companions'] for value in definition.values())
    return {word.casefold() for word in re.findall(r'\w+', text)}


def screens_of(snapshot):
    """Each endpoint's answer with whose screen it was: every companion's, then the shared ones."""
    for companion_id, screens in snapshot['companions'].items():
        for endpoint, value in screens.items():
            yield f'{named(snapshot, companion_id)}: ', endpoint, value
    for endpoint, value in snapshot['shared'].items():
        yield '', endpoint, value


def earth_words(found: Findings, name: str, snapshot):
    kinds = KINDS.get(name, ())
    if not kinds:
        return
    pattern = re.compile(r'\b(?:' + '|'.join(WORDS[kind] for kind in kinds) + r')\b', re.IGNORECASE)
    own, hits = own_words(name), {}
    for whose, endpoint, value in screens_of(snapshot):
        if endpoint.startswith(SKIP_PATHS):
            continue
        for where, text in strings(value):
            for word in {match.group(0).casefold() for match in pattern.finditer(text)} - own:
                hits.setdefault(endpoint, {}).setdefault(word, []).append(f'{whose}{where}: {text[:160]}')
    for endpoint, words in sorted(hits.items()):
        found.add(name, 'medium', 'world-fit', f'{endpoint} shows words that do not fit this world: '
                  f"{', '.join(sorted(words))}", [line for seen in words.values() for line in seen[:2]][:8])


def single_places(found: Findings, name: str, snapshot):
    """Nobody has two moms: one person at most in each place only one person holds."""
    for companion_id, screens in snapshot['companions'].items():
        people = [p for p in screens.get('/api/life/circle') or [] if p.get('status', 'active') == 'active']
        for slot, words in SLOTS.items():
            holders = [f"{p['name']} ({p['role']})" for p in people if p['role'].casefold() in words]
            if len(holders) > 1:
                found.add(name, 'high', 'app-vs-user', f'{named(snapshot, companion_id)} has more than one {slot}',
                          holders)


def jobs(found: Findings, name: str, snapshot):
    for companion_id, screens in snapshot['companions'].items():
        people = screens.get('/api/life/circle') or []
        young = [f"{p['name']}, {p.get('age')}, {p['role']}" for p in people
                 if p.get('career') == 'Retired' and (p.get('age') or 0) < 55 and not p.get('kind', {}).get('own')]
        if young:
            found.add(name, 'high', 'world-data', f"Young people in {named(snapshot, companion_id)}'s circle are "
                      '"Retired": the city has no jobs for them', young)


def kept_by_hand(found: Findings, name: str, before, later):
    """What the user set by hand is still there, as they set it, and does not read as new."""
    main = next(iter(later['companions']))
    screens = later['companions'][main]
    hobbies = (screens.get('/api/life/hobbies') or {}).get('hobbies') or []
    mine = [h for h in hobbies if h['label'].casefold() == plan.HOBBY_BY_HAND.casefold()]
    if not mine:
        found.add(name, 'high', 'user-values', f'The pastime added by hand ({plan.HOBBY_BY_HAND}) is gone', [])
    else:
        text = ' '.join(str(mine[0].get(key) or '') for key in ('level_text', 'since_text', 'status_text'))
        if JUST_STARTED.search(text):
            found.add(name, 'high', 'user-values', 'The pastime added by hand reads as just started', [text])
    edits = before or {}
    circle = {p['id']: p for p in screens.get('/api/life/circle') or []}
    friend = circle.get(edits.get('friend_id'))
    if edits.get('friend_id') and not friend:
        found.add(name, 'high', 'user-values', 'The friend the user edited left the circle', [])
    elif friend:
        if friend.get('age') not in (plan.FRIEND_AGE_BY_HAND, plan.FRIEND_AGE_BY_HAND + 1):
            found.add(name, 'high', 'user-values', 'The age set by hand changed',
                      [f"set {plan.FRIEND_AGE_BY_HAND}, now {friend.get('age')}"])
        if friend.get('career') != plan.JOB_BY_HAND['job']:
            found.add(name, 'high', 'user-values', 'The job set by hand changed',
                      [f"set {plan.JOB_BY_HAND['job']}, now {friend.get('career')}"])
        if plan.PET_BY_HAND['name'] not in [pet.get('name') for pet in friend.get('pets') or []]:
            found.add(name, 'high', 'user-values', 'The pet added by hand to a friend is gone',
                      [str(friend.get('pets'))[:200]])
    pets = (screens.get('/api/life/pets') or {}).get('pets') or []
    if 'Pickle' not in [pet.get('name') for pet in pets]:
        found.add(name, 'high', 'user-values', "The companion's pet added by hand is gone",
                  [str([p.get('name') for p in pets])])
    if 'Hollis' not in [p['name'] for p in circle.values()]:
        found.add(name, 'high', 'user-values', 'The mom added by hand is gone', [])


def ages(found: Findings, name: str, snapshot):
    for companion_id, screens in snapshot['companions'].items():
        people = [p for p in screens.get('/api/life/circle') or [] if not (p.get('kind') or {}).get('own')]
        counted = Counter(p.get('age') for p in people)
        same, count = counted.most_common(1)[0] if counted else (None, 0)
        if count >= 4:
            found.add(name, 'medium', 'app-data', f"{count} people in {named(snapshot, companion_id)}'s circle are "
                      f'all {same}', [f"{p['name']} ({p['role']})" for p in people if p.get('age') == same])


def ship_pets(found: Findings, name: str, snapshot):
    if not plan.WORLDS[name].get('aboard'):
        return
    ground = sorted({kind['label'] for screens in snapshot['companions'].values()
                     for kind in (screens.get('/api/life/pets') or {}).get('kinds') or []
                     if re.search(r'chicken|horse|stable|backyard|dog', kind['label'])})
    if ground:
        found.add(name, 'medium', 'world-fit', 'Aboard a ship, the pet picker offers pets with no room aboard', ground)
    for companion_id, screens in snapshot['companions'].items():
        for person in screens.get('/api/life/circle') or []:
            for pet in person.get('pets') or []:
                if re.search(r'chicken|horse|dog', pet.get('kind') or ''):
                    found.add(name, 'medium', 'world-fit', f"{person['name']} keeps a {pet['kind']} aboard",
                              [str(pet)[:160]])


def together(found: Findings, name: str, snapshot, ids):
    """Every companion reacts to the user's own post, and companions who know each other react to each other's."""
    feed = snapshot['shared'].get('/api/feed') or {}
    posts = feed.get('posts') or feed.get('items') or (feed if isinstance(feed, list) else [])
    mine = [post for post in posts if (post.get('author') or {}).get('kind') == 'user']
    if not mine:
        found.add(name, 'high', 'multi-companion', "The user's own post is not in the feed", [])
        return
    names = [named(snapshot, companion_id) for companion_id in ids]
    post = mine[0]
    said = json.dumps(post.get('audience') or {})
    quiet = [companion for companion in names if companion.split()[0] not in said]
    if quiet:
        # Each companion joins in by chance, likelier the closer they are (life/user_posts.py): worth a look only
        # when it keeps happening across runs.
        found.add(name, 'low', 'multi-companion', "Companions who never reacted to the user's own post",
                  quiet + [said[:300]])
    theirs = [post for post in posts if (post.get('author') or {}).get('kind') == 'companion']
    reacted = [post for post in theirs if any(other.split()[0] in json.dumps(post.get('audience') or {})
                                              for other in names if other != post['author'].get('name'))]
    if len(ids) > 1 and theirs and not reacted:
        found.add(name, 'low', 'multi-companion', f'None of {len(theirs)} companion posts got a like or comment '
                  'from another companion', [])


def strangers(found: Findings, name: str, snapshot):
    for companion_id, screens in snapshot['companions'].items():
        companion = (screens.get('/api/companion') or {}).get('companion') or {}
        definition = (companion.get('version') or {}).get('definition') or {}
        stage = json.dumps(screens.get('/api/closeness') or {})
        if definition.get('starting_closeness', 1) == 1 and re.search(r'"(?:name|label|stage)": "Friends"', stage):
            found.add(name, 'medium', 'user-values', f'{named(snapshot, companion_id)} started at Just met but '
                      'closeness says Friends', [stage[:200]])


def shared(found: Findings, name: str, snapshot, edits):
    friend_id = (edits or {}).get('friend_id')
    if not friend_id or len(snapshot['companions']) < 2:
        return
    knowing = [named(snapshot, companion_id) for companion_id, screens in snapshot['companions'].items()
               if friend_id in [p['id'] for p in screens.get('/api/life/circle') or []]]
    if len(knowing) < 2:
        found.add(name, 'high', 'multi-companion', 'A person shared into a second circle is not in both', knowing)


def families(found: Findings, name: str, snapshot):
    """A family the app planned (life/family_tree.py) reads as one: no third parent who isn't a step, nobody long
    gone or out of touch still in their days, and someone of the plan in each place only once."""
    for companion_id, screens in snapshot['companions'].items():
        people = screens.get('/api/life/circle') or []
        kin = [p for p in people if p.get('kin')]
        if not kin:
            continue
        who = named(snapshot, companion_id)
        parents = [p for p in kin if p['role'] in SLOTS['mother'] | SLOTS['father'] and p['status'] == 'active'
                   and not p.get('late')]
        if len(parents) > 2:
            found.add(name, 'high', 'app-data', f'{who} has {len(parents)} parents in touch',
                      [f"{p['name']} ({p['role']})" for p in parents])
        if wrong := [p['name'] for p in kin if (p.get('late') or p.get('estranged')) and p['now']]:
            found.add(name, 'high', 'app-data', f"Family long gone or out of touch still in {who}'s days", wrong)
        places = Counter(p['kin']['id'] for p in kin)
        if twice := [place for place, count in places.items() if count > 1]:
            found.add(name, 'high', 'app-data', f"Two people in the same place in {who}'s family", twice)


def errors(found: Findings, name: str, out: Path, logs: Path):
    for error in load(out, name, 'errors') or []:
        found.add(name, 'high' if str(error.get('status')).startswith('5') else 'medium', 'error',
                  f"{error['call']} answered {error['status']}", [error.get('body', '')[:300]])
    log = logs / f'{name}.log'
    if log.exists():
        text = log.read_text(encoding='utf-8', errors='replace')
        for block in re.findall(r'Traceback \(most recent call last\):\n(?:.*\n){1,40}?\S.*Error.*', text)[:5]:
            found.add(name, 'high', 'error', 'The app logged an error: ' + block.strip().splitlines()[-1][:160],
                      block.strip().splitlines()[-6:])


def run(out: Path, names, logs: Path):
    found = Findings()
    for name in names:
        later, edits = load(out, name, 'later') or load(out, name, 'after-edits'), load(out, name, 'edits')
        created = load(out, name, 'created') or []
        if len(created) < len(plan.WORLDS[name]['companions']):
            found.add(name, 'high', 'error', 'Not every companion could be made',
                      [c.get('version', {}).get('name', '?') for c in created])
        if later:
            earth_words(found, name, later)
            single_places(found, name, later)
            jobs(found, name, later)
            kept_by_hand(found, name, edits, later)
            ages(found, name, later)
            ship_pets(found, name, later)
            together(found, name, later, [c['id'] for c in created])
            strangers(found, name, later)
            shared(found, name, later, edits)
            families(found, name, later)
        errors(found, name, out, logs)
    return sorted(found.items, key=lambda item: (SEVERITY[item['severity']], item['kind'], item['world']))


def world_words() -> dict[str, str]:
    """Each world's words that do not fit it, as one pattern, for browse.mjs to look for on screen."""
    return {name: '|'.join(WORDS[kind] for kind in kinds) for name, kinds in KINDS.items() if kinds}


def report(out: Path, findings) -> str:
    (out / 'world-words.json').write_text(json.dumps(world_words()), encoding='utf-8')
    (out / 'findings.json').write_text(json.dumps(findings, indent=1), encoding='utf-8')
    lines = ['# Simulated end-to-end run', '', f'{len(findings)} findings.', '']
    for item in findings:
        lines.append(f"- **{item['severity']}** [{item['world']}] ({item['kind']}) {item['title']}")
        lines += [f'    - {seen}' for seen in item['seen'][:6]]
    text = '\n'.join(lines) + '\n'
    (out / 'report.md').write_text(text, encoding='utf-8')
    return text
