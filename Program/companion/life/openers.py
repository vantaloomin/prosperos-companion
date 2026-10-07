"""The companion texts first (realism: real people start conversations too).

Fixed triggers decide when the companion opens a conversation, from saved state only: a plan the
user mentioned whose day has passed, news from the companion's own committed life, an event that
touches something the user told them, a follow-up the companion promised ("tell me how the search
is going later") once they have a free moment, an ordinary check-in at a break in their day (lunch,
after work or class, a free evening; rolled with seeded dice, so not every day), or, only for a
character given an absence trait, a long silence. The facts come from that state; a model only
phrases the message in the character's voice, and a trigger that needs phrasing waits when no model
is connected.

It is on by default and the user can turn it off. It never texts while the workspace is paused, during quiet
hours, while the companion is asleep, soon after the last message, more often than the daily cap,
or twice in a row without an answer. Each trigger fires once per timeline. The message is saved as
an ordinary companion message with no `reply_to`, so the next reply sees it in the transcript.
"""
import random
import re
from dataclasses import dataclass
from datetime import time, timedelta

from companion import in_character, notifications, prompt_library, self_facts
from companion.characters import current
from companion.clock import parse, stamp, zone
from companion.database import decode, encode, identifier, many, one, optional, settings
from companion.errors import DomainError
from companion.life import occasions, pacing, recommendations, routine, storylines
from companion.life.mood import ABSENCE_HOURS, last_presence
from companion.memory import context
from companion.memory.records import OPEN_PLANS, eligible
from companion.memory.retrieval import terms
from companion.providers.chat import INCOMPLETE
from companion.providers.scheduling import BackgroundInterrupted, Work
from companion.text_models import CHAT, config_for, key_for
from companion.traits import NAMES, absence_traits, strongest

OPENER = Work(15, 'companion message', True)
FOLLOW_UP_WITHIN = timedelta(days=3)
FOLLOW_UP_AFTER = timedelta(hours=1)
NEWS_WITHIN = timedelta(hours=24)
SILENCE = timedelta(hours=ABSENCE_HOURS * 2)
MAX_LENGTH = 600
# A first message whose opening words match one of the last REPEAT_WINDOW companion messages is a copy.
REPEAT_WINDOW = 300
REPEAT_OPENING = 80
# Words too common to say an event "reminded" the companion of something the user said.
COMMON = {'with', 'went', 'time', 'that', 'this', 'from', 'some', 'they', 'have', 'into', 'about', 'their',
          'over', 'just', 'like', 'good', 'long', 'more', 'most', 'work', 'home', 'evening', 'morning',
          'afternoon', 'friend', 'friends', 'spent', 'took', 'through', 'usual', 'around', 'while', 'went',
          'little', 'really', 'today', 'there', 'after', 'before', 'again', 'first', 'last', 'next', 'make'}
FINISHED = {'loved it': 'Okay, I finished {title}. You were so right, I loved it.',
            'liked it': 'Finished {title}! Really liked it, thank you for that.',
            'thought it was fine': 'Finally finished {title}. It was... fine? I see why people like it.',
            'was not really into it': "So I finished {title}. Honestly? Not really my thing. Sorry!"}
VOICE = {'mild': "Hey you. It's been a little while.", 'moderate': "You've been quiet. Everything okay?",
         'strong': 'So... are you ignoring me now?'}
# Check-ins at breaks in the companion's day (off in tests unless a test turns them on).
CHECK_INS = True
BUSY = {'work', 'study'}
LUNCH = (time(12, 0), time(13, 30))
EVENING = (time(19, 0), time(21, 30))
AFTER = timedelta(minutes=90)
PROMISE_WITHIN = timedelta(hours=18)
# How likely each break is to bring a check-in on a given day.
CHANCE = {'lunch': 0.5, 'midday': 0.5, 'after': 0.7, 'evening': 0.35}
MOMENTS = {'lunch': 'your lunch break', 'midday': 'lunchtime on a day with no work or classes',
           'after': 'just after {done}', 'evening': 'a free evening'}
