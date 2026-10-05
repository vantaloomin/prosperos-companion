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
    'summary': 'The largest city in the United States: five boroughs of dense neighbourhoods tied together by a '
               '24-hour subway, home to Wall Street, Broadway, world-class museums and food from everywhere.',
    'lat': 40.71, 'lon': -74.01,
    'speeds': {'walk': 4.5, 'car': 18, 'rideshare': 18, 'bus': 10, 'subway': 25, 'ferry': 20,
               'commuter-rail': 50, 'bike-share': 13},
    'sources': {
        S: {'kind': 'curated', 'title': 'New York places and neighbourhoods written for Prospero Companion',
            'license': 'CC0-1.0', 'retrieved': '2026-10-05',
            'note': 'Well-known public places, institutions and employers from general knowledge. Businesses open '
                    'and close and rents move fast here: treat this as a snapshot for fiction. Rents are rounded '
                    'estimates of typical 2025 asking ranges, not listings. Coordinates are approximate '
                    'neighbourhood centres.'},
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
             'Grand Central and Penn Station, busiest on weekdays.', ['business', 'touristy', 'theatre', 'central'],
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
        hood('morningside-heights', 'Morningside Heights', 'The academic neighbourhood around Columbia University '
             'and the Cathedral of St. John the Divine.', ['academic', 'students', 'quiet'], 40.808, -73.962,
             'mid', ([2100, 2800], [2800, 3600], [3400, 4800]), ['prewar-apartment', 'student-housing'], 'high',
             CORE),
        hood('harlem', 'Harlem', 'Brownstone blocks with deep African American and Latino cultural history, centred '
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
        hood('downtown-brooklyn', 'Downtown Brooklyn', 'Brooklyn\'s civic and office centre, now dense with rental '
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
        hood('astoria', 'Astoria', 'A diverse, food-loving neighbourhood of Greek tavernas, beer gardens and '
             'two-family houses near the East River.', ['diverse', 'food', 'young-professional', 'neighbourly'],
             40.764, -73.923, 'mid', ([2100, 2700], [2500, 3300], [3000, 4000]),
             ['walk-up', 'two-family-house', 'apartment'], 'high', CORE + ['nyc-ferry']),
        hood('long-island-city', 'Long Island City', 'Glass towers on the Queens waterfront with Manhattan skyline '
             'views, plus warehouses, film studios and MoMA PS1.', ['new-build', 'views', 'waterfront', 'arts'],
             40.746, -73.949, 'very-high', ([3200, 3900], [4000, 5000], [5200, 7200]), ['apartment-tower', 'condo'],
             'high', CORE + ['nyc-ferry', 'lirr']),
        hood('flushing', 'Flushing', 'A busy Chinese and Korean commercial centre around Main Street, beside '
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
        {'id': 'nyc-ferry', 'name': 'NYC Ferry', 'kind': 'ferry', 'summary': 'East River and harbour ferry routes '
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
              'harbour crossing with views of the skyline and the Statue of Liberty.', ['free', 'views', 'water'],
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
        place('broadway-theatres', 'Broadway theatres', 'venue', 'midtown', 'Around forty large theatres in the '
              'blocks around Times Square staging musicals and plays eight times a week.', ['theatre', 'musicals',
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
        place('apollo-theater', 'Apollo Theater', 'venue', 'harlem', 'Historic 125th Street theatre famous for '
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
              'of the US Open, with Arthur Ashe Stadium at its centre.', ['tennis', 'sports'], '$$$', 'outdoor',
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
        employer('nyu-langone', 'NYU Langone Health', 'healthcare', 'kips-bay', 'large', 'Academic medical centre '
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
                 'Owner and operator of many Broadway theatres.', ['actor', 'performer', 'musician',
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
        {'id': 'outer-borough-centres', 'name': 'Downtown Brooklyn and Long Island City',
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
        event('tribeca-festival', 'Tribeca Festival', [6], None, 'Film festival with premieres and talks, centred '
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
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
