"""Life simulation, Today and Feed API (PRD T1–T7, F1, F2, F4)."""
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field

from companion import conversation
from companion.characters import require_current
from companion.clock import parse, stamp
from companion.life import feed, mood, routine, simulation, today
from companion.models import Input, LifeSettingsUpdate, MessageCreate

router = APIRouter(prefix='/api/life')
today_router = APIRouter(prefix='/api/today')
feed_router = APIRouter(prefix='/api/feed')


class Reconcile(Input):
    mode: Literal['return'] = 'return'


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


@today_router.get('')
def read_today(request: Request):
    return today.view(db(request))


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
async def discuss(request: Request, post_id: str, body: MessageCreate):
    """Send a chat message that replies to a post; the reply is built knowing which post (F1)."""
    feed.get(db(request), post_id)
    message = conversation.record_user(db(request), body)
    feed.link_message(db(request), message['id'], post_id)
    return await request.app.state.conversation.send(body)
