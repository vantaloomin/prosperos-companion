"""Curated Jeju data. Run `python scripts/world/jeju.py` to rewrite the shipped JSON."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'cities' / 'jeju.json'
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


def employer(id, name, sector, hood, size, summary, careers):
    return {'id': id, 'name': name, 'sector': sector, 'neighborhood': hood, 'size': size, 'summary': summary,
            'careers': careers, 'source': S}


def event(id, name, months, hood, summary):
    return {'id': id, 'name': name, 'months': months, 'neighborhood': hood, 'summary': summary, 'source': S}


def color(id, name, kind, summary, places=(), seasons=()):
    return {'id': id, 'name': name, 'kind': kind, 'summary': summary, 'places': list(places),
            'seasons': list(seasons), 'source': S}


def price(id, item, low, high, per=''):
    return {'id': id, 'item': item, 'low': low, 'high': high, 'per': per, 'source': S}


def won(low, high):
    """A monthly rent range in thousands of won."""
    return [low * 1000, high * 1000]


ALL = ['solo', 'friends', 'date', 'family']
ADULT = ['solo', 'friends', 'date']
DAY = ['morning', 'afternoon']
DAYTIME = ['morning', 'afternoon', 'evening']
DINNER = ['evening']
NIGHT = ['evening', 'late']
LUNCH = ['afternoon', 'evening']
WARM = ['spring', 'summer', 'fall']
SURF = ['summer', 'fall']
CITY_BUS = ['island-bus', 'express-bus', 'taxi']
TOWN_BUS = ['island-bus', 'express-bus', 'taxi', 'rental-car']
VILLAGE = ['island-bus', 'taxi', 'rental-car']

CITY = {
    'schema_version': 1, 'id': 'jeju', 'name': 'Jeju', 'region': 'Jeju Province', 'country': 'South Korea',
    'timezone': 'Asia/Seoul',
    'aliases': ['Jeju Island', 'Jejudo', 'Jeju-do', 'Jeju-si', 'Jeju City', 'Cheju', 'Cheju-do', 'Seogwipo',
                'Jeju Special Self-Governing Province', 'Jeju, South Korea'],
    'summary': 'South Korea\'s volcanic island province, taken here as one city: Jeju City on the north coast, '
               'Seogwipo on the south and the beach and farming towns around the shore, under Hallasan. Known '
               'for black pork, tangerines, women divers, oreum hikes, the Olle trails and endless ocean-view '
               'cafes.',
    'lat': 33.38, 'lon': 126.55,
    'currency': {'code': 'KRW', 'symbol': '₩', 'name': 'South Korean won'},
    'speeds': {'walk': 4.5, 'car': 40, 'rideshare': 38, 'bus': 22, 'ferry': 15, 'bike-share': 14},
    # Islanders are overwhelmingly Korean (the anglo group draws local, here Korean, names); a small share of
    # Chinese and other East Asian residents work in tourism, hotels and the duty-free trade.
    'names': {'mix': {'anglo': 1, 'east-asian': 0.04}},
    'sources': {
        S: {'kind': 'curated', 'title': 'Jeju places and neighborhoods written for Prospero Companion',
            'license': 'CC0-1.0', 'retrieved': '2026-10-10',
            'note': 'Well-known public places, institutions and employers from general knowledge, covering the '
                    'whole island: Jeju City, Seogwipo and the coastal and inland towns people treat as parts of '
                    'it. Where a street holds many small shops (black pork restaurants, beach cafes, noraebang) '
                    'the record describes the strip rather than naming one business. Businesses open and close '
                    'and rents move: treat this as a snapshot for fiction. Korean leases usually mean a large '
                    'deposit (jeonse, or wolse with a smaller deposit plus monthly rent); rents here are rounded '
                    'monthly wolse estimates for a modest deposit, not listings. Names use Revised Romanization. '
                    'Coordinates are approximate area centers.'},
        CLIMATE: {'kind': 'curated', 'title': 'Approximate monthly climate for Jeju City',
                  'license': 'CC0-1.0', 'retrieved': '2026-10-10',
                  'note': 'Rounded values in line with Korea Meteorological Administration 1991-2020 normals for '
                          'Jeju City; Seogwipo on the south coast runs a degree or two warmer in winter and '
                          'Hallasan is far colder and snowier. Rain days count days with measurable rain or snow.'},
    },
    'neighborhoods': [
        hood('old-jeju', 'Old Jeju City (Wondosim)', 'The historic heart of Jeju City around Gwandeokjeong '
             'pavilion and Dongmun Market: low concrete blocks, an underground arcade, noodle and black pork '
             'streets and an older crowd.', ['historic', 'markets', 'food', 'central'], 33.511, 126.526, 'low',
             (won(400, 650), won(550, 850), won(800, 1300)), ['one-room', 'villa', 'apartment'], 'high', CITY_BUS),
        hood('tapdong', 'Tapdong and the Jeju Port seafront', 'The seawall promenade, Tapdong Square, the ferry '
             'port and Sarabong peak, with raw-fish restaurants, hotels and a waterfront festival ground.',
             ['waterfront', 'nightlife', 'touristy', 'sunsets'], 33.518, 126.535, 'mid',
             (won(450, 700), won(650, 950), won(1000, 1600)), ['one-room', 'officetel', 'apartment'], 'high',
             CITY_BUS),
        hood('ido', 'Ido and City Hall', 'Busy residential blocks around Jeju City Hall, where the streets '
             'behind the hall fill with student bars, study cafes, PC bangs and late-night snack shops.',
             ['students', 'nightlife', 'residential', 'central'], 33.500, 126.532, 'mid',
             (won(400, 650), won(600, 900), won(1000, 1600)), ['one-room', 'villa', 'apartment'], 'high', CITY_BUS),
        hood('sinjeju', 'Sinjeju (Yeon-dong and Nohyeong)', 'The newer downtown planned in the 1980s: the '
             'provincial government, duty-free stores, Jeju Dream Tower, Nuwemaru Street\'s bars and the most '
             'apartment towers on the island.', ['business', 'shopping', 'nightlife', 'high-rise'], 33.487, 126.487,
             'high', (won(550, 850), won(800, 1200), won(1300, 2200)), ['officetel', 'apartment', 'one-room'],
             'high', CITY_BUS + ['airport-limousine']),
        hood('ara', 'Ara and Jeju National University', 'The inland university district on the slope up toward '
             'Hallasan: the national university and its hospital, student one-rooms, new apartment complexes and '
             'the Jeju Science Park tech campus.', ['students', 'academic', 'leafy', 'new-build'], 33.458, 126.560,
             'mid', (won(380, 600), won(550, 850), won(1000, 1600)), ['one-room', 'student-housing', 'apartment'],
             'medium', CITY_BUS),
        hood('airport', 'Yongdam, Dodu and the airport', 'The coast either side of Jeju International Airport: '
             'Yongduam rock, the Yongdam coastal road\'s plane-spotting cafes, rainbow seawalls at Dodu and Iho '
             'Tewoo beach.', ['waterfront', 'cafes', 'airport', 'sunsets'], 33.510, 126.495, 'mid',
             (won(500, 750), won(700, 1000), won(1100, 1700)), ['one-room', 'villa', 'apartment'], 'medium',
             CITY_BUS + ['airport-limousine', 'rental-car']),
        hood('aewol', 'Aewol', 'The cafe coast west of the city: a cliff path lined with ocean-view cafes, '
             'Gwakji beach, pensions and holiday rentals, and the grassy oreum inland where the fire festival is '
             'held.', ['cafes', 'coastal', 'trendy', 'touristy'], 33.463, 126.312, 'high',
             (won(550, 850), won(800, 1150), won(1200, 2000)), ['villa', 'detached-house', 'pension'], 'low',
             TOWN_BUS),
        hood('hallim', 'Hallim', 'A working harbour town on the northwest coast with a five-day market, fishing '
             'boats, the ferry to Biyangdo and quiet farm villages climbing inland.', ['harbour', 'local', 'quiet',
             'affordable'], 33.413, 126.266, 'low', (won(380, 600), won(550, 800), won(800, 1300)),
             ['villa', 'detached-house', 'stone-house'], 'low', TOWN_BUS),
        hood('hyeopjae', 'Hyeopjae and Geumneung beaches', 'Two shallow, glass-green beaches facing Biyangdo, '
             'beside Hallim Park, with guesthouses, beach cafes and a summer crowd.', ['beach', 'touristy',
             'summer', 'cafes'], 33.394, 126.240, 'mid', (won(450, 750), won(650, 950), won(1000, 1600)),
             ['pension', 'villa', 'stone-house'], 'medium', TOWN_BUS),
        hood('hamdeok', 'Hamdeok', 'A turquoise beach and Seoubong peak half an hour east of the city, with '
             'big glass cafes, seafood restaurants and a growing number of apartments for commuters.',
             ['beach', 'cafes', 'family', 'coastal'], 33.543, 126.669, 'mid',
             (won(450, 750), won(650, 950), won(1000, 1600)), ['villa', 'apartment', 'pension'], 'medium',
             TOWN_BUS),
        hood('gimnyeong', 'Gimnyeong and Woljeong-ri', 'Stone-walled fishing villages on the northeast coast '
             'whose white-sand beaches turned into a strip of surf shops and beach cafes, near the Manjanggul '
             'lava tube.', ['beach', 'surf', 'cafes', 'village'], 33.556, 126.775, 'mid',
             (won(450, 750), won(650, 950), won(950, 1500)), ['stone-house', 'detached-house', 'pension'], 'low',
             TOWN_BUS),
        hood('gujwa', 'Sehwa, Hado and Jongdal (Gujwa)', 'The haenyeo coast: diving villages, the Jeju Haenyeo '
             'Museum, a five-day market at Sehwa, and oreum and forest inland.', ['haenyeo', 'village', 'coastal',
             'quiet'], 33.522, 126.860, 'low', (won(380, 620), won(550, 850), won(800, 1300)),
             ['stone-house', 'detached-house', 'villa'], 'low', TOWN_BUS),
        hood('seongsan', 'Seongsan', 'The eastern tip under Seongsan Ilchulbong (Sunrise Peak): tour buses by '
             'day, galchi and black pork restaurants, Seopjikoji\'s headland and the ferry port for Udo.',
             ['touristy', 'harbour', 'sunrise', 'coastal'], 33.462, 126.932, 'low',
             (won(400, 650), won(550, 850), won(800, 1300)), ['villa', 'detached-house', 'pension'], 'medium',
             TOWN_BUS + ['udo-ferry']),
        hood('udo', 'Udo', 'A small cow-shaped island fifteen minutes by ferry from Seongsan: coral-sand '
             'beaches, peanut fields, haenyeo and electric scooters full of day visitors.', ['island', 'beach',
             'village', 'touristy'], 33.505, 126.953, 'low', (won(350, 550), won(500, 750), won(700, 1100)),
             ['stone-house', 'detached-house'], 'medium', ['udo-ferry']),
        hood('pyoseon', 'Pyoseon', 'A wide, shallow southeast beach beside the Jeju Folk Village, with resort '
             'hotels, seafood restaurants and the thatched Seongeup village inland.', ['beach', 'folk', 'quiet',
             'family'], 33.326, 126.836, 'low', (won(350, 600), won(500, 800), won(750, 1200)),
             ['detached-house', 'villa', 'stone-house'], 'low', TOWN_BUS),
        hood('namwon', 'Namwon and Wimi', 'Tangerine country on the south coast: orchards behind black stone '
             'walls and windbreak trees, camellia gardens, farm cafes and the Keunyeong cliff path.',
             ['farms', 'tangerines', 'quiet', 'coastal'], 33.279, 126.718, 'low',
             (won(350, 580), won(500, 780), won(750, 1200)), ['detached-house', 'stone-house', 'villa'], 'low',
             VILLAGE),
        hood('seogwipo', 'Seogwipo old town', 'The south-coast city center above its harbour: Maeil Olle Market, '
             'Lee Jung-seop Street, waterfalls a short walk from the bus terminal and Saeseom islet.',
             ['historic', 'markets', 'waterfalls', 'arts'], 33.249, 126.562, 'mid',
             (won(400, 650), won(580, 880), won(900, 1400)), ['one-room', 'villa', 'apartment'], 'high',
             TOWN_BUS + ['airport-limousine']),
        hood('new-seogwipo', 'New Seogwipo, Gangjeong and Beophwan', 'The newer half of Seogwipo west of the '
             'old town: apartment blocks around the World Cup stadium, Oedolgae rock, the Beophwan haenyeo '
             'village and Yakcheonsa temple.', ['residential', 'coastal', 'sports', 'family'], 33.247, 126.510,
             'mid', (won(450, 700), won(650, 950), won(1000, 1600)), ['apartment', 'villa', 'one-room'], 'medium',
             TOWN_BUS + ['airport-limousine']),
        hood('jungmun', 'Jungmun Resort', 'The planned resort zone on the south coast: big hotels, the '
             'convention center, Jungmun Saekdal surf beach, waterfalls, gardens and columnar-joint cliffs.',
             ['resort', 'beach', 'touristy', 'upscale'], 33.248, 126.412, 'high',
             (won(550, 850), won(800, 1200), won(1200, 2000)), ['officetel', 'villa', 'apartment'], 'medium',
             TOWN_BUS + ['airport-limousine']),
        hood('daejeong', 'Daejeong and Moseulpo', 'The windy southwest: Moseulpo harbour\'s yellowtail '
             'restaurants, Songaksan and Sanbangsan, wartime sites on the Alddreu airfield, the ferries to Gapado '
             'and Marado, and the international schools of Global Education City inland.',
             ['harbour', 'windy', 'history', 'schools'], 33.218, 126.252, 'mid',
             (won(420, 680), won(650, 1000), won(1100, 2000)), ['villa', 'apartment', 'detached-house'], 'low',
             TOWN_BUS + ['island-ferries']),
        hood('foothills', 'Bonggae, Gyorae and the Hallasan foothills', 'Forest and pasture on the slopes east '
             'of Hallasan: the April 3rd Peace Park, cedar forests, Saryeoni path, the Seongpanak trailhead and '
             'the native-chicken restaurants of Gyorae.', ['forest', 'hiking', 'quiet', 'history'], 33.440, 126.640,
             'mid', (won(450, 700), won(650, 950), won(1000, 1600)), ['detached-house', 'villa', 'townhouse'],
             'low', VILLAGE),
        hood('gasi', 'Gasi-ri and the eastern ranchland', 'Open grassland, horse ranches and soft oreum in '
             'inland Pyoseon-myeon, where the Noksan-ro road turns yellow with canola in spring and the hills '
             'silver with eulalia grass in autumn.', ['ranches', 'oreum', 'rural', 'quiet'], 33.365, 126.745,
             'low', (won(330, 520), won(480, 720), won(700, 1100)), ['detached-house', 'stone-house'], 'low',
             VILLAGE),
    ],
    'transit': [
        line('island-bus', 'Jeju island bus network', 'bus', 'Blue trunk and green local buses covering both '
             'cities and every coastal village, with cheap flat fares and free transfers within 40 minutes by '
             'card; slow in the countryside and thin late at night.'),
        line('express-bus', 'Red express buses', 'bus', 'Limited-stop red buses linking the airport and Jeju '
             'City with Seogwipo, Jungmun, Seongsan, Pyoseon and the west coast over the cross-island roads.'),
        line('airport-limousine', 'Airport Limousine Bus 600', 'bus', 'Coach-style buses from the airport to '
             'the Jungmun resort hotels and Seogwipo, with room for luggage.'),
        line('udo-ferry', 'Udo ferry', 'ferry', 'Car ferries from Seongsan port to Udo\'s two harbours every '
             'half hour or so in daylight; a fifteen-minute crossing that stops in high winds.'),
        line('island-ferries', 'Gapado and Marado ferries', 'ferry', 'Small passenger boats from Moseulpo\'s '
             'Unjin port and the Songaksan pier to Gapado and Marado, the southernmost point of Korea; '
             'often cancelled in rough seas.'),
        line('taxi', 'Taxis (hailed or by app)', 'rideshare', 'Taxis are cheap by Western standards and most '
             'are called by app; in the countryside they can take a while to arrive and fewer run late.'),
        line('rental-car', 'Rental cars', 'car', 'Most visitors and many residents drive: rental lots crowd the '
             'roads near the airport and most beaches, oreum and farm cafes are hard to reach any other way.'),
        line('rental-bikes', 'Rental bikes and the round-island bike path', 'bike-share', 'Bikes and e-bikes '
             'hired by the day from shops in the towns, and a signed cycle route of about 230 km around the '
             'coast, ridden over three or four days with certification booths along the way.'),
    ],
    'places': [
        # Old Jeju City.
        place('dongmun-market', 'Dongmun Market', 'market', 'old-jeju', 'Jeju\'s oldest permanent market: '
              'stalls of hairtail, abalone, tangerines and omegi rice cakes by day, and a night market of '
              'black pork skewers, tangerine juice and fried snacks after dark.', ['food', 'night-market',
              'tangerines', 'iconic'], '$', 'mixed', ALL, ['morning', 'afternoon', 'evening']),
        place('gwandeokjeong', 'Gwandeokjeong Pavilion and Jeju Mokgwana', 'landmark', 'old-jeju', 'A '
              'fifteenth-century pavilion and the rebuilt compound of the old Jeju governor\'s office, with dol '
              'hareubang at the gate.', ['history', 'joseon', 'quiet'], '$', 'outdoor', ALL, DAY),
        place('samseonghyeol', 'Samseonghyeol', 'landmark', 'old-jeju', 'The shrine around three holes in the '
              'ground where, in the island\'s founding myth, the first ancestors of the Go, Yang and Bu clans '
              'rose from the earth.', ['myth', 'history', 'garden'], '$', 'outdoor', ALL, DAY),
        place('jeju-folklore-museum', 'Jeju Folklore and Natural History Museum', 'museum', 'old-jeju',
              'Displays on volcanic geology, sea life, thatched houses, haenyeo gear and island rituals beside '
              'Sinsan Park.', ['history', 'nature', 'rainy-day', 'kids'], '$', 'indoor', ALL, DAY),
        place('chilseong-ro', 'Chilseong-ro shopping street', 'shopping', 'old-jeju', 'The old downtown '
              'shopping street under an arched roof, with clothing, cosmetics and shoe shops.', ['shopping',
              'covered', 'old-school'], '$$', 'mixed', ['solo', 'friends', 'date'], ['afternoon', 'evening']),
        place('jungang-underground-mall', 'Jungang underground shopping arcade', 'shopping', 'old-jeju', 'A long '
              'tunnel of small clothing, phone-case and accessory shops under the Jungang rotary, handy on rainy '
              'days.', ['shopping', 'rainy-day', 'cheap'], '$', 'indoor', ['solo', 'friends'], DAYTIME),
        place('black-pork-street', 'Black pork street', 'restaurant', 'old-jeju', 'A row of barbecue '
              'restaurants grilling thick slabs of Jeju black pork over charcoal, dipped in bubbling anchovy '
              'sauce, with soju on every table.', ['black-pork', 'bbq', 'soju', 'groups'], '$$', 'indoor',
              ['friends', 'family', 'date', 'coworkers'], DINNER, cuisine='korean'),
        place('noodle-street', 'Guksu Munhwa Geori (Noodle Street)', 'restaurant', 'old-jeju', 'A stretch near '
              'Samseonghyeol of gogi-guksu shops ladling thick wheat noodles into pork-bone broth topped with '
              'sliced boiled pork.', ['gogi-guksu', 'noodles', 'cheap-eats', 'lunch'], '$', 'indoor', ALL,
              ['morning', 'afternoon', 'evening'], cuisine='korean'),
        place('old-town-cafes', 'Old-town cafes in converted houses', 'cafe', 'old-jeju', 'Small cafes in '
              'renovated 1970s houses and tangerine warehouses on the lanes around Gwandeokjeong, many with '
              'hallabong drinks.', ['coffee', 'quiet', 'retro'], '$', 'indoor', ['solo', 'friends', 'date'],
              DAYTIME),
        place('sanjicheon', 'Sanjicheon stream', 'park', 'old-jeju', 'A stone-banked stream running down to the '
              'harbour through the old town, lit up at night with a walking path and stepping stones.', ['walk',
              'night-lights', 'free'], 'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('old-town-jjimjilbang', 'Old-town jjimjilbang and bathhouse', 'fitness', 'old-jeju', 'A '
              'neighborhood bathhouse with hot and cold pools, scrub attendants and a heated floor upstairs for '
              'napping in matching cotton outfits.', ['sauna', 'spa', 'late-night'], '$', 'indoor',
              ['solo', 'friends', 'family'], ['morning', 'afternoon', 'evening', 'late']),
        place('dongmun-pocha', 'Dongmun pojangmacha', 'bar', 'old-jeju', 'Tented street bars and tiny pubs '
              'near the market serving soju, makgeolli, grilled fish and spicy stews until late.',
              ['soju', 'pocha', 'late-night'], '$', 'mixed', ['friends', 'date', 'coworkers'], NIGHT),
        # Tapdong and the port.
        place('tapdong-promenade', 'Tapdong seafront promenade', 'park', 'tapdong', 'A long seawall walk and '
              'square where families skate, people fish and the city comes to watch the sunset over the harbour.',
              ['waterfront', 'walk', 'sunset', 'free'], 'free', 'outdoor', ALL, ['afternoon', 'evening', 'late']),
        place('sarabong', 'Sarabong Peak', 'trail', 'tapdong', 'A small volcanic cone behind the port with a '
              'pavilion at the top, a fifteen-minute climb known for sunsets over the harbour.', ['oreum',
              'sunset', 'views', 'short-hike'], 'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('jeju-national-museum', 'Jeju National Museum', 'museum', 'tapdong', 'The national museum\'s '
              'island branch: Tamna kingdom relics, Joseon maps and the history of the island\'s trade.',
              ['history', 'free', 'rainy-day'], 'free', 'indoor', ALL, DAY),
        place('kim-man-deok-hall', 'Kim Man-deok Memorial Hall', 'museum', 'tapdong', 'A museum honouring the '
              'eighteenth-century Jeju merchant who spent her fortune buying grain for the island during a famine.',
              ['history', 'free', 'rainy-day'], 'free', 'indoor', ALL, DAY),
        place('tapdong-raw-fish', 'Tapdong raw-fish restaurants', 'restaurant', 'tapdong', 'Seafront '
              'restaurants with tanks of flatfish, rockfish and abalone out front, served as hoe with lettuce, '
              'garlic and a spicy fish stew to finish.', ['seafood', 'hoe', 'groups'], '$$$', 'indoor',
              ['friends', 'family', 'date', 'coworkers'], DINNER, cuisine='korean'),
        place('tapdong-cafes', 'Tapdong seafront cafes', 'cafe', 'tapdong', 'Franchise and independent cafes '
              'with second-floor windows over the seawall.', ['coffee', 'sea-view'], '$$', 'indoor',
              ['solo', 'friends', 'date'], DAYTIME),
        place('tapdong-pubs', 'Tapdong chicken-and-beer pubs', 'bar', 'tapdong', 'Hof bars near the square '
              'serving fried chicken and draft beer, with outdoor tables in summer.', ['chimaek', 'beer',
              'groups'], '$$', 'mixed', ['friends', 'coworkers', 'date'], NIGHT, cuisine='korean'),
        place('woodang-library', 'Woodang Library', 'library', 'tapdong', 'A public library on the slope of '
              'Sarabong with reading rooms students fill during exam season.', ['books', 'study', 'quiet'], 'free',
              'indoor', ['solo', 'family'], DAYTIME),
        # Ido and City Hall.
        place('city-hall-bars', 'Bars behind Jeju City Hall', 'nightlife', 'ido', 'The island\'s busiest student '
              'nightlife: lanes of pubs, cheap soju bars, karaoke and late snack shops behind City Hall.',
              ['students', 'soju', 'late-night', 'groups'], '$', 'indoor', ['friends', 'coworkers', 'date'],
              NIGHT),
        place('ido-noraebang', 'Ido noraebang rooms', 'nightlife', 'ido', 'Private karaoke rooms rented by the '
              'hour, with tambourines, a big song book and coin booths for two.', ['karaoke', 'groups',
              'late-night'], '$', 'indoor', ['friends', 'date', 'coworkers'], NIGHT),
        place('ido-pc-bang', 'Ido PC bangs', 'nightlife', 'ido', 'Round-the-clock gaming rooms with fast PCs, '
              'ramyeon and fried rice ordered to your seat.', ['games', 'late-night', 'pc-bang'], '$', 'indoor',
              ['solo', 'friends'], ['afternoon', 'evening', 'late']),
        place('ido-study-cafes', 'Study cafes around City Hall', 'cafe', 'ido', 'Coffee shops and hourly study '
              'cafes full of students and job seekers with laptops.', ['coffee', 'study', 'quiet'], '$', 'indoor',
              ['solo', 'friends'], ['morning', 'afternoon', 'evening', 'late']),
        place('haejangguk-shops', 'Haejangguk breakfast shops', 'restaurant', 'ido', 'Early-opening shops '
              'serving Jeju-style hangover soup of beef, bean sprouts and congealed blood, a habit of shift '
              'workers and the morning after.', ['breakfast', 'soup', 'hangover'], '$', 'indoor',
              ['solo', 'friends', 'coworkers'], ['morning', 'afternoon'], cuisine='korean'),
        place('sinsan-park', 'Sinsan Park', 'park', 'ido', 'A big green park of pine and cherry trees between '
              'the old town and City Hall, with a walking loop and outdoor exercise machines.', ['walk',
              'cherry-blossom', 'free'], 'free', 'outdoor', ALL, DAYTIME),
        place('ido-gyms', 'Ido neighborhood gyms', 'fitness', 'ido', 'Health clubs above shops with monthly '
              'passes, a weights floor and group spin or pilates classes.', ['gym', 'pilates'], '$$', 'indoor',
              ['solo', 'friends'], ['morning', 'evening', 'late']),
        place('ido-chicken', 'Ido fried-chicken and tteokbokki shops', 'restaurant', 'ido', 'Small shops doing '
              'fried chicken, tteokbokki and gimbap for delivery and eat-in, open late.', ['chicken', 'cheap-eats',
              'delivery'], '$', 'indoor', ['solo', 'friends', 'family'], ['afternoon', 'evening', 'late'],
              cuisine='korean'),
        # Sinjeju.
        place('nuwemaru-street', 'Nuwemaru Street', 'nightlife', 'sinjeju', 'A pedestrian street of bars, '
              'clubs, karaoke, cosmetics shops and late barbecue in Yeon-dong, busy with young locals and '
              'visitors.', ['nightlife', 'karaoke', 'shopping'], '$$', 'mixed', ['friends', 'date', 'coworkers'],
              NIGHT),
        place('baojian-street', 'Baojian Street', 'shopping', 'sinjeju', 'A Yeon-dong street of restaurants, '
              'cosmetics and souvenir shops with signs in Korean and Chinese, built around tour groups.',
              ['shopping', 'chinese', 'cosmetics'], '$$', 'outdoor', ['solo', 'friends', 'date'],
              ['afternoon', 'evening']),
        place('dream-tower', 'Jeju Dream Tower', 'attraction', 'sinjeju', 'The island\'s tallest building: a '
              'Grand Hyatt hotel, a foreigners-only casino, shopping, restaurants and a rooftop lounge looking '
              'over the city to Hallasan.', ['views', 'hotel', 'shopping', 'rooftop'], '$$$', 'indoor',
              ['friends', 'date', 'family'], ['afternoon', 'evening', 'late']),
        place('nexon-computer-museum', 'Nexon Computer Museum', 'museum', 'sinjeju', 'A museum of computers, '
              'consoles and Korean online games, with a floor of playable machines.', ['games', 'tech',
              'rainy-day', 'kids'], '$$', 'indoor', ALL, DAY),
        place('halla-arboretum', 'Halla Arboretum', 'garden', 'sinjeju', 'A free arboretum at the edge of '
              'Sinjeju with native trees, a bamboo grove, greenhouses and a short oreum trail locals walk after '
              'work.', ['nature', 'walk', 'free'], 'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('shilla-duty-free', 'Shilla Duty Free Jeju', 'shopping', 'sinjeju', 'A large duty-free store for '
              'cosmetics, luxury goods and liquor, busy with Chinese and domestic tour groups.', ['duty-free',
              'cosmetics', 'luxury'], '$$$', 'indoor', ['solo', 'friends'], DAY),
        place('emart-sinjeju', 'E-Mart Sinjeju', 'shopping', 'sinjeju', 'A big-box hypermarket for groceries, '
              'household goods and island souvenirs at supermarket prices.', ['groceries', 'souvenirs'], '$',
              'indoor', ALL, DAYTIME),
        place('sinjeju-bbq', 'Yeon-dong black pork barbecue', 'restaurant', 'sinjeju', 'Busy barbecue '
              'restaurants for after-work black pork, galbi and cold noodles, with long waits on Fridays.',
              ['black-pork', 'bbq', 'groups'], '$$', 'indoor', ['friends', 'family', 'coworkers', 'date'],
              DINNER, cuisine='korean'),
        place('sinjeju-cafes', 'Sinjeju dessert cafes', 'cafe', 'sinjeju', 'Bakeries and dessert cafes with '
              'hallabong cakes, injeolmi bingsu and large window seats.', ['coffee', 'dessert', 'bingsu'], '$$',
              'indoor', ['solo', 'friends', 'date'], DAYTIME),
        place('sinjeju-24h-gyms', 'Sinjeju 24-hour gyms', 'fitness', 'sinjeju', 'Big health clubs with '
              'weights, cardio, pilates studios and personal trainers, open around the clock.', ['gym',
              'personal-training', 'pilates'], '$$', 'indoor', ['solo', 'friends'],
              ['morning', 'afternoon', 'evening', 'late']),
        place('jeju-sports-complex', 'Jeju Sports Complex', 'fitness', 'sinjeju', 'The city\'s public sports '
              'park with a running track, swimming pool, gyms and courts; joggers circle it at dawn.', ['running',
              'swimming', 'public'], '$', 'mixed', ALL, ['morning', 'afternoon', 'evening']),
        place('halla-library', 'Halla Library', 'library', 'sinjeju', 'The island\'s big public library on the '
              'edge of Ora, with reading rooms, a children\'s floor and a lawn.', ['books', 'study', 'quiet'],
              'free', 'indoor', ['solo', 'family'], DAYTIME),
        # Ara and Jeju National University.
        place('jnu-cherry-road', 'Jeju National University cherry road', 'park', 'ara', 'The entrance road to '
              'the national university, a tunnel of king cherry blossoms for a week or two in spring and a '
              'shady walk the rest of the year.', ['cherry-blossom', 'walk', 'campus'], 'free', 'outdoor', ALL,
              DAYTIME, ['spring', 'summer', 'fall']),
        place('jnu-gate-eats', 'University-gate cheap eats', 'restaurant', 'ara', 'Kimbap, tonkatsu, '
              'jjigae and set-meal shops near the main gate priced for students.', ['cheap-eats', 'students',
              'lunch'], '$', 'indoor', ['solo', 'friends'], ['afternoon', 'evening'], cuisine='korean'),
        place('ara-cafes', 'Ara-dong cafes', 'cafe', 'ara', 'Quiet cafes on the hill road with views down to the '
              'sea, where students study through the afternoon.', ['coffee', 'study', 'views'], '$', 'indoor',
              ['solo', 'friends', 'date'], DAYTIME),
        place('ara-hof', 'Student hof bars near the main gate', 'bar', 'ara', 'Cheap beer, fried chicken and '
              'soju bars where department dinners and club nights end.', ['students', 'beer', 'groups'], '$',
              'indoor', ['friends', 'coworkers'], NIGHT, cuisine='korean'),
        place('gwaneumsa', 'Gwaneumsa Temple', 'temple', 'ara', 'The island\'s head temple of the Jogye Buddhist order, in the '
              'forest on Hallasan\'s north slope, with rows of stone Buddhas and temple-stay programs.',
              ['temple', 'buddhist', 'forest', 'quiet'], 'free', 'outdoor', ALL, DAY),
        place('gwaneumsa-trail', 'Gwaneumsa Trail to Hallasan', 'trail', 'ara', 'The steeper of the two summit '
              'trails, through deep valleys to Baengnokdam crater lake; summit hikers must book online and start '
              'early.', ['hallasan', 'summit', 'hiking', 'reservation'], 'free', 'outdoor', ['solo', 'friends'],
              ['morning'], WARM),
        place('ara-climbing-gym', 'Ara climbing and pilates studios', 'fitness', 'ara', 'Small bouldering gyms '
              'and pilates studios popular with students and young hospital staff.', ['climbing', 'pilates'],
              '$$', 'indoor', ['solo', 'friends', 'date'], ['afternoon', 'evening']),
        # Yongdam, Dodu and the airport.
        place('yongduam', 'Yongduam Rock', 'landmark', 'airport', 'A lava rock shaped like a dragon\'s head '
              'rising from the sea, a few minutes from the airport, with haenyeo selling seafood on the rocks '
              'nearby.', ['iconic', 'coast', 'free'], 'free', 'outdoor', ALL, DAYTIME),
        place('yongdam-coast-cafes', 'Yongdam coastal road cafes', 'cafe', 'airport', 'Ocean-view cafes along '
              'the seaside road where planes pass low overhead on their way into the airport.', ['coffee',
              'sea-view', 'planes', 'sunset'], '$$', 'indoor', ['solo', 'friends', 'date'],
              ['morning', 'afternoon', 'evening']),
        place('iho-tewoo', 'Iho Tewoo Beach', 'beach', 'airport', 'The closest beach to the city, with red and '
              'white horse-shaped lighthouses on the breakwater and a pine grove for camping.', ['beach',
              'lighthouses', 'sunset'], 'free', 'outdoor', ALL, ['afternoon', 'evening'], ['summer']),
        place('dodubong', 'Dodubong Peak', 'trail', 'airport', 'A small oreum beside the runway: a ten-minute '
              'climb to watch planes land against the sea.', ['oreum', 'planes', 'views', 'short-hike'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('rainbow-seawall', 'Iho-Dodu rainbow coastal road', 'landmark', 'airport', 'A stretch of seawall '
              'painted in rainbow stripes, a favourite stop for photos and an evening walk.', ['photos', 'walk',
              'free'], 'free', 'outdoor', ALL, ['afternoon', 'evening']),
        place('yongdam-abalone', 'Yongdam seafood and abalone porridge restaurants', 'restaurant', 'airport',
              'Seafood restaurants near the coast road serving jeonbok-juk, grilled okdom and seafood hotpot to '
              'arriving and departing visitors.', ['abalone', 'seafood', 'porridge'], '$$', 'indoor', ALL,
              ['morning', 'afternoon', 'evening'], cuisine='korean'),
        place('airport-convenience', 'Twenty-four-hour convenience stores', 'shopping', 'airport', 'CU and GS25 '
              'stores on every other corner, for triangle kimbap, instant ramyeon with hot water, tangerine '
              'chocolate and a seat by the window.', ['convenience', 'late-night', 'snacks'], '$', 'indoor',
              ['solo', 'friends'], ['morning', 'afternoon', 'evening', 'late']),
        # Aewol.
        place('handam-coastal-walk', 'Handam Coastal Walk', 'trail', 'aewol', 'A paved path along black lava '
              'rocks from Gwakji beach to Aewol harbour, past the cafes the coast is known for.', ['coast', 'walk',
              'sunset', 'free'], 'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('aewol-cafe-street', 'Aewol cafe coast', 'cafe', 'aewol', 'Big ocean-view cafes stacked along the '
              'cliffs with terraces, bakery counters and long weekend waits.', ['coffee', 'sea-view', 'sunset',
              'instagram'], '$$', 'mixed', ['solo', 'friends', 'date', 'family'], ['morning', 'afternoon', 'evening']),
        place('gwakji-beach', 'Gwakji Beach', 'beach', 'aewol', 'A sandy beach with a rock-walled freshwater '
              'spring pool locals dip in on hot days.', ['beach', 'swimming', 'spring-water'], 'free', 'outdoor',
              ALL, ['morning', 'afternoon', 'evening'], ['summer']),
        place('saebyeol-oreum', 'Saebyeol Oreum', 'trail', 'aewol', 'A grassy volcanic cone in inland Aewol, '
              'home of the Jeju Fire Festival and silver with eulalia grass in autumn.', ['oreum', 'grassland',
              'sunset', 'short-hike'], 'free', 'outdoor', ALL, ['morning', 'afternoon']),
        place('aewol-seafood', 'Aewol seafood ramyeon and jeonbok spots', 'restaurant', 'aewol', 'Casual '
              'restaurants near the harbour doing seafood ramyeon, abalone stone-pot rice and grilled mackerel.',
              ['seafood', 'abalone', 'ramyeon'], '$$', 'indoor', ALL, LUNCH, cuisine='korean'),
        place('aewol-sunset-bars', 'Aewol sunset pubs', 'bar', 'aewol', 'A few pubs and wine bars with terraces '
              'facing west over the sea.', ['sunset', 'wine', 'beer'], '$$', 'mixed', ['friends', 'date'], NIGHT),
        place('gwakji-paddleboard', 'Gwakji paddleboard and kayak rentals', 'fitness', 'aewol', 'Stand-up '
              'paddleboard and clear kayak rentals off the beach in calm summer weather.', ['sup', 'kayak',
              'water'], '$$', 'outdoor', ['solo', 'friends', 'date'], DAY, ['summer']),
        # Hallim.
        place('hallim-five-day-market', 'Hallim five-day market', 'market', 'hallim', 'An open-air market held '
              'on dates ending in 4 and 9, with farm produce, fish, tools, plants and food stalls.', ['market',
              'local', 'food'], '$', 'outdoor', ALL, DAY),
        place('hallim-port-restaurants', 'Hallim harbour seafood restaurants', 'restaurant', 'hallim', 'Fishermen\'s '
              'restaurants by the harbour serving hairtail, mackerel and seafood stew.', ['seafood', 'harbour',
              'local'], '$$', 'indoor', ALL, LUNCH, cuisine='korean'),
        place('biyangdo', 'Biyangdo', 'attraction', 'hallim', 'A small islet reached by a fifteen-minute ferry '
              'from Hallim port, with a coastal loop, a lighthouse peak and abalone porridge shops.', ['island',
              'ferry', 'walk'], '$', 'outdoor', ALL, DAY, WARM),
        place('geumoreum', 'Geumoreum', 'trail', 'hallim', 'An inland oreum with a crater pond at the top, '
              'paragliders launching off the rim and wide views of the west coast.', ['oreum', 'paragliding',
              'sunset'], 'free', 'outdoor', ALL, ['morning', 'afternoon']),
        place('isidore-ranch', 'Saint Isidore Ranch', 'attraction', 'hallim', 'A ranch started by an Irish '
              'missionary priest after the war, with pasture, a chapel, the roofless Tesiphon-style hut and '
              'grazing horses.', ['ranch', 'history', 'photos'], 'free', 'outdoor', ALL, DAY),
        place('hallim-harbour-cafes', 'Hallim harbour cafes', 'cafe', 'hallim', 'Converted warehouses and '
              'fishermen\'s houses turned into cafes facing the harbour.', ['coffee', 'harbour', 'quiet'], '$',
              'indoor', ['solo', 'friends', 'date'], DAYTIME),
        # Hyeopjae and Geumneung.
        place('hyeopjae-beach', 'Hyeopjae Beach', 'beach', 'hyeopjae', 'Shallow, glass-green water and white '
              'sand facing Biyangdo, one of the most photographed beaches on the island.', ['beach', 'swimming',
              'sunset', 'iconic'], 'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening'], ['summer']),
        place('geumneung-beach', 'Geumneung Beach', 'beach', 'hyeopjae', 'Hyeopjae\'s quieter neighbour with '
              'a campsite in the pines and black rocks at low tide.', ['beach', 'camping', 'quiet'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening'], ['summer', 'fall']),
        place('hallim-park', 'Hallim Park', 'garden', 'hyeopjae', 'A long-running botanical park with palm '
              'avenues, lava caves, a bonsai garden and seasonal flower shows.', ['garden', 'caves', 'flowers'],
              '$$', 'outdoor', ALL, DAY),
        place('hyeopjae-cafes', 'Hyeopjae beach cafes', 'cafe', 'hyeopjae', 'Cafes and gelato counters across '
              'the coast road with window seats over the water.', ['coffee', 'sea-view', 'dessert'], '$$', 'indoor',
              ['solo', 'friends', 'date', 'family'], DAYTIME),
        place('hyeopjae-noodles', 'Hyeopjae noodle and seafood shops', 'restaurant', 'hyeopjae', 'Gogi-guksu, '
              'seafood pancake and grilled fish restaurants on the road behind the beach.', ['noodles', 'seafood',
              'lunch'], '$', 'indoor', ALL, LUNCH, cuisine='korean'),
        place('hyeopjae-guesthouse-bars', 'Hyeopjae guesthouse bars', 'bar', 'hyeopjae', 'Guesthouse party '
              'nights and small beach bars that fill with young travellers in summer.', ['beer', 'travellers',
              'summer'], '$$', 'mixed', ['friends', 'date', 'solo'], NIGHT, ['summer', 'fall']),
        # Hamdeok.
        place('hamdeok-beach', 'Hamdeok Beach', 'beach', 'hamdeok', 'A family beach of turquoise shallows and a '
              'wooden bridge over the rocks, a short drive from the city.', ['beach', 'swimming', 'family'],
              'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening'], ['summer']),
        place('seoubong', 'Seoubong Peak', 'trail', 'hamdeok', 'A low headland oreum beside the beach, yellow '
              'with canola in spring, with a trail along the sea cliffs.', ['oreum', 'canola', 'views'], 'free',
              'outdoor', ALL, ['morning', 'afternoon']),
        place('hamdeok-cafes', 'Hamdeok glass-box cafes', 'cafe', 'hamdeok', 'Large modern cafes right on the '
              'sand with floor-to-ceiling windows and bakery counters.', ['coffee', 'sea-view', 'bakery'], '$$',
              'indoor', ALL, ['morning', 'afternoon', 'evening']),
        place('hamdeok-seafood', 'Hamdeok seafood restaurants', 'restaurant', 'hamdeok', 'Hairtail stew, '
              'abalone hotpot and grilled tilefish near the beach parking lots.', ['seafood', 'galchi', 'abalone'],
              '$$', 'indoor', ALL, LUNCH, cuisine='korean'),
        place('hamdeok-beach-bar', 'Hamdeok beach pubs', 'bar', 'hamdeok', 'Fried chicken and beer on terraces '
              'facing the water, busy on warm nights.', ['beer', 'chimaek', 'summer'], '$$', 'mixed',
              ['friends', 'date', 'family'], NIGHT, WARM, cuisine='korean'),
        place('bukchon-memorial', 'Neobeunsungi 4.3 Memorial Hall', 'museum', 'hamdeok', 'A quiet memorial in '
              'Bukchon village to the hundreds of villagers killed in January 1949 during the April 3rd events, '
              'with a memorial path through the field where children\'s graves stand.', ['history', 'memorial',
              'free'], 'free', 'mixed', ['solo', 'family'], DAY),
        place('hamdeok-surf', 'Hamdeok paddleboard rentals', 'fitness', 'hamdeok', 'Paddleboards and snorkel '
              'gear rented by the hour off the beach in summer.', ['sup', 'snorkel', 'water'], '$$', 'outdoor',
              ['friends', 'family', 'date'], DAY, ['summer']),
        # Gimnyeong and Woljeong-ri.
        place('woljeongri-beach', 'Woljeongri Beach', 'beach', 'gimnyeong', 'A white-sand beach with a row of '
              'cafes and windmills offshore, popular for beginner surfing.', ['beach', 'surf', 'cafes'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening'], SURF),
        place('gimnyeong-beach', 'Gimnyeong Beach', 'beach', 'gimnyeong', 'Clear water over white sand and black '
              'rock beside the village harbour, with a campsite.', ['beach', 'snorkel', 'camping'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening'], ['summer']),
        place('manjanggul', 'Manjanggul Lava Tube', 'attraction', 'gimnyeong', 'A UNESCO-listed lava tube where '
              'a kilometre of cool, dripping tunnel is open to walk, ending at a tall lava column.', ['cave',
              'unesco', 'rainy-day', 'geology'], '$', 'indoor', ALL, DAY),
        place('woljeongri-cafes', 'Woljeong-ri beach cafes', 'cafe', 'gimnyeong', 'Cafes with chairs facing the '
              'sea, the strip that made Woljeong-ri famous.', ['coffee', 'sea-view', 'instagram'], '$$', 'mixed',
              ['solo', 'friends', 'date'], ['morning', 'afternoon', 'evening']),
        place('woljeongri-eats', 'Woljeong-ri burger and seafood spots', 'restaurant', 'gimnyeong', 'Burger '
              'joints, poke bowls and seafood ramyeon for surfers and day-trippers.', ['burgers', 'seafood',
              'casual'], '$$', 'indoor', ['solo', 'friends', 'date'], LUNCH),
        place('woljeongri-bars', 'Woljeong-ri beach bars', 'bar', 'gimnyeong', 'A few bars with outdoor seating '
              'and live music on summer weekends.', ['beer', 'live-music', 'summer'], '$$', 'mixed',
              ['friends', 'date'], NIGHT, WARM),
        place('woljeongri-surf', 'Woljeong-ri surf schools', 'fitness', 'gimnyeong', 'Board rentals and '
              'beginner lessons when the northeast swell is up.', ['surf', 'lessons', 'water'], '$$', 'outdoor',
              ['solo', 'friends', 'date'], DAY, SURF),
        place('gimnyeong-maze-park', 'Gimnyeong Maze Park', 'attraction', 'gimnyeong', 'A hedge maze in the '
              'shape of the island, planted by a long-time foreign resident, with resident cats.', ['maze',
              'kids', 'cats'], '$', 'outdoor', ['family', 'friends', 'date'], DAY),
        place('olle-route-20', 'Olle Route 20', 'trail', 'gimnyeong', 'An Olle trail section from Gimnyeong '
              'along the stone-walled fishing villages and beaches to the Haenyeo Museum.', ['olle', 'coast',
              'walk'], 'free', 'outdoor', ['solo', 'friends', 'date'], DAY),
        # Sehwa, Hado and Jongdal.
        place('haenyeo-museum', 'Jeju Haenyeo Museum', 'museum', 'gujwa', 'A museum of the island\'s women '
              'divers: their tools, rubber suits, songs, the 1932 haenyeo uprising and their lives today.',
              ['haenyeo', 'history', 'rainy-day'], '$', 'indoor', ALL, DAY),
        place('sehwa-beach', 'Sehwa Beach', 'beach', 'gujwa', 'A small, calm beach with clear water and a '
              'handful of cafes and craft stalls along the coast road.', ['beach', 'quiet', 'swimming'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening'], ['summer']),
        place('sehwa-market', 'Sehwa five-day market', 'market', 'gujwa', 'A village market on dates ending in '
              '5 and 0 with fish, vegetables, plants and food stalls.', ['market', 'local', 'food'], '$',
              'outdoor', ALL, DAY),
        place('haenyeo-kitchen', 'Haenyeo\'s Kitchen', 'restaurant', 'gujwa', 'A dining theatre in a former '
              'fish market in Jongdal-ri where haenyeo tell their stories and serve the seafood they gather.',
              ['haenyeo', 'seafood', 'show'], '$$$', 'indoor', ['friends', 'date', 'family'], LUNCH,
              cuisine='korean'),
        place('hado-haenyeo-house', 'Hado haenyeo house', 'restaurant', 'gujwa', 'A plain village co-op '
              'restaurant run by the diving collective, serving conch, sea urchin, abalone porridge and '
              'seafood noodles.', ['haenyeo', 'seafood', 'abalone'], '$$', 'indoor', ALL, LUNCH, cuisine='korean'),
        place('sehwa-cafes', 'Sehwa seaside cafes', 'cafe', 'gujwa', 'Small cafes and bookshops along the '
              'coast road with ocean views and a slower pace than Woljeong-ri.', ['coffee', 'sea-view', 'books'],
              '$$', 'indoor', ['solo', 'friends', 'date'], DAYTIME),
        place('bijarim', 'Bijarim Forest', 'park', 'gujwa', 'An old forest of nutmeg yew trees, some centuries '
              'old, with a red volcanic gravel path.', ['forest', 'walk', 'quiet'], '$', 'outdoor', ALL, DAY),
        place('yongnuni-oreum', 'Yongnuni Oreum', 'trail', 'gujwa', 'A soft green oreum with a triple crater '
              'that looks like a dragon\'s eyes from above, reopened after years of rest.', ['oreum', 'views',
              'sunrise'], 'free', 'outdoor', ALL, ['morning', 'afternoon']),
        place('darangshi-oreum', 'Darangshi Oreum', 'trail', 'gujwa', 'The "queen of oreum": a steep climb to a '
              'perfectly round crater rim with views over the eastern cones.', ['oreum', 'views', 'hike'], 'free',
              'outdoor', ALL, ['morning', 'afternoon']),
        # Seongsan.
        place('ilchulbong', 'Seongsan Ilchulbong', 'landmark', 'seongsan', 'Sunrise Peak: a tuff cone rising '
              'straight from the sea, climbed by stairs in about half an hour; a UNESCO World Heritage site.',
              ['unesco', 'sunrise', 'iconic', 'hike'], '$', 'outdoor', ALL, ['morning', 'afternoon']),
        place('seongsan-haenyeo-show', 'Haenyeo diving demonstration at Ilchulbong', 'attraction', 'seongsan',
              'Haenyeo sing, dive and sell their catch on the rocks at the foot of the peak most afternoons, '
              'weather permitting.', ['haenyeo', 'seafood', 'free'], 'free', 'outdoor', ALL, ['afternoon'], WARM),
        place('gwangchigi-beach', 'Gwangchigi Beach', 'beach', 'seongsan', 'A wide shelf of mossy lava rock and '
              'sand exposed at low tide, with Ilchulbong mirrored in the pools.', ['beach', 'tidepools', 'photos'],
              'free', 'outdoor', ALL, ['morning', 'afternoon']),
        place('seopjikoji', 'Seopjikoji', 'landmark', 'seongsan', 'A grassy headland with a small lighthouse, '
              'canola in spring and views back to Ilchulbong.', ['coast', 'walk', 'canola'], 'free', 'outdoor', ALL,
              DAY),
        place('aqua-planet', 'Aqua Planet Jeju', 'attraction', 'seongsan', 'A large aquarium at Seopjikoji '
              'with a giant ocean tank, sea mammals and a haenyeo exhibit.', ['aquarium', 'kids', 'rainy-day'],
              '$$$', 'indoor', ['family', 'friends', 'date'], DAY),
        place('seongsan-galchi', 'Seongsan hairtail and black pork restaurants', 'restaurant', 'seongsan',
              'Restaurants below the peak serving whole grilled hairtail, spicy galchi-jorim and black pork to '
              'the tour buses and the locals after them.', ['galchi', 'black-pork', 'seafood'], '$$', 'indoor',
              ALL, LUNCH, cuisine='korean'),
        place('seongsan-cafes', 'Ilchulbong view cafes', 'cafe', 'seongsan', 'Rooftop and window cafes facing '
              'the peak, open early for people coming down from sunrise.', ['coffee', 'views', 'sunrise'], '$$',
              'indoor', ['solo', 'friends', 'date', 'family'], DAYTIME),
        place('seongsan-pubs', 'Seongsan-ri pubs', 'bar', 'seongsan', 'A handful of beer pubs and seafood '
              'pochas for guesthouse guests staying over for the sunrise.', ['beer', 'travellers', 'soju'], '$',
              'indoor', ['friends', 'date'], NIGHT),
        # Udo.
        place('udobong', 'Udobong and the lighthouse park', 'trail', 'udo', 'A green hill at the south end of '
              'Udo with grazing horses, a lighthouse and views back to Seongsan.', ['views', 'walk', 'horses'],
              'free', 'outdoor', ALL, DAY),
        place('seobin-baeksa', 'Seobin Baeksa (coral sand beach)', 'beach', 'udo', 'A beach of crushed white '
              'red-algae nodules, not sand, with turquoise water.', ['beach', 'swimming', 'iconic'], 'free',
              'outdoor', ALL, DAY, ['spring', 'summer', 'fall']),
        place('hagosudong-beach', 'Hagosudong Beach', 'beach', 'udo', 'Udo\'s calm east-side beach, shallow '
              'and good for paddling.', ['beach', 'family', 'swimming'], 'free', 'outdoor', ALL, DAY, ['summer']),
        place('geommeolle', 'Geommeolle Beach and Dongangyeonggul cave', 'beach', 'udo', 'A tiny black-sand '
              'cove under the cliffs, with a sea cave you can walk into at low tide.', ['beach', 'cave', 'cliffs'],
              'free', 'outdoor', ALL, DAY),
        place('udo-peanut-cafes', 'Udo peanut ice cream cafes', 'cafe', 'udo', 'Cafes selling soft-serve '
              'topped with Udo\'s small local peanuts, and peanut lattes.', ['dessert', 'peanuts', 'coffee'], '$',
              'mixed', ALL, DAY),
        place('udo-seafood', 'Udo seafood noodle and abalone restaurants', 'restaurant', 'udo', 'Restaurants '
              'near the ferry landing doing seafood jjamppong, conch and abalone dishes.', ['seafood', 'noodles',
              'abalone'], '$$', 'indoor', ALL, LUNCH, cuisine='korean'),
        # Pyoseon.
        place('pyoseon-beach', 'Pyoseon Beach', 'beach', 'pyoseon', 'A huge, shallow tidal beach that '
              'becomes a round lagoon at high tide, beside the Haevichi resort.', ['beach', 'tidal', 'family'],
              'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening'], ['summer']),
        place('jeju-folk-village', 'Jeju Folk Village', 'museum', 'pyoseon', 'An open-air museum of over a '
              'hundred relocated thatched houses, shrines and stone walls from across the island.', ['history',
              'thatched-houses', 'family'], '$$', 'outdoor', ALL, DAY),
        place('seongeup-village', 'Seongeup Folk Village', 'landmark', 'pyoseon', 'A lived-in inland village '
              'of thatched stone houses, old trees and dol hareubang, the island\'s old district seat.',
              ['history', 'village', 'dol-hareubang'], 'free', 'outdoor', ALL, DAY),
        place('pyoseon-seafood', 'Pyoseon seafood and haemul ttukbaegi', 'restaurant', 'pyoseon', 'Seafood '
              'stews bubbling in earthenware pots, grilled fish and abalone near the beach.', ['seafood', 'stew',
              'abalone'], '$$', 'indoor', ALL, LUNCH, cuisine='korean'),
        place('pyoseon-cafes', 'Pyoseon beach cafes', 'cafe', 'pyoseon', 'Quiet cafes near the beach and '
              'folk village, some in old stone houses.', ['coffee', 'quiet', 'stone-house'], '$$', 'indoor',
              ['solo', 'friends', 'date', 'family'], DAYTIME),
        # Namwon and Wimi.
        place('keunyeong', 'Keunyeong coastal path', 'trail', 'namwon', 'A cliff-top path through pine and '
              'camellia above black lava, part of an Olle route, with a viewpoint where the trees frame a map '
              'of the Korean peninsula.', ['olle', 'cliffs', 'walk'], 'free', 'outdoor', ALL, DAY),
        place('tangerine-farm-cafes', 'Tangerine orchard cafes', 'cafe', 'namwon', 'Farm cafes inside the '
              'orchards serving fresh juice, tangerine cakes and hallabong lattes among the trees.', ['tangerines',
              'farm', 'coffee'], '$$', 'mixed', ALL, DAYTIME),
        place('tangerine-picking', 'Tangerine picking farms', 'attraction', 'namwon', 'Family farms that let '
              'visitors pick a basket of mandarins from the trees in season.', ['tangerines', 'farm', 'kids'], '$',
              'outdoor', ALL, DAY, ['fall', 'winter']),
        place('wimi-camellia', 'Wimi camellia colony', 'garden', 'namwon', 'A dense windbreak of camellia trees '
              'planted by one villager over decades, blooming red in midwinter.', ['camellia', 'flowers', 'quiet'],
              '$', 'outdoor', ALL, DAY, ['winter']),
        place('namwon-guksu', 'Namwon noodle and seafood shops', 'restaurant', 'namwon', 'Village restaurants '
              'doing gogi-guksu, momguk and grilled fish for farmers at lunch.', ['noodles', 'local', 'lunch'],
              '$', 'indoor', ALL, LUNCH, cuisine='korean'),
        # Seogwipo old town.
        place('olle-market', 'Seogwipo Maeil Olle Market', 'market', 'seogwipo', 'A covered market with a '
              'stream down the middle: tangerines, hairtail, raw-fish platters, fried chicken, omegi tteok and '
              'street food.', ['food', 'tangerines', 'street-food', 'iconic'], '$', 'mixed', ALL,
              ['morning', 'afternoon', 'evening']),
        place('lee-jung-seop-street', 'Lee Jung-seop Street and Art Museum', 'museum', 'seogwipo', 'The '
              'painter\'s small thatched room from his refugee year in Seogwipo, a museum of his work and a '
              'sloping street of craft markets and cafes.', ['art', 'history', 'crafts'], '$', 'mixed', ALL, DAY),
        place('cheonjiyeon', 'Cheonjiyeon Falls', 'attraction', 'seogwipo', 'A waterfall at the end of a short '
              'subtropical gorge walk, lit up and open into the evening.', ['waterfall', 'walk', 'night'], '$',
              'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('jeongbang', 'Jeongbang Falls', 'attraction', 'seogwipo', 'A waterfall that drops straight into the '
              'sea, reached by steps down to the rocks.', ['waterfall', 'coast', 'iconic'], '$', 'outdoor', ALL,
              DAY),
        place('saeseom', 'Saeseom islet and Saeyeongyo bridge', 'landmark', 'seogwipo', 'A footbridge shaped '
              'like a sail from Seogwipo harbour to a small wooded islet with a loop path.', ['walk', 'harbour',
              'night-lights', 'free'], 'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('jaguri-park', 'Jaguri Park', 'park', 'seogwipo', 'A seaside park with sculptures inspired by Lee '
              'Jung-seop and a view of the islands off the harbour.', ['park', 'art', 'sea-view'], 'free',
              'outdoor', ALL, DAYTIME),
        place('seogwipo-harbour-restaurants', 'Seogwipo harbour hairtail restaurants', 'restaurant', 'seogwipo',
              'Restaurants near the harbour serving galchi-guk, grilled hairtail and raw-fish platters.',
              ['galchi', 'seafood', 'harbour'], '$$', 'indoor', ALL, LUNCH, cuisine='korean'),
        place('lee-jung-seop-cafes', 'Cafes around Lee Jung-seop Street', 'cafe', 'seogwipo', 'Small cafes, '
              'bookshops and tangerine dessert counters on the art street.', ['coffee', 'art', 'dessert'], '$$',
              'indoor', ['solo', 'friends', 'date'], DAYTIME),
        place('seogwipo-pocha', 'Seogwipo old-town pubs and pochas', 'bar', 'seogwipo', 'Soju bars and small '
              'pubs on the streets above the harbour, with raw fish to go from the market.', ['soju', 'pocha',
              'local'], '$', 'indoor', ['friends', 'coworkers', 'date'], NIGHT),
        place('seogwipo-jjimjilbang', 'Seogwipo jjimjilbang', 'fitness', 'seogwipo', 'A big bathhouse and '
              'sauna with hot pools, a sleeping hall and snack bar, open around the clock.', ['sauna', 'spa',
              'late-night'], '$', 'indoor', ['solo', 'friends', 'family'], ['morning', 'afternoon', 'evening', 'late']),
        place('olle-center', 'Jeju Olle Tourist Center', 'landmark', 'seogwipo', 'The Olle trail foundation\'s '
              'center where Route 6 ends and Route 7 begins, with maps, passports for stamping, a cafe and a guesthouse.',
              ['olle', 'walking', 'information'], 'free', 'indoor', ALL, DAY),
        place('citrus-museum', 'Seogwipo Citrus Museum', 'museum', 'seogwipo', 'A museum of citrus growing '
              'with greenhouses, a tangerine orchard and the winter citrus festival.', ['tangerines', 'farm',
              'kids'], '$', 'mixed', ALL, DAY),
        # New Seogwipo, Gangjeong and Beophwan.
        place('oedolgae', 'Oedolgae Rock', 'landmark', 'new-seogwipo', 'A lone sea stack off a pine-covered '
              'coast on Olle Route 7, one of the best-loved walks on the island.', ['coast', 'olle',
              'iconic'], 'free', 'outdoor', ALL, DAYTIME),
        place('olle-route-7', 'Olle Route 7', 'trail', 'new-seogwipo', 'An Olle section from Seogwipo past Oedolgae '
              'along lava coast and pebble beaches to Wolpyeong, past Beophwan harbour.', ['olle', 'coast', 'walk'],
              'free', 'outdoor', ['solo', 'friends', 'date'], DAY),
        place('yakcheonsa', 'Yakcheonsa Temple', 'temple', 'new-seogwipo', 'A huge, modern temple hall above '
              'the sea at Daepo, with a giant seated Buddha inside and a spring believed to heal.',
              ['temple', 'buddhist', 'sea-view'], 'free', 'mixed', ALL, DAY),
        place('world-cup-stadium', 'Jeju World Cup Stadium', 'stadium', 'new-seogwipo', 'The 2002 World Cup '
              'stadium with a sail-shaped roof, home ground of Jeju SK FC.', ['football', 'sports'], '$$', 'outdoor',
              ['friends', 'family', 'date'], ['afternoon', 'evening'], ['spring', 'summer', 'fall']),
        place('beophwan-haenyeo-house', 'Beophwan haenyeo seafood houses', 'restaurant', 'new-seogwipo',
              'Seafood shacks by Beophwan harbour where the village diving collective sells sea urchin, conch '
              'and raw fish.', ['haenyeo', 'seafood', 'harbour'], '$$', 'mixed', ALL, LUNCH, cuisine='korean'),
        place('new-seogwipo-cafes', 'Gangjeong and Beophwan cafes', 'cafe', 'new-seogwipo', 'Neighborhood and '
              'ocean-view cafes between the apartment blocks and the coast.', ['coffee', 'sea-view'], '$$', 'indoor',
              ['solo', 'friends', 'date', 'family'], DAYTIME),
        place('new-seogwipo-bars', 'New Seogwipo chicken and beer pubs', 'bar', 'new-seogwipo', 'Hof bars '
              'and barbecue restaurants on the commercial streets near the stadium.', ['chimaek', 'beer',
              'groups'], '$$', 'indoor', ['friends', 'coworkers', 'family'], NIGHT, cuisine='korean'),
        place('new-seogwipo-gyms', 'New Seogwipo gyms', 'fitness', 'new-seogwipo', 'Gyms and pilates studios '
              'above the shops on the main roads.', ['gym', 'pilates'], '$$', 'indoor', ['solo', 'friends'],
              ['morning', 'evening', 'late']),
        # Jungmun.
        place('jungmun-saekdal', 'Jungmun Saekdal Beach', 'beach', 'jungmun', 'A golden-sand beach under the '
              'resort hotels and the island\'s best-known surf break; the winter penguin swim is held here.',
              ['beach', 'surf', 'resort'], 'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening'], SURF),
        place('jungmun-surf', 'Jungmun surf schools', 'fitness', 'jungmun', 'Board rentals and lessons for the '
              'summer swell at Saekdal beach.', ['surf', 'lessons'], '$$', 'outdoor', ['solo', 'friends', 'date'],
              DAY, SURF),
        place('cheonjeyeon', 'Cheonjeyeon Falls', 'attraction', 'jungmun', 'Three tiers of waterfalls in a '
              'forested gorge crossed by a high arched bridge.', ['waterfall', 'walk', 'bridge'], '$', 'outdoor',
              ALL, DAY),
        place('jusangjeolli', 'Jusangjeolli Cliff', 'landmark', 'jungmun', 'Hexagonal basalt columns stacked '
              'along the shore at Daepo, pounded by waves.', ['geology', 'coast', 'iconic'], '$', 'outdoor', ALL,
              DAY),
        place('yeomiji', 'Yeomiji Botanical Garden', 'garden', 'jungmun', 'A big glasshouse of tropical and '
              'desert plants with outdoor gardens, good on wet days.', ['garden', 'greenhouse', 'rainy-day'], '$$',
              'mixed', ALL, DAY),
        place('teddy-bear-museum', 'Teddy Bear Museum Jeju', 'museum', 'jungmun', 'A museum of teddy bears in '
              'historical scenes and costumes, a long-time stop on family trips.', ['kids', 'rainy-day', 'kitsch'],
              '$$', 'indoor', ['family', 'friends', 'date'], DAY),
        place('camellia-hill', 'Camellia Hill', 'garden', 'jungmun', 'A large camellia garden inland from '
              'Jungmun, pink and red in winter and blue with hydrangeas in early summer.', ['flowers', 'camellia',
              'photos'], '$$', 'outdoor', ALL, DAY, ['winter', 'spring', 'summer']),
        place('icc-jeju', 'International Convention Center Jeju', 'venue', 'jungmun', 'The convention center on '
              'the cliffs, host of summits, conferences and concerts.', ['conventions', 'concerts'], '$$',
              'indoor', ['solo', 'coworkers', 'friends'], ['morning', 'afternoon', 'evening']),
        place('jungmun-hotel-dining', 'Jungmun resort hotel restaurants', 'restaurant', 'jungmun', 'Buffets, '
              'Korean set menus and hotel bars in the big resorts above the beach.', ['hotel', 'buffet',
              'special-occasion'], '$$$$', 'indoor', ['date', 'family', 'coworkers'], ['morning', 'evening'],
              cuisine='korean'),
        place('jungmun-cafes', 'Jungmun ocean-view cafes', 'cafe', 'jungmun', 'Cafes on the coast road and '
              'olle path with terraces facing the sea.', ['coffee', 'sea-view', 'terrace'], '$$', 'mixed',
              ['solo', 'friends', 'date', 'family'], DAYTIME),
        place('jungmun-lounges', 'Jungmun resort lounges', 'bar', 'jungmun', 'Hotel lounges and a few pubs '
              'with live music and cocktails, quiet by city standards.', ['cocktails', 'hotel', 'live-music'], '$$$',
              'indoor', ['date', 'friends'], NIGHT),
        # Daejeong and Moseulpo.
        place('moseulpo-bangeo', 'Moseulpo yellowtail restaurants', 'restaurant', 'daejeong', 'Harbour '
              'restaurants serving fat winter bangeo (yellowtail) as thick raw slices and steamed with soy, plus '
              'mackerel the rest of the year.', ['seafood', 'bangeo', 'harbour'], '$$$', 'indoor',
              ['friends', 'family', 'coworkers', 'date'], LUNCH, cuisine='korean'),
        place('songaksan', 'Songaksan', 'trail', 'daejeong', 'A low coastal crater with a cliff path, grazing '
              'horses and wartime caves dug into the shore below by forced labour under Japanese rule.',
              ['oreum', 'coast', 'history', 'horses'], 'free', 'outdoor', ALL, DAY),
        place('alddreu-airfield', 'Alddreu Airfield', 'landmark', 'daejeong', 'Concrete hangars left in the '
              'fields from a Japanese wartime air base, near memorials to people killed there in 1950; a '
              'sobering walk among the garlic fields.', ['history', 'memorial', 'free'], 'free', 'outdoor',
              ['solo', 'friends', 'family'], DAY),
        place('marado-gapado', 'Gapado and Marado', 'attraction', 'daejeong', 'Ferries to two flat islands: '
              'Gapado with barley fields in spring, and Marado, Korea\'s southernmost point, famous for '
              'jajangmyeon restaurants.', ['island', 'ferry', 'walk'], '$$', 'outdoor', ALL, DAY),
        place('sanbangsan', 'Sanbangsan and Yongmeori Coast', 'landmark', 'daejeong', 'A lava dome with a '
              'cave temple, above a layered sandstone coast shaped like a dragon\'s head.', ['geology', 'temple',
              'coast'], '$', 'outdoor', ALL, DAY),
        place('chusa-museum', 'Jeju Chusa Museum', 'museum', 'daejeong', 'The exile house of the calligrapher '
              'Kim Jeong-hui and a museum of his work, in a building echoing his painting Sehando.',
              ['calligraphy', 'history', 'architecture'], 'free', 'indoor', ALL, DAY),
        place('osulloc-tea-museum', 'O\'sulloc Tea Museum', 'museum', 'daejeong', 'A tea house and museum '
              'among the green tea fields near Global Education City, with green-tea ice cream and roll cake.',
              ['tea', 'fields', 'dessert'], '$', 'mixed', ALL, DAY),
        place('daejeong-market', 'Daejeong five-day market', 'market', 'daejeong', 'A market in Moseulpo on '
              'dates ending in 1 and 6 with fish, garlic, vegetables and food stalls.', ['market', 'local',
              'food'], '$', 'outdoor', ALL, DAY),
        place('moseulpo-cafes', 'Moseulpo and Hamo cafes', 'cafe', 'daejeong', 'Small cafes in old houses by '
              'the harbour and windy coast.', ['coffee', 'quiet', 'harbour'], '$', 'indoor',
              ['solo', 'friends', 'date'], DAYTIME),
        place('moseulpo-pocha', 'Moseulpo harbour pochas', 'bar', 'daejeong', 'Seafood pochas and soju bars '
              'by the port where boat crews and teachers from the international schools both turn up.', ['soju',
              'seafood', 'harbour'], '$', 'indoor', ['friends', 'coworkers'], NIGHT, cuisine='korean'),
        # Bonggae, Gyorae and the foothills.
        place('peace-park', 'Jeju April 3rd Peace Park', 'museum', 'foothills', 'The national memorial to the '
              'islanders killed in the violence of 1947-1954, estimated at 14,000 to 30,000, with a museum, memorial '
              'altar and walls of names; a place for quiet.', ['history', 'memorial', 'free'], 'free', 'mixed',
              ['solo', 'family', 'friends'], DAY),
        place('jeolmul-forest', 'Jeolmul Natural Recreation Forest', 'park', 'foothills', 'A cedar forest with '
              'boardwalks, a spring and a short oreum climb, cool in summer.', ['forest', 'walk', 'family'], '$',
              'outdoor', ALL, DAY),
        place('saryeoni', 'Saryeoni Forest Path', 'trail', 'foothills', 'A long, flat path of red volcanic gravel '
              'through cedar and broadleaf forest, at its best in rain or mist.', ['forest', 'walk', 'mist'], 'free',
              'outdoor', ALL, DAY),
        place('seongpanak', 'Seongpanak Trail to Hallasan', 'trail', 'foothills', 'The longer, gentler trail to '
              'the summit of Hallasan and its crater lake: a full day, booked online in advance, with cut-off '
              'times at the shelter.', ['hallasan', 'summit', 'hiking', 'reservation'], 'free', 'outdoor',
              ['solo', 'friends'], ['morning']),
        place('jeju-stone-park', 'Jeju Stone Park', 'museum', 'foothills', 'A vast outdoor park and museum of '
              'lava rocks, stone grandfathers and the island\'s myths of the giant goddess Seolmundae Halmang.',
              ['myth', 'stone', 'architecture'], '$', 'mixed', ALL, DAY),
        place('sangumburi', 'Sangumburi Crater', 'landmark', 'foothills', 'A broad, forested crater with silver '
              'grass and a walking loop around the rim.', ['crater', 'walk', 'grassland'], '$', 'outdoor', ALL, DAY),
        place('ecoland', 'Eco Land Theme Park', 'attraction', 'foothills', 'A small steam-style train looping '
              'through gotjawal forest with stops at a lake and gardens.', ['train', 'kids', 'forest'], '$$',
              'outdoor', ['family', 'date', 'friends'], DAY),
        place('gyorae-chicken', 'Gyorae native-chicken restaurants', 'restaurant', 'foothills', 'A village '
              'known for native chicken: hotpot, chicken sashimi for the brave and porridge to finish.',
              ['chicken', 'hotpot', 'local'], '$$', 'indoor', ['family', 'friends', 'coworkers'], LUNCH,
              cuisine='korean'),
        place('forest-cafes', 'Forest-edge cafes', 'cafe', 'foothills', 'Cafes in glass boxes and old farmhouses '
              'at the edge of the forest, popular after a walk.', ['coffee', 'forest', 'quiet'], '$$', 'indoor',
              ['solo', 'friends', 'date', 'family'], DAY),
        # Gasi-ri.
        place('noksan-ro', 'Noksan-ro canola and cherry road', 'landmark', 'gasi', 'A country road where canola '
              'fields and cherry blossoms bloom together in early spring.', ['canola', 'cherry-blossom', 'drive'],
              'free', 'outdoor', ALL, DAY, ['spring']),
        place('ttarabi-oreum', 'Ttarabi Oreum', 'trail', 'gasi', 'A gentle oreum with three craters, the "queen" '
              'of the eastern cones for its curves and autumn eulalia grass.', ['oreum', 'grassland', 'sunset'],
              'free', 'outdoor', ALL, ['morning', 'afternoon']),
        place('gasi-horse-riding', 'Gasi-ri horse ranches', 'attraction', 'gasi', 'Ranches offering short rides '
              'on Jeju ponies and larger horses across the grassland.', ['horses', 'riding', 'ranch'], '$$',
              'outdoor', ['family', 'friends', 'date'], DAY, WARM),
        place('gasi-dombe-gogi', 'Gasi-ri dombe-gogi restaurants', 'restaurant', 'gasi', 'Village restaurants '
              'serving boiled pork sliced onto a wooden board, blood sausage and momguk.', ['pork', 'local',
              'momguk'], '$', 'indoor', ALL, LUNCH, cuisine='korean'),
        place('ranch-cafes', 'Ranch-country cafes', 'cafe', 'gasi', 'Cafes in converted barns and farmhouses '
              'looking out on oreum and grazing horses.', ['coffee', 'views', 'horses'], '$$', 'indoor',
              ['solo', 'friends', 'date', 'family'], DAY),
    ],
    'colleges': [
        {'id': 'jnu', 'name': 'Jeju National University', 'type': 'public-university', 'neighborhood': 'ara',
         'size': 'large', 'known_for': ['marine-science', 'agriculture', 'tourism', 'veterinary-medicine',
         'engineering'], 'source': S},
        {'id': 'jnu-medicine', 'name': 'Jeju National University School of Medicine', 'type': 'medical-school',
         'neighborhood': 'ara', 'size': 'small', 'known_for': ['medicine', 'nursing'], 'source': S},
        {'id': 'jeju-halla', 'name': 'Jeju Halla University', 'type': 'community-college',
         'neighborhood': 'sinjeju', 'size': 'medium', 'known_for': ['nursing', 'hospitality', 'tourism',
         'health-sciences'], 'source': S},
    ],
    'employers': [
        employer('jeju-provincial-government', 'Jeju Special Self-Governing Provincial Government', 'government',
                 'sinjeju', 'large', 'The provincial government, which runs most public services on the island '
                 'from its offices in Yeon-dong.', ['government-analyst', 'social-worker', 'accountant']),
        employer('jeju-office-of-education', 'Jeju Provincial Office of Education', 'education', 'sinjeju',
                 'large', 'Runs the island\'s public schools, from village elementary schools to city high schools.',
                 ['teacher', 'social-worker']),
        employer('jnu-hospital', 'Jeju National University Hospital', 'healthcare', 'ara', 'large', 'The '
                 'island\'s main teaching hospital and trauma center.', ['registered-nurse', 'night-nurse',
                 'physician-resident', 'pharmacist', 'medical-researcher']),
        employer('halla-hospital', 'Jeju Halla General Hospital', 'healthcare', 'sinjeju', 'large', 'A large '
                 'private general hospital with a busy emergency room.', ['registered-nurse', 'night-nurse',
                 'pharmacist', 'physician-resident']),
        employer('seogwipo-medical-center', 'Seogwipo Medical Center', 'healthcare', 'seogwipo', 'medium',
                 'The public hospital for the south of the island.', ['registered-nurse', 'night-nurse',
                 'pharmacist', 'social-worker']),
        employer('jnu-employer', 'Jeju National University', 'education', 'ara', 'large', 'Faculty, research '
                 'and staff jobs at the national university, strong in marine science and subtropical farming.',
                 ['professor', 'graduate-student', 'medical-researcher', 'biologist', 'data-analyst']),
        employer('kakao', 'Kakao (Jeju head office)', 'technology', 'ara', 'medium', 'The internet company\'s '
                 'registered head office, Space.1, in Jeju Science Park; most of its staff work near Seoul, but '
                 'some teams are based here.', ['software-engineer', 'ux-designer', 'data-analyst',
                 'marketing-coordinator']),
        employer('jeju-air', 'Jeju Air', 'transport', 'airport', 'large', 'The low-cost airline founded with '
                 'the province, with its registered head office in Jeju and a base at the airport.',
                 ['marketing-coordinator', 'data-analyst', 'accountant', 'software-engineer']),
        employer('jeju-airport', 'Jeju International Airport', 'transport', 'airport', 'large', 'One of the '
                 'busiest domestic airports in the world, with ground staff, shops, cafes and cargo handlers.',
                 ['retail-associate', 'barista', 'port-logistics', 'line-cook']),
        employer('dream-tower-employer', 'Jeju Dream Tower', 'hospitality', 'sinjeju', 'large', 'The Grand Hyatt '
                 'hotel, foreigners-only casino, restaurants and shops in Jeju\'s tallest tower.', ['casino-dealer',
                 'hotel-front-desk', 'line-cook', 'server', 'bartender', 'event-planner']),
        employer('shilla-jeju', 'The Shilla Jeju', 'hospitality', 'jungmun', 'large', 'A long-established '
                 'luxury resort hotel above Jungmun beach.', ['hotel-front-desk', 'event-planner', 'line-cook',
                 'server', 'bartender', 'lifeguard']),
        employer('lotte-hotel-jeju', 'Lotte Hotel Jeju', 'hospitality', 'jungmun', 'large', 'A big resort hotel '
                 'in Jungmun with windmill-themed gardens and a pool complex.', ['hotel-front-desk', 'line-cook',
                 'server', 'bartender', 'lifeguard']),
        employer('haevichi', 'Haevichi Hotel and Resort Jeju', 'hospitality', 'pyoseon', 'medium', 'A resort '
                 'hotel on Pyoseon beach.', ['hotel-front-desk', 'line-cook', 'server']),
        employer('icc-jeju-employer', 'International Convention Center Jeju', 'hospitality', 'jungmun', 'small',
                 'Conference and event staff for summits, trade shows and concerts.', ['event-planner',
                 'tour-guide']),
        employer('shilla-duty-free-employer', 'Shilla Duty Free Jeju', 'retail', 'sinjeju', 'medium', 'Sales '
                 'staff, many speaking Chinese or Japanese, for the duty-free trade.', ['retail-associate',
                 'marketing-coordinator']),
        employer('jpdc', 'Jeju Province Development Corporation (Jeju Samdasoo)', 'manufacturing', 'foothills',
                 'medium', 'The provincial company that bottles Samdasoo spring water from the lava aquifer at its '
                 'plant in Gyorae and makes tangerine juice.', ['data-analyst', 'marketing-coordinator',
                 'port-logistics', 'accountant']),
        employer('orion-yongamsu', 'Orion Jeju Yongamsu', 'manufacturing', 'gujwa', 'small', 'A bottling plant '
                 'for lava-seawater drinking water in Gujwa.', ['port-logistics', 'marketing-coordinator']),
        employer('jeju-bank', 'Jeju Bank', 'finance', 'old-jeju', 'medium', 'The island\'s own regional bank, '
                 'headquartered in the old town.', ['accountant', 'financial-analyst', 'data-analyst']),
        employer('kbs-jeju', 'KBS Jeju', 'media', 'sinjeju', 'small', 'The public broadcaster\'s Jeju station, '
                 'making island news and radio.', ['journalist']),
        employer('international-schools', 'Global Education City international schools', 'education',
                 'daejeong', 'medium', 'Boarding and day schools taught in English, including NLCS Jeju, Branksome '
                 'Hall Asia, KIS Jeju and St. Johnsbury Academy Jeju, with many foreign teachers.',
                 ['teacher', 'social-worker']),
        employer('jeju-olle-foundation', 'Jeju Olle Foundation', 'tourism', 'seogwipo', 'small', 'The non-profit '
                 'that marks and maintains the Olle trails and runs the walking festival.', ['tour-guide',
                 'event-planner', 'marketing-coordinator']),
        employer('citrus-cooperatives', 'Citrus growers\' cooperatives', 'agriculture', 'namwon', 'large',
                 'Farm co-ops that grade, pack and sell the tangerine, hallabong and cheonhyehyang crops from '
                 'thousands of family orchards.', ['citrus-farmer', 'accountant']),
        employer('fisheries-cooperatives', 'Seongsan and Moseulpo fisheries cooperatives', 'fishing', 'seongsan',
                 'medium', 'Suhyup co-ops that run the fish auctions and supply the boats and haenyeo collectives.',
                 ['fishing-crew', 'accountant']),
        employer('jeju-district-court', 'Jeju District Court', 'legal', 'ido', 'medium', 'The island\'s '
                 'courthouse near City Hall, with the prosecutors\' office and law offices around it.',
                 ['paralegal', 'government-analyst']),
        employer('jeju-naval-base', 'ROK Navy Jeju base', 'defense', 'new-seogwipo', 'medium', 'The naval base '
                 'at Gangjeong, opened in 2016 after years of village protest, which shares its harbour with '
                 'cruise ships.', ['military-sailor', 'defense-engineer']),
    ],
    'career_hubs': [
        {'id': 'jeju-city-center', 'name': 'Jeju City government and business district',
         'neighborhoods': ['sinjeju', 'old-jeju', 'ido', 'airport'], 'sectors': ['government', 'finance',
         'retail', 'media', 'healthcare', 'transport', 'legal', 'real-estate', 'construction', 'creative'],
         'summary': 'The provincial offices, courts, banks, hospitals, duty-free stores, design studios, '
         'real-estate offices, builders and airport jobs in Jeju City.', 'source': S},
        {'id': 'ara-campus', 'name': 'Ara campus and Jeju Science Park', 'neighborhoods': ['ara'],
         'sectors': ['education', 'healthcare', 'technology', 'biotech'], 'summary': 'The national university, '
         'its hospital and the tech and bio companies of the science park.', 'source': S},
        {'id': 'resort-coast', 'name': 'South-coast resorts', 'neighborhoods': ['jungmun', 'seogwipo',
         'new-seogwipo', 'pyoseon', 'seongsan'], 'sectors': ['hospitality', 'tourism', 'entertainment',
         'recreation'], 'summary': 'Resort hotels, the convention center, tour companies and attractions that '
         'employ much of the south of the island.', 'source': S},
        {'id': 'farms-and-harbours', 'name': 'Orchards, farms and harbours', 'neighborhoods': ['namwon',
         'hallim', 'daejeong', 'gujwa', 'foothills', 'gasi'], 'sectors': ['agriculture', 'fishing',
         'manufacturing'], 'summary': 'Tangerine orchards, garlic and vegetable fields, ranches, fishing ports '
         'and the island\'s bottled-water plants.', 'source': S},
    ],
    'careers': [
        {'id': 'citrus-farmer', 'name': 'Tangerine farmer', 'sector': 'agriculture', 'schedule': 'early',
         'pay': '$', 'summary': 'Tending a family tangerine or hallabong orchard: pruning in spring, spraying and '
                                'thinning in summer, and the long harvest from late autumn into winter.',
         'themes': ['the harvest', 'the weather', 'co-op prices', 'the greenhouse', 'family help']},
        {'id': 'fishing-crew', 'name': 'Fishing boat crew', 'sector': 'fishing', 'schedule': 'early',
         'pay': '$$', 'summary': 'Working the hairtail, mackerel or yellowtail boats out of Seongsan, Hallim or '
                                 'Moseulpo, then the early auction at the harbour.',
         'themes': ['the catch', 'the weather', 'the auction', 'the crew']},
    ],
    'climate': {
        'summary': 'Humid subtropical and very windy: mild, grey winters with northwest winds and occasional '
                   'snow showers, a warm spring, the jangma rains from mid-June into July, a hot and humid August '
                   'with typhoons possible into September, and a clear, mild autumn. Hallasan is much colder and '
                   'snow-capped in winter.',
        'months': [
            {'high_f': 48, 'low_f': 38, 'rain_days': 15, 'note': 'Coldest month; windy, grey, snow on Hallasan.'},
            {'high_f': 51, 'low_f': 40, 'rain_days': 12, 'note': 'Chilly; camellias and early canola.'},
            {'high_f': 57, 'low_f': 45, 'rain_days': 11, 'note': 'Canola and the first cherry blossoms.'},
            {'high_f': 65, 'low_f': 52, 'rain_days': 10, 'note': 'Mild spring; cherry blossoms early in the month.'},
            {'high_f': 72, 'low_f': 60, 'rain_days': 10, 'note': 'Warm and green; azaleas on Hallasan.'},
            {'high_f': 78, 'low_f': 67, 'rain_days': 12, 'note': 'Humid; the jangma rains arrive mid-month.'},
            {'high_f': 85, 'low_f': 76, 'rain_days': 12, 'note': 'Hot and sticky; beaches open.'},
            {'high_f': 87, 'low_f': 77, 'rain_days': 13, 'note': 'Hottest month; typhoons possible.'},
            {'high_f': 80, 'low_f': 70, 'rain_days': 11, 'note': 'Warm; typhoon season tails off.'},
            {'high_f': 72, 'low_f': 61, 'rain_days': 7, 'note': 'Clear and mild; silver grass on the oreum.'},
            {'high_f': 62, 'low_f': 50, 'rain_days': 10, 'note': 'Cool; tangerine harvest begins.'},
            {'high_f': 52, 'low_f': 41, 'rain_days': 14, 'note': 'Windy and damp; tangerines everywhere.'},
        ],
        'source': CLIMATE,
    },
    'annual_events': [
        event('penguin-swim', 'Jeju Penguin Swim', [1], 'jungmun', 'Hundreds of people in costumes run into the '
              'winter sea at Jungmun Saekdal beach to start the year.'),
        event('seongsan-sunrise-festival', 'Seongsan Sunrise Festival', [12, 1], 'seongsan', 'New Year\'s Eve '
              'into New Year\'s Day at Ilchulbong, with music, a bonfire and a crowd climbing for the first '
              'sunrise of the year.'),
        event('seollal-visits', 'Seollal family visits', [1, 2], None, 'Over the lunar new year, families '
              'gather at the eldest relative\'s home for ancestral rites, rice-cake soup and bows to elders; '
              'flights to and from the island sell out.'),
        event('fire-festival', 'Jeju Fire Festival', [3], 'aewol', 'A spring festival at Saebyeol Oreum rooted '
              'in the old practice of burning pasture to clear pests; the hillside burning itself has been '
              'scaled back or called off in dry years.'),
        event('canola-festival', 'Jeju Canola Flower Festival', [3, 4], 'gasi', 'Fields of yellow canola and '
              'cherry blossoms along Noksan-ro, with photo spots, food stalls and music.'),
        event('cherry-blossom-festival', 'Jeju cherry blossom festival', [3, 4], 'old-jeju', 'King cherry '
              'trees, a species native to Hallasan, bloom along Jeonnong-ro and the university road, with night '
              'lights and stalls.'),
        event('april-3-memorial', 'April 3rd memorial day', [4], 'foothills', 'On April 3 the island remembers '
              'those killed in the 1947-1954 violence with a national memorial ceremony at the Peace Park; '
              'families visit, and it is a day for quiet rather than celebration.'),
        event('haenyeo-festival', 'Jeju Haenyeo Festival', [9, 10], 'gujwa', 'A festival at the Haenyeo Museum '
              'honouring the women divers, with diving demonstrations, songs and seafood.'),
        event('chuseok-visits', 'Chuseok homecoming', [9, 10], None, 'At the harvest festival families gather, '
              'tend ancestors\' graves in the fields, and make songpyeon; the island fills with visiting '
              'relatives.'),
        event('seogwipo-chilsimni-festival', 'Seogwipo Chilsimni Festival', [9, 10], 'seogwipo', 'Seogwipo\'s '
              'city festival, named for the "seventy li" of its coast, with parades, concerts and food stalls.'),
        event('tamna-cultural-festival', 'Tamna Cultural Festival', [10], 'tapdong', 'The island\'s big '
              'traditional culture festival, with folk performances, shaman rituals, a street parade and Jeju '
              'dialect contests.'),
        event('olle-walking-festival', 'Jeju Olle Walking Festival', [10, 11], 'seogwipo', 'Several days of '
              'group walks along Olle routes, with village food and performances at the rest stops.'),
        event('autumn-marathons', 'Autumn road races', [10, 11], None, 'Marathons, ultramarathons and fun runs '
              'around the island\'s coast roads draw runners from the mainland in the cool season.'),
        event('bangeo-festival', 'Moseulpo Yellowtail Festival', [11], 'daejeong', 'A harbour festival when '
              'the winter yellowtail come in, with fish-catching contests and raw-fish tastings.'),
        event('tangerine-festival', 'Seogwipo Citrus Festival', [11, 12], 'seogwipo', 'A winter festival around '
              'the citrus harvest with picking, juicing and tangerine-everything food.'),
    ],
    'local_color': [
        color('black-pork', 'Heukdwaeji (black pork)', 'dish', 'Jeju\'s black-haired pigs give thick, fatty '
              'pork grilled at the table and dipped in melted myeolchi-jeot, a bubbling anchovy sauce, with '
              'lettuce, garlic and kimchi.', ['black-pork-street', 'sinjeju-bbq', 'seongsan-galchi']),
        color('gogi-guksu', 'Gogi-guksu', 'dish', 'Thick noodles in milky pork-bone broth topped with slices of '
              'boiled pork, a cheap, filling island lunch.', ['noodle-street', 'hyeopjae-noodles', 'namwon-guksu']),
        color('jeonbok-juk', 'Jeonbok-juk (abalone porridge)', 'dish', 'Rice porridge cooked with abalone and its '
              'green innards, a gentle breakfast or recovery meal.', ['yongdam-abalone', 'hado-haenyeo-house',
              'aewol-seafood']),
        color('momguk', 'Momguk', 'dish', 'A thick pork-bone soup with sargassum seaweed, once served at village '
              'weddings and funerals.', ['gasi-dombe-gogi', 'namwon-guksu']),
        color('galchi', 'Galchi (hairtail)', 'dish', 'Silver hairtail is grilled whole, braised in a spicy '
              'galchi-jorim, or simmered with pumpkin in a clear galchi-guk that only Jeju makes.',
              ['seongsan-galchi', 'seogwipo-harbour-restaurants', 'hamdeok-seafood']),
        color('bingtteok', 'Bingtteok and omegi-tteok', 'dish', 'Market snacks: thin buckwheat crepes rolled '
              'around seasoned radish, and millet rice cakes coated in red beans.', ['dongmun-market',
              'olle-market']),
        color('tangerines', 'Tangerines everywhere', 'dish', 'Gamgyul mandarins fill every market and roadside '
              'stand in winter, followed by bumpy hallabong and cheonhyehyang; neighbours hand them out by the '
              'box.', ['olle-market', 'dongmun-market', 'tangerine-farm-cafes'], ['fall', 'winter', 'spring']),
        color('hallabong-drinks', 'Hallabong ade and tangerine lattes', 'drink', 'Cafes all over the island sell '
              'hallabong juice, ade and tangerine-flavoured lattes and cakes.', ['tangerine-farm-cafes',
              'aewol-cafe-street', 'sinjeju-cafes']),
        color('hallasan-soju', 'Hallasan soju', 'drink', 'The island\'s own soju, made with Jeju water; locals '
              'often ask for it by name, and the original is stronger than most mainland brands.',
              ['black-pork-street', 'dongmun-pocha']),
        color('udo-peanut', 'Udo peanut ice cream', 'dish', 'Soft-serve covered in crushed local peanuts, the '
              'thing everyone eats on a day trip to Udo.', ['udo-peanut-cafes']),
        color('honjeo-opsye', '"Honjeo opsye"', 'saying', 'Jeju dialect for "welcome, come quickly", painted on '
              'signs at the airport and port; the dialect is hard for mainlanders to follow and is now taught '
              'to keep it alive.'),
        color('pokssak-sogatsuda', '"Pokssak sogatsuda"', 'saying', 'Jeju dialect for "you worked so hard", a '
              'warm thanks to someone after a long effort.'),
        color('samda', 'Samda: the three abundances', 'custom', 'Jeju is called the island of three '
              'abundances, wind, stones and women, and of three absences: no thieves, no beggars and no gates.'),
        color('jeongnang', 'Jeongnang gate poles', 'custom', 'Instead of gates, old houses set three wooden '
              'poles across the entrance: how many are down says whether the family is home or away for long.',
              ['seongeup-village', 'jeju-folk-village']),
        color('dol-hareubang', 'Dol hareubang', 'other', 'Stone grandfathers carved from lava, with bulging eyes '
              'and hands on their belly, stand at old town gates and in miniature in every souvenir shop.',
              ['gwandeokjeong', 'seongeup-village', 'jeju-stone-park']),
        color('batdam', 'Batdam stone walls', 'other', 'Black lava-stone walls stacked without mortar wrap every '
              'field and grave, gapped so the wind blows through rather than knocking them down.',
              ['namwon', 'gimnyeong', 'gasi']),
        color('olle', 'Olle', 'other', 'In Jeju dialect an olle is the narrow lane from the street to a house; '
              'the name was given to the long-distance walking routes that circle the island, marked with blue '
              'and orange ribbons.', ['olle-center', 'olle-route-7', 'olle-route-20']),
        color('haenyeo', 'Haenyeo', 'custom', 'Women divers, many in their sixties and seventies, who free-dive '
              'for conch, abalone, sea urchin and seaweed under collective rules; listed by UNESCO as intangible '
              'heritage.', ['haenyeo-museum', 'seongsan-haenyeo-show', 'beophwan-haenyeo-house']),
        color('singugan', 'Singugan moving week', 'custom', 'Islanders traditionally move house only in the week '
              'from late January into early February when the household gods are said to be away, and the movers are booked solid.',
              seasons=['winter']),
        color('gwendang', 'Gwendang', 'custom', 'The web of relatives and in-laws on the island; at weddings and '
              'funerals the whole gwendang turns up, and people joke that everyone on Jeju is related.'),
        color('jeju-horses', 'Jeju horses', 'other', 'Small Jeju ponies, a protected breed, and racehorses graze '
              'the eastern grasslands and the slopes of Hallasan.', ['gasi-horse-riding', 'udobong',
              'songaksan']),
        color('oreum', 'Oreum', 'other', 'The island has some 360 small volcanic cones; climbing one at sunrise '
              'or sunset is a weekend habit.', ['darangshi-oreum', 'saebyeol-oreum', 'ttarabi-oreum']),
        color('five-day-markets', 'Five-day markets', 'shop', 'Town markets held on fixed dates every five days, '
              'with farm produce, fish, seedlings and food stalls, still the way many villages shop.',
              ['hallim-five-day-market', 'sehwa-market', 'daejeong-market']),
        color('convenience-stores', 'Convenience-store life', 'shop', 'CU, GS25 and 7-Eleven stores everywhere '
              'sell lunch boxes, triangle kimbap, Jeju-only snacks and cheap beer to drink at the tables outside.',
              ['airport-convenience']),
        color('jeju-sk-fc', 'Jeju SK FC', 'team', 'The island\'s K League football club, long known as Jeju '
              'United, plays in orange at the World Cup stadium in Seogwipo.', ['world-cup-stadium'],
              ['spring', 'summer', 'fall']),
    ],
    'prices': [
        price('coffee', 'Americano', 3000, 5500, 'a cup'),
        price('latte', 'Latte', 4500, 7000),
        price('hallabong-ade', 'Hallabong ade or juice', 6000, 8500, 'a glass at a cafe'),
        price('cheap-lunch', 'Cheap lunch', 8000, 12000, 'gogi-guksu, kimbap or a set meal'),
        price('dinner', 'Mid-range dinner', 20000, 40000, 'for one'),
        price('black-pork', 'Black pork barbecue', 22000, 32000, 'a serving of about 150-200 g'),
        price('abalone-porridge', 'Abalone porridge', 14000, 20000, 'a bowl'),
        price('soju', 'Soju', 5000, 6000, 'a bottle at a restaurant'),
        price('beer', 'Draft beer', 4500, 8000, 'a 500 ml glass'),
        price('cocktail', 'Cocktail', 13000, 20000),
        price('groceries', 'Groceries', 70000, 120000, 'a week, one person'),
        price('transit', 'Island bus fare', 1150, 1200, 'one way; card or cash'),
        price('taxi', 'Taxi across Jeju City', 7000, 15000),
        price('udo-ferry', 'Udo ferry', 10000, 14000, 'round trip with island entry fee'),
        price('movie', 'Movie ticket', 14000, 16000),
        price('gym', 'Gym membership', 50000, 100000, 'a month'),
        price('jjimjilbang', 'Jjimjilbang entry', 10000, 16000),
        price('tangerines', 'Box of tangerines', 15000, 35000, 'about 5 kg, by grade and season'),
        price('wage', 'Day\'s wage', 90000, 130000, 'a day of ordinary full-time work'),
    ],
    'water': [
        {'kind': 'sea', 'name': 'Jeju Strait', 'side': 'north', 'width_km': 6},
        {'kind': 'sea', 'name': 'East China Sea', 'side': 'south', 'width_km': 6},
    ],
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
