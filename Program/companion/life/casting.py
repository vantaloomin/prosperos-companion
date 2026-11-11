"""Who a storyline can be about: only people the story can be true for, checked against their record.

A storyline (companion/life/storylines.py) is a sentence about someone in the circle. Before v1.3.4 its cast barely
looked at them: a promotion "at work" went to a seamstress who works from home, and a night spent comforting a friend
through a breakup went to the companion's rival, who had a girlfriend the whole time (tester, 2026-11-10). These rules
narrow who can be drawn; the seeded draw itself is unchanged.

Every rule takes the circle row and `Facts`, what the rules need to know about the world once per draw (how close the
companion is to people the roles don't vouch for, whether the companion holds a job, the Their love life slider, whose
wedding is planned, the era). `Facts()` with nothing filled in is a world where nothing is known beyond the rows
themselves, for callers with no connection. Rules and words only, no model.
"""
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time

from companion.life import big_days, circle, circle_love, shifts
from companion.world import catalog

# Roles that confide in the companion by default: old friends, friends, roommates and family.
CONFIDANTS = circle.OLD_FRIENDS | {'friend', 'new friend', 'roommate', 'roommate from years ago', 'best friend'}
FAMILY = circle.FAMILY | circle.GRANDPARENTS
# Anyone else confides only once this close (pairs.NAMES: 3 is "Friends").
CLOSE_ENOUGH = 3
# A rival or an ex never cries on the companion's shoulder, whatever the stage says.
ADVERSARY = re.compile(r"\b(?:rivals?|rivalry|nemesis|nemeses|arch-?enem(?:y|ies)|opponents?|enem(?:y|ies)|"
                       r"ex(?:-(?:wife|husband|girlfriend|boyfriend|partner|fianc[ée]e?))?)\b(?!-)", re.IGNORECASE)
# Someone who works for themselves, from home or in their own place: no promotion "at work" for them.
INDEPENDENT_WORDS = ('from home', 'at home', 'home based', 'own shop', 'own business', 'own practice', 'own studio',
                     'self employed', 'for themselves', 'for herself', 'for himself', 'runs a', 'owner', 'owns a')
# A relationship of record the user set between two circle people (circle.set_tie).
COUPLED_TIES = {'married', 'partners', 'divorced', 'separated'}
# Single after a breakup this recently: no engagement yet.
SINGLE_DAYS = 180
# Still taken in law or in fact: no new engagement.
TAKEN = {'married', 'engaged', 'separated'}


@dataclass
class Facts:
    """What the rules know about the world for one draw."""
    people: list[dict] = field(default_factory=list)
    close: object = None            # (row) -> closeness stage 1 to 5, or None when unknown
    companion_employed: bool = True
    love_level: int = 2             # Their love life slider (love_life.level)
    weddings: frozenset = frozenset()  # circle ids with a wedding of their own planned (big_days)
    modern: bool = True             # the companion's city is of today's era (phones)
    today: date | None = None
    states: dict = field(default_factory=dict)

    def love(self, row: dict) -> dict:
        if row['id'] not in self.states:
            self.states[row['id']] = circle_love.state(None, row, self.people)
        return self.states[row['id']]


def details(row: dict) -> dict:
    return circle.details_of(row)


def kind(row: dict) -> str:
    return circle.role_kind(row['role'])


def family(row: dict) -> bool:
    return kind(row) in FAMILY


def adversary(row: dict) -> bool:
    return bool(ADVERSARY.search(f"{row.get('role') or ''}. {details(row).get('note') or ''}")) or kind(row) == 'ex'


def confidant(row: dict, facts: Facts) -> bool:
    """Someone who would come to the companion with their troubles: they know each other, and the role says so (an
    old friend, a friend, a roommate, family), or the companion is close to them. Never a rival or an ex."""
    if circle.knowing(row) != 'both' or adversary(row):
        return False
    if kind(row) in CONFIDANTS or family(row):
        return True
    stage = facts.close(row) if facts.close else None
    return stage is not None and stage >= CLOSE_ENOUGH


def has_job(row: dict) -> bool:
    return big_days.working(details(row))


def job_words(row: dict) -> str:
    found = details(row)
    return f"{found.get('career') or ''} {found.get('employer') or ''} {found.get('note') or ''}"


def employed(row: dict) -> bool:
    """Has a job with an employer over them (staff or rota), so "a promotion at work" can be true."""
    if not has_job(row):
        return False
    if details(row).get('works_with_companion'):  # Works where the companion does.
        return True
    if independent_words(row):
        return False
    career = catalog.careers().get(row.get('career') or '')
    return shifts.employment_of(career, job_words(row)) in ('staff', 'rota')


def independent_words(row: dict) -> bool:
    return shifts.has_words(job_words(row).replace('-', ' '), INDEPENDENT_WORDS)


def independent(row: dict) -> bool:
    """Has a job and works for themselves: freelance, from home, their own shop."""
    return has_job(row) and not employed(row)


def job_is_apps(row: dict) -> bool:
    """The app chose their job, so a story may change it."""
    edited = set(details(row).get('edited', ()))
    return not edited & {'job', 'employer'}


def love_is_apps(row: dict) -> bool:
    """The app chose their love life, so a story may change it: no couple the user set, no partner the user named."""
    found = details(row)
    told = set((found.get('own_ties') or {}).values())
    return not told & COUPLED_TIES and 'partner' not in set(found.get('edited', ()))


