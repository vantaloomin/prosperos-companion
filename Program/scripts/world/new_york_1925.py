"""Curated data for New York in 1925: the Jazz Age city of speakeasies, Harlem, Broadway and new skyscrapers.

Run `python scripts/world/new_york_1925.py` to rewrite the shipped JSON.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'cities' / 'new-york-1925.json'
S = 'curated-2026-10'
ERA = 'jazz-age'


def hood(id, name, summary, vibe, lat, lon, tier, rent, housing, walk, transit):
    room, two_rooms, four_rooms = rent
    return {'id': id, 'name': name, 'summary': summary, 'vibe': vibe, 'lat': lat, 'lon': lon, 'rent_tier': tier,
            'rent': {'studio': room, 'one_bedroom': two_rooms, 'two_bedroom': four_rooms}, 'housing': housing,
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


def career(id, name, sector, schedule, pay, summary, themes):
    return {'id': id, 'name': name, 'sector': sector, 'schedule': schedule, 'pay': pay, 'summary': summary,
            'themes': themes, 'eras': [ERA]}


def line(id, name, kind, summary):
    return {'id': id, 'name': name, 'kind': kind, 'summary': summary, 'source': S}


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
DINNER = ['evening']
NIGHT = ['evening', 'late']
LATE = ['late']
ALLDAY = ['morning', 'afternoon', 'evening']
AFTERNOON_ON = ['afternoon', 'evening', 'late']
WARM = ['spring', 'summer', 'fall']
SUMMER = ['summer']
BALLGAME = ['spring', 'summer', 'fall']

IRT, BMT = 'irt-subway', 'bmt-subway'
THIRD, WEST_ELS = 'third-and-second-avenue-els', 'sixth-and-ninth-avenue-els'
TUBES, TROLLEY, COACH = 'hudson-tubes', 'streetcars', 'fifth-avenue-coach'
FERRY, PRR, CENTRAL, TAXI, WALK = 'ferries', 'pennsylvania-railroad', 'new-york-central', 'taxicabs', 'walking'

CITY = {
    'schema_version': 1, 'id': 'new-york-1925', 'name': 'New York, 1925', 'setting': 'real', 'era': ERA,
    'basis': 'Real New York City as it stood in 1925, written from general historical knowledge: neighborhoods, '
             'institutions, theaters, clubs, restaurants and ballparks that existed that year, with Prohibition, '
             'segregation and the immigrant city described as they were. No fictional characters or later places.',
    'region': 'New York', 'country': 'United States', 'timezone': 'America/New_York',
    'aliases': ['New York 1925', 'Jazz Age New York', 'Prohibition New York', '1920s New York',
                'New York in the Twenties', 'Roaring Twenties New York'],
    'summary': 'New York in 1925: the biggest city in America and still growing, with skyscrapers going up in '
               'Midtown, subways pushing out to the Bronx, Brooklyn and Queens, speakeasies behind every other '
               'door under Prohibition, Broadway and the Ziegfeld Follies, the Harlem Renaissance uptown and '
               'crowded immigrant neighborhoods downtown.',
    'lat': 40.73, 'lon': -73.99,
    'speeds': {'walk': 4.5, 'subway': 24, 'streetcar': 11, 'bus': 11, 'ferry': 14, 'commuter-rail': 40,
               'car': 18},
    # Rough heritage weights for 1925 New York (estimates, not census figures): a city of Irish, Italian,
    # Jewish and German New Yorkers, a growing Black Harlem with many Caribbean families, and old-stock Americans.
    'names': {'year': 1925,
              'mix': {'anglo': 2.8, 'irish': 2.2, 'italian': 2.2, 'jewish': 2.2, 'german': 1.4,
                      'black-american': 1.1, 'slavic': 1.0, 'caribbean': 0.25, 'hispanic': 0.15,
                      'east-asian': 0.08}},
    'sources': {
        S: {'kind': 'curated', 'title': 'New York in 1925, written for Prospero Companion',
            'license': 'CC0-1.0', 'retrieved': '2026-10-10',
            'note': 'Jazz Age New York from general historical knowledge: neighborhoods, institutions, theaters, '
                    'nightclubs, restaurants, ballparks and employers that existed in 1925, at approximate real '
                    'coordinates. Treat it as a snapshot for fiction, not a directory: clubs opened, were padlocked '
                    'by Prohibition agents and reopened under new names all the time. Rents are rounded monthly '
                    'figures in 1925 dollars for a furnished room, a two-room flat and a four-room flat. Prices '
                    'and the day wage are rounded typical figures. Climate figures are rounded New York averages '
                    'of the period.'},
    },
    'neighborhoods': [
        # Uptown
        hood('harlem', 'Harlem', 'The capital of Black America and the heart of the Harlem Renaissance: writers, '
             'artists and musicians, churches and lodges, cabarets on Lenox and Seventh Avenues, and rents set high '
             'for Black tenants, which the rent party helps pay.', ['harlem-renaissance', 'music', 'churches',
             'nightlife'], 40.811, -73.944, 'mid', ([20, 35], [40, 65], [55, 90]),
             ['brownstone', 'walk-up', 'apartment-house', 'rooming-house'], 'high', [IRT, WEST_ELS, THIRD, CENTRAL,
             TROLLEY, TAXI]),
        hood('sugar-hill', 'Hamilton Heights and Sugar Hill', 'Handsome row houses and apartment houses on the '
             'heights above Harlem around City College, where Black doctors, lawyers and musicians are beginning '
             'to move in, with the Polo Grounds below the bluff.', ['respectable', 'heights', 'baseball'], 40.826,
             -73.943, 'high', ([30, 45], [60, 90], [85, 130]), ['row-house', 'apartment-house'], 'high',
             [IRT, WEST_ELS, TROLLEY, TAXI]),
        hood('san-juan-hill', 'San Juan Hill', 'Crowded tenement blocks in the West Sixties between Amsterdam '
             'Avenue and the river, the city\'s largest Black neighborhood before Harlem, with dance halls, '
             'churches and the New York Central freight yards.', ['working-class', 'dance-halls', 'tenements'],
             40.773, -73.988, 'low', ([12, 20], [18, 30], [25, 40]), ['tenement', 'rooming-house'], 'high',
             [IRT, WEST_ELS, TROLLEY]),
        hood('upper-west-side', 'Upper West Side and Morningside Heights', 'Big apartment houses and brownstones '
             'between Central Park and Riverside Drive, with the Natural History Museum, Columbia University on '
             'the heights and many Jewish families who have moved up from downtown.', ['residential', 'family',
             'academic', 'park'], 40.792, -73.970, 'high', ([35, 55], [70, 110], [100, 160]),
             ['apartment-house', 'brownstone', 'apartment-hotel'], 'high', [IRT, WEST_ELS, TROLLEY, TAXI]),
        hood('yorkville', 'Yorkville and the Upper East Side', 'German, Hungarian and Czech Yorkville around '
             'East 86th Street, with its dance halls, bakeries and gymnastic societies, below the mansions of '
             'Fifth Avenue\'s Millionaires\' Row and the Metropolitan Museum.', ['german', 'mansions',
             'museums', 'working-class'], 40.776, -73.953, 'mid', ([18, 30], [30, 50], [45, 80]),
             ['walk-up', 'tenement', 'mansion', 'apartment-house'], 'high', [IRT, THIRD, COACH, TROLLEY, TAXI]),
        # Midtown
        hood('midtown', 'Midtown and Fifth Avenue', 'Fifth Avenue shops and churches, the Public Library, Grand '
             'Central Terminal and new office towers going up around them, with hotels, clubs and the '
             'Algonquin crowd on the side streets.', ['shopping', 'offices', 'hotels', 'skyscrapers'], 40.754,
             -73.980, 'very-high', ([45, 80], [90, 150], [140, 250]), ['apartment-hotel', 'hotel',
             'apartment-house'], 'high', [IRT, BMT, WEST_ELS, THIRD, CENTRAL, COACH, TAXI]),
        hood('times-square', 'Times Square and the Theater District', 'The electric signs of the Great White Way, '
             'some seventy legitimate theaters, vaudeville and movie palaces, dance halls, all-night restaurants '
             'and speakeasies in the side streets of the West Forties.', ['theater', 'nightlife', 'electric-signs',
             'crowds'], 40.758, -73.986, 'high', ([30, 55], [60, 100], [90, 150]),
             ['rooming-house', 'hotel', 'walk-up'], 'high', [IRT, BMT, WEST_ELS, TROLLEY, TAXI]),
        hood('herald-square', 'Herald Square and the Garment District', 'Macy\'s and Gimbels at Herald Square, '
             'Pennsylvania Station, the new garment lofts of Seventh Avenue full of cutters and pressers, and Tin '
             'Pan Alley\'s song publishers a few blocks south.', ['shopping', 'garment', 'railroad', 'music'],
             40.751, -73.990, 'mid', ([20, 35], [35, 60], [55, 85]), ['walk-up', 'rooming-house', 'hotel'],
             'high', [IRT, BMT, WEST_ELS, TUBES, PRR, TROLLEY, TAXI]),
        hood('hells-kitchen', 'Hell\'s Kitchen', 'Irish tenement blocks on the West Side between Eighth Avenue and '
             'the river, with freight trains in the street, the Ninth Avenue market under the El, gangs, gyms and '
             'the new Madison Square Garden.', ['irish', 'working-class', 'tough', 'boxing'], 40.762, -73.993,
             'low', ([12, 20], [18, 30], [25, 40]), ['tenement', 'rooming-house'], 'high', [WEST_ELS, TROLLEY,
             TAXI]),
        hood('chelsea', 'Chelsea', 'West Side blocks of row houses and tenements by the Hudson piers where the big '
             'ocean liners dock, with the National Biscuit Company bakery, the meat market on Gansevoort Street '
             'and the old Hotel Chelsea.', ['waterfront', 'working-class', 'artists'], 40.745, -74.001, 'mid',
             ([18, 30], [30, 50], [45, 75]), ['row-house', 'tenement', 'walk-up'], 'high', [IRT, BMT, WEST_ELS,
             TUBES, FERRY, TROLLEY]),
        # Downtown
        hood('greenwich-village', 'Greenwich Village', 'Crooked old streets of bohemians, little theaters, tea '
             'rooms and hidden speakeasies around Washington Square, beside Italian families on Bleecker Street '
             'and NYU on the square.', ['bohemian', 'artists', 'speakeasies', 'theater'], 40.733, -74.000, 'mid',
             ([25, 45], [40, 70], [60, 100]), ['walk-up', 'row-house', 'studio'], 'high', [IRT, WEST_ELS, TUBES,
             FERRY, COACH, TAXI]),
        hood('union-square', 'Union Square and Gramercy', 'Soapbox speakers and cut-price stores on Union Square, '
             'Tammany Hall on Fourteenth Street, Gramercy Park\'s locked garden and the Flatiron Building on '
             'Madison Square, with Cooper Union down at Astor Place.', ['politics', 'shopping', 'genteel',
             'central'], 40.737, -73.988, 'high', ([35, 60], [65, 110], [100, 160]),
             ['row-house', 'apartment-house', 'walk-up'], 'high', [IRT, BMT, THIRD, COACH, TROLLEY, TAXI]),
        hood('lower-east-side', 'Lower East Side', 'The most crowded neighborhood in America: Jewish tenements, '
             'pushcart markets on Orchard and Hester Streets, synagogues, settlement houses, Yiddish theaters on '
             'Second Avenue and delicatessens.', ['jewish', 'tenements', 'pushcarts', 'yiddish-theater'], 40.716,
             -73.987, 'low', ([12, 22], [15, 28], [22, 38]), ['tenement', 'walk-up'], 'high', [BMT, THIRD, TROLLEY]),
        hood('little-italy', 'Little Italy', 'Mulberry Street and its neighbors, packed with families from Naples '
             'and Sicily: pushcarts, pastry shops, social clubs, wine cellars and the saints\' feasts of summer.',
             ['italian', 'tenements', 'food', 'feasts'], 40.719, -73.997, 'low', ([12, 20], [16, 28], [22, 36]),
             ['tenement', 'walk-up'], 'high', [IRT, BMT, THIRD, TROLLEY]),
        hood('chinatown', 'Chinatown and the Bowery', 'A few crooked blocks of Mott, Pell and Doyers Streets, mostly '
             'men kept apart from their families by the exclusion laws, beside the Bowery\'s flophouses, missions '
             'and pawnshops under the Third Avenue El.', ['chinese', 'flophouses', 'missions', 'narrow-streets'],
             40.715, -73.998, 'low', ([12, 20], [16, 26], [22, 35]), ['tenement', 'lodging-house'], 'high',
             [BMT, THIRD, TROLLEY]),
        hood('city-hall', 'City Hall and Park Row', 'City Hall and its park, the Woolworth Building, the newspapers '
             'of Park Row, the courts and the Tombs, with the Brooklyn Bridge rising out of it and what is left '
             'of the old Five Points nearby.', ['government', 'newspapers', 'skyscrapers'], 40.712, -74.006, 'mid',
             ([18, 30], [30, 50], [45, 70]), ['rooming-house', 'walk-up'], 'high', [IRT, BMT, THIRD, TROLLEY,
             TAXI]),
        hood('financial-district', 'Wall Street and the Battery', 'Banks, brokers and the Stock Exchange in narrow '
             'canyons at the tip of Manhattan, crowded with clerks and runners by day, with Battery Park, the '
             'Aquarium and the ferries to Ellis Island, the Statue and Staten Island.', ['finance', 'harbor',
             'ferries', 'skyscrapers'], 40.706, -74.011, 'high', ([30, 50], [55, 90], [80, 130]),
             ['rooming-house', 'hotel'], 'high', [IRT, BMT, WEST_ELS, THIRD, TUBES, FERRY, TAXI]),
        # Brooklyn
        hood('brooklyn-heights', 'Brooklyn Heights and Downtown Brooklyn', 'Old brownstone streets on the bluff '
             'over the harbor, Borough Hall, the department stores of Fulton Street and, a little east, the '
             'Brooklyn Navy Yard.', ['brownstones', 'genteel', 'shopping'], 40.695, -73.992, 'high',
             ([30, 50], [55, 95], [85, 140]), ['brownstone', 'row-house', 'apartment-house'], 'high',
             [IRT, BMT, TROLLEY]),
        hood('williamsburg', 'Williamsburg and Greenpoint', 'Factory and waterfront Brooklyn by the Williamsburg '
             'Bridge: sugar refineries, Jewish families who came over the bridge from the Lower East Side, Italian '
             'blocks and Polish Greenpoint to the north.', ['industrial', 'immigrant', 'waterfront'], 40.714,
             -73.956, 'low', ([14, 24], [20, 32], [28, 45]), ['tenement', 'frame-house', 'walk-up'], 'medium',
             [BMT, TROLLEY]),
        hood('flatbush', 'Flatbush and Prospect Park', 'Leafy Brooklyn of frame houses and new apartment houses '
             'around Prospect Park, the Botanic Garden and Ebbets Field, where the Robins play.', ['leafy',
             'baseball', 'family', 'suburban'], 40.663, -73.963, 'mid', ([25, 40], [45, 70], [60, 95]),
             ['frame-house', 'apartment-house', 'row-house'], 'medium', [IRT, BMT, TROLLEY]),
        hood('coney-island', 'Coney Island', 'The Nickel Empire at the end of the subway: the new boardwalk, the '
             'beach, Luna Park and Steeplechase, hot dogs and bathhouses, packed on summer Sundays and quiet in '
             'winter.', ['amusements', 'beach', 'boardwalk', 'summer'], 40.575, -73.981, 'low',
             ([15, 25], [22, 35], [30, 50]), ['frame-house', 'bungalow', 'rooming-house'], 'medium',
             [BMT, TROLLEY]),
        # The Bronx, Queens and New Jersey
        hood('bronx', 'The Bronx and the Grand Concourse', 'New apartment houses with elevators going up along the '
             'Grand Concourse for families moving out of Manhattan, Yankee Stadium at 161st Street, the Zoo and '
             'the Botanical Garden, and Italian Belmont around Arthur Avenue.', ['new-apartments', 'family',
             'baseball', 'parks'], 40.835, -73.920, 'mid', ([25, 40], [45, 70], [60, 95]),
             ['apartment-house', 'frame-house', 'walk-up'], 'medium', [IRT, THIRD, CENTRAL, TROLLEY]),
        hood('astoria', 'Astoria and Long Island City', 'Queens across the East River: factories and rail yards '
             'in Long Island City, German, Italian and Irish blocks in Astoria, the Steinway piano works and the '
             'Famous Players-Lasky movie studio.', ['industrial', 'movies', 'immigrant'], 40.764, -73.923, 'low',
             ([16, 28], [25, 40], [35, 55]), ['frame-house', 'row-house', 'walk-up'], 'medium',
             [IRT, BMT, TROLLEY]),
        hood('hoboken', 'Hoboken, New Jersey', 'A mile-square German and Italian river town across the Hudson, '
             'with the Lackawanna terminal, transatlantic piers, Stevens Institute and a reputation for '
             'easygoing saloons, reached by ferry or the Hudson tubes.', ['across-the-river', 'waterfront',
             'german', 'saloons'], 40.744, -74.030, 'low', ([14, 24], [20, 32], [28, 45]),
             ['row-house', 'tenement', 'walk-up'], 'high', [TUBES, FERRY, TROLLEY]),
    ],
    'transit': [
        line(IRT, 'IRT subway', 'subway', 'The Interborough Rapid Transit\'s subway: the Broadway-Seventh Avenue '
             'line up the West Side and the Lexington Avenue line up the East Side, with branches into the Bronx '
             'and Brooklyn. A nickel a ride.'),
        line(BMT, 'BMT subway', 'subway', 'The Brooklyn-Manhattan Transit\'s Broadway line under Manhattan, the '
             'lines out to Coney Island and Astoria, and the new Fourteenth Street line to Williamsburg. A nickel.'),
        line(THIRD, 'Third and Second Avenue Els', 'subway', 'Steel elevated railways over the Bowery, Second and '
             'Third Avenues from South Ferry to the Bronx, noisy and dark underneath but quick, for a nickel.'),
        line(WEST_ELS, 'Sixth and Ninth Avenue Els', 'subway', 'Elevated lines up the West Side over Sixth Avenue, '
             'Ninth Avenue and Columbus Avenue to Harlem and the Polo Grounds.'),
        line(TUBES, 'Hudson tubes', 'subway', 'The Hudson and Manhattan Railroad under the river from Hoboken and '
             'Jersey City to Hudson Terminal downtown and up Sixth Avenue to 33rd Street.'),
        line(TROLLEY, 'Streetcars', 'streetcar', 'Electric trolleys on the crosstown streets and up Broadway, and a '
             'web of lines across Brooklyn, the Bronx, Queens and Hoboken. Brooklynites dodging them gave the '
             'ball club its nickname.'),
        line(COACH, 'Fifth Avenue Coach', 'bus', 'Double-decker motor buses on Fifth Avenue and Riverside Drive, a '
             'dime a ride, with open tops for the view in summer.'),
        line(FERRY, 'Harbor ferries', 'ferry', 'Ferries from the Battery to Staten Island, Ellis Island and the '
             'Statue, and across the Hudson from Barclay, Christopher and 23rd Streets to Hoboken.'),
        line(PRR, 'Pennsylvania Railroad', 'commuter-rail', 'Trains from Pennsylvania Station under the Hudson to '
             'Newark, Philadelphia and points west, and under the East River on the Long Island Rail Road.'),
        line(CENTRAL, 'New York Central', 'commuter-rail', 'Trains from Grand Central Terminal up the Hudson and to '
             'Westchester, with a stop at 125th Street in Harlem.'),
        line(TAXI, 'Taxicabs', 'car', 'Yellow and Checker cabs cruising Manhattan, about twenty cents for the first '
             'quarter mile; private motorcars crowd Fifth Avenue too.'),
        line(WALK, 'Walking', 'walk', 'Most New Yorkers walk everywhere they can, and a nickel saved on a short '
             'ride is a nickel for coffee.'),
    ],
    'places': [
        # Harlem
        place('cotton-club', 'The Cotton Club', 'nightlife', 'harlem', 'Owney Madden\'s nightclub at Lenox Avenue and '
              '142nd Street: Black dancers and a hot band in elaborate revues, a whites-only audience, steep prices '
              'and liquor served under the noses of the law.', ['jazz', 'revue', 'segregated', 'gangsters'], '$$$$',
              'indoor', ADULT, LATE),
        place('connies-inn', 'Connie\'s Inn', 'nightlife', 'harlem', 'Connie and George Immerman\'s basement club on '
              'Seventh Avenue at 131st Street, with revues and a hot band, and, like the Cotton Club, white '
              'customers only.', ['jazz', 'revue', 'segregated'], '$$$', 'indoor', ADULT, LATE),
        place('smalls-paradise', 'Small\'s Paradise', 'nightlife', 'harlem', 'Ed Smalls\'s big basement cabaret at '
              'Seventh Avenue and 135th Street, opened in the fall of 1925: Black-owned, open to everyone, with '
              'waiters who dance the Charleston carrying trays.', ['jazz', 'dancing', 'black-owned', 'integrated'],
              '$$', 'indoor', ADULT, LATE),
        place('leroys', 'Leroy\'s', 'nightlife', 'harlem', 'Leroy Wilkins\'s cabaret at Fifth Avenue and 135th '
              'Street, one of Harlem\'s oldest, where the stride pianists cut each other late at night and the '
              'crowd is from the neighborhood.', ['stride-piano', 'local', 'black-owned'], '$$', 'indoor', ADULT,
              LATE),
        place('lafayette-theatre', 'Lafayette Theatre', 'venue', 'harlem', 'The big theater on Seventh Avenue at '
              '132nd Street, home of the Lafayette Players stock company and of revues, with the "Tree of Hope" '
              'outside where performers wait for work.', ['theater', 'revue', 'black-theater'], '$', 'indoor', ALL,
              DINNER),
        place('135th-street-library', '135th Street Branch Library', 'library', 'harlem', 'The Public Library\'s '
              'Harlem branch, where the new Division of Negro Literature, History and Prints opened in 1925 and '
              'young writers meet for readings.', ['books', 'harlem-renaissance', 'readings', 'free'], 'free',
              'indoor', ALL, ALLDAY),
        place('abyssinian-baptist-church', 'Abyssinian Baptist Church', 'temple', 'harlem', 'One of the largest '
              'Protestant congregations in the country, in its new Gothic church on West 138th Street since 1923, '
              'led by the Reverend Adam Clayton Powell Sr.', ['church', 'gospel', 'community'], 'free', 'indoor',
              ALL, DAY),
        place('strivers-row', 'Strivers\' Row', 'square', 'harlem', 'The elegant row houses of West 138th and '
              '139th Streets, home to Harlem\'s doctors, lawyers and successful musicians, with signs on the '
              'gates asking people to walk their horses.', ['architecture', 'walk', 'respectable'], 'free',
              'outdoor', ALL, DAY),
        place('liberty-hall', 'Liberty Hall', 'landmark', 'harlem', 'The meeting hall of Marcus Garvey\'s Universal '
              'Negro Improvement Association on West 138th Street, still full on meeting nights though Garvey '
              'himself went to federal prison in Atlanta in February 1925.', ['politics', 'garvey', 'meetings'],
              'free', 'indoor', ADULT, DINNER),
        place('lenox-avenue-lunchroom', 'Lenox Avenue lunchrooms', 'restaurant', 'harlem', 'Counters and family '
              'restaurants along Lenox Avenue serving Southern cooking: fried chicken, pork chops, greens, '
              'biscuits and sweet potato pie, till late for the musicians.', ['southern-cooking', 'late',
              'cheap'], '$', 'indoor', ALL, ['afternoon', 'evening', 'late'], cuisine='Southern'),
        # Sugar Hill
        place('polo-grounds', 'The Polo Grounds', 'stadium', 'sugar-hill', 'The horseshoe-shaped home of John '
              'McGraw\'s New York Giants under Coogan\'s Bluff at 155th Street, where people without tickets '
              'watch from the bluff for free.', ['baseball', 'giants', 'football'], '$', 'outdoor', ALL,
              ['afternoon'], BALLGAME),
        place('jumel-mansion', 'Jumel Mansion', 'museum', 'sugar-hill', 'The colonial house on the heights at 160th '
              'Street where Washington had his headquarters in 1776, kept as a museum by patriotic societies.',
              ['history', 'colonial', 'quiet'], '$', 'indoor', ALL, DAY),
        place('st-nicholas-park', 'St. Nicholas Park', 'park', 'sugar-hill', 'A steep green park climbing from '
              'Harlem up to City College, with long stone stairways and views east over the rooftops.',
              ['park', 'stairs', 'views'], 'free', 'outdoor', ALL, DAY),
        place('amsterdam-avenue-lunchroom', 'Amsterdam Avenue lunchroom', 'restaurant', 'sugar-hill', 'A '
              'steam-table lunchroom near City College where students and clerks get soup, a hot sandwich and pie '
              'for a quarter or two.', ['cheap', 'students', 'lunch'], '$', 'indoor', ALL, DAY,
              cuisine='American'),
        place('convent-avenue-soda-fountain', 'Convent Avenue drugstore soda fountain', 'cafe', 'sugar-hill', 'A '
              'marble-counter soda fountain in a corner drugstore: egg creams, ice cream sodas, coffee and '
              'gossip.', ['soda-fountain', 'sweets', 'neighborhood'], '$', 'indoor', ALL, ALLDAY),
        # San Juan Hill
        place('jungles-casino', 'The Jungles Casino', 'nightlife', 'san-juan-hill', 'A rough basement dance hall on '
              'West 62nd Street where dockworkers from the Carolinas dance to James P. Johnson\'s stride piano, '
              'and where people say the Charleston took shape.', ['dancing', 'stride-piano', 'charleston'], '$',
              'indoor', ADULT, LATE),
        place('st-cyprians-chapel', 'St. Cyprian\'s Chapel', 'temple', 'san-juan-hill', 'An Episcopal chapel and '
              'mission on West 63rd Street serving the neighborhood\'s Black families with services, a gym and '
              'a day nursery.', ['church', 'community'], 'free', 'indoor', ALL, DAY),
        place('columbus-circle', 'Columbus Circle', 'square', 'san-juan-hill', 'The traffic circle at the corner of '
              'Central Park with Columbus on his column and the Maine monument, where soapbox speakers draw '
              'crowds on summer evenings.', ['soapbox', 'traffic', 'monuments'], 'free', 'outdoor', ALL,
              ['afternoon', 'evening']),
        place('west-61st-street-speakeasy', 'West 61st Street speakeasy', 'bar', 'san-juan-hill', 'A back room '
              'behind a tailor\'s front on West 61st Street pouring gin and needle beer to dockworkers and '
              'musicians.', ['speakeasy', 'gin', 'local'], '$', 'indoor', ADULT, LATE),
        place('amsterdam-avenue-fish-fry', 'Amsterdam Avenue fish fry', 'restaurant', 'san-juan-hill', 'Fried '
              'porgies, whiting and cornbread from a storefront kitchen, wrapped in newspaper on Friday '
              'nights.', ['fish', 'cheap', 'friday'], '$', 'indoor', ALL, ['afternoon', 'evening'],
              cuisine='Southern'),
        # Upper West Side
        place('central-park', 'Central Park', 'park', 'upper-west-side', 'Olmsted and Vaux\'s great park: the Mall '
              'and its bandstand, rowboats on the Lake, the Sheep Meadow with real sheep, skating when the ponds '
              'freeze and carriage drives.', ['walk', 'boating', 'skating', 'band-concerts'], 'free', 'outdoor', ALL,
              ALLDAY),
        place('natural-history-museum', 'American Museum of Natural History', 'museum', 'upper-west-side', 'The '
              'great museum on Central Park West, with dinosaur skeletons, Roy Chapman Andrews\'s dinosaur eggs '
              'from the Gobi and halls of animals in painted settings.', ['dinosaurs', 'science', 'rainy-day'],
              'free', 'indoor', ALL, DAY),
        place('grants-tomb', 'Grant\'s Tomb and Riverside Drive', 'landmark', 'upper-west-side', 'The granite tomb '
              'of General Grant high over the Hudson, at the end of a long promenade along Riverside Drive.',
              ['monument', 'river-views', 'walk'], 'free', 'outdoor', ALL, DAY),
        place('st-john-the-divine', 'Cathedral of St. John the Divine', 'temple', 'upper-west-side', 'The vast '
              'Episcopal cathedral on Morningside Heights, half built, with a citywide campaign under way in '
              '1925 to raise money for its nave.', ['cathedral', 'architecture', 'quiet'], 'free', 'indoor', ALL,
              DAY),
        place('childs-upper-broadway', 'Childs on upper Broadway', 'restaurant', 'upper-west-side', 'A white-tiled '
              'Childs restaurant with a cook flipping wheatcakes in the window, clean, cheap and open early and '
              'late.', ['wheatcakes', 'cheap', 'chain'], '$', 'indoor', ALL, ['morning', 'afternoon', 'evening',
              'late'], cuisine='American'),
        place('broadway-delicatessen', 'Upper Broadway delicatessen', 'restaurant', 'upper-west-side', 'A busy '
              'delicatessen for corned beef, pastrami, pickles and celery tonic, crowded after the movie houses '
              'let out.', ['deli', 'pastrami', 'late'], '$', 'indoor', ALL, AFTERNOON_ON, cuisine='Jewish deli'),
        # Yorkville
        place('metropolitan-museum', 'Metropolitan Museum of Art', 'museum', 'yorkville', 'The great art museum on '
              'Fifth Avenue at 82nd Street, with Egyptian tombs, armor, Old Masters and a new American Wing '
              'opened in 1924.', ['art', 'egyptian', 'american-wing', 'rainy-day'], 'free', 'indoor', ALL, DAY),
        place('central-park-menagerie', 'Central Park Menagerie', 'attraction', 'yorkville', 'The free menagerie '
              'behind the old Arsenal at Fifth Avenue and 64th Street, with lions, bears, monkeys and seals, '
              'popular with families on Sundays.', ['animals', 'family', 'free'], 'free', 'outdoor', ALL, DAY),
        place('yorkville-casino', 'Yorkville Casino', 'venue', 'yorkville', 'A big hall on East 86th Street for '
              'German dances, club balls, concerts, boxing and union meetings.', ['dancing', 'german', 'meetings'],
              '$', 'indoor', ['friends', 'date', 'family'], NIGHT),
        place('turn-verein', 'New York Turn Verein', 'fitness', 'yorkville', 'The German gymnastic society\'s '
              'building on Lexington Avenue, with a gymnasium, bowling alleys and a hall for singing societies.',
              ['gymnastics', 'bowling', 'german', 'club'], '$', 'indoor', ['solo', 'friends', 'family'],
              ['afternoon', 'evening']),
        place('carl-schurz-park', 'Carl Schurz Park', 'park', 'yorkville', 'A small riverside park at East 86th '
              'Street with a promenade over the East River and old Gracie Mansion in its grounds.',
              ['river-views', 'promenade', 'quiet'], 'free', 'outdoor', ALL, DAY),
        place('third-avenue-konditorei', 'Third Avenue Konditorei', 'cafe', 'yorkville', 'A German pastry shop and '
              'coffee house under the El, with strudel, Linzer tortes, Kaffee mit Schlag and newspapers in '
              'German.', ['pastry', 'coffee', 'german'], '$', 'indoor', ALL, ALLDAY, cuisine='German'),
        place('east-86th-street-restaurants', 'East 86th Street German and Hungarian restaurants', 'restaurant',
              'yorkville', 'Wood-paneled restaurants serving sauerbraten, goulash, schnitzel and dumplings, with '
              'near beer on the menu and something stronger for regulars.', ['german', 'hungarian', 'hearty'],
              '$$', 'indoor', ALL, ['afternoon', 'evening'], cuisine='German and Hungarian'),
        # Midtown
        place('public-library', 'New York Public Library', 'library', 'midtown', 'The marble library on Fifth '
              'Avenue at 42nd Street, guarded by its stone lions, with the great Reading Room upstairs open to '
              'anyone.', ['books', 'reading-room', 'free', 'architecture'], 'free', 'indoor', ['solo', 'date'],
              ALLDAY),
        place('grand-central-terminal', 'Grand Central Terminal', 'landmark', 'midtown', 'The New York Central\'s '
              'great terminal on 42nd Street, with its starry ceiling, the information booth clock and crowds of '
              'commuters.', ['railroad', 'architecture', 'meeting-place'], 'free', 'indoor', ALL, ALLDAY),
        place('oyster-bar', 'Grand Central Oyster Bar', 'restaurant', 'midtown', 'The tiled vaults below the '
              'terminal, serving oyster stew and pan roasts at the counter to commuters.', ['oysters', 'seafood',
              'counter'], '$$', 'indoor', ['solo', 'friends', 'date'], ['afternoon', 'evening'], cuisine='Seafood'),
        place('algonquin-hotel', 'Algonquin Hotel', 'restaurant', 'midtown', 'The hotel on West 44th Street where '
              'Dorothy Parker, Robert Benchley, Alexander Woollcott and the Round Table trade wisecracks over '
              'lunch, and where the new magazine The New Yorker was hatched.', ['round-table', 'writers', 'lunch'],
              '$$$', 'indoor', ['solo', 'friends', 'date'], ['afternoon', 'evening'], cuisine='American'),
        place('st-patricks-cathedral', 'St. Patrick\'s Cathedral', 'temple', 'midtown', 'The Gothic Catholic '
              'cathedral on Fifth Avenue at 50th Street, the spiritual home of Irish New York.', ['cathedral',
              'catholic', 'architecture'], 'free', 'indoor', ALL, ALLDAY),
        place('saks-fifth-avenue', 'Saks Fifth Avenue', 'shopping', 'midtown', 'The new department store at Fifth '
              'Avenue and 50th Street, opened in September 1924, for the smart set\'s clothes.', ['fashion',
              'department-store', 'new'], '$$$', 'indoor', ['solo', 'friends', 'date'], DAY),
        place('tony-somas', 'Tony Soma\'s', 'bar', 'midtown', 'Tony Soma\'s speakeasy in a brownstone on West 49th '
              'Street, where the Algonquin crowd drinks and the host sings opera standing on his head.',
              ['speakeasy', 'writers', 'cocktails'], '$$$', 'indoor', ADULT, NIGHT),
        place('schraffts', 'Schrafft\'s', 'cafe', 'midtown', 'A genteel lunchroom with '
              'waitresses in black, chicken salad, ice cream sundaes and no liquor, where women shoppers lunch '
              'alone without a second glance.', ['lunch', 'ice-cream', 'genteel'], '$$', 'indoor', ALL, ALLDAY,
              cuisine='American'),
        # Times Square
        place('times-square-crossroads', 'Times Square', 'square', 'times-square', 'The crossroads of Broadway and Seventh '
              'Avenue under the Times Tower, blazing with electric signs at night, with the news running in '
              'lights and crowds at every hour.', ['electric-signs', 'crowds', 'night'], 'free', 'outdoor', ALL,
              ['afternoon', 'evening', 'late']),
        place('new-amsterdam-theatre', 'New Amsterdam Theatre', 'venue', 'times-square', 'The Art Nouveau theater '
              'on 42nd Street, home of Florenz Ziegfeld\'s Follies with their staircases of showgirls, comics like '
              'W. C. Fields and Will Rogers, and the Midnight Frolic on the roof.', ['ziegfeld-follies', 'revue',
              'broadway'], '$$$', 'indoor', ['friends', 'date', 'family'], DINNER),
        place('palace-theatre', 'The Palace', 'venue', 'times-square', 'The Keith-Albee vaudeville house on '
              'Broadway at 47th Street: two shows a day, and every act in America dreams of playing it.',
              ['vaudeville', 'broadway', 'comedy'], '$$', 'indoor', ALL, ['afternoon', 'evening']),
        place('capitol-theatre', 'Capitol Theatre', 'venue', 'times-square', 'The biggest movie palace in the world '
              'on Broadway at 51st Street, with over five thousand seats, a symphony orchestra, a ballet and a '
              'feature film.', ['movies', 'movie-palace', 'orchestra'], '$', 'indoor', ALL,
              ['afternoon', 'evening']),
        place('roseland-ballroom', 'Roseland Ballroom', 'nightlife', 'times-square', 'The dance palace on Broadway '
              'at 51st Street, where hostesses dance with customers at ten cents a dance and Fletcher Henderson\'s '
              'orchestra, with a young cornetist named Louis Armstrong, plays for white dancers.',
              ['dancing', 'jazz', 'taxi-dancers', 'segregated'], '$', 'indoor', ADULT, NIGHT),
        place('times-square-automat', 'Horn and Hardart Automat', 'restaurant', 'times-square', 'The automat on '
              'Broadway at 46th Street: walls of little glass doors, nickels from the cashier, coffee from '
              'dolphin-head spouts and pie, beans or macaroni at any hour.', ['automat', 'nickels', 'cheap',
              'late'], '$', 'indoor', ALL, ['morning', 'afternoon', 'evening', 'late'], cuisine='American'),
        place('lindys', 'Lindy\'s', 'restaurant', 'times-square', 'Leo Lindemann\'s delicatessen restaurant on '
              'Broadway near 50th Street, where gamblers, song writers and actors eat cheesecake after the '
              'show.', ['cheesecake', 'show-people', 'late'], '$$', 'indoor', ADULT, ['evening', 'late'],
              cuisine='Jewish deli'),
        place('texas-guinans', 'Texas Guinan\'s club', 'nightlife', 'times-square', 'Texas Guinan\'s speakeasy '
              'nightclub in the West Forties, greeting every customer with "Hello, suckers!", padlocked by '
              'Prohibition agents now and then and reopened under a new name.', ['speakeasy', 'nightclub',
              'champagne', 'notorious'], '$$$$', 'indoor', ADULT, LATE),
        # Herald Square
        place('macys', 'Macy\'s', 'shopping', 'herald-square', 'The world\'s largest store, at Herald Square on 34th '
              'Street, newly enlarged, with bargains on every floor and crowds at Christmas.', ['department-store',
              'bargains', 'christmas'], '$$', 'indoor', ALL, DAY),
        place('gimbels', 'Gimbels', 'shopping', 'herald-square', 'Macy\'s rival across Herald Square, linked by a '
              'tunnel to Pennsylvania Station, with its own bargain basement.', ['department-store', 'bargains'],
              '$$', 'indoor', ALL, DAY),
        place('penn-station', 'Pennsylvania Station', 'landmark', 'herald-square', 'The Pennsylvania Railroad\'s '
              'pink granite station modeled on the Baths of Caracalla, with a vast waiting room and glass-roofed '
              'concourse, red caps and Pullman porters.', ['railroad', 'architecture', 'travel'], 'free', 'indoor',
              ALL, ALLDAY),
        place('tin-pan-alley', 'Tin Pan Alley', 'square', 'herald-square', 'West 28th Street between Broadway and '
              'Sixth Avenue, where song publishers got their start and pianos still clatter from open windows, '
              'though the bigger firms have moved up toward Times Square.', ['music', 'song-pluggers', 'pianos'],
              'free', 'outdoor', ['solo', 'friends'], DAY),
        place('garment-center', 'Seventh Avenue garment lofts', 'workshop', 'herald-square', 'Tall new loft '
              'buildings on Seventh Avenue in the Thirties full of cutting tables and sewing machines, with racks '
              'of dresses pushed through the streets.', ['garment', 'work', 'busy'], 'free', 'indoor', ['solo'],
              DAY),
        place('keens-chop-house', 'Keens Chop House', 'restaurant', 'herald-square', 'The old chophouse on West '
              '36th Street with clay pipes on the ceiling and huge mutton chops, now open to women as well as men.',
              ['chophouse', 'mutton', 'historic'], '$$$', 'indoor', ['solo', 'friends', 'date'], DINNER,
              cuisine='Chophouse'),
        place('garment-district-cafeteria', 'Seventh Avenue cafeteria', 'restaurant', 'herald-square', 'A big '
              'self-service cafeteria where garment workers line up at noon for soup, a sandwich and coffee, and '
              'cutters argue union politics over the tables.', ['cafeteria', 'cheap', 'workers'], '$', 'indoor',
              ['solo', 'friends', 'coworkers'], DAY, cuisine='American'),
        # Hell's Kitchen
        place('madison-square-garden', 'Madison Square Garden', 'stadium', 'hells-kitchen', 'Tex Rickard\'s new '
              'Garden on Eighth Avenue at 49th Street, opened at the end of November 1925, for boxing, hockey, '
              'the circus and six-day bicycle races.', ['boxing', 'hockey', 'bicycle-races', 'new'], '$$', 'indoor',
              ['solo', 'friends', 'date'], NIGHT, ['fall', 'winter', 'spring']),
        place('death-avenue', 'West Side freight line', 'square', 'hells-kitchen', 'Freight trains running down '
              'the middle of Tenth and Eleventh Avenues, led by a "West Side cowboy" on horseback waving a red flag; locals call '
              'it Death Avenue.', ['railroad', 'street-life', 'danger'], 'free', 'outdoor', ['solo', 'friends'],
              DAY),
        place('paddys-market', 'Paddy\'s Market', 'market', 'hells-kitchen', 'Pushcarts and stalls under the Ninth '
              'Avenue El in the high Thirties and Forties selling fruit, fish, meat and Greek and Italian '
              'groceries, busiest on Saturday nights.', ['pushcarts', 'groceries', 'bargains'], '$', 'outdoor', ALL,
              ['morning', 'afternoon', 'evening']),
        place('holy-cross-church', 'Holy Cross Church', 'temple', 'hells-kitchen', 'The Catholic church on West 42nd '
              'Street whose pastor is Father Francis Duffy, chaplain of the Fighting 69th in the war.', ['church',
              'catholic', 'irish'], 'free', 'indoor', ALL, DAY),
        place('stillmans-gym', 'Stillman\'s Gym', 'fitness', 'hells-kitchen', 'A grimy upstairs boxing gym on Eighth '
              'Avenue where fighters spar for watching managers and the public pays to look on.', ['boxing',
              'sparring', 'gritty'], '$', 'indoor', ['solo', 'friends'], DAY),
        place('tenth-avenue-speakeasy', 'Tenth Avenue speakeasy', 'bar', 'hells-kitchen', 'An old Irish saloon '
              'carrying on as a speakeasy behind soaped windows, with a peephole in the door and whiskey of '
              'doubtful origin.', ['speakeasy', 'irish', 'whiskey'], '$', 'indoor', ADULT, NIGHT),
        # Chelsea
        place('chelsea-piers', 'Chelsea Piers', 'docks', 'chelsea', 'The long granite-faced piers on the Hudson '
              'where the great Cunard and White Star liners dock, with crowds seeing passengers off to Europe.',
              ['liners', 'river', 'farewells'], 'free', 'outdoor', ALL, DAY),
        place('hotel-chelsea', 'Hotel Chelsea', 'inn', 'chelsea', 'The red-brick hotel on West 23rd Street with '
              'iron balconies, long a home for writers, painters and actors who stay for years.', ['artists',
              'writers', 'hotel'], '$$', 'indoor', ['solo', 'date'], ALLDAY),
        place('old-homestead', 'Old Homestead', 'restaurant', 'chelsea', 'The steakhouse on Ninth Avenue by the meat '
              'market, serving beef since the 1860s.', ['steak', 'historic'], '$$$', 'indoor', ['friends', 'date',
              'family'], DINNER, cuisine='Steakhouse'),
        place('gansevoort-market', 'Gansevoort meat market', 'market', 'chelsea', 'The wholesale meat and produce '
              'market around Gansevoort Street, loud with wagons and trucks before dawn.', ['wholesale', 'meat',
              'early'], '$', 'outdoor', ['solo'], ['morning']),
        place('chelsea-lunch-wagon', 'Tenth Avenue lunch wagon', 'restaurant', 'chelsea', 'An old horse-car turned '
              'diner by the piers, open all night for longshoremen, cabbies and anyone off a late ship.',
              ['diner', 'all-night', 'cheap'], '$', 'indoor', ['solo', 'friends'], ['morning', 'evening', 'late'],
              cuisine='American'),
        place('eighth-avenue-speakeasy', 'Eighth Avenue speakeasy', 'bar', 'chelsea', 'A cellar speakeasy on Eighth '
              'Avenue where a doorman looks you over through a slot and gin comes in coffee cups.', ['speakeasy',
              'gin'], '$$', 'indoor', ADULT, NIGHT),
        # Greenwich Village
        place('washington-square-park', 'Washington Square Park', 'park', 'greenwich-village', 'The square under the '
              'marble arch at the foot of Fifth Avenue, with NYU on one side, old red-brick houses on the other '
              'and Village characters on the benches.', ['arch', 'bohemian', 'benches'], 'free', 'outdoor', ALL,
              ALLDAY),
        place('chumleys', 'Chumley\'s', 'bar', 'greenwich-village', 'Lee Chumley\'s speakeasy behind an unmarked '
              'door on Bedford Street, with a back way out through a courtyard, book jackets on the walls and '
              'writers at the tables.', ['speakeasy', 'writers', 'hidden'], '$$', 'indoor', ADULT, NIGHT),
        place('provincetown-playhouse', 'Provincetown Playhouse', 'venue', 'greenwich-village', 'The little theater '
              'on MacDougal Street where the Provincetown Players put on Eugene O\'Neill\'s plays first.',
              ['little-theater', 'oneill', 'experimental'], '$', 'indoor', ['solo', 'friends', 'date'], DINNER),
        place('cherry-lane-theatre', 'Cherry Lane Theatre', 'venue', 'greenwich-village', 'A little theater in an '
              'old box factory on Commerce Street, founded in 1924 by Edna St. Vincent Millay and friends.',
              ['little-theater', 'new', 'poets'], '$', 'indoor', ['solo', 'friends', 'date'], DINNER),
        place('jack-and-charlies', 'Jack and Charlie\'s', 'bar', 'greenwich-village', 'Jack Kriendler and Charlie '
              'Berns\'s little speakeasy in the Village, started as the Red Head in 1922 and moved and renamed '
              'since, popular with college men and newspapermen.', ['speakeasy', 'college-crowd', 'cocktails'],
              '$$$', 'indoor', ADULT, NIGHT),
        place('romany-maries', 'Romany Marie\'s', 'cafe', 'greenwich-village', 'Marie Marchand\'s candle-lit tea '
              'room, where painters, poets and inventors talk half the night over Romanian food and Turkish '
              'coffee.', ['tea-room', 'bohemian', 'talk'], '$', 'indoor', ['solo', 'friends', 'date'],
              ['afternoon', 'evening', 'late'], cuisine='Romanian'),
        place('brevoort-cafe', 'Café of the Hotel Brevoort', 'restaurant', 'greenwich-village', 'The French '
              'basement café of the old Brevoort on Fifth Avenue, for long lunches among writers, painters and '
              'radicals.', ['french', 'writers', 'cafe'], '$$', 'indoor', ['solo', 'friends', 'date'],
              ['afternoon', 'evening'], cuisine='French'),
        # Union Square and Gramercy
        place('union-square-plaza', 'Union Square', 'square', 'union-square', 'The square at 14th Street where soapbox '
              'socialists, communists and preachers argue with passers-by, and May Day rallies fill the plaza.',
              ['soapbox', 'politics', 'rallies'], 'free', 'outdoor', ALL, DAY),
        place('flatiron-building', 'Flatiron Building', 'landmark', 'union-square', 'The thin wedge of a skyscraper '
              'at 23rd Street, where the wind whips round the corner and lifts skirts and hats.', ['skyscraper',
              'architecture'], 'free', 'outdoor', ALL, DAY),
        place('luchows', 'Lüchow\'s', 'restaurant', 'union-square', 'The big German restaurant on 14th Street, with '
              'dark wood, a string orchestra, venison and pancakes, and beer that has to be the legal kind '
              'now.', ['german', 'orchestra', 'historic'], '$$$', 'indoor', ['friends', 'date', 'family'],
              ['afternoon', 'evening'], cuisine='German'),
        place('mcsorleys', 'McSorley\'s Old Ale House', 'bar', 'union-square', 'The sawdust-floored saloon on East '
              '7th Street near Cooper Union, men only, still pouring its own "near beer" brewed in the cellar.',
              ['saloon', 'ale', 'men-only', 'historic'], '$', 'indoor', ['solo', 'friends'], NIGHT),
        place('petes-tavern', 'Pete\'s Tavern', 'bar', 'union-square', 'An old Irving Place saloon carrying on behind '
              'the front of a flower shop, with booths and a long bar.', ['speakeasy', 'historic', 'booths'], '$$',
              'indoor', ADULT, NIGHT),
        place('tammany-hall', 'Tammany Hall', 'landmark', 'union-square', 'The Democratic machine\'s headquarters on '
              '14th Street, where ward bosses trade jobs and favors for votes.', ['politics', 'machine'], 'free',
              'outdoor', ['solo'], DAY),
        place('cooper-union-great-hall', 'Great Hall of Cooper Union', 'venue', 'union-square', 'The basement '
              'lecture hall at Astor Place where Lincoln spoke, now holding free evening lectures and debates.',
              ['lectures', 'free', 'debates'], 'free', 'indoor', ['solo', 'friends'], DINNER),
        # Lower East Side
        place('katzs', 'Katz\'s Delicatessen', 'restaurant', 'lower-east-side', 'The delicatessen on Houston Street '
              'at Ludlow, with hand-carved pastrami and corned beef at long counters.',
              ['deli', 'pastrami', 'historic'], '$', 'indoor', ALL, ['morning', 'afternoon', 'evening', 'late'],
              cuisine='Jewish deli'),
        place('eldridge-street-synagogue', 'Eldridge Street Synagogue', 'temple', 'lower-east-side', 'The great '
              'Orthodox synagogue of 1887 with its rose window, its congregation thinning as families move to '
              'Brooklyn and the Bronx.', ['synagogue', 'orthodox', 'architecture'], 'free', 'indoor', ALL, DAY),
        place('orchard-street-market', 'Orchard Street pushcarts', 'market', 'lower-east-side', 'Pushcarts lining '
              'Orchard and Hester Streets with everything from pickles to petticoats, haggled over in Yiddish.',
              ['pushcarts', 'bargains', 'yiddish'], '$', 'outdoor', ALL, DAY),
        place('second-avenue-theatres', 'Second Avenue Yiddish theaters', 'venue', 'lower-east-side', 'The Yiddish '
              'Rialto on Second Avenue, with melodramas, operettas and Shakespeare in Yiddish, and stars '
              'mobbed at the stage door.', ['yiddish-theater', 'melodrama', 'stars'], '$', 'indoor', ALL, DINNER),
        place('cafe-royal', 'Café Royal', 'cafe', 'lower-east-side', 'The café at Second Avenue and 12th Street '
              'where Yiddish actors, writers and critics hold court over glasses of tea.', ['yiddish-theater',
              'tea', 'talk'], '$', 'indoor', ['solo', 'friends', 'date'], ['afternoon', 'evening', 'late'],
              cuisine='Jewish'),
        place('russ-appetizing', 'Russ\'s appetizing store', 'shopping', 'lower-east-side', 'Joel Russ\'s appetizing '
              'store on Houston Street, with smoked salmon, herring, sable and cream cheese.',
              ['appetizing', 'smoked-fish'], '$', 'indoor', ALL, DAY),
        place('yonah-schimmel', 'Yonah Schimmel Knish Bakery', 'cafe', 'lower-east-side', 'The knish bakery on '
              'Houston Street, selling potato and kasha knishes hot from the oven.', ['knishes', 'cheap'], '$',
              'indoor', ALL, ALLDAY, cuisine='Jewish'),
        place('henry-street-settlement', 'Henry Street Settlement', 'landmark', 'lower-east-side', 'Lillian Wald\'s '
              'settlement house, sending visiting nurses into the tenements and running classes, clubs and a '
              'little playhouse.', ['settlement-house', 'nurses', 'classes'], 'free', 'indoor', ALL, DAY),
        place('tenth-street-baths', 'Tenth Street Russian and Turkish Baths', 'fitness', 'lower-east-side', 'The '
              'steam baths on East 10th Street, with a hot rock room, cold plunge and platza scrubs.', ['steam',
              'baths', 'schvitz'], '$', 'indoor', ['solo', 'friends'], ALLDAY),
        # Little Italy
        place('mulberry-street', 'Mulberry Street', 'market', 'little-italy', 'The crowded heart of Little Italy, '
              'with pushcarts of vegetables and clams, salumerias, and lights strung for the summer feasts.',
              ['pushcarts', 'italian', 'street-life'], '$', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('ferrara', 'Ferrara', 'cafe', 'little-italy', 'The pastry shop and café on Grand Street for espresso, '
              'cannoli and spumoni since 1892.', ['pastry', 'espresso'], '$', 'indoor', ALL, ALLDAY,
              cuisine='Italian pastry'),
        place('lombardis', 'Lombardi\'s', 'restaurant', 'little-italy', 'Gennaro Lombardi\'s grocery on Spring '
              'Street selling tomato pies baked in a coal oven, wrapped in paper for workers to take away.',
              ['pizza', 'coal-oven'], '$', 'indoor', ALL, ['afternoon', 'evening'], cuisine='Italian'),
        place('old-st-patricks', 'Old St. Patrick\'s Cathedral', 'temple', 'little-italy', 'The old cathedral on '
              'Mott Street, Irish once and now Italian, with catacombs under its walled churchyard.', ['church',
              'catholic', 'history'], 'free', 'indoor', ALL, DAY),
        place('mulberry-social-club', 'Mulberry Street social club', 'cafe', 'little-italy', 'A storefront club for '
              'men from one village in Campania, with espresso, cards and a picture of the patron saint, members '
              'only and visitors by invitation.', ['social-club', 'cards', 'espresso'], '$', 'indoor', ['solo',
              'friends'], ['afternoon', 'evening']),
        place('mulberry-wine-cellar', 'Mulberry Street wine cellar', 'bar', 'little-italy', 'A basement where '
              'homemade red wine is poured from barrels into jugs and glasses, quietly, for neighbors.',
              ['wine', 'speakeasy', 'homemade'], '$', 'indoor', ADULT, NIGHT),
        # Chinatown and the Bowery
        place('doyers-street', 'Doyers Street', 'square', 'chinatown', 'The crooked little street called the '
              'Bloody Angle, quiet by day and tense when the tong war between the Hip Sing and On Leong flares up, '
              'as it did again in 1924 and 1925.', ['history', 'narrow', 'tongs'], 'free', 'outdoor', ['solo',
              'friends'], DAY),
        place('nom-wah', 'Nom Wah Tea Parlor', 'cafe', 'chinatown', 'A bakery and tea parlor at 11 Doyers Street, '
              'opened in 1920, selling almond cookies, mooncakes and tea.', ['tea', 'pastry', 'dim-sum'], '$',
              'indoor', ALL, DAY, cuisine='Cantonese'),
        place('mott-street-chop-suey', 'Mott Street chop suey house', 'restaurant', 'chinatown', 'An upstairs '
              'restaurant with lanterns and carved screens serving chop suey and chow mein to sightseers and '
              'real Cantonese cooking to those who ask.', ['chop-suey', 'late', 'lanterns'], '$', 'indoor', ALL,
              ['afternoon', 'evening', 'late'], cuisine='Cantonese'),
        place('bowery-mission', 'Bowery Mission', 'landmark', 'chinatown', 'The mission at 227 Bowery offering soup, '
              'a bed and a sermon to the men of the flophouses.', ['charity', 'mission'], 'free', 'indoor',
              ['solo'], ['morning', 'evening']),
        place('columbus-park', 'Columbus Park', 'park', 'chinatown', 'The park made where the Mulberry Bend slum of '
              'the Five Points once stood, with old men playing cards and children everywhere.', ['history',
              'playground'], 'free', 'outdoor', ALL, DAY),
        place('chatham-square-coffee-stand', 'Bowery coffee-and stand', 'restaurant', 'chinatown', 'A counter under '
              'the El at Chatham Square serving "coffee and", a mug of coffee and a doughnut, for a nickel to '
              'anyone, any hour.', ['cheap', 'all-night'], '$', 'indoor', ['solo'], ['morning', 'late'],
              cuisine='American'),
        # City Hall
        place('city-hall-park', 'City Hall and its park', 'landmark', 'city-hall', 'The elegant old City Hall in its '
              'park, where Mayor Hylan is serving out his term while the dapper Jimmy Walker campaigns to replace him.', ['government',
              'park', 'history'], 'free', 'outdoor', ALL, DAY),
        place('woolworth-building', 'Woolworth Building', 'landmark', 'city-hall', 'The Gothic "Cathedral of '
              'Commerce" on Broadway, tallest building in the world, with an observation deck near the top for '
              'fifty cents.', ['skyscraper', 'views', 'architecture'], '$', 'mixed', ALL, DAY),
        place('brooklyn-bridge', 'Brooklyn Bridge', 'landmark', 'city-hall', 'The great stone and cable bridge with '
              'a wooden promenade above the traffic, the best free walk and view in the city.', ['bridge', 'walk',
              'views'], 'free', 'outdoor', ALL, ALLDAY),
        place('newspaper-row', 'Newspaper Row', 'square', 'city-hall', 'Park Row, where the World\'s gold dome and '
              'the other papers\' buildings face City Hall, and crowds watch bulletins posted in the windows.',
              ['newspapers', 'bulletins'], 'free', 'outdoor', ['solo', 'friends'], DAY),
        place('park-row-lunchroom', 'Park Row lunchroom', 'restaurant', 'city-hall', 'A narrow lunch counter where '
              'reporters, printers and court clerks eat beef stew and pie at speed.', ['cheap', 'newspapermen'],
              '$', 'indoor', ['solo', 'coworkers'], ['morning', 'afternoon', 'late'], cuisine='American'),
        place('chambers-street-speakeasy', 'Chambers Street speakeasy', 'bar', 'city-hall', 'A speakeasy near the '
              'courts where politicians, lawyers and reporters drink together and nobody remembers anything.',
              ['speakeasy', 'politicians', 'reporters'], '$$', 'indoor', ADULT, NIGHT),
        # Financial District and the Battery
        place('stock-exchange', 'New York Stock Exchange', 'landmark', 'financial-district', 'The temple-fronted '
              'exchange on Broad Street, roaring with a bull market, across from J. P. Morgan\'s offices still '
              'scarred by the 1920 bomb.', ['finance', 'architecture', 'bull-market'], 'free', 'outdoor', ['solo'],
              DAY),
        place('trinity-church', 'Trinity Church', 'temple', 'financial-district', 'The Gothic church at the head of '
              'Wall Street, its churchyard holding Alexander Hamilton and lunching clerks.', ['church',
              'churchyard', 'history'], 'free', 'mixed', ALL, DAY),
        place('fraunces-tavern', 'Fraunces Tavern', 'restaurant', 'financial-district', 'The restored colonial '
              'tavern on Pearl Street where Washington said farewell to his officers, with a museum upstairs.',
              ['history', 'colonial', 'museum'], '$$', 'indoor', ALL, ['afternoon', 'evening'], cuisine='American'),
        place('battery-park', 'Battery Park', 'park', 'financial-district', 'The harborside park at the tip of '
              'Manhattan with views of the Statue and the ships coming in.', ['harbor', 'views', 'walk'], 'free',
              'outdoor', ALL, ALLDAY),
        place('new-york-aquarium', 'New York Aquarium', 'attraction', 'financial-district', 'The free aquarium in '
              'the old round fort of Castle Clinton at the Battery, with seals, sea turtles and tanks of fish.',
              ['fish', 'family', 'free'], 'free', 'indoor', ALL, DAY),
        place('ellis-island', 'Ellis Island', 'landmark', 'financial-district', 'The immigration station in the '
              'harbor, much quieter since the quota law of 1924, where families still wait to meet relatives off '
              'the ferry.', ['immigration', 'harbor', 'ferry'], 'free', 'mixed', ALL, DAY),
        place('statue-of-liberty', 'Statue of Liberty', 'landmark', 'financial-district', 'The statue on Bedloe\'s '
              'Island, reached by ferry from the Battery, with a long climb to the crown.', ['harbor', 'ferry',
              'views'], '$', 'outdoor', ALL, DAY, WARM),
        place('fulton-fish-market', 'Fulton Fish Market', 'market', 'financial-district', 'The wholesale fish market '
              'on South Street, busy from before dawn, with sailing ships and steamers at the old piers.',
              ['fish', 'wholesale', 'waterfront'], '$', 'outdoor', ['solo'], ['morning']),
        place('sweets', 'Sweet\'s', 'restaurant', 'financial-district', 'The old seafood house upstairs on Fulton '
              'Street by the fish market, with broiled fish, chowder and no reservations.', ['seafood', 'historic'],
              '$$', 'indoor', ['solo', 'friends', 'coworkers'], DAY, cuisine='Seafood'),
        # Brooklyn Heights
        place('brooklyn-heights-streets', 'Columbia Heights and Pierrepont Street', 'square', 'brooklyn-heights',
              'Brownstone and Greek Revival streets on the bluff, with views of the harbor and the Manhattan '
              'skyline from the ends of the streets.', ['brownstones', 'views', 'walk'], 'free', 'outdoor', ALL,
              DAY),
        place('plymouth-church', 'Plymouth Church', 'temple', 'brooklyn-heights', 'Henry Ward Beecher\'s old '
              'Congregational church on Orange Street, once a stop on the Underground Railroad.', ['church',
              'abolition', 'history'], 'free', 'indoor', ALL, DAY),
        place('brooklyn-academy-of-music', 'Brooklyn Academy of Music', 'venue', 'brooklyn-heights', 'The grand '
              'hall on Lafayette Avenue for concerts, opera nights and lectures.', ['concerts', 'opera',
              'lectures'], '$$', 'indoor', ['friends', 'date', 'family'], DINNER),
        place('abraham-and-straus', 'Abraham and Straus', 'shopping', 'brooklyn-heights', 'Brooklyn\'s great '
              'department store on Fulton Street.', ['department-store'], '$$', 'indoor', ALL, DAY),
        place('gage-and-tollner', 'Gage and Tollner', 'restaurant', 'brooklyn-heights', 'The gaslit oyster and chop '
              'house on Fulton Street, with mirrored walls and waiters in long white aprons.', ['oysters',
              'chophouse', 'gaslight'], '$$$', 'indoor', ['friends', 'date', 'family'], DINNER, cuisine='Seafood'),
        place('fulton-street-speakeasy', 'Fulton Street speakeasy', 'bar', 'brooklyn-heights', 'A former saloon off '
              'Fulton Street pouring bootleg rye behind a cigar-store front.', ['speakeasy', 'rye'], '$', 'indoor',
              ADULT, NIGHT),
        # Williamsburg and Greenpoint
        place('peter-luger', 'Peter Luger', 'restaurant', 'williamsburg', 'The German steak house under the '
              'Williamsburg Bridge, with bare tables, porterhouse for two and waiters who have seen everything.',
              ['steak', 'german', 'historic'], '$$$', 'indoor', ['friends', 'date', 'family'], DINNER,
              cuisine='Steakhouse'),
        place('williamsburg-bridge', 'Williamsburg Bridge', 'landmark', 'williamsburg', 'The steel bridge to the '
              'Lower East Side, with trolleys, the El and a footpath crossed by thousands moving to Brooklyn.',
              ['bridge', 'walk'], 'free', 'outdoor', ALL, DAY),
        place('st-stanislaus-kostka', 'St. Stanislaus Kostka Church', 'temple', 'williamsburg', 'The Polish Catholic '
              'church of Greenpoint, its masses and feasts in Polish.', ['church', 'polish'], 'free', 'indoor', ALL,
              DAY),
        place('manhattan-avenue-shops', 'Manhattan Avenue shops', 'shopping', 'williamsburg', 'Greenpoint\'s main '
              'street of Polish butchers, bakeries, dry goods and shoe stores.', ['polish', 'shops'], '$', 'indoor',
              ALL, DAY),
        place('greenpoint-bakery', 'Greenpoint Polish bakery', 'cafe', 'williamsburg', 'A Polish bakery selling '
              'rye bread, babka and paczki, with coffee at a little counter.', ['bakery', 'polish'], '$', 'indoor',
              ALL, DAY, cuisine='Polish'),
        place('kent-avenue-speakeasy', 'Kent Avenue waterfront speakeasy', 'bar', 'williamsburg', 'A plain room by '
              'the refineries where sugar workers and longshoremen drink whiskey that came in by boat.',
              ['speakeasy', 'waterfront', 'rough'], '$', 'indoor', ADULT, NIGHT),
        # Flatbush
        place('ebbets-field', 'Ebbets Field', 'stadium', 'flatbush', 'The Brooklyn Robins\' brick ballpark on '
              'Bedford Avenue, small enough that the fans in the bleachers can shout at the players.',
              ['baseball', 'robins', 'fans'], '$', 'outdoor', ALL, ['afternoon'], BALLGAME),
        place('prospect-park', 'Prospect Park', 'park', 'flatbush', 'Olmsted and Vaux\'s Brooklyn park with the '
              'Long Meadow, a lake for boating and skating, a carousel and a bandstand.', ['meadow', 'boating',
              'skating'], 'free', 'outdoor', ALL, ALLDAY),
        place('brooklyn-botanic-garden', 'Brooklyn Botanic Garden', 'garden', 'flatbush', 'Gardens beside '
              'Prospect Park, with a Japanese hill-and-pond garden and cherry trees in spring.', ['gardens',
              'japanese-garden', 'cherry-blossoms'], 'free', 'outdoor', ALL, DAY, WARM),
        place('brooklyn-museum', 'Brooklyn Museum', 'museum', 'flatbush', 'The Brooklyn Institute\'s great museum on '
              'Eastern Parkway, with Egyptian antiquities and American paintings.', ['art', 'egyptian',
              'rainy-day'], 'free', 'indoor', ALL, DAY),
        place('flatbush-ice-cream-parlor', 'Flatbush Avenue ice cream parlor', 'cafe', 'flatbush', 'An ice cream '
              'parlor with wire chairs and a soda fountain, full of couples after the pictures.', ['ice-cream',
              'soda-fountain', 'dates'], '$', 'indoor', ALL, ['afternoon', 'evening']),
        place('flatbush-delicatessen', 'Flatbush delicatessen', 'restaurant', 'flatbush', 'A neighborhood '
              'delicatessen near the Brighton line for hot pastrami and potato salad.', ['deli'], '$', 'indoor',
              ALL, AFTERNOON_ON, cuisine='Jewish deli'),
        # Coney Island
        place('luna-park', 'Luna Park', 'attraction', 'coney-island', 'The fairyland of towers and minarets lit by '
              'a quarter of a million electric bulbs, with rides, shows and a ballroom.', ['rides',
              'electric-lights', 'amusements'], '$', 'outdoor', ALL, ['afternoon', 'evening'], SUMMER),
        place('steeplechase-park', 'Steeplechase Park', 'attraction', 'coney-island', 'George Tilyou\'s park under '
              'the grinning Funny Face, with mechanical horses racing round the track, the Blowhole that lifts '
              'hats and skirts, and the Pavilion of Fun.', ['rides', 'funhouse', 'amusements'], '$', 'mixed', ALL,
              ['afternoon', 'evening'], SUMMER),
        place('wonder-wheel', 'Wonder Wheel', 'attraction', 'coney-island', 'The big Ferris wheel, opened in 1920, '
              'with cars that slide on rails and give riders a scare.', ['ferris-wheel', 'views'], '$', 'outdoor',
              ALL, ['afternoon', 'evening'], SUMMER),
        place('nathans', 'Nathan\'s', 'restaurant', 'coney-island', 'Nathan Handwerker\'s stand at Surf and Stillwell '
              'selling frankfurters for a nickel since 1916, half the price of his old employer Feltman\'s.',
              ['hot-dogs', 'nickel', 'cheap'], '$', 'outdoor', ALL, ['afternoon', 'evening', 'late'],
              cuisine='Hot dogs'),
        place('feltmans', 'Feltman\'s', 'restaurant', 'coney-island', 'Charles Feltman\'s huge restaurant and garden '
              'on Surf Avenue, with shore dinners, a carousel and orchestras.', ['shore-dinner', 'garden',
              'historic'], '$$', 'mixed', ALL, ['afternoon', 'evening'], WARM, cuisine='Seafood'),
        place('boardwalk', 'The Riegelmann Boardwalk', 'landmark', 'coney-island', 'The new boardwalk, opened in 1923, '
              'running along the beach from Coney Island toward Brighton, crowded on summer evenings.',
              ['boardwalk', 'walk', 'sea'], 'free', 'outdoor', ALL, ALLDAY),
        place('coney-island-beach', 'Coney Island beach', 'beach', 'coney-island', 'The packed sands where a million '
              'people come on a hot Sunday, in wool bathing suits, with lifeguards and lost-children stations.',
              ['beach', 'swimming', 'crowds'], 'free', 'outdoor', ALL, DAY, SUMMER),
        # The Bronx
        place('yankee-stadium', 'Yankee Stadium', 'stadium', 'bronx', 'The House That Ruth Built, opened in 1923 at '
              '161st Street, with Babe Ruth in right field and a young Lou Gehrig taking over first base in 1925.',
              ['baseball', 'yankees', 'babe-ruth'], '$', 'outdoor', ALL, ['afternoon'], BALLGAME),
        place('bronx-zoo', 'Bronx Zoo', 'attraction', 'bronx', 'The New York Zoological Park in Bronx Park, with '
              'buffalo, elephants, a lion house and the bird house.', ['animals', 'family'], '$', 'outdoor', ALL,
              DAY, WARM),
        place('botanical-garden', 'New York Botanical Garden', 'garden', 'bronx', 'Hemlock forest, gorges and the '
              'great glass conservatory beside the Bronx River.', ['gardens', 'conservatory', 'forest'], 'free',
              'mixed', ALL, DAY),
        place('poe-cottage', 'Poe Cottage', 'museum', 'bronx', 'The little farmhouse at Fordham where Edgar Allan Poe '
              'lived in the 1840s, kept as a museum in a park on the Grand Concourse.', ['poe', 'history'], 'free',
              'indoor', ['solo', 'date'], DAY),
        place('arthur-avenue', 'Arthur Avenue', 'market', 'bronx', 'Italian Belmont\'s market street of pushcarts, '
              'bakeries, pork stores and cheese shops near Fordham.', ['italian', 'pushcarts', 'groceries'], '$',
              'outdoor', ALL, DAY),
        place('marios', 'Mario\'s', 'restaurant', 'bronx', 'A family restaurant on Arthur Avenue, opened in 1919, '
              'serving Neapolitan cooking.', ['italian', 'family'], '$$', 'indoor', ALL, ['afternoon', 'evening'],
              cuisine='Italian'),
        place('concourse-plaza-hotel', 'Concourse Plaza Hotel', 'restaurant', 'bronx', 'The new hotel on the '
              'Concourse at 161st Street, opened in 1923, with a dining room and ballroom for Bronx weddings and '
              'ballplayers.', ['hotel', 'ballroom', 'weddings'], '$$', 'indoor', ['friends', 'date', 'family'],
              ['afternoon', 'evening'], cuisine='American'),
        # Astoria and Long Island City
        place('astoria-studio', 'Famous Players-Lasky studio', 'landmark', 'astoria', 'Paramount\'s big movie '
              'studio in Astoria, opened in 1920, where stars like Gloria Swanson make pictures near Broadway\'s '
              'stage actors; fans wait at the gate.', ['movies', 'studio', 'stars'], 'free', 'outdoor', ['solo',
              'friends'], DAY),
        place('astoria-park', 'Astoria Park', 'park', 'astoria', 'A riverside park under the arch of the Hell Gate '
              'railroad bridge, with views of the East River and Randall\'s Island.', ['river-views', 'bridge'],
              'free', 'outdoor', ALL, DAY),
        place('bohemian-hall', 'Bohemian Hall', 'bar', 'astoria', 'The Czech and Slovak hall and garden on 24th '
              'Avenue, serving near beer, sausages and dumplings under the trees, and something stronger to '
              'members.', ['beer-garden', 'czech', 'outdoor'], '$', 'mixed', ['friends', 'family', 'date'],
              ['afternoon', 'evening'], WARM, cuisine='Czech'),
        place('ditmars-bakery', 'Astoria Italian bakery', 'cafe', 'astoria', 'An Italian bakery and café with bread, '
              'biscotti and espresso for workers on their way to the factories.', ['bakery', 'italian',
              'coffee'], '$', 'indoor', ALL, DAY, cuisine='Italian'),
        place('steinway-street-deli', 'Steinway Street German delicatessen', 'restaurant', 'astoria', 'A German '
              'delicatessen and lunchroom with liverwurst sandwiches, potato salad and hot dishes.', ['german',
              'deli', 'lunch'], '$', 'indoor', ALL, DAY, cuisine='German'),
        # Hoboken
        place('lackawanna-terminal', 'Lackawanna Terminal', 'landmark', 'hoboken', 'The copper-clad railroad and '
              'ferry terminal on the river, where commuters switch from trains to boats for Manhattan.',
              ['railroad', 'ferry', 'architecture'], 'free', 'indoor', ALL, ALLDAY),
        place('hoboken-piers', 'Hoboken piers', 'docks', 'hoboken', 'Transatlantic piers along River Street where '
              'the Holland America liners dock and longshoremen shape up each morning.', ['liners', 'waterfront',
              'work'], 'free', 'outdoor', ['solo'], DAY),
        place('clam-broth-house', 'Clam Broth House', 'restaurant', 'hoboken', 'The waterfront clam house near the '
              'ferry with free clam broth, steamers and a long bar, long a men\'s haunt but serving everyone in '
              'its dining room.', ['clams', 'seafood', 'waterfront'], '$', 'indoor', ALL, ['afternoon', 'evening'],
              cuisine='Seafood'),
        place('washington-street-hoboken', 'Washington Street', 'shopping', 'hoboken', 'Hoboken\'s main street of '
              'bakeries, shoe stores and dry goods, a short walk from the ferry.', ['shops', 'main-street'], '$',
              'outdoor', ALL, DAY),
        place('elysian-park', 'Elysian Park', 'park', 'hoboken', 'A small park on the cliff above the river with a '
              'view straight across to Manhattan, near where baseball was played in its early days.',
              ['river-views', 'baseball-history'], 'free', 'outdoor', ALL, DAY),
        place('river-street-saloon', 'River Street saloon', 'bar', 'hoboken', 'One of the riverfront saloons that '
              'carry on openly enough to make Hoboken famous among thirsty New Yorkers who come over on the '
              'ferry.', ['speakeasy', 'waterfront', 'beer'], '$', 'indoor', ADULT, NIGHT),
    ],
    'colleges': [
        college('columbia', 'Columbia University', 'research-university', 'upper-west-side', 'large',
                ['journalism', 'law', 'medicine', 'engineering', 'core-curriculum']),
        college('barnard', 'Barnard College', 'liberal-arts-college', 'upper-west-side', 'small',
                ['women-students', 'liberal-arts', 'anthropology']),
        college('institute-of-musical-art', 'Institute of Musical Art', 'music-school', 'upper-west-side', 'small',
                ['piano', 'violin', 'composition', 'conservatory']),
        college('nyu', 'New York University', 'private-university', 'greenwich-village', 'large',
                ['commerce', 'law', 'evening-classes', 'washington-square']),
        college('city-college', 'City College of New York', 'public-university', 'sugar-hill', 'large',
                ['free-tuition', 'engineering', 'debate', 'immigrant-sons']),
        college('hunter', 'Hunter College', 'public-university', 'yorkville', 'medium',
                ['women-students', 'free-tuition', 'teacher-training']),
        college('fordham', 'Fordham University', 'private-university', 'bronx', 'medium',
                ['jesuit', 'law', 'football']),
        college('cooper-union', 'Cooper Union', 'technical-institute', 'union-square', 'small',
                ['free-tuition', 'engineering', 'art', 'night-school']),
        college('pratt', 'Pratt Institute', 'art-school', 'brooklyn-heights', 'medium',
                ['art', 'design', 'architecture', 'library-school']),
        college('stevens', 'Stevens Institute of Technology', 'technical-institute', 'hoboken', 'small',
                ['engineering', 'castle-point']),
        college('art-students-league', 'Art Students League', 'art-school', 'times-square', 'small',
                ['drawing', 'painting', 'life-classes']),
        college('jewish-theological-seminary', 'Jewish Theological Seminary', 'seminary', 'upper-west-side', 'small',
                ['rabbis', 'hebrew', 'teachers-institute']),
    ],
    'careers': [
        career('numbers-runner', 'Numbers runner', 'underworld', 'flexible', '$', 'Taking pennies, nickels and '
               'dimes on the day\'s three-digit number from tenement to barbershop and carrying the slips to the '
               'bank before the number comes out.', ['the slips', 'the banker', 'the daily number', 'the cops',
               'lucky dreams']),
        career('song-plugger', 'Song plugger', 'entertainment', 'flexible', '$', 'Playing and singing a music '
               'publisher\'s new songs for bandleaders, vaudevillians and dime-store customers to get them '
               'heard.', ['sheet music', 'the piano', 'bandleaders', 'a hit']),
        career('skyscraper-riveter', 'Skyscraper riveter', 'construction', 'early', '$$', 'Working in a four-person '
               'riveting gang on the steel of the new towers: heating, tossing, catching and driving red-hot '
               'rivets hundreds of feet up.', ['the gang', 'heights', 'the whistle', 'danger', 'a new tower']),
        career('bootblack', 'Shoeshine', 'services', 'early', '$', 'Shining shoes at a stand in a station, a hotel '
               'lobby or on a street corner, a nickel or a dime a shine and tips.', ['regulars', 'tips',
               'the stand', 'overheard talk']),
        career('cigarette-seller', 'Cigarette seller', 'hospitality', 'evening', '$', 'Walking a nightclub with a '
               'tray of cigarettes, cigars and candy on a strap, selling to the tables and living on tips.',
               ['the tray', 'tips', 'the club', 'late nights']),
        career('pushcart-peddler', 'Pushcart peddler', 'retail', 'early', '$', 'Renting a pushcart and a licence to '
               'sell fruit, fish, notions or clothing on a market street, haggling from dawn till dark.',
               ['the cart', 'regulars', 'haggling', 'the license inspector', 'weather']),
        career('taxi-dancer', 'Taxi dancer', 'entertainment', 'evening', '$', 'Dancing with paying customers at ten '
               'cents a dance in a ballroom, earning a share of every ticket.', ['tickets', 'the band', 'sore feet',
               'regulars']),
        career('subway-guard', 'Subway guard', 'transit', 'rotating', '$', 'Riding the subway or El between cars, '
               'opening and closing the gates and calling the stations.', ['the crowds', 'the stations',
               'rush hour', 'the motorman']),
        career('elevator-operator', 'Elevator operator', 'services', 'shift-day', '$', 'Running an elevator in an '
               'office tower, hotel or department store in a uniform and white gloves, calling the floors.',
               ['the car', 'regulars', 'the lobby', 'the starter']),
    ],
    'employers': [
        employer('stock-exchange-employer', 'New York Stock Exchange', 'finance', 'financial-district', 'large',
                 'The exchange on Broad Street and the brokerage houses around it, busy with a rising market.',
                 ['stockbroker', 'office-clerk', 'stenographer']),
        employer('jp-morgan', 'J. P. Morgan and Company', 'finance', 'financial-district', 'medium', 'The private '
                 'bank at 23 Wall Street, the most powerful in the country.', ['bank-teller', 'office-clerk',
                 'stenographer', 'accountant']),
        employer('new-york-telephone', 'New York Telephone Company', 'communications', 'financial-district',
                 'large', 'The telephone company, with exchanges all over the city full of operators at '
                 'switchboards.', ['switchboard-operator', 'office-clerk']),
        employer('new-york-world', 'The New York World', 'media', 'city-hall', 'large', 'Pulitzer\'s crusading '
                 'paper under the gold dome on Park Row.', ['journalist', 'linotype-operator', 'newsboy']),
        employer('the-new-yorker', 'The New Yorker', 'media', 'midtown', 'small', 'Harold Ross\'s new weekly '
                 'magazine on West 45th Street, first published in February 1925.', ['journalist',
                 'stenographer']),
        employer('jewish-daily-forward', 'The Jewish Daily Forward', 'media', 'lower-east-side', 'medium', 'The '
                 'Yiddish daily in its tall building on East Broadway, read by hundreds of thousands.',
                 ['journalist', 'linotype-operator', 'newsboy']),
        employer('macys-employer', 'R. H. Macy and Company', 'retail', 'herald-square', 'large', 'The world\'s '
                 'largest store at Herald Square.', ['department-store-clerk', 'office-clerk',
                 'elevator-operator']),
        employer('ziegfeld-follies', 'Ziegfeld Follies, New Amsterdam Theatre', 'entertainment', 'times-square',
                 'medium', 'Florenz Ziegfeld\'s revue on 42nd Street.', ['chorus-dancer', 'performer', 'musician',
                 'hatcheck-attendant']),
        employer('cotton-club-employer', 'The Cotton Club', 'entertainment', 'harlem', 'medium', 'The Harlem '
                 'nightclub at Lenox Avenue and 142nd Street, run by Owney Madden\'s people.', ['jazz-musician',
                 'chorus-dancer', 'cigarette-seller', 'hatcheck-attendant', 'speakeasy-bartender']),
        employer('roseland', 'Roseland Ballroom', 'entertainment', 'times-square', 'medium', 'The Broadway dance '
                 'palace with ten-cents-a-dance hostesses and big bands.', ['taxi-dancer', 'jazz-musician',
                 'hatcheck-attendant']),
        employer('shapiro-bernstein', 'Shapiro, Bernstein and Company', 'entertainment', 'herald-square', 'small',
                 'A Tin Pan Alley music publisher whose pluggers push its songs all over town.', ['song-plugger',
                 'stenographer']),
        employer('pennsylvania-station-employer', 'Pennsylvania Railroad at Pennsylvania Station', 'railroad',
                 'herald-square', 'large', 'The railroad and its Pullman sleeping cars, with porters, red caps, '
                 'clerks and a shoeshine stand in the station.', ['pullman-porter', 'bootblack', 'office-clerk',
                 'telegraph-operator']),
        employer('interborough', 'Interborough Rapid Transit Company', 'transit', 'city-hall', 'large', 'The '
                 'company running the IRT subway and the Manhattan Els, with its great powerhouse on the West '
                 'Side.', ['subway-guard', 'streetcar-motorman', 'construction-trades']),
        employer('police-department', 'New York Police Department', 'law', 'little-italy', 'large', 'The police, '
                 'from headquarters on Centre Street to the precinct houses.', ['police-patrolman',
                 'office-clerk']),
        employer('bellevue', 'Bellevue Hospital', 'healthcare', 'union-square', 'large', 'The great city hospital on '
                 'First Avenue, taking anyone who comes through the door.', ['trained-nurse', 'physician']),
        employer('harlem-hospital', 'Harlem Hospital', 'healthcare', 'harlem', 'medium', 'The city hospital on '
                 'Lenox Avenue, where Black doctors and nurses have only lately won places on the staff.',
                 ['trained-nurse', 'physician']),
        employer('brooklyn-navy-yard-employer', 'Brooklyn Navy Yard', 'defense', 'brooklyn-heights', 'large',
                 'The Navy\'s shipyard, building and refitting warships.', ['military-sailor', 'factory-hand',
                 'construction-trades']),
        employer('american-sugar', 'American Sugar Refining Company', 'manufacturing', 'williamsburg', 'large',
                 'The big Williamsburg refinery on the East River, makers of Domino sugar.', ['factory-hand']),
        employer('famous-players-lasky', 'Famous Players-Lasky Corporation, Astoria', 'entertainment', 'astoria',
                 'medium', 'Paramount\'s movie studio in Astoria.', ['actor', 'performer', 'construction-trades']),
        employer('cunard-line', 'Cunard Line, Chelsea Piers', 'logistics', 'chelsea', 'medium', 'The British line '
                 'whose liners dock at the Chelsea piers, hiring longshoremen by the shape-up.', ['longshoreman',
                 'office-clerk']),
    ],
    'career_hubs': [
        hub('wall-street', 'Wall Street and Park Row', ['financial-district', 'city-hall'],
            ['finance', 'business', 'communications', 'media', 'legal', 'law', 'transit'],
            'Banks, brokers, insurance, the telephone and telegraph companies, newspapers and City Hall.'),
        hub('broadway-and-midtown', 'Broadway and Midtown', ['times-square', 'midtown', 'herald-square'],
            ['entertainment', 'hospitality', 'retail', 'media', 'services', 'construction', 'railroad',
             'education', 'real-estate'],
            'Theaters, hotels, restaurants, department stores, the two great stations, publishers, and the '
            'building sites of the new towers.'),
        hub('harlem-hub', 'Harlem', ['harlem', 'sugar-hill'],
            ['entertainment', 'hospitality', 'underworld', 'healthcare', 'religion', 'social-services', 'retail'],
            'Cabarets, churches, hospitals, shops and the numbers banks of Black New York.'),
        hub('garment-trades', 'The garment trades', ['herald-square', 'lower-east-side'],
            ['manufacturing', 'retail', 'food', 'social-services'],
            'Cloak, suit and dress shops on Seventh Avenue and the workshops, pushcarts and settlement houses of '
            'the Lower East Side.'),
        hub('waterfront', 'The waterfront and the works', ['chelsea', 'hells-kitchen', 'brooklyn-heights',
            'williamsburg', 'hoboken', 'astoria'],
            ['logistics', 'manufacturing', 'construction', 'defense', 'railroad', 'trades', 'fishing'],
            'Piers, freight yards, refineries, bakeries, piano works and the Navy Yard on both rivers.'),
    ],
    'climate': {
        'summary': 'Four sharp seasons: cold, gray winters with snow and slush, humid summers so hot that people '
                   'sleep on fire escapes, roofs and the beach, and fine clear springs and autumns.',
        'months': [
            month(37, 24, 11, 'Cold; snow piles up in the gutters and coal stoves burn all day.'),
            month(39, 25, 10, 'Raw and slushy; skating in Central Park when the ponds freeze.'),
            month(47, 32, 11, 'Windy; St. Patrick\'s Day parade on Fifth Avenue.'),
            month(59, 42, 11, 'Showers; the baseball season opens and Easter bonnets parade.'),
            month(70, 52, 11, 'Mild and green; straw boaters come out on the fifteenth.'),
            month(79, 61, 10, 'Warm; Coney Island opens for the season.'),
            month(84, 67, 10, 'Hot and sticky; tenement families sleep on roofs and fire escapes.'),
            month(82, 66, 10, 'Heat waves and thunderstorms; the beaches are packed.'),
            month(75, 59, 8, 'Warm and clear; felt hats replace straw on the fifteenth.'),
            month(64, 48, 8, 'Crisp and bright, the best month in the city.'),
            month(52, 38, 9, 'Gray and chilly; football and the Thanksgiving parade.'),
            month(41, 28, 10, 'Cold; store windows dressed for Christmas and the first snow.'),
        ],
        'source': S,
    },
    'annual_events': [
        event('new-years-eve-times-square', 'New Year\'s Eve in Times Square', [12], 'times-square', 'Crowds pack '
              'Times Square to watch the lighted ball drop down the flagpole of the Times Tower at midnight, and '
              'the speakeasies and hotels are booked solid.'),
        event('st-patricks-day-parade', 'St. Patrick\'s Day Parade', [3], 'midtown', 'Irish New York marches up '
              'Fifth Avenue past St. Patrick\'s Cathedral with bands, county societies and the Fighting 69th.'),
        event('easter-parade', 'Easter Parade on Fifth Avenue', [3, 4], 'midtown', 'After Easter services New '
              'Yorkers stroll up Fifth Avenue in new hats and spring clothes to see and be seen.'),
        event('baseball-season', 'Baseball season', [4, 5, 6, 7, 8, 9], None, 'The Giants at the Polo Grounds, the '
              'Yankees at their new stadium in the Bronx and the Robins at Ebbets Field, with the scores chalked up '
              'in barbershops all over town.'),
        event('world-series-bulletins', 'World Series bulletin boards', [10], 'times-square', 'Crowds fill Times '
              'Square and Park Row to follow the World Series play by play on giant electric scoreboards outside '
              'the newspapers.'),
        event('fourth-of-july', 'Fourth of July', [7], 'coney-island', 'Firecrackers in every street, fireworks '
              'over the harbor and a record crowd at Coney Island.'),
        event('coney-island-mardi-gras', 'Coney Island Mardi Gras', [9], 'coney-island', 'A week of parades, '
              'floats, costumes and confetti on Surf Avenue to close the summer season.'),
        event('high-holy-days', 'The High Holy Days', [9, 10], 'lower-east-side', 'Rosh Hashanah and Yom Kippur '
              'close the shops of the Lower East Side, fill the synagogues and send families to the river for '
              'tashlikh.'),
        event('armistice-day', 'Armistice Day', [11], 'midtown', 'Veterans parade on Fifth Avenue and the city falls '
              'silent at eleven o\'clock on the eleventh.'),
        event('macys-thanksgiving-parade', 'Macy\'s Thanksgiving Parade', [11], 'herald-square', 'Macy\'s parade, '
              'first held in 1924, with employees in costume, floats, bands and animals borrowed from the Central '
              'Park Menagerie, ending at the store\'s Christmas windows.'),
        event('six-day-bicycle-race', 'Six-day bicycle race', [12], 'hells-kitchen', 'Riders circle the board '
              'track at Madison Square Garden day and night for six days, and society comes late to watch the '
              'sprints.'),
        event('chinese-new-year', 'Chinese New Year', [1, 2], 'chinatown', 'Firecrackers, lion dances and banquets '
              'on Mott and Pell Streets to welcome the new year.'),
    ],
    'local_color': [
        color('bees-knees', 'The bee\'s knees', 'saying', 'Anything excellent is "the bee\'s knees" or "the cat\'s '
              'pajamas", a good time is "the berries" and a fine fellow is "the real McCoy".'),
        color('speakeasy-slang', 'Hooch, giggle water and the blind pig', 'saying', 'Liquor is "hooch", "giggle '
              'water" or "bathtub gin"; a speakeasy is a "speak" or a "blind pig", and a raid means the place has '
              'been "padlocked".'),
        color('big-apple', 'The big apple', 'saying', 'Horse-racing people, following the Morning Telegraph\'s turf '
              'writer, call the big New York races "the big apple", the prize every stable is after.'),
        color('applesauce', 'Applesauce and banana oil', 'saying', 'Nonsense is "applesauce" or "banana '
              'oil", money is "dough" or "kale", and a person who can\'t keep a secret "spills the beans".'),
        color('speakeasy-password', 'The password at the door', 'custom', 'You knock, a slot opens in the door and '
              'you say who sent you or the password of the week; the doorman decides.',
              ['chumleys', 'tony-somas', 'tenth-avenue-speakeasy', 'jack-and-charlies']),
        color('rent-party', 'Rent parties', 'custom', 'Harlem tenants throw Saturday-night parties with a piano '
              'player, fried chicken and a jug, charging a quarter at the door to make the rent; cards in the '
              'elevators announce them.', ['harlem']),
        color('sunday-stroll', 'The Seventh Avenue stroll', 'custom', 'After church on Sunday Harlem promenades up '
              'Seventh Avenue in its best clothes, stopping to talk and show off.', ['harlem'],
              ['spring', 'summer', 'fall']),
        color('the-numbers', 'Playing the numbers', 'custom', 'Pennies on a three-digit number taken from the day\'s '
              'bank clearings, with dream books to turn a dream into a number; runners collect from barbershops '
              'and stoops.', ['harlem']),
        color('the-charleston', 'The Charleston', 'custom', 'The dance from the Broadway show Runnin\' Wild that '
              'everyone, flappers above all, is doing in 1925, kicking up their heels.',
              ['smalls-paradise', 'jungles-casino', 'roseland-ballroom']),
        color('automat-nickels', 'The automat', 'custom', 'Get a handful of nickels from the woman in the glass '
              'booth, then drop them in the slot beside the little window for a slice of pie or a plate of beans.',
              ['times-square-automat']),
        color('nathans-hot-dog', 'A Nathan\'s frankfurter', 'dish', 'A grilled frankfurter on a roll with mustard, '
              'a nickel at Nathan\'s, eaten on the street with a glass of root beer.', ['nathans']),
        color('pastrami-on-rye', 'Pastrami on rye', 'dish', 'Hand-sliced hot pastrami piled on rye bread with '
              'mustard and a pickle, from the delicatessens of the Lower East Side.',
              ['katzs', 'broadway-delicatessen', 'lindys']),
        color('egg-cream', 'Egg cream', 'drink', 'Chocolate syrup, milk and a shot of seltzer whipped to a foam in '
              'a glass, with no egg and no cream, from any candy store fountain.',
              ['convent-avenue-soda-fountain', 'flatbush-ice-cream-parlor']),
        color('cheesecake', 'Cheesecake', 'dish', 'Rich cream-cheese cheesecake, which Broadway eats after the show '
              'and argues about.', ['lindys']),
        color('bathtub-gin', 'Bathtub gin and needle beer', 'drink', 'Alcohol cut with water and juniper oil in a '
              'tub, and near beer "needled" with alcohol, are what most speakeasies pour; good Scotch comes from '
              'rum row off the coast and costs plenty.', ['tenth-avenue-speakeasy', 'west-61st-street-speakeasy']),
        color('knishes', 'Knishes', 'dish', 'Potato or kasha baked in a thin crust, hot from the pushcart or the '
              'bakery for a few cents.', ['yonah-schimmel']),
        color('chop-suey', 'Chop suey', 'dish', 'Chop suey and chow mein at Chinatown and uptown chop suey houses, '
              'the city\'s cheap late-night meal.', ['mott-street-chop-suey']),
        color('giants', 'The Giants', 'team', 'John McGraw\'s New York Giants of the National League at the Polo '
              'Grounds, National League champions four years running from 1921 to 1924.', ['polo-grounds'], BALLGAME),
        color('yankees', 'The Yankees', 'team', 'The Yankees of Babe Ruth at their new stadium in the Bronx; in 1925 '
              'the Babe is sick for much of the season and a young Lou Gehrig takes first base.',
              ['yankee-stadium'], BALLGAME),
        color('robins', 'The Brooklyn Robins', 'team', 'Brooklyn\'s National League club, called the Robins after '
              'manager Wilbert Robinson, or the Dodgers after the trolley dodgers who follow them.',
              ['ebbets-field'], BALLGAME),
        color('pushcarts', 'Pushcart markets', 'shop', 'Pushcarts line Orchard, Hester, Mulberry and Bleecker '
              'Streets, Arthur Avenue and the Ninth Avenue market, selling anything at prices that start a haggle.',
              ['orchard-street-market', 'mulberry-street', 'paddys-market', 'arthur-avenue']),
        color('fire-escape-summer', 'Sleeping on the fire escape', 'custom', 'In a heat wave tenement families carry '
              'mattresses onto roofs and fire escapes and children sleep in the parks.', [], SUMMER),
        color('straw-hat-day', 'Straw Hat Day', 'custom', 'Men switch to straw boaters on May 15 and back to felt on '
              'September 15; a straw hat worn after that is fair game to be knocked off and smashed in the street.',
              [], ['spring', 'summer', 'fall']),
    ],
    'prices': [
        price('wage', "Laborer's wage", 4, 6, 'a day; garment pieceworkers and clerks around $25 a week'),
        price('subway', 'Subway or El fare', 0.05, 0.05, 'one ride, any distance'),
        price('streetcar', 'Streetcar fare', 0.05, 0.05, 'one ride'),
        price('coffee', 'Cup of coffee', 0.05, 0.1, 'at a lunch counter or automat'),
        price('hot-dog', 'Hot dog at Nathan\'s', 0.05, 0.05, 'one frankfurter'),
        price('cheap-lunch', 'Lunch at an automat or lunch counter', 0.25, 0.5),
        price('dinner', 'Restaurant dinner', 0.75, 2.5, 'a good meal downtown'),
        price('cocktail', 'Speakeasy drink', 0.5, 1.5, 'a highball or cocktail; more in fancy clubs'),
        price('beer', 'Speakeasy beer', 0.25, 0.5, 'a glass of needle beer'),
        price('movie', 'Movie palace ticket', 0.25, 0.75, 'matinee to evening'),
        price('show', 'Broadway theater seat', 1, 5.5, 'balcony to orchestra; the Follies more'),
        price('ballgame', 'Ballgame ticket', 0.5, 2.2, 'bleachers to box seat'),
        price('newspaper', 'Daily paper', 0.02, 0.03),
        price('taxi', 'Taxicab ride', 0.5, 1.5, 'a ride across Midtown, plus tip'),
        price('cigarettes', 'Pack of cigarettes', 0.15, 0.2, 'twenty'),
        price('furnished-room', 'Furnished room', 4, 8, 'a week'),
        price('groceries', 'Week\'s groceries for a family', 8, 12, 'a week'),
    ],
    'water': [
        {'kind': 'sea', 'name': 'Lower New York Bay', 'side': 'south', 'width_km': 4},
        {'kind': 'river', 'name': 'Hudson River', 'width_km': 1.2, 'points': [
            [40.690, -74.025], [40.710, -74.020], [40.730, -74.013], [40.760, -74.004], [40.790, -73.985],
            [40.830, -73.955], [40.865, -73.933]]},
        {'kind': 'river', 'name': 'East River', 'width_km': 0.6, 'points': [
            [40.698, -74.008], [40.704, -73.990], [40.710, -73.973], [40.735, -73.970], [40.760, -73.955],
            [40.784, -73.938], [40.800, -73.927]]},
        {'kind': 'river', 'name': 'Harlem River', 'width_km': 0.2, 'points': [
            [40.800, -73.927], [40.820, -73.933], [40.845, -73.930], [40.872, -73.912]]},
    ],
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
