"""Reviewed import from a Prospero's Study workspace (PRD "Standalone product boundary")."""
import base64
import hashlib
import json
import sqlite3
import struct
from contextlib import contextmanager

import pytest

from companion.imports.study_source import open_readonly

# Library, story, Sidebar, profile and backup tables copied from prosperos-study server/schema.sql at
# bbcbde4, with the WAL journal its server/database.py sets. The Study has no identity marker table.
STUDY_SCHEMA = """
CREATE TABLE IF NOT EXISTS stories (
    id TEXT PRIMARY KEY, title TEXT NOT NULL, premise TEXT NOT NULL,
    settings TEXT NOT NULL, manifest_id TEXT, revision INTEGER NOT NULL DEFAULT 0,
    archived INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('character','lorebook','persona')),
    latest_version_id TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS asset_versions (
    id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets(id),
    number INTEGER NOT NULL, name TEXT NOT NULL, content TEXT NOT NULL,
    note TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(asset_id,number)
);
CREATE TABLE IF NOT EXISTS asset_sources (
    version_id TEXT PRIMARY KEY REFERENCES asset_versions(id),
    format TEXT NOT NULL, markdown TEXT NOT NULL, sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS manifests (
    id TEXT PRIMARY KEY, story_id TEXT NOT NULL REFERENCES stories(id),
    attachments TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS branches (
    id TEXT PRIMARY KEY, story_id TEXT NOT NULL REFERENCES stories(id),
    name TEXT NOT NULL, head_id TEXT, manifest_id TEXT NOT NULL REFERENCES manifests(id),
    forked_from TEXT REFERENCES branches(id), fork_node_id TEXT,
    revision INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY, story_id TEXT NOT NULL REFERENCES stories(id),
    parent_id TEXT REFERENCES nodes(id), role TEXT NOT NULL,
    text TEXT NOT NULL, manifest_id TEXT NOT NULL REFERENCES manifests(id),
    metadata TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY, latest_version_id TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS profile_versions (
    id TEXT PRIMARY KEY, profile_id TEXT NOT NULL REFERENCES profiles(id),
    number INTEGER NOT NULL, name TEXT NOT NULL, config TEXT NOT NULL,
    credential_ref TEXT, created_at TEXT NOT NULL, UNIQUE(profile_id,number)
);
CREATE TRIGGER IF NOT EXISTS immutable_asset_versions BEFORE UPDATE ON asset_versions
BEGIN SELECT RAISE(ABORT,'Published versions are immutable'); END;
CREATE TABLE IF NOT EXISTS side_threads (
    id TEXT PRIMARY KEY, story_id TEXT NOT NULL REFERENCES stories(id), name TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS side_turns (
    id TEXT PRIMARY KEY, thread_id TEXT NOT NULL REFERENCES side_threads(id), question TEXT NOT NULL,
    snapshot TEXT NOT NULL, selected_reply_id TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS backup_settings (
    id INTEGER PRIMARY KEY CHECK(id=1), workspace_id TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 0, enabled INTEGER NOT NULL DEFAULT 0,
    interval_minutes INTEGER NOT NULL DEFAULT 1440, keep_count INTEGER NOT NULL DEFAULT 10,
    destination TEXT NOT NULL DEFAULT '', include_sidebar INTEGER NOT NULL DEFAULT 0,
    next_run_at TEXT, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS library_media (
  sha256 TEXT PRIMARY KEY,
  source_base64 TEXT NOT NULL,
  display_base64 TEXT NOT NULL,
  thumbnail_base64 TEXT NOT NULL,
  width INTEGER NOT NULL,
  height INTEGER NOT NULL
);
"""
WHEN = '2026-09-01T10:00:00+00:00'
PROSE = 'The lighthouse keeper read her letter twice before the storm.'
SIDEBAR = 'Should Ines forgive her brother in chapter three?'


def png(width=320, height=480, salt=b'') -> bytes:
    header = struct.pack('>II', width, height) + b'\x08\x02\x00\x00\x00'
    return b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\rIHDR' + header + b'\x00\x00\x00\x00' + salt


