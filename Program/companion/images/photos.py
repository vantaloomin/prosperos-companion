"""Pictures in chat: asked what they are up to, or for a selfie or a meme, the companion can send one.

The app decides when, not the model: fixed phrasings ask for a picture, the way lookups are chosen
(X3). A photo, selfie or view shows the companion's current routine slot composed exactly as the
simulation will compose it (the same agenda entry, plan and seed), so the reply, the picture and the
event that slot becomes all tell one account. It is made on a feed post keyed to that future event
(`feed.PHOTO_KEY`); when the simulation writes the event it joins that post, so the feed shows the
same picture and the event exists once. Until then the post has no event and stays out of the feed.
A meme is a joke, not an event: its captions come from templates (`memes.py`) and its picture is a
template on this computer (`meme_pictures.py`), a reaction GIF with the user's own GIPHY key (`gifs.py`),
or, now and then when an image model is set up, made on a post of its own that never reaches the feed.
How often memes come unasked follows Realism > Their days > "Memes and GIFs".

The companion also sends pictures nobody asked for, like a person would: now and then with a reply
(a seeded chance, a meme more likely when the user sounds bored or down), and, when they may text
first, a photo text of something they are out doing (`share`). Both go through the same rules and
are capped, and the first-message rules (`openers.held`) decide when a photo text may go out.

Every picture goes through the same classification and routing as any other image (F6): NSFW only
to a backend that accepts it, the prohibited tier nowhere, and anything uncertain counts as NSFW. A request
with nowhere to go sends nothing, and nothing here ever holds up the reply.
"""
import random
import re
from datetime import timedelta
from urllib.parse import quote

from companion import events
from companion.characters import current, require_current
from companion.clock import parse, stamp, zone
from companion.database import decode, encode, many, one, optional, settings
from companion.errors import DomainError, require
from companion.images import content, gifs, jobs, meme_pictures, memes, prompts
from companion.life import agenda, composer, families, feed, routine, simulation
from companion.life.openers import Trigger, held
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
MEME = re.compile(r"\bmemes?\b|\bgifs?\b|\bmake me (?:laugh|smile)\b|\bcheer me up\b|\bi need a laugh\b",
                  re.IGNORECASE)
# Asking about another time is not asking what they are doing now.
ELSEWHEN = re.compile(r"\b(?:tomorrow|tonight|later|yesterday|last (?:night|week|weekend)|earlier|next|this "
                      r"(?:weekend|evening|afternoon)|on (?:mon|tues|wednes|thurs|fri|satur|sun)day|been up to)\b",
                      re.IGNORECASE)
# Sounding bored or low makes an unasked meme likely.
DOWN = re.compile(r"\b(?:bored|boring|bad day|rough day|long day|ugh+|stress(?:ed|ful)|exhausted|tired|sad|meh|"
                  r"blah|sucks|miserable|fed up)\b", re.IGNORECASE)
# Off in most tests (tests/conftest.py), since the chance would add pictures to unrelated replies.
UNASKED = True
UNASKED_CHANCE = 0.15
UNASKED_MEME_CHANCE = 0.5
# Memes and GIFs (life_settings.memes_realism): never, now and then, true to life, often. Scales the chance
# above; at "often" any reply may come with one.
MEME_LEVELS = (0, 0.5, 1, 1.4)
OFTEN_CHANCE = 0.05
# With a GIPHY key, a meme is a reaction GIF this often; with an image model, its picture is made by the model
# this often. Otherwise it is a template on this computer.
GIF_SHARE = 1 / 3
MODEL_SHARE = 1 / 3
# Memes belong to cities of today and of the future, not to 1895 or Camelot.
MEME_ERAS = {'modern', 'future'}
# A meme never goes with words about anyone young or anything adult (content.py's lists).
NOT_FOR_MEMES = {'minor', 'sexual', 'nudity', 'sexual_violence', 'uncertain'}
UNASKED_SELFIE_SHARE = 1 / 3
UNASKED_DAILY = 3
UNASKED_GAP = timedelta(hours=2)
# Photo texts: only of something the companion is out doing, a seeded chance per moment, one a day.
SHARE_KINDS = {'social', 'leisure', 'errand'}
SHARE_CHANCE = 0.35
SHARE_SELFIE_SHARE = 0.4
SHARE_DAILY = 1