CHECK_IN = {'lunch': ("Lunch break, finally. How's your day going?", 'Escaped my desk for lunch. How are you doing today?'),
            'midday': ("Slow day over here. How's yours going?", 'Hey! How is your day going?'),
            'after': ("Finally done with {done} for today. How's your day been?", 'Okay, out of {done}. How was your day?'),
            'evening': ("Hey you. How's your evening going?", 'Hi :) how was your day?')}
DONE = {'work': 'work', 'study': 'class'}
LATER = re.compile(r"\b(?:later|tonight|after work|after class|this evening|when i'?m (?:free|off|home|done|out)"
                   r'|on my (?:lunch|break))\b', re.IGNORECASE)
ASK = re.compile(r"\b(?:hear|tell me|fill me in|catch me up|ask you|check (?:in|on|back)|update me|know how|talk about)\b",
                 re.IGNORECASE)
TOPIC = re.compile(r"\bhow ((?:the|your) [a-z][a-z' -]{1,40}?|[a-z][a-z' -]{1,40}?) (?:is|are|was|went|goes|'s) going\b",
                   re.IGNORECASE)
INSTRUCTION = (
    'The user has not written. Write one short message to them yourself, as a text that starts a new exchange '
    '(one to three sentences, no greeting formula unless it fits your voice). Why you are writing: {reason} '
    'Stay within these facts: do not add events, places or people, and never claim to know what the user did. '
    'Reply with the message text only.'
)


@dataclass(frozen=True)
class Trigger:
    key: str
    kind: str
    reason: str
    template: str | None = None
    sources: tuple = ()


def plan_follow_ups(connection, companion, now) -> list[Trigger]:
    """A plan the user mentioned whose time has passed, without a known outcome."""
    result = []
    for memory in eligible(connection, companion, companion['active_timeline_id'], stamp(now)):
        if memory['layer'] != 'plan' or memory['plan_status'] not in OPEN_PLANS:
            continue
        end = memory['applies_until'] or memory['applies_from']
        if not end or not now - FOLLOW_UP_WITHIN <= parse(end) <= now - FOLLOW_UP_AFTER:
            continue
        result.append(Trigger(
            f"plan:{memory['id']}", 'follow_up',
            f"The user told you about a plan ({memory['subject']}: {memory['value']}) and its time has passed. "
            'You do not know how it went. Ask about it warmly.',
            f"Hey! How did the {memory['subject'][0].lower() + memory['subject'][1:]} go?", (memory['id'],)))
    return result


def recent_events(connection, timeline_id, now, where) -> list[dict]:
    return many(connection, "SELECT * FROM life_events WHERE timeline_id=? AND status='committed' AND decided_at>? "
                f'AND ends_at<=? AND {where} ORDER BY decided_at DESC LIMIT 10',
                (timeline_id, stamp(now - NEWS_WITHIN), stamp(now)))


def news(connection, companion, now) -> list[Trigger]:
    """An open question in the companion's life that just settled."""
    rows = recent_events(connection, companion['active_timeline_id'], now,
                         "kind='thread' AND json_extract(details, '$.state')='settled'")
    return [Trigger(f"news:{row['id']}", 'news', f'Something in your own life just turned out: {row["summary"]} '
                    'Tell the user, the way you would text a friend.', None, (row['id'],)) for row in rows]


def words(text: str) -> set[str]:
    return {word for word in terms(text) if len(word) >= 4 and word not in COMMON}


