"""Starting over with the same companion, or deleting the companion altogether.

Both take a verified backup first (with reference pictures), so either can be undone by restoring
it from Settings > Backups; the backup's name says which it came before. The user confirms by
typing the companion's name.

Every table in the schema is in exactly one group below (tests/test_start_over.py checks this):

- WORKSPACE stays through both: settings, model connections, image backends, lookup services,
  cities and the user's changes to them, notification and phone setup, the user's own story (Story mode,
  apart from every companion) and group chats (the companion leaves each one; their old lines stay).
  Deletion markers stay too, so a restore still honours them.
- CHARACTER is who the companion is: the companion, every version of the character, and their
  look (reference pictures, adapters, training and test pictures). Starting over keeps it;
  deleting removes it.
- HISTORY is everything that happened: every timeline with its chats, memories, life, feed,
  circle, home, closeness, the people the user mentioned and the real-world lookups made for them. Both remove it.

With one companion in the workspace, a group is cleared whole. When the user has switched main
characters (companion/cast.py), only the main character's rows go: those on their timelines, or naming
them, or hanging off those (OWN says how each table finds its rows). Lookups stay then, being about the
city the companions share. Deleting the main character then brings back whoever stepped back most recently.
Starting over gives the companion a fresh active timeline that begins now, as a newly created companion has.
"""
import shutil
import sqlite3
from pathlib import Path

from companion import backup, groups, pictures
from companion.characters import require_current
from companion.database import identifier, many
from companion.errors import require

WORKSPACE = (
    'app_identity', 'workspace_settings', 'pauses', 'pause_catch_ups', 'connection', 'model_profiles',
    'model_routes', 'life_settings', 'world_cities', 'world_changes', 'world_change_dismissals', 'image_settings',
    'image_backends', 'context_settings', 'context_services', 'context_tools', 'lora_settings', 'notification_settings', 'notification_deliveries', 'prompt_overrides', 'phone_settings',
    'phone_devices', 'phone_push', 'deletion_markers', 'debug_time', 'builtin_recall', 'story_scene', 'story_messages', 'story_people', 'dating_profile', 'dating_swipes', 'dating_dates', 'dating_photos',
    'group_moments', 'group_chats', 'group_members', 'group_messages', 'pair_backstories',
    'sqlite_sequence',
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
    'closeness_jokes', 'closeness_settings', 'openers', 'self_fact_jobs', 'self_facts', 'companion_plans', 'recommendations', 'storylines',
    'storyline_days', 'home_log', 'home_items', 'home_state', 'wardrobe_log', 'wardrobe_items', 'wardrobe_state', 'townsfolk_encounters', 'acquaintances', 'circle_people', 'life_agenda',
    'agenda_cursors', 'relationship_moods', 'visits', 'life_runs', 'life_cursors', 'memories', 'life_events',
    'user_people', 'message_pictures', 'message_edits', 'chat_reads', 'away_messages', 'messages', 'timelines',
)
# LoRA folders the backup does not carry: training runs and the test and prepared pictures.
UNBACKED_LORA = ('runs', 'evaluations', 'generated')

# One companion's rows, as temporary tables built before anything is cleared.
SCOPE = (
    ('gone_timelines', 'SELECT id FROM timelines WHERE companion_id=:companion'),
    ('gone_messages', 'SELECT id FROM messages WHERE timeline_id IN gone_timelines'),
    ('gone_memories', 'SELECT id FROM memories WHERE timeline_id IN gone_timelines'),
    ('gone_storylines', 'SELECT id FROM storylines WHERE timeline_id IN gone_timelines'),
    ('gone_candidates', 'SELECT id FROM memory_candidates WHERE timeline_id IN gone_timelines'),
    ('gone_posts', 'SELECT id FROM feed_posts WHERE timeline_id IN gone_timelines'),
    ('gone_social', 'SELECT id FROM social_posts WHERE timeline_id IN gone_timelines'),
    ('gone_events', 'SELECT id FROM life_events WHERE timeline_id IN gone_timelines'),
    ('gone_jobs', 'SELECT id FROM image_jobs WHERE timeline_id IN gone_timelines'),
    ('gone_evaluations', 'SELECT id FROM lora_evaluations WHERE companion_id=:companion'),
    ('gone_generations', 'SELECT id FROM lora_generations WHERE companion_id=:companion'),
)
# How a table without its own timeline or companion column finds one companion's rows; None keeps them.
OWN = {
    'context_uses': 'message_id IN gone_messages',
    'context_observations': None,
    'notifications': 'post_id IN gone_posts',
    'chat_photos': 'message_id IN gone_messages OR post_id IN gone_posts OR job_id IN gone_jobs',
    'message_social_links': 'message_id IN gone_messages OR post_id IN gone_social',
    'message_post_links': 'message_id IN gone_messages OR post_id IN gone_posts',
    'feed_post_events': 'post_id IN gone_posts OR event_id IN gone_events',
    'memory_sources': 'message_id IN gone_messages OR memory_id IN gone_memories',
    'memory_declines': 'message_id IN gone_messages',
    'message_pictures': 'message_id IN gone_messages',
    'message_edits': 'message_id IN gone_messages',
    'memory_jobs': 'message_id IN gone_messages',
    'self_fact_jobs': 'message_id IN gone_messages',
    'memory_vectors': 'owner_id IN gone_messages OR owner_id IN gone_memories OR owner_id IN gone_storylines',
    'memory_proposals': 'keep_id IN gone_memories OR merge_id IN gone_memories',
    'memory_activity': 'memory_id IN gone_memories OR message_id IN gone_messages OR candidate_id IN gone_candidates',
    'lora_eval_images': 'evaluation_id IN gone_evaluations',
    'lora_gen_images': 'generation_id IN gone_generations',
    'chat_reads': 'thread_id IN gone_timelines',
    'away_messages': 'message_id IN gone_messages',
    'companions': 'id=:companion',
}


