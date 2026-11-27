"""Private moments in a Story scene (companion/story_private.py): what the user whispers, shows or passes to one
person is for that person alone. Only they answer it, only they hear it, and the models are told so."""
import pytest
from test_story import busy_place, ok, say
from test_story_secrets import SECRET, declare, knows, lines_say, set_scene, turn_of

from companion import story, story_cast, story_private

NOTEPAD = ('*she winces and takes a notepad in her purse, then writes quickly and shows it to the server, careful to '
           'not let anyone else see it: Sett - The Boss*')
PRIVATE = [
    NOTEPAD,
    'I lean in and whisper to the bartender, "is that guy always here?"',
    'I whisper in the barista\'s ear: "the usual, please."',
    'She murmurs into his ear that the stew is too salty.',
    '"Don\'t look now," I say under my breath to Dana.',
    'I say quietly to Dana, "thanks for earlier."',
    'I lower my voice. "Is the back room free tonight?"',
    "I tell the server in a low voice that it's a surprise party.",
    'I pass the vendor a folded note.',
    'I slip the librarian a note with the title on it.',
    'I slide a scrap of paper across the bar to the bartender.',
    'I write the number down and show it only to the clerk.',
    'I angle my phone so only the bartender can read the screen.',
    "I turn the menu so that no one else sees what I'm pointing at.",
    'I speak softly so only she can hear: "we should go."',
    "I discreetly ask the bouncer whether he's seen her tonight.",
    'I ask the owner privately if the rumor is true.',
    'I pull the cook aside and ask about the recipe.',
    'I take Dana aside for a word.',
    'I mouth "thank you" to the barista.',
    'I cup a hand around my mouth and tell him the password.',
    'I hide the card from the others and let the dealer see it.',
    'Making sure nobody else hears, I ask the guide about the locked door.',
    "I tell her, just between us, that I'm leaving town.",
    'Out of earshot of the others, I ask the trainer what he really thinks.',
    'I show her the letter without anyone else seeing.',
    'I quietly tell the bartender to put it on my tab.',
    'I drop my voice and ask if she knows him.',
    'That was for your ears only, I tell the clerk.',
    'I whispered the address to the driver.',
]
OPEN = [
    'I sit down and order a coffee.',
    'I quietly sip my tea.',
    'The whisper of rain on the window is nice.',
    'I look around, careful not to bump into anyone.',
    'I stage-whisper to the bartender so the whole bar can hear.',
    "I don't whisper; I just say it.",
    'I say it loud enough for the regular to hear: "nice game."',
    '"Another round for everyone!" I call out.',
    'I tell the server out loud that the food was great.',
    'I hand the vendor a few coins and take the apples.',
    'I pass the bartender my empty glass.',
    'I show the clerk my ticket.',
    'I show everyone the photo on my phone.',
    'I ask the librarian where the history section is.',
    'I cover my mouth and yawn.',
    'I take off my jacket and hang it over the chair.',
    'I lean on the bar and watch the band.',
    'I pull out a chair and sit next to the regular.',
    'I take the long way around the square.',
    'I say hello to Dana and ask how her day is going.',
    "It's a secret recipe, the cook says, and I laugh.",
    'I only show up here on Fridays, I tell him.',
    'I keep my voice level and ask for the manager.',
    'I read the note on the door.',
    'I notice nobody else is in the shop.',
    'I hear someone laughing in the back.',
    'I ask if anyone has seen my keys.',
    # Part of it is for the room, so the line is not taken as private.
    "I announce that I'm buying, and whisper to the bartender to make them doubles.",
    "Today I'm finishing my last cup of heavy cream so no choice for tomorrow.",
    'It makes me think ear in the ear must be a pain to clean.',
    'OOC: can I whisper to the bartender here?',
    '((I whisper something to the server))',
]
MIRA = {'id': 'c1', 'name': 'Mira', 'full': 'Mira Santos'}
AIKO = {'sheet': {'key': 't1', 'name': 'Aiko', 'full': 'Aiko Tanaka', 'role': 'server', 'occupation': 'server'}}
KAZE = {'sheet': {'key': 't2', 'name': 'Kaze', 'full': 'Kaze Ito', 'role': 'regular', 'occupation': 'fisherman'}}


@pytest.mark.parametrize('text', PRIVATE)
def test_plain_words_make_a_line_private(text):
    assert story_private.moment(text) is not None


@pytest.mark.parametrize('text', OPEN)
def test_anything_else_is_said_in_the_open(text):
    assert story_private.moment(text) is None


def who(text, companions=(MIRA,), people=(AIKO, KAZE)):
    found = story_private.read(text, list(companions), list(people))
    return found and (found['who'] and found['who']['id'])


def test_who_a_private_moment_is_for():
    assert who(NOTEPAD) == 't1'  # By what the screen calls her.
    assert who('I whisper to the waitress: "is he always here?"') == 't1'  # Or another word for the same job.
    assert who('I whisper to Aiko, "thank you."') == 't1' and who('I whisper to Mira, "let\'s go."') == 'c1'
    # The one nearest the words that make it private, whoever else the line names.
    assert who('I say to Kaze, "nice opening," then whisper to the server: "who is he?"') == 't1'
    assert who('I whisper to the server, "don\'t tell Mira."') == 't1'
    # Nobody named: the only other person there, else nobody the rules can tell.
    assert who('I whisper to her: "happy birthday."') is None
    assert who('I whisper: "happy birthday."', companions=(), people=(AIKO,)) == 't1'
    other = {'sheet': {**AIKO['sheet'], 'key': 't3', 'name': 'Bo', 'full': 'Bo Lind'}}
    assert who('I whisper to the server.', people=(AIKO, other)) is None  # Two servers, and it says no more.
    assert story_private.read('I wave at the server.', [MIRA], [AIKO]) is None


