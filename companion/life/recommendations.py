"""The companion acts on the user's recommendations (realism: "I started the show you told me about").

A recommendation in the user's own words ("you should watch Severance", "try the pho place on
Charles St") is caught by fixed rules when the message is saved. The agenda then gives it a few of
the companion's free evenings over the next days, one session a day: episodes of a show, chapters
of a book, an album, a game, or one outing to the place. What they thought is decided before any
model is involved, seeded by the recommendation and leaning on their interests and stated tastes.

The title is the user's text and the only fact about it the companion has: the chat context tells
the companion not to invent plot, people or details. Sessions become part of the companion's account
like any other agenda entry, through the capped, reviewed events; the context shows the progress
that is committed, and a finished one can open a conversation (companion/life/openers.py).
"""
import random
import re
from dataclasses import dataclass
from datetime import timedelta

from companion.clock import parse, stamp
from companion.database import decode, identifier, many, one, optional
from companion.errors import require

SETTLE = timedelta(hours=12)
SESSION_SHARE = 0.6
SLOT_KINDS = {'leisure', 'social', 'rest'}
VERDICTS = (('loved it', 3), ('liked it', 4), ('thought it was fine', 2), ('was not really into it', 1))
TITLE = r"([^,.!?\n;]{2,60})"


@dataclass(frozen=True)
class Kind:
    key: str
    sessions: tuple[int, int]
    start: str
    more: str
    finish: str
    caption: str


KINDS = {
    'show': Kind('show', (2, 4), '{name} started watching {title} at home.', '{name} watched more of {title}.',
                 '{name} finished {title}.', 'Recommended to me. Watching.'),
    'movie': Kind('movie', (1, 1), '', '', '{name} watched {title} at home.', 'Movie night, recommended.'),
    'book': Kind('book', (3, 5), '{name} started reading {title}.', '{name} read more of {title}.',
                 '{name} finished reading {title}.', 'Current read, on a friend\'s advice.'),
    'music': Kind('music', (1, 2), '{name} listened to {title} for the first time.',
                  '{name} put {title} on again.', '{name} listened to {title} again, start to finish.',
                  'On repeat (someone told me to).'),
    'game': Kind('game', (2, 4), '{name} started playing {title}.', '{name} played more of {title}.',
                 '{name} played {title} to the end.', 'One more round.'),
    'outing': Kind('outing', (1, 1), '', '', '{name} went to {title}{together}, as recommended.',
                   'Tried the place I was told about.'),
}
VERBS = {
    'watch': 'show', 'see': 'show', 'binge': 'show', 'read': 'book', 'listen to': 'music', 'play': 'game',
    'try': 'outing', 'visit': 'outing', 'go to': 'outing', 'check out': 'outing',
}
MOVIE = re.compile(r'\b(?:movie|film)\b', re.IGNORECASE)
SHOW = re.compile(r'\b(?:show|series|season|anime|documentary)\b', re.IGNORECASE)
ASK = re.compile(r"\byou (?:should|have to|gotta|need to|must|ought to|really should) "
                 r"(watch|see|binge|read|listen to|play|try|visit|go to|check out) " + TITLE, re.IGNORECASE)
NOT_TITLES = {'it', 'that', 'this', 'them', 'me', 'out', 'him', 'her', 'a doctor', 'the doctor', 'some sleep',
              'to bed', 'bed', 'yourself', 'harder', 'again'}
TRAILING = re.compile(r'\s+(?:sometime|some time|someday|one day|soon|next|too|first|already|asap|tonight|'
                      r'this weekend|when you can|if you can|honestly|though|lol|haha|btw)\b.*$', re.IGNORECASE)


