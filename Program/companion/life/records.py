"""Changes a life event makes to a circle person's row, and taking them back (companion/life/happenings.py).

`write` changes some keys of `details` and some columns, and returns the undo: what each key and column was before
and the row as it was written. `restore` puts it back: byte for byte when nothing else changed the row since, else
only the keys and columns this change touched, so a later edit by the user or another event stays.
"""
from companion.clock import stamp
from companion.database import decode, encode, optional

COLUMNS = ('role', 'career', 'schedule')
# A details key the row did not have before the change.
ABSENT = '\x00absent'


def write(connection, person_id: str, now, details: dict | None = None, **columns) -> dict | None:
    """Set `details` keys (None removes one) and columns ('schedule' as a list) on a circle row. The undo, or None
    when nothing changed."""
    row = optional(connection, 'SELECT * FROM circle_people WHERE id=?', (person_id,))
    if row is None:
        return None
    found = decode(row['details']) or {}
    changed = dict(found)
    for key, value in (details or {}).items():
        if value is None:
            changed.pop(key, None)
        else:
            changed[key] = value
    values = {column: encode(value) if column == 'schedule' else value for column, value in columns.items()}
    after = {'details': encode(changed), **{column: values.get(column, row[column]) for column in COLUMNS}}
    before = {'details': row['details'], **{column: row[column] for column in COLUMNS}}
    if after == before:
        return None
    connection.execute('UPDATE circle_people SET details=?, role=?, career=?, schedule=?, revision=revision+1, '
                       'updated_at=? WHERE id=?', (after['details'], after['role'], after['career'], after['schedule'],
                                                   stamp(now), person_id))
    return {'id': person_id, 'before': before, 'after': after,
            'keys': {key: found.get(key, ABSENT) for key in details or {}}, 'columns': sorted(columns),
            'schedule': 'schedule' in columns and values['schedule'] != row['schedule']}


def restore(connection, undo: dict, now) -> bool:
    """Put a row back as `write` found it. Returns whether its schedule changed back."""
    row = optional(connection, 'SELECT * FROM circle_people WHERE id=?', (undo['id'],))
    if row is None:
        return False
    current = {'details': row['details'], **{column: row[column] for column in COLUMNS}}
    if current == undo['after']:
        back = undo['before']
    else:
        details = decode(row['details']) or {}
        for key, value in undo['keys'].items():
            if value == ABSENT:
                details.pop(key, None)
            else:
                details[key] = value
        back = {**current, 'details': encode(details), **{column: undo['before'][column] for column in undo['columns']}}
    connection.execute('UPDATE circle_people SET details=?, role=?, career=?, schedule=?, revision=revision+1, '
                       'updated_at=? WHERE id=?', (back['details'], back['role'], back['career'], back['schedule'],
                                                   stamp(now), undo['id']))
    return back['schedule'] != row['schedule']