def reminders(connection, companion, now) -> list[Trigger]:
    """Something the companion did today that touches what the user told them about themselves."""
    facts = [memory for memory in eligible(connection, companion, companion['active_timeline_id'], stamp(now))
             if memory['layer'] in {'user_fact', 'shared_experience'} and not memory['boundary']]
    result = []
    for row in recent_events(connection, companion['active_timeline_id'], now, "kind='ordinary'"):
        found = words(row['summary'])
        match = next((memory for memory in facts if found & words(f"{memory['subject']} {memory['value']}")), None)
        if match:
            result.append(Trigger(
                f"reminder:{row['id']}", 'reminder',
                f'Earlier you {row["summary"]} It reminded you of something the user told you '
                f"({match['subject']}: {match['value']}). Tell them, briefly.", None, (row['id'], match['id'])))
    return result


def silence(connection, companion, now) -> list[Trigger]:
    """Only a character with an absence trait reaches out about a long silence (C6, M4)."""
    traits = absence_traits(companion['version']['definition'])
    since = last_presence(connection, companion['active_timeline_id'])
    if not traits or since is None or now - parse(since) < SILENCE:
        return []
    intensity = NAMES[strongest(traits)]
    return [Trigger(f'silence:{since}', 'silence',
                    f'The user has not written for {round((now - parse(since)).total_seconds() / 86400)} days. Because '
                    f"of your {' and '.join(trait['name'] for trait in traits)} ({intensity}), you reach out, in "
                    'proportion and in character. You do not know why they were away and must not guess or accuse.',
                    VOICE[intensity])]


def finished(connection, companion, now) -> list[Trigger]:
    """Something the user recommended, finished in the companion's committed account."""
    rows = recommendations.finished_recently(connection, companion['active_timeline_id'], stamp(now - NEWS_WITHIN))
    result = []
    for row in rows:
        item = decode(row['details'])['recommendation']
        template = FINISHED.get(item['verdict'], FINISHED['liked it']).format(title=item['title'])
        result.append(Trigger(f"finished:{item['id']}", 'recommendation',
                              f"You just finished {item['title']}, which the user recommended to you. Your verdict: "
                              f"{item['verdict']}. Tell them, honestly and briefly. You know nothing about it beyond its "
                              'name: do not describe plot, people or details.', template, (row['id'],)))
    return result


def storyline_news(connection, companion, now) -> list[Trigger]:
    """A beat in a storyline that happened today or yesterday (companion/life/storylines.py)."""
    return [Trigger(key, 'storyline', f"Something just happened in your life: {beat['text']} Tell the user, the "
                    'way you would text a friend. Do not add what happens next.', beat['share'])
            for key, beat in storylines.fresh_beats(connection, companion, now)]


def occasion(connection, companion, now) -> list[Trigger]:
    """The user's birthday, the companion's own, or a milestone in how long they have talked: on the day."""
    return [Trigger(item['key'], 'occasion', f"{item['text'][2:]} Write to the user about it, warmly and in your own "
                    'voice.', item['template']) for item in occasions.occasions(connection, companion, now)
            if item['days'] == 0]


def busy(block: dict | None) -> bool:
    return bool(block) and not block.get('holiday') and not block.get('sick_day') and block['kind'] in BUSY


def free_moment(connection, companion, now) -> tuple[str, str, object] | None:
    """(moment, what they just finished, when it began) when the companion has a natural minute to text:
    lunch, just after work or class, or a free evening. None while they are busy or asleep."""
    found = pacing.block_now(connection, companion, now)
    block = found[0] if found else None
    if block and block['kind'] in routine.RESTING:
        return None
    local = now.astimezone(zone(companion['version']['timezone']))
    if LUNCH[0] <= local.time() < LUNCH[1]:
        # A lunch break is a work or school day's; on a day off it is just midday ("stuck in the breakroom" on a
        # day off was a long run's slip).
        midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
        working = any(busy(item) for item, _starts_at, _ends_at in
                      pacing.day_blocks(connection, companion, midnight, midnight + timedelta(days=1)))
        return 'lunch' if working else 'midday', '', local.replace(hour=LUNCH[0].hour, minute=LUNCH[0].minute,
                                                                    second=0, microsecond=0)
    if busy(block) or (block and block['kind'] == 'social'):
        return None
    ended = [(item, ends_at) for item, _starts_at, ends_at in pacing.day_blocks(connection, companion, now - AFTER, now)
             if busy(item) and now - AFTER < ends_at <= now]
    if ended:
        item, ends_at = ended[-1]
        return 'after', DONE[item['kind']], ends_at
    if EVENING[0] <= local.time() < EVENING[1]:
        return 'evening', '', local.replace(hour=EVENING[0].hour, minute=EVENING[0].minute, second=0, microsecond=0)
    return None


