"""Curated New York City data. Run `python scripts/world/new_york.py` to rewrite the shipped JSON."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'cities' / 'new-york.json'
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


def event(id, name, months, hood, summary):
    return {'id': id, 'name': name, 'months': months, 'neighborhood': hood, 'summary': summary, 'source': S}


def color(id, name, kind, summary, places=(), seasons=()):
    return {'id': id, 'name': name, 'kind': kind, 'summary': summary, 'places': list(places),
            'seasons': list(seasons), 'source': S}


ALL = ['solo', 'friends', 'date', 'family']
ADULT = ['solo', 'friends', 'date']
DAY = ['morning', 'afternoon']
DINNER = ['evening']
NIGHT = ['evening', 'late']
WARM = ['spring', 'summer', 'fall']
CORE = ['subway', 'mta-bus', 'citi-bike']

CITY = {
    'schema_version': 1, 'id': 'new-york', 'name': 'New York', 'region': 'New York', 'country': 'US',
    'timezone': 'America/New_York', 'aliases': ['NYC', 'New York City', 'The Big Apple', 'New York, NY'],
    'summary': 'The largest city in the United States: five boroughs of dense neighborhoods tied together by a '
               '24-hour subway, home to Wall Street, Broadway, world-class museums and food from everywhere.',
    'lat': 40.71, 'lon': -74.01,
    'speeds': {'walk': 4.5, 'car': 18, 'rideshare': 18, 'bus': 10, 'subway': 25, 'ferry': 20,
               'commuter-rail': 50, 'bike-share': 13},
    # Rough heritage weights for residents' names (estimates, not census figures).
    'names': {'mix': {'hispanic': 3, 'anglo': 2.5, 'black-american': 2, 'jewish': 1.2, 'east-asian': 1.5,
                       'italian': 0.9, 'irish': 0.7, 'caribbean': 1, 'south-asian': 0.7, 'slavic': 0.6, 'arabic': 0.3,
                       'west-african': 0.4}},
    'sources': {
        S: {'kind': 'curated', 'title': 'New York places and neighborhoods written for Prospero Companion',
            'license': 'CC0-1.0', 'retrieved': '2026-10-05',
            'note': 'Well-known public places, institutions and employers from general knowledge. Businesses open '
                    'and close and rents move fast here: treat this as a snapshot for fiction. Rents are rounded '
                    'estimates of typical 2025 asking ranges, not listings. Coordinates are approximate '
                    'neighborhood centers.'},
        CLIMATE: {'kind': 'curated', 'title': 'Approximate monthly climate for New York (Central Park)',
                  'license': 'CC0-1.0', 'retrieved': '2026-10-05',
                  'note': 'Rounded values in line with NOAA 1991-2020 normals for Central Park; refresh with '
                          'scripts/world when network access to NOAA is available.'},
    },
    'neighborhoods': [
        # Manhattan
        hood('financial-district', 'Financial District', 'Wall Street, the World Trade Center and City Hall at the '
             'southern tip of Manhattan, with ferries leaving from the Battery.', ['business', 'historic',
             'waterfront', 'touristy'], 40.707, -74.009, 'very-high', ([3200, 4000], [4200, 5500], [5800, 8500]),
             ['apartment-tower', 'converted-office', 'condo'], 'high',
             CORE + ['path', 'nyc-ferry', 'staten-island-ferry']),
        hood('soho', 'SoHo', 'Cast-iron loft buildings and cobbled side streets packed with flagship shops and '
             'galleries.', ['shopping', 'architecture', 'upscale', 'artsy'], 40.723, -74.000, 'very-high',
             ([3300, 4300], [4300, 6000], [6000, 9500]), ['loft', 'walk-up', 'condo'], 'high', CORE),
        hood('lower-east-side', 'Lower East Side', 'Old tenement blocks of immigrant history, now mixing delis, '
             'galleries and late-night bars, next to Chinatown.', ['historic', 'nightlife', 'food', 'gritty'],
             40.715, -73.987, 'high', ([2700, 3500], [3400, 4600], [4300, 6200]),
             ['tenement', 'walk-up', 'public-housing', 'new-build'], 'high', CORE + ['nyc-ferry']),
        hood('east-village', 'East Village', 'Walk-up apartments, cheap eats, dive bars and NYU students around '
             'Tompkins Square Park and St. Marks Place.', ['students', 'nightlife', 'food', 'punk-history'], 40.727,
             -73.984, 'high', ([2700, 3500], [3400, 4600], [4300, 6200]), ['walk-up', 'tenement'], 'high', CORE),
        hood('greenwich-village', 'Greenwich Village', 'Crooked tree-lined streets of townhouses, jazz clubs and '
             'cafes around Washington Square and NYU, running west into the West Village.',
             ['historic', 'lgbtq-friendly', 'jazz', 'students', 'leafy'], 40.733, -74.002, 'very-high',
             ([3200, 4200], [4200, 5800], [5800, 9000]), ['walk-up', 'townhouse', 'prewar-apartment'], 'high',
             CORE + ['path']),
        hood('chelsea', 'Chelsea', 'Art galleries, the High Line, Chelsea Market and big tech offices on the West '
             'Side between the Meatpacking District and Hudson Yards.', ['art', 'lgbtq-friendly', 'tech',
             'upscale'], 40.746, -74.001, 'very-high', ([3200, 4100], [4300, 5600], [5800, 8500]),
             ['walk-up', 'apartment-tower', 'public-housing'], 'high', CORE + ['path']),
        hood('flatiron', 'Flatiron and Union Square', 'Startup offices and showrooms around the Flatiron Building, '
             'Madison Square Park and the Union Square Greenmarket.', ['tech', 'business', 'food', 'central'], 40.740,
             -73.990, 'very-high', ([3200, 4100], [4300, 5600], [5800, 8500]),
             ['loft', 'prewar-apartment', 'apartment-tower'], 'high', CORE + ['path']),
        hood('kips-bay', 'Kips Bay and Murray Hill', 'East Side blocks of mid-rise apartments beside the hospital '
             'row on First Avenue, popular with young professionals and medical staff.',
             ['medical', 'young-professional', 'practical'], 40.743, -73.978, 'high',
             ([2900, 3600], [3700, 4700], [4800, 6800]), ['apartment-tower', 'walk-up', 'co-op'], 'high',
             CORE + ['nyc-ferry']),
        hood('midtown', 'Midtown', 'The skyscraper core: Times Square, the Theater District, Rockefeller Center, '
             'Grand Central and Penn Station, busiest on weekdays.', ['business', 'touristy', 'theater', 'central'],
             40.755, -73.984, 'very-high', ([3000, 3900], [4000, 5200], [5300, 7800]),
             ['apartment-tower', 'condo'], 'high', CORE + ['path', 'lirr', 'metro-north']),
        hood('hudson-yards', 'Hudson Yards', 'A new district of glass towers, offices and a mall built over the '
             'West Side rail yards.', ['new-build', 'corporate', 'upscale'], 40.754, -74.001, 'very-high',
             ([3800, 4800], [5000, 6800], [7500, 11000]), ['apartment-tower', 'condo'], 'medium',
             ['subway', 'mta-bus', 'lirr', 'citi-bike']),
        hood('upper-west-side', 'Upper West Side', 'Prewar apartment buildings and brownstones between Central Park '
             'and Riverside Park, with Lincoln Center and the Natural History Museum.',
             ['family', 'cultural', 'leafy', 'residential'], 40.787, -73.975, 'high',
             ([2600, 3300], [3500, 4700], [4800, 7500]), ['prewar-apartment', 'brownstone', 'co-op'], 'high', CORE),
        hood('upper-east-side', 'Upper East Side', 'Museum Mile on Fifth Avenue, Park Avenue co-ops and busier '
             'rental blocks toward the East River, plus a cluster of major hospitals.',
             ['affluent', 'museums', 'medical', 'residential'], 40.773, -73.957, 'high',
             ([2400, 3100], [3200, 4300], [4300, 6800]), ['co-op', 'prewar-apartment', 'walk-up', 'townhouse'],
             'high', CORE + ['nyc-ferry']),
        hood('morningside-heights', 'Morningside Heights', 'The academic neighborhood around Columbia University '
             'and the Cathedral of St. John the Divine.', ['academic', 'students', 'quiet'], 40.808, -73.962,
             'mid', ([2100, 2800], [2800, 3600], [3400, 4800]), ['prewar-apartment', 'student-housing'], 'high',
             CORE),
        hood('harlem', 'Harlem', 'Brownstone blocks with deep African American and Latino cultural history, centered '
             'on 125th Street and the Apollo.', ['historic', 'music', 'brownstones', 'food'], 40.811, -73.946,
             'mid', ([2000, 2600], [2500, 3300], [3100, 4300]), ['brownstone', 'prewar-apartment', 'public-housing'],
             'high', CORE + ['metro-north']),
        # Brooklyn
        hood('williamsburg', 'Williamsburg', 'Former warehouses turned waterfront towers, bars, music venues and '
             'restaurants one subway stop from Manhattan, with a large Hasidic community to the south.',
             ['nightlife', 'young-professional', 'waterfront', 'food', 'music'], 40.714, -73.957, 'very-high',
             ([3000, 3800], [3800, 4900], [4700, 6800]), ['apartment-tower', 'walk-up', 'loft'], 'high',
             CORE + ['nyc-ferry']),
        hood('dumbo', 'DUMBO', 'Cobbled streets of converted warehouses under the Manhattan and Brooklyn Bridges, '
             'beside Brooklyn Bridge Park.', ['views', 'waterfront', 'upscale', 'photogenic'], 40.703, -73.989,
             'very-high', ([3400, 4200], [4300, 5800], [6000, 8500]), ['loft', 'condo'], 'high',
             CORE + ['nyc-ferry']),
        hood('downtown-brooklyn', 'Downtown Brooklyn', 'Brooklyn\'s civic and office center, now dense with rental '
             'towers, beside Fort Greene, Barclays Center and BAM.', ['business', 'new-build', 'central',
             'students'], 40.693, -73.987, 'high', ([3000, 3700], [3700, 4700], [4700, 6300]),
             ['apartment-tower', 'brownstone'], 'high', CORE + ['lirr']),
        hood('park-slope', 'Park Slope', 'Brownstone streets of young families sloping down from Prospect Park.',
             ['family', 'leafy', 'brownstones', 'park'], 40.672, -73.977, 'high',
             ([2400, 3100], [3100, 4100], [3900, 5700]), ['brownstone', 'walk-up'], 'high', CORE),
        hood('bushwick', 'Bushwick', 'Warehouses covered in murals, artist lofts, late-night clubs and a long-standing '
             'Latino community.', ['arts', 'nightlife', 'street-art', 'affordable'], 40.697, -73.918, 'mid',
             ([2000, 2600], [2500, 3300], [3000, 4000]), ['walk-up', 'loft', 'rowhouse'], 'medium', CORE),
        hood('coney-island', 'Coney Island', 'The seaside amusement district at the end of the subway lines, quiet '
             'in winter and packed on summer weekends.', ['beach', 'amusements', 'seaside', 'affordable'], 40.575,
             -73.985, 'low', ([1600, 2100], [1900, 2500], [2300, 3100]), ['apartment-tower', 'public-housing'],
             'medium', ['subway', 'mta-bus']),
        # Queens
        hood('astoria', 'Astoria', 'A diverse, food-loving neighborhood of Greek tavernas, beer gardens and '
             'two-family houses near the East River.', ['diverse', 'food', 'young-professional', 'neighbourly'],
             40.764, -73.923, 'mid', ([2100, 2700], [2500, 3300], [3000, 4000]),
             ['walk-up', 'two-family-house', 'apartment'], 'high', CORE + ['nyc-ferry']),
        hood('long-island-city', 'Long Island City', 'Glass towers on the Queens waterfront with Manhattan skyline '
             'views, plus warehouses, film studios and MoMA PS1.', ['new-build', 'views', 'waterfront', 'arts'],
             40.746, -73.949, 'very-high', ([3200, 3900], [4000, 5000], [5200, 7200]), ['apartment-tower', 'condo'],
             'high', CORE + ['nyc-ferry', 'lirr']),
        hood('flushing', 'Flushing', 'A busy Chinese and Korean commercial center around Main Street, beside '
             'Flushing Meadows Corona Park with Citi Field and the US Open grounds.',
             ['diverse', 'food', 'busy', 'family'], 40.759, -73.830, 'mid', ([1800, 2400], [2200, 2900],
             [2700, 3600]), ['apartment', 'co-op', 'single-family'], 'high', ['subway', 'mta-bus', 'lirr']),
        # The Bronx
        hood('concourse', 'Concourse', 'Art Deco apartment houses along the Grand Concourse, a short walk from '
             'Yankee Stadium.', ['historic', 'sports', 'art-deco', 'affordable'], 40.828, -73.922, 'low',
             ([1600, 2100], [1900, 2500], [2300, 3100]), ['prewar-apartment', 'public-housing'], 'medium',
             CORE + ['metro-north']),
        hood('belmont', 'Belmont (Arthur Avenue)', 'The Bronx\'s Little Italy of bakeries, butchers and red-sauce '
             'restaurants, between Fordham University and the Bronx Zoo.', ['food', 'italian', 'students',
             'neighbourly'], 40.855, -73.887, 'low', ([1500, 2000], [1800, 2400], [2200, 2900]),
             ['walk-up', 'two-family-house', 'apartment'], 'medium', ['subway', 'mta-bus', 'metro-north']),
    ],
    'transit': [
        {'id': 'subway', 'name': 'New York City Subway', 'kind': 'subway', 'summary': 'The 24-hour MTA subway, '
         'with lettered and numbered lines across Manhattan, Brooklyn, Queens and the Bronx.', 'source': S},
        {'id': 'mta-bus', 'name': 'MTA New York City buses', 'kind': 'bus', 'summary': 'Local, Select Bus Service '
         'and express routes in all five boroughs; slow in Manhattan traffic.', 'source': S},
        {'id': 'nyc-ferry', 'name': 'NYC Ferry', 'kind': 'ferry', 'summary': 'East River and harbor ferry routes '
         'linking Wall Street, Midtown, Brooklyn, Queens, the Bronx and the Rockaways.', 'source': S},
        {'id': 'staten-island-ferry', 'name': 'Staten Island Ferry', 'kind': 'ferry', 'summary': 'Free 24-hour '
         'ferry from Whitehall Terminal to St. George, passing the Statue of Liberty.', 'source': S},
        {'id': 'path', 'name': 'PATH', 'kind': 'subway', 'summary': 'Port Authority trains from Lower Manhattan '
         'and Sixth Avenue to Hoboken, Jersey City and Newark.', 'source': S},
        {'id': 'lirr', 'name': 'Long Island Rail Road', 'kind': 'commuter-rail', 'summary': 'Commuter rail from '
         'Penn Station, Grand Central Madison and Atlantic Terminal through Queens to Long Island.', 'source': S},
        {'id': 'metro-north', 'name': 'Metro-North Railroad', 'kind': 'commuter-rail', 'summary': 'Commuter rail '
         'from Grand Central through Harlem and the Bronx to Westchester and Connecticut.', 'source': S},
        {'id': 'citi-bike', 'name': 'Citi Bike', 'kind': 'bike-share', 'summary': 'Docked bike share, including '
         'e-bikes, across Manhattan and much of Brooklyn, Queens and the Bronx.', 'source': S},
    ],
    'places': [
        # Financial District
        place('statue-of-liberty', 'Statue of Liberty and Ellis Island', 'landmark', 'financial-district', 'Ferries '
              'from Battery Park to Liberty Island and the Ellis Island immigration museum.', ['iconic', 'history',
              'ferry'], '$$', 'mixed', ALL, DAY),
        place('911-memorial', '9/11 Memorial & Museum', 'museum', 'financial-district', 'Twin reflecting pools in '
              'the footprints of the towers, with an underground museum.', ['history', 'memorial', 'rainy-day'],
              '$$', 'mixed', ['solo', 'family', 'friends'], DAY),
        place('staten-island-ferry-ride', 'Staten Island Ferry ride', 'attraction', 'financial-district', 'A free '
              'harbor crossing with views of the skyline and the Statue of Liberty.', ['free', 'views', 'water'],
              'free', 'mixed', ALL, ['morning', 'afternoon', 'evening']),
        place('dead-rabbit', 'The Dead Rabbit', 'bar', 'financial-district', 'Irish-style taproom and cocktail '
              'parlour on Water Street, a regular on world best-bar lists.', ['cocktails', 'irish', 'pub'], '$$$',
              'indoor', ['friends', 'date', 'coworkers'], NIGHT),
        # SoHo
        place('soho-shopping', 'SoHo shopping streets', 'shopping', 'soho', 'Flagship stores and boutiques along '
              'Broadway, Prince and Spring Streets.', ['fashion', 'boutiques', 'walk'], '$$$', 'outdoor',
              ['friends', 'solo', 'date'], ['afternoon']),
        place('balthazar', 'Balthazar', 'restaurant', 'soho', 'Long-running Parisian-style brasserie on Spring '
              'Street with a bakery next door.', ['brasserie', 'brunch', 'classic'], '$$$', 'indoor',
              ['date', 'friends', 'coworkers'], ['morning', 'afternoon', 'evening'], cuisine='french'),
        # Lower East Side
        place('katzs', 'Katz\'s Delicatessen', 'restaurant', 'lower-east-side', 'Cavernous deli on Houston Street '
              'serving hand-cut pastrami since the nineteenth century.', ['deli', 'pastrami', 'iconic', 'historic'],
              '$$', 'indoor', ALL, ['morning', 'afternoon', 'evening', 'late'], cuisine='jewish-deli'),
        place('russ-and-daughters', 'Russ & Daughters', 'restaurant', 'lower-east-side', 'Family-run "appetizing" '
              'shop on Houston Street for bagels, lox and smoked fish since 1914.', ['bagels', 'smoked-fish',
              'historic'], '$$', 'indoor', ALL, DAY, cuisine='jewish-appetizing'),
        place('essex-market', 'Essex Market', 'market', 'lower-east-side', 'Public market hall with butchers, '
              'cheesemongers and lunch counters, now in a modern building on Delancey Street.', ['food', 'market',
              'local'], '$', 'indoor', ALL, DAY),
        # East Village
        place('mcsorleys', 'McSorley\'s Old Ale House', 'bar', 'east-village', 'Sawdust-floored saloon dating '
              'to the 1850s that serves only its own light or dark ale.', ['historic', 'dive', 'beer'], '$',
              'indoor', ['friends', 'solo'], ['afternoon', 'evening', 'late']),
        place('veselka', 'Veselka', 'restaurant', 'east-village', 'Ukrainian diner on Second Avenue known for '
              'pierogi and borscht, open from breakfast to late.', ['diner', 'pierogi', 'late-night'], '$$',
              'indoor', ALL, ['morning', 'afternoon', 'evening', 'late'], cuisine='ukrainian'),
        place('venieros', 'Veniero\'s Pasticceria', 'cafe', 'east-village', 'Italian pastry shop and cafe on '
              'East 11th Street dating to the 1890s.', ['dessert', 'cannoli', 'historic'], '$', 'indoor', ALL,
              ['afternoon', 'evening'], cuisine='italian-pastry'),
        # Greenwich Village
        place('washington-square-park', 'Washington Square Park', 'park', 'greenwich-village', 'The arch, the '
              'fountain, chess players, buskers and NYU students.', ['people-watching', 'music', 'iconic'],
              'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('joes-pizza', 'Joe\'s Pizza', 'restaurant', 'greenwich-village', 'Classic New York slice counter on '
              'Carmine Street, open since 1975.', ['pizza', 'slice', 'quick'], '$', 'indoor', ALL,
              ['afternoon', 'evening', 'late'], cuisine='pizza'),
        place('stonewall-inn', 'The Stonewall Inn', 'bar', 'greenwich-village', 'Gay bar on Christopher Street '
              'where the 1969 uprising began, now part of a national monument.', ['lgbtq', 'history', 'bar'], '$$',
              'indoor', ['friends', 'solo', 'date'], NIGHT),
        place('caffe-reggio', 'Caffe Reggio', 'cafe', 'greenwich-village', 'Dim, art-filled MacDougal Street '
              'coffeehouse open since 1927.', ['coffee', 'historic', 'cosy'], '$', 'indoor', ADULT,
              ['afternoon', 'evening', 'late'], cuisine='italian-cafe'),
        place('whitney-museum', 'Whitney Museum of American Art', 'museum', 'greenwich-village', 'Modern and '
              'contemporary American art in a Renzo Piano building at the foot of the High Line.', ['art',
              'terraces', 'rainy-day'], '$$', 'indoor', ADULT, ['afternoon', 'evening']),
        # Chelsea
        place('high-line', 'The High Line', 'park', 'chelsea', 'Elevated park on an old freight rail line running '
              'from the Meatpacking District to Hudson Yards.', ['walk', 'views', 'gardens', 'iconic'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('chelsea-market', 'Chelsea Market', 'market', 'chelsea', 'Food hall in the old Nabisco factory, with '
              'tech offices upstairs.', ['food-hall', 'rainy-day', 'touristy'], '$$', 'indoor', ALL,
              ['morning', 'afternoon', 'evening']),
        place('chelsea-piers', 'Chelsea Piers', 'fitness', 'chelsea', 'Hudson River sports complex with a gym, '
              'golf range, ice rinks and climbing walls.', ['gym', 'sports', 'skating'], '$$$', 'mixed',
              ['solo', 'friends', 'family'], ['morning', 'afternoon', 'evening']),
        # Flatiron and Union Square
        place('union-square-greenmarket', 'Union Square Greenmarket', 'market', 'flatiron', 'The city\'s best-known '
              'farmers\' market, four days a week.', ['farmers-market', 'local', 'food'], '$', 'outdoor', ALL,
              ['morning', 'afternoon']),
        place('madison-square-park', 'Madison Square Park', 'park', 'flatiron', 'Small park facing the Flatiron '
              'Building, with rotating public art and the original Shake Shack.', ['park', 'art', 'burgers'],
              'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('strand-bookstore', 'Strand Book Store', 'shopping', 'flatiron', 'Huge independent bookshop at '
              'Broadway and 12th Street, famous for "18 miles of books".', ['books', 'rainy-day', 'browse'], '$',
              'indoor', ['solo', 'date', 'friends'], ['morning', 'afternoon', 'evening']),
        # Midtown
        place('times-square', 'Times Square', 'landmark', 'midtown', 'Neon billboards, crowds and costumed '
              'characters at the crossroads of the Theater District.', ['iconic', 'touristy', 'lights'], 'free',
              'outdoor', ALL, ['afternoon', 'evening', 'late']),
        place('broadway-theatres', 'Broadway theaters', 'venue', 'midtown', 'Around forty large theaters in the '
              'blocks around Times Square staging musicals and plays eight times a week.', ['theater', 'musicals',
              'iconic'], '$$$$', 'indoor', ['date', 'friends', 'family'], ['afternoon', 'evening']),
        place('rockefeller-center', 'Rockefeller Center', 'landmark', 'midtown', 'Art Deco complex with the '
              'Top of the Rock observation deck, a winter ice rink and the Christmas tree.', ['art-deco', 'views',
              'skating', 'iconic'], '$$', 'mixed', ALL, ['morning', 'afternoon', 'evening']),
        place('empire-state-building', 'Empire State Building', 'attraction', 'midtown', 'Art Deco skyscraper '
              'with open-air observation decks on the 86th floor.', ['views', 'iconic', 'art-deco'], '$$$', 'mixed',
              ALL, ['morning', 'afternoon', 'evening', 'late']),
        place('grand-central', 'Grand Central Terminal', 'landmark', 'midtown', 'Beaux-Arts rail terminal with a '
              'celestial ceiling, a food hall and the Whispering Gallery.', ['architecture', 'trains', 'iconic'],
              'free', 'indoor', ALL, ['morning', 'afternoon', 'evening']),
        place('grand-central-oyster-bar', 'Grand Central Oyster Bar', 'restaurant', 'midtown', 'Vaulted, tiled '
              'seafood restaurant beneath Grand Central, open since 1913.', ['oysters', 'historic', 'seafood'],
              '$$$', 'indoor', ['coworkers', 'date', 'solo'], ['afternoon', 'evening'], cuisine='seafood'),
        place('moma', 'Museum of Modern Art', 'museum', 'midtown', 'Major modern art collection on West 53rd '
              'Street, from Van Gogh\'s "The Starry Night" to contemporary design.', ['art', 'iconic', 'rainy-day'],
              '$$$', 'indoor', ALL, ['morning', 'afternoon', 'evening']),
        place('madison-square-garden', 'Madison Square Garden', 'stadium', 'midtown', 'Arena above Penn Station, '
              'home of the Knicks and Rangers and a major concert venue.', ['basketball', 'hockey', 'concerts'],
              '$$$', 'indoor', ['friends', 'family', 'date'], ['evening']),
        # Hudson Yards
        place('edge-observation-deck', 'Edge', 'attraction', 'hudson-yards', 'Glass-floored outdoor observation '
              'deck jutting from the 100th floor of 30 Hudson Yards.', ['views', 'thrill', 'sunset'], '$$$',
              'outdoor', ['date', 'friends', 'family'], ['afternoon', 'evening']),
        # Upper West Side
        place('central-park', 'Central Park', 'park', 'upper-west-side', 'The 843-acre park between the Upper West '
              'and Upper East Sides, with lakes, meadows, a reservoir loop and the Delacorte Theater.', ['park',
              'running', 'iconic', 'boating'], 'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('amnh', 'American Museum of Natural History', 'museum', 'upper-west-side', 'Dinosaur halls, the blue '
              'whale and the Hayden Planetarium on Central Park West.', ['science', 'dinosaurs', 'kids',
              'rainy-day'], '$$', 'indoor', ALL, DAY),
        place('lincoln-center', 'Lincoln Center', 'venue', 'upper-west-side', 'Performing arts campus for the '
              'Metropolitan Opera, New York Philharmonic, New York City Ballet and Juilliard.', ['opera', 'ballet',
              'classical', 'fountain'], '$$$$', 'indoor', ['date', 'solo', 'family'], ['evening']),
        place('levain-bakery', 'Levain Bakery', 'cafe', 'upper-west-side', 'Basement bakery on West 74th Street '
              'known for enormous six-ounce cookies.', ['cookies', 'bakery', 'line'], '$', 'indoor', ALL, DAY,
              cuisine='bakery'),
        # Upper East Side
        place('the-met', 'The Metropolitan Museum of Art', 'museum', 'upper-east-side', 'One of the world\'s great '
              'art museums, on Fifth Avenue at the edge of Central Park, with a summer rooftop garden.', ['art',
              'iconic', 'rainy-day'], '$$', 'indoor', ALL, ['morning', 'afternoon', 'evening']),
        place('guggenheim', 'Solomon R. Guggenheim Museum', 'museum', 'upper-east-side', 'Frank Lloyd Wright\'s '
              'spiralling museum of modern and contemporary art.', ['art', 'architecture', 'rainy-day'], '$$',
              'indoor', ADULT, DAY),
        place('bemelmans-bar', 'Bemelmans Bar', 'bar', 'upper-east-side', 'Piano bar in the Carlyle Hotel with '
              'murals by the creator of "Madeline".', ['cocktails', 'piano', 'classic'], '$$$$', 'indoor',
              ['date', 'friends'], NIGHT),
        # Morningside Heights
        place('st-john-the-divine', 'Cathedral of St. John the Divine', 'landmark', 'morningside-heights', 'Vast, '
              'still-unfinished Episcopal cathedral on Amsterdam Avenue.', ['architecture', 'quiet', 'history'],
              '$', 'indoor', ['solo', 'family', 'date'], DAY),
        # Harlem
        place('apollo-theater', 'Apollo Theater', 'venue', 'harlem', 'Historic 125th Street theater famous for '
              'its Wednesday Amateur Night.', ['music', 'history', 'comedy'], '$$', 'indoor', ['friends', 'date',
              'family'], ['evening']),
        place('sylvias', 'Sylvia\'s', 'restaurant', 'harlem', 'Soul food restaurant on Lenox Avenue since 1962, '
              'with a Sunday gospel brunch.', ['soul-food', 'brunch', 'historic'], '$$', 'indoor', ALL,
              ['morning', 'afternoon', 'evening'], cuisine='soul-food'),
        # Williamsburg
        place('smorgasburg', 'Smorgasburg Williamsburg', 'market', 'williamsburg', 'Saturday outdoor food market '
              'on the waterfront with dozens of vendors and skyline views.', ['food', 'waterfront', 'weekend'],
              '$$', 'outdoor', ALL, ['morning', 'afternoon'], WARM),
        place('peter-luger', 'Peter Luger Steak House', 'restaurant', 'williamsburg', 'Old-school German-style '
              'steakhouse under the Williamsburg Bridge, open since 1887.', ['steak', 'historic', 'old-school'],
              '$$$$', 'indoor', ['date', 'friends', 'coworkers', 'family'], ['afternoon', 'evening'],
              cuisine='steakhouse'),
        place('devocion', 'Devoción', 'cafe', 'williamsburg', 'Skylit Colombian coffee roastery with a green wall.',
              ['coffee', 'roastery', 'laptop'], '$', 'indoor', ['solo', 'friends', 'date'], DAY, cuisine='coffee'),
        # DUMBO
        place('brooklyn-bridge', 'Brooklyn Bridge walk', 'landmark', 'dumbo', 'The 1883 suspension bridge\'s '
              'elevated promenade from DUMBO to City Hall.', ['iconic', 'walk', 'views'], 'free', 'outdoor', ALL,
              ['morning', 'afternoon', 'evening']),
        place('brooklyn-bridge-park', 'Brooklyn Bridge Park', 'park', 'dumbo', 'Piers turned into lawns, sports '
              'fields and Jane\'s Carousel along the Brooklyn waterfront.', ['waterfront', 'views', 'sunset'],
              'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('julianas', 'Juliana\'s', 'restaurant', 'dumbo', 'Coal-fired pizzeria at the foot of the Brooklyn '
              'Bridge.', ['pizza', 'coal-oven'], '$$', 'indoor', ALL, ['afternoon', 'evening'], cuisine='pizza'),
        # Downtown Brooklyn
        place('barclays-center', 'Barclays Center', 'stadium', 'downtown-brooklyn', 'Arena at Atlantic Avenue, home '
              'of the Brooklyn Nets and big concerts.', ['basketball', 'concerts'], '$$$', 'indoor',
              ['friends', 'family', 'date'], ['evening']),
        place('juniors', 'Junior\'s', 'restaurant', 'downtown-brooklyn', 'Diner on Flatbush Avenue Extension '
              'famous for its cheesecake since 1950.', ['cheesecake', 'diner', 'classic'], '$$', 'indoor', ALL,
              ['morning', 'afternoon', 'evening'], cuisine='american-diner'),
        # Park Slope
        place('prospect-park', 'Prospect Park', 'park', 'park-slope', 'Brooklyn\'s great park by the designers of '
              'Central Park, with the Long Meadow, a lake and Saturday Grand Army Plaza Greenmarket.', ['park',
              'running', 'picnic', 'dogs'], 'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        # Bushwick
        place('house-of-yes', 'House of Yes', 'nightlife', 'bushwick', 'Club and performance space with aerialists, '
              'costumed theme nights and dancing until late.', ['dancing', 'costumes', 'queer-friendly'], '$$',
              'indoor', ['friends', 'date'], ['late']),
        place('robertas', 'Roberta\'s', 'restaurant', 'bushwick', 'Wood-fired pizza in a cinderblock building that '
              'helped put Bushwick on the food map.', ['pizza', 'garden'], '$$', 'mixed', ADULT,
              ['afternoon', 'evening'], cuisine='pizza'),
        # Coney Island
        place('coney-island-beach', 'Coney Island Beach and Boardwalk', 'beach', 'coney-island', 'Wide public sand '
              'beach and wooden boardwalk with lifeguards in season.', ['beach', 'boardwalk', 'swimming'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening'], ['summer']),
        place('luna-park', 'Luna Park and the Cyclone', 'attraction', 'coney-island', 'Amusement park rides beside '
              'the 1927 Cyclone wooden roller coaster and the Wonder Wheel.', ['rides', 'retro', 'thrill'], '$$',
              'outdoor', ['family', 'friends', 'date'], ['afternoon', 'evening'], WARM),
        place('nathans-famous', 'Nathan\'s Famous', 'restaurant', 'coney-island', 'The original 1916 hot dog stand '
              'on Surf Avenue, site of the Fourth of July eating contest.', ['hot-dogs', 'historic', 'quick'], '$',
              'mixed', ALL, ['afternoon', 'evening'], cuisine='hot-dogs'),
        # Astoria
        place('museum-of-the-moving-image', 'Museum of the Moving Image', 'museum', 'astoria', 'Film, television '
              'and video game museum with a cinema, beside Kaufman Astoria Studios.', ['film', 'games',
              'rainy-day'], '$$', 'indoor', ALL, ['afternoon', 'evening']),
        place('bohemian-hall', 'Bohemian Hall & Beer Garden', 'bar', 'astoria', 'Czech beer hall with a big '
              'tree-shaded garden, open since 1910.', ['beer-garden', 'historic', 'outdoor'], '$$', 'mixed',
              ['friends', 'coworkers'], ['afternoon', 'evening'], cuisine='czech'),
        # Long Island City
        place('moma-ps1', 'MoMA PS1', 'museum', 'long-island-city', 'Contemporary art in a former public school, '
              'with summer courtyard parties.', ['art', 'contemporary', 'experimental'], '$$', 'indoor', ADULT,
              ['afternoon']),
        # Flushing
        place('flushing-meadows-corona-park', 'Flushing Meadows Corona Park', 'park', 'flushing', 'Former '
              'World\'s Fair grounds with the Unisphere, the Queens Museum and lakes.', ['park', 'unisphere',
              'history'], 'free', 'outdoor', ALL, DAY),
        place('usta-tennis-center', 'USTA Billie Jean King National Tennis Center', 'stadium', 'flushing', 'Home '
              'of the US Open, with Arthur Ashe Stadium at its center.', ['tennis', 'sports'], '$$$', 'outdoor',
              ['friends', 'family', 'date'], ['afternoon', 'evening'], ['summer']),
        place('citi-field', 'Citi Field', 'stadium', 'flushing', 'The New York Mets\' ballpark beside Flushing '
              'Meadows.', ['baseball', 'sports'], '$$', 'outdoor', ALL, ['afternoon', 'evening'],
              ['spring', 'summer', 'fall']),
        # The Bronx
        place('yankee-stadium', 'Yankee Stadium', 'stadium', 'concourse', 'The Yankees\' ballpark on 161st Street, '
              'with Monument Park beyond the outfield.', ['baseball', 'sports', 'iconic'], '$$$', 'outdoor', ALL,
              ['afternoon', 'evening'], ['spring', 'summer', 'fall']),
        place('arthur-avenue-market', 'Arthur Avenue Retail Market', 'market', 'belmont', 'Indoor Italian market '
              'from the 1940s with butchers, a cigar roller and sandwich counters.', ['food', 'italian',
              'historic'], '$', 'indoor', ALL, DAY),
        place('bronx-zoo', 'Bronx Zoo', 'attraction', 'belmont', 'One of the largest city zoos in the country, '
              'in Bronx Park beside Belmont.', ['animals', 'kids', 'big'], '$$', 'outdoor', ['family', 'date',
              'friends'], DAY, WARM),
        # Everyday neighborhood spots: cafes, diners, pubs, libraries, parks and markets.
        place('fraunces-tavern', 'Fraunces Tavern', 'restaurant', 'financial-district', 'Colonial-era tavern where '
              'Washington said farewell to his officers, now a pub and restaurant above a small museum.',
              ['historic', 'pub', 'museum'], '$$', 'indoor', ['friends', 'coworkers', 'family'],
              ['afternoon', 'evening'], cuisine='american-pub'),
        place('the-battery', 'The Battery', 'park', 'financial-district', 'Harbor-front park at Manhattan\'s tip '
              'with gardens, a bikeway, the SeaGlass Carousel and lunch-break benches.', ['waterfront', 'gardens',
              'lunch-break'], 'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('stone-street', 'Stone Street', 'nightlife', 'financial-district', 'Cobblestone lane lined with pubs '
              'whose picnic tables fill with after-work Wall Street crowds.', ['after-work', 'outdoor-drinking',
              'cobblestones'], '$$', 'outdoor', ['coworkers', 'friends'], NIGHT, WARM),
        place('fanelli-cafe', 'Fanelli Cafe', 'bar', 'soho', 'Old corner saloon on Prince Street, a bar since the '
              'nineteenth century, with burgers and checked tablecloths.', ['historic', 'pub', 'burgers'], '$$',
              'indoor', ['friends', 'solo', 'date'], ['afternoon', 'evening', 'late'], cuisine='american-pub'),
        place('mcnally-jackson-soho', 'McNally Jackson Books', 'shopping', 'soho', 'Independent bookstore on Prince '
              'Street with deep fiction shelves and author readings.', ['books', 'readings', 'indie'], '$', 'indoor',
              ['solo', 'date', 'friends'], ['morning', 'afternoon', 'evening']),
        place('dominique-ansel', 'Dominique Ansel Bakery', 'cafe', 'soho', 'French bakery on Spring Street, home '
              'of the Cronut and a pretty back garden.', ['bakery', 'pastry', 'cronut'], '$$', 'mixed', ALL, DAY,
              cuisine='french-bakery'),
        place('housing-works-bookstore', 'Housing Works Bookstore Cafe', 'cafe', 'soho', 'Volunteer-run used '
              'bookstore and cafe on Crosby Street whose proceeds support people with HIV and homelessness.',
              ['books', 'used', 'coffee', 'charity'], '$', 'indoor', ['solo', 'friends', 'date'], DAY,
              cuisine='cafe'),
        place('tenement-museum', 'Tenement Museum', 'museum', 'lower-east-side', 'Guided tours through restored '
              'Orchard Street tenement apartments of immigrant families.', ['history', 'immigration', 'tours'],
              '$$', 'indoor', ['solo', 'family', 'date'], DAY),
        place('seward-park', 'Seward Park', 'park', 'lower-east-side', 'Neighborhood park with a playground, '
              'chess tables and handball courts, beside the old Forward Building.', ['playground', 'chess',
              'local'], 'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('seward-park-library', 'NYPL Seward Park Library', 'library', 'lower-east-side', 'Historic Carnegie '
              'branch library facing the park, busy with students and Chinese-language readers.',
              ['books', 'study', 'historic'], 'free', 'indoor', ALL, DAY),
        place('mercury-lounge', 'Mercury Lounge', 'venue', 'lower-east-side', 'Small, long-running rock club on '
              'Houston Street where many bands play their first New York shows.', ['live-music', 'indie', 'rock'],
              '$$', 'indoor', ['friends', 'solo', 'date'], NIGHT),
        place('kossars', 'Kossar\'s Bagels & Bialys', 'cafe', 'lower-east-side', 'Old Grand Street bakery making '
              'bialys and bagels since the 1930s.', ['bagels', 'bakery', 'historic'], '$', 'indoor', ALL,
              ['morning'], cuisine='jewish-bakery'),
        place('tompkins-square-park', 'Tompkins Square Park', 'park', 'east-village', 'The East Village\'s '
              'backyard: dog run, basketball, chess, a Saturday Greenmarket and buskers.', ['dogs', 'local',
              'greenmarket'], 'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('ottendorfer-library', 'NYPL Ottendorfer Library', 'library', 'east-village', 'One of the oldest '
              'public library buildings in Manhattan, an ornate branch on Second Avenue.', ['books', 'historic',
              'quiet'], 'free', 'indoor', ALL, DAY),
        place('bh-dairy', 'B&H Dairy', 'restaurant', 'east-village', 'Narrow kosher dairy lunch counter serving '
              'blintzes, pierogi and challah toast since the 1940s.', ['lunch-counter', 'cheap', 'historic'], '$',
              'indoor', ['solo', 'friends'], ['morning', 'afternoon'], cuisine='jewish-dairy'),
        place('momofuku-noodle-bar', 'Momofuku Noodle Bar', 'restaurant', 'east-village', 'David Chang\'s ramen '
              'and pork-bun counter on First Avenue.', ['ramen', 'buns'], '$$', 'indoor', ['friends', 'date',
              'solo'], ['afternoon', 'evening'], cuisine='asian-american'),
        place('comedy-cellar', 'Comedy Cellar', 'venue', 'greenwich-village', 'Basement comedy club on MacDougal '
              'Street where well-known comics drop in unannounced.', ['comedy', 'late-night'], '$$', 'indoor',
              ['friends', 'date'], NIGHT),
        place('jefferson-market-library', 'NYPL Jefferson Market Library', 'library', 'greenwich-village',
              'Victorian Gothic former courthouse turned branch library, with a garden next door.',
              ['books', 'architecture', 'garden'], 'free', 'indoor', ALL, DAY),
        place('chelsea-galleries', 'Chelsea gallery district', 'museum', 'chelsea', 'Hundreds of free contemporary '
              'art galleries in old warehouses between Tenth and Eleventh Avenues.', ['art', 'free', 'walk'],
              'free', 'indoor', ['solo', 'date', 'friends'], ['afternoon']),
        place('cookshop', 'Cookshop', 'restaurant', 'chelsea', 'Seasonal American restaurant on Tenth Avenue by the '
              'High Line, a neighborhood brunch favorite.', ['brunch', 'seasonal', 'patio'], '$$$', 'mixed',
              ['date', 'friends'], ['morning', 'afternoon', 'evening'], cuisine='american'),
        place('muhlenberg-library', 'NYPL Muhlenberg Library', 'library', 'chelsea', 'Branch library on West 23rd '
              'Street with computers, study tables and kids\' programs.', ['books', 'quiet', 'kids'], 'free',
              'indoor', ALL, DAY),
        place('shake-shack-madison-square', 'Shake Shack Madison Square Park', 'restaurant', 'flatiron', 'The '
              'original burger kiosk in the park, with a lunchtime line and outdoor tables.', ['burgers', 'outdoor',
              'lunch'], '$', 'outdoor', ALL, ['afternoon', 'evening'], cuisine='burgers'),
        place('eataly-flatiron', 'Eataly Flatiron', 'market', 'flatiron', 'Big Italian food hall and grocery on '
              'Fifth Avenue with counters for pasta, pizza and espresso.', ['italian', 'grocery', 'food-hall'], '$$',
              'indoor', ALL, ['morning', 'afternoon', 'evening'], cuisine='italian'),
        place('old-town-bar', 'Old Town Bar', 'bar', 'flatiron', 'Wood-panelled 1890s tavern on East 18th Street '
              'with booths, burgers and a dumbwaiter.', ['historic', 'pub', 'burgers'], '$$', 'indoor',
              ['friends', 'solo', 'coworkers'], NIGHT, cuisine='american-pub'),
        place('kips-bay-library', 'NYPL Kips Bay Library', 'library', 'kips-bay', 'Neighborhood branch library on '
              'Third Avenue used by students and hospital staff.', ['books', 'quiet', 'study'], 'free', 'indoor',
              ALL, DAY),
        place('kalustyans', 'Kalustyan\'s', 'market', 'kips-bay', 'Packed spice and specialty grocery on Lexington '
              'Avenue\'s "Curry Hill", with a small upstairs deli.', ['grocery', 'spices', 'indian'], '$', 'indoor',
              ALL, ['morning', 'afternoon', 'evening']),
        place('st-vartan-park', 'St. Vartan Park', 'park', 'kips-bay', 'Neighborhood park with a playground, '
              'ball courts and a turf field on First Avenue.', ['playground', 'sports', 'local'], 'free', 'outdoor',
              ALL, ['morning', 'afternoon', 'evening']),
        place('sarges-deli', 'Sarge\'s Deli', 'restaurant', 'kips-bay', 'Old-school Jewish deli on Third Avenue in '
              'Murray Hill with towering pastrami sandwiches.', ['deli', 'pastrami', 'old-school'], '$$', 'indoor',
              ALL, ['morning', 'afternoon', 'evening', 'late'], cuisine='jewish-deli'),
        place('petes-tavern', 'Pete\'s Tavern', 'bar', 'kips-bay', 'Gramercy saloon that claims to be the oldest '
              'continuously operating bar in the city.', ['historic', 'pub'], '$$', 'indoor',
              ['friends', 'date', 'coworkers'], NIGHT, cuisine='american-pub'),
        place('bryant-park', 'Bryant Park', 'park', 'midtown', 'Midtown\'s lunchtime lawn behind the library, with '
              'movable chairs, a carousel and a winter skating rink.', ['lunch-break', 'lawn', 'skating'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('nypl-schwarzman', 'New York Public Library main branch', 'library', 'midtown', 'The Beaux-Arts '
              'Stephen A. Schwarzman Building with its stone lions and the Rose Main Reading Room.',
              ['books', 'architecture', 'quiet', 'iconic'], 'free', 'indoor', ALL, DAY),
        place('mercado-little-spain', 'Mercado Little Spain', 'restaurant', 'hudson-yards', 'José Andrés\'s Spanish '
              'food hall under the Hudson Yards towers, with tapas counters and a bar.', ['food-hall', 'tapas'],
              '$$', 'indoor', ['friends', 'coworkers', 'date'], ['afternoon', 'evening'], cuisine='spanish'),
        place('the-shed', 'The Shed', 'venue', 'hudson-yards', 'Arts center with a sliding shell hosting '
              'exhibitions, concerts and performances.', ['arts', 'performance'], '$$', 'indoor',
              ['friends', 'date', 'solo'], ['afternoon', 'evening']),
        place('shops-at-hudson-yards', 'The Shops at Hudson Yards', 'shopping', 'hudson-yards', 'Multi-level mall '
              'of chain stores and restaurants, a warm place to walk in winter.', ['mall', 'errands'], '$$$',
              'indoor', ALL, ['morning', 'afternoon', 'evening']),
        place('bella-abzug-park', 'Bella Abzug Park', 'park', 'hudson-yards', 'Narrow mid-block park running '
              'north from Hudson Yards with lawns, fountains and food kiosks.', ['lawn', 'lunch-break', 'dogs'],
              'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('zabars', 'Zabar\'s', 'market', 'upper-west-side', 'Crowded Broadway gourmet grocery for smoked fish, '
              'coffee and cheese, with a cafe counter next door.', ['grocery', 'deli', 'iconic'], '$$', 'indoor',
              ALL, ['morning', 'afternoon', 'evening']),
        place('barney-greengrass', 'Barney Greengrass', 'restaurant', 'upper-west-side', 'The "Sturgeon King", an '
              'Amsterdam Avenue appetizing shop and restaurant for lox and eggs.', ['brunch', 'smoked-fish',
              'historic'], '$$', 'indoor', ALL, DAY, cuisine='jewish-deli'),
        place('riverside-park', 'Riverside Park', 'park', 'upper-west-side', 'Long Hudson-front park with running '
              'paths, dog runs and playgrounds below Riverside Drive.', ['running', 'waterfront', 'dogs'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('carl-schurz-park', 'Carl Schurz Park', 'park', 'upper-east-side', 'Quiet riverside park by Gracie '
              'Mansion with a promenade over the East River and a busy dog run.', ['waterfront', 'dogs', 'quiet'],
              'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('lexington-candy-shop', 'Lexington Candy Shop', 'restaurant', 'upper-east-side', 'Luncheonette from '
              '1925 with a soda fountain, egg creams and diner breakfasts.', ['diner', 'historic', 'milkshakes'], '$',
              'indoor', ALL, DAY, cuisine='american-diner'),
        place('jg-melon', 'J.G. Melon', 'bar', 'upper-east-side', 'Cash-only corner pub on Third Avenue famous for '
              'its burgers and cottage fries.', ['burgers', 'pub', 'classic'], '$$', 'indoor', ['friends', 'date',
              'solo'], ['afternoon', 'evening', 'late'], cuisine='american-pub'),
        place('67th-street-library', 'NYPL 67th Street Library', 'library', 'upper-east-side', 'Carnegie branch '
              'library on East 67th Street.', ['books', 'quiet', 'historic'], 'free', 'indoor', ALL, DAY),
        place('toms-restaurant-morningside', 'Tom\'s Restaurant', 'restaurant', 'morningside-heights', 'Columbia '
              'students\' diner on Broadway, whose sign was used as Monk\'s Café on Seinfeld.', ['diner', 'students',
              'cheap'], '$', 'indoor', ALL, ['morning', 'afternoon', 'evening', 'late'], cuisine='american-diner'),
        place('hungarian-pastry-shop', 'Hungarian Pastry Shop', 'cafe', 'morningside-heights', 'Dim, cosy cafe on '
              'Amsterdam Avenue where Columbia students write papers over pastries for hours.', ['pastry', 'study',
              'students'], '$', 'mixed', ['solo', 'friends', 'date'], ['morning', 'afternoon', 'evening'],
              cuisine='hungarian-pastry'),
        place('book-culture', 'Book Culture', 'shopping', 'morningside-heights', 'Independent bookstore near '
              'Columbia with academic titles, fiction and readings.', ['books', 'students', 'indie'], '$', 'indoor',
              ['solo', 'friends'], ['morning', 'afternoon', 'evening']),
        place('morningside-park', 'Morningside Park', 'park', 'morningside-heights', 'Steep cliffside park between '
              'the Heights and Harlem with a pond, ball fields and a Saturday farmers market.', ['local',
              'playground', 'farmers-market'], 'free', 'outdoor', ALL, DAY),
        place('riverside-church', 'Riverside Church', 'landmark', 'morningside-heights', 'Gothic church tower over '
              'the Hudson with a famous carillon and a long activist history.', ['architecture', 'history',
              'music'], 'free', 'indoor', ['solo', 'family'], DAY),
        place('schomburg-center', 'Schomburg Center for Research in Black Culture', 'library', 'harlem', 'NYPL '
              'research library and exhibition space on Malcolm X Boulevard devoted to the African diaspora.',
              ['books', 'black-history', 'exhibits'], 'free', 'indoor', ['solo', 'friends', 'family'], DAY),
        place('marcus-garvey-park', 'Marcus Garvey Park', 'park', 'harlem', 'Rocky park with a fire watchtower, '
              'an amphitheatre for summer concerts and a Saturday drum circle.', ['music', 'playground', 'local'],
              'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('amy-ruths', 'Amy Ruth\'s', 'restaurant', 'harlem', 'Soul food restaurant on West 116th Street known '
              'for chicken and waffles named after famous Harlemites.', ['soul-food', 'chicken-and-waffles'], '$$',
              'indoor', ALL, ['morning', 'afternoon', 'evening'], cuisine='soul-food'),
        place('red-rooster', 'Red Rooster', 'restaurant', 'harlem', 'Marcus Samuelsson\'s Lenox Avenue restaurant '
              'with comfort food, a lively bar and live music downstairs.', ['soul-food', 'live-music', 'brunch'],
              '$$$', 'indoor', ['date', 'friends', 'family'], ['afternoon', 'evening'], cuisine='american-southern'),
        place('mccarren-park', 'McCarren Park', 'park', 'williamsburg', 'Williamsburg and Greenpoint\'s shared park '
              'with a running track, a big public pool and a Saturday Greenmarket.', ['running', 'pool', 'dogs'],
              'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('brooklyn-brewery', 'Brooklyn Brewery', 'bar', 'williamsburg', 'Brewery taproom on North 11th Street '
              'with weekend tours and long shared tables.', ['brewery', 'beer', 'tours'], '$$', 'indoor',
              ['friends', 'date'], ['afternoon', 'evening']),
        place('domino-park', 'Domino Park', 'park', 'williamsburg', 'Waterfront park beside the old Domino Sugar '
              'refinery with a taco stand, volleyball and skyline views.', ['waterfront', 'views', 'volleyball'],
              'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('janes-carousel', 'Jane\'s Carousel', 'attraction', 'dumbo', 'Restored 1920s carousel in a glass '
              'pavilion on the river below the Brooklyn Bridge.', ['carousel', 'kids', 'views'], '$', 'indoor',
              ['family', 'date'], DAY),
        place('grimaldis', 'Grimaldi\'s', 'restaurant', 'dumbo', 'Coal-oven pizzeria under the Brooklyn Bridge with '
              'a line of visitors outside.', ['pizza', 'touristy'], '$$', 'indoor', ALL, ['afternoon', 'evening'],
              cuisine='pizza'),
        place('brooklyn-heights-promenade', 'Brooklyn Heights Promenade', 'landmark', 'downtown-brooklyn', 'Esplanade '
              'above the BQE with the classic view of Lower Manhattan.', ['views', 'walk', 'skyline'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('fort-greene-park', 'Fort Greene Park', 'park', 'downtown-brooklyn', 'Hilly park with tennis courts, '
              'a Saturday Greenmarket and the Prison Ship Martyrs\' Monument.', ['tennis', 'greenmarket', 'dogs'],
              'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('bam', 'Brooklyn Academy of Music', 'venue', 'downtown-brooklyn', 'Performing arts center with '
              'theater, dance, opera and a repertory cinema.', ['theater', 'film', 'dance'], '$$', 'indoor',
              ['date', 'friends', 'solo'], ['afternoon', 'evening']),
        place('dekalb-market-hall', 'DeKalb Market Hall', 'market', 'downtown-brooklyn', 'Basement food hall under '
              'City Point with dozens of counters, including a Katz\'s outpost.', ['food-hall', 'lunch'], '$',
              'indoor', ALL, ['afternoon', 'evening']),
        place('brooklyn-central-library', 'Brooklyn Public Library Central Library', 'library', 'park-slope',
              'Art Deco main library at Grand Army Plaza with a cafe and big reading rooms.',
              ['books', 'architecture', 'study'], 'free', 'indoor', ALL, ['morning', 'afternoon', 'evening']),
        place('grand-army-plaza-greenmarket', 'Grand Army Plaza Greenmarket', 'market', 'park-slope', 'Saturday '
              'farmers market at the park\'s main entrance, the neighborhood\'s weekly grocery run.',
              ['farmers-market', 'saturday', 'produce'], '$', 'outdoor', ALL, ['morning']),
        place('community-bookstore', 'Community Bookstore', 'shopping', 'park-slope', 'Long-running independent '
              'bookstore on Seventh Avenue with a resident cat.', ['books', 'indie', 'kids'], '$', 'indoor', ALL,
              ['morning', 'afternoon', 'evening']),
        place('union-hall', 'Union Hall', 'bar', 'park-slope', 'Fifth Avenue bar with indoor bocce courts, '
              'fireplaces and a basement venue for comedy and music.', ['bocce', 'comedy', 'live-music'], '$$',
              'indoor', ['friends', 'date'], NIGHT),
        place('toms-restaurant-brooklyn', 'Tom\'s Restaurant', 'restaurant', 'park-slope', 'Prospect Heights diner '
              'open since the 1930s, known for lemon-ricotta pancakes and weekend lines.', ['diner', 'breakfast',
              'historic'], '$', 'indoor', ALL, DAY, cuisine='american-diner'),
        place('brooklyn-botanic-garden', 'Brooklyn Botanic Garden', 'garden', 'park-slope', 'Garden beside Prospect '
              'Park with a Japanese hill-and-pond garden and spring cherry blossoms.', ['flowers', 'cherry-blossoms',
              'quiet'], '$$', 'outdoor', ALL, DAY, WARM),
        place('maria-hernandez-park', 'Maria Hernandez Park', 'park', 'bushwick', 'Neighborhood park with a dog '
              'run, handball courts and weekend vendors.', ['dogs', 'local', 'playground'], 'free', 'outdoor', ALL,
              ['morning', 'afternoon', 'evening']),
        place('bushwick-collective', 'The Bushwick Collective', 'landmark', 'bushwick', 'Blocks of large street '
              'murals around Troutman Street and Saint Nicholas Avenue, repainted regularly.',
              ['street-art', 'walk', 'free'], 'free', 'outdoor', ['friends', 'solo', 'date'], ['afternoon']),
        place('bushwick-library', 'Brooklyn Public Library Bushwick Branch', 'library', 'bushwick', 'Restored '
              'Carnegie branch library on Bushwick Avenue.', ['books', 'historic', 'kids'], 'free', 'indoor', ALL,
              DAY),
        place('totonnos', 'Totonno\'s Pizzeria Napolitano', 'restaurant', 'coney-island', 'Coal-oven pizzeria on '
              'Neptune Avenue run by the same family since 1924.', ['pizza', 'historic'], '$$', 'indoor', ALL,
              ['afternoon', 'evening'], cuisine='pizza'),
        place('maimonides-park', 'Maimonides Park', 'stadium', 'coney-island', 'Minor-league ballpark of the '
              'Brooklyn Cyclones by the boardwalk, with summer fireworks nights.', ['baseball', 'cheap', 'family'],
              '$', 'outdoor', ALL, ['afternoon', 'evening'], ['summer']),
        place('ny-aquarium', 'New York Aquarium', 'attraction', 'coney-island', 'Aquarium on the boardwalk with '
              'sea lions, sharks and penguins.', ['animals', 'kids'], '$$', 'mixed', ['family', 'date'], DAY),
        place('coney-island-library', 'Brooklyn Public Library Coney Island Branch', 'library', 'coney-island',
              'Neighborhood branch library on Mermaid Avenue.', ['books', 'kids', 'quiet'], 'free', 'indoor', ALL,
              DAY),
        place('astoria-park', 'Astoria Park', 'park', 'astoria', 'Riverside park under the Hell Gate and RFK bridges '
              'with the city\'s biggest public pool, a track and tennis courts.', ['pool', 'running', 'views'],
              'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('taverna-kyclades', 'Taverna Kyclades', 'restaurant', 'astoria', 'Busy Ditmars Boulevard Greek '
              'seafood taverna with grilled octopus and long waits.', ['greek', 'seafood'], '$$', 'indoor', ALL,
              ['afternoon', 'evening'], cuisine='greek'),
        place('socrates-sculpture-park', 'Socrates Sculpture Park', 'park', 'astoria', 'Riverfront outdoor sculpture '
              'park with free summer movies and a weekend market.', ['art', 'waterfront', 'free'], 'free', 'outdoor',
              ALL, DAY, WARM),
        place('gantry-plaza', 'Gantry Plaza State Park', 'park', 'long-island-city', 'Waterfront park with restored '
              'rail gantries, the Pepsi-Cola sign and Midtown skyline views.', ['waterfront', 'views', 'skyline'],
              'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('hunters-point-library', 'Hunters Point Library', 'library', 'long-island-city', 'Queens Public '
              'Library branch in a striking concrete building by the river with skyline-facing windows.',
              ['books', 'architecture', 'views'], 'free', 'indoor', ALL, DAY),
        place('manducatis', 'Manducatis', 'restaurant', 'long-island-city', 'Old family-run Italian restaurant on '
              'Jackson Avenue with home-style cooking and a deep wine cellar.', ['italian', 'old-school', 'family'],
              '$$', 'indoor', ['family', 'date', 'friends'], DINNER, cuisine='italian'),
        place('dutch-kills', 'Dutch Kills', 'bar', 'long-island-city', 'Dim cocktail bar on Jackson Avenue with '
              'hand-cut ice and wooden booths.', ['cocktails', 'speakeasy'], '$$', 'indoor', ['date', 'friends'],
              NIGHT),
        place('flushing-library', 'Queens Public Library at Flushing', 'library', 'flushing', 'One of the busiest '
              'libraries in the country, with books in Chinese, Korean and many other languages.',
              ['books', 'multilingual', 'study'], 'free', 'indoor', ALL, ['morning', 'afternoon', 'evening']),
        place('queens-botanical-garden', 'Queens Botanical Garden', 'garden', 'flushing', 'Neighborhood botanical '
              'garden with a rose garden, an arboretum and seasonal festivals.', ['flowers', 'quiet', 'kids'], '$',
              'outdoor', ALL, DAY, WARM),
        place('queens-museum', 'Queens Museum', 'museum', 'flushing', 'Museum in Flushing Meadows famous for the '
              'Panorama, a scale model of every building in the city.', ['art', 'history', 'rainy-day'], '$',
              'indoor', ALL, DAY),
        place('new-world-mall', 'New World Mall food court', 'market', 'flushing', 'Basement food court with '
              'stalls for hand-pulled noodles, dumplings and malatang, beside a large Asian supermarket.',
              ['food-court', 'chinese', 'grocery'], '$', 'indoor', ALL, ['morning', 'afternoon', 'evening'],
              cuisine='chinese'),
        place('nan-xiang', 'Nan Xiang Xiao Long Bao', 'restaurant', 'flushing', 'Busy soup-dumpling restaurant on '
              'Prince Street.', ['dumplings', 'chinese'], '$', 'indoor', ALL, ['morning', 'afternoon', 'evening'],
              cuisine='shanghainese'),
        place('joyce-kilmer-park', 'Joyce Kilmer Park', 'park', 'concourse', 'Green square on the Grand Concourse '
              'opposite the courthouse with the Lorelei fountain.', ['local', 'benches', 'history'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('bronx-museum', 'Bronx Museum of the Arts', 'museum', 'concourse', 'Free contemporary art museum on the '
              'Grand Concourse focused on artists of color and Bronx stories.', ['art', 'free', 'rainy-day'],
              'free', 'indoor', ALL, DAY),
        place('yankee-tavern', 'Yankee Tavern', 'bar', 'concourse', 'Old bar near the stadium, packed before and '
              'after Yankees games.', ['sports', 'game-day', 'historic'], '$', 'indoor', ['friends', 'solo'],
              ['afternoon', 'evening', 'late'], cuisine='american-pub'),
        place('court-deli', 'Court Deli', 'restaurant', 'concourse', 'Long-running deli on East 161st Street '
              'serving pastrami and corned beef to jurors, lawyers and fans.', ['deli', 'lunch', 'game-day'], '$',
              'indoor', ALL, DAY, cuisine='jewish-deli'),
        place('bronx-terminal-market', 'Bronx Terminal Market', 'shopping', 'concourse', 'Big-box shopping center '
              'by the Major Deegan for groceries and errands.', ['errands', 'mall'], '$$', 'indoor', ALL,
              ['morning', 'afternoon', 'evening']),
        place('dominicks', 'Dominick\'s', 'restaurant', 'belmont', 'Arthur Avenue institution with no menus, no '
              'bills and communal tables; the waiters tell you what there is.', ['italian', 'old-school'], '$$',
              'indoor', ['family', 'friends'], DINNER, cuisine='italian'),
        place('madonia-brothers', 'Madonia Brothers Bakery', 'cafe', 'belmont', 'Family bakery since 1918 known for '
              'olive bread and cannoli filled to order.', ['bakery', 'cannoli'], '$', 'indoor', ALL, DAY,
              cuisine='italian-bakery'),
        place('nybg', 'New York Botanical Garden', 'garden', 'belmont', 'Huge garden with a Victorian glasshouse, '
              'old-growth forest and the holiday train show.', ['flowers', 'forest', 'holiday'], '$$$', 'mixed', ALL,
              DAY),
        place('belmont-library', 'NYPL Belmont Library', 'library', 'belmont', 'Branch library with the Enrico Fermi '
              'Cultural Center\'s Italian-American collection.', ['books', 'italian', 'history'], 'free', 'indoor',
              ALL, DAY),
    ],
    'colleges': [
        college('columbia', 'Columbia University', 'research-university', 'morningside-heights', 'large',
                ['ivy-league', 'journalism', 'law', 'business', 'engineering', 'research']),
        college('nyu', 'New York University', 'research-university', 'greenwich-village', 'large',
                ['film', 'business', 'law', 'arts', 'research']),
        college('ccny', 'The City College of New York (CUNY)', 'public-university', 'harlem', 'large',
                ['engineering', 'architecture', 'sciences']),
        college('hunter', 'Hunter College (CUNY)', 'public-university', 'upper-east-side', 'large',
                ['nursing', 'education', 'social-work', 'liberal-arts']),
        college('baruch', 'Baruch College (CUNY)', 'public-university', 'kips-bay', 'large',
                ['business', 'accounting', 'public-affairs']),
        college('city-tech', 'New York City College of Technology (CUNY)', 'technical-institute',
                'downtown-brooklyn', 'medium', ['engineering-technology', 'architecture', 'hospitality', 'nursing']),
        college('laguardia-cc', 'LaGuardia Community College (CUNY)', 'community-college', 'long-island-city',
                'large', ['health-sciences', 'business', 'adult-education']),
        college('juilliard', 'The Juilliard School', 'music-school', 'upper-west-side', 'small',
                ['music', 'dance', 'drama']),
        college('new-school', 'The New School (Parsons)', 'private-university', 'greenwich-village', 'medium',
                ['fashion-design', 'design', 'social-research', 'jazz']),
        college('fit', 'Fashion Institute of Technology (SUNY)', 'art-school', 'chelsea', 'medium',
                ['fashion-design', 'merchandising', 'textiles', 'illustration']),
        college('cooper-union', 'The Cooper Union', 'technical-institute', 'east-village', 'small',
                ['engineering', 'architecture', 'fine-art']),
        college('fordham', 'Fordham University', 'private-university', 'belmont', 'large',
                ['business', 'law', 'liberal-arts', 'jesuit']),
        college('weill-cornell-medicine', 'Weill Cornell Medicine', 'medical-school', 'upper-east-side', 'medium',
                ['medicine', 'biomedical-research']),
    ],
    'employers': [
        employer('nyu-langone', 'NYU Langone Health', 'healthcare', 'kips-bay', 'large', 'Academic medical center '
                 'on First Avenue and one of the city\'s largest employers.', ['registered-nurse', 'night-nurse',
                 'physician-resident', 'pharmacist', 'medical-researcher', 'social-worker']),
        employer('mount-sinai', 'The Mount Sinai Hospital', 'healthcare', 'upper-east-side', 'large', 'Flagship '
                 'hospital and medical school on Fifth Avenue at 100th Street, facing Central Park.',
                 ['registered-nurse', 'night-nurse', 'physician-resident', 'pharmacist', 'medical-researcher']),
        employer('nyp-weill-cornell', 'NewYork-Presbyterian/Weill Cornell Medical Center', 'healthcare',
                 'upper-east-side', 'large', 'Large teaching hospital on York Avenue.', ['registered-nurse',
                 'night-nurse', 'physician-resident', 'pharmacist', 'social-worker']),
        employer('msk', 'Memorial Sloan Kettering Cancer Center', 'healthcare', 'upper-east-side', 'large',
                 'Cancer hospital and research institute on the East Side.', ['registered-nurse',
                 'medical-researcher', 'biotech-scientist', 'pharmacist']),
        employer('jpmorgan-chase', 'JPMorgan Chase', 'finance', 'midtown', 'large', 'The largest US bank, '
                 'headquartered in a new tower at 270 Park Avenue.', ['finance-banker', 'financial-analyst',
                 'software-engineer', 'data-analyst', 'accountant']),
        employer('goldman-sachs', 'Goldman Sachs', 'finance', 'financial-district', 'large', 'Investment bank '
                 'headquartered at 200 West Street by the Hudson.', ['finance-banker', 'financial-analyst',
                 'software-engineer', 'data-analyst']),
        employer('bloomberg-lp', 'Bloomberg L.P.', 'media', 'midtown', 'large', 'Financial data and news company '
                 'at 731 Lexington Avenue.', ['software-engineer', 'data-analyst', 'journalist',
                 'financial-analyst']),
        employer('google-nyc', 'Google New York', 'technology', 'chelsea', 'large', 'Google\'s largest office '
                 'outside California, at 111 Eighth Avenue and nearby buildings on the West Side.',
                 ['software-engineer', 'ux-designer', 'data-analyst', 'marketing-coordinator']),
        employer('meta-nyc', 'Meta New York', 'technology', 'hudson-yards', 'large', 'Engineering and sales '
                 'offices around Hudson Yards and the Farley Building.', ['software-engineer', 'ux-designer',
                 'data-analyst']),
        employer('nyt', 'The New York Times', 'media', 'midtown', 'large', 'Newsroom and digital teams in the '
                 'Times Building on Eighth Avenue.', ['journalist', 'graphic-designer', 'software-engineer',
                 'data-analyst']),
        employer('conde-nast', 'Condé Nast', 'media', 'financial-district', 'large', 'Magazine publisher of Vogue '
                 'and The New Yorker, based at One World Trade Center.', ['journalist', 'fashion-assistant',
                 'graphic-designer', 'marketing-coordinator']),
        employer('ralph-lauren', 'Ralph Lauren', 'fashion', 'midtown', 'large', 'Fashion house with headquarters '
                 'and design studios on Madison Avenue.', ['fashion-assistant', 'graphic-designer',
                 'marketing-coordinator', 'retail-associate']),
        employer('macys-herald-square', 'Macy\'s Herald Square', 'retail', 'midtown', 'large', 'The flagship '
                 'department store on 34th Street, which also produces the Thanksgiving Day Parade.',
                 ['retail-associate', 'fashion-assistant', 'event-planner', 'marketing-coordinator']),
        employer('shubert-organization', 'The Shubert Organization', 'entertainment', 'midtown', 'medium',
                 'Owner and operator of many Broadway theaters.', ['actor', 'performer', 'musician',
                 'marketing-coordinator']),
        employer('msg-entertainment', 'Madison Square Garden Entertainment', 'entertainment', 'midtown', 'large',
                 'Runs the Garden, Radio City Music Hall and the Rockettes\' Christmas Spectacular.',
                 ['performer', 'event-planner', 'bartender', 'marketing-coordinator']),
        employer('marriott-marquis', 'New York Marriott Marquis', 'hospitality', 'midtown', 'large', 'Huge Times '
                 'Square hotel with convention space and a revolving restaurant.', ['hotel-front-desk',
                 'event-planner', 'line-cook', 'server', 'bartender']),
        employer('ushg', 'Union Square Hospitality Group', 'hospitality', 'flatiron', 'medium', 'Restaurant group '
                 'behind Gramercy Tavern and The Modern.', ['line-cook', 'server', 'bartender', 'baker']),
        employer('nyc-public-schools', 'New York City Public Schools', 'education', 'financial-district', 'large',
                 'The country\'s largest school district, run from the Tweed Courthouse.', ['teacher',
                 'social-worker']),
        employer('nyc-government', 'City of New York', 'government', 'financial-district', 'large', 'City agencies '
                 'around City Hall and the Municipal Building.', ['government-analyst', 'social-worker',
                 'accountant', 'paralegal']),
        employer('mta', 'Metropolitan Transportation Authority', 'government', 'financial-district', 'large',
                 'Runs the subway, buses and commuter railroads from offices at 2 Broadway.',
                 ['government-analyst', 'construction-trades', 'data-analyst']),
        employer('port-authority', 'Port Authority of New York and New Jersey', 'logistics', 'financial-district',
                 'large', 'Runs the airports, bridges, tunnels, PATH and the region\'s container ports.',
                 ['port-logistics', 'construction-trades', 'government-analyst']),
        employer('skadden', 'Skadden, Arps, Slate, Meagher & Flom', 'legal', 'hudson-yards', 'large', 'Large law '
                 'firm headquartered at One Manhattan West.', ['paralegal']),
        employer('columbia-employer', 'Columbia University', 'education', 'morningside-heights', 'large',
                 'Faculty, research and staff jobs on the Morningside campus.', ['professor', 'graduate-student',
                 'medical-researcher', 'data-analyst']),
        employer('nyu-employer', 'New York University', 'education', 'greenwich-village', 'large', 'Faculty, '
                 'research and staff jobs around Washington Square.', ['professor', 'graduate-student']),
    ],
    'career_hubs': [
        {'id': 'midtown-core', 'name': 'Midtown business district', 'neighborhoods': ['midtown', 'hudson-yards'],
         'sectors': ['finance', 'legal', 'media', 'entertainment', 'hospitality', 'tourism', 'real-estate',
                     'construction'],
         'summary': 'Corporate headquarters, law firms, Broadway, hotels and new towers from Hudson Yards to Park '
                    'Avenue.', 'source': S},
        {'id': 'wall-street', 'name': 'Financial District and Civic Center', 'neighborhoods': ['financial-district'],
         'sectors': ['finance', 'government', 'legal', 'media'],
         'summary': 'Banks, insurers, city government and the World Trade Center offices.', 'source': S},
        {'id': 'silicon-alley', 'name': 'Silicon Alley', 'neighborhoods': ['flatiron', 'chelsea', 'soho'],
         'sectors': ['technology', 'creative', 'business', 'media'],
         'summary': 'Big tech offices on the West Side and startups around Flatiron and Union Square.', 'source': S},
        {'id': 'garment-district', 'name': 'Garment District and fashion', 'neighborhoods': ['midtown', 'chelsea'],
         'sectors': ['creative', 'fashion', 'retail'],
         'summary': 'Showrooms, design studios and fabric shops in the West 30s, near FIT and Herald Square.',
         'source': S},
        {'id': 'east-side-medical', 'name': 'East Side hospital corridor',
         'neighborhoods': ['upper-east-side', 'kips-bay'], 'sectors': ['healthcare', 'biotech', 'education'],
         'summary': 'Hospital rows along York and First Avenues, plus the Alexandria Center for Life Science.',
         'source': S},
        {'id': 'outer-borough-centers', 'name': 'Downtown Brooklyn and Long Island City',
         'neighborhoods': ['downtown-brooklyn', 'long-island-city'],
         'sectors': ['technology', 'creative', 'government', 'education', 'logistics', 'construction'],
         'summary': 'Back offices, courts, colleges, film studios and warehouses just across the East River.',
         'source': S},
    ],
    'climate': {
        'summary': 'Humid subtropical: hot, humid summers with thunderstorms, pleasant springs and autumns, and cold '
                   'winters with a few snowstorms most years.',
        'months': [
            {'high_f': 39, 'low_f': 27, 'rain_days': 11, 'note': 'Coldest month; snow and icy wind off the rivers.'},
            {'high_f': 42, 'low_f': 29, 'rain_days': 10, 'note': 'Cold and grey; the snowiest month on average.'},
            {'high_f': 50, 'low_f': 35, 'rain_days': 11, 'note': 'Changeable; early blossoms late in the month.'},
            {'high_f': 62, 'low_f': 45, 'rain_days': 11, 'note': 'Cherry blossoms and spring showers.'},
            {'high_f': 72, 'low_f': 55, 'rain_days': 11, 'note': 'Mild and green; outdoor dining fills up.'},
            {'high_f': 80, 'low_f': 64, 'rain_days': 10, 'note': 'Warm; beaches open Memorial Day weekend.'},
            {'high_f': 85, 'low_f': 70, 'rain_days': 10, 'note': 'Hottest month; muggy subway platforms.'},
            {'high_f': 84, 'low_f': 69, 'rain_days': 10, 'note': 'Hot and humid; many locals leave town.'},
            {'high_f': 76, 'low_f': 62, 'rain_days': 9, 'note': 'Warm early, crisper later.'},
            {'high_f': 65, 'low_f': 51, 'rain_days': 9, 'note': 'Crisp, often sunny autumn.'},
            {'high_f': 54, 'low_f': 42, 'rain_days': 9, 'note': 'Cool; leaves turn in the parks.'},
            {'high_f': 44, 'low_f': 33, 'rain_days': 11, 'note': 'Cold; holiday windows and lights.'},
        ],
        'source': CLIMATE,
    },
    'annual_events': [
        event('fashion-week', 'New York Fashion Week', [2, 9], None, 'Runway shows and showroom presentations at '
              'venues around Manhattan each February and September.'),
        event('tribeca-festival', 'Tribeca Festival', [6], None, 'Film festival with premieres and talks, centered '
              'on Tribeca in Lower Manhattan.'),
        event('nyc-pride-march', 'NYC Pride March', [6], 'greenwich-village', 'The last Sunday in June, ending in '
              'the Village near the Stonewall Inn.'),
        event('mermaid-parade', 'Mermaid Parade', [6], 'coney-island', 'Costumed summer parade along the Coney '
              'Island boardwalk.'),
        event('shakespeare-in-the-park', 'Shakespeare in the Park', [6, 7, 8], 'upper-west-side', 'Free Public '
              'Theater productions at the Delacorte Theater in Central Park.'),
        event('summerstage', 'SummerStage', [6, 7, 8], None, 'Outdoor concerts in city parks, with its main stage '
              'in Central Park.'),
        event('us-open', 'US Open tennis', [8, 9], 'flushing', 'Two weeks of Grand Slam tennis around Labor Day '
              'at Flushing Meadows.'),
        event('west-indian-day-parade', 'West Indian American Day Carnival', [9], None, 'Labor Day parade of '
              'Caribbean costumes and soca along Eastern Parkway in Brooklyn.'),
        event('village-halloween-parade', 'Village Halloween Parade', [10], 'greenwich-village', 'Night-time '
              'costume parade up Sixth Avenue on October 31.'),
        event('nyc-marathon', 'New York City Marathon', [11], 'upper-west-side', 'Runners cross all five boroughs '
              'on the first Sunday of November and finish in Central Park.'),
        event('macys-parade', 'Macy\'s Thanksgiving Day Parade', [11], 'midtown', 'Giant balloons travel from '
              'Central Park West to Herald Square on Thanksgiving morning.'),
        event('rockefeller-tree', 'Rockefeller Center Christmas Tree', [11, 12, 1], 'midtown', 'The tree is '
              'raised in November, lit in early December and stays up into January.'),
        event('new-years-eve-times-square', 'New Year\'s Eve in Times Square', [12], 'midtown', 'The ball drop '
              'at midnight, watched by huge crowds penned in from mid-afternoon.'),
    ],
    'local_color': [
        color('bacon-egg-and-cheese', 'Bacon, egg and cheese', 'dish', 'The bodega breakfast: bacon, a fried egg and '
              'American cheese on a roll, ordered as "salt, pepper, ketchup" and eaten walking to the train.'),
        color('bodega', 'Bodegas', 'shop', 'Corner delis that stay open late or all night, with a grill at the back, '
              'coffee, lottery tickets, everything from cat food to cold medicine, and often a resident cat.'),
        color('the-slice', 'A slice', 'dish', 'Thin, wide New York pizza sold by the slice from a counter, folded in '
              'half lengthwise to eat on the move.', ['joes-pizza']),
        color('bagel-and-schmear', 'Bagel with a schmear', 'dish', 'Boiled-then-baked bagels with cream cheese, or '
              'with lox, onion and capers from an appetizing store; locals have strong views on toasting.',
              ['russ-and-daughters', 'zabars', 'barney-greengrass', 'kossars']),
        color('pastrami-on-rye', 'Pastrami on rye', 'dish', 'Hot pastrami piled high on rye with mustard and a sour '
              'pickle on the side, the signature order at the old Jewish delis.',
              ['katzs', 'sarges-deli', 'court-deli']),
        color('chicken-over-rice', 'Chicken over rice', 'dish', 'The halal cart plate: chopped chicken or lamb over '
              'yellow rice with lettuce, white sauce and hot sauce, sold from street carts on Midtown corners.',
              ['midtown']),
        color('black-and-white-cookie', 'Black-and-white cookie', 'dish', 'A big, soft, cakey cookie iced half vanilla '
              'and half chocolate, sold in delis and bakeries across the city.'),
        color('egg-cream', 'Egg cream', 'drink', 'A soda-fountain drink with neither egg nor cream: chocolate syrup, '
              'milk and seltzer stirred until it foams.', ['lexington-candy-shop']),
        color('coffee-regular', '"Coffee regular"', 'saying', 'At a deli or coffee cart, "regular" means with milk and '
              'sugar, not plain black.'),
        color('walking-etiquette', 'Sidewalk etiquette', 'custom', 'Walk fast, keep to the right, never stop dead at '
              'the top of subway stairs, and step to the side before checking your phone or map.'),
        color('on-line', '"On line"', 'saying', 'New Yorkers wait "on line" rather than "in line", whether at the '
              'deli, the DMV or a sample sale.'),
        color('the-city', '"The city"', 'saying', 'To people in Brooklyn, Queens, the Bronx and Staten Island, "going '
              'into the city" means going to Manhattan.'),
        color('stoop-life', 'Stoop sitting and stoop sales', 'custom', 'Brownstone stoops become front porches in warm '
              'weather, with neighbors talking, kids playing and weekend stoop sales of books and old clothes.',
              ['park-slope', 'harlem'], ['spring', 'summer', 'fall']),
        color('yankees', 'New York Yankees', 'team', 'The Bronx Bombers play baseball at Yankee Stadium; their '
              'pinstripes and interlocking NY are seen worldwide.', ['yankee-stadium'], ['spring', 'summer', 'fall']),
        color('mets', 'New York Mets', 'team', 'Queens\'s National League baseball team plays at Citi Field in '
              'Flushing, with fans used to suffering and loyal anyway.', ['citi-field'], ['spring', 'summer', 'fall']),
        color('knicks', 'New York Knicks', 'team', 'The NBA team plays at Madison Square Garden, where courtside seats '
              'draw celebrities and a long wait for a title is part of the identity.',
              ['madison-square-garden'], ['fall', 'winter', 'spring']),
        color('rangers', 'New York Rangers', 'team', 'One of the NHL\'s Original Six, playing hockey at Madison Square '
              'Garden.', ['madison-square-garden'], ['fall', 'winter', 'spring']),
        color('nets', 'Brooklyn Nets', 'team', 'The NBA team that moved from New Jersey to Barclays Center in 2012, '
              'wearing black and white.', ['barclays-center'], ['fall', 'winter', 'spring']),
        color('liberty', 'New York Liberty', 'team', 'The WNBA team plays at Barclays Center and won its first '
              'championship in 2024.', ['barclays-center'], ['spring', 'summer', 'fall']),
        color('giants-and-jets', 'Giants and Jets', 'team', 'Both of New York\'s NFL teams play across the Hudson at '
              'MetLife Stadium in New Jersey, and fans of each look down on the other.', seasons=['fall', 'winter']),
    ],
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
