"""Curated Osaka data. Run `python scripts/world/osaka.py` to rewrite the shipped JSON."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'cities' / 'osaka.json'
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


def hub(id, name, neighborhoods, sectors, summary):
    return {'id': id, 'name': name, 'neighborhoods': neighborhoods, 'sectors': sectors, 'summary': summary,
            'source': S}


def line(id, name, kind, summary):
    return {'id': id, 'name': name, 'kind': kind, 'summary': summary, 'source': S}


def event(id, name, months, hood, summary):
    return {'id': id, 'name': name, 'months': months, 'neighborhood': hood, 'summary': summary, 'source': S}


def color(id, name, kind, summary, places=(), seasons=()):
    return {'id': id, 'name': name, 'kind': kind, 'summary': summary, 'places': list(places),
            'seasons': list(seasons), 'source': S}


def price(id, item, low, high, per=''):
    return {'id': id, 'item': item, 'low': low, 'high': high, 'per': per, 'source': S}


def month(high_c, low_c, rain_days, note):
    """Climate in the schema's Fahrenheit, from Celsius normals."""
    return {'high_f': round(high_c * 9 / 5 + 32), 'low_f': round(low_c * 9 / 5 + 32), 'rain_days': rain_days,
            'note': note}


ALL = ['solo', 'friends', 'date', 'family']
ADULT = ['solo', 'friends', 'date']
DAY = ['morning', 'afternoon']
DAYTIME = ['morning', 'afternoon', 'evening']
LUNCH = ['afternoon', 'evening']
DINNER = ['evening']
NIGHT = ['evening', 'late']
WARM = ['spring', 'summer', 'fall']

# Rents per month in yen: one-room (studio), 1LDK (one bedroom) and 2LDK (two bedrooms).
VERY_HIGH = ([75000, 110000], [130000, 220000], [200000, 350000])
HIGH = ([62000, 90000], [105000, 170000], [150000, 260000])
MID = ([52000, 78000], [90000, 145000], [130000, 220000])
LOWER_MID = ([46000, 68000], [78000, 120000], [105000, 170000])
LOW = ([38000, 58000], [62000, 98000], [85000, 140000])

