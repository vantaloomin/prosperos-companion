"""Life simulation, Today and Feed API (PRD T1–T7, F1, F2, F4)."""
from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field

from companion import consequences, conversation, news
from companion.characters import require_current
from companion.clock import parse, stamp
from companion.database import settings
from companion.errors import DomainError, require
from companion.life import (
    agenda,
    ages,
    big_days,
    big_turns,
    breakups,
    calls,
    chapters,
    circle,
    circle_edit,
    circle_pets,
    citymap,
    deck,
    encounters,
    families,
    feed,
    kids,
    long_distance,
    loss,
    love_life,
    money,
    mood,
    moving_in,
    network,
    outings,
    parenthood,
    pets,
    pets_routes,
    reactions,
    recommendations,
    rough_patches,
    routine,
    simulation,
    social,
    steps,
    storylines,
    their_people,
    today,
    together,
    town_personality,
    trips,
    user_posts,
    web,
    wedding,
)
from companion.memory import pairs
from companion.models import Input, KindChange, LifeSettingsUpdate, MessageCreate, TownsfolkPersonality
from companion.world import lifespans, paper, ships

router = APIRouter(prefix='/api/life')
today_router = APIRouter(prefix='/api/today')
feed_router = APIRouter(prefix='/api/feed')


class Reconcile(Input):
    mode: Literal['return'] = 'return'


class PersonUpdate(Input):
    name: str = Field(min_length=1, max_length=60, pattern=r'\S')


class PersonAbout(Input):
    """The user's changes to someone in the circle (companion/life/circle_edit.py); only the fields given change."""
    name: str | None = Field(default=None, min_length=1, max_length=60, pattern=r'\S')
    role: str | None = Field(default=None, min_length=1, max_length=40, pattern=r'\S')
    pronouns: Literal['she/her', 'he/him', 'they/them'] | None = None
    job: str | None = Field(default=None, max_length=60)
    employer: str | None = Field(default=None, max_length=80)
    age: int | None = Field(default=None, ge=0, le=5000)
    local: bool | None = None
    note: str | None = Field(default=None, max_length=300)


class PersonNew(PersonAbout):
    name: str = Field(min_length=1, max_length=60, pattern=r'\S')


class PersonSpared(Input):
    spared: bool


class ReadPosts(Input):
    post_ids: list[str] | None = Field(default=None, max_length=200)


class Reaction(Input):
    reaction: Literal['heart', 'laugh', 'wow', 'sad', 'hug'] | None = None


class Answer(Input):
    option: str = Field(min_length=1, max_length=200)
    client_id: str = Field(min_length=8, max_length=100)


class OwnPost(Input):
    text: str = Field(min_length=1, max_length=user_posts.TEXT_LIMIT)


class PostCreate(Input):
    event_id: str
    intro: str = Field(default='', max_length=1000)


def db(request: Request):
    return request.app.state.database


@router.get('/settings')
def read_settings(request: Request):
    return simulation.read_settings(db(request))


@router.put('/settings')
def update_settings(request: Request, body: LifeSettingsUpdate):
    return simulation.update_settings(db(request), body)


@router.post('/reconcile')
async def reconcile(request: Request, body: Reconcile | None = None):
    return await request.app.state.life.look_in((body or Reconcile()).mode)


@router.get('/storylines')
def list_storylines(request: Request, include_ended: bool = False):
    """What is going on in the companion's and their circle's lives: beats that have happened so far."""
    return storylines.listing(request.app.state.database, include_ended)


@router.post('/storylines/{storyline_id}/end')
def end_storyline(request: Request, storyline_id: str):
    return storylines.end(request.app.state.database, storyline_id)


@router.get('/recommendations')
def list_recommendations(request: Request):
    """What the user recommended, with how far the companion has got."""
    return recommendations.listing(request.app.state.database)


@router.post('/recommendations/{rec_id}/drop')
def drop_recommendation(request: Request, rec_id: str):
    return recommendations.drop(request.app.state.database, rec_id)


@router.post('/texts/check')
async def check_texts(request: Request):
    """Asked by the open app about once a minute: the companion may send a first message now."""
    return await request.app.state.openers.check()


@router.post('/prepare')
async def prepare(request: Request):
    """Hint that the user is typing or idle: prepare likely work in the background and return at once."""
    return request.app.state.life.prepare()


@router.get('/pauses')
def list_pauses(request: Request):
    return simulation.pauses(db(request))


