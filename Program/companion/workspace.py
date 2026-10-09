"""Workspace settings, permission revisions and pause (PRD T6, M7)."""
from companion import local_zone, notifications
from companion.clock import zone
from companion.database import identifier, optional, settings
from companion.errors import require

FLAGS = ('automatic_memory', 'sensitive_memory', 'share_profile_across_timelines', 'background_activity',
         'model_memory_suggestions', 'chat_sounds', 'chat_retro_dark', 'ask_about_people',
         'story_mode', 'show_secret_slips', 'show_moods', 'show_news', 'show_odds')
# Changing any of these can make queued work stale, so they advance the permission revision.
PERMISSIONS = {'automatic_memory', 'sensitive_memory', 'background_activity', 'model_memory_suggestions'}


def view(row: dict) -> dict:
    return {**row, **{flag: bool(row[flag]) for flag in FLAGS},
            'paused': row['paused_at'] is not None, 'review_required': bool(row['review_required']),
            'ai_notice_confirmed': row['ai_notice_at'] is not None,
            'system_timezone': local_zone.detect()}


def follows_pc(row: dict) -> bool:
    """A zone the user picked is never replaced; the untouched UTC default and a PC-set zone are."""
    return row['user_timezone_source'] == 'pc' or (row['user_timezone_source'] == 'default'
                                                    and row['user_timezone'] == 'UTC')


def timezone_change(row: dict, changes: dict):
    """Turns the requested zone and its source into columns. 'detected' is the interface reporting the PC's
    zone on its own, so it only applies while the workspace follows the PC; 'pc' is the user asking for it."""
    source = changes.pop('user_timezone_source', None)
    if 'user_timezone' not in changes:
        return
    zone(changes['user_timezone'])
    if source == 'detected' and not follows_pc(row):
        del changes['user_timezone']
        return
    changes['user_timezone_source'] = 'chosen' if source in (None, 'chosen') else 'pc'


def adopt_pc_timezone(database, detected: str | None):
    """At startup, a workspace still on the UTC default (or following the PC) takes this PC's zone."""
    if not detected:
        return
    with database.connect(write=True) as connection:
        row = settings(connection)
        if follows_pc(row) and (row['user_timezone'], row['user_timezone_source']) != (detected, 'pc'):
            connection.execute("UPDATE workspace_settings SET user_timezone=?, user_timezone_source='pc', "
                               'updated_at=? WHERE id=1', (detected, database.now()))


def read(database) -> dict:
    with database.connect() as connection:
        return view(settings(connection))


def update(database, body) -> dict:
    changes = body.model_dump(exclude_none=True)
    with database.connect(write=True) as connection:
        row = settings(connection)
        timezone_change(row, changes)
        review_done = changes.pop('review_complete', False)
        # The first-run notice is confirmed once and stays confirmed.
        if changes.pop('ai_notice_confirmed', False) and row['ai_notice_at'] is None:
            changes['ai_notice_at'] = database.now()
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
        if 'share_profile_across_timelines' in changed:
            # What the next reply may know changed, so a reply already being written is withheld (M9).
            assignments['memory_revision'] = row['memory_revision'] + 1
        columns = ', '.join(f'{key}=?' for key in assignments)
        connection.execute(f'UPDATE workspace_settings SET {columns} WHERE id=1', tuple(assignments.values()))
        if changed.get('background_activity') is False:
            # Revoking background permission applies to queued notifications as well.
            notifications.cancel_queued(connection, assignments['updated_at'], 'Background activity was turned off.')
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
