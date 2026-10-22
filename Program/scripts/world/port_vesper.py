"""Original orbital station for Prospero Companion (Hit List #77). Run `python scripts/world/port_vesper.py` to
rewrite the shipped JSON.

Port Vesper is invented: a trading station and shipyard that left Earth after the Long Meridian (long_meridian.py),
caught up with it thirty-seven years ago and flies alongside, three hours away by shuttle. The ship lists the station
as its neighbour, which works both ways. Nothing is taken from any published setting.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'cities' / 'port-vesper.json'

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

CHEAP = ((560, 760), (780, 1050), (1080, 1450))
MID = ((850, 1150), (1150, 1550), (1600, 2100))
HIGH = ((1250, 1650), (1650, 2200), (2300, 3100))

HOODS = [
    hood('the-concourse', 'The Concourse', 'The docking hub at the centre of the station: shuttle gates, customs, '
         'hotels for traders and the departures board everyone checks twice.', ['travel', 'busy', 'trade'],
         -139.5, 0.0, 'mid', MID, ['hotel-cabin', 'cabin'], 'high', ['on-foot', 'ring-shuttle', 'spoke-lifts']),
    hood('market-ring', 'Market Ring', 'The station\'s shopping and eating ring: coffee houses, tailors, spice '
         'stalls, restaurants and the noise of a place that trades for a living.', ['shopping', 'food', 'lively'],
         -139.49, 0.008, 'mid', MID, ['cabin', 'apartment-cabin', 'shared-berth'], 'high',
         ['on-foot', 'ring-shuttle', 'spoke-lifts']),
    hood('spinward-terraces', 'Spinward Terraces', 'Terraced homes with wide windows on the spinward side, where '
         'the yard owners, captains and old Earth families live.', ['wealthy', 'quiet', 'views'], -139.48, -0.004,
         'very-high', HIGH, ['terrace-home', 'apartment-cabin'], 'high', ['on-foot', 'ring-shuttle']),
    hood('the-yards', 'The Yards', 'The shipyard and foundry, building shuttles, drones and spare rings for the '
         'Meridian, with welders\' bunks and a canteen that never closes.', ['industrial', 'working', 'loud'],
         -139.51, -0.008, 'low', CHEAP, ['crew-berth', 'shared-berth'], 'medium', ['on-foot', 'ring-shuttle',
         'spoke-lifts']),
    hood('garden-ring', 'Garden Ring', 'The station\'s farm ring: a coffee plantation under lamps, a sheep deck '
         'for the wool everyone on the Meridian wants and a green park in the middle.', ['green', 'farming',
         'calm'], -139.49, -0.012, 'mid', MID, ['garden-cabin', 'cabin'], 'medium', ['on-foot', 'ring-shuttle']),
    hood('low-ring', 'Low Ring', 'The cheapest ring, half a gravity and full of young crews, music bars, '
         'late kitchens and cabins three to a room.', ['young', 'nightlife', 'cheap'], -139.51, 0.012, 'low',
         CHEAP, ['shared-berth', 'bunkroom', 'cabin'], 'high', ['on-foot', 'ring-shuttle', 'spoke-lifts']),
    hood('observation-spoke', 'Observation Spoke', 'A long spoke reaching out to the station\'s great window, '
         'with the school, a gallery and the best view of the Meridian turning in the dark.',
         ['views', 'family', 'quiet'], -139.47, 0.004, 'high', HIGH, ['apartment-cabin', 'family-berth'], 'high',
         ['on-foot', 'spoke-lifts']),
    hood('old-hull', 'Old Hull', 'The original Earth-built core of the station, all scuffed panels and stencilled '
         'deck numbers, with the arrival museum, the chapel and the oldest bar aboard.',
         ['historic', 'characterful', 'quiet'], -139.52, 0.0, 'mid', MID, ['cabin', 'family-berth'], 'high',
         ['on-foot', 'spoke-lifts']),
]

P = [
    place('departures-hall', 'The Departures Hall', 'landmark', 'the-concourse', 'A bright hall under the great '
          'board, where shuttles to the Meridian leave on the hour and families wave from the rail.',
          ['shuttles', 'departures', 'people-watching'], 'free', 'indoor', 'sfm', 'MAEL'),
    place('gatehouse-hotel', 'The Gatehouse', 'inn', 'the-concourse', 'A traders\' hotel by the gates with real '
          'beds, a quiet bar and breakfast served until the last shuttle.', ['hotel', 'traders', 'breakfast'],
          '$$$', 'indoor', 'sfc', 'MAEL'),
    place('gate-six-coffee', 'Gate Six Coffee', 'cafe', 'the-concourse', 'The station\'s most famous coffee bar, '
          'roasting beans from the Garden Ring and selling them by the tin to Meridian visitors.',
          ['coffee', 'roastery', 'souvenirs'], '$$', 'indoor', 'sfc', 'MA'),
    place('customs-canteen', 'Customs Canteen', 'restaurant', 'the-concourse', 'A plain canteen behind the customs '
          'desks, with the cheapest hot lunch on the station and the best gossip.', ['canteen', 'cheap', 'gossip'],
          '$', 'indoor', 'sc', 'MA'),
    place('last-shuttle', 'The Last Shuttle', 'bar', 'the-concourse', 'A bar named for everyone who has missed '
          'it, with a clock showing the next launch and a crowd that does not care.', ['travellers', 'cocktails',
          'late'], '$$', 'indoor', 'fdc', 'EL'),
    place('spice-arcade', 'The Spice Arcade', 'market', 'market-ring', 'A covered arcade of spice merchants, '
          'pickles and dried fruit, smelling of cardamom from one end to the other.', ['spices', 'stalls',
          'smells'], '$', 'indoor', 'sf', 'MA'),
    place('wool-and-weft', 'Wool & Weft', 'shopping', 'market-ring', 'A knitwear shop selling real station wool, '
          'the most wanted present on the Meridian.', ['wool', 'knitwear', 'gifts'], '$$', 'indoor', 's', 'MA'),
    place('copper-pan', 'The Copper Pan', 'restaurant', 'market-ring', 'A bustling bistro with a menu that '
          'changes with each supply run: braised greens, fresh pasta and real cheese.',
          ['bistro', 'pasta', 'date-night'], '$$$', 'indoor', 'dfm', 'AE', 'station-bistro'),
    place('ring-bakehouse', 'Ring Bakehouse', 'cafe', 'market-ring', 'A bakery that fills the ring with the smell '
          'of rye and cinnamon at the morning bell.', ['bakery', 'bread', 'morning'], '$', 'indoor', 'sfm', 'M'),
    place('market-ring-theatre', 'The Little Ring Theatre', 'venue', 'market-ring', 'A hundred-seat theatre over '
          'the shops, with comedy, cabaret and touring players from the Meridian.', ['comedy', 'cabaret',
          'theatre'], '$$', 'indoor', 'fd', 'EL'),
    place('noodle-lane', 'Noodle Lane', 'restaurant', 'market-ring', 'Six noodle counters in a row, each claiming '
          'to be the original.', ['noodles', 'cheap', 'quick'], '$', 'indoor', 'sf', 'AEL', 'station-street-food'),
    place('terrace-wine-bar', 'The Terrace Wine Bar', 'bar', 'spinward-terraces', 'A wine bar pouring the '
          'station\'s own vintages from the Garden Ring vines, with a window wall onto the stars.',
          ['wine', 'views', 'romantic'], '$$$', 'indoor', 'dfs', 'EL'),
    place('spinward-promenade', 'The Spinward Promenade', 'park', 'spinward-terraces', 'A planted promenade along '
          'the terraces, where nannies push prams and captains walk their dogs.', ['promenade', 'dogs',
          'planters'], 'free', 'indoor', 'sdm', 'MAE'),
    place('captains-table', "The Captains' Table", 'restaurant', 'spinward-terraces', 'A formal dining room where '
          'yard owners close deals over station lamb and too much wine.', ['fine-dining', 'deals', 'lamb'], '$$$$',
          'indoor', 'dc', 'E', 'station-bistro'),
    place('terrace-salon', 'Terrace Salon', 'shopping', 'spinward-terraces', 'A hairdresser and beauty salon '
          'where the Terraces get their news before the feed does.', ['salon', 'gossip', 'grooming'], '$$$',
          'indoor', 's', 'MA'),
    place('terrace-tea-room', 'The Tea Room', 'cafe', 'spinward-terraces', 'A genteel tea room with tiered cakes '
          'and a pianist on rest-day afternoons.', ['tea', 'cakes', 'piano'], '$$', 'indoor', 'sdm', 'MA'),
    place('foundry-canteen', 'Foundry Canteen', 'restaurant', 'the-yards', 'A twenty-four-hour canteen for '
          'welders and fitters: pies, fried rice and tea strong enough to weld with.', ['canteen', 'all-hours',
          'cheap'], '$', 'indoor', 'sc', 'MAEL', 'station-street-food'),
    place('slipway-gallery', 'The Slipway Gallery', 'attraction', 'the-yards', 'A viewing gallery over the '
          'slipway where a new shuttle is always half built.', ['shipyard', 'views', 'engineering'], 'free',
          'indoor', 'sfm', 'MA'),
    place('rivet-bar', 'The Rivet', 'bar', 'the-yards', 'A loud yard bar with arm-wrestling on Fridays and a '
          'ceiling covered in signed welding masks.', ['yard-crews', 'loud', 'cheap'], '$', 'indoor', 'fc', 'EL'),
    place('yards-fitness', 'Yard Gym', 'fitness', 'the-yards', 'A no-frills gym with heavy weights and a boxing '
          'ring the yard crews fight charity bouts in.', ['weights', 'boxing', 'gym'], '$', 'indoor', 'sf', 'MAE'),
    place('makers-bench', "The Makers' Bench", 'workshop', 'the-yards', 'A public workshop with offcuts from the '
          'yard, where anyone can learn to weld on rest days.', ['welding', 'makers', 'classes'], '$', 'indoor',
          'sf', 'AE'),
    place('coffee-terraces', 'The Coffee Terraces', 'attraction', 'garden-ring', 'Stepped rows of coffee bushes '
          'under warm lamps, with tours, tastings and pickers in wide hats.', ['coffee', 'tours', 'tastings'],
          '$', 'mixed', 'sfm', 'MA'),
    place('sheep-deck', 'The Sheep Deck', 'attraction', 'garden-ring', 'A grassy deck of sheep kept for their '
          'wool, with shearing days that draw a crowd from the Meridian.', ['sheep', 'animals', 'family-friendly'],
          'free', 'mixed', 'sm', 'MA'),
    place('green-commons', 'Green Commons', 'park', 'garden-ring', 'The station\'s central lawn, with picnic '
          'tables, a bandstand and the only grass you can lie on for three hours\' flight.',
          ['lawn', 'picnics', 'bandstand'], 'free', 'mixed', 'sfdm', 'MAE'),
    place('the-vineyard-house', 'The Vineyard House', 'restaurant', 'garden-ring', 'A farm restaurant among the '
          'vines with long lunches of lamb, bread and the house red.', ['farm-to-table', 'wine', 'long-lunch'],
          '$$$', 'indoor', 'dfm', 'AE', 'station-bistro'),
    place('garden-ring-cafe', 'The Potting Shed', 'cafe', 'garden-ring', 'A cafe in a former potting shed, '
          'serving lamp-grown coffee and scones to farm hands.', ['coffee', 'scones', 'farm'], '$', 'indoor',
          'sfm', 'MA'),
    place('low-ring-night-kitchen', 'Night Kitchen', 'restaurant', 'low-ring', 'A late kitchen of skewers, '
          'flatbreads and hot sauce, busiest after the bars close.', ['late-night', 'skewers', 'cheap'], '$',
          'indoor', 'sf', 'EL', 'station-street-food'),
    place('half-g-club', 'Half-G', 'nightlife', 'low-ring', 'A club in half gravity where the dancing is mostly '
          'jumping, and the jumps are very high.', ['dancing', 'low-gravity', 'djs'], '$$', 'indoor', 'fd', 'L'),
    place('the-bunkhouse', 'The Bunkhouse', 'bar', 'low-ring', 'A crowded bar of young crews, open-mic nights and '
          'cheap shots named after shuttle routes.', ['open-mic', 'young', 'cheap'], '$', 'indoor', 'f', 'EL'),
    place('low-ring-laundrette', 'Spin Cycle', 'cafe', 'low-ring', 'A laundrette and cafe where half the ring '
          'meets on a rest-day morning.', ['laundrette', 'coffee', 'neighbours'], '$', 'indoor', 'sf', 'MA'),
    place('low-ring-records', 'Groove Bay', 'shopping', 'low-ring', 'A record shop of Earth music, station bands '
          'and the odd Meridian folk recording.', ['records', 'music', 'browsing'], '$$', 'indoor', 'sf', 'AE'),
    place('the-great-window', 'The Great Window', 'landmark', 'observation-spoke', 'A window forty metres wide '
          'at the end of the spoke, with the Meridian turning slowly in the dark beyond it.',
          ['viewport', 'the-meridian', 'romantic'], 'free', 'indoor', 'sdfm', 'MAEL'),
    place('spoke-school-library', 'Spoke Library', 'library', 'observation-spoke', 'The station library, shared '
          'with the school, with a corner of real paper books shipped from Earth.', ['books', 'study', 'kids'],
          'free', 'indoor', 'sm', 'MAE'),
    place('window-cafe', 'The Window Cafe', 'cafe', 'observation-spoke', 'A cafe right under the Great Window, '
          'where the coffee is ordinary and the view is not.', ['coffee', 'views', 'quiet'], '$$', 'indoor',
          'sdf', 'MAE'),
    place('spoke-gallery', 'Spoke Gallery', 'museum', 'observation-spoke', 'A small art gallery of station '
          'painters and photographs of the Meridian across thirty-seven years alongside.',
          ['art', 'photography', 'exhibitions'], 'free', 'indoor', 'sdm', 'AE'),
    place('spoke-pool', 'The Spoke Pool', 'fitness', 'observation-spoke', 'A long swimming pool lit from below, '
          'with lane swimming at dawn and family swims after school.', ['swimming', 'lanes', 'family'], '$',
          'indoor', 'sfm', 'MA'),
    place('arrival-museum', 'Museum of the Arrival', 'museum', 'old-hull', 'The story of the station\'s chase '
          'across the dark and the day it caught up with the Meridian, with the first handshake on film.',
          ['history', 'exhibits', 'family-friendly'], '$', 'indoor', 'sfm', 'MA'),
    place('hull-chapel', 'The Hull Chapel', 'temple', 'old-hull', 'A small chapel in a storage bay, with '
          'candles in jars and a wall of photos from Earth.', ['chapel', 'candles', 'memorial'], 'free', 'indoor',
          'sm', 'MAE'),
    place('the-first-pour', 'The First Pour', 'bar', 'old-hull', 'The oldest bar on the station, where the '
          'founding crew drank the first beer brewed aboard and the tap still says so.',
          ['history', 'regulars', 'beer'], '$$', 'indoor', 'sf', 'EL'),
    place('stencil-diner', 'Stencil Diner', 'restaurant', 'old-hull', 'A diner under stencilled deck numbers, '
          'serving pancakes and coffee from the first shift to the last.', ['diner', 'pancakes', 'breakfast'], '$',
          'indoor', 'sfm', 'MA', 'station-bistro'),
    place('hull-market', 'Old Hull Market', 'market', 'old-hull', 'A rest-day market of secondhand tools, '
          'heirlooms from Earth and old station uniforms.', ['secondhand', 'heirlooms', 'bargains'], '$', 'indoor',
          'sf', 'MA'),
]

EMPLOYERS = [
    employer('vesper-port-authority', 'Vesper Port Authority', 'aerospace', 'the-concourse', 'large', 'Runs the '
             'gates, the shuttle schedule to the Meridian and customs.', ['docking-controller', 'shuttle-pilot',
             'customs-inspector', 'traffic-controller', 'cargo-handler']),
    employer('vesper-yards', 'Vesper Yards', 'manufacturing', 'the-yards', 'large', 'Builds shuttles, drones '
             'and spare ring sections for the station and the Meridian.', ['pressure-welder', 'habitat-builder',
             'fabrication-technician', 'machinist', 'robotics-technician', 'drone-operator']),
    employer('vesper-trading-house', 'Vesper Trading House', 'commerce', 'market-ring', 'medium', 'The '
             'station\'s biggest trading firm, buying and selling with the Meridian.', ['trade-negotiator',
             'freight-scheduler', 'supply-chain-manager', 'ledger-accountant', 'credit-broker']),
    employer('garden-ring-estates', 'Garden Ring Estates', 'agriculture', 'garden-ring', 'medium', 'Grows the '
             'station\'s coffee and vines and keeps the sheep.', ['crop-scientist', 'hydroponics-technician',
             'pollination-technician', 'shepherd', 'coffee-roaster']),
    employer('vesper-infirmary', 'Vesper Infirmary', 'healthcare', 'observation-spoke', 'medium', 'The station '
             'hospital and clinic.', ['general-practitioner', 'clinic-nurse', 'emergency-medic', 'midwife',
             'dispensary-pharmacist']),
    employer('spoke-school', 'Spoke School', 'education', 'observation-spoke', 'medium', 'The station\'s school '
             'and nursery.', ['schoolteacher', 'nursery-worker', 'tutor']),
    employer('vesper-station-ops', 'Station Operations', 'engineering', 'old-hull', 'large', 'Keeps the air, '
             'water, power and spin running.', ['life-support-engineer', 'reactor-technician',
             'power-grid-technician', 'air-systems-technician', 'water-reclamation-technician', 'hull-technician']),
    employer('market-ring-hospitality', 'Market Ring Hospitality', 'hospitality', 'market-ring', 'medium', 'The '
             'station\'s hotels, restaurants and coffee bars.', ['head-chef', 'galley-cook', 'concierge',
             'guesthouse-manager', 'coffee-bar-attendant', 'lounge-bartender']),
    employer('vesper-feed', 'Vesper Feed', 'media', 'old-hull', 'small', 'The station\'s news and music '
             'broadcast, with a weekly show for the Meridian.', ['feed-reporter', 'broadcaster', 'photographer']),
    employer('vesper-watch', 'Vesper Watch', 'security', 'the-concourse', 'small', 'The station\'s security and '
             'rescue crews.', ['security-officer', 'investigator', 'rescue-specialist', 'fire-and-pressure-crew']),
    employer('vesper-council', 'Station Council', 'government', 'old-hull', 'small', 'The station\'s council '
             'and the offices that talk to the Meridian\'s Voyage Council.', ['council-clerk',
             'district-administrator', 'housing-officer', 'mediator']),
    employer('low-ring-venues', 'Low Ring Venues', 'entertainment', 'low-ring', 'small', 'The clubs, bars and '
             'stages of the Low Ring.', ['club-dj', 'session-musician', 'lounge-bartender', 'event-coordinator']),
]

CAREERS = [
    career('shepherd', 'Shepherd', 'agriculture', 'early', 'staff', '$', 'Keeps the Sheep Deck\'s flock fed, '
           'sheared and out of the coffee bushes.', ['the flock', 'shearing days', 'the Sheep Deck', 'wool']),
    career('coffee-roaster', 'Coffee roaster', 'food', 'early', 'staff', '$$', 'Roasts the Garden Ring\'s beans '
           'for the station and the tins that go over to the Meridian.', ['roasting', 'beans', 'tins', 'the smell']),
    career('gate-announcer', 'Gate announcer', 'aerospace', 'rotating', 'rota', '$', 'Calls every shuttle '
           'departure and arrival on the Concourse, and every name of every passenger who is late.',
           ['the board', 'late passengers', 'the Concourse', 'the microphone']),
]

EVENTS = [
    event('shearing-days', 'Shearing Days', [5], 'garden-ring', 'The flock is sheared on the Sheep Deck, with a '
          'fair, a knitting race and visitors from the Meridian.'),
    event('arrival-week', 'Arrival Week', [7], 'old-hull', 'A week of parties for the day the station caught up '
          'with the Meridian, ending with a shuttle parade.'),
    event('yards-launch', 'Shuttle Launch', [3, 9], 'the-yards', 'A new shuttle rolls off the slipway and is '
          'christened with a bottle of the house red.'),
    event('coffee-harvest', 'Coffee Harvest', [11], 'garden-ring', 'The coffee terraces are picked and the whole '
          'station smells of roasting for a week.'),
    event('window-nights', 'Window Nights', [1], 'observation-spoke', 'The spoke goes dark so everyone can watch '
          'the Meridian\'s lights turning past the Great Window.'),
    event('low-ring-music-week', 'Low Ring Music Week', [8], 'low-ring', 'Bands from both ships play every bar '
          'on the ring, and nobody sleeps.'),
]

HOLIDAYS = [
    {'id': 'arrival-day', 'name': 'Arrival Day', 'kind': 'public', 'month': 7, 'day': 30, 'summary': 'The day '
     'Port Vesper caught up with the Meridian after a fourteen-year chase, with a toast at the Departures Hall.'},
    {'id': 'station-new-year', 'name': 'Station New Year', 'kind': 'public', 'month': 1, 'day': 1, 'summary':
     'New year by the Earth calendar the station still keeps, with a countdown on the great board.'},
    {'id': 'earth-day-vesper', 'name': 'Earth Remembrance', 'kind': 'observance', 'month': 4, 'day': 22,
     'summary': 'People share photos and stories of Earth at the Hull Chapel and the Window Cafe.'},
    {'id': 'yards-day', 'name': 'Yards Day', 'kind': 'public', 'month': 9, 'weekday': 0, 'nth': 1, 'summary':
     'A day off for the yard crews, with a parade of drones down the Concourse.'},
    {'id': 'midwinter-vesper', 'name': 'Midwinter', 'kind': 'feast', 'month': 12, 'day': 21, 'summary':
     'Candles in every window, mulled wine from the Garden Ring and presents swapped with Meridian friends.'},
]

LOCAL = [
    colour('station-red', 'Station red', 'drink', 'The house red from the Garden Ring vines, rough when young and '
           'much better than anyone on the Meridian admits.', ['terrace-wine-bar', 'the-vineyard-house']),
    colour('gate-six-blend', 'Gate Six blend', 'drink', 'The station\'s own roast, sold by the tin to every '
           'visitor from the Meridian.', ['gate-six-coffee']),
    colour('station-lamb', 'Station lamb', 'dish', 'Lamb from the Sheep Deck, rare and dear, roasted for '
           'Midwinter and big deals.', ['captains-table', 'the-vineyard-house']),
    colour('cardamom-buns', 'Cardamom buns', 'dish', 'Sticky cardamom buns from the Ring Bakehouse, carried back '
           'to the Meridian by the boxful.', ['ring-bakehouse']),
    colour('yard-pie', 'Yard pie', 'dish', 'A pie the size of a welding mask, filled with whatever the canteen '
           'had left.', ['foundry-canteen']),
    colour('mind-the-gate', '"Mind the gate"', 'saying', 'Goodbye on Port Vesper, said to anyone heading for a '
           'shuttle.'),
    colour('caught-up', '"We caught up, didn\'t we?"', 'saying', 'Said when something hard finally works out, '
           'after the station\'s long chase.'),
    colour('meridian-cousins', 'Meridian cousins', 'custom', 'Station families keep up with a family on the '
           'Meridian, swapping wool for honey cake and visiting on Arrival Day.'),
    colour('window-proposals', 'Proposals at the Great Window', 'custom', 'Proposing at the Great Window with '
           'the Meridian passing behind is the station\'s favourite romantic cliche.', ['the-great-window']),
    colour('yard-masks', 'Signed masks', 'custom', 'Every welder signs their first mask and hangs it on the '
           'ceiling of the Rivet.', ['rivet-bar']),
    colour('vesper-rovers', 'Vesper Rovers', 'team', 'The station\'s hoopball team, who travel to the Meridian '
           'for away games and lose most of them.'),
    colour('fifteenth-crew', 'The fifteenth crew member', 'legend', 'The founding crew was fourteen, but every '
           'photo of them shows fifteen, and nobody can say who the last one is.', ['arrival-museum']),
    colour('chase-rumour', 'The other station', 'rumor', 'Some say a second station left Earth after Vesper and '
           'is still chasing the Meridian. The Port Authority says nothing.', ['departures-hall']),
    colour('earth-time', 'Earth time', 'other', 'The station still counts years by the Earth calendar, which '
           'makes every meeting with the Meridian\'s voyage years a small argument.'),
    colour('shuttle-hours', 'The hourly shuttle', 'other', 'Shuttles leave for the Meridian on the hour from the '
           'Departures Hall; the flight takes about three hours.', ['departures-hall']),
]

PRICES = [
    price('coffee', 'Gate Six coffee', 4, 7, 'a cup'),
    price('cheap-lunch', 'Canteen lunch', 7, 12, 'a tray'),
    price('takeout', 'Noodles to go', 8, 14, 'a bowl'),
    price('dinner', 'Dinner out', 32, 65, 'for one, with a glass of station red'),
    price('beer', 'Beer at the First Pour', 6, 9, 'a glass'),
    price('cocktail', 'Cocktail at the Last Shuttle', 13, 20),
    price('groceries', 'A week of groceries', 80, 125, 'for one'),
    price('transit', 'Ring shuttle', 1, 2, 'one way'),
    price('show', 'Little Ring Theatre seat', 18, 35),
    price('gym', 'Yard Gym month', 30, 50, 'a month'),
    price('haircut', 'Haircut at the Terrace Salon', 25, 60),
    price('wool-jumper', 'Station wool jumper', 90, 180),
    price('shuttle-fare', 'Shuttle to the Meridian', 60, 110, 'one way'),
    price('wage', "Day's pay", 150, 230, "a day's take-home for an ordinary job"),
]

QUIRKS = [
    {'text': 'checks the departures board even when not travelling', 'bio': 'I check the board. I am not going '
     'anywhere. I just like to know.'},
    {'text': 'keeps a photo of Earth by the bed', 'bio': 'There is a photo of Earth by my bed. My grandmother '
     'took it.'},
    {'text': 'calls everyone from the Meridian "cousin"', 'bio': 'Meridian folk are all cousins to me.'},
    {'text': 'can tell a coffee bean\'s terrace by the smell', 'bio': 'Give me a bean and I will tell you which '
     'terrace it grew on.'},
    {'text': 'has a signed welding mask on the Rivet\'s ceiling', 'bio': 'My mask is on the Rivet ceiling, third '
     'row from the bar.'},
    {'text': 'watches the Meridian turn past the Great Window every evening', 'bio': 'Every evening, the Great '
     'Window. It is cheaper than the cinema.'},
    {'text': 'knits on every shuttle ride', 'bio': 'One shuttle ride, one sleeve.'},
    {'text': 'argues about Earth years and voyage years', 'bio': 'It is the Earth year that counts. Fight me.'},
]

GOALS = [
    goal('vesper-jumper', 'knit a jumper from their own station wool', 6, ('market', 'afternoon'),
         '{name} finished another panel of the jumper', '{name} wore their station-wool jumper on the Concourse',
         'knitting', 'Knitting a jumper from wool I sheared myself.'),
    goal('vesper-pilot', 'fly the hourly shuttle to the Meridian', 8, ('library', 'evening'),
         '{name} passed another simulator flight', '{name} flew the hourly shuttle over to the Meridian',
         'flying', 'Training to fly the Meridian shuttle.'),
    goal('vesper-welding', 'learn to weld well enough to sign a mask', 5, ('workshop', 'evening'),
         '{name} laid a cleaner bead at the Makers\' Bench', '{name} signed their first mask and hung it in the Rivet',
         'welding', 'Learning to weld at the Makers\' Bench.'),
    goal('vesper-band', 'play a set at Low Ring Music Week', 5, ('venue', 'evening'),
         '{name} got through a whole set at the Bunkhouse open mic',
         '{name} played their set at Music Week to a packed bar', 'music',
         'Getting my band ready for Music Week.'),
    goal('vesper-roast', 'roast their own blend at Gate Six', 5, ('cafe', 'morning'),
         '{name} roasted another test batch at Gate Six', '{name} saw their own blend on the Gate Six board',
         'coffee', 'Working on my own coffee blend.'),
]

CITY = {
    'schema_version': 1, 'id': 'port-vesper', 'name': 'Port Vesper', 'setting': 'original', 'era': 'future',
    'category': 'fictional',
    'basis': 'Original setting written for Prospero Companion: an orbital trading station that flies beside the '
             'Long Meridian, the built-in generation ship. Nothing is taken from any published setting.',
    'region': 'Beside the Long Meridian', 'country': 'Orbital station', 'timezone': 'UTC',
    'aliases': ['Vesper', 'Vesper Station'],
    'summary': 'A station of about seven thousand people that left Earth after the Meridian, caught up with it '
               'thirty-seven years ago and now flies alongside: a trading port, a shipyard, coffee terraces, a '
               'sheep deck and a great window onto the ship three hours away by shuttle.',
    'lat': 0.0, 'lon': -139.5,
    'currency': {'code': 'CR', 'symbol': 'cr', 'name': 'credits'}, 'rent_period': 'month',
    'speeds': {'walk': 4.5, 'shuttle': 28, 'lift': 18},
    'enclosed': True,
    'calendar': 'none',
    'sources': {SRC: {'kind': 'curated', 'title': 'Port Vesper, written for Prospero Companion',
                      'license': 'CC0-1.0', 'retrieved': '2026-10-20',
                      'note': 'An invented station. Its rings, trades, prices and calendar are written for it; every '
                              'business, family and person named is fictional. Prices and rents are in credits, '
                              'monthly. Coordinates sit far out in the Pacific for distance estimates only.'}},
    'neighborhoods': HOODS, 'places': P,
    'colleges': [
        {'id': 'vesper-yards-institute', 'name': 'Yards Institute', 'type': 'technical-institute',
         'neighborhood': 'the-yards', 'size': 'small', 'known_for': ['welding', 'shipbuilding', 'robotics'],
         'source': SRC},
    ],
    'employers': EMPLOYERS,
    'career_hubs': [
        {'id': 'hub-port', 'name': 'The port', 'neighborhoods': ['the-concourse', 'market-ring'],
         'sectors': ['aerospace', 'commerce', 'logistics', 'hospitality', 'retail'], 'summary': 'Gates, customs, '
         'traders and the shops and hotels that live off them.', 'source': SRC},
        {'id': 'hub-yards', 'name': 'The yards', 'neighborhoods': ['the-yards', 'old-hull'],
         'sectors': ['manufacturing', 'engineering', 'construction'], 'summary': 'The shipyard, the foundry and '
         'station operations.', 'source': SRC},
    ],
    'transit': [
        {'id': 'on-foot', 'name': 'On foot', 'kind': 'walk', 'summary': 'Each ring walks round in twenty minutes; '
         'the spokes are long, and most people take the lifts.', 'source': SRC},
        {'id': 'ring-shuttle', 'name': 'Ring shuttle', 'kind': 'shuttle', 'summary': 'Little carts that run round '
         'each ring and across to the Concourse every few minutes.', 'source': SRC},
        {'id': 'spoke-lifts', 'name': 'Spoke lifts', 'kind': 'lift', 'summary': 'Lifts up and down the spokes, '
         'from full gravity on the rings to none at the Concourse.', 'source': SRC},
    ],
    'climate': climate('Climate-controlled rings: mild all year, warm on the Garden Ring, cool in the Yards.',
                       'Climate-controlled rings'),
    'annual_events': EVENTS, 'careers': CAREERS,
    'names': {'mix': {'anglo': 1.5, 'hispanic': 1.5, 'east-asian': 1.5, 'south-asian': 1.2, 'west-african': 1,
                      'slavic': 0.8, 'arabic': 0.8, 'italian': 0.4, 'irish': 0.4}},
    'local_color': LOCAL, 'prices': PRICES, 'holidays': HOLIDAYS,
    'townsfolk': {'quirks': QUIRKS, 'goals': GOALS},
    # What this city calls things on the in-world screens (companion/world/era_words.py).
    'words': {
        'posts_tab': 'Stationnet',
    }
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
