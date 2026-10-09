"""Life chapters: lasting changes to the companion's life every few months, picked by the consequence engine.

Once a month, on a day seeded by the timeline, a chapter may begin: how likely is set by the drama level, never
sooner than `GAP` after the last one or `SETTLE_IN` after the timeline began. Which chapter comes from the odds
table `chapter:next` (world/data/consequences.json), read from the marks earlier outcomes left (money tight since
spring makes a new job likelier; a promotion makes a move likelier), the companion's description and what they have
(a pet already, friends in the circle). The chapter then rewrites state for good:

- `new_job`: another career the city offers on the same kind of schedule, paying the same or more (more when money
  has been tight); the budget follows.
- `move`: another neighbourhood of the city whose rents fit their pay; the home is the new place from that day.
- `pet`: a pet comes home.
- `hobby`: a pastime they take up for real joins their interests.
- `friend_moves`: a friend in the circle moves away to another city and leaves the circle.

Changes to who they are (career, location, interests) are an overlay on the character's active version for this
timeline (applied by companion/characters.py `with_chapters`), so a fork without the chapter keeps the old life and the
character's own description and personality are never rewritten. A chapter never touches personality, emotional
traits or a romance companion's love life. Today lists them with "Why it went this way" and an undo; the chat context
tells the companion for a while, and the news can open a conversation. No model decides anything.
"""
import random
from datetime import date, timedelta

from companion import consequences
from companion.characters import apply_changes, require_current
from companion.clock import stamp
from companion.database import decode, encode, identifier, many, one, optional
from companion.errors import require
from companion.life import circle, home, money, storylines
from companion.memory import pairs
from companion.world import catalog

# A month's chance that a chapter begins, by drama level (quiet to soap opera).
CHANCE = (0.12, 0.2, 0.3, 0.4)
GAP = timedelta(days=75)
SETTLE_IN = timedelta(days=45)
TOLD_DAYS = 90  # How long the chat context keeps a new chapter.
FRESH_DAYS = 1  # A chapter from today or yesterday can open a conversation.
CHOICE = 'chapter:next'
KINDS = ('new_job', 'move', 'pet', 'hobby', 'friend_moves')
HOBBIES = {
    True: ('running', 'pottery', 'rock climbing', 'learning guitar', 'baking bread', 'photography', 'yoga',
           'painting', 'cycling', 'learning Spanish', 'chess', 'gardening', 'dancing lessons', 'swimming'),
    False: ('embroidery', 'fencing', 'riding', 'learning the fiddle', 'baking bread', 'sketching', 'archery',
            'gardening', 'dancing', 'chess', 'swimming', 'calligraphy'),
}
FRIENDS = {'close friend', 'longtime friend', 'old friend from school', 'old classmate', 'friend', 'new friend',
           'neighbor', 'coworker'}


# Deciding ------------------------------------------------------------------------------------------------

def advance(connection, companion: dict, world, now) -> int:
    """Check each day since the last check (a month's chapter day can come once). Returns chapters begun."""
    timeline_id = companion['active_timeline_id']
    today = storylines.local_today(companion, now)
    cursor = optional(connection, 'SELECT through FROM chapter_days WHERE timeline_id=?', (timeline_id,))
    day = date.fromisoformat(cursor['through']) + timedelta(days=1) if cursor else today
    begun = 0
    while day <= today:
        if day.day == check_day(timeline_id) and begins(connection, companion, day):
            begun += bool(begin(connection, companion, world, day, now))
        day += timedelta(days=1)
    connection.execute('INSERT INTO chapter_days (timeline_id, through) VALUES (?, ?) ON CONFLICT(timeline_id) '
                       'DO UPDATE SET through=excluded.through', (timeline_id, today.isoformat()))
    return begun


def check_day(timeline_id: str) -> int:
    return 1 + random.Random(f'chapter-day:{timeline_id}').randrange(28)


def begins(connection, companion: dict, day: date) -> bool:
    timeline_id = companion['active_timeline_id']
    started = optional(connection, 'SELECT COALESCE(activated_at, created_at) AS since FROM timelines WHERE id=?',
                       (timeline_id,))
    if started and date.fromisoformat(started['since'][:10]) > day - SETTLE_IN:
        return False
    last = optional(connection, 'SELECT MAX(started_on) AS on_ FROM life_chapters WHERE timeline_id=? '
                    'AND undone_at IS NULL', (timeline_id,))
    if last and last['on_'] and date.fromisoformat(last['on_']) > day - GAP:
        return False
    chance = CHANCE[storylines.drama(connection)]
    return random.Random(f'chapter:{timeline_id}:{day.isoformat()}').random() < chance


