"""Curated Baltimore data. Run `python scripts/world/baltimore.py` to rewrite the shipped JSON."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'cities' / 'baltimore.json'
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


ALL = ['solo', 'friends', 'date', 'family']
ADULT = ['solo', 'friends', 'date']
DAY = ['morning', 'afternoon']
DINNER = ['evening']
NIGHT = ['evening', 'late']
WARM = ['spring', 'summer', 'fall']

CITY = {
    'schema_version': 1, 'id': 'baltimore', 'name': 'Baltimore', 'region': 'Maryland', 'country': 'US',
    'timezone': 'America/New_York', 'aliases': ['Charm City', 'Bmore', 'Baltimore, MD'],
    'summary': 'A port city of rowhouse neighborhoods on the Chesapeake Bay, known for its harbor, '
               'Johns Hopkins, steamed crabs and a strong local arts scene.',
    'lat': 39.29, 'lon': -76.61,
    'speeds': {'walk': 4.5, 'car': 25, 'rideshare': 25, 'bus': 13, 'light-rail': 20, 'subway': 28,
               'commuter-rail': 45, 'water-taxi': 10},
    # Rough heritage weights for residents' names (estimates, not census figures).
    'names': {'mix': {'black-american': 6, 'anglo': 3, 'hispanic': 0.8, 'irish': 0.5, 'italian': 0.4, 'jewish': 0.5,
                       'slavic': 0.4, 'east-asian': 0.4, 'south-asian': 0.3, 'west-african': 0.4, 'caribbean': 0.2}},
    'sources': {
        S: {'kind': 'curated', 'title': 'Baltimore places and neighborhoods written for Prospero Companion',
            'license': 'CC0-1.0', 'retrieved': '2026-10-05',
            'note': 'Well-known public places, institutions and employers from general knowledge. Businesses open '
                    'and close and rents move: treat this as a snapshot for fiction. Rents are rounded estimates '
                    'of typical asking ranges, not listings. Coordinates are approximate neighborhood centers.'},
        CLIMATE: {'kind': 'curated', 'title': 'Approximate monthly climate for Baltimore (BWI area)',
                  'license': 'CC0-1.0', 'retrieved': '2026-10-05',
                  'note': 'Rounded values in line with NOAA 1991-2020 normals; refresh with scripts/world when '
                          'network access to NOAA is available.'},
    },
    'neighborhoods': [
        hood('inner-harbor', 'Inner Harbor', 'The tourist waterfront: promenade, aquarium, science center and '
             'harbor views, busy on summer weekends.', ['waterfront', 'touristy', 'central'], 39.286, -76.610,
             'high', ([1400, 1800], [1600, 2300], [2200, 3200]), ['apartment-tower', 'condo'], 'high',
             ['light-rail', 'water-taxi', 'circulator', 'citylink']),
        hood('downtown', 'Downtown', 'Office towers, the stadiums, Lexington Market and the theater district.',
             ['business', 'sports', 'central'], 39.290, -76.616, 'mid', ([1200, 1600], [1400, 2000],
             [1900, 2700]), ['apartment-tower', 'converted-office'], 'high',
             ['light-rail', 'subway', 'circulator', 'citylink', 'marc']),
        hood('fells-point', 'Fells Point', 'Cobblestone streets, eighteenth-century rowhouses, pubs and live music '
             'on the waterfront.', ['historic', 'nightlife', 'waterfront', 'cobblestones'], 39.283, -76.593,
             'high', ([1300, 1700], [1500, 2100], [2000, 2900]), ['rowhouse', 'loft', 'condo'], 'high',
             ['water-taxi', 'circulator', 'citylink']),
        hood('harbor-east', 'Harbor East', 'Polished new towers, hotels, offices and upscale restaurants between '
             'downtown and Fells Point.', ['upscale', 'new-build', 'waterfront'], 39.283, -76.600, 'very-high',
             ([1600, 2100], [1900, 2700], [2600, 3800]), ['apartment-tower', 'condo'], 'high',
             ['water-taxi', 'circulator', 'citylink']),
        hood('little-italy', 'Little Italy', 'A few compact blocks of Italian restaurants, bakeries and bocce, '
             'with an outdoor film festival in summer.', ['historic', 'food', 'quiet'], 39.285, -76.602, 'high',
             ([1300, 1700], [1500, 2000], [1900, 2700]), ['rowhouse'], 'high', ['circulator', 'citylink']),
        hood('canton', 'Canton', 'Former cannery rowhouses turned young-professional hub around O\'Donnell Square, '
             'with a waterfront park and the marine terminals beyond.', ['young-professional', 'bars', 'waterfront'],
             39.280, -76.575, 'high', ([1200, 1600], [1400, 1900], [1900, 2700]), ['rowhouse', 'condo'], 'medium',
             ['water-taxi', 'citylink']),
        hood('highlandtown', 'Highlandtown', 'Working-class rowhouses beside Patterson Park, with Latin American '
             'groceries and an arts district.', ['diverse', 'arts', 'affordable', 'park'], 39.288, -76.570, 'mid',
             ([950, 1250], [1100, 1500], [1400, 1900]), ['rowhouse'], 'medium', ['citylink']),
        hood('federal-hill', 'Federal Hill', 'Hilltop park views over the harbor, a lively bar strip and Cross Street '
             'Market.', ['young-professional', 'bars', 'views'], 39.278, -76.611, 'high',
             ([1250, 1650], [1450, 2000], [1900, 2800]), ['rowhouse', 'condo'], 'high',
             ['water-taxi', 'circulator', 'citylink']),
        hood('locust-point', 'Locust Point', 'A quiet peninsula of rowhouses on the way to Fort McHenry, beside the '
             'Domino Sugars plant and its neon sign.', ['quiet', 'historic', 'waterfront', 'family'], 39.271,
             -76.590, 'high', ([1200, 1550], [1400, 1900], [1900, 2600]), ['rowhouse', 'townhouse'], 'medium',
             ['water-taxi', 'citylink']),
        hood('baltimore-peninsula', 'Baltimore Peninsula', 'A new mixed-use waterfront district in Port Covington, '
             'home to Under Armour\'s headquarters.', ['new-build', 'waterfront', 'corporate'], 39.265, -76.613,
             'very-high', ([1600, 2100], [1900, 2600], [2600, 3600]), ['apartment-tower'], 'medium', ['citylink']),
        hood('mount-vernon', 'Mount Vernon', 'Grand nineteenth-century townhouses around the original Washington '
             'Monument, with museums, the Peabody and a strong LGBTQ+ community.',
             ['historic', 'cultural', 'lgbtq-friendly', 'architecture'], 39.298, -76.615, 'mid',
             ([1000, 1400], [1200, 1700], [1600, 2300]), ['brownstone', 'apartment', 'converted-mansion'], 'high',
             ['light-rail', 'subway', 'circulator', 'citylink']),
        hood('bolton-hill', 'Bolton Hill', 'Leafy brick townhouse blocks next to the MICA campus.',
             ['historic', 'quiet', 'arts'], 39.305, -76.625, 'mid', ([1000, 1350], [1200, 1650], [1600, 2200]),
             ['brownstone', 'apartment'], 'medium', ['light-rail', 'subway', 'citylink']),
        hood('station-north', 'Station North', 'The arts and entertainment district around Penn Station: murals, '
             'studios, an indie cinema and late-night bars.', ['arts', 'nightlife', 'gritty', 'affordable'],
             39.310, -76.615, 'low', ([850, 1150], [1000, 1400], [1300, 1800]), ['apartment', 'loft', 'rowhouse'],
             'high', ['light-rail', 'marc', 'citylink', 'circulator']),
        hood('remington', 'Remington', 'Small rowhouse blocks between Hampden and Charles Village with a food hall '
             'and music venues.', ['up-and-coming', 'food', 'music'], 39.318, -76.623, 'mid',
             ([950, 1300], [1150, 1550], [1450, 2000]), ['rowhouse', 'apartment'], 'medium', ['citylink']),
        hood('charles-village', 'Charles Village', 'Painted Ladies rowhouses around the Johns Hopkins Homewood campus '
             'and the Baltimore Museum of Art.', ['students', 'academic', 'colorful'], 39.322, -76.619, 'mid',
             ([950, 1300], [1100, 1550], [1450, 2100]), ['rowhouse', 'apartment', 'student-housing'], 'medium',
             ['citylink', 'circulator']),
        hood('hampden', 'Hampden', 'Former mill village turned quirky shopping strip on 36th Street ("The Avenue"), '
             'with thrift shops, cafes and a famous Christmas light block.', ['quirky', 'shopping', 'food', 'artsy'],
             39.330, -76.633, 'mid', ([1000, 1350], [1200, 1650], [1550, 2200]), ['rowhouse', 'mill-loft'],
             'medium', ['citylink']),
        hood('reservoir-hill', 'Reservoir Hill', 'Large Victorian homes on the edge of Druid Hill Park and the '
             'Maryland Zoo.', ['historic', 'park', 'affordable'], 39.316, -76.635, 'low',
             ([850, 1150], [1000, 1350], [1300, 1800]), ['victorian', 'apartment'], 'medium', ['citylink']),
        hood('roland-park', 'Roland Park', 'One of the first planned suburbs in the country: winding streets, '
             'large houses, private schools and old trees.', ['affluent', 'leafy', 'family', 'quiet'], 39.351,
             -76.633, 'very-high', ([1200, 1500], [1400, 1900], [2000, 2900]), ['single-family', 'apartment'],
             'low', ['citylink']),
        hood('lauraville', 'Lauraville', 'Northeast Baltimore single-family homes with porches near Morgan State '
             'and the Harford Road restaurant strip.', ['family', 'quiet', 'neighbourly'], 39.346, -76.565, 'mid',
             ([900, 1200], [1050, 1450], [1400, 1950]), ['single-family', 'rowhouse'], 'low', ['citylink']),
        hood('towson', 'Towson', 'The Baltimore County seat just north of the city: Towson University, a large '
             'mall, hospitals and a busy suburban downtown.', ['suburban', 'college-town', 'shopping'], 39.401,
             -76.602, 'mid', ([1150, 1450], [1350, 1800], [1700, 2400]), ['apartment', 'townhouse',
             'single-family'], 'medium', ['citylink']),
    ],
    'transit': [
        {'id': 'light-rail', 'name': 'Light RailLink', 'kind': 'light-rail', 'summary': 'North-south light rail '
         'from Hunt Valley through downtown and past the stadiums to BWI Airport.', 'source': S},
        {'id': 'subway', 'name': 'Metro SubwayLink', 'kind': 'subway', 'summary': 'A single line from Owings Mills '
         'through downtown to Johns Hopkins Hospital.', 'source': S},
        {'id': 'citylink', 'name': 'CityLink and LocalLink buses', 'kind': 'bus', 'summary': 'The MTA bus '
         'network, the main way around for people without cars.', 'source': S},
        {'id': 'circulator', 'name': 'Charm City Circulator', 'kind': 'bus', 'summary': 'Free downtown buses '
         'linking the harbor, Fells Point, Federal Hill, Mount Vernon and Penn Station.', 'source': S},
        {'id': 'water-taxi', 'name': 'Baltimore Water Taxi', 'kind': 'water-taxi', 'summary': 'Harbor boats '
         'between the Inner Harbor, Fells Point, Canton, Harbor East, Locust Point and Fort McHenry.', 'source': S},
        {'id': 'marc', 'name': 'MARC Penn Line', 'kind': 'commuter-rail', 'summary': 'Commuter trains from Penn '
         'Station to Washington, D.C., used by many federal workers.', 'source': S},
    ],
    'places': [
        place('national-aquarium', 'National Aquarium', 'attraction', 'inner-harbor', 'Big aquarium on the pier '
              'with a rooftop rainforest, a coral reef tank and a shark ring.', ['animals', 'rainy-day',
              'iconic'], '$$$', 'indoor', ALL, DAY),
        place('inner-harbor-promenade', 'Inner Harbor promenade', 'landmark', 'inner-harbor', 'Brick waterfront '
              'walk past historic ships, paddle boats and street performers.', ['waterfront', 'walk', 'iconic'],
              'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening'], WARM),
        place('maryland-science-center', 'Maryland Science Center', 'museum', 'inner-harbor', 'Hands-on science '
              'museum with a planetarium and IMAX.', ['science', 'rainy-day', 'kids'], '$$', 'indoor',
              ['family', 'friends', 'date'], DAY),
        place('uss-constellation', 'USS Constellation', 'landmark', 'inner-harbor', 'A Civil War-era sloop of war '
              'you can board in the harbor.', ['history', 'ships'], '$$', 'mixed', ALL, DAY),
        place('harbor-paddle-boats', 'Inner Harbor paddle boats', 'attraction', 'inner-harbor',
              'Dragon-shaped pedal boats for a slow loop of the harbor.', ['water', 'silly'], '$$', 'outdoor',
              ['friends', 'date', 'family'], ['afternoon'], ['spring', 'summer']),
        place('camden-yards', 'Oriole Park at Camden Yards', 'stadium', 'downtown', 'The Orioles\' retro ballpark '
              'beside the old B&O warehouse.', ['baseball', 'sports', 'iconic'], '$$', 'outdoor', ALL,
              ['afternoon', 'evening'], ['spring', 'summer', 'fall']),
        place('ravens-stadium', 'M&T Bank Stadium', 'stadium', 'downtown', 'Home of the Ravens; tailgates fill the '
              'lots on game days.', ['football', 'sports', 'tailgate'], '$$$', 'outdoor', ['friends', 'family'],
              ['afternoon', 'evening'], ['fall', 'winter']),
        place('lexington-market', 'Lexington Market', 'market', 'downtown', 'One of the oldest public markets in '
              'the country, rebuilt with food stalls including Faidley\'s crab cakes.', ['food', 'crab-cakes',
              'historic'], '$', 'indoor', ALL, ['morning', 'afternoon']),
        place('hippodrome', 'Hippodrome Theatre', 'venue', 'downtown', 'Restored 1914 theater hosting touring '
              'Broadway shows.', ['theater', 'broadway'], '$$$', 'indoor', ['date', 'friends', 'family'],
              ['evening']),
        place('bromo-seltzer-tower', 'Bromo Seltzer Arts Tower', 'landmark', 'downtown', 'Clock tower with artist '
              'studios and occasional open-studio days.', ['architecture', 'art'], 'free', 'indoor', ADULT,
              ['afternoon']),
        place('power-plant-live', 'Power Plant Live!', 'nightlife', 'downtown', 'An entertainment block of clubs '
              'and bars with outdoor concerts in summer.', ['clubs', 'party'], '$$', 'mixed', ['friends'], NIGHT),
        place('jfx-farmers-market', 'Baltimore Farmers\' Market & Bazaar', 'market', 'downtown', 'Sunday morning '
              'market under the Jones Falls Expressway.', ['farmers-market', 'sunday', 'food'], '$', 'outdoor', ALL,
              ['morning'], WARM),
        place('attmans-deli', 'Attman\'s Delicatessen', 'restaurant', 'downtown', 'Century-old deli on Lombard '
              'Street\'s "Corned Beef Row".', ['deli', 'historic'], '$', 'indoor', ALL, ['morning', 'afternoon'],
              cuisine='jewish-deli'),
        place('fells-point-waterfront', 'Thames Street waterfront', 'landmark', 'fells-point', 'Cobblestones, tug '
              'boats and the old Recreation Pier on the harbor edge.', ['waterfront', 'walk', 'historic'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('broadway-market', 'Broadway Market', 'market', 'fells-point', 'Historic market hall with lunch '
              'counters and seafood.', ['food', 'historic'], '$', 'indoor', ALL, ['morning', 'afternoon']),
        place('thames-street-oyster-house', 'Thames Street Oyster House', 'restaurant', 'fells-point', 'Busy '
              'seafood house known for its oyster bar and lobster rolls.', ['seafood', 'oysters'], '$$$', 'indoor',
              ['date', 'friends'], DINNER, cuisine='seafood'),
        place('blue-moon-cafe', 'Blue Moon Cafe', 'restaurant', 'fells-point', 'Tiny breakfast spot with a weekend '
              'line out the door for Cap\'n Crunch French toast.', ['brunch', 'line'], '$$', 'indoor', ALL,
              ['morning'], cuisine='american-breakfast'),
        place('berthas', 'Bertha\'s Mussels', 'bar', 'fells-point', 'Old pub with "Eat Bertha\'s Mussels" '
              'bumper-sticker fame and live music.', ['pub', 'mussels', 'live-music'], '$$', 'indoor', ADULT,
              NIGHT, cuisine='seafood'),
        place('the-horse-you-came-in-on', 'The Horse You Came In On Saloon', 'bar', 'fells-point', 'Claims to be '
              'one of the oldest continually operating saloons in the country.', ['bar', 'historic', 'live-music'],
              '$', 'indoor', ['friends', 'solo'], NIGHT),
        place('vaccaros', 'Vaccaro\'s Italian Pastry Shop', 'cafe', 'little-italy', 'Cannoli and gelato institution.',
              ['dessert', 'cannoli'], '$', 'indoor', ALL, ['afternoon', 'evening'], cuisine='italian-pastry'),
        place('sabatinos', 'Sabatino\'s', 'restaurant', 'little-italy', 'Old-school red-sauce Italian open late, '
              'famous for its "Bookmaker" salad.', ['italian', 'old-school'], '$$', 'indoor', ['family', 'date',
              'friends'], NIGHT, cuisine='italian'),
        place('canton-waterfront-park', 'Canton Waterfront Park', 'park', 'canton', 'Small harbor-side park with '
              'a water taxi landing and views of the Domino Sugars sign.', ['waterfront', 'walk'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening'], WARM),
        place('odonnell-square', 'O\'Donnell Square', 'nightlife', 'canton', 'A square ringed by bars and '
              'restaurants, crowded on weekend nights.', ['bars', 'patios'], '$$', 'mixed', ['friends', 'date'],
              NIGHT),
        place('captain-james', 'Captain James Crab House', 'restaurant', 'canton', 'Steamed crabs on butcher paper '
              'beside a building shaped like a ship.', ['crabs', 'waterfront'], '$$', 'mixed', ALL, DINNER,
              ['summer', 'fall'], cuisine='seafood'),
        place('patterson-park', 'Patterson Park', 'park', 'highlandtown', 'A big city park with a pagoda, a boat '
              'lake, an ice rink and weekend soccer.', ['park', 'pagoda', 'dogs', 'running'], 'free', 'outdoor',
              ALL, ['morning', 'afternoon']),
        place('federal-hill-park', 'Federal Hill Park', 'park', 'federal-hill', 'A steep hilltop with the best '
              'free view of the harbor skyline.', ['views', 'sunset'], 'free', 'outdoor', ALL,
              ['morning', 'afternoon', 'evening']),
        place('cross-street-market', 'Cross Street Market', 'market', 'federal-hill', 'Renovated market hall with '
              'food stalls and a lively after-work crowd.', ['food-hall', 'happy-hour'], '$$', 'indoor',
              ['friends', 'date', 'solo'], ['afternoon', 'evening']),
        place('avam', 'American Visionary Art Museum', 'museum', 'federal-hill', 'Museum of self-taught "outsider" '
              'art, with a mirrored mosaic facade.', ['art', 'quirky', 'rainy-day'], '$$', 'indoor', ALL,
              ['afternoon']),
        place('fort-mchenry', 'Fort McHenry', 'landmark', 'locust-point', 'Star-shaped fort whose 1814 defence '
              'inspired "The Star-Spangled Banner", with a shoreline walking path.', ['history', 'national-park',
              'walk'], '$', 'outdoor', ALL, DAY),
        place('lp-steamers', 'L.P. Steamers', 'restaurant', 'locust-point', 'Neighborhood crab house with a '
              'rooftop deck.', ['crabs', 'rooftop'], '$$', 'mixed', ['friends', 'family'], DINNER,
              ['summer', 'fall'], cuisine='seafood'),
        place('walters-art-museum', 'Walters Art Museum', 'museum', 'mount-vernon', 'Free museum with armour, '
              'manuscripts and art spanning five thousand years.', ['art', 'free', 'rainy-day'], 'free', 'indoor',
              ALL, DAY),
        place('washington-monument', 'Mount Vernon Place and the Washington Monument', 'landmark', 'mount-vernon',
              'The first monument to George Washington, set in four landscaped squares; climbable for a small fee.',
              ['views', 'architecture', 'walk'], 'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('pratt-library', 'Enoch Pratt Free Library Central Library', 'library', 'mount-vernon', 'The grand '
              'central library on Cathedral Street.', ['books', 'quiet', 'free'], 'free', 'indoor', ['solo',
              'family'], DAY),
        place('meyerhoff', 'Joseph Meyerhoff Symphony Hall', 'venue', 'mount-vernon', 'Home of the Baltimore '
              'Symphony Orchestra.', ['classical', 'concerts'], '$$$', 'indoor', ['date', 'solo', 'family'],
              ['evening']),
        place('mount-vernon-marketplace', 'Mount Vernon Marketplace', 'restaurant', 'mount-vernon', 'Casual food '
              'hall with ramen, tacos, oysters and a bar.', ['food-hall', 'casual'], '$$', 'indoor', ADULT,
              ['afternoon', 'evening']),
        place('charles-theatre', 'The Charles Theatre', 'venue', 'station-north', 'Independent cinema showing art '
              'films and revival screenings.', ['movies', 'indie', 'rainy-day'], '$$', 'indoor', ['solo', 'date',
              'friends'], ['afternoon', 'evening']),
        place('ottobar', 'Ottobar', 'venue', 'remington', 'Long-running punk and indie rock club.', ['live-music',
              'rock'], '$$', 'indoor', ['friends', 'solo'], NIGHT),
        place('r-house', 'R. House', 'restaurant', 'remington', 'Food hall in a former auto body shop with a big '
              'patio.', ['food-hall', 'patio'], '$$', 'mixed', ALL, ['afternoon', 'evening']),
        place('bma', 'Baltimore Museum of Art', 'museum', 'charles-village', 'Free art museum with a major Matisse '
              'collection and a sculpture garden.', ['art', 'free', 'sculpture-garden'], 'free', 'mixed', ALL, DAY),
        place('the-avenue', 'The Avenue on 36th Street', 'shopping', 'hampden', 'Thrift shops, boutiques, cafes '
              'and kitsch along Hampden\'s main street.', ['thrift', 'boutiques', 'walk'], '$', 'outdoor', ALL,
              ['morning', 'afternoon']),
        place('the-charmery', 'The Charmery', 'cafe', 'hampden', 'Small-batch ice cream shop with local flavours '
              'like Old Bay caramel.', ['ice-cream', 'dessert'], '$', 'indoor', ALL, ['afternoon', 'evening']),
        place('ekiben', 'Ekiben', 'restaurant', 'hampden', 'Local favorite for steamed-bun sandwiches and tempura '
              'broccoli.', ['buns', 'casual'], '$', 'indoor', ADULT, ['afternoon', 'evening'], cuisine='asian-fusion'),
        place('jones-falls-trail', 'Jones Falls Trail', 'trail', 'hampden', 'Paved trail along the stream from the '
              'mills to Druid Hill Park and downtown.', ['running', 'cycling', 'walk'], 'free', 'outdoor', ALL,
              DAY, WARM),
        place('druid-hill-park', 'Druid Hill Park', 'park', 'reservoir-hill', 'Huge park with a reservoir loop, a '
              'Victorian conservatory and the Maryland Zoo.', ['park', 'running', 'conservatory'], 'free',
              'outdoor', ALL, DAY),
        place('maryland-zoo', 'The Maryland Zoo', 'attraction', 'reservoir-hill', 'Zoo in Druid Hill Park known '
              'for its African penguin colony.', ['animals', 'penguins', 'kids'], '$$', 'outdoor', ['family',
              'date'], DAY, WARM),
        place('kocos-pub', 'Koco\'s Pub', 'restaurant', 'lauraville', 'Neighborhood pub famous for huge crab '
              'cakes.', ['crab-cakes', 'pub'], '$$', 'indoor', ALL, DINNER, cuisine='seafood'),
        place('towson-town-center', 'Towson Town Center', 'shopping', 'towson', 'The region\'s big indoor mall.',
              ['mall', 'rainy-day'], '$$', 'indoor', ALL, ['afternoon', 'evening']),
        # Everyday neighborhood spots: cafes, diners, pubs, libraries, parks and markets.
        place('rash-field', 'Rash Field Park', 'park', 'inner-harbor', 'Rebuilt waterfront park below Federal Hill '
              'with a skate park, beach volleyball courts and lawn chairs facing the harbor.',
              ['waterfront', 'skate', 'volleyball'], 'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening'],
              WARM),
        place('pratt-street-ale-house', 'Pratt Street Ale House', 'restaurant', 'inner-harbor', 'Long-running '
              'brewpub near the Convention Center pouring Oliver ales with pub food before Orioles games.',
              ['brewpub', 'beer', 'game-day'], '$$', 'indoor', ['friends', 'solo', 'coworkers'],
              ['afternoon', 'evening'], cuisine='american-pub'),
        place('charleston', 'Charleston', 'restaurant', 'harbor-east', 'Cindy Wolf\'s acclaimed tasting-menu '
              'restaurant, one of the city\'s special-occasion dinners.', ['fine-dining', 'special-occasion', 'wine'],
              '$$$$', 'indoor', ['date'], DINNER, cuisine='southern-french'),
        place('cinghiale', 'Cinghiale', 'restaurant', 'harbor-east', 'Italian osteria and enoteca with house-made '
              'pasta and a long wine list.', ['italian', 'wine', 'pasta'], '$$$', 'indoor', ['date', 'friends'],
              DINNER, cuisine='italian'),
        place('ouzo-bay', 'Ouzo Bay', 'restaurant', 'harbor-east', 'Glossy Greek seafood restaurant with whole fish '
              'and a see-and-be-seen bar.', ['seafood', 'greek', 'upscale'], '$$$', 'indoor', ['date', 'friends'],
              NIGHT, cuisine='greek'),
        place('bagby-pizza-harbor-east', 'Bagby Pizza', 'restaurant', 'harbor-east', 'Casual brick-oven pizza shop '
              'that feeds the neighborhood\'s office workers and families.', ['pizza', 'casual', 'lunch'], '$',
              'indoor', ALL, ['afternoon', 'evening'], cuisine='pizza'),
        place('whole-foods-harbor-east', 'Whole Foods Market Harbor East', 'market', 'harbor-east', 'The '
              'neighborhood\'s big grocery store, with a hot bar and seating for a quick lunch.',
              ['grocery', 'lunch'], '$$', 'indoor', ALL, ['morning', 'afternoon', 'evening']),
        place('harbor-east-promenade', 'Harbor East waterfront promenade', 'landmark', 'harbor-east', 'Brick '
              'harbor walk linking the Inner Harbor to Fells Point past marinas and hotel terraces.',
              ['waterfront', 'walk', 'running'], 'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('chiapparellis', 'Chiapparelli\'s', 'restaurant', 'little-italy', 'Family-run red-sauce restaurant '
              'since 1940, known for its house salad and big platters.', ['italian', 'old-school', 'family'], '$$',
              'indoor', ['family', 'date', 'friends'], DINNER, cuisine='italian'),
        place('amiccis', 'Amicci\'s', 'restaurant', 'little-italy', 'Casual Italian spot famous for its pane '
              'rotondo, a hollowed-out loaf filled with shrimp.', ['italian', 'casual'], '$$', 'indoor', ALL,
              ['afternoon', 'evening'], cuisine='italian'),
        place('little-italy-bocce', 'Little Italy bocce courts', 'park', 'little-italy', 'Neighborhood bocce '
              'courts where league games run on warm evenings and spectators bring folding chairs.',
              ['bocce', 'local', 'games'], 'free', 'outdoor', ADULT, ['afternoon', 'evening'], WARM),
        place('canton-library', 'Enoch Pratt Canton Branch', 'library', 'canton', 'Small historic branch library a '
              'block from the waterfront, with story times and study tables.', ['books', 'quiet', 'kids'], 'free',
              'indoor', ALL, DAY),
        place('nacho-mamas', 'Nacho Mama\'s', 'restaurant', 'canton', 'Elvis-and-Natty-Boh-themed Tex-Mex bar on '
              'O\'Donnell Square, serving margaritas in hubcaps.', ['tex-mex', 'kitschy', 'margaritas'], '$$',
              'indoor', ['friends', 'family', 'date'], ['afternoon', 'evening'], cuisine='tex-mex'),
        place('claddagh-pub', 'The Claddagh Pub', 'bar', 'canton', 'Irish pub on O\'Donnell Street with a big '
              'menu, sports on the TVs and a busy St. Patrick\'s Day.', ['pub', 'irish', 'sports'], '$$', 'indoor',
              ADULT, NIGHT, cuisine='irish-pub'),
        place('can-company', 'The Can Company', 'shopping', 'canton', 'A former American Can Company factory turned '
              'into shops, restaurants and offices on Boston Street.', ['errands', 'historic', 'industrial'], '$$',
              'indoor', ALL, ['morning', 'afternoon', 'evening']),
        place('matthews-pizza', 'Matthew\'s Pizza', 'restaurant', 'highlandtown', 'Baltimore\'s oldest pizzeria, '
              'serving thick, crispy-edged pies on Eastern Avenue since 1943.', ['pizza', 'historic', 'local'], '$',
              'indoor', ALL, ['afternoon', 'evening'], cuisine='pizza'),
        place('creative-alliance', 'Creative Alliance', 'venue', 'highlandtown', 'Arts center in the old Patterson '
              'movie theater with concerts, film nights, galleries and classes.', ['arts', 'live-music', 'film'],
              '$', 'indoor', ['friends', 'date', 'solo'], ['evening']),
        place('southeast-anchor-library', 'Enoch Pratt Southeast Anchor Library', 'library', 'highlandtown',
              'Large modern branch library on Eastern Avenue with computers, bilingual programs and a teen space.',
              ['books', 'study', 'kids'], 'free', 'indoor', ALL, DAY),
        place('dipasquales', 'Di Pasquale\'s Italian Marketplace', 'market', 'highlandtown', 'Old Italian grocery '
              'and deli making its own mozzarella, with sandwiches and lasagne to eat in.',
              ['grocery', 'deli', 'italian'], '$', 'indoor', ALL, DAY, cuisine='italian-deli'),
        place('patterson-park-ice-rink', 'Patterson Park ice rink', 'fitness', 'highlandtown', 'The Mimi DiPietro '
              'Family Skating Center, a city rink with public skates, hockey and lessons.', ['skating', 'winter',
              'kids'], '$', 'indoor', ALL, ['afternoon', 'evening'], ['fall', 'winter', 'spring']),
        place('patterson-park-pagoda', 'Patterson Park Pagoda', 'landmark', 'highlandtown', 'Victorian observation '
              'tower in the park, open on summer Sundays for views over the rooftops to the harbor.',
              ['views', 'historic'], 'free', 'outdoor', ALL, ['afternoon'], ['spring', 'summer']),
        place('light-street-library', 'Enoch Pratt Light Street Branch', 'library', 'federal-hill', 'Neighborhood '
              'branch library on Light Street for books, computers and kids\' programs.', ['books', 'quiet'], 'free',
              'indoor', ALL, DAY),
        place('mothers-federal-hill', 'Mother\'s Federal Hill Grille', 'bar', 'federal-hill', 'Big neighborhood '
              'sports bar known for Ravens game days and its Purple Patio.', ['sports', 'ravens', 'patio'], '$$',
              'mixed', ['friends'], ['afternoon', 'evening', 'late'], cuisine='american-pub'),
        place('ryleighs-oyster', 'Ryleigh\'s Oyster', 'restaurant', 'federal-hill', 'Oyster bar and seafood '
              'restaurant across from Cross Street Market.', ['oysters', 'seafood', 'happy-hour'], '$$', 'indoor',
              ADULT, ['afternoon', 'evening'], cuisine='seafood'),
        place('museum-of-industry', 'Baltimore Museum of Industry', 'museum', 'locust-point', 'Museum in an old '
              'oyster cannery on Key Highway covering the city\'s factories, printers and port.',
              ['history', 'industry', 'rainy-day'], '$', 'indoor', ALL, DAY),
        place('latrobe-park', 'Latrobe Park', 'park', 'locust-point', 'Neighborhood park with ball fields, a '
              'playground and dog walkers at the end of Fort Avenue.', ['playground', 'dogs', 'sports'], 'free',
              'outdoor', ['family', 'solo', 'friends'], ['morning', 'afternoon', 'evening']),
        place('riverside-park', 'Riverside Park', 'park', 'locust-point', 'Hilly South Baltimore park with a public '
              'pool, playing fields and Civil War-era history.', ['pool', 'playground', 'local'], 'free', 'outdoor',
              ['family', 'solo', 'friends'], ['morning', 'afternoon', 'evening']),
        place('sagamore-spirit', 'Sagamore Spirit Distillery', 'bar', 'baltimore-peninsula', 'Rye whiskey distillery '
              'on the Middle Branch with tours and a tasting-room bar.', ['whiskey', 'tours', 'waterfront'], '$$',
              'mixed', ['friends', 'date'], ['afternoon', 'evening']),
        place('nicks-fish-house', 'Nick\'s Fish House', 'restaurant', 'baltimore-peninsula', 'Casual seafood house '
              'and deck by the Hanover Street Bridge, with crabs and live music in summer.',
              ['crabs', 'deck', 'waterfront'], '$$', 'mixed', ['friends', 'family', 'date'], ['afternoon', 'evening'],
              cuisine='seafood'),
        place('swann-park', 'Swann Park', 'park', 'baltimore-peninsula', 'City ball fields and waterfront green by '
              'the Middle Branch, used for youth sports and pick-up games.', ['sports', 'fields', 'waterfront'],
              'free', 'outdoor', ['family', 'friends'], ['afternoon', 'evening'], WARM),
        place('middle-branch-park', 'Middle Branch Park', 'park', 'baltimore-peninsula', 'Shoreline park with a '
              'fishing pier, trails and the Baltimore Rowing Club boathouse across the water.',
              ['waterfront', 'fishing', 'rowing', 'trail'], 'free', 'outdoor', ALL, DAY),
        place('middle-branch-fitness', 'Middle Branch Fitness and Wellness Center', 'fitness', 'baltimore-peninsula',
              'City recreation center with a pool, gym and fitness classes beside the Middle Branch.',
              ['gym', 'pool', 'rec-center'], '$', 'indoor', ALL, ['morning', 'afternoon', 'evening']),
        place('mount-royal-tavern', 'Mount Royal Tavern', 'bar', 'bolton-hill', 'Cheap, friendly dive bar beloved '
              'by MICA students, with a copy of the Sistine Chapel ceiling painted overhead.',
              ['dive-bar', 'art-students', 'cheap'], '$', 'indoor', ['friends', 'solo'], NIGHT),
        place('lyric-baltimore', 'Lyric Baltimore', 'venue', 'bolton-hill', 'Historic concert hall on Mount Royal '
              'Avenue hosting touring comedians, concerts and the opera.', ['concerts', 'comedy', 'historic'], '$$',
              'indoor', ['date', 'friends'], ['evening']),
        place('mica-galleries', 'MICA galleries', 'museum', 'bolton-hill', 'Free student and faculty exhibitions '
              'in the Maryland Institute College of Art buildings, including the glass Brown Center.',
              ['art', 'free', 'students'], 'free', 'indoor', ['solo', 'friends', 'date'], DAY),
        place('eutaw-place', 'Eutaw Place medians', 'park', 'bolton-hill', 'Long landscaped medians with fountains '
              'and statues running down a grand boulevard of townhouses.', ['walk', 'architecture', 'dogs'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('brown-memorial-church', 'Brown Memorial Park Avenue Presbyterian Church', 'landmark', 'bolton-hill',
              'Stone church with Tiffany stained-glass windows and regular organ concerts.',
              ['architecture', 'tiffany', 'music'], 'free', 'indoor', ['solo', 'date', 'family'], ['afternoon']),
        place('club-charles', 'Club Charles', 'bar', 'station-north', 'Art deco dive bar across from the Charles '
              'Theatre, a late-night haunt for artists and film crowds.', ['dive-bar', 'late-night', 'art-deco'],
              '$', 'indoor', ['friends', 'solo', 'date'], NIGHT),
        place('tapas-teatro', 'Tapas Teatro', 'restaurant', 'station-north', 'Spanish small-plates restaurant next '
              'to the Charles, the classic dinner before a film.', ['tapas', 'sangria', 'pre-movie'], '$$', 'mixed',
              ['date', 'friends'], DINNER, cuisine='spanish'),
        place('penn-station', 'Baltimore Penn Station', 'landmark', 'station-north', 'Beaux-Arts train station for '
              'Amtrak and MARC, fronted by the big aluminium "Male/Female" sculpture.', ['trains', 'architecture'],
              'free', 'indoor', ['solo'], ['morning', 'afternoon', 'evening']),
        place('green-mount-cemetery', 'Green Mount Cemetery', 'park', 'station-north', 'Walled nineteenth-century '
              'garden cemetery with old trees, grand mausoleums and John Wilkes Booth\'s grave.',
              ['history', 'quiet', 'walk'], 'free', 'outdoor', ['solo', 'date'], DAY),
        place('paper-moon-diner', 'Paper Moon Diner', 'restaurant', 'remington', 'Diner covered inside and out in '
              'toys, mannequins and Pez dispensers, serving breakfast all day.', ['diner', 'quirky', 'brunch'], '$',
              'indoor', ALL, ['morning', 'afternoon', 'evening'], cuisine='american-diner'),
        place('clavel', 'Clavel', 'restaurant', 'remington', 'Mezcaleria and taqueria with handmade tortillas and a '
              'crowded bar.', ['tacos', 'mezcal'], '$$', 'indoor', ADULT, NIGHT, cuisine='mexican'),
        place('wyman-park', 'Wyman Park', 'park', 'remington', 'Wooded valley park between Remington and the Hopkins '
              'campus, with trails down to Stony Run.', ['woods', 'trail', 'dogs'], 'free', 'outdoor',
              ['solo', 'friends', 'family'], DAY),
        place('wyman-park-dell', 'Wyman Park Dell', 'park', 'charles-village', 'Grassy dell next to the Baltimore '
              'Museum of Art with a playground and the Charles Village Festival in spring.',
              ['playground', 'picnic', 'dogs'], 'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('waverly-farmers-market', '32nd Street Farmers Market', 'market', 'charles-village', 'Year-round '
              'Saturday market in Waverly with produce, coffee, breakfast stalls and neighbours catching up.',
              ['farmers-market', 'saturday', 'breakfast'], '$', 'outdoor', ALL, ['morning']),
        place('normals-books', 'Normal\'s Books & Records', 'shopping', 'charles-village', 'Crammed used book and '
              'record shop in Waverly with occasional experimental music shows.', ['books', 'records', 'used'], '$',
              'indoor', ['solo', 'friends'], ['afternoon']),
        place('red-emmas', 'Red Emma\'s', 'cafe', 'charles-village', 'Worker-owned cafe, vegan restaurant and '
              'radical bookstore in Waverly with talks in the evenings.', ['vegan', 'books', 'coffee', 'events'],
              '$', 'indoor', ['solo', 'friends'], ['morning', 'afternoon', 'evening'], cuisine='vegan'),
        place('homewood-campus', 'Johns Hopkins Homewood campus', 'landmark', 'charles-village', 'Red-brick '
              'quads, the Beach lawn and Homewood Museum on the university\'s main campus.',
              ['campus', 'architecture', 'walk'], 'free', 'outdoor', ALL, DAY),
        place('atomic-books', 'Atomic Books', 'shopping', 'hampden', 'Independent bookstore for comics, zines and '
              'odd literature, with a bar in the back room.', ['books', 'comics', 'zines'], '$', 'indoor',
              ['solo', 'friends'], ['afternoon', 'evening']),
        place('hampden-library', 'Enoch Pratt Hampden Branch', 'library', 'hampden', 'Neighborhood branch library '
              'on Falls Road, a quiet stop off The Avenue.', ['books', 'quiet', 'kids'], 'free', 'indoor', ALL, DAY),
        place('union-craft-brewing', 'Union Craft Brewing', 'bar', 'hampden', 'Brewery taproom in the Union '
              'Collective, with food trucks, trivia and a big patio.', ['brewery', 'beer', 'patio'], '$$', 'mixed',
              ['friends', 'date', 'solo'], ['afternoon', 'evening']),
        place('holy-frijoles', 'Holy Frijoles', 'restaurant', 'hampden', 'Small, loud Tex-Mex restaurant on The '
              'Avenue with big burritos.', ['tex-mex', 'casual'], '$', 'indoor', ['friends', 'family', 'solo'],
              ['afternoon', 'evening'], cuisine='tex-mex'),
        place('rawlings-conservatory', 'Rawlings Conservatory', 'garden', 'reservoir-hill', 'Victorian glass '
              'conservatory in Druid Hill Park with palms, orchids and desert houses; free to visit.',
              ['plants', 'rainy-day', 'quiet'], 'free', 'indoor', ALL, DAY),
        place('druid-hill-farmers-market', 'Druid Hill Park Farmers Market', 'market', 'reservoir-hill',
              'Wednesday afternoon market by the park\'s Superintendent\'s House with produce and prepared food.',
              ['farmers-market', 'produce'], '$', 'outdoor', ALL, ['afternoon'], WARM),
        place('druid-lake-loop', 'Druid Lake loop', 'trail', 'reservoir-hill', 'Paved loop around Druid Lake, the '
              'neighborhood\'s running and dog-walking track with skyline views.', ['running', 'walk', 'views'],
              'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('druid-hill-pool', 'Druid Hill Park pool', 'fitness', 'reservoir-hill', 'Big city outdoor pool in '
              'the park, cheap and packed on hot summer afternoons.', ['pool', 'swimming', 'kids'], '$', 'outdoor',
              ALL, ['afternoon'], ['summer']),
        place('miss-shirleys', 'Miss Shirley\'s Cafe', 'restaurant', 'roland-park', 'The original location of the '
              'local brunch chain, with crab cake Benedict and long weekend waits.', ['brunch', 'breakfast',
              'crab'], '$$', 'indoor', ALL, DAY, cuisine='american-breakfast'),
        place('petit-louis', 'Petit Louis Bistro', 'restaurant', 'roland-park', 'Classic French bistro in the '
              'Roland Park shopping strip.', ['french', 'bistro', 'wine'], '$$$', 'indoor', ['date', 'friends'],
              ['afternoon', 'evening'], cuisine='french'),
        place('eddies-of-roland-park', 'Eddie\'s of Roland Park', 'market', 'roland-park', 'Family-owned gourmet '
              'grocery on Roland Avenue since the 1940s, with a prepared-food counter.', ['grocery', 'deli',
              'local'], '$$', 'indoor', ALL, ['morning', 'afternoon', 'evening']),
        place('roland-park-library', 'Enoch Pratt Roland Park Branch', 'library', 'roland-park', 'Busy '
              'neighborhood library on Roland Avenue with a strong children\'s section.', ['books', 'kids', 'quiet'],
              'free', 'indoor', ALL, DAY),
        place('stony-run-trail', 'Stony Run Trail', 'trail', 'roland-park', 'Wooded footpath along a stream from '
              'Wyman Park up through Roland Park, popular with dog walkers.', ['woods', 'walk', 'dogs'], 'free',
              'outdoor', ['solo', 'friends', 'family'], DAY),
        place('sherwood-gardens', 'Sherwood Gardens', 'garden', 'roland-park', 'Guilford neighborhood garden famous '
              'for its tens of thousands of spring tulips.', ['flowers', 'picnic', 'tulips'], 'free', 'outdoor', ALL,
              DAY, ['spring', 'summer']),
        place('herring-run-park', 'Herring Run Park', 'park', 'lauraville', 'Long stream-valley park with trails, '
              'ball fields and a playground through northeast Baltimore.', ['trail', 'playground', 'woods'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('lake-montebello', 'Lake Montebello', 'trail', 'lauraville', 'Reservoir with a flat paved loop of '
              'about a mile and a half, crowded with runners, cyclists and walkers.', ['running', 'cycling', 'walk'],
              'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('zekes-coffee', 'Zeke\'s Coffee', 'cafe', 'lauraville', 'Local roaster with a cafe on Harford Road, '
              'the neighborhood\'s morning stop.', ['coffee', 'roaster', 'local'], '$', 'indoor',
              ['solo', 'friends', 'coworkers'], DAY, cuisine='coffee'),
        place('hamilton-library', 'Enoch Pratt Hamilton Branch', 'library', 'lauraville', 'Neighborhood branch '
              'library on Harford Road.', ['books', 'quiet', 'kids'], 'free', 'indoor', ALL, DAY),
        place('towson-diner', 'Towson Diner', 'restaurant', 'towson', 'Big Greek-run diner on York Road with an '
              'enormous menu and late hours for students.', ['diner', 'late-night', 'breakfast'], '$', 'indoor', ALL,
              ['morning', 'afternoon', 'evening', 'late'], cuisine='american-diner'),
        place('towson-library', 'Towson Branch Library', 'library', 'towson', 'Baltimore County\'s large Towson '
              'branch library, with study rooms and a busy children\'s area.', ['books', 'study', 'kids'], 'free',
              'indoor', ALL, ['morning', 'afternoon', 'evening']),
        place('towson-farmers-market', 'Towson Farmers Market', 'market', 'towson', 'Thursday market downtown with '
              'produce, baked goods and lunch vendors.', ['farmers-market', 'lunch'], '$', 'outdoor', ALL, DAY, WARM),
        place('hampton-nhs', 'Hampton National Historic Site', 'landmark', 'towson', 'Georgian mansion and estate '
              'grounds that tell the history of a plantation and the people enslaved there.', ['history', 'grounds'],
              'free', 'mixed', ['solo', 'family', 'date'], DAY),
        place('cromwell-valley-park', 'Cromwell Valley Park', 'park', 'towson', 'County park of farm fields, '
              'orchards and trails with nature programs.', ['trail', 'nature', 'kids'], 'free', 'outdoor', ALL, DAY),
        place('hopkins-dome', 'Johns Hopkins Hospital dome', 'landmark', 'east-baltimore', 'The historic Billings '
              'Building with its dome and the marble Christus statue in the rotunda.', ['history', 'medical'],
              'free', 'indoor', ['solo', 'family'], DAY),
        place('northeast-market', 'Northeast Market', 'market', 'east-baltimore', 'City public market on Monument '
              'Street with lunch counters feeding hospital staff and neighbours.', ['food', 'lunch', 'historic'],
              '$', 'indoor', ALL, DAY),
        place('eager-park', 'Eager Park', 'park', 'east-baltimore', 'New neighborhood park with lawns, a '
              'playground and summer concerts near the Hopkins campus.', ['playground', 'lawn', 'events'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('orleans-street-library', 'Enoch Pratt Orleans Street Branch', 'library', 'east-baltimore',
              'Neighborhood branch library on Orleans Street with computers and after-school programs.',
              ['books', 'kids', 'computers'], 'free', 'indoor', ALL, DAY),
        place('great-blacks-in-wax', 'National Great Blacks In Wax Museum', 'museum', 'east-baltimore', 'Wax '
              'figures telling African American history, from the Middle Passage to the civil rights movement.',
              ['history', 'black-history'], '$', 'indoor', ALL, DAY),
    ],
    'colleges': [
        {'id': 'jhu', 'name': 'Johns Hopkins University', 'type': 'research-university',
         'neighborhood': 'charles-village', 'size': 'large', 'known_for': ['medicine', 'public-health',
         'engineering', 'international-studies', 'research'], 'source': S},
        {'id': 'jhu-medicine', 'name': 'Johns Hopkins School of Medicine', 'type': 'medical-school',
         'neighborhood': 'east-baltimore', 'size': 'medium', 'known_for': ['medicine', 'nursing',
         'public-health'], 'source': S},
        {'id': 'peabody', 'name': 'Peabody Institute', 'type': 'music-school', 'neighborhood': 'mount-vernon',
         'size': 'small', 'known_for': ['music', 'composition', 'dance'], 'source': S},
        {'id': 'mica', 'name': 'Maryland Institute College of Art', 'type': 'art-school',
         'neighborhood': 'bolton-hill', 'size': 'small', 'known_for': ['fine-art', 'illustration',
         'graphic-design'], 'source': S},
        {'id': 'umb', 'name': 'University of Maryland, Baltimore', 'type': 'medical-school',
         'neighborhood': 'downtown', 'size': 'medium', 'known_for': ['medicine', 'law', 'pharmacy', 'nursing',
         'social-work'], 'source': S},
        {'id': 'ubalt', 'name': 'University of Baltimore', 'type': 'public-university',
         'neighborhood': 'mount-vernon', 'size': 'medium', 'known_for': ['law', 'business', 'public-policy'],
         'source': S},
        {'id': 'loyola-md', 'name': 'Loyola University Maryland', 'type': 'private-university',
         'neighborhood': 'roland-park', 'size': 'medium', 'known_for': ['business', 'liberal-arts'], 'source': S},
        {'id': 'morgan-state', 'name': 'Morgan State University', 'type': 'public-university',
         'neighborhood': 'lauraville', 'size': 'medium', 'known_for': ['hbcu', 'engineering', 'architecture',
         'business'], 'source': S},
        {'id': 'towson-u', 'name': 'Towson University', 'type': 'public-university', 'neighborhood': 'towson',
         'size': 'large', 'known_for': ['education', 'nursing', 'business'], 'source': S},
    ],
    'employers': [
        {'id': 'jh-hospital', 'name': 'The Johns Hopkins Hospital', 'sector': 'healthcare',
         'neighborhood': 'east-baltimore', 'size': 'large', 'summary': 'The flagship teaching hospital and the '
         'city\'s largest employer group.', 'careers': ['registered-nurse', 'night-nurse', 'physician-resident',
         'pharmacist', 'medical-researcher', 'social-worker'], 'source': S},
        {'id': 'jhu-employer', 'name': 'Johns Hopkins University (Homewood)', 'sector': 'education',
         'neighborhood': 'charles-village', 'size': 'large', 'summary': 'Faculty, research and staff jobs on the '
         'main campus.', 'careers': ['professor', 'graduate-student', 'medical-researcher', 'data-analyst',
         'software-engineer'], 'source': S},
        {'id': 'umm-center', 'name': 'University of Maryland Medical Center', 'sector': 'healthcare',
         'neighborhood': 'downtown', 'size': 'large', 'summary': 'Academic hospital with the Shock Trauma Center.',
         'careers': ['registered-nurse', 'night-nurse', 'physician-resident', 'pharmacist'], 'source': S},
        {'id': 'kennedy-krieger', 'name': 'Kennedy Krieger Institute', 'sector': 'healthcare',
         'neighborhood': 'east-baltimore', 'size': 'medium', 'summary': 'Care and research for children with '
         'developmental disabilities.', 'careers': ['registered-nurse', 'social-worker', 'medical-researcher'],
         'source': S},
        {'id': 't-rowe-price', 'name': 'T. Rowe Price', 'sector': 'finance', 'neighborhood': 'harbor-east',
         'size': 'large', 'summary': 'Investment management firm headquartered on the waterfront at Harbor Point.',
         'careers': ['financial-analyst', 'software-engineer', 'data-analyst', 'marketing-coordinator'],
         'source': S},
        {'id': 'constellation', 'name': 'Constellation Energy', 'sector': 'energy', 'neighborhood': 'harbor-east',
         'size': 'large', 'summary': 'Energy company with a headquarters tower in Harbor East.',
         'careers': ['financial-analyst', 'data-analyst', 'accountant', 'software-engineer'], 'source': S},
        {'id': 'under-armour', 'name': 'Under Armour', 'sector': 'apparel', 'neighborhood': 'baltimore-peninsula',
         'size': 'large', 'summary': 'Sportswear company headquartered on the Baltimore Peninsula.',
         'careers': ['marketing-coordinator', 'graphic-designer', 'ux-designer', 'software-engineer',
         'data-analyst'], 'source': S},
        {'id': 'port-of-baltimore', 'name': 'Port of Baltimore marine terminals', 'sector': 'logistics',
         'neighborhood': 'canton', 'size': 'large', 'summary': 'Container and roll-on/roll-off terminals that '
         'employ longshore workers, logisticians and truckers.', 'careers': ['port-logistics'], 'source': S},
        {'id': 'baltimore-city-schools', 'name': 'Baltimore City Public Schools', 'sector': 'education',
         'neighborhood': 'station-north', 'size': 'large', 'summary': 'The city school district, headquartered on '
         'North Avenue.', 'careers': ['teacher', 'social-worker'], 'source': S},
        {'id': 'city-hall', 'name': 'Baltimore City government', 'sector': 'government', 'neighborhood': 'downtown',
         'size': 'large', 'summary': 'City agencies around City Hall and the municipal buildings.',
         'careers': ['government-analyst', 'social-worker', 'accountant'], 'source': S},
        {'id': 'horseshoe-baltimore', 'name': 'Horseshoe Casino Baltimore', 'sector': 'hospitality',
         'neighborhood': 'downtown', 'size': 'medium', 'summary': 'Casino near the stadiums.',
         'careers': ['casino-dealer', 'bartender', 'line-cook', 'server'], 'source': S},
        {'id': 'baltimore-sun', 'name': 'The Baltimore Sun', 'sector': 'media', 'neighborhood': 'downtown',
         'size': 'small', 'summary': 'The city\'s daily newspaper.', 'careers': ['journalist'], 'source': S},
        {'id': 'four-seasons-baltimore', 'name': 'Four Seasons Hotel Baltimore', 'sector': 'hospitality',
         'neighborhood': 'harbor-east', 'size': 'medium', 'summary': 'Luxury waterfront hotel.',
         'careers': ['hotel-front-desk', 'event-planner', 'line-cook', 'server', 'bartender'], 'source': S},
        {'id': 'center-stage', 'name': 'Baltimore Center Stage', 'sector': 'entertainment',
         'neighborhood': 'mount-vernon', 'size': 'small', 'summary': 'Maryland\'s state theater, in a converted '
         'school building on North Calvert Street.', 'careers': ['actor', 'performer', 'event-planner'],
         'source': S},
        {'id': 'everyman-theatre', 'name': 'Everyman Theatre', 'sector': 'entertainment', 'neighborhood': 'downtown',
         'size': 'small', 'summary': 'Resident-company theater on Fayette Street.', 'careers': ['actor', 'performer'],
         'source': S},
        {'id': 'towson-u-employer', 'name': 'Towson University', 'sector': 'education', 'neighborhood': 'towson',
         'size': 'large', 'summary': 'A large public university campus.', 'careers': ['professor',
         'graduate-student'], 'source': S},
    ],
    'career_hubs': [
        {'id': 'medical-campuses', 'name': 'Hospital and research campuses', 'neighborhoods': ['east-baltimore',
         'downtown'], 'sectors': ['healthcare', 'biotech', 'education'], 'summary': 'Johns Hopkins in East '
         'Baltimore and the University of Maryland campus downtown anchor the city\'s "eds and meds" economy.',
         'source': S},
        {'id': 'harbor-business', 'name': 'Harbor business district', 'neighborhoods': ['downtown',
         'harbor-east', 'inner-harbor'], 'sectors': ['finance', 'legal', 'energy', 'government', 'hospitality'],
         'summary': 'Banks, law firms, energy and investment companies, plus hotels and convention work.',
         'source': S},
        {'id': 'port-district', 'name': 'The port', 'neighborhoods': ['canton', 'locust-point'],
         'sectors': ['logistics', 'manufacturing'], 'summary': 'Marine terminals, warehouses and the Domino '
         'Sugars refinery.', 'source': S},
        {'id': 'homewood', 'name': 'Homewood and North Baltimore campuses', 'neighborhoods': ['charles-village',
         'roland-park', 'towson'], 'sectors': ['education'], 'summary': 'Universities and private schools.',
         'source': S},
    ],
    'climate': {
        'summary': 'Humid subtropical: hot, sticky summers with thunderstorms, mild springs and autumns, and cold '
                   'but changeable winters with occasional snow.',
        'months': [
            {'high_f': 42, 'low_f': 26, 'rain_days': 10, 'note': 'Coldest month; a few snow days most years.'},
            {'high_f': 46, 'low_f': 28, 'rain_days': 9, 'note': 'Cold, grey; snow possible.'},
            {'high_f': 55, 'low_f': 35, 'rain_days': 11, 'note': 'Changeable; early blossoms late in the month.'},
            {'high_f': 66, 'low_f': 45, 'rain_days': 11, 'note': 'Spring rain and blossoms.'},
            {'high_f': 75, 'low_f': 54, 'rain_days': 12, 'note': 'Warm and green; patios open.'},
            {'high_f': 84, 'low_f': 63, 'rain_days': 10, 'note': 'Humid; crab season gets going.'},
            {'high_f': 88, 'low_f': 68, 'rain_days': 10, 'note': 'Hottest month; afternoon thunderstorms.'},
            {'high_f': 86, 'low_f': 67, 'rain_days': 9, 'note': 'Hot and humid.'},
            {'high_f': 79, 'low_f': 60, 'rain_days': 8, 'note': 'Still warm; humidity eases.'},
            {'high_f': 68, 'low_f': 48, 'rain_days': 8, 'note': 'Crisp, sunny autumn.'},
            {'high_f': 57, 'low_f': 38, 'rain_days': 8, 'note': 'Cool; leaves turn.'},
            {'high_f': 46, 'low_f': 30, 'rain_days': 10, 'note': 'Cold; holiday lights.'},
        ],
        'source': CLIMATE,
    },
    'annual_events': [
        {'id': 'orioles-opening-day', 'name': 'Orioles Opening Day', 'months': [3, 4], 'neighborhood': 'downtown',
         'summary': 'The baseball season starts at Camden Yards and downtown fills with orange.', 'source': S},
        {'id': 'flower-mart', 'name': 'Flower Mart', 'months': [5], 'neighborhood': 'mount-vernon',
         'summary': 'Spring festival around the Washington Monument with flowers and lemon sticks.', 'source': S},
        {'id': 'kinetic-sculpture-race', 'name': 'Kinetic Sculpture Race', 'months': [5],
         'neighborhood': 'federal-hill', 'summary': 'Human-powered art vehicles race over land, mud and harbor '
         'water, starting at the American Visionary Art Museum.', 'source': S},
        {'id': 'baltimore-pride', 'name': 'Baltimore Pride', 'months': [6], 'neighborhood': 'mount-vernon',
         'summary': 'Parade and block party.', 'source': S},
        {'id': 'july-fourth-harbor', 'name': 'Fourth of July fireworks', 'months': [7],
         'neighborhood': 'inner-harbor', 'summary': 'Fireworks over the Inner Harbor.', 'source': S},
        {'id': 'little-italy-film-fest', 'name': 'Little Italy open-air film festival', 'months': [7, 8],
         'neighborhood': 'little-italy', 'summary': 'Friday night films projected onto a wall in Little Italy.',
         'source': S},
        {'id': 'artscape', 'name': 'Artscape', 'months': [7, 9], 'neighborhood': 'station-north',
         'summary': 'A large free outdoor arts festival; its dates have moved between summer and early autumn.',
         'source': S},
        {'id': 'ravens-season', 'name': 'Ravens football season', 'months': [9, 10, 11, 12, 1],
         'neighborhood': 'downtown', 'summary': 'Purple Fridays and Sunday game days.', 'source': S},
        {'id': 'fells-point-fun-festival', 'name': 'Fells Point Fun Festival', 'months': [10],
         'neighborhood': 'fells-point', 'summary': 'Street festival with music stages and food on the cobblestones.',
         'source': S},
        {'id': 'christmas-village', 'name': 'Christmas Village', 'months': [11, 12], 'neighborhood': 'inner-harbor',
         'summary': 'German-style Christmas market by the harbor.', 'source': S},
        {'id': 'miracle-on-34th', 'name': 'Miracle on 34th Street', 'months': [12], 'neighborhood': 'hampden',
         'summary': 'A block of rowhouses covered in over-the-top Christmas lights.', 'source': S},
    ],
}

# East Baltimore is referenced by Hopkins but listed here so the hospital campus has a neighborhood.
CITY['neighborhoods'].append(hood(
    'east-baltimore', 'East Baltimore Midway', 'The neighborhood around the Johns Hopkins medical campus, with '
    'new graduate housing beside older rowhouse blocks.', ['medical', 'students', 'changing'], 39.297, -76.592,
    'mid', ([1000, 1400], [1200, 1700], [1500, 2100]), ['apartment', 'rowhouse', 'student-housing'], 'medium',
    ['subway', 'citylink']))

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