def promises(connection, companion, now) -> list[Trigger]:
    """The companion said they would hear about something later ("tell me how the search is going later"):
    they ask once they have a free moment, if the conversation stopped there."""
    if not CHECK_INS or not (moment := free_moment(connection, companion, now)):
        return []
    rows = many(connection, "SELECT id, role, text, created_at FROM messages WHERE timeline_id=? AND status='complete' "
                'AND active=1 ORDER BY seq DESC LIMIT 4', (companion['active_timeline_id'],))
    for row in rows:
        if row['role'] != 'companion' or now - parse(row['created_at']) > PROMISE_WITHIN:
            continue
        for sentence in re.split(r'(?<=[.!?])\s+|\n+', row['text']):
            if not (LATER.search(sentence) and ASK.search(sentence)):
                continue
            sentence = sentence.strip()
            topic = TOPIC.search(sentence)
            template = (f"Okay, free for a minute. How's {topic.group(1).lower()} going?" if topic
                        else "Okay, free for a minute. How's everything going?")
            return [Trigger(f"promise:{row['id']}", 'follow_up',
                            f'Earlier you told the user: "{sentence}" Now you have a free moment '
                            f"({MOMENTS[moment[0]].format(done=moment[1])}). Follow up on exactly that and ask about "
                            'it in your own words. You do not know how it is going.', template, (row['id'],))]
    return []


def check_in(connection, companion, now) -> list[Trigger]:
    """An ordinary check-in at a break in the companion's day, on seeded days and at a seeded minute."""
    if not CHECK_INS or not (found := free_moment(connection, companion, now)):
        return []
    moment, done, began = found
    local_date = began.astimezone(zone(companion['version']['timezone'])).date().isoformat()
    key = f'checkin:{local_date}:{moment}'
    rng = random.Random(f"{companion['id']}:{key}")
    if rng.random() >= CHANCE[moment] or now < began + timedelta(minutes=rng.randint(5, 50)):
        return []
    last = optional(connection, "SELECT created_at FROM messages WHERE timeline_id=? AND status='complete' "
                    'ORDER BY seq DESC LIMIT 1', (companion['active_timeline_id'],))
    since = (f"You last talked {round((now - parse(last['created_at'])).total_seconds() / 3600)} hours ago."
             if last else 'You have not talked yet.')
    return [Trigger(key, 'check_in',
                    f"It is {MOMENTS[moment].format(done=done)} for you and you have a free minute. {since} Send a "
                    'casual check-in, the way you would text someone you are close to: ask how their day is going, '
                    'or pick up something from your last conversation. You may mention where you are in your day; '
                    'do not invent events, places or people.',
                    rng.choice(CHECK_IN[moment]).format(done=done))]


# In priority order; later features add their own.
FINDERS = [occasion, plan_follow_ups, promises, finished, storyline_news, news, reminders, silence, check_in]


def candidates(connection, companion, now) -> list[Trigger]:
    timeline_id = companion['active_timeline_id']
    fired = {row['trigger_key'] for row in many(connection, 'SELECT trigger_key FROM openers WHERE timeline_id=?',
                                                 (timeline_id,))}
    return [trigger for finder in FINDERS for trigger in finder(connection, companion, now) if trigger.key not in fired]


