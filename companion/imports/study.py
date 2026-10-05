"""Reviewed import of one character from Prospero's Study (PRD "Standalone product boundary").

Inspect lists the Study's characters and Review shows exactly what one of them would become;
neither writes anywhere. Import repeats the review, refuses it if the result no longer matches
the reviewed token, and creates the companion with new local ids. Only the selected character's
latest version and its own artwork are copied. Stories, Sidebar conversations, profiles and
credentials, backups and other library items are never read, and no writing history becomes a
memory or relationship.
"""
import hashlib

from companion import characters
from companion.database import decode, encode, identifier, one
from companion.errors import DomainError, require
from companion.imports import study_source as source
from companion.lora import references
from companion.models import CharacterDefinition

# Study character field -> Companion definition field. Pronouns and form of address share "identity".
FIELDS = (
    ('text', 'Character & background', 'background'),
    ('behavior_rules', 'Behavior & boundaries', 'personality'),
    ('voice', 'Voice & manner', 'voice'),
    ('pronouns', 'Pronouns', 'identity'),
    ('address', 'Form of address', 'identity'),
)
LIMITS = {'background': 12000, 'personality': 8000, 'voice': 4000, 'identity': 4000}
TARGET_LABELS = {'name': 'Name', 'background': 'Background', 'personality': 'Personality', 'voice': 'Voice',
                 'identity': 'Who they are'}
NOT_IMPORTED = {
    'scenario': ('Scenario', "It sets up a story's starting circumstances; the companion's life starts fresh."),
    'example_dialogue': ('Example dialogue', 'Written exchanges stay in the Study; they never become shared history.'),
    'greetings': ('Opening greetings', 'Story openings stay in the Study.'),
    'author_notes': ('Editor notes', 'Private authoring notes stay in the Study.'),
    'lorebook_versions': ('Linked lorebooks', 'Lorebooks are separate library items and are not copied.'),
}


def inspect(database, path) -> dict:
    workspace, file = source.locate(path, database.path)
    with source.open_readonly(file) as connection:
        return {'workspace': describe(connection, workspace, file), 'characters': source.characters(connection)}


def describe(connection, workspace, file) -> dict:
    return {'path': str(workspace), 'database': str(file), 'study_version': source.app_version(workspace, file),
            'schema_fingerprint': source.fingerprint(connection)}


def review(database, path, character_id) -> dict:
    return {key: value for key, value in build(database, path, character_id).items() if key != 'files'}


def build(database, path, character_id) -> dict:
    workspace, file = source.locate(path, database.path)
    with source.open_readonly(file) as connection:
        found = source.character(connection, character_id)
        definition, fields = mapping(found)
        art, files = artwork(connection, found['content'].get('artwork_sha256'))
        result = {'workspace': describe(connection, workspace, file),
                  'source': {'character_id': found['id'], 'version_id': found['version_id'],
                             'version_number': found['number'], 'name': found['name'],
                             'created_at': found['created_at']},
                  'definition': definition.model_dump(), 'fields': fields, 'artwork': art,
                  'exclusions': exclusions(connection, found), 'defaults': DEFAULTS}
    with database.connect() as connection:
        result['companion_exists'] = characters.current(connection) is not None
    result['review_token'] = token(result)
    return {**result, 'files': files}


DEFAULTS = ['Relationship starts as friendship and the timezone as UTC; change both on the Character page.',
            'Interests, routine, home city and emotional traits start empty.']


def token(result) -> str:
    """A digest of everything shown in the review except thumbnails."""
    shown = {**result, 'artwork': [{key: value for key, value in item.items() if key != 'thumbnail'}
                                   for item in result['artwork']]}
    shown.pop('companion_exists', None)
    return hashlib.sha256(encode(shown).encode()).hexdigest()


def mapping(found) -> tuple[CharacterDefinition, list[dict]]:
    content = found['content']
    values = {'name': found['name'].strip()[:120] or 'Imported character'}
    fields = [{'source': 'name', 'label': 'Name', 'target': 'name', 'target_label': 'Name', 'status': 'copied',
               'characters': len(values['name']), 'note': ''}]
    identity_lines = []
    for key, label, target in FIELDS:
        text = content.get(key)
        if not isinstance(text, str) or not text.strip():
            continue
        text = text.strip()
        if target == 'identity':
            identity_lines.append(f'{label}: {text}')
        else:
            values[target] = text
        fields.append({'source': key, 'label': label, 'target': target, 'target_label': TARGET_LABELS[target],
                       'status': 'copied', 'characters': len(text), 'note': ''})
    if identity_lines:
        values['identity'] = '\n'.join(identity_lines)
    for target, limit in LIMITS.items():
        if len(values.get(target, '')) > limit:
            values[target] = values[target][:limit].rstrip()
            for field in fields:
                if field['target'] == target:
                    field.update(status='shortened', note=f'The Companion keeps the first {limit:,} characters; '
                                 'the full text stays in the Study.')
    fields.extend(skipped(content))
    return CharacterDefinition(**values), fields


def skipped(content) -> list[dict]:
    mapped = {key for key, _label, _target in FIELDS} | {'artwork_sha256'}
    listed = []
    for key, value in content.items():
        if key in mapped or value in (None, '', [], {}):
            continue
        label, note = NOT_IMPORTED.get(key, (key, 'The Companion has no matching field.'))
        listed.append({'source': key, 'label': label, 'target': None, 'target_label': None,
                       'status': 'not_imported', 'characters': None, 'note': note})
    return listed