def preview(database) -> dict:
    """What starting over or deleting would remove, for the confirmation."""
    with database.connect() as connection:
        companion = require_current(connection)
        mine = 'timeline_id IN (SELECT id FROM timelines WHERE companion_id=:companion)'

        def count(sql):
            return connection.execute(sql, {'companion': companion['id']}).fetchone()[0]

        others = others_of(connection, companion['id'])
        return {
            'name': companion['version']['name'],
            # Both sides of the chat, each message once even when a fork copied it.
            'messages': count(
                'SELECT COUNT(DISTINCT COALESCE(origin_id, id)) FROM messages '
                f"WHERE redacted_at IS NULL AND status NOT IN ('failed', 'streaming') AND {mine}"
            ),
            'memories': count(f"SELECT COUNT(*) FROM memories WHERE status='active' AND {mine}"),
            'timelines': count('SELECT COUNT(*) FROM timelines WHERE companion_id=:companion'),
            'images': count(f"SELECT COUNT(*) FROM image_jobs WHERE status='completed' AND {mine}"),
            'versions': count('SELECT COUNT(*) FROM character_versions WHERE companion_id=:companion'),
            'adapters': count('SELECT COUNT(*) FROM lora_adapters WHERE removed_at IS NULL AND companion_id=:companion'),
            'references': count('SELECT COUNT(*) FROM lora_references WHERE companion_id=:companion'),
            'training': count("SELECT COUNT(*) FROM lora_runs WHERE status='running' AND companion_id=:companion") > 0,
            # Other companions stay; deleting brings back the first of them.
            'others': [row['name'] for row in others],
        }


def others_of(connection, companion_id: str) -> list[dict]:
    """The companions who stepped back, most recently first."""
    return many(connection, 'SELECT c.id, v.name FROM companions c JOIN character_versions v ON '
                'v.id=c.active_version_id WHERE c.id!=? ORDER BY c.stepped_back_at DESC', (companion_id,))


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


def clear_own(connection, tables, companion_id: str):
    """Only this companion's rows of each table, children before parents."""
    values = {'companion': companion_id}
    for name, select in SCOPE:
        connection.execute(f'CREATE TEMP TABLE {name} AS {select}', values)
    try:
        for table in tables:
            columns = {row[1] for row in connection.execute(f'PRAGMA table_info({table})')}
            where = OWN[table] if table in OWN else 'timeline_id IN gone_timelines' if 'timeline_id' in columns \
                else 'companion_id=:companion'
            if where:
                connection.execute(f'DELETE FROM {table} WHERE {where}', values)  # noqa: S608 - from the constants above
    finally:
        for name, _select in SCOPE:
            connection.execute(f'DROP TABLE temp.{name}')


def image_files(connection, companion_id: str | None = None) -> list[str]:
    mine = ' WHERE timeline_id IN (SELECT id FROM timelines WHERE companion_id=?)' if companion_id else ''
    rows = many(connection, f'SELECT output_file, raw_file FROM image_jobs{mine}', (companion_id,) if companion_id else ())
    return [f'images/{row["output_file"]}' for row in rows if row['output_file']] + \
        [f'images/raw/{row["raw_file"]}' for row in rows if row['raw_file']] + pictures.files_of(connection, companion_id)


