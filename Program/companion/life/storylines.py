"""Storylines: things that unfold over days in the companion's life and their circle's (realism).

"Omg, my dad just got a promotion." "I hate the new guy at work, he keeps hitting on me." "I got
drunk and kissed my best friend." Each storyline is a fixed template with a cast drawn from the
circle (or the companion's own work), and two or three beats spread over the following days. Which
storyline starts on which day, who is in it and how each beat turns out are all decided by a seed
when it starts, never by a model. Beats stay hidden until their day comes, like the agenda.

The Life setting `drama` is the slider from quiet to soap opera: it sets how often a storyline
starts, how many can run at once and how far they can go. Quiet keeps to good news; realistic adds
everyday trouble; dramatic adds health scares, feuds and secret romances; soap opera adds drunk
kisses, separations and family secrets. A companion in a romance with the user never gets a
storyline about their own love life.

Beats reach the chat context told to the companion as "you" (decided, never contradicted, the ending
never guessed); a settled one stays pinned for two months by its outcome, then goes to memory search.
They can open a conversation (companion/life/openers.py) and are listed in Today, where the user can
end one.
Text names people as they are named now, so renaming someone carries over; removing someone ends
the storylines they are in.
"""
import random
from dataclasses import dataclass
from datetime import date, timedelta

from companion.clock import stamp, zone
from companion.database import decode, encode, identifier, many, one, optional
from companion.errors import require
from companion.life import circle

LEVELS = ('quiet', 'realistic', 'dramatic', 'soap opera')
# Per drama level: chance a storyline starts on a given day, and how many can run at once.
START = CHANCES = (0.04, 0.08, 0.15, 0.28)
RUNNING = (1, 2, 3, 4)
REPEAT_AFTER = timedelta(days=90)
CATCH_UP_DAYS = 14
RECENT_DAYS = 21
SETTLED_DAYS = 60


@dataclass(frozen=True)
class Beat:
    text: str
    share: str
    tone: str = 'mixed'


@dataclass(frozen=True)
class Story:
    key: str
    level: int
    cast: str
    stages: tuple[tuple[Beat, ...], ...]
    gap: tuple[int, int] = (2, 6)


def beat(text, share, tone='mixed'):
    return (Beat(text, share, tone),)


def either(*beats):
    return tuple(Beat(*item) for item in beats)


