"""Opt-in emotional traits (PRD C6) and how they are described to the model."""

ABSENCE_TRAITS = {'guilt_over_absence', 'neediness', 'sulking'}
TRAIT_NAMES = {'jealousy': 'jealousy', 'guilt_over_absence': 'guilt over absence', 'possessiveness': 'possessiveness',
               'neediness': 'neediness', 'sulking': 'a tendency to sulk'}


def traits_text(traits, relationship) -> str:
    """User-chosen traits (C6). They shape mood and dialogue only, within what you can know."""
    listed = ', '.join(f"{TRAIT_NAMES[trait['trait']]} ({trait['intensity']}/5)" for trait in traits)
    text = (f'Emotional traits the user chose for you, with intensity out of 5: {listed}. Express them in '
            'character and in proportion to their intensity. You may be hurt or curious, but never claim to know '
            'what the user did, and never guilt them about settings, pausing or leaving.')
    if relationship != 'romance' and any(trait['trait'] in {'jealousy', 'possessiveness'} for trait in traits):
        text += ' Your relationship is not romantic: never express jealousy or possessiveness as romantic exclusivity.'
    return text
