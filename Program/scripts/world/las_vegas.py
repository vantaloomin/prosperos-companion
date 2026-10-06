"""Curated Las Vegas data. Run `python scripts/world/las_vegas.py` to rewrite the shipped JSON."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'cities' / 'las-vegas.json'
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
ALWAYS = ['morning', 'afternoon', 'evening', 'late']
# Outdoor desert outings: summer afternoons are dangerously hot.
MILD = ['fall', 'winter', 'spring']

CITY = {
    'schema_version': 1, 'id': 'las-vegas', 'name': 'Las Vegas', 'region': 'Nevada', 'country': 'US',
    'timezone': 'America/Los_Angeles', 'aliases': ['Vegas', 'Sin City', 'Las Vegas, NV', 'LV'],
    'summary': 'A desert metro in the Mojave built around the casino resorts of the Strip, with a 24-hour '
               'hospitality economy, sprawling master-planned suburbs and red-rock country on its edges.',
    'lat': 36.17, 'lon': -115.14,
    'speeds': {'walk': 4.5, 'car': 35, 'rideshare': 35, 'bus': 12, 'monorail': 20},
    # Rough heritage weights for residents' names (estimates, not census figures).
    'names': {'mix': {'anglo': 3.5, 'hispanic': 3, 'black-american': 1.2, 'east-asian': 1.2, 'italian': 0.3,
                       'irish': 0.3, 'jewish': 0.3, 'south-asian': 0.2, 'slavic': 0.2, 'caribbean': 0.1}},
    'sources': {
        S: {'kind': 'curated', 'title': 'Las Vegas places and neighborhoods written for Prospero Companion',
            'license': 'CC0-1.0', 'retrieved': '2026-10-05',
            'note': 'Well-known public places, institutions and employers from general knowledge. Businesses open '
                    'and close and rents move: treat this as a snapshot for fiction. Rents are rounded estimates '
                    'of typical asking ranges, not listings. Coordinates are approximate neighborhood centers.'},
        CLIMATE: {'kind': 'curated', 'title': 'Approximate monthly climate for Las Vegas (Harry Reid '
                  'International Airport)', 'license': 'CC0-1.0', 'retrieved': '2026-10-05',
                  'note': 'Rounded values in line with NOAA 1991-2020 normals; refresh with scripts/world when '
                          'network access to NOAA is available. Summer heat is extreme (often above 110F in July) '
                          'and most summer rain falls in brief monsoon storms from July to September.'},
    },
    'neighborhoods': [
        hood('the-strip', 'The Strip (Paradise)', 'Las Vegas Boulevard\'s megaresorts, casinos, arenas and '
             'high-rise condo towers in unincorporated Paradise, busy around the clock.',
             ['touristy', 'nightlife', '24-hour', 'casinos', 'iconic'], 36.114, -115.173, 'very-high',
             ([1300, 1900], [1600, 2600], [2300, 4000]), ['high-rise-condo', 'apartment'], 'high',
             ['deuce', 'monorail', 'rtc-bus', 'rideshare', 'walk']),
        hood('convention-center', 'Convention Center and Paradise Road', 'The blocks east of the Strip around the '
             'Las Vegas Convention Center, with older condos, apartments and off-Strip hotels.',
             ['business', 'conventions', 'central'], 36.131, -115.152, 'mid', ([950, 1300], [1150, 1550],
             [1450, 2000]), ['apartment', 'condo', 'high-rise-condo'], 'medium',
             ['monorail', 'rtc-bus', 'rideshare', 'car']),
        hood('downtown', 'Downtown and Fremont Street', 'The original casino district under the Fremont Street '
             'canopy, plus Fremont East bars, city and county offices, and Symphony Park.',
             ['historic', 'nightlife', 'casinos', 'gritty', 'central'], 36.170, -115.141, 'mid',
             ([900, 1300], [1100, 1600], [1400, 2100]), ['apartment', 'high-rise-condo', 'loft'], 'high',
             ['deuce', 'rtc-bus', 'rideshare', 'walk']),
        hood('arts-district', 'Arts District (18b)', 'Former industrial blocks south of downtown turned galleries, '
             'antique shops, craft bars and restaurants, with new apartment buildings.',
             ['arts', 'bars', 'food', 'up-and-coming'], 36.158, -115.152, 'mid', ([950, 1350], [1150, 1650],
             [1500, 2200]), ['apartment', 'loft', 'bungalow'], 'high', ['deuce', 'rtc-bus', 'rideshare', 'walk']),
        hood('chinatown', 'Chinatown (Spring Mountain Road)', 'Miles of strip-mall restaurants along Spring '
             'Mountain Road west of the Strip, many open late for casino workers and chefs.',
             ['food', 'diverse', 'late-night', 'asian'], 36.126, -115.197, 'low', ([850, 1100], [1000, 1350],
             [1250, 1700]), ['apartment', 'condo'], 'medium', ['rtc-bus', 'car', 'rideshare']),
        hood('medical-district', 'Medical District', 'The hospital cluster around University Medical Center near '
             'Charleston Boulevard and US 95, with older ranch homes and apartments.',
             ['medical', 'working-class', 'central'], 36.160, -115.168, 'low', ([800, 1050], [950, 1300],
             [1200, 1650]), ['apartment', 'single-family'], 'medium', ['rtc-bus', 'car']),
        hood('university-district', 'University District', 'The area around UNLV on Maryland Parkway, with student '
             'apartments, cheap eats and midcentury houses.', ['students', 'academic', 'affordable'], 36.108,
             -115.143, 'low', ([800, 1050], [950, 1300], [1200, 1650]),
             ['apartment', 'student-housing', 'single-family'], 'medium', ['rtc-bus', 'car', 'rideshare']),
        hood('eastside', 'East Las Vegas', 'Working-class east valley of ranch homes and apartments, with a large '
             'Latino community and taquerias along Fremont and Charleston.', ['diverse', 'affordable',
             'working-class', 'latino'], 36.160, -115.090, 'low', ([750, 1000], [900, 1200], [1100, 1550]),
             ['single-family', 'apartment', 'mobile-home'], 'low', ['rtc-bus', 'car']),
        hood('north-las-vegas', 'North Las Vegas', 'A separate city of newer subdivisions, warehouses and older '
             'neighborhoods, next to Nellis Air Force Base.', ['affordable', 'suburban', 'military', 'industrial'],
             36.220, -115.120, 'low', ([800, 1050], [950, 1300], [1250, 1700]),
             ['single-family', 'apartment', 'townhouse'], 'low', ['rtc-bus', 'car']),
        hood('centennial-hills', 'Centennial Hills', 'Northwest suburbs of stucco subdivisions and shopping '
             'centers on the road toward Mount Charleston.', ['suburban', 'family', 'quiet'], 36.275, -115.265,
             'mid', ([1000, 1300], [1200, 1550], [1500, 2000]), ['single-family', 'apartment', 'casita'], 'low',
             ['rtc-bus', 'car']),
        hood('summerlin', 'Summerlin', 'A large master-planned community on the west edge of the valley with '
             'trails, parks, a ballpark and Downtown Summerlin, beside Red Rock Canyon.',
             ['master-planned', 'affluent', 'family', 'outdoorsy'], 36.165, -115.320, 'high',
             ([1150, 1500], [1350, 1850], [1700, 2500]), ['master-planned', 'single-family', 'townhouse',
             'apartment', 'casita'], 'low', ['rtc-bus', 'car']),
        hood('spring-valley', 'Spring Valley', 'Central-west suburbs of apartment complexes and tract homes, where '
             'Chinatown\'s restaurants spill west along Spring Mountain and Rainbow.',
             ['suburban', 'diverse', 'affordable'], 36.108, -115.245, 'mid', ([900, 1150], [1050, 1400],
             [1350, 1800]), ['apartment', 'single-family', 'condo'], 'low', ['rtc-bus', 'car']),
        hood('enterprise', 'Southwest (Enterprise)', 'The fast-growing southwest valley of master-planned '
             'subdivisions like Mountain\'s Edge, plus data centers and warehouses.',
             ['suburban', 'new-build', 'family'], 36.025, -115.240, 'mid', ([1000, 1300], [1200, 1600],
             [1500, 2100]), ['master-planned', 'single-family', 'apartment', 'casita'], 'low', ['rtc-bus', 'car']),
        hood('southern-highlands', 'Southern Highlands', 'A master-planned community at the south end of the valley '
             'built around a private golf club, with gated enclaves.', ['affluent', 'gated', 'golf', 'quiet'],
             35.995, -115.200, 'high', ([1150, 1450], [1300, 1750], [1650, 2400]),
             ['master-planned', 'single-family', 'apartment'], 'low', ['car']),
        hood('green-valley', 'Green Valley (Henderson)', 'Henderson\'s older master-planned core of parks, '
             'schools and shopping centers, popular with families.', ['suburban', 'family', 'safe'], 36.035,
             -115.085, 'mid', ([1050, 1350], [1200, 1650], [1550, 2200]),
             ['master-planned', 'single-family', 'apartment', 'townhouse'], 'low', ['rtc-bus', 'car']),
        hood('henderson', 'Downtown Henderson', 'Henderson\'s original town center around Water Street, with '
             'newer subdivisions climbing toward the River Mountains.', ['suburban', 'small-town', 'family'],
             36.030, -114.982, 'mid', ([950, 1250], [1100, 1500], [1450, 2000]),
             ['single-family', 'apartment', 'townhouse'], 'medium', ['rtc-bus', 'car']),
        hood('lake-las-vegas', 'Lake Las Vegas', 'A resort community around a man-made lake at the eastern edge of '
             'Henderson, with Mediterranean-style condos and a village of restaurants.',
             ['waterfront', 'resort', 'quiet', 'affluent'], 36.105, -114.928, 'high', ([1200, 1500],
             [1400, 1900], [1800, 2700]), ['condo', 'villa', 'single-family'], 'low', ['car']),
        hood('boulder-city', 'Boulder City', 'A small, quiet town built for the Hoover Dam workers, with no casinos '
             'and Lake Mead on its doorstep.', ['small-town', 'historic', 'outdoorsy', 'quiet'], 35.979, -114.832,
             'mid', ([900, 1150], [1050, 1400], [1350, 1850]), ['single-family', 'apartment', 'mobile-home'],
             'medium', ['car']),
    ],
    'transit': [
        {'id': 'rtc-bus', 'name': 'RTC Transit buses', 'kind': 'bus', 'summary': 'The Regional Transportation '
         'Commission\'s valley-wide bus network, running 24 hours on major routes.', 'source': S},
        {'id': 'deuce', 'name': 'The Deuce', 'kind': 'bus', 'summary': 'Double-decker RTC buses running around the '
         'clock along the Strip to downtown.', 'source': S},
        {'id': 'monorail', 'name': 'Las Vegas Monorail', 'kind': 'monorail', 'summary': 'Elevated line behind the '
         'east side of the Strip from MGM Grand to SAHARA, with a stop at the Convention Center.', 'source': S},
        {'id': 'car', 'name': 'Driving', 'kind': 'car', 'summary': 'How most residents get around: wide arterials, '
         'the I-15 and the 215 beltway, and plentiful parking off the Strip.', 'source': S},
        {'id': 'rideshare', 'name': 'Rideshare and taxis', 'kind': 'rideshare', 'summary': 'Uber, Lyft and cabs '
         'with dedicated pickup areas at every resort and the airport.', 'source': S},
        {'id': 'walk', 'name': 'Walking', 'kind': 'walk', 'summary': 'Practical on the Strip and downtown via '
         'pedestrian bridges, though distances between resorts are long and summer heat is punishing.',
         'source': S},
    ],
    'places': [
        place('bellagio-fountains', 'Fountains of Bellagio', 'landmark', 'the-strip', 'Free water shows set to music '
              'on the lake in front of Bellagio, every half hour or so from the afternoon.',
              ['free', 'iconic', 'romantic', 'show'], 'free', 'outdoor', ALL, ['afternoon', 'evening', 'late']),
        place('bellagio-conservatory', 'Bellagio Conservatory & Botanical Gardens', 'attraction', 'the-strip',
              'Free indoor garden with elaborate floral displays that change with the seasons.',
              ['free', 'flowers', 'rainy-day'], 'free', 'indoor', ALL, ALWAYS),
        place('o-cirque', '"O" by Cirque du Soleil', 'venue', 'the-strip', 'Long-running water-themed Cirque show '
              'staged in and above a pool at Bellagio.', ['show', 'acrobatics', 'iconic'], '$$$$', 'indoor',
              ['date', 'friends', 'family'], DINNER),
        place('welcome-sign', 'Welcome to Fabulous Las Vegas sign', 'landmark', 'the-strip', 'The 1959 neon sign on '
              'the south Strip, with a small parking lot and a queue for photos.', ['photo-op', 'iconic', 'neon'],
              'free', 'outdoor', ALL, ALWAYS),
        place('high-roller', 'High Roller', 'attraction', 'the-strip', 'Giant observation wheel at The LINQ with '
              'glass cabins and Strip views; a full turn takes about half an hour.', ['views', 'iconic'], '$$$',
              'indoor', ALL, ['afternoon', 'evening', 'late']),
        place('linq-promenade', 'The LINQ Promenade', 'shopping', 'the-strip', 'Open-air street of bars, '
              'restaurants and shops between the Strip and the High Roller.', ['walk', 'bars', 'shops'], '$$',
              'outdoor', ALL, ['afternoon', 'evening', 'late']),
        place('brooklyn-bowl', 'Brooklyn Bowl', 'venue', 'the-strip', 'Bowling alley and concert venue on the LINQ '
              'Promenade.', ['live-music', 'bowling'], '$$', 'indoor', ['friends', 'date'], NIGHT),
        place('venetian-canals', 'Grand Canal Shoppes gondolas', 'attraction', 'the-strip', 'Gondola rides along '
              'indoor canals under a painted sky at The Venetian, with an outdoor canal on the Strip.',
              ['romantic', 'kitsch', 'shopping'], '$$$', 'mixed', ['date', 'family'], ['afternoon', 'evening']),
        place('sphere', 'Sphere', 'venue', 'the-strip', 'The LED-covered globe behind The Venetian, showing '
              'immersive films and concert residencies on a wraparound screen.', ['concerts', 'immersive', 'iconic'],
              '$$$$', 'indoor', ['friends', 'date', 'solo'], NIGHT),
        place('forum-shops', 'The Forum Shops at Caesars', 'shopping', 'the-strip', 'Luxury mall at Caesars Palace '
              'built like a Roman street, with a spiral escalator and animatronic fountain shows.',
              ['luxury', 'mall', 'rainy-day'], '$$$', 'indoor', ALL, ['afternoon', 'evening']),
        place('bacchanal-buffet', 'Bacchanal Buffet', 'restaurant', 'the-strip', 'Caesars Palace\'s huge buffet with '
              'hundreds of dishes across live-cooking stations.', ['buffet', 'splurge'], '$$$$', 'indoor', ALL,
              ['morning', 'afternoon', 'evening'], cuisine='buffet'),
        place('fashion-show-mall', 'Fashion Show Las Vegas', 'shopping', 'the-strip', 'Big indoor mall on the Strip '
              'with department stores and a runway in the center court.', ['mall', 'rainy-day'], '$$', 'indoor',
              ALL, ['afternoon', 'evening']),
        place('tacos-el-gordo', 'Tacos El Gordo', 'restaurant', 'the-strip', 'Tijuana-style taqueria on the north '
              'Strip with adobada shaved off the spit, open into the small hours.', ['tacos', 'late-night', 'cheap'],
              '$', 'indoor', ADULT, NIGHT, cuisine='mexican'),
        place('peppermill', 'Peppermill Restaurant & Fireside Lounge', 'restaurant', 'the-strip', 'Twenty-four-hour '
              'diner and neon-lit lounge with a firepit, unchanged since the 1970s.', ['24-hour', 'retro', 'diner'],
              '$$', 'indoor', ALL, ALWAYS, cuisine='american-diner'),
        place('hash-house-linq', 'Hash House A Go Go at The LINQ', 'restaurant', 'the-strip', 'Brunch spot known for '
              'enormous portions of farm-style breakfast.', ['brunch', 'huge-portions'], '$$', 'indoor', ALL, DAY,
              cuisine='american-breakfast'),
        place('golden-steer', 'Golden Steer Steakhouse', 'restaurant', 'the-strip', 'Old-Vegas steakhouse from 1958 '
              'with red leather booths and tableside Caesar salad.', ['steak', 'old-vegas', 'retro'], '$$$$',
              'indoor', ['date', 'friends'], DINNER, cuisine='steakhouse'),
        place('t-mobile-arena', 'T-Mobile Arena', 'stadium', 'the-strip', 'Home of the Vegas Golden Knights, also '
              'used for big concerts and fights.', ['hockey', 'concerts', 'sports'], '$$$', 'indoor',
              ['friends', 'family', 'date'], NIGHT),
        place('allegiant-stadium', 'Allegiant Stadium', 'stadium', 'the-strip', 'Domed home of the Las Vegas Raiders '
              'and UNLV football, just west of I-15 from Mandalay Bay.', ['football', 'concerts', 'sports'], '$$$$',
              'indoor', ['friends', 'family'], ['afternoon', 'evening']),
        place('shark-reef', 'Shark Reef Aquarium', 'attraction', 'the-strip', 'Aquarium at Mandalay Bay with a walk-'
              'through shark tunnel.', ['animals', 'kids', 'rainy-day'], '$$$', 'indoor', ['family', 'date'], DAY),
        place('strat-skypod', 'The STRAT SkyPod', 'attraction', 'the-strip', 'Observation deck atop the STRAT tower '
              'at the north end of the Strip, with thrill rides on the roof.', ['views', 'thrill-rides'], '$$$',
              'mixed', ['friends', 'date', 'family'], ['afternoon', 'evening', 'late']),
        place('area15', 'AREA15 and Omega Mart', 'attraction', 'the-strip', 'Immersive art and entertainment '
              'complex just west of the Strip, anchored by Meow Wolf\'s Omega Mart.', ['immersive', 'art',
              'quirky'], '$$$', 'indoor', ['friends', 'date', 'family'], ['afternoon', 'evening', 'late']),
        place('pinball-hall-of-fame', 'Pinball Hall of Fame', 'attraction', 'the-strip', 'Warehouse of playable '
              'vintage pinball and arcade machines near the Welcome sign.', ['arcade', 'retro', 'cheap'], '$',
              'indoor', ALL, ['afternoon', 'evening']),
        place('fremont-street-experience', 'Fremont Street Experience', 'landmark', 'downtown', 'Pedestrian mall of '
              'old casinos under a huge LED canopy with nightly light shows, buskers and a zipline.',
              ['neon', 'free', 'street-performers', 'iconic'], 'free', 'mixed', ADULT, NIGHT),
        place('mob-museum', 'The Mob Museum', 'museum', 'downtown', 'National museum of organised crime and law '
              'enforcement in the former federal courthouse, with a speakeasy and distillery downstairs.',
              ['history', 'crime', 'rainy-day'], '$$$', 'indoor', ['solo', 'friends', 'date'], DAY),
        place('neon-museum', 'The Neon Museum', 'museum', 'downtown', 'Outdoor "Neon Boneyard" of rescued casino '
              'signs, best on the evening guided tours when some are relit.', ['neon', 'history', 'photo-op'],
              '$$$', 'outdoor', ADULT, ['afternoon', 'evening']),
        place('container-park', 'Downtown Container Park', 'shopping', 'downtown', 'Small boutiques and bars in '
              'stacked shipping containers behind a fire-breathing praying mantis sculpture.',
              ['boutiques', 'quirky', 'kids'], '$$', 'outdoor', ALL, ['afternoon', 'evening']),
        place('atomic-liquors', 'Atomic Liquors', 'bar', 'downtown', 'Fremont East bar that dates to the 1950s, '
              'billed as the oldest freestanding bar in the city.', ['bar', 'historic', 'craft-beer'], '$$', 'indoor',
              ['friends', 'solo', 'date'], NIGHT),
        place('circa-stadium-swim', 'Stadium Swim at Circa', 'attraction', 'downtown', 'Tiered pool amphitheatre at '
              'Circa resort facing a giant screen showing live sports.', ['pool', 'sports', 'party'], '$$$',
              'outdoor', ['friends'], ['afternoon'], ['spring', 'summer', 'fall']),
        place('smith-center', 'The Smith Center for the Performing Arts', 'venue', 'downtown', 'Art deco performing '
              'arts center in Symphony Park hosting touring Broadway, the symphony and the ballet.',
              ['theater', 'broadway', 'classical'], '$$$', 'indoor', ['date', 'family', 'solo'], DINNER),
        place('discovery-childrens-museum', 'Discovery Children\'s Museum', 'museum', 'downtown', 'Three floors of '
              'hands-on exhibits in Symphony Park.', ['kids', 'rainy-day', 'science'], '$$', 'indoor', ['family'],
              DAY),
        place('publicus', 'PublicUs', 'cafe', 'downtown', 'Airy Fremont East coffee shop and bakery popular for '
              'laptop mornings.', ['coffee', 'pastries', 'brunch'], '$', 'indoor', ['solo', 'friends', 'date'], DAY,
              cuisine='cafe'),
        place('esthers-kitchen', 'Esther\'s Kitchen', 'restaurant', 'arts-district', 'Arts District Italian '
              'restaurant known for house-made pasta and sourdough.', ['pasta', 'local-favorite'], '$$$', 'indoor',
              ['date', 'friends'], ['afternoon', 'evening'], cuisine='italian'),
        place('velveteen-rabbit', 'Velveteen Rabbit', 'bar', 'arts-district', 'Moody craft cocktail bar with a '
              'patio in the Arts District.', ['cocktails', 'patio'], '$$', 'mixed', ['friends', 'date'], NIGHT),
        place('arts-factory', 'Arts Factory', 'attraction', 'arts-district', 'Converted building of galleries and '
              'studios at the heart of 18b and its First Friday art walk.', ['art', 'galleries', 'free'], 'free',
              'indoor', ADULT, ['afternoon', 'evening']),
        place('pho-kim-long', 'Pho Kim Long', 'restaurant', 'chinatown', 'Vietnamese noodle house on Spring '
              'Mountain Road open around the clock.', ['pho', '24-hour', 'cheap'], '$', 'indoor', ALL, ALWAYS,
              cuisine='vietnamese'),
        place('raku', 'Raku', 'restaurant', 'chinatown', 'Small Japanese robata grill famous for house-made tofu, '
              'open late and popular with off-duty chefs.', ['japanese', 'late-night', 'chef-favorite'], '$$$',
              'indoor', ['date', 'friends', 'solo'], NIGHT, cuisine='japanese'),
        place('chinatown-plaza', 'Chinatown Plaza', 'shopping', 'chinatown', 'The original 1990s Chinatown mall on '
              'Spring Mountain Road, with a gate, Asian grocers and restaurants.', ['food', 'groceries', 'asian'],
              '$', 'mixed', ALL, ['afternoon', 'evening']),
        place('herbs-and-rye', 'Herbs & Rye', 'bar', 'chinatown', 'Dim, award-winning cocktail bar on West Sahara '
              'with half-price steaks at happy hour.', ['cocktails', 'steak', 'happy-hour'], '$$$', 'indoor',
              ['date', 'friends'], NIGHT),
        place('lotus-of-siam', 'Lotus of Siam', 'restaurant', 'university-district', 'Celebrated Thai restaurant '
              'known for Northern Thai dishes and a long riesling list.', ['thai', 'local-favorite'], '$$$',
              'indoor', ['date', 'friends', 'family'], ['afternoon', 'evening'], cuisine='thai'),
        place('ellis-island', 'Ellis Island Casino & Brewery', 'bar', 'convention-center', 'Locals\' casino off the '
              'Strip with a brewery, karaoke lounge and a cheap steak special.', ['karaoke', 'brewery', 'locals'],
              '$', 'indoor', ['friends', 'solo'], NIGHT),
        place('thomas-and-mack', 'Thomas & Mack Center', 'stadium', 'university-district', 'UNLV\'s arena for '
              'Runnin\' Rebels basketball and the National Finals Rodeo.', ['basketball', 'rodeo', 'sports'], '$$',
              'indoor', ['friends', 'family'], NIGHT),
        place('barrick-museum', 'Marjorie Barrick Museum of Art', 'museum', 'university-district', 'Free '
              'contemporary art museum on the UNLV campus.', ['art', 'free', 'rainy-day'], 'free', 'indoor', ADULT,
              DAY),
        place('springs-preserve', 'Springs Preserve', 'museum', 'medical-district', 'Desert gardens, trails and '
              'museums at the site of the springs where Las Vegas began.', ['nature', 'history', 'kids'], '$$',
              'mixed', ALL, DAY),
        place('premium-outlets-north', 'Las Vegas North Premium Outlets', 'shopping', 'medical-district',
              'Large open-air outlet mall just west of downtown.', ['outlets', 'bargains'], '$$', 'outdoor', ALL,
              ['morning', 'afternoon', 'evening']),
        place('freeds-bakery', 'Freed\'s Bakery', 'cafe', 'eastside', 'Family bakery since the 1950s, known for '
              'elaborate custom cakes.', ['cakes', 'pastries', 'family-run'], '$', 'indoor', ALL, DAY,
              cuisine='bakery'),
        place('wetlands-park', 'Clark County Wetlands Park', 'park', 'eastside', 'Ponds, cottonwoods and trails '
              'along the Las Vegas Wash with a nature center and good birdwatching.', ['nature', 'birds', 'walk'],
              'free', 'outdoor', ALL, DAY, MILD),
        place('red-rock-canyon', 'Red Rock Canyon National Conservation Area', 'park', 'summerlin', 'Red sandstone '
              'cliffs on a 13-mile scenic loop drive with hiking and climbing, minutes from Summerlin.',
              ['hiking', 'climbing', 'scenic-drive', 'desert'], '$', 'outdoor', ALL, DAY, MILD),
        place('las-vegas-ballpark', 'Las Vegas Ballpark', 'stadium', 'summerlin', 'Minor-league home of the Las '
              'Vegas Aviators, with a pool beyond the outfield.', ['baseball', 'sports', 'family'], '$$', 'outdoor',
              ALL, ['evening'], ['spring', 'summer']),
        place('downtown-summerlin', 'Downtown Summerlin', 'shopping', 'summerlin', 'Open-air shopping and dining '
              'district at the center of Summerlin.', ['shops', 'restaurants', 'walk'], '$$', 'outdoor', ALL,
              ['afternoon', 'evening']),
        place('summerlin-farmers-market', 'Downtown Summerlin Farmers Market', 'market', 'summerlin', 'Weekly '
              'farmers market with produce, baked goods and food stalls.', ['farmers-market', 'food'], '$',
              'outdoor', ALL, ['morning']),
        place('floyd-lamb-park', 'Floyd Lamb Park at Tule Springs', 'park', 'centennial-hills', 'Shady historic '
              'ranch park with ponds, peacocks and old cottonwoods.', ['picnic', 'ponds', 'history'], 'free',
              'outdoor', ALL, DAY),
        place('mount-charleston', 'Mount Charleston', 'trail', 'centennial-hills', 'Pine forest trails in the Spring '
              'Mountains, about 45 minutes from the northwest valley and markedly cooler, with winter snow.',
              ['hiking', 'mountains', 'snow', 'cool-escape'], 'free', 'outdoor', ['solo', 'friends', 'family'], DAY),
        place('craig-ranch-park', 'Craig Ranch Regional Park', 'park', 'north-las-vegas', 'Large park in North Las '
              'Vegas with a skate park, dog parks and an outdoor amphitheatre.', ['park', 'dogs', 'concerts'],
              'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('valley-of-fire', 'Valley of Fire State Park', 'trail', 'north-las-vegas', 'Red sandstone formations '
              'and petroglyphs about an hour northeast of the city.', ['hiking', 'desert', 'day-trip'], '$',
              'outdoor', ALL, DAY, MILD),
        place('ethel-m', 'Ethel M Chocolates factory and cactus garden', 'attraction', 'green-valley', 'Chocolate '
              'factory with a free botanical cactus garden that is lit up for the holidays.',
              ['chocolate', 'free', 'garden'], 'free', 'mixed', ALL, ['afternoon', 'evening']),
        place('the-district-gvr', 'The District at Green Valley Ranch', 'shopping', 'green-valley', 'Walkable '
              'shopping street beside the Green Valley Ranch resort.', ['shops', 'restaurants'], '$$', 'outdoor',
              ALL, ['afternoon', 'evening']),
        place('water-street', 'Water Street District', 'landmark', 'henderson', 'Henderson\'s small historic main '
              'street with an events plaza, restaurants and a weekly farmers market.', ['main-street', 'events'],
              'free', 'outdoor', ALL, ['afternoon', 'evening']),
        place('sloan-canyon', 'Sloan Canyon National Conservation Area', 'trail', 'henderson', 'Desert hiking south '
              'of Henderson to a canyon of ancient petroglyphs.', ['hiking', 'petroglyphs', 'desert'], 'free',
              'outdoor', ['solo', 'friends', 'family'], ['morning'], MILD),
        place('river-mountains-loop', 'River Mountains Loop Trail', 'trail', 'henderson', 'Paved 34-mile loop '
              'linking Henderson, Boulder City and Lake Mead.', ['cycling', 'running', 'views'], 'free', 'outdoor',
              ['solo', 'friends'], ['morning'], MILD),
        place('lake-las-vegas-village', 'MonteLago Village', 'landmark', 'lake-las-vegas', 'Lakeside village of '
              'restaurants, paddleboard and boat rentals at Lake Las Vegas.', ['waterfront', 'paddleboard',
              'quiet'], '$$', 'outdoor', ['date', 'family', 'friends'], ['afternoon', 'evening']),
        place('hoover-dam', 'Hoover Dam', 'landmark', 'boulder-city', 'The 1930s concrete dam on the Colorado River '
              'at the Arizona line, with tours and a bypass bridge walkway.', ['history', 'engineering', 'views',
              'iconic'], '$$', 'mixed', ALL, DAY),
        place('lake-mead', 'Lake Mead National Recreation Area', 'park', 'boulder-city', 'Reservoir behind the dam '
              'for boating, kayaking and swimming at Boulder Beach, with the bathtub ring of drought visible.',
              ['lake', 'boating', 'swimming'], '$', 'outdoor', ALL, DAY, ['spring', 'summer', 'fall']),
        place('historic-railroad-trail', 'Historic Railroad Trail', 'trail', 'boulder-city', 'Flat gravel trail '
              'through five railroad tunnels above Lake Mead toward Hoover Dam; bighorn sheep are often seen.',
              ['hiking', 'history', 'wildlife'], '$', 'outdoor', ALL, ['morning'], MILD),
        place('seven-magic-mountains', 'Seven Magic Mountains', 'landmark', 'southern-highlands', 'Ugo Rondinone\'s '
              'stacks of day-glo painted boulders in the desert off I-15, about 20 minutes south of the valley.',
              ['art', 'photo-op', 'desert'], 'free', 'outdoor', ALL, DAY, MILD),
        # Everyday neighborhood spots: cafes, diners, pubs, libraries, parks and markets.
        place('hofbrauhaus-las-vegas', 'Hofbräuhaus Las Vegas', 'restaurant', 'convention-center', 'Munich '
              'beer-hall replica on Paradise Road with oompah bands, pretzels and steins.', ['beer-hall', 'german',
              'live-music'], '$$', 'indoor', ['friends', 'coworkers', 'family'], NIGHT, cuisine='german'),
        place('battistas', 'Battista\'s Hole in the Wall', 'restaurant', 'convention-center', 'Old-school Italian '
              'restaurant behind the Strip since 1970, with an accordion player and free house wine.',
              ['italian', 'old-school', 'kitschy'], '$$', 'indoor', ['date', 'friends', 'family'], DINNER,
              cuisine='italian'),
        place('westgate-las-vegas', 'Westgate Las Vegas', 'landmark', 'convention-center', 'The former Las Vegas '
              'Hilton beside the convention center, where Elvis played hundreds of shows, with a huge sportsbook.',
              ['casino', 'elvis', 'sportsbook'], '$$', 'indoor', ['friends', 'solo'], ALWAYS),
        place('winchester-park', 'Winchester Dondero Cultural Center', 'park', 'convention-center', 'County park '
              'and cultural center with a playground, gallery, classes and a small theater.', ['playground', 'arts',
              'classes'], 'free', 'mixed', ALL, ['morning', 'afternoon', 'evening']),
        place('main-street-antiques', 'Main Street antique row', 'shopping', 'arts-district', 'Blocks of vintage '
              'and antique shops selling midcentury furniture, casino memorabilia and old neon.',
              ['vintage', 'antiques', 'browsing'], '$$', 'indoor', ['solo', 'friends', 'date'], DAY),
        place('makers-and-finders', 'Makers & Finders', 'cafe', 'arts-district', 'Latin-inspired coffee bar and '
              'brunch spot in the Arts District.', ['coffee', 'brunch', 'latin'], '$$', 'indoor', ALL, DAY,
              cuisine='latin'),
        place('99-ranch-las-vegas', '99 Ranch Market', 'market', 'chinatown', 'Big Asian supermarket anchoring a '
              'Spring Mountain Road plaza, with a bakery and hot food counters.', ['grocery', 'asian'], '$',
              'indoor', ALL, ['morning', 'afternoon', 'evening']),
        place('ping-pang-pong', 'Ping Pang Pong', 'restaurant', 'chinatown', 'Locals\' dim sum restaurant inside '
              'the Gold Coast casino, packed for weekend lunches.', ['dim-sum', 'chinese', 'locals'], '$$', 'indoor',
              ALL, ['morning', 'afternoon', 'evening'], cuisine='chinese'),
        place('lorenzi-park', 'Lorenzi Park', 'park', 'medical-district', 'City park with a duck pond, tennis '
              'courts, a playground and a walking loop.', ['pond', 'playground', 'walk'], 'free', 'outdoor', ALL,
              ['morning', 'evening']),
        place('dona-maria-tamales', 'Doña Maria Tamales', 'restaurant', 'medical-district', 'Family Mexican '
              'restaurant on Charleston Boulevard famous for its tamales since the 1980s.', ['tamales', 'mexican',
              'local'], '$', 'indoor', ALL, ['morning', 'afternoon', 'evening'], cuisine='mexican'),
        place('west-las-vegas-library', 'West Las Vegas Library', 'library', 'medical-district', 'Historic Westside '
              'branch library with a theater and African American collections.', ['books', 'theater',
              'black-history'], 'free', 'indoor', ALL, DAY),
        place('clark-county-library', 'Clark County Library', 'library', 'university-district', 'Large library on '
              'Flamingo Road near UNLV with a theater and art gallery.', ['books', 'study', 'theater'], 'free',
              'indoor', ALL, ['morning', 'afternoon', 'evening']),
        place('crown-and-anchor', 'Crown & Anchor British Pub', 'bar', 'university-district', 'Twenty-four-hour '
              'British pub near UNLV with fish and chips and football on the TVs.', ['pub', 'british', 'late-night'],
              '$$', 'indoor', ['friends', 'solo'], ALWAYS, cuisine='british-pub'),
        place('east-las-vegas-library', 'East Las Vegas Library', 'library', 'eastside', 'Branch library with '
              'bilingual programs, computers and a busy children\'s room.', ['books', 'bilingual', 'kids'], 'free',
              'indoor', ALL, DAY),
        place('frenchman-mountain', 'Frenchman Mountain', 'trail', 'eastside', 'Steep, rocky hike up the mountain '
              'at the valley\'s east edge for a view over the whole city.', ['hiking', 'views', 'sunrise'], 'free',
              'outdoor', ['solo', 'friends'], ['morning'], MILD),
        place('commercial-center', 'Commercial Center', 'shopping', 'eastside', 'Aging 1960s shopping center on '
              'East Sahara, home to cheap Asian restaurants and some of the city\'s oldest gay bars.',
              ['cheap-eats', 'lgbtq', 'retro'], '$', 'mixed', ['friends', 'solo'], ['afternoon', 'evening', 'late']),
        place('huntridge-tavern', 'Huntridge Tavern', 'bar', 'eastside', 'Classic dive bar at Charleston and '
              'Maryland Parkway with cheap drinks and video poker.', ['dive-bar', 'video-poker', 'cheap'], '$',
              'indoor', ['friends', 'solo'], NIGHT),
        place('aliante-nature-park', 'Aliante Nature Discovery Park', 'park', 'north-las-vegas', 'Park with a lake, '
              'dinosaur-themed playground and walking paths.', ['lake', 'playground', 'walk'], 'free', 'outdoor',
              ALL, ['morning', 'evening']),
        place('alexander-library', 'Alexander Library', 'library', 'north-las-vegas', 'North Las Vegas branch '
              'library with study rooms and computers.', ['books', 'study', 'kids'], 'free', 'indoor', ALL, DAY),
        place('aliante-casino', 'Aliante Casino', 'nightlife', 'north-las-vegas', 'Locals casino with a movie '
              'theater, bars and a buffet.', ['casino', 'locals', 'movies'], '$$', 'indoor',
              ['friends', 'date'], NIGHT),
        place('tule-springs', 'Tule Springs Fossil Beds National Monument', 'trail', 'north-las-vegas', 'Open desert '
              'washes where Ice Age mammoth and camel fossils were found, with simple trailheads.',
              ['fossils', 'desert', 'hiking'], 'free', 'outdoor', ['solo', 'family', 'friends'], ['morning'], MILD),
        place('centennial-hills-library', 'Centennial Hills Library', 'library', 'centennial-hills', 'Big suburban '
              'branch library with a YMCA next door.', ['books', 'kids', 'study'], 'free', 'indoor', ALL, DAY),
        place('centennial-hills-park', 'Centennial Hills Park', 'park', 'centennial-hills', 'Large city park with '
              'an amphitheatre, fields, playgrounds and a dog park.', ['playground', 'dogs', 'sports'], 'free',
              'outdoor', ALL, ['morning', 'evening']),
        place('santa-fe-station', 'Santa Fe Station', 'nightlife', 'centennial-hills', 'Northwest locals casino '
              'with a bowling center, cinema and bars.', ['casino', 'bowling', 'locals'], '$$', 'indoor',
              ['friends', 'family', 'date'], ['afternoon', 'evening', 'late']),
        place('gilcrease-orchard', 'Gilcrease Orchard', 'market', 'centennial-hills', 'Pick-your-own orchard and '
              'farm stand with apples, pumpkins and cider doughnuts in autumn.', ['u-pick', 'pumpkins', 'family'],
              '$', 'outdoor', ALL, ['morning'], ['fall', 'spring']),
        place('honey-salt', 'Honey Salt', 'restaurant', 'summerlin', 'Neighborhood farm-to-table restaurant on '
              'Rampart, popular for brunch.', ['brunch', 'seasonal', 'local'], '$$$', 'indoor',
              ['date', 'friends', 'family'], ['morning', 'afternoon', 'evening'], cuisine='american'),
        place('summerlin-library', 'Summerlin Library', 'library', 'summerlin', 'Branch library with a performing '
              'arts theater and gallery.', ['books', 'theater', 'quiet'], 'free', 'indoor', ALL, DAY),
        place('sahara-west-library', 'Sahara West Library', 'library', 'spring-valley', 'Large branch library with '
              'a gallery and many study rooms.', ['books', 'study', 'art'], 'free', 'indoor', ALL,
              ['morning', 'afternoon', 'evening']),
        place('desert-breeze-park', 'Desert Breeze Park', 'park', 'spring-valley', 'County park with a community '
              'center, aquatic complex, skate park and dog park.', ['pool', 'skate', 'dogs'], 'free', 'mixed', ALL,
              ['morning', 'afternoon', 'evening']),
        place('spring-valley-library', 'Spring Valley Library', 'library', 'spring-valley', 'Neighborhood branch '
              'library with story times and computers.', ['books', 'kids', 'computers'], 'free', 'indoor', ALL, DAY),
        place('orleans-arena', 'Orleans Arena', 'venue', 'spring-valley', 'Mid-sized arena at the Orleans casino '
              'for concerts, rodeo finals and college tournaments.', ['concerts', 'sports'], '$$', 'indoor',
              ['friends', 'family'], ['evening']),
        place('orleans-bowling', 'Orleans Bowling Center', 'fitness', 'spring-valley', 'Big locals bowling center '
              'inside the Orleans, with leagues and late-night games.', ['bowling', 'leagues', 'late-night'], '$',
              'indoor', ALL, ALWAYS),
        place('shang-artisan-noodle', 'Shang Artisan Noodle', 'restaurant', 'spring-valley', 'Strip-mall noodle '
              'shop on Flamingo where the beef noodle soup comes with noodles hand-pulled to order.',
              ['noodles', 'cheap', 'locals'], '$', 'indoor', ALL, ['afternoon', 'evening'], cuisine='chinese'),
        place('mountains-edge-park', 'Mountain\'s Edge Regional Park', 'park', 'enterprise', 'Large park with '
              'fields, playgrounds and a dog park at the foot of the southwest hills.', ['playground', 'dogs',
              'sports'], 'free', 'outdoor', ALL, ['morning', 'evening']),
        place('exploration-peak', 'Exploration Peak Park', 'trail', 'enterprise', 'Park with a short summit trail '
              'and views over the southwest valley.', ['hiking', 'views', 'playground'], 'free', 'outdoor', ALL,
              ['morning', 'evening'], MILD),
        place('enterprise-library', 'Enterprise Library', 'library', 'enterprise', 'Branch library serving the '
              'southwest suburbs.', ['books', 'kids', 'study'], 'free', 'indoor', ALL, DAY),
        place('windmill-library', 'Windmill Library', 'library', 'enterprise', 'Branch library with a large '
              'children\'s area and study rooms.', ['books', 'kids', 'study'], 'free', 'indoor', ALL, DAY),
        place('town-square-las-vegas', 'Town Square Las Vegas', 'shopping', 'enterprise', 'Open-air shopping and '
              'restaurant center with a cinema and a children\'s park.', ['shopping', 'cinema', 'restaurants'],
              '$$', 'outdoor', ALL, ['afternoon', 'evening']),
        place('yard-house-town-square', 'Yard House at Town Square', 'bar', 'enterprise', 'Big sports-bar '
              'restaurant at Town Square with a long wall of draft taps and a busy happy hour.', ['beer',
              'happy-hour', 'sports'], '$$', 'indoor', ADULT + ['coworkers'], NIGHT, cuisine='american'),
        place('m-resort', 'M Resort', 'nightlife', 'southern-highlands', 'Locals resort casino at the south end of '
              'Las Vegas Boulevard with a pool deck and lounge views up the valley.', ['casino', 'views', 'locals'],
              '$$', 'indoor', ['friends', 'date'], NIGHT),
        place('studio-b-buffet', 'Studio B Buffet', 'restaurant', 'southern-highlands', 'The M Resort\'s buffet, a '
              'locals\' favorite with free beer and wine.', ['buffet', 'locals'], '$$', 'indoor', ALL,
              ['morning', 'afternoon', 'evening'], cuisine='buffet'),
        place('south-point-bowling', 'South Point Bowling Center', 'fitness', 'southern-highlands', 'Large bowling '
              'center at the South Point casino, open around the clock.', ['bowling', 'leagues', 'late-night'], '$',
              'indoor', ALL, ALWAYS),
        place('silverado-ranch-park', 'Silverado Ranch Park', 'park', 'southern-highlands', 'County park with '
              'fields, playgrounds and shaded picnic areas.', ['playground', 'sports', 'picnic'], 'free', 'outdoor',
              ALL, ['morning', 'evening']),
        place('paseo-verde-library', 'Paseo Verde Library', 'library', 'green-valley', 'Henderson branch library '
              'with a gallery and a park next door.', ['books', 'kids', 'art'], 'free', 'indoor', ALL, DAY),
        place('sunset-park', 'Sunset Park', 'park', 'green-valley', 'Big county park with a pond, disc golf, '
              'volleyball and dog runs.', ['pond', 'disc-golf', 'dogs'], 'free', 'outdoor', ALL,
              ['morning', 'evening']),
        place('green-valley-ranch', 'Green Valley Ranch Resort', 'nightlife', 'green-valley', 'Henderson locals '
              'resort with a casino, pool scene and restaurants.', ['casino', 'pool', 'locals'], '$$', 'mixed',
              ['friends', 'date'], NIGHT),
        place('henderson-bird-preserve', 'Henderson Bird Viewing Preserve', 'park', 'henderson', 'Ponds at the '
              'water-treatment plant where hundreds of bird species stop over; free and quiet.', ['birds', 'nature',
              'quiet'], 'free', 'outdoor', ['solo', 'family', 'date'], ['morning']),
        place('gibson-library', 'James I. Gibson Library', 'library', 'henderson', 'Henderson\'s central branch '
              'library near Water Street.', ['books', 'kids', 'study'], 'free', 'indoor', ALL, DAY),
        place('emerald-island-casino', 'Emerald Island Casino', 'nightlife', 'henderson', 'Small Irish-themed '
              'locals casino on Water Street with video poker, a bar and a cheap grill.', ['casino', 'locals',
              'cheap'], '$', 'indoor', ADULT, NIGHT),
        place('lake-las-vegas-water-sports', 'Lake Las Vegas Water Sports', 'fitness', 'lake-las-vegas', 'Kayak, '
              'paddleboard and pedal-boat rentals on the lake.', ['kayaking', 'paddleboard'], '$$', 'outdoor', ALL,
              DAY, ['spring', 'summer', 'fall']),
        place('reflection-bay-golf', 'Reflection Bay Golf Club', 'fitness', 'lake-las-vegas', 'Jack Nicklaus-'
              'designed public golf course along the lakeshore.', ['golf', 'views'], '$$$', 'outdoor',
              ['friends', 'coworkers', 'solo'], DAY),
        place('lake-las-vegas-path', 'Lake Las Vegas lakeside path', 'trail', 'lake-las-vegas', 'Walking path '
              'around the lake past the village and its bridges.', ['walk', 'lake', 'running'], 'free', 'outdoor',
              ALL, ['morning', 'evening']),
        place('luna-rossa', 'Luna Rossa', 'restaurant', 'lake-las-vegas', 'Italian restaurant in MonteLago '
              'Village with a patio over the water and pasta made in-house.', ['italian', 'lakeside', 'patio'],
              '$$$', 'mixed', ['date', 'friends', 'family'], DINNER, cuisine='italian'),
        place('northshore-road', 'Northshore Road scenic drive', 'landmark', 'lake-las-vegas', 'Desert drive from '
              'Lake Las Vegas into Lake Mead National Recreation Area, past red rock and coves.',
              ['scenic-drive', 'desert', 'views'], '$', 'outdoor', ['solo', 'friends', 'date'], DAY, MILD),
        place('boulder-dam-brewing', 'Boulder Dam Brewing Company', 'restaurant', 'boulder-city', 'Small-town '
              'brewpub with a patio, pub food and dam-themed beers.', ['brewery', 'patio', 'local'], '$$', 'mixed',
              ALL, ['afternoon', 'evening'], cuisine='american-pub'),
        place('boulder-city-library', 'Boulder City Library', 'library', 'boulder-city', 'The town\'s friendly '
              'public library, a short walk from the historic district.', ['books', 'kids', 'quiet'], 'free',
              'indoor', ALL, DAY),
        place('boulder-dam-hotel', 'Boulder Dam Hotel and Museum', 'museum', 'boulder-city', 'Historic 1930s hotel '
              'with a small museum on the building of the dam.', ['history', 'museum', 'hotel'], '$', 'indoor', ALL,
              DAY),
        # Everyday routines: coffee and pastry stops and places to work out.
        place('bellagio-patisserie', 'Bellagio Patisserie', 'cafe', 'the-strip', 'Pastry shop at Bellagio, '
              'formerly Jean Philippe, with a tall chocolate fountain in the window.', ['pastry', 'chocolate',
              'dessert'], '$$', 'indoor', ALL, ['morning', 'afternoon', 'evening'], cuisine='french-pastry'),
        place('mothership-coffee', 'Mothership Coffee Roasters', 'cafe', 'green-valley', 'Henderson roaster\'s '
              'airy coffee shop with pastries and a patio.', ['coffee', 'roaster', 'laptop'], '$', 'mixed',
              ['solo', 'friends', 'coworkers'], DAY, cuisine='coffee'),
        place('coffee-cup-boulder-city', 'The Coffee Cup', 'cafe', 'boulder-city', 'Small diner on Nevada Way known '
              'for big breakfasts and a line of Hoover Dam visitors.', ['breakfast', 'diner', 'local'], '$',
              'indoor', ALL, ['morning'], cuisine='american-breakfast'),
        place('donut-bar', 'Donut Bar', 'cafe', 'downtown', 'Downtown doughnut shop that often sells out of its '
              'oversized doughnuts by late morning.', ['doughnuts', 'line', 'breakfast'], '$', 'indoor', ALL,
              ['morning'], cuisine='bakery'),
        place('bagel-cafe', 'The Bagel Cafe', 'cafe', 'summerlin', 'Long-running Jewish deli and bakery on Buffalo '
              'Drive for bagels, breakfast and sandwiches.', ['bagels', 'deli', 'breakfast'], '$', 'indoor', ALL,
              DAY, cuisine='jewish-deli'),
        place('red-rock-climbing-center', 'Red Rock Climbing Center', 'fitness', 'summerlin', 'Climbing gym on '
              'West Charleston used by local climbers training for Red Rock Canyon.', ['climbing', 'bouldering',
              'yoga'], '$$', 'indoor', ['solo', 'friends', 'date'], ['morning', 'evening']),
        place('centennial-hills-ymca', 'Centennial Hills YMCA', 'fitness', 'centennial-hills', 'Northwest Y beside '
              'the library, with indoor and outdoor pools and a gym.', ['gym', 'pool', 'classes'], '$', 'mixed',
              ALL, ['morning', 'evening']),
        place('henderson-multigen', 'Henderson Multigenerational Center', 'fitness', 'henderson', 'City recreation '
              'center with pools, a climbing wall, a track and fitness classes.', ['rec-center', 'pool', 'classes'],
              '$', 'indoor', ALL, ['morning', 'evening']),
        place('mayweather-boxing', 'Mayweather Boxing Club', 'fitness', 'chinatown', 'Floyd Mayweather\'s boxing '
              'gym west of the Strip, where pros train and the public can take classes.', ['boxing', 'training'],
              '$$', 'indoor', ['solo', 'friends'], ['morning', 'evening']),
    ],
    'colleges': [
        {'id': 'unlv', 'name': 'University of Nevada, Las Vegas', 'type': 'research-university',
         'neighborhood': 'university-district', 'size': 'large', 'known_for': ['hospitality', 'gaming',
         'engineering', 'nursing', 'business'], 'source': S},
        {'id': 'unlv-medicine', 'name': 'Kirk Kerkorian School of Medicine at UNLV', 'type': 'medical-school',
         'neighborhood': 'medical-district', 'size': 'small', 'known_for': ['medicine', 'residency-training'],
         'source': S},
        {'id': 'unlv-law', 'name': 'William S. Boyd School of Law', 'type': 'research-university',
         'neighborhood': 'university-district', 'size': 'small', 'known_for': ['law', 'gaming-law'], 'source': S},
        {'id': 'csn-charleston', 'name': 'College of Southern Nevada (Charleston campus)', 'type': 'community-college',
         'neighborhood': 'spring-valley', 'size': 'large', 'known_for': ['health-sciences', 'transfer',
         'hospitality'], 'source': S},
        {'id': 'csn-north', 'name': 'College of Southern Nevada (North Las Vegas campus)',
         'type': 'community-college', 'neighborhood': 'north-las-vegas', 'size': 'large',
         'known_for': ['transfer', 'automotive', 'trades'], 'source': S},
        {'id': 'csn-henderson', 'name': 'College of Southern Nevada (Henderson campus)', 'type': 'community-college',
         'neighborhood': 'henderson', 'size': 'medium', 'known_for': ['transfer', 'nursing'], 'source': S},
        {'id': 'nevada-state', 'name': 'Nevada State University', 'type': 'public-university',
         'neighborhood': 'henderson', 'size': 'medium', 'known_for': ['nursing', 'education', 'psychology'],
         'source': S},
        {'id': 'touro-nevada', 'name': 'Touro University Nevada', 'type': 'medical-school',
         'neighborhood': 'green-valley', 'size': 'small', 'known_for': ['osteopathic-medicine', 'physician-assistant',
         'nursing'], 'source': S},
        {'id': 'roseman', 'name': 'Roseman University of Health Sciences', 'type': 'medical-school',
         'neighborhood': 'green-valley', 'size': 'small', 'known_for': ['pharmacy', 'nursing', 'dental-medicine'],
         'source': S},
    ],
    'employers': [
        {'id': 'mgm-resorts', 'name': 'MGM Resorts International', 'sector': 'hospitality',
         'neighborhood': 'the-strip', 'size': 'large', 'summary': 'Runs Bellagio, MGM Grand, Aria, Mandalay Bay and '
         'other Strip resorts; the largest private employer in the state.', 'careers': ['casino-dealer',
         'hotel-front-desk', 'bartender', 'server', 'line-cook', 'event-planner', 'data-analyst', 'accountant',
         'marketing-coordinator'], 'source': S},
        {'id': 'caesars', 'name': 'Caesars Entertainment', 'sector': 'hospitality', 'neighborhood': 'the-strip',
         'size': 'large', 'summary': 'Operates Caesars Palace, The LINQ, Paris, Harrah\'s and other Strip '
         'resorts.', 'careers': ['casino-dealer', 'hotel-front-desk', 'bartender', 'server', 'line-cook',
         'event-planner', 'marketing-coordinator'], 'source': S},
        {'id': 'wynn', 'name': 'Wynn Las Vegas and Encore', 'sector': 'hospitality', 'neighborhood': 'the-strip',
         'size': 'large', 'summary': 'Luxury resort pair on the north Strip with high-end shops and nightlife.',
         'careers': ['casino-dealer', 'hotel-front-desk', 'bartender', 'server', 'line-cook', 'retail-associate',
         'event-planner'], 'source': S},
        {'id': 'venetian', 'name': 'The Venetian Resort', 'sector': 'hospitality', 'neighborhood': 'the-strip',
         'size': 'large', 'summary': 'All-suite resort with a casino, shopping canals and a large expo hall.',
         'careers': ['casino-dealer', 'hotel-front-desk', 'server', 'line-cook', 'event-planner'], 'source': S},
        {'id': 'resorts-world', 'name': 'Resorts World Las Vegas', 'sector': 'hospitality',
         'neighborhood': 'the-strip', 'size': 'large', 'summary': 'Newer north Strip resort with a casino, three '
         'Hilton hotels and a food hall.', 'careers': ['casino-dealer', 'hotel-front-desk', 'bartender', 'server',
         'line-cook'], 'source': S},
        {'id': 'station-casinos', 'name': 'Station Casinos (Red Rock Resorts)', 'sector': 'hospitality',
         'neighborhood': 'summerlin', 'size': 'large', 'summary': 'Locals\' casino company headquartered in '
         'Summerlin, running Red Rock, Green Valley Ranch, Durango and others.', 'careers': ['casino-dealer',
         'bartender', 'server', 'line-cook', 'accountant', 'financial-analyst', 'marketing-coordinator'],
         'source': S},
        {'id': 'cirque-du-soleil', 'name': 'Cirque du Soleil resident shows', 'sector': 'entertainment',
         'neighborhood': 'the-strip', 'size': 'medium', 'summary': 'Several permanent Cirque productions in Strip '
         'resort theaters, with artists, musicians and technical crews.', 'careers': ['performer', 'musician',
         'actor'], 'source': S},
        {'id': 'lvcva', 'name': 'Las Vegas Convention and Visitors Authority', 'sector': 'tourism',
         'neighborhood': 'convention-center', 'size': 'medium', 'summary': 'Runs the Las Vegas Convention Center '
         'and markets the city to visitors and trade shows.', 'careers': ['event-planner', 'marketing-coordinator',
         'government-analyst', 'tour-guide'], 'source': S},
        {'id': 'harry-reid-airport', 'name': 'Harry Reid International Airport', 'sector': 'logistics',
         'neighborhood': 'the-strip', 'size': 'large', 'summary': 'The county-run airport just east of the south '
         'Strip, with airline, cargo, concession and security jobs.', 'careers': ['port-logistics',
         'retail-associate', 'server'], 'source': S},
        {'id': 'allegiant-air', 'name': 'Allegiant Air', 'sector': 'aviation', 'neighborhood': 'summerlin',
         'size': 'medium', 'summary': 'Low-cost airline headquartered in Summerlin.', 'careers': ['data-analyst',
         'software-engineer', 'financial-analyst', 'accountant', 'marketing-coordinator'], 'source': S},
        {'id': 'switch', 'name': 'Switch', 'sector': 'technology', 'neighborhood': 'enterprise', 'size': 'medium',
         'summary': 'Data center company with large campuses in the southwest valley.', 'careers':
         ['software-engineer', 'data-analyst', 'construction-trades'], 'source': S},
        {'id': 'zappos', 'name': 'Zappos', 'sector': 'technology', 'neighborhood': 'downtown', 'size': 'medium',
         'summary': 'Online shoe and clothing retailer headquartered in the old City Hall downtown.',
         'careers': ['software-engineer', 'ux-designer', 'graphic-designer', 'marketing-coordinator',
         'data-analyst'], 'source': S},
        {'id': 'raiders', 'name': 'Las Vegas Raiders', 'sector': 'sports', 'neighborhood': 'henderson',
         'size': 'medium', 'summary': 'NFL team with its headquarters and practice facility in Henderson.',
         'careers': ['fitness-trainer', 'marketing-coordinator', 'event-planner', 'data-analyst'], 'source': S},
        {'id': 'umc', 'name': 'University Medical Center of Southern Nevada', 'sector': 'healthcare',
         'neighborhood': 'medical-district', 'size': 'large', 'summary': 'The county public hospital with the '
         'state\'s only Level I trauma center, and UNLV\'s main teaching hospital.', 'careers': ['registered-nurse',
         'night-nurse', 'physician-resident', 'pharmacist', 'social-worker'], 'source': S},
        {'id': 'sunrise-hospital', 'name': 'Sunrise Hospital and Medical Center', 'sector': 'healthcare',
         'neighborhood': 'university-district', 'size': 'large', 'summary': 'Large HCA hospital on Maryland Parkway '
         'with a children\'s hospital.', 'careers': ['registered-nurse', 'night-nurse', 'physician-resident',
         'pharmacist'], 'source': S},
        {'id': 'st-rose-dominican', 'name': 'Dignity Health St. Rose Dominican', 'sector': 'healthcare',
         'neighborhood': 'green-valley', 'size': 'large', 'summary': 'Catholic hospital group with several '
         'campuses in Henderson.', 'careers': ['registered-nurse', 'night-nurse', 'pharmacist', 'social-worker'],
         'source': S},
        {'id': 'lou-ruvo-center', 'name': 'Cleveland Clinic Lou Ruvo Center for Brain Health', 'sector': 'healthcare',
         'neighborhood': 'downtown', 'size': 'small', 'summary': 'Neurology clinic and research center in a Frank '
         'Gehry building in Symphony Park.', 'careers': ['medical-researcher', 'registered-nurse'], 'source': S},
        {'id': 'unlv-employer', 'name': 'UNLV', 'sector': 'education', 'neighborhood': 'university-district',
         'size': 'large', 'summary': 'Faculty, research and staff jobs at the main university campus.',
         'careers': ['professor', 'graduate-student', 'medical-researcher', 'data-analyst'], 'source': S},
        {'id': 'ccsd', 'name': 'Clark County School District', 'sector': 'education', 'neighborhood': 'spring-valley',
         'size': 'large', 'summary': 'One of the largest school districts in the country, chronically short of '
         'teachers.', 'careers': ['teacher', 'social-worker'], 'source': S},
        {'id': 'clark-county', 'name': 'Clark County government and courts', 'sector': 'government',
         'neighborhood': 'downtown', 'size': 'large', 'summary': 'County agencies at the Government Center and the '
         'Regional Justice Center downtown; the county also governs the Strip.', 'careers': ['government-analyst',
         'social-worker', 'accountant', 'paralegal'], 'source': S},
        {'id': 'city-of-las-vegas', 'name': 'City of Las Vegas', 'sector': 'government', 'neighborhood': 'downtown',
         'size': 'medium', 'summary': 'City Hall and municipal departments on Main Street.',
         'careers': ['government-analyst', 'accountant'], 'source': S},
        {'id': 'nellis-afb', 'name': 'Nellis Air Force Base', 'sector': 'defense', 'neighborhood': 'north-las-vegas',
         'size': 'large', 'summary': 'Major Air Force base for advanced fighter training, with civilian and '
         'contractor engineering jobs.', 'careers': ['defense-engineer'], 'source': S},
        {'id': 'review-journal', 'name': 'Las Vegas Review-Journal', 'sector': 'media', 'neighborhood': 'downtown',
         'size': 'small', 'summary': 'The state\'s largest daily newspaper.', 'careers': ['journalist'],
         'source': S},
    ],
    'career_hubs': [
        {'id': 'strip-resorts', 'name': 'The Strip resorts', 'neighborhoods': ['the-strip'],
         'sectors': ['hospitality', 'entertainment', 'tourism', 'retail', 'fitness', 'recreation'],
         'summary': 'Tens of thousands of casino, hotel, kitchen, spa, pool and show jobs running 24 hours a day.',
         'source': S},
        {'id': 'convention-corridor', 'name': 'Convention Center and Paradise Road', 'neighborhoods':
         ['convention-center', 'the-strip'], 'sectors': ['hospitality', 'business', 'tourism'], 'summary':
         'Trade-show work around the Las Vegas Convention Center and resort expo halls.', 'source': S},
        {'id': 'downtown-core', 'name': 'Downtown and the Arts District', 'neighborhoods': ['downtown',
         'arts-district'], 'sectors': ['government', 'legal', 'media', 'technology', 'hospitality', 'creative'],
         'summary': 'City and county offices, the courts, Fremont Street casinos, tech offices and small creative '
         'studios.', 'source': S},
        {'id': 'medical-hub', 'name': 'Medical District and UNLV', 'neighborhoods': ['medical-district',
         'university-district'], 'sectors': ['healthcare', 'education', 'biotech'], 'summary': 'UMC, the UNLV '
         'medical school and nearby hospitals, plus the main university campus.', 'source': S},
        {'id': 'summerlin-corporate', 'name': 'Summerlin offices', 'neighborhoods': ['summerlin',
         'centennial-hills'], 'sectors': ['business', 'finance', 'technology', 'real-estate', 'aviation'],
         'summary': 'Corporate headquarters, banks and real-estate offices in the west valley.', 'source': S},
        {'id': 'henderson-hub', 'name': 'Henderson', 'neighborhoods': ['henderson', 'green-valley'],
         'sectors': ['healthcare', 'education', 'sports', 'real-estate', 'retail'], 'summary': 'Hospitals, health '
         'sciences schools, the Raiders\' headquarters and fast-growing suburban retail.', 'source': S},
        {'id': 'southwest-industrial', 'name': 'Southwest warehouses and data centers', 'neighborhoods':
         ['enterprise', 'spring-valley'], 'sectors': ['logistics', 'technology', 'construction'], 'summary':
         'Distribution centers, data centers and home building in the growing southwest valley.', 'source': S},
        {'id': 'north-valley', 'name': 'Nellis and North Las Vegas', 'neighborhoods': ['north-las-vegas'],
         'sectors': ['defense', 'logistics', 'manufacturing', 'construction'], 'summary': 'The air base, '
         'industrial parks and warehouses along I-15 north.', 'source': S},
    ],
    'climate': {
        'summary': 'Hot desert: very hot, dry summers with brief monsoon storms, mild sunny winters with cold '
                   'nights, and very little rain at any time of year.',
        'months': [
            {'high_f': 58, 'low_f': 40, 'rain_days': 3, 'note': 'Coolest month; sunny days, chilly nights.'},
            {'high_f': 63, 'low_f': 44, 'rain_days': 4, 'note': 'Mild and dry; occasional windy storms.'},
            {'high_f': 71, 'low_f': 50, 'rain_days': 3, 'note': 'Pleasant; spring wind gusts.'},
            {'high_f': 79, 'low_f': 57, 'rain_days': 2, 'note': 'Warm and dry; prime hiking season ends.'},
            {'high_f': 89, 'low_f': 67, 'rain_days': 1, 'note': 'Hot; pool season opens.'},
            {'high_f': 99, 'low_f': 76, 'rain_days': 1, 'note': 'Very hot and bone dry.'},
            {'high_f': 105, 'low_f': 82, 'rain_days': 2, 'note': 'Hottest month; 110F days and monsoon storms.'},
            {'high_f': 103, 'low_f': 81, 'rain_days': 3, 'note': 'Extreme heat; monsoon flash floods possible.'},
            {'high_f': 95, 'low_f': 73, 'rain_days': 2, 'note': 'Still hot; monsoon fades.'},
            {'high_f': 81, 'low_f': 60, 'rain_days': 2, 'note': 'Warm, sunny and comfortable.'},
            {'high_f': 67, 'low_f': 47, 'rain_days': 2, 'note': 'Mild days, cool nights.'},
            {'high_f': 57, 'low_f': 39, 'rain_days': 3, 'note': 'Cool; occasional freezing nights.'},
        ],
        'source': CLIMATE,
    },
    'annual_events': [
        {'id': 'ces', 'name': 'CES', 'months': [1], 'neighborhood': 'convention-center', 'summary': 'The giant '
         'consumer electronics trade show fills the Convention Center and hotels in early January.', 'source': S},
        {'id': 'chinese-new-year', 'name': 'Chinese New Year in Chinatown', 'months': [1, 2],
         'neighborhood': 'chinatown', 'summary': 'Lion dances and celebrations on Spring Mountain Road, with '
         'decorations at Strip resorts.', 'source': S},
        {'id': 'first-friday', 'name': 'First Friday', 'months': list(range(1, 13)), 'neighborhood': 'arts-district',
         'summary': 'Monthly evening art walk with open galleries, food trucks and live music.', 'source': S},
        {'id': 'nascar-weekends', 'name': 'NASCAR at Las Vegas Motor Speedway', 'months': [3, 10],
         'neighborhood': 'north-las-vegas', 'summary': 'Cup Series race weekends in spring and autumn at the '
         'speedway in the northeast valley.', 'source': S},
        {'id': 'aviators-season', 'name': 'Aviators baseball season', 'months': [4, 5, 6, 7, 8, 9],
         'neighborhood': 'summerlin', 'summary': 'Triple-A baseball nights at Las Vegas Ballpark.', 'source': S},
        {'id': 'edc', 'name': 'Electric Daisy Carnival', 'months': [5], 'neighborhood': 'north-las-vegas',
         'summary': 'Huge three-night electronic music festival at Las Vegas Motor Speedway.', 'source': S},
        {'id': 'punk-rock-bowling', 'name': 'Punk Rock Bowling', 'months': [5], 'neighborhood': 'downtown',
         'summary': 'Memorial Day weekend punk festival downtown with a bowling tournament.', 'source': S},
        {'id': 'raiders-season', 'name': 'Raiders football season', 'months': [9, 10, 11, 12, 1],
         'neighborhood': 'the-strip', 'summary': 'NFL game days at Allegiant Stadium.', 'source': S},
        {'id': 'golden-knights-season', 'name': 'Golden Knights hockey season', 'months': [10, 11, 12, 1, 2, 3, 4],
         'neighborhood': 'the-strip', 'summary': 'NHL games with elaborate pregame shows at T-Mobile Arena.',
         'source': S},
        {'id': 'sema', 'name': 'SEMA Show', 'months': [11], 'neighborhood': 'convention-center', 'summary': 'Car '
         'customisation trade show that brings custom builds to the Convention Center.', 'source': S},
        {'id': 'f1-grand-prix', 'name': 'Las Vegas Grand Prix', 'months': [11], 'neighborhood': 'the-strip',
         'summary': 'Formula 1 night race on a street circuit along the Strip, with weeks of road closures.',
         'source': S},
        {'id': 'nfr', 'name': 'National Finals Rodeo', 'months': [12], 'neighborhood': 'university-district',
         'summary': 'Ten nights of championship rodeo at the Thomas & Mack Center, with cowboy events across town.',
         'source': S},
        {'id': 'new-years-eve', 'name': 'New Year\'s Eve on the Strip', 'months': [12], 'neighborhood': 'the-strip',
         'summary': 'The Strip closes to cars for crowds and rooftop fireworks at midnight.', 'source': S},
    ],
    'local_color': [
        color('locals-avoid-the-strip', 'Locals avoid the Strip', 'custom', 'Residents mostly stay off Las Vegas '
              'Boulevard except to take visitors out, see a show or go to work, and plan routes around its traffic.'),
        color('locals-casinos', 'Locals casinos', 'custom', 'Neighborhood casinos off the Strip draw residents with '
              'cheaper food, bowling, movie theaters and player\'s club deals, and are where many people actually '
              'gamble.',
              ['santa-fe-station', 'green-valley-ranch', 'aliante-casino', 'm-resort', 'orleans-bowling',
               'south-point-bowling']),
        color('grocery-store-slots', 'Slots everywhere', 'custom', 'Slot and video poker machines stand in grocery '
              'stores, gas stations and the airport, and locals stop noticing them within a week.'),
        color('locals-discounts', 'Locals discounts', 'custom', 'Many shows, restaurants and attractions give a '
              'discount to anyone with a Nevada ID, so "Are you a local?" is a common question at the counter.'),
        color('nevada-pronunciation', 'Saying "Nevada"', 'saying', 'Locals say it with the middle sound of "bad" '
              '(ne-VAD-a), and notice at once when someone says ne-VAH-da.'),
        color('dry-heat', '"But it\'s a dry heat"', 'saying', 'The standard half-joking reply about summer days over '
              '40 degrees Celsius; low humidity does help, until it does not.', seasons=['summer']),
        color('summer-heat-habits', 'Summer heat habits', 'custom', 'In summer people hunt for shaded parking, use '
              'windshield shades, keep a towel for the steering wheel and do outdoor exercise before sunrise.',
              seasons=['summer']),
        color('twenty-four-hour-town', 'A 24-hour town', 'custom', 'Bars, casinos, gyms and some grocery stores never '
              'close, and so many people work swing and graveyard shifts that dinner at 3 a.m. is normal.'),
        color('glitter-gulch', 'Glitter Gulch', 'saying', 'The old nickname for the neon-lit casino blocks of Fremont '
              'Street downtown, the Las Vegas of before the megaresorts.', ['fremont-street-experience']),
        color('shrimp-cocktail', 'Downtown shrimp cocktail', 'dish', 'The cheap shrimp cocktail in a tall glass, sold '
              'for decades by downtown casinos as a lure, is a piece of old Vegas many locals still order.',
              ['fremont-street-experience']),
        color('buffets', 'Buffets', 'dish', 'All-you-can-eat buffets are a Las Vegas institution, from lavish Strip '
              'spreads to cheaper ones in locals casinos.', ['bacchanal-buffet', 'studio-b-buffet']),
        color('steak-special', 'Ellis Island steak special', 'dish', 'Ellis Island\'s cheap steak dinner special, a '
              'few blocks off the Strip, has long been one of the best-known locals bargains in town.',
              ['ellis-island']),
        color('adobada-tacos', 'Adobada tacos', 'dish', 'Tijuana-style tacos of marinated pork carved from a spit, '
              'eaten standing up at busy taco shops late at night.', ['tacos-el-gordo']),
        color('spring-mountain-road', 'Chinatown on Spring Mountain', 'dish', 'Spring Mountain Road west of the Strip '
              'is a long strip of Asian restaurants where chefs and casino workers go after their shifts.',
              ['chinatown', 'chinatown-plaza', 'raku', 'pho-kim-long', 'ping-pang-pong']),
        color('vegas-golden-knights', 'Vegas Golden Knights', 'team', 'The NHL team that reached the Stanley Cup final '
              'in its first season (2018) and won the Cup in 2023, playing at T-Mobile Arena.',
              ['t-mobile-arena'], ['fall', 'winter', 'spring']),
        color('las-vegas-raiders', 'Las Vegas Raiders', 'team', 'The NFL team moved from Oakland in 2020 and plays at '
              'Allegiant Stadium, with many visiting fans on game days.', ['allegiant-stadium'], ['fall', 'winter']),
        color('las-vegas-aces', 'Las Vegas Aces', 'team', 'The WNBA team, champions in 2022 and 2023, playing at '
              'Michelob Ultra Arena at Mandalay Bay.', seasons=['spring', 'summer', 'fall']),
        color('las-vegas-aviators', 'Las Vegas Aviators', 'team', 'The Triple-A minor league baseball team plays in '
              'Summerlin at Las Vegas Ballpark.', ['las-vegas-ballpark'], ['spring', 'summer']),
        color('unlv-rebels', 'UNLV Runnin\' Rebels', 'team', 'UNLV basketball, national champions in 1990, plays at '
              'the Thomas & Mack Center, and the city still remembers the Tarkanian years.',
              ['thomas-and-mack'], ['fall', 'winter']),
    ],
    'prices': [
        price('coffee', 'Coffee', 2.5, 4.5, 'a cup'),
        price('latte', 'Latte', 5, 7.5, 'more on the Strip'),
        price('breakfast-sandwich', 'Breakfast sandwich', 6, 10),
        price('cheap-lunch', 'Cheap lunch', 11, 18, 'off-Strip'),
        price('dinner', 'Mid-range dinner', 35, 70, 'for one, off-Strip to Strip'),
        price('beer', 'Pint of beer', 7, 12, 'off-Strip to Strip'),
        price('cocktail', 'Cocktail', 14, 25),
        price('groceries', 'Groceries', 75, 110, 'a week, one person'),
        price('bus', 'RTC bus fare', 2, 6, 'one ride; Strip routes cost more'),
        price('monorail', 'Monorail ride', 5.5, 5.5, 'one way'),
        price('rideshare', 'Rideshare across town', 15, 35),
        price('buffet', 'Casino buffet', 30, 80, 'dinner'),
        price('show', 'Show ticket', 60, 200, 'a Strip production show'),
        price('gym', 'Gym membership', 25, 60, 'a month'),
    ],
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