@router.post('/pauses/{pause_id}/catch-up')
async def catch_up_pause(request: Request, pause_id: str):
    return await request.app.state.life.catch_up_pause(pause_id)


@router.get('/runs')
def list_runs(request: Request, limit: int = 20):
    return simulation.runs(db(request), min(max(limit, 1), 100))


@router.get('/routine')
def read_routine(request: Request):
    database = db(request)
    now = database.clock.now()
    with database.connect() as connection:
        companion = require_current(connection)
        position = simulation.cursor(connection, companion['active_timeline_id'])
    version = companion['version']
    schedule, default = routine.blocks(version['definition'])
    now_slot, next_slot = routine.current_and_next(schedule, version['timezone'], now)
    return {'timezone': version['timezone'], 'default_schedule': default,
            'blocks': [block.view() for block in schedule],
            'current': now_slot.view() if now_slot else None, 'next': next_slot.view() if next_slot else None,
            'simulated_through': position['simulated_through'], 'now': stamp(now),
            'clock_behind': now < parse(position['simulated_through'])}


def circle_change(request: Request, person_id: str, change) -> dict:
    """Apply a change to one person, then rebuild the upcoming entries it affects."""
    database, engine = db(request), request.app.state.life
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        timeline_id = companion['active_timeline_id']
        row = circle.person(connection, person_id)
        require(row['timeline_id'] == timeline_id, 'That person is not in the circle.', 404)
        change(connection, now)
        agenda.forget_person(connection, timeline_id, person_id, now)
        if simulation.may_extend(settings(connection), 'return'):
            agenda.extend(connection, companion, engine.world, now)
        found = next(person for person in agenda.circle_view(connection, timeline_id, now, include_removed=True)
                     if person['id'] == person_id)
        return with_pets(connection, companion, engine.world, [found], now)[0]


@router.get('/circle')
def read_circle(request: Request, include_removed: bool = False):
    """The companion's social circle (PRD T8), assembled the first time it is read."""
    database, engine = db(request), request.app.state.life
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        circle.ensure(connection, companion, engine.world, now)
        people = agenda.circle_view(connection, companion['active_timeline_id'], now, include_removed)
        stages = pairs.for_circle(connection, companion, circle.people(connection, companion['active_timeline_id'],
                                                                       include_removed), now)
        people = with_pets(connection, companion, engine.world, people, now)
        # Someone they are seeing (companion/life/love_life.py): where the two of them stand.
        love = love_life.circle_extras(connection, companion, now, bool(settings(connection)['show_odds']))
        met = their_people.for_circle(connection, companion, bool(settings(connection)['show_odds']), now)
        # Their children and a due month while expecting (companion/life/families.py), in words only.
        kids = families.for_circle(connection, companion, now)
        return [{**person, 'stage': stages.get(person['id']), 'met': met.get(person['id']), **love.get(person['id'], {}),
                 **kids.get(person['id'], {'children': [], 'expecting': None})} for person in people]


def pet_world(connection, companion: dict, world, now) -> tuple[dict, date]:
    """Where the circle's pets live (companion/life/circle_pets.py `where`) and the companion's today."""
    definition = companion['version']['definition']
    data = circle.city_data(definition, world)
    started = pets.timeline_start(connection, companion['active_timeline_id'], definition.get('timezone'))
    return ({'era': pets.era_of(data), 'start': started, 'aboard': ships.enclosed(data)},
            storylines.local_today(companion, now))


def with_pets(connection, companion: dict, world, people: list[dict], now) -> list[dict]:
    """Each person in the circle with their pets (companion/life/pets.py): seeded by the person until the user
    changes them (companion/life/circle_pets.py)."""
    where, day = pet_world(connection, companion, world, now)
    return [{**{key: value for key, value in person.items() if key != circle_pets.KEPT},
             'pets': person_pets(connection, circle_pets.of_person(person, where), day, now)} for person in people]


def person_pets(connection, found: list[dict], day: date, now) -> list[dict]:
    """Their pets' views, each with the number the user's edits name it by."""
    return [view | {'number': each['number']} for each, view in zip(found, pets.lived(connection, found, day, now))]


def pet_change(request: Request, person_id: str, action) -> dict:
    """Run `action(connection, where, today, now)` on someone's pets, then return the person."""
    world = request.app.state.life.world

    def change(connection, now):
        where, today = pet_world(connection, require_current(connection), world, now)
        action(connection, where, today, now)
    return circle_change(request, person_id, change)