def lora_files(connection, companion_id: str) -> tuple[list[str], list[str]]:
    """One companion's LoRA files and run folders, when the others' must stay."""
    values = (companion_id,)
    names = [f"lora/adapters/{row['file']}" for row in many(
        connection, 'SELECT file FROM lora_adapters WHERE companion_id=?', values)]
    for row in many(connection, 'SELECT file, crop_file FROM lora_references WHERE companion_id=?', values):
        names += [f'lora/references/{name}' for name in (row['file'], row['crop_file']) if name]
    names += [f"lora/generated/{row['output_file']}" for row in many(
        connection, 'SELECT i.output_file FROM lora_gen_images i JOIN lora_generations g ON g.id=i.generation_id '
        'WHERE g.companion_id=? AND i.output_file IS NOT NULL', values)]
    names += [f"lora/evaluations/{row['output_file']}" for row in many(
        connection, 'SELECT i.output_file FROM lora_eval_images i JOIN lora_evaluations e ON e.id=i.evaluation_id '
        'WHERE e.companion_id=? AND i.output_file IS NOT NULL', values)]
    folders = [f"lora/runs/{row['folder']}" for row in many(
        connection, 'SELECT folder FROM lora_runs WHERE companion_id=?', values) if row['folder']]
    return names, folders


def wipe(database, keep_character: bool) -> tuple[list[str], list[str], list[str] | None]:
    """Clear the groups in one transaction. Returns reply attempts still being written, to stop, the
    workspace files the cleared records named, and with other companions in the workspace, the LoRA
    folders that were only this companion's (else None: every LoRA folder goes)."""
    with database.connect(write=True) as connection:
        # Checked at commit, so a kept row still pointing at a cleared one fails the whole change.
        connection.execute('PRAGMA defer_foreign_keys=ON')
        companion = require_current(connection)
        groups.leave_everywhere(connection, companion['id'], database.now())
        others = others_of(connection, companion['id'])
        if others:
            return wipe_own(database, connection, companion, others, keep_character)
        streaming = [row['id'] for row in many(connection, "SELECT id FROM messages WHERE status='streaming'")]
        files = image_files(connection)
        clear(connection, HISTORY)
        if keep_character:
            fresh_timeline(connection, database.now(), companion['id'])
        else:
            clear(connection, CHARACTER)
        revalidate(connection, database.now())
    return streaming, files, None


def wipe_own(database, connection, companion: dict, others: list[dict], keep_character: bool):
    """`wipe` for the main character alone, when other companions share the workspace."""
    streaming = [row['id'] for row in many(
        connection, "SELECT id FROM messages WHERE status='streaming' AND timeline_id IN "
        '(SELECT id FROM timelines WHERE companion_id=?)', (companion['id'],))]
    files, folders = image_files(connection, companion['id']), []
    if not keep_character:
        names, folders = lora_files(connection, companion['id'])
        files += names
    clear_own(connection, HISTORY + (() if keep_character else CHARACTER), companion['id'])
    if keep_character:
        fresh_timeline(connection, database.now(), companion['id'])
    else:
        connection.execute('UPDATE companions SET slot=1, stepped_back_at=NULL WHERE id=?', (others[0]['id'],))
    revalidate(connection, database.now())
    return streaming, files, folders


def fresh_timeline(connection, timestamp: str, companion_id: str):
    timeline_id = identifier()
    connection.execute("INSERT INTO timelines (id, companion_id, status, created_at) VALUES (?, ?, 'active', ?)",
                       (timeline_id, companion_id, timestamp))
    connection.execute('UPDATE companions SET active_timeline_id=? WHERE id=?', (timeline_id, companion_id))


def revalidate(connection, timestamp: str):
    """Work queued or running for what was cleared is revalidated and dropped (T7, M9)."""
    connection.execute('UPDATE workspace_settings SET permission_revision=permission_revision+1, '
                       'memory_revision=memory_revision+1, updated_at=? WHERE id=1', (timestamp,))


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
    streaming, files, _folders = wipe(database, keep_character=True)
    remove_files(database.path.parent, files)
    compact(database)
    return {'backup': made, 'stopped_reply_ids': streaming}


def delete(database, typed: str) -> dict:
    """The companion and everything about them; the workspace's own setup stays."""
    current = confirmed(database, typed)
    require(not current['training'], 'An adapter is training for this companion. Stop it first.', 409)
    made = take_backup(database, 'delete')
    streaming, files, folders = wipe(database, keep_character=False)
    if folders is None:
        remove_files(database.path.parent, [], ('images', pictures.FOLDER, *(f'lora/{name}' for name in
                                                            ('adapters', 'references', *UNBACKED_LORA))))
    else:
        remove_files(database.path.parent, files, tuple(folders))
    compact(database)
    return {'backup': made, 'stopped_reply_ids': streaming}