def facts(connection, companion: dict, day: date) -> dict:
    """What the engine reads for the next chapter."""
    timeline_id, definition = companion['active_timeline_id'], companion['version']['definition']
    me = pairs.companion_key(companion['id'])
    return {'drama': storylines.drama(connection), 'mood': consequences.total(connection, timeline_id, me, 'mood',
                                                                          day.isoformat()),
            'money': consequences.total(connection, timeline_id, me, 'money', day.isoformat()),
            'sheet': {group for group in consequences.WORDS if consequences.sheet_has(definition, group)},
            'friends': len(friends(connection, timeline_id))}


def begin(connection, companion: dict, world, day: date, now) -> dict | None:
    """Pick a chapter with the engine, make its change and record it."""
    timeline_id, definition = companion['active_timeline_id'], companion['version']['definition']
    seed = f'chapter:{timeline_id}:{day.isoformat()}'
    plans = plans_for(connection, companion, world, day, seed)
    if not plans:
        return None
    found = facts(connection, companion, day)
    found.update({f'can_{kind}': int(kind in plans) for kind in KINDS})
    names = {'name': definition['name'].split()[0], 'a': 'someone', 'b': ''}
    labels = [plans[kind]['title'] if kind in plans else option['label'].format(**names)
              for kind, option in zip(KINDS, consequences.tables()[CHOICE]['options'], strict=True)]
    outcome = consequences.decide(connection, timeline_id=timeline_id, choice=CHOICE, subject=seed,
                                  facts=found, names=names, labels=labels, day=day.isoformat(), timestamp=stamp(now))
    kind = KINDS[outcome['picked']]
    if kind not in plans:
        return None
    chapter_id = identifier()
    connection.execute(
        'INSERT INTO life_chapters (id, timeline_id, kind, started_on, title, told, share, consequence_id, created_at) '
        "VALUES (?, ?, ?, ?, '', '', '', ?, ?)", (chapter_id, timeline_id, kind, day.isoformat(), outcome['id'],
                                                  stamp(now)))
    make(connection, companion, world, chapter_id, kind, plans[kind], now)
    return one(connection, 'SELECT * FROM life_chapters WHERE id=?', (chapter_id,))


def plans_for(connection, companion: dict, world, day: date, seed: str) -> dict:
    return {kind: plan for kind in KINDS if (plan := PLANS[kind](connection, companion, world, day, seed))}


def make(connection, companion: dict, world, chapter_id: str, kind: str, plan: dict, now):
    """Make the chapter's change and write what it was (and how to take it back) on its row."""
    row = one(connection, 'SELECT started_on FROM life_chapters WHERE id=?', (chapter_id,))
    undo = DOERS[kind](connection, companion, world, date.fromisoformat(row['started_on']), plan, now)
    connection.execute('UPDATE life_chapters SET kind=?, title=?, told=?, share=?, changes=?, undo=? WHERE id=?',
                       (kind, plan['title'], plan['told'], plan['share'], encode(plan.get('changes', {})),
                        encode(undo), chapter_id))


# What each chapter would be -------------------------------------------------------------------------------

def plan_job(connection, companion, world, day, seed) -> dict | None:
    definition = companion['version']['definition']
    city = money.city_for(definition)
    if not city or not money.has_money(city):
        return None
    current, _guessed = money.career_for(definition, city)
    tier = money.PAY_TIERS.get(current['pay'], money.DEFAULT_TIER) if current else money.DEFAULT_TIER
    tight = consequences.total(connection, companion['active_timeline_id'], pairs.companion_key(companion['id']),
                               'money', day.isoformat()) < 0
    options = sorted(career['id'] for career in catalog.careers_for(city).values()
                     if (not current or (career['id'] != current['id'] and career['schedule'] == current['schedule']))
                     and money.PAY_TIERS.get(career['pay'], money.DEFAULT_TIER) >= tier + tight)
    if not options:
        return None
    career = catalog.careers_for(city)[random.Random(f'{seed}:job').choice(options)]
    title = career['name'].lower()
    name = definition['name'].split()[0]
    return {'title': f'{name} started a new job as {article(title)}', 'changes': {'career': career['id']},
            'told': f'You started a new job as {article(title)}.',
            'share': f'Big news: I start a new job as {article(title)}!'}