@router.post('/circle/{person_id}/pets')
def add_circle_pet(request: Request, person_id: str, body: pets_routes.PetCreate):
    return pet_change(request, person_id, lambda connection, where, today, now: circle_pets.add(
        connection, person_id, pet_given(body, today), where, today, now))


@router.patch('/circle/{person_id}/pets/{number}')
def edit_circle_pet(request: Request, person_id: str, number: int, body: pets_routes.PetUpdate):
    return pet_change(request, person_id, lambda connection, where, today, now: circle_pets.edit(
        connection, person_id, number, pet_given(body, today), where, today, now))


@router.post('/circle/{person_id}/pets/{number}/remove')
def remove_circle_pet(request: Request, person_id: str, number: int):
    """They no longer have this pet; the app does not give it back."""
    return pet_change(request, person_id, lambda connection, where, _today, now: circle_pets.remove(
        connection, person_id, number, where, now))


def pet_given(body, today: date) -> dict:
    """The fields the user gave, with a birth date from the age they stepped to or the looks they wrote."""
    given = body.model_dump(exclude_unset=True)
    kind = given.get('kind') or 'cat'
    born = pets_routes.born(given.pop('age', None), today) or pets.age_from_looks(given.get('looks') or '', kind, today)
    return given | ({'born': born} if born else {})


@router.get('/circle/room')
def circle_room(request: Request):
    """How many people the circle has and how many it should have, for the offer to add more."""
    with db(request).connect() as connection:
        return circle.room(connection, require_current(connection))


@router.get('/circle/home')
def circle_home(request: Request):
    """Whether the companion lives aboard a ship or station ('ship', 'station' or None), so "where they live" in
    the circle reads Aboard the ship and Off the ship there rather than In town and Out of town."""
    with db(request).connect() as connection:
        return {'aboard': ships.vessel_of(connection, require_current(connection)['version']['definition'])}


@router.post('/circle/grow')
def grow_circle(request: Request):
    """Add people to a circle assembled smaller than it should be now (a sociable companion, or a
    bigger circle size in Settings). Nobody already there changes."""
    database, engine = db(request), request.app.state.life
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        circle.grow(connection, companion, engine.world, now)
        if simulation.may_extend(settings(connection), 'return'):
            agenda.extend(connection, companion, engine.world, now)
        return agenda.circle_view(connection, companion['active_timeline_id'], now)


@router.patch('/circle/{person_id}')
def rename_person(request: Request, person_id: str, body: PersonUpdate):
    return circle_change(request, person_id,
                         lambda connection, now: circle.rename(connection, person_id, body.name, now))


@router.put('/circle/{person_id}/about')
def edit_person(request: Request, person_id: str, body: PersonAbout):
    """The user's changes to someone in the circle: who they are, their job, where they live and a note."""
    world = request.app.state.life.world
    return circle_change(request, person_id, lambda connection, now: circle_edit.edit(
        connection, require_current(connection), world, person_id, body.model_dump(exclude_unset=True), now))


@router.post('/circle/people')
def add_person(request: Request, body: PersonNew):
    """Someone the user adds by hand; whatever they leave out the app picks."""
    database, engine = db(request), request.app.state.life
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        added = circle_edit.add(connection, companion, engine.world, body.model_dump(exclude_unset=True), now)
        if simulation.may_extend(settings(connection), 'return'):
            agenda.extend(connection, companion, engine.world, now)
        return next(person for person in agenda.circle_view(connection, companion['active_timeline_id'], now)
                    if person['id'] == added['id'])


@router.put('/circle/{person_id}/kind')
def set_person_kind(request: Request, person_id: str, body: KindChange):
    return circle_change(request, person_id,
                         lambda connection, now: circle.set_kind(connection, person_id, body.kind, body.lifespan, now,
                                                                 kinds_city(connection)))


def kinds_city(connection) -> dict | None:
    """The open companion's city, whose own kinds the pickers offer (companion/world/lifespans.py)."""
    return ages.city_of(connection, require_current(connection)['version']['definition'])


@router.get('/kinds')
def kinds(request: Request):
    """What the Kind and How long they live pickers offer, where the open companion lives."""
    with db(request).connect() as connection:
        companion = require_current(connection)
        return lifespans.choices(ages.city_of(connection, companion['version']['definition']))


