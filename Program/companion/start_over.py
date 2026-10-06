"""Starting over with the same companion, or deleting the companion altogether.

Both take a verified backup first (with reference pictures), so either can be undone by restoring
it from Settings > Backups; the backup's name says which it came before. The user confirms by
typing the companion's name.

Every table in the schema is in exactly one group below (tests/test_start_over.py checks this):

- WORKSPACE stays through both: settings, model connections, image backends, lookup services,
  cities and the user's changes to them, notification and phone setup. Deletion markers stay too, so a restore still honours them.
- CHARACTER is who the companion is: the companion, every version of the character, and their
  look (reference pictures, adapters, training and test pictures). Starting over keeps it;
  deleting removes it.
- HISTORY is everything that happened: every timeline with its chats, memories, life, feed,
  circle, home, closeness, the people the user mentioned and the real-world lookups made for them. Both remove it.

There is one companion per workspace, so a group is cleared whole. Starting over then gives the
companion a fresh active timeline that begins now, as a newly created companion has.
"""
import shutil
import sqlite3
from pathlib import Path

from companion import backup
from companion.characters import require_current
from companion.database import identifier, many
from companion.errors import require

WORKSPACE = (
    'app_identity', 'workspace_settings', 'pauses', 'pause_catch_ups', 'connection', 'model_profiles',
    'model_routes', 'life_settings', 'world_cities', 'world_changes', 'world_change_dismissals', 'image_settings',
    'image_backends', 'context_settings', 'context_services', 'context_tools', 'lora_settings', 'notification_settings', 'notification_deliveries', 'prompt_overrides', 'phone_settings',
    'phone_devices', 'phone_push', 'deletion_markers', 'debug_time', 'sqlite_sequence',
)
# Children before parents, so the order also reads as what depends on what.
CHARACTER = (
    'lora_eval_images', 'lora_evaluations', 'lora_gen_images', 'lora_generations', 'appearance_current',
    'appearance_versions', 'lora_adapters', 'lora_references', 'lora_runs', 'study_imports', 'character_versions',
    'companions',
)
# Lookups were made for the companion's replies and city, so they go with the history. City news
# drawn from them (world_changes with origin 'real') goes with them by ON DELETE CASCADE; changes
# the user made to a city stay.
HISTORY = (
    'context_uses', 'context_observations', 'notifications', 'chat_photos', 'message_social_links', 'social_posts', 'message_post_links',
    'feed_post_events', 'image_jobs', 'feed_posts', 'memory_sources', 'memory_declines', 'memory_jobs',
    'memory_candidates', 'memory_vectors', 'memory_summaries', 'memory_proposals', 'memory_activity',
    'closeness_jokes', 'closeness_settings', 'openers', 'self_facts', 'recommendations', 'storylines',
    'storyline_days', 'home_log', 'home_items', 'home_state', 'townsfolk_encounters', 'acquaintances', 'circle_people', 'life_agenda',
    'agenda_cursors', 'relationship_moods', 'visits', 'life_runs', 'life_cursors', 'memories', 'life_events',
    'user_people', 'messages', 'timelines',
)
# LoRA folders the backup does not carry: training runs and the test and prepared pictures.
UNBACKED_LORA = ('runs', 'evaluations', 'generated')


def preview(database) -> dict:
    """What starting over or deleting would remove, for the confirmation."""
    with database.connect() as connection:
        companion = require_current(connection)

        def count(sql):
            return connection.execute(sql).fetchone()[0]

        return {
            'name': companion['version']['name'],
            'messages': count("SELECT COUNT(*) FROM messages WHERE role='user' AND redacted_at IS NULL"),
            'memories': count("SELECT COUNT(*) FROM memories WHERE status='active'"),
            'timelines': count('SELECT COUNT(*) FROM timelines'),
            'images': count("SELECT COUNT(*) FROM image_jobs WHERE status='completed'"),
            'versions': count('SELECT COUNT(*) FROM character_versions'),
            'adapters': count('SELECT COUNT(*) FROM lora_adapters WHERE removed_at IS NULL'),
            'references': count('SELECT COUNT(*) FROM lora_references'),
            'training': count("SELECT COUNT(*) FROM lora_runs WHERE status='running'") > 0,
        }


