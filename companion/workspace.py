"""Workspace settings, permission revisions and pause (PRD T6, M7)."""
from companion.clock import zone
from companion.database import identifier, optional, settings
from companion.errors import require

FLAGS = ('automatic_memory', 'sensitive_memory', 'share_profile_across_timelines', 'background_activity')
# Changing any of these can make queued work stale, so they advance the permission revision.
PERMISSIONS = {'automatic_memory', 'sensitive_memory', 'background_activity'}


def view(row: dict) -> dict:
    return {**row, **{flag: bool(row[flag]) for flag in FLAGS},
            'paused': row['paused_at'] is not None, 'review_required': bool(row['review_required'])}


def read(database) -> dict:
    with database.connect() as connection:
        return view(settings(connection))


def update(database, body) -> dict:
    changes = body.model_dump(exclude_none=True)
    if 'user_timezone' in changes:
        zone(changes['user_timezone'])
    with database.connect(write=True) as connection:
        row = settings(connection)
        review_done = changes.pop('review_complete', False)
        changed = {key: value for key, value in changes.items() if row[key] != value}
        enabling = any(changed.get(key) is True for key in PERMISSIONS)
        require(not (enabling and row['review_required'] and not review_done),
                'Review the restored workspace before enabling memory or background activity.', 409)
        assignments = {**{key: int(value) if isinstance(value, bool) else value for key, value in changed.items()},
                       'updated_at': database.now()}
        if review_done:
            assignments['review_required'] = 0
        if PERMISSIONS & changed.keys():
            assignments['permission_revision'] = row['permission_revision'] + 1
        columns = ', '.join(f'{key}=?' for key in assignments)
        connection.execute(f'UPDATE workspace_settings SET {columns} WHERE id=1', tuple(assignments.values()))
        return view(settings(connection))


def pause(database) -> dict:
    with database.connect(write=True) as connection:
        if settings(connection)['paused_at'] is None:
            timestamp = database.now()
            connection.execute('UPDATE workspace_settings SET paused_at=?, permission_revision=permission_revision+1, '
                               'updated_at=? WHERE id=1', (timestamp, timestamp))
            connection.execute('INSERT INTO pauses (id, started_at) VALUES (?, ?)', (identifier(), timestamp))
        return view(settings(connection))


def resume(database) -> dict:
    """Resuming skips the paused interval; nothing is generated for it automatically."""
    with database.connect(write=True) as connection:
        if settings(connection)['paused_at'] is not None:
            timestamp = database.now()
            connection.execute('UPDATE workspace_settings SET paused_at=NULL, permission_revision=permission_revision+1, '
                               'updated_at=? WHERE id=1', (timestamp,))
            connection.execute('UPDATE pauses SET ended_at=? WHERE ended_at IS NULL', (timestamp,))
        return view(settings(connection))


def overlapping_pause(connection, starts_at: str, ends_at: str) -> dict | None:
    """A pause the user deliberately caught up (T6) no longer blocks its interval."""
    return optional(connection, 'SELECT * FROM pauses WHERE started_at < ? AND COALESCE(ended_at, ?) > ? '
                    'AND id NOT IN (SELECT pause_id FROM pause_catch_ups) LIMIT 1', (ends_at, ends_at, starts_at))
