"""Profile pictures made while setting up a companion.

Three pictures, each made from the one before it so they show the same person:

1. the profile picture: waist up, facing the camera, in an everyday outfit, with an expression
   that fits their personality;
2. a three-quarter view in a second everyday outfit, following picture 1;
3. a close-up of the face, following picture 2.

The whole set goes to one backend that can take a reference picture (backends.takes_reference),
in the user's order. When none can, nothing is sent unless the user explicitly asks for the set
to be made from the description alone, so a set of three unrelated people is never passed off
as one. Each picture is classified and routed like any image (PRD F6): Prohibited is refused
everywhere and NSFW goes to a local backend only.

The set is a `lora_generations` row of kind `portraits`, so it runs through the same runner,
admission rules and keep step as the LoRA maker's generated pictures. Kept pictures join the
character's reference set, and the kept profile picture becomes the companion's picture.
Expression and outfits are drafted from fixed lists without a model, and are editable.
"""
import random
import re

from companion.characters import require_current
from companion.database import encode, identifier, one, optional
from companion.errors import DomainError, require
from companion.images import backends
from companion.images.content import classify
from companion.images.jobs import image_settings
from companion.images.prompts import NEGATIVE
from companion.images.routing import route
from companion.lora import generation, references

# Personality words, first match wins, and the expression they suggest.
EXPRESSIONS = (
    (r'\b(shy|timid|reserved|introvert\w*|quiet|awkward)', 'a small, slightly shy smile'),
    (r'\b(sarcas\w*|dry|wry|deadpan|cynic\w*|sardonic)', 'a wry half-smile'),
    (r'\b(playful|mischiev\w*|cheeky|teas\w*|goofy|silly)', 'a playful grin'),
    (r'\b(bubbly|cheerful|sunny|upbeat|energetic|enthusias\w*|optimis\w*)', 'a bright, open smile'),
    (r'\b(confident|bold|assertive|ambitious|driven|charismatic)', 'a confident, easy smile'),
    (r'\b(serious|stoic|calm|composed|steady|thoughtful|analytical)', 'a calm, composed expression with a hint of '
     'a smile'),
    (r'\b(warm|kind|gentle|caring|sweet|nurturing|friendly)', 'a warm, gentle smile'),
    (r'\b(moody|brooding|melanchol\w*|guarded|aloof)', 'a guarded, thoughtful look'),
)
DEFAULT_EXPRESSION = 'a relaxed, natural smile'
OUTFITS = ('a plain t-shirt under a light jacket', 'a soft knit sweater', 'a casual button-up shirt',
           'a comfortable hoodie', 'a denim jacket over a plain top', 'a cardigan over a t-shirt',
           'a crewneck sweatshirt', 'a flannel shirt over a t-shirt', 'a simple long-sleeved top',
           'a light overshirt over a tank top')
# (key, label, shot, aspect). {outfit}, {other_outfit} and {expression} are filled from the draft.
STEPS = (
    ('profile', 'Profile picture', 'waist-up photo facing the camera, wearing {outfit}, {expression}, plain softly '
     'lit background', 'portrait'),
    ('three_quarter', 'Three-quarter view', 'waist-up photo in three-quarter view, body and face turned slightly '
     'to one side, wearing {other_outfit}, {expression}, plain softly lit background', 'portrait'),
    ('close_up', 'Face close-up', 'close-up of the face, head and shoulders filling the frame, {expression}, soft '
     'natural light', 'square'),
)
FOLLOW = ('The attached reference picture shows this same person: keep their face, hair, skin tone and build '
          'exactly as they are there, and change only the outfit, pose and framing described here.')
NO_REFERENCE = ('None of your enabled image backends can make a picture from a reference picture, so pictures 2 and '
                '3 would show a different person. Codex, OpenRouter, the OpenAI API, or a ComfyUI server with a '
                'reference workflow can. You can still make all three from the description alone.')


def expression_for(definition) -> str:
    text = ' '.join(str(definition.get(key, '')) for key in ('personality', 'identity', 'voice')).casefold()
    return next((expression for pattern, expression in EXPRESSIONS if re.search(pattern, text)), DEFAULT_EXPRESSION)


def outfits_for(companion_id: str) -> tuple[str, str]:
    """Two different everyday outfits, the same ones each time for this companion."""
    first, second = random.Random(companion_id).sample(OUTFITS, 2)
    return first, second


def usable(connection, without_reference=False) -> list[dict]:
    pool = generation.routable_backends(connection)
    return pool if without_reference else [backend for backend in pool if backends.takes_reference(backend)]


def backend_line(backend) -> dict | None:
    return None if backend is None else {'id': backend['id'], 'label': backend['label'], 'kind': backend['kind'],
                                         'local': backends.is_local(backend)}


def draft(database) -> dict:
    with database.connect() as connection:
        companion = require_current(connection)
        definition = companion['version']['definition']
        style = image_settings(connection)['style']
        enabled = generation.routable_backends(connection)
        follows = usable(connection)
    expression = expression_for(definition)
    outfit, other_outfit = outfits_for(companion['id'])
    shots = [{'key': key, 'label': label, 'aspect': aspect,
              'shot': shot.format(outfit=outfit, other_outfit=other_outfit, expression=expression)}
             for key, label, shot, aspect in STEPS]
    return {'base': generation.base_of(definition), 'style': style or generation.DEFAULT_STYLE, 'negative': NEGATIVE,
            'seed': random.SystemRandom().randrange(1, 2**31), 'shots': shots, 'any_backend': bool(enabled),
            'reference_backend': backend_line(follows[0] if follows else None)}


