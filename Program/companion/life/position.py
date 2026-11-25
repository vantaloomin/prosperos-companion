"""Where the companion stands at work (v1.5.0): runs the place, manages people, or works for someone.

Hours (companion/life/shifts.py) say which days they work; this says who is in charge. Before it, everyone with a job
was an employee, so Sett, who runs the fighting pits, heard "There are rumors of layoffs at Sett's work" (tester,
2026-11-25). Now the work stories, the yearly review, layoffs and quitting, and the lines about a boss follow the
position: a promotion is for someone with a boss, and the owner of the place is never laid off from it.

The position is read each time it is needed, with rules and words only, so nothing is stored and an existing world
corrects itself on its next day:
1. what the user picked on the character form (Work and money > Position);
2. a business the app started for them (companion/life/business.py): they run it;
3. their career's own `position` tag (the built-in owners and managers, and any a city pack tags);
4. the words on their card that say what they do for work (identity, background, routine), then the career's name:
   "owns the bar", "runs a small bakery", "proprietor", "head chef", "shift supervisor";
5. otherwise they work for someone, as before.
Owner words are read before manager words, and only about the companion: not "her mother runs the bakery", not
"dreams of owning her own shop", not "used to run a bar".
"""
import re

POSITIONS = ('owner', 'lead', 'staff')
LABELS = {'owner': 'Runs the place', 'lead': 'Manages people', 'staff': 'Works for someone'}
# What the stories and events that need a boss above them are open to.
BOSSED = ('lead', 'staff')

# Places a person can own or run, so "runs a bakery" reads as work and "runs a marathon" does not ("a studio
# apartment" and "a gym membership" are not places of work either).
PLACE = (r"(?:shop|store|bar|pub|tavern|inn|alehouse|saloon|speakeasy|caf[eé]|coffee ?shop|bakery|restaurant|diner|"
         r"bistro|eatery|noodle ?bar|food ?truck|stall|gym|dojo|studio|salon|parlou?r|boutique|bookshop|bookstore|"
         r"business|company|firm|practice|clinic|agency|farm|ranch|orchard|vineyard|winery|brewery|distillery|garage|"
         r"workshop|forge|smithy|mill|hotel|motel|guest ?house|hostel|b ?& ?b|bed and breakfast|boarding ?house|"
         r"night ?club|club|venue|theat(?:er|re)|gallery|label|operation|empire|outfit|syndicate|gang|startup|"
         r"enterprise|franchise|dispensary|florist|kennel|stable|circus|troupe|newspaper|magazine|casino|brothel|den|"
         r"pit|arena|academy|school|establishment|emporium)(?:e?s)?\b(?!\s+(?:apartment|flat|membership|card|pass|"
         r"account|ticket)s?\b)")
# A run of up to three words between a verb and the place: "runs the underground fighting pits".
BETWEEN = r"(?:[\w'&-]+\s+){0,3}?"
ARTICLE = r"(?:a|an|the|her|his|their|its|two|three|several)\s+"
OWNER = re.compile(
    r"\b(?:co-?)?owns\s+(?:and\s+(?:runs|manages)\s+)?" + ARTICLE + BETWEEN + PLACE
    + r"|\bruns\s+" + ARTICLE + BETWEEN + r"(?:" + PLACE + r"|(?:place|joint)\b)"
    + r"|\b(?:her|his|their|my) own\s+" + BETWEEN + PLACE
    + r"|\b" + PLACE + r"\s+owner\b|\bowner(?:-operator)? (?:of|and)\b|\bthe owner\b"
    r"|\b(?:proprietor|proprietress|founder|co-?founder|guild ?master|guild ?mistress|shopkeeper|innkeeper|"
    r"storekeeper|tavern[ -]keeper|publican|alewife)\b(?!['’]s\b)"
    r"|\b(?:landlord|landlady|boss) of (?:a|an|the)\b"
    r"|\bin charge of " + ARTICLE + BETWEEN + r"(?:business|operation|place|company|firm|shop|bar|pits?|club|venue|"
    r"establishment)\b",
    re.IGNORECASE)
# What a manager manages: "manages the bar staff", never "manages her anxiety".
MANAGED = (r"(?:team|staff|crew|shift|kitchen|floor|department|ward|unit|desk|office|branch|site|project|store|shop|"
           r"bar|restaurant|hotel|venue|club|section|workers|employees|people|fighters|guards|men|women|band|warehouse|"
           r"factory|plant|line|watch)s?\b")
LEAD = re.compile(
    r"\b(?:(?:assistant|general|shift|floor|store|shop|bar|office|restaurant|hotel|site|project|team|stage|house|line|"
    r"kitchen|branch|warehouse)\s+)?manager\b"
    r"|\b(?:supervisor|foreman|forewoman|forelady|overseer|superintendent|sergeant|lieutenant|quartermaster|"
    r"headmaster|headmistress|matron|charge nurse|team lead(?:er)?|shift lead|crew (?:chief|boss|leader)|"
    r"ma[iî]tre d|sous[ -]chef|director of|editor-in-chief|police captain|fire captain|"
    r"(?:ship's|sea|army|navy|boat) captain)\b"
    r"|\bhead (?:chef|cook|nurse|waiter|waitress|gardener|bartender|teacher|librarian|clerk|groom|"
    r"of (?!(?:the |her |his |their )?(?:hair|curls|house|household|family|steam)\b)(?:the )?\w+)"
    r"|\bchief (?:of|engineer|inspector|officer|executive|editor|clerk|steward)\b"
    r"|\bcaptain of " + ARTICLE + r"(?:ship|boat|vessel|guard|watch)\b"
    r"|\b(?:manages|supervises|oversees|leads)\s+(?!to\b)" + ARTICLE + BETWEEN + MANAGED
    + r"|\bruns the (?:kitchen|floor|shift|night shift|day shift|team|department|ward|unit|desk|front desk|line|crew|"
    r"front of house|warehouse|factory)\b"
    r"|\bin charge of " + r"(?:" + ARTICLE + r")?" + BETWEEN + MANAGED,
    re.IGNORECASE)
