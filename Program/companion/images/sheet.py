"""A character reference sheet, made on Codex before any other picture of a companion (Vanta, 2026-10-11).

When a picture of the companion is about to go to a Codex backend and they have no sheet yet, the app
first asks Codex for a three-panel reference sheet (a face close-up, a front body view without the head,
a back view, on a grey studio background), saves it as the companion's identity reference, and then
makes the real picture with the sheet attached. Every later picture of them on Codex follows the same
sheet, so the first picture of someone costs two Codex calls and every later one a single call.

The sheet is a fixed template filled from the companion's own data, never written by a model: their
looks sheet and appearance in words, an everyday outfit (the profile picture's), and the backend's
picture style. When they already have a profile picture, it is attached and the sheet follows it.
Editing their appearance makes a new sheet the next time; the old one stays on disk until it is
replaced. The sheet is classified and must be eligible for the backend like any request (F6); when
it is not, or the sheet fails for any reason but a sign-in problem, the picture is made from the
description alone, as before.

Codex calls stay serial: the sheet and the picture run one after the other inside the one Codex slot
the picture already holds, and the adapter's own lock still covers each call.
"""
import contextlib
import hashlib
import random
import re

from companion.characters import by_id
from companion.database import identifier, optional
from companion.images import backends, prompts
from companion.images.adapters.base import AdapterError, ImageRequest, size_for
from companion.images.content import classify
from companion.images.routing import eligible
from companion.images.storage import directory as images_directory
from companion.images.storage import sniff
from companion.lora import files

# Off in most tests (tests/conftest.py), since the extra Codex call would change unrelated counts.
ENABLED = True
FOLDER = 'sheets'
# The sheet is landscape; Codex makes nothing larger than 1536 x 1024.
ASPECT = 'landscape'

FROM_PICTURE = 'Use the attached image as the primary and authoritative reference for the character.'
FROM_WORDS = ('There is no picture of this character yet. Use the character description below as the primary and '
              'authoritative reference for the character.')
TEMPLATE = """# UNIVERSAL PROFESSIONAL CHARACTER REFERENCE SHEET — PRODUCTION STANDARD

**REFERENCE:** {source}

**CHARACTER DESCRIPTION:** {description}

**OBJECTIVE:** Create a professional, production-ready, three-panel character reference sheet designed specifically \
for AI image generation, character consistency, and cinematic production.

### 1. IDENTITY & REFERENCE LOCK

Preserve the exact identity and appearance of the reference character. Maintain the original facial features, skin \
tone, age, hairstyle, hair color, body proportions, clothing, accessories, and distinctive characteristics. Do not \
redesign, beautify, reinterpret, or replace the character. The character is fictional; preserve its original design.

### 2. BACKGROUND & LAYOUT

Use a solid, neutral, medium-gray studio background across all three panels. Create a clean horizontal triptych \
with three equally organized vertical panels, subtle separators, consistent neutral studio lighting, realistic \
shadows, and professional production-sheet presentation. Render the character as: {style}.

### PANEL 01 — FACE DETAIL / CLOSE-UP

Create a tight, high-resolution close-up of the exact character's face and head. Clearly reveal the facial \
structure, eyes, eyebrows, nose, lips, skin texture, hairline, hairstyle, and other identifying details. Use a \
neutral expression, natural lighting, sharp focus, and realistic anatomical detail. Frame the face large enough to \
serve as a precise identity reference.

### PANEL 02 — FRONT BODY VIEW / FACE EXCLUDED

Show the exact same character standing upright in a straight, neutral, front-facing full-body pose. Frame the image \
from the base of the neck down to the feet, with the entire face and head excluded from the frame. Clearly show the \
shoulders, torso, arms, hands, clothing, waist, legs, footwear, body proportions, and complete silhouette. Keep the \
arms slightly separated from the torso so the body structure and outfit remain clearly visible.

### PANEL 03 — BACK BODY VIEW

Show the exact same character standing upright in a straight, neutral, rear-facing full-body pose. Display the back \
of the head, hairstyle from behind, shoulders, back, arms, clothing details, legs, and footwear. Keep the complete \
character visible from head to feet. Match the exact outfit, body proportions, hairstyle, and physical appearance \
established in the other panels.

### 3. STRICT CONSISTENCY RULES

- All three panels must depict the same individual or character.
- Preserve identical clothing, colors, accessories, hairstyle, body proportions, and physical characteristics.
- Use consistent camera height, neutral studio lighting, gray background, and realistic proportions.
- Keep the front and back views anatomically correct and naturally posed.
- Do not invent additional characters, outfits, accessories, or design variations.
- Do not add action poses, cinematic environments, dramatic lighting, decorative graphics, text, labels, or \
unnecessary details.
- Do not allow the character to become cropped in the back-view panel.
- The center panel must exclude the face and head completely.
- The left panel must prioritize facial identity and fine details.
- The right panel must prioritize the rear silhouette and back-of-head details.

### 4. FINAL OUTPUT

Generate one clean, landscape-format, three-panel professional character reference sheet. Prioritize reference \
accuracy, clear separation of views, realistic detail, and practical usability as a character reference. The final \
image must function as a technical character reference rather than a decorative character collage.

**RESOLUTION:** Generate the final image in landscape format at the largest size available, {width} × {height} \
pixels.

**FINAL PRIORITY:** Exact reference preservation, accurate front and back views, clear facial identity, consistent \
wardrobe, neutral gray background, and production-ready character continuity."""
# Added to a picture that follows the sheet. It keeps the sheet's person and drops its layout.
FOLLOW = ('The attached image is a character reference sheet of this same person: a close-up of the face, a front '
          'view and a back view. Keep their face, hair, skin tone, body proportions and build exactly as they are '
          'there; take the outfit, pose, setting and framing from this description, and make one ordinary picture, '
          'not a reference sheet: no panels, no grey studio background.')


