"""Group chat moods (Feature Hit List #14, wave E): how each member feels right now, who they're not speaking to,
and walking out (docs/group-chat.md, "Moods").

Every member has at most one current mood (`group_moods`): a feeling (calm, happy, excited, annoyed, hurt, angry,
anxious, sad), an intensity from 1 to 3 and, for some, who it is about. All by rules, never a model:

- Events lead. Finding out a secret that was kept from them (companion/secrets.py) hurts, toward whoever it is
  about: hurt 2, or furious (angry 3) for someone with a temper. A storyline beat of their own that turned out badly
  today leaves them sad, and a good one happy, when nothing else is going on.
- A reply nudges it: a sentence of their own that names a feeling and another member ("honestly I'm so annoyed
  with Sally") moves that feeling toward that person one step, never past 2 (angry replies alone never reach
  furious, so two members can't talk each other into walking out). Negations, quotes, "lol" and "jk" don't count,
  and it is at most one step a reply.
- It fades a step every `FADE` and resets overnight, their time.
- Only someone with a temper gets angry: a temper the user wrote into their character ("hot-tempered", "quick to
  anger"), or the temper flaw a townsperson came with. Anyone else tops out at annoyed or hurt.

What it does, the ladder:
- annoyed: their replies stay short;
- hurt or angry at 2 or more toward someone here: they ignore them. They are never picked to answer them, their
  prompt says "You're not speaking to Sally right now", and a reply that still names Sally is written once more;
- furious toward someone here for `WALK_OUT_REPLIES` replies, or two people furious at each other (the one with
  the stronger temper goes first): they walk out ("Billy left the group."), only when the group's "People can walk
  out" switch is on (off by default). They can be added back once they're no longer angry; until then Add says why.

The profile in the group's people panel shows each member's mood, read-only, with its reason.
"""
import random
import re
from datetime import timedelta

from companion.characters import by_id
from companion.clock import parse, stamp, zone
from companion.database import optional
from companion.life import storylines
from companion.world import perception

FEELINGS = ('calm', 'happy', 'excited', 'annoyed', 'hurt', 'angry', 'anxious', 'sad')
FADE = timedelta(hours=3)
WALK_OUT_REPLIES = 3
NUDGE_LIMIT = 2
IGNORES = ('hurt', 'angry')
IGNORE_LEVEL = 2
# How a reply's words name a feeling; longer phrases first.
WORDS = (
    ('angry', r'angry|mad at|furious|pissed|livid'),
    ('hurt', r'hurt|upset with|let down|betrayed'),
    ('annoyed', r'annoyed|irritated|fed up|sick of|over it'),
    ('anxious', r'worried|anxious|nervous'),
    ('excited', r'excited|thrilled|can\'t wait'),
    ('happy', r'happy|glad|grateful'),
    ('sad', r'sad|miss'),
)
NEGATION = re.compile(r"\b(?:not|never|isn't|aren't|wasn't|don't|didn't|no)\b", re.IGNORECASE)
JOKING = re.compile(r'\b(?:lol|lmao|jk|haha\w*|kidding)\b|["“”]', re.IGNORECASE)
SENTENCE = re.compile(r'(?<=[.!?])\s+|\n+')
TEMPER = re.compile(r"\b(?:hot[- ]?tempered|short[- ]tempered|quick[- ]tempered|bad[- ]tempered|(?:a|her|his|their|"
                    r"short|quick|bad|fiery|explosive) temper|hot[- ]?headed|quick to anger|easily angered|"
                    r"flies off the handle|volatile)\b", re.IGNORECASE)
SHEET_FIELDS = ('identity', 'personality', 'voice', 'background', 'flaws')
ADVERB = {1: 'a bit ', 2: '', 3: 'really '}
PREPOSITION = {'annoyed': 'with', 'hurt': 'by', 'angry': 'at', 'happy': 'with', 'excited': 'about',
               'anxious': 'about', 'sad': 'about'}


# Who has a temper ----------------------------------------------------------------------------------------

def temper(connection, key: str) -> int:
    """How strong a member's temper is: 0 without one. The user's words on the character, or the temper flaw a
    companion made from a townsperson came with."""
    companion_id = key.removeprefix('companion:') if key.startswith('companion:') else None
    companion = by_id(connection, companion_id) if companion_id else None
    if companion is None:
        return 0
    definition = companion['version']['definition']
    text = ' '.join(' '.join(value) if isinstance(value, list) else str(value or '')
                    for value in (definition.get(field) for field in SHEET_FIELDS))
    found = sum(1 for match in TEMPER.finditer(text) if not NEGATION.search(text[max(0, match.start() - 12):match.start()]))
    if companion.get('townsfolk_key') and perception.for_companion(companion['id'], definition)['picks'].get(
            'flaw') == 'temper':
        found += 1
    return found