def confirmed(database, typed: str) -> dict:
    current = preview(database)
    require(typed.strip().casefold() == current['name'].strip().casefold(),
            f"Type {current['name']} to confirm.", 422)
    return current


def take_backup(database, kind: str) -> dict:
    """A full backup, reference pictures included; archive() reads it back and checks every digest."""
    created_at = database.now()
    name = f"before-{kind}-{created_at[:19].replace(':', '').replace('-', '')}.zip"
    made = backup.archive(database.path, database.path.parent / 'backups' / name, created_at,
                          include_datasets=True)
    return {'name': name, 'path': made['path']}


def clear(connection, tables):
    for table in tables:
        connection.execute(f'DELETE FROM {table}')  # noqa: S608 - names come from the constants above


def image_files(connection) -> list[str]:
    rows = many(connection, 'SELECT output_file, raw_file FROM image_jobs')
    return [f'images/{row["output_file"]}' for row in rows if row['output_file']] + \
        [f'images/raw/{row["raw_file"]}' for row in rows if row['raw_file']]


def wipe(database, keep_character: bool) -> tuple[list[str], list[str]]:
    """Clear the groups in one transaction. Returns reply attempts still being written, to stop, and
    the workspace files the cleared records named."""
    with database.connect(write=True) as connection:
        # Checked at commit, so a kept row still pointing at a cleared one fails the whole change.
        connection.execute('PRAGMA defer_foreign_keys=ON')
        companion = require_current(connection)
        streaming = [row['id'] for row in many(connection, "SELECT id FROM messages WHERE status='streaming'")]
        files = image_files(connection)
        clear(connection, HISTORY)
        if keep_character:
            timestamp, timeline_id = database.now(), identifier()
            connection.execute("INSERT INTO timelines (id, companion_id, status, created_at) VALUES (?, ?, 'active', ?)",
                               (timeline_id, companion['id'], timestamp))
            connection.execute('UPDATE companions SET active_timeline_id=? WHERE id=?', (timeline_id, companion['id']))
        else:
            clear(connection, CHARACTER)
        # Work queued or running for what was cleared is revalidated and dropped (T7, M9).
        connection.execute('UPDATE workspace_settings SET permission_revision=permission_revision+1, '
                           'memory_revision=memory_revision+1, updated_at=? WHERE id=1', (database.now(),))
    return streaming, files


def remove_files(workspace: Path, names: list[str], folders: tuple[str, ...] = ()):
    for name in names:
        (workspace / name).unlink(missing_ok=True)
    for folder in folders:
        shutil.rmtree(workspace / folder, ignore_errors=True)


def compact(database):
    """Cleared rows can linger in free pages of the database file until it is rewritten."""
    connection = sqlite3.connect(database.path, timeout=15)
    try:
        connection.execute('VACUUM')
        connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    except sqlite3.OperationalError:
        pass  # Busy: the space is reused by later writes and the next backup copies only live rows.
    finally:
        connection.close()


def start_over(database, typed: str) -> dict:
    """Same character, fresh history: their look and every character version stay."""
    confirmed(database, typed)
    made = take_backup(database, 'reset')
    streaming, files = wipe(database, keep_character=True)
    remove_files(database.path.parent, files)
    compact(database)
    return {'backup': made, 'stopped_reply_ids': streaming}


def delete(database, typed: str) -> dict:
    """The companion and everything about them; the workspace's own setup stays."""
    current = confirmed(database, typed)
    require(not current['training'], 'An adapter is training for this companion. Stop it first.', 409)
    made = take_backup(database, 'delete')
    streaming, _files = wipe(database, keep_character=False)
    remove_files(database.path.parent, [], ('images', *(f'lora/{name}' for name in
                                                        ('adapters', 'references', *UNBACKED_LORA))))
    compact(database)
    return {'backup': made, 'stopped_reply_ids': streaming}
