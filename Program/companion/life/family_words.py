"""The family line in chat (companion/life/family_tree.py): what the people list alone doesn't say about their family.

"- Your family: Your parents divorced when you were 9. Your dad married Karen (your stepmom) when you were 12. Your
mom Ruth died when you were 14. You don't talk to your dad Frank anymore." It reads the circle as it is now, so a
name the user changed, someone they brought back, or the sheet's own mom in the plan's place reads as they are.
"""
from companion.database import decode
from companion.life import circle


def rows_by_plan(connection, timeline_id: str) -> dict[str, dict]:
    """The circle's people by their place in the family plan, with their details."""
    found = {}
    for row in circle.people(connection, timeline_id, include_removed=True):
        details = decode(row['details']) or {}
        if kin := details.get('kin'):
            found[kin['id']] = {'name': row['name'], 'role': row['role'], 'status': row['status'], **details}
    return found


def parents_text(tree: dict, rows: dict[str, dict], say, older: bool) -> list[str]:
    """How their parents stand, in a sentence or two."""
    parents = [rows[key] for key in ('p1', 'p2') if key in rows]
    names = ' and '.join(person['name'] for person in parents)
    if tree['story'] == 'same_sex' and len(parents) == 2:
        word = say('mom') + 's' if parents[0].get('pronouns') == 'she/her' else say('dad') + 's'
        return [f"You have two {word}, {names}" + (', who adopted you as a baby.' if tree['adopted'] else '.')]
    if tree['story'] == 'adopted':
        return [f'{names} adopted you as a baby.' if names else 'You were adopted as a baby.']
    if tree['story'] == 'single' and parents:
        other = say('dad') if tree['absent'] == 'he/him' else say('mom')
        return [f"Your {say(parents[0]['role'])} {parents[0]['name']} raised you on your own; your {other} was "
                'never in the picture.']
    if tree['story'] == 'split':
        return [f"Your parents {'separated' if older else 'divorced'} when you were {tree['split_at']}.",
                *remarried_text(tree, rows, say)]
    alive = [person for person in parents if not person.get('late')]
    return ['Your parents are still married.'] if len(alive) == 2 else []


def remarried_text(tree: dict, rows: dict[str, dict], say) -> list[str]:
    found = []
    for item in tree['people']:
        step, partner = rows.get(item['id']), rows.get(item.get('partner') or '')
        if item['step'] and step and partner:
            found.append(f"Your {say(partner['role'])} married {step['name']} (your {say(step['role'])}) when you "
                         f"were {item['remarried_at']}.")
    return found


def gone_text(rows: dict[str, dict], say) -> list[str]:
    """Who died before now, and whom they don't talk to."""
    found = []
    for person in rows.values():
        if person.get('late') and person.get('long_ago') is not None:
            found.append(f"Your {say(person['role'])} {person['name']} died when you were {person['long_ago']}.")
        elif person['status'] == 'removed' and person.get('estranged'):
            found.append(f"You don't talk to your {say(person['role'])} {person['name']} anymore.")
    return found


def siblings_text(tree: dict, rows: dict[str, dict]) -> list[str]:
    grown = [person for key, person in rows.items() if key.startswith('s')]
    found = []
    if not grown and not tree['minors'] and not tree['more']:
        found.append("You're an only child.")
    if tree['minors']:
        found.append(f"You also have {tree['minors']} younger {'sibling' if tree['minors'] == 1 else 'siblings'} "
                     'still growing up.')
    if tree['more']:
        found.append(f"You have {tree['more']} more brothers and sisters who live far away.")
    return found


def line(tree: dict, rows: dict[str, dict], definition: dict) -> str | None:
    older = circle.voice(perception_home(definition)) == 'older'

    def say(role: str) -> str:
        return circle.said(role, definition)
    parts = [*parents_text(tree, rows, say, older), *gone_text(rows, say), *siblings_text(tree, rows)]
    return f"- Your family: {' '.join(parts)}" if parts else None


def perception_home(definition: dict) -> dict | None:
    from companion.world import perception
    return perception.home_data(definition)