STORIES = (
    # Quiet and up: good news.
    Story('parent_promotion', 0, 'working parent', (
        beat('{a}, {name}\'s {a_rel}, got a promotion at work.', 'Omg, my {a_rel} just got a promotion!!', 'good'),)),
    Story('sibling_engaged', 0, 'unmarried sibling', (
        beat('{name}\'s {a_rel} {a} got engaged.', 'BIG news: {a} just got engaged!!', 'good'),
        beat('{a} set a wedding date for next year.', "{a} set a date! I'm already stressing about what to wear lol",
             'good')), (5, 14)),
    Story('cousin_baby', 0, 'cousin', (
        beat('{name}\'s cousin {a} announced they are expecting a baby.',
             "My cousin {a} is having a baby!! What does that make me, a second cousin? idk", 'good'),)),
    Story('friend_new_job', 0, 'friend', (
        beat('{a} got a job offer and keeps asking {name} whether to take it.',
             "{a} got a job offer and won't stop asking me what to do"),
        either(('{a} took the new job.', '{a} took the job!! so proud of them', 'good'),
               ('{a} turned the job offer down and is staying where they are.',
                '{a} turned the job down in the end. honestly kind of relieved'))), (2, 5)),
    Story('promotion_chance', 0, 'work', (
        beat("{name} heard they are being considered for a promotion.",
             "ok don't jinx it but I might be up for a promotion??"),
        either(('{name} got the promotion.', 'I GOT IT. the promotion. I got it!!', 'good'),
               ('{name} did not get the promotion; it went to someone else.',
                "didn't get the promotion. it's fine. (it's not fine)", 'bad'))), (4, 10)),
    # Realistic: everyday trouble.
    Story('work_creep', 1, 'work', (
        beat('A new guy at {name}\'s work keeps hitting on them, and it is getting uncomfortable.',
             'I hate the new guy at work. He keeps hitting on me.', 'bad'),
        either(('{name} told the new guy to knock it off, and he finally backed off.',
                'update on the new guy: I told him to knock it off and he actually did', 'good'),
               ('{name} reported the new guy to their manager after he kept at it.',
                'had to go to my manager about the new guy. ugh. glad I did though'))), (2, 5)),
    Story('friend_breakup', 1, 'friend', (
        beat('{a} went through a breakup, and {name} spent the evening on the phone with them.',
             'rough night. {a} got dumped and I was on the phone with them for hours', 'bad'),
        beat('{a} is doing better after the breakup.', "{a}'s doing a lot better btw. bounced back fast",
             'good')), (4, 9)),
    Story('coworker_leaving', 1, 'coworker', (
        beat('{a} told {name} they are quitting.', 'noooo {a} is quitting. who am I supposed to eat lunch with',
             'bad'),
        beat("{a} had their last day, and {name} went to the send-off drinks.",
             "{a}'s last day today. we gave them a proper send-off")), (5, 12)),
    Story('layoff_rumors', 1, 'work', (
        beat("There are rumors of layoffs at {name}'s work.", 'everyone at work is whispering about layoffs. fun times',
             'bad'),
        either(("The layoffs hit another team; {name}'s job is safe.", "my job's safe. the layoffs hit another team. "
                                                                         'feel awful for them though'),
               ('The layoffs at work were called off.', 'false alarm, the layoffs got called off!', 'good'))),
          (3, 8)),
    # Dramatic: health scares, feuds, secret romances.
    Story('parent_health', 2, 'parent', (
        beat("{name}'s {a_rel} {a} had a health scare and is waiting on test results.",
             "kind of a scary day. my {a_rel} had a health thing and they're running tests", 'bad'),
        either(("{a}'s test results came back fine.", "{a_rel}'s results came back fine. I can breathe again",
                'good'),
               ("{a}'s test results mean treatment; they start soon and say they feel positive.",
                "{a_rel}'s starting treatment soon. they're being really positive about it", 'bad'))), (3, 7)),
    Story('friends_feud', 2, 'two friends', (
        beat('{a} and {b} had a falling out, and both of them are venting to {name}.',
             "ugh, {a} and {b} are fighting and I'm stuck in the middle", 'bad'),
        either(('{a} and {b} made up.', '{a} and {b} made up! peace has returned', 'good'),
               ("{a} and {b} still aren't speaking; {name} is seeing them separately.",
                "{a} and {b} are STILL not talking. I'm doing everything twice now"))), (3, 9)),
    Story('secret_couple', 2, 'two friends', (
        beat('{name} found out {a} and {b} have been secretly seeing each other.', 'WAIT. {a} and {b}?? since WHEN'),
        either(('{a} and {b} made it official.', "{a} and {b} are official now lol. called it (I did not call it)",
                'good'),
               ("{a} and {b} broke it off, and it's awkward when they're in the same room.",
                '{a} and {b} broke up. group hangs are going to be SO awkward', 'bad'))), (5, 14)),
    Story('friend_fight', 2, 'close friend', (
        beat("{name} and {a} had an argument and haven't talked since.",
             "{a} and I had a big fight. I don't really want to get into it yet", 'bad'),
        either(('{name} and {a} talked it out and are okay again.', 'talked to {a}. we\'re good again', 'good'),
               ('{name} and {a} are still a bit cold with each other.',
                "things with {a} are still weird. we're talking but it's not the same", 'bad'))), (3, 8)),
    # Soap opera: drunk kisses, separations, family secrets.
    Story('drunk_kiss', 3, 'best friend, single', (
        beat('{name} got drunk and kissed {a}, their best friend.', 'I got drunk and kissed my best friend. what do I do'),
        beat('{name} and {a} are being weird around each other.', "{a} and I are being so weird around each other. help"),
        either(('{name} and {a} agreed it was a mistake and are staying friends.',
                '{a} and I talked. we\'re staying friends. it was the tequila'),
               ('{name} and {a} decided to try dating.', "so... {a} and I are kind of trying a thing??", 'good'))),
          (1, 4)),
    Story('parents_separating', 3, 'parents', (
        beat("{a} and {b}, {name}'s parents, told {name} they are separating.",
             "my parents are separating. I did not see that coming", 'bad'),
        beat('{name} had a long dinner with {a} about the separation.',
             'long dinner with {a} about everything. it helped, I think')), (3, 8)),
    Story('love_triangle', 3, 'two friends', (
        beat('{a} and {b} have both fallen for the same person, and it is turning into a whole thing.',
             "{a} and {b} like the SAME person. this is a soap opera"),
        either(('The person picked {a}, and {b} is not taking it well.', 'they picked {a}. {b} is NOT okay', 'bad'),
               ('The person picked neither of them, and {a} and {b} are bonding over it.',
                "plot twist: they picked neither. {a} and {b} are bonding over it lmao"))), (3, 9)),
    Story('family_secret', 3, 'parent', (
        beat('{name}\'s {a_rel} {a} let slip that {name} has a half-sibling they never knew about.',
             'so... apparently I have a half-sibling??'),
        beat('{name} looked the half-sibling up online but has not reached out.',
             "found my half-sibling online. haven't messaged. not sure I will")), (2, 6)),
)


