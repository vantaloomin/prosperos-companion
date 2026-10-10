"""Original 1920s town for Prospero Companion. Run `python scripts/world/pellmouth.py` to rewrite the shipped JSON.

Pellmouth is invented: a fog-bound river-mouth town on the North Shore of Massachusetts in 1926, modelled on real
Essex County harbour, mill and college towns of the period. Its cosmic-horror lean is mood, local custom, legend and
rumour only: nothing uncanny is ever confirmed, and nothing is taken from Lovecraft's stories or later works.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'cities' / 'pellmouth.json'
S = 'curated-2026-10'
ERA = 'jazz-age'


def hood(id, name, summary, vibe, lat, lon, tier, rent, housing, walk, transit):
    studio, one, two = rent
    return {'id': id, 'name': name, 'summary': summary, 'vibe': vibe, 'lat': lat, 'lon': lon, 'rent_tier': tier,
            'rent': {'studio': studio, 'one_bedroom': one, 'two_bedroom': two}, 'housing': housing,
            'walkability': walk, 'transit': transit, 'source': S}


def place(id, name, kind, hood, summary, tags, cost, setting, good_for, day_parts, seasons=(), cuisine=''):
    return {'id': id, 'name': name, 'kind': kind, 'neighborhood': hood, 'summary': summary, 'tags': tags,
            'cost': cost, 'setting': setting, 'good_for': good_for, 'day_parts': day_parts,
            'seasons': list(seasons), 'cuisine': cuisine, 'source': S}


def college(id, name, type, hood, size, known_for):
    return {'id': id, 'name': name, 'type': type, 'neighborhood': hood, 'size': size, 'known_for': known_for,
            'source': S}


def career(id, name, sector, schedule, pay, summary, themes):
    return {'id': id, 'name': name, 'sector': sector, 'schedule': schedule, 'pay': pay, 'summary': summary,
            'themes': themes, 'eras': [ERA]}


def employer(id, name, sector, hood, size, summary, careers):
    return {'id': id, 'name': name, 'sector': sector, 'neighborhood': hood, 'size': size, 'summary': summary,
            'careers': careers, 'source': S}


def line(id, name, kind, summary):
    return {'id': id, 'name': name, 'kind': kind, 'summary': summary, 'source': S}


def event(id, name, months, hood, summary):
    return {'id': id, 'name': name, 'months': months, 'neighborhood': hood, 'summary': summary, 'source': S}


def color(id, name, kind, summary, places=(), seasons=()):
    return {'id': id, 'name': name, 'kind': kind, 'summary': summary, 'places': list(places),
            'seasons': list(seasons), 'source': S}


def price(id, item, low, high, per=''):
    return {'id': id, 'item': item, 'low': low, 'high': high, 'per': per, 'source': S}


ALL = ['solo', 'friends', 'date', 'family']
ADULT = ['solo', 'friends', 'date']
DAY = ['morning', 'afternoon']
DINNER = ['evening']
NIGHT = ['evening', 'late']
ALLDAY = ['morning', 'afternoon', 'evening']
LONG = ['morning', 'afternoon', 'evening', 'late']
WARM = ['spring', 'summer', 'fall']

# Rents are monthly, in 1926 dollars: a furnished room, a flat of three or four rooms, a whole floor or a small house.
CHEAP = ([18, 24], [22, 32], [28, 40])
MIDDLE = ([22, 30], [28, 40], [36, 50])
BETTER = ([28, 38], [36, 50], [45, 60])

# Legends and rumours are hearsay (schema.HEARSAY_KINDS): prompts give them as what locals say, never as fact.
LEGEND, RUMOR = 'legend', 'rumor'

WALK, CAR, RAIL, FERRY, BUS = 'on-foot', 'shore-street-railway', 'boston-and-maine', 'pell-river-ferry', 'shore-road-bus'

CITY = {
    'schema_version': 1, 'id': 'pellmouth', 'name': 'Pellmouth', 'setting': 'original', 'era': ERA,
    'category': 'fictional',
    'basis': 'Original setting written for Prospero Companion: a 1920s New England town with a cosmic-horror lean, '
             'modelled on real Massachusetts river and harbour towns. Nothing is taken from Lovecraft\'s stories or '
             'later works.',
    'region': 'Massachusetts', 'country': 'United States', 'timezone': 'America/New_York',
    'aliases': ['Pellmouth, Mass.', 'Pellmouth, Massachusetts', 'Pellmouth 1926'],
    'summary': 'A fog-bound town of about eighteen thousand people at the mouth of the Pell River on the North Shore '
               'of Massachusetts, 1926: a harbour and cannery, a shut-mouthed fishing quarter, a hill of gambrel '
               'roofs and a meetinghouse sealed for thirty years, a small university with a strange bequest, shoe '
               'mills, a flooded quarry, an asylum on the bluff and a lighthouse that keeps its own hours.',
    'lat': 42.705, 'lon': -70.815,
    'currency': {'code': 'USD', 'symbol': '$', 'name': 'dollars (1926)'},
    'rent_period': 'month',
    'speeds': {'walk': 4.5, 'streetcar': 14, 'commuter-rail': 40, 'ferry': 11, 'bus': 18, 'car': 24},
    'sources': {
        S: {'kind': 'curated', 'title': 'Pellmouth, Massachusetts, written for Prospero Companion',
            'license': 'CC0-1.0', 'retrieved': '2026-10-10',
            'note': 'An invented town. Its institutions, trades, prices and yearly calendar follow what was usual '
                    'in North Shore harbour, shoe-mill, quarry and college towns of the mid-1920s, drawn from '
                    'general historical knowledge. Every business, family and person named is fictional, and the '
                    'legends and rumours are written for it; none is taken from Lovecraft or any later work. Rents '
                    'are monthly, in 1926 dollars. Coordinates sit on the Essex County coast for distance estimates '
                    'only; the climate follows that coast.'},
    },
    'neighborhoods': [
        hood('market-square', 'Market Square', 'The brick and granite downtown around the old market house: the '
             'town hall, the bank, the Courier office, dry goods, the Bijou, the Athenaeum and the Boston & Maine '
             'depot at the foot of Depot Street.', ['central', 'business', 'shopping', 'civic'], 42.705, -70.815,
             'mid', MIDDLE, ['rooms-over-store', 'apartment-hotel', 'boarding-house'], 'high', [WALK, CAR, RAIL, BUS]),
        hood('harbor-front', 'Harbor Front', 'Granite wharves, fish piers, the cannery, the Custom House and the '
             'ferry slip; it smells of tar, cod and coal smoke, and the fog horn on the point sets the rhythm of '
             'the night.', ['waterfront', 'working', 'fishing', 'busy'], 42.703, -70.806, 'low', CHEAP,
             ['boarding-house', 'rooms-over-store', 'sailors-home'], 'high', [WALK, CAR, FERRY]),
        hood('the-narrows', 'The Narrows', 'The old fishing quarter where the river pinches in: leaning clapboard '
             'houses, net lofts and a Portuguese parish. Families have fished here for generations, marry among '
             'themselves and keep their own counsel; strangers are polite to and not much more.',
             ['fishing', 'portuguese', 'close-knit', 'old', 'shabby'], 42.708, -70.801, 'low', CHEAP,
             ['clapboard-house', 'two-family-house', 'rooms-over-loft'], 'high', [WALK, FERRY]),
        hood('meetinghouse-hill', 'Meetinghouse Hill', 'A steep hill of gambrel-roofed captains\' houses from the '
             '1700s, elms, iron fences and slate gravestones, with the First Parish church, the Historical Society '
             'and the boarded-up Second Parish meetinghouse at the top.',
             ['old-money', 'historic', 'quiet', 'gambrel-roofs', 'elms'], 42.709, -70.818, 'high', BETTER,
             ['gambrel-house', 'federal-house', 'rented-rooms'], 'high', [WALK, CAR]),
        hood('college-hill', 'College Hill', 'Haskett University\'s brick halls and elm-shaded yard, the State '
             'Normal School, faculty houses, student rooming houses, the College Spa and the boathouse on the '
             'river below.', ['academic', 'students', 'leafy', 'bookish'], 42.714, -70.826, 'mid', MIDDLE,
             ['rooming-house', 'faculty-house', 'two-family-house'], 'high', [WALK, CAR]),
        hood('the-falls', 'Lower Falls', 'The shoe mills and their brick housing along the falls of the Pell, where '
             'French-Canadian families came down from Quebec to work; church bells, mill whistles and pork pies.',
             ['mills', 'french-canadian', 'working-class', 'noisy'], 42.716, -70.838, 'low', CHEAP,
             ['triple-decker', 'mill-block', 'tenement'], 'high', [WALK, CAR, BUS]),
        hood('south-end', 'South End', 'Triple-deckers, corner stores and an Irish parish south of Market Square, '
             'with the car barn, the YMCA, the ballfield and the Spiritualist hall where messages from the dead are '
             'read out on Sunday evenings.', ['irish', 'working-class', 'family', 'streetcar'], 42.698, -70.822, 'low',
             CHEAP, ['triple-decker', 'two-family-house', 'tenement'], 'high', [WALK, CAR, BUS]),
        hood('the-bluff', 'The Bluff', 'High ground north of the river mouth: the long brick wings of the State '
             'Hospital, its farm and greenhouses, a cliff walk above the rocks, and a few houses for hospital staff.',
             ['hospital', 'windswept', 'quiet', 'lonely'], 42.722, -70.808, 'low', CHEAP,
             ['staff-cottage', 'boarding-house', 'farmhouse'], 'low', [CAR, BUS]),
        hood('gannet-point', 'Gannet Point', 'The rocky point at the harbour entrance with the lighthouse, the Coast '
             'Guard station, a long beach, the summer dance pavilion and shingled cottages that stand empty from '
             'October to June.', ['coast', 'lighthouse', 'summer', 'remote'], 42.700, -70.790, 'mid', MIDDLE,
             ['summer-cottage', 'keepers-house', 'boarding-house'], 'medium', [FERRY, BUS]),
        hood('quarry-village', 'Quarry Village', 'The granite company\'s village west of town: Italian, Polish and '
             'Finnish quarry families, a cooperative store, two halls, and the old pits, some of them flooded to a '
             'depth nobody has measured.', ['quarrying', 'italian', 'polish', 'immigrant'], 42.700, -70.852, 'low',
             CHEAP, ['company-house', 'two-family-house', 'boarding-house'], 'medium', [CAR, BUS]),
        hood('west-parish', 'West Parish', 'Farms, orchards and stone walls up the river: a grange hall, a cider '
             'mill, Pratt\'s Pond where the town skates, and Sayer\'s Rock, where a widow was examined for '
             'witchcraft in 1692.', ['rural', 'farms', 'orchards', 'old-legends'], 42.722, -70.865, 'low', CHEAP,
             ['farmhouse', 'cape-house', 'rented-rooms'], 'low', [BUS]),
    ],
    'transit': [
        line(WALK, 'On foot', 'walk', 'The town is small and steep: Market Square to the wharves is five minutes, '
             'to College Hill fifteen uphill. In fog people walk by the sound of the bell buoy.'),
        line(CAR, 'Pellmouth & Shore Street Railway', 'streetcar', 'Yellow trolley cars every fifteen minutes from '
             'the South End car barn through Market Square to College Hill and the Lower Falls, and out the shore '
             'line to the Bluff; a dime a ride.'),
        line(RAIL, 'Boston & Maine Railroad', 'commuter-rail', 'Steam trains from the Depot Street station to '
             'Boston in about an hour and a quarter, and north along the coast; the evening train brings the '
             'papers.'),
        line(FERRY, 'Pell River ferry', 'ferry', 'A small steam ferry from the Harbor Front slip to the Narrows '
             'landing and on to Gannet Point, every half hour in summer and four times a day in winter; it does '
             'not run in thick fog.'),
        line(BUS, 'Shore Road motor bus', 'bus', 'Motor buses from Market Square out to Gannet Point, the State '
             'Hospital, Quarry Village and West Parish, where the trolley does not go.'),
    ],
    'places': [
        # Market Square
        place('market-house-square', 'Market Square', 'square', 'market-square', 'The cobbled square around the '
              '1790s market house, with the town pump, the war memorial and a bench where the same old-timers watch '
              'the weather and everybody else.', ['square', 'people-watching', 'market-house'], 'free', 'outdoor',
              ALL, ALLDAY),
        place('kimballs-lunch', 'Kimball\'s Lunch', 'restaurant', 'market-square', 'A narrow lunch counter of '
              'twelve stools: fish chowder, hash, pie and coffee, with the Courier\'s reporters at one end and '
              'the bank clerks at the other.', ['lunch-counter', 'chowder', 'pie', 'gossip'], '$', 'indoor',
              ['solo', 'friends', 'coworkers'], ['morning', 'afternoon'], cuisine='new-england'),
        place('tarbox-drug-store', 'Tarbox\'s Drug Store soda fountain', 'cafe', 'market-square', 'A marble soda '
              'fountain at the back of the drug store: frappes, ice cream sodas, coffee and a newspaper rack; '
              'couples come after the pictures.', ['soda-fountain', 'frappes', 'courting'], '$', 'indoor',
              ['solo', 'date', 'friends', 'family'], ALLDAY, cuisine='sweets'),
        place('abbots-chop-house', 'Abbot\'s Chop House', 'restaurant', 'market-square', 'Dark panelling, '
              'mutton chops, broiled scrod and Indian pudding, where the selectmen lunch and anyone with something '
              'to celebrate dines.', ['chop-house', 'scrod', 'old-fashioned'], '$$', 'indoor', ['date', 'friends',
              'family', 'coworkers'], ['afternoon', 'evening'], cuisine='new-england'),
        place('larkin-pratt-dry-goods', 'Larkin & Pratt Dry Goods', 'shopping', 'market-square', 'Three floors of '
              'dry goods, ready-made dresses, oilskins and wool, with cash carriers whizzing on wires to the '
              'office upstairs.', ['department-store', 'dry-goods', 'cash-railway'], '$$', 'indoor', ALL, DAY),
        place('tuttles-books', 'Tuttle\'s Antiquarian Books', 'shopping', 'market-square', 'A crooked shop of '
              'secondhand books, sea charts and town histories, with a back room of older things the owner shows '
              'only to buyers they know.', ['books', 'antiquarian', 'charts', 'back-room'], '$$', 'indoor',
              ['solo', 'friends'], DAY),
        place('bijou-theatre', 'Bijou Theatre', 'venue', 'market-square', 'Pictures with an organist, vaudeville '
              'on Saturdays and amateur nights; the balcony is where the town does its courting.', ['pictures',
              'vaudeville', 'organ', 'courting'], '$', 'indoor', ALL, ['afternoon', 'evening']),
        place('pellmouth-athenaeum', 'Pellmouth Athenaeum', 'library', 'market-square', 'A subscription library of '
              'leather armchairs, ships\' portraits and bound newspapers back to 1790, with a reading room open to '
              'anyone who keeps quiet.', ['library', 'newspapers', 'reading-room', 'quiet'], 'free', 'indoor',
              ['solo', 'friends'], ALLDAY),
        place('depot-street-station', 'Boston & Maine depot', 'landmark', 'market-square', 'The brick depot with '
              'its iron canopy, where the Boston papers come in on the evening train and the town meets whoever '
              'is coming home.', ['railroad', 'trains', 'newsstand'], 'free', 'mixed', ALL, ALLDAY),
        # Harbor Front
        place('central-wharf', 'Central Wharf and fish pier', 'docks', 'harbor-front', 'The granite fish pier where '
              'the schooners and the new motor draggers unload cod, haddock and mackerel before dawn, and gulls '
              'argue over everything.', ['fish-pier', 'schooners', 'early', 'gulls'], 'free', 'outdoor',
              ['solo', 'coworkers', 'friends'], ['morning', 'afternoon']),
        place('old-custom-house', 'Old Custom House', 'landmark', 'harbor-front', 'A granite custom house with an '
              'eagle over the door; the harbormaster posts the week\'s tide table on the board outside, and people '
              'in the Narrows read it and then do as they please.', ['custom-house', 'tide-table', 'historic'],
              'free', 'mixed', ['solo', 'friends'], DAY),
        place('driscolls-oyster-bar', 'Driscoll\'s Oyster Bar', 'restaurant', 'harbor-front', 'A long marble '
              'counter of oysters, steamers and fish chowder under a pressed-tin ceiling; the coffee comes with a '
              'nod toward the back stairs.', ['oysters', 'steamers', 'counter'], '$$', 'indoor', ['solo', 'friends',
              'date'], ['afternoon', 'evening', 'late'], cuisine='seafood'),
        place('night-boat-diner', 'The Night Boat Diner', 'restaurant', 'harbor-front', 'A dining car set down by the '
              'ferry slip, open all night for cannery shifts and fishing crews: fried eggs, beans, coffee and doughnuts '
              'at a nickel.', ['diner', 'all-night', 'coffee'], '$', 'indoor', ['solo', 'coworkers', 'friends'], LONG,
              cuisine='american'),
        place('the-ropewalk', 'The Ropewalk', 'nightlife', 'harbor-front', 'A speakeasy in the long loft of an old '
              'ropewalk, reached through a sail-maker\'s shop: Canadian whisky that came in on a foggy night, a '
              'piano, a three-piece band and a knock you have to know.', ['speakeasy', 'jazz', 'whisky', 'secret'],
              '$$', 'indoor', ADULT, NIGHT),
        place('seamens-bethel', 'Seamen\'s Bethel', 'temple', 'harbor-front', 'A plain chapel for sailors with '
              'boards on the walls naming every Pellmouth vessel lost since 1716 and everyone aboard; people stop '
              'in on the way to the wharf.', ['chapel', 'memorials', 'sailors'], 'free', 'indoor', ['solo', 'family'],
              DAY),
        place('hapgoods-chandlery', 'Hapgood\'s Ship Chandlery', 'shopping', 'harbor-front', 'Rope, oilskins, '
              'lamp oil, compasses and a wall of barometers that the old skippers tap on their way past.',
              ['chandlery', 'barometers', 'marine'], '$$', 'indoor', ['solo'], DAY),
        place('ellsworth-boatyard', 'Ellsworth\'s boatyard', 'workshop', 'harbor-front', 'A boatyard of sheds and '
              'slipways where dories and draggers are built and mended, smelling of oakum, pine tar and steam '
              'boxes.', ['boatyard', 'dories', 'craft'], 'free', 'mixed', ['solo', 'friends'], DAY),
        # The Narrows
        place('holy-ghost-church', 'Church of the Holy Ghost', 'temple', 'the-narrows', 'The Portuguese parish '
              'church, white clapboard with a blue door, where the fleet is blessed in June and the old keep '
              'candles burning for those at sea.', ['church', 'portuguese', 'candles'], 'free', 'indoor',
              ['solo', 'family'], ['morning', 'evening']),
        place('medeiros-lunch', 'Medeiros\' Lunch', 'restaurant', 'the-narrows', 'Four tables in a front room: '
              'kale soup, fish stew, linguiça and bread, and a silence when a stranger walks in that lifts once '
              'they have ordered.', ['portuguese', 'kale-soup', 'family-run'], '$', 'indoor', ['solo', 'friends',
              'family'], ['afternoon', 'evening'], cuisine='portuguese'),
        place('furtados-bakery', 'Furtado\'s Bakery', 'cafe', 'the-narrows', 'Sweet bread, malassadas on '
              'Tuesdays and strong coffee from five in the morning, when the fishing crews come in for the day\'s '
              'bread.', ['bakery', 'sweet-bread', 'early'], '$', 'indoor', ALL, DAY, cuisine='portuguese'),
        place('narrows-fish-market', 'Narrows fish market', 'market', 'the-narrows', 'Open stalls along the landing '
              'of salt cod, fresh flounder, clams and eels, sold by families who will tell you the fish but not '
              'where they caught it.', ['fish-market', 'salt-cod', 'clams'], '$', 'mixed', ['solo', 'family'],
              ['morning']),
        place('cordage-lane-net-lofts', 'Cordage Lane net lofts', 'workshop', 'the-narrows', 'Weathered lofts where '
              'nets are mended by hand and hung to dry; the menders sing in Portuguese and stop when the tide turns.',
              ['nets', 'craft', 'portuguese'], 'free', 'mixed', ['solo'], DAY),
        place('the-tide-steps', 'The tide steps', 'park', 'the-narrows', 'Worn granite steps running down into '
              'the river at the end of Water Lane; on the big spring tides the water comes up to the top step, and '
              'the Narrows lights a lamp in every window that faces it.', ['tide', 'steps', 'river', 'custom'], 'free',
              'outdoor', ['solo', 'date'], ['afternoon', 'evening']),
        place('narrows-landing-store', 'Rapoza\'s variety store', 'shopping', 'the-narrows', 'A dim little store of '
              'thread, candles, holy pictures, tobacco and penny candy, where the Narrows leaves messages for one '
              'another behind the counter.', ['variety-store', 'messages', 'candles'], '$', 'indoor', ['solo',
              'family'], DAY),
        # Meetinghouse Hill
        place('second-parish-meetinghouse', 'The old Second Parish meetinghouse', 'landmark', 'meetinghouse-hill',
              'A tall white meetinghouse boarded and chained since 1894. The town record says the congregation split '
              'and the roof failed; nobody has paid to mend it, and nobody will buy it.', ['sealed', 'church',
              'historic', 'legend'], 'free', 'outdoor', ['solo', 'friends', 'date'], DAY),
        place('hill-burying-ground', 'Old Hill Burying Ground', 'park', 'meetinghouse-hill', 'Slate stones with '
              'winged skulls and weeping willows under old elms; a quiet walk with a view of the harbour, and the '
              'sexton\'s lantern after dark.', ['cemetery', 'slate-stones', 'view', 'quiet'], 'free', 'outdoor',
              ['solo', 'date'], DAY),
        place('pellmouth-historical-society', 'Pellmouth Historical Society', 'museum', 'meetinghouse-hill',
              'A 1720s house of portraits, ship models, samplers and the county court papers of 1692, which the '
              'volunteers will show you but would rather not discuss.', ['history', 'ship-models', '1692'], '$',
              'indoor', ['solo', 'friends', 'family'], ['afternoon']),
        place('gambrel-tea-room', 'The Gambrel Tea Room', 'cafe', 'meetinghouse-hill', 'Tea, scones, chicken '
              'salad and lemon cake in the front parlours of an old house, among the hill\'s garden clubs and '
              'faculty spouses.', ['tea-room', 'cake', 'genteel'], '$$', 'indoor', ['friends', 'date',
              'family'], ['afternoon'], cuisine='tea-room'),
        place('first-parish-church', 'First Parish Church', 'temple', 'meetinghouse-hill', 'The white Unitarian '
              'church with the town clock in its steeple, where the old families sit in the same box pews their '
              'great-grandparents bought.', ['church', 'unitarian', 'clock'], 'free', 'indoor', ['solo', 'family'],
              ['morning']),
        place('wainwright-house-garden', 'Wainwright House garden', 'garden', 'meetinghouse-hill', 'A walled '
              'eighteenth-century garden of box hedges, roses and a sundial, opened to visitors by the Garden Club '
              'on afternoons in season.', ['garden', 'roses', 'walled'], 'free', 'outdoor', ['solo', 'date',
              'friends'], ['afternoon'], WARM),
        place('hill-antiques', 'Merrill Street antiques', 'shopping', 'meetinghouse-hill', 'A parlour shop of '
              'pewter, sea chests, samplers and portraits of nobody in particular, sold off by families letting '
              'go of the old houses one room at a time.', ['antiques', 'sea-chests', 'old-houses'], '$$', 'indoor',
              ['solo', 'date', 'friends'], ['afternoon']),
        # College Hill
        place('haskett-old-yard', 'Haskett University Old Yard', 'landmark', 'college-hill', 'A green of elms and '
              'red brick halls from the 1780s on, with a chapel bell that rings the hours and students lying on '
              'the grass in May.', ['university', 'elms', 'brick', 'students'], 'free', 'outdoor', ALL, ALLDAY),
        place('lindall-library', 'Lindall Library and the Whitcomb Room', 'library', 'college-hill', 'The '
              'university library, open to townspeople by card. Its Whitcomb Room keeps a family bequest of '
              'almanacs, sermons, ships\' logs and private journals that may not leave the room, and by the terms '
              'of the gift is locked at sundown.', ['library', 'special-collections', 'bequest', 'quiet'], 'free',
              'indoor', ['solo', 'friends'], ['morning', 'afternoon']),
        place('haskett-museum', 'Haskett Museum of Natural History', 'museum', 'college-hill', 'Cases of birds, '
              'shells, whale bones and things brought home by Pellmouth captains, some labelled only "Pacific, '
              'before 1840".', ['natural-history', 'curiosities', 'whaling'], '$', 'indoor', ALL, ['afternoon']),
        place('the-college-spa', 'The College Spa', 'cafe', 'college-hill', 'A corner spa of tonic, cigarettes, '
              'magazines and a lunch counter where students argue about Freud and Mencken over coffee cabinets.',
              ['spa', 'students', 'lunch-counter', 'debate'], '$', 'indoor', ['solo', 'friends', 'date'], ALLDAY,
              cuisine='american'),
        place('commons-beanery', 'The Commons Beanery', 'restaurant', 'college-hill', 'A basement lunch room of '
              'long tables where students and junior faculty eat baked beans, brown bread and hash at prices made '
              'for scholarships.', ['beanery', 'students', 'cheap-eats'], '$', 'indoor', ['solo', 'friends',
              'coworkers'], ['morning', 'afternoon', 'evening'], cuisine='new-england'),
        place('haskett-boathouse', 'Haskett boathouse', 'fitness', 'college-hill', 'A shingled boathouse on the '
              'river where the crew rows at dawn and anyone with a quarter can hire a canoe on summer evenings.',
              ['rowing', 'canoes', 'river'], '$', 'mixed', ['solo', 'friends', 'date'], ['morning', 'evening'], WARM),
        place('blanchard-observatory', 'Blanchard Observatory', 'attraction', 'college-hill', 'A small domed '
              'observatory with public nights on clear Fridays, which in Pellmouth are fewer than the astronomers '
              'would like.', ['telescope', 'stars', 'public-nights'], 'free', 'indoor', ['solo', 'date', 'family'],
              ['evening']),
        place('haskett-chapel', 'Haskett chapel', 'temple', 'college-hill', 'A plain brick chapel with a bell that '
              'rings the hours and an organ students practise on at odd times of night.', ['chapel', 'organ', 'bell'],
              'free', 'indoor', ['solo', 'date'], ['morning', 'evening']),
        # Lower Falls
        place('st-jean-baptiste', 'St. Jean-Baptiste Church', 'temple', 'the-falls', 'The big brick church of the '
              'French-Canadian parish, with sermons in French, a parochial school and a bell that wakes the mill '
              'blocks on Sunday.', ['church', 'french-canadian', 'bells'], 'free', 'indoor', ['solo', 'family'],
              ['morning']),
        place('falls-diner', 'The Falls Diner', 'restaurant', 'the-falls', 'A Worcester lunch car by the mill gate, '
              'serving the shifts eggs, hash, pea soup and coffee from five in the morning till midnight.',
              ['diner', 'mill-shifts', 'pea-soup'], '$', 'indoor', ['solo', 'coworkers', 'friends'], LONG,
              cuisine='american'),
        place('cotes-market', 'Côté\'s Market', 'market', 'the-falls', 'A corner grocery of salt pork, molasses, '
              'tourtière at Christmas, maple sugar in spring and credit on the slate until payday.',
              ['grocery', 'french-canadian', 'credit'], '$', 'indoor', ['solo', 'family'], DAY),
        place('club-lafayette', 'Club Social Lafayette', 'bar', 'the-falls', 'A members\' club over a hardware '
              'store with cards, a pool table and near beer on the price list; the real beer is brewed in a cellar '
              'two streets over.', ['social-club', 'cards', 'home-brew'], '$', 'indoor', ['solo', 'friends'], NIGHT),
        place('lafayette-bowling', 'Lafayette Bowling Alleys', 'fitness', 'the-falls', 'Eight candlepin lanes with '
              'pinsetters, a league every weeknight and the clatter of pins until eleven.',
              ['candlepin', 'leagues', 'bowling'], '$', 'indoor', ['friends', 'date', 'coworkers'], NIGHT),
        place('falls-footbridge', 'The falls footbridge', 'park', 'the-falls', 'An iron footbridge over the falls '
              'where mill workers eat lunch in the spray and couples walk after the evening shift.',
              ['falls', 'bridge', 'river', 'lunch'], 'free', 'outdoor', ALL, ALLDAY),
        # South End
        place('st-brendans', 'St. Brendan\'s Church', 'temple', 'south-end', 'The Irish parish church, with a '
              'Sunday crowd that spills down the steps and a parish hall that holds whist drives and dances.',
              ['church', 'irish', 'whist'], 'free', 'indoor', ['solo', 'family'], ['morning', 'evening']),
        place('pellmouth-ymca', 'Pellmouth YMCA', 'fitness', 'south-end', 'A brick Y with a swimming tank, a '
              'running track over the gym, boxing on Tuesday nights and Bible classes nobody is made to attend.',
              ['ymca', 'swimming', 'boxing', 'gym'], '$', 'indoor', ['solo', 'friends', 'family'], ALLDAY),
        place('odays-lunch-room', 'O\'Day\'s Lunch Room', 'restaurant', 'south-end', 'Corned beef, boiled dinner on '
              'Thursdays, fish cakes on Fridays and a counter where the car-barn crews take their dinner.',
              ['lunch-room', 'boiled-dinner', 'irish'], '$', 'indoor', ['solo', 'coworkers', 'family'], ALLDAY,
              cuisine='irish-american'),
        place('spiritualist-hall', 'First Spiritualist Society hall', 'venue', 'south-end', 'A plain upstairs hall '
              'with folding chairs and a harmonium, where Sunday evening services end with a medium reading '
              'messages for whoever came hoping for one.', ['spiritualism', 'seances', 'sunday'], '$', 'indoor',
              ['solo', 'friends', 'family'], ['evening']),
        place('riverside-oval', 'Riverside Oval', 'park', 'south-end', 'A cinder-ringed ballfield by the river where '
              'the Twilight League plays after supper and the high school plays football on Thanksgiving morning.',
              ['baseball', 'twilight-league', 'football'], 'free', 'outdoor', ALL, ['afternoon', 'evening']),
        place('mahoneys-garage', 'The back room at Mahoney\'s Garage', 'nightlife', 'south-end', 'A speakeasy behind '
              'a garage where you drink gin out of teacups among tyre racks, and a fiddler and a banjo play reels '
              'and foxtrots by turns.', ['speakeasy', 'gin', 'dancing'], '$', 'indoor', ADULT, NIGHT),
        place('hibernian-hall', 'Hibernian Hall', 'venue', 'south-end', 'A dance hall over a block of shops with '
              'Saturday dances, a St. Patrick\'s ball and a polished floor the young people wear thin.',
              ['dance-hall', 'saturday-dances', 'irish'], '$', 'indoor', ['friends', 'date'], NIGHT),
        place('kellehers-market', 'Kelleher\'s Market', 'market', 'south-end', 'A corner grocery and meat market '
              'with sawdust on the floor, corned beef in the barrel and the week\'s gossip at the register.',
              ['grocery', 'butcher', 'corner-store'], '$', 'indoor', ['solo', 'family'], DAY),
        # The Bluff
        place('state-hospital-grounds', 'State Hospital grounds', 'park', 'the-bluff', 'The long brick wings '
              'and central tower of Pellmouth State Hospital, set in lawns behind an iron fence; families walk '
              'there on visiting Sundays, and townsfolk lower their voices driving past.', ['hospital', 'tower',
              'lawns', 'visiting-day'], 'free', 'outdoor', ['solo', 'family'], DAY),
        place('bluff-cliff-walk', 'Bluff cliff walk', 'trail', 'the-bluff', 'A path along the cliff above the rocks '
              'with the whole harbour mouth below, the light on the point opposite and the fog coming in like a '
              'wall.', ['cliff', 'sea-view', 'fog', 'walk'], 'free', 'outdoor', ['solo', 'date', 'friends'],
              ['morning', 'afternoon']),
        place('hospital-road-inn', 'Hospital Road Inn', 'inn', 'the-bluff', 'A plain inn by the hospital gate for '
              'families come to visit, with a dining room of pot roast and pie and a landlord who never asks whom '
              'you have come to see.', ['inn', 'pot-roast', 'visitors'], '$$', 'indoor', ['solo', 'family'],
              ALLDAY, cuisine='new-england'),
        place('bluff-general-store', 'Ellery\'s general store', 'market', 'the-bluff', 'Groceries, tobacco, '
              'postcards and the post office in one, kept by a family who have sold to hospital staff for forty '
              'years.', ['general-store', 'post-office'], '$', 'indoor', ['solo', 'family'], DAY),
        place('hospital-farm', 'State Hospital farm and greenhouses', 'garden', 'the-bluff', 'Fields, a dairy and '
              'glasshouses worked by patients and attendants; the greenhouse sells cut flowers and seedlings at '
              'the gate.', ['farm', 'greenhouses', 'flowers'], '$', 'mixed', ['solo', 'family'], DAY, WARM),
        place('laceys-parlor', 'The Lacey parlour', 'attraction', 'the-bluff', 'A front parlour in a '
              'staff cottage where a medium holds private sittings by lamplight, with tea after and a donation '
              'jar on the hall table.', ['seances', 'spiritualism', 'parlour'], '$', 'indoor', ['solo', 'friends'],
              ['evening']),
        # Gannet Point
        place('gannet-point-light', 'Gannet Point Light', 'landmark', 'gannet-point', 'A white stone tower and '
              'keeper\'s house on the rocks at the harbour mouth. The lamp is lit at sunset by the almanac, and '
              'sometimes well before it, which the keeper puts down to the fog.', ['lighthouse', 'fog-bell', 'rocks',
              'legend'], 'free', 'outdoor', ['solo', 'date', 'family'], ['afternoon', 'evening']),
        place('long-sands-beach', 'Long Sands beach', 'beach', 'gannet-point', 'A mile of sand inside the point '
              'with bathhouses, cold water, picnics in July and a bonfire on the Fourth.', ['beach', 'bathing',
              'picnics'], 'free', 'outdoor', ALL, DAY, ['summer']),
        place('gannet-pavilion', 'Gannet Point Pavilion', 'venue', 'gannet-point', 'A summer dance pavilion on '
              'pilings with a bandstand, Japanese lanterns and dance tickets at a dime; it shuts after the Harvest '
              'Moon dance.', ['dance-pavilion', 'bands', 'summer'], '$', 'mixed', ['friends', 'date'], NIGHT,
              ['summer', 'fall']),
        place('pikes-clam-shack', 'Pike\'s Clam Shack', 'restaurant', 'gannet-point', 'A shack on the causeway frying '
              'clams in lard and selling them in paper boats with a pickle, from Decoration Day to Labor Day.',
              ['fried-clams', 'take-away', 'summer'], '$', 'outdoor', ALL, ['afternoon', 'evening'], ['summer'],
              cuisine='seafood'),
        place('the-gannet-house', 'The Gannet House', 'inn', 'gannet-point', 'A shingled inn that stays open all '
              'year, with a parlour fire, fish dinners, and a ledger of guests going back to 1868 that the '
              'proprietor likes to read aloud from.', ['inn', 'fish-dinners', 'fireside'], '$$', 'indoor', ['date',
              'family', 'friends'], ALLDAY, cuisine='seafood'),
        place('point-ledges', 'The Ledges', 'park', 'gannet-point', 'Flat granite ledges below the lighthouse full '
              'of tide pools, where children hunt crabs and the old people say not to stay past the turn.',
              ['tide-pools', 'rocks', 'sea'], 'free', 'outdoor', ALL, DAY, WARM),
        place('coast-guard-station', 'Gannet Point Coast Guard station', 'landmark', 'gannet-point', 'A shingled '
              'lifeboat station with a lookout tower and a wireless mast, where the crew drills on the beach every '
              'morning and watches for rum-runners every night.', ['coast-guard', 'lifeboat', 'wireless'], 'free',
              'outdoor', ALL, DAY),
        # Quarry Village
        place('number-four-quarry', 'Number Four quarry', 'park', 'quarry-village', 'A granite pit abandoned in '
              '1908 when it struck a spring and flooded overnight; the water is black and very still, and the '
              'company has fenced it twice.', ['quarry', 'flooded', 'legend'], 'free', 'outdoor', ['solo', 'friends'],
              DAY),
        place('the-deep-hole', 'The Deep Hole', 'beach', 'quarry-village', 'An old pit with a granite ledge to jump '
              'from, where young people swim in summer despite the signs and the stories.', ['swimming', 'quarry',
              'summer'], 'free', 'outdoor', ['friends', 'date'], ['afternoon'], ['summer']),
        place('zanettis', 'Zanetti\'s', 'restaurant', 'quarry-village', 'A front-room restaurant of spaghetti, '
              'veal and bread, with red wine served in coffee cups and accordion music on Saturdays.',
              ['italian', 'spaghetti', 'family-run', 'wine'], '$', 'indoor', ['friends', 'date', 'family'],
              ['afternoon', 'evening'], cuisine='italian'),
        place('quarry-cooperative-store', 'Quarry Workers\' Cooperative Store', 'market', 'quarry-village', 'A '
              'cooperative store run by the Finnish and Italian families, with flour, olive oil, rye bread, dried '
              'fish and a share for every member.', ['cooperative', 'groceries', 'immigrant'], '$', 'indoor',
              ['solo', 'family'], DAY),
        place('mutuo-soccorso-hall', 'Società di Mutuo Soccorso hall', 'venue', 'quarry-village', 'The Italian '
              'mutual-aid society\'s hall, with bocce out back, a bar that sells only coffee and anisette, and '
              'dances on feast days.', ['italian', 'bocce', 'dances', 'hall'], '$', 'mixed', ['friends', 'family'],
              NIGHT),
        place('polish-national-home', 'Polish National Home', 'bar', 'quarry-village', 'A hall with a long bar, '
              'kielbasa and pickles, a polka band on Saturdays and a choir practising upstairs on Wednesdays.',
              ['polish', 'polka', 'hall'], '$', 'indoor', ['friends', 'family', 'date'], NIGHT),
        place('st-casimir', 'St. Casimir\'s Church', 'temple', 'quarry-village', 'A wooden Polish church the '
              'quarry families built themselves on Sundays, with a painted ceiling and a choir that can be heard '
              'from the pits.', ['church', 'polish', 'choir'], 'free', 'indoor', ['solo', 'family'], ['morning']),
        # West Parish
        place('pratts-pond', 'Pratt\'s Pond', 'park', 'west-parish', 'A spring-fed pond ringed by pines where '
              'families picnic in summer, with a warming hut for skaters and a willow children dare each other to '
              'climb.', ['pond', 'picnics', 'pines'], 'free', 'outdoor', ALL, DAY),
        place('pratts-pond-skating', 'Skating on Pratt\'s Pond', 'fitness', 'west-parish', 'The whole town skates '
              'on Pratt\'s Pond once the selectmen hang out the red ball, with a bonfire, hot cider and a hockey '
              'game at one end.', ['skating', 'bonfire', 'winter'], 'free', 'outdoor', ALL, ['afternoon', 'evening'],
              ['winter']),
        place('sayers-rock', 'Sayer\'s Rock', 'trail', 'west-parish', 'A split boulder in a hayfield where, the '
              'story goes, the widow Annis Sayer was examined in 1692 and from which she was never seen to come '
              'down. Nothing grows in the crack, and the farmer mows around it.', ['legend', '1692', 'boulder'],
              'free', 'outdoor', ['solo', 'friends', 'date'], DAY),
        place('dodges-cider-mill', 'Dodge\'s cider mill', 'market', 'west-parish', 'A press barn of sweet cider, '
              'doughnuts, apples by the peck and jugs of hard cider sold to people the family knows.',
              ['cider', 'apples', 'doughnuts'], '$', 'mixed', ALL, DAY, ['fall'], cuisine='farm'),
        place('west-parish-grange', 'West Parish Grange Hall', 'venue', 'west-parish', 'A plain hall of bean '
              'suppers, contra dances with a fiddler caller, and the Harvest Moon dance in October.', ['grange',
              'contra-dance', 'bean-supper'], '$', 'indoor', ALL, ['evening']),
        place('wayside-roadhouse', 'The Wayside', 'nightlife', 'west-parish', 'A roadhouse on the Boston road with '
              'chicken dinners, a dance floor and a back room where the cider is applejack; the motorcar crowd '
              'drives out from town on Saturday nights.', ['roadhouse', 'chicken-dinner', 'dancing', 'applejack'],
              '$$', 'indoor', ['friends', 'date'], NIGHT, cuisine='american'),
    ],
    'colleges': [
        college('haskett-university', 'Haskett University', 'private-university', 'college-hill', 'small',
                ['classics', 'theology', 'natural-history', 'astronomy', 'special-collections', 'rowing']),
        college('pellmouth-normal-school', 'Pellmouth State Normal School', 'liberal-arts-college', 'college-hill', 'small',
                ['teacher-training', 'model-school', 'domestic-science']),
    ],
    'careers': [
        career('asylum-attendant', 'Asylum attendant', 'healthcare', 'rotating', '$', 'Twelve-hour shifts on the '
               'wards of the State Hospital: bathing, feeding and watching patients, walking them on the lawns, and '
               'living in the attendants\' home.', ['the wards', 'patients', 'night shifts', 'the doctors']),
        career('lighthouse-keeper', 'Lighthouse keeper', 'maritime', 'rotating', '$$', 'Keeping the Gannet Point '
               'lamp lit, the lens polished, the fog bell rung and the log written up, through every watch of the '
               'night.', ['the lamp', 'the log', 'fog', 'the weather']),
        career('rare-books-cataloguer', 'Rare-books cataloguer', 'education', 'office', '$$', 'Cataloguing the '
               'Whitcomb bequest card by card at the Lindall Library, in a room that must be locked at sundown.',
               ['old books', 'the catalogue', 'the bequest', 'readers']),
        career('tide-clerk', 'Tide-table clerk', 'maritime', 'office', '$', 'Working out and posting the week\'s '
               'tides, keeping the harbormaster\'s ledgers and logging every vessel in and out.',
               ['tides', 'ledgers', 'the harbor', 'skippers']),
        career('cannery-hand', 'Fish-cannery hand', 'fishing', 'early', '$', 'Gutting, packing and sealing fish at '
               'the Pell River Packing Company, on shifts set by whatever the boats bring in.',
               ['the line', 'the smell', 'piece rates', 'the boats']),
        career('spiritualist-medium', 'Séance medium', 'spiritualism', 'evening', '$', 'Holding sittings in a front '
               'parlour and reading messages at the Spiritualist hall for people who have lost someone.',
               ['sittings', 'clients', 'the departed', 'skeptics']),
        career('dowser', 'Dowser', 'trades', 'flexible', '$', 'Walking farms and house lots with a forked witch-hazel '
               'stick to find where a well should go, paid if the water comes.', ['wells', 'farmers', 'the rod',
               'water']),
        career('quarry-worker', 'Quarry worker', 'quarrying', 'early', '$$', 'Drilling, blasting and splitting '
               'granite in the Pellmouth Granite Company pits, by derrick and steam drill.',
               ['the pit', 'blasting', 'the derricks', 'the union']),
        career('sexton', 'Sexton', 'religion', 'early', '$', 'Ringing the bell, minding the furnace, keeping the '
               'burying ground and digging the graves for First Parish.', ['the bell', 'graves', 'the church',
               'the burying ground']),
        career('folklore-lecturer', 'Folklore lecturer', 'education', 'academic', '$$', 'Teaching New England '
               'folklore at Haskett and collecting ballads, sayings and stories from old people who would rather '
               'not be written down.', ['lectures', 'field notes', 'old stories', 'students']),
        career('wireless-operator', 'Wireless operator', 'communications', 'shift-night', '$$', 'Keeping the night '
               'watch on the Coast Guard station\'s wireless set, and a radio ham in the off hours who talks to '
               'strangers across the ocean.', ['the wireless', 'distress calls', 'night watch', 'far stations']),
        career('clam-digger', 'Clam digger', 'fishing', 'early', '$', 'Digging soft-shell clams on the flats at low '
               'tide with a fork and a hod, and selling them to the clam shacks and the cannery.', ['the flats',
               'low tide', 'the catch', 'the weather']),
        career('boatbuilder', 'Boatbuilder', 'trades', 'early', '$$', 'Building and mending dories and draggers at '
               'Ellsworth\'s yard by eye, adze and steam box.', ['the yard', 'planking', 'the boats', 'skippers']),
        career('ferry-deckhand', 'Ferry deckhand', 'transit', 'rotating', '$', 'Handling lines, fares and the '
               'gangway on the Pell River ferry, and telling the skipper when the fog is too thick to cross.',
               ['the ferry', 'passengers', 'fog', 'the river']),
    ],
    'employers': [
        employer('haskett-university-employer', 'Haskett University', 'education', 'college-hill', 'medium', 'A small '
                 'old university of six hundred students, a library with a famous and peculiar bequest, a museum and '
                 'an observatory.', ['professor', 'librarian', 'rare-books-cataloguer', 'folklore-lecturer',
                 'museum-curator']),
        employer('normal-school-employer', 'Pellmouth State Normal School', 'education', 'college-hill', 'small',
                 'The state teachers\' college and its model school, training schoolteachers for the North Shore.',
                 ['teacher', 'professor']),
        employer('pellmouth-state-hospital', 'Pellmouth State Hospital', 'healthcare', 'the-bluff', 'large', 'The '
                 'state hospital for the insane on the bluff, with fourteen hundred patients, its own farm, laundry '
                 'and power house, and the largest payroll in town.', ['physician', 'trained-nurse',
                 'asylum-attendant']),
        employer('gannet-point-station', 'Gannet Point Light and Coast Guard station', 'maritime', 'gannet-point',
                 'small', 'The lighthouse, its keepers and the Coast Guard lifeboat station beside it, which also '
                 'keeps a lookout for rum-runners.', ['lighthouse-keeper', 'wireless-operator']),
        employer('harbormasters-office', 'Harbormaster\'s office', 'maritime', 'harbor-front', 'small', 'The '
                 'harbormaster and clerks in the Old Custom House, keeping moorings, tides and the vessel log.',
                 ['tide-clerk']),
        employer('pell-river-packing', 'Pell River Packing Company', 'fishing', 'harbor-front', 'medium', 'The '
                 'cannery on the wharf, packing sardines, fish flakes and chowder clams for grocers across New '
                 'England.', ['cannery-hand', 'longshoreman']),
        employer('narrows-fishermens-cooperative', 'Narrows Fishermen\'s Cooperative', 'fishing', 'the-narrows',
                 'small', 'The Narrows families\' co-op of boats, nets, ice house and fish stalls.',
                 ['fisherman', 'clam-digger']),
        employer('ellsworth-boatyard-employer', 'Ellsworth\'s boatyard', 'trades', 'harbor-front', 'small', 'A '
                 'family boatyard building dories and fishing draggers.', ['boatbuilder']),
        employer('pellmouth-granite', 'Pellmouth Granite Company', 'quarrying', 'quarry-village', 'medium', 'The '
                 'granite company working four pits west of town for paving blocks, curbstone and monuments.',
                 ['quarry-worker']),
        employer('hatch-merrill-shoe', 'Hatch & Merrill Shoe Company', 'manufacturing', 'the-falls', 'large',
                 'Two brick shoe mills at the falls making work boots and women\'s shoes, on piece rates.',
                 ['mill-hand', 'factory-hand']),
        employer('pellmouth-courier', 'Pellmouth Evening Courier', 'media', 'market-square', 'small', 'The town\'s '
                 'evening paper: shipping news, tide tables, court reports and the social column.',
                 ['journalist', 'linotype-operator', 'newsboy']),
        employer('tibbetts-funeral-home', 'Tibbetts & Son Funeral Home', 'trades', 'meetinghouse-hill', 'small',
                 'The old funeral parlour in a gambrel house on Church Street, three generations in the trade.',
                 ['undertaker']),
        employer('first-parish-employer', 'First Parish Church', 'religion', 'meetinghouse-hill', 'small', 'The '
                 'Unitarian church of the old families, and keeper of the Old Hill Burying Ground.',
                 ['minister', 'sexton']),
        employer('first-spiritualist-society', 'First Spiritualist Society', 'spiritualism', 'south-end', 'small',
                 'A Spiritualist congregation with an upstairs hall, Sunday message services and mediums who also '
                 'sit privately for a fee.', ['spiritualist-medium']),
        employer('shore-street-railway-company', 'Pellmouth & Shore Street Railway', 'transit', 'south-end', 'medium',
                 'The trolley company and its car barn.', ['streetcar-motorman']),
        employer('pellmouth-police', 'Pellmouth Police Department', 'law', 'market-square', 'small', 'Two dozen '
                 'officers working out of the town hall basement, more busy with fog than with crime.',
                 ['police-patrolman']),
        employer('pellmouth-telephone-exchange', 'Pellmouth telephone exchange', 'communications', 'market-square',
                 'small', 'The switchboard over the bank where every call in town goes through a pair of hands.',
                 ['switchboard-operator', 'telegraph-operator']),
    ],
    'career_hubs': [
        {'id': 'hub-waterfront', 'name': 'The waterfront', 'neighborhoods': ['harbor-front', 'the-narrows',
         'gannet-point'], 'sectors': ['fishing', 'logistics', 'maritime', 'transit', 'trades', 'underworld',
         'defense'], 'summary': 'Wharves, the cannery, the boatyard, the ferry, the light and every boat in the '
         'harbour, including the ones that come in without lights.', 'source': S},
        {'id': 'hub-hill', 'name': 'The hill and the square', 'neighborhoods': ['market-square', 'college-hill',
         'meetinghouse-hill', 'the-bluff'], 'sectors': ['education', 'healthcare', 'religion', 'spiritualism', 'media',
         'communications', 'law', 'legal', 'finance', 'business', 'retail', 'hospitality', 'entertainment',
         'real-estate', 'social-services', 'technology', 'domestic'], 'summary': 'The university, the State Hospital, '
         'the churches, the bank, the paper and the shops.', 'source': S},
        {'id': 'hub-mills', 'name': 'The mills and the pits', 'neighborhoods': ['the-falls', 'quarry-village',
         'south-end', 'west-parish'], 'sectors': ['manufacturing', 'quarrying', 'construction', 'food', 'railroad',
         'creative', 'recreation'], 'summary': 'The shoe mills at the falls, the granite pits, the car barn and the '
         'farms up the river.', 'source': S},
    ],
    'climate': {
        'summary': 'The North Shore coast: cold snowy winters with nor\'easters, a raw late spring, fog banks off the '
                   'water from May to July, warm summers cooled by the sea breeze, and a clear, bright autumn.',
        'months': [
            {'high_f': 35, 'low_f': 19, 'rain_days': 11, 'note': 'Cold and grey; nor\'easters bring snow and tides '
             'over the wharves.'},
            {'high_f': 37, 'low_f': 21, 'rain_days': 10, 'note': 'Snow on the ground, ice in the river; the winter '
             'carnival.'},
            {'high_f': 44, 'low_f': 28, 'rain_days': 11, 'note': 'Raw and windy, with the worst of the nor\'easters.'},
            {'high_f': 54, 'low_f': 37, 'rain_days': 11, 'note': 'Cold rain, mud and the first fog banks.'},
            {'high_f': 64, 'low_f': 46, 'rain_days': 11, 'note': 'Lilacs on the hill; fog most mornings until noon.'},
            {'high_f': 73, 'low_f': 55, 'rain_days': 10, 'note': 'Sea fog rolls in at evening; the fog horn sounds '
             'half the night.'},
            {'high_f': 79, 'low_f': 61, 'rain_days': 9, 'note': 'Warm days, sea breeze, and fog that comes and goes '
             'in an hour.'},
            {'high_f': 78, 'low_f': 60, 'rain_days': 9, 'note': 'The warmest water of the year; thunderstorms over '
             'the flats.'},
            {'high_f': 71, 'low_f': 53, 'rain_days': 9, 'note': 'Clear and golden; a gale now and then.'},
            {'high_f': 60, 'low_f': 42, 'rain_days': 9, 'note': 'Bright leaves, frost in West Parish, the Harvest '
             'Moon.'},
            {'high_f': 50, 'low_f': 34, 'rain_days': 10, 'note': 'Grey and blowing; nor\'easter season begins.'},
            {'high_f': 40, 'low_f': 25, 'rain_days': 11, 'note': 'Short dark days, first snow, ice creeping out on '
             'the pond.'},
        ],
        'source': S,
    },
    'annual_events': [
        event('winter-carnival', 'Haskett Winter Carnival', [2], 'college-hill', 'A weekend of ski jumping off the '
              'observatory hill, snow sculptures in the Old Yard, a torchlight skate and the Carnival Ball.'),
        event('commencement', 'Haskett commencement', [6], 'college-hill', 'Caps and gowns in the Old Yard, the '
              'chapel bell, class day picnics and parents filling every room in town.'),
        event('blessing-of-the-fleet', 'Blessing of the Fleet', [6], 'the-narrows', 'The priest of the Holy Ghost '
              'blesses every boat from the end of the landing, the boats circle the harbour dressed in flags, and '
              'the Narrows holds open house for an afternoon.'),
        event('founders-day', 'Founders\' Day', [6], 'market-square', 'The town\'s birthday, kept since 1843: a '
              'parade of the militia, fire companies and schools, an oration on the common and a band concert.'),
        event('holy-ghost-feast', 'Feast of the Holy Ghost', [7], 'the-narrows', 'The Narrows\' festa: a crowning '
              'in the church, a procession, and free sopas of beef and bread for everyone, strangers included.'),
        event('fourth-of-july', 'The Fourth', [7], 'gannet-point', 'Bells at dawn, the parade through Market Square, '
              'a band at the pavilion and a bonfire on Long Sands.'),
        event('lights-on-the-river', 'The night of the lights on the river', [8], 'the-narrows', 'On the night of '
              'the lowest August tide the Narrows floats candles in paper boats down the river from the tide steps, '
              'for the drowned. The rest of town comes to watch; nobody explains why it must be that night.'),
        event('sayers-night', 'The last night of September', [9], 'west-parish', 'The anniversary of the widow '
              'Sayer\'s examination, which the town does not mark: shops close early, curtains are drawn, the '
              'Historical Society shuts at noon, and nobody is in the hayfield after dark.'),
        event('harvest-moon-dance', 'Harvest Moon dance', [10], 'west-parish', 'The grange hall\'s big dance of the '
              'year under paper lanterns, with a fiddler caller, cider and a supper of baked beans and pie.'),
        event('armistice-day', 'Armistice Day', [11], 'market-square', 'Silence at eleven at the war memorial, '
              'the Legion parade, and names of the Pellmouth dead read out from the town hall steps.'),
        event('first-ice', 'First ice on Pratt\'s Pond', [12, 1], 'west-parish', 'The day the selectmen declare the '
              'ice safe and hang out the red ball, half the town skips work to skate.'),
    ],
    'local_color': [
        color('mind-the-tide', '"Mind the tide"', 'saying', 'The Narrows\' way of saying goodbye, and also of '
              'saying mind your own business; strangers rarely know which is meant.', ['the-narrows']),
        color('up-the-bluff', '"Gone up the Bluff"', 'saying', 'Said of someone committed to the State Hospital, '
              'in a low voice, and never in front of the family.', ['state-hospital-grounds']),
        color('the-lights-early', '"The light\'s early"', 'saying', 'Said when the Gannet Point lamp is lit before '
              'sunset: the boats stay in, parents call the children home, and the Courier blames the fog.',
              ['gannet-point-light']),
        color('wicked', '"Wicked"', 'saying', 'The North Shore\'s all-purpose intensifier: wicked cold, wicked good, '
              'a wicked lot of fog.'),
        color('tide-lamps', 'Lamps on the spring tides', 'custom', 'In the Narrows a lamp burns in every window that '
              'faces the river on the nights of the big spring tides. Ask why and you are told it always has.',
              ['the-tide-steps']),
        color('no-whistling', 'No whistling on the wharf', 'custom', 'Nobody whistles on a Pellmouth wharf or '
              'aboard a boat; it calls up wind, or worse, and a newcomer who does it is told once.',
              ['central-wharf']),
        color('whitcomb-sundown', 'Out of the Whitcomb Room by sundown', 'custom', 'By the terms of the bequest the '
              'Whitcomb Room is locked at sundown, and the librarians clear it ten minutes early, every day, '
              'without exception.', ['lindall-library']),
        color('beans-saturday', 'Saturday beans', 'dish', 'Baked beans with salt pork and molasses and steamed '
              'brown bread for Saturday supper, in nearly every kitchen in town.', ['commons-beanery']),
        color('fish-chowder', 'Fish chowder', 'dish', 'Haddock, potatoes, salt pork and milk, never tomatoes; '
              'arguing about the crackers is allowed.', ['kimballs-lunch', 'driscolls-oyster-bar']),
        color('fried-clams', 'Fried clams', 'dish', 'Whole-belly clams fried in lard in a paper boat, a summer '
              'thing from the shacks on the causeway.', ['pikes-clam-shack'], ['summer']),
        color('kale-soup', 'Kale soup', 'dish', 'The Narrows\' soup of kale, potatoes, beans and linguiça, on the '
              'stove all winter.', ['medeiros-lunch'], ['fall', 'winter']),
        color('tourtiere', 'Tourtière', 'dish', 'Spiced pork pie the Falls families bake for Christmas Eve after '
              'midnight mass.', ['cotes-market'], ['winter']),
        color('frappe', 'A frappe', 'drink', 'Ice cream shaken with milk and syrup; in Pellmouth a milkshake has '
              'no ice cream in it, and visitors find out the hard way.', ['tarbox-drug-store']),
        color('canadian-whisky', 'Canadian', 'drink', 'Whisky that came down from Nova Scotia on a schooner and in '
              'over the flats on a foggy night; the town calls it simply "Canadian".', ['the-ropewalk']),
        color('hard-cider', 'West Parish hard cider', 'drink', 'Cider left to work in the barrel over the winter, '
              'legal if you made it yourself and sold by the jug to people the family knows.',
              ['dodges-cider-mill', 'wayside-roadhouse'], ['fall', 'winter']),
        color('twilight-league', 'The Twilight League', 'team', 'Mill, car barn, cannery and quarry teams playing '
              'seven innings after supper at Riverside Oval, with bets the whole town knows about.',
              ['riverside-oval'], ['spring', 'summer']),
        color('haskett-crew', 'The Haskett crew', 'team', 'The university eight, who row the river at dawn and lose '
              'to bigger colleges every spring with great dignity.', ['haskett-boathouse'], ['spring']),
        color('annis-sayer', 'The widow Sayer', LEGEND, 'Annis Sayer, a widow of West Parish, was examined for '
              'witchcraft on a boulder in 1692. The court papers stop mid-page; the story says she was never seen to '
              'come down.', ['sayers-rock', 'pellmouth-historical-society']),
        color('sealed-meetinghouse', 'The sealed meetinghouse', LEGEND, 'The Second Parish meetinghouse was shut '
              'in 1894 after a winter service nobody who attended would describe. The record says a quarrel and a '
              'bad roof.', ['second-parish-meetinghouse']),
        color('no-bottom', 'Number Four has no bottom', LEGEND, 'Quarry Village says nobody has ever sounded the '
              'bottom of Number Four, that the water is warm in January, and that what goes in does not come up.',
              ['number-four-quarry']),
        color('tide-folk', 'The Narrows know the tide', RUMOR, 'Uptown it is said the Narrows families know the '
              'tides better than the printed tables, and that on some nights they go down to the steps to meet it. '
              'The Narrows says uptown talks too much.', ['the-tide-steps', 'old-custom-house']),
        color('whitcomb-journals', 'What is in the Whitcomb Room', RUMOR, 'Students swear one of the Whitcomb '
              'journals is written in no known language, and that a professor who asked to take it home left the '
              'faculty the same term.', ['lindall-library']),
        color('fourth-floor', 'The fourth floor of the tower', RUMOR, 'Attendants say nobody is ever assigned to '
              'the top floor of the State Hospital tower, and that its lights are on all the same.',
              ['state-hospital-grounds']),
        color('college-spa-shop', 'The spa', 'shop', 'A Massachusetts "spa" is a corner store with a soda fountain, '
              'tobacco and magazines; the College Spa on College Hill is the one everybody means.',
              ['the-college-spa']),
        color('tuttles-back-room', 'Tuttle\'s back room', 'shop', 'The antiquarian bookshop keeps its oldest stock '
              'in a back room shown only to customers it knows, which is most of what anyone talks about.',
              ['tuttles-books']),
    ],
    'prices': [
        price('coffee', 'Cup of coffee', 0.05, 0.1),
        price('lunch-counter', 'Lunch at a counter', 0.25, 0.5),
        price('chop-house-dinner', 'Dinner at the chop house', 0.75, 1.5),
        price('oysters', 'Oysters', 0.35, 0.6, 'a dozen on the half shell'),
        price('fried-clams', 'Fried clams', 0.25, 0.4, 'a paper boat'),
        price('ice-cream-soda', 'Ice cream soda or frappe', 0.15, 0.25),
        price('pictures', 'Seat at the pictures', 0.1, 0.35),
        price('streetcar-fare', 'Trolley fare', 0.1, 0.1, 'a ride'),
        price('train-to-boston', 'Train to Boston', 0.85, 1.4, 'one way'),
        price('newspaper', 'Evening Courier', 0.02, 0.03),
        price('haircut', 'Haircut', 0.35, 0.5),
        price('bootleg-gin', 'Bootleg gin', 1.5, 3, 'a pint'),
        price('seance-sitting', 'Private sitting with a medium', 0.5, 2),
        price('room-and-board', 'Room and board', 8, 12, 'a week'),
        price('groceries', 'Groceries for a family', 7, 11, 'a week'),
        price('wage', 'Day wage', 4, 6, 'a day in the mills, the pits or the cannery; clerks $20-$30 a week'),
    ],
    # The town's own quirks and goals for its townsfolk, drawn beside the shared ones: everyday habits of a harbour
    # town, uncanny only as mood. Nothing here says anything strange is real.
    'townsfolk': {
        'quirks': [
            {'text': 'keeps the tide table pinned by the door', 'bio': 'I know when high water is. Always.'},
            {'text': "won't whistle near the water after dark",
             'bio': 'I will not whistle by the harbour after dark. Do not ask me why; nobody here does.'},
            {'text': 'counts the foghorn blasts under their breath', 'bio': 'I count the foghorn. It passes the time.'},
            {'text': 'always takes the long way round the old meetinghouse',
             'bio': 'I take the long way round the old meetinghouse. Habit.'},
            {'text': 'reads the Courier shipping news before the front page',
             'bio': 'Shipping news first, then the rest of the paper.'},
            {'text': 'keeps a lamp lit in the window on foggy nights', 'bio': 'There is always a lamp in my window when '
             'the fog comes in.'},
            {'text': 'taps the barometer every time they pass a chandlery window',
             'bio': 'I tap every barometer I pass. Old skipper habit, and I never was a skipper.'},
            {'text': 'knows every family plot in the Old Hill Burying Ground', 'bio': 'Ask me about anyone in the Old Hill Burying Ground.'},
        ],
        'goals': [
            {'id': 'pellmouth-dory', 'text': 'build a dory of their own over the winter', 'steps': 6,
             'practice': ['workshop', 'evening'],
             'progress': '{name} got another strake fastened on the dory in the shed',
             'done': '{name} launched the new dory off the town landing, with half the street watching',
             'interest': 'boatbuilding', 'bio': 'Building a dory in my shed, one plank at a time.'},
            {'id': 'pellmouth-family-papers', 'text': "trace their family back through the town's old records",
             'steps': 5, 'practice': ['library', 'afternoon'],
             'progress': '{name} found another great-grandparent in the Athenaeum ledgers',
             'done': '{name} traced the family back to the first settlers, and stopped there',
             'interest': 'family history', 'bio': 'Digging through the town records for my family.'},
            {'id': 'pellmouth-chowder', 'text': 'win the chowder supper at the West Parish Grange', 'steps': 4,
             'practice': ['market', 'morning'],
             'progress': '{name} tried another batch of chowder on the neighbours',
             'done': '{name} took first prize for chowder, and will not share the secret',
             'interest': 'cooking', 'bio': 'Working on a chowder that will win the Grange supper.'},
            {'id': 'pellmouth-mooring', 'text': 'save for a mooring and a boat in the harbour', 'steps': 6,
             'practice': None, 'progress': '{name} put another week of pay towards a mooring',
             'done': '{name} has a boat on a mooring of their own at last',
             'interest': 'boats', 'bio': 'Saving for a mooring in the harbour.'},
            {'id': 'pellmouth-boston-job', 'text': 'get a place in Boston and off the North Shore', 'steps': 7,
             'practice': None, 'progress': '{name} wrote off to another Boston firm about a position',
             'done': '{name} got an offer in Boston, and has not yet said whether they will go',
             'interest': 'getting ahead', 'bio': 'Looking for a job in Boston. Maybe.'},
        ],
    },
    'names': {
        'mix': {'anglo': 6, 'irish': 2, 'french-canadian': 1.5, 'italian': 1, 'portuguese': 0.8, 'slavic': 0.6,
                'german': 0.5, 'jewish': 0.3, 'black-american': 0.15},
        'groups': {
            # The shared banks have no Portuguese group; these are names common among Azorean and mainland
            # Portuguese families in Massachusetts fishing towns around 1926.
            'portuguese': {
                'feminine': ['Maria', 'Rosa', 'Conceição', 'Mary', 'Isabel', 'Amélia', 'Adelaide', 'Emília',
                             'Olívia', 'Glória', 'Laura', 'Clara', 'Lucinda', 'Alice', 'Hilda', 'Irene', 'Delfina',
                             'Ermelinda', 'Natália', 'Beatriz'],
                'masculine': ['Manuel', 'José', 'António', 'João', 'Francisco', 'Joaquim', 'Frank', 'Joseph',
                              'Anthony', 'John', 'Augusto', 'Alfredo', 'Domingos', 'Jacinto', 'Mateus', 'Luís',
                              'Henrique', 'Fernando', 'Ernesto', 'Albino'],
                'family': ['Silva', 'Souza', 'Medeiros', 'Furtado', 'Pereira', 'Costa', 'Mello', 'Rapoza', 'Amaral',
                           'Avila', 'Rego', 'Cabral', 'Sylvia', 'Lopes', 'Tavares', 'Pacheco', 'Correia', 'Duarte',
                           'Bettencourt', 'Machado', 'Gaspar', 'Mendonça', 'Raposo', 'Fernandes', 'Teixeira'],
            },
        },
        'year': 1926,
    },
    'water': [
        {'kind': 'sea', 'name': 'Massachusetts Bay', 'side': 'east', 'width_km': 2},
        {'kind': 'river', 'name': 'Pell River', 'width_km': 0.12, 'points': [
            [42.727, -70.878], [42.722, -70.857], [42.718, -70.840], [42.718, -70.830], [42.715, -70.815],
            [42.709, -70.806], [42.705, -70.795], [42.702, -70.780]]},
    ],
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
