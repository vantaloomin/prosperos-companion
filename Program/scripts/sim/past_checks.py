"""Checks over what past_years.py saved: a world in a past year showing things from after its year, people not born
yet, jobs and pastimes nobody had then, Back when not rolling the two of you back, and errors the app gave."""
import json
import re
from pathlib import Path

import checks
from checks import Findings, load, screens_of, strings

# Things the world's year can't know yet, with the first year they could show. Generous: the year they were common
# enough to come up, not the year they were patented.
NEWER = {
    r'smart ?phones?': 2007, r'iphones?': 2007, r'ipads?': 2010, r'android': 2008, r'instagram': 2010,
    r'tiktok': 2017, r'snapchats?': 2011, r'facebook': 2004, r'twitter|tweets?|tweeted': 2006, r'youtube': 2005,
    r'whatsapp': 2009, r'netflix': 1997, r'streaming|binge-?watch\w*': 2007, r'spotify': 2008, r'podcasts?': 2004,
    r'uber|lyft|rideshares?|ride-?hailing': 2010, r'doordash|grubhub|delivery apps?': 2010, r'venmo': 2010,
    r'airbnb': 2009, r'tinder|bumble|hinge|dating apps?|swip(?:e|ed|ing)': 2012, r'selfies?': 2010,
    r'emojis?': 2011, r'facetime': 2010, r'zoom calls?|on zoom': 2020, r'covid|pandemic|lockdowns?': 2020,
    r'wi-?fi': 2000, r'google[ds]?': 1998, r'gmail': 2004, r'wikipedia': 2001, r'reddit': 2005,
    r'texts?|texted|texting': 1999, r'e-?mails?|e-?mailed': 1995, r'online|internet|websites?': 1995,
    r'blogs?|blogging': 2000, r'myspace': 2004, r'blackberr(?:y|ies)': 2003, r'group ?chats?': 2010,
    r'apps?': 2009, r'influencers?': 2015, r'memes?': 2008, r'vlogs?|vlogging': 2006, r'kindle': 2008,
    r'instant pot|air fryer': 2016, r'oat milk': 2017, r'kombucha': 2010, r'avocado toast': 2013,
    r'crypto|bitcoin|nfts?': 2014, r'electric scooters?|e-?scooters?': 2018, r'teslas?': 2012, r'drones?': 2013,
}
# Endpoints whose words are the user's own, the settings, or the stand-in model's canned replies.
SKIP_PATHS = checks.SKIP_PATHS + ('/api/worlds', '/api/companion/cast')
YEAR = re.compile(r'\b(19[5-9]\d|20[0-4]\d)\b')
SKIP_KEYS_YEAR = {'started_on', 'on', 'date', 'day', 'since', 'born', 'birthday', 'due', 'ends', 'starts', 'reached_on'}


def year_of(snapshot) -> int | None:
    world = ((snapshot.get('shared') or {}).get('/api/worlds') or {}).get('world') or {}
    return world.get('year')


def newer_words(found: Findings, name: str, label: str, snapshot, year: int):
    patterns = [(re.compile(rf'\b(?:{words})\b', re.IGNORECASE), first) for words, first in NEWER.items()
                if first > year]
    hits = {}
    for whose, endpoint, value in screens_of(snapshot):
        if endpoint.startswith(SKIP_PATHS):
            continue
        for where, text in strings(value):
            for pattern, first in patterns:
                if match := pattern.search(text):
                    hits.setdefault(endpoint, {}).setdefault(f'{match.group(0).casefold()} ({first})', []).append(
                        f'{whose}{where}: {text[:180]}')
    for endpoint, words in sorted(hits.items()):
        found.add(f'{name}/{label}', 'medium', 'newer-than-year', f'{endpoint} in {year} shows {", ".join(sorted(words))}',
                  [line for seen in words.values() for line in seen[:2]][:8])


def later_years(found: Findings, name: str, label: str, snapshot, year: int):
    """A year after the world's in words the screens show (dates are checked by tests/test_world_year.py)."""
    hits = {}
    for whose, endpoint, value in screens_of(snapshot):
        if endpoint.startswith(SKIP_PATHS):
            continue
        for where, text in strings(value):
            if where.rsplit('.', 1)[-1] in SKIP_KEYS_YEAR:
                continue
            later = [int(match) for match in YEAR.findall(text) if int(match) > year + 1]
            if later:
                hits.setdefault(endpoint, []).append(f'{whose}{where}: {text[:180]}')
    for endpoint, seen in sorted(hits.items()):
        found.add(f'{name}/{label}', 'medium', 'newer-than-year', f'{endpoint} in {year} names a later year', seen[:8])


def media(found: Findings, name: str, label: str, snapshot, year: int):
    for whose, endpoint, value in screens_of(snapshot):
        if endpoint != '/api/life/media':
            continue
        for where, text in _dated(value):
            if text > year:
                found.add(f'{name}/{label}', 'high', 'newer-than-year', f'{whose}media from {text} in {year}', [where])


