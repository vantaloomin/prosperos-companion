"""A job in someone's own words matched to a career the app knows, without a model.

"ER nurse", "a paralegal", "retired teacher": the circle (companion/life/circle.py) reads jobs the character sheet gives
its people, and the user can type one on the circle list. The words stay what they show; the matched career only
gives their week its hours and a fitting workplace. Words that match nothing still show, with ordinary office hours.
"""
import re

# Everyday words for careers whose names say it another way: the word, then career ids to try in order.
ALIASES = {
    'nurse': ('registered-nurse', 'trained-nurse'), 'doctor': ('physician', 'physician-resident'),
    'gp': ('physician',), 'surgeon': ('physician',), 'resident': ('physician-resident',),
    'student': ('undergraduate',), 'college student': ('undergraduate',), 'university student': ('undergraduate',),
    'uni student': ('undergraduate',), 'grad student': ('graduate-student',), 'phd student': ('graduate-student',),
    'teacher': ('teacher',), 'schoolteacher': ('teacher',), 'professor': ('professor',), 'lecturer': ('professor',),
    'programmer': ('software-engineer',), 'developer': ('software-engineer',), 'coder': ('software-engineer',),
    'engineer': ('software-engineer', 'defense-engineer'), 'designer': ('graphic-designer', 'ux-designer'),
    'chef': ('line-cook',), 'cook': ('line-cook',), 'waiter': ('server',), 'waitress': ('server',),
    'cashier': ('retail-associate',), 'shop assistant': ('retail-associate',), 'sales assistant': ('retail-associate',),
    'police officer': ('police-patrolman',), 'cop': ('police-patrolman',), 'policeman': ('police-patrolman',),
    'policewoman': ('police-patrolman',), 'detective': ('private-detective',), 'mechanic': ('garage-mechanic',),
    'realtor': ('real-estate-agent',), 'estate agent': ('real-estate-agent',), 'banker': ('finance-banker',),
    'trainer': ('fitness-trainer',), 'reporter': ('journalist',), 'writer': ('journalist',),
    'electrician': ('construction-trades',), 'plumber': ('construction-trades',), 'carpenter': ('construction-trades',),
    'builder': ('construction-trades',), 'sailor': ('military-sailor',), 'pastor': ('minister',),
    'priest': ('minister',), 'vicar': ('minister',), 'analyst': ('data-analyst',), 'clerk': ('office-clerk',),
    'secretary': ('office-clerk',), 'receptionist': ('hotel-front-desk', 'office-clerk'),
    'singer': ('musician', 'performer'), 'dancer': ('performer', 'chorus-dancer'), 'scientist': ('biotech-scientist',),
}
# Words that say someone has no job: (shown as, kept as retired).
NO_JOB = {'retired': ('Retired', True), 'unemployed': ('Between jobs', False), 'none': ('', False),
          'no job': ('', False), 'stay at home parent': ('Stay-at-home parent', False),
          'homemaker': ('Homemaker', False), 'housewife': ('Homemaker', False)}
# Words before a job that leave the job the same: "a senior accountant", "a part-time barista".
SOFT = re.compile(r'^(?:(?:senior|junior|head|lead|chief|assistant|part time|full time|freelance|self employed|'
                  r'local|young|new|former|trainee|apprentice|staff|er|icu|night shift|pediatric|paediatric)\s+)+')


def plain(text: str) -> str:
    return ' '.join(re.findall(r'[a-z]+', text.casefold()))


def no_job(text: str) -> tuple[str, bool] | None:
    """(how it shows, retired) when the words say they have no job ("retired", "retired teacher"), else None."""
    words = plain(text)
    if words.startswith('retired'):
        return 'Retired', True
    return NO_JOB.get(words)


def career_match(text: str, offered: dict[str, dict]) -> dict | None:
    """The offered career the words name: by its name or id, an everyday word for it, or the last words of either
    ("pediatric nurse" finds "Registered nurse"); None when nothing fits."""
    words = plain(text)
    if not words or no_job(text):
        return None
    softened = SOFT.sub('', words)
    for candidate in dict.fromkeys((words, softened)):
        for career in offered.values():
            if candidate in (plain(career['name']), plain(career['id'])):
                return career
        for career_id in ALIASES.get(candidate, ()):
            if career_id in offered:
                return offered[career_id]
    last = softened.split()[-1]
    fitting = [career for career in offered.values() if plain(career['name']).split()[-1] == last
               or plain(career['id']).split()[-1] == last]
    if fitting:
        return min(fitting, key=lambda career: (len(career['name']), career['id']))
    return next((offered[career_id] for career_id in ALIASES.get(last, ()) if career_id in offered), None)


def label(text: str) -> str:
    """How a typed job shows: their own words, first letter capitalised ("ER nurse" keeps its capitals)."""
    words = ' '.join(text.split()).strip(' .,;')
    words = re.sub(r'^(?:a|an)\s+', '', words, flags=re.IGNORECASE)
    return words[:1].upper() + words[1:]
