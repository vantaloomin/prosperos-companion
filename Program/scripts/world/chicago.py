"""Curated Chicago data. Run `python scripts/world/chicago.py` to rewrite the shipped JSON."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'cities' / 'chicago.json'
S = 'curated-2026-10'
CLIMATE = 'curated-climate-2026-10'


def hood(id, name, summary, vibe, lat, lon, tier, rent, housing, walk, transit):
    studio, one, two = rent
    return {'id': id, 'name': name, 'summary': summary, 'vibe': vibe, 'lat': lat, 'lon': lon, 'rent_tier': tier,
            'rent': {'studio': studio, 'one_bedroom': one, 'two_bedroom': two}, 'housing': housing,
            'walkability': walk, 'transit': transit, 'source': S}


def place(id, name, kind, hood, summary, tags, cost, setting, good_for, day_parts, seasons=(), cuisine=''):
    return {'id': id, 'name': name, 'kind': kind, 'neighborhood': hood, 'summary': summary, 'tags': tags,
            'cost': cost, 'setting': setting, 'good_for': good_for, 'day_parts': day_parts,
            'seasons': list(seasons), 'cuisine': cuisine, 'source': S}


def line(id, name, kind, summary):
    return {'id': id, 'name': name, 'kind': kind, 'summary': summary, 'source': S}


def college(id, name, type, hood, size, known_for):
    return {'id': id, 'name': name, 'type': type, 'neighborhood': hood, 'size': size, 'known_for': known_for,
            'source': S}


def employer(id, name, sector, hood, size, summary, careers):
    return {'id': id, 'name': name, 'sector': sector, 'neighborhood': hood, 'size': size, 'summary': summary,
            'careers': careers, 'source': S}


def hub(id, name, hoods, sectors, summary):
    return {'id': id, 'name': name, 'neighborhoods': hoods, 'sectors': sectors, 'summary': summary, 'source': S}


def event(id, name, months, hood, summary):
    return {'id': id, 'name': name, 'months': months, 'neighborhood': hood, 'summary': summary, 'source': S}


def month(high, low, rain, note):
    return {'high_f': high, 'low_f': low, 'rain_days': rain, 'note': note}


def color(id, name, kind, summary, places=(), seasons=()):
    return {'id': id, 'name': name, 'kind': kind, 'summary': summary, 'places': list(places),
            'seasons': list(seasons), 'source': S}


def price(id, item, low, high, per=''):
    return {'id': id, 'item': item, 'low': low, 'high': high, 'per': per, 'source': S}


ALL = ['solo', 'friends', 'date', 'family']
ADULT = ['solo', 'friends', 'date']
DAY = ['morning', 'afternoon']
DAYLONG = ['morning', 'afternoon', 'evening']
LUNCH = ['afternoon', 'evening']
DINNER = ['evening']
NIGHT = ['evening', 'late']
WARM = ['spring', 'summer', 'fall']
SUMMER = ['summer']
BEACH = ['spring', 'summer']
NORTH_L = ['red', 'brown', 'purple', 'cta-bus', 'divvy']

CITY = {
    'schema_version': 1, 'id': 'chicago', 'name': 'Chicago', 'region': 'Illinois', 'country': 'US',
    'timezone': 'America/Chicago',
    'aliases': ['Chi-Town', 'Chitown', 'The Windy City', 'Chicago, IL', 'Chicagoland', 'City of Big Shoulders'],
    'summary': 'The big city of the Midwest on Lake Michigan: a skyline of landmark architecture along the river, '
               'free lakefront beaches, the elevated L, blues and improv, deep-dish and Italian beef, and '
               'neighborhoods with fierce loyalties from Rogers Park to the South Side.',
    'lat': 41.88, 'lon': -87.63,
    'speeds': {'walk': 4.5, 'car': 24, 'rideshare': 24, 'bus': 12, 'subway': 28, 'commuter-rail': 50,
               'water-taxi': 12, 'bike-share': 14},
    # Rough heritage weights for residents' names (estimates, not census figures). Polish and Ukrainian Chicago
    # are drawn from the slavic group, Puerto Rican and Mexican Chicago from hispanic.
    'names': {'mix': {'hispanic': 2.9, 'black-american': 2.8, 'anglo': 2.3, 'slavic': 0.9, 'irish': 0.8,
                       'italian': 0.6, 'east-asian': 0.6, 'south-asian': 0.5, 'jewish': 0.4, 'arabic': 0.3,
                       'west-african': 0.2, 'caribbean': 0.1}},
    'sources': {
        S: {'kind': 'curated', 'title': 'Chicago places and neighborhoods written for Prospero Companion',
            'license': 'CC0-1.0', 'retrieved': '2026-10-10',
            'note': 'Well-known public places, institutions and employers from general knowledge. Businesses open '
                    'and close and rents move: treat this as a snapshot for fiction. Rents are rounded estimates '
                    'of typical asking ranges, not listings. Coordinates are approximate neighborhood centers.'},
        CLIMATE: {'kind': 'curated', 'title': 'Approximate monthly climate for Chicago (O\'Hare and Midway)',
                  'license': 'CC0-1.0', 'retrieved': '2026-10-10',
                  'note': 'Rounded values in line with NOAA 1991-2020 normals; refresh with scripts/world when '
                          'network access to NOAA is available.'},
    },
    'neighborhoods': [
        hood('the-loop', 'The Loop', 'The downtown ringed by the elevated tracks: trading floors on LaSalle, the '
             'theater district on State and Randolph, Millennium Park and the Art Institute on Michigan Avenue.',
             ['business', 'central', 'architecture', 'cultural'], 41.881, -87.629, 'high',
             ([1500, 2000], [1900, 2700], [2700, 3900]), ['apartment-tower', 'converted-office', 'condo'], 'high',
             ['red', 'blue', 'brown', 'green', 'orange', 'pink', 'metra', 'cta-bus']),
        hood('river-north', 'River North', 'Galleries turned into steakhouses, clubs and glassy rental towers north '
             'of the river, with the Merchandise Mart and the tourist deep-dish rooms.',
             ['nightlife', 'young-professional', 'dining', 'central'], 41.892, -87.633, 'very-high',
             ([1600, 2100], [2000, 2900], [2900, 4300]), ['apartment-tower', 'loft', 'condo'], 'high',
             ['red', 'brown', 'purple', 'cta-bus', 'water-taxi', 'divvy']),
        hood('streeterville', 'Streeterville', 'High-rises between the Magnificent Mile and the lake, home to Navy '
             'Pier, the Northwestern hospital campus and its medical students.',
             ['upscale', 'medical', 'lakefront', 'touristy'], 41.893, -87.620, 'very-high',
             ([1600, 2100], [2000, 2800], [2800, 4200]), ['apartment-tower', 'condo'], 'high',
             ['red', 'cta-bus', 'water-taxi', 'divvy']),
        hood('gold-coast', 'Gold Coast', 'Old money mansions and doorman co-ops off Lake Shore Drive, with Oak Street '
             'boutiques and the late-night Rush and Division bar strip a block away.',
             ['affluent', 'historic', 'lakefront', 'nightlife'], 41.905, -87.628, 'very-high',
             ([1400, 1900], [1900, 2800], [2800, 4500]), ['co-op', 'brownstone', 'apartment-tower', 'condo'], 'high',
             NORTH_L),
        hood('lincoln-park', 'Lincoln Park & Old Town', 'Leafy greystones and brick two-flats around the free zoo '
             'and the big lakefront park, with DePaul students, Steppenwolf and Second City on Wells Street.',
             ['leafy', 'young-professional', 'park', 'comedy'], 41.921, -87.648, 'high',
             ([1300, 1700], [1700, 2400], [2400, 3500]), ['greystone', 'two-flat', 'condo', 'apartment'], 'high',
             NORTH_L),
        hood('lakeview', 'Lakeview & Wrigleyville', 'Vintage courtyard buildings, the ivy at Wrigley Field and '
             'its bars, and Northalsted, the city\'s historic LGBTQ+ neighborhood.',
             ['sports', 'bars', 'lgbtq-friendly', 'young-professional'], 41.943, -87.654, 'high',
             ([1200, 1600], [1500, 2100], [2100, 3000]), ['courtyard-building', 'two-flat', 'apartment', 'condo'],
             'high', NORTH_L),
        hood('wicker-park', 'Wicker Park & Bucktown', 'The six-corner crossroads of Milwaukee, North and Damen: '
             'boutiques, record shops, cocktail bars and the elevated 606 trail, once the heart of Polish Chicago.',
             ['hip', 'shopping', 'nightlife', 'arts'], 41.909, -87.677, 'high',
             ([1300, 1700], [1600, 2300], [2200, 3200]), ['two-flat', 'loft', 'apartment', 'single-family'],
             'high', ['blue', 'cta-bus', 'divvy']),
        hood('ukrainian-village', 'Ukrainian Village & West Town', 'Gold-domed churches, Ukrainian bakeries and '
             'dive bars along Chicago Avenue, with old workers\' cottages between them.',
             ['historic', 'dive-bars', 'music', 'church'], 41.899, -87.684, 'mid',
             ([1150, 1500], [1450, 1950], [1900, 2700]), ['two-flat', 'workers-cottage', 'apartment'], 'high',
             ['blue', 'cta-bus', 'divvy']),
        hood('logan-square', 'Logan Square', 'Wide boulevards and greystones around the eagle-topped Centennial '
             'Monument, with a Sunday farmers market, a strong Latino history and a young, creative crowd.',
             ['boulevards', 'hip', 'food', 'changing'], 41.923, -87.708, 'mid',
             ([1100, 1450], [1400, 1900], [1800, 2600]), ['greystone', 'two-flat', 'apartment'], 'high',
             ['blue', 'cta-bus', 'divvy']),
        hood('humboldt-park', 'Humboldt Park', 'The center of Puerto Rican Chicago: a vast park with a lagoon and '
             'boathouse, and Paseo Boricua on Division Street between two giant steel flags.',
             ['puerto-rican', 'park', 'community', 'affordable'], 41.902, -87.721, 'low',
             ([900, 1200], [1100, 1500], [1400, 2000]), ['two-flat', 'greystone', 'apartment'], 'medium',
             ['cta-bus', 'divvy']),
        hood('west-loop', 'West Loop & Fulton Market', 'Meatpacking warehouses turned into Restaurant Row, tech '
             'offices and hotels, with the United Center to the west and the commuter stations to the east.',
             ['dining', 'tech', 'new-build', 'nightlife'], 41.885, -87.650, 'very-high',
             ([1700, 2200], [2100, 3000], [3000, 4400]), ['loft', 'apartment-tower', 'condo'], 'high',
             ['blue', 'green', 'pink', 'metra', 'cta-bus', 'water-taxi', 'divvy']),
        hood('little-italy', 'Little Italy & University Village', 'Taylor Street\'s red-sauce restaurants and '
             'lemonade stands beside the UIC campus and the Illinois Medical District hospitals.',
             ['students', 'medical', 'italian', 'historic'], 41.869, -87.660, 'mid',
             ([1100, 1500], [1400, 1900], [1800, 2600]), ['apartment', 'student-housing', 'rowhouse', 'condo'],
             'high', ['blue', 'pink', 'cta-bus', 'divvy']),
        hood('pilsen', 'Pilsen', 'Mexican Chicago\'s cultural heart: murals on every viaduct, panaderias and taquerias '
             'along 18th Street and old Bohemian brick buildings full of artists\' studios.',
             ['mexican', 'arts', 'murals', 'changing'], 41.857, -87.660, 'mid',
             ([950, 1300], [1200, 1650], [1500, 2200]), ['two-flat', 'workers-cottage', 'apartment'], 'high',
             ['pink', 'cta-bus', 'divvy']),
        hood('little-village', 'Little Village', 'La Villita: 26th Street, one of the busiest Mexican shopping '
             'streets in the country, under a welcome arch, with families in brick bungalows and two-flats.',
             ['mexican', 'family', 'shopping', 'affordable'], 41.845, -87.712, 'low',
             ([850, 1100], [1000, 1350], [1300, 1800]), ['two-flat', 'bungalow', 'apartment'], 'medium',
             ['pink', 'cta-bus']),
        hood('chinatown', 'Chinatown', 'Wentworth Avenue and the newer Chinatown Square under the red gate, with dim '
             'sum, bakeries and Ping Tom park on the river.', ['chinese', 'food', 'family', 'riverside'], 41.852,
             -87.632, 'mid', ([1000, 1350], [1250, 1700], [1600, 2300]), ['apartment', 'townhouse', 'two-flat'],
             'high', ['red', 'orange', 'cta-bus', 'water-taxi', 'divvy']),
        hood('south-loop', 'South Loop & Museum Campus', 'Former rail yards turned towers and townhouses, with '
             'Printers Row, Columbia College students and the museums and Soldier Field on the lake.',
             ['museums', 'lakefront', 'students', 'new-build'], 41.862, -87.624, 'high',
             ([1400, 1850], [1700, 2400], [2400, 3500]), ['apartment-tower', 'loft', 'townhouse', 'condo'], 'high',
             ['red', 'orange', 'green', 'metra', 'south-shore', 'cta-bus', 'divvy']),
        hood('bronzeville', 'Bronzeville', 'The "Black Metropolis" of the Great Migration: greystones and mansions '
             'along King Drive, the jazz and blues history of 47th Street, and the IIT campus to the west.',
             ['historic', 'black-history', 'architecture', 'changing'], 41.823, -87.617, 'mid',
             ([950, 1300], [1150, 1600], [1500, 2200]), ['greystone', 'two-flat', 'apartment'], 'medium',
             ['green', 'red', 'metra', 'cta-bus', 'divvy']),
        hood('hyde-park', 'Hyde Park', 'The University of Chicago\'s gothic quads, bookstores and co-op flats '
             'between Washington Park and the lake, a famously integrated, intellectual corner of the South Side.',
             ['academic', 'students', 'lakefront', 'bookish'], 41.795, -87.594, 'mid',
             ([1050, 1400], [1300, 1800], [1800, 2600]), ['apartment', 'courtyard-building', 'co-op',
             'student-housing'], 'high', ['metra', 'south-shore', 'cta-bus', 'divvy']),
        hood('bridgeport', 'Bridgeport', 'Old Irish South Side, home of five mayors and the White Sox, now mixed '
             'with Chinese and Mexican families, art spaces and corner taverns.',
             ['working-class', 'sports', 'historic', 'taverns'], 41.838, -87.647, 'low',
             ([900, 1200], [1100, 1500], [1400, 2000]), ['workers-cottage', 'two-flat', 'bungalow'], 'medium',
             ['red', 'orange', 'cta-bus', 'divvy']),
        hood('andersonville', 'Andersonville', 'The old Swedish strip of Clark Street: independent shops, Belgian beer, '
             'a large LGBTQ+ community and a water tower painted with the Swedish flag.',
             ['independent-shops', 'lgbtq-friendly', 'swedish', 'neighbourly'], 41.980, -87.668, 'mid',
             ([1100, 1450], [1350, 1850], [1800, 2600]), ['courtyard-building', 'two-flat', 'apartment'], 'high',
             ['red', 'cta-bus', 'divvy']),
        hood('uptown', 'Uptown', 'Grand old theaters and ballrooms, the Green Mill, Vietnamese Argyle Street and '
             'Montrose Beach, in one of the most mixed neighborhoods in the city.',
             ['music', 'diverse', 'historic', 'lakefront'], 41.966, -87.655, 'mid',
             ([1000, 1350], [1250, 1700], [1650, 2400]), ['courtyard-building', 'apartment', 'condo'], 'high',
             ['red', 'cta-bus', 'divvy']),
        hood('rogers-park', 'Rogers Park & West Ridge', 'The far North Side by the lake: Loyola\'s campus, small '
             'beaches at the end of nearly every street, and Devon Avenue\'s South Asian shops to the west.',
             ['diverse', 'lakefront', 'students', 'affordable'], 42.005, -87.672, 'low',
             ([900, 1200], [1100, 1500], [1400, 2000]), ['courtyard-building', 'apartment', 'two-flat'], 'medium',
             ['red', 'purple', 'metra', 'cta-bus', 'divvy']),
        hood('evanston', 'Evanston', 'The first suburb north on the lake: Northwestern University, a walkable '
             'downtown, big old houses and fenced beaches that charge a summer token.',
             ['suburban', 'college-town', 'lakefront', 'leafy'], 42.045, -87.688, 'mid',
             ([1150, 1500], [1450, 1950], [1900, 2800]), ['apartment', 'single-family', 'condo'], 'medium',
             ['purple', 'metra', 'cta-bus', 'pace', 'divvy']),
        hood('oak-park', 'Oak Park', 'The village just west of the city line, with the world\'s largest collection '
             'of Frank Lloyd Wright buildings, Hemingway\'s birthplace and tree-lined family streets.',
             ['suburban', 'architecture', 'family', 'leafy'], 41.885, -87.785, 'mid',
             ([1050, 1400], [1300, 1800], [1700, 2500]), ['single-family', 'apartment', 'condo'], 'medium',
             ['green', 'blue', 'metra', 'pace']),
    ],
    'transit': [
        # The L lines come first so a trip both ends of which share an L line takes it.
        line('red', 'CTA Red Line', 'subway', 'The busiest L line, 24 hours a day, from Howard through the State '
             'Street subway to 95th Street, stopping at Wrigley Field and the White Sox park.'),
        line('blue', 'CTA Blue Line', 'subway', 'A 24-hour line from O\'Hare Airport through Logan Square, Wicker '
             'Park and the Dearborn subway to the Loop and on west to Forest Park.'),
        line('brown', 'CTA Brown Line', 'subway', 'Elevated line from Kimball through Ravenswood, Lakeview and Old '
             'Town around the Loop, the classic rattling ride past back porches.'),
        line('green', 'CTA Green Line', 'subway', 'From Oak Park and the West Side over Lake Street through the '
             'Loop and south through Bronzeville.'),
        line('orange', 'CTA Orange Line', 'subway', 'From Midway Airport past Bridgeport and Chinatown to the Loop.'),
        line('pink', 'CTA Pink Line', 'subway', 'From Cicero through Little Village and Pilsen to the Loop.'),
        line('purple', 'CTA Purple Line', 'subway', 'From Linden in Wilmette through Evanston to Howard, with '
             'rush-hour express trains running on to the Loop.'),
        line('metra', 'Metra', 'commuter-rail', 'Commuter rail from Union Station, Ogilvie, LaSalle Street and '
             'Millennium Station to the suburbs, including the Electric line to Hyde Park.'),
        line('south-shore', 'South Shore Line', 'commuter-rail', 'The interurban from Millennium Station through '
             'Hyde Park to Gary and South Bend in Indiana.'),
        line('cta-bus', 'CTA buses', 'bus', 'A grid of bus routes on nearly every major street, including the '
             'lakefront express buses along Lake Shore Drive.'),
        line('pace', 'Pace suburban buses', 'bus', 'Buses across the suburbs, including Evanston and Oak Park.'),
        line('water-taxi', 'Chicago Water Taxi and Shoreline water taxis', 'water-taxi', 'River boats between '
             'the commuter stations, Michigan Avenue and Chinatown, and lake taxis between Navy Pier and the '
             'Museum Campus in summer.'),
        line('divvy', 'Divvy', 'bike-share', 'Blue bikes and e-bikes docked across the city and Evanston.'),
    ],
    'places': [
        # The Loop
        place('art-institute', 'Art Institute of Chicago', 'museum', 'the-loop', 'One of the great art museums, '
              'guarded by two bronze lions: Seurat\'s "La Grande Jatte", "Nighthawks", "American Gothic" and the '
              'Thorne miniature rooms.', ['art', 'iconic', 'rainy-day'], '$$$', 'indoor', ALL, DAY),
        place('millennium-park', 'Millennium Park', 'park', 'the-loop', 'Cloud Gate (the Bean), the Crown Fountain '
              'faces that spit water at children, gardens and free summer concerts at the Pritzker Pavilion.',
              ['iconic', 'free', 'sculpture', 'concerts'], 'free', 'outdoor', ALL, DAYLONG),
        place('maggie-daley-park', 'Maggie Daley Park', 'park', 'the-loop', 'Playgrounds and climbing walls in '
              'summer and a looping ice-skating ribbon in winter, just east of Millennium Park.',
              ['skating', 'kids', 'climbing'], 'free', 'outdoor', ['family', 'friends', 'date'], DAYLONG),
        place('buckingham-fountain', 'Buckingham Fountain', 'landmark', 'the-loop', 'The great tiered fountain in '
              'Grant Park, with water shows on the hour and a lit display after dark in the warm months.',
              ['fountain', 'grant-park', 'iconic'], 'free', 'outdoor', ALL, DAYLONG, WARM),
        place('chicago-riverwalk', 'Chicago Riverwalk', 'landmark', 'the-loop', 'A promenade along the main branch '
              'of the river under the bridges, with wine bars, kayak rentals and tour boats.',
              ['waterfront', 'walk', 'drinks'], 'free', 'outdoor', ALL, DAYLONG, WARM),
        place('architecture-river-cruise', 'Architecture river cruise', 'attraction', 'the-loop', 'A ninety-minute '
              'boat tour down the river with a guide naming every tower, from the Wrigley Building to Willis Tower.',
              ['architecture', 'boat', 'iconic'], '$$$', 'outdoor', ALL, DAYLONG, WARM),
        place('willis-tower-skydeck', 'Skydeck at Willis Tower', 'attraction', 'the-loop', 'Glass boxes on the '
              '103rd floor of the tower everyone still calls the Sears Tower.', ['views', 'iconic', 'touristy'],
              '$$$', 'indoor', ['family', 'friends', 'date'], DAYLONG),
        place('chicago-cultural-center', 'Chicago Cultural Center', 'museum', 'the-loop', 'The old public library, '
              'free to enter, with the world\'s largest Tiffany glass dome, exhibitions and lunchtime concerts.',
              ['free', 'architecture', 'rainy-day'], 'free', 'indoor', ALL, DAY),
        place('chicago-theatre', 'Chicago Theatre', 'venue', 'the-loop', 'The 1921 movie palace under the famous '
              'red CHICAGO marquee on State Street, now for comedians and concerts.', ['theater', 'iconic',
              'concerts'], '$$$', 'indoor', ['date', 'friends'], DINNER),
        place('symphony-center', 'Symphony Center', 'venue', 'the-loop', 'Home of the Chicago Symphony Orchestra on '
              'Michigan Avenue across from the Art Institute.', ['classical', 'music'], '$$$', 'indoor',
              ['date', 'solo', 'friends'], DINNER),
        place('goodman-theatre', 'Goodman Theatre', 'venue', 'the-loop', 'The city\'s oldest nonprofit theater, in the '
              'Randolph Street theater district, with a "Christmas Carol" every December.', ['theater'], '$$$',
              'indoor', ['date', 'friends', 'family'], DINNER),
        place('harold-washington-library', 'Harold Washington Library Center', 'library', 'the-loop', 'The huge '
              'central public library with owls on the roof, a winter garden on the ninth floor and free music '
              'studios.', ['books', 'free', 'quiet'], 'free', 'indoor', ['solo', 'family'], DAY),
        place('the-berghoff', 'The Berghoff', 'restaurant', 'the-loop', 'German restaurant on Adams Street since '
              '1898, with its own root beer, schnitzel and a standing bar.', ['historic', 'german', 'beer'], '$$',
              'indoor', ALL, LUNCH, cuisine='german'),
        place('intelligentsia-millennium', 'Intelligentsia Coffee (Randolph Street)', 'cafe', 'the-loop', 'The '
              'Chicago roaster\'s downtown bar by Millennium Park, full of office workers before nine.',
              ['coffee', 'commuters'], '$', 'indoor', ['solo', 'friends', 'coworkers'], DAY),
        # River North
        place('pizzeria-uno', 'Pizzeria Uno', 'restaurant', 'river-north', 'The 1943 basement room where deep-dish '
              'began, at Ohio and Wabash; expect a wait and a forty-minute bake.', ['deep-dish', 'historic',
              'pizza'], '$$', 'indoor', ALL, LUNCH, cuisine='pizza'),
        place('lou-malnatis-river-north', 'Lou Malnati\'s (River North)', 'restaurant', 'river-north', 'The local '
              'favourite for deep-dish with a buttery crust and a sausage patty that covers the whole pie.',
              ['deep-dish', 'pizza'], '$$', 'indoor', ALL, LUNCH, cuisine='pizza'),
        place('portillos-river-north', 'Portillo\'s (River North)', 'restaurant', 'river-north', 'Big, loud, '
              'fast hot dogs, Italian beef and chocolate cake shakes in a Prohibition-themed hall.',
              ['hot-dogs', 'italian-beef', 'cheap'], '$', 'indoor', ALL, ['afternoon', 'evening', 'late'],
              cuisine='chicago-street-food'),
        place('mr-beef', 'Mr. Beef on Orleans', 'restaurant', 'river-north', 'A no-frills Italian beef counter, '
              'decades older than the TV show it inspired.', ['italian-beef', 'cheap', 'counter'], '$', 'indoor',
              ['solo', 'friends', 'coworkers'], DAY, cuisine='chicago-street-food'),
        place('frontera-grill', 'Frontera Grill', 'restaurant', 'river-north', 'Rick Bayless\'s regional Mexican '
              'restaurant on Clark Street, with moles and margaritas.', ['mexican', 'celebrated'], '$$$', 'indoor',
              ['date', 'friends'], DINNER, cuisine='mexican'),
        place('gene-georgetti', 'Gene & Georgetti', 'restaurant', 'river-north', 'Old-school steakhouse in a frame '
              'house under the L since 1941, with tuxedoed waiters.', ['steak', 'historic', 'special-occasion'],
              '$$$$', 'indoor', ['date', 'coworkers', 'family'], DINNER, cuisine='steakhouse'),
        place('andys-jazz-club', 'Andy\'s Jazz Club', 'nightlife', 'river-north', 'Long-running jazz room on Hubbard '
              'Street with two sets a night and a supper menu.', ['jazz', 'live-music'], '$$', 'indoor', ADULT,
              NIGHT),
        place('east-bank-club', 'East Bank Club', 'fitness', 'river-north', 'A huge riverside athletic club with '
              'pools, courts and a well-known members\' scene.', ['gym', 'pool', 'upscale'], '$$$', 'indoor',
              ['solo', 'friends'], ['morning', 'afternoon', 'evening']),
        place('art-on-the-mart', 'Art on the Mart', 'attraction', 'river-north', 'Projected digital art across the '
              'river face of the Merchandise Mart after dark, best watched from the Riverwalk.', ['art', 'free',
              'night'], 'free', 'outdoor', ALL, ['evening'], WARM),
        # Streeterville
        place('navy-pier', 'Navy Pier', 'attraction', 'streeterville', 'A long pier into the lake with the '
              'Centennial Wheel, boat tours, a children\'s museum and summer fireworks.', ['iconic', 'touristy',
              'lake', 'kids'], '$$', 'mixed', ALL, DAYLONG),
        place('mca-chicago', 'Museum of Contemporary Art', 'museum', 'streeterville', 'Contemporary art museum off '
              'Michigan Avenue, with a summer farmers market on its plaza.', ['art', 'rainy-day'], '$$', 'indoor',
              ADULT, DAY),
        place('360-chicago', '360 Chicago', 'attraction', 'streeterville', 'The observation deck on the 94th floor '
              'of the former John Hancock Center, with the tilting TILT windows.', ['views', 'iconic'], '$$$',
              'indoor', ['date', 'friends', 'family'], DAYLONG),
        place('ohio-street-beach', 'Ohio Street Beach', 'beach', 'streeterville', 'A small sheltered beach by Navy '
              'Pier where open-water swimmers train along the buoy line.', ['swimming', 'lake'], 'free', 'outdoor',
              ['solo', 'friends'], DAY, SUMMER),
        place('chicago-shakespeare', 'Chicago Shakespeare Theater', 'venue', 'streeterville', 'Thrust-stage theater '
              'at Navy Pier doing Shakespeare and musicals.', ['theater'], '$$$', 'indoor', ['date', 'family',
              'friends'], LUNCH),
        place('water-tower', 'Water Tower and Magnificent Mile', 'shopping', 'streeterville', 'The castle-like 1869 '
              'Water Tower that survived the Great Fire, and the flagship stores of North Michigan Avenue around it.',
              ['shopping', 'historic', 'touristy'], '$$$', 'mixed', ALL, DAY),
        place('billy-goat-tavern', 'Billy Goat Tavern', 'bar', 'streeterville', 'Underground grill-and-bar on lower '
              'Michigan Avenue, of the "cheezborger, cheezborger" sketch and the Cubs curse.', ['historic', 'dive',
              'burgers'], '$', 'indoor', ['solo', 'friends', 'coworkers'], ['afternoon', 'evening', 'late'],
              cuisine='american'),
        place('starbucks-reserve-roastery', 'Starbucks Reserve Roastery', 'cafe', 'streeterville', 'Five floors of '
              'roasting machines, bars and tourists on the Magnificent Mile.', ['coffee', 'touristy'], '$$',
              'indoor', ALL, DAY),
        # Gold Coast
        place('oak-street-beach', 'Oak Street Beach', 'beach', 'gold-coast', 'Sand right under the high-rises where '
              'Lake Shore Drive bends, busy and glamorous on hot weekends.', ['swimming', 'lake', 'people-watching'],
              'free', 'outdoor', ADULT, DAY, SUMMER),
        place('gibsons', 'Gibsons Bar & Steakhouse', 'restaurant', 'gold-coast', 'Rush Street steakhouse with huge '
              'martinis, slabs of cake and a well-dressed crowd.', ['steak', 'see-and-be-seen'], '$$$$', 'indoor',
              ['date', 'coworkers', 'friends'], DINNER, cuisine='steakhouse'),
        place('rush-and-division', 'Rush and Division', 'nightlife', 'gold-coast', 'The "Viagra Triangle" strip of '
              'bars and clubs where Rush meets Division and Elm, loud until late.', ['clubs', 'party', 'bars'],
              '$$$', 'indoor', ['friends'], NIGHT),
        place('original-pancake-house', 'The Original Pancake House (Bellevue)', 'restaurant', 'gold-coast',
              'Weekend lines for the oven-baked apple pancake and the Dutch baby.', ['brunch', 'line'], '$$',
              'indoor', ALL, DAY, cuisine='american-breakfast'),
        place('surgical-science-museum', 'International Museum of Surgical Science', 'museum', 'gold-coast',
              'Odd, absorbing medical history in a lakefront mansion: trepanned skulls, iron lungs and amputation '
              'kits.', ['quirky', 'history', 'rainy-day'], '$$', 'indoor', ADULT, DAY),
        place('newberry-library', 'Newberry Library', 'library', 'gold-coast', 'Independent research library facing '
              'Washington Square, the old "Bughouse Square" of soapbox speakers.', ['books', 'history', 'quiet'],
              'free', 'indoor', ['solo'], DAY),
        place('giordanos-rush', 'Giordano\'s (Rush Street)', 'restaurant', 'gold-coast', 'Stuffed pizza with a '
              'top crust and a cheese pull for the photos.', ['deep-dish', 'pizza'], '$$', 'indoor', ALL, LUNCH,
              cuisine='pizza'),
        # Lincoln Park & Old Town
        place('lincoln-park-zoo', 'Lincoln Park Zoo', 'attraction', 'lincoln-park', 'A free zoo in the park since '
              '1868, with gorillas, lions and ZooLights in winter.', ['animals', 'free', 'kids'], 'free', 'mixed',
              ALL, DAY),
        place('lincoln-park-conservatory', 'Lincoln Park Conservatory', 'park', 'lincoln-park', 'Victorian glass '
              'houses of palms, ferns and orchids, warm and green in January.', ['plants', 'free', 'winter-escape'],
              'free', 'indoor', ALL, DAY),
        place('north-avenue-beach', 'North Avenue Beach', 'beach', 'lincoln-park', 'The big volleyball beach with a '
              'boat-shaped beach house and the skyline view south.', ['volleyball', 'swimming', 'views'], 'free',
              'outdoor', ['friends', 'date', 'family'], DAY, SUMMER),
        place('lakefront-trail', 'Lakefront Trail', 'trail', 'lincoln-park', 'Eighteen miles of separated paths for '
              'runners and cyclists along the lake from Ardmore to 71st Street.', ['running', 'cycling', 'lake'],
              'free', 'outdoor', ALL, DAYLONG, WARM),
        place('second-city', 'The Second City', 'venue', 'lincoln-park', 'The improv and sketch theater on Wells '
              'Street that trained generations of comedians, with a free improv set after the late show.',
              ['comedy', 'improv', 'iconic'], '$$', 'indoor', ['friends', 'date'], NIGHT),
        place('steppenwolf', 'Steppenwolf Theatre', 'venue', 'lincoln-park', 'Ensemble theater on Halsted Street '
              'known for intense, actor-driven productions.', ['theater'], '$$$', 'indoor', ['date', 'friends',
              'solo'], DINNER),
        place('kingston-mines', 'Kingston Mines', 'nightlife', 'lincoln-park', 'Two stages of blues alternating all '
              'night on Halsted Street, open until four on weekends.', ['blues', 'live-music', 'late'], '$$',
              'indoor', ['friends', 'date'], NIGHT),
        place('chicago-history-museum', 'Chicago History Museum', 'museum', 'lincoln-park', 'The city\'s story '
              'from the Great Fire to the Cubs, with the first L car and a Chicago-style hot dog "sensory" exhibit.',
              ['history', 'rainy-day'], '$$', 'indoor', ALL, DAY),
        place('wieners-circle', 'The Wiener\'s Circle', 'restaurant', 'lincoln-park', 'Late-night char-dogs on '
              'Clark Street, where customers and staff trade insults across the counter at 2 a.m.',
              ['hot-dogs', 'late-night', 'cheap'], '$', 'indoor', ['friends'], ['evening', 'late'],
              cuisine='chicago-street-food'),
        place('old-town-ale-house', 'Old Town Ale House', 'bar', 'lincoln-park', 'A beloved dive across from Second '
              'City, its walls hung with the owner\'s satirical paintings.', ['dive', 'historic'], '$', 'indoor',
              ADULT, NIGHT),
        place('alinea', 'Alinea', 'restaurant', 'lincoln-park', 'Grant Achatz\'s tasting-menu restaurant, theatrical '
              'and very expensive, on Halsted Street.', ['tasting-menu', 'special-occasion'], '$$$$', 'indoor',
              ['date'], DINNER, cuisine='modern-american'),
        place('bourgeois-pig', 'The Bourgeois Pig Cafe', 'cafe', 'lincoln-park', 'Creaky Victorian coffeehouse on '
              'Fullerton full of DePaul students and literary-named sandwiches.', ['coffee', 'students', 'study'],
              '$', 'indoor', ['solo', 'friends', 'date'], DAYLONG),
        # Lakeview & Wrigleyville
        place('wrigley-field', 'Wrigley Field', 'stadium', 'lakeview', 'The Cubs\' 1914 ballpark with ivy on the '
              'outfield walls, a hand-turned scoreboard and rooftop bleachers across the street.',
              ['baseball', 'iconic', 'sports'], '$$$', 'outdoor', ALL, ['afternoon', 'evening'], WARM),
        place('murphys-bleachers', 'Murphy\'s Bleachers', 'bar', 'lakeview', 'The bar across from the Wrigley '
              'bleacher gate, packed before and after every game.', ['baseball', 'beer', 'crowded'], '$$', 'mixed',
              ['friends'], ['afternoon', 'evening', 'late'], cuisine='american'),
        place('ann-sather', 'Ann Sather', 'restaurant', 'lakeview', 'Swedish diner on Belmont famous for its '
              'gooey cinnamon rolls and lingonberry pancakes.', ['brunch', 'swedish', 'cinnamon-rolls'], '$',
              'indoor', ALL, DAY, cuisine='swedish'),
        place('pats-pizza', 'Pat\'s Pizza', 'restaurant', 'lakeview', 'Thin, crackly tavern-style pizza cut into '
              'squares, made on Lincoln Avenue since 1950.', ['tavern-style', 'pizza', 'family'], '$$', 'indoor',
              ALL, LUNCH, cuisine='pizza'),
        place('metro-chicago', 'Metro', 'venue', 'lakeview', 'The rock club on Clark Street where generations of '
              'bands played on their way up, with Smart Bar dance club in the basement.', ['live-music', 'rock',
              'dancing'], '$$', 'indoor', ['friends', 'date'], NIGHT),
        place('music-box-theatre', 'Music Box Theatre', 'venue', 'lakeview', '1929 movie palace on Southport with a '
              'twinkling ceiling, an organist, repertory and art films.', ['cinema', 'classic-films'], '$', 'indoor',
              ['date', 'solo', 'friends'], ['afternoon', 'evening']),
        place('sidetrack', 'Sidetrack', 'nightlife', 'lakeview', 'Huge Northalsted gay bar with video screens, '
              'show-tune nights and a rooftop.', ['lgbtq', 'show-tunes', 'party'], '$$', 'mixed', ['friends'],
              NIGHT),
        place('intelligentsia-broadway', 'Intelligentsia Coffee (Broadway)', 'cafe', 'lakeview', 'The original '
              'cafe of the Chicago roaster, on Broadway near Belmont.', ['coffee', 'laptops'], '$', 'indoor',
              ['solo', 'friends', 'date'], DAY),
        place('lakeview-ymca', 'Lakeview YMCA', 'fitness', 'lakeview', 'A neighborhood Y on Marshfield with a pool, '
              'classes and an older, friendly membership.', ['gym', 'pool', 'community'], '$', 'indoor',
              ['solo', 'family'], DAYLONG),
        # Wicker Park & Bucktown
        place('the-606', 'The 606 (Bloomingdale Trail)', 'trail', 'wicker-park', 'An old elevated rail line turned '
              'into a trail for joggers, bikes and strollers, running west to Humboldt Park.', ['running',
              'cycling', 'walk'], 'free', 'outdoor', ALL, DAYLONG),
        place('myopic-books', 'Myopic Books', 'shopping', 'wicker-park', 'Three cramped floors of used books on '
              'Milwaukee Avenue, quiet by house rule.', ['books', 'used'], '$', 'indoor', ['solo', 'date'],
              DAYLONG),
        place('big-star', 'Big Star', 'restaurant', 'wicker-park', 'Taqueria and whiskey bar in an old gas station '
              'across from the Damen Blue Line, with a crowded summer patio.', ['tacos', 'patio', 'whiskey'], '$$',
              'mixed', ['friends', 'date'], ['afternoon', 'evening', 'late'], cuisine='mexican'),
        place('violet-hour', 'The Violet Hour', 'bar', 'wicker-park', 'Speakeasy-style cocktail bar behind a '
              'mural-covered wall with no sign, with high-backed chairs and house rules.', ['cocktails',
              'speakeasy'], '$$$', 'indoor', ['date', 'friends'], NIGHT),
        place('map-room', 'The Map Room', 'bar', 'wicker-park', 'Bucktown travelers\' tavern with a deep beer list, '
              'maps and globes, and coffee in the mornings.', ['beer', 'cozy'], '$$', 'indoor', ADULT,
              ['morning', 'afternoon', 'evening', 'late']),
        place('wormhole-coffee', 'Wormhole Coffee', 'cafe', 'wicker-park', 'Milwaukee Avenue coffee shop decorated '
              'with 1980s movie props, including a DeLorean.', ['coffee', 'quirky', 'laptops'], '$', 'indoor',
              ['solo', 'friends'], DAY),
        place('midtown-athletic-club', 'Midtown Athletic Club', 'fitness', 'wicker-park', 'A large club on Elston '
              'Avenue with indoor tennis, pools and a rooftop.', ['gym', 'tennis', 'pool'], '$$$', 'mixed',
              ['solo', 'friends', 'family'], DAYLONG),
        place('subterranean', 'Subterranean', 'venue', 'wicker-park', 'A two-level club near the six corners for '
              'indie bands, hip-hop and open mics.', ['live-music', 'hip-hop'], '$$', 'indoor', ['friends'], NIGHT),
        # Ukrainian Village & West Town
        place('empty-bottle', 'Empty Bottle', 'venue', 'ukrainian-village', 'The scuffed indie and punk club on '
              'Western Avenue, with cheap beer and shows most nights.', ['live-music', 'indie', 'dive'], '$', 'indoor',
              ['friends', 'solo'], NIGHT),
        place('ukrainian-national-museum', 'Ukrainian National Museum', 'museum', 'ukrainian-village', 'Folk art, '
              'pysanky eggs and the history of the community, on Chicago Avenue.', ['history', 'folk-art'], '$',
              'indoor', ALL, DAY),
        place('st-nicholas-cathedral', 'St. Nicholas Ukrainian Catholic Cathedral', 'landmark', 'ukrainian-village',
              'A cathedral topped with thirteen copper domes for Christ and the apostles, with Byzantine mosaics '
              'inside.', ['church', 'architecture'], 'free', 'mixed', ['solo', 'family'], DAY),
        place('anns-bakery', 'Ann\'s Bakery & Deli', 'market', 'ukrainian-village', 'Ukrainian bakery and deli for '
              'poppy-seed rolls, pierogi and smoked meats to take home.', ['bakery', 'ukrainian', 'deli'], '$',
              'indoor', ALL, DAY, cuisine='ukrainian'),
        place('rainbo-club', 'Rainbo Club', 'bar', 'ukrainian-village', 'An old Division Street dive with a photo '
              'booth and a long history with local artists and musicians.', ['dive', 'photo-booth'], '$', 'indoor',
              ADULT, NIGHT),
        place('star-lounge', 'Star Lounge Coffee Bar', 'cafe', 'ukrainian-village', 'Neighborhood espresso bar on '
              'Chicago Avenue with a pressed-tin ceiling.', ['coffee', 'neighbourly'], '$', 'indoor', ['solo',
              'friends'], DAY),
        place('sportsmans-club', 'Sportsman\'s Club', 'bar', 'ukrainian-village', 'A corner tavern on Chicago Avenue '
              'with a tiki-lit back patio and a short list of cocktails.', ['patio', 'cocktails', 'tavern'], '$$',
              'mixed', ADULT, NIGHT),
        # Logan Square
        place('lula-cafe', 'Lula Cafe', 'restaurant', 'logan-square', 'The neighborhood restaurant that helped '
              'make Logan Square a food destination, seasonal and relaxed since 1999.', ['brunch', 'seasonal'], '$$',
              'indoor', ['date', 'friends', 'solo'], DAYLONG, cuisine='american'),
        place('longman-and-eagle', 'Longman & Eagle', 'restaurant', 'logan-square', 'Whiskey-heavy gastropub with '
              'rooms upstairs and a long brunch.', ['whiskey', 'brunch', 'gastropub'], '$$', 'indoor',
              ['date', 'friends'], ['morning', 'afternoon', 'evening', 'late'], cuisine='american'),
        place('logan-theatre', 'Logan Theatre', 'venue', 'logan-square', 'A restored 1915 neighborhood cinema with '
              'cheap tickets and a bar in the lobby.', ['cinema', 'cheap'], '$', 'indoor', ['date', 'friends',
              'solo'], ['afternoon', 'evening']),
        place('logan-square-farmers-market', 'Logan Square Farmers Market', 'market', 'logan-square', 'Sunday market '
              'on the boulevard with produce, tamales and live music, moving indoors in winter.', ['farmers-market',
              'sunday', 'food'], '$', 'mixed', ALL, ['morning']),
        place('centennial-monument', 'Illinois Centennial Monument', 'landmark', 'logan-square', 'The eagle-topped '
              'column at the center of the square, ringed by boulevards and greystones.', ['boulevards', 'walk'],
              'free', 'outdoor', ALL, DAYLONG),
        place('revolution-brewing', 'Revolution Brewing Brewpub', 'bar', 'logan-square', 'The local brewery\'s first '
              'pub on Milwaukee Avenue, with raised-fist tap handles and bacon-fat popcorn.', ['beer', 'brewpub'],
              '$$', 'indoor', ['friends', 'coworkers', 'date'], NIGHT, cuisine='american'),
        place('the-whistler', 'The Whistler', 'bar', 'logan-square', 'Small cocktail bar with free live jazz and '
              'experimental music most nights.', ['cocktails', 'live-music', 'jazz'], '$$', 'indoor',
              ['date', 'friends'], NIGHT),
        # Humboldt Park
        place('humboldt-park-lagoon', 'Humboldt Park', 'park', 'humboldt-park', 'A 200-acre park with a lagoon, '
              'Prairie-style boathouse, rose garden and summer barbecues blasting salsa and reggaeton.',
              ['lagoon', 'picnics', 'community'], 'free', 'outdoor', ALL, DAYLONG, WARM),
        place('humboldt-park-beach', 'Humboldt Park Beach', 'beach', 'humboldt-park', 'An inland swimming lagoon '
              'with a sand beach and lifeguards in summer.', ['swimming', 'kids'], 'free', 'outdoor',
              ['family', 'friends'], DAY, SUMMER),
        place('paseo-boricua', 'Paseo Boricua', 'landmark', 'humboldt-park', 'Division Street between two 59-foot '
              'steel Puerto Rican flags, lined with murals, bakeries and social clubs.', ['puerto-rican', 'murals',
              'walk'], 'free', 'outdoor', ALL, DAYLONG),
        place('nmprac', 'National Museum of Puerto Rican Arts & Culture', 'museum', 'humboldt-park', 'Exhibitions '
              'and classes in the park\'s old horse stables.', ['art', 'puerto-rican', 'free'], 'free', 'indoor',
              ALL, DAY),
        place('cafe-colao', 'Café Colao', 'cafe', 'humboldt-park', 'Puerto Rican bakery on Division for café con '
              'leche, quesitos and pastelillos.', ['coffee', 'bakery', 'puerto-rican'], '$', 'indoor', ALL, DAY,
              cuisine='puerto-rican'),
        place('papas-cache-sabroso', 'Papa\'s Cache Sabroso', 'restaurant', 'humboldt-park', 'Counter-service '
              'Puerto Rican food, best known for the jibarito made with fried plantains for bread.', ['jibarito',
              'cheap', 'puerto-rican'], '$', 'indoor', ALL, LUNCH, cuisine='puerto-rican'),
        # West Loop & Fulton Market
        place('girl-and-the-goat', 'Girl & the Goat', 'restaurant', 'west-loop', 'Stephanie Izard\'s loud, '
              'shareable-plates room that set off Randolph Street\'s restaurant boom.', ['celebrated', 'sharing'],
              '$$$', 'indoor', ['date', 'friends'], DINNER, cuisine='modern-american'),
        place('au-cheval', 'Au Cheval', 'restaurant', 'west-loop', 'Diner-style bar with a famous double cheeseburger '
              'and long waits.', ['burgers', 'line', 'late-night'], '$$', 'indoor', ['friends', 'date'],
              ['afternoon', 'evening', 'late'], cuisine='american'),
        place('time-out-market', 'Time Out Market Chicago', 'market', 'west-loop', 'A Fulton Market food hall of '
              'local chefs\' stalls with a rooftop bar.', ['food-hall', 'groups'], '$$', 'indoor', ALL, LUNCH),
        place('lou-mitchells', 'Lou Mitchell\'s', 'restaurant', 'west-loop', 'A Route 66 breakfast diner near Union '
              'Station since 1923 that hands out Milk Duds and donut holes to the queue.', ['breakfast', 'historic',
              'diner'], '$', 'indoor', ALL, ['morning'], cuisine='american-breakfast'),
        place('sawada-coffee', 'Sawada Coffee', 'cafe', 'west-loop', 'Military-latte coffee bar in a warehouse '
              'off Green Street.', ['coffee', 'matcha'], '$', 'indoor', ['solo', 'friends', 'coworkers'], DAY),
        place('union-station', 'Chicago Union Station', 'landmark', 'west-loop', 'The Beaux-Arts Great Hall under a '
              'barrel-vault skylight, still busy with Amtrak and Metra.', ['architecture', 'trains', 'free'],
              'free', 'indoor', ALL, DAYLONG),
        place('united-center', 'United Center', 'stadium', 'west-loop', 'Arena of the Bulls and Blackhawks, with '
              'the Michael Jordan statue out front and big touring concerts.', ['basketball', 'hockey',
              'concerts'], '$$$', 'indoor', ['friends', 'family', 'date'], ['evening'], ['fall', 'winter',
              'spring']),
        place('haymarket-pub', 'Haymarket Pub & Brewery', 'bar', 'west-loop', 'Brewpub near the site of the 1886 '
              'Haymarket rally, with beer brewed on site.', ['beer', 'brewpub', 'history'], '$$', 'indoor',
              ['friends', 'coworkers'], NIGHT, cuisine='american'),
        # Little Italy & University Village
        place('marios-lemonade', 'Mario\'s Italian Lemonade', 'restaurant', 'little-italy', 'A summer-only Taylor '
              'Street stand scooping Italian ice since 1954, with a line on hot evenings.', ['italian-ice',
              'summer', 'cheap'], '$', 'outdoor', ALL, ['afternoon', 'evening'], ['spring', 'summer'],
              cuisine='dessert'),
        place('als-beef-taylor', 'Al\'s #1 Italian Beef (Taylor Street)', 'restaurant', 'little-italy', 'The '
              'original Al\'s counter, where people eat beef sandwiches standing at the ledge in the "Italian '
              'stance".', ['italian-beef', 'historic', 'cheap'], '$', 'indoor', ['solo', 'friends'], LUNCH,
              cuisine='chicago-street-food'),
        place('jims-original', 'Jim\'s Original', 'restaurant', 'little-italy', 'Walk-up stand by the expressway '
              'serving Maxwell Street Polish sausages with grilled onions and free fries, nearly around the clock.',
              ['polish-sausage', 'late-night', 'cheap'], '$', 'outdoor', ['solo', 'friends'],
              ['morning', 'afternoon', 'evening', 'late'], cuisine='chicago-street-food'),
        place('conte-di-savoia', 'Conte di Savoia', 'market', 'little-italy', 'Italian grocery and deli on Taylor '
              'Street for imported pasta, cheeses and sub sandwiches.', ['deli', 'italian', 'groceries'], '$',
              'indoor', ALL, DAY, cuisine='italian'),
        place('hull-house-museum', 'Jane Addams Hull-House Museum', 'museum', 'little-italy', 'The settlement house '
              'of the social reformer, now on the UIC campus, with free tours and soup lunches.', ['history', 'free'],
              'free', 'indoor', ['solo', 'friends'], DAY),
        place('tufanos', 'Tufano\'s Vernon Park Tap', 'restaurant', 'little-italy', 'A family-run red-sauce '
              'tavern since the 1930s, with chalkboard specials and old-neighborhood regulars.', ['italian',
              'historic', 'family'], '$$', 'indoor', ALL, LUNCH, cuisine='italian'),
        place('maxwell-street-market', 'Maxwell Street Market', 'market', 'little-italy', 'The descendant of the '
              'old open-air market where Chicago blues was played on the street, now a Sunday market of tools, '
              'clothes and tacos.', ['flea-market', 'tacos', 'sunday'], '$', 'outdoor', ALL, ['morning'], WARM),
        # Pilsen
        place('national-museum-mexican-art', 'National Museum of Mexican Art', 'museum', 'pilsen', 'A free museum in '
              'Harrison Park with a large collection and a famous Day of the Dead exhibition every autumn.',
              ['art', 'free', 'mexican'], 'free', 'indoor', ALL, DAY),
        place('pilsen-murals', '18th Street murals', 'landmark', 'pilsen', 'Murals on viaducts, schools and '
              'storefronts along 16th and 18th streets, from Aztec themes to labor history.', ['murals', 'walk',
              'art'], 'free', 'outdoor', ALL, DAY),
        place('cafe-jumping-bean', 'Café Jumping Bean', 'cafe', 'pilsen', 'Long-running 18th Street coffeehouse '
              'covered in local art, with tortas and chess players.', ['coffee', 'art', 'community'], '$', 'indoor',
              ['solo', 'friends'], DAYLONG),
        place('carnitas-uruapan', 'Carnitas Uruapan', 'restaurant', 'pilsen', 'Family-run since 1975, selling '
              'carnitas by the pound with tortillas, salsa and chicharrón.', ['tacos', 'carnitas', 'family'], '$',
              'indoor', ALL, DAY, cuisine='mexican'),
        place('thalia-hall', 'Thalia Hall', 'venue', 'pilsen', 'An 1892 Bohemian opera hall at 18th and Allport, '
              'restored for concerts.', ['live-music', 'historic'], '$$', 'indoor', ['friends', 'date'], NIGHT),
        place('pilsen-community-books', 'Pilsen Community Books', 'shopping', 'pilsen', 'Used and new bookshop on '
              '18th Street with readings and a strong Latinx shelf.', ['books', 'community'], '$', 'indoor',
              ['solo', 'date'], DAYLONG),
        # Little Village
        place('little-village-arch', 'Little Village Arch', 'landmark', 'little-village', 'The tiled "Bienvenidos a '
              'Little Village" arch with its clock over 26th Street.', ['mexican', 'photo'], 'free', 'outdoor', ALL,
              DAYLONG),
        place('26th-street', '26th Street', 'shopping', 'little-village', 'A mile of quinceañera dress shops, '
              'botas, paleterías and the Discount Mall, busiest on weekends.', ['shopping', 'mexican', 'paletas'],
              '$', 'outdoor', ALL, DAYLONG),
        place('el-milagro', 'Taquería El Milagro', 'restaurant', 'little-village', 'Cafeteria-style tacos and '
              'tamales beside the tortilla factory on 26th Street.', ['tacos', 'cheap', 'tortillas'], '$', 'indoor',
              ALL, DAYLONG, cuisine='mexican'),
        place('douglass-park', 'Douglass Park', 'park', 'little-village', 'A big West Side park with a lagoon and '
              'soccer fields busy every weekend.', ['soccer', 'picnics'], 'free', 'outdoor', ALL, DAYLONG, WARM),
        place('mi-tierra', 'Mi Tierra', 'restaurant', 'little-village', 'Big family restaurant on 26th with '
              'mariachis on weekend nights and enormous margaritas.', ['mexican', 'mariachi', 'groups'], '$$',
              'indoor', ['family', 'friends'], LUNCH, cuisine='mexican'),
        # Chinatown
        place('ping-tom-park', 'Ping Tom Memorial Park', 'park', 'chinatown', 'Riverside park with a pagoda, a '
              'water taxi stop and dragon boats in summer.', ['riverside', 'kids', 'dragon-boats'], 'free',
              'outdoor', ALL, DAYLONG),
        place('ping-tom-fieldhouse', 'Ping Tom Park Fieldhouse', 'fitness', 'chinatown', 'Park district fieldhouse '
              'with an indoor pool, gym and cheap classes.', ['pool', 'gym', 'cheap'], '$', 'indoor',
              ['solo', 'family'], DAYLONG),
        place('chinatown-gate', 'Chinatown Gate and Wentworth Avenue', 'landmark', 'chinatown', 'The red gate at '
              'Cermak and Wentworth, with herbalists, bakeries and the Pui Tak Center beyond.', ['walk', 'history'],
              'free', 'outdoor', ALL, DAYLONG),
        place('chinatown-square', 'Chinatown Square', 'shopping', 'chinatown', 'Two-story outdoor mall with '
              'zodiac statues, bubble tea, hot pot and karaoke.', ['shopping', 'bubble-tea'], '$', 'outdoor', ALL,
              DAYLONG),
        place('chiu-quon-bakery', 'Chiu Quon Bakery', 'cafe', 'chinatown', 'Wentworth Avenue bakery since 1986 for '
              'egg tarts, pineapple buns and barbecue pork buns.', ['bakery', 'cheap', 'pastries'], '$', 'indoor',
              ALL, DAY, cuisine='chinese'),
        place('minghin', 'MingHin Cuisine', 'restaurant', 'chinatown', 'Busy Cantonese room with weekend dim sum '
              'carts of dumplings and turnip cakes.', ['dim-sum', 'groups', 'family'], '$$', 'indoor', ALL,
              DAYLONG, cuisine='cantonese'),
        place('lao-sze-chuan', 'Lao Sze Chuan', 'restaurant', 'chinatown', 'Fiery Sichuan dishes like dry chili '
              'chicken, a Chinatown staple.', ['spicy', 'groups'], '$$', 'indoor', ['friends', 'family', 'date'],
              LUNCH, cuisine='sichuan'),
        place('chinatown-library', 'Chinatown Branch Library', 'library', 'chinatown', 'A rounded glass library '
              'with a central atrium, open since 2015.', ['books', 'architecture', 'quiet'], 'free', 'indoor',
              ['solo', 'family'], DAY),
        # South Loop & Museum Campus
        place('field-museum', 'Field Museum', 'museum', 'south-loop', 'Natural history on the lakefront: Sue the '
              'T. rex, the Egyptian tomb and halls of dioramas.', ['dinosaurs', 'rainy-day', 'kids', 'iconic'], '$$$',
              'indoor', ALL, DAY),
        place('shedd-aquarium', 'Shedd Aquarium', 'attraction', 'south-loop', 'Lakefront aquarium with beluga whales, '
              'a Caribbean reef and a view back to the skyline.', ['animals', 'rainy-day', 'kids'], '$$$', 'indoor',
              ALL, DAY),
        place('adler-planetarium', 'Adler Planetarium', 'museum', 'south-loop', 'Planetarium at the end of the '
              'Museum Campus peninsula, with the best skyline view in the city.', ['space', 'views', 'kids'], '$$',
              'mixed', ALL, DAY),
        place('soldier-field', 'Soldier Field', 'stadium', 'south-loop', 'The Bears\' lakefront stadium inside '
              'its old colonnades, also home to the Chicago Fire.', ['football', 'soccer', 'sports'], '$$$',
              'outdoor', ['friends', 'family'], ['afternoon', 'evening'], ['fall', 'winter']),
        place('12th-street-beach', '12th Street Beach', 'beach', 'south-loop', 'A small curving beach behind the '
              'Adler, quieter than the North Side beaches.', ['swimming', 'quiet'], 'free', 'outdoor', ALL, DAY,
              SUMMER),
        place('buddy-guys-legends', 'Buddy Guy\'s Legends', 'nightlife', 'south-loop', 'Blues club on Wabash owned '
              'by the guitarist, with Cajun food and bands every night.', ['blues', 'live-music', 'iconic'], '$$',
              'indoor', ADULT, NIGHT, cuisine='cajun'),
        place('jazz-showcase', 'Jazz Showcase', 'nightlife', 'south-loop', 'A serious jazz room near Dearborn '
              'Station that has booked touring greats since 1947.', ['jazz', 'live-music'], '$$', 'indoor',
              ['date', 'solo', 'friends'], NIGHT),
        place('glessner-house', 'Glessner House', 'museum', 'south-loop', 'A fortress-like 1887 Richardson house on '
              'Prairie Avenue, once the city\'s millionaires\' row.', ['architecture', 'history'], '$$', 'indoor',
              ['solo', 'date'], DAY),
        place('eleven-city-diner', 'Eleven City Diner', 'restaurant', 'south-loop', 'Jewish deli and diner on '
              'Wabash with pastrami, matzo ball soup and egg creams.', ['deli', 'brunch'], '$$', 'indoor', ALL,
              DAYLONG, cuisine='jewish-deli'),
        # Bronzeville
        place('victory-monument', 'Victory Monument', 'landmark', 'bronzeville', 'Memorial to the Black 8th '
              'Illinois regiment of the First World War, at 35th and King Drive.', ['history', 'black-history'],
              'free', 'outdoor', ALL, DAY),
        place('bronzeville-walk-of-fame', 'Bronzeville Walk of Fame', 'landmark', 'bronzeville', 'Plaques along King '
              'Drive honouring Louis Armstrong, Ida B. Wells, Gwendolyn Brooks and other residents.', ['history',
              'black-history', 'walk'], 'free', 'outdoor', ALL, DAY, WARM),
        place('chicago-bee-library', 'Chicago Bee Branch Library', 'library', 'bronzeville', 'A public library in '
              'the art deco home of the Chicago Bee, a Black newspaper of the 1920s.', ['books', 'history',
              'architecture'], 'free', 'indoor', ['solo', 'family'], DAY),
        place('peachs', 'Peach\'s Restaurant', 'restaurant', 'bronzeville', 'Southern breakfast on 47th Street: '
              'shrimp and grits, salmon croquettes and a weekend crowd after church.', ['brunch', 'soul-food'], '$$',
              'indoor', ALL, DAY, cuisine='soul-food'),
        place('gallery-guichard', 'Gallery Guichard', 'museum', 'bronzeville', 'Gallery of art from the African '
              'diaspora on 47th Street, with openings that turn into parties.', ['art', 'black-history'], 'free',
              'indoor', ADULT, ['afternoon', 'evening']),
        place('31st-street-beach', '31st Street Beach', 'beach', 'bronzeville', 'A family beach by the harbor, with '
              'a pier, picnic lawns and a cafe in the beach house.', ['swimming', 'family', 'harbor'], 'free',
              'outdoor', ALL, DAY, SUMMER),
        # Hyde Park
        place('museum-science-industry', 'Museum of Science and Industry', 'museum', 'hyde-park', 'The last big '
              'building of the 1893 World\'s Fair, holding a coal mine, a German U-boat and a working tornado.',
              ['science', 'kids', 'rainy-day', 'iconic'], '$$$', 'indoor', ALL, DAY),
        place('robie-house', 'Frederick C. Robie House', 'museum', 'hyde-park', 'Frank Lloyd Wright\'s long, low '
              'Prairie house on the university campus, open for tours.', ['architecture', 'wright'], '$$', 'indoor',
              ['solo', 'date'], DAY),
        place('promontory-point', 'Promontory Point', 'park', 'hyde-park', 'A stepped limestone peninsula for '
              'swimming off the rocks, bonfires and a long skyline view north.', ['lake', 'views', 'picnics'],
              'free', 'outdoor', ALL, DAYLONG, WARM),
        place('seminary-co-op', 'Seminary Co-op Bookstores', 'shopping', 'hyde-park', 'The scholarly co-op '
              'bookstore and 57th Street Books, the neighborhood\'s two serious bookshops.', ['books', 'academic'],
              '$$', 'indoor', ['solo', 'date'], DAYLONG),
        place('plein-air-cafe', 'Plein Air Cafe', 'cafe', 'hyde-park', 'Light-filled cafe next to the Robie House, '
              'with students and lecturers on laptops.', ['coffee', 'students'], '$', 'indoor', ['solo', 'friends'],
              DAY),
        place('medici-on-57th', 'Medici on 57th', 'restaurant', 'hyde-park', 'Carved-up wooden booths, pizza, '
              'burgers and a bakery next door, a student haunt since 1963.', ['students', 'historic'], '$', 'indoor',
              ALL, DAYLONG, cuisine='american'),
        place('valois', 'Valois Restaurant', 'restaurant', 'hyde-park', 'A 53rd Street cafeteria ("See Your Food") '
              'with cheap breakfast, a long counter and everyone from cops to professors.', ['breakfast', 'cheap',
              'cafeteria'], '$', 'indoor', ALL, DAY, cuisine='american-breakfast'),
        place('isac-museum', 'ISAC Museum', 'museum', 'hyde-park', 'The University of Chicago\'s free museum of the '
              'ancient Near East, with a 40-ton winged bull from Khorsabad.', ['history', 'free', 'archaeology'],
              'free', 'indoor', ['solo', 'date', 'family'], DAY),
        place('dusable-museum', 'DuSable Black History Museum', 'museum', 'hyde-park', 'One of the oldest museums of '
              'African American history, in Washington Park.', ['history', 'black-history'], '$', 'indoor', ALL,
              DAY),
        place('jackson-park', 'Jackson Park and the Garden of the Phoenix', 'park', 'hyde-park', 'Olmsted\'s '
              'lagoons and wooded island from the 1893 fair, with a Japanese garden.', ['garden', 'walk', 'birds'],
              'free', 'outdoor', ALL, DAY, WARM),
        # Bridgeport
        place('rate-field', 'Rate Field', 'stadium', 'bridgeport', 'The White Sox ballpark at 35th Street, long '
              'called Comiskey and then Guaranteed Rate Field, with Maxwell Street Polishes at the stands.',
              ['baseball', 'sports'], '$$', 'outdoor', ALL, ['afternoon', 'evening'], WARM),
        place('marias', 'Maria\'s Packaged Goods & Community Bar', 'bar', 'bridgeport', 'A liquor store in front '
              'and a craft-beer bar in back, a model of the new Bridgeport.', ['beer', 'neighbourly'], '$$',
              'indoor', ADULT, NIGHT),
        place('bridgeport-coffee', 'Bridgeport Coffee', 'cafe', 'bridgeport', 'A corner coffee shop on Morgan '
              'Street that roasts its own beans.', ['coffee', 'neighbourly'], '$', 'indoor', ['solo', 'friends'],
              DAY),
        place('duck-inn', 'The Duck Inn', 'restaurant', 'bridgeport', 'Tavern-meets-restaurant with a rotisserie '
              'duck and a duck-fat hot dog.', ['hot-dogs', 'cocktails'], '$$', 'indoor', ['date', 'friends'],
              DINNER, cuisine='american'),
        place('palmisano-park', 'Palmisano Park', 'park', 'bridgeport', 'A former limestone quarry turned into a park '
              'with a fishing pond, terraced paths and a hilltop skyline view.', ['views', 'walk', 'fishing'],
              'free', 'outdoor', ALL, DAYLONG, WARM),
        place('ramova', 'Ramova Theatre', 'venue', 'bridgeport', 'A 1929 Spanish-style movie palace on Halsted, '
              'reopened as a music venue with a brewery and the old grill next door.', ['live-music', 'historic',
              'beer'], '$$', 'indoor', ['friends', 'date'], NIGHT),
        # Andersonville
        place('swedish-american-museum', 'Swedish American Museum', 'museum', 'andersonville', 'Small museum on '
              'Clark Street about Swedish immigrants, with a children\'s museum upstairs.', ['history', 'kids'], '$',
              'indoor', ALL, DAY),
        place('hopleaf', 'Hopleaf', 'bar', 'andersonville', 'Belgian beer bar with a long list, mussels and frites '
              'and no kids allowed.', ['beer', 'belgian', 'mussels'], '$$', 'indoor', ADULT, NIGHT,
              cuisine='belgian'),
        place('women-and-children-first', 'Women & Children First', 'shopping', 'andersonville', 'A feminist '
              'bookstore since 1979, with readings and a strong LGBTQ+ section.', ['books', 'feminist',
              'readings'], '$$', 'indoor', ['solo', 'date', 'friends'], DAYLONG),
        place('coffee-studio', 'The Coffee Studio', 'cafe', 'andersonville', 'Small, serious coffee bar on Clark '
              'Street with seats in the window.', ['coffee', 'neighbourly'], '$', 'indoor', ['solo', 'friends'],
              DAY),
        place('big-jones', 'Big Jones', 'restaurant', 'andersonville', 'Southern heritage cooking with a well-loved '
              'brunch of beignets and fried chicken.', ['southern', 'brunch'], '$$', 'indoor', ALL, DAYLONG,
              cuisine='southern'),
        place('simons-tavern', 'Simon\'s Tavern', 'bar', 'andersonville', 'Old Swedish tavern with a neon fish sign '
              'that serves its own glögg in winter.', ['dive', 'swedish', 'glogg'], '$', 'indoor', ADULT, NIGHT),
        # Uptown
        place('green-mill', 'Green Mill Cocktail Lounge', 'nightlife', 'uptown', 'A 1907 jazz lounge where Capone '
              'had a booth, with live jazz nightly and the Uptown Poetry Slam on Sundays.', ['jazz', 'historic',
              'cocktails'], '$$', 'indoor', ['date', 'friends', 'solo'], NIGHT),
        place('aragon-ballroom', 'Aragon Ballroom', 'venue', 'uptown', 'A 1926 Spanish-courtyard ballroom with a '
              'starry ceiling, now for big rock and electronic shows.', ['live-music', 'historic'], '$$', 'indoor',
              ['friends'], NIGHT),
        place('riviera-theatre', 'Riviera Theatre', 'venue', 'uptown', 'A former movie palace at Broadway and '
              'Lawrence hosting mid-size concerts.', ['live-music'], '$$', 'indoor', ['friends', 'date'], NIGHT),
        place('montrose-beach', 'Montrose Beach and the Magic Hedge', 'beach', 'uptown', 'The city\'s biggest beach, '
              'with a dog beach, a fishing pier and a bird sanctuary famous for spring migration.', ['swimming',
              'birding', 'dogs'], 'free', 'outdoor', ALL, DAY, BEACH),
        place('tank-noodle', 'Tank Noodle', 'restaurant', 'uptown', 'Big, busy pho and bánh mì restaurant at '
              'Argyle and Broadway.', ['pho', 'cheap', 'vietnamese'], '$', 'indoor', ALL, DAYLONG,
              cuisine='vietnamese'),
        place('ba-le', 'Ba Le Sandwiches', 'restaurant', 'uptown', 'Bakery and bánh mì shop on Broadway with French '
              'bread baked in house.', ['banh-mi', 'cheap', 'bakery'], '$', 'indoor', ['solo', 'friends'], DAY,
              cuisine='vietnamese'),
        place('carols-pub', 'Carol\'s Pub', 'bar', 'uptown', 'Late-night honky-tonk on Clark Street with a house '
              'country band and karaoke nights.', ['country', 'dive', 'late-night'], '$', 'indoor', ['friends'],
              NIGHT),
        place('first-ascent-uptown', 'First Ascent Uptown', 'fitness', 'uptown', 'A climbing gym for bouldering '
              'and ropes, with yoga and a fitness floor.', ['climbing', 'gym', 'yoga'], '$$', 'indoor',
              ['solo', 'friends', 'date'], DAYLONG),
        # Rogers Park & West Ridge
        place('loyola-beach', 'Loyola Beach', 'beach', 'rogers-park', 'The largest Rogers Park beach, along a '
              'seawall covered in community murals.', ['swimming', 'murals', 'quiet'], 'free', 'outdoor', ALL, DAY,
              SUMMER),
        place('lifeline-theatre', 'Lifeline Theatre', 'venue', 'rogers-park', 'Small theater on Glenwood Avenue '
              'staging adaptations of novels and family shows.', ['theater', 'kids'], '$$', 'indoor',
              ['date', 'family', 'friends'], ['afternoon', 'evening']),
        place('glenwood-sunday-market', 'Glenwood Sunday Market', 'market', 'rogers-park', 'Farmers market on a '
              'closed street beside the Morse L stop.', ['farmers-market', 'sunday'], '$', 'outdoor', ALL,
              ['morning'], WARM),
        place('devon-avenue', 'Devon Avenue', 'shopping', 'rogers-park', 'The South Asian shopping street of West '
              'Ridge: sari shops, jewellers, sweets counters and halal butchers.', ['south-asian', 'shopping',
              'walk'], '$', 'outdoor', ALL, DAYLONG),
        place('udupi-palace', 'Udupi Palace', 'restaurant', 'rogers-park', 'South Indian vegetarian restaurant on '
              'Devon for dosas and thalis.', ['vegetarian', 'dosas'], '$', 'indoor', ALL, LUNCH,
              cuisine='south-indian'),
        place('sabri-nihari', 'Sabri Nihari', 'restaurant', 'rogers-park', 'Pakistani restaurant on Devon known for '
              'nihari stew and grilled meats.', ['halal', 'spicy'], '$$', 'indoor', ['family', 'friends'], LUNCH,
              cuisine='pakistani'),
        place('patel-brothers', 'Patel Brothers', 'market', 'rogers-park', 'The original Patel Brothers on Devon, '
              'an Indian grocery that grew into a national chain.', ['groceries', 'south-asian'], '$', 'indoor',
              ALL, DAYLONG),
        place('the-glenwood', 'The Glenwood', 'bar', 'rogers-park', 'Friendly neighborhood bar by the Morse '
              'stop, popular with the area\'s LGBTQ+ residents.', ['neighbourly', 'lgbtq'], '$', 'indoor', ADULT,
              NIGHT),
        # Evanston
        place('northwestern-lakefill', 'Northwestern Lakefill', 'park', 'evanston', 'Lawns and rocks on landfill at '
              'the edge of the campus, with a view of the skyline down the shore.', ['lake', 'students', 'views'],
              'free', 'outdoor', ALL, DAYLONG, WARM),
        place('block-museum', 'Block Museum of Art', 'museum', 'evanston', 'Northwestern\'s free art museum, with a '
              'film series in its auditorium.', ['art', 'free', 'film'], 'free', 'indoor', ['solo', 'date'], DAY),
        place('grosse-point-lighthouse', 'Grosse Point Lighthouse', 'landmark', 'evanston', 'An 1873 lighthouse '
              'with gardens at the north end of town, open for summer tours.', ['history', 'lake'], '$', 'outdoor',
              ALL, DAY, WARM),
        place('evanston-beaches', 'Evanston beaches', 'beach', 'evanston', 'A string of lakefront beaches that '
              'charge a seasonal token, quieter than the city\'s.', ['swimming', 'family'], '$', 'outdoor', ALL,
              DAY, SUMMER),
        place('bennisons-bakery', 'Bennison\'s Bakery', 'cafe', 'evanston', 'Old-fashioned downtown Evanston bakery '
              'with coffee, pastries and birthday cakes.', ['bakery', 'coffee'], '$', 'indoor', ALL, DAY),
        place('mcgaw-ymca', 'McGaw YMCA', 'fitness', 'evanston', 'Evanston\'s big Y, with pools, weights and youth '
              'sports.', ['gym', 'pool', 'community'], '$', 'indoor', ['solo', 'family'], DAYLONG),
        place('space-evanston', 'SPACE', 'venue', 'evanston', 'A listening room for folk, roots and jazz, with '
              'pizza from the attached restaurant.', ['live-music', 'folk'], '$$', 'indoor', ['date', 'friends'],
              NIGHT),
        place('edzos', 'Edzo\'s Burger Shop', 'restaurant', 'evanston', 'Griddled burgers, hand-cut fries and '
              'milkshakes, popular with Northwestern students.', ['burgers', 'cheap', 'students'], '$', 'indoor',
              ALL, DAY, cuisine='american'),
        # Oak Park
        place('wright-home-and-studio', 'Frank Lloyd Wright Home and Studio', 'museum', 'oak-park', 'Where the '
              'architect lived and worked for twenty years, with walking tours past his early houses.',
              ['architecture', 'wright', 'tours'], '$$', 'indoor', ['solo', 'date', 'family'], DAY),
        place('unity-temple', 'Unity Temple', 'landmark', 'oak-park', 'Wright\'s concrete 1908 church, a World '
              'Heritage Site, still used by its congregation.', ['architecture', 'wright'], '$$', 'indoor',
              ['solo', 'date'], DAY),
        place('hemingway-birthplace', 'Ernest Hemingway Birthplace Museum', 'museum', 'oak-park', 'The Queen Anne '
              'house where the writer was born in 1899.', ['literature', 'history'], '$', 'indoor', ['solo',
              'date'], DAY),
        place('oak-park-farmers-market', 'Oak Park Farmers Market', 'market', 'oak-park', 'Saturday-morning market '
              'with church-made donuts that sell out early.', ['farmers-market', 'donuts'], '$', 'outdoor', ALL,
              ['morning'], WARM),
        place('lake-theatre', 'Lake Theatre', 'venue', 'oak-park', 'An art deco cinema on Lake Street in downtown '
              'Oak Park.', ['cinema', 'art-deco'], '$', 'indoor', ALL, ['afternoon', 'evening']),
        place('poor-phils', 'Poor Phil\'s', 'bar', 'oak-park', 'Neighborhood oyster bar and grill with a big patio '
              'in downtown Oak Park.', ['oysters', 'patio'], '$$', 'mixed', ['friends', 'family', 'date'], NIGHT,
              cuisine='seafood'),
    ],
    'colleges': [
        college('uchicago', 'University of Chicago', 'research-university', 'hyde-park', 'large',
                ['economics', 'physics', 'law', 'medicine', 'social-sciences', 'research']),
        college('northwestern', 'Northwestern University', 'research-university', 'evanston', 'large',
                ['journalism', 'theater', 'engineering', 'business', 'music']),
        college('northwestern-chicago', 'Northwestern University (Chicago campus)', 'medical-school', 'streeterville',
                'medium', ['medicine', 'law', 'nursing']),
        college('loyola', 'Loyola University Chicago', 'private-university', 'rogers-park', 'large',
                ['nursing', 'business', 'law', 'social-work']),
        college('depaul', 'DePaul University', 'private-university', 'lincoln-park', 'large',
                ['business', 'computing', 'theater', 'music']),
        college('uic', 'University of Illinois Chicago', 'public-university', 'little-italy', 'large',
                ['medicine', 'pharmacy', 'engineering', 'nursing', 'architecture']),
        college('columbia-college', 'Columbia College Chicago', 'art-school', 'south-loop', 'medium',
                ['film', 'music', 'photography', 'comedy-writing']),
        college('saic', 'School of the Art Institute of Chicago', 'art-school', 'the-loop', 'medium',
                ['fine-art', 'fashion', 'sculpture', 'art-history']),
        college('iit', 'Illinois Institute of Technology', 'technical-institute', 'bronzeville', 'medium',
                ['architecture', 'engineering', 'design', 'computer-science']),
        college('harold-washington-college', 'Harold Washington College', 'community-college', 'the-loop', 'medium',
                ['transfer', 'business', 'art']),
        college('truman-college', 'Truman College', 'community-college', 'uptown', 'medium',
                ['nursing', 'english-as-a-second-language', 'transfer']),
        college('roosevelt', 'Roosevelt University', 'private-university', 'the-loop', 'small',
                ['music', 'performing-arts', 'social-justice']),
    ],
    'employers': [
        employer('northwestern-medicine', 'Northwestern Memorial Hospital', 'healthcare', 'streeterville', 'large',
                 'The flagship of Northwestern Medicine, among the busiest hospitals in the Midwest.',
                 ['registered-nurse', 'night-nurse', 'physician-resident', 'pharmacist', 'medical-researcher',
                  'social-worker']),
        employer('lurie-childrens', 'Ann & Robert H. Lurie Children\'s Hospital', 'healthcare', 'streeterville',
                 'large', 'Children\'s hospital tower in Streeterville.',
                 ['registered-nurse', 'night-nurse', 'physician-resident', 'social-worker']),
        employer('rush', 'Rush University Medical Center', 'healthcare', 'little-italy', 'large', 'Academic '
                 'hospital with a butterfly-shaped tower in the Illinois Medical District.',
                 ['registered-nurse', 'night-nurse', 'physician-resident', 'pharmacist', 'medical-researcher']),
        employer('uchicago-medicine', 'University of Chicago Medicine', 'healthcare', 'hyde-park', 'large',
                 'Academic medical center and the South Side\'s adult trauma center.',
                 ['registered-nurse', 'night-nurse', 'physician-resident', 'medical-researcher', 'biotech-scientist']),
        employer('uchicago-employer', 'University of Chicago', 'education', 'hyde-park', 'large', 'Faculty, research '
                 'and staff jobs on the Hyde Park campus.',
                 ['professor', 'graduate-student', 'medical-researcher', 'data-analyst', 'biologist']),
        employer('northwestern-employer', 'Northwestern University', 'education', 'evanston', 'large', 'The '
                 'university\'s Evanston campus.', ['professor', 'graduate-student', 'software-engineer', 'biologist']),
        employer('united-airlines', 'United Airlines', 'transportation', 'the-loop', 'large', 'Airline headquartered '
                 'in Willis Tower, with its biggest hub at O\'Hare.',
                 ['data-analyst', 'software-engineer', 'financial-analyst', 'marketing-coordinator']),
        employer('cme-group', 'CME Group', 'finance', 'the-loop', 'large', 'The futures exchange, descended from the '
                 'Board of Trade and the Mercantile Exchange, headquartered on Wacker Drive.',
                 ['financial-analyst', 'software-engineer', 'data-analyst', 'finance-banker']),
        employer('northern-trust', 'Northern Trust', 'finance', 'the-loop', 'large', 'Wealth management and custody '
                 'bank on LaSalle Street.', ['finance-banker', 'financial-analyst', 'accountant', 'software-engineer']),
        employer('kirkland-ellis', 'Kirkland & Ellis', 'legal', 'the-loop', 'large', 'Large law firm headquartered '
                 'in the Loop.', ['paralegal', 'accountant']),
        employer('exelon', 'Exelon and ComEd', 'energy', 'the-loop', 'large', 'The utility holding company and the '
                 'electric company that serves northern Illinois.',
                 ['financial-analyst', 'data-analyst', 'construction-trades', 'accountant']),
        employer('hyatt', 'Hyatt Hotels', 'hospitality', 'the-loop', 'large', 'Hotel company headquartered on the '
                 'river at Riverside Plaza.', ['marketing-coordinator', 'accountant', 'data-analyst', 'event-planner']),
        employer('palmer-house', 'Palmer House Hilton', 'hospitality', 'the-loop', 'large', 'A grand 1870s hotel '
                 'with a painted lobby ceiling, where the brownie was invented.',
                 ['hotel-front-desk', 'event-planner', 'line-cook', 'server', 'bartender']),
        employer('city-of-chicago', 'City of Chicago', 'government', 'the-loop', 'large', 'City departments around '
                 'City Hall on LaSalle Street.', ['government-analyst', 'social-worker', 'accountant', 'paralegal']),
        employer('cps', 'Chicago Public Schools', 'education', 'the-loop', 'large', 'The third-largest school '
                 'district in the country, with headquarters on Madison Street.', ['teacher', 'social-worker']),
        employer('cta', 'Chicago Transit Authority', 'transportation', 'west-loop', 'large', 'Runs the L and the '
                 'buses from its headquarters on Lake Street.',
                 ['government-analyst', 'construction-trades', 'data-analyst', 'accountant']),
        employer('mcdonalds-hq', 'McDonald\'s headquarters', 'food', 'west-loop', 'large', 'The company\'s global '
                 'headquarters in Fulton Market, with a test kitchen and a ground-floor restaurant.',
                 ['marketing-coordinator', 'data-analyst', 'software-engineer', 'graphic-designer', 'ux-designer']),
        employer('google-chicago', 'Google Chicago', 'technology', 'west-loop', 'large', 'Engineering and sales '
                 'offices in a former cold-storage building in Fulton Market.',
                 ['software-engineer', 'ux-designer', 'data-analyst']),
        employer('united-center-employer', 'United Center', 'entertainment', 'west-loop', 'medium', 'Arena for '
                 'the Bulls, the Blackhawks and big concerts.',
                 ['event-planner', 'bartender', 'server', 'retail-associate']),
        employer('navy-pier-employer', 'Navy Pier', 'tourism', 'streeterville', 'medium', 'Restaurants, rides, boat '
                 'tours and events on the pier.',
                 ['event-planner', 'server', 'line-cook', 'tour-guide', 'retail-associate']),
        employer('chicago-public-media', 'Chicago Public Media', 'media', 'streeterville', 'medium', 'WBEZ and the '
                 'Chicago Sun-Times, with studios at Navy Pier.', ['journalist', 'marketing-coordinator']),
        employer('lyric-opera', 'Lyric Opera of Chicago', 'entertainment', 'the-loop', 'medium', 'The opera company '
                 'at the Civic Opera House on Wacker Drive.', ['musician', 'performer', 'event-planner']),
        employer('steppenwolf-employer', 'Steppenwolf Theatre Company', 'entertainment', 'lincoln-park', 'small',
                 'Ensemble theater company on Halsted Street.', ['actor', 'performer']),
        employer('second-city-employer', 'The Second City', 'entertainment', 'lincoln-park', 'medium', 'Comedy '
                 'theater and training center with resident and touring companies.',
                 ['actor', 'performer', 'bartender', 'server']),
        employer('ballys-chicago', 'Bally\'s Chicago', 'hospitality', 'river-north', 'medium', 'The city\'s '
                 'first casino, opened in the old Medinah Temple while a permanent one is built.',
                 ['casino-dealer', 'bartender', 'server', 'line-cook']),
        employer('field-museum-employer', 'Field Museum', 'education', 'south-loop', 'medium', 'Natural history '
                 'museum with research collections and scientists on staff.',
                 ['biologist', 'tour-guide', 'event-planner']),
        employer('cubs', 'Chicago Cubs', 'entertainment', 'lakeview', 'medium', 'The baseball club and its '
                 'Wrigley Field game-day staff.', ['marketing-coordinator', 'event-planner', 'bartender', 'server']),
    ],
    'career_hubs': [
        hub('loop-business', 'The Loop and the river', ['the-loop', 'river-north', 'west-loop'],
            ['finance', 'legal', 'government', 'transportation', 'energy', 'hospitality'],
            'Trading firms and banks on LaSalle Street, law firms, corporate headquarters along the river and City '
            'Hall.'),
        hub('fulton-market', 'Fulton Market', ['west-loop'], ['technology', 'food', 'business'],
            'Old meatpacking blocks now holding corporate headquarters, tech offices and startups.'),
        hub('medical-district', 'Hospital campuses', ['streeterville', 'little-italy', 'hyde-park'],
            ['healthcare', 'biotech', 'education'], 'Northwestern Medicine in Streeterville, Rush and UI Health in '
            'the Illinois Medical District, and UChicago Medicine on the South Side.'),
        hub('campuses', 'University campuses', ['hyde-park', 'evanston', 'lincoln-park', 'rogers-park'],
            ['education'], 'UChicago, Northwestern, DePaul and Loyola.'),
        hub('lakefront-culture', 'Museums and venues', ['south-loop', 'the-loop', 'streeterville'],
            ['entertainment', 'tourism', 'hospitality', 'education'], 'The Museum Campus, the theater district, '
            'Navy Pier and the hotels around them.'),
    ],
    'climate': {
        'summary': 'Humid continental: long, cold, windy winters with lake-effect snow, a short spring, hot and '
                   'humid summers with thunderstorms, and a crisp, golden autumn. The lake keeps the shore '
                   'cooler in spring and summer.',
        'months': [
            month(32, 18, 11, 'Bitter cold and wind off the lake; subzero snaps and snow most weeks.'),
            month(36, 21, 9, 'Still frozen; the lake edge piles up with ice.'),
            month(47, 30, 11, 'Raw and changeable; a spring storm can still bring heavy snow.'),
            month(59, 40, 12, 'Cool and wet; cold lake breezes along the shore.'),
            month(70, 50, 12, 'Patios and beaches open; it can be 80 inland and 55 by the lake.'),
            month(80, 60, 11, 'Warm and humid; afternoon thunderstorms.'),
            month(85, 66, 10, 'Hottest month; muggy heat waves and crowded beaches.'),
            month(83, 65, 9, 'Hot and humid; the lake is warmest for swimming.'),
            month(76, 57, 9, 'Warm days, cooler nights; the best weather of the year.'),
            month(63, 45, 10, 'Crisp; leaves turn and the first frost arrives.'),
            month(49, 33, 10, 'Grey and windy; the first snow flurries.'),
            month(36, 22, 10, 'Cold, dark and snowy; the Hawk wind arrives.'),
        ],
        'source': CLIMATE,
    },
    'annual_events': [
        event('st-patricks-river', 'St. Patrick\'s Day river dyeing and parade', [3], 'the-loop', 'The river is dyed '
              'bright green on the Saturday before St. Patrick\'s Day, followed by a parade on Columbus Drive.'),
        event('cubs-opening-day', 'Cubs Opening Day', [3, 4], 'lakeview', 'Wrigleyville bars open at dawn for the '
              'first home game, often in snow flurries.'),
        event('blues-fest', 'Chicago Blues Festival', [6], 'the-loop', 'Free blues festival in Millennium Park, '
              'the largest of its kind.'),
        event('printers-row-lit-fest', 'Printers Row Lit Fest', [6], 'south-loop', 'Book tents, author talks and '
              'used-book dealers along Dearborn Street.'),
        event('chicago-pride', 'Chicago Pride Parade and Pride Fest', [6], 'lakeview', 'Northalsted street fest '
              'and a huge Sunday parade through Lakeview.'),
        event('puerto-rican-fest', 'Puerto Rican People\'s Parade and Fiesta Boricua', [6, 9], 'humboldt-park',
              'Parade, music and food in and around Humboldt Park, with flags on every car.'),
        event('grant-park-music-festival', 'Grant Park Music Festival', [6, 7, 8], 'the-loop', 'Free classical '
              'concerts at the Pritzker Pavilion, with picnics on the lawn.'),
        event('lollapalooza', 'Lollapalooza', [7, 8], 'the-loop', 'Four days of rock, pop and EDM across Grant Park '
              'in late July or early August.'),
        event('air-and-water-show', 'Chicago Air and Water Show', [8], 'lincoln-park', 'Jets and stunt planes over '
              'North Avenue Beach, rattling windows all along the lakefront.'),
        event('jazz-fest', 'Chicago Jazz Festival', [8, 9], 'the-loop', 'Free jazz festival in Millennium Park over '
              'Labor Day weekend.'),
        event('mexican-independence-parade', '26th Street Mexican Independence Day Parade', [9], 'little-village',
              'Floats, horses, flags and honking cars on 26th Street around September 16.'),
        event('taste-of-chicago', 'Taste of Chicago', [9], 'the-loop', 'Food stalls from local restaurants in Grant '
              'Park; long a July event, it now usually runs in September.'),
        event('chicago-marathon', 'Chicago Marathon', [10], 'the-loop', 'A flat, fast course through 29 '
              'neighborhoods from Grant Park, with crowds cheering in Pilsen, Chinatown and Boystown.'),
        event('open-house-chicago', 'Open House Chicago', [10], 'the-loop', 'A weekend of free entry to buildings '
              'normally closed to the public, from penthouses to churches.'),
        event('lights-festival', 'Magnificent Mile Lights Festival', [11], 'streeterville', 'A parade and the '
              'lighting of the trees along Michigan Avenue the weekend before Thanksgiving.'),
        event('christkindlmarket', 'Christkindlmarket', [11, 12], 'the-loop', 'German-style Christmas market in '
              'Daley Plaza with mulled wine in collectable boot mugs.'),
        event('zoolights', 'ZooLights', [11, 12, 1], 'lincoln-park', 'Millions of lights across Lincoln Park Zoo on '
              'winter evenings.'),
        event('bears-season', 'Bears football season', [9, 10, 11, 12, 1], 'south-loop', 'Sunday game days, '
              'tailgates in the Soldier Field lots and Monday moods across the city.'),
    ],
    'local_color': [
        color('deep-dish', 'Deep-dish pizza', 'dish', 'A tall, buttery crust baked in a pan, filled with cheese and '
              'sausage and topped with chunky tomato sauce; locals eat it for visitors and occasions more than '
              'every week.', ['pizzeria-uno', 'lou-malnatis-river-north', 'giordanos-rush']),
        color('tavern-style', 'Tavern-style pizza', 'dish', 'The pizza Chicagoans actually eat most: thin, crackly '
              'crust cut into squares ("party cut"), and the corner pieces are fought over.', ['pats-pizza']),
        color('italian-beef', 'Italian beef', 'dish', 'Thin-sliced roast beef soaked in jus on a long roll, topped '
              'with sweet peppers or hot giardiniera; order it "dipped" or "wet" and eat it leaning over the '
              'counter.', ['als-beef-taylor', 'mr-beef', 'portillos-river-north']),
        color('chicago-dog', 'Chicago-style hot dog', 'dish', 'An all-beef dog on a poppy-seed bun "dragged through '
              'the garden": yellow mustard, neon relish, onion, tomato, pickle spear, sport peppers and celery salt. '
              'Never ketchup.', ['portillos-river-north', 'wieners-circle']),
        color('maxwell-street-polish', 'Maxwell Street Polish', 'dish', 'A grilled Polish sausage with grilled '
              'onions and mustard, from the old Maxwell Street market.', ['jims-original', 'rate-field']),
        color('jibarito', 'Jibarito', 'dish', 'A Chicago Puerto Rican invention: steak, garlic mayo, lettuce and '
              'tomato between two flattened fried plantains.', ['papas-cache-sabroso']),
        color('paczki', 'Pączki Day', 'custom', 'On Fat Tuesday, Polish bakeries sell out of rich filled '
              'doughnuts (pączki) from before dawn, and offices fill with boxes of them.', seasons=['winter']),
        color('garrett-mix', 'Chicago Mix popcorn', 'dish', 'Caramel and cheese popcorn mixed in one bag, sold by '
              'Garrett Popcorn shops downtown with lines out the door.'),
        color('malort', 'Malört', 'drink', 'A bitter wormwood liqueur that locals pour for visitors to watch their '
              'faces, then drink themselves as a point of pride.', ['rainbo-club', 'old-town-ale-house']),
        color('old-style', 'Old Style', 'drink', 'The cheap lager on corner-tavern signs and at Wrigley for '
              'decades; tall cans of it signal an old-school bar.', ['murphys-bleachers']),
        color('the-bean', '"The Bean"', 'saying', 'Nobody calls Anish Kapoor\'s Cloud Gate by its name; it is the '
              'Bean, and meeting "at the Bean" is a standard plan downtown.', ['millennium-park']),
        color('dibs', 'Dibs', 'custom', 'After a snowstorm, people who dig out a street parking space claim it '
              'with a lawn chair, a cone or an old ironing board, and moving someone\'s dibs starts feuds.',
              seasons=['winter']),
        color('the-l', '"The L"', 'saying', 'The trains are the L, whether elevated or underground, and lines go by '
              'color; directions are given as "take the Red to Belmont".'),
        color('lake-shore-drive', '"Lake Shore Drive"', 'saying', 'The lakefront highway is still Lake Shore Drive '
              'to locals, officially renamed for Jean Baptiste Point DuSable in 2021, and directions are given '
              'as "the lake is east".'),
        color('the-hawk', '"The Hawk"', 'saying', 'The bitter winter wind off the lake, as in "the Hawk is out '
              'today".', seasons=['winter']),
        color('pop', '"Pop", "Jewels" and "the Ryan"', 'saying', 'Soda is pop, Jewel-Osco is "the Jewels", and '
              'expressways go by names: the Kennedy, the Dan Ryan, the Eisenhower.'),
        color('north-south-side', 'Cubs or Sox', 'custom', 'Baseball loyalty roughly follows the city map: the North '
              'Side for the Cubs, the South Side for the White Sox, and switching sides is not done.',
              ['wrigley-field', 'rate-field'], WARM),
        color('lakefront', 'Lakefront summer', 'custom', 'The first warm weekend, everyone heads to the lake: '
              'beaches, the trail, volleyball and grills along twenty-six miles of mostly public shore.',
              ['north-avenue-beach', 'montrose-beach', 'lakefront-trail', 'promontory-point'], ['summer']),
        color('cubs', 'Chicago Cubs', 'team', 'The North Side baseball team at Wrigley Field, whose 2016 World '
              'Series ended a 108-year wait; fans sing "Go Cubs Go" after wins and fly a W flag.',
              ['wrigley-field', 'murphys-bleachers'], WARM),
        color('white-sox', 'Chicago White Sox', 'team', 'The South Side baseball team in Bridgeport, with a '
              'working-class, no-nonsense fan base.', ['rate-field'], WARM),
        color('bears', 'Chicago Bears', 'team', '"Da Bears": the NFL team at Soldier Field, followed with grim '
              'devotion through long, cold seasons.', ['soldier-field'], ['fall', 'winter']),
        color('bulls-blackhawks', 'Bulls and Blackhawks', 'team', 'The basketball and hockey teams share the '
              'United Center; the Jordan-era Bulls and the 2010s Blackhawks are still talked about.',
              ['united-center'], ['fall', 'winter', 'spring']),
        color('blues-and-improv', 'Blues and improv', 'other', 'Chicago blues came up from the Delta through the '
              'South Side, and improv comedy grew up here too; both are still played nightly.',
              ['kingston-mines', 'buddy-guys-legends', 'second-city']),
    ],
    'prices': [
        price('coffee', 'Coffee', 2.5, 4, 'a cup'),
        price('latte', 'Latte', 5, 7),
        price('breakfast-sandwich', 'Breakfast sandwich', 6, 10),
        price('cheap-lunch', 'Cheap lunch', 12, 18),
        price('dinner', 'Mid-range dinner', 35, 60, 'for one'),
        price('beer', 'Pint of beer', 7, 10, 'a pint'),
        price('cocktail', 'Cocktail', 14, 18),
        price('groceries', 'Groceries', 75, 120, 'a week, one person'),
        price('transit', 'CTA fare', 2.25, 2.5, 'one ride, bus or L'),
        price('rideshare', 'Rideshare across town', 15, 32),
        price('movie', 'Movie ticket', 12, 18),
        price('gym', 'Gym membership', 30, 70, 'a month'),
        price('deep-dish', 'Deep-dish pizza', 25, 45, 'a large to share'),
        price('italian-beef', 'Italian beef sandwich', 9, 14),
        price('chicago-dog', 'Chicago-style hot dog', 4, 7),
    ],
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
