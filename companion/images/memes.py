"""Memes the companion sends in chat, assembled from templates without a model.

A meme is a reaction picture with top and bottom text. The text comes from a small library keyed
to the companion's situation (what their routine has them doing, the weather, the time of day), so
it fits their day and never needs a model call. The picture is either the companion pulling a face
or a simple fictional scene; the interface draws the text over it, since image models garble text.
Nothing here is an event: a meme is a joke, not something that happened.
"""
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Template:
    top: str
    bottom: str
    # The companion's expression in the picture, or a scene that replaces them.
    expression: str = ''
    subject: str = ''


SITUATIONS = {
    'work': (
        Template('Me at work', 'Pretending I know what the meeting is about', 'politely baffled'),
        Template('"Quick call?"', 'It is never quick', 'thousand-yard stare'),
        Template('My brain at {label}', 'Loading...', subject='a cat staring blankly at a laptop screen'),
        Template('Me answering one email', 'Time for a break', 'proud, exhausted'),
    ),
    'study': (
        Template("Me: I'll study for five minutes", 'Three hours later: still on page one', 'dazed'),
        Template('Opening my notes', 'Understanding none of them', 'squinting in confusion'),
        Template('The textbook', 'Me, emotionally', subject='a very small dog next to a very large stack of books'),
    ),
    'errand': (
        Template('Me running one quick errand', 'Somehow it has been three hours', 'frazzled'),
        Template('The list said four things', 'I bought eleven', 'guilty grin'),
    ),
    'social': (
        Template("Me saying I'll leave early", 'Still here at closing time', 'delighted'),
        Template('My social battery', 'Somehow still at 100%', 'beaming'),
    ),
    'leisure': (
        Template('Nobody:', 'Me, living my best life at {where}', 'blissfully content'),
        Template('My plans for today', 'Absolutely none, and I love it', 'smug'),
        Template('Me doing nothing', 'Me, doing it extremely well', subject='a cat sprawled across a sunny windowsill'),
    ),
}
WEATHER = {
    'rain': (
        Template('The forecast: sunny', 'The sky: absolutely not', 'betrayed'),
        Template('Me checking if the rain stopped', 'It did not', subject='a soggy pigeon under an awning'),
    ),
}
TIMES = {
    'night': (
        Template('Me at 2 a.m.', 'Why am I like this', 'wide awake and sheepish'),
    ),
    'morning': (
        Template('Me before coffee', 'Me after coffee', subject='a sleepy owl next to a steaming mug'),
    ),
}
ANYTIME = (
    Template('You', 'The person I wanted to send this to', 'pointing at the camera'),
    Template('When you text me', "and I'm already smiling", 'grinning'),
    Template('Me trying to be normal', 'Me', subject='a dog wearing sunglasses in a coffee shop'),
    Template('Thinking about you', '(this is a meme, act natural)', 'trying to look casual'),
)


def situation(moment, local_hour) -> tuple:
    """The templates that fit: the routine's kind first, then weather and time of day, then any."""
    found = list(SITUATIONS.get(moment['kind'], ())) if moment else []
    if moment and moment.get('rain'):
        found += WEATHER['rain']
    if local_hour >= 23 or local_hour < 5:
        found += TIMES['night']
    elif local_hour < 10:
        found += TIMES['morning']
    return tuple(found) or ANYTIME


def choose(moment, local_hour, seed: str, recent=()) -> dict:
    """One meme, varied by seed and avoiding the ones sent lately (`recent` top lines)."""
    rng = random.Random(seed)
    options = [template for template in situation(moment, local_hour) + ANYTIME if template.top not in recent]
    template = rng.choice(options or list(ANYTIME))
    label = (moment or {}).get('label', 'work').lower()
    where = (moment or {}).get('place') or 'home'
    fill = {'label': label, 'where': where}
    return {'top': template.top.format(**fill), 'bottom': template.bottom.format(**fill),
            'expression': template.expression, 'subject': template.subject,
            'where': f' at {where}' if moment and moment.get('place') and not template.subject else ''}