# Titles that are someone else's when they are "her manager", "Ana's boss".
TITLES = re.compile(r'manager|supervisor|foreman|forewoman|forelady|owner|proprietor|landlord|landlady|boss|'
                    r'sergeant|lieutenant|captain|chief|director|head|matron', re.IGNORECASE)
POSSESSED = re.compile(r"\b(?:(?i:my|his|her|their|your|our)|[A-Z][a-z]+['’]s)\s+(?:[\w-]+\s+)?$")
# Someone else before the words: "her mother runs the bakery" is about her mother.
SOMEONE_ELSE = re.compile(
    r"\b(?:father|mother|dad|mom|mum|mama|papa|parents?|brother|sister|siblings?|uncle|aunt|grand\w+|husband|wife|"
    r"boyfriend|girlfriend|partner|fianc[ée]e?|friends?|cousin|son|daughter|boss|neighbou?r|employer|landlord|"
    r"landlady)\b", re.IGNORECASE)
# The past, or a hope, before the words: neither says where they stand now.
NOT_NOW = re.compile(
    r"\b(?:used to|former|formerly|years ago|retired|grew up|as a (?:kid|child|girl|boy|teen)|childhood|dreams?|"
    r"dreaming|hopes?|hoping|wants? to|wanted to|wish(?:es)?|someday|some day|one day|saving|saves|plans? to|"
    r"planning|would love|aspir\w*|aims? to|might|could|left|quit|sold)\b", re.IGNORECASE)
SENTENCE = re.compile(r'(?<=[.!?])\s+|\n+')
# Clauses: a sentence's parts between commas, semicolons, colons and dashes, and before "and" or "but".
CLAUSE = re.compile(r'[,;:()]|\s[-–—]\s|\s(?:and|but|while|whereas|though|although)\s', re.IGNORECASE)


def chosen(definition: dict) -> str:
    """What the user picked on the character form, '' for the app's pick."""
    found = (definition.get('money') or {}).get('position') or ''
    return found if found in POSITIONS else ''


def clauses(text: str) -> list[str]:
    return [part for sentence in SENTENCE.split(text or '') for part in CLAUSE.split(sentence) if part.strip()]


def said(pattern: re.Pattern, clause: str) -> bool:
    """The pattern names the companion's own work in this clause: nobody else is named before it, it is not the past
    or a hope, and a title is not someone else's ("her manager")."""
    for match in pattern.finditer(clause):
        before = clause[:match.start()]
        if SOMEONE_ELSE.search(before) or NOT_NOW.search(before):
            continue
        if TITLES.search(match.group(0)) and POSSESSED.search(before):
            continue
        return True
    return False


def from_words(text: str) -> str:
    """'owner' or 'lead' when the words say it of them, else ''. Owner words anywhere win over manager words."""
    found = clauses(text)
    for position, pattern in (('owner', OWNER), ('lead', LEAD)):
        if any(said(pattern, clause) for clause in found):
            return position
    return ''


def card_words(definition: dict) -> str:
    return '\n'.join(definition.get(key) or '' for key in ('identity', 'background', 'routine'))


def guess(definition: dict, career: dict | None) -> str:
    """The app's pick, whatever the user chose: a business the app started, the career's tag, the card's words, then
    the career's name; else they work for someone."""
    if definition.get('business'):
        return 'owner'
    if career and career.get('position') in POSITIONS:
        return career['position']
    return from_words(card_words(definition)) or from_words((career or {}).get('name') or '') or 'staff'


def of(definition: dict, career: dict | None) -> str:
    """Their position: the user's pick, else the app's."""
    return chosen(definition) or guess(definition, career)


def companion_position(connection, companion: dict) -> str:
    """The companion's position as things stand, '' when it does not apply: no job, a student, or freelance (gigs
    have no boss and no staff to speak of)."""
    from companion.life import outings, shifts, work
    definition = companion['version']['definition']
    if not definition.get('business') and not work.works(definition):
        return ''
    city = outings.city_data(connection, definition) if connection else None
    career = work.career_of(definition, city)
    if work.kind_of(career) == work.STUDY or shifts.employment(definition, career) == 'freelance':
        return ''
    return of(definition, career)


# A line about their boss ("brb, boss is here"), which nobody who runs the place says.
BOSS = re.compile(r"\bboss(?:'s|es)?\b", re.IGNORECASE)


def lines_for(lines, held: str) -> list[str]:
    """Lines about work that fit someone in this position: the owner's leave out a boss; everyone else's are all."""
    return [line for line in lines if not BOSS.search(line)] if held == 'owner' else list(lines)


def fits(positions, position: str) -> bool:
    """Whether something open to `positions` (empty: anyone) is open to someone in `position` ('' counts as
    staff: what it was before positions)."""
    return not positions or (position or 'staff') in positions