CITY = {
    'schema_version': 1, 'id': 'osaka', 'name': 'Osaka', 'region': 'Osaka Prefecture', 'country': 'Japan',
    'timezone': 'Asia/Tokyo', 'aliases': ['Ōsaka', 'Naniwa', 'Osaka City', 'Osaka, Japan', '大阪'],
    'summary': 'Japan\'s merchant city on Osaka Bay: loud, friendly and food-obsessed, with neon over the '
               'Dotonbori canal, shotengai shopping arcades, manzai comedy, standing bars and a castle park, tied '
               'together by the Osaka Metro and a web of private railways.',
    'lat': 34.69, 'lon': 135.50,
    'currency': {'code': 'JPY', 'symbol': '¥', 'name': 'Japanese yen'},
    'rent_period': 'month',
    'speeds': {'walk': 4.5, 'car': 20, 'rideshare': 20, 'bus': 11, 'subway': 30, 'commuter-rail': 45,
               'monorail': 30, 'light-rail': 25, 'streetcar': 13, 'bike-share': 12},
    # Rough weights for residents' names (estimates, not census figures). `anglo` draws the local country's names,
    # here Japanese; the small East Asian share adds Zainichi Korean and Chinese families (Tsuruhashi, Ikuno).
    'names': {'mix': {'anglo': 9, 'east-asian': 0.5}},
    'sources': {
        S: {'kind': 'curated', 'title': 'Osaka places and neighborhoods written for Prospero Companion',
            'license': 'CC0-1.0', 'retrieved': '2026-10-10',
            'note': 'Well-known public places, institutions and employers from general knowledge. Businesses open '
                    'and close and rents move: treat this as a snapshot for fiction. Rents are rounded estimates '
                    'of typical monthly asking ranges in yen, not listings. Coordinates are approximate '
                    'neighborhood centers. Names use common Hepburn spellings without macrons.'},
        CLIMATE: {'kind': 'curated', 'title': 'Approximate monthly climate for Osaka (Osaka Regional '
                                               'Meteorological Observatory)',
                  'license': 'CC0-1.0', 'retrieved': '2026-10-10',
                  'note': 'Rounded values in line with Japan Meteorological Agency 1991-2020 normals, converted to '
                          'Fahrenheit; rain days count days with 1 mm or more. Refresh with scripts/world when '
                          'network access to the JMA is available.'},
    },
    'neighborhoods': [
        # Kita (north of the center)
        hood('umeda', 'Umeda', 'Kita\'s hub around Osaka and Umeda stations: department stores, underground '
             'malls, office towers, Grand Front Osaka and a maze of izakaya and karaoke on Higashi-dori.',
             ['business', 'shopping', 'nightlife', 'central', 'transit-hub'], 34.703, 135.497, 'very-high',
             VERY_HIGH, ['tower-mansion', 'one-room-mansion', 'mansion'], 'high',
             ['midosuji', 'tanimachi', 'yotsubashi', 'jr-loop', 'hankyu', 'hanshin', 'rail-network', 'buses']),
        hood('nakazakicho', 'Nakazakicho and Chayamachi', 'Old wooden row houses that survived the war, turned '
             'into cafes, vintage shops and galleries a few minutes\' walk from Umeda, beside the theaters of '
             'Chayamachi.', ['artsy', 'retro', 'cafes', 'quiet'], 34.708, 135.506, 'mid', MID,
             ['nagaya', 'apartment', 'one-room-mansion'], 'high', ['tanimachi', 'hankyu', 'rail-network', 'buses']),
        hood('tenma', 'Tenma and Tenjinbashisuji', 'Tenjinbashisuji, the longest shopping street in Japan, runs '
             'past Osaka Tenmangu shrine and a warren of cheap, packed izakaya around JR Tenma station.',
             ['shotengai', 'izakaya', 'local', 'traditional'], 34.703, 135.512, 'mid', MID,
             ['mansion', 'one-room-mansion', 'apartment'], 'high',
             ['jr-loop', 'sakaisuji', 'tanimachi', 'rail-network', 'buses']),
        hood('fukushima', 'Fukushima', 'One stop west of Osaka station, a grid of small streets known across the '
             'city for izakaya, yakitori and oden, with the central wholesale market at Noda.',
             ['izakaya', 'food', 'young-professional', 'local'], 34.697, 135.485, 'high', HIGH,
             ['mansion', 'one-room-mansion', 'tower-mansion'], 'high',
             ['jr-loop', 'hanshin', 'sennichimae', 'rail-network', 'buses']),
        hood('nakanoshima', 'Nakanoshima', 'The island between the Dojima and Tosabori rivers: City Hall, the '
             'red-brick Central Public Hall, art museums, Festival Hall and a rose garden at the eastern tip.',
             ['cultural', 'riverside', 'business', 'architecture'], 34.692, 135.495, 'high',
             ([70000, 100000], [120000, 200000], [180000, 320000]), ['tower-mansion', 'mansion'], 'high',
             ['yotsubashi', 'midosuji', 'keihan', 'rail-network', 'buses']),
        hood('kitahama', 'Kitahama', 'The old financial quarter south of the Tosabori river, with the Osaka '
             'Exchange, Meiji and Taisho-era buildings and riverside terraces.',
             ['historic', 'business', 'riverside', 'cafes'], 34.689, 135.507, 'high', HIGH,
             ['mansion', 'tower-mansion'], 'high', ['sakaisuji', 'keihan', 'midosuji', 'rail-network', 'buses']),
        hood('honmachi', 'Honmachi and Semba', 'The weekday business district along Midosuji boulevard: '
             'trading houses, textile wholesalers, pharmaceutical head offices in Doshomachi and the green '
             'strip of Utsubo Park.', ['business', 'office', 'leafy', 'quiet-weekends'], 34.682, 135.500, 'high',
             ([65000, 92000], [110000, 180000], [160000, 280000]), ['mansion', 'tower-mansion'], 'high',
             ['midosuji', 'chuo', 'yotsubashi', 'sakaisuji', 'rail-network', 'buses']),
        # Minami (south of the center)
        hood('shinsaibashi', 'Shinsaibashi and Amerikamura', 'The covered Shinsaibashi-suji arcade and '
             'department stores on one side of Midosuji; on the other, Amerikamura\'s thrift shops, street '
             'fashion and clubs, running into Horie\'s boutiques.', ['shopping', 'fashion', 'youth', 'nightlife'],
             34.673, 135.499, 'high', HIGH, ['one-room-mansion', 'mansion'], 'high',
             ['midosuji', 'nagahori-tsurumi-ryokuchi', 'yotsubashi', 'rail-network', 'buses']),
        hood('dotonbori', 'Dotonbori', 'The canal-side strip of giant food signs, the Glico running man, '
             'takoyaki stands and theaters, packed until late every night; the stone alley of Hozenji sits just '
             'behind it.', ['neon', 'food', 'touristy', 'nightlife'], 34.669, 135.502, 'mid', MID,
             ['one-room-mansion', 'mansion'], 'high',
             ['midosuji', 'sennichimae', 'yotsubashi', 'nankai', 'kintetsu', 'rail-network', 'buses']),
        hood('namba', 'Namba', 'Minami\'s rail hub: Nankai and Kintetsu terminals, Namba Parks, Takashimaya, '
             'the Sennichimae arcades and Namba Grand Kagetsu, the home of Yoshimoto comedy.',
             ['transit-hub', 'comedy', 'shopping', 'food'], 34.665, 135.501, 'mid', MID,
             ['one-room-mansion', 'mansion', 'tower-mansion'], 'high',
             ['midosuji', 'sennichimae', 'yotsubashi', 'nankai', 'kintetsu', 'rail-network', 'buses']),
        hood('nipponbashi', 'Nipponbashi and Den Den Town', 'Kuromon Market\'s covered fish and produce stalls, '
             'the National Bunraku Theatre, and Den Den Town\'s electronics, anime, retro game and maid cafe '
             'strip along Sakaisuji.', ['otaku', 'market', 'electronics', 'theater'], 34.660, 135.506, 'mid',
             LOWER_MID, ['one-room-mansion', 'mansion'], 'high',
             ['sakaisuji', 'sennichimae', 'kintetsu', 'rail-network', 'buses']),
        hood('shinsekai', 'Shinsekai', 'A retro entertainment district built in 1912 under Tsutenkaku tower, all '
             'kushikatsu counters, shogi parlors and old-fashioned signs, between Tennoji Park and Spa World.',
             ['retro', 'food', 'working-class', 'touristy'], 34.652, 135.506, 'low', LOW,
             ['apartment', 'one-room-mansion'], 'high',
             ['sakaisuji', 'midosuji', 'jr-loop', 'nankai', 'hankai', 'rail-network', 'buses']),
        hood('tennoji', 'Tennoji and Abeno', 'A southern hub around Tennoji station and Abeno Harukas, Japan\'s '
             'second-tallest building, with Shitennoji temple, Tennoji Park and the zoo.',
             ['transit-hub', 'shopping', 'temples', 'family'], 34.646, 135.514, 'mid',
             ([55000, 80000], [95000, 155000], [140000, 240000]), ['mansion', 'tower-mansion', 'apartment'],
             'high', ['midosuji', 'tanimachi', 'jr-loop', 'kintetsu', 'hankai', 'rail-network', 'buses']),
        hood('tsuruhashi', 'Tsuruhashi and Ikuno Koreatown', 'Where the smell of yakiniku greets you on the '
             'platform: a covered market of kimchi, hanbok and fish stalls, and the Koreatown shopping street, '
             'home to one of Japan\'s oldest Zainichi Korean communities.',
             ['multicultural', 'market', 'food', 'working-class'], 34.663, 135.533, 'low',
             ([40000, 60000], [65000, 100000], [90000, 140000]), ['apartment', 'mansion', 'detached-house'],
             'high', ['sennichimae', 'jr-loop', 'kintetsu', 'rail-network', 'buses']),
        hood('osaka-castle', 'Osaka Castle and Morinomiya', 'The castle\'s moats, stone walls and huge park, '
             'with Osaka-jo Hall, the history museum and residential Morinomiya to the south-east.',
             ['historic', 'park', 'running', 'family'], 34.684, 135.528, 'high',
             ([60000, 85000], [100000, 160000], [150000, 250000]), ['mansion', 'tower-mansion', 'apartment'],
             'high', ['tanimachi', 'chuo', 'nagahori-tsurumi-ryokuchi', 'jr-loop', 'rail-network', 'buses']),
        hood('kyobashi', 'Kyobashi', 'A busy junction of the Loop Line and Keihan railway, famous for cheap '
             'standing bars that open in the morning, with the cherry trees of Sakuranomiya along the river.',
             ['drinking', 'working-class', 'transit-hub', 'riverside'], 34.697, 135.534, 'mid', LOWER_MID,
             ['mansion', 'one-room-mansion', 'apartment'], 'high',
             ['jr-loop', 'keihan', 'nagahori-tsurumi-ryokuchi', 'rail-network', 'buses']),
        hood('juso', 'Juso', 'A gritty, friendly Hankyu junction just across the Yodo river from Umeda, with '
             'shopping arcades, late bars, a famous negiyaki shop and the fireworks on the riverbank.',
             ['gritty', 'nightlife', 'riverside', 'cheap'], 34.720, 135.484, 'low',
             ([42000, 62000], [70000, 110000], [95000, 150000]), ['apartment', 'one-room-mansion', 'mansion'],
             'high', ['hankyu', 'rail-network', 'buses']),
        hood('bay-area', 'Bentencho and the Bay Area', 'The waterfront west of the center: Kaiyukan aquarium '
             'and the Tempozan wheel, Universal Studios Japan across the river at Sakurajima, Kyocera Dome, the '
             'port, and the Okinawan eateries of Taisho.', ['waterfront', 'family', 'theme-park', 'port'],
             34.662, 135.445, 'mid', ([48000, 70000], [80000, 125000], [110000, 180000]),
             ['mansion', 'public-housing', 'apartment'], 'medium',
             ['chuo', 'jr-loop', 'jr-yumesaki', 'new-tram', 'rail-network', 'buses']),
        hood('sumiyoshi', 'Sumiyoshi', 'A calm southern district around Sumiyoshi Taisha, one of Japan\'s oldest '
             'shrines, with Nagai Park\'s stadiums and the Osaka Metropolitan University campus nearby.',
             ['traditional', 'residential', 'shrines', 'students'], 34.613, 135.496, 'mid',
             ([45000, 65000], [75000, 115000], [100000, 160000]), ['detached-house', 'mansion', 'apartment'],
             'medium', ['midosuji', 'nankai', 'hankai', 'rail-network', 'buses']),
        hood('nishinari', 'Nishinari and Kamagasaki', 'Osaka\'s poorest and oldest working district, where '
             'Kamagasaki\'s day labourers, now mostly elderly, live in small lodging-house rooms beside cheap '
             'diners, budget hostels and a strong network of community support groups.',
             ['working-class', 'cheap', 'community', 'changing'], 34.644, 135.500, 'low',
             ([28000, 45000], [50000, 80000], [65000, 110000]), ['apartment', 'doya', 'public-housing'], 'high',
             ['midosuji', 'sakaisuji', 'nankai', 'jr-loop', 'hankai', 'rail-network', 'buses']),
        # Near suburbs and neighbours
        hood('suita', 'Suita', 'A northern suburb and university town: Expo \'70 Commemorative Park and the Tower '
             'of the Sun, Osaka University\'s main campus, Kansai University and Gamba Osaka\'s stadium.',
             ['suburban', 'students', 'family', 'parks'], 34.785, 135.520, 'mid', LOWER_MID,
             ['mansion', 'danchi', 'detached-house', 'student-housing'], 'medium',
             ['midosuji', 'hankyu', 'osaka-monorail', 'rail-network', 'buses']),
        hood('toyonaka-minoh', 'Toyonaka and Minoh', 'Leafy commuter towns on the Hankyu lines below the hills, '
             'with Hattori Ryokuchi park, the Itami airport runway and the Minoo waterfall walk.',
             ['suburban', 'leafy', 'family', 'nature'], 34.810, 135.470, 'mid',
             ([50000, 70000], [85000, 130000], [120000, 200000]), ['detached-house', 'mansion', 'danchi'],
             'medium', ['hankyu', 'midosuji', 'osaka-monorail', 'rail-network', 'buses']),
        hood('sakai', 'Sakai', 'Osaka\'s southern neighbour, a medieval free port turned industrial city, known '
             'for keyhole-shaped imperial tombs, kitchen knives, Sen no Rikyu\'s tea and Sharp\'s bayside '
             'head office.', ['historic', 'suburban', 'crafts', 'industrial'], 34.573, 135.483, 'low',
             ([40000, 58000], [65000, 100000], [85000, 140000]), ['detached-house', 'mansion', 'danchi'],
             'medium', ['nankai', 'hankai', 'midosuji', 'rail-network', 'buses']),
    ],
    'transit': [
        # Specific metro lines come first, so a commute names the line when both ends share one.
        line('midosuji', 'Osaka Metro Midosuji Line', 'subway', 'The red north-south trunk line under Midosuji '
             'boulevard, from Esaka (through to Senri-Chuo and Minoh) via Umeda, Namba and Tennoji to Nakamozu in '
             'Sakai; standing room only at rush hour.'),
        line('tanimachi', 'Osaka Metro Tanimachi Line', 'subway', 'The purple line from Dainichi through Higashi-'
             'Umeda, Tenmabashi, Tanimachi 4-chome and Tennoji to Yaominami.'),
        line('yotsubashi', 'Osaka Metro Yotsubashi Line', 'subway', 'The blue line from Nishi-Umeda down the west '
             'side via Higobashi and Yotsubashi to Namba and Suminoekoen.'),
        line('chuo', 'Osaka Metro Chuo Line', 'subway', 'The green east-west line from Nagata through Morinomiya, '
             'Tanimachi 4-chome and Honmachi to Osakako and Yumeshima.'),
        line('sennichimae', 'Osaka Metro Sennichimae Line', 'subway', 'The pink line from Nodahanshin through '
             'Namba, Nipponbashi and Tsuruhashi to Minami-Tatsumi.'),
        line('sakaisuji', 'Osaka Metro Sakaisuji Line', 'subway', 'The brown line from Tenjinbashisuji 6-chome '
             'through Kitahama and Nipponbashi to Dobutsuen-mae and Tengachaya, running through to Hankyu '
             'trains for Kyoto.'),
        line('nagahori-tsurumi-ryokuchi', 'Osaka Metro Nagahori Tsurumi-ryokuchi Line', 'subway', 'The light '
             'green line from Taisho through Shinsaibashi, Morinomiya and Kyobashi to Kadoma-minami.'),
        line('imazatosuji', 'Osaka Metro Imazatosuji Line', 'subway', 'The orange line through the eastern '
             'wards from Itakano to Imazato, linking with the Sennichimae Line.'),
        line('new-tram', 'New Tram (Nanko Port Town Line)', 'light-rail', 'Driverless rubber-tyred trains on '
             'an elevated guideway from Cosmosquare through the Nanko port district to Suminoekoen.'),
        line('jr-loop', 'JR Osaka Loop Line', 'commuter-rail', 'The orange loop around the center through '
             'Osaka, Kyobashi, Tsuruhashi, Tennoji, Shin-Imamiya, Bentencho and Fukushima; trains run both ways.'),
        line('jr-yumesaki', 'JR Yumesaki Line', 'commuter-rail', 'The short branch from Nishikujo to Universal '
             'City and Sakurajima, often run with character-wrapped trains.'),
        line('hankyu', 'Hankyu Railway', 'commuter-rail', 'Maroon trains from Osaka-umeda to Kyoto, Kobe and '
             'Takarazuka, with branches to Minoo and Senri; every line crosses the river at Juso.'),
        line('hanshin', 'Hanshin Electric Railway', 'commuter-rail', 'The coastal line from Osaka-umeda to Kobe '
             'by way of Koshien Stadium, and the Namba Line to Nara through Kintetsu.'),
        line('keihan', 'Keihan Electric Railway', 'commuter-rail', 'From Nakanoshima and Yodoyabashi along the '
             'Yodo river through Kyobashi, Kadoma and Hirakata to Kyoto.'),
        line('nankai', 'Nankai Electric Railway', 'commuter-rail', 'From Namba south through Shin-Imamiya, '
             'Sumiyoshi Taisha and Sakai, and out to Kansai Airport and Wakayama.'),
        line('kintetsu', 'Kintetsu Railway', 'commuter-rail', 'Japan\'s largest private railway, from Osaka-'
             'Namba, Osaka-Uehommachi and Osaka-Abenobashi to Nara, Ise and Nagoya, through Tsuruhashi.'),
        line('osaka-monorail', 'Osaka Monorail', 'monorail', 'An elevated monorail in an arc across the northern '
             'suburbs, from Osaka Airport through Senri-Chuo and Banpaku-kinen-koen (Expo park).'),
        line('hankai', 'Hankai Tramway', 'streetcar', 'Osaka\'s last streetcars, rattling from Tennoji-ekimae and '
             'Ebisucho through Sumiyoshi to Sakai.'),
        # Changing trains, and everything that isn't a train.
        line('rail-network', 'Osaka trains, changing lines', 'subway', 'Metro, JR and private railways meet at '
             'Umeda, Namba, Tennoji, Kyobashi and Tsuruhashi; most trips across town change trains once or twice '
             'on one ICOCA card.'),
        line('buses', 'City and private buses', 'bus', 'Osaka City Bus routes in the city, and Hankyu, Keihan, '
             'Kintetsu and Nankai buses in the suburbs; boarded at the middle door, paid at the front.'),
        line('bike-share', 'Bike share and mamachari', 'bike-share', 'Docked share bikes around the center, and '
             'everyone\'s own city bicycle with a basket and a child seat, parked in vast station lots.'),
    ],
    'places': [
        # Umeda
        place('umeda-sky-building', 'Umeda Sky Building Floating Garden Observatory', 'attraction', 'umeda',
              'Open-air rooftop deck joining two towers forty floors up, with night views over the Yodo river.',
              ['views', 'architecture', 'sunset', 'date-spot'], '$$', 'mixed', ['date', 'friends', 'family'],
              ['afternoon', 'evening', 'late']),
        place('takimi-koji', 'Takimi Koji', 'restaurant', 'umeda', 'A recreated Showa-era alley of okonomiyaki, '
              'kushikatsu and izakaya counters in the basement of the Umeda Sky Building.',
              ['retro', 'okonomiyaki', 'kushikatsu'], '$$', 'indoor', ALL, LUNCH, cuisine='japanese'),
        place('hep-five-ferris-wheel', 'HEP FIVE Ferris Wheel', 'attraction', 'umeda', 'Red Ferris wheel growing '
              'out of the roof of a youth fashion mall, fifteen minutes around above Umeda.',
              ['views', 'date-spot', 'shopping'], '$', 'indoor', ['date', 'friends', 'family'], DAYTIME + ['late']),
        place('grand-front-osaka', 'Grand Front Osaka', 'shopping', 'umeda', 'Shops, restaurants and offices '
              'north of Osaka station, beside the Umekita lawns.', ['shopping', 'restaurants', 'rainy-day'], '$$',
              'indoor', ALL, DAYTIME),
        place('umekita-park', 'Umekita Park', 'park', 'umeda', 'The large new park on the old freight yard north '
              'of Osaka station, with lawns, water play and events in front of the towers.',
              ['lawn', 'picnic', 'new', 'events'], 'free', 'outdoor', ALL, DAYTIME),
        place('hankyu-umeda-food-hall', 'Hankyu Umeda Main Store food hall', 'market', 'umeda', 'The busiest '
              'depachika in the city: bento, sweets, pickles and gift boxes, with the counters marked down near '
              'closing time.', ['depachika', 'sweets', 'bento', 'gifts'], '$$', 'indoor', ALL, DAYTIME,
              cuisine='japanese'),
        place('hanshin-umeda-food-hall', 'Hanshin Umeda Main Store food hall', 'market', 'umeda', 'The everyday '
              'department store basement, known for its long-running ikayaki squid-pancake stand.',
              ['depachika', 'ikayaki', 'snacks'], '$', 'indoor', ALL, DAYTIME, cuisine='japanese'),
        place('shin-umeda-shokudogai', 'Shin-Umeda Shokudogai', 'restaurant', 'umeda', 'A cramped two-level '
              'warren of cheap eateries and standing bars under the JR tracks, open since 1950.',
              ['cheap-eats', 'standing-bar', 'retro'], '$', 'indoor', ['solo', 'friends', 'coworkers'], NIGHT,
              cuisine='japanese'),
        place('higashi-dori', 'Higashi-dori shopping street', 'nightlife', 'umeda', 'Umeda\'s nightlife arcade of '
              'izakaya chains, karaoke boxes, game centers and bars, loud until the last trains.',
              ['karaoke', 'izakaya', 'arcade'], '$$', 'indoor', ['friends', 'coworkers'], NIGHT),
        # Nakazakicho and Chayamachi
        place('salon-de-amanto', 'Salon de AManTo', 'cafe', 'nakazakicho', 'A ramshackle cafe and arts space in a '
              'century-old wooden house that helped start Nakazakicho\'s revival.', ['retro', 'arts', 'cozy'],
              '$', 'indoor', ADULT, DAYTIME, cuisine='cafe'),
        place('nakazakicho-nagaya-cafes', 'Nakazakicho row-house cafes', 'cafe', 'nakazakicho', 'Tiny cafes and '
              'sweet shops tucked into converted nagaya along the narrow lanes, each seating a handful.',
              ['cozy', 'retro', 'sweets'], '$', 'indoor', ['solo', 'date', 'friends'], DAY, cuisine='cafe'),
        place('nakazakicho-vintage', 'Nakazakicho vintage and zakka shops', 'shopping', 'nakazakicho', 'Secondhand '
              'clothes, handmade goods and small galleries in old houses.', ['vintage', 'crafts', 'browsing'],
              '$$', 'indoor', ADULT, DAY),
        place('umeda-arts-theater', 'Umeda Arts Theater', 'venue', 'nakazakicho', 'Large theater in Chayamachi '
              'for musicals, plays and touring productions.', ['musicals', 'theater'], '$$$', 'indoor',
              ['date', 'friends', 'family'], ['afternoon', 'evening']),
        place('chayamachi-spice-curry', 'Chayamachi spice curry counters', 'restaurant', 'nakazakicho', 'Small '
              'counters serving Osaka-style spice curry, several curries on one plate with rice, at lunch.',
              ['curry', 'lunch', 'local-trend'], '$', 'indoor', ['solo', 'friends', 'coworkers'], LUNCH,
              cuisine='curry'),
        place('nakazakicho-wine-bars', 'Nakazakicho natural wine and craft bars', 'bar', 'nakazakicho', 'A few '
              'snug bars in old houses pouring natural wine and craft beer to a small crowd.',
              ['wine', 'craft-beer', 'cozy'], '$$', 'indoor', ADULT, NIGHT),
        place('nakazakicho-izakaya', 'Nakazakicho back-street izakaya', 'restaurant', 'nakazakicho', 'Neighbourhood '
              'izakaya and yakitori grills on the streets between the station and the tracks.',
              ['izakaya', 'yakitori'], '$$', 'indoor', ['friends', 'coworkers', 'date'], DINNER,
              cuisine='izakaya'),
        # Tenma and Tenjinbashisuji
        place('tenjinbashisuji', 'Tenjinbashisuji Shopping Street', 'shopping', 'tenma', 'About 2.6 km of '
              'covered arcade, the longest in Japan: croquettes, tea shops, cheap clothes and everything else.',
              ['shotengai', 'street-food', 'rainy-day'], '$', 'indoor', ALL, DAYTIME),
        place('osaka-tenmangu', 'Osaka Tenmangu', 'temple', 'tenma', 'The shrine to Sugawara no Michizane, god of '
              'learning, where students pray before exams and the Tenjin Matsuri begins.',
              ['shrine', 'festival', 'plum-blossom'], 'free', 'outdoor', ALL, DAYTIME),
        place('tenma-tenjin-hanjotei', 'Tenma Tenjin Hanjotei', 'venue', 'tenma', 'A rakugo theater beside '
              'the shrine, with storytellers on stage every day.', ['rakugo', 'comedy', 'traditional'], '$$',
              'indoor', ['solo', 'date', 'friends'], ['afternoon', 'evening']),
        place('osaka-museum-of-housing', 'Osaka Museum of Housing and Living', 'museum', 'tenma', 'A full-size '
              'Edo-period Osaka street indoors, with houses to walk into and kimono to try on.',
              ['history', 'rainy-day', 'kimono'], '$', 'indoor', ALL, DAY),
        place('tenma-izakaya', 'Tenma izakaya alleys', 'bar', 'tenma', 'Dozens of cheap, crowded izakaya, '
              'standing bars and seafood counters around JR Tenma station, spilling into the street.',
              ['izakaya', 'standing-bar', 'cheap'], '$', 'mixed', ['friends', 'coworkers', 'solo'], NIGHT),
        place('harukoma-sushi', 'Harukoma', 'restaurant', 'tenma', 'A cheap, popular sushi counter on '
              'Tenjinbashisuji with a queue at most hours.', ['sushi', 'queue', 'local-favorite'], '$$', 'indoor',
              ['solo', 'friends', 'date'], LUNCH, cuisine='sushi'),
        place('nakamuraya-croquette', 'Nakamuraya', 'market', 'tenma', 'Takeaway croquette shop on the arcade, '
              'famous for hot, cheap potato korokke.', ['croquette', 'street-food', 'cheap'], '$', 'indoor', ALL,
              DAY, cuisine='japanese'),
        place('tenma-ichiba', 'Tenma Market', 'market', 'tenma', 'Old covered fresh market of fish, vegetables '
              'and pickles off the arcade, with cheap eateries round about.', ['market', 'fish', 'produce'], '$',
              'indoor', ALL, DAY),
        place('ogimachi-pool', 'Ogimachi Pool', 'fitness', 'tenma', 'Municipal indoor pool and gym in Ogimachi '
              'Park, cheap per visit.', ['swimming', 'gym', 'municipal'], '$', 'indoor', ['solo', 'friends',
              'family'], DAYTIME),
        place('mint-bureau-cherry-passage', 'Japan Mint cherry blossom passage', 'garden', 'tenma', 'For one week '
              'in April the Mint opens its riverside lane of late-blooming cherry varieties to the public.',
              ['cherry-blossom', 'seasonal', 'free'], 'free', 'outdoor', ALL, DAYTIME, ['spring']),
        place('tenma-kissaten', 'Tenjinbashisuji kissaten', 'cafe', 'tenma', 'Old coffee shops along the arcade '
              'with morning sets, mix juice and regulars reading the paper.', ['kissaten', 'morning-set', 'retro'],
              '$', 'indoor', ['solo', 'friends'], DAY, cuisine='kissaten'),
        # Fukushima
        place('fukushima-izakaya', 'Fukushima izakaya streets', 'bar', 'fukushima', 'Back streets of small '
              'izakaya, yakitori grills and wine bars between JR Fukushima and the Hanshin line.',
              ['izakaya', 'yakitori', 'hopping'], '$$', 'indoor', ['friends', 'coworkers', 'date'], NIGHT),
        place('hanakujira', 'Hanakujira', 'restaurant', 'fukushima', 'Oden shop with a famous queue for its '
              'dashi-soaked daikon, tofu and beef tendon.', ['oden', 'queue', 'local-favorite'], '$$', 'indoor',
              ['friends', 'date', 'solo'], DINNER, ['fall', 'winter', 'spring'], cuisine='oden'),
        place('fukushima-standing-bars', 'Fukushima standing bars under the tracks', 'bar', 'fukushima', 'Tiny '
              'tachinomi counters beneath the JR viaduct where office workers stop for a highball and skewers.',
              ['standing-bar', 'cheap', 'after-work'], '$', 'indoor', ['solo', 'coworkers', 'friends'], NIGHT),
        place('osaka-central-wholesale-market', 'Osaka Municipal Central Wholesale Market', 'market', 'fukushima',
              'The city\'s main fish and produce market at Noda, busiest before dawn; its restaurant row is '
              'open to the public.', ['fish', 'market', 'early-morning'], '$$', 'indoor', ['solo', 'friends'],
              ['morning']),
        place('endo-sushi', 'Endo Sushi', 'restaurant', 'fukushima', 'Early-morning sushi counter by the central '
              'market, serving plates of five pieces from the day\'s catch.', ['sushi', 'breakfast',
              'market'], '$$', 'indoor', ['solo', 'friends', 'date'], ['morning'], cuisine='sushi'),
        # Nakanoshima
        place('nakanoshima-park', 'Nakanoshima Park', 'park', 'nakanoshima', 'Riverside lawns and a rose garden '
              'at the eastern end of the island, Osaka\'s first public park.', ['roses', 'riverside', 'picnic'],
              'free', 'outdoor', ALL, DAYTIME),
        place('central-public-hall', 'Osaka City Central Public Hall', 'landmark', 'nakanoshima', 'Red-brick '
              'and granite hall from 1918, paid for by a stockbroker\'s gift, still used for concerts and '
              'lectures.', ['architecture', 'history', 'concerts'], 'free', 'mixed', ALL, DAYTIME),
        place('nakanoshima-library', 'Osaka Prefectural Nakanoshima Library', 'library', 'nakanoshima', 'The '
              'domed 1904 library beside City Hall, with business and Osaka history collections.',
              ['library', 'architecture', 'quiet'], 'free', 'indoor', ['solo'], DAY),
        place('nakanoshima-museum-of-art', 'Nakanoshima Museum of Art, Osaka', 'museum', 'nakanoshima', 'A black '
              'box of a museum opened in 2022, with modern art, design and big touring shows.',
              ['art', 'design', 'rainy-day'], '$$', 'indoor', ALL, DAYTIME),
        place('festival-hall', 'Festival Hall', 'venue', 'nakanoshima', 'Concert hall with famous acoustics, '
              'rebuilt in 2013 inside a skyscraper, for orchestras, pop shows and kabuki.',
              ['concerts', 'classical', 'pop'], '$$$', 'indoor', ['date', 'friends', 'solo'], ['evening']),
        place('takamura-wine-coffee', 'Takamura Wine & Coffee Roasters', 'cafe', 'nakanoshima', 'A warehouse '
              'south of Higobashi that roasts its own coffee and sells wine, with long tables to linger at.',
              ['specialty-coffee', 'wine', 'warehouse'], '$$', 'indoor', ['solo', 'date', 'friends'],
              DAYTIME, cuisine='cafe'),
        place('festival-city-dining', 'Festival City restaurant floors', 'restaurant', 'nakanoshima', 'Restaurants '
              'and cafes in the twin Festival towers, from set lunches to river-view dinners.',
              ['lunch', 'views', 'after-work'], '$$$', 'indoor', ['coworkers', 'date', 'friends'], LUNCH,
              cuisine='japanese'),
        place('nakanoshima-riverside-bars', 'Nakanoshima riverside bars', 'bar', 'nakanoshima', 'A handful of '
              'bars and bistros looking onto the Dojima and Tosabori rivers, with terraces in fine weather.',
              ['riverside', 'cocktails', 'after-work'], '$$$', 'mixed', ['date', 'coworkers'], NIGHT),
        place('nakanoshima-bistros', 'Higobashi bistros and izakaya', 'restaurant', 'nakanoshima', 'Small '
              'French bistros, wine bars and izakaya around Higobashi where office workers have dinner.',
              ['bistro', 'izakaya', 'after-work'], '$$$', 'indoor', ['date', 'coworkers'], DINNER,
              cuisine='bistro'),
        place('nakanoshima-park-cafes', 'Nakanoshima Park cafes', 'cafe', 'nakanoshima', 'Cafes and kiosks by '
              'the rose garden and the riverside lawns.', ['coffee', 'riverside', 'park-view'], '$', 'mixed', ALL,
              DAYTIME, cuisine='cafe'),
        # Kitahama
        place('kitahama-retro', 'Kitahama Retro', 'cafe', 'kitahama', 'An English-style tea room in a tiny 1912 '
              'brick building facing the river, known for afternoon tea and scones.',
              ['afternoon-tea', 'historic', 'queue'], '$$', 'indoor', ['date', 'friends', 'solo'], DAY,
              cuisine='tea-room'),
        place('brooklyn-roasting-kitahama', 'Brooklyn Roasting Company Kitahama', 'cafe', 'kitahama', 'Big, airy '
              'coffee shop facing the Tosabori river, with seats on the riverside terrace.',
              ['coffee', 'riverside', 'laptop'], '$', 'mixed', ['solo', 'friends', 'date'], DAYTIME,
              cuisine='cafe'),
        place('kitahama-terrace', 'Kitahama Terrace', 'restaurant', 'kitahama', 'Wooden decks along the Tosabori '
              'river behind cafes and restaurants, open from spring to autumn.', ['riverside', 'terrace',
              'seasonal'], '$$', 'outdoor', ['date', 'friends', 'coworkers'], LUNCH, WARM, cuisine='various'),
        place('tekijuku', 'Tekijuku', 'museum', 'kitahama', 'The Edo-period house of Ogata Koan\'s school of Dutch '
              'medicine, where Fukuzawa Yukichi studied; an ancestor of Osaka University.',
              ['history', 'medicine', 'architecture'], '$', 'indoor', ['solo', 'date'], DAY),
        place('kitahama-curry-counters', 'Kitahama and Doshomachi lunch counters', 'restaurant', 'kitahama',
              'Spice curry, soba and teishoku counters with office-worker queues from noon to one.',
              ['lunch', 'curry', 'soba'], '$', 'indoor', ['solo', 'coworkers'], ['afternoon'], cuisine='japanese'),
        place('kitahama-sake-bars', 'Kitahama sake and wine bars', 'bar', 'kitahama', 'Quiet bars in old office '
              'buildings serving regional sake and wine to the after-work crowd.', ['sake', 'wine', 'quiet'],
              '$$$', 'indoor', ['date', 'coworkers', 'solo'], NIGHT),
        # Honmachi and Semba
        place('utsubo-park', 'Utsubo Park', 'park', 'honmachi', 'A long green park on an old airfield, with a '
              'rose garden, zelkova trees and cafes on its edges.', ['roses', 'picnic', 'dogs'], 'free',
              'outdoor', ALL, DAYTIME),
        place('utsubo-tennis-center', 'Utsubo Tennis Center', 'fitness', 'honmachi', 'Public tennis courts in '
              'Utsubo Park, with a stadium court for tournaments.', ['tennis', 'municipal'], '$', 'outdoor',
              ['solo', 'friends', 'date'], DAYTIME, WARM),
        place('semba-center-building', 'Semba Center Building', 'shopping', 'honmachi', 'A kilometre-long '
              'building under the expressway full of textile and clothing wholesalers who sell to anyone.',
              ['wholesale', 'clothes', 'bargains'], '$', 'indoor', ['solo', 'friends'], DAY),
        place('kyomachibori-bistros', 'Kyomachibori bistros', 'restaurant', 'honmachi', 'Small restaurants and '
              'wine bars on the streets east of Utsubo Park, popular for dates.', ['bistro', 'wine', 'date-spot'],
              '$$$', 'indoor', ['date', 'friends'], DINNER, cuisine='bistro'),
        place('honmachi-lunch', 'Honmachi office lunch spots', 'restaurant', 'honmachi', 'Udon, curry and '
              'teishoku set-meal shops in the side streets, all rushed at noon on weekdays.',
              ['lunch', 'udon', 'teishoku'], '$', 'indoor', ['solo', 'coworkers'], ['afternoon'],
              cuisine='japanese'),
        place('utsubo-park-cafes', 'Utsubo Park cafes', 'cafe', 'honmachi', 'Bakeries and coffee stands lining '
              'the park, with seats looking onto the trees.', ['coffee', 'bakery', 'park-view'], '$', 'mixed',
              ALL, DAY, cuisine='cafe'),
        place('honmachi-standing-bars', 'Honmachi standing bars', 'bar', 'honmachi', 'After-work tachinomi near '
              'the stations where suits stand elbow to elbow over beer and fried skewers.',
              ['standing-bar', 'after-work'], '$', 'indoor', ['coworkers', 'solo', 'friends'], NIGHT),
        place('osaka-municipal-central-library', 'Osaka Municipal Central Library', 'library', 'honmachi', 'The '
              'city\'s main library at Nishi-Nagahori, open late with big study floors.',
              ['library', 'study', 'quiet'], 'free', 'indoor', ['solo', 'family'], DAYTIME),
        place('yoshino-sushi', 'Yoshino Sushi', 'restaurant', 'honmachi', 'Old Semba shop serving Osaka-style '
              'hakozushi, pressed box sushi cut into neat squares, since the Edo period.', ['hakozushi',
              'historic', 'lunch'], '$$$', 'indoor', ['solo', 'date', 'family'], ['afternoon'], cuisine='sushi'),
        # Shinsaibashi and Amerikamura
        place('shinsaibashi-suji', 'Shinsaibashi-suji Shopping Street', 'shopping', 'shinsaibashi', 'The covered '
              'shopping arcade from Nagahori to Dotonbori, crowded with fashion chains, drugstores and visitors.',
              ['shopping', 'arcade', 'rainy-day'], '$$', 'indoor', ALL, DAYTIME),
        place('daimaru-shinsaibashi', 'Daimaru Shinsaibashi', 'shopping', 'shinsaibashi', 'Department store '
              'rebuilt in 2019 behind its old Vories facade, with a busy food hall in the basement.',
              ['department-store', 'depachika', 'architecture'], '$$$', 'indoor', ALL, DAYTIME),
        place('amerikamura-triangle-park', 'Triangle Park (Mitsu Park)', 'landmark', 'shinsaibashi', 'A small '
              'concrete square at the heart of Amerikamura where young people sit, eat takoyaki and watch the '
              'street.', ['youth', 'people-watching', 'street-culture'], 'free', 'outdoor',
              ['friends', 'solo', 'date'], ['afternoon', 'evening', 'late']),
        place('amerikamura-thrift', 'Amerikamura vintage shops', 'shopping', 'shinsaibashi', 'Used American '
              'clothes, sneakers, records and street fashion stacked into narrow buildings.',
              ['vintage', 'streetwear', 'records'], '$$', 'indoor', ['friends', 'solo', 'date'], ['afternoon',
              'evening']),
        place('kogaryu-takoyaki', 'Kogaryu', 'restaurant', 'shinsaibashi', 'The Amerikamura takoyaki stand by '
              'Triangle Park, eaten standing or on the benches.', ['takoyaki', 'street-food', 'cheap'], '$',
              'outdoor', ALL, ['afternoon', 'evening', 'late'], cuisine='takoyaki'),
        place('matsubaya-kitsune-udon', 'Usami-tei Matsubaya', 'restaurant', 'shinsaibashi', 'Old udon shop in '
              'Minami-Senba that claims to have invented kitsune udon, with sweet fried tofu on top.',
              ['udon', 'kitsune-udon', 'historic'], '$', 'indoor', ['solo', 'friends', 'family'], LUNCH,
              cuisine='udon'),
        place('lilo-coffee-roasters', 'LiLo Coffee Roasters', 'cafe', 'shinsaibashi', 'Tiny specialty roaster in '
              'Nishi-Shinsaibashi with light-roast single origins and a few stools.',
              ['specialty-coffee', 'small'], '$', 'indoor', ['solo', 'friends', 'date'], DAYTIME, cuisine='cafe'),
        place('amerikamura-clubs', 'Amerikamura bars and clubs', 'nightlife', 'shinsaibashi', 'DJ bars, small '
              'clubs and late bars in the blocks around Triangle Park, busiest on Friday and Saturday.',
              ['clubs', 'dj', 'late-night'], '$$', 'indoor', ['friends', 'date'], ['late']),
        place('neon-shokudogai', 'Shinsaibashi Neon Shokudogai', 'restaurant', 'shinsaibashi', 'A basement food '
              'alley in Shinsaibashi PARCO, with neon-lit counters of gyoza, ramen and highballs.',
              ['food-hall', 'neon', 'drinks'], '$$', 'indoor', ['friends', 'date', 'coworkers'], LUNCH + ['late']),
        # Dotonbori
        place('glico-sign', 'Glico sign and Ebisubashi', 'landmark', 'dotonbori', 'The running-man billboard over '
              'the canal, the city\'s favourite photo spot; the bridge below is where crowds gather to celebrate.',
              ['iconic', 'neon', 'photo-spot'], 'free', 'outdoor', ALL, ['afternoon', 'evening', 'late']),
        place('tombori-river-cruise', 'Tombori River Cruise', 'attraction', 'dotonbori', 'Twenty-minute boat ride '
              'along the Dotonbori canal with a chatty guide.', ['boat', 'canal', 'touristy'], '$', 'outdoor',
              ALL, ['afternoon', 'evening']),
        place('hozenji-yokocho', 'Hozenji and Hozenji Yokocho', 'temple', 'dotonbori', 'A moss-covered Fudo '
              'statue people splash with water for luck, in a lantern-lit flagstone alley of small restaurants.',
              ['temple', 'lanterns', 'atmospheric'], 'free', 'outdoor', ALL, ['afternoon', 'evening', 'late']),
        place('kani-doraku-dotonbori', 'Kani Doraku Dotonbori Main Store', 'restaurant', 'dotonbori', 'Crab '
              'restaurant under the giant moving crab sign, serving crab courses in private rooms.',
              ['crab', 'iconic', 'splurge'], '$$$', 'indoor', ['family', 'date', 'friends'], LUNCH,
              cuisine='seafood'),
        place('kukuru-takoyaki', 'Takoyaki Dotonbori Kukuru', 'restaurant', 'dotonbori', 'Takoyaki stand with an '
              'octopus on the sign and big pieces of octopus inside, eaten at the counter or on the street.',
              ['takoyaki', 'street-food'], '$', 'mixed', ALL, ['afternoon', 'evening', 'late'], cuisine='takoyaki'),
        place('kinryu-ramen', 'Kinryu Ramen', 'restaurant', 'dotonbori', 'Pork-bone ramen under a dragon sign, '
              'open all night, with free kimchi and garlic on the counter.', ['ramen', 'late-night', 'cheap'],
              '$', 'mixed', ['solo', 'friends'], ['afternoon', 'evening', 'late'], cuisine='ramen'),
        place('mizuno-okonomiyaki', 'Mizuno', 'restaurant', 'dotonbori', 'Family-run okonomiyaki shop since 1945, '
              'cooked on the griddle in front of you; expect a queue.', ['okonomiyaki', 'queue', 'family-run'],
              '$$', 'indoor', ALL, LUNCH, cuisine='okonomiyaki'),
        place('arabiya-coffee', 'Arabiya Coffee', 'cafe', 'dotonbori', 'Kissaten near Hozenji serving siphon '
              'coffee and toast since the early 1950s.', ['kissaten', 'retro', 'siphon'], '$', 'indoor',
              ['solo', 'date', 'friends'], DAYTIME, cuisine='kissaten'),
        place('kissa-american', 'Kissa American', 'cafe', 'dotonbori', 'Grand old kissaten from 1946 with '
              'chandeliers, thick hotcakes and waiters in bow ties.', ['kissaten', 'retro', 'hotcakes'], '$$',
              'indoor', ALL, DAYTIME, cuisine='kissaten'),
        place('shochikuza', 'Osaka Shochikuza', 'venue', 'dotonbori', 'A 1923 theater with an arched facade on '
              'the canal, staging kabuki, plays and musicals.', ['kabuki', 'theater', 'historic'], '$$$', 'indoor',
              ['date', 'family', 'solo'], ['afternoon', 'evening']),
        # Namba
        place('namba-grand-kagetsu', 'Namba Grand Kagetsu', 'venue', 'namba', 'Yoshimoto\'s flagship comedy '
              'theater: manzai duos, then the slapstick Yoshimoto Shinkigeki troupe, several shows a day.',
              ['manzai', 'comedy', 'iconic'], '$$', 'indoor', ['friends', 'date', 'family'],
              ['afternoon', 'evening']),
        place('namba-parks', 'Namba Parks', 'shopping', 'namba', 'Mall stepping up in terraces of rooftop gardens '
              'behind Nankai Namba station.', ['shopping', 'rooftop-garden'], '$$', 'mixed', ALL, DAYTIME),
        place('takashimaya-osaka', 'Takashimaya Osaka', 'shopping', 'namba', 'The grand department store on top of '
              'Nankai Namba station, with a deep food hall and restaurant floors.', ['department-store',
              'depachika'], '$$$', 'indoor', ALL, DAYTIME),
        place('doguyasuji', 'Sennichimae Doguyasuji', 'shopping', 'namba', 'Covered arcade of kitchenware '
              'shops: knives, takoyaki pans, plastic food samples and shop lanterns.',
              ['kitchenware', 'knives', 'browsing'], '$', 'indoor', ['solo', 'friends', 'date'], DAY),
        place('takoyaki-wanaka', 'Takoyaki Wanaka Sennichimae Main Store', 'restaurant', 'namba', 'Takoyaki shop '
              'by Namba Grand Kagetsu, crisp outside and molten inside, with a choice of sauces.',
              ['takoyaki', 'street-food', 'comedy'], '$', 'mixed', ALL, ['afternoon', 'evening'],
              cuisine='takoyaki'),
        place('jiyuken', 'Jiyuken', 'restaurant', 'namba', 'Western-style restaurant since 1910, known for '
              'curry already mixed into the rice and topped with a raw egg.', ['curry', 'yoshoku', 'historic'],
              '$', 'indoor', ['solo', 'friends', 'family'], LUNCH, cuisine='yoshoku'),
        place('horai-551-main', '551 Horai Main Store', 'market', 'namba', 'The pork bun shop on Ebisubashi-suji '
              'where the butaman are folded in the window; everyone queues.', ['butaman', 'takeaway', 'queue'],
              '$', 'indoor', ALL, DAYTIME, cuisine='chinese'),
        place('rikuro-ojisan', 'Rikuro\'s Namba Main Store', 'cafe', 'namba', 'Bakery that rings a bell each time '
              'a jiggly baked cheesecake comes out of the oven.', ['cheesecake', 'bakery', 'takeaway'], '$',
              'indoor', ALL, DAY, cuisine='bakery'),
        place('maru-fuku-coffee', 'Maru-Fuku Coffee Sennichimae Main Shop', 'cafe', 'namba', 'Dark, wood-panelled '
              'kissaten serving strong drip coffee and hotcakes since 1934.', ['kissaten', 'retro', 'strong'],
              '$', 'indoor', ['solo', 'date', 'friends'], DAYTIME, cuisine='kissaten'),
        place('ura-namba', 'Ura-Namba', 'bar', 'namba', 'Back streets east of Namba packed with standing bars, '
              'oyster bars and tiny izakaya where strangers end up talking.', ['standing-bar', 'izakaya',
              'hopping'], '$', 'mixed', ['friends', 'date', 'solo'], NIGHT),
        place('edion-arena', 'Edion Arena Osaka', 'stadium', 'namba', 'The prefectural gymnasium, home of the '
              'Spring Grand Sumo Tournament each March and of boxing and concerts the rest of the year.',
              ['sumo', 'sports', 'concerts'], '$$$', 'indoor', ['friends', 'family', 'date'],
              ['afternoon', 'evening']),
        # Nipponbashi and Den Den Town
        place('kuromon-market', 'Kuromon Market', 'market', 'nipponbashi', 'The covered "kitchen of Osaka": fish '
              'stalls, grilled scallops, fruit and wagyu skewers eaten on the spot.', ['market', 'seafood',
              'street-food'], '$$', 'indoor', ALL, DAY, cuisine='seafood'),
        place('national-bunraku-theatre', 'National Bunraku Theatre', 'venue', 'nipponbashi', 'The home of '
              'bunraku puppet theater, born in Osaka, with English earphone guides.', ['bunraku', 'traditional',
              'theater'], '$$', 'indoor', ['solo', 'date', 'family'], ['afternoon', 'evening']),
        place('den-den-town', 'Den Den Town', 'shopping', 'nipponbashi', 'Electronics, anime, figure and card '
              'shops along Sakaisuji and Otaku Road.', ['anime', 'electronics', 'figures'], '$$', 'indoor',
              ['friends', 'solo', 'date'], ['afternoon', 'evening']),
        place('den-den-arcades', 'Den Den Town game centers', 'attraction', 'nipponbashi', 'Floors of crane games, '
              'rhythm games and fighting-game cabinets.', ['arcade', 'games', 'rainy-day'], '$', 'indoor',
              ['friends', 'date', 'solo'], ['afternoon', 'evening', 'late']),
        place('den-den-maid-cafes', 'Den Den Town maid cafes', 'cafe', 'nipponbashi', 'Themed cafes on Otaku Road '
              'where staff in costume serve omurice with drawings in ketchup.', ['themed', 'otaku', 'kitsch'],
              '$$', 'indoor', ['friends', 'solo'], ['afternoon', 'evening'], cuisine='cafe'),
        place('kuromon-fugu', 'Kuromon fugu and seafood restaurants', 'restaurant', 'nipponbashi', 'Restaurants '
              'around the market serving pufferfish hot pot in winter and sashimi all year.',
              ['fugu', 'seafood', 'winter'], '$$$', 'indoor', ['friends', 'family', 'date'], DINNER,
              cuisine='seafood'),
        place('nipponbashi-ramen', 'Sakaisuji ramen counters', 'restaurant', 'nipponbashi', 'Ramen and gyoza '
              'counters feeding gamers and shop staff along Sakaisuji until late.', ['ramen', 'cheap',
              'late-night'], '$', 'indoor', ['solo', 'friends'], ['afternoon', 'evening', 'late'], cuisine='ramen'),
        place('nipponbashi-game-bars', 'Nipponbashi game bars', 'bar', 'nipponbashi', 'Small bars with consoles '
              'and anime on the screens, where regulars play and drink.', ['games', 'anime', 'bar'], '$$',
              'indoor', ['friends', 'solo'], NIGHT),
        # Shinsekai
        place('tsutenkaku', 'Tsutenkaku', 'attraction', 'shinsekai', 'The 1956 steel tower over Shinsekai, with '
              'the lucky Billiken statue on the observation deck and an outdoor slide down the side.',
              ['tower', 'retro', 'views', 'billiken'], '$$', 'mixed', ALL, DAYTIME),
        place('kushikatsu-daruma-shinsekai', 'Kushikatsu Daruma Shinsekai Main Store', 'restaurant', 'shinsekai',
              'The 1929 kushikatsu counter whose angry-chef statue warns: no double-dipping in the sauce.',
              ['kushikatsu', 'iconic', 'counter'], '$', 'indoor', ['friends', 'solo', 'date'], LUNCH,
              cuisine='kushikatsu'),
        place('yaekatsu', 'Yaekatsu', 'restaurant', 'shinsekai', 'Long-running kushikatsu counter in Janjan '
              'Yokocho with a constant queue and fast-moving cooks.', ['kushikatsu', 'queue', 'counter'], '$',
              'indoor', ['friends', 'solo'], LUNCH, cuisine='kushikatsu'),
        place('tengu-kushikatsu', 'Tengu', 'restaurant', 'shinsekai', 'Kushikatsu and doteyaki beef-tendon stew '
              'at a crowded counter in Janjan Yokocho.', ['kushikatsu', 'doteyaki', 'counter'], '$', 'indoor',
              ['friends', 'solo'], LUNCH, cuisine='kushikatsu'),
        place('janjan-yokocho', 'Janjan Yokocho', 'landmark', 'shinsekai', 'A narrow covered alley of kushikatsu '
              'counters, standing bars and old men playing shogi in open-fronted parlors.',
              ['retro', 'shogi', 'atmospheric'], 'free', 'indoor', ['friends', 'solo', 'date'], DAYTIME),
        place('shinsekai-standing-bars', 'Shinsekai standing bars', 'bar', 'shinsekai', 'Cheap tachinomi where '
              'a beer, doteyaki and a chat with the regulars costs very little.', ['standing-bar', 'cheap',
              'locals'], '$', 'indoor', ['solo', 'friends'], ['afternoon', 'evening']),
        place('shinsekai-doteyaki', 'Shinsekai doteyaki and horumon stalls', 'restaurant', 'shinsekai', 'Stalls '
              'and counters simmering beef tendon in miso and grilling offal on the main street.',
              ['doteyaki', 'horumon', 'street-food'], '$', 'mixed', ['friends', 'solo'], LUNCH,
              cuisine='japanese'),
        place('spa-world', 'Spa World', 'attraction', 'shinsekai', 'A huge onsen complex with themed European and '
              'Asian bath floors (alternating by gender month to month), a swimsuit pool zone and rest areas.',
              ['onsen', 'sento', 'pool', 'rainy-day'], '$$', 'indoor', ['friends', 'family', 'solo'],
              DAYTIME + ['late']),
        place('tennoji-zoo', 'Tennoji Zoo', 'attraction', 'shinsekai', 'A century-old city zoo between Shinsekai '
              'and Tennoji Park, with an African savanna zone.', ['animals', 'kids'], '$', 'outdoor',
              ['family', 'date', 'friends'], DAY),
        # Tennoji and Abeno
        place('abeno-harukas-300', 'Harukas 300', 'attraction', 'tennoji', 'Glass-walled observation floors at '
              'the top of the 300-metre Abeno Harukas, with views to Kobe and the bay at sunset.',
              ['views', 'skyscraper', 'sunset'], '$$', 'indoor', ['date', 'family', 'friends'], DAYTIME),
        place('shitennoji', 'Shitennoji', 'temple', 'tennoji', 'One of Japan\'s oldest temples, founded by '
              'Prince Shotoku in 593, with a five-story pagoda and a monthly flea market.',
              ['temple', 'pagoda', 'history'], 'free', 'outdoor', ALL, DAY),
        place('shitennoji-flea-market', 'Shitennoji flea market', 'market', 'tennoji', 'Stalls of antiques, '
              'old kimono, tools and snacks fill the temple grounds on the 21st and 22nd of each month.',
              ['antiques', 'flea-market', 'monthly'], '$', 'outdoor', ALL, DAY),
        place('tennoji-park-keitakuen', 'Tennoji Park and Keitakuen Garden', 'park', 'tennoji', 'City park with '
              'a stroll garden around a pond, beside the zoo and the art museum.', ['garden', 'pond', 'walk'],
              '$', 'outdoor', ALL, DAY),
        place('tennoshiba', 'Tennoshiba', 'cafe', 'tennoji', 'The lawn at the front of Tennoji Park ringed by '
              'cafes, a playground and a dog run.', ['lawn', 'cafes', 'family'], '$', 'mixed', ALL, DAYTIME,
              cuisine='cafe'),
        place('osaka-city-museum-of-fine-arts', 'Osaka City Museum of Fine Arts', 'museum', 'tennoji', 'Asian '
              'art and big exhibitions in a 1936 building in Tennoji Park.', ['art', 'history', 'rainy-day'],
              '$$', 'indoor', ['solo', 'date', 'family'], DAY),
        place('harukas-kintetsu-food-hall', 'Abeno Harukas Kintetsu food hall', 'market', 'tennoji', 'Sprawling '
              'department store basement of bento, wagashi and deli counters under the tower.',
              ['depachika', 'bento', 'sweets'], '$$', 'indoor', ALL, DAYTIME, cuisine='japanese'),
        place('harukas-dining', 'Abeno Harukas restaurant floors', 'restaurant', 'tennoji', 'Restaurant floors '
              'high in the tower, from tonkatsu to kaiseki, with views across the south of the city.',
              ['views', 'dinner', 'date-spot'], '$$$', 'indoor', ['date', 'family', 'friends'], LUNCH,
              cuisine='japanese'),
        place('ura-tennoji', 'Ura-Tennoji', 'bar', 'tennoji', 'Lanes behind Tennoji station full of small '
              'bars, yakitori and Spanish-style bars in old houses.', ['izakaya', 'hopping', 'small-bars'], '$$',
              'mixed', ['friends', 'date', 'coworkers'], NIGHT),
        # Tsuruhashi and Ikuno Koreatown
        place('tsuruhashi-market', 'Tsuruhashi Market', 'market', 'tsuruhashi', 'A dark, covered maze of kimchi '
              'stalls, Korean rice cakes, hanbok tailors, fish and dried goods beside the station.',
              ['market', 'kimchi', 'korean'], '$', 'indoor', ALL, DAY, cuisine='korean'),
        place('tsuruhashi-yakiniku', 'Tsuruhashi yakiniku alleys', 'restaurant', 'tsuruhashi', 'Charcoal yakiniku '
              'shops crowded under the tracks, smoke rolling over the platforms.', ['yakiniku', 'smoky',
              'groups'], '$$', 'indoor', ['friends', 'family', 'coworkers'], DINNER, cuisine='yakiniku'),
        place('tsuruichi', 'Tsuruichi', 'restaurant', 'tsuruhashi', 'Long-established yakiniku house by '
              'Tsuruhashi station, with cuts grilled over charcoal and sauce made in the house.',
              ['yakiniku', 'historic'], '$$', 'indoor', ['family', 'friends', 'date'], DINNER, cuisine='yakiniku'),
        place('fugetsu-tsuruhashi', 'Tsuruhashi Fugetsu Main Store', 'restaurant', 'tsuruhashi', 'Where the '
              'Fugetsu okonomiyaki chain started in 1950, cooked for you on the table griddle.',
              ['okonomiyaki', 'historic'], '$$', 'indoor', ALL, LUNCH, cuisine='okonomiyaki'),
        place('ikuno-koreatown', 'Ikuno Koreatown', 'shopping', 'tsuruhashi', 'The Miyuki-dori shopping street of '
              'Korean groceries, cosmetics and K-pop goods, busy with young visitors at weekends.',
              ['korean', 'k-pop', 'shopping'], '$', 'outdoor', ALL, DAYTIME),
        place('koreatown-cafes', 'Koreatown cafes and hotteok stands', 'cafe', 'tsuruhashi', 'Korean cafes, '
              'cheese hotdog and hotteok stands along the shopping street.', ['korean', 'street-food', 'sweets'],
              '$', 'mixed', ['friends', 'date', 'family'], DAYTIME, cuisine='korean'),
        place('osaka-koreatown-history-museum', 'Osaka Koreatown History Museum', 'museum', 'tsuruhashi',
              'Small museum telling the century-long story of Korean residents in Ikuno.', ['history',
              'community'], '$', 'indoor', ['solo', 'friends', 'family'], DAY),
        # Osaka Castle and Morinomiya
        place('osaka-castle-tower', 'Osaka Castle Main Tower', 'museum', 'osaka-castle', 'The gold-trimmed '
              '1931 concrete rebuild of Hideyoshi\'s keep, a museum of the castle\'s wars with a lookout on top.',
              ['castle', 'history', 'iconic'], '$', 'indoor', ALL, DAY),
        place('osaka-castle-park', 'Osaka Castle Park', 'park', 'osaka-castle', 'Huge park inside and around the '
              'moats, with a plum grove in February and thousands of cherry trees in April.',
              ['park', 'cherry-blossom', 'plum-blossom', 'picnic'], 'free', 'outdoor', ALL, DAYTIME),
        place('nishinomaru-garden', 'Nishinomaru Garden', 'garden', 'osaka-castle', 'Lawn garden under the castle '
              'walls, a favourite hanami spot with evening cherry-blossom lighting.', ['cherry-blossom', 'lawn',
              'views'], '$', 'outdoor', ALL, DAYTIME),
        place('osaka-castle-running', 'Osaka Castle Park running loop', 'fitness', 'osaka-castle', 'The '
              'moat-side loops where half the city\'s runners train, with lockers and showers at the station.',
              ['running', 'outdoors'], 'free', 'outdoor', ['solo', 'friends'], ['morning', 'evening']),
        place('osaka-jo-hall', 'Osaka-jo Hall', 'venue', 'osaka-castle', 'Big arena in the castle park for pop '
              'concerts and sports.', ['concerts', 'arena'], '$$$', 'indoor', ['friends', 'date'], ['evening']),
        place('osaka-museum-of-history', 'Osaka Museum of History', 'museum', 'osaka-castle', 'Museum that walks '
              'down through the centuries floor by floor, with views over the castle and the Naniwa palace site.',
              ['history', 'views', 'rainy-day'], '$', 'indoor', ALL, DAY),
        place('jo-terrace', 'JO-TERRACE OSAKA', 'restaurant', 'osaka-castle', 'Restaurants and cafes by '
              'Osakajokoen station, handy after a run or a concert.', ['casual', 'after-run'], '$$', 'mixed',
              ALL, DAYTIME, cuisine='various'),
        place('miraiza', 'Miraiza Osaka-jo', 'restaurant', 'osaka-castle', 'Restaurants and a rooftop bar in a '
              'castle-style 1931 military headquarters inside the park.', ['historic-building', 'rooftop'], '$$',
              'indoor', ALL, LUNCH, cuisine='various'),
        place('morinomiya-izakaya', 'Morinomiya izakaya', 'bar', 'osaka-castle', 'Neighbourhood izakaya and '
              'yakitori around Morinomiya station, full of locals after work.', ['izakaya', 'locals'], '$$',
              'indoor', ['friends', 'coworkers'], NIGHT),
        place('castle-park-food-stalls', 'Osaka Castle hanami stalls', 'market', 'osaka-castle', 'Yatai selling '
              'takoyaki, yakisoba and beer along the paths at cherry blossom time.', ['yatai', 'hanami',
              'seasonal'], '$', 'outdoor', ['friends', 'family', 'date'], DAYTIME, ['spring'], cuisine='street-food'),
        place('tanimachi-lunch', 'Tanimachi lunch counters and kissaten', 'restaurant', 'osaka-castle', 'Curry, '
              'udon and coffee shops along Tanimachi-suji feeding prefectural office workers.', ['lunch', 'curry',
              'kissaten'], '$', 'indoor', ['solo', 'coworkers'], DAY, cuisine='japanese'),
        # Kyobashi
        place('tachinomi-toyo', 'Tachinomi Toyo', 'bar', 'kyobashi', 'Famous standing bar where the owner '
              'sears tuna with a blowtorch in front of the crowd.', ['standing-bar', 'tuna', 'iconic'], '$',
              'mixed', ['friends', 'solo'], ['afternoon', 'evening']),
        place('kyobashi-standing-bars', 'Kyobashi standing bars', 'bar', 'kyobashi', 'Morning-to-night '
              'tachinomi around the station, some serving a beer at breakfast time.', ['standing-bar', 'cheap',
              'locals'], '$', 'indoor', ['solo', 'friends', 'coworkers'], ['morning', 'afternoon', 'evening']),
        place('kyobashi-grand-chateau', 'Kyobashi Grand Chateau', 'nightlife', 'kyobashi', 'A 1970s leisure '
              'building of karaoke, bars and restaurants, famous for its old TV jingle.',
              ['karaoke', 'retro', 'bars'], '$$', 'indoor', ['friends', 'coworkers'], NIGHT),
        place('kyobashi-eateries', 'Kyobashi arcade eateries', 'restaurant', 'kyobashi', 'Udon, gyoza, '
              'kushikatsu and teishoku shops along the arcade.', ['cheap-eats', 'udon', 'gyoza'], '$', 'indoor',
              ['solo', 'friends', 'family'], LUNCH, cuisine='japanese'),
        place('kyobashi-kissaten', 'Kyobashi kissaten', 'cafe', 'kyobashi', 'Old coffee shops with morning sets '
              'of toast, boiled egg and coffee for regulars reading the sports paper.', ['kissaten',
              'morning-set'], '$', 'indoor', ['solo', 'friends'], DAY, cuisine='kissaten'),
        place('sakuranomiya-park', 'Kema Sakuranomiya Park', 'park', 'kyobashi', 'Kilometres of cherry trees '
              'along the Okawa river, crowded with hanami parties in April and joggers all year.',
              ['cherry-blossom', 'riverside', 'running'], 'free', 'outdoor', ALL, DAYTIME),
        # Juso
        place('negiyaki-yamamoto', 'Negiyaki Yamamoto Main Store', 'restaurant', 'juso', 'Where negiyaki began '
              'in 1965: a thin savoury pancake buried in green onion, finished with lemon and soy.',
              ['negiyaki', 'historic', 'local-favorite'], '$$', 'indoor', ALL, LUNCH, cuisine='okonomiyaki'),
        place('juso-izakaya', 'Juso izakaya and bars', 'bar', 'juso', 'Narrow streets west of Hankyu Juso '
              'station lined with cheap izakaya and standing bars.', ['izakaya', 'snack-bar', 'cheap'],
              '$', 'indoor', ['friends', 'coworkers', 'solo'], NIGHT),
        place('juso-bakeries-kissa', 'Juso bakeries and kissaten', 'cafe', 'juso', 'Old kissaten and local '
              'bakeries in the arcades, with morning sets and sweet buns.', ['kissaten', 'bakery'], '$',
              'indoor', ['solo', 'friends'], DAY, cuisine='kissaten'),
        place('juso-ramen-yakiniku', 'Juso late-night ramen and yakiniku', 'restaurant', 'juso', 'Ramen counters '
              'and horumon grills that keep going after the bars close.', ['ramen', 'horumon', 'late-night'],
              '$', 'indoor', ['friends', 'solo'], ['evening', 'late'], cuisine='ramen'),
        place('seventh-art-theater', 'The Seventh Art Theater', 'venue', 'juso', 'Independent mini-cinema showing '
              'documentaries and art films.', ['cinema', 'indie'], '$$', 'indoor', ['solo', 'date'],
              ['afternoon', 'evening']),
        place('yodogawa-riverside', 'Yodogawa riverside park', 'fitness', 'juso', 'Wide grassy riverbanks along '
              'the Yodo with running and cycling paths and baseball fields.', ['running', 'cycling', 'riverside'],
              'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('juso-snack-bars', 'Juso snack bars', 'nightlife', 'juso', 'Tiny "sunakku" bars run by a mama-san, '
              'with a bottle kept for regulars and a karaoke machine in the corner.', ['snack-bar', 'karaoke',
              'regulars'], '$$', 'indoor', ['solo', 'friends', 'coworkers'], ['late']),
        # Bentencho and the Bay Area
        place('kaiyukan', 'Kaiyukan', 'attraction', 'bay-area', 'One of the world\'s largest aquariums, spiralling '
              'down around a giant central tank with a whale shark.', ['aquarium', 'kids', 'rainy-day'], '$$$',
              'indoor', ALL, DAYTIME),
        place('naniwa-kuishinbo-yokocho', 'Naniwa Kuishinbo Yokocho', 'restaurant', 'bay-area', 'A retro 1960s '
              'Osaka street inside Tempozan Marketplace with takoyaki, okonomiyaki and curry shops.',
              ['retro', 'food-court', 'family'], '$', 'indoor', ALL, LUNCH, cuisine='japanese'),
        place('universal-studios-japan', 'Universal Studios Japan', 'attraction', 'bay-area', 'The theme park at '
              'Sakurajima, with Super Nintendo World, the Wizarding World of Harry Potter and seasonal events.',
              ['theme-park', 'nintendo', 'all-day'], '$$$$', 'outdoor', ['friends', 'date', 'family'], DAYTIME),
        place('universal-citywalk', 'Universal CityWalk Osaka', 'restaurant', 'bay-area', 'Restaurants, takoyaki '
              'stands and shops outside the theme park gates.', ['restaurants', 'theme-park'], '$$', 'mixed',
              ALL, DAYTIME, cuisine='various'),
        place('kyocera-dome', 'Kyocera Dome Osaka', 'stadium', 'bay-area', 'Domed ballpark of the Orix Buffaloes '
              'and a stadium-size concert venue.', ['baseball', 'concerts'], '$$', 'indoor', ['friends', 'family',
              'date'], ['afternoon', 'evening']),
        place('taisho-okinawan', 'Taisho Okinawan eateries', 'restaurant', 'bay-area', 'Okinawan shokudo and '
              'bars of Taisho ward, serving goya champuru, Okinawa soba and awamori.', ['okinawan', 'community'],
              '$', 'indoor', ['friends', 'family', 'solo'], LUNCH, cuisine='okinawan'),
        place('bentencho-izakaya', 'Bentencho izakaya', 'bar', 'bay-area', 'Plain izakaya and standing bars '
              'under the Loop Line at Bentencho station.', ['izakaya', 'locals'], '$', 'indoor',
              ['friends', 'coworkers', 'solo'], NIGHT),
        place('osaka-pool', 'Osaka Pool', 'fitness', 'bay-area', 'The big municipal swimming pool by '
              'Asashiobashi station, with a 50 m pool open to the public.', ['swimming', 'municipal'], '$',
              'indoor', ['solo', 'friends', 'family'], DAYTIME),
        place('osaka-central-gymnasium', 'Osaka Municipal Central Gymnasium', 'fitness', 'bay-area', 'Domed sports '
              'center under a grassy hill, with a public training room and studio classes.', ['gym', 'municipal',
              'classes'], '$', 'indoor', ['solo', 'friends'], DAYTIME),
        place('hirao-shotengai', 'Hirao shopping street', 'market', 'bay-area', 'Taisho\'s arcade with Okinawan '
              'groceries, sata andagi doughnuts and shops for the ward\'s Okinawan community.', ['okinawan',
              'shotengai', 'community'], '$', 'mixed', ALL, DAY, cuisine='okinawan'),
        # Sumiyoshi
        place('sumiyoshi-taisha', 'Sumiyoshi Taisha', 'temple', 'sumiyoshi', 'Head of Japan\'s Sumiyoshi shrines, '
              'with its own ancient architecture and a steep red arched bridge over the pond.',
              ['shrine', 'architecture', 'new-year'], 'free', 'outdoor', ALL, DAY),
        place('nagai-park', 'Nagai Park', 'park', 'sumiyoshi', 'Large park with a botanical garden, a natural '
              'history museum and two stadiums.', ['park', 'botanical-garden', 'stadiums'], 'free', 'outdoor', ALL,
              DAYTIME),
        place('nagai-park-running', 'Nagai Park jogging course', 'fitness', 'sumiyoshi', 'Measured running loop '
              'around the stadiums, busy with club runners.', ['running', 'measured-course'], 'free', 'outdoor',
              ['solo', 'friends'], ['morning', 'evening']),
        place('yodoko-sakura-stadium', 'Yodoko Sakura Stadium', 'stadium', 'sumiyoshi', 'Football stadium in Nagai '
              'Park, home of Cerezo Osaka.', ['football', 'cerezo'], '$$', 'outdoor', ['friends', 'family'],
              ['afternoon', 'evening'], ['spring', 'summer', 'fall']),
        place('sumiyoshi-sweet-shops', 'Sumiyoshi Taisha mochi and tea shops', 'cafe', 'sumiyoshi', 'Old sweet '
              'shops by the shrine gates selling mochi and green tea to worshippers.', ['wagashi', 'mochi',
              'traditional'], '$', 'indoor', ALL, DAY, cuisine='wagashi'),
        place('sumiyoshi-shotengai', 'Sumiyoshi local shopping streets', 'market', 'sumiyoshi', 'Small arcades '
              'of greengrocers, tofu makers and croquette counters near the tram stops.', ['shotengai', 'local',
              'cheap'], '$', 'mixed', ALL, DAY),
        place('sumiyoshi-izakaya', 'Hankai tram-stop izakaya', 'bar', 'sumiyoshi', 'Family-run izakaya by the '
              'streetcar stops, with oden and highballs.', ['izakaya', 'locals', 'quiet'], '$', 'indoor',
              ['friends', 'solo'], NIGHT),
        place('sumiyoshi-okonomiyaki', 'Sumiyoshi neighbourhood okonomiyaki', 'restaurant', 'sumiyoshi', 'Small '
              'okonomiyaki shops where the owner cooks on a griddle that fills the room.',
              ['okonomiyaki', 'locals'], '$', 'indoor', ALL, LUNCH, cuisine='okonomiyaki'),
        place('tezukayama-cafes', 'Tezukayama bakeries and cafes', 'cafe', 'sumiyoshi', 'Bakeries and quiet '
              'cafes in the leafy hill streets above the shrine.', ['bakery', 'coffee', 'quiet'], '$', 'indoor',
              ALL, DAY, cuisine='bakery'),
        # Nishinari and Kamagasaki
        place('supermarket-tamade', 'Supermarket Tamade', 'market', 'nishinari', 'The neon-lit, all-hours '
              'discount supermarket chain born in Nishinari, known for very cheap bento.', ['discount', 'neon',
              'late-night'], '$', 'indoor', ALL, ['morning', 'afternoon', 'evening', 'late']),
        place('cocoroom', 'Cocoroom', 'cafe', 'nishinari', 'Guesthouse, garden and cafe in Kamagasaki that runs '
              'poetry, art and study sessions with local residents.', ['community', 'arts', 'guesthouse'], '$',
              'mixed', ['solo', 'friends'], DAYTIME, cuisine='cafe'),
        place('shin-imamiya-standing-bars', 'Shin-Imamiya standing bars', 'bar', 'nishinari', 'Some of the '
              'cheapest drinks in Japan, poured at counters near the station for regulars and backpackers.',
              ['standing-bar', 'cheap', 'locals'], '$', 'indoor', ['solo', 'friends'], ['afternoon', 'evening']),
        place('nishinari-shokudo', 'Nishinari shokudo and horumon counters', 'restaurant', 'nishinari', 'Cheap '
              'canteens serving set meals, doteyaki and grilled offal from early morning.', ['cheap-eats',
              'horumon', 'local'], '$', 'indoor', ['solo', 'friends'], ['morning', 'afternoon', 'evening'],
              cuisine='japanese'),
        place('tengachaya-shotengai', 'Tengachaya shopping street', 'market', 'nishinari', 'Old covered arcade '
              'of greengrocers, fishmongers and cheap clothes by the Nankai station.', ['shotengai', 'local',
              'cheap'], '$', 'indoor', ALL, DAY),
        # Suita
        place('expo-70-park', 'Expo \'70 Commemorative Park', 'park', 'suita', 'The grounds of the 1970 World '
              'Expo turned into a huge park of lawns, forests, a Japanese garden and seasonal flower fields.',
              ['park', 'cherry-blossom', 'picnic'], '$', 'outdoor', ALL, DAY),
        place('tower-of-the-sun', 'Tower of the Sun', 'landmark', 'suita', 'Taro Okamoto\'s three-faced tower '
              'from Expo \'70, which can be visited inside by reservation.', ['art', 'iconic', 'expo'], '$',
              'mixed', ALL, DAY),
        place('minpaku', 'National Museum of Ethnology (Minpaku)', 'museum', 'suita', 'One of the world\'s largest '
              'ethnology museums, with everyday objects from every continent.', ['culture', 'rainy-day'], '$',
              'indoor', ALL, DAY),
        place('expocity', 'EXPOCITY', 'shopping', 'suita', 'Mall beside Expo park with the Nifrel living museum, '
              'the Osaka Wheel and a food court.', ['mall', 'ferris-wheel', 'family'], '$$', 'indoor', ALL,
              DAYTIME),
        place('expocity-food-court', 'EXPOCITY restaurants and food court', 'restaurant', 'suita', 'Ramen, '
              'okonomiyaki, burgers and family restaurants under one roof.', ['food-court', 'family'], '$$',
              'indoor', ['family', 'friends'], LUNCH, cuisine='various'),
        place('panasonic-stadium-suita', 'Panasonic Stadium Suita', 'stadium', 'suita', 'Football stadium of '
              'Gamba Osaka, steep and loud, beside Expo park.', ['football', 'gamba'], '$$', 'outdoor',
              ['friends', 'family'], ['afternoon', 'evening'], ['spring', 'summer', 'fall']),
        place('esaka-izakaya', 'Esaka izakaya streets', 'bar', 'suita', 'Bars and izakaya around Esaka station on '
              'the Midosuji line, popular with students and young workers.', ['izakaya', 'students'], '$',
              'indoor', ['friends', 'coworkers'], NIGHT),
        place('kandai-mae-eateries', 'Kandaimae student eateries', 'restaurant', 'suita', 'Cheap ramen, curry '
              'and set-meal shops on the slope up to Kansai University.', ['cheap-eats', 'students'], '$',
              'indoor', ['solo', 'friends'], LUNCH, cuisine='japanese'),
        place('suita-cafes', 'Suita station cafes', 'cafe', 'suita', 'Chain and local coffee shops by the '
              'stations where students study over a single drink.', ['study', 'coffee'], '$', 'indoor',
              ['solo', 'friends'], DAYTIME, cuisine='cafe'),
        place('esaka-ramen', 'Esaka ramen and gyoza counters', 'restaurant', 'suita', 'Ramen, gyoza and '
              'teishoku shops around Esaka station, open late.', ['ramen', 'gyoza', 'cheap'], '$', 'indoor',
              ['solo', 'friends'], ['afternoon', 'evening', 'late'], cuisine='ramen'),
        # Toyonaka and Minoh
        place('minoo-park', 'Minoo Park and Minoo Falls', 'trail', 'toyonaka-minoh', 'A three-kilometre path up a '
              'wooded gorge to a 33-metre waterfall, at its best in autumn colours.', ['hiking', 'waterfall',
              'autumn-leaves'], 'free', 'outdoor', ALL, DAY),
        place('momiji-tempura', 'Minoo momiji tempura stands', 'market', 'toyonaka-minoh', 'Shops on the path to '
              'the falls frying maple leaves in sweet batter, a snack found almost only here.',
              ['street-food', 'unique', 'autumn-leaves'], '$', 'outdoor', ALL, DAY, cuisine='snacks'),
        place('katsuoji', 'Katsuoji', 'temple', 'toyonaka-minoh', 'Mountain temple of winning luck, covered in '
              'small red daruma dolls left by visitors.', ['temple', 'daruma', 'nature'], '$', 'outdoor', ALL, DAY),
        place('minoh-beer', 'Minoh Beer', 'bar', 'toyonaka-minoh', 'Award-winning family craft brewery from '
              'Minoh, poured at its own taproom near the station.', ['craft-beer', 'local'], '$$', 'indoor',
              ['friends', 'date'], NIGHT),
        place('hattori-ryokuchi', 'Hattori Ryokuchi Park', 'park', 'toyonaka-minoh', 'Big park with ponds, a '
              'riding ground and an open-air museum of old farmhouses.', ['park', 'cycling', 'family'], 'free',
              'outdoor', ALL, DAYTIME),
        place('ishibashi-shotengai', 'Ishibashi Handai-mae eateries', 'restaurant', 'toyonaka-minoh', 'Cheap '
              'student restaurants and izakaya in the arcade below Osaka University\'s Toyonaka campus.',
              ['students', 'cheap-eats'], '$', 'indoor', ['friends', 'solo'], LUNCH, cuisine='japanese'),
        place('toyonaka-cafes', 'Toyonaka bakeries and cafes', 'cafe', 'toyonaka-minoh', 'Neighbourhood '
              'bakeries and coffee shops by the Hankyu stations, busy with parents after school drop-off.',
              ['bakery', 'coffee', 'family'], '$', 'indoor', ALL, DAY, cuisine='bakery'),
        place('minoh-izakaya', 'Minoh and Senri-Chuo izakaya', 'bar', 'toyonaka-minoh', 'Quiet suburban '
              'izakaya near the stations for a drink on the way home.', ['izakaya', 'suburban'], '$$', 'indoor',
              ['friends', 'coworkers'], NIGHT),
        # Sakai
        place('daisen-kofun', 'Daisen Kofun (Emperor Nintoku\'s tomb)', 'landmark', 'sakai', 'The largest of the '
              'keyhole-shaped Mozu tombs, a UNESCO World Heritage site ringed by moats; walk the path round it.',
              ['history', 'unesco', 'walk'], 'free', 'outdoor', ALL, DAY),
        place('sakai-city-museum', 'Sakai City Museum', 'museum', 'sakai', 'Museum of Sakai\'s tombs, merchants '
              'and crafts in Daisen Park.', ['history', 'rainy-day'], '$', 'indoor', ALL, DAY),
        place('sakai-rikyu-akiko', 'Sakai Plaza of Rikyu and Akiko', 'museum', 'sakai', 'Museum of tea master '
              'Sen no Rikyu and poet Yosano Akiko, both from Sakai, with tea served in its tea rooms.',
              ['tea-ceremony', 'poetry', 'history'], '$', 'indoor', ['solo', 'date', 'family'], DAY),
        place('sakai-traditional-crafts', 'Sakai Traditional Crafts Museum', 'shopping', 'sakai', 'Knife smiths\' '
              'showroom and shop where chefs buy Sakai kitchen knives.', ['knives', 'crafts'], '$$$', 'indoor',
              ['solo', 'friends'], DAY),
        place('kanbukuro', 'Kanbukuro', 'cafe', 'sakai', 'Sweet shop founded centuries ago, serving kurumi mochi '
              'in green bean paste, often over shaved ice in summer.', ['wagashi', 'historic', 'kakigori'], '$',
              'indoor', ALL, DAY, cuisine='wagashi'),
        place('sakai-higashi-izakaya', 'Sakai-Higashi izakaya', 'bar', 'sakai', 'Izakaya and standing bars '
              'around Sakai-Higashi station.', ['izakaya', 'locals'], '$', 'indoor', ['friends', 'coworkers'],
              NIGHT),
        place('sakai-eateries', 'Sakai old-town eateries', 'restaurant', 'sakai', 'Soba, udon and okonomiyaki '
              'shops in the old town along the Hankai tram line.', ['soba', 'local'], '$', 'indoor', ALL, LUNCH,
              cuisine='japanese'),
        place('sakai-kissaten', 'Sakai kissaten', 'cafe', 'sakai', 'Neighbourhood coffee shops with morning '
              'sets and newspapers.', ['kissaten', 'morning-set'], '$', 'indoor', ['solo', 'friends'], DAY,
              cuisine='kissaten'),
        place('sakai-fish-market-eats', 'Sakai harbour seafood shokudo', 'restaurant', 'sakai', 'Plain seafood '
              'canteens near the harbour serving rice bowls of the morning\'s fish.', ['seafood', 'breakfast'],
              '$', 'indoor', ['solo', 'friends'], ['morning', 'afternoon'], cuisine='seafood'),
    ],
    'colleges': [
        college('osaka-university', 'Osaka University', 'research-university', 'suita', 'large',
                ['medicine', 'engineering', 'science', 'research', 'foreign-studies']),
        college('osaka-metropolitan-university', 'Osaka Metropolitan University', 'public-university',
                'sumiyoshi', 'large', ['engineering', 'medicine', 'urban-studies', 'business', 'veterinary']),
        college('kansai-university', 'Kansai University', 'private-university', 'suita', 'large',
                ['law', 'business', 'sociology', 'engineering']),
        college('kindai-university', 'Kindai University', 'private-university', 'tsuruhashi', 'large',
                ['aquaculture', 'medicine', 'law', 'engineering']),
        college('kansai-gaidai', 'Kansai Gaidai University', 'private-university', 'kyobashi', 'medium',
                ['languages', 'international-studies', 'exchange-programs']),
        college('osaka-university-of-arts', 'Osaka University of Arts', 'art-school', 'tennoji', 'medium',
                ['art', 'design', 'film', 'music', 'manga']),
        college('osaka-institute-of-technology', 'Osaka Institute of Technology', 'technical-institute', 'kyobashi',
                'large', ['engineering', 'robotics', 'information-science']),
    ],
    'employers': [
        employer('panasonic', 'Panasonic', 'technology', 'kyobashi', 'large', 'Electronics maker founded in Osaka '
                 'by Konosuke Matsushita in 1918, headquartered in Kadoma, a short Keihan ride east of Kyobashi.',
                 ['software-engineer', 'data-analyst', 'ux-designer', 'marketing-coordinator', 'accountant']),
        employer('sharp', 'Sharp', 'technology', 'sakai', 'large', 'Electronics company founded in Osaka in 1912, '
                 'with its head office on the Sakai waterfront.', ['software-engineer', 'data-analyst',
                 'marketing-coordinator']),
        employer('daikin', 'Daikin Industries', 'technology', 'umeda', 'large', 'Air-conditioning maker with its '
                 'head office in Umeda.', ['software-engineer', 'data-analyst', 'accountant',
                 'marketing-coordinator', 'construction-trades']),
        employer('sakura-internet', 'Sakura Internet', 'technology', 'umeda', 'medium', 'Cloud and data-center '
                 'company with its head office in Grand Front Osaka.', ['software-engineer', 'data-analyst',
                 'ux-designer']),
        employer('kansai-electric', 'Kansai Electric Power', 'energy', 'nakanoshima', 'large', 'Kanden, the '
                 'utility that powers the Kansai region, run from its tower on the west of Nakanoshima.',
                 ['data-analyst', 'accountant', 'software-engineer', 'construction-trades']),
        employer('takeda', 'Takeda Pharmaceutical', 'biotech', 'honmachi', 'large', 'Drug maker founded in '
                 'Doshomachi, Osaka\'s old medicine merchants\' street, in 1781; it keeps its Osaka head office '
                 'there.', ['biotech-scientist', 'medical-researcher', 'pharmacist', 'marketing-coordinator',
                 'accountant']),
        employer('shionogi', 'Shionogi', 'biotech', 'honmachi', 'large', 'Pharmaceutical company founded in '
                 'Doshomachi in 1878, headquartered there still, with research labs in Toyonaka.',
                 ['biotech-scientist', 'medical-researcher', 'pharmacist', 'data-analyst']),
        employer('suntory', 'Suntory', 'food', 'nakanoshima', 'large', 'Whisky, beer and soft-drink company '
                 'founded in Osaka in 1899, with its Osaka head office at Dojimahama by the river.',
                 ['marketing-coordinator', 'accountant', 'data-analyst']),
        employer('nissin-foods', 'Nissin Foods', 'food', 'juso', 'large', 'The instant noodle company Momofuku '
                 'Ando founded, with its Osaka head office in Yodogawa ward north of the river.',
                 ['marketing-coordinator', 'accountant', 'data-analyst']),
        employer('kintetsu-group', 'Kintetsu Group', 'transport', 'tennoji', 'large', 'Japan\'s largest private railway '
                 'group, headquartered in Uehommachi, which also runs Abeno Harukas, department stores and '
                 'hotels.', ['hotel-front-desk', 'retail-associate', 'accountant', 'marketing-coordinator',
                 'real-estate-agent']),
        employer('hankyu-hanshin', 'Hankyu Hanshin group', 'transport', 'umeda', 'large', 'The group behind the '
                 'Hankyu and Hanshin railways, the Umeda department stores, the Takarazuka Revue and the Hanshin '
                 'Tigers.', ['retail-associate', 'real-estate-agent', 'event-planner', 'marketing-coordinator',
                 'accountant']),
        employer('osaka-city-office', 'Osaka City Office', 'government', 'nakanoshima', 'large', 'City Hall on '
                 'Nakanoshima and the ward offices, including the board of education that runs the city\'s '
                 'public schools.', ['government-analyst', 'social-worker', 'teacher', 'accountant',
                 'construction-trades']),
        employer('osaka-university-hospital', 'Osaka University Hospital', 'healthcare', 'suita', 'large',
                 'Teaching hospital on the Suita campus.', ['registered-nurse', 'night-nurse',
                 'physician-resident', 'medical-researcher', 'pharmacist']),
        employer('omu-hospital', 'Osaka Metropolitan University Hospital', 'healthcare', 'tennoji', 'large',
                 'University hospital at Abeno, a short walk from Tennoji station.', ['registered-nurse',
                 'night-nurse', 'physician-resident', 'medical-researcher']),
        employer('osaka-international-cancer-institute', 'Osaka International Cancer Institute', 'healthcare',
                 'osaka-castle', 'large', 'Prefectural cancer hospital and research center by Osaka Castle.',
                 ['registered-nurse', 'night-nurse', 'medical-researcher', 'pharmacist']),
        employer('kitano-hospital', 'Kitano Hospital', 'healthcare', 'tenma', 'medium', 'General hospital in '
                 'Ogimachi, Kita ward.', ['registered-nurse', 'night-nurse', 'physician-resident']),
        employer('usj-llc', 'Universal Studios Japan', 'entertainment', 'bay-area', 'large',
                 'The Sakurajima theme park, one of the city\'s biggest hirers of performers, cooks and crew.',
                 ['performer', 'actor', 'server', 'line-cook', 'retail-associate', 'event-planner']),
        employer('yoshimoto-kogyo', 'Yoshimoto Kogyo', 'entertainment', 'namba', 'large', 'The comedy company '
                 'founded in Osaka in 1912, running Namba Grand Kagetsu and a training school for manzai duos.',
                 ['performer', 'actor', 'event-planner', 'marketing-coordinator']),
        employer('asahi-broadcasting', 'Asahi Broadcasting (ABC TV)', 'media', 'fukushima', 'medium', 'Osaka TV '
                 'and radio broadcaster at Hotarumachi, Fukushima.', ['journalist', 'graphic-designer',
                 'marketing-coordinator', 'event-planner']),
        employer('port-of-osaka', 'Port of Osaka', 'logistics', 'bay-area', 'large', 'Container terminals at '
                 'Nanko and Yumeshima, ferry piers and warehouses run by the city and private operators.',
                 ['port-logistics', 'construction-trades']),
        employer('resona-bank', 'Resona Bank', 'finance', 'honmachi', 'large', 'Bank with its registered head '
                 'office in Osaka\'s Chuo ward.', ['finance-banker', 'financial-analyst', 'accountant']),
        employer('osaka-exchange', 'Osaka Exchange', 'finance', 'kitahama', 'medium', 'Japan\'s derivatives '
                 'exchange, part of Japan Exchange Group, in the old Osaka Stock Exchange building at Kitahama.',
                 ['financial-analyst', 'software-engineer', 'data-analyst']),
        employer('imperial-hotel-osaka', 'Imperial Hotel Osaka', 'hospitality', 'tenma', 'medium', 'Grand hotel on '
                 'the Okawa river across from the Mint.', ['hotel-front-desk', 'line-cook', 'server', 'bartender',
                 'event-planner']),
    ],
    'career_hubs': [
        hub('kita', 'Kita business district', ['umeda', 'nakazakicho', 'nakanoshima', 'fukushima'],
            ['finance', 'technology', 'business', 'media', 'legal', 'real-estate', 'energy', 'retail'],
            'Head offices, banks, law firms and broadcasters in the towers around Umeda and Nakanoshima.'),
        hub('semba', 'Semba and Kitahama', ['honmachi', 'kitahama'],
            ['finance', 'biotech', 'business', 'legal', 'fashion'],
            'The old merchant quarter: trading houses, textile wholesalers and the pharmaceutical street of '
            'Doshomachi.'),
        hub('minami', 'Minami', ['namba', 'dotonbori', 'shinsaibashi', 'nipponbashi', 'tennoji'],
            ['hospitality', 'retail', 'entertainment', 'tourism', 'food', 'creative', 'fashion'],
            'Restaurants, department stores, theaters, hotels and shops from Shinsaibashi down to Tennoji.'),
        hub('bay', 'Osaka Bay', ['bay-area'], ['logistics', 'tourism', 'entertainment', 'construction'],
            'The port, warehouses, the aquarium and the theme park along the bay.'),
        hub('northern-campuses', 'Northern campuses and research parks', ['suita', 'toyonaka-minoh'],
            ['education', 'healthcare', 'biotech', 'technology'],
            'Universities, hospitals and corporate labs in the northern suburbs.'),
    ],
    'climate': {
        'summary': 'Humid subtropical: mild, dry winters; a rainy season in June and early July; long, hot, '
                   'humid summers with typhoons possible from August to October; and clear, comfortable autumns.',
        'months': [
            month(9.6, 2.8, 6, 'Coldest month; dry and clear, rarely any snow.'),
            month(10.4, 3.0, 7, 'Cold and dry; plum blossoms open at the castle late in the month.'),
            month(14.1, 5.8, 10, 'Changeable; cherry blossoms usually open in the last week.'),
            month(19.9, 10.9, 9, 'Cherry blossoms early in the month; mild and pleasant.'),
            month(24.9, 16.0, 9, 'Warm and sunny through Golden Week.'),
            month(28.0, 20.2, 12, 'Tsuyu rainy season sets in; damp and muggy.'),
            month(31.8, 24.6, 11, 'Rainy season ends mid-month, then hot, sticky festival nights.'),
            month(33.7, 25.6, 7, 'Hottest month; heat warnings, cicadas and the odd typhoon.'),
            month(29.5, 21.8, 10, 'Still hot; typhoon season peaks.'),
            month(23.8, 15.8, 8, 'Warm, clear and comfortable.'),
            month(17.9, 9.8, 7, 'Crisp and dry; autumn leaves in the parks and at Minoo.'),
            month(12.1, 4.9, 6, 'Cool and dry; illuminations along Midosuji and Nakanoshima.'),
        ],
        'source': CLIMATE,
    },
    'annual_events': [
        event('toka-ebisu', 'Toka Ebisu', [1], 'shinsekai', 'From the 9th to the 11th of January, crowds at '
              'Imamiya Ebisu Shrine buy bamboo branches hung with lucky charms for business in the year ahead.'),
        event('doya-doya', 'Doya Doya at Shitennoji', [1], 'tennoji', 'On January 14 teams in loincloths '
              'wrestle for paper charms showered down in the temple hall.'),
        event('osaka-marathon', 'Osaka Marathon', [2], 'osaka-castle', 'Late-February marathon through the center, '
              'from the prefectural offices by the castle out and back across the city.'),
        event('spring-sumo-basho', 'Spring Grand Sumo Tournament', [3], 'namba', 'Fifteen days of top-division '
              'sumo at Edion Arena each March, with wrestlers seen around Namba.'),
        event('cherry-blossom-viewing', 'Cherry blossom season', [3, 4], 'osaka-castle', 'Hanami picnics under '
              'the trees at Osaka Castle, Sakuranomiya and Expo park from late March into early April.'),
        event('mint-cherry-passage', 'Mint Bureau cherry blossom passage', [4], 'tenma', 'One week in mid-April '
              'when the Japan Mint opens its riverside lane of late-blooming cherry trees.'),
        event('aizen-matsuri', 'Aizen Matsuri', [6, 7], 'tennoji', 'From June 30 to July 2 at Aizendo near '
              'Shitennoji, the first of Osaka\'s summer festivals, with yukata-clad women carried in palanquins.'),
        event('tenjin-matsuri', 'Tenjin Matsuri', [7], 'tenma', 'On July 24 and 25, one of Japan\'s three great '
              'festivals: a land procession from Osaka Tenmangu, a hundred boats on the Okawa river and '
              'fireworks overhead.'),
        event('sumiyoshi-matsuri', 'Sumiyoshi Matsuri', [7, 8], 'sumiyoshi', 'Summer purification festival at '
              'Sumiyoshi Taisha, ending on August 1 with a portable shrine carried to Sakai.'),
        event('naniwa-yodogawa-fireworks', 'Naniwa Yodogawa Fireworks', [8], 'juso', 'A summer night of '
              'fireworks over the Yodo river near Juso, watched from packed riverbanks.'),
        event('koshien-summer', 'Summer Koshien high school baseball', [8], None, 'The national high school '
              'baseball championship at Koshien Stadium in Nishinomiya, a short Hanshin ride away; the whole '
              'region watches on TV.'),
        event('kishiwada-danjiri', 'Kishiwada Danjiri Matsuri', [9], None, 'In Kishiwada, south of Sakai, '
              'teams haul heavy carved wooden floats through the streets at a run, taking corners at speed.'),
        event('midosuji-autumn-party', 'Midosuji Autumn Party', [10, 11], 'honmachi', 'A day when Midosuji '
              'boulevard closes to traffic for parades, marching bands and stalls under the ginkgo trees.'),
        event('osaka-hikari-renaissance', 'OSAKA Hikari-Renaissance', [12], 'nakanoshima', 'Light shows '
              'projected on the Central Public Hall and illuminations along Nakanoshima through December.'),
        event('midosuji-illumination', 'Midosuji Illumination', [11, 12], 'shinsaibashi', 'Kilometres of '
              'Midosuji\'s ginkgo trees strung with lights from November to the new year.'),
    ],
    'local_color': [
        color('takoyaki', 'Takoyaki', 'dish', 'Batter balls with octopus inside, turned with picks in a dimpled '
              'pan, topped with sauce, mayonnaise, aonori and bonito flakes; many families own a takoyaki pan.',
              ['kogaryu-takoyaki', 'takoyaki-wanaka', 'kukuru-takoyaki']),
        color('okonomiyaki', 'Okonomiyaki', 'dish', 'The savoury cabbage pancake cooked on a griddle, Osaka style '
              'with everything mixed into the batter, often eaten with rice as a set.',
              ['mizuno-okonomiyaki', 'fugetsu-tsuruhashi', 'takimi-koji']),
        color('kushikatsu', 'Kushikatsu', 'dish', 'Deep-fried skewers of meat, vegetables and cheese, dipped once '
              'in a shared tin of sauce; "no double-dipping" is the rule, and cabbage scoops more sauce.',
              ['kushikatsu-daruma-shinsekai', 'yaekatsu', 'tengu-kushikatsu']),
        color('kitsune-udon', 'Kitsune udon', 'dish', 'Udon in light kombu dashi topped with sweet fried tofu, '
              'an Osaka invention; locals insist the soup should be clear, not dark like Tokyo\'s.',
              ['matsubaya-kitsune-udon']),
        color('butaman', '551 Horai butaman', 'dish', 'Big pork buns bought by the box at the station and carried '
              'home or to the office; the TV ad line goes "when there is 551, everyone smiles".',
              ['horai-551-main']),
        color('negiyaki-ikayaki', 'Negiyaki and ikayaki', 'dish', 'Negiyaki is a thin pancake buried in green '
              'onion; ikayaki is Osaka\'s squid-and-egg pancake folded in paper, eaten standing in the Hanshin '
              'basement.', ['negiyaki-yamamoto', 'hanshin-umeda-food-hall']),
        color('mix-juice', 'Mix juice', 'drink', 'A kissaten classic: banana, peach, orange and milk blended '
              'smooth and served cold.', ['kissa-american', 'maru-fuku-coffee']),
        color('highball', 'Highball', 'drink', 'Whisky and soda in a big mug, the default order in standing bars '
              'and izakaya alongside a beer.'),
        color('maido', '"Maido"', 'saying', 'The all-purpose shopkeeper\'s greeting, "thanks as always", which '
              'the abacus-shaking merchant spirit of the city boils down to.'),
        color('ookini', '"Ookini"', 'saying', 'Osaka-ben for thank you, still heard from older shopkeepers and '
              'taxi drivers.'),
        color('nande-ya-nen', '"Nande ya nen"', 'saying', 'The comedian\'s "what do you mean?!", the tsukkomi '
              'line everyone in Osaka uses to snap back at nonsense.'),
        color('mokarimakka', '"Mokarimakka?" "Bochi bochi denna"', 'saying', 'The merchants\' joke greeting, '
              '"making money?" answered with "so-so", said half in earnest.'),
        color('honma', '"Honma" and "akan"', 'saying', 'Osaka-ben for "really" and "no good", used in every '
              'second sentence.'),
        color('kuidaore', 'Kuidaore', 'custom', 'Osaka\'s motto of eating until you drop, or eating yourself into '
              'ruin: food is where the money goes. Its mascot, Kuidaore Taro, a '
              'drum-beating clown doll, stands outside a Dotonbori building.', ['dotonbori']),
        color('escalator-right', 'Standing on the right', 'custom', 'On Osaka escalators people stand on the '
              'right and walk on the left, the opposite of Tokyo.'),
        color('boke-tsukkomi', 'Boke and tsukkomi', 'custom', 'Conversations run like manzai: one person plays '
              'the fool and the other slaps back with the correction, and a story without a punchline is '
              'complained about.', ['namba-grand-kagetsu']),
        color('haggling', '"Nanbo?" and haggling', 'custom', 'Osakans ask "how much?" and push for "makete" (a '
              'discount), and like to tell you how cheaply they got something.'),
        color('obachan-ame-chan', 'Osaka obachan and ame-chan', 'custom', 'The neighbourhood aunties, famous for '
              'loud prints, bicycles and handing candy ("ame-chan") to strangers on trains.'),
        color('mamachari', 'Mamachari', 'custom', 'Everyday city bicycles with baskets and child seats ridden on '
              'the pavements, often holding an umbrella, and parked by the hundred at every station.'),
        color('billiken', 'Billiken', 'other', 'The grinning god of things as they ought to be; people rub the '
              'soles of his feet in Tsutenkaku for luck.', ['tsutenkaku']),
        color('depachika-konbini', 'Depachika and konbini', 'shop', 'Department store basements for gifts and '
              'evening bento discounts, and a Lawson, FamilyMart or 7-Eleven on every corner for everything '
              'else.', ['hankyu-umeda-food-hall', 'harukas-kintetsu-food-hall']),
        color('hanshin-tigers', 'Hanshin Tigers', 'team', 'The baseball team followed with near-religious '
              'devotion; fans sing "Rokko Oroshi" at Koshien, and after the 2023 Japan Series title some jumped '
              'off Ebisubashi into the canal.', ['glico-sign'], ['spring', 'summer', 'fall']),
        color('orix-buffaloes', 'Orix Buffaloes', 'team', 'Osaka\'s other baseball team, playing at Kyocera Dome, '
              'Pacific League champions three years running from 2021.', ['kyocera-dome'],
              ['spring', 'summer', 'fall']),
        color('gamba-osaka', 'Gamba Osaka', 'team', 'J.League football club in blue and black, playing at '
              'Panasonic Stadium Suita.', ['panasonic-stadium-suita'], ['spring', 'summer', 'fall']),
        color('cerezo-osaka', 'Cerezo Osaka', 'team', 'The city\'s pink-shirted J.League club, named for the '
              'cherry blossom, at Nagai Park.', ['yodoko-sakura-stadium'], ['spring', 'summer', 'fall']),
        color('expo-2025-memories', 'Expo 2025 memories', 'other', 'The 2025 World Expo ran on the reclaimed '
              'island of Yumeshima from April to October 2025; Myaku-Myaku, its red and blue mascot, still turns '
              'up on souvenirs, and the island is now being rebuilt for a planned integrated resort.'),
        color('ehomaki', 'Ehomaki at Setsubun', 'custom', 'On Setsubun in early February people eat a whole '
              'uncut sushi roll in silence, facing the year\'s lucky direction, a custom spread from Osaka.',
              seasons=['winter']),
    ],
    'prices': [
        price('coffee', 'Kissaten blend coffee', 450, 650, 'a cup'),
        price('latte', 'Cafe latte', 480, 700),
        price('onigiri', 'Konbini onigiri', 150, 250, 'one rice ball'),
        price('takoyaki', 'Takoyaki', 500, 800, 'eight pieces'),
        price('cheap-lunch', 'Cheap lunch', 750, 1200, 'udon, curry or a set meal'),
        price('dinner', 'Izakaya dinner', 3000, 5000, 'for one, with a couple of drinks'),
        price('beer', 'Draft beer', 450, 750, 'a mug'),
        price('cocktail', 'Highball or cocktail', 400, 1000, 'a glass'),
        price('groceries', 'Groceries', 6000, 10000, 'a week, one person'),
        price('transit', 'Metro fare', 190, 390, 'one way'),
        price('rideshare', 'Taxi across town', 1800, 3500),
        price('movie', 'Movie ticket', 1900, 2200),
        price('show', 'Comedy at Namba Grand Kagetsu', 4000, 6000, 'a seat'),
        price('sento', 'Public bath (sento)', 550, 600, 'one entry'),
        price('gym', 'Gym membership', 7000, 12000, 'a month'),
        price('haircut', 'Haircut', 3000, 6000),
        price('wage', 'Day\'s pay', 8000, 12000, 'a day\'s take-home for an ordinary job'),
    ],
    'water': [
        {'kind': 'sea', 'name': 'Osaka Bay', 'side': 'west', 'width_km': 5},
        {'kind': 'river', 'name': 'Yodo River', 'width_km': 0.6, 'points': [
            [34.760, 135.565], [34.735, 135.530], [34.716, 135.500], [34.708, 135.470], [34.695, 135.440]]},
        {'kind': 'river', 'name': 'Okawa', 'width_km': 0.12, 'points': [
            [34.712, 135.523], [34.700, 135.518], [34.693, 135.510], [34.692, 135.495], [34.689, 135.478],
            [34.680, 135.460]]},
    ],
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