def asked_kind(text: str) -> str | None:
    """Which picture a message asks for: 'meme', 'selfie', 'view', 'moment', or None."""
    text = text or ''
    if MEME.search(text):
        return 'gif' if gifs.GIF_ASK.search(text) else 'meme'
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


def memes_level(connection) -> int:
    row = optional(connection, 'SELECT memes_realism FROM life_settings WHERE id=1')
    return row['memes_realism'] if row and row['memes_realism'] in range(4) else 2


def memes_fit(text: str) -> bool:
    return not content.matches(content.normalize(text or '')) & NOT_FOR_MEMES


def place_text(place) -> str:
    return place.get('name', '') if isinstance(place, dict) else ''


def place_area(place) -> str | None:
    """The place's neighbourhood, which a picture of a visit names in place of "Your place" (images/prompts.py)."""
    return place.get('neighborhood') if isinstance(place, dict) else None


class ChatPhotos:
    def __init__(self, database, images, life, openers=None, vault=None):
        self.database = database
        self.images = images
        self.life = life
        # Writes photo texts as first messages (companion/life/openers.py); set by the app.
        self.openers = openers
        # Holds the user's GIPHY key, if any (gifs.py).
        self.vault = vault

    def for_message(self, user, attempt_id) -> dict | None:
        """The picture this reply sends, recorded against the reply, or None. Never raises."""
        try:
            kind = asked_kind(user['text'])
            if kind in MEME_KINDS and not memes_fit(user['text']):
                return None
            if kind is not None:
                return self.send(kind, attempt_id)
            kind = self.unasked_kind(user['text'], attempt_id)
            if kind in MEME_KINDS and not memes_fit(user['text']):
                return None
            return self.send(kind, attempt_id, unasked=True) if kind else None
        except Exception:  # noqa: BLE001 - the reply goes ahead without a picture.
            return None

    def unasked_kind(self, text, attempt_id) -> str | None:
        """Whether this reply comes with a picture nobody asked for, and which: a seeded chance."""
        with self.database.connect() as connection:
            companion = current(connection)
            if not UNASKED or companion is None or not jobs.image_settings(connection)['unprompted_photos'] or \
                    not unasked_room(connection, companion['active_timeline_id'], self.database.clock.now()):
                return None
            level = memes_level(connection)
        rng = random.Random(attempt_id)
        if DOWN.search(text or ''):
            return 'meme' if rng.random() < UNASKED_MEME_CHANCE * MEME_LEVELS[level] else None
        if level == 3 and rng.random() < OFTEN_CHANCE:
            return 'meme'
        if rng.random() >= UNASKED_CHANCE:
            return None
        return 'selfie' if rng.random() < UNASKED_SELFIE_SHARE else 'moment'

    def send(self, kind, attempt_id, unasked=False) -> dict | None:
        # Without the agenda, the moment would be composed without the circle's plans (a birthday
        # outing) and the event the run later writes for this slot could tell a different story.
        self.life.extend_agenda('return')
        now = self.database.clock.now()
        with self.database.connect() as connection:
            if not jobs.image_settings(connection)['chat_photos'] or settings(connection)['paused_at']:
                return None
            companion = require_current(connection)
            moment = self.moment(connection, companion, now)
            local_hour = now.astimezone(zone(companion['version']['timezone'])).hour
            recent = recent_memes(connection, companion['active_timeline_id'])
        if kind in MEME_KINDS:
            return self.memes.send(attempt_id, moment, local_hour, recent, companion, unasked, asked_gif=kind == 'gif')
        if moment is None or unasked and self.in_chat(moment['event_key']):
            return None  # Unasked pictures are of something new.
        return self.send_moment(attempt_id, moment, kind, unasked)

    def send_moment(self, attempt_id, moment, kind, unasked=False) -> dict | None:
        post_id, job_id = self.picture(moment, kind)
        if job_id is None:
            return None
        self.record(attempt_id, post_id, job_id, kind, moment['event_key'], moment['summary'], unasked=unasked)
        return {'post_id': post_id, 'text': moment_text(moment, kind, unasked)}

    def picture(self, moment, kind) -> tuple[str | None, str | None]:
        """The post and job showing this moment in this framing, reusing one already made."""
        with self.database.connect() as connection:
            inputs = prompts.build_moment(connection, moment, jobs.image_settings(connection), kind)
        post = self.post_for(moment['timeline_id'], feed.PHOTO_KEY + moment['event_key'], moment['ends_at'])
        if post['status'] == 'removed':
            return None, None
        return post['id'], self.shown_job(post['id'], kind) or self.make(post['id'], inputs)

    def in_chat(self, event_key) -> bool:
        with self.database.connect() as connection:
            return optional(connection, 'SELECT message_id FROM chat_photos WHERE event_key=?', (event_key,)) is not None

    def share(self) -> dict | None:
        """Maybe text the user a photo of what the companion is out doing, unasked. Never raises."""
        try:
            return self.share_now(self.database.clock.now())
        except Exception:  # noqa: BLE001 - checked again on the next tick.
            return None

    def share_now(self, now) -> dict | None:
        with self.database.connect() as connection:
            companion = current(connection)
            if not UNASKED or self.openers is None or companion is None or not may_share(connection, companion, now):
                return None
        self.life.extend_agenda('background')
        with self.database.connect() as connection:
            moment = self.moment(connection, companion, now)
        if not moment or moment['kind'] not in SHARE_KINDS or self.in_chat(moment['event_key']) or \
                random.Random(moment['event_key']).random() >= SHARE_CHANCE:
            return None
        kind = 'selfie' if random.Random(moment['event_key'] + ':selfie').random() < SHARE_SELFIE_SHARE else 'moment'
        post_id, job_id = self.picture(moment, kind)
        if job_id is None:
            return None
        trigger = Trigger(feed.PHOTO_KEY + moment['event_key'], 'photo',
                          f"You texted the user a photo you took: {yours(moment)}", moment['caption'],
                          (moment['event_key'],))
        sent = self.openers.save(companion, trigger, moment['caption'], 'template', now)
        if sent['message'] is None:
            return None
        self.record(sent['message']['id'], post_id, job_id, kind, moment['event_key'], moment['summary'],
                    unasked=True)
        return {**sent['message'], 'photo': get(self.database, sent['message']['id'])}

    @property
    def memes(self):
        return Memes(self)

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

    def record(self, attempt_id, post_id, job_id, kind, event_key, summary, top='', bottom='', unasked=False,
               source='', picture=None, gif=None):
        with self.database.connect(write=True) as connection:
            connection.execute('INSERT OR REPLACE INTO chat_photos (message_id, post_id, job_id, kind, event_key, '
                               'summary, top_text, bottom_text, unasked, created_at, meme_source, meme_picture, gif) '
                               'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                               (attempt_id, post_id, job_id, kind, event_key, summary, top, bottom, int(unasked),
                                self.database.now(), source, encode(picture) if picture else None,
                                encode(gif) if gif else None))

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
        if families.pictured(connection, timeline_id, [words['summary'], words['post'], place_text(composed.get('place'))]) \
                or families.childs_day(connection, [(composed.get('outing') or {}).get('id')]):
            return None  # Children in their circle (companion/life/families.py) are told in words only.
        until = parse(shown['ends_at']).astimezone(zone(version['timezone'])).strftime('%H:%M')
        return {'event_key': key, 'summary': words['summary'], 'caption': words['post'], 'name': version['definition']['name'],
                'mood': composed.get('mood', ''), 'place': place_text(composed.get('place')),
                'neighborhood': place_area(composed.get('place')),
                'label': shown['block']['label'], 'kind': shown['block']['kind'], 'until': until,
                'rain': bool((composed.get('weather') or {}).get('rain')), 'timeline_id': timeline_id,
                'ends_at': shown['ends_at'], 'activity': composed.get('activity'), 'block_kind': shown['block']['kind'],
                'local_date': slot.local_date.isoformat(), 'weather': composed.get('weather') or shown['block'].get('weather'),
                'hour': now.astimezone(zone(version['timezone'])).hour, 'with': composed.get('with'),
                'hobby': composed.get('hobby')}

    def post_for(self, timeline_id, key, occurs_at) -> dict:
        """The post a picture is made on, made once: for a moment, the one its event will join."""
        with self.database.connect(write=True) as connection:
            post_id = feed.create(connection, timeline_id, 'event', key, [], occurs_at, self.database.now())
            return one(connection, 'SELECT * FROM feed_posts WHERE id=?', (post_id,))


