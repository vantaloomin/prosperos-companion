"""What a storyline is made of (companion/life/storylines.py): a story, its beats, and an evening a beat takes."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Spent:
    """A beat that says the companion spent real time with someone in it (v1.4.0): it takes a slot of the companion's
    day (`summary`, their agenda entry) and the same slot of that person's day (`theirs`, companion/life/joint.py).
    `short` and `short_share` tell the beat when no slot could take it, without saying where the evening went."""
    activity: str
    summary: str
    theirs: str
    short: str
    short_share: str
    mood: str = 'content'
    with_cast: int = 0


@dataclass(frozen=True)
class Beat:
    text: str
    share: str
    tone: str = 'mixed'
    spent: Spent | None = None


@dataclass(frozen=True)
class Story:
    key: str
    level: int
    cast: str
    stages: tuple[tuple[Beat, ...], ...]
    gap: tuple[int, int] = (2, 6)
    own: bool = False  # Started by its own module, never by the drama roll, and outside its caps.
    # For a story about the companion's own work: the positions it is true for (companion/life/position.py), empty
    # for anyone. A promotion needs a boss above them; the owner of the place gets none.
    positions: tuple[str, ...] = ()


def beat(text, share, tone='mixed', spent=None):
    return (Beat(text, share, tone, spent),)


def either(*beats):
    return tuple(Beat(*item) for item in beats)