def find_story(key) -> Story:
    return next(story for story in STORIES if story.key == key)


def drama(connection) -> int:
    row = optional(connection, 'SELECT drama FROM life_settings WHERE id=1')
    return row['drama'] if row else 1


# Casting ------------------------------------------------------------------------------------------

def kind(person: dict) -> str:
    return circle.role_kind(person['role'])


def working(person: dict) -> bool:
    details = decode(person['details'])
    return (details.get('age') or 40) < 67 and details.get('career') != 'Retired'


FRIENDLY = {'friends', 'old friends', 'coworkers'}
SINGLE_CASTS = {
    'working parent': lambda person: kind(person) == 'parent' and working(person),
    'parent': lambda person: kind(person) == 'parent',
    'sibling': lambda person: kind(person) == 'sibling',
    # A sibling the circle records as married never gets engaged (companion/life/circle.py married_sibling).
    'unmarried sibling': lambda person: kind(person) == 'sibling' and not decode(person['details']).get('married'),
    'cousin': lambda person: kind(person) == 'cousin',
    'coworker': lambda person: kind(person) == 'coworker',
    'friend': lambda person: kind(person) not in circle.FAMILY and kind(person) not in {'coworker', 'neighbor', 'mentor'},
    'close friend': lambda person: kind(person) in circle.OLD_FRIENDS,
    'best friend, single': lambda person: kind(person) in circle.OLD_FRIENDS,
}


def casts(story: Story, people: list[dict], definition: dict) -> list[tuple[str, ...]]:
    """Every cast this story could have from these people (ids), in circle order."""
    works = bool(circle.work_blocks(definition))
    if story.cast == 'work':
        return [()] if works else []
    if story.cast == 'best friend, single' and definition.get('relationship') == 'romance':
        return []
    if story.cast in SINGLE_CASTS:
        return [(person['id'],) for person in people if SINGLE_CASTS[story.cast](person)]
    pairs = []
    for index, first in enumerate(people):
        for second in people[index + 1:]:
            how = circle.tie(first, second)
            if story.cast == 'parents' and how == 'married':
                pairs.append((first['id'], second['id']))
            elif story.cast == 'two friends' and how in FRIENDLY and not {kind(first), kind(second)} & circle.FAMILY:
                pairs.append((first['id'], second['id']))
    return pairs


def running(connection, timeline_id, today: str) -> list[dict]:
    rows = many(connection, "SELECT * FROM storylines WHERE timeline_id=? AND status='running'", (timeline_id,))
    return [row for row in rows if decode(row['stages'])[-1]['on'] > today]


def start(connection, companion, people, day: date, level: int) -> dict | None:
    """The storyline that starts on this day, if one does: seeded by the timeline and the date."""
    timeline_id, definition = companion['active_timeline_id'], companion['version']['definition']
    rng = random.Random(f'storyline:{timeline_id}:{day.isoformat()}')
    if rng.random() >= START[level] or len(running(connection, timeline_id, day.isoformat())) >= RUNNING[level]:
        return None
    since = (day - REPEAT_AFTER).isoformat()
    recent = many(connection, 'SELECT story, cast_ids FROM storylines WHERE timeline_id=? AND started_on>=?',
                  (timeline_id, since))
    used = {row['story'] for row in recent}
    busy = {person for row in running(connection, timeline_id, day.isoformat()) for person in decode(row['cast_ids'])}
    options = []
    for story in STORIES:
        if story.level > level or story.key in used:
            continue
        free = [cast for cast in casts(story, people, definition) if not set(cast) & busy]
        if free:
            options.append((story, free, 3 if story.level == level else 1))
    if not options:
        return None
    story, free, _weight = rng.choices(options, [weight for *_rest, weight in options])[0]
    cast, on, stages = rng.choice(free), day, []
    for index, alternatives in enumerate(story.stages):
        if index:
            on += timedelta(days=rng.randint(*story.gap))
        if len(alternatives) > 1:
            # How it turns out is left to the consequence engine on the day (settle).
            stages.append({'on': on.isoformat(), 'text': '', 'share': '', 'tone': '', 'pending': choice_key(story, index)})
            continue
        chosen = alternatives[0]
        stages.append({'on': on.isoformat(), 'text': chosen.text, 'share': chosen.share, 'tone': chosen.tone})
    return {'story': story.key, 'level': story.level, 'cast_ids': list(cast), 'stages': stages}


