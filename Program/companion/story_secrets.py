"""Secrets and news in a Story scene (1.5, docs/story.md): everyone in the scene hears what is said there.

The group chat's rules (companion/secrets.py, companion/news.py), for a scene in person. Rules only, no model call
of its own. Who is "there" is everyone in the scene the two ledgers know: the companions in it, and the people a
plan under way is with (companion/story_plans.py). Townsfolk the narrator voices are in neither ledger.

- With someone else there, a companion's own notes say what they know and who there must not find out, and what
  news they heard that someone there hasn't (the group chat's lines, "here" for "in this group").
- A companion's line is checked before it is saved, as a group reply is: a line that gives away a secret someone
  there must not find out is written once more with a private reminder. If that still gives it away, it stays as a
  slip only at the "soap opera" drama setting (then a note says so); otherwise they think better of it, and the line
  says only that.
- A finished line, the user's or a companion's, is witnessed: everyone there learns any secret it gives away and
  hears any news it tells, from whoever said it, as in a group. Only while Story scenes count
  (Settings > Realism, companion/story_visits.py); the check above runs either way. A line out of character, or the
  app's own hidden line, is not said in the scene, and the narrator holds no secrets, so its lines are not read.
- Telling the whole reply again takes back what its lines let people learn.
"""
import hashlib

from companion import in_character, news, secrets, story_plans, story_visits
from companion.database import encode
from companion.life import pronouns as words

ACTIVE = True
WHERE, WHAT = 'here', 'turn'
# A companion's line in place of one that would still have given a secret away, one of these by the scene's line so
# a second time in a scene reads differently (Iris).
HELD = ('{name} starts to say something, then thinks better of it.',
        '{name} opens {their} mouth, then closes it again.',
        '{name} hesitates, and lets it go.')
# Under a slip that stays (at the soap opera drama setting).
SLIPPED = '{name} let a secret slip. Everyone here knows it now.'


def held(item: dict, seed: str) -> str:
    """What they do instead of saying it, picked steadily by the line they answer."""
    text = HELD[int(hashlib.sha1(f"{seed}:{item['id']}".encode()).hexdigest(), 16) % len(HELD)]
    return text.format(name=item['name'], **words.person(item['pronouns']))


def key(item: dict) -> str:
    return secrets.companion_key(item['id'])


def there(connection, view: dict) -> dict[str, str]:
    """{person key: name as the scene says it} for everyone in the scene the ledgers know."""
    found = {}
    for item in view['companions']:
        found[key(item)] = item['name']
        for person in story_plans.people(item['plan']) if item.get('plan') else ():
            found.setdefault(secrets.circle_key(connection, person['id']), secrets.first_name(person['name']))
    return found


def lines(connection, view: dict, item: dict, now) -> list[tuple[str, str]]:
    """The speaker's own notes on secrets and news, while someone else is in the scene with them."""
    if not ACTIVE:
        return []
    names = there(connection, view)
    names.pop(key(item), None)
    if not names:
        return []
    others = list(names)
    return secrets.group_lines(connection, key(item), others, names, now, where=WHERE) + \
        news.group_lines(connection, key(item), others, names, now)


def watched(connection, view: dict, item: dict) -> list[dict]:
    """Secrets the speaker knows that someone in the scene must not find out: their line gets checked."""
    return secrets.watched(connection, key(item), list(there(connection, view))) if ACTIVE else []


def given(watch: list[dict], text: str, item: dict) -> list[dict]:
    """The watched secrets a line gives away, by the group chat's rules."""
    return [secret for secret in watch if secrets.hits(secret, text, key(item))]


def reminder(connection, view: dict, item: dict, found: list[dict]) -> str:
    names = there(connection, view)
    return secrets.reminder(found, item['name'], list(names), connection, names, what=WHAT)


def noted(packet: dict, note: str) -> dict:
    """The companion's request with a private note right before their turn."""
    notes = packet['messages'][-1]['content'].removesuffix(packet['turn'])
    return {**packet, 'messages': [*packet['messages'][:-1],
                                   {'role': 'user', 'content': f"{notes}{note}\n\n{packet['turn']}"}]}


def sync(connection, view: dict, now) -> None:
    """Secrets from storylines and sheets registered before anyone in the scene speaks."""
    if ACTIVE and view['companions']:
        secrets.sync(connection, now)


def heard(connection, row: dict, view: dict) -> list[str]:
    """A finished line said in the scene: everyone there learns what it gives away. Returns the ids of secrets it
    gave away to someone they were kept from."""
    if not ACTIVE or row['status'] != 'complete' or row.get('hidden') or not view['companions'] or \
            row['role'] not in ('user', 'companion') or not story_visits.counts(connection):
        return []
    if row['role'] == 'user' and in_character.out_of_character(row['text']):
        return []
    message = {'id': row['id'], 'text': row['text'], 'created_at': row['created_at'],
               'author': 'user' if row['role'] == 'user' else secrets.companion_key(row['speaker']),
               'present': encode(list(there(connection, view)))}
    news.witness(connection, message)
    return secrets.witness(connection, message)


def unsay(connection, message_ids: list[str], timestamp: str) -> None:
    """Lines told again are taken back: nobody learned anything from them."""
    if not message_ids:
        return
    marks = ', '.join('?' for _ in message_ids)
    connection.execute(f'UPDATE knowledge_holders SET ended_at=? WHERE ended_at IS NULL AND message_id IN ({marks})',
                       (timestamp, *message_ids))
    connection.execute(f'DELETE FROM news_holders WHERE message_id IN ({marks})', tuple(message_ids))