MEME_KINDS = ('meme', 'gif')


class Memes:
    """One meme: its captions, then its picture. A reaction GIF when there is a GIPHY key (asked for, or
    a seeded share), a model picture now and then when one is set up, else a template on this computer."""

    def __init__(self, photos: ChatPhotos):
        self.photos = photos
        self.database = photos.database

    def allowed(self, connection, companion) -> bool:
        """Memes are on (Realism > Their days) and fit the city's time."""
        return memes_level(connection) > 0 and families.era_of(connection, companion['version']['definition']) in MEME_ERAS

    def send(self, attempt_id, moment, local_hour, recent, companion, unasked=False, asked_gif=False) -> dict | None:
        with self.database.connect() as connection:
            if not self.allowed(connection, companion):
                return None
            classics = bool(jobs.image_settings(connection)['meme_formats'])
        root = self.database.root
        if classics:
            meme_pictures.warm(root)
        meme = memes.choose(moment, local_hour, attempt_id, recent, choice=meme_pictures.has_choice(root, classics))
        rng = random.Random(attempt_id + ':source')
        timeline_id = companion['active_timeline_id']
        if asked_gif or rng.random() < GIF_SHARE:
            gif = gifs.pick(self.photos.vault, meme['mood'], attempt_id, asked=asked_gif) if self.photos.vault else None
            if gif:
                return self.send_gif(attempt_id, meme, gif, timeline_id, unasked)
        if meme['mood'] != 'choice' and rng.random() < MODEL_SHARE and (sent := self.send_model(attempt_id, meme, timeline_id, unasked)):
            return sent
        picture = meme_pictures.pick(meme, attempt_id, root, classics)
        return self.send_template(attempt_id, meme, picture, timeline_id, unasked) if picture else None

    def send_model(self, attempt_id, meme, timeline_id, unasked) -> dict | None:
        with self.database.connect() as connection:
            inputs = prompts.build_meme(connection, meme, jobs.image_settings(connection))
        post = self.photos.post_for(timeline_id, f'meme:{attempt_id}', self.database.now())
        job_id = self.photos.make(post['id'], inputs)
        if job_id is None:
            return None
        summary = meme['subject'] or f"you, looking {meme['expression']}"
        self.photos.record(attempt_id, post['id'], job_id, 'meme', '', summary, meme['top'], meme['bottom'], unasked)
        return {'post_id': post['id'], 'text': meme_text(summary, meme, unasked)}

    def send_template(self, attempt_id, meme, picture, timeline_id, unasked) -> dict:
        post = self.photos.post_for(timeline_id, f'meme:{attempt_id}', self.database.now())
        self.photos.record(attempt_id, post['id'], None, 'meme', '', picture.about, meme['top'], meme['bottom'], unasked,
                           'template', picture.view())
        return {'post_id': post['id'], 'text': meme_text(picture.about, meme, unasked)}

    def send_gif(self, attempt_id, meme, gif, timeline_id, unasked) -> dict:
        post = self.photos.post_for(timeline_id, f'meme:{attempt_id}', self.database.now())
        summary = (gif.get('title') or '')[:200] or f"a reaction GIF ({gif['tag']})"
        self.photos.record(attempt_id, post['id'], None, 'meme', '', summary, unasked=unasked, source='gif', gif=gif)
        lead = 'A reaction GIF you decided to send, unasked' if unasked else 'A reaction GIF you sent'
        return {'post_id': post['id'], 'text': f"- {lead} (a joke, not something that happened): "
                                               f"a GIF found by searching «{gif['tag']}»."}