def in_town(row: dict) -> bool:
    return details(row).get('local', True) is not False


def adult(row: dict) -> bool:
    from companion.life import ages
    age = details(row).get('age')
    return not isinstance(age, int) or age >= ages.ADULT


def single(row: dict, facts: Facts) -> bool:
    return facts.love(row)['state'] in ('single', 'divorced', 'widowed')


def seeing_someone(row: dict, facts: Facts) -> bool:
    """Seeing someone or engaged, and not to the companion: a breakup can happen to them."""
    found = facts.love(row)
    partner = found.get('partner') or {}
    return found['state'] in ('seeing', 'engaged') and partner.get('key') != 'companion'


# The storyline casts (Story.cast) -------------------------------------------------------------------------------

def employed_parent(row: dict, facts: Facts) -> bool:
    return kind(row) == 'parent' and employed(row) and job_is_apps(row)


def independent_parent(row: dict, facts: Facts) -> bool:
    return kind(row) == 'parent' and independent(row)


def friend_with_a_job(row: dict, facts: Facts) -> bool:
    return confidant(row, facts) and not family(row) and employed(row) and job_is_apps(row) and \
        not details(row).get('works_with_companion')


def friend_seeing_someone(row: dict, facts: Facts) -> bool:
    """A friend with a partner the app gave them, no wedding planned, and near enough to sit up with (or a phone)."""
    return confidant(row, facts) and not family(row) and seeing_someone(row, facts) and love_is_apps(row) and \
        row['id'] not in facts.weddings and (facts.modern or in_town(row))


def coworker(row: dict, facts: Facts) -> bool:
    return kind(row) == 'coworker' and bool(details(row).get('works_with_companion')) and facts.companion_employed


def known_parent(row: dict, facts: Facts) -> bool:
    return kind(row) == 'parent' and circle.knowing(row) == 'both'


def unmarried_sibling(row: dict, facts: Facts) -> bool:
    return kind(row) == 'sibling' and not details(row).get('married') and facts.love(row)['state'] not in TAKEN and \
        love_is_apps(row) and circle_love.single_by_event_since(row, SINGLE_DAYS, facts.today) is None


def close_friend(row: dict, facts: Facts) -> bool:
    return kind(row) in circle.OLD_FRIENDS and confidant(row, facts)


def single_best_friend(row: dict, facts: Facts) -> bool:
    return close_friend(row, facts) and single(row, facts) and facts.love_level > 0


SINGLE = {
    'employed parent': employed_parent,
    'independent parent': independent_parent,
    'parent': known_parent,
    'unmarried sibling': unmarried_sibling,
    'cousin': lambda row, facts: kind(row) == 'cousin',
    'coworker': coworker,
    'friend with a job': friend_with_a_job,
    'friend seeing someone': friend_seeing_someone,
    'close friend': close_friend,
    'best friend, single': single_best_friend,
}


def two_friends(first: dict, second: dict, facts: Facts) -> bool:
    return confidant(first, facts) and confidant(second, facts)


def two_single_friends(first: dict, second: dict, facts: Facts) -> bool:
    return all(confidant(row, facts) and single(row, facts) and love_is_apps(row) and adult(row)
               for row in (first, second))


def parents(first: dict, second: dict, facts: Facts) -> bool:
    """Married parents, as the app has it: a marriage the user set is theirs to end."""
    return circle.own_tie(first, second) is None and (not facts.modern or in_town(first) or in_town(second))


PAIRS = {'two friends': two_friends, 'two single friends': two_single_friends, 'parents': parents}


def facts(connection, companion: dict, people: list[dict], day: date) -> Facts:
    """What the rules need, read once for a draw on this day."""
    from companion.clock import zone
    from companion.life import love_life
    from companion.memory import pairs
    from companion.world import perception
    me, cache = pairs.companion_key(companion['id']), {}
    now = datetime.combine(day, time(12), zone(companion['version']['timezone']))

    def close(row):
        if row['id'] not in cache:
            cache[row['id']] = pairs.closeness(connection, me, row['seed'], now)
        return cache[row['id']]

    weddings = frozenset(row['person_id'] for row in connection.execute(
        "SELECT person_id FROM big_days WHERE timeline_id=? AND kind='wedding' AND person_id IS NOT NULL "
        "AND status IN ('planned', 'invited', 'declined')", (companion['active_timeline_id'],)))
    definition = companion['version']['definition']
    return Facts(people=people, close=close, companion_employed=companion_employed(connection, companion),
                 love_level=love_life.level(connection), weddings=weddings,
                 modern=perception.era_modern(definition), today=day,
                 states={row['id']: circle_love.state(connection, row, people) for row in people})


def companion_employed(connection, companion: dict) -> bool:
    """The companion works for someone else and is not between jobs: a manager, a promotion and layoffs are real."""
    from companion.life import outings, work
    definition = companion['version']['definition']
    if not work.works(definition):
        return False
    career = work.career_of(definition, outings.city_data(connection, definition)) if connection else None
    if shifts.employment(definition, career) == 'freelance':
        return False
    found = work.state(connection, companion['active_timeline_id']) if connection else None
    return not found or found['status'] == 'working'