def find(text: str) -> list[tuple[str, str]]:
    """(kind, title) for each recommendation in a user message. Hypotheticals and questions are skipped."""
    from companion.memory.extraction import HYPOTHETICAL, QUOTED, SENTENCE
    found = []
    for sentence in SENTENCE.findall(QUOTED.sub(' ', text)):
        if sentence.strip().endswith('?') or HYPOTHETICAL.search(sentence):
            continue
        for match in ASK.finditer(sentence):
            verb, title = match.group(1).lower(), TRAILING.sub('', match.group(2)).strip(' ,"\'“”')
            title = re.sub(r'^(?:watching|reading|playing|listening to|trying|visiting)\s+', '', title, flags=re.I)
            if len(title) < 2 or title.lower() in NOT_TITLES or title.lower().startswith(('me ', 'my ', 'your ')):
                continue
            kind = VERBS[verb]
            if kind == 'show':
                kind = 'movie' if MOVIE.search(title) else 'show' if SHOW.search(title) or verb == 'binge' else 'show'
            found.append((kind, title))
    return found


def note(connection, message: dict, timestamp: str) -> list[dict]:
    """Record the recommendations in a user message; their sessions are scheduled from tomorrow-ish."""
    added = []
    for index, (kind, title) in enumerate(find(message['text'])):
        if optional(connection, "SELECT id FROM recommendations WHERE timeline_id=? AND lower(title)=lower(?) "
                    "AND status!='dropped'", (message['timeline_id'], title)):
            continue
        rng = random.Random(f"recommendation:{message['id']}:{index}")
        rec_id = identifier()
        connection.execute(
            'INSERT INTO recommendations (id, timeline_id, message_id, kind, title, sessions, status, starts_after, '
            "created_at) VALUES (?, ?, ?, ?, ?, ?, 'waiting', ?, ?)",
            (rec_id, message['timeline_id'], message['id'], kind, title, rng.randint(*KINDS[kind].sessions),
             stamp(parse(timestamp) + SETTLE), timestamp))
        added.append(rec_id)
    if added:
        rebuild_upcoming(connection, message['timeline_id'], timestamp)
    return added


def rebuild_upcoming(connection, timeline_id, timestamp):
    connection.execute("DELETE FROM life_agenda WHERE timeline_id=? AND subject='companion' AND status='upcoming' "
                       'AND starts_at>?', (timeline_id, timestamp))
    connection.execute("UPDATE agenda_cursors SET through=MIN(through, ?) WHERE timeline_id=? AND subject='companion'",
                       (timestamp, timeline_id))


def verdict(rec: dict, definition: dict) -> str:
    """What they thought, seeded by the recommendation; their interests and stated likes tip it warmer."""
    words = {word.casefold() for phrase in [*definition.get('interests', ()),
                                            *(definition.get('self_tastes') or {}).get('likes', ())]
             for word in phrase.split() if len(word) > 3}
    title = rec['title'].casefold()
    warm = any(word in title for word in words)
    options = [(text, weight + (2 if warm and index < 2 else 0)) for index, (text, weight) in enumerate(VERDICTS)]
    rng = random.Random(f"verdict:{rec['id']}")
    return rng.choices([text for text, _weight in options], [weight for _text, weight in options])[0]


def active(connection, timeline_id) -> list[dict]:
    return many(connection, "SELECT * FROM recommendations WHERE timeline_id=? AND status!='dropped' "
                'ORDER BY created_at', (timeline_id,))


def scheduled(connection, timeline_id, rec_id) -> list[dict]:
    rows = many(connection, "SELECT local_date, entry FROM life_agenda WHERE timeline_id=? AND subject='companion' "
                "AND json_extract(entry, '$.recommendation.id')=? ORDER BY starts_at", (timeline_id, rec_id))
    return [{'local_date': row['local_date'], **decode(row['entry'])['recommendation']} for row in rows]


def session_for(connection, timeline_id, slot, block, definition, seed, company=()) -> dict | None:
    """The next session of the oldest waiting recommendation, if this free slot gets one (at most one a day)."""
    if block['kind'] not in SLOT_KINDS or block.get('sick_day') or block.get('holiday'):
        return None
    for rec in active(connection, timeline_id):
        if slot.starts_at < parse(rec['starts_after']):
            continue
        done = scheduled(connection, timeline_id, rec['id'])
        if len(done) >= rec['sessions'] or any(item['local_date'] == slot.local_date.isoformat() for item in done):
            continue
        if random.Random(f'{seed}:recommendation').random() >= SESSION_SHARE:
            return None
        return compose(rec, len(done) + 1, definition, seed, company)
    return None


