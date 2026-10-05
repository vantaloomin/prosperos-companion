"""Calderwick, an original steampunk mill-and-canal town. Run `python scripts/world/calderwick.py` to rewrite the JSON."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'cities' / 'calderwick.json'
S = 'curated-2026-10'
ERA = 'steampunk'


def hood(id, name, summary, vibe, lat, lon, tier, rent, housing, walk, transit):
    room, two_rooms, house = rent
    return {'id': id, 'name': name, 'summary': summary, 'vibe': vibe, 'lat': lat, 'lon': lon, 'rent_tier': tier,
            'rent': {'studio': room, 'one_bedroom': two_rooms, 'two_bedroom': house}, 'housing': housing,
            'walkability': walk, 'transit': transit, 'source': S}


def place(id, name, kind, hood, summary, tags, cost, setting, good_for, day_parts, seasons=(), cuisine=''):
    return {'id': id, 'name': name, 'kind': kind, 'neighborhood': hood, 'summary': summary, 'tags': tags,
            'cost': cost, 'setting': setting, 'good_for': good_for, 'day_parts': day_parts,
            'seasons': list(seasons), 'cuisine': cuisine, 'source': S}


def employer(id, name, sector, hood, size, summary, careers):
    return {'id': id, 'name': name, 'sector': sector, 'neighborhood': hood, 'size': size, 'summary': summary,
            'careers': careers, 'source': S}


def career(id, name, sector, schedule, pay, summary, themes):
    return {'id': id, 'name': name, 'sector': sector, 'schedule': schedule, 'pay': pay, 'summary': summary,
            'themes': themes, 'eras': [ERA]}


def event(id, name, months, hood, summary):
    return {'id': id, 'name': name, 'months': months, 'neighborhood': hood, 'summary': summary, 'source': S}


def month(high, low, rain, note):
    return {'high_f': high, 'low_f': low, 'rain_days': rain, 'note': note}


ALL = ['solo', 'friends', 'date', 'family']
ADULT = ['solo', 'friends', 'date']
DAY = ['morning', 'afternoon']
NIGHT = ['evening', 'late']
WARM = ['spring', 'summer', 'fall']

CITY = {
    'schema_version': 1, 'id': 'calderwick', 'name': 'Calderwick', 'setting': 'original', 'era': ERA,
    'basis': 'Original setting written for Prospero Companion.',
    'region': 'West Riding', 'country': 'England', 'timezone': 'Europe/London',
    'aliases': ['Calderwick-on-Calder', 'the Tube Town'],
    'summary': 'A smoky river and canal town in the Pennine foothills that made its fortune drawing metal tube '
               'and building pneumatic dispatch systems: the cash carriers in shop ceilings, the message tubes in '
               'banks and the town\'s own pneumatic post.',
    'lat': 53.735, 'lon': -1.940,
    'currency': {'code': 's', 'symbol': 's', 'name': 'shillings'},
    'rent_period': 'week',
    'speeds': {'walk': 4.5, 'tram': 11, 'bus': 8, 'commuter-rail': 30, 'boat': 5, 'carriage': 10, 'horse': 12,
               'airship': 60},
    'sources': {
        S: {'kind': 'curated', 'title': 'Calderwick, an original setting written for Prospero Companion',
            'license': 'CC0-1.0', 'retrieved': '2026-10-05',
            'note': 'Invented town with no real counterpart. Its texture follows ordinary late-Victorian life in '
                    'the textile and engineering towns of the West Riding and Lancashire: canal basins, '
                    'workers\' terraces, temperance halls, mechanics\' institutes, wakes weeks, Whit walks and '
                    'municipal parks. Rents are weekly, in shillings, for one room, two rooms and a small whole '
                    'house. Climate is rounded from Pennine-town normals with winter smog added for the setting.'},
    },
    'neighborhoods': [
        hood('castle-hill', 'Castle Hill', 'The old town on the hill: the ruined castle, the parish church, '
             'crooked stone lanes and the tall houses of the families who owned the land before the works came.',
             ['old-town', 'old-families', 'quiet', 'views'], 53.7385, -1.9420, 'high', ([6, 9], [10, 16], [25, 45]),
             ['stone-townhouse', 'lodgings'], 'high', ['kirkgate-tram']),
        hood('lowfield', 'Lowfield', 'The works district on the flat river land: tube mills, foundries and pump '
             'shops, chimneys in every direction and a hooter at six each morning.',
             ['industrial', 'loud', 'soot', 'working-class'], 53.7300, -1.9310, 'low', ([2, 3], [3, 5], [5, 7]),
             ['back-to-back', 'lodging-house'], 'medium', ['river-road-tram', 'omnibus']),
        hood('saltergate-basin', 'Saltergate Basin', 'The canal basin where the Calder and Aske Navigation meets '
             'the river: warehouses, wharf cranes, horse-boat stables and boat families living aboard.',
             ['canal', 'warehouses', 'working', 'waterside'], 53.7330, -1.9380, 'low', ([2, 4], [4, 6], [6, 9]),
             ['canal-boat', 'warehouse-lodgings', 'terrace'], 'medium', ['river-road-tram', 'packet-boat']),
        hood('hobcroft', 'Hobcroft', 'Rows of red-brick workers\' terraces up the slope from Lowfield, with corner '
             'shops, a wash-house, chapels and washing strung across the back streets on Mondays.',
             ['terraces', 'working-class', 'neighbourly', 'chapels'], 53.7275, -1.9445, 'low',
             ([2, 3], [3, 5], [5, 8]), ['terrace', 'back-to-back'], 'medium', ['river-road-tram', 'omnibus']),
        hood('ings-end', 'Ings End', 'Newer through-terraces on the old water meadows downstream, built by the '
             'Co-operative building society, with allotments running down to the river.',
             ['terraces', 'allotments', 'respectable-working', 'riverside'], 53.7240, -1.9180, 'low',
             ([2, 4], [4, 6], [6, 9]), ['through-terrace', 'cottage'], 'medium', ['river-road-tram']),
        hood('exchange-quarter', 'Exchange Quarter', 'The respectable merchant quarter: banks, insurance offices, '
             'the Exchange, the department store and the town\'s first pneumatic post office.',
             ['commercial', 'respectable', 'offices', 'shopping'], 53.7355, -1.9400, 'high',
             ([5, 8], [9, 14], [18, 30]), ['rooms-over-shops', 'stone-townhouse'], 'high',
             ['kirkgate-tram', 'river-road-tram', 'omnibus']),
        hood('station-fields', 'Station Fields', 'The railway quarter around Calderwick Central: goods yards, '
             'the engine shed, commercial hotels, cab ranks and the music hall.',
             ['railway', 'hotels', 'nightlife', 'transient'], 53.7340, -1.9480, 'mid', ([3, 5], [5, 8], [8, 12]),
             ['lodging-house', 'terrace', 'hotel-rooms'], 'high', ['kirkgate-tram', 'local-trains', 'omnibus']),
        hood('market-place', 'Market Place', 'The market district below Castle Hill: the covered market hall, '
             'Saturday stalls on the setts, tripe shops, pawnbrokers and the Theatre Royal.',
             ['market', 'busy', 'food', 'theatre'], 53.7370, -1.9375, 'mid', ([3, 5], [5, 8], [9, 14]),
             ['rooms-over-shops', 'lodgings'], 'high', ['kirkgate-tram', 'omnibus']),
        hood('paradise', 'Paradise', 'The immigrant quarter around Paradise Street, settled by Irish labourers who '
             'dug the canal and later by Italian families: ice-cream carts, a Catholic church and crowded courts.',
             ['immigrant', 'irish', 'italian', 'crowded', 'catholic'], 53.7310, -1.9450, 'low',
             ([2, 3], [3, 5], [5, 7]), ['court-housing', 'lodging-house', 'terrace'], 'high',
             ['river-road-tram']),
        hood('ackroyd-park', 'Ackroyd Park', 'Villas and better terraces around the park that Hannah Ackroyd, '
             'widow of a tube-mill owner, gave the town, with its glasshouse, lake and bandstand.',
             ['park', 'leafy', 'family', 'respectable'], 53.7420, -1.9330, 'mid', ([4, 6], [7, 11], [14, 24]),
             ['villa', 'through-terrace'], 'medium', ['kirkgate-tram']),
        hood('moorside', 'Moorside', 'The institute district on the road up to the moor: the Pennock Institute, '
             'the art school, the infirmary, the museum and lodgings full of students and nurses.',
             ['students', 'institute', 'medical', 'lodgings'], 53.7440, -1.9450, 'mid', ([3, 5], [6, 9], [12, 18]),
             ['lodgings', 'terrace', 'nurses-home'], 'medium', ['kirkgate-tram', 'omnibus']),
        hood('fernleigh', 'Fernleigh', 'Where the new money lives: big stone villas of the tube and pump '
             'manufacturers, each with a carriage drive, a conservatory and a message tube to the works.',
             ['new-money', 'affluent', 'villas', 'quiet'], 53.7490, -1.9300, 'very-high', ([8, 12], [14, 22],
             [40, 80]), ['villa', 'coach-house-flat'], 'low', ['omnibus']),
        hood('ridley-moor', 'Ridley Moor', 'Open moor above the town with reservoirs, a few farms and the airship '
             'mooring mast where the mail ship ties up.',
             ['moorland', 'airship', 'reservoirs', 'fresh-air'], 53.7560, -1.9550, 'mid', ([3, 5], [5, 8],
             [9, 15]), ['farm-cottage', 'cottage'], 'low', ['air-mail', 'omnibus']),
        hood('calder-holme', 'Calder Holme', 'The riverside pleasure ground upstream of the works, with the lido, '
             'the velodrome, a pier on the old mill dam and Sunday crowds in summer.',
             ['leisure', 'riverside', 'summer', 'sport'], 53.7270, -1.9620, 'mid', ([3, 5], [5, 8], [9, 14]),
             ['terrace', 'cottage'], 'medium', ['river-road-tram', 'packet-boat']),
    ],
    'transit': [
        {'id': 'kirkgate-tram', 'name': 'Kirkgate steam tram', 'kind': 'tram', 'summary': 'A small steam tram '
         'engine pulling double-deck cars from Station Fields up Kirkgate past the market to Moorside and the '
         'park gates.', 'source': S},
        {'id': 'river-road-tram', 'name': 'River Road horse tram', 'kind': 'tram', 'summary': 'Horse trams along '
         'the valley bottom from Calder Holme through Lowfield and the basin to Ings End, packed at shift change.',
         'source': S},
        {'id': 'omnibus', 'name': 'Corporation horse omnibuses', 'kind': 'bus', 'summary': 'Horse buses on the '
         'hill routes the trams cannot climb, out to Fernleigh and up to Ridley Moor.', 'source': S},
        {'id': 'local-trains', 'name': 'Calder Valley local trains', 'kind': 'commuter-rail', 'summary': 'Stopping '
         'trains from Calderwick Central down the valley to the neighbouring mill towns and the main line.',
         'source': S},
        {'id': 'packet-boat', 'name': 'Canal packet boat', 'kind': 'boat', 'summary': 'A slow horse-drawn '
         'passenger boat on the canal between Saltergate Basin and Calder Holme, popular on summer Sundays.',
         'source': S},
        {'id': 'air-mail', 'name': 'Ridley Moor air mail', 'kind': 'airship', 'summary': 'One mail airship that '
         'flies the bags to the coast and back twice a week, carrying a handful of paying passengers.',
         'source': S},
        {'id': 'cab', 'name': 'Hackney cabs', 'kind': 'carriage', 'summary': 'Horse cabs from the station rank and '
         'the Exchange, for anyone who can afford a shilling.', 'source': S},
    ],
    'places': [
        place('old-bell', 'The Old Bell', 'tavern', 'castle-hill', 'The oldest pub in town, low-beamed, by the '
              'church gate; bell-ringers drink there after practice night.', ['old', 'pub', 'quiet'], '$',
              'indoor', ADULT, NIGHT),
        place('castle-ruins', 'Calderwick Castle ruins', 'landmark', 'castle-hill', 'A broken keep and curtain '
              'wall on top of the hill with a view over the chimneys and the canal.', ['history', 'views', 'walk'],
              'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('st-wilfrids', "St Wilfrid's parish church", 'temple', 'castle-hill', 'The old parish church, '
              'blackened by soot, with Sunday services and a Thursday organ recital.', ['church', 'music'],
              'free', 'indoor', ALL, ['morning', 'evening']),
        place('moulders-arms', "The Moulders' Arms", 'tavern', 'lowfield', 'A works pub at the gates of Dunmore '
              'Brothers that opens early for men coming off the night turn.', ['pub', 'works', 'rough'], '$',
              'indoor', ['solo', 'friends', 'coworkers'], ['morning', 'evening', 'late']),
        place('lowfield-boxing', 'Lowfield Amateur Boxing Club', 'fitness', 'lowfield', 'A boxing gym in an old '
              'pattern shop, with skipping ropes, a ring and Friday night bouts.', ['boxing', 'sport'], '$',
              'indoor', ['solo', 'friends'], ['evening']),
        place('saltergate-wharves', 'Saltergate wharves', 'docks', 'saltergate-basin', 'The canal wharves where '
              'narrowboats unload coal and pig iron and load crated tube for the coast.', ['canal', 'boats',
              'work'], 'free', 'outdoor', ['solo', 'friends', 'family'], DAY),
        place('navigation-inn', 'The Navigation Inn', 'tavern', 'saltergate-basin', 'A boatmen\'s pub on the '
              'basin with a stable yard behind and a fire in the back room.', ['pub', 'canal', 'boatmen'], '$',
              'indoor', ADULT, NIGHT),
        place('basin-coffee-tavern', 'Basin Coffee Tavern', 'cafe', 'saltergate-basin', 'A temperance coffee '
              'tavern for boat families: mugs of cocoa, bacon breadcakes and newspapers on a rail.',
              ['temperance', 'breakfast', 'cheap'], '$', 'indoor', ALL, DAY, cuisine='cafe'),
        place('hobcroft-baths', 'Hobcroft Public Baths and Wash-house', 'fitness', 'hobcroft', 'Corporation baths '
              'with a swimming bath, slipper baths by the half hour and a steam laundry for washing day.',
              ['swimming', 'baths', 'laundry'], '$', 'indoor', ['solo', 'friends', 'family'], DAY),
        place('hobcroft-fish-saloon', 'Garside\'s Fish Saloon', 'restaurant', 'hobcroft', 'A fish and chip shop '
              'with a back room of oilcloth tables, open till the last pub closes.', ['fish-and-chips', 'cheap'],
              '$', 'indoor', ALL, ['afternoon', 'evening', 'late'], cuisine='fish and chips'),
        place('hope-street-hall', 'Hope Street Temperance Hall', 'venue', 'hobcroft', 'A temperance hall with '
              'magic-lantern shows, penny readings, choir practice and a tea urn that never goes cold.',
              ['temperance', 'lantern-shows', 'choir'], '$', 'indoor', ALL, ['evening']),
        place('ings-allotments', 'Ings End allotments', 'garden', 'ings-end', 'Allotment strips down to the river, '
              'with leeks, rhubarb, pigeon lofts and sheds for a quiet pipe.', ['allotments', 'pigeons',
              'outdoors'], 'free', 'outdoor', ['solo', 'friends', 'family'], DAY, WARM),
        place('rose-and-crown', 'The Rose and Crown', 'tavern', 'ings-end', 'A neighbourhood pub with a bowling '
              'green, a darts board and a Saturday sing-song round the piano.', ['pub', 'bowls', 'singing'], '$',
              'mixed', ADULT, NIGHT),
        place('the-exchange', 'The Calderwick Exchange', 'landmark', 'exchange-quarter', 'The columned Exchange '
              'where tube orders and metal prices are dealt on Tuesdays, with a public gallery.',
              ['architecture', 'commerce'], 'free', 'indoor', ['solo', 'friends'], DAY),
        place('bulmers-chophouse', "Bulmer's Chophouse", 'restaurant', 'exchange-quarter', 'A panelled chophouse '
              'for clerks and merchants: chops, steak pudding and stout at long tables.', ['chophouse',
              'lunch'], '$$', 'indoor', ['solo', 'friends', 'coworkers', 'date'], ['afternoon', 'evening'],
              cuisine='English'),
        place('listers-coffee-rooms', "Lister's Coffee Rooms", 'cafe', 'exchange-quarter', 'Upstairs coffee rooms '
              'with chess tables, the London papers and a pneumatic tube to send notes to the Exchange.',
              ['coffee', 'chess', 'newspapers'], '$', 'indoor', ['solo', 'friends', 'date'], DAY,
              cuisine='coffee'),
        place('wright-battersby', 'Wright and Battersby', 'shopping', 'exchange-quarter', 'The department store, '
              'with cash carriers whizzing through ceiling tubes to the counting house and a tea room upstairs.',
              ['department-store', 'shopping'], '$$', 'indoor', ['solo', 'friends', 'family', 'date'], DAY),
        place('free-library', 'Calderwick Free Library', 'library', 'exchange-quarter', 'The free lending library '
              'and newsroom, warm in winter, with a ladies\' reading room and a long waiting list for new novels.',
              ['books', 'newspapers', 'quiet'], 'free', 'indoor', ['solo', 'family'], ['morning', 'afternoon',
              'evening']),
        place('railway-tavern', 'The Railway Tavern', 'tavern', 'station-fields', 'A busy pub opposite the station '
              'full of porters, commercial travellers and drivers off the late train.', ['pub', 'railway'], '$',
              'indoor', ADULT, NIGHT),
        place('thornbers-varieties', "Thornber's Varieties", 'venue', 'station-fields', 'The music hall: comic '
              'singers, a juggler, a ventriloquist and the chorus, twice nightly, with a bar at the back.',
              ['music-hall', 'comedy', 'songs'], '$', 'indoor', ['friends', 'date'], NIGHT),
        place('station-refreshment-room', 'Central Station refreshment room', 'restaurant', 'station-fields',
              'Tea, pork pies and hot soup on the platform, open for the first and last trains.', ['tea',
              'railway', 'quick'], '$', 'indoor', ['solo', 'friends'], ['morning', 'afternoon', 'evening'],
              cuisine='English'),
        place('market-hall', 'Calderwick Market Hall', 'market', 'market-place', 'A cast-iron covered market of '
              'butchers, cheese stalls, a sweet stall, a herbalist and a mushy-pea stand.', ['market', 'food',
              'shopping'], '$', 'indoor', ALL, DAY),
        place('saturday-market', 'Saturday open market', 'market', 'market-place', 'Stalls on the setts every '
              'Saturday selling cloth, crockery, second-hand books and quack remedies, lit by naphtha flares '
              'after dark.', ['market', 'saturday', 'bargains'], '$', 'outdoor', ALL, ['morning', 'afternoon',
              'evening']),
        place('brierleys-tripe', "Brierley's Tripe and Cow-heel Shop", 'restaurant', 'market-place', 'A tripe '
              'dresser\'s with a dining room behind: tripe and onions, pies and peas, very cheap.', ['tripe',
              'pies', 'cheap'], '$', 'indoor', ['solo', 'friends', 'family'], ['afternoon', 'evening'],
              cuisine='English'),
        place('whiteleys-cafe', "Whiteley's Cafe", 'cafe', 'market-place', 'A tea room above the confectioner\'s, '
              'with fat rascals, curd tarts and a trio playing on Saturday afternoons.', ['tea-room', 'cakes'],
              '$', 'indoor', ['friends', 'date', 'family'], DAY, cuisine='tea room'),
        place('theatre-royal', 'Theatre Royal', 'venue', 'market-place', 'The proper theatre, with touring '
              'companies, melodrama, Shakespeare in winter and the pantomime from Boxing Day.', ['theatre',
              'pantomime'], '$$', 'indoor', ['friends', 'date', 'family'], ['afternoon', 'evening']),
        place('rossis-ices', "Rossi's ice-cream parlour", 'cafe', 'paradise', 'An Italian family\'s parlour that '
              'sells ice cream, hot chestnuts in winter and strong coffee all year.', ['ice-cream', 'italian'],
              '$', 'indoor', ALL, ['afternoon', 'evening'], cuisine='Italian'),
        place('st-patricks-hall', "St Patrick's Hall", 'venue', 'paradise', 'The Catholic parish hall: Irish '
              'dances on Saturday night, whist drives and a boxing tournament at Easter.', ['dances', 'irish',
              'whist'], '$', 'indoor', ['friends', 'date', 'family'], ['evening']),
        place('bonettis-bakery', "Bonetti's bakery", 'market', 'paradise', 'A bakery on Paradise Street selling '
              'bread rolls, biscotti and hot pies to the works crowds before six.', ['bakery', 'italian', 'early'],
              '$', 'indoor', ['solo', 'family'], ['morning'], cuisine='bakery'),
        place('ackroyd-park-grounds', 'Ackroyd Park', 'park', 'ackroyd-park', 'The philanthropist\'s park, with a '
              'boating lake, a bandstand, bowling greens and a drinking fountain carved with her motto.',
              ['park', 'bandstand', 'boating'], 'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('ackroyd-glasshouse', 'Ackroyd Palm House', 'garden', 'ackroyd-park', 'The botanic glasshouse in the '
              'park, warm and wet, with palms, ferns and a banana plant that fruited once.', ['glasshouse',
              'plants', 'warm'], 'free', 'indoor', ALL, DAY),
        place('fernleigh-tennis', 'Fernleigh Lawn Tennis Club', 'fitness', 'fernleigh', 'Grass courts and a '
              'pavilion where manufacturers\' sons and daughters play doubles and flirt.', ['tennis', 'society'],
              '$$', 'outdoor', ['friends', 'date'], ['afternoon'], WARM),
        place('fernleigh-assembly-rooms', 'Fernleigh Assembly Rooms', 'venue', 'fernleigh', 'Subscription balls, '
              'charity bazaars and lectures by visiting explorers.', ['balls', 'society'], '$$$', 'indoor',
              ['friends', 'date'], ['evening']),
        place('museum-of-pneumatics', 'Calderwick Museum of Pneumatics', 'museum', 'moorside', 'The town\'s own '
              'industry museum: the first cash carrier, cutaway compressors and a working tube you can send a '
              'message through.', ['industry', 'machines', 'hands-on'], '$', 'indoor', ALL, DAY),
        place('art-gallery', 'Calderwick Art Gallery and Museum', 'museum', 'moorside', 'Paintings given by mill '
              'owners, stuffed birds, Roman coins from the castle and a mummy nobody can explain.',
              ['art', 'natural-history', 'rainy-day'], 'free', 'indoor', ALL, DAY),
        place('mechanics-library', "Mechanics' Library", 'library', 'moorside', 'The Pennock Institute\'s lending '
              'library of engineering books and trade journals, open to members until nine.', ['books',
              'engineering', 'study'], '$', 'indoor', ['solo'], ['afternoon', 'evening']),
        place('moorside-coffee-room', 'Moorside Coffee Room', 'cafe', 'moorside', 'A cheap coffee room where '
              'students argue over drawings and nurses come off the morning shift.', ['students', 'coffee'],
              '$', 'indoor', ['solo', 'friends', 'date'], ['morning', 'afternoon', 'evening'], cuisine='cafe'),
        place('mooring-mast', 'Ridley Moor mooring mast', 'landmark', 'ridley-moor', 'The iron mast where the mail '
              'airship ties up; people walk up on Tuesdays and Fridays to watch her come in.', ['airship',
              'views'], 'free', 'outdoor', ALL, DAY),
        place('reservoir-walk', 'Ridley reservoirs walk', 'trail', 'ridley-moor', 'A path round the reservoirs and '
              'over the moor, above the smoke, with curlews in spring.', ['walk', 'moorland', 'fresh-air'],
              'free', 'outdoor', ALL, DAY, WARM),
        place('moor-cock-inn', 'The Moor Cock Inn', 'inn', 'ridley-moor', 'A stone inn on the moor road serving ham '
              'and eggs to walkers and the airship crew.', ['inn', 'walkers'], '$', 'indoor', ALL,
              ['afternoon', 'evening'], cuisine='English'),
        place('calder-holme-lido', 'Calder Holme Lido', 'beach', 'calder-holme', 'An open-air bathing pool fed '
              'from the river, cold even in August, with a sand bank and changing huts.', ['swimming',
              'outdoors', 'summer'], '$', 'outdoor', ALL, DAY, ['summer']),
        place('calderwick-velodrome', 'Calderwick Velodrome', 'stadium', 'calder-holme', 'A cinder and timber '
              'cycle track with Saturday races, betting under the stand and a club for lady cyclists.',
              ['cycling', 'races', 'sport'], '$', 'outdoor', ['friends', 'family', 'date'], ['afternoon'], WARM),
        place('holme-pier', 'Holme pleasure pier', 'attraction', 'calder-holme', 'A short pier on the old mill '
              'dam with rowing boats, a penny-in-the-slot machine hall and a whelk stall.', ['pier', 'boating',
              'amusements'], '$', 'outdoor', ALL, ['afternoon', 'evening'], WARM),
    ],
    'colleges': [
        {'id': 'pennock-institute', 'name': 'Pennock Institute of Mechanical Science', 'type': 'technical-institute',
         'neighborhood': 'moorside', 'size': 'medium', 'known_for': ['pneumatics', 'mechanical-engineering',
         'draughtsmanship', 'chemistry', 'evening-classes'], 'source': S},
        {'id': 'school-of-art', 'name': 'Calderwick School of Art', 'type': 'art-school', 'neighborhood': 'moorside',
         'size': 'small', 'known_for': ['design', 'drawing', 'photography', 'pattern-design'], 'source': S},
        {'id': 'infirmary-nursing-school', 'name': 'Royal Infirmary Training School for Nurses',
         'type': 'medical-school', 'neighborhood': 'moorside', 'size': 'small', 'known_for': ['nursing',
         'midwifery'], 'source': S},
        {'id': 'grammar-school', 'name': 'Calderwick Grammar School', 'type': 'academy', 'neighborhood':
         'castle-hill', 'size': 'small', 'known_for': ['latin', 'mathematics', 'scholarships'], 'source': S},
        {'id': 'pupil-teacher-centre', 'name': 'Calderwick Pupil-Teacher Centre', 'type': 'academy',
         'neighborhood': 'hobcroft', 'size': 'small', 'known_for': ['teacher-training', 'elementary-schooling'],
         'source': S},
    ],
    'careers': [
        career('tube-fitter', 'Tube fitter', 'engineering', 'shift-day', '$$', 'Installing and repairing '
               'pneumatic tube runs in shops, banks and offices across town and beyond.', ['ladders and ceilings',
               'customers watching', 'blockages', 'travelling jobs']),
        career('tube-drawer', 'Tube drawer', 'manufacturing', 'rotating', '$', 'Drawing hot and cold metal tube '
               'on the benches of a tube mill, on day and night turns.', ['heat', 'noise', 'piecework',
               'the turn changing']),
        career('boilermaker', 'Boilermaker', 'manufacturing', 'shift-day', '$$', 'Riveting and caulking boiler '
               'plate for engines and compressors.', ['rivet gangs', 'deafness', 'the union', 'apprentices']),
        career('iron-moulder', 'Iron moulder', 'manufacturing', 'shift-day', '$$', 'Making sand moulds and pouring '
               'castings in a foundry.', ['casting days', 'burns', 'skill and pride']),
        career('draughtsman', 'Draughtsman', 'engineering', 'office', '$$', 'Drawing engineering plans in a works '
               'drawing office, with evening classes at the Institute.', ['tracing paper', 'deadlines',
               'the chief draughtsman', 'evening classes']),
        career('mill-hand', 'Mill hand', 'textiles', 'early', '$', 'Minding looms in a worsted shed from six in '
               'the morning, as many young women in town do.', ['looms', 'noise', 'mill friendships',
               'half-holidays']),
        career('canal-boatman', 'Canal boatman', 'transport', 'rotating', '$', 'Working a horse-drawn narrowboat '
               'between the basin and the coast with family aboard.', ['locks', 'the horse', 'weather',
               'long trips']),
        career('lock-keeper', 'Lock-keeper', 'transport', 'early', '$', 'Keeping a canal lock and its cottage, '
               'working the gates for every boat.', ['boats passing', 'gardening', 'solitude']),
        career('railway-signalman', 'Railway signalman', 'transport', 'rotating', '$$', 'Working the levers and '
               'bells in a signal box on eight-hour turns.', ['bells and levers', 'night turns', 'responsibility']),
        career('telegraphist', 'Telegraphist', 'communications', 'rotating', '$$', 'Sending and taking telegrams '
               'at the post office instrument room.', ['morse', 'urgent news', 'night duty']),
        career('tube-post-sorter', 'Tube post sorter', 'communications', 'shift-day', '$', 'Sorting and '
               'dispatching carriers in the town\'s pneumatic post office.', ['carriers', 'jams', 'speed']),
        career('airship-mail-rigger', 'Airship mail rigger', 'transport', 'rotating', '$$', 'Handling lines, gas '
               'bags and mail at the mooring mast and flying as crew on the mail run.', ['heights', 'weather',
               'the mast crew', 'flights to the coast']),
        career('typist', 'Typist', 'clerical', 'office', '$', 'Typing letters and invoices in a works or '
               'merchant\'s office, one of the new jobs open to young women.', ['typewriters', 'office gossip',
               'shorthand']),
        career('office-clerk', 'Clerk', 'clerical', 'office', '$$', 'Keeping ledgers and copying letters in a '
               'counting house or company office.', ['ledgers', 'the senior clerk', 'respectability on little '
               'pay']),
        career('shop-assistant', 'Shop assistant', 'retail', 'shift-day', '$', 'Serving behind the counter in a '
               'store, long hours, living in above the shop.', ['customers', 'the floorwalker', 'late Saturdays']),
        career('infirmary-nurse', 'Infirmary nurse', 'healthcare', 'rotating', '$', 'Ward nursing at the Royal '
               'Infirmary, living in the nurses\' home.', ['ward sister', 'works accidents', 'night duty']),
        career('schoolteacher', 'Board school teacher', 'education', 'academic', '$', 'Teaching a class of sixty in '
               'a board school, mostly children of mill and works families.', ['big classes', 'inspections',
               'clever children']),
        career('institute-lecturer', 'Institute lecturer', 'education', 'academic', '$$', 'Teaching mechanics and '
               'drawing at the Pennock Institute, many classes in the evening.', ['students', 'apparatus',
               'the exhibition']),
        career('music-hall-singer', 'Music hall singer', 'entertainment', 'evening', '$', 'Singing comic and '
               'sentimental songs twice nightly, touring the halls between bookings.', ['the audience',
               'new songs', 'touring', 'stage-door friends']),
        career('union-organiser', 'Union organiser', 'labour', 'flexible', '$', 'Recruiting members and fighting '
               'grievances for the tube workers\' union.', ['meetings', 'masters', 'strike talk', 'hope']),
        career('pastry-cook', 'Pastry cook', 'food', 'early', '$', 'Baking tarts, pies and cakes from four in the '
               'morning for a confectioner and tea room.', ['ovens', 'early starts', 'wedding cakes']),
        career('compositor', 'Compositor', 'press', 'shift-night', '$$', 'Setting type by hand for the morning '
               'paper, through the night.', ['type cases', 'deadlines', 'the press thundering']),
        career('reporter', 'Reporter', 'press', 'flexible', '$$', 'Covering council meetings, police court, '
               'accidents and football for the town paper.', ['notebooks', 'the editor', 'scoops']),
        career('photographer', 'Photographer', 'arts', 'flexible', '$$', 'Taking studio portraits, wedding groups '
               'and works outings.', ['the darkroom', 'sitters', 'glass plates']),
        career('barmaid', 'Bar staff', 'hospitality', 'evening', '$', 'Pulling pints and keeping order in a brewery '
               'tied house.', ['regulars', 'closing time', 'the landlord']),
    ],
    'employers': [
        employer('haworth-pyne', 'Haworth and Pyne Pneumatic Works', 'engineering', 'lowfield', 'large', 'The '
                 'largest firm in town, making and fitting pneumatic dispatch systems for shops, banks and post '
                 'offices across the country.', ['tube-fitter', 'draughtsman', 'office-clerk', 'typist']),
        employer('ingleby-tube-mill', "Ingleby's Drawn Tube Mill", 'manufacturing', 'lowfield', 'large', 'A hot '
                 'and noisy mill drawing copper and steel tube by the mile, worked round the clock.',
                 ['tube-drawer', 'office-clerk']),
        employer('dunmore-brothers', 'Dunmore Brothers Engine and Pump Works', 'manufacturing', 'lowfield',
                 'large', 'Builds the compressors and pumping engines that drive the tube systems, with its own '
                 'boiler shop and foundry.', ['boilermaker', 'iron-moulder', 'draughtsman', 'typist']),
        employer('sugden-mill', 'Sugden and Sons Worsted Mill', 'textiles', 'hobcroft', 'large', 'The old family '
                 'mill on the river, still spinning and weaving worsted with a mostly female workforce.',
                 ['mill-hand', 'office-clerk']),
        employer('navigation-company', 'Calder and Aske Navigation Company', 'transport', 'saltergate-basin',
                 'medium', 'Owns the canal, the basin, the warehouses and the lock cottages, and hires out boats.',
                 ['canal-boatman', 'lock-keeper', 'office-clerk']),
        employer('valley-railway', 'Calder Valley Railway', 'transport', 'station-fields', 'large', 'Runs Central '
                 'station, the goods yards and the valley line.', ['railway-signalman', 'telegraphist',
                 'office-clerk']),
        employer('corporation-gasworks', 'Calderwick Corporation Gasworks', 'municipal', 'saltergate-basin',
                 'medium', 'The municipal gasworks by the basin, lighting the streets and supplying the tube post '
                 'engines.', ['boilermaker', 'office-clerk']),
        employer('royal-infirmary', 'Calderwick Royal Infirmary', 'healthcare', 'moorside', 'large', 'The town '
                 'hospital, paid for by subscription and works collections, busy with works accidents.',
                 ['infirmary-nurse', 'office-clerk']),
        employer('calderwick-examiner', 'The Calderwick Examiner', 'press', 'exchange-quarter', 'medium', 'The '
                 'daily paper, Liberal in politics, printed overnight behind its Exchange Street office.',
                 ['compositor', 'reporter', 'typist']),
        employer('pennock-institute-staff', 'Pennock Institute', 'education', 'moorside', 'medium', 'The '
                 'engineering institute founded by a pump maker, teaching day and evening classes.',
                 ['institute-lecturer', 'office-clerk']),
        employer('tube-post-office', 'Calderwick Pneumatic and Telegraph Office', 'communications',
                 'exchange-quarter', 'medium', 'The post office instrument room and the hub of the town\'s '
                 'pneumatic post.', ['telegraphist', 'tube-post-sorter']),
        employer('ridley-air-mail', 'Ridley Moor Air Mail Company', 'transport', 'ridley-moor', 'small', 'Runs the '
                 'single mail airship and its mast crew.', ['airship-mail-rigger', 'office-clerk']),
        employer('wright-battersby-store', 'Wright and Battersby', 'retail', 'exchange-quarter', 'medium', 'The '
                 'department store, with live-in assistants and a counting house fed by cash tubes.',
                 ['shop-assistant', 'office-clerk', 'pastry-cook']),
        employer('whiteleys', "Whiteley's Confectioners", 'food', 'market-place', 'small', 'A confectioner and tea '
                 'room baking for weddings, funerals and Saturday afternoons.', ['pastry-cook', 'shop-assistant']),
        employer('school-board', 'Calderwick School Board', 'education', 'hobcroft', 'large', 'Runs the board '
                 'schools in the terraces and Paradise.', ['schoolteacher']),
        employer('tube-workers-union', "Amalgamated Society of Tube Workers", 'labour', 'hobcroft', 'small',
                 'The union of tube drawers and fitters, meeting upstairs at Hope Street.', ['union-organiser']),
        employer('thornbers', "Thornber's Varieties", 'entertainment', 'station-fields', 'small', 'The music hall '
                 'and its company of turns.', ['music-hall-singer', 'barmaid']),
        employer('ackworth-brewery', "Ackworth's Calder Brewery", 'hospitality', 'ings-end', 'medium', 'The local '
                 'brewery and its tied pubs across the valley.', ['barmaid', 'office-clerk']),
        employer('fothergill-studio', "Fothergill's Photographic Studio", 'arts', 'exchange-quarter', 'small',
                 'A portrait studio with a glass roof and painted backdrops.', ['photographer']),
    ],
    'career_hubs': [
        {'id': 'lowfield-works', 'name': 'Lowfield works', 'neighborhoods': ['lowfield', 'hobcroft'],
         'sectors': ['engineering', 'manufacturing', 'textiles', 'labour'], 'summary': 'The tube mills, pump works, '
         'foundries and the worsted shed along the river.', 'source': S},
        {'id': 'exchange-offices', 'name': 'Exchange Quarter offices and shops', 'neighborhoods':
         ['exchange-quarter', 'market-place'], 'sectors': ['clerical', 'retail', 'press', 'communications', 'food',
         'arts'], 'summary': 'Banks, merchants\' counting houses, the newspaper, the post office and the shops.',
         'source': S},
        {'id': 'basin-and-railway', 'name': 'Basin and railway', 'neighborhoods': ['saltergate-basin',
         'station-fields', 'ridley-moor'], 'sectors': ['transport', 'municipal', 'hospitality', 'entertainment'],
         'summary': 'The canal basin, gasworks, station yards, music hall and the airship mast.', 'source': S},
        {'id': 'moorside-institutions', 'name': 'Moorside institutions', 'neighborhoods': ['moorside'],
         'sectors': ['healthcare', 'education'], 'summary': 'The Infirmary, the Pennock Institute and the art '
         'school.', 'source': S},
    ],
    'climate': {
        'summary': 'Cool and wet Pennine weather: mild summers, long grey winters, rain in every month and '
                   'smoke fogs in the valley bottom on still winter days.',
        'months': [
            month(43, 34, 17, 'Raw and dark; smoke fogs sit in Lowfield for days.'),
            month(44, 34, 15, 'Cold, with sleet and snow on the moor.'),
            month(48, 36, 15, 'Wind and showers; the first light evenings.'),
            month(53, 39, 13, 'Bright spells, curlews back on the moor.'),
            month(59, 44, 13, 'Mild; washing dries outside again.'),
            month(64, 49, 13, 'Long light evenings and the smoke lifts.'),
            month(67, 53, 13, 'Warmest month; the lido opens fully.'),
            month(66, 52, 14, 'Warm but showery; wakes week.'),
            month(61, 48, 14, 'Fresh mornings and mellow afternoons.'),
            month(54, 43, 17, 'Wet and windy; fires lit again.'),
            month(47, 38, 17, 'Dark by half past four; fog returns.'),
            month(44, 35, 17, 'Cold and grey; the worst smog of the year.'),
        ],
        'source': S,
    },
    'annual_events': [
        event('mast-day', 'Mast Day', [4], 'ridley-moor', 'Crowds walk up the moor to see the mail airship come '
              'back from her winter overhaul and take the first bags of the year.'),
        event('whit-walks', 'Whit Walks', [5, 6], 'market-place', 'Sunday schools and chapels march through town '
              'behind banners and bands, children in new clothes, then tea and races in the park.'),
        event('canal-regatta', 'Saltergate canal regatta', [6], 'saltergate-basin', 'Rowing, sculling and '
              'decorated-boat races on the basin, with a greasy pole and a boatmen\'s tug of war.'),
        event('infirmary-gala', 'Infirmary Sunday gala', [7], 'ackroyd-park', 'Band concerts and a procession in '
              'Ackroyd Park collecting for the Royal Infirmary.'),
        event('institute-exhibition', 'Pennock Institute exhibition', [7], 'moorside', 'Students show engines, '
              'models and drawings, and the firms come looking for apprentices.'),
        event('wakes-week', 'Calder Wakes Week', [8], None, 'The works and mills shut for a week; the town empties '
              'to the seaside and those who stay crowd the lido and the pier.'),
        event('velodrome-championship', 'Valley cycling championship', [9], 'calder-holme', 'The big race meeting '
              'of the season at the velodrome, with bookmakers under the stand and a band between heats.'),
        event('charter-fair', 'Calderwick Charter Fair', [10], 'market-place', 'The old market charter fair: '
              'steam roundabouts, coconut shies, brandy snap stalls and a hiring of farm servants on the first '
              'day.'),
        event('bonfire-night', 'Bonfire Night', [11], 'hobcroft', 'Every street in the terraces builds a bonfire on '
              'the fifth, with parkin, toffee and treacle.'),
        event('lantern-procession', 'Lantern procession', [12], 'castle-hill', 'Children and choirs carry paper '
              'lanterns up Kirkgate to the castle on the shortest day, ending with carols at St Wilfrid\'s.'),
        event('pantomime-season', 'Pantomime season', [12, 1], 'market-place', 'The Theatre Royal pantomime runs '
              'from Boxing Day, with works outings booking whole rows.'),
    ],
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