def depicts_companion(inputs: dict) -> bool:
    """Whether a picture shows the companion: a view of what they see does not, nor a meme of something else."""
    return inputs.get('framing') != 'view' and not (inputs.get('meme') or {}).get('subject')


def companion_of_version(connection, version_id: str | None) -> str | None:
    row = optional(connection, 'SELECT companion_id FROM character_versions WHERE id=?', (version_id,)) \
        if version_id else None
    return row['companion_id'] if row else None


def outfit_of(companion_id: str) -> str:
    from companion.lora.portraits import outfits_for  # portraits builds on the image modules that import this one
    return outfits_for(companion_id)[0]


def description(companion: dict) -> str:
    """Their looks in words, what the appearance says a camera can see, and an everyday outfit unless the
    appearance already says what they wear."""
    definition = companion['version']['definition']
    # The user's own In photos line, when they wrote one, is what every picture of them follows, this sheet included.
    appearance = (definition.get('in_photos') or '').strip() or definition.get('appearance', '')
    looks, who = prompts.sheet_for(companion, definition)
    look = prompts.in_photos(definition, who)
    subject = prompts.PRONOUNS[who][0]
    dressed = any(prompts.clothing(clause) for clause in re.split(r'[.!?,;]', appearance) if clause.strip())
    wearing = '' if dressed else f"{subject} {'are' if who == 'they' else 'is'} wearing {outfit_of(companion['id'])}."
    return ' '.join(part for part in (looks, f'{look}.' if look else '', wearing) if part)


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:32]


def compose(text: str, style: str | None, has_picture: bool, backend_kind='codex') -> str:
    width, height = size_for(backend_kind, ASPECT)
    style = (style or prompts.DEFAULT_STYLE).strip().rstrip('.')
    return TEMPLATE.format(source=FROM_PICTURE if has_picture else FROM_WORDS, description=text, style=style,
                           width=width, height=height)


def folder(database):
    path = images_directory(database) / FOLDER
    path.mkdir(parents=True, exist_ok=True)
    return path


def stored(database, connection, companion_id: str, mark: str) -> bytes | None:
    row = optional(connection, 'SELECT file FROM character_sheets WHERE companion_id=? AND fingerprint=? '
                               'ORDER BY created_at DESC, rowid DESC LIMIT 1', (companion_id, mark))
    if row is None:
        return None
    with contextlib.suppress(OSError):
        return files.inside(folder(database), row['file']).read_bytes()
    return None


def profile_picture(database, connection, companion: dict) -> bytes | None:
    if not companion.get('portrait_reference_id'):
        return None
    row = optional(connection, 'SELECT file FROM lora_references WHERE id=? AND companion_id=?',
                   (companion['portrait_reference_id'], companion['id']))
    if row is None:
        return None
    with contextlib.suppress(OSError):
        return files.inside(files.folder(database, 'references'), row['file']).read_bytes()
    return None


async def ensure(database, adapter, backend: dict, config: dict, key, raw_dir, companion_id: str | None,
                 general_style: str | None) -> bytes | None:
    """The companion's sheet for this Codex backend, made now when there is none for their current looks.
    None means the picture goes ahead from the description alone. A sign-in error is raised, so the
    caller stops the Codex queue as for any picture."""
    if not ENABLED or backend['kind'] != 'codex' or companion_id is None:
        return None
    with database.connect() as connection:
        companion = by_id(connection, companion_id)
        if companion is None:
            return None
        text = description(companion)
        mark = fingerprint(text)
        existing = stored(database, connection, companion_id, mark)
        if existing is not None:
            return existing
        picture = profile_picture(database, connection, companion)
    appearance = companion['version']['definition'].get('appearance', '')
    prompt = compose(text, backends.style_for(backend, general_style), picture is not None, backend['kind'])
    classification = classify({'prompt': prompt, 'negative': prompts.NEGATIVE, 'appearance': appearance})
    if not eligible(classification, backend):
        return None
    sheet_id = identifier()
    width, height = size_for(backend['kind'], ASPECT)
    request = ImageRequest(f'sheet-{sheet_id}', prompt, prompts.NEGATIVE, random.SystemRandom().randrange(1, 2**31),
                           width, height, backend, config, key, raw_dir, reference=picture)
    result = None
    try:
        result = await adapter.generate(request)
        kind, out_width, out_height = sniff(result.data)
    except AdapterError as error:
        if error.code == 'auth':
            raise
        return None
    except Exception:  # noqa: BLE001 - a failed sheet never stops the picture itself.
        return None
    finally:
        if result is not None and result.raw_path:
            with contextlib.suppress(OSError):
                result.raw_path.unlink()
    name = f'{sheet_id}.{kind}'
    target = folder(database) / name
    partial = target.with_name(name + '.partial')
    partial.write_bytes(result.data)
    partial.replace(target)
    with database.connect(write=True) as connection:
        connection.execute(
            'INSERT INTO character_sheets (id, companion_id, fingerprint, file, prompt, backend_id, from_picture, '
            'width, height, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (sheet_id, companion_id, mark, name, prompt, backend['id'], int(picture is not None), out_width,
             out_height, database.now()))
    return result.data