@router.post('/circle/{person_id}/remove')
def remove_person(request: Request, person_id: str):
    return circle_change(request, person_id,
                         lambda connection, now: circle.set_status(connection, person_id, 'removed', now))


@router.post('/circle/{person_id}/restore')
def restore_person(request: Request, person_id: str):
    def change(connection, now):
        if found := loss.of_person(connection, person_id):  # Someone late comes back as if they never passed away.
            return loss.undo(connection, require_current(connection), found['id'], now)
        return circle.set_status(connection, person_id, 'active', now)
    return circle_change(request, person_id, change)


@router.post('/circle/{person_id}/spared')
def spare_person(request: Request, person_id: str, body: PersonSpared):
    """People can pass away: whether this person can (companion/life/loss.py). Someone the user wrote into the
    character's description is spared until this says otherwise."""
    return circle_change(request, person_id,
                         lambda connection, now: loss.set_spared(connection, person_id, body.spared, now))


@router.post('/circle/{person_id}/bring-back')
def bring_back(request: Request, person_id: str):
    """Someone who passed away comes back as if it never happened (companion/life/loss.py)."""
    def change(connection, now):
        found = loss.of_person(connection, person_id)
        require(found is not None, 'They have not passed away.', 409)
        loss.undo(connection, require_current(connection), found['id'], now)
    return circle_change(request, person_id, change)


@router.get('/circle/{person_id}/diary')
def person_diary(request: Request, person_id: str, before: str | None = None, limit: int = 20):
    """What this person did, newest first. Upcoming entries stay hidden (PRD T9)."""
    with db(request).connect() as connection:
        companion = require_current(connection)
        row = circle.person(connection, person_id)
        require(row['timeline_id'] == companion['active_timeline_id'], 'That person is not in the circle.', 404)
        return agenda.diary(connection, row['timeline_id'], person_id, min(max(limit, 1), 100), before)


@router.get('/network')
def network_people(request: Request, key: str):
    """Someone's own people, a few layers out from the circle (companion/life/network.py): `key` is a circle
    member's `key` or a key from an earlier answer. Built on request and never stored."""
    with db(request).connect() as connection:
        companion = require_current(connection)
        found = network.find(connection, companion, key)
        require(found is not None, 'That person is not around the circle.', 404)
        return {'person': found, 'people': network.people_of(connection, companion, key),
                'deeper': found['depth'] + 1 < network.MAX_DEPTH}


@router.get('/acquaintances')
def read_acquaintances(request: Request):
    """People the companion has met through their circle, newest first."""
    database = db(request)
    with database.connect() as connection:
        companion = require_current(connection)
        return network.acquaintances(connection, companion['active_timeline_id'], database.clock.now())


@router.get('/map')
def read_map(request: Request):
    """The companion's city with their places marked, for the map (companion/life/citymap.py)."""
    database = db(request)
    with database.connect() as connection:
        companion = require_current(connection)
        return citymap.build(connection, companion, database.clock.now(), bool(settings(connection)['story_mode']))


@router.get('/outings')
def read_outings(request: Request):
    """Going out with the user and trips away (companion/life/outings.py, trips.py), from two weeks ago on."""
    database = db(request)
    with database.connect() as connection:
        companion, now = require_current(connection), database.clock.now()
        return {'outings': outings.listing(connection, companion, now), 'trips': trips.listing(connection, companion, now)}


@router.get('/where')
def read_where(request: Request):
    """Where the companion in focus is with the user right now, for the chat strip (companion/life/together.py)."""
    database = db(request)
    with database.connect() as connection:
        return together.view(connection, require_current(connection), database.clock.now())


@router.post('/living/{action}')
def home_together(request: Request, action: Literal['out', 'home']):
    """Living together (companion/life/moving_in.py): the user heads out for a while (the chat texts), or is home."""
    database = db(request)
    with database.connect(write=True) as connection:
        companion, now = require_current(connection), database.clock.now()
        moving_in.set_out(connection, companion, action == 'out', now)
        return together.view(connection, companion, now)


@router.post('/calls')
def start_call(request: Request):
    """The user calls the companion in focus (the chat header's Call button, companion/life/calls.py): they pick up
    when they are free, otherwise it is a missed call they text back about."""
    database = db(request)
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        now = database.clock.now()
        calls.call(connection, companion, now)
        return together.view(connection, companion, now)


