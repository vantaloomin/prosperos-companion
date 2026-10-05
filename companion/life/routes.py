"""Life simulation, Today and Feed API (PRD T1–T7, F1, F2, F4)."""
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field

from companion import conversation
from companion.characters import require_current
from companion.clock import parse, stamp
from companion.database import settings
from companion.errors import require
from companion.life import agenda, circle, feed, money, mood, recommendations, routine, simulation, today
from companion.models import Input, LifeSettingsUpdate, MessageCreate

router = APIRouter(prefix='/api/life')
today_router = APIRouter(prefix='/api/today')
feed_router = APIRouter(prefix='/api/feed')


class Reconcile(Input):
    mode: Literal['return'] = 'return'


class PersonUpdate(Input):
    name: str = Field(min_length=1, max_length=60, pattern=r'\S')


class ReadPosts(Input):
    post_ids: list[str] | None = Field(default=None, max_length=200)


class Reaction(Input):
    reaction: Literal['heart', 'laugh', 'wow', 'sad', 'hug'] | None = None


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
    return await request.app.state.life.reconcile((body or Reconcile()).mode)


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
        return next(person for person in agenda.circle_view(connection, timeline_id, now, include_removed=True)
                    if person['id'] == person_id)


@router.get('/circle')
def read_circle(request: Request, include_removed: bool = False):
    """The companion's social circle (PRD T8), assembled the first time it is read."""
    database, engine = db(request), request.app.state.life
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        circle.ensure(connection, companion, engine.world, now)
        return agenda.circle_view(connection, companion['active_timeline_id'], now, include_removed)


@router.get('/circle/room')
def circle_room(request: Request):
    """How many people the circle has and how many it should have, for the offer to add more."""
    with db(request).connect() as connection:
        return circle.room(connection, require_current(connection))


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


@router.post('/circle/{person_id}/remove')
def remove_person(request: Request, person_id: str):
    return circle_change(request, person_id,
                         lambda connection, now: circle.set_status(connection, person_id, 'removed', now))


@router.post('/circle/{person_id}/restore')
def restore_person(request: Request, person_id: str):
    return circle_change(request, person_id,
                         lambda connection, now: circle.set_status(connection, person_id, 'active', now))


@router.get('/circle/{person_id}/diary')
def person_diary(request: Request, person_id: str, before: str | None = None, limit: int = 20):
    """What this person did, newest first. Upcoming entries stay hidden (PRD T9)."""
    with db(request).connect() as connection:
        companion = require_current(connection)
        row = circle.person(connection, person_id)
        require(row['timeline_id'] == companion['active_timeline_id'], 'That person is not in the circle.', 404)
        return agenda.diary(connection, row['timeline_id'], person_id, min(max(limit, 1), 100), before)


@today_router.get('')
def read_today(request: Request):
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
def read_feed(request: Request, before: str | None = None, limit: int = 20, hidden: bool = False):
    return feed.listing(db(request), before, min(max(limit, 1), 100), hidden)


@feed_router.get('/export')
def export_feed(request: Request):
    return feed.export(db(request))


@feed_router.post('/read')
def read_posts(request: Request, body: ReadPosts | None = None):
    return feed.mark_read(db(request), (body or ReadPosts()).post_ids)


@feed_router.post('/posts')
def create_post(request: Request, body: PostCreate):
    return feed.post_event(db(request), body.event_id, body.intro)


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
    feed.get(db(request), post_id)
    message = conversation.record_user(db(request), body)
    feed.link_message(db(request), message['id'], post_id)
    return await request.app.state.conversation.send(body, wait)
