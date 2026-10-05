"""Pictures in chat: asked what they are up to, or for a selfie or a meme, the companion can send one.

The app decides when, not the model: fixed phrasings ask for a picture, the way lookups are chosen
(X3). A photo, selfie or view shows the companion's current routine slot composed exactly as the
simulation will compose it (the same agenda entry, plan and seed), so the reply, the picture and the
event that slot becomes all tell one account. It is made on a feed post keyed to that future event
(`feed.PHOTO_KEY`); when the simulation writes the event it joins that post, so the feed shows the
same picture and the event exists once. Until then the post has no event and stays out of the feed.
A meme is a joke, not an event: its captions come from templates (`memes.py`) and its picture is
made on a post of its own that never reaches the feed.

Every picture goes through the same classification and routing as any other image (F6): NSFW only
to a local backend, the prohibited tier nowhere, and anything uncertain counts as NSFW. A request
with nowhere to go sends nothing, and nothing here ever holds up the reply.
"""
import re

from companion import events
from companion.characters import require_current
from companion.clock import parse, zone
from companion.database import decode, many, one, optional, settings
from companion.images import jobs, memes, prompts
from companion.life import agenda, feed, routine, simulation
from companion.life.synthesis import PROMPT_VERSION as WORDING_VERSION
from companion.text_models import config_for
from companion.workspace import overlapping_pause

ASKS = re.compile(
    r"\b(?:what(?:'?s| are| r|'re|cha|chu)? ?(?:you|u|ya)? ?(?:up to|doing|doin'?)"
    r"|wyd|where (?:are|r) (?:you|u) (?:right now|rn|at)\b"
    r"|(?:send|show)(?: me)?(?: a| an| another| one)? ?(?:quick )?(?:pic|picture|photo|selfie|snap)s?"
    r"|show me (?:what|where) (?:you(?:'re| are)|u r)"
    r"|(?:pic|picture|photo|selfie)s? (?:or it didn'?t happen|of (?:what|where) (?:you|u)))",
    re.IGNORECASE)
SELFIE = re.compile(r"\bselfies?\b|\b(?:pic|picture|photo)s? of (?:you|u|yourself|your face)\b"
                    r"|\bsee (?:your face|you)\b", re.IGNORECASE)
VIEW = re.compile(r"\b(?:pic|picture|photo|show me)\b.{0,20}\b(?:the view|your view|what you(?:'re| are)? see"
                  r"(?:ing)?|where you are|around you)\b", re.IGNORECASE)
MEME = re.compile(r"\bmemes?\b|\bmake me (?:laugh|smile)\b|\bcheer me up\b|\bi need a laugh\b",
                  re.IGNORECASE)
# Asking about another time is not asking what they are doing now.
ELSEWHEN = re.compile(r"\b(?:tomorrow|tonight|later|yesterday|last (?:night|week|weekend)|earlier|next|this "
                      r"(?:weekend|evening|afternoon)|on (?:mon|tues|wednes|thurs|fri|satur|sun)day|been up to)\b",
                      re.IGNORECASE)


def asked_kind(text: str) -> str | None:
    """Which picture a message asks for: 'meme', 'selfie', 'view', 'moment', or None."""
    text = text or ''
    if MEME.search(text):
        return 'meme'
    if ELSEWHEN.search(text):
        return None
    if SELFIE.search(text):
        return 'selfie'
    if VIEW.search(text):
        return 'view'
    return 'moment' if ASKS.search(text) else None


def asks_for_photo(text: str) -> bool:
    return asked_kind(text) is not None


def wording(connection, composed, prepared) -> dict:
    """The words the simulation will use for this slot: wording prepared ahead by the current life
    model when there is some, else the template. The photo never asks a model to phrase anything."""
    config = config_for(connection, 'life')
    life = simulation.life_settings(connection)
    if prepared and config and life['phrase_with_model'] and (prepared.get('model'), prepared.get('base_url'),
                                                              prepared.get('prompt_version')) == \
            (config['model'], config['base_url'], WORDING_VERSION):
        return {'summary': prepared['summary'], 'post': prepared['post']}
    return {'summary': composed['summary'], 'post': composed['post']}


def place_text(place) -> str:
    return place.get('name', '') if isinstance(place, dict) else ''