@router.post('/calls/{call_id}/{action}')
def change_call(request: Request, call_id: str, action: Literal['answer', 'decline', 'end']):
    """Answer or decline their call, or end the one under way."""
    database = db(request)
    with database.connect(write=True) as connection:
        return calls.act(connection, require_current(connection), call_id, action, database.clock.now())


@router.post('/trips/{trip_id}/{action}')
def change_visit(request: Request, trip_id: str, action: Literal['cancel', 'undo']):
    """Call off a weekend visit with the user that has not started (companion/life/long_distance.py), or undo that."""
    database = db(request)
    change = {'cancel': long_distance.cancel, 'undo': long_distance.undo}[action]
    with database.connect(write=True) as connection:
        changed = change(connection, require_current(connection), trip_id, database.clock.now())
    request.app.state.life.extend_agenda('return')
    return changed


@router.post('/outings/{outing_id}/{action}')
def change_outing(request: Request, outing_id: str, action: Literal['cancel', 'elsewhere', 'home', 'undo']):
    """Call an outing off, have the companion pick somewhere else, head home early, or undo calling it off or
    heading home."""
    database = db(request)
    change = {'cancel': outings.cancel, 'elsewhere': outings.elsewhere, 'home': outings.head_home,
              'undo': outings.undo}[action]
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        changed = change(connection, companion, outing_id, database.clock.now())
        if action == 'cancel':
            # Calling it off on the day can leave a little friction (companion/life/rough_patches.py).
            rough_patches.called_off(connection, companion, changed, database.clock.now())
    request.app.state.life.extend_agenda('return')
    return changed


@router.get('/rough-patch')
def read_rough_patch(request: Request):
    """Whether things are tense with the companion in focus (companion/life/rough_patches.py), for the Character page."""
    return rough_patches.read(db(request))


@router.post('/rough-patch/{patch_id}/let-go')
def let_go_rough_patch(request: Request, patch_id: str):
    """The user clears the air: that rough patch ends now."""
    return rough_patches.let_go(db(request), patch_id)


@router.post('/rough-patch/{patch_id}/undo')
def undo_let_go_rough_patch(request: Request, patch_id: str):
    """Take back Let it go."""
    return rough_patches.undo_let_go(db(request), patch_id)


@router.get('/breakup')
def read_breakup(request: Request):
    """Whether things are strained, on a break or over with the companion in focus (companion/life/breakups.py)."""
    return breakups.read(db(request))


@router.post('/breakup/{breakup_id}/mend')
def mend_breakup(request: Request, breakup_id: str):
    """The user overrides: things are fine again, or exes are back together."""
    return breakups.mend(db(request), breakup_id)


@router.post('/breakup/{breakup_id}/undo')
def undo_mend_breakup(request: Request, breakup_id: str):
    """Take back the override."""
    return breakups.undo_mend(db(request), breakup_id)


@router.get('/web')
def read_web(request: Request):
    """Who knows who: everyone the user has met or heard about and how they are tied (companion/life/web.py)."""
    database = db(request)
    with database.connect() as connection:
        require_current(connection)
        return web.build(connection, database.clock.now(), bool(settings(connection)['story_mode']))


@router.get('/townsfolk')
def read_townsfolk(request: Request):
    """Townsfolk the companion has run into around the city (companion/life/encounters.py), most recently seen
    first, with only what the companion has learned about them so far."""
    database = db(request)
    with database.connect() as connection:
        companion, now = require_current(connection), database.clock.now()
        return [{**person, 'stage': pairs.for_townsperson(connection, companion, person, now)}
                for person in encounters.known(connection, companion, now)]


@router.post('/townsfolk/personality')
def save_townsfolk_personality(request: Request, body: TownsfolkPersonality):
    """The personality sliders the user set on a townsperson's profile (companion/life/town_personality.py); the
    sliders left out, or handed back to the roll, are rolled again. Only someone the companion has met."""
    database = db(request)
    with database.connect(write=True) as connection:
        companion, now = require_current(connection), database.clock.now()
        known = {person['key']: person for person in encounters.known(connection, companion, now)}
        found = known.get(body.key)
        require(found is not None and found.get('personality') is not None,
                'The companion has not met that person.', 404)
        town = town_personality.town_of(companion)
        town_personality.save(connection, town, body.key, body.model_dump()['sliders'], database.now())
        data = network.city(connection, companion)
        sheet = encounters.resolve(data, body.key, encounters.town_cast(connection, companion, data))
        return town_personality.view(sheet, town_personality.edited(connection, town, body.key))