def capped(feeling: str, intensity: int, has_temper: bool) -> tuple[str, int]:
    """Anger needs a temper; without one it is hurt, at most 2."""
    if feeling == 'angry' and not has_temper:
        return 'hurt', min(intensity, 2)
    return feeling, max(1, min(intensity, 3))


# Reading and writing ----------------------------------------------------------------------------------------

def local_day(connection, key: str, instant) -> str:
    companion = by_id(connection, key.removeprefix('companion:')) if key.startswith('companion:') else None
    timezone = zone(companion['version']['timezone']) if companion else zone('UTC')
    return instant.astimezone(timezone).date().isoformat()


def stored(connection, key: str, now) -> dict | None:
    """The mood as it stands now: faded a step per FADE since it last changed, gone overnight."""
    row = optional(connection, 'SELECT * FROM group_moods WHERE holder=?', (key,))
    if row is None or row['day'] != local_day(connection, key, now):
        return None
    intensity = row['intensity'] - int((now - parse(row['updated_at'])) / FADE)
    return {**row, 'intensity': intensity} if intensity > 0 else None


def from_today(connection, key: str, now) -> dict | None:
    """With nothing else going on: sad or happy about how a storyline of theirs turned out today."""
    companion = by_id(connection, key.removeprefix('companion:')) if key.startswith('companion:') else None
    if companion is None:
        return None
    today = storylines.local_today(companion, now).isoformat()
    for item in storylines.visible(connection, companion, now):
        beat = next((beat for beat in reversed(item['beats']) if beat['on'] == today and beat['tone']), None)
        if beat and beat['tone'] in ('good', 'bad') and item['story'] not in ('secret_couple', 'family_secret'):
            return {'holder': key, 'feeling': 'happy' if beat['tone'] == 'good' else 'sad', 'intensity': 1,
                    'target': None, 'reason': beat['text'].rstrip('.'), 'furious_replies': 0}
    return None


def current(connection, key: str, now) -> dict | None:
    """Someone's mood right now, or None for calm."""
    return stored(connection, key, now) or from_today(connection, key, now)


def save(connection, key: str, feeling: str, intensity: int, target: str | None, reason: str, now):
    feeling, intensity = capped(feeling, intensity, temper(connection, key) > 0)
    connection.execute(
        'INSERT INTO group_moods (holder, feeling, intensity, target, reason, day, furious_replies, updated_at) '
        'VALUES (?, ?, ?, ?, ?, ?, 0, ?) ON CONFLICT(holder) DO UPDATE SET feeling=excluded.feeling, '
        'intensity=excluded.intensity, target=excluded.target, reason=excluded.reason, day=excluded.day, '
        'furious_replies=0, updated_at=excluded.updated_at',
        (key, feeling, intensity, target, reason[:300], local_day(connection, key, now), stamp(now)))


def furious(mood: dict | None) -> bool:
    return bool(mood) and mood['feeling'] == 'angry' and mood['intensity'] >= 3


def ignores(mood: dict | None, other: str) -> bool:
    """Whether this mood means not speaking to `other`."""
    return bool(mood) and mood['target'] == other and mood['feeling'] in IGNORES and mood['intensity'] >= IGNORE_LEVEL


# Events ---------------------------------------------------------------------------------------------------

def found_out(connection, secret: dict, member: str, now):
    """`member` found out a secret that was kept from them: hurt, or furious with a temper, toward whoever it's
    about (the first person in it who is in the app)."""
    target = next((subject['key'] for subject in secret['subjects']
                   if subject.get('key') and subject['key'] != member), None)
    if target is None:
        return
    feeling, intensity = ('angry', 3) if temper(connection, member) else ('hurt', 2)
    save(connection, member, feeling, intensity, target, f"found out {secret['statement'].rstrip('.')}", now)


def feeling_in(sentence: str) -> str | None:
    for feeling, pattern in WORDS:
        found = re.search(rf"\b(?:{pattern})\b", sentence, re.IGNORECASE)
        if found and not NEGATION.search(sentence[:found.start()][-20:]):
            return feeling
    return None


def named(sentence: str, members: list[dict], author: str) -> str | None:
    for stay in members:
        if stay['member'] == author:
            continue
        words = {stay['name'], stay['name'].split()[0]}
        if any(re.search(rf'(?<!\w){re.escape(word)}(?!\w)', sentence, re.IGNORECASE) for word in words if word):
            return stay['member']
    return None


