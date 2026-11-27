"""Private moments in a Story scene (1.5.1, docs/story.md): what the user whispers, shows or passes to one person
is for that person alone.

Rules only, no model call of its own. A line of the user's holds a private moment when it says so in plain words
(PRIVATE: a whisper, something said in someone's ear or under their breath, a note passed, something shown so that
nobody else sees it). Anything else is said in the open, and so is a line that also says it is out loud (OPEN). Who
it was for is the person in the scene the line names, by name or by what the screen calls them ("the server"), the
one nearest the words that make it private; with nobody named, the only other person there. A line that names
nobody the scene knows, with several people there, is private but for nobody the rules can tell.

What follows from it:
- The narrator is told right after the user's line that it was for that person alone (NOTE), and the line keeps a
  tag (TAG) in what the narrator and the companions read for as long as the story stays at the place.
- Only the one it was for answers: a companion it was not for takes no turn (companion/story_cast.py, `speakers`),
  and one it was for is told so in their own notes (OWN). Their answer is as private as the line (REPLY_TAG).
- Only the one it was for hears it in the secrets and news ledgers (companion/story_secrets.py, `heard`). The
  townsfolk the narrator voices are in neither, so from them it goes no further.
- A companion it was not for does not read the words in the scene either: in their scene so far the line is a note
  that something passed (UNHEARD), and so is the answer of the companion it was for (`unheard`).
- A companion it was not for is not told of it in their own chat either, during the visit or after it: the line
  keeps who it was for (`mark`), and what their chat reads of the scene leaves it out (companion/story_visits.py,
  `lines_of`). One the rules can't place is left out too, unless they answered it.

The narrator's own wording has a standing line for what these phrases miss (companion/story.py, NARRATOR).
"""
import re

from companion import in_character, secrets, story_plans
from companion.database import optional
from companion.life import their_people

ACTIVE = True
_WHO = r"(?:any\s?one|anybody|no\s?one|nobody|the\s+others|others|the\s+rest|the\s+room|everyone\s+else)"
_SENSE = r"(?:see|hear|overhear|read|catch|listen)(?:s|es|ing)?|notic(?:e|es|ing)"
_SAY = r"(?:say|says|said|tell|tells|told|ask|asks|asked|add|adds|added|speak|speaks|spoke|murmur|murmurs|" \
       r"murmured|mutter|mutters|muttered)"
_WORDS = r"(?:[\w'’-]+\s+)"
# The plain words that make a line private, read as written. Anything else is said in the open.
PRIVATE = re.compile(rf"""
      \bwhisper(?:s|ed|ing)?\b(?!\s+of\b)
    | \bunder\s+(?:my|her|his|their|your)\s+breath\b
    | \bin(?:to)?\s+(?:the\s+)?(?:my|his|her|their|[\w-]+['’]s)\s+ear\b
    | \b(?:so|where)\s+(?:that\s+)?(?:only|no\s?one|nobody)\b[^.!?\n]{{0,40}}?\b(?:{_SENSE})\b
    | \b(?:careful|sure|care)\b[^.!?\n]{{0,40}}?\b{_WHO}\b[^.!?\n]{{0,25}}?\b(?:{_SENSE})\b
    | \bwithout\s+{_WORDS}{{0,2}}?{_WHO}(?:\s+else)?\s+(?:{_SENSE})\b
    | \bout\s+of\s+(?:earshot|hearing|sight\s+of)\b
    | \b(?:slip|slips|slipped|slide|slides|slid|pass|passes|passed|hand|hands|handed)\b[^.!?\n]{{0,30}}?
      \b(?:note|slip\s+of\s+paper|scrap\s+of\s+paper|folded\s+paper)\b
    | \b(?:discreetly|privately|secretly|covertly|furtively|surreptitiously|sotto\s+voce)\b
    | \bin\s+(?:private|secret)\b | \bon\s+the\s+(?:sly|quiet)\b
    | \b{_SAY}\b(?:\s+[\w'’-]+){{0,3}}?\s+(?:quietly|softly|in\s+a\s+(?:low|hushed|quiet)\s+(?:voice|tone))\b
    | \b(?:quietly|softly)\s+{_SAY}\b
    | \b(?:lower|lowers|lowered|lowering|drop|drops|dropped|dropping)\s+(?:my|her|his|their)\s+voice\b
    | \b(?:for|to)\s+{_WORDS}{{1,2}}?(?:eyes|ears)\s+only\b
    | \b(?:show|shows|showed|showing|tell|tells|told|telling)\s+(?:it\s+|this\s+|that\s+|them\s+)?only\s+
    | \bonly\s+(?:show|shows|let|lets|tell|tells)\s+(?!up\b)
    | \b(?:just\s+)?between\s+(?:us|you\s+and\s+me|the\s+two\s+of\s+us)\b
    | \b(?:pull|pulls|pulled|take|takes|took|draw|draws|drew)\s+{_WORDS}{{1,3}}?aside\b
    | \bmouth(?:s|ed|ing)?\s+(?:the\s+words?\b|silently\b|to\b|["“'‘])
    | \b(?:shield(?:s|ed|ing)?|hid(?:e|es|ing)?|cover(?:s|ed|ing)?|angl(?:e|es|ed|ing)|tilt(?:s|ed|ing)?)\b
      [^.!?\n]{{0,30}}?\b(?:from\s+(?:view|the\s+others|everyone|the\s+room|anyone)
                           |so\s+(?:that\s+)?(?:only|no\s?one|nobody))\b
    | \bcup(?:s|ped|ping)?\s+(?:a|my|her|his|their)\s+hands?\b
    """, re.IGNORECASE | re.VERBOSE)