class ChatPhotos:
    def __init__(self, database, images, life):
        self.database = database
        self.images = images
        self.life = life

    def for_message(self, user, attempt_id) -> dict | None:
        """The picture this reply sends, recorded against the reply, or None. Never raises."""
        kind = asked_kind(user['text'])
        if kind is None:
            return None
        try:
            return self.send(kind, attempt_id)
        except Exception:  # noqa: BLE001 - the reply goes ahead without a picture.
            return None

    def send(self, kind, attempt_id) -> dict | None:
        now = self.database.clock.now()
        with self.database.connect() as connection:
            if not jobs.image_settings(connection)['chat_photos'] or settings(connection)['paused_at']:
                return None
            companion = require_current(connection)
            moment = self.moment(connection, companion, now)
            local_hour = now.astimezone(zone(companion['version']['timezone'])).hour
            recent = recent_memes(connection, companion['active_timeline_id'])
        if kind == 'meme':
            return self.send_meme(attempt_id, moment, memes.choose(moment, local_hour, attempt_id, recent),
                                  companion['active_timeline_id'])
        return self.send_moment(attempt_id, moment, kind) if moment else None

    def send_moment(self, attempt_id, moment, kind) -> dict | None:
        with self.database.connect() as connection:
            inputs = prompts.build_moment(connection, moment, jobs.image_settings(connection), kind)
        post = self.post_for(moment['timeline_id'], feed.PHOTO_KEY + moment['event_key'], moment['ends_at'])
        if post['status'] == 'removed':
            return None
        job_id = self.shown_job(post['id'], kind) or self.make(post['id'], inputs)
        if job_id is None:
            return None
        self.record(attempt_id, post['id'], job_id, kind, moment['event_key'], moment['summary'])
        return {'post_id': post['id'], 'text': moment_text(moment, kind)}

    def send_meme(self, attempt_id, moment, meme, timeline_id) -> dict | None:
        with self.database.connect() as connection:
            inputs = prompts.build_meme(connection, meme, jobs.image_settings(connection))
        post = self.post_for(timeline_id, f'meme:{attempt_id}', self.database.now())
        job_id = self.make(post['id'], inputs)
        if job_id is None:
            return None
        summary = meme['subject'] or f"you, looking {meme['expression']}"
        self.record(attempt_id, post['id'], job_id, 'meme', '', summary, meme['top'], meme['bottom'])
        return {'post_id': post['id'], 'text': f"- A meme you made to share (a joke, not something that happened): "
                                               f"a picture of {summary}, captioned «{meme['top']}» / "
                                               f"«{meme['bottom']}»."}

    def shown_job(self, post_id, kind) -> str | None:
        """A picture of this moment already made or on its way that answers the ask: any for a plain
        photo, the same framing for a selfie or a view. Asking again never makes another."""
        with self.database.connect() as connection:
            for job in many(connection, "SELECT id, inputs FROM image_jobs WHERE post_id=? AND status IN "
                            "('queued', 'running', 'completed') ORDER BY created_at DESC, rowid DESC", (post_id,)):
                if kind == 'moment' or decode(job['inputs']).get('framing', 'moment') == kind:
                    return job['id']
        return None

    def make(self, post_id, inputs) -> str | None:
        """Queue the picture if some backend may take it (F6); None when nothing may."""
        if not jobs.routable(self.database, inputs):
            return None
        job = jobs.enqueue(self.database, post_id, 'manual', inputs=inputs)
        self.images.wake()
        return job['id']

    def record(self, attempt_id, post_id, job_id, kind, event_key, summary, top='', bottom=''):
        with self.database.connect(write=True) as connection:
            connection.execute('INSERT OR REPLACE INTO chat_photos (message_id, post_id, job_id, kind, event_key, '
                               'summary, top_text, bottom_text, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                               (attempt_id, post_id, job_id, kind, event_key, summary, top, bottom,
                                self.database.now()))

    def moment(self, connection, companion, now) -> dict | None:
        """What the companion is doing right now, if anything worth a photo: the current slot,
        composed as the simulation will compose it."""
        version, timeline_id = companion['version'], companion['active_timeline_id']
        schedule, _default = routine.blocks(version['definition'])
        slot, _next = routine.current_and_next(schedule, version['timezone'], now)
        if slot is None or slot.block.kind in routine.RESTING or \
                overlapping_pause(connection, slot.view()['starts_at'], slot.view()['ends_at']):
            return None
        key = simulation.event_key(timeline_id, slot.key)
        if optional(connection, 'SELECT id FROM life_events WHERE idempotency_key=?', (key,)):
            return None  # Already told as an event; its feed post carries any picture.
        precomputed = agenda.companion_entry(connection, timeline_id, slot.key, version['id'])
        recent = events.committed(connection, timeline_id)[-5:]
        composed, shown, prepared = self.life.compose_slot(
            slot.view(), version, key, simulation.plan_for(connection, timeline_id, slot.key), precomputed, recent)
        if composed is None:
            return None
        words = wording(connection, composed, prepared)
        until = parse(shown['ends_at']).astimezone(zone(version['timezone'])).strftime('%H:%M')
        return {'event_key': key, 'summary': words['summary'], 'caption': words['post'],
                'mood': composed.get('mood', ''), 'place': place_text(composed.get('place')),
                'label': shown['block']['label'], 'kind': shown['block']['kind'], 'until': until,
                'rain': bool((composed.get('weather') or {}).get('rain')), 'timeline_id': timeline_id,
                'ends_at': shown['ends_at']}

    def post_for(self, timeline_id, key, occurs_at) -> dict:
        """The post a picture is made on, made once: for a moment, the one its event will join."""
        with self.database.connect(write=True) as connection:
            post_id = feed.create(connection, timeline_id, 'event', key, [], occurs_at, self.database.now())
            return one(connection, 'SELECT * FROM feed_posts WHERE id=?', (post_id,))


