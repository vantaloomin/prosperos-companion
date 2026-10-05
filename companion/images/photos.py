"""Photos in chat: asked what they are up to, the companion can answer with a photo of the moment.

The app decides when, not the model: a fixed set of phrasings asks for one, the way lookups are
chosen (X3). The photo shows the companion's current routine slot composed exactly as the
simulation will compose it (the same agenda entry, plan and seed), so the reply, the photo and the
event that slot becomes all tell one account. The image is made on a feed post keyed to that
future event (`feed.PHOTO_KEY`); when the simulation writes the event it joins that post, so the
feed shows the same picture and the event exists once. Until then the post has no event and stays
out of the feed.

Every photo goes through the same classification and routing as any other image (F6): NSFW only to
a local backend, the prohibited tier nowhere, and anything uncertain counts as NSFW. A request with
nowhere to go sends no photo, and nothing here ever holds up the reply.
"""
import re

from companion import events
from companion.characters import require_current
from companion.clock import parse, zone
from companion.database import many, one, optional, settings
from companion.images import jobs, prompts
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
# Asking about another time is not asking what they are doing now.
ELSEWHEN = re.compile(r"\b(?:tomorrow|tonight|later|yesterday|last (?:night|week|weekend)|earlier|next|this "
                      r"(?:weekend|evening|afternoon)|on (?:mon|tues|wednes|thurs|fri|satur|sun)day|been up to)\b",
                      re.IGNORECASE)
SHOWN = ('queued', 'running', 'completed')
RESTARTED = ('none', 'cancelled', 'interrupted')


def asks_for_photo(text: str) -> bool:
    return bool(ASKS.search(text or '')) and not ELSEWHEN.search(text or '')


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
        """The photo this reply sends, recorded against the reply, or None. Never raises."""
        if not asks_for_photo(user['text']):
            return None
        try:
            return self.send(attempt_id)
        except Exception:  # noqa: BLE001 - the reply goes ahead without a photo.
            return None

    def send(self, attempt_id) -> dict | None:
        now = self.database.clock.now()
        with self.database.connect() as connection:
            if not jobs.image_settings(connection)['chat_photos'] or settings(connection)['paused_at']:
                return None
            moment = self.moment(connection, require_current(connection), now)
            inputs = moment and prompts.build_moment(connection, moment, jobs.image_settings(connection))
        if moment is None:
            return None
        post = self.post_for(moment)
        if post['status'] == 'removed':
            return None
        if post['image_status'] in RESTARTED:
            if not jobs.routable(self.database, inputs):
                return None
            jobs.enqueue(self.database, post['id'], 'manual', inputs=inputs)
            self.images.wake()
        elif post['image_status'] not in SHOWN:
            return None  # It failed for this moment already; the feed post offers a retry once it shows.
        with self.database.connect(write=True) as connection:
            connection.execute('INSERT OR REPLACE INTO chat_photos (message_id, post_id, event_key, summary, '
                               'created_at) VALUES (?, ?, ?, ?, ?)',
                               (attempt_id, post['id'], moment['event_key'], moment['summary'], self.database.now()))
        return {'post_id': post['id'], 'text': moment_text(moment)}

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
                'label': shown['block']['label'], 'until': until, 'timeline_id': timeline_id,
                'ends_at': shown['ends_at']}

    def post_for(self, moment) -> dict:
        """The post the slot's event will join, made once."""
        with self.database.connect(write=True) as connection:
            post_id = feed.create(connection, moment['timeline_id'], 'event', feed.PHOTO_KEY + moment['event_key'],
                                  [], moment['ends_at'], self.database.now())
            return one(connection, 'SELECT * FROM feed_posts WHERE id=?', (post_id,))


def moment_text(moment) -> str:
    return f"- {moment['summary']} ({moment['label'].lower()}, until {moment['until']} your time)"


def view(row) -> dict:
    return {'message_id': row['message_id'], 'post_id': row['post_id'], 'summary': row['summary'],
            'status': row['image_status'], 'job_id': row['image_job_id'], 'ref': row['image_ref'],
            'error': row['image_error'], 'in_feed': row['in_feed'] > 0}


SELECT = ('SELECT photo.message_id, photo.post_id, photo.summary, post.image_status, post.image_job_id, '
          'post.image_ref, post.image_error, (SELECT COUNT(*) FROM feed_post_events link '
          'WHERE link.post_id=post.id) AS in_feed FROM chat_photos photo JOIN feed_posts post ON post.id=photo.post_id '
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