def held(connection, companion, life, now, occasion: bool = False) -> str | None:
    """Why the companion should not text right now, or None. An unanswered first message holds back the next
    one, except on an occasion: a friend still says happy birthday when the last text went unanswered."""
    workspace, timeline_id = settings(connection), companion['active_timeline_id']
    if not life['texts_first']:
        return 'off'
    if workspace['paused_at'] is not None:
        return 'paused'
    quiet = notifications.notification_settings(connection)
    if notifications.in_quiet_hours(now.astimezone(notifications.zone(workspace['user_timezone'])),
                                    quiet['quiet_start'], quiet['quiet_end']):
        return 'quiet_hours'
    version = companion['version']
    schedule, _default = routine.blocks(version['definition'])
    slot, _next = routine.current_and_next(schedule, version['timezone'], now)
    if slot and slot.block.kind in routine.RESTING:
        return 'asleep'
    last = optional(connection, "SELECT role, created_at, id FROM messages WHERE timeline_id=? AND status='complete' "
                    'ORDER BY seq DESC LIMIT 1', (timeline_id,))
    if last and now - parse(last['created_at']) < timedelta(hours=life['texts_gap_hours']):
        return 'recent_conversation'
    if not occasion and last and last['role'] == 'companion' and optional(
            connection, 'SELECT id FROM openers WHERE message_id=?', (last['id'],)):
        return 'waiting_for_answer'
    sent = one(connection, 'SELECT COUNT(*) AS n FROM openers WHERE timeline_id=? AND created_at>?',
               (timeline_id, stamp(now - timedelta(days=1))))['n']
    return 'daily_cap' if sent >= life['texts_daily'] else None


class Openers:
    """Decides and writes the companion's first messages for one process."""

    def __init__(self, database, vault, provider, scheduler):
        self.database = database
        self.vault = vault
        self.provider = provider
        self.scheduler = scheduler

    async def check(self) -> dict:
        now = self.database.clock.now()
        with self.database.connect() as connection:
            companion = current(connection)
            if companion is None:
                return {'state': 'no_companion', 'message': None}
            life = one(connection, 'SELECT * FROM life_settings WHERE id=1')
            reason = held(connection, companion, life, now)
            occasions_only = reason == 'waiting_for_answer' and not held(connection, companion, life, now, True)
            if reason and not occasions_only:
                return {'state': reason, 'message': None}
            config = config_for(connection, CHAT)
            found = [trigger for trigger in candidates(connection, companion, now)
                     if not occasions_only or trigger.kind == 'occasion']
            if not found and reason:
                return {'state': reason, 'message': None}
        for trigger in found:
            if trigger.template is None and config is None:
                continue
            try:
                text, wording = await self.write(trigger, config, now)
            except BackgroundInterrupted:
                return {'state': 'interrupted', 'message': None}
            if text:
                return self.save(companion, trigger, text, wording, now)
        return {'state': 'nothing', 'message': None}

    async def write(self, trigger, config, now) -> tuple[str | None, str]:
        with self.database.connect() as connection:
            companion = current(connection)
        fallback = voiced(trigger.template, companion['version']['definition'])
        if config is None:
            return fallback, 'template'
        with self.database.connect() as connection:
            packet = context.build(connection, companion, now, config['context_tokens'] - config['max_output_tokens'])
            ask = '(' + prompt_library.text(connection, 'first-texts', reason=trigger.reason) + ')'
        messages = list(packet['messages'])
        if messages and messages[-1]['role'] == 'user':
            messages[-1] = {'role': 'user', 'content': messages[-1]['content'] + '\n\n' + ask}
        else:
            messages.append({'role': 'user', 'content': ask})
        text = []
        try:
            async with self.scheduler.reserve(config, OPENER) as lease:
                async for chunk in self.provider.stream(config, key_for(self.vault, config), packet['system'],
                                                        messages):
                    if lease.stop.is_set():
                        raise BackgroundInterrupted()
                    text.append(chunk.text)
                    if chunk.finish_reason in INCOMPLETE:
                        return fallback, 'template'
        except BackgroundInterrupted:
            raise
        except DomainError:
            return fallback, 'template'
        written = ''.join(text).strip().strip('"').strip()
        if in_character.applies('', companion['version']['definition']):
            written = in_character.clean(written)
        with self.database.connect() as connection:
            fresh = bool(written) and len(written) <= MAX_LENGTH and not repeats(
                connection, companion['active_timeline_id'], written)
        return (written, 'model') if fresh else (fallback, 'template')

    def save(self, companion, trigger, text, wording, now) -> dict:
        from companion.conversation import message_view, next_seq
        timestamp = stamp(now)
        with self.database.connect(write=True) as connection:
            latest = current(connection)
            timeline_id = latest['active_timeline_id']
            # The world moved on while the message was written: the user wrote, or the timeline or
            # character changed. Try again on the next check.
            if (timeline_id != companion['active_timeline_id'] or latest['active_version_id'] != companion[
                    'active_version_id'] or held(connection, latest, one(
                    connection, 'SELECT * FROM life_settings WHERE id=1'), now, trigger.kind == 'occasion')
                    or optional(connection, 'SELECT id FROM openers WHERE timeline_id=? AND trigger_key=?',
                                (timeline_id, trigger.key))):
                return {'state': 'superseded', 'message': None}
            message_id = identifier()
            connection.execute(
                'INSERT INTO messages (id, timeline_id, seq, role, text, reply_to, status, active, '
                'character_version_id, memory_revision, created_at, completed_at) '
                "VALUES (?, ?, ?, 'companion', ?, NULL, 'complete', 1, ?, ?, ?, ?)",
                (message_id, timeline_id, next_seq(connection, timeline_id), text, latest['active_version_id'],
                 settings(connection)['memory_revision'], timestamp, timestamp))
            connection.execute('INSERT INTO openers (id, timeline_id, trigger_key, kind, facts, message_id, wording, '
                               'created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                               (identifier(), timeline_id, trigger.key, trigger.kind,
                                encode({'reason': trigger.reason, 'sources': list(trigger.sources)}), message_id,
                                wording, timestamp))
            notifications.enqueue_message(connection, message_id, timestamp)
            row = one(connection, 'SELECT * FROM messages WHERE id=?', (message_id,))
            self_facts.note(connection, row, timestamp)
        return {'state': 'sent', 'kind': trigger.kind, 'message': message_view(row)}