def meme_text(summary, meme, unasked) -> str:
    lead = 'A meme you decided to send, unasked, to cheer them up' if unasked else 'A meme you made to share'
    return f"- {lead} (a joke, not something that happened): a picture of {summary}, captioned «{meme['top']}» / «{meme['bottom']}»."


def unasked_room(connection, timeline_id, now) -> bool:
    """Unasked pictures stay occasional: a few a day, a while apart."""
    rows = many(connection, 'SELECT photo.created_at FROM chat_photos photo JOIN messages message ON '
                'message.id=photo.message_id WHERE photo.unasked=1 AND message.timeline_id=? AND photo.created_at>? '
                'ORDER BY photo.created_at DESC', (timeline_id, stamp(now - timedelta(days=1))))
    return len(rows) < UNASKED_DAILY and (not rows or now - parse(rows[0]['created_at']) >= UNASKED_GAP)


def may_share(connection, companion, now) -> bool:
    """A photo text needs pictures on, unasked ones allowed, and the companion free to text first."""
    image = jobs.image_settings(connection)
    if not image['chat_photos'] or not image['unprompted_photos']:
        return False
    timeline_id = companion['active_timeline_id']
    if held(connection, companion, one(connection, 'SELECT * FROM life_settings WHERE id=1'), now):
        return False
    shared = one(connection, "SELECT COUNT(*) AS n FROM openers WHERE timeline_id=? AND kind='photo' AND created_at>?",
                 (timeline_id, stamp(now - timedelta(days=1))))['n']
    return shared < SHARE_DAILY and unasked_room(connection, timeline_id, now)


