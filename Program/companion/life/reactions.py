"""How a companion takes what the user did, through the consequence engine (companion/consequences.py).

Only four things count, each one the app can tell happened without guessing: the user telling someone a secret in
a group chat, an agreed plan with a date passing with no message from the user that day, the user chatting on the
companion's birthday or a first-talk anniversary without mentioning it, and the user adding someone to a group with
"show everything". Each is a choice in the odds tables (`user:*`): how likely it is to sting comes only from an
emotional trait the user built into the character whose name speaks to it (`MINDS`), so without one she lets it go.
A sting leaves a mood mark for a few days that the chat context tells her as "you", so she can bring it up once in
her own words; it never cools closeness. Odds show only in "Why it went this way" and out-of-character answers.
"""
import re
from datetime import date, timedelta

from companion import consequences, secrets
from companion.characters import by_id
from companion.clock import parse, stamp, zone
from companion.database import many, settings
from companion.errors import require
from companion.life import occasions, storylines
from companion.memory import pairs
from companion.traits import LEVELS

# Words in an emotional trait's name that make it about each choice.
MINDS = {
    'user:told_secret': r'trust|betray|priva|secret|loyal|guarded',
    'user:missed_plan': r'let ?down|disappoint|reliab|flak|abandon|neglect|need|clingy|lonely|sulk|sensitive',
    'user:forgot_occasion': r'forg[eo]t|birthday|anniversar|sentimental|sensitive|need|attention|neglect|sulk',
    'user:showed_everything': r'priva|guarded|secret|trust|shy|parano',
}
MENTIONS = re.compile(r"\b(?:birthday|bday|b-day|anniversary)\b", re.IGNORECASE)
LOOK_BACK = 3  # Days back the daily check looks for a plan or an occasion that passed.


def minds(definition: dict, choice: str) -> tuple[int, str]:
    """(intensity 0 to 3, trait name) of the strongest emotional trait about this choice."""
    found = [(LEVELS.get(trait.get('intensity'), 1), trait['name'])
             for trait in definition.get('emotional_traits') or []
             if re.search(MINDS[choice], trait.get('name', ''), re.IGNORECASE)]
    return max(found, default=(0, ''))


def react(connection, companion: dict, choice: str, subject: str, names: dict, day: str, now) -> dict:
    """Decide once how the companion takes it, with the marks it leaves; a second call returns the first."""
    definition = companion['version']['definition']
    level, trait = minds(definition, choice)
    names = {'name': definition['name'].split()[0], 'a': 'someone', 'b': '', 'trait': trait, **names}
    table = consequences.tables()[choice]
    return consequences.decide(
        connection, timeline_id=companion['active_timeline_id'], choice=choice, subject=subject,
        facts={'minds': level}, names=names, labels=[option['label'].format(**names) for option in table['options']],
        day=day, timestamp=stamp(now), holders={'me': pairs.companion_key(companion['id'])}, now=now)


def what_if(companion: dict, choice: str, names: dict) -> list[dict]:
    """The odds for a choice the user hasn't made, for out-of-character "what if" answers; nothing is rolled."""
    definition = companion['version']['definition']
    level, trait = minds(definition, choice)
    names = {'name': definition['name'].split()[0], 'a': 'someone', 'b': '', 'trait': trait, **names}
    found = consequences.odds(choice, {'minds': level}, names)
    for item, option in zip(found, consequences.tables()[choice]['options'], strict=True):
        item['label'] = option['label'].format(**names)
    return found


# The four things the user can do ----------------------------------------------------------------------

def told_secret(connection, secret: dict, told: str, now):
    """The user told someone a secret it was kept from: each companion who held it from the start reacts."""
    listener = secrets.label(connection, told, {})
    for holder in held_by(connection, secret['id']):
        companion = by_id(connection, pairs.companion_id(holder) or '')
        if companion and companion['active_timeline_id']:
            react(connection, companion, 'user:told_secret', f"secret:{secret['id']}:{told}>{holder}", {'a': listener},
                  local_day(companion, now), now)


def showed_everything(connection, group: dict, added: str, now):
    """The user added someone with everything so far: members who had said something there react."""
    newcomer = secrets.label(connection, added, {})
    spoke = {row['author'] for row in many(connection, "SELECT DISTINCT author FROM group_messages WHERE group_id=? "
                                           "AND status='complete'", (group['id'],))}
    for member in spoke - {added}:
        companion = by_id(connection, pairs.companion_id(member) or '')
        if companion and companion['active_timeline_id']:
            react(connection, companion, 'user:showed_everything', f"group:{group['id']}:{added}>{member}",
                  {'a': newcomer, 'group': group['name'] or 'the group'}, local_day(companion, now), now)


def daily(connection, companion: dict, now) -> int:
    """Plans and occasions from the last few days that passed without a word from the user. Returns how many."""
    timezone = zone(settings(connection)['user_timezone'])
    today = now.astimezone(timezone).date()
    found = 0
    for day in (today - timedelta(days=offset) for offset in range(1, LOOK_BACK + 1)):
        said = user_messages(connection, companion['active_timeline_id'], day, timezone)
        for plan in agreed_plans(connection, companion, day):
            if not said:
                react(connection, companion, 'user:missed_plan', f"plan:{plan['id']}", {'plan': plan['value']},
                      day.isoformat(), now)
                found += 1
        what = occasion_on(connection, companion, day, timezone)
        if what and said and not any(MENTIONS.search(text) for text in said):
            react(connection, companion, 'user:forgot_occasion', f"occasion:{companion['active_timeline_id']}:{day.isoformat()}", {'occasion': what},
                  day.isoformat(), now)
            found += 1
    return found


