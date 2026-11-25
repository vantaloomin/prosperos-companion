"""A feed picture shows the moment as it happened (tester's Sett, 2026-11-18): a named block or a plan of their own is
not at home unless its words say so, the light is the middle of the moment (lunch at lunchtime), a grey sky greys the
daylight, the weather is said early as something to draw, and a home description never ends in two periods or names
them."""
from companion.images import prompts

LOOK = 'Tall muscular man, early thirties'


def draw(event, setting=''):
    return prompts.compose('Sett', '', [event], 'Painted fantasy art', setting, dressed=True, who='he', look=LOOK)


def test_a_named_block_or_own_plan_is_at_home_only_when_its_words_say_so():
    yard = {'summary': 'Sett spent the morning brawling in the Training yard, as usual.', 'place': '',
            'moment': {'activity': 'own-block'}}
    assert not prompts.at_home(yard)
    assert prompts.at_home({**yard, 'summary': 'Sett spent the evening at home with a book, as usual.'})
    assert not prompts.at_home({'summary': 'Sett spent the afternoon at the old mill, as planned.', 'place': '',
                                'moment': {'activity': 'own-plan'}})
    assert prompts.at_home({'summary': 'Sett read.', 'place': '', 'moment': {'activity': 'reading'}})
    assert not prompts.at_home({'summary': 'Sett walked.', 'place': '', 'moment': {'activity': 'walk'}})
    assert not prompts.at_home({'summary': 'Sett ate.', 'place': 'Kettle and Oar', 'moment': {'activity': 'lunch-out'}})


def test_the_light_is_the_middle_of_the_moment_and_lunch_is_at_lunchtime():
    tz = 'UTC'
    morning = {'starts_at': '2026-11-17T08:00:00+00:00', 'ends_at': '2026-11-17T13:00:00+00:00', 'moment': {}}
    assert prompts.moment_hour(morning, tz) == 10
    lunch = {'starts_at': '2026-11-17T09:30:00+00:00', 'ends_at': '2026-11-17T13:30:00+00:00',
             'moment': {'activity': 'lunch-out'}}
    assert prompts.moment_hour(lunch, tz) == 12
    assert prompts.moment_hour({'starts_at': '2026-11-17T09:00:00+00:00', 'moment': {}}, tz) == 9
    overnight = {'starts_at': '2026-11-17T22:00:00+00:00', 'ends_at': '2026-11-18T02:00:00+00:00', 'moment': {}}
    assert prompts.moment_hour(overnight, tz) == 22


def test_a_grey_sky_greys_the_daylight_and_the_rain_is_said_early():
    event = {'summary': 'Sett spent the morning brawling in the Training yard.', 'place': '', 'hour': 10,
             'weather': {'rain': True}, 'mood': 'content'}
    prompt = draw(event)
    assert 'Soft, grey morning light.' in prompt and 'Bright morning' not in prompt
    rain = prompt.index('It is raining')
    assert prompt.index('Training yard') < rain < prompt.index('only person') < prompt.index('grey morning light')
    assert 'Bright morning daylight.' in draw({**event, 'weather': {}}) and 'It is raining' not in draw({**event, 'weather': {}})
    night = draw({**event, 'hour': 22})
    assert 'Rain-wet streets.' in night and 'grey sky' not in night


def test_rain_shows_on_the_windows_at_home_and_not_in_other_rooms():
    event = {'summary': 'Sett read.', 'place': '', 'hour': 14, 'weather': {'rain': True}, 'indoor': True}
    assert 'Rain streaks the windows' in draw({**event, 'home': True})
    assert 'rain' not in draw(event).lower().replace('grey', '')


def test_lunch_shows_the_food_in_front_of_them():
    event = {'summary': 'During the shift, Sett took a proper lunch break at Kettle and Oar.', 'place': 'Kettle and Oar',
             'activity': 'lunch-out', 'hour': 12}
    assert 'He is eating lunch at a small table, a full plate of food and a drink in front of him at Kettle and Oar.' \
        in draw(event)
    shift = draw({'summary': 'Sett worked.', 'place': 'The Great Pit', 'activity': 'steady-shift', 'hour': 12})
    assert 'the task in front of him' in shift


def test_their_name_in_the_home_description_is_a_pronoun_that_fits():
    setting = ('At home: a small apartment above the pits, close enough for Sett to keep an eye on his business. '
               'Wearing a russet tunic.')
    prompt = draw({'summary': 'Sett read.', 'place': '', 'activity': 'reading', 'hour': 14}, setting)
    assert 'close enough for him to keep an eye' in prompt and 'Sett' not in prompt