def recent_memes(connection, timeline_id, limit=6) -> list[str]:
    rows = many(connection, "SELECT photo.top_text FROM chat_photos photo JOIN messages message ON "
                "message.id=photo.message_id WHERE photo.kind='meme' AND message.timeline_id=? "
                'ORDER BY photo.created_at DESC LIMIT ?', (timeline_id, limit))
    return [row['top_text'] for row in rows]


LEADS = {'moment': 'A photo of what you are doing right now', 'selfie': 'A selfie you are taking right now',
         'view': 'A photo of what you can see right now'}


# In the day's summary "you" is the user ("Mira went to dinner at Lupa with you"): told to the companion, the user.
THE_USER = {'you': 'the user', 'You': 'The user', 'your': "the user's", 'Your': "The user's"}
YOU = {'They': 'You', 'they': 'you', 'Their': 'Your', 'their': 'your', 'Themselves': 'Yourself',
       'themselves': 'yourself'}


def yours(moment: dict) -> str:
    """The moment told to them in the second person ("You had a busy shift"), not as a summary about them
    ("Megan had a busy shift"), which the model would echo back."""
    summary = re.sub(r'\b(' + '|'.join(THE_USER) + r')\b', lambda m: THE_USER[m.group(1)], moment['summary'])
    if moment.get('name'):
        summary = prompts.unnamed(summary, moment['name'], 'they')
    # "Took Jo out for their birthday" is Jo's birthday, so that "their" stays (composer.py's own birthday lines aside).
    friends = ' for their birthday' in summary and not composer.OWN_BIRTHDAY_LINE.search(summary)
    told = re.sub(r'\b(' + '|'.join(YOU) + r')\b', lambda m: YOU[m.group(1)], summary)
    return told.replace(' for your birthday', ' for their birthday') if friends else told


def moment_text(moment, kind='moment', unasked=False) -> str:
    chose = ' You decided to send it; the user did not ask for it.' if unasked else ''
    return (f"- {LEADS[kind]} (from your day; still happening): {yours(moment)} "
            f"({moment['label'].lower()}, until {moment['until']} your time).{chose}")


def view(row) -> dict:
    done = row['job_status'] == 'completed' and row['output_file'] is not None
    return {'message_id': row['message_id'], 'post_id': row['post_id'], 'kind': row['kind'],
            'summary': row['summary'], 'top_text': row['top_text'], 'bottom_text': row['bottom_text'],
            'status': row['job_status'] or 'failed', 'job_id': row['job_id'], 'ref': row['job_id'] if done else None,
            'error': row['job_error'], 'in_feed': row['in_feed'] > 0, 'unasked': bool(row['unasked']),
            # The shape it is made in, so the chat holds its space while it loads and nothing moves when it lands.
            'aspect': decode(row['job_inputs']).get('aspect', 'landscape') if row['job_inputs'] else 'landscape',
            'source': row['meme_source'] or 'model', 'src': None, 'width': None, 'height': None, 'boxes': [],
            **ready_meme(row)}