def test_only_the_one_it_was_for_answers():
    def speakers(text):
        return [item['name'] for item in story_cast.speakers([MIRA], [AIKO, KAZE], text)]
    assert speakers('I whisper to Mira, "let\'s go."') == ['Mira']
    assert speakers(NOTEPAD) == []
    assert speakers('I whisper to her: "happy birthday."') == ['Mira']  # Can't tell: as any other line.
    assert speakers('I look around.') == ['Mira']


def narrator_requests(provider):
    return [request for request in provider.requests if turn_of(request['messages']) is None]


def test_the_narrator_is_told_who_it_was_for_and_the_line_stays_marked(client, clock, provider):
    from test_drafting import connect
    from test_social_circle import make
    make(client, 'Warm and curious.')
    connect(client)
    place, people = busy_place(client, clock)
    ok(client.put('/api/story/scene', json={'city_id': 'baltimore', 'place_id': place['id']}))
    sheet = people[0]['sheet']
    say(client, f'I whisper to {sheet["name"]}: "the password is plum."', 'story-0001')
    told = provider.requests[-1]
    assert 'People know only what they could see or hear from where they are.' in told['system']
    assert told['messages'][-1]['content'].endswith(story_private.NOTE.format(who=sheet['full']))
    # Said in the open, the next line gets no note, and the private one keeps its tag.
    say(client, 'I look around the room.', 'story-0002')
    later = provider.requests[-1]['messages']
    assert '[Private:' not in later[-1]['content']
    tag = story_private.TAG.format(who=sheet['full'])
    assert any(f'plum."\n{tag}' in message['content'] for message in later[:-1])
    assert all(story_private.NOTE.format(who=sheet['full']) not in message['content'] for message in later)
    # Somewhere else, with other people, the tag is gone.
    other = next(item for item in ok(client.get('/api/story'))['scene']['places'] if item['id'] != place['id'])
    ok(client.put('/api/story/scene', json={'city_id': 'baltimore', 'place_id': other['id']}))
    say(client, 'I look around.', 'story-0003')
    assert all('[Private:' not in message['content'] for message in provider.requests[-1]['messages'])


def test_a_whisper_to_one_companion_is_theirs_alone(client, monkeypatch, provider):
    scene = set_scene(client, monkeypatch)
    secret = declare(client, scene)
    provider.respond = lines_say(Mira='"Keep it down," Mira says, low.')
    whisper = f'I whisper to Mira, "{SECRET}, right?"'
    sent = say(client, whisper, 'story-0001')
    # Only Mira answers, told it was for her; Sam, who it is kept from, has not found out.
    assert [(row['role'], row.get('name')) for row in sent['replies']] == [('narrator', None), ('companion', 'Mira')]
    assert set(provider.respond.asked) == {'Mira'}
    assert story_private.OWN in provider.respond.asked['Mira'][0]['notes']
    assert f"{whisper}\n\n{story_private.NOTE_OWN.format(who='Mira')}\n\n[Mira and Sam will answer" in \
        narrator_requests(provider)[-1]['messages'][-1]['content']
    assert knows(client, secret['id']) == {'Mira': 'origin'}
    # Later in the scene Sam reads that the line and her answer were private; the narrator too.
    say(client, 'I turn to Sam. "How is the beer?"', 'story-0002')
    sam = provider.respond.asked['Sam'][-1]['notes']
    assert f'User: {whisper}\n{story_private.TAG.format(who="Mira")}' in sam
    assert f'Mira: "Keep it down," Mira says, low.\n{story_private.REPLY_TAG}' in sam
    assert story_private.OWN not in provider.respond.asked['Sam'][-1]['notes']
    told = '\n'.join(message['content'] for message in narrator_requests(provider)[-1]['messages'])
    assert story_private.TAG.format(who='Mira') in told and story_private.REPLY_TAG in told
    assert knows(client, secret['id']) == {'Mira': 'origin'}


def test_a_whisper_to_someone_else_is_not_for_the_companions_there(client, clock, monkeypatch, provider):
    scene = set_scene(client, monkeypatch)
    secret = declare(client, scene)
    with client.app.state.database.connect() as connection:
        data = story.city_data(connection, 'baltimore')
        moment = story.local_moment(data, clock.now())
        person = next(found[0] for place in data['places']
                      if (found := story.present(connection, data, place['id'], moment)))
    monkeypatch.setattr(story, 'present', lambda *_args: [person])
    provider.respond = lines_say()
    whisper = f'I whisper to {person["sheet"]["name"]}: "{SECRET}."'
    sent = say(client, whisper, 'story-0001')
    # The narrator voices the one it was for; no companion takes a turn, and nobody the ledgers know has heard it.
    assert [row['role'] for row in sent['replies']] == ['narrator'] and not provider.respond.asked
    assert f"{whisper}\n\n{story_private.NOTE.format(who=person['sheet']['full'])}" in \
        narrator_requests(provider)[-1]['messages'][-1]['content']
    assert knows(client, secret['id']) == {'Mira': 'origin'}
    # Said out loud, everyone there hears it, as before.
    say(client, f'I say to {person["sheet"]["name"]}: "{SECRET}."', 'story-0002')
    assert knows(client, secret['id']) == {'Mira': 'origin', 'Sam': 'reveal'}
