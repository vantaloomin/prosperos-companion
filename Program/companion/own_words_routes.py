"""Their own words API (companion/memory/own_words.py): the user's list of words to drop or swap, and what was caught
lately in the current companion's replies, with Keep and Dismiss."""
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field

from companion.characters import current
from companion.memory import context, own_words
from companion.memory.records import blocked_messages
from companion.models import Input

router = APIRouter(prefix='/api/own-words')


class WordRule(Input):
    phrase: str = Field(min_length=1, max_length=120)
    action: Literal['drop', 'swap', 'keep', 'dismiss']
    replacement: str = Field(default='', max_length=120)
    everyone: bool = False


def listing(connection) -> dict:
    companion = current(connection)
    if companion is None:
        return {'rules': [own_words.public(row) for row in own_words.rules(connection) if row['action'] != 'dismiss'],
                'caught': [], 'limit': own_words.MAX_RULES}
    timeline_id = companion['active_timeline_id']
    messages = context.transcript(connection, timeline_id, blocked_messages(connection, companion['id']))
    return own_words.listing(connection, timeline_id, companion['version']['definition'], messages)


@router.get('')
def read(request: Request):
    with request.app.state.database.connect() as connection:
        return listing(connection)


@router.post('')
def add(request: Request, body: WordRule):
    database = request.app.state.database
    with database.connect(write=True) as connection:
        own_words.add(connection, body.phrase, body.action, body.replacement, body.everyone, database.now())
        return listing(connection)


@router.delete('/{rule_id}')
def remove(request: Request, rule_id: str):
    database = request.app.state.database
    with database.connect(write=True) as connection:
        own_words.remove(connection, rule_id)
        return listing(connection)
