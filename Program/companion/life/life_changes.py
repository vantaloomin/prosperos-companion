"""The changes a companion's own news about their people makes to their record (Hit List #103).

companion/life/said_events.py finds "my mom just retired" in a companion's message; companion/life/happenings.py
records it through the one door for life events. These are the `apply` of the kinds only that news brings: work that
ended (retired, laid off, quit), a move (in town, away, back), health, and a baby. Each returns the undo list
`happenings.take_back` reads: records.write undos, or {'storyline_id'} / {'child_id'} for a pregnancy or a baby.
Rules only, no model.
"""
from datetime import date

from companion.clock import stamp
from companion.database import decode, encode, identifier, optional

# What the record says once their work has ended: their job in words, and the day it ended.
ENDED = {'retired': ('Retired', 'retired_on'), 'laid_off': ('Between jobs', 'left_job_on'),
         'quit': ('Between jobs', 'left_job_on')}


def made_of(row: dict) -> dict:
    return {'name': row['name'], 'role': row['role'], 'career': row['career'], 'details': decode(row['details']) or {},
            'schedule': decode(row['schedule']) or []}


def write_made(event, made: dict, extra: dict) -> list[dict]:
    """Write a person as circle_edit / circle.with_job made them: the details they changed, their career and week."""
    from companion.life import happenings, records
    before = decode(event.row['details']) or {}
    changed = {key: value for key, value in made['details'].items() if before.get(key) != value}
    gone = {key: None for key in before if key not in made['details']}
    return happenings.with_card(event, records.write(event.connection, event.row['id'], event.now,
                                                     changed | gone | extra, career=made['career'],
                                                     schedule=made['schedule']))


def work_ended(event) -> list[dict]:
    """Retired, laid off or quit: no employer, their week without work (a retired week; nothing out of town)."""
    from companion.life import circle
    shown, key = ENDED[event.kind]
    made = circle.with_job(made_of(event.row), shown, None, '', f"{event.row['seed']}:{event.source}")
    return write_made(event, made, {key: event.day})


def moved(event) -> list[dict]:
    """A new home: in town, a neighborhood they named or one the city picks for them; away, the place they went;
    back, a home in town again. Someone out of town who moved where they live only gets the day they moved."""
    from companion.life import circle_edit, happenings
    place, seed = (event.given or {}).get('place') or '', f"{event.row['seed']}:{event.source}"
    was_local = (decode(event.row['details']) or {}).get('local', True) is not False
    local = {'moved_back': True, 'moved_away': False, 'moved_away_to': False}.get(event.kind, was_local)
    data, made = happenings.city(event), made_of(event.row)
    if local and data:
        made = circle_edit.move(made, True, data, seed)
    elif not local and (was_local or place):
        made = circle_edit.move(made, False, data, seed)
        made['details']['city'] = place
    if event.kind == 'moved_to' and place:
        made['details']['neighborhood'] = place
    if local != was_local:
        made = circle_edit.new_job(made, {}, data, seed)
    return write_made(event, made, {'moved_on': event.day})


def unwell(event) -> list[dict]:
    """In hospital, after surgery, hurt, ill or diagnosed: what it is and since when; a diagnosis means treatment."""
    from companion.life import happenings, records
    found = {'health': {'what': event.kind, 'since': event.day}}
    if event.kind == 'diagnosed':
        found['in_treatment_since'] = event.day
    return happenings.listed(records.write(event.connection, event.row['id'], event.now, found))


def recovered(event) -> list[dict]:
    from companion.life import happenings, records
    return happenings.listed(records.write(event.connection, event.row['id'], event.now,
                                           {'health': None, 'in_treatment_since': None}))


def expecting(event) -> list[dict]:
    """A pregnancy as the families module runs one (companion/life/families.py): its storyline, the baby due later.
    The companion gave its news themselves, so they do not text it again as a first message (storylines.fresh_beats)."""
    from companion.life import families
    how = families.kinship(event.row) or 'friend'
    storyline_id = families.begin(event.connection, event.companion, None, event.row, how,
                                  date.fromisoformat(event.day), event.now)
    row = optional(event.connection, 'SELECT stages FROM storylines WHERE id=?', (storyline_id,))
    stages = decode(row['stages'])
    stages[0]['told'] = 'said'
    event.connection.execute('UPDATE storylines SET stages=? WHERE id=?', (encode(stages), storyline_id))
    return [{'storyline_id': storyline_id}]


def had_baby(event) -> list[dict]:
    """A baby born that day, with the name and sex the companion gave when they did, else as families would pick."""
    from companion.life import families
    from companion.world.generators import unit
    given, row = event.given or {}, event.row
    seed = f"family:{event.companion['active_timeline_id']}:{row['id']}:{event.day}"
    pronouns = given.get('pronouns') or ('she/her' if unit(seed, 'sex') < 0.49 else 'he/him')
    name = given.get('child') or families.baby_name(event.companion['version']['definition'], None, seed, pronouns,
                                                    families.taken_names(event.connection, event.companion))
    title = families.title(families.kinship(row) or 'friend', seed)
    child_id = identifier()
    event.connection.execute(
        'INSERT INTO circle_children (id, timeline_id, parent_id, storyline_id, name, pronouns, title, born_on, status, '
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'born', ?, ?)",
        (child_id, event.companion['active_timeline_id'], row['id'], event.source, name, pronouns, title, event.day,
         stamp(event.now), stamp(event.now)))
    event.names['child'] = name
    return [{'child_id': child_id}]


def undo(connection, item: dict) -> bool:
    """Take back a pregnancy or a baby this module made: True when `item` was one."""
    if item.get('storyline_id'):
        connection.execute('DELETE FROM circle_children WHERE storyline_id=?', (item['storyline_id'],))
        connection.execute('DELETE FROM storylines WHERE id=?', (item['storyline_id'],))
        return True
    if item.get('child_id'):
        connection.execute('DELETE FROM circle_children WHERE id=?', (item['child_id'],))
        return True
    return False
