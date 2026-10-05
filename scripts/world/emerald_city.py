"""Curated Emerald City of Oz data. Run `python scripts/world/emerald_city.py` to rewrite the shipped JSON.

Draws only on L. Frank Baum's Oz books (public domain in the US), never on the 1939 MGM film or later
adaptations. Oz has no money (The Road to Oz, The Emerald City of Oz), so rents are None and every place
is free; career `pay` is a uniform '$$' because everyone is looked after equally.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'cities' / 'emerald-city.json'
S = 'curated-2026-10'
ERA = 'fantasy'


def hood(id, name, summary, vibe, lat, lon, tier, housing, walk, transit):
    return {'id': id, 'name': name, 'summary': summary, 'vibe': vibe, 'lat': lat, 'lon': lon, 'rent_tier': tier,
            'rent': None, 'housing': housing, 'walkability': walk, 'transit': transit, 'source': S}


def place(id, name, kind, hood, summary, tags, setting, good_for, day_parts, seasons=(), cuisine=''):
    return {'id': id, 'name': name, 'kind': kind, 'neighborhood': hood, 'summary': summary, 'tags': tags,
            'cost': 'free', 'setting': setting, 'good_for': good_for, 'day_parts': day_parts,
            'seasons': list(seasons), 'cuisine': cuisine, 'source': S}


def career(id, name, sector, schedule, summary, themes):
    return {'id': id, 'name': name, 'sector': sector, 'schedule': schedule, 'pay': '$$', 'summary': summary,
            'themes': themes, 'eras': [ERA]}


def employer(id, name, sector, hood, size, summary, careers):
    return {'id': id, 'name': name, 'sector': sector, 'neighborhood': hood, 'size': size, 'summary': summary,
            'careers': careers, 'source': S}


def event(id, name, months, hood, summary):
    return {'id': id, 'name': name, 'months': months, 'neighborhood': hood, 'summary': summary, 'source': S}


ALL = ['solo', 'friends', 'date', 'family']
ADULT = ['solo', 'friends', 'date']
DAY = ['morning', 'afternoon']
DAYLONG = ['morning', 'afternoon', 'evening']
NIGHT = ['evening', 'late']
WARM = ['spring', 'summer', 'fall']

CITY = {
    'schema_version': 1, 'id': 'emerald-city', 'name': 'The Emerald City', 'setting': 'fictional', 'era': ERA,
    'basis': 'Drawn only from L. Frank Baum\'s Oz books (The Wonderful Wizard of Oz, 1900, and its sequels through '
             'the 1920s), which are public domain in the US. Nothing from the 1939 MGM film or later adaptations. '
             'Everyday districts, shops and taverns are invented in Baum\'s spirit and marked as such.',
    'region': 'Land of Oz', 'country': 'Oz', 'timezone': 'America/Chicago',
    'aliases': ['Emerald City', 'City of Emeralds', 'Emerald City of Oz'],
    'summary': 'The green capital at the centre of Oz, where the yellow brick road ends: green marble streets set '
               'with emeralds, Ozma\'s palace, and (as Baum counts it) 9,654 buildings and 57,318 people who work '
               'half the time and play half the time, with no money at all.',
    'lat': 38.5, 'lon': -98.0,
    'currency': {'code': 'none', 'symbol': '', 'name': 'no money (Oz has none)'},
    'rent_period': 'month',
    'speeds': {'walk': 4.5, 'carriage': 9},
    'sources': {
        S: {'kind': 'curated', 'title': 'The Emerald City of Oz written for Prospero Companion',
            'license': 'CC0-1.0', 'retrieved': '2026-10-05',
            'note': 'Canon details (the green spectacles locked on at the gates in the first book, the Guardian of '
                    'the Gates, the palace, Ozma\'s rule, the tiny Royal Army, the Wizard as a humbug, the four '
                    'countries, the yellow brick road, and the rule of no money with half work and half play from '
                    'The Road to Oz and The Emerald City of Oz) come from Baum\'s public-domain books only. In the '
                    'first book a girl buys green lemonade with green pennies; this file follows the later books, '
                    'where Oz has no money. Districts, shops, taverns, schools, festivals and coordinates are '
                    'invented for fiction and placed on a fixed anchor in central Kansas. Climate is invented: '
                    'Baum gives Oz gentle, pleasant weather.'},
    },
    'neighborhoods': [
        hood('palace-grounds', 'Palace Grounds', 'The Royal Palace at the centre of the city, with its gardens, '
             'fountains and servants\' quarters; Ozma rules from here.', ['royal', 'gardens', 'central', 'grand'],
             38.500, -98.000, 'very-high', ['palace-quarters', 'garden-cottage'], 'high', ['green-streets']),
        hood('gate-quarter', 'Gate Quarter', 'The streets just inside the great gate, where the Guardian of the '
             'Gates keeps the gatehouse and visitors from the yellow brick road first walk in.',
             ['gateway', 'busy', 'visitors'], 38.500, -97.982, 'high', ['green-marble-house', 'flat-above-shop'],
             'high', ['green-streets', 'market-wagons']),
        hood('market-square', 'Market Square', 'An everyday city district around a broad square where wagons from '
             'all four countries unload fruit, grain and cloth.', ['market', 'food', 'central', 'busy'], 38.494,
             -97.992, 'mid', ['flat-above-shop', 'green-marble-house'], 'high', ['green-streets', 'market-wagons']),
        hood('cutters-row', 'Cutters\' Row', 'An everyday city district of long workshops where emerald cutters '
             'and goldsmiths shape the stones that are set into the city\'s walls and pavements.',
             ['craft', 'workshops', 'quiet'], 38.507, -97.991, 'mid', ['rowhouse', 'flat-above-shop'], 'high',
             ['green-streets']),
        hood('oven-street', 'Oven Street', 'An everyday city district of bakehouses, dairies and kitchens that '
             'smells of bread before sunrise.', ['food', 'early-risers', 'neighbourly'], 38.489, -98.004, 'mid',
             ['rowhouse', 'flat-above-shop'], 'high', ['green-streets']),
        hood('needle-hill', 'Needle Hill', 'An everyday city district of tailors, dyers and weavers on a low rise, '
             'with green cloth drying on lines between the houses.', ['craft', 'textiles', 'hilly'], 38.511,
             -98.010, 'mid', ['rowhouse', 'green-marble-house'], 'medium', ['green-streets']),
        hood('bookbinders-close', 'Bookbinders\' Close', 'An everyday city district of small streets around the '
             'public reading room, the schoolhouse and a few binderies.', ['quiet', 'bookish', 'leafy'], 38.496,
             -98.013, 'high', ['green-marble-house', 'rowhouse'], 'high', ['green-streets']),
        hood('pump-square', 'Pump Square', 'An everyday city district of houses around an old green-tiled pump, '
             'with a bathhouse, a bandstand and children everywhere.', ['family', 'neighbourly', 'residential'],
             38.485, -97.990, 'mid', ['green-marble-house', 'rowhouse'], 'high', ['green-streets']),
        hood('winkie-street', 'Winkie Street', 'An everyday city district on the west side where tinsmiths and '
             'metalworkers from the yellow Winkie Country have set up shop.', ['craft', 'metalwork', 'winkie'],
             38.502, -98.025, 'low', ['rowhouse', 'flat-above-shop'], 'medium', ['green-streets', 'market-wagons']),
        hood('quadling-lane', 'Quadling Lane', 'An everyday city district on the south side where families from the '
             'red Quadling Country live in houses with red shutters among the green.', ['quadling', 'family',
             'residential'], 38.477, -98.003, 'low', ['cottage', 'rowhouse'], 'medium',
             ['green-streets', 'market-wagons']),
        hood('gillikin-gardens', 'Gillikin Gardens', 'An everyday district on the north edge with allotments and '
             'purple-trimmed cottages built by families from the Gillikin Country.', ['gardens', 'gillikin',
             'quiet', 'family'], 38.523, -98.002, 'low', ['cottage', 'garden-cottage'], 'low',
             ['green-streets', 'market-wagons']),
        hood('barracks-corner', 'Barracks Corner', 'A few streets beside the Royal Army\'s barracks, which are much '
             'too big for an army that has always had more officers than privates.', ['quiet', 'military',
             'residential'], 38.505, -97.998, 'mid', ['rowhouse', 'green-marble-house'], 'high', ['green-streets']),
        hood('yellow-brick-road', 'Yellow Brick Road farms', 'Farmland outside the east gate along the yellow brick '
             'road, where blue Munchkin Country begins to give way to green fields and orchards.',
             ['rural', 'farms', 'munchkin', 'roadside'], 38.503, -97.945, 'low', ['farmhouse', 'cottage'], 'low',
             ['market-wagons']),
    ],
    'transit': [
        {'id': 'green-streets', 'name': 'The green marble streets', 'kind': 'walk', 'summary': 'Nearly everyone '
         'walks: the city is compact and its paved streets run straight from the palace to the gates.', 'source': S},
        {'id': 'market-wagons', 'name': 'Farm and market wagons', 'kind': 'carriage', 'summary': 'Slow wagons '
         'bringing produce in along the yellow brick road and the other country roads give anyone a lift for '
         'nothing.', 'source': S},
    ],
    'places': [
        # Canon landmarks.
        place('royal-palace', 'The Royal Palace', 'landmark', 'palace-grounds', 'Ozma\'s palace of green marble '
              'and emeralds, with long halls open to the people on audience days.', ['royal', 'iconic', 'canon'],
              'mixed', ALL, DAY),
        place('throne-room', 'The Throne Room', 'attraction', 'palace-grounds', 'The domed room with the green '
              'marble throne where the Wizard once fooled visitors with a great head and a ball of fire, and where '
              'Ozma now hears requests.', ['royal', 'history', 'canon'], 'indoor', ALL, DAY),
        place('royal-gardens', 'The Royal Gardens', 'garden', 'palace-grounds', 'The palace gardens of flowers, '
              'fountains and fruit trees, open for anyone to walk in.', ['gardens', 'fountains', 'canon'],
              'outdoor', ALL, DAYLONG, WARM),
        place('great-gate', 'The great gate', 'landmark', 'gate-quarter', 'The tall gate studded with emeralds '
              'where the yellow brick road ends and the Guardian of the Gates greets travellers.',
              ['gate', 'iconic', 'canon'], 'outdoor', ALL, DAY),
        place('gatehouse-spectacles', 'The Guardian\'s gatehouse', 'attraction', 'gate-quarter', 'The small room '
              'in the city wall full of green spectacles in boxes, where visitors in the old days had a pair locked '
              'on before entering.', ['history', 'spectacles', 'canon'], 'indoor', ALL, DAY),
        place('yellow-brick-road-walk', 'The yellow brick road', 'trail', 'yellow-brick-road', 'The road of '
              'yellow brick running east from the gate between fences and fields, good for a long walk out of the '
              'city.', ['walk', 'road', 'canon'], 'outdoor', ALL, DAY, WARM),
        place('balloon-yard', 'The balloon yard', 'landmark', 'palace-grounds', 'The open yard before the palace '
              'where the Wizard once cast off in his silk balloon and left without Dorothy.',
              ['history', 'humbug', 'canon'], 'outdoor', ALL, DAY),
        place('royal-army-parade-ground', 'The Royal Army parade ground', 'square', 'barracks-corner', 'A gravel '
              'square where the city\'s tiny army drills, which rarely takes long.', ['army', 'canon', 'square'],
              'outdoor', ALL, ['morning'], WARM),
        # Invented everyday places.
        place('market-square-stalls', 'Market Square stalls', 'market', 'market-square', 'Everyday city market of '
              'covered stalls where farmers from the four countries hand out apples, cheese, cabbages and bolts of '
              'cloth to anyone who needs them.', ['market', 'produce', 'everyday'], 'outdoor', ALL, DAY,
              cuisine='produce'),
        place('green-pump-bathhouse', 'Pump Square bathhouse', 'fitness', 'pump-square', 'Everyday city bathhouse '
              'with a warm green-tiled pool, a cold plunge and benches for gossip.', ['bath', 'swimming', 'everyday'],
              'indoor', ['solo', 'friends', 'family'], DAYLONG),
        place('public-reading-room', 'Public Reading Room', 'library', 'bookbinders-close', 'Everyday city library: '
              'one long room of shelves and green-shaded lamps where anyone may borrow books.',
              ['books', 'quiet', 'everyday'], 'indoor', ['solo', 'friends', 'family'], DAYLONG),
        place('half-moon-tavern', 'The Half Moon', 'tavern', 'gate-quarter', 'Everyday city tavern by the gate where '
              'travellers off the yellow brick road eat stew and hear the news.', ['tavern', 'travellers',
              'everyday'], 'indoor', ADULT, NIGHT, cuisine='stew and bread'),
        place('wayfarers-rest', 'The Wayfarers\' Rest', 'inn', 'gate-quarter', 'Everyday city inn with a dozen '
              'rooms, a long table and a landlady who knows every road in Oz.', ['inn', 'travellers', 'everyday'],
              'indoor', ALL, ['evening'], cuisine='roast dinners'),
        place('pump-square-bandstand', 'Pump Square bandstand', 'venue', 'pump-square', 'Everyday city bandstand '
              'where neighbourhood players give concerts on summer evenings.', ['music', 'outdoor', 'everyday'],
              'outdoor', ALL, ['evening'], ['summer']),
        place('oven-street-bakehouse', 'Hobbs\'s Bakehouse', 'cafe', 'oven-street', 'Everyday city bakery with '
              'benches outside, known for cream buns and warm rye in the early morning.', ['bakery', 'breakfast',
              'everyday'], 'mixed', ALL, ['morning'], cuisine='bakery'),
        place('dairy-kitchen', 'The Dairy Kitchen', 'restaurant', 'oven-street', 'Everyday city eating house that '
              'serves custards, cheese pies and buttermilk at shared tables.', ['lunch', 'dairy', 'everyday'],
              'indoor', ALL, ['afternoon'], cuisine='dairy and pies'),
        place('green-lemonade-stand', 'The lemonade stand on Market Square', 'cafe', 'market-square', 'Everyday '
              'city stand selling green lemonade and green popcorn, as in the first book, though now for nothing.',
              ['snacks', 'lemonade', 'everyday'], 'outdoor', ALL, DAY, WARM, cuisine='lemonade and popcorn'),
        place('cutters-arms', 'The Cutters\' Arms', 'tavern', 'cutters-row', 'Everyday city tavern where emerald '
              'cutters meet after work over cider and a game of draughts.', ['tavern', 'games', 'everyday'],
              'indoor', ADULT, NIGHT, cuisine='cider and pies'),
        place('cutters-row-workshops', 'Cutters\' Row workshops', 'workshop', 'cutters-row', 'Everyday city '
              'workshops with open doors where anyone may watch emeralds being split and polished.',
              ['craft', 'emeralds', 'everyday'], 'indoor', ALL, DAY),
        place('needle-hill-cloth-hall', 'Needle Hill cloth hall', 'shopping', 'needle-hill', 'Everyday city hall '
              'where tailors fit new clothes and hand them out, mostly in a dozen shades of green.',
              ['clothes', 'tailors', 'everyday'], 'indoor', ALL, DAY),
        place('dye-yard', 'The Needle Hill dye yard', 'workshop', 'needle-hill', 'Everyday city dye yard of vats and '
              'drying lines, where cloth turns green and visitors usually leave with green fingers.',
              ['craft', 'dye', 'everyday'], 'outdoor', ALL, DAY, WARM),
        place('bramble-tearoom', 'Bramble\'s Tearoom', 'cafe', 'bookbinders-close', 'Everyday city tearoom with '
              'six tables, raspberry tarts and a cat on the windowsill.', ['tea', 'quiet', 'everyday'], 'indoor',
              ADULT, ['afternoon'], cuisine='tea and cakes'),
        place('bookbinders-close-green', 'The Close green', 'park', 'bookbinders-close', 'Everyday city green with '
              'elm trees and benches where people read in the afternoon.', ['park', 'reading', 'everyday'],
              'outdoor', ALL, DAY, WARM),
        place('pump-square-green', 'Pump Square', 'square', 'pump-square', 'Everyday city square around the old '
              'green-tiled pump, with hopscotch chalked on the marble.', ['square', 'children', 'everyday'],
              'outdoor', ALL, DAYLONG),
        place('tin-lantern', 'The Tin Lantern', 'tavern', 'winkie-street', 'Everyday city tavern run by a Winkie '
              'family, with yellow walls, tin mugs and fiddle music on most nights.', ['tavern', 'music',
              'winkie', 'everyday'], 'indoor', ADULT, NIGHT, cuisine='Winkie country cooking'),
        place('winkie-street-tinsmiths', 'Winkie Street tinsmiths', 'workshop', 'winkie-street', 'Everyday city '
              'workshops where Winkie tinsmiths make pails, lanterns and oil cans.', ['craft', 'tin', 'everyday'],
              'indoor', ALL, DAY),
        place('quadling-kitchen', 'Mother Pell\'s kitchen', 'restaurant', 'quadling-lane', 'Everyday city eating '
              'house with red tablecloths, serving Quadling Country dumplings and plum pudding.', ['dinner',
              'quadling', 'everyday'], 'indoor', ALL, ['evening'], cuisine='Quadling country cooking'),
        place('quadling-lane-orchard', 'Quadling Lane orchard', 'park', 'quadling-lane', 'Everyday city orchard of '
              'cherry and pear trees where anyone may pick fruit in season.', ['orchard', 'fruit', 'everyday'],
              'outdoor', ALL, DAY, WARM),
        place('gillikin-allotments', 'Gillikin Gardens allotments', 'garden', 'gillikin-gardens', 'Everyday city '
              'allotments of vegetable beds and sweet peas, with a shed of shared tools.', ['gardening',
              'vegetables', 'everyday'], 'outdoor', ALL, DAY, WARM),
        place('purple-plum', 'The Purple Plum', 'tavern', 'gillikin-gardens', 'Everyday city tavern with a purple '
              'door, plum wine and a skittle alley out back.', ['tavern', 'skittles', 'gillikin', 'everyday'],
              'mixed', ADULT, NIGHT, cuisine='plum wine and cold meats'),
        place('barracks-mess', 'The Barracks Mess', 'restaurant', 'barracks-corner', 'Everyday city canteen beside '
              'the barracks, open to everyone, serving porridge and fried eggs to soldiers and neighbours.',
              ['breakfast', 'canteen', 'everyday'], 'indoor', ALL, ['morning'], cuisine='breakfast'),
        place('gate-quarter-stables', 'Gate Quarter wagon yard', 'square', 'gate-quarter', 'Everyday city yard '
              'where market wagons unhitch and drivers trade news from the four countries.', ['wagons', 'news',
              'everyday'], 'outdoor', ADULT, DAY),
        place('east-road-orchards', 'East Road orchards', 'park', 'yellow-brick-road', 'Everyday orchards along '
              'the yellow brick road, with apple trees and a cider press in the fall.', ['orchard', 'country',
              'everyday'], 'outdoor', ALL, DAY, WARM),
        place('roadside-farm-kitchen', 'The Crossroads farm kitchen', 'inn', 'yellow-brick-road', 'Everyday farm '
              'kitchen where a Munchkin family feeds travellers at a blue-painted table.', ['farm', 'munchkin',
              'everyday'], 'indoor', ALL, ['afternoon', 'evening'], cuisine='Munchkin farm cooking'),
        place('palace-music-hall', 'The palace music hall', 'venue', 'palace-grounds', 'Hall in the palace where '
              'concerts and dances are held on feast nights, open to all who come.', ['music', 'dancing',
              'royal'], 'indoor', ALL, ['evening']),
        place('city-wall-walk', 'The wall walk', 'trail', 'gillikin-gardens', 'Everyday path along the top of the '
              'green city wall with views over all four countries on a clear day.', ['walk', 'views', 'everyday'],
              'outdoor', ALL, DAYLONG, WARM),
        place('ball-field', 'Pump Square ball field', 'fitness', 'pump-square', 'Everyday city field for rounders, '
              'races and tug-of-war on play days.', ['games', 'sport', 'everyday'], 'outdoor', ALL, DAY, WARM),
        place('glass-house', 'The Glass House', 'workshop', 'cutters-row', 'Everyday city glassworks where green '
              'window glass is blown and anyone can watch from the doorway.', ['craft', 'glass', 'everyday'],
              'indoor', ALL, DAY),
        place('market-square-puppets', 'The Market Square puppet booth', 'venue', 'market-square', 'Everyday city '
              'puppet booth giving afternoon shows about Oz history, including the Wizard\'s humbug.',
              ['puppets', 'children', 'everyday'], 'outdoor', ['family', 'friends'], ['afternoon'], WARM),
        place('cobblers-yard', 'Cobblers\' Yard', 'shopping', 'oven-street', 'Everyday city yard of cobblers\' '
              'benches where shoes are made and mended while you wait.', ['shoes', 'craft', 'everyday'], 'mixed',
              ALL, DAY),
        place('history-room', 'The Oz history room', 'museum', 'bookbinders-close', 'Everyday city museum of maps of '
              'the four countries, old green spectacles and a model of the yellow brick road.', ['history', 'maps',
              'rainy-day', 'everyday'], 'indoor', ALL, DAY),
        # More everyday places, one neighbourhood at a time.
        place('palace-kitchen-door', 'The palace kitchen door', 'restaurant', 'palace-grounds', 'Everyday city '
              'kitchen door behind the palace where the cooks hand out bowls of soup and warm rolls at noon.',
              ['lunch', 'soup', 'everyday'], 'mixed', ALL, ['afternoon'], cuisine='soup and bread'),
        place('fountain-court', 'The fountain court', 'square', 'palace-grounds', 'Everyday city courtyard by the '
              'palace laundry, with a fountain and stone benches where servants and neighbours eat their lunch.',
              ['fountain', 'benches', 'everyday'], 'outdoor', ALL, DAY, WARM),
        place('wheelwrights-yard', 'The wheelwright\'s yard', 'workshop', 'gate-quarter', 'Everyday city yard just '
              'inside the gate where wagon wheels and axles cracked on the country roads are mended.',
              ['craft', 'wagons', 'everyday'], 'mixed', ALL, DAY),
        place('gate-quarter-washhouse', 'The travellers\' washhouse', 'fitness', 'gate-quarter', 'Everyday city '
              'washhouse with hot tubs and clean towels for travellers who arrive dusty from the road.',
              ['bath', 'travellers', 'everyday'], 'indoor', ['solo', 'friends', 'family'], DAYLONG),
        place('apple-cart', 'The Apple Cart', 'tavern', 'market-square', 'Everyday city tavern on the corner of '
              'Market Square where wagon drivers drink cider and eat cold pork before the long ride home.',
              ['tavern', 'cider', 'everyday'], 'indoor', ADULT, ['afternoon', 'evening'], cuisine='cider and pork'),
        place('weighing-house', 'The weighing house', 'landmark', 'market-square', 'Everyday city hall with a '
              'great beam scale, where farmers weigh their loads and a clerk writes down what each country sent.',
              ['market', 'scales', 'everyday'], 'indoor', ALL, ['morning']),
        place('polishers-table', 'The Polishers\' Table', 'restaurant', 'cutters-row', 'Everyday city cookshop where '
              'cutters and goldsmiths eat mutton pies and pea soup at one long table at midday.',
              ['lunch', 'pies', 'everyday'], 'indoor', ALL, ['afternoon'], cuisine='pies and soup'),
        place('cutters-green', 'Cutters\' green', 'square', 'cutters-row', 'Everyday city patch of grass with a '
              'drinking fountain at the end of the row, where apprentices play marbles at noon.',
              ['square', 'marbles', 'everyday'], 'outdoor', ALL, DAY, WARM),
        place('oven-street-dairy', 'The Oven Street dairy', 'market', 'oven-street', 'Everyday city dairy where '
              'milk, butter and soft cheese are handed out from the counter at first light.',
              ['milk', 'cheese', 'everyday'], 'indoor', ALL, ['morning'], cuisine='dairy'),
        place('flour-loft', 'The flour loft', 'workshop', 'oven-street', 'Everyday city loft where flour from the '
              'country mills is sifted and sacked for the bakehouses, and children slide on the empty sacks.',
              ['flour', 'craft', 'everyday'], 'indoor', ALL, ['morning']),
        place('the-thimble', 'The Thimble', 'tavern', 'needle-hill', 'Everyday city tavern of tailors and dyers, '
              'small and warm, with green ale and a long argument about cloth every night.',
              ['tavern', 'tailors', 'everyday'], 'indoor', ADULT, NIGHT, cuisine='ale and toasted cheese'),
        place('needle-hill-tea-garden', 'Needle Hill tea garden', 'cafe', 'needle-hill', 'Everyday city tea garden '
              'on the top of the rise, with a view over the drying lines and lemon cake on a tray.',
              ['tea', 'views', 'everyday'], 'outdoor', ALL, ['afternoon'], WARM, cuisine='tea and cakes'),
        place('needle-hill-laundry', 'The Needle Hill laundry', 'workshop', 'needle-hill', 'Everyday city laundry '
              'of coppers and mangles where neighbours wash on Mondays and the steam fogs the windows.',
              ['laundry', 'neighbours', 'everyday'], 'indoor', ['solo', 'family'], ['morning']),
        place('close-bindery', 'The Close bindery', 'workshop', 'bookbinders-close', 'Everyday city bindery with '
              'its door propped open, where worn library books are restitched and anyone may learn to sew a '
              'notebook.', ['books', 'craft', 'everyday'], 'indoor', ALL, DAY),
        place('pump-square-pie-shop', 'Mrs Gubbin\'s pie shop', 'restaurant', 'pump-square', 'Everyday city pie '
              'shop on the corner of the square, with pork pies, apple turnovers and a queue of children after '
              'school.', ['pies', 'children', 'everyday'], 'indoor', ALL, ['afternoon', 'evening'], cuisine='pies'),
        place('toy-mender', 'The toy mender', 'workshop', 'pump-square', 'Everyday city workshop where an old '
              'carpenter glues dolls, restrings tops and repaints wooden soldiers for the square\'s children.',
              ['toys', 'children', 'everyday'], 'indoor', ['family', 'solo'], DAY),
        place('yellow-kettle', 'The Yellow Kettle', 'cafe', 'winkie-street', 'Everyday city breakfast room run by '
              'Winkie tinsmiths\' wives, with porridge, fried bread and tea in tin mugs.',
              ['breakfast', 'winkie', 'everyday'], 'indoor', ALL, ['morning'], cuisine='breakfast'),
        place('winkie-street-stalls', 'Winkie Street stalls', 'market', 'winkie-street', 'Everyday city street '
              'market where Winkie farmers hand out yellow apples, honey and buttercup cheese from their carts.',
              ['market', 'winkie', 'everyday'], 'outdoor', ALL, DAY, WARM, cuisine='produce'),
        place('winkie-street-baths', 'Winkie Street baths', 'fitness', 'winkie-street', 'Everyday city bathhouse '
              'with a big tin tub heated from the forge next door, much used by tinsmiths at the end of the day.',
              ['bath', 'tinsmiths', 'everyday'], 'indoor', ['solo', 'friends'], ['afternoon', 'evening']),
        place('red-shutter', 'The Red Shutter', 'tavern', 'quadling-lane', 'Everyday city tavern run by a Quadling '
              'family, red-painted inside, with cherry cordial for children and stronger drink for the rest.',
              ['tavern', 'quadling', 'everyday'], 'indoor', ALL, NIGHT, cuisine='Quadling country cooking'),
        place('quadling-dance-yard', 'The Quadling dance yard', 'venue', 'quadling-lane', 'Everyday city yard '
              'strung with red lanterns where families dance the Quadling reels on play-day evenings.',
              ['dancing', 'music', 'quadling', 'everyday'], 'outdoor', ALL, ['evening'], WARM),
        place('quadling-lane-wash-green', 'Quadling Lane wash green', 'square', 'quadling-lane', 'Everyday city '
              'green where washing is laid out to bleach, with a pump at one end and children at the other.',
              ['washing', 'children', 'everyday'], 'outdoor', ALL, DAY, WARM),
        place('gillikin-seed-shed', 'The seed shed', 'market', 'gillikin-gardens', 'Everyday city shed where '
              'allotment keepers swap seeds, cuttings and spare onions, with the swaps chalked on a board.',
              ['gardening', 'seeds', 'everyday'], 'indoor', ALL, DAY, WARM),
        place('gillikin-oatcake-oven', 'The Gillikin oatcake oven', 'cafe', 'gillikin-gardens', 'Everyday city '
              'bakehouse with a purple door where Gillikin oatcakes and plum buns come out hot every morning.',
              ['bakery', 'gillikin', 'everyday'], 'indoor', ALL, ['morning'], cuisine='bakery'),
        place('brass-button', 'The Brass Button', 'tavern', 'barracks-corner', 'Everyday city tavern by the '
              'barracks where officers outnumber privates at the bar, as they do on the parade ground.',
              ['tavern', 'army', 'everyday'], 'indoor', ADULT, NIGHT, cuisine='ale and sausages'),
        place('officers-reading-room', 'The officers\' reading room', 'library', 'barracks-corner', 'Everyday '
              'city reading room in a wing of the barracks nobody needs, now open to the whole neighbourhood.',
              ['books', 'quiet', 'everyday'], 'indoor', ['solo', 'friends', 'family'], DAYLONG),
        place('barracks-plunge', 'The barracks plunge', 'fitness', 'barracks-corner', 'Everyday city cold plunge '
              'pool built for an army that never filled it, where the neighbours swim on hot afternoons.',
              ['swimming', 'cold', 'everyday'], 'indoor', ['solo', 'friends', 'family'], DAY, ['summer']),
        place('halfway-well', 'The halfway well', 'square', 'yellow-brick-road', 'Everyday roadside well with a '
              'bench and a tin cup on a chain, where walkers on the yellow brick road stop to drink.',
              ['well', 'road', 'everyday'], 'outdoor', ALL, DAY),
        place('cider-barn', 'The cider barn', 'workshop', 'yellow-brick-road', 'Everyday farm barn with a cider '
              'press where neighbours bring apples in the fall and leave with a jug.',
              ['cider', 'farm', 'everyday'], 'mixed', ALL, DAY, ['fall'], cuisine='cider'),
    ],
    'colleges': [
        {'id': 'little-schoolhouse', 'name': 'The Pump Square schoolhouse', 'type': 'academy',
         'neighborhood': 'pump-square', 'size': 'small', 'known_for': ['reading', 'sums', 'geography-of-oz'],
         'source': S},
        {'id': 'cutters-guild-school', 'name': 'The Emerald Cutters\' school', 'type': 'guild-school',
         'neighborhood': 'cutters-row', 'size': 'small', 'known_for': ['gem-cutting', 'goldsmithing',
         'glasswork'], 'source': S},
        {'id': 'gardeners-school', 'name': 'The Royal Gardens school', 'type': 'guild-school',
         'neighborhood': 'palace-grounds', 'size': 'small', 'known_for': ['gardening', 'orchards', 'beekeeping'],
         'source': S},
        {'id': 'city-music-academy', 'name': 'The City Music Academy', 'type': 'music-school',
         'neighborhood': 'bookbinders-close', 'size': 'small', 'known_for': ['fiddle', 'brass-band', 'singing'],
         'source': S},
    ],
    'careers': [
        career('gardener', 'Gardener', 'gardens', 'early', 'Tends beds, fountains and fruit trees in the royal '
               'gardens or the city orchards.', ['seasons', 'growing things', 'early starts', 'outdoors']),
        career('palace-cook', 'Palace cook', 'palace', 'shift-day', 'Cooks in the palace kitchens for the court, '
               'its guests and the many feasts.', ['kitchen heat', 'feasts', 'teamwork']),
        career('palace-steward', 'Palace steward', 'palace', 'rotating', 'Keeps the palace halls, guest rooms and '
               'linen in order and looks after visitors.', ['hospitality', 'visitors', 'royal routines']),
        career('emerald-cutter', 'Emerald cutter', 'crafts', 'office', 'Splits and polishes emeralds for the city\'s '
               'walls, pavements and jewellery.', ['patience', 'precision', 'craft pride']),
        career('goldsmith', 'Goldsmith', 'crafts', 'office', 'Sets emeralds in gold for doors, lamps and brooches.',
               ['craft', 'fine work', 'apprentices']),
        career('baker', 'Baker', 'food', 'early', 'Bakes the city\'s bread, buns and pies before dawn.',
               ['early mornings', 'warm ovens', 'regulars']),
        career('tavern-keeper', 'Tavern keeper', 'food', 'evening', 'Runs a tavern or inn, keeps the fire and '
               'feeds whoever comes in.', ['company', 'stories', 'late nights']),
        career('tailor', 'Tailor', 'textiles', 'office', 'Cuts and sews the green clothes nearly everyone in the '
               'city wears.', ['fittings', 'fashion', 'handwork']),
        career('dyer', 'Dyer', 'textiles', 'shift-day', 'Works the vats that turn cloth a dozen shades of green.',
               ['stained hands', 'colour', 'outdoor work']),
        career('royal-army-soldier', 'Soldier of the Royal Army', 'army', 'flexible', 'Serves in the famously tiny '
               'Royal Army of Oz, mostly parading and standing guard.', ['ceremony', 'uniforms', 'easy duty']),
        career('gate-warden', 'Gate warden', 'gates', 'rotating', 'Helps the Guardian of the Gates welcome '
               'travellers and look after the boxes of green spectacles.', ['visitors', 'news', 'tradition']),
        career('librarian', 'Librarian', 'learning', 'office', 'Keeps the public reading room and finds books for '
               'readers of every age.', ['books', 'quiet', 'questions']),
        career('schoolteacher', 'Schoolteacher', 'learning', 'academic', 'Teaches the city\'s children reading, '
               'sums and the geography of the four countries.', ['children', 'patience', 'lessons']),
        career('musician', 'Musician', 'music', 'evening', 'Plays at palace feasts, the bandstand and the taverns.',
               ['performing', 'practice', 'evenings out']),
        career('tinsmith', 'Tinsmith', 'crafts', 'office', 'Makes and mends tin pails, lanterns and oil cans, a '
               'trade the Winkies are known for.', ['metalwork', 'repairs', 'Winkie pride']),
        career('cobbler', 'Cobbler', 'crafts', 'office', 'Makes and mends shoes and boots.', ['handwork',
               'regulars', 'leather']),
        career('glazier', 'Glazier', 'crafts', 'shift-day', 'Blows and fits the green glass in the city\'s '
               'windows.', ['heat', 'fragile work', 'craft']),
        career('street-keeper', 'Street keeper', 'city-works', 'early', 'Sweeps and polishes the green marble '
               'streets and resets loose emeralds.', ['early starts', 'neighbourhood', 'outdoors']),
        career('carpenter', 'Carpenter', 'city-works', 'shift-day', 'Builds and repairs houses, wagons and '
               'market stalls.', ['building', 'tools', 'teamwork']),
        career('road-mender', 'Road mender', 'city-works', 'shift-day', 'Relays broken yellow bricks and fills the '
               'holes in the road outside the gate.', ['outdoors', 'travellers', 'hard work']),
        career('healer', 'Healer', 'care', 'rotating', 'Looks after the sick and the injured at the city\'s '
               'house of healing.', ['caring', 'herbs', 'night calls']),
        career('farmer', 'Farmer', 'farming', 'early', 'Grows grain, fruit and vegetables on the farms along the '
               'yellow brick road and brings them to market.', ['seasons', 'harvest', 'animals']),
        career('market-keeper', 'Market keeper', 'food', 'early', 'Sets out stalls on Market Square and shares '
               'produce out fairly.', ['people', 'produce', 'early starts']),
    ],
    'employers': [
        employer('royal-palace-household', 'The Royal Palace household', 'palace', 'palace-grounds', 'large',
                 'The staff who run Ozma\'s palace: kitchens, halls, guest rooms and feasts.',
                 ['palace-cook', 'palace-steward', 'musician']),
        employer('royal-gardens-staff', 'The Royal Gardens', 'gardens', 'palace-grounds', 'medium', 'Gardeners '
                 'who keep the palace gardens and the city\'s orchards and greens.', ['gardener']),
        employer('royal-army', 'The Royal Army of Oz', 'army', 'barracks-corner', 'small', 'The city\'s tiny army, '
                 'which has always had more officers than privates.', ['royal-army-soldier']),
        employer('gatehouse', 'The Gatehouse of the Emerald City', 'gates', 'gate-quarter', 'small', 'The staff of '
                 'the great gate who greet travellers and keep the green spectacles.', ['gate-warden']),
        employer('cutters-row-shops', 'The Cutters\' Row workshops', 'crafts', 'cutters-row', 'medium', 'Everyday '
                 'city workshops where emeralds are cut and set in gold.', ['emerald-cutter', 'goldsmith']),
        employer('glass-house-works', 'The Glass House', 'crafts', 'cutters-row', 'small', 'Everyday city '
                 'glassworks making green window glass.', ['glazier']),
        employer('oven-street-bakehouses', 'The Oven Street bakehouses', 'food', 'oven-street', 'medium',
                 'Everyday city bakehouses that bake for the whole city.', ['baker']),
        employer('market-square-keepers', 'The Market Square keepers', 'food', 'market-square', 'small',
                 'Everyday city stallholders who unload the wagons and share out the produce.', ['market-keeper']),
        employer('city-taverns', 'The Half Moon and the Wayfarers\' Rest', 'food', 'gate-quarter', 'small',
                 'Everyday city tavern and inn by the gate.', ['tavern-keeper', 'musician']),
        employer('needle-hill-cloth', 'The Needle Hill cloth hall', 'textiles', 'needle-hill', 'medium', 'Everyday '
                 'city tailors and dyers who clothe the city.', ['tailor', 'dyer']),
        employer('reading-room', 'The Public Reading Room', 'learning', 'bookbinders-close', 'small', 'Everyday '
                 'city library open to everyone.', ['librarian']),
        employer('schoolhouse', 'The Pump Square schoolhouse', 'learning', 'pump-square', 'small', 'Everyday city '
                 'school for children of the city.', ['schoolteacher']),
        employer('winkie-tinsmiths', 'The Winkie Street tinsmiths', 'crafts', 'winkie-street', 'small', 'Everyday '
                 'city tinsmiths\' and cobblers\' workshops on the west side.', ['tinsmith', 'cobbler']),
        employer('street-keepers-lodge', 'The Street Keepers\' Lodge', 'city-works', 'market-square', 'medium',
                 'Everyday city crew that sweeps the streets, mends houses and keeps up the roads.',
                 ['street-keeper', 'carpenter', 'road-mender']),
        employer('house-of-healing', 'The house of healing', 'care', 'quadling-lane', 'small', 'Everyday city house '
                 'where the sick and injured are looked after; in Oz few people ever die, but they still catch '
                 'colds and break arms.', ['healer']),
        employer('east-road-farms', 'The East Road farms', 'farming', 'yellow-brick-road', 'medium', 'Everyday '
                 'farms along the yellow brick road that feed the city.', ['farmer']),
    ],
    'career_hubs': [
        {'id': 'palace-hub', 'name': 'The palace and its gardens', 'neighborhoods': ['palace-grounds',
         'barracks-corner'], 'sectors': ['palace', 'gardens', 'army', 'music'], 'summary': 'The palace, its '
         'gardens and the barracks employ more people than anywhere else in the city.', 'source': S},
        {'id': 'workshop-streets', 'name': 'The workshop streets', 'neighborhoods': ['cutters-row', 'needle-hill',
         'winkie-street'], 'sectors': ['crafts', 'textiles'], 'summary': 'Emerald cutters, goldsmiths, tailors, '
         'dyers and tinsmiths work in long open workshops.', 'source': S},
        {'id': 'market-and-ovens', 'name': 'Market and ovens', 'neighborhoods': ['market-square', 'oven-street',
         'gate-quarter'], 'sectors': ['food', 'city-works', 'gates'], 'summary': 'Bakers, stallholders, tavern '
         'keepers and street crews keep the city fed and clean.', 'source': S},
        {'id': 'town-and-country', 'name': 'Town edge and country', 'neighborhoods': ['yellow-brick-road',
         'gillikin-gardens', 'quadling-lane', 'pump-square', 'bookbinders-close'], 'sectors': ['farming', 'care',
         'learning'], 'summary': 'Schools, the reading room, the house of healing and the farms beyond the gate.',
         'source': S},
    ],
    'climate': {
        'summary': 'Mild and pleasant all year, as Baum describes Oz: warm summers, soft rain, short cool winters '
                   'with hardly any snow. Values are invented for fiction.',
        'months': [
            {'high_f': 52, 'low_f': 34, 'rain_days': 5, 'note': 'Coolest month; crisp mornings, rare light snow.'},
            {'high_f': 55, 'low_f': 36, 'rain_days': 5, 'note': 'Cool and bright.'},
            {'high_f': 62, 'low_f': 42, 'rain_days': 7, 'note': 'First blossoms in the orchards.'},
            {'high_f': 68, 'low_f': 48, 'rain_days': 8, 'note': 'Soft spring showers.'},
            {'high_f': 74, 'low_f': 54, 'rain_days': 8, 'note': 'Gardens in full flower.'},
            {'high_f': 79, 'low_f': 59, 'rain_days': 6, 'note': 'Long warm days.'},
            {'high_f': 82, 'low_f': 62, 'rain_days': 5, 'note': 'Warmest month; evenings outdoors.'},
            {'high_f': 81, 'low_f': 61, 'rain_days': 5, 'note': 'Warm; the first fruit harvest.'},
            {'high_f': 76, 'low_f': 56, 'rain_days': 5, 'note': 'Golden and calm.'},
            {'high_f': 69, 'low_f': 48, 'rain_days': 5, 'note': 'Apple pressing; cool nights.'},
            {'high_f': 60, 'low_f': 41, 'rain_days': 5, 'note': 'Leaves turn; fires lit in the taverns.'},
            {'high_f': 54, 'low_f': 36, 'rain_days': 5, 'note': 'Short cool days.'},
        ],
        'source': S,
    },
    'annual_events': [
        event('ozma-birthday', 'Ozma\'s birthday', [8], 'palace-grounds', 'A great party at the palace with guests '
              'from all over Oz, as in The Road to Oz; the month here is invented.'),
        event('army-review', 'Review of the Royal Army', [5], 'barracks-corner', 'The whole Royal Army parades '
              'across its square, which takes a few minutes, and everyone cheers.'),
        event('spring-planting', 'Spring planting days', [3, 4], 'gillikin-gardens', 'Everyone turns out to dig '
              'and sow the allotments, orchards and palace beds.'),
        event('four-countries-fair', 'Four Countries fair', [9], 'market-square', 'Wagons from the Munchkin, '
              'Winkie, Quadling and Gillikin countries fill Market Square with harvest goods in their own colours.'),
        event('road-mending', 'Road-mending week', [4], 'yellow-brick-road', 'Volunteers walk out along the yellow '
              'brick road to relay broken bricks and fill the holes.'),
        event('apple-pressing', 'Apple pressing', [10], 'yellow-brick-road', 'Cider presses run in the East Road '
              'orchards and city people walk out to help.'),
        event('cutters-open-day', 'Cutters\' open day', [6], 'cutters-row', 'Workshops on Cutters\' Row open fully '
              'and apprentices show their first polished stones.'),
        event('bandstand-summer', 'Bandstand evenings', [6, 7, 8], 'pump-square', 'Neighbourhood bands play Pump '
              'Square on warm evenings.'),
        event('midwinter-dance', 'Midwinter dance', [12], 'palace-grounds', 'A night of music and dancing in the '
              'palace hall for anyone who comes.'),
        event('spectacle-day', 'Spectacle day', [11], 'gate-quarter', 'Children borrow green spectacles from the '
              'gatehouse for a day to see the city the way visitors once did.'),
    ],
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