def compose(rec: dict, number: int, definition: dict, seed: str, company=()) -> dict:
    kind, rng = KINDS[rec['kind']], random.Random(f'{seed}:recommendation:text')
    last = number >= rec['sessions']
    friend = company[0] if company and rec['kind'] == 'outing' and rng.random() < 0.5 else None
    template = kind.finish if last else kind.start if number == 1 else kind.more
    summary = template.format(name=definition['name'], title=rec['title'],
                              together=f" with {friend['name']}" if friend else '')
    thought = verdict(rec, definition) if last else None
    if thought:
        summary += f" {definition['name']} {thought}."
    return {'summary': summary, 'post': kind.caption, 'mood': 'unimpressed' if thought and 'not' in thought
            else 'content', 'activity': 'recommendation', 'place': {'name': rec['title'], 'kind': 'recommended',
                                                                 'neighborhood': ''} if rec['kind'] == 'outing'
            else None, 'with': friend, 'recommendation': {'id': rec['id'], 'title': rec['title'], 'kind': rec['kind'],
                                                         'session': number, 'of': rec['sessions'],
                                                         'verdict': thought},
            'composer_version': 'recommendation-1'}


def progress(connection, timeline_id) -> list[dict]:
    """Each recommendation with what the companion's committed account says about it so far."""
    result = []
    for rec in active(connection, timeline_id):
        rows = many(connection, "SELECT details, starts_at FROM life_events WHERE timeline_id=? AND status='committed' "
                    "AND json_extract(details, '$.recommendation.id')=? ORDER BY starts_at", (timeline_id, rec['id']))
        sessions = [decode(row['details'])['recommendation'] for row in rows]
        finished = next((item for item in sessions if item.get('verdict')), None)
        result.append({**{key: rec[key] for key in ('id', 'kind', 'title', 'created_at', 'message_id')},
                       'state': 'finished' if finished else 'started' if sessions else 'waiting',
                       'sessions_done': len(sessions), 'verdict': finished['verdict'] if finished else None,
                       'finished_at': rows[-1]['starts_at'] if finished else None})
    return result


def context_text(item: dict) -> str:
    noun = {'show': 'show', 'movie': 'movie', 'book': 'book', 'music': 'music', 'game': 'game',
            'outing': 'place'}[item['kind']]
    if item['state'] == 'finished':
        return f"- {item['title']} ({noun}): you finished it. Your verdict: {item['verdict']}."
    if item['state'] == 'started':
        return f"- {item['title']} ({noun}): you have started it but not finished."
    return f"- {item['title']} ({noun}): you have not started it yet but mean to soon."


def listing(database) -> list[dict]:
    from companion.characters import require_current
    with database.connect() as connection:
        return progress(connection, require_current(connection)['active_timeline_id'])


def drop(database, rec_id) -> list[dict]:
    """The user takes a recommendation back: its upcoming sessions go; what happened stays."""
    from companion.characters import require_current
    with database.connect(write=True) as connection:
        rec = one(connection, 'SELECT * FROM recommendations WHERE id=?', (rec_id,))
        require(rec['status'] != 'dropped', 'This was already taken back.', 409)
        connection.execute("UPDATE recommendations SET status='dropped' WHERE id=?", (rec_id,))
        connection.execute("DELETE FROM life_agenda WHERE timeline_id=? AND subject='companion' AND status='upcoming' "
                           "AND json_extract(entry, '$.recommendation.id')=?", (rec['timeline_id'], rec_id))
        rebuild_upcoming(connection, rec['timeline_id'], database.now())
        return progress(connection, require_current(connection)['active_timeline_id'])


def finished_recently(connection, timeline_id, since) -> list[dict]:
    """Committed final sessions since an instant, for a first message about them."""
    return many(connection, "SELECT * FROM life_events WHERE timeline_id=? AND status='committed' AND decided_at>? "
                "AND json_extract(details, '$.recommendation.verdict') IS NOT NULL", (timeline_id, since))