def plan_move(connection, companion, world, day, seed) -> dict | None:
    definition = companion['version']['definition']
    profile, city = money.profile(definition), money.city_for(definition)
    if not profile or not city:
        return None
    fitting = sorted(hood['name'] for hood in city['neighborhoods'] if hood.get('rent')
                     and hood['name'] != profile.neighborhood and hood['rent_tier'] in money.HOOD_TIERS[profile.tier])
    if not fitting:
        return None
    hood = random.Random(f'{seed}:move').choice(fitting)
    name = definition['name'].split()[0]
    return {'title': f'{name} moved to {hood}', 'changes': {'location': f"{hood}, {city['name']}"},
            'told': f'You moved to a new place in {hood}.', 'share': f'I did it, I moved! New place in {hood}.'}


def plan_pet(connection, companion, world, day, seed) -> dict | None:
    if any(item['kind'] == 'pet' for item in home.items_on(connection, companion['active_timeline_id'], day)):
        return None
    data = circle.city_data(companion['version']['definition'], world)
    pet = home.pet_item(f'{seed}:pet', home.modern(data), 'chapter')
    kind = pet['variety']
    name = companion['version']['definition']['name'].split()[0]
    return {'title': f"{name} adopted a {kind} named {pet['name']}", 'item': pet,
            'told': f"You adopted a {kind}, {pet['details']['description']}, and named them {pet['name']}.",
            'share': f"Meet {pet['name']}! I adopted a {kind}."}


def plan_hobby(connection, companion, world, day, seed) -> dict | None:
    definition = companion['version']['definition']
    data = circle.city_data(definition, world)
    have = {interest.casefold() for interest in definition.get('interests') or []}
    options = [hobby for hobby in HOBBIES[home.modern(data)] if hobby.casefold() not in have]
    if not options:
        return None
    hobby = random.Random(f'{seed}:hobby').choice(options)
    name = definition['name'].split()[0]
    return {'title': f'{name} took up {hobby} for real', 'changes': {'interest': hobby},
            'told': f'You took up {hobby} for real; it is part of your weeks now.',
            'share': f"I've officially gotten into {hobby}. Like, properly."}


def plan_friend(connection, companion, world, day, seed) -> dict | None:
    timeline_id = companion['active_timeline_id']
    busy = {person for row in storylines.running(connection, timeline_id, day.isoformat())
            for person in decode(row['cast_ids'])}
    choices = [person for person in friends(connection, timeline_id) if person['id'] not in busy]
    if not choices:
        return None
    person = random.Random(f'{seed}:friend').choice(choices)
    definition = companion['version']['definition']
    here = circle.city_data(definition, world)
    cities = sorted(data['name'] for data in catalog.cities().values() if not here or data['id'] != here['id'])
    away = random.Random(f'{seed}:city').choice(cities) if cities else 'another city'
    name = definition['name'].split()[0]
    return {'title': f"{person['name']}, {name}'s {person['role']}, moved away to {away}", 'person': person['id'],
            'told': f"Your {person['role']} {person['name']} moved away to {away}; you keep in touch by phone.",
            'share': f"{person['name']} is moving to {away}. I'm going to miss having them around."}


def friends(connection, timeline_id: str) -> list[dict]:
    return [person for person in circle.people(connection, timeline_id) if person['role'] in FRIENDS]


def article(text: str) -> str:
    return f"{'an' if text[:1] in 'aeiou' else 'a'} {text}"


PLANS = {'new_job': plan_job, 'move': plan_move, 'pet': plan_pet, 'hobby': plan_hobby, 'friend_moves': plan_friend}


# Making the change, and undoing it ------------------------------------------------------------------------

def do_overlay(connection, companion, world, day, plan, now) -> dict:
    return {}


def do_move(connection, companion, world, day, plan, now) -> dict:
    """The old home ends the day before; the new one is built from the moved definition."""
    timeline_id = companion['active_timeline_id']
    old = [item for item in home.items_on(connection, timeline_id, day) if item['kind'] == 'home']
    for item in old:
        connection.execute('UPDATE home_items SET until=? WHERE id=?', (day.isoformat(), item['id']))
    definition = apply_changes(companion['version']['definition'], plan['changes'])
    place = home.place_item(f'home:{timeline_id}:{day.isoformat()}', definition, circle.city_data(definition, world))
    added = home.insert_item(connection, timeline_id, place, 'change', day, now)
    return {'ended': [item['id'] for item in old], 'added': [added]}


def do_pet(connection, companion, world, day, plan, now) -> dict:
    return {'added': [home.insert_item(connection, companion['active_timeline_id'], plan['item'], 'change', day, now)]}