@router.get('/townsfolk/person')
def read_townsperson(request: Request, key: str):
    """One townsperson the companion has met, with where they probably are right now by their rules."""
    database = db(request)
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        now = database.clock.now()
        found = next((person for person in encounters.known(connection, companion, now) if person['key'] == key),
                     None)
        require(found is not None, 'The companion has not met that person.', 404)
        return {**found, 'now': encounters.whereabouts_now(connection, companion, key, now),
                'pets': encounters.pets_of(connection, companion, key, found['times'], now)}


@router.get('/paper')
def read_paper(request: Request, day: str | None = None):
    """The town paper for the companion's city (companion/world/paper.py): this week's issue, or the one out on or
    before `day` (YYYY-MM-DD), with the dates of the issues either side."""
    database = db(request)
    with database.connect() as connection:
        companion = require_current(connection)
        current = paper.issue_date(storylines.local_today(companion, database.clock.now()))
        asked = paper.issue_date(require_date(day)) if day else current
        shown = min(asked, current)
        # Their own town: seeded townsfolk, and the townsfolk who became companions staying put (world/turnover.py).
        data = network.city(connection, companion)
        require(bool(data.get('neighborhoods')), 'Pick a home city for the companion to get its paper.', 404)
        return {**paper.issue(connection, data, request.app.state.life.world, shown),
                'previous': (shown - timedelta(days=7)).isoformat(),
                'next': (shown + timedelta(days=7)).isoformat() if shown < current else None}


def require_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise DomainError('Give the date as YYYY-MM-DD.', 422) from None


class OutcomeChange(Input):
    option: int = Field(ge=0, le=31)  # chapter:next has 13 ways it can go.


@router.get('/consequences/{consequence_id}')
def read_consequence(request: Request, consequence_id: str):
    """How a turning in the world went and why (companion/consequences.py): each way it could have gone, with
    its odds and reasons, and the one it took."""
    with db(request).connect() as connection:
        found = consequences.by_id(connection, consequence_id)
        companion = require_current(connection)
        # Sharing a home: the answer of one living there shows on the newcomer's page too (moving_in.py).
        require(found['timeline_id'] == companion['active_timeline_id'] or
                moving_in.shown_with(connection, consequence_id, companion), 'That outcome is not on this timeline.', 404)
        # How a stage went, once a later stage followed: no "Make it go this way", and why (big_turns.py).
        return {**found, 'settled': big_turns.settled_note(connection, found) or families.odds_settled(connection, found)}


# "Change how it went" by subject prefix, for those that take (connection, companion, consequence_id, option, now).
CHANGES = {'moving_in:': lambda: moving_in.change, 'steps:': lambda: steps.change,
           'people:': lambda: their_people.change, 'breakup:': lambda: breakups.change,
           'bigday:': lambda: big_days.change, 'tense-ask:': lambda: rough_patches.change_ask,
           'wedding:': lambda: wedding.change_size, 'loss:': lambda: loss.change,
           'family:': lambda: parenthood.change,
           # How a business, a health turn or a parent's care is going (big_turns.py).
           'business:': lambda: big_turns.change_stage, 'health:': lambda: big_turns.change_stage,
           'caring:': lambda: big_turns.change_stage, 'kids:': lambda: kids.change,
           'baby:': lambda: families.change_baby}


@router.post('/consequences/{consequence_id}/change')
def change_consequence(request: Request, consequence_id: str, body: OutcomeChange):
    """The user makes it go another way instead."""
    with db(request).connect() as connection:
        subject = consequences.by_id(connection, consequence_id)['subject']
    if subject.startswith('storyline:'):
        return storylines.change_outcome(db(request), consequence_id, body.option)
    if subject.startswith('chapter:'):
        return chapters.change(db(request), request.app.state.life.world, consequence_id, body.option)
    if subject.startswith('love:'):
        database = db(request)
        with database.connect(write=True) as connection:
            return love_life.change(connection, require_current(connection), request.app.state.life.world,
                                    consequence_id, body.option, database.clock.now())
    change = next((found for prefix, found in CHANGES.items() if subject.startswith(prefix)), None)
    if change:
        database = db(request)
        with database.connect(write=True) as connection:
            return change()(connection, require_current(connection), consequence_id, body.option, database.clock.now())
    return reactions.change(db(request), consequence_id, body.option)