def choice_key(story: Story, index: int) -> str:
    return f'storyline:{story.key}:{index}'


def settle(connection, companion, today: date, now) -> int:
    """Turnings whose day has come are decided by the consequence engine (companion/consequences.py), from the
    people in the storyline as things stand now, and written into the storyline. Returns how many."""
    timeline_id, settled = companion['active_timeline_id'], 0
    for row in many(connection, "SELECT * FROM storylines WHERE timeline_id=? AND status='running'", (timeline_id,)):
        stages = decode(row['stages'])
        due = [index for index, stage in enumerate(stages) if stage.get('pending') and stage['on'] <= today.isoformat()]
        for index in due:
            stages[index] = decided_stage(connection, companion, row, index, stages[index], now)
            settled += 1
        if due:
            connection.execute('UPDATE storylines SET stages=? WHERE id=?', (encode(stages), row['id']))
    return settled


def decided_stage(connection, companion, row, index: int, stage: dict, now) -> dict:
    from companion import consequences
    story, definition = find_story(row['story']), companion['version']['definition']
    alternatives = story.stages[index]
    names = cast_names(connection, row, definition)
    outcome = consequences.decide(
        connection, timeline_id=row['timeline_id'], choice=stage['pending'], subject=f"storyline:{row['id']}",
        facts=facts(connection, companion, row, now), names=names,
        labels=[fill(item.text, row, names_by_id(connection, row), definition) for item in alternatives],
        day=stage['on'], timestamp=stamp(now))
    return outcome_stage(stage['on'], alternatives[outcome['picked']], outcome['id'])


def outcome_stage(on: str, chosen: Beat, consequence_id: str) -> dict:
    return {'on': on, 'text': chosen.text, 'share': chosen.share, 'tone': chosen.tone, 'consequence': consequence_id}


def names_by_id(connection, row) -> dict:
    return {person['id']: {'name': person['name'], 'role': person['role']}
            for person in circle.people(connection, row['timeline_id'], include_removed=True)}


def cast_names(connection, row, definition: dict) -> dict:
    """{name, a, b} for the engine's reasons."""
    found = names_by_id(connection, row)
    cast = [found.get(person, {'name': 'someone'})['name'] for person in decode(row['cast_ids'])]
    return {'name': definition['name'].split()[0], 'a': cast[0] if cast else 'someone',
            'b': cast[1] if len(cast) > 1 else 'someone'}


def facts(connection, companion, row, now) -> dict:
    """What the engine reads for a storyline: the drama level, how close the companion is to each person in
    it, how the two of them know each other, the first person's age, and the companion's own description."""
    from companion import consequences
    from companion.memory import pairs
    people = {person['id']: person for person in circle.people(connection, row['timeline_id'], include_removed=True)}
    cast = [people[person] for person in decode(row['cast_ids']) if person in people]
    me, definition = pairs.companion_key(companion['id']), companion['version']['definition']
    found = {'drama': drama(connection), 'sheet': {group for group in consequences.WORDS
                                                  if consequences.sheet_has(definition, group)}}
    for field, person in zip(('a', 'b'), cast, strict=False):
        found[f'closeness_{field}'] = pairs.closeness(connection, me, person['seed'], now)
    if cast:
        found['age_a'] = decode(cast[0]['details']).get('age')
    if len(cast) > 1:
        found['tie'] = circle.tie(cast[0], cast[1])
    return found


def fork_stages(connection, row, copy_id: str, timeline_id: str, cutoff: str) -> list[dict]:
    """A storyline's stages for a new timeline's copy: turnings decided by the fork keep their outcome (copied
    with it), later ones are left for the copy's own engine to decide."""
    from companion import consequences
    story, stages = find_story(row['story']), decode(row['stages'])
    for index, stage in enumerate(stages):
        if not stage.get('consequence'):
            continue
        if stage['on'] > cutoff:
            stages[index] = {'on': stage['on'], 'text': '', 'share': '', 'tone': '', 'pending': choice_key(story, index)}
        else:
            copied = consequences.copy(connection, stage['consequence'], timeline_id, f'storyline:{copy_id}')
            stages[index] = {**stage, 'consequence': copied}
    return stages