def user_messages(connection, timeline_id: str, day: date, timezone) -> list[str]:
    rows = many(connection, "SELECT text, created_at FROM messages WHERE timeline_id=? AND role='user' "
                "AND status='complete' AND created_at>=? AND created_at<?",
                (timeline_id, stamp(local_start(day - timedelta(days=1), timezone)),
                 stamp(local_start(day + timedelta(days=2), timezone))))
    return [row['text'] for row in rows if parse(row['created_at']).astimezone(timezone).date() == day]


def local_start(day: date, timezone):
    from datetime import datetime, time
    return datetime.combine(day, time(), timezone)


def agreed_plans(connection, companion: dict, day: date) -> list[dict]:
    """Agreed plans with the user set for that day, with a sure date."""
    return many(connection, "SELECT id, value FROM memories WHERE timeline_id=? AND status='active' AND layer='plan' "
                "AND plan_status='agreed' AND dates_uncertain=0 AND substr(applies_from, 1, 10)=?",
                (companion['active_timeline_id'], day.isoformat()))


def occasion_on(connection, companion: dict, day: date, timezone) -> str | None:
    """'your birthday', or how long since the first talk on an anniversary of it, when that day was one."""
    mine = occasions.own_birthday(companion)
    if mine and occasions.on(day, mine):
        return 'your birthday'
    first = occasions.first_talk(connection, companion['active_timeline_id'], timezone)
    span = occasions.milestone(first, day) if first and day > first else None
    return f'{span} since you two first talked' if span else None


def local_day(companion: dict, now) -> str:
    return now.astimezone(zone(companion['version']['timezone'])).date().isoformat()


def lately_lines(connection, companion: dict, now) -> list[tuple[str, str]]:
    return consequences.lately_lines(connection, companion['active_timeline_id'],
                                     pairs.companion_key(companion['id']), local_day(companion, now))


def held_by(connection, secret_id: str) -> list[str]:
    return [row['holder'] for row in many(connection, "SELECT holder FROM knowledge_holders WHERE knowledge_id=? "
                                          "AND via='origin' AND ended_at IS NULL", (secret_id,))]


# Today ----------------------------------------------------------------------------------------------------

RECENT_DAYS = 30


def listing(database) -> list[dict]:
    """How the companion took what the user did over the last month, newest first, for Today."""
    from companion.characters import require_current
    with database.connect() as connection:
        companion = require_current(connection)
        since = (date.fromisoformat(local_day(companion, database.clock.now())) - timedelta(days=RECENT_DAYS))
        return consequences.recent(connection, companion['active_timeline_id'], 'user:', since.isoformat())


def change(database, consequence_id: str, option: int) -> dict:
    """The user changes how the companion took it; the marks follow."""
    from companion.characters import require_current
    with database.connect(write=True) as connection:
        found = consequences.by_id(connection, consequence_id)
        companion = require_current(connection)
        require(found['timeline_id'] == companion['active_timeline_id'], 'That outcome is not on this timeline.', 404)
        now = database.clock.now()
        return consequences.redo(connection, consequence_id, option, now, date.fromisoformat(local_day(companion, now)))


# Out of character: "what if?" -----------------------------------------------------------------------------

AHEAD = 7  # Days ahead an occasion or plan counts for "what if" answers.


def what_if_note(connection, companion: dict, now) -> str:
    """The odds the app worked out for what could happen, for an out-of-character answer. Nothing here is rolled,
    so asking spoils nothing and changes nothing."""
    lines = [f"- {item['label']} (due {item['on']}): {odds_text(item['options'])}"
             for item in storylines.upcoming_odds(connection, companion, now)]
    lines += [f'- {situation}: {odds_text(found)}' for situation, found in user_what_ifs(connection, companion, now)]
    if not lines:
        return ''
    return ('If the user asks what would happen if something went a certain way, answer honestly from these odds, '
            'which the app worked out from everything it knows. Say them in plain words ("most likely..., about 7 in '
            "10\"), as odds, never as what will happen; nothing has been decided yet:\n" + '\n'.join(lines))


def odds_text(options: list[dict]) -> str:
    likely = sorted(options, key=lambda item: -item['odds'])
    parts = [f"{item['label'].rstrip('.')} (about {round(item['odds'] * 100)}%"
             + (f"; {'; '.join(item['reasons'])})" if item['reasons'] else ')') for item in likely if item['odds'] > 0]
    ruled_out = [reason for item in likely if item['odds'] == 0 for reason in item['reasons']]
    return '; '.join(parts) + (f" (ruled out: {'; '.join(ruled_out)})" if ruled_out else '')


def user_what_ifs(connection, companion: dict, now) -> list[tuple[str, list[dict]]]:
    """(situation, odds) for the user's own choices the app would notice."""
    me, found = pairs.companion_key(companion['id']), []
    for secret in secrets.active(connection):
        if me in held_by(connection, secret['id']):
            for member in secret['guarded']:
                name = secrets.label(connection, member, {})
                found.append((f"If the user told {name} that {secret['statement'].rstrip('.')}",
                              what_if(companion, 'user:told_secret', {'a': name})))
    timezone = zone(settings(connection)['user_timezone'])
    today = now.astimezone(timezone).date()
    for day in (today + timedelta(days=offset) for offset in range(AHEAD + 1)):
        for plan in agreed_plans(connection, companion, day):
            found.append((f"If the plan ({plan['value']}) on {day.isoformat()} passed without a word from the user",
                          what_if(companion, 'user:missed_plan', {'plan': plan['value']})))
        if what := occasion_on(connection, companion, day, timezone):
            found.append((f"If the user chatted on {day.isoformat()} ({what}) without mentioning it",
                          what_if(companion, 'user:forgot_occasion', {'occasion': what})))
    return found
