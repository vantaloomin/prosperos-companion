"""Original generation ship for Prospero Companion (Hit List #77). Run `python scripts/world/long_meridian.py` to
rewrite the shipped JSON.

The Long Meridian is invented: a generation ship of about twenty-six thousand people in the 188th year of its
voyage, with spun habitat rings, a forest deck, a weightless core and Port Vesper (port_vesper.py) flying beside it.
It is enclosed (companion/world/ships.py), so it has no weather, Earth seasons or cars, and its people travel only to
the station, by shuttle. Nothing is taken from any published setting.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'cities' / 'long-meridian.json'

SRC = 'curated-2026-10'
WHO = {'s': 'solo', 'f': 'friends', 'd': 'date', 'm': 'family', 'c': 'coworkers'}
WHEN = {'M': 'morning', 'A': 'afternoon', 'E': 'evening', 'L': 'late'}


def hood(id, name, summary, vibe, lon, lat, tier, rent, housing, walk, transit):
    out = {'id': id, 'name': name, 'summary': summary, 'vibe': vibe, 'lat': lat, 'lon': lon, 'rent_tier': tier}
    if rent:
        out['rent'] = {'studio': list(rent[0]), 'one_bedroom': list(rent[1]), 'two_bedroom': list(rent[2])}
    return out | {'housing': housing, 'walkability': walk, 'transit': transit, 'source': SRC}


def place(id, name, kind, hood_id, summary, tags, cost, setting, who, when, cuisine='', spots=()):
    out = {'id': id, 'name': name, 'kind': kind, 'neighborhood': hood_id, 'summary': summary, 'tags': tags,
           'cost': cost, 'setting': setting, 'good_for': [WHO[c] for c in who], 'day_parts': [WHEN[c] for c in when],
           'seasons': [], 'cuisine': cuisine}
    if spots:
        out['spots'] = list(spots)
    return out | {'source': SRC}


def employer(id, name, sector, hood_id, size, summary, careers):
    return {'id': id, 'name': name, 'sector': sector, 'neighborhood': hood_id, 'size': size, 'summary': summary,
            'careers': careers, 'source': SRC}


def career(id, name, sector, schedule, employment, pay, summary, themes):
    return {'id': id, 'name': name, 'sector': sector, 'schedule': schedule, 'employment': employment, 'pay': pay,
            'summary': summary, 'themes': themes, 'eras': ['future']}


def event(id, name, months, hood_id, summary):
    return {'id': id, 'name': name, 'months': months, 'neighborhood': hood_id, 'summary': summary, 'source': SRC}


def colour(id, name, kind, summary, places=()):
    return {'id': id, 'name': name, 'kind': kind, 'summary': summary, 'places': list(places), 'seasons': [],
            'source': SRC}


def price(id, item, low, high, per=''):
    return {'id': id, 'item': item, 'low': low, 'high': high, 'per': per, 'source': SRC}


def goal(id, text, steps, practice, progress, done, interest, bio):
    return {'id': id, 'text': text, 'steps': steps, 'practice': list(practice), 'progress': progress, 'done': done,
            'interest': interest, 'bio': bio}


def climate(summary, note):
    return {'summary': summary, 'months': [{'high_f': 70, 'low_f': 66, 'rain_days': 0, 'note': note}] * 12,
            'source': SRC}

T = ['on-foot', 'spine-tram', 'ring-lifts', 'pod-line']
CHEAP = ((520, 700), (720, 980), (1000, 1350))
MID = ((780, 1050), (1050, 1400), (1450, 1900))
HIGH = ((1100, 1450), (1450, 1950), (2000, 2700))
TOP = ((1500, 1950), (1950, 2600), (2700, 3600))

HOODS = [
    hood('the-bow', 'The Bow', 'The forward end of the ship: the great observation dome, the observatory, navigation '
         'and a few prized cabins with the stars ahead in the window.', ['views', 'quiet', 'stargazing'],
         -139.952, 0.0, 'very-high', TOP, ['view-cabin', 'cabin'], 'high', ['on-foot', 'spine-tram']),
    hood('command-deck', 'Command Deck', 'The bridge, the Voyage Council chamber, the Archive and the offices that '
         'keep twenty-six thousand people fed, housed and counted.', ['civic', 'offices', 'formal'],
         -139.962, 0.004, 'high', HIGH, ['cabin', 'officers-quarters'], 'high', ['on-foot', 'spine-tram', 'ring-lifts']),
    hood('founders-ring', "Founders' Ring", 'The oldest habitat ring, spun up in the first year of the voyage: '
         'terraced family berths, the Founders\' Hall, worn handrails and the quietest corridors aboard.',
         ['historic', 'family', 'quiet'], -139.972, 0.012, 'high', HIGH, ['family-berth', 'terrace-berth', 'cabin'],
         'high', ['on-foot', 'ring-lifts', 'pod-line']),
    hood('lantern-ring', 'Lantern Ring', 'The ring that never sleeps: noodle bars, the theatre, the night market, '
         'paper lanterns strung along the curve and music from every other hatch.',
         ['nightlife', 'food', 'lively'], -139.972, -0.012, 'mid', MID, ['cabin', 'shared-berth', 'loft-cabin'],
         'high', ['on-foot', 'ring-lifts', 'pod-line']),
    hood('arboretum', 'The Arboretum', 'Four hundred metres of forest under a painted sky: oaks and fruit trees '
         'grown from the founders\' seeds, a stream, a pond and paths worn by six generations.',
         ['green', 'calm', 'outdoorsy'], -139.982, 0.0, 'high', HIGH, ['garden-cabin', 'cabin'], 'high',
         ['on-foot', 'spine-tram']),
    hood('green-decks', 'Green Decks', 'Stacked hydroponic farms, algae vats, mushroom caves and the seed vault, '
         'lit purple and pink, with growers\' berths along the service corridors.',
         ['farming', 'working', 'humid'], -139.992, 0.01, 'low', CHEAP, ['crew-berth', 'cabin', 'shared-berth'],
         'medium', ['on-foot', 'spine-tram', 'pod-line']),
    hood('commons-ring', 'Commons Ring', 'The everyday ring: the clinic, schools, the big mess hall, shops, '
         'playrooms and the family cabins most people grow up in.', ['family', 'everyday', 'neighbourly'],
         -139.992, -0.012, 'mid', MID, ['family-berth', 'cabin', 'shared-berth'], 'high',
         ['on-foot', 'ring-lifts', 'pod-line']),
    hood('academy-deck', 'Academy Deck', 'The Meridian Academy and the Conservatory, the long library, study '
         'lounges that stay lit all night and students\' bunkrooms above the lecture halls.',
         ['students', 'studious', 'young'], -140.002, 0.008, 'mid', MID, ['bunkroom', 'shared-berth', 'cabin'],
         'high', ['on-foot', 'spine-tram', 'ring-lifts']),
    hood('the-spindle', 'The Spindle', 'The weightless core the rings turn around: the zero-g gym, the flight '
         'hall, the drop pool and the long low-gravity running track.', ['sport', 'zero-g', 'energetic'],
         -140.012, 0.0, 'mid', MID, ['cabin', 'crew-berth'], 'medium', ['on-foot', 'spine-tram', 'ring-lifts']),
    hood('tidewater-deck', 'Tidewater Deck', 'The ship\'s great water tank, with a warm swimming lagoon on top, '
         'the reclamation plant below and cabins along the lido rail.', ['water', 'leisure', 'relaxed'],
         -140.022, -0.01, 'mid', MID, ['cabin', 'family-berth'], 'high', ['on-foot', 'spine-tram', 'pod-line']),
    hood('cargo-holds', 'Cargo Holds', 'Cavernous holds of crates and spares, the fabrication shops, the '
         'Quartermaster\'s stores and the Swap, the ship\'s sprawling trading floor.',
         ['industrial', 'trade', 'busy'], -140.032, 0.01, 'low', CHEAP, ['crew-berth', 'loft-cabin', 'shared-berth'],
         'medium', ['on-foot', 'spine-tram', 'pod-line']),
    hood('dockside', 'Dockside', 'The shuttle bays and docking ring: customs, the traders from Port Vesper, '
         'travellers\' bunks and the bars where crews wait out a delayed launch.', ['travel', 'trade', 'transient'],
         -140.042, -0.006, 'mid', MID, ['cabin', 'shared-berth', 'bunkroom'], 'medium',
         ['on-foot', 'spine-tram', 'pod-line']),
    hood('engine-decks', 'Engine Decks', 'Reactor halls, the drive and the engineers who keep them: warm decks, '
         'loud bars, steady shifts and the best cheap food on the ship.', ['working', 'loud', 'tight-knit'],
         -140.052, 0.006, 'low', CHEAP, ['crew-berth', 'shared-berth', 'cabin'], 'medium',
         ['on-foot', 'spine-tram', 'pod-line']),
    hood('stern-gallery', 'Stern Gallery', 'The aft end, old crew quarters turned into studios and cheap '
         'cabins, with the stern viewport where the Sun is one bright star among thousands.',
         ['artsy', 'bohemian', 'quiet'], -140.062, 0.0, 'low', CHEAP, ['loft-cabin', 'cabin', 'shared-berth'],
         'high', ['on-foot', 'spine-tram']),
]

P = [
    # The Bow
    place('bow-dome', 'The Bow Dome', 'landmark', 'the-bow', 'The great clear dome at the very front of the ship, '
          'where the stars ahead seem to stand still and people come to sit in silence.',
          ['viewport', 'stars', 'quiet'], 'free', 'indoor', 'sdfm', 'MAEL', spots=['the front rail',
          'the dark benches at the back', 'the star chart table']),
    place('meridian-observatory', 'Meridian Observatory', 'museum', 'the-bow', 'The ship\'s working observatory, '
          'open to visitors in the afternoons, with a gallery of the first star charts made aboard.',
          ['astronomy', 'telescopes', 'history'], '$', 'indoor', 'sfm', 'AE'),
    place('forward-lounge', 'The Forward Lounge', 'bar', 'the-bow', 'A hushed cocktail lounge under the dome, '
          'all low lights and deep chairs, where couples book a window table for anniversaries.',
          ['cocktails', 'romantic', 'views'], '$$$', 'indoor', 'sdf', 'EL', spots=['a window table',
          'the long bar', 'the corner booth']),
    place('starward-cafe', 'Starward Cafe', 'cafe', 'the-bow', 'A small, bright cafe by the dome stairs, with '
          'pastries from the Commons bakery and a board of what the navigators saw this week.',
          ['coffee', 'pastries', 'views'], '$$', 'indoor', 'sfdc', 'MA', 'ship-fusion'),
    place('the-chart-room', 'The Chart Room', 'restaurant', 'the-bow', 'The ship\'s finest restaurant, a tasting '
          'menu built from whatever the Green Decks harvested that morning, served under the star charts.',
          ['tasting-menu', 'fine-dining', 'special-occasion'], '$$$$', 'indoor', 'dfm', 'E', 'ship-fusion'),
    place('quiet-chapel', 'The Quiet Chapel', 'temple', 'the-bow', 'A plain room open to every faith and none, '
          'with a single viewport and a book where people write the names of those they have lost.',
          ['chapel', 'reflection', 'memorial'], 'free', 'indoor', 'sm', 'MAE'),
    # Command Deck
    place('council-chamber', 'The Council Chamber', 'landmark', 'command-deck', 'The round chamber where the '
          'Voyage Council meets in the open, with a public gallery that fills up for any vote about rations.',
          ['civic', 'debates', 'history'], 'free', 'indoor', 'sf', 'MA'),
    place('ship-archive', 'The Archive', 'library', 'command-deck', 'Every log, letter, birth and recipe since '
          'launch, with reading booths, an archivist on duty and a waiting list for the founders\' diaries.',
          ['archive', 'records', 'quiet'], 'free', 'indoor', 's', 'MA'),
    place('bridge-mess', 'Bridge Mess', 'restaurant', 'command-deck', 'The officers\' canteen, open to all, '
          'known for its strong coffee, cheap set lunches and loud arguments about course corrections.',
          ['canteen', 'set-lunch', 'officers'], '$', 'indoor', 'sc', 'MA', 'ship-fusion'),
    place('log-and-ledger', 'Log & Ledger', 'bar', 'command-deck', 'A wood-panelled bar for clerks and officers '
          'after shift, with a brass bell rung whenever someone retires.', ['after-work', 'quiet', 'officers'],
          '$$', 'indoor', 'fc', 'EL'),
    place('voyage-museum', 'Museum of the Voyage', 'museum', 'command-deck', 'The story of the Meridian from the '
          'shipyards of Earth to today, with the launch bell, a founder\'s cabin kept as it was and the '
          'patched panel from the Breach.', ['history', 'exhibits', 'family-friendly'], '$', 'indoor', 'sfm', 'MA'),
    place('signal-tea-house', 'Signal Tea House', 'cafe', 'command-deck', 'A narrow tea house beside the comms '
          'office, with leaf teas grown on the Green Decks and a back room for quiet meetings.',
          ['tea', 'quiet', 'meetings'], '$', 'indoor', 'sdc', 'MA'),
    # Founders' Ring
    place('founders-hall', "Founders' Hall", 'landmark', 'founders-ring', 'The ring\'s meeting hall, with the '
          'names of the first four thousand aboard carved into the walls and dances on rest days.',
          ['history', 'dances', 'community'], 'free', 'indoor', 'sfm', 'AE'),
    place('old-galley', 'The Old Galley', 'restaurant', 'founders-ring', 'A family restaurant in the ring\'s '
          'first kitchen, cooking the founders\' recipes: long-simmered bean stew, flatbread and rice pudding.',
          ['comfort-food', 'family', 'history'], '$$', 'indoor', 'fdm', 'AE', 'ship-heritage'),
    place('terrace-steps', 'The Terrace Steps', 'park', 'founders-ring', 'Planted steps climbing the curve of the '
          'ring, where children race the handrails and older people sit with tea in the long evenings.',
          ['terraces', 'planters', 'benches'], 'free', 'indoor', 'sfdm', 'MAE'),
    place('rivet-and-thread', 'Rivet & Thread', 'shopping', 'founders-ring', 'A tailor and mender who can turn a '
          'grandparent\'s jacket into something new, and still sells the plain grey ship-wool.',
          ['tailor', 'mending', 'clothes'], '$$', 'indoor', 's', 'MA'),
    place('first-light-bakery', 'First Light Bakery', 'cafe', 'founders-ring', 'The ring\'s bakery since year '
          'one, with a queue at the morning bell for seed loaves and honey buns.', ['bakery', 'bread', 'morning'],
          '$', 'indoor', 'sfm', 'M'),
    place('the-handrail', 'The Handrail', 'bar', 'founders-ring', 'A tiny old bar with eight stools and a '
          'handrail polished by two hundred years of elbows; the landlord knows everyone\'s grandparents.',
          ['local', 'cosy', 'regulars'], '$', 'indoor', 'sf', 'EL'),
    place('founders-garden', "Founders' Garden", 'garden', 'founders-ring', 'A walled garden of herbs and roses '
          'kept by volunteers, with a sundial that works off the ring\'s lamps.', ['herbs', 'roses', 'volunteers'],
          'free', 'indoor', 'sdm', 'MA'),
    # Lantern Ring
    place('lantern-night-market', 'Lantern Night Market', 'market', 'lantern-ring', 'Two hundred stalls under '
          'paper lanterns along the curve: dumplings, cricket skewers, secondhand screens, charms and haircuts.',
          ['street-food', 'stalls', 'lanterns'], '$', 'indoor', 'sfd', 'EL', 'ship-street-food',
          ['the dumpling row', 'the charm stalls', 'the long tables by the lift']),
    place('red-hatch-noodles', 'Red Hatch Noodles', 'restaurant', 'lantern-ring', 'A steamy noodle bar behind a '
          'red-painted hatch, open until the small hours, with broth that has been on the go for decades.',
          ['noodles', 'late-night', 'cheap'], '$', 'indoor', 'sfc', 'AEL', 'ship-street-food'),
    place('lantern-theatre', 'The Lantern Theatre', 'venue', 'lantern-ring', 'The ship\'s main stage: new plays '
          'by ship-born writers, old Earth classics and a winter pantomime the whole ship argues about.',
          ['theatre', 'plays', 'shows'], '$$', 'indoor', 'fdm', 'E'),
    place('the-loop', 'The Loop', 'nightlife', 'lantern-ring', 'A dance club in a disused cargo lift, where the '
          'floor turns slowly with the ring and the DJs play until the morning lights come up.',
          ['dancing', 'djs', 'late-night'], '$$', 'indoor', 'fd', 'L'),
    place('copper-kettle', 'The Copper Kettle', 'bar', 'lantern-ring', 'A loud, friendly bar with ship-brewed '
          'ales, quiz nights and a corner stage for anyone brave enough with a fiddle.',
          ['ales', 'quiz', 'live-music'], '$$', 'indoor', 'fc', 'EL'),
    place('paper-moon-cafe', 'Paper Moon Cafe', 'cafe', 'lantern-ring', 'A cafe full of mismatched chairs and '
          'paper lanterns, where writers and night-shift workers share the long table.',
          ['coffee', 'writers', 'all-night'], '$', 'indoor', 'sf', 'MAEL'),
    place('sweet-orbit', 'Sweet Orbit', 'shopping', 'lantern-ring', 'A sweet shop of jars and hand-pulled '
          'sugar, famous for the moon drops children save their credits for.', ['sweets', 'treats', 'kids'],
          '$', 'indoor', 'sm', 'AE'),
    place('ring-cinema', 'Ring Cinema', 'venue', 'lantern-ring', 'A two-screen cinema showing films from the '
          'Earth archive and the ship\'s own studios, with a midnight double bill on rest days.',
          ['films', 'cinema', 'date-night'], '$$', 'indoor', 'fdm', 'AEL'),
    # The Arboretum
    place('arboretum-paths', 'The Arboretum Paths', 'park', 'arboretum', 'Winding paths under oak, beech and '
          'fruit trees, with a stream fed from the tank and a painted sky that turns to dusk on schedule.',
          ['forest', 'walking', 'trees'], 'free', 'mixed', 'sfdm', 'MAE', spots=['the old oak', 'the stream bridge',
          'the fern hollow', 'the orchard walk']),
    place('lily-pond', 'The Lily Pond', 'park', 'arboretum', 'A still pond at the heart of the forest, with '
          'ducks descended from the founders\' six and a jetty where couples sit at dusk.',
          ['pond', 'ducks', 'romantic'], 'free', 'mixed', 'sdm', 'MAE'),
    place('orchard-kitchen', 'Orchard Kitchen', 'restaurant', 'arboretum', 'A glass-walled restaurant among the '
          'apple trees, serving whatever is ripe, with cider pressed on the spot.', ['seasonal', 'cider', 'views'],
          '$$$', 'indoor', 'dfm', 'AE', 'ship-heritage'),
    place('ranger-hut', "The Rangers' Hut", 'cafe', 'arboretum', 'A wooden kiosk run by the arboretum rangers, '
          'selling tea, flapjacks and nature trail maps for children.', ['tea', 'snacks', 'family-friendly'], '$',
          'mixed', 'sm', 'MA'),
    place('canopy-walk', 'The Canopy Walk', 'attraction', 'arboretum', 'A rope bridge strung through the tops of '
          'the tallest trees, close enough to touch the painted sky.', ['treetops', 'bridges', 'views'], '$',
          'mixed', 'sfdm', 'MA'),
    place('seed-library', 'The Seed Library', 'library', 'arboretum', 'Drawers of seeds anyone can borrow and '
          'return as next year\'s harvest, with growing classes on rest-day mornings.',
          ['seeds', 'gardening', 'classes'], 'free', 'indoor', 'sm', 'MA'),
    # Green Decks
    place('green-deck-canteen', 'The Green Canteen', 'restaurant', 'green-decks', 'A long canteen where growers '
          'eat at shared tables: big bowls of greens, mushroom broth and bread still warm.',
          ['canteen', 'fresh', 'cheap'], '$', 'indoor', 'sc', 'MA', 'ship-heritage'),
    place('mushroom-caves', 'The Mushroom Caves', 'attraction', 'green-decks', 'Dim, damp racks of oyster and '
          'shiitake under red light, with tours on rest days and a stall selling the day\'s pick.',
          ['mushrooms', 'tours', 'farms'], '$', 'indoor', 'sfm', 'MA'),
    place('pink-light-bar', 'Pink Light', 'bar', 'green-decks', 'A grower\'s bar bathed in the farms\' pink grow '
          'light, pouring sour beer brewed from the algae vats, which tastes better than it sounds.',
          ['algae-beer', 'growers', 'cheap'], '$', 'indoor', 'fc', 'EL'),
    place('seed-vault-gallery', 'Seed Vault Gallery', 'museum', 'green-decks', 'A viewing gallery over the frozen '
          'seed vault, with the story of every crop the ship carries.', ['seeds', 'science', 'quiet'], 'free',
          'indoor', 'sm', 'MA'),
    place('greens-market', 'Greens Market', 'market', 'green-decks', 'The morning market at the farm gate: '
          'herbs, tomatoes, mushrooms and the odd strawberry, sold off the harvest trolleys.',
          ['produce', 'market', 'morning'], '$', 'indoor', 'sm', 'M'),
    place('sprout-cafe', 'Sprout', 'cafe', 'green-decks', 'A cafe in an old pump room, with sprouted-grain toast, '
          'fresh mint tea and growers swapping gossip before shift.', ['tea', 'toast', 'growers'], '$', 'indoor',
          'sfc', 'MA'),
    # Commons Ring
    place('commons-mess-hall', 'Commons Mess Hall', 'restaurant', 'commons-ring', 'The ship\'s biggest mess hall, '
          'loud and warm, with long tables, a different stew every day and a pudding queue that never shortens.',
          ['mess-hall', 'family', 'cheap'], '$', 'indoor', 'sfmc', 'MAE', 'ship-heritage',
          ['the long tables', 'the pudding queue', 'the family corner']),
    place('commons-playdeck', 'The Playdeck', 'park', 'commons-ring', 'A padded play deck with climbing nets, a '
          'sandpit and benches where every parent on the ring meets every other.',
          ['playground', 'kids', 'parents'], 'free', 'indoor', 'm', 'MA'),
    place('commons-baths', 'Commons Baths', 'fitness', 'commons-ring', 'Public baths with a hot pool, a cold '
          'plunge and a steam room, busiest after the day shift.', ['baths', 'steam', 'relaxing'], '$', 'indoor',
          'sf', 'AE'),
    place('ring-stores', 'Ring Stores', 'shopping', 'commons-ring', 'The ring\'s general store: rations, soap, '
          'socks, batteries and a noticeboard thick with lost cats and spare cabins.',
          ['groceries', 'everyday', 'noticeboard'], '$', 'indoor', 's', 'MAE'),
    place('two-moons-cafe', 'Two Moons', 'cafe', 'commons-ring', 'A family-run cafe by the school lift, with '
          'proper coffee for parents and hot chocolate for whoever survived the school run.',
          ['coffee', 'family', 'cosy'], '$', 'indoor', 'sfm', 'MA'),
    place('commons-pet-clinic', 'Commons Pet Clinic', 'vet', 'commons-ring', 'The ship\'s animal clinic for cats, '
          'rabbits, birds and the odd lizard, with a waiting room full of carriers.', ['pets', 'vet', 'animals'],
          '$$', 'indoor', 's', 'MA'),
    place('the-gathering', 'The Gathering', 'bar', 'commons-ring', 'The ring\'s family pub, with a games corner, '
          'cheap pies and darts that every child is warned about.', ['pub', 'games', 'family-friendly'], '$',
          'indoor', 'fmc', 'AE'),
    place('ring-library', 'Commons Library', 'library', 'commons-ring', 'A friendly lending library with story '
          'hours, game nights and the ship\'s best collection of old Earth picture books.',
          ['books', 'story-time', 'games'], 'free', 'indoor', 'sm', 'MAE'),
    # Academy Deck
    place('long-library', 'The Long Library', 'library', 'academy-deck', 'A library that runs the full length '
          'of the deck, open all night, with study pods, a reading room and the ship\'s rare printed books.',
          ['books', 'study', 'all-night'], 'free', 'indoor', 's', 'MAEL', spots=['a study pod',
          'the reading room', 'the rare books desk']),
    place('lecture-steps', 'The Lecture Steps', 'square', 'academy-deck', 'Wide steps outside the main hall '
          'where students eat lunch, argue and hold impromptu concerts.', ['students', 'lunch', 'gathering'],
          'free', 'indoor', 'sf', 'MA'),
    place('ink-and-orbit', 'Ink & Orbit', 'cafe', 'academy-deck', 'A cramped student cafe with cheap coffee, '
          'sticky tables and a wall of notes offering tutoring, bands and spare bunks.',
          ['coffee', 'students', 'cheap'], '$', 'indoor', 'sf', 'MAE'),
    place('the-thesis', 'The Thesis', 'bar', 'academy-deck', 'The students\' bar, with cheap ale, a debating '
          'night and a pool table older than anyone\'s grandparents.', ['students', 'debates', 'cheap'], '$',
          'indoor', 'f', 'EL'),
    place('conservatory-hall', 'Conservatory Hall', 'venue', 'academy-deck', 'The Conservatory\'s concert hall, '
          'with free lunchtime recitals and a full orchestra season.', ['concerts', 'classical', 'recitals'],
          '$$', 'indoor', 'sdm', 'AE'),
    place('dumpling-desk', 'The Dumpling Desk', 'restaurant', 'academy-deck', 'A counter of steamed dumplings '
          'sold by the dozen to students who should be studying.', ['dumplings', 'cheap', 'quick'], '$', 'indoor',
          'sf', 'AEL', 'ship-street-food'),
    # The Spindle
    place('zero-g-gym', 'Zero-G Gym', 'fitness', 'the-spindle', 'A weightless gym of nets and handholds, where '
          'the workout is mostly not drifting into someone else.', ['zero-g', 'fitness', 'classes'], '$$', 'indoor',
          'sf', 'MAE'),
    place('flight-hall', 'The Flight Hall', 'stadium', 'the-spindle', 'A weightless arena for the ship\'s '
          'favourite sport, hoopball, with rival deck teams and a roaring crowd strapped into the stands.',
          ['hoopball', 'sport', 'crowds'], '$$', 'indoor', 'fm', 'E'),
    place('drop-pool', 'The Drop Pool', 'attraction', 'the-spindle', 'A sphere of water held in low gravity, which '
          'swimmers fall into slowly from the gallery above.', ['swimming', 'low-gravity', 'thrills'], '$$',
          'indoor', 'sfd', 'AE'),
    place('core-track', 'The Core Track', 'fitness', 'the-spindle', 'A running track around the core at a '
          'third of a gravity, where every stride feels like a leap.', ['running', 'low-gravity', 'fitness'],
          'free', 'indoor', 'sf', 'MA'),
    place('hub-juice-bar', 'Hub Juice', 'cafe', 'the-spindle', 'A juice bar at the core lift with squeeze bulbs '
          'for the weightless side, and real cups for everyone else.', ['juice', 'smoothies', 'sport'], '$',
          'indoor', 'sf', 'MA'),
    place('the-tether', 'The Tether', 'bar', 'the-spindle', 'A sports bar at the edge of the core where hoopball '
          'fans watch the replays and drink from bulbs because the glasses kept floating off.',
          ['sport', 'replays', 'fans'], '$$', 'indoor', 'f', 'EL'),
    # Tidewater Deck
    place('tidewater-lagoon', 'Tidewater Lagoon', 'park', 'tidewater-deck', 'A warm swimming lagoon on top of the '
          'great tank, with sand made from crushed glass and a painted horizon.',
          ['swimming', 'lido', 'sunlamps'], '$', 'mixed', 'sfdm', 'MA', spots=['the shallow end',
          'the sunlamp loungers', 'the diving board']),
    place('lido-kiosk', 'The Lido Kiosk', 'cafe', 'tidewater-deck', 'A striped kiosk selling ices, tea and fried '
          'algae crisps to swimmers on the lagoon steps.', ['ices', 'snacks', 'family-friendly'], '$', 'mixed',
          'sfm', 'MA'),
    place('reclamation-tour', 'Reclamation Works Tour', 'attraction', 'tidewater-deck', 'A guided walk through the '
          'plant that cleans every drop of water aboard, ending with a glass of it.',
          ['tours', 'engineering', 'water'], 'free', 'indoor', 'sm', 'A'),
    place('shell-and-salt', 'Shell & Salt', 'restaurant', 'tidewater-deck', 'A lagoon-side restaurant serving '
          'tank-farmed prawns and mussels with ship-grown lemon.', ['seafood', 'views', 'date-night'], '$$$',
          'indoor', 'dfm', 'AE', 'ship-fusion'),
    place('tank-view-bar', 'The Tank Window', 'bar', 'tidewater-deck', 'A bar built against the tank wall, with '
          'a great window into the blue where fish drift past the bottles.', ['aquarium', 'cocktails', 'views'],
          '$$', 'indoor', 'fd', 'EL'),
    place('the-wave-room', 'The Wave Room', 'fitness', 'tidewater-deck', 'A wave pool for surf lessons on '
          'machine-made breakers, with the ship\'s best-tanned instructors.', ['surfing', 'lessons', 'waves'],
          '$$', 'indoor', 'sf', 'MA'),
    # Cargo Holds
    place('the-swap', 'The Swap', 'market', 'cargo-holds', 'A trading floor the size of a field, where anything '
          'aboard can be bartered: tools, clothes, seeds, old screens and favours.',
          ['barter', 'secondhand', 'bargains'], '$', 'indoor', 'sf', 'MA', spots=['the tool tables',
          'the clothes rails', 'the favour board']),
    place('hold-nine-diner', 'Hold Nine Diner', 'restaurant', 'cargo-holds', 'A diner in a shipping container, '
          'serving fry-ups and strong tea to loaders on every shift.', ['diner', 'fry-up', 'all-hours'], '$',
          'indoor', 'sc', 'MAEL', 'ship-heritage'),
    place('fab-shop', 'The Fab Shop', 'workshop', 'cargo-holds', 'A public fabrication workshop with printers, '
          'lathes and looms, and a volunteer who will show anyone how.', ['makers', 'printers', 'classes'], '$',
          'indoor', 'sf', 'MAE'),
    place('crate-and-barrel', 'Crate & Barrel', 'bar', 'cargo-holds', 'A bar built from cargo crates, run by a '
          'retired loader who pours the strongest still-spirit aboard.', ['spirits', 'loaders', 'rough'], '$',
          'indoor', 'fc', 'EL'),
    place('quartermasters-stores', "The Quartermaster's Stores", 'shopping', 'cargo-holds', 'Where every new '
          'cabin is kitted out: bedding, pans, lamps and the dreaded ration book.', ['supplies', 'homeware',
          'rations'], '$', 'indoor', 's', 'MA'),
    place('hold-climbing-wall', 'The Hold Wall', 'fitness', 'cargo-holds', 'A climbing wall on the side of a '
          'stack of crates sixty metres high, with a cafe at the top.', ['climbing', 'fitness', 'views'], '$$',
          'indoor', 'sf', 'AE'),
    # Dockside
    place('shuttle-concourse', 'Shuttle Concourse', 'landmark', 'dockside', 'The bright hall where the shuttles '
          'from Port Vesper dock, with a board of arrivals and a wall of reunion photos.',
          ['shuttles', 'arrivals', 'travel'], 'free', 'indoor', 'sfm', 'MAEL'),
    place('waiting-room-bar', 'The Waiting Room', 'bar', 'dockside', 'A bar for crews and passengers waiting on a '
          'launch window, with the departures board over the taps.', ['travellers', 'crews', 'departures'], '$$',
          'indoor', 'sfc', 'AEL'),
    place('docking-ring-noodles', 'Docking Ring Noodles', 'restaurant', 'dockside', 'A noodle counter by the '
          'airlocks feeding pilots, traders and customs officers at all hours.', ['noodles', 'quick', 'all-hours'],
          '$', 'indoor', 'sc', 'MAEL', 'ship-street-food'),
    place('vesper-traders-row', "Vesper Traders' Row", 'market', 'dockside', 'Stalls of goods brought over from '
          'Port Vesper: station spices, real wool, new music and gadgets nobody aboard can make yet.',
          ['imports', 'traders', 'gadgets'], '$$', 'indoor', 'sf', 'MA'),
    place('berth-inn', 'The Berth Inn', 'inn', 'dockside', 'A travellers\' inn of pod bunks and a few proper rooms, '
          'with a breakfast room that smells of station coffee.', ['inn', 'travellers', 'breakfast'], '$$',
          'indoor', 'sf', 'MAEL'),
    place('airlock-cafe', 'The Airlock', 'cafe', 'dockside', 'A tiny cafe between the customs desks where pilots '
          'drink coffee before launch and swap gossip from the station.', ['coffee', 'pilots', 'gossip'], '$',
          'indoor', 'sc', 'MA'),
    # Engine Decks
    place('reactor-gallery', 'Reactor Gallery', 'attraction', 'engine-decks', 'A shielded viewing gallery over '
          'the reactor hall, with a guide from the engine crew on open days.', ['engineering', 'tours', 'glow'],
          'free', 'indoor', 'sfm', 'A'),
    place('the-coolant', 'The Coolant', 'bar', 'engine-decks', 'The engineers\' bar: warm, loud, cheap, with '
          'shift bells on the wall and a jukebox nobody admits to filling.', ['engineers', 'loud', 'cheap'], '$',
          'indoor', 'fc', 'EL'),
    place('pressure-pot', 'The Pressure Pot', 'restaurant', 'engine-decks', 'A spicy one-pot kitchen beloved by '
          'engine crews, where the chilli is graded by reactor output.', ['spicy', 'cheap', 'hearty'], '$',
          'indoor', 'sfc', 'AEL', 'ship-street-food'),
    place('shift-change-cafe', 'Shift Change', 'cafe', 'engine-decks', 'A cafe that opens at every shift bell, '
          'with breakfast for the night crew and bedtime tea for the day crew.', ['coffee', 'breakfast', 'crews'],
          '$', 'indoor', 'sc', 'MAEL'),
    place('engine-boxing-club', 'Engine Deck Boxing Club', 'fitness', 'engine-decks', 'A sweaty boxing gym where '
          'engineers settle arguments with gloves on and buy each other a drink after.',
          ['boxing', 'gym', 'community'], '$', 'indoor', 'sf', 'AE'),
    place('drive-hall-museum', 'The Drive Hall', 'museum', 'engine-decks', 'The old drive housing, now a museum of '
          'engines with a model of the ship\'s path and a button children are allowed to press.',
          ['engineering', 'history', 'kids'], '$', 'indoor', 'sm', 'MA'),
    # Stern Gallery
    place('stern-viewport', 'The Stern Viewport', 'landmark', 'stern-gallery', 'A long window looking back the '
          'way the ship came, where the Sun is one bright star among thousands.', ['viewport', 'sun', 'reflection'],
          'free', 'indoor', 'sdm', 'MAEL', spots=['the Sun bench', 'the window seat', 'the guest book']),
    place('studio-row', 'Studio Row', 'shopping', 'stern-gallery', 'A corridor of open studios: potters, '
          'printmakers, jewellers and a glassblower who works off the ship\'s scrap glass.',
          ['art', 'studios', 'crafts'], '$$', 'indoor', 'sfd', 'AE'),
    place('the-wake', 'The Wake', 'bar', 'stern-gallery', 'An artists\' bar with poetry on rest-day evenings and '
          'walls covered in two hundred years of sketches.', ['poetry', 'artists', 'bohemian'], '$', 'indoor',
          'sfd', 'EL'),
    place('aft-gallery', 'The Aft Gallery', 'museum', 'stern-gallery', 'The ship\'s gallery of art made aboard, '
          'from the founders\' first paintings to this year\'s graduates.', ['art', 'exhibitions', 'free'], 'free',
          'indoor', 'sdm', 'AE'),
    place('slow-kettle', 'The Slow Kettle', 'cafe', 'stern-gallery', 'A cafe that brews every pot by hand and '
          'refuses to hurry, with board games and a cat called Ballast.', ['tea', 'board-games', 'cat'], '$',
          'indoor', 'sfd', 'MAE'),
    place('stern-kitchen', 'Stern Kitchen', 'restaurant', 'stern-gallery', 'A pay-what-you-can kitchen run by '
          'the artists\' co-op, with one dish a night and long shared tables.', ['co-op', 'shared-tables',
          'cheap'], '$', 'indoor', 'sfm', 'E', 'ship-heritage'),
]

EMPLOYERS = [
    employer('navigation-office', 'Navigation Office', 'aerospace', 'the-bow', 'medium', 'Keeps the ship on '
             'course: navigators, star cartographers and the astronomers at the observatory.',
             ['navigator', 'star-cartographer', 'observatory-astronomer', 'astrophysicist']),
    employer('the-bridge', 'The Bridge', 'aerospace', 'command-deck', 'medium', 'The officers who fly the ship, '
             'keep watch around the clock and talk to Port Vesper.', ['bridge-officer', 'comms-officer',
             'traffic-controller', 'navigator']),
    employer('voyage-council', 'The Voyage Council', 'government', 'command-deck', 'large', 'The elected council '
             'and the offices behind it: housing, the census, rations and every form aboard.',
             ['council-clerk', 'district-administrator', 'census-officer', 'housing-officer', 'rations-planner',
              'mediator']),
    employer('the-archive-office', 'The Archive', 'learning', 'command-deck', 'small', 'Keeps the ship\'s '
             'records, the founders\' papers and the museum.', ['archivist', 'heritage-curator']),
    employer('meridian-clinic', 'Meridian Clinic', 'healthcare', 'commons-ring', 'large', 'The ship\'s hospital '
             'and clinics, from births to bad backs.', ['general-practitioner', 'clinic-nurse', 'night-ward-nurse',
             'surgeon', 'midwife', 'dispensary-pharmacist', 'medical-lab-technician', 'physiotherapist', 'dentist']),
    employer('commons-schools', 'Commons Schools', 'education', 'commons-ring', 'large', 'The ship\'s nurseries '
             'and schools, one on every ring.', ['schoolteacher', 'nursery-worker', 'tutor', 'counsellor']),
    employer('meridian-academy-employer', 'The Meridian Academy', 'education', 'academy-deck', 'large', 'The '
             'ship\'s academy, training engineers, medics, growers and the odd poet.',
             ['academy-lecturer', 'academy-student', 'archivist', 'software-developer']),
    employer('green-deck-farms', 'Green Deck Farms', 'agriculture', 'green-decks', 'large', 'Grows almost '
             'everything the ship eats, in stacked hydroponic racks, vats and caves.',
             ['hydroponics-technician', 'crop-scientist', 'algae-farm-worker', 'mushroom-grower',
              'pollination-technician', 'ecosystem-biologist']),
    employer('arboretum-trust', 'The Arboretum Trust', 'gardens', 'arboretum', 'medium', 'Keeps the forest, '
             'the pond and the seed library alive.', ['arboretum-keeper', 'arboretum-ranger', 'ecosystem-biologist']),
    employer('life-support-division', 'Life Support', 'engineering', 'tidewater-deck', 'large', 'Air, water and '
             'warmth for every cabin: the reclamation plant, the scrubbers and the tank.',
             ['life-support-engineer', 'water-reclamation-technician', 'air-systems-technician',
              'environmental-controller', 'tank-diver']),
    employer('engine-crew', 'Engine Crew', 'engineering', 'engine-decks', 'large', 'Runs the reactor and the '
             'drive on round-the-clock shifts.', ['reactor-technician', 'propulsion-engineer',
             'power-grid-technician', 'radiation-safety-officer', 'drive-watch-engineer']),
    employer('hull-works', 'Hull Works', 'engineering', 'cargo-holds', 'medium', 'Patches, inspects and '
             'rebuilds the hull and the rings.', ['hull-technician', 'pressure-welder', 'habitat-builder',
             'drone-operator', 'robotics-technician']),
    employer('quartermasters-office', "Quartermaster's Office", 'logistics', 'cargo-holds', 'large', 'Every '
             'crate, spare part and ration aboard, counted, stored and handed out.',
             ['quartermaster', 'cargo-handler', 'freight-scheduler', 'supply-chain-manager', 'corridor-courier']),
    employer('fabrication-guild', 'Fabrication Guild', 'manufacturing', 'cargo-holds', 'medium', 'Makes what the '
             'ship cannot get from the station: parts, tools, furniture and clothes.',
             ['fabrication-technician', 'machinist', 'cabin-fitter', 'tailor']),
    employer('dock-control', 'Dock Control', 'aerospace', 'dockside', 'medium', 'Runs the shuttle bays, the '
             'launch windows and the customs desks.', ['docking-controller', 'shuttle-pilot', 'customs-inspector',
             'flight-instructor', 'cargo-handler']),
    employer('ship-galleys', 'Ship Galleys', 'food', 'commons-ring', 'large', 'Runs the mess halls and the '
             'canteens, and the cultured-meat and food-printer plants behind them.',
             ['galley-cook', 'head-chef', 'canteen-baker', 'cultured-meat-technician', 'food-printer-technician',
              'nutritionist']),
    employer('lantern-ring-traders', 'Lantern Ring Traders', 'hospitality', 'lantern-ring', 'medium', 'The '
             'association of the ring\'s bars, stalls and noodle shops.', ['noodle-bar-owner', 'lounge-bartender',
             'coffee-bar-attendant', 'market-trader', 'brewer']),
    employer('lantern-theatre-company', 'Lantern Theatre Company', 'entertainment', 'lantern-ring', 'small',
             'The ship\'s theatre company, with a resident troupe and a winter pantomime.',
             ['stage-actor', 'session-musician', 'immersive-designer', 'event-coordinator']),
    employer('ship-feed', 'The Ship Feed', 'media', 'command-deck', 'small', 'The ship\'s news feed and '
             'broadcast, read in every mess hall at breakfast.', ['feed-reporter', 'broadcaster', 'photographer']),
    employer('watch-and-safety', 'Watch and Safety', 'public-safety', 'commons-ring', 'medium', 'The ship\'s '
             'watch officers, investigators and the fire-and-pressure crews.', ['security-officer', 'investigator',
             'fire-and-pressure-crew', 'rescue-specialist', 'emergency-medic']),
    employer('spindle-sports', 'Spindle Sports', 'recreation', 'the-spindle', 'small', 'Runs the zero-g gym, '
             'the drop pool and the hoopball league.', ['zero-g-coach', 'fitness-coach', 'pool-attendant',
             'hoopball-player']),
    employer('ship-transit', 'Ship Transit', 'transit', 'dockside', 'medium', 'Runs the spine tram, the ring '
             'lifts and the pod line.', ['transit-pod-operator', 'transit-dispatcher', 'lift-mechanic']),
    employer('ship-trades-pool', 'Trades Pool', 'trades', 'engine-decks', 'medium', 'Electricians, plumbers '
             'and fitters sent wherever something breaks.', ['electrician', 'plumber', 'lift-mechanic',
             'recycling-worker', 'waste-processing-technician']),
    employer('stern-artists-coop', "Stern Artists' Co-op", 'arts', 'stern-gallery', 'small', 'The studios and '
             'gallery of the stern, run by the artists themselves.', ['muralist', 'heritage-curator',
             'photographer', 'novelist', 'glassblower']),
    employer('ship-credit-office', 'Ship Credit Office', 'finance', 'command-deck', 'small', 'Keeps the credit '
             'ledger and the trade accounts with Port Vesper.', ['ledger-accountant', 'credit-broker',
             'trade-negotiator', 'insurance-assessor']),
]

CAREERS = [
    career('arboretum-ranger', 'Arboretum ranger', 'gardens', 'shift-day', 'rota', '$', 'Walks the arboretum '
           'paths, prunes, guides school groups and stops teenagers climbing the old oak.',
           ['the old oak', 'school groups', 'pruning', 'the ducks']),
    career('tank-diver', 'Tank diver', 'engineering', 'rotating', 'rota', '$$', 'Dives the great water tank to '
           'clean the filters, check the seals and count the fish.', ['the tank', 'filters', 'dive shifts',
           'the fish']),
    career('drive-watch-engineer', 'Drive watch engineer', 'engineering', 'shift-night', 'rota', '$$', 'Sits '
           'the long night watch over the drive, reading gauges and logging every hum.',
           ['the night watch', 'the drive', 'gauges', 'the logbook']),
    career('hoopball-player', 'Hoopball player', 'recreation', 'evening', 'staff', '$$', 'Plays weightless '
           'hoopball for a deck team, training in the Flight Hall and signing autographs after.',
           ['the team', 'training', 'match nights', 'fans']),
    career('glassblower', 'Glassblower', 'arts', 'flexible', 'freelance', '$', 'Blows cups, lamps and '
           'commissions from the ship\'s scrap glass in a studio on Studio Row.',
           ['the furnace', 'commissions', 'scrap glass', 'Studio Row']),
    career('voyage-registrar', 'Voyage registrar', 'government', 'office', 'staff', '$$', 'Records births, '
           'partnerships and deaths in the ship\'s register, and gets invited to a lot of parties.',
           ['the register', 'new parents', 'partnerships', 'paperwork']),
    career('lantern-maker', 'Lantern maker', 'arts', 'flexible', 'freelance', '$', 'Makes the paper lanterns '
           'that hang along the Lantern Ring and sells them before every festival.',
           ['paper', 'festivals', 'the night market', 'orders']),
    career('seed-vault-keeper', 'Seed vault keeper', 'agriculture', 'office', 'staff', '$$', 'Tends the frozen '
           'seed vault, tests old seeds and decides which crops grow next year.',
           ['the vault', 'old seeds', 'planting plans', 'the growers']),
    career('ring-steward', 'Ring steward', 'government', 'shift-day', 'rota', '$', 'Looks after one ring\'s '
           'corridors and cabins: sorting complaints, welcoming new families and fixing what nobody else will.',
           ['neighbours', 'complaints', 'new families', 'the noticeboard']),
    career('star-guide', 'Star guide', 'tourism', 'evening', 'rota', '$', 'Leads stargazing evenings at the '
           'Bow Dome, naming the stars ahead to families and couples.', ['the dome', 'the stars ahead',
           'families', 'couples']),
]

TRANSIT = [
    {'id': 'on-foot', 'name': 'On foot', 'kind': 'walk', 'summary': 'Corridors, ramps and stairs run bow to stern; '
     'a ring walks round in half an hour and the whole spine in an afternoon.', 'source': SRC},
    {'id': 'spine-tram', 'name': 'Spine tram', 'kind': 'tram', 'summary': 'A tram up and down the ship\'s spine '
     'from the Bow to the Stern Gallery, every four minutes by day, every twenty at ship\'s night.', 'source': SRC},
    {'id': 'ring-lifts', 'name': 'Ring lifts', 'kind': 'lift', 'summary': 'Big passenger lifts on the spokes '
     'between the rings and the weightless core; the ride up makes children giggle as gravity fades.',
     'source': SRC},
    {'id': 'pod-line', 'name': 'Pod line', 'kind': 'pod', 'summary': 'Four-seat transit pods on rails around '
     'and between the rings, booked from any hatch panel.', 'source': SRC},
]

EVENTS = [
    event('bloom-week', 'Bloom Week', [4], 'arboretum', 'The arboretum\'s fruit trees blossom on the ship\'s '
          'spring schedule and the whole ship comes to picnic under them.'),
    event('lantern-fair', 'The Lantern Fair', [10], 'lantern-ring', 'A week when every hatch on the Lantern Ring '
          'hangs a new lantern and the night market stays open until the morning bell.'),
    event('spindle-games', 'The Spindle Games', [7], 'the-spindle', 'The deck teams\' hoopball finals and the '
          'weightless races, with every ring painting its colours on its cheeks.'),
    event('harvest-rotation', 'Harvest Rotation', [9], 'green-decks', 'The big replanting of the farm racks, with '
          'volunteers, a harvest supper in the canteen and the first strawberries handed round.'),
    event('academy-commencement', 'Academy Commencement', [6], 'academy-deck', 'Graduates throw their caps into '
          'the low gravity of the lecture hall, where they float for a very long time.'),
    event('engine-open-day', 'Engine Open Day', [5], 'engine-decks', 'The engine crew open the reactor gallery '
          'and the drive hall to everyone, with tours, food stalls and a tug-of-war.'),
    event('swap-fair', 'The Great Swap', [3], 'cargo-holds', 'The year\'s biggest barter fair, when people clear '
          'out their cabins and the Swap spills over every hold.'),
    event('stargazing-nights', 'Stargazing Nights', [1, 2], 'the-bow', 'The dome lights go fully dark for a '
          'fortnight so everyone can see the stars ahead at their clearest.'),
    event('stern-open-studios', 'Open Studios', [11], 'stern-gallery', 'Every studio on Studio Row opens its '
          'doors, with music in the corridors and the year\'s graduates showing in the Aft Gallery.'),
    event('lagoon-regatta', 'Lagoon Regatta', [8], 'tidewater-deck', 'Home-made boats raced across the lagoon, '
          'most of which sink, to loud applause.'),
    event('founders-dance', "The Founders' Dance", [12], 'founders-ring', 'The old ring\'s winter dance in the '
          'Founders\' Hall, with the founders\' tunes and three generations on the floor.'),
    event('pantomime-season', 'Pantomime Season', [12, 1], 'lantern-ring', 'The Lantern Theatre\'s pantomime, '
          'full of jokes about the Voyage Council and the ration book.'),
    event('vesper-trade-week', 'Vesper Trade Week', [6], 'dockside', 'Port Vesper\'s traders bring extra '
          'shuttles of goods and the dockside turns into a fair.'),
]

HOLIDAYS = [
    {'id': 'launch-day', 'name': 'Launch Day', 'kind': 'public', 'month': 4, 'day': 9, 'summary': 'The day the '
     'Meridian left Earth orbit: the launch bell is rung, the founders\' names are read and every mess hall '
     'serves bean stew and honey cake.'},
    {'id': 'turning-of-the-year', 'name': 'Turning of the Year', 'kind': 'public', 'month': 1, 'day': 1,
     'summary': 'The ship\'s new year, counted in voyage years; people stay up to watch the year counter turn '
     'over on the Command Deck.'},
    {'id': 'firstborn-day', 'name': 'Firstborn Day', 'kind': 'observance', 'month': 2, 'day': 3, 'summary':
     'For the first child born aboard; children get a sweet from Sweet Orbit and the registrar reads the year\'s '
     'births.'},
    {'id': 'breach-remembrance', 'name': 'Breach Remembrance', 'kind': 'observance', 'month': 6, 'day': 17,
     'summary': 'For the forty-one lost when a hull panel failed in voyage year 71; a minute\'s silence at the '
     'shift bell and lights left on at the Quiet Chapel.'},
    {'id': 'crew-day', 'name': 'Crew Day', 'kind': 'public', 'month': 8, 'weekday': 0, 'nth': 1, 'summary':
     'A day off for everyone who keeps the ship running, with the officers serving breakfast in the mess halls.'},
    {'id': 'sunfall', 'name': 'Sunfall', 'kind': 'observance', 'month': 11, 'day': 2, 'summary': 'The day the Sun '
     'shrank to a star in the stern window; families visit the Stern Viewport and say goodbye to Earth again.'},
    {'id': 'long-night', 'name': 'The Long Night', 'kind': 'feast', 'month': 12, 'day': 21, 'summary': 'The '
     'ship\'s midwinter: the lights stay low all day, lanterns are lit on every ring and people give small '
     'presents made by hand.'},
    {'id': 'harvest-supper', 'name': 'Harvest Supper', 'kind': 'feast', 'month': 9, 'weekday': 6, 'nth': -1,
     'summary': 'The end of Harvest Rotation, with long tables down the Green Decks and the first fruit '
     'shared out.'},
    {'id': 'council-day', 'name': 'Council Day', 'kind': 'observance', 'month': 5, 'weekday': 1, 'nth': 2,
     'summary': 'The Voyage Council elections, with debates in the Council Chamber and voting at every mess hall.'},
    {'id': 'vesper-day', 'name': 'Vesper Day', 'kind': 'observance', 'month': 7, 'day': 30, 'summary': 'The day '
     'Port Vesper joined the voyage, with a shuttle of station visitors and a toast on the concourse.'},
]

LOCAL = [
    colour('bean-stew', 'Founders\' bean stew', 'dish', 'The ship\'s oldest dish: beans, barley and greens '
           'simmered all day, made from the founders\' recipe on Launch Day and whenever someone is ill.',
           ['old-galley', 'commons-mess-hall']),
    colour('moon-drops', 'Moon drops', 'dish', 'Round boiled sweets in pale lemon, sold by weight at Sweet Orbit; '
           'children are paid in them for chores.', ['sweet-orbit']),
    colour('algae-crisps', 'Algae crisps', 'dish', 'Salty green crisps fried from the vats, eaten by the bag at '
           'the lido and argued over by everyone else.', ['lido-kiosk', 'lantern-night-market']),
    colour('honey-cake', 'Launch honey cake', 'dish', 'A dense honey cake from the ship\'s bees, baked for Launch '
           'Day and birthdays.', ['first-light-bakery']),
    colour('mushroom-broth', 'Cave broth', 'dish', 'A dark mushroom broth from the caves, the grower\'s cure for '
           'everything.', ['green-deck-canteen']),
    colour('pink-ale', 'Pink ale', 'drink', 'Sour algae beer brewed on the Green Decks, pink from the grow lights '
           'it is drunk under.', ['pink-light-bar']),
    colour('still-spirit', 'Still-spirit', 'drink', 'A clear and dangerous spirit distilled in the holds from '
           'whatever is going spare.', ['crate-and-barrel']),
    colour('mint-tea', 'Deck mint tea', 'drink', 'Fresh mint tea, the ship\'s everyday drink; offering someone a '
           'cup is how you say sorry.', ['sprout-cafe', 'signal-tea-house']),
    colour('station-coffee', 'Station coffee', 'drink', 'Real coffee from Port Vesper, expensive and much '
           'boasted about.', ['airlock-cafe', 'starward-cafe']),
    colour('steady-as-she-turns', '"Steady as she turns"', 'saying', 'Said for "take it easy" or "don\'t '
           'worry", after the rings that never stop turning.'),
    colour('see-you-at-the-bell', '"See you at the bell"', 'saying', 'A goodbye, after the shift bells that '
           'ring three times a day.'),
    colour('spacer-breath', '"Hold your breath"', 'saying', 'What people say when someone is about to do '
           'something foolish; an old airlock joke.'),
    colour('not-on-my-ration', '"Not on my ration"', 'saying', 'A firm no, from the days when the ration book '
           'decided everything.'),
    colour('bell-greeting', 'Bell greetings', 'custom', 'At each shift bell, people in a corridor nod to '
           'whoever is passing; not nodding is a small insult.'),
    colour('naming-the-lamp', 'Naming the lamp', 'custom', 'A new baby\'s family hangs a lamp outside their '
           'cabin with the child\'s name on it for their first month.'),
    colour('cabin-swap', 'Cabin swaps', 'custom', 'Families swap cabins as children come and go, and the ring '
           'steward keeps a waiting list that is the subject of endless gossip.'),
    colour('handmade-gifts', 'Handmade gifts', 'custom', 'Presents are made, not bought: a printed cup, a knitted '
           'scarf, a lantern. Buying one from the Swap is fine if you pretend you made it.'),
    colour('stern-goodbye', 'Saying goodbye at the stern', 'custom', 'When someone dies, their family scatters '
           'a pinch of soil from the arboretum at the Stern Viewport.', ['stern-viewport']),
    colour('lantern-rings-team', 'Lantern Ring Lamplighters', 'team', 'The Lantern Ring\'s hoopball team, '
           'loud and loved, who win almost nothing.', ['flight-hall']),
    colour('engine-sparks-team', 'Engine Deck Sparks', 'team', 'The engine crews\' hoopball team, champions '
           'six years running and not modest about it.', ['flight-hall', 'the-tether']),
    colour('founders-oaks-team', "Founders' Oaks", 'team', 'The oldest hoopball team aboard, in green, '
           'supported by grandparents and nobody else.', ['flight-hall']),
    colour('ghost-of-deck-nine', 'The engineer on Deck Nine', 'legend', 'Night-shift crews say a founder in '
          'old overalls still checks the valves on Deck Nine and leaves them a little tighter.',
           ['reactor-gallery']),
    colour('second-ship', 'The second ship', 'rumor', 'Some say the Meridian was one of two ships launched and '
           'the other one is still out there, a few light years off. The Archive says otherwise.',
           ['ship-archive']),
    colour('lost-cat-colony', 'The cats of the holds', 'legend', 'A colony of cats has lived in the cargo '
           'holds for a hundred years; the loaders feed them and give them ranks.', ['the-swap']),
    colour('oak-wishes', 'Wishes on the old oak', 'custom', 'Couples tie a ribbon to the oldest oak in the '
           'arboretum when they partner, and the rangers pretend not to mind.', ['arboretum-paths']),
    colour('ration-book', 'The ration book', 'other', 'Most things are paid for in credits now, but every cabin '
           'still has a ration book for water and the rare foods, and nobody loses theirs.',
           ['quartermasters-stores']),
    colour('ships-night', "Ship's night", 'other', 'At 22:00 the corridor lights dim to amber and the painted '
           'sky in the arboretum turns to stars; the ship keeps quiet until the morning bell at 06:00.'),
    colour('voyage-year', 'Voyage years', 'other', 'People count years from launch, not by the Earth calendar: '
           'this is the 188th year of the voyage, and the Meridian is a little past halfway.'),
    colour('vesper-traders', 'The Vesper traders', 'other', 'Station traders who shuttle over every week with '
           'coffee, wool and gossip, and are treated like visiting cousins.', ['vesper-traders-row']),
    colour('the-swap-rules', 'Swap rules', 'custom', 'At the Swap, a handshake closes a trade and a favour owed '
           'is written on the favour board for everyone to see.', ['the-swap']),
]

PRICES = [
    price('coffee', 'Mint tea or ship coffee', 3, 5, 'a cup'),
    price('latte', 'Station coffee', 7, 11, 'a cup'),
    price('cheap-lunch', 'Mess hall lunch', 6, 10, 'a tray'),
    price('takeout', 'Noodles to go', 8, 13, 'a bowl'),
    price('dinner', 'Dinner out', 28, 55, 'for one, with a drink'),
    price('beer', 'Pink ale', 5, 8, 'a glass'),
    price('cocktail', 'Cocktail at the Forward Lounge', 14, 22),
    price('groceries', 'A week of groceries', 70, 110, 'for one, after the ration book'),
    price('transit', 'Spine tram or pod ride', 0, 2, 'one way'),
    price('movie', 'Ring Cinema ticket', 9, 14),
    price('show', 'Lantern Theatre seat', 20, 45),
    price('gym', 'Zero-G Gym month', 35, 60, 'a month'),
    price('haircut', 'Haircut at the night market', 12, 25),
    price('water-ration', 'Extra water ration', 4, 9, 'a week'),
    price('shuttle-fare', 'Shuttle to Port Vesper', 60, 110, 'one way'),
    price('wage', "Day's pay", 140, 210, "a day's take-home for an ordinary job"),
]

QUIRKS = [
    {'text': 'nods at every shift bell, even alone', 'bio': 'I nod at the bell. Everybody does. Well, everybody '
     'should.'},
    {'text': 'keeps a jar of arboretum soil on the shelf', 'bio': 'There is a jar of soil from the old oak on my '
     'shelf, for luck.'},
    {'text': 'counts the voyage years out loud on their birthday', 'bio': 'Born in voyage year 158, and I will '
     'tell you so.'},
    {'text': 'can name every star ahead of the Bow', 'bio': 'Ask me which star we are heading for. Go on.'},
    {'text': 'still carries their grandparent\'s ration book', 'bio': 'I carry my gran\'s old ration book. It '
     'is not sentimental. It is a bit sentimental.'},
    {'text': 'swims the lagoon every morning before the bell', 'bio': 'Lagoon at 05:45, every single day.'},
    {'text': 'talks to the cats in the cargo holds', 'bio': 'The hold cats know me by name. Two of them, anyway.'},
    {'text': 'refuses to drink pink ale', 'bio': 'I will not drink pink ale. I have tried. Twice.'},
    {'text': 'trades favours on the Swap board', 'bio': 'I owe half the Swap a favour and the other half owes me.'},
    {'text': 'never misses a Lamplighters match', 'bio': 'Lamplighters till I die. We will win one day.'},
    {'text': 'keeps a station coffee tin for special occasions', 'bio': 'I have one tin of real station coffee '
     'and you would have to earn a cup.'},
    {'text': 'sleeps with the cabin window shutter open to the stars', 'bio': 'I sleep with the shutter open. '
     'The stars are better than any lamp.'},
    {'text': 'makes all their gifts by hand', 'bio': 'Every present I give, I made. Some of them even work.'},
    {'text': 'has been to Port Vesper exactly once and talks about it constantly', 'bio': 'I have been to Port '
     'Vesper. Once. Ask me about it.'},
    {'text': 'checks the hatch seal twice before bed', 'bio': 'I double-check the hatch seal every night. '
     'Old habit from Engine Deck.'},
]

GOALS = [
    goal('meridian-hoopball', 'make the reserve squad of a hoopball team', 6, ('gym', 'evening'),
         '{name} lasted a full scrimmage in the Flight Hall without drifting off course',
         '{name} made the reserve squad and got their first team shirt', 'hoopball',
         'Training for the hoopball reserves. Do not laugh at my turns.'),
    goal('meridian-orchard-tree', 'grow a fruit tree from a seed-library seed', 6, ('park', 'morning'),
         '{name} repotted their little apple tree and it grew a new leaf',
         '{name} planted their apple tree in the arboretum with the rangers watching', 'gardening',
         'Growing an apple tree from a seed. It is slow. So am I.'),
    goal('meridian-family-log', 'trace their family back to the founders in the Archive', 5,
         ('library', 'afternoon'), '{name} found another great-grandparent in the Archive\'s birth logs',
         '{name} traced the family to a founder\'s name on the Founders\' Hall wall', 'family history',
         'Hunting for my founder in the Archive logs.'),
    goal('meridian-lantern', 'make a lantern for the Lantern Fair', 4, ('workshop', 'evening'),
         '{name} got another panel of the lantern glued and painted',
         '{name} hung their lantern on the Lantern Ring for the fair', 'lantern making',
         'Making my first lantern for the fair.'),
    goal('meridian-drop-dive', 'learn to dive into the Drop Pool from the top gallery', 5,
         ('gym', 'afternoon'), '{name} jumped from one gallery higher at the Drop Pool',
         '{name} dived from the top gallery and fell slowly all the way in', 'swimming',
         'Working up to the top gallery at the Drop Pool.'),
    goal('meridian-shuttle-licence', 'earn a shuttle pilot\'s licence', 8, ('library', 'evening'),
         '{name} passed another flight test in the dockside simulator',
         '{name} flew a shuttle solo round the docking ring and got their licence', 'flying',
         'Studying for my shuttle licence. Wish me steady hands.'),
    goal('meridian-glass', 'blow a set of glasses on Studio Row', 5, ('workshop', 'afternoon'),
         '{name} blew a glass that was nearly round', '{name} blew a matching set of four glasses and kept them all',
         'glassblowing', 'Learning to blow glass. Most of it is broken glass.'),
    goal('meridian-theatre', 'get a part in the winter pantomime', 5, ('venue', 'evening'),
         '{name} got through another rehearsal at the Lantern Theatre',
         '{name} played their part in the pantomime and got the biggest laugh of the night', 'acting',
         'Auditioning for the panto. I will be a very good back half of a cow.'),
    goal('meridian-stars', 'map the stars ahead for the observatory\'s public chart', 5, ('museum', 'evening'),
         '{name} logged another night of stars at the Bow Dome',
         '{name} saw their own star chart pinned up in the observatory', 'astronomy',
         'Mapping stars at the Bow on clear nights. They are all clear nights.'),
    goal('meridian-swap-trade', 'trade their way from a spare screw to a bicycle on the Swap', 6,
         ('market', 'morning'), '{name} traded up again on the Swap floor',
         '{name} rode the bicycle home from the Swap, three hundred trades later', 'trading',
         'Trading a single screw up to a bicycle on the Swap. Going well.'),
]

SHIPBORN = {
    'feminine': ['Wren', 'Juniper', 'Linnea', 'Tamsin', 'Marisol', 'Ines', 'Hazel', 'Ada', 'Iris', 'Clementine',
                 'Rosalind', 'Mae', 'Noor', 'Talia', 'Priya', 'Saoirse', 'Mira', 'Ingrid', 'Delphine', 'Yara',
                 'Esme', 'Imogen', 'Selma', 'Freya', 'Opal', 'Pearl', 'Ruth', 'Beatrix', 'Odette', 'Lucia',
                 'Paloma', 'Signe', 'Thea', 'Willa', 'Zadie', 'Aurelia', 'Celeste', 'Maren', 'Nell', 'Hester'],
    'masculine': ['Orrin', 'Soren', 'Tobias', 'Ezra', 'Felix', 'Rafael', 'Anselm', 'Bram', 'Caspian', 'Dashiell',
                  'Emil', 'Gideon', 'Hugo', 'Idris', 'Jonah', 'Kasimir', 'Leander', 'Mateo', 'Nico',
                  'Osric', 'Pavel', 'Quentin', 'Rafferty', 'Silas', 'Teodor', 'Ulric', 'Viktor', 'Wendell',
                  'Yusuf', 'Zeno', 'Arlo', 'Booker', 'Cyrus', 'Dov', 'Elias', 'Florian', 'Jasper', 'Lorcan',
                  'Magnus'],
    'neutral': ['Sol', 'Lark', 'Rowan', 'Sage', 'Ash', 'River', 'Quinn', 'Ellis', 'Marlowe', 'Robin', 'Sasha',
                'Indigo', 'Jules', 'Reese', 'Emery', 'Hollis', 'Linden', 'Perry', 'Shay', 'Teagan'],
    'family': ['Keel', 'Hollis', 'Marchetti', 'Okafor', 'Lindqvist', 'Tanaka-Reyes', 'Abernathy', 'Castell',
               'Osei', 'Brandt', 'Ferreira', 'Nakamura', 'Halvorsen', 'Delacroix', 'Mbeki', 'Quist', 'Sato',
               'Varga', 'Whitlow', 'Achterberg', 'Bellamy', 'Corrigan', 'Dunmore', 'Eskildsen', 'Farrow',
               'Galloway', 'Harrow', 'Ibarra', 'Jansen', 'Kowalczyk', 'Larkin', 'Moreau', 'Novak', 'Oyelaran',
               'Pereira', 'Rasmussen', 'Sandoval', 'Thorsen', 'Ueda', 'Vance', 'Winslow', 'Yilmaz', 'Zielinski',
               'Ashby', 'Brennan', 'Calloway', 'Devereux', 'Ellery', 'Fairweather', 'Greaves', 'Hargreave',
               'Iwasaki', 'Joubert', 'Kincaid', 'Lomax', 'Mallory', 'Nwosu', 'Ortega', 'Pemberton', 'Ravel'],
}

CITY = {
    'schema_version': 1, 'id': 'long-meridian', 'name': 'The Long Meridian', 'setting': 'original', 'era': 'future',
    'category': 'fictional',
    'basis': 'Original setting written for Prospero Companion: a generation ship in the 188th year of its voyage, '
             'with spun habitat rings, a forest deck and a station flying alongside. Nothing is taken from any '
             'published setting.',
    'region': 'Between the stars', 'country': 'Generation ship', 'timezone': 'UTC',
    'aliases': ['Long Meridian', 'Meridian', 'The Meridian'],
    'summary': 'A generation ship of about twenty-six thousand people, 188 years out from Earth and a little past '
               'halfway: spun rings of family cabins, a forest deck, a night market under paper lanterns, a '
               'weightless core for sport and Port Vesper three hours away by shuttle.',
    'lat': 0.0, 'lon': -140.0,
    'currency': {'code': 'CR', 'symbol': 'cr', 'name': 'credits'}, 'rent_period': 'month',
    'speeds': {'walk': 4.5, 'tram': 26, 'lift': 18, 'pod': 30},
    'enclosed': True,
    'neighbours': [{'city': 'port-vesper', 'hours': 3}],
    'calendar': 'none',
    'sources': {SRC: {'kind': 'curated', 'title': 'The Long Meridian, written for Prospero Companion',
                      'license': 'CC0-1.0', 'retrieved': '2026-10-20',
                      'note': 'An invented generation ship. Its decks, trades, prices and calendar are written for '
                              'it; every business, family and person named is fictional. Prices and berth fees are '
                              'in ship credits, monthly. Coordinates sit far out in the Pacific for distance '
                              'estimates only, along the ship\'s spine from bow to stern.'}},
    'neighborhoods': HOODS, 'places': P,
    'colleges': [
        {'id': 'meridian-academy', 'name': 'The Meridian Academy', 'type': 'academy', 'neighborhood': 'academy-deck',
         'size': 'medium', 'known_for': ['engineering', 'medicine', 'agronomy', 'navigation', 'life-support'],
         'source': SRC},
        {'id': 'founders-conservatory', 'name': "The Founders' Conservatory", 'type': 'music-school',
         'neighborhood': 'academy-deck', 'size': 'small', 'known_for': ['strings', 'composition', 'theatre'],
         'source': SRC},
        {'id': 'dockside-flight-school', 'name': 'Dockside Flight School', 'type': 'technical-institute',
         'neighborhood': 'dockside', 'size': 'small', 'known_for': ['piloting', 'docking', 'navigation'],
         'source': SRC},
    ],
    'employers': EMPLOYERS,
    'career_hubs': [
        {'id': 'hub-engineering', 'name': 'The engineering decks', 'neighborhoods': ['engine-decks', 'tidewater-deck',
         'cargo-holds'], 'sectors': ['engineering', 'manufacturing', 'construction', 'trades', 'city-works'],
         'summary': 'The reactor, the drive, life support and the hull: the work that keeps everyone breathing.',
         'source': SRC},
        {'id': 'hub-farms', 'name': 'The farms', 'neighborhoods': ['green-decks', 'arboretum'],
         'sectors': ['agriculture', 'gardens', 'science', 'food'], 'summary': 'Racks, vats, caves and the forest, '
         'growing almost everything aboard.', 'source': SRC},
        {'id': 'hub-command', 'name': 'Command and council', 'neighborhoods': ['command-deck', 'the-bow'],
         'sectors': ['aerospace', 'government', 'communications', 'learning', 'finance', 'media'],
         'summary': 'The bridge, the council offices, the Archive and the observatory.', 'source': SRC},
        {'id': 'hub-docks', 'name': 'The docks', 'neighborhoods': ['dockside', 'cargo-holds'],
         'sectors': ['aerospace', 'logistics', 'transit', 'commerce', 'hospitality'], 'summary': 'Shuttles, '
         'customs, cargo and the traders from Port Vesper.', 'source': SRC},
    ],
    'transit': TRANSIT,
    'climate': climate('Climate-controlled decks: the same mild air all year, warmer on the Engine Decks and '
                       'humid on the farms.', 'Climate-controlled decks'),
    'annual_events': EVENTS, 'careers': CAREERS,
    'names': {'mix': {'shipborn': 4, 'anglo': 1, 'hispanic': 1, 'east-asian': 1, 'south-asian': 0.8,
                      'west-african': 0.7, 'slavic': 0.5, 'arabic': 0.4},
              'groups': {'shipborn': SHIPBORN}},
    'local_color': LOCAL, 'prices': PRICES, 'holidays': HOLIDAYS,
    'townsfolk': {'quirks': QUIRKS, 'goals': GOALS},
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