def recent_memes(connection, timeline_id, limit=6) -> list[str]:
    rows = many(connection, "SELECT photo.top_text FROM chat_photos photo JOIN messages message ON "
                "message.id=photo.message_id WHERE photo.kind='meme' AND message.timeline_id=? "
                'ORDER BY photo.created_at DESC LIMIT ?', (timeline_id, limit))
    return [row['top_text'] for row in rows]


LEADS = {'moment': 'A photo of what you are doing right now', 'selfie': 'A selfie you are taking right now',
         'view': 'A photo of what you can see right now'}


def moment_text(moment, kind='moment') -> str:
    return (f"- {LEADS[kind]} (from your day; still happening): {moment['summary']} "
            f"({moment['label'].lower()}, until {moment['until']} your time)")


def view(row) -> dict:
    done = row['job_status'] == 'completed' and row['output_file'] is not None
    return {'message_id': row['message_id'], 'post_id': row['post_id'], 'kind': row['kind'],
            'summary': row['summary'], 'top_text': row['top_text'], 'bottom_text': row['bottom_text'],
            'status': row['job_status'] or 'failed', 'job_id': row['job_id'], 'ref': row['job_id'] if done else None,
            'error': row['job_error'], 'in_feed': row['in_feed'] > 0}


SELECT = ('SELECT photo.*, job.status AS job_status, job.output_file, job.error AS job_error, '
          '(SELECT COUNT(*) FROM feed_post_events link WHERE link.post_id=post.id) AS in_feed '
          'FROM chat_photos photo JOIN feed_posts post ON post.id=photo.post_id '
          'LEFT JOIN image_jobs job ON job.id=photo.job_id '
          "WHERE post.status!='removed' AND photo.message_id IN ")


def for_messages(connection, message_ids) -> dict[str, dict]:
    found = {}
    ids = list(message_ids)
    for start in range(0, len(ids), 500):
        chunk = ids[start:start + 500]
        rows = many(connection, SELECT + f"({','.join('?' * len(chunk))})", tuple(chunk))
        found.update({row['message_id']: view(row) for row in rows})
    return found


def decorate(connection, messages: list[dict]) -> list[dict]:
    """Message views with the photo each reply sent, if any."""
    photos = for_messages(connection, [message['id'] for message in messages if message['role'] == 'companion'])
    return [{**message, 'photo': photos.get(message['id'])} for message in messages]


def get(database, message_id) -> dict | None:
    with database.connect() as connection:
        return for_messages(connection, [message_id]).get(message_id)