def _dated(value, path=''):
    if isinstance(value, dict):
        if isinstance(value.get('year'), int) and value.get('title'):
            yield f"{path}: {value['title']} ({value['year']})", value['year']
        for key, item in value.items():
            yield from _dated(item, f'{path}.{key}')
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _dated(item, f'{path}[{index}]')


def ages(found: Findings, name: str, label: str, snapshot):
    for whose, endpoint, value in screens_of(snapshot):
        if endpoint not in ('/api/life/townsfolk', '/api/life/circle', '/api/life/acquaintances', '/api/people'):
            continue
        for where, age in _ages(value):
            if age < 0:
                found.add(f'{name}/{label}', 'high', 'unborn', f'{whose}{endpoint} has someone aged {age}', [where])


def _ages(value, path=''):
    if isinstance(value, dict):
        if isinstance(value.get('age'), int):
            yield f"{path}: {value.get('name')}", value['age']
        for key, item in value.items():
            yield from _ages(item, f'{path}.{key}')
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _ages(item, f'{path}[{index}]')


def back_when(found: Findings, out: Path):
    name = 'back-when'
    present, strangers, history = (load(out, name, label) for label in ('present', 'strangers', 'history'))
    sheet = load(out, name, 'sheet') or {}
    if not sheet.get('moments'):
        found.add(name, 'high', 'back-when', 'The Back when sheet offered no moments', [json.dumps(sheet)[:300]])
    inside = (load(out, name, 'sheet-inside') or {}).get('status')
    if inside != 409:
        found.add(name, 'medium', 'back-when', f'The Back when sheet inside a past world answered {inside}', [])
    for label, snapshot in (('strangers', strangers), ('history', history)):
        if not (present and snapshot):
            found.add(name, 'high', 'back-when', f'No {label} world to check', [])
            continue
        year = year_of(snapshot)
        if not year:
            found.add(name, 'high', 'back-when', f'The {label} world has no year', [])
            continue
        back = (year_of(present) or 0) - year
        main = next(iter(present['companions']))
        before = _companion(present, main)
        after = _companion(snapshot, main)
        if before.get('age') and after.get('age') is not None and before['age'] - after['age'] not in (back, back - 1, back + 1):
            found.add(name, 'high', 'back-when', f"{label}: age {before['age']} became {after['age']} {back} years back", [])
        closeness = ((snapshot['companions'][main].get('/api/closeness')) or {})
        if label == 'strangers':
            found.add(name, 'low', 'info', f"strangers: closeness then {json.dumps(closeness)[:200]}", [])


def _companion(snapshot, companion_id) -> dict:
    view = (snapshot['companions'].get(companion_id) or {}).get('/api/companion') or {}
    return view.get('companion') or {}


def run(out: Path, names, logs: Path):
    found = Findings()
    for name in names:
        for label in ('present', 'strangers', 'strangers-later', 'history', 'fresh', 'later'):
            snapshot = load(out, name, label)
            year = snapshot and year_of(snapshot)
            if not year:
                continue
            newer_words(found, name, label, snapshot, year)
            later_years(found, name, label, snapshot, year)
            media(found, name, label, snapshot, year)
            ages(found, name, label, snapshot)
            checks.jobs(found, f'{name}/{label}', snapshot)
            checks.single_places(found, f'{name}/{label}', snapshot)
        checks.errors(found, name, out, logs)
    if 'back-when' in names:
        back_when(found, out)
    return sorted(found.items, key=lambda item: (checks.SEVERITY[item['severity']], item['kind'], item['world']))


def world_words(out: Path) -> dict[str, str]:
    """Each scene's words from after the year of the world it ended in, as one pattern, for browse.mjs."""
    words = {}
    for folder in sorted(path for path in out.iterdir() if path.is_dir() and path.name != 'apps'):
        for label in ('history', 'later', 'strangers-later', 'fresh'):
            if (snapshot := load(out, folder.name, label)) and (year := year_of(snapshot)):
                words[folder.name] = '|'.join(pattern for pattern, first in NEWER.items() if first > year)
                break
    return words


def report(out: Path, findings) -> str:
    (out / 'world-words.json').write_text(json.dumps(world_words(out)), encoding='utf-8')
    (out / 'findings.json').write_text(json.dumps(findings, indent=1), encoding='utf-8')
    lines = ['# 1.2 past-year run', '', f'{len(findings)} findings.', '']
    for item in findings:
        lines.append(f"- **{item['severity']}** [{item['world']}] ({item['kind']}) {item['title']}")
        lines += [f'    - {seen}' for seen in item['seen'][:6]]
    text = '\n'.join(lines) + '\n'
    (out / 'report.md').write_text(text, encoding='utf-8')
    return text