class Study:
    """A Study workspace folder built from the copied schema."""

    def __init__(self, root):
        self.root = root
        (root / 'data').mkdir(parents=True)
        (root / 'pyproject.toml').write_text('[project]\nname = "roleplay-interface"\nversion = "0.9.0"\n')
        self.path = root / 'data' / 'roleplay.sqlite3'
        with self.connect() as connection:
            connection.execute('PRAGMA journal_mode=WAL')
            connection.executescript(STUDY_SCHEMA)
            connection.execute("INSERT INTO stories VALUES ('story-1','Harbour','A storm',?,NULL,0,0,?,?)",
                               ('{}', WHEN, WHEN))
            connection.execute("INSERT INTO manifests VALUES ('manifest-1','story-1','[]',?)", (WHEN,))
            connection.execute("INSERT INTO nodes VALUES ('node-1','story-1',NULL,'narrator',?,'manifest-1','{}',?)",
                               (PROSE, WHEN))
            connection.execute("INSERT INTO side_threads VALUES ('side-1','story-1','Planning',?)", (WHEN,))
            connection.execute("INSERT INTO side_turns VALUES ('turn-1','side-1',?,'{}',NULL,?)", (SIDEBAR, WHEN))
            connection.execute("INSERT INTO profiles VALUES ('profile-1','pv-1',?)", (WHEN,))
            connection.execute("INSERT INTO profile_versions VALUES ('pv-1','profile-1',1,'Local',?, 'cred-ref',?)",
                               (json.dumps({'base_url': 'http://127.0.0.1:1234/v1'}), WHEN))
            connection.execute("INSERT INTO backup_settings (id, workspace_id, enabled, destination, updated_at) "
                               "VALUES (1, 'ws', 1, 'D:/Backups', ?)", (WHEN,))

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, isolation_level=None)
        try:
            yield connection
        finally:
            connection.close()

    def media(self, data: bytes) -> str:
        digest = hashlib.sha256(data).hexdigest()
        encoded = base64.b64encode(data).decode()
        with self.connect() as connection:
            connection.execute('INSERT INTO library_media VALUES (?,?,?,?,?,?)',
                               (digest, encoded, encoded, base64.b64encode(b'thumb').decode(), 320, 480))
        return digest

    def character(self, asset_id, name, content, kind='character', versions=1) -> str:
        with self.connect() as connection:
            connection.execute('INSERT INTO assets VALUES (?,?,NULL,?)', (asset_id, kind, WHEN))
        for number in range(1, versions + 1):
            self.version(asset_id, number, name, content)
        return asset_id

    def version(self, asset_id, number, name, content) -> str:
        version_id = f'{asset_id}-v{number}'
        with self.connect() as connection:
            connection.execute('INSERT INTO asset_versions VALUES (?,?,?,?,?,?,?)',
                               (version_id, asset_id, number, name, json.dumps(content), '', WHEN))
            connection.execute('UPDATE assets SET latest_version_id=? WHERE id=?', (version_id, asset_id))
        return version_id


@pytest.fixture
def study(tmp_path):
    workspace = Study(tmp_path / 'study')
    art = png()
    digest = workspace.media(art)
    workspace.art = art
    workspace.character('char-ines', 'Ines', {
        'text': 'A lighthouse keeper from Porto.', 'voice': 'Dry, quick, fond of tide charts.',
        'behavior_rules': 'Patient; never cruel.', 'pronouns': 'she/her', 'address': 'Calls you "skipper".',
        'scenario': 'The storm has cut the island off.', 'example_dialogue': '{{char}}: Tide is turning.',
        'greetings': [{'id': 'g1', 'label': 'Opening', 'text': PROSE}], 'author_notes': 'Secret plot twist.',
        'artwork_sha256': digest}, versions=2)
    workspace.character('char-other', 'Tomas', {'text': 'Her brother.'})
    workspace.character('persona-me', 'Me', {'text': 'The author.'}, kind='persona')
    workspace.character('lore-1', 'Island', {'text': 'Lore.'}, kind='lorebook')
    return workspace


def reviewed(client, study, path=None):
    response = client.post('/api/import/study/review', json={'path': str(path or study.root),
                                                              'character_id': 'char-ines'})
    assert response.status_code == 200, response.text
    return response.json()