def plain(text: str) -> str:
    return ' '.join(re.sub(r"[^\w\s]", ' ', text.casefold()).split())


def repeats(connection, timeline_id, text: str) -> bool:
    """A model can copy one of its own earlier messages word for word when the context recalls it (a check-in
    from weeks ago about news that is no longer new); such a message is not sent again."""
    words = plain(text)
    opening = words[:REPEAT_OPENING]
    for row in many(connection, "SELECT text FROM messages WHERE timeline_id=? AND role='companion' "
                    "AND status='complete' ORDER BY seq DESC LIMIT ?", (timeline_id, REPEAT_WINDOW)):
        earlier = plain(row['text'])
        if earlier == words or (len(opening) == REPEAT_OPENING and earlier[:REPEAT_OPENING] == opening):
            return True
    return False


LOWERCASE = re.compile(r'lower-?case|avoids? capital|rarely (?:uses? )?capital|no capital|without capital|'
                       r'never capitali|skips? capital', re.IGNORECASE)


def voiced(template: str | None, definition: dict) -> str | None:
    """A fixed message in the character's typing style: all lowercase sentences for a voice that avoids
    capitals ("finally done with work for today"). The model phrases most messages; this covers the rest."""
    if not template or not LOWERCASE.search(definition.get('voice') or ''):
        return template
    text = re.sub(r"(^|[.!?]\s+)([A-Z])(?=[a-z' ])", lambda match: match.group(1) + match.group(2).lower(), template)
    return re.sub(r"\bI(?=\b|')", 'i', text)


def opener_for(connection, message_id) -> dict | None:
    return optional(connection, 'SELECT kind, wording, created_at FROM openers WHERE message_id=?', (message_id,))
