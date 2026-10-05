"""Which user-chosen emotional traits (PRD C6) react to the user's absence (M4).

Traits are free-text names with an intensity of mild, moderate or strong. A trait counts as an
absence trait when its name speaks of absence, guilt, missing someone, neediness or sulking.
"""
ABSENCE_WORDS = ('absence', 'absent', 'guilt', 'miss', 'need', 'clingy', 'lonely', 'sulk', 'abandon')
LEVELS = {'mild': 1, 'moderate': 2, 'strong': 3}
NAMES = {level: name for name, level in LEVELS.items()}


def absence_traits(definition) -> list[dict]:
    return [trait for trait in definition.get('emotional_traits') or []
            if any(word in trait['name'].lower() for word in ABSENCE_WORDS)]


def strongest(traits) -> int:
    return max(LEVELS.get(trait['intensity'], 1) for trait in traits)