# Said for the room after all, whatever else the line holds: it is not private.
OPEN = re.compile(r"""
      \bstage[\s-]whisper | \b(?:not|never|without)\s+(?:\w+\s+){0,2}?whisper | n['’]t\s+(?:\w+\s+){0,2}?whisper
    | \bloud\s+enough\b | \bout\s+loud\b | \baloud\b | \bannounc(?:e|es|ed|ing)\b | \bto\s+the\s+(?:whole\s+)?room\b
    | \b(?:so|for)\s+(?:that\s+)?(?:everyone|everybody|the\s+whole\s+\w+|all\s+of\s+them|the\s+room)\b[^.!?\n]{0,20}?
      \b(?:hear|see)
    | \b(?:shout|shouts|shouted|yell|yells|yelled|call\s+out|calls\s+out|called\s+out)\b
    """, re.IGNORECASE | re.VERBOSE)
# Other words people use for someone's job, by the last word of the title the scene gives it.
ALSO = {'server': ('waiter', 'waitress'), 'bartender': ('barkeep', 'barman', 'barmaid'),
        'barkeep': ('bartender', 'barman', 'barmaid'), 'barista': ('counter hand',), 'hand': ('barista',),
        'owner': ('proprietor',), 'proprietor': ('owner',), 'vendor': ('seller', 'stallholder'),
        'stallholder': ('vendor', 'seller'), 'clerk': ('cashier', 'assistant'), 'assistant': ('clerk',),
        'cook': ('chef',), 'bouncer': ('doorman',), 'doorman': ('bouncer',)}

# What the narrator is told right after the user's line ({who}: the one it was for, by name).
NOTE = ('[Private: that was for {who} alone. Nobody else here saw or heard what it was. Only {who} answers it, '
        'quietly. Everyone else carries on as if nothing was said.]')
# The same when the one it was for is a companion, who answers for themself.
NOTE_OWN = ('[Private: that was for {who} alone. Nobody else here saw or heard what it was. Everyone else carries on '
            'as if nothing was said.]')
# When the rules can't tell who it was for.
NOTE_SOMEONE = ('[Private: that was for one person alone, the one the user turned to. Nobody else here saw or heard '
                'what it was. Only that person answers it, quietly. Everyone else carries on as if nothing was said.]')
# On the line itself, in later turns at the same place: for the narrator and in a companion's scene so far.
TAG = '[Private: only {who} saw or heard this.]'
TAG_SOMEONE = '[Private: only the one it was meant for saw or heard this.]'
# On a companion's answer to a line that was for them alone.
REPLY_TAG = '[Private: only the user heard this.]'
# In a companion's scene so far, in place of a line that was for someone else alone, and of that one's answer:
# they are told that something passed, never what.
UNHEARD = '[The user says or shows something to {who}, for {who} alone. You did not see or hear what it was.]'
UNHEARD_REPLY = '[{name} answers the user too quietly for you to hear.]'
# In a companion's own notes, when the user's latest line was for them alone.
OWN = 'The user meant that for you alone. Nobody else here caught it. Keep your answer just as quiet.'


def moment(text: str) -> re.Match | None:
    """The words that make a line of the user's private, or None: said in the open, or out of the story."""
    if not ACTIVE or in_character.out_of_character(text) or OPEN.search(text):
        return None
    return PRIVATE.search(text)


def word(text: str, exact: bool) -> re.Pattern:
    return re.compile(rf'(?<![\w-]){re.escape(text)}(?![\w-])', 0 if exact else re.IGNORECASE)