def nudge(connection, author: str, text: str, members: list[dict], now) -> bool:
    """A reply of theirs names a feeling and another member in one sentence: that feeling toward them moves a
    step, never past NUDGE_LIMIT. Returns whether it moved."""
    for sentence in SENTENCE.split(text or ''):
        if JOKING.search(sentence):
            continue
        feeling, target = feeling_in(sentence), named(sentence, members, author)
        if feeling is None or target is None:
            continue
        mood = stored(connection, author, now)
        same = mood and mood['feeling'] == capped(feeling, 1, temper(connection, author) > 0)[0] \
            and mood['target'] == target
        if same and mood['intensity'] >= NUDGE_LIMIT:
            return False
        intensity = mood['intensity'] + 1 if same else 1
        name = next(stay['name'] for stay in members if stay['member'] == target)
        save(connection, author, feeling, intensity, target, f'said they were {feeling} {PREPOSITION[feeling]} '
             f'{name}', now)
        return True
    return False


def counted(connection, author: str, now):
    """One more reply while furious."""
    if furious(stored(connection, author, now)):
        connection.execute('UPDATE group_moods SET furious_replies=furious_replies+1 WHERE holder=?', (author,))


def walking_out(connection, members: list[dict], now) -> dict | None:
    """Who walks out now, if anyone: two members furious at each other (the stronger temper first, ties by the
    seeded dice), or someone furious at a member here for WALK_OUT_REPLIES replies."""
    here = {stay['member']: stay for stay in members}
    moods = {member: stored(connection, member, now) for member in here}
    for member, mood in moods.items():
        if not furious(mood) or mood['target'] not in here:
            continue
        other = moods.get(mood['target'])
        if furious(other) and other['target'] == member:
            pair = sorted((member, mood['target']))
            strengths = [temper(connection, key) for key in pair]
            if strengths[0] == strengths[1]:
                return here[random.Random(f"walk:{'|'.join(pair)}").choice(pair)]
            return here[pair[strengths.index(max(strengths))]]
        if mood['furious_replies'] >= WALK_OUT_REPLIES:
            return here[member]
    return None


def blocked(connection, key: str, members: list[dict], now) -> str | None:
    """Why someone can't be added back yet: still angry at someone in the group."""
    mood = stored(connection, key, now)
    if mood and mood['feeling'] == 'angry' and mood['target'] in {stay['member'] for stay in members}:
        name = next(stay['name'] for stay in members if stay['member'] == mood['target'])
        companion = by_id(connection, key.removeprefix('companion:'))
        first = companion['version']['name'].split()[0] if companion else 'They'
        return f'{first} is still angry at {name}.'
    return None


# Showing it ----------------------------------------------------------------------------------------------

def text(mood: dict | None, labels: dict[str, str]) -> str:
    """"Seems angry at Sally", "Seems a bit sad"; "Seems calm" without a mood."""
    if not mood:
        return 'Seems calm'
    word = 'furious' if furious(mood) else f"{ADVERB[mood['intensity']]}{mood['feeling']}"
    target = labels.get(mood['target']) if mood['target'] else None
    return f"Seems {word}" + (f" {'at' if mood['feeling'] == 'angry' else PREPOSITION[mood['feeling']]} {target}"
                              if target else '')


def view(connection, key: str, labels: dict[str, str], now) -> dict:
    mood = current(connection, key, now)
    return {'feeling': mood['feeling'] if mood else 'calm', 'intensity': mood['intensity'] if mood else 0,
            'text': text(mood, labels), 'reason': mood['reason'] if mood else None,
            'ignoring': labels.get(mood['target']) if mood and ignores(mood, mood['target']) else None}


def lines(connection, speaker: str, members: list[dict], now) -> list[tuple[str, str]]:
    """The speaker's own mood for their group section, and who they're not speaking to."""
    mood = current(connection, speaker, now)
    if not mood:
        return []
    labels = {stay['member']: stay['name'] for stay in members}
    target = labels.get(mood['target'])
    word = 'furious' if furious(mood) else f"{ADVERB[mood['intensity']]}{mood['feeling']}"
    about = f" {'at' if mood['feeling'] == 'angry' else PREPOSITION[mood['feeling']]} {target}" if target else ''
    result = [(f"mood:{mood['feeling']}:{mood['intensity']}:{mood['target']}",
               f"- Right now you feel {word}{about} (why: {mood['reason']}).")]
    if mood['feeling'] == 'annoyed':
        result.append(('mood:short', '- Keep your messages short while you feel this way.'))
    if target and ignores(mood, mood['target']):
        result.append((f"mood:ignoring:{mood['target']}", f"- You're not speaking to {target} right now; talk to the "
                       f"others, not to {target}."))
    return result


def ignored_named(connection, speaker: str, reply: str, members: list[dict], now) -> str | None:
    """The member a reply names although the speaker isn't speaking to them, if any."""
    mood = stored(connection, speaker, now)
    if not mood or not ignores(mood, mood['target']):
        return None
    stay = next((item for item in members if item['member'] == mood['target']), None)
    if stay and named(reply, [stay], speaker):
        return stay['name']
    return None


def forget(connection, key: str):
    """Start over or Delete: their mood goes, and nobody stays upset with them."""
    connection.execute('DELETE FROM group_moods WHERE holder=? OR target=?', (key, key))
