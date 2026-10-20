"""Memes the companion sends in chat, assembled from templates without a model.

A meme is a reaction picture with top and bottom text. The text comes from a caption bank keyed
to the companion's situation (what their routine has them doing, rain, late night, morning, or
anything at all; meme_data/captions.json), so it fits their day and never needs a model call.
Each caption has a mood, which picks the picture: a template on this computer
(companion/images/meme_pictures.py), a reaction GIF (gifs.py), or, when an image model is set up,
the companion pulling that face or a scene of something else. The interface draws the text over
it, since image models garble text. Nothing here is an event: a meme is a joke, not something
that happened.
"""
import json
import random
from functools import cache
from pathlib import Path

DATA = Path(__file__).parent / 'meme_data'
# A caption from the situation itself rather than one that fits any time.
SITUATION_SHARE = 0.75
# A "this, not that" meme, when that two-panel format is on this computer.
CHOICE_SHARE = 0.12
# A picture of something else rather than the companion pulling a face, when a model draws it.
SCENE_SHARE = 0.5


@cache
def bank() -> dict:
    return json.loads((DATA / 'captions.json').read_text(encoding='utf-8'))


def situation(moment, local_hour) -> list[str]:
    """The situations that fit: the routine's kind first, then weather and time of day."""
    found = [moment['kind']] if moment and moment.get('kind') in bank()['situations'] else []
    if moment and moment.get('rain'):
        found.append('rain')
    if local_hour >= 23 or local_hour < 5:
        found.append('night')
    elif local_hour < 10:
        found.append('morning')
    return found


def captions(names, where, recent) -> list[list[str]]:
    """The captions of these situations not sent lately; one naming the place only when there is one."""
    return [row for name in names for row in bank()['situations'][name]
            if row[0] not in recent and (where or '{where}' not in row[0] + row[1])]


def choose(moment, local_hour, seed: str, recent=(), choice=False) -> dict:
    """One meme, varied by seed and avoiding the ones sent lately (`recent` top lines). `choice`: the
    two-panel format is at hand, so a "this, not that" pair may be picked."""
    rng = random.Random(seed)
    if choice and rng.random() < CHOICE_SHARE:
        pairs = [pair for pair in bank()['choice'] if pair[0] not in recent] or bank()['choice']
        no, yes = rng.choice(pairs)
        return {'top': no, 'bottom': yes, 'mood': 'choice', 'expression': '', 'subject': '', 'where': ''}
    where = (moment or {}).get('place') or ''
    names = situation(moment, local_hour)
    options = captions(names, where, recent) if names and rng.random() < SITUATION_SHARE else []
    options = options or captions(['anytime'], where, recent) or bank()['situations']['anytime']
    top, bottom, mood = rng.choice(options)
    look = bank()['moods'][mood]
    scene = rng.choice(look['scenes']) if rng.random() < SCENE_SHARE else ''
    return {'top': top.format(where=where), 'bottom': bottom.format(where=where), 'mood': mood,
            'expression': '' if scene else rng.choice(look['faces']), 'subject': scene,
            'where': f' at {where}' if where and not scene else ''}