def artwork(connection, digest) -> tuple[list[dict], dict]:
    """The artwork the selected version names, when it is intact and usable as a reference picture."""
    if not digest:
        return [], {}
    item = {'sha256': str(digest), 'width': None, 'height': None, 'format': None, 'bytes': None,
            'status': 'excluded', 'reason': '', 'thumbnail': None}
    row = source.artwork(connection, digest) if isinstance(digest, str) else None
    if row is None:
        return [{**item, 'reason': 'The Study no longer has this artwork.'}], {}
    data = row['data']
    item.update(bytes=len(data), thumbnail=f"data:image/png;base64,{row['thumbnail']}" if row['thumbnail'] else None)
    if hashlib.sha256(data).hexdigest() != digest:
        return [{**item, 'reason': 'The stored artwork does not match its checksum.'}], {}
    if len(data) > references.MAX_BYTES:
        return [{**item, 'reason': 'The artwork is larger than 30 MB.'}], {}
    try:
        kind, width, height = references.checked_image(data)
    except DomainError as error:
        return [{**item, 'reason': error.message}], {}
    item.update(status='included', format=kind, width=width, height=height,
                reason='Copied to the reference pictures, marked "Not stated" until you confirm your rights.')
    return [item], {digest: (kind, data)}


def exclusions(connection, found) -> list[dict]:
    others = source.count(connection, "SELECT COUNT(*) FROM assets WHERE kind IN ('character','persona')") - 1
    return [
        {'item': 'Story prose', 'detail': f"{source.count(connection, 'SELECT COUNT(*) FROM stories')} "
                                          'stories and every passage in them stay in the Study.'},
        {'item': 'Sidebar conversations',
         'detail': f"{source.count(connection, 'SELECT COUNT(*) FROM side_threads')} Sidebar threads are not read."},
        {'item': 'Model credentials and connection profiles',
         'detail': "Not read. Saved keys stay in the Study's own credential store."},
        {'item': 'Backup schedules and archives', 'detail': 'Not read.'},
        {'item': 'Other characters and personas', 'detail': f'{max(others, 0)} other library characters and '
                                                            'personas are not copied.'},
        {'item': 'Lorebooks and writing styles', 'detail': 'Not copied.'},
        {'item': 'Earlier versions of this character',
         'detail': f"Only version {found['number']} is copied; {found['versions'] - 1} earlier versions stay."},
        {'item': 'Relationship and memories',
         'detail': 'Nothing from the Study becomes a memory or relationship history. The companion starts new.'},
    ]


def run(database, body) -> dict:
    reviewed = build(database, body.path, body.character_id)
    require(reviewed['review_token'] == body.review_token,
            'The Study character changed since you reviewed it. Review it again before importing.', 409)
    require(not reviewed['companion_exists'], 'This workspace already has a companion. Import into an empty '
            'workspace, or edit the companion on the Character page.', 409)
    written = []
    try:
        pictures = [store(database, digest, *reviewed['files'][digest], written) for digest in reviewed['files']]
        with database.connect(write=True) as connection:
            return record(connection, database.now(), reviewed, pictures)
    except BaseException:
        for path in written:
            path.unlink(missing_ok=True)
        raise


def store(database, digest, kind, data, written) -> dict:
    reference_id = identifier()
    name = f'{reference_id}.{kind}'
    target = references.directory(database) / name
    partial = target.with_name(name + '.partial')
    partial.write_bytes(data)
    partial.replace(target)
    written.append(target)
    return {'id': reference_id, 'file': name, 'sha256': digest, 'kind': kind, 'bytes': len(data)}


def record(connection, timestamp, reviewed, pictures) -> dict:
    found = reviewed['source']
    note = f"Imported from Prospero's Study: {found['name']}, version {found['version_number']}"
    companion = characters.create_in(connection, timestamp, CharacterDefinition(**reviewed['definition']),
                                     note[:500])
    art = {item['sha256']: item for item in reviewed['artwork']}
    for picture in pictures:
        shown = art[picture['sha256']]
        connection.execute(
            'INSERT INTO lora_references (id, companion_id, file, original_name, media_type, sha256, width, height, '
            'bytes, source_note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (picture['id'], companion['id'], picture['file'], f"study-artwork.{picture['kind']}",
             references.TYPES[picture['kind']], picture['sha256'], shown['width'], shown['height'],
             picture['bytes'], f"{note} (Study artwork {picture['sha256'][:12]})"[:1000], timestamp, timestamp))
    workspace = reviewed['workspace']
    import_id = identifier()
    connection.execute(
        'INSERT INTO study_imports (id, companion_id, character_version_id, workspace_path, database_path, '
        'study_version, schema_fingerprint, source_character_id, source_version_id, source_version_number, '
        'source_name, review_token, fields, artwork, imported_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (import_id, companion['id'], companion['active_version_id'], workspace['path'], workspace['database'],
         workspace['study_version'], workspace['schema_fingerprint'], found['character_id'], found['version_id'],
         found['version_number'], found['name'], reviewed['review_token'], encode(reviewed['fields']),
         encode(copied_artwork(reviewed['artwork'], pictures)), timestamp))
    return {'companion': companion, 'import': attribution(connection, import_id)}


def copied_artwork(shown, pictures) -> list[dict]:
    stored = {picture['sha256']: picture['id'] for picture in pictures}
    return [{**{key: value for key, value in item.items() if key != 'thumbnail'},
             'reference_id': stored.get(item['sha256'])} for item in shown]


def attribution(connection, import_id) -> dict:
    row = one(connection, 'SELECT * FROM study_imports WHERE id=?', (import_id,))
    return {**row, 'fields': decode(row['fields']), 'artwork': decode(row['artwork'])}


def imports(database) -> list[dict]:
    with database.connect() as connection:
        companion = characters.current(connection)
        if companion is None:
            return []
        rows = connection.execute('SELECT id FROM study_imports WHERE companion_id=? ORDER BY imported_at',
                                  (companion['id'],)).fetchall()
        return [attribution(connection, row[0]) for row in rows]
