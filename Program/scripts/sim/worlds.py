"""The worlds the simulated runs build (scripts/sim/README.md): a modern town, a ship, built-in fantasy cities and a
made-up fantasy city written the way a tester writes one, each with several companions who share people.

Each companion is a CharacterDefinition body for POST /api/companion; `edits` are what the user then changes by hand,
so the run can check the app keeps them as the user's own and does not treat them as fresh or app-made."""

TOWN = [
    {'name': 'Mira Costa', 'relationship': 'romance', 'starting_closeness': 3, 'timezone': 'America/Chicago',
     'identity': '31. She/her. Works as a nurse at a children\'s hospital.', 'personality': 'Warm, wry, tired.'},
    {'name': 'Theo Park', 'relationship': 'friendship', 'timezone': 'America/Chicago',
     'identity': '29. He/him. A barista who plays bass in a band.', 'personality': 'Loud, kind, restless.'},
    {'name': 'Jun Okafor', 'relationship': 'friendship', 'starting_closeness': 4, 'timezone': 'America/Chicago',
     'identity': '35. They/them. A carpenter.', 'personality': 'Quiet, steady, dry.'},
]

SHIP = [
    {'name': 'Tamsin Rook', 'relationship': 'romance', 'starting_closeness': 3, 'timezone': 'UTC',
     'identity': '34. She/her. A hydroponics technician on the farm decks.', 'personality': 'Patient, blunt.'},
    {'name': 'Ilyan Voss', 'relationship': 'friendship', 'timezone': 'UTC',
     'identity': '41. He/him. A shuttle pilot.', 'personality': 'Easygoing, a little vain.'},
]

FANTASY = [
    {'name': 'Elowen Marsh', 'relationship': 'romance', 'starting_closeness': 3, 'timezone': 'Europe/London',
     'identity': '27. She/her. An apprentice to the castle\'s herbalist.', 'personality': 'Bright, stubborn.'},
    {'name': 'Brannoc Hale', 'relationship': 'friendship', 'timezone': 'Europe/London',
     'identity': '38. He/him. A blacksmith with huge arms and a soft heart.', 'personality': 'Gruff, loyal.'},
]

# A made-up city as a tester writes it from the template: places, a few people and little else, so every block the
# app fills in by itself (careers, media, names, holidays) comes from the app's own defaults for a fantasy world.
OWN_CITY = {
    'id': 'thornhaven', 'name': 'Thornhaven', 'country': 'The Thorn Isles', 'region': 'Ironreach',
    'era': 'medieval', 'setting': 'original', 'timezone': 'Europe/London', 'calendar': 'none',
    'summary': 'A walled river town of guilds, temples and a brawling pit, ruled by a council of wardens.',
    'neighborhoods': [
        {'id': 'pit-ward', 'name': 'Pit Ward', 'summary': 'Fighting pits, taverns and loud nights.'},
        {'id': 'temple-hill', 'name': 'Temple Hill', 'summary': 'Monasteries, shrines and quiet gardens.'},
        {'id': 'harbour-row', 'name': 'Harbour Row', 'summary': 'Docks, fishmongers and shipwrights.'},
    ],
    'places': [
        {'id': 'the-pit', 'name': 'The Pit', 'kind': 'arena', 'neighborhood': 'pit-ward',
         'summary': 'A sunken fighting ring with roaring crowds.'},
        {'id': 'brass-tankard', 'name': 'The Brass Tankard', 'kind': 'tavern', 'neighborhood': 'pit-ward',
         'summary': 'Ale, stew and arguments.'},
        {'id': 'moonwell-temple', 'name': 'Moonwell Temple', 'kind': 'temple', 'neighborhood': 'temple-hill',
         'summary': 'An old temple around a still pool.'},
        {'id': 'saltmarket', 'name': 'The Saltmarket', 'kind': 'market', 'neighborhood': 'harbour-row',
         'summary': 'Stalls of fish, rope and gossip.'},
        {'id': 'warden-hall', 'name': 'Warden Hall', 'kind': 'hall', 'neighborhood': 'temple-hill',
         'summary': 'Where the wardens sit in council.'},
    ],
    'notables': [
        {'name': 'Kael Ironjaw', 'role': 'Pit champion', 'place': 'the-pit', 'pronouns': 'he/him', 'age': 33},
        {'name': 'Sister Veyra', 'role': 'High priestess', 'place': 'moonwell-temple', 'pronouns': 'she/her',
         'age': 61},
    ],
}

OWN = [
    {'name': 'Garrick Stone', 'relationship': 'romance', 'starting_closeness': 3, 'timezone': 'Europe/London',
     'identity': '32. He/him. A pit fighter who runs the Pit and drinks at the Brass Tankard.',
     'personality': 'Brash, proud, protective of his mother.'},
    {'name': 'Liss Arden', 'relationship': 'friendship', 'timezone': 'Europe/London',
     'identity': '26. She/her. A novice at Moonwell Temple.', 'personality': 'Serene, nosy.'},
]

WORLDS = {
    'town': {'city': 'chicago', 'companions': TOWN, 'earth': True},
    'ship': {'city': 'long-meridian', 'companions': SHIP, 'earth': False, 'aboard': True},
    'camelot': {'city': 'camelot', 'companions': FANTASY, 'earth': False},
    'grandport': {'city': 'grandport', 'companions': FANTASY, 'earth': False},
    'own-city': {'city': 'thornhaven', 'own_city': OWN_CITY, 'companions': OWN, 'earth': False},
}

# What the user does by hand in every world, on the first companion (the "main" one) unless it says otherwise.
HOBBY_BY_HAND = 'Archery'
JOB_BY_HAND = {'job': 'Scribe', 'employer': 'The Harbour Office'}
MOM_BY_HAND = {'name': 'Hollis', 'role': 'mom', 'pronouns': 'she/her', 'age': 58, 'local': True}
FRIEND_AGE_BY_HAND = 47
PET_BY_HAND = {'name': 'Biscuit', 'kind': 'cat', 'looks': 'ginger, missing half an ear', 'age': 6}
OWN_POST = 'Finally finished the big project at work. Celebrating with far too much cake tonight.'
