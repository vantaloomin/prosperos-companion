"""Companions in the Story's scene (companion/story_cast.py): there when the story is where their day has them,
speaking in their own lines after the narrator's."""
from datetime import timedelta

import pytest
from conftest import Chunk, reconcile
from test_drafting import connect
from test_drop_by import SHIFTS
from test_story import ok, say
from test_together import mira


@pytest.fixture
def barkeep(client, monkeypatch):
    mira(client, monkeypatch, schedule=SHIFTS)
    reconcile(client)


def script(provider, *texts):
    provider.replies = [[Chunk(text), Chunk('', 'stop')] for text in texts]


def at_work(client):
    return ok(client.put('/api/story/scene', json={'city_id': 'baltimore', 'place_id': 'club-charles'}))


def test_a_companion_at_work_is_in_the_scene_and_answers_for_themself(client, barkeep, provider, clock):
    moved = at_work(client)
    assert moved['scene']['around'][0] == 'Mira' and moved['scene']['companions'][0]['name'] == 'Mira'
    assert [(row['role'], row['text']) for row in moved['messages'][-2:]] == [
        ('scene', 'You arrive at Club Charles, Station North, Baltimore.'), ('cast', 'Mira is here.')]
    script(provider, 'The bar is dim and nearly empty.', 'Mira looks up from the taps. "You came."')
    sent = say(client, 'I look around.', 'story-0001')
    assert [(row['role'], row['name']) for row in sent['replies']] == [('narrator', None), ('companion', 'Mira')]
    assert sent['replies'][1]['text'] == 'Mira looks up from the taps. "You came."'
    narrator, own = provider.requests[-2], provider.requests[-1]