def plan(connection, body) -> list[dict]:
    """Each picture's prompt, classification and destination, exactly as it would be sent. The
    first picture's backend makes the rest, so the set stays one person."""
    definition = require_current(connection)['version']['definition']
    style = image_settings(connection)['style']
    pool = usable(connection, body.without_reference)
    chosen = body.backend_id
    blocked = None
    if not pool:
        blocked = 'No image backend is enabled. Set one up in Settings to make images.' \
            if body.without_reference else NO_REFERENCE
    elif chosen and chosen not in {backend['id'] for backend in pool}:
        blocked = 'That backend cannot make a picture from a reference picture. Choose another one.'
    planned = []
    for position, shot in enumerate(body.shots):
        follows = None if position == 0 or body.without_reference else position - 1
        prompt = generation.compose(style, body.base, shot.shot) + (f' {FOLLOW}' if follows is not None else '')
        classification = classify({'prompt': prompt, 'negative': NEGATIVE,
                                   'appearance': definition.get('appearance', '')})
        decision = route(classification, pool, chosen)
        refusal = blocked or decision.refusal
        target = None if refusal else decision.target
        if position == 0 and target is not None:
            chosen = target['id']
        planned.append({'label': shot.label, 'shot': shot.shot, 'aspect': shot.aspect, 'prompt': prompt,
                        'follows': follows, 'tier': classification.tier, 'reasons': classification.reasons,
                        'route_reason': decision.reason, 'refusal': refusal, 'backend': backend_line(target)})
    return planned


def preview(database, body) -> dict:
    with database.connect() as connection:
        return {'shots': plan(connection, body)}


def create(database, body) -> dict:
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        busy = connection.execute("SELECT 1 FROM lora_generations WHERE status='running' AND companion_id=?",
                                  (companion['id'],)).fetchone()
        require(busy is None, 'Pictures are already being made. Wait for them or stop them first.', 409)
        planned = plan(connection, body)
        if planned[0]['backend'] is None:
            code = 'no_reference_backend' if planned[0]['refusal'] == NO_REFERENCE else 'refused'
            raise DomainError(planned[0]['refusal'], 409, code)
        generation_id = identifier()
        timestamp = database.now()
        connection.execute("INSERT INTO lora_generations (id, companion_id, base, seed, status, kind, created_at) "
                           "VALUES (?, ?, ?, ?, 'running', 'portraits', ?)",
                           (generation_id, companion['id'], body.base.strip(), body.seed, timestamp))
        for position, item in enumerate(planned):
            target = item['backend']
            refused = target is None
            connection.execute(
                'INSERT INTO lora_gen_images (id, generation_id, position, label, shot, prompt, negative, aspect, '
                'seed, classification, reasons, route_reason, backend_id, backend_label, backend_kind, status, '
                'error, finished_at, follows) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (identifier(), generation_id, position, item['label'], item['shot'], item['prompt'], NEGATIVE,
                 item['aspect'], body.seed, item['tier'], encode(item['reasons']), item['route_reason'],
                 None if refused else target['id'], None if refused else target['label'],
                 None if refused else target['kind'], 'failed' if refused else 'queued',
                 item['refusal'] if refused else None, timestamp if refused else None, item['follows']))
    return generation.get(database, generation_id)


def latest(database) -> dict | None:
    with database.connect() as connection:
        companion = require_current(connection)
        row = optional(connection, "SELECT * FROM lora_generations WHERE companion_id=? AND kind='portraits' "
                                   'ORDER BY created_at DESC, rowid DESC LIMIT 1', (companion['id'],))
        return None if row is None else generation.view(connection, row)


def redo(database, generation_id, position) -> dict:
    """Make one picture again, and every picture after it, since they follow it. Each gets a new
    seed, or a seeded backend would return the same picture."""
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        row = one(connection, "SELECT * FROM lora_generations WHERE id=? AND companion_id=? AND kind='portraits'",
                  (generation_id, companion['id']))
        require(row['status'] != 'running', 'These pictures are still being made.', 409)
        busy = connection.execute("SELECT 1 FROM lora_generations WHERE status='running' AND companion_id=?",
                                  (companion['id'],)).fetchone()
        require(busy is None, 'Pictures are already being made. Wait for them or stop them first.', 409)
        images = connection.execute('SELECT * FROM lora_gen_images WHERE generation_id=? ORDER BY position',
                                    (generation_id,)).fetchall()
        require(0 <= position < len(images), 'There is no such picture.', 404)
        again = [dict(image) for image in images[position:]]
        require(all(image['decision'] is None for image in again), 'A picture you kept cannot be made again.', 409)
        first = dict(images[0])
        require(first['backend_id'] is not None, 'The first picture had nowhere to go.', 409)
        seed = random.SystemRandom().randrange(1, 2**31)
        for image in again:
            connection.execute(
                "UPDATE lora_gen_images SET status='queued', error=NULL, output_file=NULL, width=NULL, height=NULL, "
                'used_seed=NULL, model=NULL, workflow=NULL, started_at=NULL, finished_at=NULL, seed=?, '
                'backend_id=?, backend_label=?, backend_kind=? WHERE id=?',
                (seed, first['backend_id'], first['backend_label'], first['backend_kind'], image['id']))
        connection.execute("UPDATE lora_generations SET status='running', finished_at=NULL WHERE id=?",
                           (generation_id,))
    for image in again:
        if image['output_file']:
            (generation.directory(database) / image['output_file']).unlink(missing_ok=True)
    return generation.get(database, generation_id)


def set_portrait(database, reference_id: str | None) -> dict:
    """The companion's picture: one of their reference pictures, or none (their initial)."""
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        if reference_id is not None:
            references.get(connection, reference_id)
        connection.execute('UPDATE companions SET portrait_reference_id=? WHERE id=?', (reference_id, companion['id']))
    return {'portrait_reference_id': reference_id}
