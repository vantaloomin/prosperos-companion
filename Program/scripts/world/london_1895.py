"""Curated data for London in 1895, the London of Conan Doyle's Sherlock Holmes stories.

Run `python scripts/world/london_1895.py` to rewrite the shipped JSON.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'cities' / 'london-1895.json'
S = 'curated-2026-10'
ERA = 'victorian'


def hood(id, name, summary, vibe, lat, lon, tier, rent, housing, walk, transit):
    one_room, two_rooms, three_rooms = rent
    return {'id': id, 'name': name, 'summary': summary, 'vibe': vibe, 'lat': lat, 'lon': lon, 'rent_tier': tier,
            'rent': {'studio': one_room, 'one_bedroom': two_rooms, 'two_bedroom': three_rooms}, 'housing': housing,
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
SOLO = ['solo']
DAY = ['morning', 'afternoon']
DINNER = ['evening']
NIGHT = ['evening', 'late']
ALLDAY = ['morning', 'afternoon', 'evening']
WARM = ['spring', 'summer', 'fall']

BUS, TRAM, CAB, STEAMER = 'horse-omnibus', 'horse-tram', 'hansom-cab', 'thames-steamer'
MET, DISTRICT, TUBE, NLR = 'metropolitan-railway', 'district-railway', 'city-and-south-london', 'north-london-railway'

CITY = {
    'schema_version': 1, 'id': 'london-1895', 'name': 'London, 1895', 'setting': 'fictional', 'era': ERA,
    'category': 'other-eras',
    'basis': 'Real late-Victorian London, as it stood in 1895, together with the places of Arthur Conan Doyle\'s '
             'Sherlock Holmes stories, all of which are in the public domain in the US. Nothing is taken from '
             'later films, television or pastiches.',
    'region': 'County of London', 'country': 'United Kingdom of Great Britain and Ireland',
    'timezone': 'Europe/London',
    'aliases': ['Victorian London', 'Holmes\'s London', 'London 1895', 'Sherlock Holmes\'s London'],
    'summary': 'The capital of the British Empire in 1895: gaslit streets, hansom cabs, horse omnibuses and '
               'steam trains under the ground, banks in the City, newspapers on Fleet Street, docks downriver, '
               'and Mr Sherlock Holmes in rooms at 221B Baker Street.',
    'lat': 51.512, 'lon': -0.123,
    'currency': {'code': 'shilling', 'symbol': 's.', 'name': 'shillings'},
    'rent_period': 'week',
    'speeds': {'walk': 4.5, 'bus': 7, 'tram': 9, 'carriage': 12, 'subway': 20, 'commuter-rail': 25, 'boat': 11},
    'sources': {
        S: {'kind': 'curated', 'title': 'London in 1895, written for Prospero Companion',
            'license': 'CC0-1.0', 'retrieved': '2026-10-05',
            'note': 'Late-Victorian London from general historical knowledge: neighbourhoods, institutions, '
                    'theatres, pubs and markets that existed in 1895, at approximate real coordinates. Holmes '
                    'locations (221B Baker Street, the Diogenes Club) come from Arthur Conan Doyle\'s stories, '
                    'public domain in the US. Rents are rounded weekly figures in shillings for a single room, '
                    'two rooms, and three rooms or a small flat, meant for fiction. Climate figures are rounded '
                    'London averages of the period; winter fogs were thicker then than now.'},
    },
    'neighborhoods': [
        hood('marylebone', 'Marylebone and Baker Street', 'Respectable terraces of lodging houses and doctors\' '
             'consulting rooms between Oxford Street and Regent\'s Park, with Baker Street station on the '
             'Metropolitan line.', ['respectable', 'lodgings', 'park'], 51.522, -0.157, 'high',
             ([8, 15], [15, 30], [25, 50]), ['lodging-house', 'terrace', 'mansion-flat'], 'high',
             [MET, BUS, CAB]),
        hood('mayfair', 'Mayfair', 'Town houses of the rich between Piccadilly and Oxford Street, full of servants '
             'during the Season, with tailors, galleries and Bond Street shops.', ['wealthy', 'fashionable',
             'shopping'], 51.510, -0.148, 'very-high', ([20, 40], [40, 80], [80, 160]),
             ['town-house', 'mews', 'servants-quarters'], 'high', [BUS, CAB]),
        hood('westminster', 'Westminster and St James\'s', 'Parliament, the Abbey, government offices on Whitehall, '
             'New Scotland Yard on the Embankment, and the gentlemen\'s clubs of Pall Mall.',
             ['government', 'clubs', 'historic'], 51.503, -0.130, 'high', ([12, 25], [25, 45], [40, 80]),
             ['chambers', 'terrace', 'mansion-flat'], 'high', [DISTRICT, BUS, CAB, STEAMER]),
        hood('strand-covent-garden', 'The Strand and Covent Garden', 'Theatres, restaurants and hotels along the '
             'Strand, and the fruit, flower and vegetable market at Covent Garden, busy from before dawn.',
             ['theatres', 'market', 'nightlife'], 51.511, -0.122, 'mid', ([7, 14], [12, 25], [20, 40]),
             ['rooms-over-shops', 'lodging-house', 'chambers'], 'high', [DISTRICT, BUS, CAB, STEAMER]),
        hood('fleet-street', 'Fleet Street and the Temple', 'Newspaper offices and printing works, chop houses and '
             'old taverns, with barristers\' chambers in the Inns of Court behind.', ['press', 'law', 'taverns'],
             51.514, -0.108, 'mid', ([7, 12], [12, 22], [18, 35]), ['chambers', 'rooms-over-shops'], 'high',
             [BUS, CAB, STEAMER]),
        hood('the-city', 'The City', 'The square mile of banks, insurance offices and merchant houses around the '
             'Bank of England, crowded with clerks by day and nearly empty at night.', ['finance', 'commerce',
             'historic'], 51.513, -0.089, 'high', ([8, 14], [14, 25], [20, 40]), ['caretaker-flat', 'chambers'],
             'high', [MET, DISTRICT, TUBE, BUS, CAB, STEAMER]),
        hood('whitechapel', 'Whitechapel and Spitalfields', 'Crowded East End streets of tailoring workshops, '
             'common lodging houses, street markets and new Jewish arrivals from Eastern Europe, with Toynbee '
             'Hall and the London Hospital.', ['working-class', 'crowded', 'markets'], 51.517, -0.065, 'low',
             ([2, 5], [5, 8], [7, 11]), ['tenement', 'common-lodging-house', 'model-dwelling'], 'high',
             [MET, BUS, TRAM]),
        hood('limehouse', 'Limehouse and the Docks', 'Riverside streets beside the West India Docks: warehouses, '
             'ships\' chandlers, sailors\' boarding houses and a small Chinese quarter.', ['docks', 'river',
             'working-class'], 51.511, -0.033, 'low', ([2, 4], [4, 7], [6, 10]), ['terrace', 'boarding-house'],
             'medium', [BUS, TRAM, STEAMER]),
        hood('bloomsbury', 'Bloomsbury', 'Garden squares of boarding houses near the British Museum and University '
             'College, home to students, writers, governesses between posts and clerks on small salaries.',
             ['academic', 'squares', 'boarding-houses'], 51.521, -0.127, 'mid', ([6, 14], [12, 25], [20, 40]),
             ['boarding-house', 'terrace', 'lodging-house'], 'high', [MET, BUS, CAB]),
        hood('southwark', 'Southwark and the Borough', 'South of London Bridge: Borough Market, Guy\'s Hospital, '
             'hop warehouses, breweries and the last galleried coaching inn.', ['working-class', 'markets',
             'river'], 51.504, -0.091, 'low', ([3, 6], [5, 9], [8, 13]), ['terrace', 'tenement', 'model-dwelling'],
             'high', [TUBE, BUS, TRAM]),
        hood('lambeth', 'Lambeth', 'Across Westminster Bridge: the Canterbury music hall, Doulton\'s pottery '
             'works, the New Cut street market and rows of small terraces.', ['working-class', 'music-halls',
             'industry'], 51.497, -0.115, 'low', ([3, 6], [6, 9], [8, 14]), ['terrace', 'tenement'], 'medium',
             [TUBE, BUS, TRAM, STEAMER]),
        hood('pimlico', 'Pimlico', 'Plain stucco terraces near Victoria station, cut up into lodgings for clerks, '
             'widows and shop assistants.', ['quiet', 'lodgings', 'respectable'], 51.489, -0.138, 'mid',
             ([6, 12], [10, 20], [16, 30]), ['lodging-house', 'terrace'], 'medium', [DISTRICT, BUS, CAB, STEAMER]),
        hood('chelsea', 'Chelsea', 'Riverside streets of painters\' studios and old houses along Cheyne Walk, with '
             'the Royal Hospital and Battersea Park across the water.', ['artists', 'river', 'quiet'], 51.487,
             -0.168, 'mid', ([6, 14], [12, 25], [20, 45]), ['studio', 'terrace', 'mansion-flat'], 'medium',
             [DISTRICT, BUS, STEAMER]),
        hood('kensington', 'Kensington and Knightsbridge', 'Large stucco houses, the museums of South Kensington, '
             'the Royal Albert Hall, Kensington Gardens and Harrods.', ['wealthy', 'museums', 'family'], 51.498,
             -0.180, 'high', ([10, 25], [20, 45], [35, 80]), ['town-house', 'mansion-flat', 'mews'], 'medium',
             [MET, DISTRICT, BUS, CAB]),
        hood('hampstead', 'Hampstead', 'A hill village of old houses and new villas on the northern edge, with the '
             'Heath, its ponds and its inns.', ['village', 'heath', 'quiet'], 51.556, -0.178, 'high',
             ([8, 18], [15, 30], [25, 55]), ['villa', 'cottage', 'terrace'], 'medium', [NLR, BUS]),
        hood('kew', 'Kew and Richmond', 'Riverside villages upstream, reached by train or steamer, with the Royal '
             'Botanic Gardens, Richmond Park and boating on the Thames.', ['suburban', 'river', 'gardens'], 51.478,
             -0.290, 'mid', ([5, 10], [9, 18], [14, 28]), ['villa', 'cottage'], 'low', [DISTRICT, NLR, STEAMER]),
    ],
    'transit': [
        line(BUS, 'Horse omnibuses', 'bus', 'Two-horse buses of the London General Omnibus Company and its rivals, '
             'with knifeboard seats on the roof; a penny or twopence a stage.'),
        line(TRAM, 'Horse tramways', 'tram', 'Horse-drawn trams on rails, mostly in South and East London, since '
             'they are kept out of the West End and the City.'),
        line(CAB, 'Hansom cabs and growlers', 'carriage', 'Two-wheeled hansoms for speed and four-wheeled growlers '
             'for luggage, hired from a rank or hailed in the street; a shilling for the first two miles.'),
        line(MET, 'Metropolitan Railway', 'subway', 'Steam trains under the New Road through Baker Street, King\'s '
             'Cross and on to the City, sooty but quick.'),
        line(DISTRICT, 'Metropolitan District Railway', 'subway', 'Steam underground line along the Embankment '
             'through Westminster, Charing Cross and South Kensington, out to Richmond.'),
        line(TUBE, 'City and South London Railway', 'subway', 'The first deep electric tube, opened in 1890 from '
             'King William Street in the City under the river to Stockwell, in small padded carriages.'),
        line(NLR, 'North London Railway', 'commuter-rail', 'Suburban steam trains looping round the north, with '
             'stations at Hampstead Heath and Kew Gardens.'),
        line(STEAMER, 'Thames steamboats', 'boat', 'Penny steamers calling at piers from Chelsea to London Bridge, '
             'with summer boats upriver to Kew and Richmond.'),
    ],
    'places': [
        # Marylebone
        place('221b-baker-street', '221B Baker Street', 'landmark', 'marylebone', 'The first-floor rooms Mr '
              'Sherlock Holmes shares with Dr Watson, kept by Mrs Hudson, with a bow window over Baker Street.',
              ['holmes', 'canon', 'street'], 'free', 'outdoor', ALL, ALLDAY),
        place('regents-park', 'Regent\'s Park', 'park', 'marylebone', 'Nash terraces round a wide park with a '
              'boating lake, the Inner Circle gardens and band music on summer evenings.', ['walk', 'boating',
              'lake'], 'free', 'outdoor', ALL, ALLDAY),
        place('london-zoo', 'Zoological Gardens', 'attraction', 'marylebone', 'The Zoological Society\'s gardens in '
              'Regent\'s Park, with the lion house, the reptile house and elephant rides for children.',
              ['animals', 'family', 'outing'], '$', 'outdoor', ALL, DAY, WARM),
        place('madame-tussauds', 'Madame Tussaud\'s', 'attraction', 'marylebone', 'The waxwork exhibition on '
              'Marylebone Road, with kings, queens, famous murderers in the Chamber of Horrors and a band in the '
              'Hall of Kings.', ['waxworks', 'rainy-day', 'popular'], '$', 'indoor', ALL, ALLDAY),
        place('queens-hall', 'Queen\'s Hall', 'venue', 'marylebone', 'New concert hall in Langham Place, opened '
              'in 1893, known for its good sound and cheap promenade tickets.', ['music', 'concerts'], '$$',
              'indoor', ADULT, DINNER),
        # Mayfair
        place('cafe-royal', 'Café Royal', 'restaurant', 'mayfair', 'French restaurant and domino room on Regent '
              'Street where artists, writers and young men about town meet over absinthe and dinner.',
              ['artists', 'french', 'late'], '$$$', 'indoor', ADULT, NIGHT, cuisine='French'),
        place('criterion', 'The Criterion', 'bar', 'mayfair', 'Long bar and restaurant at Piccadilly Circus, where '
              'Dr Watson ran into young Stamford before he met Holmes.', ['canon', 'piccadilly', 'drinks'], '$$',
              'indoor', ADULT, ['afternoon', 'evening']),
        place('liberty', 'Liberty and Co.', 'shopping', 'mayfair', 'Regent Street shop selling Eastern silks, '
              'printed fabrics and art furnishings to the artistic set.', ['fabrics', 'fashion', 'art'], '$$$',
              'indoor', ['solo', 'friends', 'date'], DAY),
        place('lyons-piccadilly', 'Lyons tea shop, Piccadilly', 'cafe', 'mayfair', 'The first Lyons tea shop, opened '
              'in 1894: tea, buns and a plate of ham at fixed low prices, with waitresses in uniform.',
              ['tea', 'cheap', 'new'], '$', 'indoor', ALL, ALLDAY, cuisine='Tea and light meals'),
        # Westminster and St James's
        place('diogenes-club', 'The Diogenes Club', 'landmark', 'westminster', 'The Pall Mall club of Mycroft '
              'Holmes, for the least sociable men in London; no member may speak to another except in the '
              'Strangers\' Room.', ['holmes', 'canon', 'club'], '$$$', 'indoor', SOLO, ['afternoon', 'evening']),
        place('st-james-park', 'St James\'s Park', 'park', 'westminster', 'Lake with pelicans and ducks between '
              'Buckingham Palace and the Horse Guards, a lunchtime walk for government clerks.', ['lake', 'walk',
              'ducks'], 'free', 'outdoor', ALL, ALLDAY),
        place('westminster-abbey', 'Westminster Abbey', 'temple', 'westminster', 'The coronation church, with Poets\' '
              'Corner and choral evensong every afternoon.', ['church', 'history', 'music'], 'free', 'indoor',
              ALL, DAY),
        place('london-library', 'The London Library', 'library', 'westminster', 'Subscription lending library in '
              'St James\'s Square, where members take books home and read in a quiet upstairs room.',
              ['books', 'quiet', 'subscription'], '$$', 'indoor', SOLO, DAY),
        # Strand and Covent Garden
        place('covent-garden-market', 'Covent Garden Market', 'market', 'strand-covent-garden', 'The great fruit, '
              'flower and vegetable market, loud with porters and costers before dawn and quieter by noon.',
              ['flowers', 'produce', 'early'], '$', 'mixed', ALL, ['morning']),
        place('simpsons', 'Simpson\'s-in-the-Strand', 'restaurant', 'strand-covent-garden', 'Old Strand dining '
              'room where joints of beef and mutton are wheeled to the table on silver trolleys and carved there.',
              ['roast-beef', 'canon', 'traditional'], '$$$', 'indoor', ADULT, ['afternoon', 'evening'],
              cuisine='English roasts'),
        place('lamb-and-flag', 'The Lamb and Flag', 'tavern', 'strand-covent-garden', 'Small, old timber-framed '
              'pub up an alley off Rose Street, full of market men and actors.', ['pub', 'old', 'beer'], '$',
              'indoor', ADULT, NIGHT),
        place('savoy-theatre', 'Savoy Theatre', 'venue', 'strand-covent-garden', 'The electrically lit theatre built '
              'for Gilbert and Sullivan\'s comic operas.', ['theatre', 'comic-opera'], '$$', 'indoor', ALL,
              DINNER),
        place('lyceum', 'Lyceum Theatre', 'venue', 'strand-covent-garden', 'Henry Irving and Ellen Terry\'s theatre '
              'off the Strand, where Holmes and Watson met Mary Morstan by the third pillar.', ['theatre',
              'canon', 'drama'], '$$', 'indoor', ADULT, DINNER),
        place('drury-lane', 'Theatre Royal, Drury Lane', 'venue', 'strand-covent-garden', 'Huge old theatre known '
              'for spectacular melodramas in autumn and the Christmas pantomime.', ['theatre', 'pantomime'], '$$',
              'indoor', ALL, DINNER),
        place('gattis', 'Gatti\'s', 'cafe', 'strand-covent-garden', 'Swiss café and restaurant in the Strand known '
              'for ices, coffee and cheap suppers before or after the theatre.', ['ices', 'coffee', 'theatre'],
              '$', 'indoor', ALL, ALLDAY, cuisine='Swiss and Italian'),
        place('turkish-baths', 'Nevill\'s Turkish Baths, Northumberland Avenue', 'fitness', 'strand-covent-garden',
              'Tiled hot rooms, a plunge pool and couches for resting, where Holmes and Watson took a bath in "The '
              'Illustrious Client".', ['baths', 'canon', 'steam'], '$$', 'indoor', SOLO, ALLDAY),
        place('charing-cross-bookshops', 'Charing Cross Road bookshops', 'shopping', 'strand-covent-garden',
              'Secondhand booksellers with sixpenny boxes outside on the new Charing Cross Road.', ['books',
              'browsing'], '$', 'mixed', ['solo', 'friends', 'date'], DAY),
        # Fleet Street and the Temple
        place('cheshire-cheese', 'Ye Olde Cheshire Cheese', 'tavern', 'fleet-street', 'Dark chop house, rebuilt after '
              'the Great Fire, off Fleet Street, with sawdust floors, a famous beefsteak pudding and '
              'newspapermen at every table.',
              ['pub', 'pudding', 'press'], '$', 'indoor', ADULT, ['afternoon', 'evening'], cuisine='English'),
        place('st-pauls', 'St Paul\'s Cathedral', 'temple', 'fleet-street', 'Wren\'s cathedral at the top of Ludgate '
              'Hill, with the Whispering Gallery and a view from the Golden Gallery for the energetic.',
              ['church', 'views', 'history'], 'free', 'indoor', ALL, DAY),
        # The City
        place('leadenhall-market', 'Leadenhall Market', 'market', 'the-city', 'Iron-and-glass market hall, newly '
              'rebuilt, selling poultry, game and cheese to City clerks and their households.', ['poultry',
              'covered'], '$$', 'indoor', ALL, DAY),
        place('billingsgate', 'Billingsgate Market', 'market', 'the-city', 'The fish market on the river below '
              'London Bridge, where porters carry boxes of fish on leather hats from five in the morning.',
              ['fish', 'early', 'river'], '$', 'mixed', SOLO, ['morning']),
        place('smithfield', 'Smithfield Market', 'market', 'the-city', 'The London Central Meat Market by St '
              'Bartholomew\'s Hospital, with pubs that open at dawn for the market men.', ['meat', 'early'], '$',
              'indoor', SOLO, ['morning']),
        place('abc-cheapside', 'ABC tea shop, Cheapside', 'cafe', 'the-city', 'An Aerated Bread Company tea room '
              'where clerks and typists, women among them, take a cheap lunch of tea and a bun.', ['tea', 'cheap',
              'lunch'], '$', 'indoor', ['solo', 'friends', 'coworkers'], DAY, cuisine='Tea and light meals'),
        # Bloomsbury
        place('british-museum', 'British Museum', 'museum', 'bloomsbury', 'The national collections on Great Russell '
              'Street: the Elgin Marbles, Egyptian mummies and the Assyrian reliefs, free to all.', ['antiquities',
              'free', 'rainy-day'], 'free', 'indoor', ALL, DAY),
        place('reading-room', 'British Museum Reading Room', 'library', 'bloomsbury', 'The great domed reading room, '
              'open to anyone with a reader\'s ticket, where Holmes once lodged near by in Montague Street.',
              ['books', 'study', 'canon'], 'free', 'indoor', SOLO, DAY),
        # Whitechapel and the East End
        place('petticoat-lane', 'Petticoat Lane market', 'market', 'whitechapel', 'The Sunday morning clothes and '
              'oddments market on Middlesex Street, crowded with buyers and loud with patter.', ['secondhand',
              'clothes', 'sunday'], '$', 'outdoor', ['solo', 'friends', 'family'], ['morning']),
        place('peoples-palace', 'The People\'s Palace', 'venue', 'whitechapel', 'Hall, library, gymnasium and '
              'technical school on the Mile End Road for East Enders, with cheap concerts and lectures.',
              ['concerts', 'lectures', 'cheap'], '$', 'indoor', ALL, ['afternoon', 'evening']),
        place('toynbee-hall', 'Toynbee Hall', 'landmark', 'whitechapel', 'University settlement in '
              'Commercial Street where young graduates live and run evening classes, a library and lectures.',
              ['settlement', 'classes', 'reform'], 'free', 'indoor', ['solo', 'friends'], ['evening']),
        # Limehouse and the docks
        place('the-grapes', 'The Grapes', 'tavern', 'limehouse', 'Narrow riverside pub in Narrow Street with a '
              'back room over the water, known to lightermen and ship\'s officers.', ['pub', 'river', 'docks'],
              '$', 'indoor', ADULT, NIGHT),
        place('west-india-docks', 'West India Docks', 'docks', 'limehouse', 'Long basins of sailing ships and '
              'steamers unloading rum, sugar and timber into brick warehouses.', ['ships', 'river', 'work'],
              'free', 'outdoor', ['solo', 'friends'], DAY),
        place('victoria-park', 'Victoria Park', 'park', 'limehouse', 'The East End\'s big park, with lakes, '
              'open-air bathing and Sunday crowds by the drinking fountain.', ['lake', 'bathing', 'east-end'],
              'free', 'outdoor', ALL, DAY, WARM),
        # Southwark and Lambeth
        place('george-inn', 'The George Inn', 'inn', 'southwark', 'The last galleried coaching inn in London, off '
              'Borough High Street, partly used as a railway goods depot.', ['pub', 'galleries', 'old'], '$',
              'indoor', ADULT, ['afternoon', 'evening']),
        place('borough-market', 'Borough Market', 'market', 'southwark', 'Wholesale vegetable market under the '
              'railway viaducts by Southwark Cathedral.', ['produce', 'early', 'railway'], '$', 'mixed',
              ['solo', 'friends'], ['morning']),
        place('canterbury-music-hall', 'Canterbury Music Hall', 'venue', 'lambeth', 'Big music hall on Westminster '
              'Bridge Road: comic singers, acrobats and a chairman, with drinks served at your seat.',
              ['music-hall', 'comedy', 'songs'], '$', 'indoor', ADULT, NIGHT),
        place('lambeth-baths', 'Lambeth Public Baths', 'fitness', 'lambeth', 'Public swimming bath and slipper '
              'baths on the Westminster Bridge Road, cheap on second-class days.', ['swimming', 'baths', 'cheap'],
              '$', 'indoor', ['solo', 'friends', 'family'], DAY),
        place('the-new-cut', 'The New Cut', 'market', 'lambeth', 'Saturday night street market lit by naphtha '
              'flares, selling cheap meat, crockery and old clothes.', ['street-market', 'saturday'], '$',
              'outdoor', ['solo', 'friends', 'family'], ['evening']),
        # Pimlico, Chelsea, Kensington
        place('battersea-park', 'Battersea Park', 'park', 'chelsea', 'Across the Albert Bridge: a boating lake, '
              'a subtropical garden and long paths where people learn to ride the new safety bicycles.',
              ['cycling', 'boating', 'lake'], 'free', 'outdoor', ALL, DAY, WARM),
        place('hyde-park', 'Hyde Park', 'park', 'kensington', 'The Serpentine, Rotten Row for riders, and the '
              'afternoon carriage parade of fashionable society during the Season.', ['walk', 'riding', 'lake'],
              'free', 'outdoor', ALL, ALLDAY),
        place('south-kensington-museum', 'South Kensington Museum', 'museum', 'kensington', 'Decorative arts, casts '
              'and design collections in Cromwell Road, with the first museum refreshment rooms.', ['art',
              'design', 'tea-room'], 'free', 'indoor', ALL, DAY),
        place('royal-albert-hall', 'Royal Albert Hall', 'venue', 'kensington', 'The great round hall for concerts, '
              'choral societies and balls.', ['concerts', 'choirs'], '$$', 'indoor', ALL, DINNER),
        place('harrods', 'Harrods', 'shopping', 'kensington', 'Grocer and draper in the Brompton Road grown into a '
              'department store.', ['department-store', 'groceries'], '$$', 'indoor', ALL, DAY),
        place('pimlico-dairy', 'Dairy tea shop, Pimlico Road', 'cafe', 'pimlico', 'A small dairy with a few tables '
              'selling milk, eggs, bread and butter and pots of tea to lodgers and shop girls.', ['tea', 'cheap',
              'local'], '$', 'indoor', ['solo', 'friends'], DAY, cuisine='Tea, bread and eggs'),
        # Hampstead and Kew
        place('hampstead-heath', 'Hampstead Heath', 'park', 'hampstead', 'Rough heath, ponds and the view over '
              'London from Parliament Hill, crowded with fairs on Bank Holidays.', ['heath', 'views', 'ponds'],
              'free', 'outdoor', ALL, DAY),
        place('spaniards-inn', 'The Spaniards Inn', 'inn', 'hampstead', 'Old inn by the tollhouse at the top of the '
              'Heath, with a garden for tea and beer after a walk.', ['pub', 'garden', 'heath'], '$', 'mixed',
              ALL, ['afternoon', 'evening']),
        place('kew-gardens', 'Royal Botanic Gardens, Kew', 'garden', 'kew', 'Palm House, Temperate House and '
              'pagoda, a penny admission and a long day out by steamer or train.', ['plants', 'glasshouses',
              'outing'], '$', 'mixed', ALL, DAY),
        # Everyday places in every neighbourhood. Tag 'invented' marks small businesses made up for fiction.
        place('marylebone-church', 'St Marylebone Parish Church', 'temple', 'marylebone', 'The big classical '
              'parish church on the Marylebone Road where the Brownings married, with a choir on Sundays.',
              ['church', 'parish', 'music'], 'free', 'indoor', ALL, DAY),
        place('marylebone-baths', 'St Marylebone Public Baths', 'fitness', 'marylebone', 'Parish baths and '
              'wash-houses on the Marylebone Road: a swimming bath, slipper baths and a laundry for households.',
              ['swimming', 'baths', 'laundry'], '$', 'indoor', ['solo', 'friends', 'family'], DAY),
        place('blandford-street-chop-house', 'Dawson\'s chop house, Blandford Street', 'restaurant', 'marylebone',
              'A plain chop house off Baker Street with high-backed boxes, mutton chops, kidneys and a pint of '
              'stout for lodgers and cabmen.', ['chop-house', 'cheap', 'invented'], '$', 'indoor',
              ['solo', 'friends', 'coworkers'], ['afternoon', 'evening'], cuisine='English chops'),
        place('shepherd-market', 'Shepherd Market', 'market', 'mayfair', 'A small village of lanes off Curzon '
              'Street with a butcher, a dairy, a pub and cheap rooms, where Mayfair\'s servants do their own '
              'shopping.', ['shops', 'servants', 'village'], '$', 'mixed', ALL, DAY),
        place('st-stephens-tavern', 'St Stephen\'s Tavern', 'tavern', 'westminster', 'A pub on Bridge Street '
              'facing the Clock Tower, with a division bell so members of Parliament can finish their drinks.',
              ['pub', 'parliament', 'gossip'], '$', 'indoor', ADULT, ['afternoon', 'evening']),
        place('army-and-navy-stores', 'Army and Navy Stores', 'shopping', 'westminster', 'The great co-operative '
              'store on Victoria Street, for members and their friends, selling everything from tea to tents.',
              ['department-store', 'groceries', 'members'], '$$', 'indoor', ALL, DAY),
        place('great-smith-street-baths', 'Westminster Public Baths, Great Smith Street', 'fitness', 'westminster',
              'New parish baths with a swimming bath, private hot baths and a public wash-house behind the Abbey.',
              ['swimming', 'baths', 'laundry'], '$', 'indoor', ['solo', 'friends', 'family'], DAY),
        place('ye-olde-cock-tavern', 'Ye Olde Cock Tavern', 'tavern', 'fleet-street', 'Old Fleet Street chop house '
              'and tavern, moved across the road when the bank took its site, still serving chops and stout to '
              'lawyers and printers.', ['pub', 'chops', 'press'], '$', 'indoor', ADULT, ['afternoon', 'evening'],
              cuisine='English chops'),
        place('st-bride-foundation', 'St Bride Foundation Institute', 'library', 'fleet-street', 'New institute '
              'in Bride Lane for the printing trades, with a technical library, a reading room and swimming baths.',
              ['books', 'printing', 'baths'], '$', 'indoor', ['solo', 'friends', 'coworkers'], ALLDAY),
        place('temple-gardens', 'Inner Temple Garden', 'garden', 'fleet-street', 'Lawns and flower borders between '
              'the barristers\' chambers and the Embankment, a quiet place to eat a sandwich.',
              ['garden', 'quiet', 'law'], 'free', 'outdoor', ['solo', 'friends', 'date'], DAY, WARM),
        place('simpsons-tavern', 'Simpson\'s Tavern', 'restaurant', 'the-city', 'Old chop house up Ball Court off '
              'Cornhill where clerks crowd the benches at one o\'clock for chops, stewed cheese and beer.',
              ['chop-house', 'lunch', 'clerks'], '$', 'indoor', ['solo', 'friends', 'coworkers'], ['afternoon'],
              cuisine='English chops'),
        place('guildhall-library', 'Guildhall Library', 'library', 'the-city', 'The Corporation\'s free reference '
              'library in the Guildhall, full of maps, directories and London history, open to all.',
              ['books', 'free', 'history'], 'free', 'indoor', ['solo'], DAY),
        place('ten-bells', 'The Ten Bells', 'tavern', 'whitechapel', 'Corner pub on Commercial Street opposite '
              'Christ Church, Spitalfields, crowded with market porters and weavers\' descendants.',
              ['pub', 'market', 'east-end'], '$', 'indoor', ADULT, NIGHT),
        place('spitalfields-market', 'Spitalfields Market', 'market', 'whitechapel', 'The fruit and vegetable '
              'market in its new buildings by Christ Church, busy with carts from before dawn.',
              ['produce', 'early', 'carts'], '$', 'mixed', ['solo', 'friends', 'family'], ['morning']),
        place('whitechapel-library', 'Whitechapel Public Library', 'library', 'whitechapel', 'New free library on '
              'the High Street with a newsroom and reading room, much used by young immigrants learning English.',
              ['books', 'free', 'newsroom'], 'free', 'indoor', ['solo', 'friends', 'family'], ALLDAY),
        place('goulston-street-baths', 'Goulston Street Baths and Wash-houses', 'fitness', 'whitechapel', 'Early '
              'public baths and wash-houses where women do the family washing and men pay a penny for a bath.',
              ['baths', 'laundry', 'cheap'], '$', 'indoor', ['solo', 'family'], DAY),
        place('prospect-of-whitby', 'The Prospect of Whitby', 'tavern', 'limehouse', 'Old riverside pub on Wapping '
              'Wall with a flagstone floor, a pewter bar and a balcony over the Thames.',
              ['pub', 'river', 'old'], '$', 'indoor', ADULT, NIGHT),
        place('chrisp-street-market', 'Chrisp Street market', 'market', 'limehouse', 'Poplar\'s street market of '
              'costers\' barrows selling vegetables, fish, crockery and cheap clothes to dockers\' wives.',
              ['street-market', 'cheap', 'east-end'], '$', 'outdoor', ['solo', 'family'], DAY),
        place('poplar-baths', 'Poplar Public Baths', 'fitness', 'limehouse', 'Parish baths on the East India Dock '
              'Road with a swimming bath, slipper baths and a wash-house for dock families.',
              ['swimming', 'baths', 'laundry'], '$', 'indoor', ['solo', 'friends', 'family'], DAY),
        place('museum-tavern', 'The Museum Tavern', 'tavern', 'bloomsbury', 'Pub on Great Russell Street opposite '
              'the British Museum gates, full of readers, students and porters at lunchtime.',
              ['pub', 'students', 'lunch'], '$', 'indoor', ADULT, ['afternoon', 'evening']),
        place('the-lamb', 'The Lamb', 'tavern', 'bloomsbury', 'Small pub in Lamb\'s Conduit Street with snob '
              'screens at the bar, used by hospital staff and clerks from the Inns of Court.',
              ['pub', 'snob-screens', 'local'], '$', 'indoor', ADULT, NIGHT),
        place('mudies-library', 'Mudie\'s Select Library', 'library', 'bloomsbury', 'The great circulating library '
              'on New Oxford Street, where a guinea a year lets you borrow the new three-volume novels.',
              ['books', 'novels', 'subscription'], '$$', 'indoor', ['solo', 'friends'], DAY),
        place('the-anchor-bankside', 'The Anchor, Bankside', 'tavern', 'southwark', 'Riverside pub by the Barclay '
              'Perkins brewery, with draymen at the bar and a view across to St Paul\'s.',
              ['pub', 'river', 'brewery'], '$', 'indoor', ADULT, ['afternoon', 'evening']),
        place('st-saviours-southwark', 'St Saviour\'s Church, Southwark', 'temple', 'southwark', 'The old priory '
              'church by London Bridge, its nave being rebuilt, with a parish of market men and hop factors.',
              ['church', 'old', 'parish'], 'free', 'indoor', ALL, DAY),
        place('southwark-park', 'Southwark Park', 'park', 'southwark', 'A people\'s park in Rotherhithe with a '
              'lake, a bandstand and cricket pitches, near the Surrey Docks.', ['park', 'bandstand', 'cricket'],
              'free', 'outdoor', ALL, DAY, WARM),
        place('old-vic', 'Royal Victoria Hall', 'venue', 'lambeth', 'Miss Cons\'s temperance music hall on the '
              'Waterloo Road: cheap concerts, ballads and lantern lectures, with coffee instead of gin.',
              ['music-hall', 'temperance', 'lectures'], '$', 'indoor', ALL, ['evening']),
        place('vauxhall-park', 'Vauxhall Park', 'park', 'lambeth', 'Small new public park off the South Lambeth '
              'Road with flower beds, benches and a playground for the neighbouring terraces.',
              ['park', 'children', 'new'], 'free', 'outdoor', ALL, DAY, WARM),
        place('lower-marsh-eel-pie-shop', 'Pie and eel shop, Lower Marsh', 'restaurant', 'lambeth', 'Marble '
              'tables and sawdust on the floor, serving hot meat pies, mashed potato and stewed eels with green '
              'liquor.', ['pies', 'eels', 'cheap', 'invented'], '$', 'indoor', ALL, ['afternoon', 'evening'],
              cuisine='Pie and eels'),
        place('st-barnabas-pimlico', 'St Barnabas, Pimlico', 'temple', 'pimlico', 'High church in Church Street '
              'with a choir school and incense, popular with servants and lodgers on Sunday evenings.',
              ['church', 'choir', 'high-church'], 'free', 'indoor', ALL, ['morning', 'evening']),
        place('victoria-station', 'Victoria Station', 'landmark', 'pimlico', 'Two railway termini side by side, '
              'for Brighton and for the Continent, with bookstalls, a refreshment room and a cab yard.',
              ['railway', 'travel', 'bookstall'], 'free', 'indoor', ALL, ALLDAY),
        place('lupus-street-coffee-house', 'Coffee house, Lupus Street', 'cafe', 'pimlico', 'A clean coffee house '
              'with high-backed boxes, serving coffee, rashers and toast to clerks before the omnibus.',
              ['coffee', 'breakfast', 'cheap', 'invented'], '$', 'indoor', ['solo', 'friends'], DAY,
              cuisine='Coffee and breakfasts'),
        place('warwick-way-laundry', 'Mrs Pratt\'s laundry, Warwick Way', 'workshop', 'pimlico', 'A hand laundry '
              'of coppers, mangles and drying lines that collects lodgers\' collars and shirts by the dozen.',
              ['laundry', 'local', 'invented'], '$', 'indoor', ['solo'], DAY),
        place('royal-hospital-chelsea', 'Royal Hospital Chelsea', 'landmark', 'chelsea', 'Wren\'s home for old '
              'soldiers, whose pensioners in scarlet coats show visitors the chapel and the great hall.',
              ['history', 'soldiers', 'gardens'], 'free', 'mixed', ALL, DAY),
        place('kings-head-eight-bells', 'The King\'s Head and Eight Bells', 'tavern', 'chelsea', 'Old corner pub '
              'on Cheyne Walk by the river, used by painters, watermen and pensioners.',
              ['pub', 'river', 'artists'], '$', 'indoor', ADULT, ['afternoon', 'evening']),
        place('carlyles-house', 'Carlyle\'s House', 'museum', 'chelsea', 'Thomas Carlyle\'s plain brick house in '
              'Cheyne Row, newly opened to visitors with his books, pipes and soundproof study.',
              ['writers', 'history', 'new'], '$', 'indoor', ['solo', 'friends'], DAY),
        place('chelsea-public-library', 'Chelsea Public Library', 'library', 'chelsea', 'Free library in Manresa '
              'Road with a reading room, newspapers and a good shelf of art books for the studio crowd.',
              ['books', 'free', 'art'], 'free', 'indoor', ['solo', 'family'], ALLDAY),
        place('the-grenadier', 'The Grenadier', 'tavern', 'kensington', 'Small pub hidden in Wilton Row mews, said '
              'to have been the Guards\' officers\' mess, with a sentry box outside.',
              ['pub', 'mews', 'hidden'], '$', 'indoor', ADULT, NIGHT),
        place('brompton-oratory', 'The Brompton Oratory', 'temple', 'kensington', 'The new Italianate Catholic '
              'church on the Brompton Road, known for its music at Sunday high mass.',
              ['church', 'music', 'catholic'], 'free', 'indoor', ALL, DAY),
        place('jack-straws-castle', 'Jack Straw\'s Castle', 'inn', 'hampstead', 'Weatherboarded inn at the top of '
              'the Heath by the Whitestone Pond, with chops, ale and a view of the whole of London.',
              ['pub', 'heath', 'views'], '$', 'indoor', ALL, ['afternoon', 'evening'], cuisine='English'),
        place('hampstead-parish-church', 'St John-at-Hampstead', 'temple', 'hampstead', 'The village parish church '
              'at the end of Church Row, with Constable buried in the churchyard.',
              ['church', 'village', 'churchyard'], 'free', 'indoor', ALL, DAY),
        place('heath-bathing-ponds', 'Hampstead Heath bathing ponds', 'fitness', 'hampstead', 'The old reservoir '
              'ponds on the Heath where men bathe before work, in all weathers if they are hardy.',
              ['swimming', 'ponds', 'early'], 'free', 'outdoor', ['solo', 'friends'], ['morning'], WARM),
        place('richmond-park', 'Richmond Park', 'park', 'kew', 'The royal deer park on the hill above Richmond, '
              'with herds of red and fallow deer, ponds and long rides for walkers and riders.',
              ['deer', 'walk', 'riding'], 'free', 'outdoor', ALL, DAY),
        place('maids-of-honour', 'Newens\' Maids of Honour tea shop', 'cafe', 'kew', 'Bakery and tea room on the '
              'Kew Road, famous for the little curd tarts called maids of honour.', ['tea', 'cakes', 'outing'],
              '$', 'indoor', ALL, DAY, cuisine='Tea and cakes'),
        place('kew-green', 'Kew Green', 'square', 'kew', 'The village green by the gardens\' main gate, with '
              'cricket on summer Saturdays and St Anne\'s church at one end.', ['cricket', 'green', 'village'],
              'free', 'outdoor', ALL, DAY, WARM),
        place('richmond-boat-hire', 'Boat hire at Richmond Bridge', 'attraction', 'kew', 'Boatmen\'s rafts by the '
              'bridge hiring skiffs and punts by the hour for rowing up toward Petersham and Teddington.',
              ['boating', 'river', 'summer'], '$', 'outdoor', ['friends', 'date', 'family'], DAY, ['summer']),
    ],
    'colleges': [
        college('ucl', 'University College London', 'research-university', 'bloomsbury', 'medium',
                ['medicine', 'engineering', 'secular', 'admits-women']),
        college('kings-college', 'King\'s College London', 'research-university', 'strand-covent-garden', 'medium',
                ['theology', 'engineering', 'medicine']),
        college('slade', 'Slade School of Fine Art', 'art-school', 'bloomsbury', 'small',
                ['drawing', 'painting', 'women-students']),
        college('royal-academy-of-music', 'Royal Academy of Music', 'music-school', 'mayfair', 'small',
                ['piano', 'singing', 'composition']),
        college('lsmw', 'London School of Medicine for Women', 'medical-school', 'bloomsbury', 'small',
                ['medicine', 'women-doctors', 'royal-free-hospital']),
        college('birkbeck', 'Birkbeck Literary and Scientific Institution', 'technical-institute', 'fleet-street',
                'medium', ['evening-classes', 'working-students', 'science']),
    ],
    'careers': [
        career('clerk', 'Office clerk', 'commerce', 'office', '$', 'Copying letters, keeping ledgers and running '
               'errands in a merchant\'s or solicitor\'s office from half past nine to six, Saturdays till two.',
               ['ledgers', 'the senior clerk', 'Saturday half-day', 'keeping respectable on a small wage']),
        career('bank-clerk', 'Bank clerk', 'finance', 'office', '$$', 'A desk in a City bank, counting, posting '
               'and checking figures under strict rules about dress and punctuality.',
               ['ledgers', 'promotion', 'City crowds', 'a steady salary']),
        career('typist', 'Typewriter girl', 'commerce', 'office', '$', 'Typing letters and documents on a '
               'Remington in an office or a typewriting bureau, a new kind of work for young women.',
               ['the machine', 'carbon copies', 'independence', 'ABC lunches']),
        career('telegraph-operator', 'Telegraph clerk', 'communications', 'rotating', '$', 'Sending and receiving '
               'messages by Morse sounder at the Central Telegraph Office, on day and night turns.',
               ['Morse', 'urgent messages', 'the instrument room', 'night turns']),
        career('postman', 'Postman', 'communications', 'early', '$', 'Up to twelve deliveries a day on a fixed '
               'round, starting before seven in the morning.', ['the round', 'weather', 'regular faces']),
        career('governess', 'Governess', 'education', 'flexible', '$', 'Living in with a family to teach their '
               'children lessons, music and manners, neither servant nor family.',
               ['pupils', 'the schoolroom', 'loneliness', 'references']),
        career('schoolmistress', 'Board school teacher', 'education', 'academic', '$', 'Teaching a class of fifty '
               'or sixty children reading, writing and arithmetic in a London School Board school.',
               ['big classes', 'the inspector', 'children of the district']),
        career('housemaid', 'Housemaid', 'domestic-service', 'early', '$', 'Up at six to clean grates, carry water '
               'and keep a household running, with one afternoon off a week.',
               ['the mistress', 'the servants\' hall', 'afternoon off', 'other servants']),
        career('cook', 'Cook', 'domestic-service', 'early', '$', 'Running the kitchen of a private house, planning '
               'meals with the mistress and ordering from tradesmen.', ['menus', 'tradesmen', 'the kitchen maid']),
        career('cabman', 'Cabman', 'transport', 'rotating', '$', 'Driving a hired hansom from a cab rank, paying the '
               'proprietor a daily rent for horse and cab and keeping the rest.',
               ['fares', 'the horse', 'the cab rank', 'fog']),
        career('railway-porter', 'Railway porter', 'transport', 'rotating', '$', 'Handling luggage and parcels on '
               'the platforms at a big terminus, relying on tips.', ['trains', 'luggage', 'tips']),
        career('constable', 'Police constable', 'law-enforcement', 'rotating', '$', 'Walking a beat for the '
               'Metropolitan Police by day or night, with a lantern, a whistle and a notebook.',
               ['the beat', 'night duty', 'the station sergeant', 'lost children']),
        career('nurse', 'Hospital nurse', 'healthcare', 'shift-day', '$', 'A trained nurse on the wards of a '
               'voluntary hospital, living in the nurses\' home under the matron\'s rules.',
               ['ward rounds', 'the sister', 'patients', 'the nurses\' home']),
        career('physician', 'Physician', 'healthcare', 'flexible', '$$$', 'A doctor with a consulting room, seeing '
               'patients in the morning and making house calls in the afternoon.',
               ['patients', 'house calls', 'the practice', 'night calls']),
        career('retail-associate', 'Shop assistant', 'retail', 'shift-day', '$', 'Serving behind the counter of a '
               'draper\'s or department store, often living in over the shop, until eight or later.',
               ['customers', 'long hours', 'living in', 'the floorwalker']),
        career('seamstress', 'Seamstress', 'garment', 'shift-day', '$', 'Sewing blouses, shirts or mantles in a '
               'workroom or at home by the piece.', ['piecework', 'the workroom', 'the season rush']),
        career('performer', 'Music hall performer', 'entertainment', 'evening', '$', 'Singing comic songs or doing '
               'a turn on the halls, sometimes at two or three halls a night.',
               ['the turn', 'the audience', 'agents', 'cabbing between halls']),
        career('actor', 'Actor', 'entertainment', 'evening', '$', 'Playing in a West End company or touring the '
               'provinces, with rehearsals by day and performances every evening.',
               ['rehearsals', 'notices', 'the company', 'touring']),
        career('journalist', 'Journalist', 'press', 'flexible', '$$', 'Writing paragraphs, reports and columns for '
               'a Fleet Street paper, chasing stories by cab and telegraph.',
               ['deadlines', 'the editor', 'Fleet Street taverns', 'the night edition']),
        career('compositor', 'Compositor', 'press', 'shift-night', '$$', 'Setting type by hand for a daily paper, '
               'working through the night to make the morning edition.', ['type', 'the chapel', 'night work']),
        career('docker', 'Docker', 'shipping', 'early', '$', 'Waiting at the dock gates each morning to be taken on '
               'for a day\'s work unloading ships, at sixpence an hour since the strike of 1889.',
               ['the call-on', 'cargo', 'the union', 'uncertain work']),
        career('bartender', 'Barmaid or barman', 'hospitality', 'evening', '$', 'Serving beer, spirits and talk '
               'behind the bar of a public house or restaurant bar until half past twelve.',
               ['regulars', 'the landlord', 'closing time']),
        career('waiter', 'Restaurant waiter', 'hospitality', 'evening', '$', 'Serving tables in a hotel or '
               'restaurant, many of the waiters Swiss, German or Italian.', ['tables', 'tips', 'the head waiter']),
        career('undergraduate', 'Student', 'education', 'academic', '$', 'Attending lectures, laboratories or '
               'studio classes at a London college, often while living in lodgings.',
               ['lectures', 'examinations', 'lodgings', 'friends']),
        career('detective', 'Detective sergeant', 'law-enforcement', 'flexible', '$$', 'A plain-clothes officer '
               'of the Criminal Investigation Department, working cases from Scotland Yard.',
               ['cases', 'Scotland Yard', 'witnesses', 'long days']),
    ],
    'employers': [
        employer('bank-of-england', 'Bank of England', 'finance', 'the-city', 'large', 'The central bank on '
                 'Threadneedle Street, guarded at night by soldiers.', ['bank-clerk', 'clerk']),
        employer('coutts', 'Coutts and Co.', 'finance', 'strand-covent-garden', 'medium', 'Private bank of the '
                 'aristocracy at 59 Strand, where clerks wear frock coats.', ['bank-clerk', 'clerk']),
        employer('lloyds-of-london', 'Lloyd\'s', 'finance', 'the-city', 'medium', 'Underwriters of marine '
                 'insurance in the Royal Exchange, busy with shipping news.', ['clerk', 'typist']),
        employer('gpo', 'General Post Office', 'communications', 'the-city', 'large', 'The Post Office headquarters '
                 'at St Martin\'s-le-Grand, with the Central Telegraph Office across the road.',
                 ['postman', 'telegraph-operator', 'clerk', 'typist']),
        employer('lnwr-euston', 'London and North Western Railway, Euston', 'transport', 'bloomsbury', 'large',
                 'The great railway company\'s London terminus and head offices behind the Euston Arch.',
                 ['railway-porter', 'clerk', 'telegraph-operator']),
        employer('west-india-dock-company', 'East and West India Docks Company', 'shipping', 'limehouse', 'large',
                 'Docks and warehouses at Poplar and Limehouse taking on casual labour each morning.',
                 ['docker', 'clerk']),
        employer('scotland-yard', 'Metropolitan Police, New Scotland Yard', 'law-enforcement', 'westminster',
                 'large', 'Police headquarters in the new building on the Victoria Embankment, home of the '
                 'Criminal Investigation Department.', ['constable', 'detective', 'clerk']),
        employer('barts', 'St Bartholomew\'s Hospital', 'healthcare', 'the-city', 'large', 'Ancient hospital at '
                 'West Smithfield with a medical school, where Watson first met Holmes in the chemical laboratory.',
                 ['nurse', 'physician']),
        employer('guys-hospital', 'Guy\'s Hospital', 'healthcare', 'southwark', 'large', 'Teaching hospital near '
                 'London Bridge.', ['nurse', 'physician']),
        employer('daily-telegraph', 'The Daily Telegraph', 'press', 'fleet-street', 'medium', 'Penny morning paper '
                 'in Fleet Street with the biggest sale in the world.', ['journalist', 'compositor', 'clerk']),
        employer('harrods-employer', 'Harrods', 'retail', 'kensington', 'medium', 'Department store in the '
                 'Brompton Road, staff living in over the shop.', ['retail-associate', 'clerk', 'seamstress']),
        employer('liberty-employer', 'Liberty and Co.', 'retail', 'mayfair', 'medium', 'Regent Street shop for '
                 'silks and art fabrics with its own dressmaking workroom.', ['retail-associate', 'seamstress']),
        employer('savoy', 'The Savoy', 'hospitality', 'strand-covent-garden', 'medium', 'The Savoy theatre and '
                 'its new electric-lit hotel by the Embankment, with Escoffier in the kitchen.',
                 ['waiter', 'bartender', 'actor', 'performer']),
        employer('lyceum-company', 'Henry Irving\'s Lyceum company', 'entertainment', 'strand-covent-garden',
                 'small', 'Irving and Ellen Terry\'s company at the Lyceum Theatre.', ['actor']),
        employer('london-school-board', 'School Board for London', 'education', 'westminster', 'large',
                 'Runs the board schools across London from offices on the Victoria Embankment.',
                 ['schoolmistress', 'clerk']),
        employer('doulton', 'Doulton and Co., Lambeth', 'manufacturing', 'lambeth', 'medium', 'Pottery and '
                 'drainpipe works on Lambeth High Street, with a studio of women painting art stoneware.',
                 ['clerk', 'seamstress']),
    ],
    'career_hubs': [
        {'id': 'city-commerce', 'name': 'The City', 'neighborhoods': ['the-city'],
         'sectors': ['finance', 'commerce', 'communications', 'shipping'],
         'summary': 'Banks, insurance offices, shipping firms and merchant houses employing armies of clerks.',
         'source': S},
        {'id': 'fleet-street-strand', 'name': 'Fleet Street and the Strand', 'neighborhoods': ['fleet-street',
         'strand-covent-garden'], 'sectors': ['press', 'entertainment', 'hospitality', 'law'],
         'summary': 'Newspapers, theatres, hotels, restaurants and the lawyers of the Temple.', 'source': S},
        {'id': 'west-end-households', 'name': 'West End houses and shops', 'neighborhoods': ['mayfair', 'kensington',
         'marylebone'], 'sectors': ['domestic-service', 'retail', 'garment', 'education', 'healthcare'],
         'summary': 'Great houses that need servants and governesses, doctors\' consulting rooms, and the '
                    'shops and dressmakers that serve them.', 'source': S},
        {'id': 'docks-and-river', 'name': 'The docks and the river', 'neighborhoods': ['limehouse', 'southwark'],
         'sectors': ['shipping', 'transport', 'manufacturing'],
         'summary': 'Docks, wharves, breweries and warehouses along both banks below London Bridge.', 'source': S},
        {'id': 'east-end-workshops', 'name': 'East End workshops', 'neighborhoods': ['whitechapel'],
         'sectors': ['garment', 'manufacturing'], 'summary': 'Small tailoring and boot-making workshops in '
         'Whitechapel and Spitalfields.', 'source': S},
    ],
    'climate': {
        'summary': 'Cool and damp: mild summers, raw grey winters, rain spread through the year, and thick yellow '
                   'coal-smoke fogs from November to February.',
        'months': [
            month(43, 34, 15, 'Cold and dark by four; the worst fogs come now.'),
            month(44, 34, 13, 'Raw; February 1895 was bitterly cold, with ice floes on the Thames.'),
            month(49, 36, 13, 'Wind and showers; the Boat Race at the end of the month or in early April.'),
            month(55, 39, 12, 'Showery spring; parks green up.'),
            month(62, 45, 12, 'Mild; the Season begins and the Royal Academy opens.'),
            month(68, 51, 11, 'Warmest dry spell; Derby Day and garden parties.'),
            month(72, 54, 11, 'Warm, sometimes close and smelly by the river.'),
            month(70, 54, 12, 'Society leaves town; Bank Holiday crowds on the Heath.'),
            month(65, 50, 12, 'Mild and settled; Londoners back from the seaside.'),
            month(57, 45, 14, 'Damp and misty; theatres reopen for the autumn.'),
            month(49, 39, 15, 'Fog season starts; gas lamps lit by mid-afternoon.'),
            month(45, 36, 15, 'Cold, wet and foggy; Christmas markets and pantomimes.'),
        ],
        'source': S,
    },
    'annual_events': [
        event('the-season', 'The London Season', [5, 6, 7], 'mayfair', 'Society comes up to town for balls, '
              'dinners, presentations at Court and the afternoon parade in Hyde Park, and every house in Mayfair '
              'needs extra servants.'),
        event('royal-academy-summer-exhibition', 'Royal Academy Summer Exhibition', [5, 6, 7], 'mayfair',
              'The year\'s new paintings hung floor to ceiling at Burlington House, and everyone has an opinion.'),
        event('boat-race', 'The University Boat Race', [3, 4], 'chelsea', 'Oxford and Cambridge row from Putney to '
              'Mortlake, and crowds wearing dark or light blue line the towpaths and bridges.'),
        event('derby-day', 'Derby Day', [6], None, 'Half of London goes down to Epsom Downs by train, brake and '
              'costermonger\'s cart for the great horse race.'),
        event('august-bank-holiday', 'August Bank Holiday on Hampstead Heath', [8], 'hampstead', 'Hundreds of '
              'thousands come up to the Heath for swings, donkey rides, coconut shies and picnics.'),
        event('promenade-concerts', 'Promenade concerts at Queen\'s Hall', [8, 9, 10], 'marylebone', 'Robert '
              'Newman and the young conductor Henry Wood begin a season of cheap nightly concerts in August 1895, '
              'with a shilling to stand.'),
        event('guy-fawkes-night', 'Guy Fawkes Night', [11], None, 'Boys wheel guys through the streets begging '
              'pennies, and bonfires and fireworks go up on the fifth of November.'),
        event('lord-mayors-show', 'Lord Mayor\'s Show', [11], 'the-city', 'The new Lord Mayor rides in the gilded '
              'state coach through the City to the Law Courts, with bands and floats.'),
        event('smithfield-christmas', 'Christmas at Smithfield and Leadenhall', [12], 'the-city', 'Geese, turkeys '
              'and beef hung in rows for the Christmas trade, and goose clubs paying out.'),
        event('christmas-pantomime', 'Christmas pantomimes', [12, 1], 'strand-covent-garden', 'Drury Lane and the '
              'other big theatres open their pantomimes on Boxing Day, with comedians, a transformation scene and '
              'a harlequinade.'),
    ],
    'local_color': [
        color('pie-mash-and-eels', 'Pie, mash and eels', 'dish', 'Minced-meat pies with mashed potato and green '
              'parsley "liquor", or stewed and jellied eels, eaten at marble-topped tables in South and East London '
              'pie shops.', ['lower-marsh-eel-pie-shop', 'the-new-cut']),
        color('whelks-and-cockles', 'Whelks and cockles', 'dish', 'Saucers of whelks, cockles and mussels with vinegar '
              'and pepper, bought from stalls outside pubs and on the market streets on a Saturday night.',
              ['the-new-cut', 'petticoat-lane', 'chrisp-street-market']),
        color('baked-potatoes-and-chestnuts', 'Baked potatoes and hot chestnuts', 'dish', 'Street sellers with glowing '
              'cans sell hot baked potatoes and roast chestnuts for a halfpenny or a penny, as much to warm the hands '
              'as to eat.', seasons=['fall', 'winter']),
        color('fried-fish-and-chips', 'Fried fish and chips', 'dish', 'Fried fish shops, many kept by Jewish families '
              'in the East End, sell fish fried in batter with chipped potatoes, wrapped in paper to carry away.',
              ['whitechapel']),
        color('chop-and-porter', 'A chop and a pint of porter', 'dish', 'The City clerk\'s dinner: a mutton chop or '
              'steak from the gridiron with a potato and a pewter pint of porter, in a sawdust-floored chop house.',
              ['cheshire-cheese', 'simpsons-tavern', 'ye-olde-cock-tavern', 'blandford-street-chop-house']),
        color('tea-shop-tea', 'A pot of tea at the tea shop', 'drink', 'The new Aerated Bread Company and Lyons tea '
              'shops serve tea, buns and poached eggs cheaply, and are respectable places for women to eat alone.',
              ['abc-cheapside', 'lyons-piccadilly']),
        color('half-and-half', 'Half-and-half', 'drink', 'A pint drawn half of ale and half of porter, a common order '
              'at the public-house bar.'),
        color('christmas-pudding', 'Christmas pudding', 'dish', 'Households stir the plum pudding on Stir-up Sunday in '
              'late November, everyone taking a turn and making a wish, and serve it flaming with brandy on Christmas '
              'Day.', seasons=['fall', 'winter']),
        color('hot-cross-buns', 'Hot cross buns', 'dish', 'Spiced buns marked with a cross are cried in the streets on '
              'Good Friday morning: "Hot cross buns! One a penny, two a penny!"', seasons=['spring']),
        color('rhyming-slang', 'Rhyming slang', 'saying', 'Cockneys say "apples and pears" for stairs and "plates of '
              'meat" for feet, and often drop the rhyming word so that outsiders are lost.',
              ['whitechapel', 'limehouse']),
        color('money-slang', 'A bob, a tanner, a quid', 'saying', 'Everyone counts in slang: a "bob" is a shilling, a '
              '"tanner" sixpence, a "joey" fourpence, a "quid" a sovereign or pound, and a "monkey" five hundred '
              'pounds.'),
        color('peelers-and-bobbies', 'Bobbies and coppers', 'saying', 'Police constables are "bobbies", "peelers" '
              'after Sir Robert Peel, or "coppers"; a toff is a well-dressed gentleman and a swell a showy one.'),
        color('pea-souper', 'A pea-souper', 'other', 'The thick yellow coal-smoke fogs, also called "London '
              'particulars", that stop the traffic, put link-boys to work with torches and leave soot on every collar.',
              seasons=['fall', 'winter']),
        color('costermongers', 'Costermongers', 'shop', 'Costers sell fruit, vegetables and fish from barrows and '
              'donkey carts, crying their goods, and dress for best in pearl-buttoned jackets.',
              ['the-new-cut', 'petticoat-lane', 'chrisp-street-market', 'covent-garden-market']),
        color('muffin-man', 'The muffin man', 'custom', 'On winter afternoons the muffin man walks the residential '
              'streets ringing a handbell, with a tray of muffins and crumpets on his head for toasting at the fire.',
              seasons=['fall', 'winter']),
        color('church-parade', 'Church parade', 'custom', 'During the Season, fashionable London walks in Hyde Park '
              'near the Achilles statue after Sunday morning service to see and be seen.',
              ['hyde-park'], ['spring', 'summer']),
        color('calling-cards', 'Calling cards and at-home days', 'custom', 'Ladies of the middle and upper classes '
              'leave engraved cards when they call, turn down a corner for a personal visit, and keep a fixed '
              'afternoon "at home" each week.', ['mayfair', 'kensington', 'marylebone']),
        color('music-hall-chorus', 'Joining in the chorus', 'custom', 'Music hall audiences sing along with the '
              'choruses of the comic songs, eat and drink in their seats, and let a turn they dislike know about it.',
              ['canterbury-music-hall', 'peoples-palace']),
        color('appy-ampstead', '\'Appy \'Ampstead', 'custom', 'On bank holidays East Enders crowd onto Hampstead Heath '
              'for donkey rides, swings, coconut shies and roundabouts.', ['hampstead-heath'], ['spring', 'summer']),
        color('county-cricket', 'Surrey and Middlesex cricket', 'team', 'County cricket at the Oval (Surrey) and '
              'Lord\'s (Middlesex) draws big summer crowds, and W. G. Grace\'s run-making is the talk of 1895.',
              seasons=['summer']),
    ],
    'prices': [
        price('beer', 'Pint of beer', 0.17, 0.25, 'a pint, 2d.-3d.'),
        price('loaf', 'Quartern loaf', 0.42, 0.5, '4 lb, 5d.-6d.'),
        price('coffee-stall', 'Coffee at a stall', 0.08, 0.17, 'a mug, 1d.-2d.'),
        price('chophouse', 'Chophouse dinner', 1, 2.5, 'chop, potatoes, bread and beer'),
        price('lodging-house', 'Common lodging-house bed', 0.33, 0.5, 'a night, 4d.-6d.'),
        price('hotel', 'Hotel room', 4, 12, 'a night'),
        price('board', 'Board and lodging', 15, 25, "a week's board"),
        price('hansom', 'Hansom cab', 1, 2.5, 'a short ride; 1s. the first two miles'),
        price('omnibus', 'Omnibus fare', 0.08, 0.5, 'one way, 1d.-6d.'),
        price('newspaper', 'Daily paper', 0.04, 0.25, 'halfpenny papers to The Times at 3d.'),
        price('music-hall', 'Music-hall seat', 0.5, 3, 'gallery to stalls'),
        price('theatre', 'West End theatre stall', 7.5, 10.5, '7s. 6d. to half a guinea'),
        price('tobacco', 'Shag tobacco', 0.25, 0.33, 'an ounce, 3d.-4d.'),
        price('boots', 'Working boots', 8, 15, 'a pair'),
    ],
    # Drawn on the map, since the city has no street map (src/features/map/drawn.ts).
    'water': [{'kind': 'river', 'name': 'Thames', 'width_km': 0.3, 'points': [
        [51.470, -0.300], [51.468, -0.215], [51.480, -0.170], [51.486, -0.126], [51.500, -0.121], [51.508, -0.102],
        [51.506, -0.080], [51.505, -0.055], [51.507, -0.036], [51.492, -0.015]]}],
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