class MomentChange(Input):
    way: Literal['another', 'nothing']


@router.post('/moments/{day}/change')
def change_moment(request: Request, day: date, body: MomentChange):
    """Make a day's small moment from the Life deck go another way: another card, or nothing at all."""
    database = db(request)
    with database.connect(write=True) as connection:
        return deck.change(connection, require_current(connection), day, body.way, database.clock.now())


@router.get('/chapters')
def read_chapters(request: Request):
    """The life chapters in place on this timeline (companion/life/chapters.py), newest first."""
    return chapters.listing(db(request))


@router.get('/chapters/lately')
def read_chapters_lately(request: Request):
    """Big turns on their way and the latest chapters, for the Character page (companion/life/big_turns.py)."""
    return chapters.lately(db(request))


@router.post('/chapters/{chapter_id}/undo')
def undo_chapter(request: Request, chapter_id: str):
    """Take a chapter back; returns the chapters still in place."""
    return chapters.undo(db(request), chapter_id)


@router.get('/news')
def read_news(request: Request):
    """Word getting around (companion/news.py): the companion's recent news and who has heard it, in order."""
    return news.read(db(request))


@router.get('/reactions')
def read_reactions(request: Request):
    """How the companion took what the user did lately (companion/life/reactions.py), newest first."""
    return reactions.listing(db(request))


@today_router.get('')
def read_today(request: Request):
    social.refresh(db(request))
    return today.view(db(request))


@today_router.get('/money')
def read_money(request: Request):
    return money.view(db(request))


@today_router.post('/seen')
def seen(request: Request):
    return today.mark_seen(db(request))


@today_router.post('/mood/{mood_id}/reset')
def reset_mood(request: Request, mood_id: str):
    return mood.reset(db(request), mood_id)


@feed_router.get('')
def read_feed(request: Request, before: str | None = None, limit: int = 20, hidden: bool = False,
              source: Literal['all', 'companion', 'circle', 'mine'] = 'all'):
    social.refresh(db(request))
    return feed.listing(db(request), before, min(max(limit, 1), 100), hidden, source)


@feed_router.get('/export')
def export_feed(request: Request):
    return feed.export(db(request))


@feed_router.post('/read')
def read_posts(request: Request, body: ReadPosts | None = None):
    return feed.mark_read(db(request), (body or ReadPosts()).post_ids)


@feed_router.post('/posts')
def create_post(request: Request, body: PostCreate):
    return feed.post_event(db(request), body.event_id, body.intro)


@feed_router.post('/mine')
def create_own_post(request: Request, body: OwnPost):
    """A post of the user's own, which every companion and their circles see (companion/life/user_posts.py)."""
    return user_posts.create(db(request), body.text)


@feed_router.get('/{post_id}')
def read_post(request: Request, post_id: str):
    return feed.get(db(request), post_id)


@feed_router.post('/{post_id}/hide')
def hide_post(request: Request, post_id: str):
    return feed.set_status(db(request), post_id, 'hidden')


@feed_router.post('/{post_id}/unhide')
def unhide_post(request: Request, post_id: str):
    return feed.set_status(db(request), post_id, 'visible')


@feed_router.post('/{post_id}/remove')
def remove_post(request: Request, post_id: str):
    return feed.set_status(db(request), post_id, 'removed')


@feed_router.post('/{post_id}/reaction')
def react(request: Request, post_id: str, body: Reaction):
    return feed.react(db(request), post_id, body.reaction)


@feed_router.post('/{post_id}/discuss')
async def discuss(request: Request, post_id: str, body: MessageCreate, wait: bool = True):
    """Send a chat message that replies to a post; the reply is built knowing which post (F1).

    `wait=false` returns once the reply attempt is saved, as for ordinary sends."""
    require(feed.get(db(request), post_id)['source'] != user_posts.USER, 'That is your own post.', 409)
    message = conversation.record_user(db(request), body)
    feed.link_message(db(request), message['id'], post_id)
    return await request.app.state.conversation.send(body, wait)


@feed_router.post('/{post_id}/answer')
async def answer(request: Request, post_id: str, body: Answer, wait: bool = True):
    """Pick a choice on a question post; the pick goes to chat as a reply to the post."""
    social.answer(db(request), post_id, body.option)
    return await discuss(request, post_id, MessageCreate(text=body.option, client_id=body.client_id), wait)