def role_words(role: str) -> list[str]:
    last = role.split()[-1] if role.split() else ''
    return [found for found in (role, last, *ALSO.get(last.lower(), ())) if found and found.lower() != 'regular']


def cast(companions: list[dict], people: list[dict]) -> list[dict]:
    """Everyone in the scene a line could be for, with the words it could call them by: a name is read as a name
    is written, a job in any case."""
    found = [{'kind': 'companion', 'id': item['id'], 'full': item['full'], 'first': item['name'],
              'names': [item['full'], item['name']], 'roles': []} for item in companions]
    for item in companions:
        for person in story_plans.people(item['plan']) if item.get('plan') else ():
            first = their_people.first(person['name'])
            found.append({'kind': 'along', 'id': person['id'], 'full': person['name'], 'first': first,
                          'names': [person['name'], first], 'roles': [person['role']]})
    for person in people:
        sheet = person['sheet']
        roles = role_words(sheet.get('role') or '') + role_words(sheet.get('occupation') or '')
        found.append({'kind': 'person', 'id': sheet['key'], 'full': sheet['full'], 'first': sheet['name'],
                      'names': [sheet['full'], sheet['name']], 'roles': roles, 'person': person})
    return found


def distance(entry: dict, text: str, private: re.Match) -> int | None:
    """How far from the private words the line names them, or None when it does not."""
    patterns = [word(name, True) for name in entry['names'] if name] + \
               [word(role, False) for role in entry['roles'] if role]
    spans = [found.span() for pattern in patterns for found in pattern.finditer(text)]
    gaps = [0 if start < private.end() and end > private.start() else
            min(abs(start - private.end()), abs(private.start() - end)) for start, end in spans]
    return min(gaps) if gaps else None


def read(text: str, companions: list[dict], people: list[dict]) -> dict | None:
    """A private moment in the user's line: {'who': the one it was for, or None when the rules can't tell}. None
    when the line is said in the open."""
    private = moment(text)
    if private is None:
        return None
    everyone = cast(companions, people)
    named = sorted(((gap, index) for index, entry in enumerate(everyone)
                    if (gap := distance(entry, text, private)) is not None))
    if named and (len(named) == 1 or named[0][0] < named[1][0]):
        return {'who': everyone[named[0][1]]}
    return {'who': everyone[0] if len(everyone) == 1 and not named else None}


UNKNOWN = '?'


def kept(found: dict | None) -> str | None:
    """What a line keeps of its private moment (story_messages.private_for): who it was for as 'kind:id', UNKNOWN
    when the rules can't tell, None for a line said in the open."""
    if found is None:
        return None
    return f"{found['who']['kind']}:{found['who']['id']}" if found['who'] else UNKNOWN


def mark(connection, user: dict, view: dict) -> None:
    """The user's line was just saved or reworded: who it was for stays on it, since only now is it known who was
    there. What a companion is told of the scene later, in their chat, leaves out a line that was for someone else
    (companion/story_visits.py `lines_of`)."""
    found = None if user.get('hidden') else read(user['text'], view['companions'], view['people'])
    connection.execute('UPDATE story_messages SET private_for=? WHERE id=?', (kept(found), user['id']))


def for_companion(found: dict | None, item: dict) -> bool:
    who = found and found['who']
    return bool(who) and who['kind'] == 'companion' and who['id'] == item['id']


def only(found: dict | None, companions: list[dict]) -> list[dict] | None:
    """The companions who may answer a private line, or None when the usual rules decide: with someone it was
    for, only them."""
    if not found or not found['who']:
        return None
    return [item for item in companions if for_companion(found, item)]


# What the models are told -------------------------------------------------------------------------

def after(chat: list[dict], found: dict | None) -> list[dict]:
    """The narrator's conversation with the note after the user's latest line."""
    if not found or not chat or chat[-1]['role'] != 'user':
        return chat
    who = found['who']
    note = NOTE_SOMEONE if who is None else (NOTE_OWN if who['kind'] == 'companion' else NOTE).format(who=who['full'])
    return [*chat[:-1], {'role': 'user', 'content': f"{chat[-1]['content']}\n\n{note}"}]


def shown(who: dict | None, view: dict, seen) -> str | None:
    """Who a tag names: by full name for the narrator, and as the screen shows them (`seen`, the Story's own) for a
    companion standing in the scene."""
    if who is None:
        return None
    if not seen:
        return who['full']
    # Someone the user has not met has no name yet: "the server".
    return who['first'] if who['kind'] != 'person' or who['id'] in view['known'] else seen(who['person'], view)


