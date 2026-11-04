"""A picture shows where the moment is: a shift at the workplace their words name, and the place as the world's lore
and city file describe it (companion/images/places.py), with light and camera words that fit the place and the
user's style."""
from companion.database import encode
from companion.images import places, prompts
from companion.world import looks

CITY = {'places': [
    {'id': 'the-great-pit', 'name': 'The Great Pit', 'kind': 'stadium', 'setting': 'indoor',
     'summary': 'A sunken ring of packed sand under hanging lamps, with tiers of benches. Fights every night.'},
    {'id': 'blue-cup', 'name': 'Blue Cup Cafe', 'kind': 'cafe', 'setting': 'indoor', 'summary': 'A small cafe.'}]}
ENTRIES = [
    {'title': 'His mother', 'keywords': encode(['Ma']), 'text': 'Kalo adores his mother.'},
    {'title': 'The pits', 'keywords': encode(['the pits', 'Great Pit']),
     'text': '{{char}} took the whole thing over. The pits are tunnels, dice dens and the Great Pit itself: a sand '
             'ring under lamps.'}]


def test_a_shift_is_at_the_workplace_their_words_name():
    definition = {'identity': 'Kalo loves the Blue Cup Cafe on Sundays. He owns the Great Pit and runs it himself.'}
    assert places.workplace(definition, CITY)['id'] == 'the-great-pit'
    assert places.workplace({'identity': 'He loves the Blue Cup Cafe.'}, CITY) is None
    assert places.workplace({}, CITY, 'Nights at the Great Pit')['id'] == 'the-great-pit'


def test_the_place_looks_as_the_lore_and_the_city_say_without_the_companion_in_it():
    line = places.lore_line(ENTRIES, 'The Great Pit', 'Kalo')
    assert line.startswith('The pits are tunnels') and '{{char}}' not in line
    assert places.looks(line, places.summary_line(CITY['places'][0])) == line
    assert places.looks('', places.summary_line(CITY['places'][0])).endswith('with tiers of benches.')
    assert places.lore_line(ENTRIES, 'Blue Cup Cafe', 'Kalo') == ''


def test_a_place_look_goes_into_the_picture_with_indoor_light_and_one_of_them():
    event = {'summary': 'Kalo had a busy night shift.', 'place': 'The Great Pit', 'activity': 'busy-shift', 'hour': 23,
             'weather': {'rain': True}, 'indoor': True, 'place_look': 'The setting is The Great Pit. A sand ring.'}
    prompt = prompts.compose('Kalo', 'A tall man.', [event], 'Painted fantasy art', framing='selfie', who='he')
    assert 'moving quickly at The Great Pit.' in prompt and 'The setting is The Great Pit. A sand ring.' in prompt
    assert 'He appears only once in the picture.' in prompt
    assert 'Night, lit by warm lamps.' in prompt and 'streetlights' not in prompt and 'rain' not in prompt


def test_camera_words_follow_only_a_photographic_style():
    assert prompts.camera('Candid, natural-light photograph', 'selfie')
    assert prompts.camera('Splash art, painterly, non-photorealistic, polished concept art', 'selfie') == ''
    assert prompts.camera('Anime illustration, photo-like lighting', 'moment') == ''


def test_their_own_in_photos_age_wins_over_the_sheets():
    sheet = 'A very tall man in his mid twenties with tan skin.'
    assert prompts.one_age(sheet, 'Muscular man, early thirties') == 'A very tall man with tan skin.'
    assert prompts.one_age(sheet, 'Muscular man, red hair') == sheet


SETT = {'name': 'Sett', 'appearance': 'Tall, broad, heavily muscled half-vastayan man in his early thirties with upswept '
        'pointed pink furry ears.',
        'in_photos': 'tall muscular half-vastayan man, early thirties, swept-back red-brown hair, pointed pink furry ears, '
                     'amber eyes, taped knuckles, gold chain'}
SETT_SHEET = {'age': 35, 'height_cm': 196, 'build': '', 'skin': 'tan', 'face': 'square', 'jaw': 'a strong, square jaw',
              'nose': '', 'eyes': '', 'eye_shape': '', 'hair': '', 'facial_hair': '',
              'feature': 'vastayan ears on top of his head, covered in pink fur'}


def test_the_sheet_leaves_out_what_their_in_photos_line_says():
    said = prompts.in_photos(SETT, 'he')
    sheet = looks.picture(SETT_SHEET, 'he', said)
    # Size, age and ears are said once, in their own words; the rest of the sheet follows them.
    assert sheet == 'He has tan skin, a square face and a strong, square jaw.'
    # A feature they set on the looks form is said in the form's words, and the In photos line leaves it out.
    own = {**SETT, 'looks': {'feature': SETT_SHEET['feature']}}
    assert 'ears' not in prompts.in_photos(own, 'he') and 'amber eyes' in prompts.in_photos(own, 'he')
    assert looks.picture(SETT_SHEET, 'he', prompts.in_photos(own, 'he')).endswith('covered in pink fur.')
    prompt = prompts.compose('Sett', SETT['appearance'], [{'summary': 'Sett read a book.', 'place': '', 'mood': ''}],
                             'Painted fantasy art', who='he', sheet=sheet, look=said)
    assert prompt.index('Tall muscular half-vastayan man') < prompt.index('He has tan skin')
    assert 'very tall' not in prompt and 'thirties' in prompt and prompt.count('ears') == 1
    # Words that say none of it keep the whole sheet, freckles beside taped knuckles included.
    assert looks.picture(SETT_SHEET, 'he', 'Red hair, taped knuckles').startswith('A very tall man in his mid thirties')
    assert 'freckles' in looks.picture({**SETT_SHEET, 'feature': 'freckles'}, 'he', 'Red hair, taped knuckles')
    assert looks.picture(SETT_SHEET, 'he') == looks.picture(SETT_SHEET, 'he', '')


def test_an_errand_is_a_picture_of_its_things_with_nobody_in_it():
    event = {'summary': 'Sett picked up the resoled boots and bought a spare pair of laces.', 'place': 'Cobbler Row',
             'mood': 'content', 'hour': 13, 'moment': {'admin': {'source': 'admin'}},
             'place_look': 'The setting is Cobbler Row. A cobbler shop.', 'indoor': True}
    assert prompts.errand(event) and not prompts.errand({**event, 'moment': {'admin': {'source': 'health'}}})
    prompt = prompts.errand_prompt(SETT, event, 'Candid photo', 'he')
    assert 'just after he picked up the resoled boots and bought a spare pair of laces.' in prompt
    assert 'No people in the picture' in prompt and 'only person' not in prompt and 'face shows' not in prompt
    assert 'half-vastayan' not in prompt and 'The setting is Cobbler Row.' in prompt
    assert prompt.endswith(prompts.CAMERAS['things'])
    assert not prompts.camera('Painted fantasy art', 'things')