PICTURES = '/api/images/memes/pictures/'


def ready_meme(row) -> dict:
    """A meme with a template or a GIF under it: there from the start, no image job behind it."""
    if row['meme_source'] == 'template' and row['meme_picture']:
        picture = decode(row['meme_picture'])
        return {'status': 'completed', 'src': PICTURES + quote(picture['id'], safe=':'), 'width': picture['width'],
                'height': picture['height'], 'boxes': picture.get('boxes') or []}
    if row['meme_source'] == 'gif' and row['gif']:
        gif = decode(row['gif'])
        return {'status': 'completed', 'src': gif['url'], 'width': gif['width'], 'height': gif['height'],
                'page': gif.get('page') or '', 'still': gif.get('still') or ''}
    return {}


SELECT = ('SELECT photo.*, job.status AS job_status, job.output_file, job.error AS job_error, job.inputs AS job_inputs, '
          '(SELECT COUNT(*) FROM feed_post_events link WHERE link.post_id=post.id) AS in_feed '
          'FROM chat_photos photo JOIN feed_posts post ON post.id=photo.post_id '
          'LEFT JOIN image_jobs job ON job.id=photo.job_id '
          "WHERE post.status!='removed' AND photo.message_id IN ")


JOB = 'id, status, output_file, error, inputs'


def newest_job(connection, job_id) -> dict | None:
    """The photo's newest attempt: a retry or a fallback to another backend takes the place of the one it follows."""
    job = optional(connection, f'SELECT {JOB} FROM image_jobs WHERE id=?', (job_id,))
    while job and (later := optional(connection, f'SELECT {JOB} FROM image_jobs '
                                     'WHERE retry_of=? ORDER BY created_at DESC, rowid DESC LIMIT 1', (job['id'],))):
        job = later
    return job


def followed(connection, row) -> dict:
    """The row with its newest attempt's state, so a fallback or a retry shows instead of the first failure."""
    if row['job_id'] is None or row['job_status'] in jobs.ACTIVE or row['job_status'] == 'completed':
        return row
    job = newest_job(connection, row['job_id'])
    if job is None or job['id'] == row['job_id']:
        return row
    return {**row, 'job_id': job['id'], 'job_status': job['status'], 'output_file': job['output_file'],
            'job_error': job['error'], 'job_inputs': job['inputs']}


def for_messages(connection, message_ids) -> dict[str, dict]:
    found = {}
    ids = list(message_ids)
    for start in range(0, len(ids), 500):
        chunk = ids[start:start + 500]
        rows = many(connection, SELECT + f"({','.join('?' * len(chunk))})", tuple(chunk))
        found.update({row['message_id']: view(followed(connection, row)) for row in rows})
    return found


def retry(database, message_id) -> dict:
    """Make a chat photo that failed again from where it stopped: the same request, or the current settings
    when the moment changed since. The photo then follows the new attempt."""
    photo = get(database, message_id)
    require(photo is not None, 'This photo could not be found.', 404)
    require(photo['status'] not in jobs.ACTIVE, 'This photo is still being made.', 409)
    require(photo['status'] != 'completed', 'This photo is already here.', 409)
    require(photo['job_id'] is not None, 'No image service could take this photo. Check Settings > Images.', 409)
    try:
        jobs.retry(database, photo['job_id'])
    except DomainError as failure:
        if failure.code != 'stale_inputs':
            raise
        jobs.retry(database, photo['job_id'], current_settings=True)
    return get(database, message_id)


def decorate(connection, messages: list[dict]) -> list[dict]:
    """Message views with the photo each reply sent, if any."""
    photos = for_messages(connection, [message['id'] for message in messages if message['role'] == 'companion'])
    return [{**message, 'photo': photos.get(message['id'])} for message in messages]


def get(database, message_id) -> dict | None:
    with database.connect() as connection:
        return for_messages(connection, [message_id]).get(message_id)