def tags(rows: list[dict], view: dict, seen=None, skip: str | None = None) -> dict[str, str]:
    """{line id: its tag} for the private lines since the story came to this place, and a companion's answers to
    one that was theirs. `skip` is the line the narrator's note already covers."""
    start = max((index for index, row in enumerate(rows) if row['role'] == 'scene'), default=-1)
    found, theirs = {}, set()
    for row in rows[start + 1:]:
        if row['role'] == 'user' and not row.get('hidden'):
            private = read(row['text'], view['companions'], view['people'])
            if private is None:
                continue
            who = shown(private['who'], view, seen)
            found[row['id']] = TAG.format(who=who) if who else TAG_SOMEONE
            if private['who'] and private['who']['kind'] == 'companion':
                theirs.add((row['id'], private['who']['id']))
        elif row['role'] == 'companion' and (row.get('reply_to'), row.get('speaker')) in theirs:
            found[row['id']] = REPLY_TAG
    found.pop(skip, None)
    return found


def unheard(rows: list[dict], view: dict, item: dict, seen=None) -> dict[str, str]:
    """{line id: what stands in its place} in one companion's scene so far: a line of the user's that was for someone
    else alone, and a companion's answer to one that was theirs. A tag on the line was not enough: the words were
    still in the prompt, and asked about it directly a companion gave them away (A/B 2026-11-27: 12 of 34 with the
    tag, Claude Haiku among them). Who a line was for is read from the line (`mark`), so it holds after the story
    moves on; one from before lines kept that is read as the tags are. A line the rules can't place stays, tagged,
    since the one it was for may be this companion."""
    start = max((index for index, row in enumerate(rows) if row['role'] == 'scene'), default=-1)
    own, found, theirs = kept({'who': {'kind': 'companion', 'id': item['id']}}), {}, set()
    for index, row in enumerate(rows):
        if row['role'] == 'user':
            for_, who = meant(row, view, index > start)
            if for_ and for_ not in (own, UNKNOWN):
                found[row['id']] = UNHEARD.format(who=shown(who, view, seen) or 'someone else')
                theirs.add((row['id'], for_.partition(':')[2]))
        elif row['role'] == 'companion' and (row.get('reply_to'), row.get('speaker')) in theirs:
            found[row['id']] = UNHEARD_REPLY.format(name=row['name'])
    return found


def meant(row: dict, view: dict, here: bool) -> tuple[str | None, dict | None]:
    """Who a line of the user's was for, as the line keeps it, and that one as the scene has them when they are in
    it still. `here`: the line was said at this place, so one saved before lines kept it can be read now."""
    if row.get('hidden'):
        return None, None
    private = read(row['text'], view['companions'], view['people'])
    for_ = row.get('private_for') or (kept(private) if here else None)
    return for_, private['who'] if private and for_ and kept(private) == for_ else None


def tagged(text: str, row: dict, found: dict[str, str] | None) -> str:
    tag = (found or {}).get(row['id'])
    return f'{text}\n{tag}' if tag else text


def own_lines(rows: list[dict], view: dict, item: dict) -> list[tuple[str, str]]:
    """A companion's own note when the user's latest line was for them alone."""
    latest = next((row for row in reversed(rows) if row['role'] == 'user'), None)
    if latest is None or latest.get('hidden'):
        return []
    found = read(latest['text'], view['companions'], view['people'])
    return [('story:private', OWN)] if for_companion(found, item) else []


# Who hears it -------------------------------------------------------------------------------------

def said(connection, row: dict) -> str | None:
    """The user's line a finished line belongs to: its own text, or the one a companion's line answers."""
    if row['role'] == 'user':
        return None if row.get('hidden') else row['text']
    asked = optional(connection, "SELECT text, hidden FROM story_messages WHERE id=? AND role='user'",
                     (row.get('reply_to'),)) if row.get('reply_to') else None
    return asked['text'] if asked and not asked['hidden'] else None


def hearers(connection, row: dict, view: dict) -> list[str] | None:
    """The ledger keys of who hears a finished line, or None for everyone in the scene, as usual. A private line of
    the user's is heard by the one it was for (nobody the ledgers know, when that is a townsperson or can't be
    told); a companion's answer to one that was for them is heard by the user alone."""
    text = said(connection, row)
    found = read(text, view['companions'], view['people']) if text else None
    if found is None:
        return None
    who = found['who']
    if row['role'] != 'user':
        return [] if who and who['kind'] == 'companion' and who['id'] == row.get('speaker') else None
    if who and who['kind'] == 'companion':
        return [secrets.companion_key(who['id'])]
    return [secrets.circle_key(connection, who['id'])] if who and who['kind'] == 'along' else []