def local_today(companion, now) -> date:
    return now.astimezone(zone(companion['version']['timezone'])).date()


def advance(connection, companion, now) -> int:
    """Decide the storylines that started on each day since the last check (cheap, no model)."""
    timeline_id, today = companion['active_timeline_id'], local_today(companion, now)
    end_removed(connection, timeline_id)
    level = drama(connection)
    cursor = optional(connection, 'SELECT through FROM storyline_days WHERE timeline_id=?', (timeline_id,))
    first = today - timedelta(days=CATCH_UP_DAYS)
    day = max(date.fromisoformat(cursor['through']) + timedelta(days=1), first) if cursor else today
    people = circle.people(connection, timeline_id)
    started = 0
    while day <= today:
        found = start(connection, companion, people, day, level)
        if found:
            connection.execute(
                'INSERT INTO storylines (id, timeline_id, story, level, cast_ids, stages, started_on, status, created_at) '
                "VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?)",
                (identifier(), timeline_id, found['story'], found['level'], encode(found['cast_ids']),
                 encode(found['stages']), day.isoformat(), stamp(now)))
            started += 1
        day += timedelta(days=1)
    connection.execute('INSERT INTO storyline_days (timeline_id, through) VALUES (?, ?) ON CONFLICT(timeline_id) '
                       'DO UPDATE SET through=excluded.through', (timeline_id, today.isoformat()))
    settle(connection, companion, today, now)
    return started


def end_removed(connection, timeline_id):
    """Someone removed from the circle takes their unfinished storylines with them."""
    removed = {row['id'] for row in many(connection, "SELECT id FROM circle_people WHERE timeline_id=? "
                                         "AND status='removed'", (timeline_id,))}
    for row in many(connection, "SELECT id, cast_ids FROM storylines WHERE timeline_id=? AND status='running'",
                    (timeline_id,)):
        if set(decode(row['cast_ids'])) & removed:
            connection.execute("UPDATE storylines SET status='ended' WHERE id=?", (row['id'],))


# The chat context speaks to the companion: a template's third person becomes "you" before it is filled.
SECOND_PERSON = (("{name}'s", 'your'), ('{name} is ', 'you are '), ('{name} has ', 'you have '),
                 ('but has not', 'but have not'), ('{name} heard they are', 'you heard you are'),
                 ('hitting on them', 'hitting on you'), ('to their manager', 'to your manager'),
                 ('their best friend', 'your best friend'), ('they never knew', 'you never knew'), ('{name}', 'you'))


def second_person(text: str) -> str:
    for old, new in SECOND_PERSON:
        text = text.replace(old, new)
    return text


# Views --------------------------------------------------------------------------------------------

def fill(text: str, row: dict, names: dict, definition: dict, you=False) -> str:
    text = second_person(text) if you else text
    cast = decode(row['cast_ids'])
    people = [names.get(person_id, {'name': 'someone', 'role': 'friend'}) for person_id in cast]
    values = {'name': definition['name'], 'a': '', 'b': '', 'a_rel': ''}
    if people:
        values |= {'a': people[0]['name'], 'a_rel': people[0]['role']}
    if len(people) > 1:
        values['b'] = people[1]['name']
    filled = text.format(**values)
    return filled[0].upper() + filled[1:] if filled else filled


def view(row: dict, names: dict, definition: dict, today: str, you=False) -> dict:
    stages = decode(row['stages'])
    beats = [{'on': stage['on'], 'text': fill(stage['text'], row, names, definition, you),
              'share': fill(stage['share'], row, names, definition), 'tone': stage['tone'],
              'consequence': stage.get('consequence')}
             for stage in stages if stage['on'] <= today and not stage.get('pending')]
    return {'id': row['id'], 'story': row['story'], 'level': LEVELS[row['level']], 'started_on': row['started_on'],
            'status': row['status'], 'cast': [{'id': person_id, **names[person_id]} for person_id in
                                              decode(row['cast_ids']) if person_id in names],
            'beats': beats, 'unfolding': row['status'] == 'running' and (stages[-1]['on'] > today or
                                                                          bool(stages[-1].get('pending')))}