def do_friend(connection, companion, world, day, plan, now) -> dict:
    circle.set_status(connection, plan['person'], 'removed', now)
    return {'removed': [plan['person']]}


DOERS = {'new_job': do_overlay, 'move': do_move, 'pet': do_pet, 'hobby': do_overlay, 'friend_moves': do_friend}


def undo(database, chapter_id: str) -> list[dict]:
    """Take a chapter back: its overlay goes, a new home or pet goes and the old home returns, a friend who moved
    away comes back. What happened in the meantime stays."""
    with database.connect(write=True) as connection:
        row = mine(connection, chapter_id)
        reverse(connection, decode(row['undo']), database.clock.now())
        connection.execute('UPDATE life_chapters SET undone_at=? WHERE id=?', (database.now(), chapter_id))
    return listing(database)


def change(database, world, consequence_id: str, option: int) -> dict:
    """The user picks another chapter instead ("Make it go this way"): the one that happened is taken back and the
    picked one happens from the same day, if it can."""
    with database.connect(write=True) as connection:
        found = optional(connection, 'SELECT id FROM life_chapters WHERE consequence_id=?', (consequence_id,))
        require(found is not None, 'That chapter was not found.', 404)
        row = mine(connection, found['id'])
        require(0 <= option < len(KINDS), 'There is no such way for it to go.', 422)
        now, day = database.clock.now(), date.fromisoformat(row['started_on'])
        reverse(connection, decode(row['undo']), now)
        connection.execute("UPDATE life_chapters SET changes='{}', undo='{}' WHERE id=?", (row['id'],))
        companion = require_current(connection)
        plan = PLANS[KINDS[option]](connection, companion, world, day, f"chapter:{row['timeline_id']}:{day}")
        require(plan is not None, "That can't happen in their life right now.", 409)
        make(connection, companion, world, row['id'], KINDS[option], plan, now)
        return consequences.redo(connection, consequence_id, option, now, day)


def mine(connection, chapter_id: str) -> dict:
    """A chapter on the main character's active timeline that is still in place."""
    companion = require_current(connection)
    row = optional(connection, 'SELECT * FROM life_chapters WHERE id=? AND timeline_id=?',
                   (chapter_id, companion['active_timeline_id']))
    require(row is not None, 'That chapter is not on this timeline.', 404)
    require(row['undone_at'] is None, 'That chapter was already undone.', 409)
    return row


def reverse(connection, found: dict, now):
    for item_id in found.get('added', ()):
        connection.execute('DELETE FROM home_items WHERE id=?', (item_id,))
    for item_id in found.get('ended', ()):
        connection.execute('UPDATE home_items SET until=NULL WHERE id=?', (item_id,))
    for person_id in found.get('removed', ()):
        circle.set_status(connection, person_id, 'active', now)


# Reading -------------------------------------------------------------------------------------------------

def view(row: dict) -> dict:
    return {'id': row['id'], 'kind': row['kind'], 'started_on': row['started_on'], 'title': row['title'],
            'consequence': row['consequence_id'], 'undone': row['undone_at'] is not None}


def listing(database) -> list[dict]:
    with database.connect() as connection:
        companion = require_current(connection)
        rows = many(connection, 'SELECT * FROM life_chapters WHERE timeline_id=? AND undone_at IS NULL '
                    'ORDER BY started_on DESC, created_at DESC', (companion['active_timeline_id'],))
        return [view(row) for row in rows]


def context_lines(connection, companion: dict, now) -> list[tuple[str, str]]:
    """New chapters for the chat context's storylines section, told as "you", for `TOLD_DAYS`."""
    today = storylines.local_today(companion, now)
    since = (today - timedelta(days=TOLD_DAYS)).isoformat()
    rows = many(connection, 'SELECT * FROM life_chapters WHERE timeline_id=? AND undone_at IS NULL AND started_on>=? '
                'AND started_on<=? ORDER BY started_on', (companion['active_timeline_id'], since, today.isoformat()))
    return [(f"chapter:{row['id']}", f"- A new chapter, since {row['started_on']}: {row['told']} This is how your "
             'life is now; it replaces anything older about it.') for row in rows]


def fresh(connection, companion: dict, now) -> list[dict]:
    """Chapters from today or yesterday, for a first message."""
    today = storylines.local_today(companion, now)
    return many(connection, 'SELECT * FROM life_chapters WHERE timeline_id=? AND undone_at IS NULL AND started_on>=? '
                'AND started_on<=?', (companion['active_timeline_id'],
                                      (today - timedelta(days=FRESH_DAYS)).isoformat(), today.isoformat()))

