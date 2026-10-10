"""Curated New Orleans data. Run `python scripts/world/new_orleans.py` to rewrite the shipped JSON."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'cities' / 'new-orleans.json'
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


def college(id, name, type, hood, size, known_for):
    return {'id': id, 'name': name, 'type': type, 'neighborhood': hood, 'size': size, 'known_for': known_for,
            'source': S}


def employer(id, name, sector, hood, size, summary, careers):
    return {'id': id, 'name': name, 'sector': sector, 'neighborhood': hood, 'size': size, 'summary': summary,
            'careers': careers, 'source': S}


def hub(id, name, hoods, sectors, summary):
    return {'id': id, 'name': name, 'neighborhoods': hoods, 'sectors': sectors, 'summary': summary, 'source': S}


def line(id, name, kind, summary):
    return {'id': id, 'name': name, 'kind': kind, 'summary': summary, 'source': S}


def event(id, name, months, hood, summary):
    return {'id': id, 'name': name, 'months': months, 'neighborhood': hood, 'summary': summary, 'source': S}


def holiday(id, name, kind, summary, **rule):
    return {'id': id, 'name': name, 'kind': kind, 'summary': summary, **rule}


def color(id, name, kind, summary, places=(), seasons=()):
    return {'id': id, 'name': name, 'kind': kind, 'summary': summary, 'places': list(places),
            'seasons': list(seasons), 'source': S}


def price(id, item, low, high, per=''):
    return {'id': id, 'item': item, 'low': low, 'high': high, 'per': per, 'source': S}


ALL = ['solo', 'friends', 'date', 'family']
ADULT = ['solo', 'friends', 'date']
DAY = ['morning', 'afternoon']
OPEN = ['morning', 'afternoon', 'evening']
DINNER = ['evening']
NIGHT = ['evening', 'late']
LATE = ['afternoon', 'evening', 'late']
WARM = ['spring', 'summer', 'fall']
SNOBALL = ['spring', 'summer']
# Streetcars, buses, ferry and bike share each neighbourhood can use.
CORE = ['rta-bus', 'blue-bikes']

CITY = {
    'schema_version': 1, 'id': 'new-orleans', 'name': 'New Orleans', 'region': 'Louisiana', 'country': 'US',
    'timezone': 'America/Chicago',
    'aliases': ['NOLA', 'The Big Easy', 'Crescent City', 'New Orleans, LA', 'Nawlins'],
    'summary': 'A port city in a bend of the Mississippi, below sea level behind its levees, where Creole and '
               'Cajun cooking, brass bands, Carnival krewes, second lines and a calendar packed with festivals '
               'shape ordinary life as much as any job does.',
    'lat': 29.95, 'lon': -90.07,
    'speeds': {'walk': 4.5, 'car': 26, 'rideshare': 26, 'bus': 12, 'streetcar': 11, 'ferry': 10,
               'bike-share': 13},
    # Rough heritage weights for residents' names (estimates, not census figures). East Asian stands in for the
    # Vietnamese community of New Orleans East; Hispanic includes the large Honduran community.
    'names': {'mix': {'black-american': 6, 'anglo': 3, 'hispanic': 0.9, 'italian': 0.5, 'irish': 0.4,
                       'east-asian': 0.4, 'caribbean': 0.2, 'jewish': 0.2, 'arabic': 0.2, 'south-asian': 0.1}},
    'sources': {
        S: {'kind': 'curated', 'title': 'New Orleans places and neighborhoods written for Prospero Companion',
            'license': 'CC0-1.0', 'retrieved': '2026-10-10',
            'note': 'Well-known public places, institutions, festivals and employers from general knowledge, '
                    'covering Orleans Parish plus Metairie in neighbouring Jefferson Parish. Businesses open and '
                    'close, festival dates move and rents change: treat this as a snapshot for fiction. Rents are '
                    'rounded estimates of typical asking ranges, not listings. Coordinates are approximate '
                    'neighborhood centers.'},
        CLIMATE: {'kind': 'curated', 'title': 'Approximate monthly climate for New Orleans (Louis Armstrong '
                  'International Airport area)', 'license': 'CC0-1.0', 'retrieved': '2026-10-10',
                  'note': 'Rounded values in line with NOAA 1991-2020 normals; refresh with scripts/world when '
                          'network access to NOAA is available. Hurricane season runs June to November.'},
    },
    'neighborhoods': [
        hood('french-quarter', 'French Quarter', 'The Vieux Carré: cast-iron balconies, courtyards and Creole '
             'townhouses around Jackson Square, with Bourbon Street\'s neon on one side and quiet residential '
             'blocks of locals toward Esplanade.', ['historic', 'nightlife', 'touristy', 'music', 'architecture'],
             29.958, -90.065, 'very-high', ([1300, 1800], [1500, 2300], [2100, 3200]),
             ['creole-townhouse', 'apartment', 'condo'], 'high', ['riverfront', 'rampart', 'canal', 'ferry', *CORE]),
        hood('marigny', 'Faubourg Marigny', 'Colourful Creole cottages downriver from the Quarter, with Frenchmen '
             'Street\'s jazz clubs at one end and St. Claude Avenue\'s bars and galleries at the other.',
             ['music', 'nightlife', 'lgbtq-friendly', 'artsy', 'historic'], 29.964, -90.054, 'high',
             ([1100, 1500], [1300, 1800], [1700, 2500]), ['creole-cottage', 'shotgun', 'apartment'], 'high',
             ['rampart', *CORE]),
        hood('bywater', 'Bywater', 'Painted shotgun houses, murals and a riverfront park, home to artists, '
             'musicians and a few too many new short-term rentals, with backyard wine bars and po-boy corners.',
             ['artsy', 'quirky', 'riverfront', 'music'], 29.963, -90.040, 'high',
             ([1050, 1450], [1250, 1750], [1650, 2400]), ['shotgun', 'creole-cottage', 'warehouse-loft'],
             'medium', CORE),
        hood('treme', 'Tremé', 'Among the oldest Black neighborhoods in the country, home of Congo Square, brass '
             'bands, Sunday second lines and Mardi Gras Indian gangs, with Creole cottages along leafy streets.',
             ['historic', 'music', 'black-culture', 'second-lines'], 29.966, -90.071, 'mid',
             ([950, 1300], [1100, 1500], [1400, 2000]), ['creole-cottage', 'shotgun', 'double'], 'high',
             ['rampart', 'canal', *CORE]),
        hood('seventh-ward', 'Seventh Ward', 'Historically the heart of Creole of colour New Orleans, home to '
             'generations of plasterers, carpenters and musicians, with fried chicken counters, Bayou Road '
             'shops and the Claiborne Avenue underpass where Mardi Gras Indians meet.',
             ['historic', 'creole', 'working-class', 'black-culture'], 29.976, -90.060, 'low',
             ([800, 1100], [950, 1300], [1200, 1700]), ['shotgun', 'double', 'creole-cottage'], 'medium', CORE),
        hood('mid-city', 'Mid-City', 'A big, mixed neighborhood of raised doubles and bungalows between Canal '
             'Street and City Park, with the Canal streetcar, old Creole-Italian restaurants and the hospital '
             'district at its downtown edge.', ['family', 'food', 'park', 'neighbourly'], 29.975, -90.095, 'mid',
             ([1000, 1350], [1150, 1600], [1500, 2100]), ['double', 'raised-cottage', 'apartment'], 'medium',
             ['canal', 'jet', *CORE]),
        hood('bayou-st-john', 'Bayou St. John', 'Faubourg St. John and the Esplanade Ridge: big old houses and '
             'oak-shaded streets on a slow bayou where people paddle, picnic and walk to Jazz Fest at the Fair '
             'Grounds.', ['leafy', 'historic', 'waterside', 'festival'], 29.981, -90.087, 'high',
             ([1050, 1400], [1250, 1700], [1650, 2300]), ['raised-cottage', 'double', 'single-family'], 'medium',
             ['canal', *CORE]),
        hood('cbd', 'CBD and Warehouse District', 'Office towers along Poydras, the Superdome and Smoothie King '
             'Center, museums and galleries in converted warehouses on Julia Street, convention hotels and '
             'the ferry at the foot of Canal Street.', ['business', 'museums', 'sports', 'central', 'arts'],
             29.948, -90.070, 'high', ([1300, 1800], [1550, 2300], [2100, 3200]),
             ['apartment-tower', 'warehouse-loft', 'condo'], 'high',
             ['st-charles', 'canal', 'riverfront', 'rampart', 'ferry', 'jet', *CORE]),
        hood('lower-garden-district', 'Lower Garden District', 'Faded Greek Revival mansions split into '
             'apartments around Coliseum Square, with the young, bar-hopping stretch of Magazine Street and the '
             'film stages by the river.', ['young-professional', 'bars', 'historic', 'shopping'], 29.938, -90.075,
             'mid', ([1150, 1500], [1300, 1800], [1700, 2500]), ['converted-mansion', 'apartment', 'double'],
             'high', ['st-charles', *CORE]),
        hood('garden-district', 'Garden District', 'Grand antebellum houses behind iron fences and magnolias, '
             'Commander\'s Palace across from Lafayette Cemetery, and the St. Charles streetcar rattling under '
             'the oaks.', ['affluent', 'historic', 'leafy', 'architecture'], 29.928, -90.084, 'very-high',
             ([1250, 1700], [1450, 2100], [2000, 3000]), ['mansion', 'double', 'apartment'], 'high',
             ['st-charles', *CORE]),
        hood('irish-channel', 'Irish Channel', 'Shotgun doubles between Magazine Street and the river, built for '
             'Irish and German dockworkers, now a mix of old families and newcomers, with corner bars and the '
             'cabbage-throwing St. Patrick\'s parade.', ['historic', 'bars', 'neighbourly', 'riverfront'],
             29.921, -90.079, 'high', ([1100, 1450], [1250, 1700], [1700, 2400]), ['shotgun', 'double'],
             'medium', CORE),
        hood('central-city', 'Central City', 'A historic Black neighborhood around Oretha Castle Haley '
             'Boulevard, the old Dryades Street shopping strip, now home to arts centers, the Jazz Market and '
             'Uptown\'s Super Sunday Indian gathering.', ['historic', 'black-culture', 'changing', 'arts'],
             29.938, -90.088, 'low', ([850, 1150], [1000, 1350], [1250, 1750]), ['shotgun', 'double', 'apartment'],
             'medium', ['st-charles', *CORE]),
        hood('uptown', 'Uptown', 'Oak-lined avenues between St. Charles and the river: Tulane and Loyola, '
             'Audubon Park and Zoo, snowball stands, Tipitina\'s and the parade route that turns into a '
             'neighbourhood picnic every Carnival.', ['leafy', 'students', 'family', 'music', 'parades'],
             29.920, -90.105, 'high', ([1100, 1450], [1250, 1750], [1650, 2500]),
             ['double', 'single-family', 'apartment', 'student-housing'], 'medium', ['st-charles', *CORE]),
        hood('carrollton', 'Carrollton and Riverbend', 'Where the St. Charles streetcar turns onto Carrollton '
             'Avenue: Oak Street\'s shops and music bars, the levee path, student renters and old Creole '
             'cottages near the river bend.', ['students', 'music', 'riverfront', 'neighbourly'], 29.944, -90.128,
             'mid', ([1000, 1350], [1150, 1550], [1500, 2100]), ['double', 'shotgun', 'apartment'], 'medium',
             ['st-charles', *CORE]),
        hood('freret', 'Freret', 'A once-shuttered commercial street near the universities, revived as a strip '
             'of burger joints, cocktail bars and po-boy counters with a big spring street festival.',
             ['food', 'students', 'bars', 'changing'], 29.932, -90.106, 'mid',
             ([1000, 1300], [1150, 1550], [1500, 2100]), ['double', 'shotgun'], 'medium', CORE),
        hood('broadmoor', 'Broadmoor and Gert Town', 'A low-lying, close-knit neighborhood that famously '
             'organised to rebuild itself after Katrina, next to Gert Town and the Xavier University campus.',
             ['family', 'community', 'affordable', 'students'], 29.946, -90.106, 'mid',
             ([900, 1200], [1050, 1400], [1350, 1850]), ['double', 'single-family', 'raised-cottage'], 'medium',
             CORE),
        hood('gentilly', 'Gentilly', 'A middle-class, majority-Black district of ranch houses and 1920s bungalows '
             'on the ridge toward the lake, home to Dillard, SUNO and the University of New Orleans.',
             ['family', 'suburban', 'black-culture', 'campus'], 30.005, -90.060, 'mid',
             ([850, 1100], [950, 1300], [1200, 1650]), ['single-family', 'bungalow', 'ranch'], 'low', ['rta-bus']),
        hood('lakeview', 'Lakeview', 'Quiet lakeside streets of raised new houses rebuilt after the levee '
             'breaches flooded it in 2005, with a small main street on Harrison Avenue and the seawall on Lake '
             'Pontchartrain.', ['family', 'quiet', 'suburban', 'lakefront'], 30.005, -90.105, 'high',
             ([1000, 1300], [1200, 1600], [1600, 2200]), ['single-family', 'raised-house', 'apartment'], 'low',
             ['rta-bus']),
        hood('algiers-point', 'Algiers Point', 'A small-town corner of the West Bank, a five-minute ferry ride '
             'from the Quarter, with Victorian cottages, a levee view of the skyline and a couple of beloved '
             'bars.', ['quiet', 'historic', 'riverfront', 'small-town'], 29.954, -90.053, 'mid',
             ([950, 1250], [1100, 1500], [1450, 2000]), ['victorian', 'shotgun', 'creole-cottage'], 'medium',
             ['ferry', 'rta-bus']),
        hood('lower-ninth-ward', 'Lower Ninth Ward and Holy Cross', 'Downriver past the Industrial Canal: Holy '
             'Cross\'s steamboat houses on the levee, Fats Domino\'s home and the still-rebuilding blocks and '
             'wetlands of the Lower Ninth.', ['historic', 'resilient', 'riverfront', 'community'], 29.962, -90.015,
             'low', ([750, 1000], [850, 1150], [1050, 1450]), ['single-family', 'shotgun', 'raised-house'], 'low',
             ['rta-bus']),
        hood('new-orleans-east', 'New Orleans East', 'Sprawling suburban-style subdivisions east of the Industrial '
             'Canal, a large Black middle class and, in Village de l\'Est, the Vietnamese community around Mary '
             'Queen of Vietnam with its bakeries and backyard gardens.', ['suburban', 'vietnamese', 'family',
             'black-culture'], 30.030, -89.960, 'low', ([750, 1000], [850, 1150], [1050, 1450]),
             ['single-family', 'ranch', 'apartment'], 'low', ['rta-bus']),
        hood('metairie', 'Metairie', 'The big suburb just over the parish line in Jefferson Parish: ranch '
             'houses, Lakeside mall, the Saints\' training base, Ochsner\'s main campus and its own Carnival '
             'parades.', ['suburban', 'family', 'shopping'], 29.990, -90.150, 'mid',
             ([950, 1250], [1100, 1450], [1400, 1900]), ['single-family', 'ranch', 'apartment'], 'low', ['jet']),
    ],
    'transit': [
        line('st-charles', 'St. Charles streetcar', 'streetcar', 'The green, wooden-seated streetcars in service '
             'since the 1920s, running from Canal Street up St. Charles Avenue past the mansions, universities '
             'and parade route to Carrollton.'),
        line('canal', 'Canal streetcar', 'streetcar', 'Red streetcars from the river up Canal Street to the '
             'cemeteries, with a branch up Carrollton Avenue to City Park and the art museum.'),
        line('riverfront', 'Riverfront streetcar', 'streetcar', 'A short red line along the river from the '
             'French Market past the aquarium to the Convention Center.'),
        line('rampart', 'Rampart-St. Claude streetcar', 'streetcar', 'Red streetcars from the Union Passenger '
             'Terminal along Rampart Street on the edge of the Quarter and Tremé to Elysian Fields.'),
        line('ferry', 'Algiers Point ferry', 'ferry', 'The Canal Street ferry across the Mississippi to Algiers '
             'Point, a few minutes each way and a cheap river view.'),
        line('rta-bus', 'RTA buses', 'bus', 'The New Orleans Regional Transit Authority bus network, the main way '
             'around for people without cars outside the streetcar corridors.'),
        line('jet', 'Jefferson Transit (JeT)', 'bus', 'Jefferson Parish buses linking Metairie to Mid-City and '
             'downtown New Orleans.'),
        line('blue-bikes', 'Blue Bikes', 'bike-share', 'The city\'s electric-assist bike share, docked across '
             'the older, flat neighborhoods near the river.'),
    ],
    'places': [
        # French Quarter
        place('jackson-square', 'Jackson Square', 'landmark', 'french-quarter', 'The old Place d\'Armes in front '
              'of the cathedral, ringed by fortune tellers, painters hanging work on the iron fence and brass '
              'bands busking for tips.', ['iconic', 'street-performers', 'historic', 'walk'], 'free', 'outdoor',
              ALL, OPEN),
        place('st-louis-cathedral', 'St. Louis Cathedral', 'landmark', 'french-quarter', 'The triple-spired '
              'white cathedral over Jackson Square, the oldest continuously active Catholic cathedral in the '
              'United States, with Mass, weddings and free visits between services.',
              ['church', 'iconic', 'architecture'], 'free', 'indoor', ALL, DAY),
        place('cafe-du-monde', 'Café du Monde', 'cafe', 'french-quarter', 'Open-air coffee stand at the French '
              'Market since 1862, serving beignets under drifts of powdered sugar and café au lait with chicory.',
              ['beignets', 'chicory-coffee', 'iconic'], '$', 'mixed', ALL, OPEN, cuisine='beignets'),
        place('french-market', 'French Market', 'market', 'french-quarter', 'Colonnaded market sheds along the '
              'river with a flea market, food stalls, pralines and hot sauce, and the Creole Tomato Festival in '
              'June.', ['market', 'flea-market', 'food'], '$', 'mixed', ALL, DAY),
        place('preservation-hall', 'Preservation Hall', 'venue', 'french-quarter', 'A worn, candlelit room on St. '
              'Peter Street where traditional New Orleans jazz has been played nightly since 1961; short sets, '
              'mostly standing room, no bar.', ['jazz', 'live-music', 'historic', 'iconic'], '$$', 'indoor',
              ['solo', 'date', 'friends', 'family'], ['evening']),
        place('bourbon-street', 'Bourbon Street', 'nightlife', 'french-quarter', 'Thirteen blocks of neon, '
              'balcony bead-throwing, cover bands, strip clubs and drinks in plastic go-cups; locals mostly '
              'pass through on the way somewhere else.', ['party', 'touristy', 'neon', 'go-cups'], '$$',
              'outdoor', ['friends'], NIGHT),
        place('cabildo', 'The Cabildo', 'museum', 'french-quarter', 'Louisiana State Museum in the Spanish colonial '
              'seat of government where the Louisiana Purchase was signed, with Napoleon\'s death mask.',
              ['history', 'rainy-day'], '$', 'indoor', ALL, DAY),
        place('hnoc', 'The Historic New Orleans Collection', 'museum', 'french-quarter', 'Free galleries on '
              'Royal and Chartres streets covering three centuries of the city, with maps, paintings and '
              'rotating exhibitions.', ['history', 'free', 'rainy-day'], 'free', 'indoor', ALL, DAY),
        place('galatoires', 'Galatoire\'s', 'restaurant', 'french-quarter', 'Bourbon Street Creole grand dame '
              'since 1905, where jacketed regulars hold long Friday lunches that run into the evening.',
              ['creole', 'old-line', 'friday-lunch', 'special-occasion'], '$$$$', 'indoor',
              ['date', 'friends', 'family'], ['afternoon', 'evening'], cuisine='creole'),
        place('antoines', 'Antoine\'s', 'restaurant', 'french-quarter', 'Founded in 1840, the city\'s oldest '
              'family-run restaurant, with a warren of dining rooms hung with Carnival memorabilia and the '
              'original oysters Rockefeller.', ['creole', 'historic', 'special-occasion'], '$$$$', 'indoor',
              ['date', 'family'], ['afternoon', 'evening'], cuisine='creole'),
        place('acme-oyster-house', 'Acme Oyster House', 'restaurant', 'french-quarter', 'Iberville Street oyster '
              'bar with shuckers working the marble counter and a line out the door for chargrilled oysters.',
              ['oysters', 'seafood', 'line'], '$$', 'indoor', ALL, ['afternoon', 'evening'], cuisine='seafood'),
        place('napoleon-house', 'Napoleon House', 'bar', 'french-quarter', 'Crumbling 200-year-old building on '
              'Chartres Street with classical music, Pimm\'s Cups and warm muffulettas.',
              ['pimms-cup', 'muffuletta', 'historic'], '$$', 'mixed', ADULT, ['afternoon', 'evening'],
              cuisine='creole-italian'),
        place('lafittes-blacksmith-shop', 'Lafitte\'s Blacksmith Shop', 'bar', 'french-quarter', 'Candlelit bar '
              'in an eighteenth-century cottage at the quiet end of Bourbon, with a piano player and purple '
              'daiquiris.', ['historic', 'candlelit', 'piano'], '$$', 'indoor', ADULT, NIGHT),
        place('pat-obriens', 'Pat O\'Brien\'s', 'bar', 'french-quarter', 'Home of the rum Hurricane, with a '
              'flaming fountain in the courtyard and duelling pianos in the back room.',
              ['hurricanes', 'piano-bar', 'courtyard'], '$$', 'mixed', ['friends', 'date'], NIGHT),
        place('cafe-lafitte-in-exile', 'Café Lafitte in Exile', 'bar', 'french-quarter', 'One of the oldest gay '
              'bars in the country, with a wraparound balcony over Bourbon that fills during Southern '
              'Decadence.', ['lgbtq', 'balcony', 'historic'], '$', 'indoor', ['friends', 'solo', 'date'], LATE),
        place('coops-place', 'Coop\'s Place', 'restaurant', 'french-quarter', 'Dim, loud Decatur Street bar '
              'kitchen serving rabbit and sausage jambalaya and fried chicken late into the night.',
              ['cajun', 'late-night', 'dive'], '$', 'indoor', ['friends', 'solo'], LATE, cuisine='cajun'),
        place('woldenberg-park', 'Woldenberg Park and the Moonwalk', 'park', 'french-quarter', 'Riverfront lawns '
              'and a boardwalk where people watch ships and the Algiers ferry, and where French Quarter Fest '
              'puts its biggest stages.', ['riverfront', 'walk', 'views'], 'free', 'outdoor', ALL, OPEN),
        place('steamboat-natchez', 'Steamboat Natchez', 'attraction', 'french-quarter', 'A sternwheeler with a '
              'steam calliope offering harbor cruises and evening jazz dinner cruises from the Toulouse Street '
              'wharf.', ['river', 'cruise', 'jazz'], '$$$', 'mixed', ['family', 'date', 'friends'],
              ['afternoon', 'evening']),
        place('jazz-museum', 'New Orleans Jazz Museum', 'museum', 'french-quarter', 'Museum in the Old U.S. Mint on '
              'Esplanade with instruments, recordings and a performance hall; the Satchmo SummerFest stage sits '
              'on its lawn.', ['jazz', 'music', 'rainy-day', 'history'], '$', 'indoor', ALL, DAY),
        place('royal-street', 'Royal Street galleries and antiques', 'shopping', 'french-quarter', 'Blocks of '
              'antique dealers, galleries and street musicians, closed to cars by day on the busiest stretch.',
              ['antiques', 'galleries', 'buskers', 'walk'], '$$', 'outdoor', ALL, DAY),
        place('faulkner-house-books', 'Faulkner House Books', 'shopping', 'french-quarter', 'Tiny bookshop in Pirate '
              'Alley in the house where William Faulkner lived in 1925.', ['books', 'literary', 'small'], '$',
              'indoor', ['solo', 'date'], DAY),
        # Faubourg Marigny
        place('frenchmen-street', 'Frenchmen Street', 'nightlife', 'marigny', 'Three blocks of music clubs where '
              'brass bands play on the corner and you can hear jazz, funk and blues through every open door.',
              ['live-music', 'jazz', 'brass-bands', 'locals'], '$', 'mixed', ['friends', 'date', 'solo'], NIGHT),
        place('spotted-cat', 'The Spotted Cat Music Club', 'bar', 'marigny', 'Small, packed, cash-only club on '
              'Frenchmen with swing and trad jazz bands and couples dancing in the narrow space before the bar.',
              ['jazz', 'swing-dancing', 'cash-only'], '$', 'indoor', ['friends', 'date', 'solo'], LATE),
        place('snug-harbor', 'Snug Harbor Jazz Bistro', 'venue', 'marigny', 'Frenchmen\'s sit-down modern jazz room, '
              'with two seated sets a night upstairs and a steak-and-burger dining room below.',
              ['jazz', 'seated', 'dinner'], '$$$', 'indoor', ['date', 'solo', 'friends'], NIGHT),
        place('dba-new-orleans', 'd.b.a.', 'venue', 'marigny', 'Long, dark bar with a deep beer and whiskey list and '
              'a stage for brass bands, funk and blues most nights.', ['live-music', 'beer', 'whiskey'], '$$',
              'indoor', ['friends', 'date', 'solo'], LATE),
        place('frenchmen-art-market', 'Frenchmen Art Market', 'market', 'marigny', 'Evening open-air market of '
              'local artists\' prints, jewellery and oddities under string lights between the clubs.',
              ['art', 'night-market', 'local-makers'], '$$', 'outdoor', ADULT, NIGHT),
        place('washington-square-park', 'Washington Square Park', 'park', 'marigny', 'Fenced green square at the '
              'end of Frenchmen with dog walkers, picnics and the odd festival stage.',
              ['dogs', 'picnic', 'neighbourhood'], 'free', 'outdoor', ALL, OPEN),
        place('cafe-rose-nicaud', 'Café Rose Nicaud', 'cafe', 'marigny', 'Frenchmen Street coffeehouse named for '
              'an enslaved woman who bought her freedom selling coffee in the French Market, with breakfast and '
              'vegetarian lunches.', ['coffee', 'breakfast', 'history'], '$', 'indoor', ALL, DAY, cuisine='coffee'),
        place('buffas', 'Buffa\'s', 'restaurant', 'marigny', 'Esplanade Avenue bar and back room with red beans, '
              'burgers and piano jazz, open around the clock for musicians coming off gigs.',
              ['red-beans', 'late-night', 'piano', 'dive'], '$', 'indoor', ['friends', 'solo'],
              ['morning', 'afternoon', 'evening', 'late'], cuisine='creole'),
        place('genes-po-boys', 'Gene\'s Po-Boys', 'restaurant', 'marigny', 'The hot-pink corner building at '
              'Elysian Fields and St. Claude, known for hot sausage po-boys and daiquiris at any hour.',
              ['po-boys', 'daiquiris', 'late-night'], '$', 'indoor', ['friends', 'solo'],
              ['afternoon', 'evening', 'late'], cuisine='po-boys'),
        place('marigny-opera-house', 'Marigny Opera House', 'venue', 'marigny', 'A deconsecrated 1850s church used '
              'for chamber music, dance and small festival shows under its high ceilings.',
              ['classical', 'dance', 'historic'], '$$', 'indoor', ['date', 'solo', 'friends'], ['evening']),
        place('nola-boulder-lounge', 'New Orleans Boulder Lounge', 'fitness', 'marigny', 'Bouldering gym in a '
              'St. Claude Avenue warehouse with yoga classes and an after-work crowd of climbers.',
              ['climbing', 'bouldering', 'yoga'], '$$', 'indoor', ['solo', 'friends', 'date'],
              ['morning', 'afternoon', 'evening']),
        # Bywater
        place('crescent-park', 'Crescent Park', 'park', 'bywater', 'Long riverside park reached over the rusty '
              'arched "Rusty Rainbow" bridge, with wharf sheds, a dog run and skyline views back to the CBD.',
              ['riverfront', 'running', 'dogs', 'views'], 'free', 'outdoor', ALL, OPEN),
        place('bacchanal', 'Bacchanal Wine', 'bar', 'bywater', 'Wine shop with a ramshackle backyard where you '
              'pick a bottle and cheese inside, then sit under the lights to small plates and live jazz.',
              ['wine', 'backyard', 'live-music'], '$$', 'outdoor', ['date', 'friends'], LATE,
              cuisine='mediterranean'),
        place('elizabeths', 'Elizabeth\'s', 'restaurant', 'bywater', 'Upstairs-downstairs neighbourhood brunch spot '
              'near the levee, famous for praline bacon and its "Real Food Done Real Good" sign.',
              ['brunch', 'praline-bacon', 'local'], '$$', 'indoor', ALL, DAY, cuisine='creole'),
        place('the-joint', 'The Joint', 'restaurant', 'bywater', 'Smokehouse in a Mazant Street cottage with '
              'ribs, pulled pork and peanut butter pie on a back patio.', ['barbecue', 'patio', 'casual'], '$$',
              'mixed', ALL, ['afternoon', 'evening'], cuisine='barbecue'),
        place('saturn-bar', 'Saturn Bar', 'bar', 'bywater', 'St. Claude Avenue dive decorated with decades of junk '
              'art, with DJs, local bands and a crowd of artists and musicians.',
              ['dive-bar', 'art', 'live-music'], '$', 'indoor', ['friends', 'solo'], NIGHT),
        place('pizza-delicious', 'Pizza Delicious', 'restaurant', 'bywater', 'New York-style pizza by the slice '
              'on Piety Street, grown from a once-a-week pop-up into a neighbourhood hangout.',
              ['pizza', 'casual', 'patio'], '$', 'mixed', ALL, ['afternoon', 'evening'], cuisine='pizza'),
        place('bywater-bakery', 'Bywater Bakery', 'cafe', 'bywater', 'Neighbourhood bakery on Dauphine Street for '
              'coffee, king cakes in Carnival and a bulletin board of local goings-on, with music on weekends.',
              ['bakery', 'king-cake', 'coffee', 'local'], '$', 'indoor', ALL, DAY, cuisine='bakery'),
        place('parleaux-beer-lab', 'Parleaux Beer Lab', 'bar', 'bywater', 'Small brewery with a big backyard of '
              'picnic tables, food pop-ups and dogs.', ['brewery', 'backyard', 'dogs'], '$$', 'mixed',
              ['friends', 'date', 'solo'], ['afternoon', 'evening']),
        place('euclid-records', 'Euclid Records', 'shopping', 'bywater', 'Two floors of new and used vinyl heavy '
              'on local jazz, funk and bounce, with in-store sets during festival season.',
              ['records', 'music', 'local'], '$', 'indoor', ['solo', 'friends'], ['afternoon']),
        place('stallings-st-claude', 'Stallings St. Claude Recreation Center', 'fitness', 'bywater', 'City-run '
              'recreation center with a pool, gym and youth leagues on St. Claude Avenue.',
              ['pool', 'gym', 'rec-center'], 'free', 'indoor', ALL, ['morning', 'afternoon', 'evening']),
        # Tremé
        place('congo-square', 'Congo Square in Louis Armstrong Park', 'park', 'treme', 'The plaza where enslaved '
              'and free people of African descent gathered on Sundays to drum and dance, now inside Armstrong Park '
              'with its lagoon and statues of musicians.', ['history', 'drumming', 'black-history'], 'free',
              'outdoor', ALL, DAY),
        place('backstreet-museum', 'Backstreet Cultural Museum', 'museum', 'treme', 'Small museum of Mardi Gras '
              'Indian suits, Baby Dolls, Skull and Bone gang costumes and social aid and pleasure club regalia.',
              ['mardi-gras-indians', 'black-history', 'costumes'], '$', 'indoor', ALL, DAY),
        place('st-augustine-church', 'St. Augustine Church', 'landmark', 'treme', 'Built in 1841, one of the oldest '
              'Black Catholic parishes in the country, with the Tomb of the Unknown Slave beside it and a gospel '
              'Mass on Sundays.', ['church', 'history', 'black-history'], 'free', 'indoor', ALL, DAY),
        place('dooky-chase', 'Dooky Chase\'s Restaurant', 'restaurant', 'treme', 'Leah Chase\'s Creole restaurant, '
              'a civil rights meeting place hung with Black art, known for its lunch buffet and Holy Thursday '
              'gumbo z\'herbes.', ['creole', 'history', 'lunch-buffet'], '$$', 'indoor', ALL, ['afternoon'],
              cuisine='creole'),
        place('willie-maes', 'Willie Mae\'s Scotch House', 'restaurant', 'treme', 'Corner restaurant on St. Ann '
              'Street with a cult following for its wet-battered fried chicken and butter beans.',
              ['fried-chicken', 'soul-food', 'line'], '$', 'indoor', ALL, ['morning', 'afternoon'],
              cuisine='soul-food'),
        place('mahalia-jackson-theater', 'Mahalia Jackson Theater', 'venue', 'treme', 'The performing arts hall in '
              'Armstrong Park, home to the opera and ballet seasons and touring shows.',
              ['theater', 'opera', 'ballet'], '$$$', 'indoor', ['date', 'family', 'friends'], ['evening']),
        place('kermits-mother-in-law', 'Kermit\'s Tremé Mother-in-Law Lounge', 'bar', 'treme', 'Trumpeter Kermit '
              'Ruffins\'s lounge in Ernie K-Doe\'s old bar on Claiborne, with murals outside and Kermit often '
              'cooking for the crowd.', ['live-music', 'trumpet', 'murals'], '$', 'indoor',
              ['friends', 'solo'], NIGHT),
        place('noaam', 'New Orleans African American Museum', 'museum', 'treme', 'Museum in the Meilleur-Goldthwaite '
              'House and its grounds telling the story of Black New Orleans, from Tremé\'s free people of colour '
              'onward.', ['history', 'black-history', 'art'], '$', 'mixed', ALL, DAY),
        place('lafitte-greenway', 'Lafitte Greenway', 'trail', 'treme', 'Paved path along an old canal and rail '
              'line from Armstrong Park to Mid-City, with ball fields and Blue Bikes along the way.',
              ['cycling', 'running', 'walk'], 'free', 'outdoor', ALL, OPEN),
        place('treme-recreation-center', 'Tremé Recreation Community Center', 'fitness', 'treme', 'City recreation '
              'center with an indoor pool, gym floor and after-school programs in the heart of Tremé.',
              ['pool', 'gym', 'rec-center'], 'free', 'indoor', ALL, ['morning', 'afternoon', 'evening']),
        # Seventh Ward
        place('lil-dizzys', 'Li\'l Dizzy\'s Café', 'restaurant', 'seventh-ward', 'Esplanade Avenue Creole soul '
              'kitchen run by the Baquet family, with a weekday lunch buffet, fried chicken and trout Baquet.',
              ['creole', 'soul-food', 'breakfast'], '$', 'indoor', ALL, DAY, cuisine='creole'),
        place('mchardys', 'McHardy\'s Chicken & Fixin\'', 'restaurant', 'seventh-ward', 'Takeout counter on Broad '
              'Street whose fried chicken boxes turn up at every party, wake and second line.',
              ['fried-chicken', 'takeout', 'local'], '$', 'indoor', ['family', 'friends', 'solo'],
              ['afternoon', 'evening'], cuisine='fried-chicken'),
        place('pagoda-cafe', 'Pagoda Café', 'cafe', 'seventh-ward', 'Coffee, breakfast tacos and lemonade from a '
              'pagoda-roofed former laundry with a shady patio near Bayou Road.', ['coffee', 'patio', 'breakfast'],
              '$', 'outdoor', ALL, DAY, cuisine='cafe'),
        place('community-book-center', 'Community Book Center', 'shopping', 'seventh-ward', 'Black-owned bookstore '
              'on Bayou Road since 1983, a gathering place for readings and conversation.',
              ['books', 'black-owned', 'community'], '$', 'indoor', ['solo', 'friends'], DAY),
        place('hunters-field', 'Hunter\'s Field', 'park', 'seventh-ward', 'Neighbourhood ball field and playground '
              'on Claiborne where the downtown Mardi Gras Indian gangs gather to start Super Sunday.', ['sports', 'playground', 'mardi-gras-indians'], 'free', 'outdoor', ALL, OPEN),
        place('claiborne-underpass', 'Claiborne Avenue underpass', 'landmark', 'seventh-ward', 'Under the I-10, '
              'whose building in the 1960s cut down the oaks of the old Black main street, the concrete pillars '
              'are painted with murals and the neutral ground fills with families and Indians on Mardi Gras Day.',
              ['murals', 'history', 'mardi-gras'], 'free', 'outdoor', ALL, DAY),
        # Mid-City and City Park
        place('city-park', 'City Park', 'park', 'mid-city', 'A park bigger than Central Park, draped in live oaks '
              'centuries old, with lagoons, paddle boats, a golf course, festival grounds and families picnicking '
              'under the Singing Oak.', ['live-oaks', 'lagoons', 'picnic', 'iconic'], 'free', 'outdoor', ALL, OPEN),
        place('noma', 'New Orleans Museum of Art', 'museum', 'mid-city', 'The city\'s art museum at the head of '
              'City Park, with a Degas painted in New Orleans, photography, Louisiana art and Friday night '
              'programs.', ['art', 'rainy-day'], '$$', 'indoor', ALL, DAY),
        place('besthoff-sculpture-garden', 'Sydney and Walda Besthoff Sculpture Garden', 'garden', 'mid-city',
              'Free sculpture garden beside the art museum, with winding paths, lagoons and big outdoor works '
              'under the oaks.', ['art', 'free', 'walk'], 'free', 'outdoor', ALL, DAY),
        place('botanical-garden', 'New Orleans Botanical Garden', 'garden', 'mid-city', 'Art Deco gardens in City '
              'Park with a conservatory, a garden train layout and plants that like the swampy heat.',
              ['plants', 'quiet', 'walk'], '$', 'mixed', ALL, DAY),
        place('carousel-gardens', 'Carousel Gardens Amusement Park', 'attraction', 'mid-city', 'Small amusement '
              'park in City Park around a century-old wooden carousel, the centerpiece of Celebration in the Oaks '
              'lights in winter.', ['kids', 'carousel', 'rides'], '$$', 'outdoor', ['family', 'date'],
              ['afternoon', 'evening']),
        place('city-park-tennis', 'City Park Tennis Center', 'fitness', 'mid-city', 'Public tennis center with '
              'dozens of hard and clay courts, lessons and leagues.', ['tennis', 'lessons'], '$', 'outdoor',
              ['solo', 'friends', 'family'], ['morning', 'afternoon', 'evening']),
        place('mandinas', 'Mandina\'s', 'restaurant', 'mid-city', 'Canal Street Creole-Italian institution since '
              '1932: turtle soup, trout amandine, red beans on Monday and a busy bar of regulars.',
              ['creole-italian', 'old-school', 'family'], '$$', 'indoor', ALL, ['afternoon', 'evening'],
              cuisine='creole-italian'),
        place('liuzzas', 'Liuzza\'s Restaurant & Bar', 'restaurant', 'mid-city', 'Corner neighbourhood joint '
              'serving frozen fishbowl mugs of beer, fried pickles and the "Frenchuletta".',
              ['po-boys', 'frozen-mugs', 'neighbourhood'], '$', 'indoor', ALL, ['afternoon', 'evening'],
              cuisine='creole-italian'),
        place('rock-n-bowl', 'Rock \'n\' Bowl', 'venue', 'mid-city', 'Bowling alley and dance hall on Carrollton '
              'where couples two-step and jitterbug to zydeco and swamp pop between frames.',
              ['zydeco', 'bowling', 'dancing'], '$$', 'indoor', ['friends', 'date', 'family'], NIGHT),
        place('angelo-brocato', 'Angelo Brocato', 'cafe', 'mid-city', 'Sicilian gelato, cannoli and spumoni parlour '
              'founded in 1905 and still run by the family, with fig cookies for St. Joseph\'s Day.',
              ['gelato', 'cannoli', 'dessert', 'historic'], '$', 'indoor', ALL, ['afternoon', 'evening'],
              cuisine='italian-pastry'),
        place('pandoras-snowballs', 'Pandora\'s Snowballs', 'cafe', 'mid-city', 'Neighbourhood snowball stand on '
              'North Carrollton with a long syrup board and a line of kids and parents on hot afternoons.',
              ['snowballs', 'dessert', 'kids'], '$', 'outdoor', ALL, ['afternoon', 'evening'], SNOBALL,
              cuisine='snowballs'),
        place('ruby-slipper-mid-city', 'Ruby Slipper Café', 'restaurant', 'mid-city', 'The first location of the '
              'local brunch chain, opened after Katrina, with bananas Foster pain perdu and shrimp and grits.',
              ['brunch', 'breakfast', 'line'], '$$', 'indoor', ALL, DAY, cuisine='creole-brunch'),
        place('crescent-city-steaks', 'Crescent City Steaks', 'restaurant', 'mid-city', 'Family-run steakhouse on '
              'Broad Street since 1934 with curtained private booths and steaks sizzling in butter.',
              ['steak', 'old-school', 'booths'], '$$$', 'indoor', ['date', 'family'], DINNER, cuisine='steakhouse'),
        place('ralphs-on-the-park', 'Ralph\'s on the Park', 'restaurant', 'mid-city', 'Contemporary Creole '
              'restaurant facing City Park\'s oaks, a favourite for anniversaries and jazz brunch.',
              ['creole', 'brunch', 'park-views'], '$$$', 'indoor', ['date', 'family'], ['afternoon', 'evening'],
              cuisine='creole'),
        place('cypress-grove-cemetery', 'Cypress Grove and Greenwood cemeteries', 'landmark', 'mid-city', 'Cities '
              'of above-ground tombs at the end of the Canal streetcar line, including the firemen\'s monuments.',
              ['cemetery', 'history', 'quiet'], 'free', 'outdoor', ['solo', 'date'], DAY),
        # Bayou St. John
        place('parkway-bakery', 'Parkway Bakery & Tavern', 'restaurant', 'bayou-st-john', 'Po-boy shop on the '
              'bayou since 1911, with roast beef debris dripping gravy, fried shrimp and a line on Saturdays.',
              ['po-boys', 'roast-beef', 'iconic'], '$', 'mixed', ALL, DAY, cuisine='po-boys'),
        place('pitot-house', 'Pitot House', 'museum', 'bayou-st-john', 'A raised Creole colonial plantation house '
              'from about 1799 on the bayou, open for tours.', ['history', 'architecture', 'house-museum'], '$',
              'mixed', ['solo', 'family', 'date'], DAY),
        place('fair-grinds', 'Fair Grinds Coffeehouse', 'cafe', 'bayou-st-john', 'Community coffeehouse a block '
              'from the Fair Grounds, full of neighbours, laptops and flyers for the next fundraiser.',
              ['coffee', 'community', 'laptop'], '$', 'indoor', ['solo', 'friends', 'coworkers'], DAY,
              cuisine='coffee'),
        place('cafe-degas', 'Café Degas', 'restaurant', 'bayou-st-john', 'French bistro on Esplanade built around '
              'a pecan tree that grows through the enclosed porch.', ['french', 'bistro', 'romantic'], '$$$',
              'indoor', ['date', 'friends'], ['afternoon', 'evening'], cuisine='french'),
        place('bayou-st-john-water', 'Bayou St. John', 'park', 'bayou-st-john', 'The slow bayou itself, lined with '
              'grass banks for picnics and kayak and paddleboard launches, busy with crawfish boils and festivals '
              'in spring.', ['kayaking', 'picnic', 'waterside'], 'free', 'outdoor', ALL, OPEN, WARM),
        place('pals-lounge', 'Pal\'s Lounge', 'bar', 'bayou-st-john', 'Cosy neighbourhood bar with strong drinks, '
              'a pool table and a bathroom wallpapered in vintage pin-ups.', ['neighbourhood-bar', 'pool',
              'cocktails'], '$', 'indoor', ['friends', 'solo', 'date'], NIGHT),
        place('liuzzas-by-the-track', 'Liuzza\'s by the Track', 'restaurant', 'bayou-st-john', 'Tiny corner bar '
              'and kitchen by the Fair Grounds, famous for barbecue shrimp po-boys and gumbo, mobbed during '
              'Jazz Fest.', ['po-boys', 'gumbo', 'jazz-fest'], '$', 'indoor', ALL, DAY, cuisine='creole'),
        place('fair-grounds', 'Fair Grounds Race Course', 'stadium', 'bayou-st-john', 'Historic racetrack with '
              'thoroughbred racing from Thanksgiving to March and the infield that hosts Jazz Fest.',
              ['horse-racing', 'festivals', 'historic'], '$', 'mixed', ['friends', 'date', 'family'],
              ['afternoon'], ['fall', 'winter', 'spring']),
        place('st-louis-cemetery-3', 'St. Louis Cemetery No. 3', 'landmark', 'bayou-st-john', 'Rows of white '
              'family tombs and society vaults on Esplanade by the bayou, open to visitors without a guide.',
              ['cemetery', 'history', 'quiet'], 'free', 'outdoor', ['solo', 'date'], DAY),
        # CBD and Warehouse District
        place('wwii-museum', 'The National WWII Museum', 'museum', 'cbd', 'Sprawling museum of the Second World '
              'War, with Higgins boats built in New Orleans, aircraft hung in a glass pavilion and a 4D film.',
              ['history', 'rainy-day', 'iconic'], '$$$', 'indoor', ALL, DAY),
        place('ogden-museum', 'Ogden Museum of Southern Art', 'museum', 'cbd', 'Southern art from folk to '
              'contemporary, with Thursday evening concerts in the atrium.', ['art', 'southern', 'live-music'],
              '$$', 'indoor', ALL, ['morning', 'afternoon', 'evening']),
        place('contemporary-arts-center', 'Contemporary Arts Center', 'venue', 'cbd', 'Warehouse arts center for '
              'exhibitions, dance, theater and talks on Camp Street.', ['art', 'theater', 'contemporary'], '$$',
              'indoor', ['solo', 'date', 'friends'], ['afternoon', 'evening']),
        place('audubon-aquarium', 'Audubon Aquarium', 'attraction', 'cbd', 'Riverfront aquarium at the foot of '
              'Canal Street with a Gulf of Mexico oil-rig tank, an Amazon gallery and white alligators.',
              ['animals', 'rainy-day', 'kids'], '$$$', 'indoor', ALL, DAY),
        place('caesars-new-orleans', 'Caesars New Orleans', 'nightlife', 'cbd', 'The casino at the foot of Canal '
              'Street, for decades Harrah\'s and renamed Caesars after a 2024 remodel, with tables, slots and a '
              'hotel tower.', ['casino', 'late-night'], '$$$', 'indoor', ['friends', 'date'], LATE),
        place('superdome', 'Caesars Superdome', 'stadium', 'cbd', 'The giant dome where the Saints play, the '
              'Sugar Bowl and Bayou Classic are held and Essence Fest fills the nights each July.',
              ['football', 'saints', 'concerts', 'iconic'], '$$$', 'indoor', ['friends', 'family'],
              ['afternoon', 'evening']),
        place('smoothie-king-center', 'Smoothie King Center', 'stadium', 'cbd', 'Arena beside the Superdome where '
              'the Pelicans play and touring concerts stop.', ['basketball', 'pelicans', 'concerts'], '$$',
              'indoor', ['friends', 'family', 'date'], ['evening'], ['fall', 'winter', 'spring']),
        place('saenger-theatre', 'Saenger Theatre', 'venue', 'cbd', 'Restored 1927 movie palace on Canal Street '
              'with a ceiling of twinkling stars, now staging Broadway tours and concerts.',
              ['theater', 'broadway', 'historic'], '$$$', 'indoor', ['date', 'family', 'friends'], ['evening']),
        place('cochon', 'Cochon', 'restaurant', 'cbd', 'Donald Link\'s Warehouse District Cajun restaurant with '
              'wood-fired oyster roasts, boudin and rabbit and dumplings; the Butcher counter next door does '
              'sandwiches.', ['cajun', 'pork', 'boudin'], '$$$', 'indoor', ['date', 'friends', 'coworkers'],
              ['afternoon', 'evening'], cuisine='cajun'),
        place('emerils', 'Emeril\'s', 'restaurant', 'cbd', 'Emeril Lagasse\'s flagship in a Tchoupitoulas '
              'warehouse, now run as a tasting menu by his son.', ['fine-dining', 'special-occasion'], '$$$$',
              'indoor', ['date'], DINNER, cuisine='creole'),
        place('mothers-restaurant', 'Mother\'s Restaurant', 'restaurant', 'cbd', 'Cafeteria-style Poydras Street '
              'counter since 1938, known for the "Ferdi" ham and debris po-boy and jambalaya.',
              ['po-boys', 'cafeteria', 'historic'], '$$', 'indoor', ALL, ['morning', 'afternoon', 'evening'],
              cuisine='creole'),
        place('rouses-cbd', 'Rouses Market downtown', 'market', 'cbd', 'The downtown branch of the Louisiana '
              'grocery chain, with a hot bar, boiled seafood in season and king cakes stacked by the door in '
              'Carnival.', ['grocery', 'king-cake', 'lunch'], '$$', 'indoor', ALL, OPEN),
        place('lafayette-square', 'Lafayette Square', 'park', 'cbd', 'Shady downtown square across from Gallier '
              'Hall where office workers eat lunch and the free Wednesday at the Square concerts run in spring.',
              ['lunch', 'concerts', 'shade'], 'free', 'outdoor', ALL, OPEN),
        place('crescent-city-farmers-market', 'Crescent City Farmers Market', 'market', 'cbd', 'Saturday-morning '
              'market in the Warehouse District with Creole tomatoes, satsumas, Gulf shrimp and a chef demo.',
              ['farmers-market', 'saturday', 'produce'], '$', 'outdoor', ALL, ['morning']),
        place('mammoth-espresso', 'Mammoth Espresso', 'cafe', 'cbd', 'Small, serious coffee bar in the Warehouse '
              'District for office workers and convention visitors.', ['coffee', 'espresso', 'laptop'], '$',
              'indoor', ['solo', 'coworkers', 'friends'], DAY, cuisine='coffee'),
        place('mardi-gras-world', 'Mardi Gras World', 'attraction', 'cbd', 'Blaine Kern\'s float warehouses by the '
              'Convention Center, where artists build and paint the papier-mâché figures for dozens of krewes.',
              ['carnival', 'floats', 'tours'], '$$', 'indoor', ALL, DAY),
        place('ferry-terminal-canal', 'Canal Street ferry landing', 'landmark', 'cbd', 'The riverfront terminal for '
              'the Algiers Point ferry, with the Spanish Plaza fountain beside it and big ships passing close.',
              ['river', 'views', 'ferry'], '$', 'outdoor', ALL, OPEN),
        # Lower Garden District
        place('coliseum-square', 'Coliseum Square', 'park', 'lower-garden-district', 'Long, oak-shaded park '
              'surrounded by Greek Revival mansions, used by dog walkers and the neighbourhood\'s fall art fair.',
              ['dogs', 'shade', 'architecture'], 'free', 'outdoor', ALL, OPEN),
        place('courtyard-brewery', 'Courtyard Brewery', 'bar', 'lower-garden-district', 'Small brewery taproom '
              'with a gravel yard for food trucks, dogs and long afternoons.', ['brewery', 'food-trucks', 'dogs'],
              '$$', 'mixed', ['friends', 'date', 'solo'], ['afternoon', 'evening']),
        place('steins-deli', 'Stein\'s Market & Deli', 'restaurant', 'lower-garden-district', 'Magazine Street '
              'deli making Philadelphia-style hoagies and Reubens, with a fridge of craft beer.',
              ['deli', 'sandwiches', 'beer'], '$$', 'indoor', ['solo', 'friends', 'coworkers'], DAY,
              cuisine='jewish-deli'),
        place('french-truck-coffee', 'French Truck Coffee', 'cafe', 'lower-garden-district', 'Local roaster that '
              'began delivering beans from a yellow truck, with a busy cafe on Magazine Street.',
              ['coffee', 'roaster', 'laptop'], '$', 'indoor', ['solo', 'friends', 'coworkers'], DAY,
              cuisine='coffee'),
        place('avenue-pub', 'The Avenue Pub', 'bar', 'lower-garden-district', 'Twenty-four-hour beer bar on St. '
              'Charles with a serious tap list and an upstairs balcony over the parade route.',
              ['beer', 'balcony', 'parade-route'], '$$', 'mixed', ['friends', 'solo'], LATE,
              cuisine='american-pub'),
        place('juans-flying-burrito', 'Juan\'s Flying Burrito', 'restaurant', 'lower-garden-district', 'Loud, '
              'tattooed "Creole taqueria" on Magazine with big burritos and cheap margaritas.',
              ['burritos', 'casual', 'margaritas'], '$', 'indoor', ['friends', 'solo', 'family'],
              ['afternoon', 'evening'], cuisine='tex-mex'),
        # Garden District
        place('commanders-palace', 'Commander\'s Palace', 'restaurant', 'garden-district', 'The turquoise-and-white '
              'Victorian where the Brennan family serves turtle soup, bread pudding soufflé and twenty-five-cent '
              'weekday lunch martinis, with a jazz brunch on weekends.', ['creole', 'jazz-brunch',
              'special-occasion', 'iconic'], '$$$$', 'indoor', ['date', 'family', 'friends'],
              ['afternoon', 'evening'], cuisine='creole'),
        place('coquette', 'Coquette', 'restaurant', 'garden-district', 'Southern bistro in an old corner grocery on '
              'Magazine and Washington with a changing menu and a good bar.', ['southern', 'bistro', 'cocktails'],
              '$$$', 'indoor', ['date', 'friends'], ['afternoon', 'evening'], cuisine='southern'),
        place('garden-district-houses', 'Garden District house walk', 'landmark', 'garden-district', 'Self-guided '
              'walk past the mansions of Prytania and First streets, with their cast-iron fences, raised galleries '
              'and famous former residents.', ['architecture', 'walk', 'history'], 'free', 'outdoor', ALL, DAY),
        place('garden-district-book-shop', 'Garden District Book Shop', 'shopping', 'garden-district', 'Independent '
              'bookshop in The Rink, an old skating rink turned shops, strong on local writers and signed '
              'editions.', ['books', 'local-authors'], '$', 'indoor', ['solo', 'date'], DAY),
        place('magazine-street-shops', 'Magazine Street shops', 'shopping', 'garden-district', 'Six miles of '
              'boutiques, vintage shops, galleries and cafés from the Lower Garden District to Audubon Park.',
              ['boutiques', 'vintage', 'walk'], '$$', 'outdoor', ALL, DAY),
        place('lafayette-cemetery-1', 'Lafayette Cemetery No. 1', 'landmark', 'garden-district', 'Walled 1833 '
              'city of tombs across from Commander\'s Palace; its gates have spent long stretches closed for '
              'repairs, but the vaults rise over the walls on Washington Avenue.', ['cemetery', 'history'], 'free',
              'outdoor', ['solo', 'date'], DAY),
        # Irish Channel
        place('traceys', 'Tracey\'s', 'bar', 'irish-channel', 'Irish Channel corner bar with roast beef po-boys, '
              'Saints games on every screen and the end of the St. Patrick\'s parade at its door.',
              ['sports-bar', 'po-boys', 'irish'], '$', 'indoor', ['friends', 'solo'], LATE, cuisine='po-boys'),
        place('mahonys', 'Mahony\'s Po-Boys', 'restaurant', 'irish-channel', 'Magazine Street po-boy shop in an old '
              'cottage, known for fried green tomato and shrimp remoulade po-boys and a porch to eat them on.',
              ['po-boys', 'porch', 'casual'], '$', 'mixed', ALL, ['afternoon', 'evening'], cuisine='po-boys'),
        place('st-mary-assumption', 'St. Mary\'s Assumption Church', 'landmark', 'irish-channel', 'Towering German '
              'Baroque church built by the neighbourhood\'s German Catholics, with the shrine of Blessed Francis '
              'Xavier Seelos.', ['church', 'architecture', 'history'], 'free', 'indoor', ALL, DAY),
        place('urban-south', 'Urban South Brewery', 'bar', 'irish-channel', 'Warehouse brewery on Tchoupitoulas '
              'with a big family- and dog-friendly taproom.', ['brewery', 'family-friendly', 'dogs'], '$$', 'indoor',
              ALL, ['afternoon', 'evening']),
        place('irish-channel-blocks', 'Irish Channel shotgun blocks', 'landmark', 'irish-channel', 'Streets of '
              'nineteenth-century shotgun doubles in candy colours, with neighbours on stoops and porches.',
              ['architecture', 'walk', 'neighbourhood'], 'free', 'outdoor', ALL, OPEN),
        # Central City
        place('sofab', 'Southern Food & Beverage Museum', 'museum', 'central-city', 'Museum of Southern food and '
              'drink on Oretha Castle Haley, home to the Museum of the American Cocktail and cooking demos.',
              ['food', 'cocktails', 'history'], '$$', 'indoor', ADULT, DAY),
        place('cafe-reconcile', 'Café Reconcile', 'restaurant', 'central-city', 'Lunch restaurant run as a '
              'training program for young people entering hospitality, serving red beans, fried fish and '
              'bread pudding.', ['lunch', 'community', 'soul-food'], '$', 'indoor', ALL, ['afternoon'],
              cuisine='creole'),
        place('ashe-cultural-arts', 'Ashé Cultural Arts Center', 'venue', 'central-city', 'Black arts center in a '
              'former department store with performances, exhibitions and community gatherings.',
              ['arts', 'black-culture', 'community'], '$', 'indoor', ALL, ['afternoon', 'evening']),
        place('jazz-market', 'New Orleans Jazz Market', 'venue', 'central-city', 'The New Orleans Jazz Orchestra\'s '
              'home in a converted department store, with concerts and a bar.', ['jazz', 'concerts'], '$$',
              'indoor', ['date', 'friends', 'solo'], ['evening']),
        place('central-city-bbq', 'Central City BBQ', 'restaurant', 'central-city', 'Smoked brisket and ribs on '
              'a huge patio with yard games and Saints games on the big screen.', ['barbecue', 'patio', 'sports'],
              '$$', 'mixed', ALL, ['afternoon', 'evening'], cuisine='barbecue'),
        place('al-davis-park', 'A.L. Davis Park', 'park', 'central-city', 'Neighbourhood park on Washington Avenue '
              'where the Uptown Mardi Gras Indian gangs gather on Super Sunday in their new suits.',
              ['mardi-gras-indians', 'playground', 'community'], 'free', 'outdoor', ALL, OPEN),
        place('dryades-ymca', 'Dryades YMCA', 'fitness', 'central-city', 'Historic YMCA founded in 1905 for Black '
              'New Orleanians, still running a gym, pool and youth programs.', ['gym', 'pool', 'history'], '$',
              'indoor', ALL, ['morning', 'afternoon', 'evening']),
        # Uptown
        place('audubon-park', 'Audubon Park', 'park', 'uptown', 'Oak-shaded park across from Tulane and Loyola '
              'with a paved loop full of runners and strollers, a lagoon of egrets and a golf course.',
              ['running', 'live-oaks', 'birds', 'iconic'], 'free', 'outdoor', ALL, OPEN),
        place('audubon-zoo', 'Audubon Zoo', 'attraction', 'uptown', 'The city zoo with a Louisiana Swamp exhibit '
              'of alligators and Cajun houseboats, jaguars and a splash park.', ['animals', 'kids', 'swamp'],
              '$$$', 'outdoor', ['family', 'date', 'friends'], DAY),
        place('the-fly', 'The Fly', 'park', 'uptown', 'Riverside lawn behind the zoo where students and families '
              'picnic, play frisbee and watch ships and sunsets on the Mississippi.',
              ['riverfront', 'sunset', 'picnic'], 'free', 'outdoor', ALL, ['afternoon', 'evening']),
        place('audubon-golf', 'Audubon Park Golf Course', 'fitness', 'uptown', 'Short public course inside Audubon '
              'Park with a clubhouse and lagoon views.', ['golf', 'outdoors'], '$$', 'outdoor', ['solo', 'friends'],
              DAY),
        place('tipitinas', 'Tipitina\'s', 'venue', 'uptown', 'Napoleon Avenue music hall named for Professor '
              'Longhair\'s song, with his bust by the door and funk, brass and Cajun dances on the bill.',
              ['live-music', 'funk', 'historic'], '$$', 'indoor', ['friends', 'date'], NIGHT),
        place('hansens-sno-bliz', 'Hansen\'s Sno-Bliz', 'cafe', 'uptown', 'Snowball stand on Tchoupitoulas since '
              '1939, shaving ice on a homemade machine and dousing it in house syrups.',
              ['snowballs', 'historic', 'dessert'], '$', 'indoor', ALL, ['afternoon', 'evening'], SNOBALL,
              cuisine='snowballs'),
        place('le-bon-temps-roule', 'Le Bon Temps Roulé', 'bar', 'uptown', 'Magazine Street neighbourhood bar with a '
              'pool table and free live music in the back room, including a long-running Thursday brass band.',
              ['live-music', 'brass-band', 'pool'], '$', 'indoor', ['friends', 'solo'], NIGHT),
        place('casamentos', 'Casamento\'s', 'restaurant', 'uptown', 'Tiled oyster bar on Magazine since 1919 that '
              'closes for the hot months when oysters are thin, serving oyster loaves on thick white bread.',
              ['oysters', 'historic', 'seasonal'], '$$', 'indoor', ALL, ['afternoon', 'evening'],
              ['fall', 'winter', 'spring'], cuisine='seafood'),
        place('domilises', 'Domilise\'s Po-Boy & Bar', 'restaurant', 'uptown', 'Family po-boy shop in a yellow '
              'house on Annunciation Street, with Barq\'s root beer and shrimp and roast beef po-boys.',
              ['po-boys', 'old-school', 'local'], '$', 'indoor', ALL, DAY, cuisine='po-boys'),
        place('clancys', 'Clancy\'s', 'restaurant', 'uptown', 'White-tablecloth Uptown bistro where locals order '
              'smoked soft-shell crab and fried oysters with brie.', ['creole', 'locals', 'fine-dining'], '$$$$',
              'indoor', ['date', 'friends'], DINNER, cuisine='creole'),
        place('pascals-manale', 'Pascal\'s Manale', 'restaurant', 'uptown', 'Napoleon Avenue restaurant since 1913 '
              'that claims barbecue shrimp, cooked in a peppery butter sauce for dunking bread, plus an oyster bar.',
              ['bbq-shrimp', 'oysters', 'old-school'], '$$$', 'indoor', ['family', 'date', 'friends'], DINNER,
              cuisine='creole-italian'),
        place('hey-cafe', 'Hey! Café', 'cafe', 'uptown', 'Magazine Street coffee shop that roasts its own beans in '
              'the room, with comfy chairs and a regular crowd of students.', ['coffee', 'roaster', 'laptop'], '$',
              'indoor', ['solo', 'friends'], OPEN, cuisine='coffee'),
        place('tulane-campus', 'Tulane and Loyola campuses', 'landmark', 'uptown', 'Neighbouring campuses on St. '
              'Charles Avenue facing Audubon Park, with Gibson Hall, Holy Name of Jesus church and the streetcar '
              'stop out front.', ['campus', 'architecture', 'walk'], 'free', 'outdoor', ALL, DAY),
        # Carrollton and Riverbend
        place('oak-street', 'Oak Street', 'shopping', 'carrollton', 'Small-town main street of shops, bars and '
              'cafés off Carrollton, home of the Po-Boy Festival.', ['main-street', 'shops', 'walk'], '$',
              'outdoor', ALL, OPEN),
        place('jacques-imos', 'Jacques-Imo\'s Café', 'restaurant', 'carrollton', 'Loud, colourful Oak Street '
              'restaurant reached through the bar, known for shrimp and alligator sausage cheesecake.',
              ['creole', 'funky', 'loud'], '$$$', 'indoor', ['friends', 'date'], DINNER, cuisine='creole'),
        place('maple-leaf-bar', 'Maple Leaf Bar', 'venue', 'carrollton', 'Pressed-tin-ceilinged music bar where '
              'Rebirth Brass Band has played Tuesday nights for decades.', ['brass-band', 'funk', 'late-night'],
              '$$', 'indoor', ['friends', 'date'], LATE),
        place('cooter-browns', 'Cooter Brown\'s Tavern & Oyster Bar', 'bar', 'carrollton', 'Riverbend bar by the '
              'levee with hundreds of beers, oysters on the half shell and a gallery of celebrity caricatures.',
              ['beer', 'oysters', 'sports'], '$$', 'indoor', ['friends', 'solo'], LATE, cuisine='seafood'),
        place('plum-street-snoball', 'Plum Street Snoball', 'cafe', 'carrollton', 'Neighbourhood snowball stand '
              'serving towering cups, including the famous ones in Chinese takeout boxes.',
              ['snowballs', 'dessert', 'kids'], '$', 'outdoor', ALL, ['afternoon', 'evening'], SNOBALL,
              cuisine='snowballs'),
        place('camellia-grill', 'Camellia Grill', 'restaurant', 'carrollton', 'White-columned diner at the '
              'streetcar turn where waiters in bow ties serve omelettes and chocolate freezes at the counter.',
              ['diner', 'counter', 'breakfast'], '$', 'indoor', ALL, OPEN, cuisine='american-diner'),
        place('levee-path', 'Mississippi River levee path', 'trail', 'carrollton', 'Paved path along the top of the '
              'levee from the Fly upriver, used by runners and cyclists, with ships passing below.',
              ['running', 'cycling', 'river', 'views'], 'free', 'outdoor', ALL, OPEN),
        place('college-inn', 'Ye Olde College Inn', 'restaurant', 'carrollton', 'Neighbourhood restaurant since '
              'the 1930s, with po-boys and Creole plates and vegetables from its own urban farm.',
              ['po-boys', 'creole', 'family'], '$$', 'indoor', ALL, ['afternoon', 'evening'], cuisine='creole'),
        # Freret
        place('cure', 'Cure', 'bar', 'freret', 'The cocktail bar in an old firehouse that helped revive Freret '
              'Street and the city\'s craft cocktail scene.', ['cocktails', 'craft', 'date-night'], '$$$', 'indoor',
              ['date', 'friends'], NIGHT),
        place('company-burger', 'The Company Burger', 'restaurant', 'freret', 'Smashed double burgers with house '
              'condiments, no substitutions and a cold beer.', ['burgers', 'casual'], '$', 'indoor', ALL,
              ['afternoon', 'evening'], cuisine='burgers'),
        place('dat-dog', 'Dat Dog', 'restaurant', 'freret', 'The original location of the local hot dog shop with '
              'alligator and crawfish sausages and a big upstairs deck.', ['hot-dogs', 'deck', 'casual'], '$',
              'mixed', ALL, ['afternoon', 'evening', 'late'], cuisine='hot-dogs'),
        place('high-hat-cafe', 'High Hat Café', 'restaurant', 'freret', 'Delta-style café with fried catfish, '
              'pimento cheese and a long happy hour.', ['southern', 'catfish', 'happy-hour'], '$$', 'indoor', ALL,
              ['afternoon', 'evening'], cuisine='southern'),
        place('freret-strip', 'Freret Street corridor', 'nightlife', 'freret', 'A walkable stretch of bars, '
              'restaurants and a monthly market between Napoleon and Jefferson, busy with students on weekends.',
              ['bars', 'students', 'walk'], '$$', 'outdoor', ['friends', 'date'], NIGHT),
        # Broadmoor and Gert Town
        place('rosa-keller-library', 'Rosa F. Keller Library & Community Center', 'library', 'broadmoor', 'Branch '
              'library rebuilt by the neighbourhood after Katrina in an old mansion and a modern wing, with '
              'meeting rooms and homework help.', ['books', 'community', 'study'], 'free', 'indoor', ALL, DAY),
        place('zony-mash', 'Zony Mash Beer Project', 'bar', 'broadmoor', 'Brewery in the restored Gem Theater on '
              'Broad Street, with a kitchen, trivia and a family-friendly taproom.', ['brewery', 'historic',
              'trivia'], '$$', 'indoor', ALL, ['afternoon', 'evening']),
        place('xavier-chapel', 'Xavier University campus', 'landmark', 'broadmoor', 'The green-roofed campus of the '
              'only historically Black Catholic university in the country, with the St. Katharine Drexel Chapel.',
              ['campus', 'architecture', 'hbcu'], 'free', 'outdoor', ['solo', 'family'], DAY),
        place('rosenwald-rec', 'Rosenwald Recreation Center', 'fitness', 'broadmoor', 'City recreation center on '
              'Broad Street with a gym, fields and youth sports.', ['gym', 'youth-sports', 'rec-center'], 'free',
              'indoor', ALL, ['morning', 'afternoon', 'evening']),
        place('washington-avenue-neutral-ground', 'Washington Avenue neutral ground', 'park', 'broadmoor', 'Wide '
              'grassy median where neighbours walk dogs, kids ride bikes and Sunday second lines pass.',
              ['walk', 'dogs', 'second-lines'], 'free', 'outdoor', ALL, OPEN),
        # Gentilly
        place('dillard-campus', 'Dillard University', 'landmark', 'gentilly', 'White-columned buildings around a '
              'long oak avenue on the campus of the historically Black university on Gentilly Boulevard.',
              ['campus', 'hbcu', 'live-oaks'], 'free', 'outdoor', ['solo', 'family'], DAY),
        place('pontchartrain-park', 'Pontchartrain Park', 'park', 'gentilly', 'Park and neighbourhood built in the '
              '1950s as the first suburb for Black homeowners in the city, with ball fields and a lagoon.',
              ['history', 'playground', 'sports'], 'free', 'outdoor', ALL, OPEN),
        place('bartholomew-golf', 'Joseph M. Bartholomew Sr. Golf Course', 'fitness', 'gentilly', 'Public course in '
              'Pontchartrain Park named for the Black golf architect who designed courses he was barred from '
              'playing.', ['golf', 'history'], '$$', 'outdoor', ['solo', 'friends'], DAY),
        place('lakefront-arena', 'UNO Lakefront Arena', 'venue', 'gentilly', 'University arena by the lake for '
              'basketball, graduations, concerts and touring shows.', ['concerts', 'basketball'], '$$', 'indoor',
              ['friends', 'family'], ['evening']),
        place('gentilly-terrace', 'Gentilly Terrace bungalows', 'landmark', 'gentilly', 'Blocks of 1910s and 1920s '
              'Arts and Crafts and Spanish revival bungalows set on the old ridge.', ['architecture', 'walk'],
              'free', 'outdoor', ['solo', 'date', 'family'], DAY),
        place('sammys-deli', 'Sammy\'s Food Service & Deli', 'restaurant', 'gentilly', 'Elysian Fields deli and '
              'po-boy shop feeding Gentilly lunch crowds, students and church groups.', ['po-boys', 'plate-lunch',
              'local'], '$', 'indoor', ALL, DAY, cuisine='po-boys'),
        # Lakeview
        place('lakefront-seawall', 'Lakeshore Drive seawall', 'park', 'lakeview', 'Miles of stepped concrete '
              'seawall on Lake Pontchartrain for sunsets, fishing, cycling and grills on holiday weekends.',
              ['lakefront', 'sunset', 'fishing', 'cycling'], 'free', 'outdoor', ALL, OPEN),
        place('new-basin-lighthouse', 'New Canal Lighthouse', 'landmark', 'lakeview', 'Rebuilt nineteenth-century '
              'lighthouse at the end of the old New Basin Canal, with a small museum on the lake and its storms.',
              ['lakefront', 'history', 'views'], '$', 'mixed', ALL, DAY),
        place('mondo', 'Mondo', 'restaurant', 'lakeview', 'Susan Spicer\'s easygoing Harrison Avenue restaurant '
              'with wood-fired pizza and global plates.', ['pizza', 'family', 'local'], '$$', 'indoor', ALL,
              ['afternoon', 'evening'], cuisine='global'),
        place('velvet-cactus', 'The Velvet Cactus', 'restaurant', 'lakeview', 'Tex-Mex with a sprawling courtyard '
              'of string lights and frozen margaritas.', ['tex-mex', 'courtyard', 'margaritas'], '$$', 'mixed',
              ['friends', 'family', 'date'], ['afternoon', 'evening'], cuisine='tex-mex'),
        place('parlays', 'Parlay\'s', 'bar', 'lakeview', 'Lakeview neighbourhood bar on Harrison Avenue for '
              'cold beer, darts and every LSU and Saints game.', ['neighbourhood-bar', 'sports'], '$', 'indoor',
              ['friends', 'solo'], NIGHT),
        place('lakeview-brew', 'Lakeview Brew Coffee Café', 'cafe', 'lakeview', 'Neighbourhood café for coffee, '
              'pastries and lunch salads on Harrison Avenue.', ['coffee', 'pastries', 'lunch'], '$', 'indoor', ALL,
              DAY, cuisine='cafe'),
        place('harrison-avenue', 'Harrison Avenue', 'shopping', 'lakeview', 'Lakeview\'s main street of shops, '
              'cafés and restaurants, rebuilt after the 2005 flood.', ['main-street', 'errands'], '$$', 'outdoor',
              ALL, DAY),
        # Algiers Point
        place('congregation-coffee', 'Congregation Coffee Roasters', 'cafe', 'algiers-point', 'Algiers Point\'s '
              'coffee roaster and café, a short walk from the ferry landing.', ['coffee', 'roaster', 'local'], '$',
              'indoor', ['solo', 'friends', 'coworkers'], DAY, cuisine='coffee'),
        place('old-point-bar', 'Old Point Bar', 'bar', 'algiers-point', 'Neighbourhood bar by the levee with live '
              'music on weekends and a crowd of locals who all know each other.', ['live-music', 'local',
              'neighbourhood-bar'], '$', 'indoor', ['friends', 'solo'], NIGHT),
        place('algiers-levee', 'Algiers Point levee', 'park', 'algiers-point', 'Grassy levee top and path with the '
              'best view of the downtown skyline across the river, crowded for Fourth of July fireworks.',
              ['views', 'riverfront', 'sunset'], 'free', 'outdoor', ALL, OPEN),
        place('tout-de-suite', 'Tout de Suite Café', 'cafe', 'algiers-point', 'Casual café in an old corner store '
              'serving breakfast, sandwiches and coffee to neighbours.', ['breakfast', 'coffee', 'local'], '$',
              'indoor', ALL, DAY, cuisine='cafe'),
        place('dry-dock-cafe', 'Dry Dock Café', 'restaurant', 'algiers-point', 'Seafood and po-boy spot by the ferry '
              'landing, a stop for commuters and day-trippers.', ['seafood', 'po-boys', 'ferry'], '$$', 'indoor',
              ALL, ['afternoon', 'evening'], cuisine='seafood'),
        place('algiers-courthouse', 'Algiers Courthouse', 'landmark', 'algiers-point', 'Red-brick 1896 courthouse '
              'facing the river, a landmark for anyone stepping off the ferry.', ['architecture', 'history'],
              'free', 'outdoor', ['solo', 'family'], DAY),
        place('algiers-point-library', 'Cita Dennis Hubbell Library', 'library', 'algiers-point', 'Small branch '
              'library in Algiers Point with story times and a reading garden.', ['books', 'quiet', 'kids'],
              'free', 'indoor', ALL, DAY),
        # Lower Ninth Ward and Holy Cross
        place('steamboat-houses', 'Doullut Steamboat Houses', 'landmark', 'lower-ninth-ward', 'Two early '
              'twentieth-century houses built by a riverboat pilot to look like steamboats, by the Holy Cross '
              'levee.', ['architecture', 'quirky', 'history'], 'free', 'outdoor', ALL, DAY),
        place('holy-cross-levee', 'Holy Cross levee', 'park', 'lower-ninth-ward', 'Quiet levee top with river views '
              'back to the city, popular with walkers, fishers and photographers.', ['riverfront', 'walk', 'views'],
              'free', 'outdoor', ALL, OPEN),
        place('fats-domino-house', 'Fats Domino\'s house', 'landmark', 'lower-ninth-ward', 'The yellow-and-black '
              'home and studio on Caffin Avenue that Antoine "Fats" Domino kept in the neighbourhood he never '
              'left.', ['music', 'history'], 'free', 'outdoor', ['solo', 'friends'], DAY),
        place('cafe-dauphine', 'Café Dauphine', 'restaurant', 'lower-ninth-ward', 'Family-owned Creole soul '
              'restaurant serving stuffed shrimp, gumbo and fried chicken to a neighbourhood with few sit-down '
              'spots.', ['creole', 'soul-food', 'local'], '$$', 'indoor', ALL, ['afternoon', 'evening'],
              cuisine='creole'),
        place('lower-ninth-living-museum', 'Lower Ninth Ward Living Museum', 'museum', 'lower-ninth-ward', 'Small '
              'museum in a house telling the neighbourhood\'s story from plantation land to the 2005 flood and '
              'return.', ['history', 'katrina', 'community'], 'free', 'indoor', ALL, DAY),
        place('sankofa-wetland-park', 'Sankofa Wetland Park', 'park', 'lower-ninth-ward', 'Restored wetland park '
              'with trails, birdwatching and a nature classroom, built to soak up stormwater.',
              ['wetlands', 'birds', 'trail'], 'free', 'outdoor', ALL, DAY),
        # New Orleans East
        place('dong-phuong', 'Dong Phuong Bakery & Restaurant', 'restaurant', 'new-orleans-east', 'Vietnamese '
              'bakery whose bread is in banh mi and po-boys across the city and whose king cakes sell out in '
              'minutes every Carnival.', ['banh-mi', 'king-cake', 'bakery', 'vietnamese'], '$', 'indoor', ALL, DAY,
              cuisine='vietnamese'),
        place('versailles-market', 'Village de l\'Est Saturday market', 'market', 'new-orleans-east', 'Early '
              'Saturday morning market where Vietnamese growers sell herbs, greens, live ducks and snacks.',
              ['market', 'vietnamese', 'produce', 'early'], '$', 'outdoor', ALL, ['morning']),
        place('mary-queen-of-vietnam', 'Mary Queen of Vietnam Church', 'landmark', 'new-orleans-east', 'The parish '
              'at the heart of the Vietnamese community, which led its return after Katrina, with Tet celebrations '
              'on its grounds.', ['church', 'vietnamese', 'community'], 'free', 'mixed', ALL, DAY),
        place('joe-brown-rec', 'Joe W. Brown Recreation Center', 'fitness', 'new-orleans-east', 'Large city '
              'recreation center and park with a natatorium, tennis courts and walking paths.',
              ['pool', 'tennis', 'rec-center'], 'free', 'indoor', ALL, ['morning', 'afternoon', 'evening']),
        place('bayou-sauvage', 'Bayou Sauvage Urban National Wildlife Refuge', 'park', 'new-orleans-east',
              'One of the largest urban wildlife refuges in the country, with boardwalks over marsh full of '
              'herons and alligators.', ['wildlife', 'birds', 'boardwalk', 'nature'], 'free', 'outdoor', ALL, DAY),
        place('chef-menteur-strip', 'Chef Menteur Highway pho shops', 'restaurant', 'new-orleans-east', 'Strip-mall '
              'Vietnamese restaurants and bakeries along Chef Menteur and Alcee Fortier serving pho, bun and '
              'banh xeo.', ['pho', 'vietnamese', 'casual'], '$', 'indoor', ALL, ['morning', 'afternoon', 'evening'],
              cuisine='vietnamese'),
        # Metairie
        place('morning-call', 'Morning Call', 'cafe', 'metairie', 'Old-school coffee stand that moved out from the '
              'French Market in 1974, with beignets you sugar yourself at the counter.',
              ['beignets', 'chicory-coffee', 'old-school'], '$', 'indoor', ALL, OPEN, cuisine='beignets'),
        place('lakeside-shopping-center', 'Lakeside Shopping Center', 'shopping', 'metairie', 'The region\'s big '
              'indoor mall on Causeway Boulevard, where Carnival parade-goers find bathrooms.',
              ['mall', 'rainy-day'], '$$', 'indoor', ALL, ['afternoon', 'evening']),
        place('lafreniere-park', 'Lafreniere Park', 'park', 'metairie', 'Big Jefferson Parish park with a lake, '
              'walking loop, dog park and a holiday lights display.', ['walk', 'dogs', 'playground'], 'free',
              'outdoor', ALL, OPEN),
        place('dragos', 'Drago\'s Seafood Restaurant', 'restaurant', 'metairie', 'The Croatian-American family '
              'restaurant that invented charbroiled oysters, sizzling with garlic butter and parmesan.',
              ['charbroiled-oysters', 'seafood'], '$$', 'indoor', ALL, ['afternoon', 'evening'], cuisine='seafood'),
        place('deanies-bucktown', 'Deanie\'s Seafood Bucktown', 'restaurant', 'metairie', 'Family seafood house in '
              'the old fishing village of Bucktown, serving boiled seafood and fried platters with complimentary '
              'new potatoes.', ['seafood', 'boiled-seafood', 'family'], '$$', 'indoor', ALL,
              ['afternoon', 'evening'], cuisine='seafood'),
        place('ochsner-fitness', 'Ochsner Fitness Center', 'fitness', 'metairie', 'Large medical fitness club with '
              'pools, classes and physical therapy.', ['gym', 'pool', 'classes'], '$$', 'indoor', ALL,
              ['morning', 'evening']),
        place('martin-wine-cellar', 'Martin Wine Cellar', 'market', 'metairie', 'Wine shop and deli with a '
              'sandwich counter and tasting events.', ['wine', 'deli'], '$$', 'indoor', ADULT, DAY),
    ],
    'colleges': [
        college('tulane', 'Tulane University', 'research-university', 'uptown', 'large',
                ['medicine', 'public-health', 'architecture', 'law', 'business', 'research']),
        college('tulane-medicine', 'Tulane University School of Medicine', 'medical-school', 'cbd', 'medium',
                ['medicine', 'public-health', 'tropical-medicine']),
        college('lsu-health', 'LSU Health New Orleans', 'medical-school', 'cbd', 'medium',
                ['medicine', 'nursing', 'dentistry', 'allied-health']),
        college('loyola', 'Loyola University New Orleans', 'private-university', 'uptown', 'medium',
                ['music-industry', 'law', 'mass-communication', 'business']),
        college('xavier', 'Xavier University of Louisiana', 'private-university', 'broadmoor', 'medium',
                ['hbcu', 'pharmacy', 'pre-med', 'sciences']),
        college('dillard', 'Dillard University', 'liberal-arts-college', 'gentilly', 'small',
                ['hbcu', 'nursing', 'public-health', 'film']),
        college('uno', 'University of New Orleans', 'public-university', 'gentilly', 'medium',
                ['engineering', 'naval-architecture', 'hospitality', 'film', 'business']),
        college('suno', 'Southern University at New Orleans', 'public-university', 'gentilly', 'small',
                ['hbcu', 'social-work', 'education', 'business']),
        college('delgado', 'Delgado Community College', 'community-college', 'mid-city', 'large',
                ['nursing', 'culinary-arts', 'trades', 'transfer']),
        college('nocca', 'New Orleans Center for Creative Arts', 'art-school', 'marigny', 'small',
                ['jazz', 'theater', 'visual-arts', 'culinary-arts', 'dance']),
        college('notre-dame-seminary', 'Notre Dame Seminary', 'seminary', 'carrollton', 'small',
                ['theology', 'priesthood']),
    ],
    'employers': [
        employer('ochsner', 'Ochsner Medical Center', 'healthcare', 'metairie', 'large', 'The flagship campus of '
                 'Louisiana\'s largest health system on Jefferson Highway, just over the parish line.',
                 ['registered-nurse', 'night-nurse', 'physician-resident', 'pharmacist', 'medical-researcher',
                  'social-worker', 'data-analyst']),
        employer('umc-new-orleans', 'University Medical Center New Orleans (LCMC Health)', 'healthcare', 'cbd',
                 'large', 'LCMC Health\'s Level I trauma center and teaching hospital in the medical district on '
                 'Canal Street.', ['registered-nurse', 'night-nurse', 'physician-resident', 'pharmacist',
                                   'social-worker']),
        employer('childrens-hospital', 'Children\'s Hospital New Orleans (LCMC Health)', 'healthcare', 'uptown',
                 'large', 'The region\'s children\'s hospital on the river end of Henry Clay Avenue.',
                 ['registered-nurse', 'night-nurse', 'physician-resident', 'social-worker']),
        employer('va-new-orleans', 'Southeast Louisiana Veterans Health Care System', 'healthcare', 'cbd', 'large',
                 'The VA medical center in the downtown medical district.',
                 ['registered-nurse', 'pharmacist', 'social-worker', 'physician-resident']),
        employer('tulane-employer', 'Tulane University', 'education', 'uptown', 'large', 'One of the city\'s '
                 'largest private employers, with the Uptown campus and the downtown medical school.',
                 ['professor', 'graduate-student', 'medical-researcher', 'data-analyst', 'software-engineer']),
        employer('port-of-new-orleans', 'Port of New Orleans', 'logistics', 'uptown', 'large', 'Container, '
                 'breakbulk and cruise terminals along the river, including the Napoleon Avenue container '
                 'terminal.', ['port-logistics', 'government-analyst', 'accountant']),
        employer('entergy', 'Entergy', 'energy', 'cbd', 'large', 'The Fortune 500 utility headquartered in a tower '
                 'on Loyola Avenue.', ['financial-analyst', 'data-analyst', 'accountant', 'software-engineer',
                                       'construction-trades']),
        employer('caesars-employer', 'Caesars New Orleans', 'hospitality', 'cbd', 'large', 'The Canal Street casino '
                 'and hotel, long known as Harrah\'s.', ['casino-dealer', 'bartender', 'line-cook', 'server',
                                                        'hotel-front-desk']),
        employer('superdome-employer', 'Caesars Superdome and Smoothie King Center', 'entertainment', 'cbd', 'large',
                 'The stadium and arena run for the state, staffing game days, concerts, Essence Fest and the '
                 'Sugar Bowl.', ['event-planner', 'server', 'bartender', 'retail-associate']),
        employer('saints-pelicans', 'New Orleans Saints and Pelicans', 'sports', 'metairie', 'medium', 'The NFL and '
                 'NBA franchises, with their front offices and training base in Metairie.',
                 ['marketing-coordinator', 'fitness-trainer', 'data-analyst', 'event-planner']),
        employer('hotel-monteleone', 'Hotel Monteleone', 'hospitality', 'french-quarter', 'medium', 'Family-owned '
                 'Royal Street hotel since 1886, home of the revolving Carousel Bar.',
                 ['hotel-front-desk', 'bartender', 'server', 'line-cook', 'event-planner']),
        employer('roosevelt-hotel', 'The Roosevelt New Orleans', 'hospitality', 'cbd', 'medium', 'Grand hotel off '
                 'Canal Street with the Sazerac Bar and a famous Christmas lobby.',
                 ['hotel-front-desk', 'bartender', 'server', 'line-cook', 'event-planner']),
        employer('convention-center', 'Ernest N. Morial Convention Center', 'hospitality', 'cbd', 'large', 'One '
                 'of the biggest convention halls in the country, stretching along the river.',
                 ['event-planner', 'line-cook', 'server', 'construction-trades']),
        employer('commanders-employer', 'Commander\'s Palace', 'hospitality', 'garden-district', 'small', 'The '
                 'Brennan family restaurant that has trained generations of the city\'s chefs and servers.',
                 ['line-cook', 'server', 'bartender']),
        employer('audubon-institute', 'Audubon Nature Institute', 'tourism', 'uptown', 'medium', 'Runs the zoo, '
                 'aquarium, insectarium and Louisiana nature centers.',
                 ['biologist', 'tour-guide', 'event-planner', 'retail-associate']),
        employer('michoud', 'NASA Michoud Assembly Facility', 'aerospace', 'new-orleans-east', 'large', 'Vast '
                 'rocket factory where contractors build core stages for NASA\'s Space Launch System.',
                 ['defense-engineer', 'software-engineer', 'construction-trades', 'data-analyst']),
        employer('second-line-stages', 'Second Line Stages', 'film', 'lower-garden-district', 'medium', 'Sound '
                 'stages by the river serving the film and television productions drawn by Louisiana\'s tax '
                 'credits.', ['actor', 'performer', 'graphic-designer', 'construction-trades', 'event-planner']),
        employer('city-of-new-orleans', 'City of New Orleans', 'government', 'cbd', 'large', 'City agencies around '
                 'City Hall on Perdido Street.', ['government-analyst', 'social-worker', 'accountant']),
        employer('nola-public-schools', 'NOLA Public Schools', 'education', 'central-city', 'large', 'The public '
                 'school system, almost entirely run as charter schools, with campuses across the city.',
                 ['teacher', 'social-worker']),
        employer('pan-american-life', 'Pan-American Life Insurance Group', 'finance', 'cbd', 'medium', 'Insurance '
                 'company headquartered in New Orleans since 1911.',
                 ['financial-analyst', 'accountant', 'data-analyst', 'marketing-coordinator']),
        employer('times-picayune', 'The Times-Picayune | The New Orleans Advocate', 'media', 'cbd', 'small',
                 'The city\'s daily newspaper and website.', ['journalist', 'graphic-designer']),
        employer('wwoz', 'WWOZ 90.7 FM', 'media', 'french-quarter', 'small', 'Listener-supported community radio '
                 'for jazz and heritage music, broadcasting from the French Market.', ['journalist', 'musician']),
        employer('rouses', 'Rouses Markets', 'retail', 'cbd', 'large', 'The family-owned Louisiana grocery chain '
                 'with stores across the city and suburbs.', ['retail-associate', 'baker', 'line-cook']),
        employer('boh-bros', 'Boh Bros. Construction', 'construction', 'broadmoor', 'medium', 'Century-old '
                 'New Orleans contractor for bridges, levees and roads.', ['construction-trades']),
    ],
    'career_hubs': [
        hub('medical-district', 'Medical district and Ochsner', ['cbd', 'mid-city', 'metairie', 'uptown'],
            ['healthcare', 'biotech', 'education'], 'University Medical Center, the VA, the Tulane and LSU medical '
            'schools downtown, Touro and Children\'s Uptown and Ochsner on Jefferson Highway.'),
        hub('downtown-offices', 'Downtown offices', ['cbd'], ['finance', 'legal', 'energy', 'government', 'media'],
            'Law firms, oil and gas offices, banks and city government along Poydras Street.'),
        hub('tourism', 'Hotels, restaurants and music', ['french-quarter', 'cbd', 'marigny', 'garden-district'],
            ['hospitality', 'entertainment', 'tourism'], 'The biggest employer by far: hotels, restaurants, '
            'bars, tours, music clubs, the convention center and festival work.'),
        hub('river-and-port', 'River, port and shipyards', ['uptown', 'irish-channel', 'algiers-point',
            'lower-ninth-ward', 'new-orleans-east'], ['logistics', 'manufacturing', 'aerospace', 'construction'],
            'Wharves, shipyards and fabrication shops along the river and the Industrial Canal, and the Michoud '
            'rocket plant in the East.'),
        hub('campuses', 'Universities', ['uptown', 'gentilly', 'broadmoor', 'mid-city'], ['education'],
            'Tulane, Loyola, Xavier, Dillard, UNO, SUNO and Delgado.'),
        hub('film', 'Film and television', ['lower-garden-district', 'cbd', 'new-orleans-east'],
            ['film', 'entertainment'], 'Sound stages and location shoots that come and go with Louisiana\'s film '
            'tax credits.'),
    ],
    'climate': {
        'summary': 'Humid subtropical: long, hot, very humid summers with near-daily afternoon storms, mild short '
                   'winters with occasional cold snaps, and hurricane season from June through November.',
        'months': [
            {'high_f': 62, 'low_f': 44, 'rain_days': 10, 'note': 'Mild and damp; Carnival season begins.'},
            {'high_f': 66, 'low_f': 47, 'rain_days': 9, 'note': 'Parade weather is a gamble: warm or a cold snap.'},
            {'high_f': 73, 'low_f': 53, 'rain_days': 8, 'note': 'Azaleas, crawfish season and festivals begin.'},
            {'high_f': 79, 'low_f': 59, 'rain_days': 7, 'note': 'Festival season; warm and mostly dry.'},
            {'high_f': 86, 'low_f': 67, 'rain_days': 8, 'note': 'Heat and humidity build; snowball stands busy.'},
            {'high_f': 90, 'low_f': 73, 'rain_days': 13, 'note': 'Hurricane season opens; afternoon downpours.'},
            {'high_f': 91, 'low_f': 75, 'rain_days': 15, 'note': 'Hottest, wettest month; streets flood fast.'},
            {'high_f': 91, 'low_f': 75, 'rain_days': 14, 'note': 'Sweltering; peak hurricane watching begins.'},
            {'high_f': 88, 'low_f': 72, 'rain_days': 10, 'note': 'Still hot; height of hurricane season.'},
            {'high_f': 80, 'low_f': 62, 'rain_days': 7, 'note': 'First cool front brings relief; festivals return.'},
            {'high_f': 71, 'low_f': 52, 'rain_days': 7, 'note': 'Pleasant and dry; hurricane season ends.'},
            {'high_f': 64, 'low_f': 46, 'rain_days': 9, 'note': 'Mild, grey; Christmas lights in the oaks.'},
        ],
        'source': CLIMATE,
    },
    'annual_events': [
        event('twelfth-night', 'Twelfth Night', [1], 'french-quarter', 'Carnival opens on January 6: the Joan of '
              'Arc parade winds through the Quarter, the Phunny Phorty Phellows ride the St. Charles streetcar and '
              'the first king cakes are cut.'),
        event('krewe-du-vieux', 'Krewe du Vieux', [1, 2], 'marigny', 'A bawdy, satirical walking parade of '
              'hand-pulled floats and brass bands through the Marigny and the Quarter, weeks before Mardi Gras.'),
        event('chewbacchus', 'Krewe of Chewbacchus', [1, 2], 'marigny', 'A science-fiction walking parade of '
              'homemade costumes, droids and glowing throws on St. Claude Avenue.'),
        event('carnival-parades', 'Uptown Carnival parades', [1, 2, 3], 'uptown', 'For about two weeks before Mardi '
              'Gras, krewes like Muses, Nyx, Bacchus and Orpheus roll down St. Charles; families stake out the '
              'neutral ground with ladders, tents and grills.'),
        event('endymion', 'Endymion', [2, 3], 'mid-city', 'The Saturday super-krewe that rolls through Mid-City, '
              'where neighbours camp along Orleans Avenue and Canal Street from the night before.'),
        event('lundi-gras', 'Lundi Gras', [2, 3], 'cbd', 'The Monday before Mardi Gras, when Zulu and Rex arrive '
              'by river and Orpheus rolls through the night.'),
        event('mardi-gras-day', 'Mardi Gras Day', [2, 3], None, 'Fat Tuesday: Zulu and Rex parade from dawn, the '
              'Société de Sainte Anne walks in costume from Bywater, Mardi Gras Indians meet in the streets and '
              'at midnight the police sweep Bourbon Street to begin Lent.'),
        event('st-josephs-day', 'St. Joseph\'s Day altars', [3], None, 'On March 19, Italian-American families and '
              'churches build tiered altars of breads, cookies and fava beans open to anyone, and the Mardi Gras '
              'Indians come out at night.'),
        event('super-sunday', 'Super Sunday', [3], 'central-city', 'The Sunday nearest St. Joseph\'s Day, when '
              'Mardi Gras Indian gangs parade in their new beaded suits, Uptown from A.L. Davis Park and downtown '
              'from Hunter\'s Field.'),
        event('irish-channel-parade', 'Irish Channel St. Patrick\'s parade', [3], 'irish-channel', 'Marching clubs '
              'trade paper flowers for kisses and floats throw cabbages, carrots and potatoes for Irish stew.'),
        event('tennessee-williams-fest', 'Tennessee Williams & New Orleans Literary Festival', [3], 'french-quarter',
              'Readings, plays and a Stanley-and-Stella shouting contest in Jackson Square.'),
        event('wednesday-at-the-square', 'Wednesday at the Square', [3, 4, 5], 'cbd', 'Free after-work concerts in '
              'Lafayette Square each spring.'),
        event('french-quarter-fest', 'French Quarter Festival', [4], 'french-quarter', 'Four free days of local '
              'music on stages from Jackson Square to the riverfront, with food booths from neighbourhood '
              'restaurants.'),
        event('jazz-fest', 'New Orleans Jazz & Heritage Festival', [4, 5], 'bayou-st-john', 'Two weekends at the '
              'Fair Grounds: a dozen stages of jazz, gospel, blues, brass, zydeco and pop, crawfish Monica and '
              'Mardi Gras Indians in the Heritage Square.'),
        event('bayou-boogaloo', 'Mid-City Bayou Boogaloo', [5], 'bayou-st-john', 'A music festival on the banks of '
              'Bayou St. John, with people floating to the stages on homemade rafts.'),
        event('creole-tomato-fest', 'Creole Tomato Festival', [6], 'french-quarter', 'A French Market weekend '
              'celebrating the summer\'s first local tomatoes with cooking demos, Bloody Marys and music.'),
        event('essence-fest', 'Essence Festival of Culture', [7], 'cbd', 'Over the Fourth of July weekend, nights of '
              'R&B and hip-hop concerts in the Superdome and daytime talks and markets at the Convention Center.'),
        event('running-of-the-bulls', 'San Fermín in Nueva Orleans', [7], 'cbd', 'A New Orleans take on Pamplona '
              'where roller derby skaters with plastic bats chase runners dressed in white and red.'),
        event('satchmo-summerfest', 'Satchmo SummerFest', [8], 'french-quarter', 'A weekend for Louis Armstrong\'s '
              'birthday at the Old U.S. Mint, with trumpet tributes, seminars and a jazz Mass and second line.'),
        event('white-linen-night', 'White Linen Night', [8], 'cbd', 'Julia Street galleries open their doors on a '
              'hot August Saturday and the crowd wears white; Dirty Linen Night follows on Royal Street.'),
        event('southern-decadence', 'Southern Decadence', [8, 9], 'french-quarter', 'Labor Day weekend LGBTQ+ '
              'festival with a walking parade, balcony parties and huge crowds around Bourbon and St. Ann.'),
        event('second-line-season', 'Second line season', [8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6], None, 'Almost every '
              'Sunday from late summer to early summer, a social aid and pleasure club parades for hours through '
              'its neighbourhood behind a brass band, with a crowd dancing along.'),
        event('saints-season', 'Saints football season', [9, 10, 11, 12, 1], 'cbd', 'Black-and-gold Sundays: '
              'tailgates, "Who Dat" chants, church let out early and the Superdome shaking.'),
        event('pelicans-season', 'Pelicans basketball season', [10, 11, 12, 1, 2, 3, 4], 'cbd', 'NBA nights at the '
              'Smoothie King Center.'),
        event('voodoo-fest', 'Voodoo Music + Arts Experience', [10], 'mid-city', 'A Halloween-weekend rock, hip-hop '
              'and electronic festival held in City Park in most years since 1999, with costumes encouraged.'),
        event('halloween-in-the-quarter', 'Halloween in the Quarter', [10], 'french-quarter', 'The Krewe of Boo '
              'parade rolls, and on Halloween night the Quarter and Frenchmen Street fill with elaborate costumes.'),
        event('all-saints-day', 'All Saints\' Day', [11], None, 'Families whitewash and tidy their tombs and bring '
              'flowers to the cemeteries on November 1.'),
        event('po-boy-fest', 'Oak Street Po-Boy Festival', [11], 'carrollton', 'A Sunday when restaurants line Oak '
              'Street selling creative po-boys to crowds with music stages.'),
        event('bayou-classic', 'Bayou Classic', [11], 'cbd', 'Grambling and Southern play their Thanksgiving '
              'weekend football rivalry in the Superdome, with a battle of the bands and a parade.'),
        event('celebration-in-the-oaks', 'Celebration in the Oaks', [11, 12, 1], 'mid-city', 'City Park strings its '
              'live oaks with holiday lights and opens the carousel and rides at night.'),
        event('reveillon', 'Réveillon dinners', [12], 'french-quarter', 'Restaurants offer prix-fixe Christmas '
              'Réveillon menus revived from the old Creole tradition of a feast after midnight Mass.'),
        event('sugar-bowl', 'Allstate Sugar Bowl', [12, 1], 'cbd', 'The New Year\'s college football bowl game in '
              'the Superdome, with fans of both teams filling the Quarter.'),
    ],
    'holidays': [
        holiday('twelfth-night', 'Twelfth Night', 'observance', 'The start of Carnival season, when the first king '
                'cakes appear.', month=1, day=6),
        holiday('lundi-gras', 'Lundi Gras', 'observance', 'The Monday before Mardi Gras; many schools are already '
                'out and Zulu and Rex arrive on the riverfront.', easter=-48),
        holiday('mardi-gras', 'Mardi Gras', 'public', 'Fat Tuesday, a legal holiday in New Orleans: offices and '
                'schools close and the whole city is in costume or on a parade route.', easter=-47),
        holiday('ash-wednesday', 'Ash Wednesday', 'observance', 'The first day of Lent, with ashes on foreheads and '
                'the hangover of Carnival; Friday fish fries follow until Easter.', easter=-46),
        holiday('st-josephs-day', 'St. Joseph\'s Day', 'observance', 'Altars open in homes and churches and Mardi '
                'Gras Indians come out at night.', month=3, day=19),
        holiday('good-friday', 'Good Friday', 'public', 'A Louisiana state holiday; state offices close.',
                easter=-2),
        holiday('all-saints-day', 'All Saints\' Day', 'observance', 'A day for tending family tombs.', month=11,
                day=1),
    ],
    'local_color': [
        color('king-cake', 'King cake', 'dish', 'A ring of braided brioche or Danish dough, iced in purple, green and '
              'gold and hiding a small plastic baby; whoever gets the baby buys the next one. Eaten only between '
              'Twelfth Night and Mardi Gras.', ['dong-phuong', 'bywater-bakery', 'rouses-cbd'], ['winter']),
        color('red-beans-monday', 'Red beans and rice on Monday', 'dish', 'Monday was wash day, so a pot of red '
              'beans with ham bone simmered all day; restaurants and families still serve it every Monday.',
              ['buffas', 'mandinas']),
        color('crawfish-boil', 'Crawfish boil', 'custom', 'Sacks of live crawfish boiled with cayenne, corn, potatoes '
              'and garlic, dumped onto newspaper-covered tables in backyards and parks for an afternoon of peeling '
              'and beer.', ['bayou-st-john-water'], ['winter', 'spring']),
        color('po-boy', 'Po-boy', 'dish', 'A long sandwich on light, crackly French bread, filled with fried shrimp '
              'or oysters, or roast beef in gravy; "dressed" means with lettuce, tomato, pickles and mayo.',
              ['parkway-bakery', 'domilises', 'mahonys', 'mothers-restaurant']),
        color('gumbo', 'Gumbo', 'dish', 'A dark roux stew of seafood or chicken and andouille over rice, thickened '
              'with okra or filé; every family argues its own version is right.',
              ['dooky-chase', 'liuzzas-by-the-track'], ['fall', 'winter']),
        color('muffuletta', 'Muffuletta', 'dish', 'A round Sicilian sesame loaf piled with salami, ham, provolone and '
              'olive salad, born in the French Quarter\'s Italian groceries; a quarter is a meal.',
              ['napoleon-house']),
        color('beignets', 'Beignets and café au lait', 'dish', 'Square fried doughnuts buried in powdered sugar, '
              'eaten with milky coffee cut with chicory root; locals go early or late to dodge the line.',
              ['cafe-du-monde', 'morning-call']),
        color('snowball', 'Snowball', 'dish', 'Ice shaved as fine as snow and soaked in syrup, often with condensed '
              'milk or a scoop of ice cream inside; stands open in spring and close when it cools.',
              ['hansens-sno-bliz', 'plum-street-snoball', 'pandoras-snowballs'], SNOBALL),
        color('yakamein', 'Yakamein', 'dish', 'Beef noodle soup with soy, hot sauce and a boiled egg, sold from '
              'coolers at second lines and called "Old Sober" for what it does after a long night.'),
        color('charbroiled-oysters', 'Charbroiled oysters', 'dish', 'Oysters grilled on the half shell with garlic '
              'butter and cheese until they sizzle, eaten with French bread to mop up the butter.',
              ['dragos', 'acme-oyster-house']),
        color('bbq-shrimp', 'Barbecue shrimp', 'dish', 'Not barbecue at all: head-on Gulf shrimp baked in butter, '
              'black pepper and Worcestershire, with bread for the sauce.', ['pascals-manale']),
        color('banh-mi', 'Banh mi', 'dish', 'Vietnamese sandwiches on the same light, crusty bread as a po-boy; in '
              'the East they are often simply called Vietnamese po-boys.', ['dong-phuong', 'chef-menteur-strip']),
        color('sazerac', 'Sazerac', 'drink', 'Rye whiskey, Peychaud\'s bitters and sugar in an absinthe-rinsed '
              'glass, the city\'s official cocktail.', ['napoleon-house']),
        color('hurricane', 'Hurricane', 'drink', 'A sweet red rum punch in a tall curved glass, invented at Pat '
              'O\'Brien\'s and mostly drunk by visitors.', ['pat-obriens']),
        color('go-cup', 'Go-cups', 'custom', 'Drinking on the street is legal in plastic cups, so bars hand you one '
              'on the way out and parades, second lines and walks home all come with a drink in hand.',
              ['bourbon-street', 'frenchmen-street']),
        color('daiquiri-shops', 'Drive-through daiquiri shops', 'shop', 'Frozen daiquiris spin in rows of machines '
              'at strip-mall shops, some with drive-through windows; the lid has to stay taped over the straw '
              'hole.', ['genes-po-boys']),
        color('where-yat', '"Where y\'at?"', 'saying', 'The local "how are you", answered with "awright"; the '
              'broad Yat accent sounds closer to Brooklyn than to the Deep South.'),
        color('making-groceries', '"Making groceries"', 'saying', 'What New Orleanians call going grocery shopping, '
              'from the French "faire son marché".'),
        color('neutral-ground', '"Neutral ground"', 'saying', 'The grassy median of a boulevard, named for the strip '
              'of Canal Street that divided the Creole and American sides of town; where you stand for parades.',
              ['washington-avenue-neutral-ground']),
        color('lagniappe', 'Lagniappe', 'saying', 'A little something extra thrown in for free, like a thirteenth '
              'beignet or an extra scoop, and anything extra in general.'),
        color('yeah-you-right', '"Yeah you right"', 'saying', 'Emphatic agreement, often heard as "yeah you rite".'),
        color('second-line', 'Second lines', 'custom', 'Behind a social aid and pleasure club and its brass band '
              'comes the "second line" of anyone who joins in, dancing for hours through the neighbourhood with '
              'stops at bars along the route; jazz funerals end the same way.',
              ['treme', 'central-city', 'seventh-ward']),
        color('krewes-throws', 'Krewes and throws', 'custom', 'Carnival clubs called krewes build floats and toss '
              'beads, cups and doubloons; the prized throws are hand-decorated Zulu coconuts and Muses shoes, and '
              'families keep parade ladders for the kids.', ['mardi-gras-world'], ['winter']),
        color('mardi-gras-indians', 'Mardi Gras Indians', 'custom', 'Black New Orleanians in gangs led by a Big Chief '
              'sew elaborate beaded and feathered suits all year, then meet in the street on Mardi Gras, St. '
              'Joseph\'s night and Super Sunday to chant and see who is prettiest.',
              ['backstreet-museum', 'hunters-field', 'al-davis-park']),
        color('st-joseph-altar', 'St. Joseph\'s altars and lucky beans', 'custom', 'Visitors to a St. Joseph\'s '
              'altar take home a blessed fava bean for the wallet, said to keep you from going broke.',
              ['angelo-brocato'], ['spring']),
        color('hurricane-prep', 'Hurricane season', 'custom', 'From June to November people watch the tropics, keep '
              'water and batteries in, learn the contraflow route, and either evacuate or hold a hurricane party '
              'when a storm comes.', seasons=['summer', 'fall']),
        color('who-dat', 'New Orleans Saints', 'team', 'The NFL team, whose fans chant "Who dat say dey gonna beat dem '
              'Saints?"; the 2010 Super Bowl win after Katrina is still the city\'s happiest memory.',
              ['superdome'], ['fall', 'winter']),
        color('pelicans', 'New Orleans Pelicans', 'team', 'The NBA team at the Smoothie King Center.',
              ['smoothie-king-center'], ['fall', 'winter', 'spring']),
        color('brass-bands', 'Brass bands', 'other', 'Rebirth, the Dirty Dozen, Hot 8, the Soul Rebels and dozens of '
              'younger bands play second lines, club nights and street corners.',
              ['maple-leaf-bar', 'frenchmen-street', 'le-bon-temps-roule']),
    ],
    'prices': [
        price('coffee', 'Coffee', 2.5, 4, 'a cup'),
        price('latte', 'Latte', 4.5, 6.5),
        price('beignets', 'Beignets', 4, 6, 'an order of three'),
        price('po-boy', 'Po-boy', 12, 20, 'a full-size shrimp or roast beef'),
        price('cheap-lunch', 'Cheap lunch', 11, 18),
        price('dinner', 'Mid-range dinner', 35, 60, 'for one'),
        price('beer', 'Pint of beer', 5, 8, 'a pint'),
        price('cocktail', 'Cocktail', 12, 16),
        price('daiquiri', 'Frozen daiquiri', 7, 14, 'a large cup'),
        price('groceries', 'Groceries', 75, 115, 'a week, one person'),
        price('transit', 'Streetcar or bus fare', 1.25, 1.25, 'one way'),
        price('jazzy-pass', 'Jazzy Pass', 3, 3, 'a day of unlimited rides'),
        price('ferry', 'Algiers ferry fare', 2, 2, 'one way'),
        price('rideshare', 'Rideshare across town', 12, 28),
        price('movie', 'Movie ticket', 12, 16),
        price('gym', 'Gym membership', 30, 70, 'a month'),
        price('snowball', 'Snowball', 3, 7),
        price('crawfish', 'Boiled crawfish', 5, 10, 'a pound, by season'),
        price('king-cake', 'King cake', 20, 45, 'a whole cake'),
        price('music-cover', 'Club cover on Frenchmen', 0, 20),
    ],
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