def visible(connection, companion, now, include_ended=False, you=False) -> list[dict]:
    """Storylines with at least one beat that has happened, newest first; `you` tells them to the companion."""
    timeline_id, definition = companion['active_timeline_id'], companion['version']['definition']
    today = local_today(companion, now).isoformat()
    names = {row['id']: {'name': row['name'], 'role': row['role']}
             for row in circle.people(connection, timeline_id, include_removed=True)}
    status = '' if include_ended else "AND status='running' "
    rows = many(connection, f'SELECT * FROM storylines WHERE timeline_id=? {status}AND started_on<=? '
                'ORDER BY started_on DESC', (timeline_id, today))
    return [view(row, names, definition, today, you) for row in rows]


def context_lines(connection, companion, now) -> list[tuple[str, str]]:
    """Recent storylines for the chat context, told to the companion: what happened so far, and whether it is
    still unfolding. A settled one stays pinned for SETTLED_DAYS after its last beat, by its outcome once older."""
    today = local_today(companion, now)
    recent, pinned = ((today - timedelta(days=days)).isoformat() for days in (RECENT_DAYS, SETTLED_DAYS))
    result = []
    for item in visible(connection, companion, now, you=True):
        last = item['beats'][-1]
        if last['on'] >= recent:
            text = ' Then: '.join(beat_['text'] for beat_ in item['beats'])
            tail = ' Still unfolding: you do not know how it ends yet.' if item['unfolding'] else ''
            result.append((item['id'], f"- Since {item['started_on']}: {text}{tail}"))
        elif not item['unfolding'] and last['on'] >= pinned:
            result.append((item['id'], f"- Settled on {last['on']}: {last['text']}"))
    return result


def recall_items(connection, companion, now) -> list[dict]:
    """Settled storylines past the pinned window, for memory search (companion/memory/context.py): {id, day, text}."""
    pinned = (local_today(companion, now) - timedelta(days=SETTLED_DAYS)).isoformat()
    return [{'id': item['id'], 'day': item['beats'][-1]['on'],
             'text': ' Then: '.join(beat_['text'] for beat_ in item['beats'])}
            for item in visible(connection, companion, now, you=True)
            if not item['unfolding'] and item['beats'][-1]['on'] < pinned]


def fresh_beats(connection, companion, now) -> list[tuple[str, dict]]:
    """Beats that happened today or yesterday, for a first message: (trigger key, beat)."""
    yesterday = (local_today(companion, now) - timedelta(days=1)).isoformat()
    result = []
    for item in visible(connection, companion, now, you=True):
        for index, beat_ in enumerate(item['beats']):
            if beat_['on'] >= yesterday:
                result.append((f"storyline:{item['id']}:{index}", beat_))
    return result


def listing(database, include_ended=False) -> list[dict]:
    from companion.characters import require_current
    with database.connect() as connection:
        return visible(connection, require_current(connection), database.clock.now(), include_ended)


def end(database, storyline_id) -> list[dict]:
    """The user ends a storyline: it leaves the context and Today, and its later beats never happen."""
    from companion.characters import require_current
    with database.connect(write=True) as connection:
        row = one(connection, 'SELECT * FROM storylines WHERE id=?', (storyline_id,))
        companion = require_current(connection)
        require(row['timeline_id'] == companion['active_timeline_id'], 'That storyline is not on this timeline.', 404)
        require(row['status'] == 'running', 'This storyline has already ended.', 409)
        connection.execute("UPDATE storylines SET status='ended' WHERE id=?", (storyline_id,))
        return visible(connection, companion, database.clock.now())



def change_outcome(database, consequence_id: str, option: int) -> dict:
    """The user changes how a turning went: the storyline takes the other way, and the outcome says the user
    chose it. Returns the outcome."""
    from companion import consequences
    from companion.characters import require_current
    with database.connect(write=True) as connection:
        found = consequences.by_id(connection, consequence_id)
        companion = require_current(connection)
        row = optional(connection, 'SELECT * FROM storylines WHERE id=?', (found['subject'].removeprefix('storyline:'),))
        require(row is not None and row['timeline_id'] == companion['active_timeline_id'],
                'That outcome is not on this timeline.', 404)
        outcome = consequences.change(connection, consequence_id, option, stamp(database.clock.now()))
        stages = decode(row['stages'])
        index = next(index for index, stage in enumerate(stages) if stage.get('consequence') == consequence_id)
        chosen = find_story(row['story']).stages[index][option]
        stages[index] = outcome_stage(stages[index]['on'], chosen, consequence_id)
        connection.execute('UPDATE storylines SET stages=? WHERE id=?', (encode(stages), row['id']))
        return outcome