def test_inspect_lists_only_characters(client, study):
    response = client.post('/api/import/study/inspect', json={'path': str(study.root)})
    assert response.status_code == 200, response.text
    data = response.json()
    assert [item['name'] for item in data['characters']] == ['Ines', 'Tomas']
    ines = data['characters'][0]
    assert ines['version_number'] == 2 and ines['versions'] == 2 and ines['has_artwork']
    assert data['workspace']['study_version'] == '0.9.0'
    assert data['workspace']['database'] == str(study.path)
    assert client.get('/api/companion').json()['companion'] is None


def test_review_maps_fields_and_lists_exclusions(client, study):
    review = reviewed(client, study)
    definition = review['definition']
    assert definition['name'] == 'Ines'
    assert definition['background'] == 'A lighthouse keeper from Porto.'
    assert definition['personality'] == 'Patient; never cruel.'
    assert definition['voice'] == 'Dry, quick, fond of tide charts.'
    assert definition['identity'] == 'Pronouns: she/her\nForm of address: Calls you "skipper".'
    assert definition['relationship'] == 'friendship'
    statuses = {field['source']: field['status'] for field in review['fields']}
    assert statuses['scenario'] == statuses['greetings'] == statuses['author_notes'] == 'not_imported'
    assert statuses['example_dialogue'] == 'not_imported'
    text = json.dumps(review['definition'])
    assert PROSE not in text and SIDEBAR not in text and 'Secret plot twist' not in text and 'Tomas' not in text
    items = {item['item']: item['detail'] for item in review['exclusions']}
    assert items['Story prose'].startswith('1 stories')
    assert 'Sidebar conversations' in items and 'Model credentials and connection profiles' in items
    assert 'Backup schedules and archives' in items
    assert items['Other characters and personas'].startswith('2 other')
    assert review['source'] == {'character_id': 'char-ines', 'version_id': 'char-ines-v2', 'version_number': 2,
                                'name': 'Ines', 'created_at': WHEN}
    assert review['artwork'][0]['status'] == 'included' and review['artwork'][0]['format'] == 'png'
    assert len(review['review_token']) == 64 and 'files' not in review


def test_study_database_is_opened_read_only(client, study):
    before = (study.path.read_bytes(), study.path.stat().st_mtime_ns)
    token = reviewed(client, study)['review_token']
    assert client.post('/api/import/study', json={'path': str(study.root), 'character_id': 'char-ines',
                                                  'review_token': token}).status_code == 200
    assert (study.path.read_bytes(), study.path.stat().st_mtime_ns) == before
    with open_readonly(study.path) as connection:
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("DELETE FROM nodes")
    assert (study.path.read_bytes(), study.path.stat().st_mtime_ns) == before


def test_import_creates_new_identities_and_attribution(client, study, app):
    review = reviewed(client, study)
    response = client.post('/api/import/study', json={'path': str(study.root), 'character_id': 'char-ines',
                                                      'review_token': review['review_token']})
    assert response.status_code == 200, response.text
    companion = response.json()['companion']
    study_ids = {'char-ines', 'char-ines-v1', 'char-ines-v2', review['artwork'][0]['sha256']}
    assert companion['id'] not in study_ids and companion['active_version_id'] not in study_ids
    assert companion['version']['definition']['background'] == 'A lighthouse keeper from Porto.'
    assert companion['version']['note'] == "Imported from Prospero's Study: Ines, version 2"
    record = client.get('/api/import/study').json()['imports'][0]
    assert record['source_character_id'] == 'char-ines' and record['source_version_id'] == 'char-ines-v2'
    assert record['source_version_number'] == 2 and record['study_version'] == '0.9.0'
    assert record['workspace_path'] == str(study.root) and record['imported_at']
    assert record['character_version_id'] == companion['active_version_id']
    assert record['id'] not in study_ids
    with app.state.database.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM memories').fetchone()[0] == 0
        assert connection.execute('SELECT COUNT(*) FROM messages').fetchone()[0] == 0
        dump = '\n'.join(connection.iterdump())
    assert PROSE not in dump and SIDEBAR not in dump and 'Tomas' not in dump and 'cred-ref' not in dump
    assert 'D:/Backups' not in dump and 'Secret plot twist' not in dump


def test_artwork_is_copied_into_the_reference_pictures(client, study):
    review = reviewed(client, study)
    client.post('/api/import/study', json={'path': str(study.root), 'character_id': 'char-ines',
                                           'review_token': review['review_token']})
    pictures = client.get('/api/lora/references').json()['references']
    assert len(pictures) == 1
    picture = pictures[0]
    assert picture['sha256'] == hashlib.sha256(study.art).hexdigest()
    assert picture['rights'] == 'unknown' and "Prospero's Study" in picture['source_note']
    assert picture['id'] != picture['sha256'] and not picture['missing']
    assert client.get(f"/api/lora/references/{picture['id']}/file").content == study.art


def test_damaged_or_unusable_artwork_is_excluded(client, study):
    with study.connect() as connection:
        connection.execute("UPDATE library_media SET source_base64=?", (base64.b64encode(b'tampered').decode(),))
    review = reviewed(client, study)
    assert review['artwork'][0]['status'] == 'excluded'
    assert 'checksum' in review['artwork'][0]['reason']


def test_stale_review_is_refused(client, study, app):
    token = reviewed(client, study)['review_token']
    study.version('char-ines', 3, 'Ines', {'text': 'Rewritten.'})
    response = client.post('/api/import/study', json={'path': str(study.root), 'character_id': 'char-ines',
                                                      'review_token': token})
    assert response.status_code == 409
    assert 'Review it again' in response.json()['detail']
    assert client.get('/api/companion').json()['companion'] is None


def test_existing_companion_is_not_replaced(client, study, companion):
    review = reviewed(client, study)
    assert review['companion_exists']
    response = client.post('/api/import/study', json={'path': str(study.root), 'character_id': 'char-ines',
                                                      'review_token': review['review_token']})
    assert response.status_code == 409
    assert client.get('/api/companion').json()['companion']['version']['name'] == 'Mira'
    assert client.get('/api/lora/references').json()['references'] == []


def test_database_file_path_is_accepted(client, study):
    review = reviewed(client, study, study.path)
    assert review['workspace']['path'] == str(study.root)


def test_companion_and_foreign_databases_are_refused(client, app, tmp_path):
    own = client.post('/api/import/study/inspect', json={'path': str(app.state.database.path)})
    assert own.status_code == 409
    from companion.database import Database
    other = Database(tmp_path / 'other' / 'companion.sqlite3')
    response = client.post('/api/import/study/inspect', json={'path': str(other.path)})
    assert response.status_code == 409 and 'Companion workspace' in response.json()['detail']
    plain = tmp_path / 'plain.sqlite3'
    with sqlite3.connect(plain) as connection:
        connection.execute('CREATE TABLE notes (id TEXT)')
    assert client.post('/api/import/study/inspect', json={'path': str(plain)}).status_code == 422
    junk = tmp_path / 'junk.sqlite3'
    junk.write_bytes(b'not a database at all' * 10)
    assert client.post('/api/import/study/inspect', json={'path': str(junk)}).status_code == 422
    empty = tmp_path / 'empty'
    empty.mkdir()
    assert client.post('/api/import/study/inspect', json={'path': str(empty)}).status_code == 404
    assert client.post('/api/import/study/inspect', json={'path': 'relative/path'}).status_code == 422


def test_unknown_or_non_character_items_cannot_be_reviewed(client, study):
    for character_id in ('persona-me', 'lore-1', 'missing'):
        response = client.post('/api/import/study/review', json={'path': str(study.root),
                                                                 'character_id': character_id})
        assert response.status_code == 404


def test_long_fields_are_shortened_and_marked(client, study):
    study.version('char-ines', 3, 'Ines', {'voice': 'x' * 5000})
    review = reviewed(client, study)
    assert len(review['definition']['voice']) == 4000
    assert next(field for field in review['fields'] if field['source'] == 'voice')['status'] == 'shortened'


def test_a_running_study_is_read_without_touching_its_file(client, study):
    running = sqlite3.connect(study.path, isolation_level=None)
    try:
        running.execute('INSERT INTO asset_versions VALUES (?,?,?,?,?,?,?)',
                        ('char-ines-v3', 'char-ines', 3, 'Ines', json.dumps({'text': 'Newer.'}), '', WHEN))
        running.execute("UPDATE assets SET latest_version_id='char-ines-v3' WHERE id='char-ines'")
        before = (study.path.read_bytes(), study.path.stat().st_mtime_ns)
        review = reviewed(client, study)
        assert review['source']['version_number'] == 3 and review['definition']['background'] == 'Newer.'
        assert (study.path.read_bytes(), study.path.stat().st_mtime_ns) == before
    finally:
        running.close()
