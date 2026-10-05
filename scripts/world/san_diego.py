"""Curated San Diego data. Run `python scripts/world/san_diego.py` to rewrite the shipped JSON."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'cities' / 'san-diego.json'
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
DAYLONG = ['morning', 'afternoon', 'evening']
DINNER = ['evening']
NIGHT = ['evening', 'late']
WARM = ['spring', 'summer', 'fall']

CITY = {
    'schema_version': 1, 'id': 'san-diego', 'name': 'San Diego', 'region': 'California', 'country': 'US',
    'timezone': 'America/Los_Angeles', 'aliases': ["America's Finest City", 'San Diego, CA', 'SD, California'],
    'summary': 'A sunny Pacific port city on the Mexican border, known for its beaches, Balboa Park, the Navy, '
               'biotech on the Torrey Pines mesa, fish tacos and craft beer.',
    'lat': 32.72, 'lon': -117.16,
    'speeds': {'walk': 4.5, 'car': 32, 'rideshare': 32, 'bus': 13, 'light-rail': 28, 'commuter-rail': 55,
               'ferry': 15},
    # Rough heritage weights for residents' names (estimates, not census figures).
    'names': {'mix': {'anglo': 4, 'hispanic': 3, 'east-asian': 1.6, 'black-american': 0.6, 'south-asian': 0.4,
                       'irish': 0.4, 'italian': 0.3, 'arabic': 0.3, 'jewish': 0.3, 'slavic': 0.2}},
    'sources': {
        S: {'kind': 'curated', 'title': 'San Diego places and neighborhoods written for Prospero Companion',
            'license': 'CC0-1.0', 'retrieved': '2026-10-05',
            'note': 'Well-known public places, institutions and employers from general knowledge. Businesses open '
                    'and close and rents move: treat this as a snapshot for fiction. Rents are rounded estimates '
                    'of typical 2025 asking ranges, not listings. Coordinates are approximate neighborhood centers.'},
        CLIMATE: {'kind': 'curated', 'title': 'Approximate monthly climate for San Diego (Lindbergh Field)',
                  'license': 'CC0-1.0', 'retrieved': '2026-10-05',
                  'note': 'Rounded values in line with NOAA 1991-2020 normals for San Diego International '
                          'Airport (Lindbergh Field); the coast is cooler and inland neighborhoods warmer. '
                          'Refresh with scripts/world when network access to NOAA is available.'},
    },
    'neighborhoods': [
        hood('downtown', 'Downtown and the Embarcadero', 'Condo towers in the Marina and Columbia districts, '
             'office blocks on Broadway and a bayfront promenade lined with ships.', ['central', 'waterfront',
             'business', 'high-rise'], 32.714, -117.166, 'very-high', ([2200, 2900], [2700, 3600], [3600, 5000]),
             ['apartment-tower', 'condo'], 'high', ['blue-line', 'green-line', 'orange-line', 'coaster', 'mts-bus',
             'coronado-ferry']),
        hood('gaslamp', 'Gaslamp Quarter', 'Victorian-era blocks of bars, restaurants and hotels between Broadway '
             'and the Convention Center.', ['nightlife', 'historic', 'touristy', 'central'], 32.711, -117.160,
             'very-high', ([2200, 2900], [2700, 3600], [3600, 5000]), ['apartment-tower', 'condo', 'loft'], 'high',
             ['green-line', 'blue-line', 'orange-line', 'mts-bus']),
        hood('east-village', 'East Village', 'Downtown\'s largest district: new apartment towers, breweries, the '
             'ballpark and the Central Library.', ['young-professional', 'sports', 'new-build', 'central'], 32.711,
             -117.153, 'high', ([2000, 2700], [2500, 3300], [3300, 4600]), ['apartment-tower', 'loft'], 'high',
             ['blue-line', 'green-line', 'orange-line', 'mts-bus']),
        hood('little-italy', 'Little Italy', 'A walkable grid of restaurants, piazzas and design shops on India '
             'Street, with a big Saturday market.', ['food', 'walkable', 'upscale'], 32.724, -117.169, 'very-high',
             ([2300, 3000], [2800, 3800], [3800, 5200]), ['apartment-tower', 'condo'], 'high',
             ['blue-line', 'green-line', 'mts-bus']),
        hood('bankers-hill', 'Bankers Hill', 'Old mansions and mid-rise apartments on the western edge of Balboa '
             'Park, with views over the bay.', ['historic', 'park', 'quiet', 'views'], 32.728, -117.162, 'high',
             ([1800, 2400], [2300, 3000], [3000, 4200]), ['apartment', 'condo', 'victorian'], 'high', ['mts-bus']),
        hood('hillcrest', 'Hillcrest', 'The heart of the city\'s LGBTQ+ community, with rainbow flags, brunch spots, '
             'bars and two big hospitals.', ['lgbtq-friendly', 'nightlife', 'brunch', 'walkable'], 32.748,
             -117.164, 'high', ([1600, 2100], [2000, 2700], [2700, 3700]), ['apartment', 'condo', 'bungalow'],
             'high', ['mts-bus', 'rapid']),
        hood('north-park', 'North Park', 'Craftsman bungalows, breweries, coffee shops and a bar strip on 30th '
             'Street.', ['hip', 'craft-beer', 'bars', 'young-professional'], 32.747, -117.130, 'mid',
             ([1500, 1950], [1850, 2500], [2500, 3400]), ['bungalow', 'apartment', 'craftsman'], 'high',
             ['mts-bus', 'rapid']),
        hood('south-park', 'South Park', 'A small, leafy neighborhood of craftsman houses and independent shops '
             'on the east side of Balboa Park.', ['quiet', 'leafy', 'neighbourly'], 32.723, -117.130, 'mid',
             ([1500, 1900], [1850, 2450], [2500, 3300]), ['craftsman', 'bungalow', 'apartment'], 'medium',
             ['mts-bus']),
        hood('normal-heights', 'Normal Heights', 'Bungalows above Mission Valley along Adams Avenue, with antique '
             'shops, dive bars and coffee.', ['laid-back', 'neighbourly', 'affordable'], 32.763, -117.112, 'mid',
             ([1400, 1800], [1750, 2300], [2300, 3100]), ['bungalow', 'apartment'], 'medium', ['mts-bus', 'rapid']),
        hood('pacific-beach', 'Pacific Beach', 'A young beach town of surf shops, bars on Garnet Avenue and a '
             'busy boardwalk.', ['beach', 'party', 'young', 'surf'], 32.797, -117.240, 'high',
             ([1700, 2200], [2200, 2900], [2900, 4000]), ['apartment', 'beach-cottage', 'condo'], 'high',
             ['mts-bus']),
        hood('mission-beach', 'Mission Beach', 'A narrow sandbar between the ocean and Mission Bay, packed with '
             'vacation rentals and the Belmont Park boardwalk.', ['beach', 'touristy', 'summer'], 32.775, -117.252,
             'very-high', ([1900, 2500], [2400, 3300], [3200, 4800]), ['beach-cottage', 'duplex', 'condo'], 'high',
             ['mts-bus']),
        hood('ocean-beach', 'Ocean Beach', 'Bohemian surf town with a long fishing pier, a dog beach and antique '
             'shops on Newport Avenue.', ['beach', 'bohemian', 'surf', 'dogs'], 32.747, -117.247, 'high',
             ([1600, 2100], [2000, 2700], [2700, 3700]), ['beach-cottage', 'apartment', 'duplex'], 'high',
             ['mts-bus']),
        hood('point-loma', 'Point Loma', 'A hilly peninsula of family homes, sportfishing docks, the Liberty '
             'Station redevelopment and naval installations.', ['family', 'military', 'views', 'waterfront'],
             32.733, -117.225, 'high', ([1700, 2200], [2200, 2900], [2900, 4100]),
             ['single-family', 'apartment', 'condo'], 'medium', ['mts-bus']),
        hood('la-jolla', 'La Jolla', 'An affluent seaside village with sea caves, seals and sea lions, galleries '
             'and the Scripps Institution of Oceanography.', ['affluent', 'beach', 'scenic', 'upscale'], 32.847,
             -117.273, 'very-high', ([2000, 2600], [2600, 3500], [3500, 5200]),
             ['single-family', 'condo', 'apartment'], 'medium', ['mts-bus']),
        hood('university-city', 'University City and UTC', 'Apartment complexes and offices around Westfield UTC '
             'mall and the UC San Diego campus, at the end of the Blue Line.', ['students', 'suburban',
             'corporate', 'academic'], 32.870, -117.213, 'high', ([2000, 2500], [2500, 3200], [3100, 4200]),
             ['apartment', 'condo', 'student-housing'], 'medium', ['blue-line', 'mts-bus']),
        hood('sorrento-valley', 'Sorrento Valley and Torrey Pines Mesa', 'Office parks and labs for biotech and '
             'wireless companies on the mesa above the Torrey Pines coast.', ['biotech', 'tech', 'corporate',
             'suburban'], 32.898, -117.230, 'high', ([2000, 2500], [2500, 3100], [3000, 4000]),
             ['apartment', 'townhouse'], 'low', ['coaster', 'mts-bus']),
        hood('mission-valley', 'Mission Valley', 'The freeway valley of malls, hotels and newer apartment '
             'complexes along the San Diego River, with Snapdragon Stadium at its east end.', ['shopping',
             'suburban', 'new-build', 'central'], 32.772, -117.150, 'high', ([1900, 2400], [2400, 3100],
             [3000, 4000]), ['apartment', 'condo'], 'medium', ['green-line', 'mts-bus']),
        hood('old-town', 'Old Town', 'Where the city began: adobe buildings, Mexican restaurants and the main '
             'transit center on the way to the beaches.', ['historic', 'touristy', 'mexican-food'], 32.754,
             -117.197, 'high', ([1700, 2200], [2100, 2800], [2800, 3700]), ['apartment', 'townhouse'], 'medium',
             ['blue-line', 'green-line', 'coaster', 'mts-bus']),
        hood('barrio-logan', 'Barrio Logan', 'A historically Mexican-American neighborhood under the Coronado '
             'Bridge, known for Chicano Park murals, galleries and the shipyards beside it.', ['chicano-culture',
             'arts', 'industrial', 'gentrifying'], 32.698, -117.143, 'low', ([1300, 1700], [1600, 2100],
             [2000, 2800]), ['apartment', 'bungalow', 'loft'], 'medium', ['blue-line', 'mts-bus']),
        hood('coronado', 'Coronado', 'A wealthy island-like resort town across the bay, home to the Hotel del '
             'Coronado and Naval Air Station North Island.', ['affluent', 'beach', 'military', 'resort'], 32.686,
             -117.183, 'very-high', ([2200, 2900], [2800, 3800], [3800, 5500]),
             ['single-family', 'condo', 'apartment'], 'high', ['coronado-ferry', 'mts-bus']),
        hood('kearny-mesa', 'Kearny Mesa', 'A mesa of office parks, hospitals and car dealerships, with the '
             'Asian restaurants of Convoy Street; MCAS Miramar is just to the north.', ['food', 'asian-food',
             'suburban', 'medical'], 32.825, -117.152, 'mid', ([1600, 2000], [1950, 2500], [2500, 3300]),
             ['apartment', 'single-family'], 'low', ['mts-bus']),
        hood('college-area', 'College Area', 'Student apartments and ranch houses around San Diego State '
             'University.', ['students', 'college-town', 'affordable'], 32.773, -117.071, 'mid',
             ([1300, 1750], [1700, 2200], [2200, 3000]), ['student-housing', 'apartment', 'single-family'],
             'medium', ['green-line', 'mts-bus', 'rapid']),
        hood('linda-vista', 'Linda Vista', 'A diverse, modest neighborhood on the mesa above Mission Valley, '
             'home to the University of San Diego.', ['diverse', 'affordable', 'academic'], 32.780, -117.178,
             'mid', ([1450, 1850], [1800, 2300], [2300, 3100]), ['apartment', 'single-family'], 'medium',
             ['green-line', 'mts-bus']),
    ],
    'transit': [
        {'id': 'blue-line', 'name': 'UC San Diego Blue Line (MTS Trolley)', 'kind': 'light-rail',
         'summary': 'Trolley from the San Ysidro border crossing through downtown and Old Town to UC San Diego '
         'and UTC.', 'source': S},
        {'id': 'green-line', 'name': 'Green Line (MTS Trolley)', 'kind': 'light-rail', 'summary': 'Trolley from '
         'downtown through Old Town and Mission Valley past Snapdragon Stadium and SDSU to Santee.',
         'source': S},
        {'id': 'orange-line', 'name': 'Orange Line (MTS Trolley)', 'kind': 'light-rail', 'summary': 'Trolley from '
         'downtown east through Southeast San Diego to Lemon Grove and El Cajon.', 'source': S},
        {'id': 'mts-bus', 'name': 'MTS buses', 'kind': 'bus', 'summary': 'The Metropolitan Transit System bus '
         'network, the only transit to the beach neighborhoods.', 'source': S},
        {'id': 'rapid', 'name': 'MTS Rapid buses', 'kind': 'bus', 'summary': 'Limited-stop bus routes, including '
         'the line along El Cajon Boulevard to SDSU.', 'source': S},
        {'id': 'coaster', 'name': 'COASTER', 'kind': 'commuter-rail', 'summary': 'Commuter trains along the coast '
         'from Santa Fe Depot via Old Town and Sorrento Valley to Oceanside.', 'source': S},
        {'id': 'coronado-ferry', 'name': 'Coronado Ferry', 'kind': 'ferry', 'summary': 'Passenger ferry across the '
         'bay between downtown and the Coronado Ferry Landing.', 'source': S},
        {'id': 'car', 'name': 'Driving', 'kind': 'car', 'summary': 'Most San Diegans drive; the freeways I-5, I-8, '
         'I-15 and SR-163 jam at rush hour.', 'source': S},
        {'id': 'rideshare', 'name': 'Rideshare', 'kind': 'rideshare', 'summary': 'App-based rides, common for '
         'nights out in the Gaslamp and Pacific Beach.', 'source': S},
    ],
    'places': [
        # Downtown and the Embarcadero
        place('uss-midway', 'USS Midway Museum', 'museum', 'downtown', 'A decommissioned aircraft carrier on the '
              'bay with restored planes on the flight deck.', ['history', 'military', 'iconic', 'ships'], '$$$',
              'mixed', ALL, DAY),
        place('maritime-museum', 'Maritime Museum of San Diego', 'museum', 'downtown', 'Historic ships on the '
              'Embarcadero, led by the 1863 sailing ship Star of India.', ['history', 'ships', 'waterfront'], '$$',
              'mixed', ALL, DAY),
        place('embarcadero', 'Embarcadero waterfront', 'landmark', 'downtown', 'Bayfront promenade along Harbor '
              'Drive past the ships, cruise terminal and Tuna Harbor.', ['waterfront', 'walk', 'views'], 'free',
              'outdoor', ALL, DAYLONG),
        place('seaport-village', 'Seaport Village', 'shopping', 'downtown', 'Waterfront shops and snack stands on '
              'the bay, beside a historic carousel.', ['touristy', 'waterfront', 'souvenirs'], '$$', 'outdoor', ALL,
              DAYLONG),
        place('waterfront-park', 'Waterfront Park', 'park', 'downtown', 'Lawns and splash fountains in front of '
              'the County Administration Center.', ['fountains', 'kids', 'picnic'], 'free', 'outdoor', ALL, DAY),
        place('rady-shell', 'The Rady Shell at Jacobs Park', 'venue', 'downtown', 'Outdoor bayfront concert shell, '
              'home to the San Diego Symphony\'s summer season.', ['concerts', 'classical', 'outdoor'], '$$$',
              'outdoor', ['date', 'friends', 'solo'], ['evening'], WARM),
        place('civic-theatre', 'San Diego Civic Theatre', 'venue', 'downtown', 'The main downtown hall for touring '
              'Broadway shows and the opera.', ['theater', 'broadway'], '$$$', 'indoor', ['date', 'friends',
              'family'], ['evening']),
        # Gaslamp and East Village
        place('gaslamp-fifth-avenue', 'Fifth Avenue in the Gaslamp', 'nightlife', 'gaslamp', 'Blocks of bars, '
              'rooftop lounges and clubs under the Gaslamp Quarter arch.', ['bars', 'clubs', 'rooftops'], '$$$',
              'mixed', ['friends', 'date'], NIGHT),
        place('petco-park', 'Petco Park', 'stadium', 'east-village', 'The Padres\' downtown ballpark, built around '
              'the old Western Metal Supply building.', ['baseball', 'sports', 'iconic'], '$$', 'outdoor', ALL,
              ['afternoon', 'evening'], ['spring', 'summer', 'fall']),
        place('central-library', 'San Diego Central Library', 'library', 'east-village', 'The domed main library '
              'with a reading room and terrace views.', ['books', 'quiet', 'free', 'views'], 'free', 'indoor',
              ['solo', 'family'], DAY),
        # Little Italy
        place('little-italy-mercato', 'Little Italy Mercato', 'market', 'little-italy', 'Big Saturday farmers\' '
              'market filling several blocks of Date Street and Cedar Street.', ['farmers-market', 'saturday',
              'food'], '$', 'outdoor', ALL, ['morning']),
        place('crack-shack', 'The Crack Shack', 'restaurant', 'little-italy', 'Open-air fried chicken and egg '
              'sandwich spot with a bocce court.', ['fried-chicken', 'patio', 'casual'], '$$', 'outdoor', ALL,
              ['afternoon', 'evening'], cuisine='american'),
        place('james-coffee', 'James Coffee Co.', 'cafe', 'little-italy', 'Roaster and coffee bar in a bright '
              'warehouse space on India Street.', ['coffee', 'roaster', 'laptop'], '$', 'indoor', ADULT, DAY,
              cuisine='coffee'),
        # Balboa Park (listed under Bankers Hill)
        place('balboa-park', 'Balboa Park', 'park', 'bankers-hill', 'A huge park of Spanish Revival buildings, '
              'gardens and museums along El Prado.', ['park', 'architecture', 'gardens', 'iconic'], 'free',
              'outdoor', ALL, DAYLONG),
        place('san-diego-zoo', 'San Diego Zoo', 'attraction', 'bankers-hill', 'The famous zoo in Balboa Park, '
              'spread across canyons with a Skyfari aerial tram.', ['animals', 'kids', 'iconic'], '$$$',
              'outdoor', ALL, DAY),
        place('sdma', 'San Diego Museum of Art', 'museum', 'bankers-hill', 'Balboa Park\'s main art museum, with '
              'Spanish old masters and a sculpture garden.', ['art', 'rainy-day'], '$$', 'indoor', ALL, DAY),
        place('fleet-science-center', 'Fleet Science Center', 'museum', 'bankers-hill', 'Hands-on science museum '
              'with a dome theater.', ['science', 'kids', 'rainy-day'], '$$', 'indoor', ['family', 'friends',
              'date'], DAY),
        place('the-nat', 'San Diego Natural History Museum', 'museum', 'bankers-hill', '"The Nat": fossils, '
              'regional wildlife and a giant-screen theater.', ['science', 'dinosaurs', 'kids', 'rainy-day'], '$$',
              'indoor', ['family', 'friends', 'solo'], DAY),
        place('museum-of-us', 'Museum of Us', 'museum', 'bankers-hill', 'Anthropology museum under the California '
              'Tower, the landmark of Balboa Park.', ['anthropology', 'history', 'rainy-day'], '$$', 'indoor', ALL,
              DAY),
        place('spreckels-organ', 'Spreckels Organ Pavilion', 'venue', 'bankers-hill', 'Outdoor pipe organ with '
              'free Sunday afternoon concerts.', ['free', 'concerts', 'sunday'], 'free', 'outdoor', ALL,
              ['afternoon']),
        place('old-globe', 'The Old Globe', 'venue', 'bankers-hill', 'Respected theater in Balboa Park known for '
              'its summer Shakespeare festival.', ['theater', 'shakespeare'], '$$$', 'mixed', ['date', 'friends',
              'solo'], ['evening']),
        # Uptown
        place('hillcrest-farmers-market', 'Hillcrest Farmers Market', 'market', 'hillcrest', 'Sunday market with '
              'produce and international food stalls.', ['farmers-market', 'sunday', 'food'], '$', 'outdoor', ALL,
              ['morning']),
        place('hillcrest-nightlife', 'University Avenue bars in Hillcrest', 'nightlife', 'hillcrest', 'The '
              'center of San Diego\'s gay nightlife, with bars and dance clubs around the Hillcrest sign.',
              ['lgbtq', 'bars', 'dancing'], '$$', 'indoor', ['friends', 'date', 'solo'], NIGHT),
        place('north-park-thirtieth', '30th Street in North Park', 'nightlife', 'north-park', 'A strip of '
              'breweries, beer bars and restaurants.', ['craft-beer', 'bars'], '$$', 'mixed', ['friends', 'date'],
              NIGHT),
        place('observatory-north-park', 'The Observatory North Park', 'venue', 'north-park', 'Restored 1920s '
              'theater hosting touring rock and indie bands.', ['live-music', 'concerts'], '$$', 'indoor',
              ['friends', 'date', 'solo'], NIGHT),
        place('north-park-thursday-market', 'North Park Thursday Market', 'market', 'north-park', 'Weekly evening '
              'farmers\' market with food stalls.', ['farmers-market', 'food'], '$', 'outdoor', ALL,
              ['afternoon', 'evening']),
        place('adams-avenue', 'Adams Avenue', 'shopping', 'normal-heights', 'Antique and vintage shops, bars and '
              'cafes along Normal Heights\' main street.', ['vintage', 'antiques', 'walk'], '$', 'outdoor', ALL,
              DAY),
        # Beaches
        place('pacific-beach-boardwalk', 'Pacific Beach and the boardwalk', 'beach', 'pacific-beach', 'Wide surf '
              'beach with a boardwalk busy with skaters, cyclists and joggers.', ['beach', 'surf', 'boardwalk'],
              'free', 'outdoor', ALL, DAYLONG),
        place('crystal-pier', 'Crystal Pier', 'landmark', 'pacific-beach', 'Wooden pier at the end of Garnet '
              'Avenue with a row of cottages built on it.', ['pier', 'sunset', 'views'], 'free', 'outdoor', ALL,
              DAYLONG),
        place('garnet-avenue', 'Garnet Avenue bars', 'nightlife', 'pacific-beach', 'Beach bars and taco shops '
              'packed with a young crowd at night.', ['bars', 'party', 'young'], '$$', 'mixed', ['friends'], NIGHT),
        place('oscars-mexican-seafood', 'Oscar\'s Mexican Seafood', 'restaurant', 'pacific-beach', 'Small, busy '
              'counter for fish and shrimp tacos.', ['tacos', 'fish-tacos', 'casual'], '$', 'mixed', ALL,
              ['afternoon', 'evening'], cuisine='mexican-seafood'),
        place('belmont-park', 'Belmont Park', 'attraction', 'mission-beach', 'Beachfront amusement park around the '
              'Giant Dipper, a wooden roller coaster from 1925.', ['rides', 'roller-coaster', 'kids'], '$$',
              'outdoor', ['family', 'friends', 'date'], DAYLONG),
        place('mission-beach-sand', 'Mission Beach', 'beach', 'mission-beach', 'Crowded summer beach along the '
              'boardwalk south of Pacific Beach.', ['beach', 'volleyball', 'boardwalk'], 'free', 'outdoor', ALL,
              DAY, WARM),
        place('mission-bay-park', 'Mission Bay Park', 'park', 'mission-beach', 'A large aquatic park of calm '
              'coves, beaches and lawns for kayaking, paddleboarding and bonfires.', ['water', 'kayaking',
              'picnic', 'cycling'], 'free', 'outdoor', ALL, DAYLONG),
        place('ob-pier', 'Ocean Beach Pier', 'landmark', 'ocean-beach', 'One of the longest concrete piers on the '
              'West Coast, popular with fishermen.', ['pier', 'fishing', 'sunset'], 'free', 'outdoor', ALL,
              DAYLONG),
        place('ob-dog-beach', 'Ocean Beach Dog Beach', 'beach', 'ocean-beach', 'An off-leash beach where the San '
              'Diego River meets the ocean.', ['dogs', 'beach'], 'free', 'outdoor', ALL, DAY),
        place('hodads', 'Hodad\'s', 'restaurant', 'ocean-beach', 'Burger joint on Newport Avenue covered in '
              'license plates and surf stickers.', ['burgers', 'line', 'casual'], '$$', 'indoor', ALL,
              ['afternoon', 'evening'], cuisine='burgers'),
        place('newport-avenue', 'Newport Avenue', 'shopping', 'ocean-beach', 'OB\'s main street of antique malls, '
              'surf shops and dive bars.', ['antiques', 'surf-shops', 'walk'], '$', 'outdoor', ALL, DAYLONG),
        place('ob-farmers-market', 'Ocean Beach Farmers Market', 'market', 'ocean-beach', 'Wednesday afternoon '
              'market on Newport Avenue with food and buskers.', ['farmers-market', 'food', 'music'], '$',
              'outdoor', ALL, ['afternoon', 'evening']),
        place('sunset-cliffs', 'Sunset Cliffs Natural Park', 'park', 'ocean-beach', 'Sandstone bluffs and sea '
              'arches where people gather to watch the sun go down.', ['sunset', 'views', 'cliffs', 'surf'], 'free',
              'outdoor', ALL, ['afternoon', 'evening']),
        # Point Loma
        place('cabrillo-monument', 'Cabrillo National Monument', 'landmark', 'point-loma', 'National park site at '
              'the tip of Point Loma with an old lighthouse, bay views and tide pools.', ['national-park', 'views',
              'tide-pools', 'history'], '$', 'outdoor', ALL, DAY),
        place('liberty-station', 'Liberty Station', 'shopping', 'point-loma', 'A former Naval Training Center '
              'turned into shops, restaurants, arts studios and lawns.', ['shopping', 'arts', 'history'], '$$',
              'mixed', ALL, DAYLONG),
        place('liberty-public-market', 'Liberty Public Market', 'market', 'point-loma', 'Food hall in a former '
              'navy building at Liberty Station.', ['food-hall', 'casual'], '$$', 'indoor', ALL,
              ['afternoon', 'evening']),
        place('stone-liberty-station', 'Stone Brewing World Bistro & Gardens', 'bar', 'point-loma', 'Large '
              'brewery restaurant at Liberty Station with a garden patio.', ['craft-beer', 'patio'], '$$', 'mixed',
              ADULT, ['afternoon', 'evening']),
        place('shelter-island', 'Shelter Island', 'park', 'point-loma', 'Bayfront strip with a walking path, '
              'marinas and skyline views.', ['waterfront', 'walk', 'views', 'fishing'], 'free', 'outdoor', ALL,
              DAYLONG),
        place('phils-bbq', 'Phil\'s BBQ', 'restaurant', 'point-loma', 'Long-running barbecue spot near the sports '
              'arena, known for ribs and long lines.', ['barbecue', 'ribs', 'line'], '$$', 'indoor', ALL,
              ['afternoon', 'evening'], cuisine='barbecue'),
        # La Jolla
        place('la-jolla-cove', 'La Jolla Cove', 'beach', 'la-jolla', 'A small cove where sea lions sprawl on the '
              'rocks and snorkelers swim with garibaldi.', ['sea-lions', 'snorkeling', 'iconic', 'views'], 'free',
              'outdoor', ALL, DAY),
        place('childrens-pool', 'Children\'s Pool', 'beach', 'la-jolla', 'Seawall-sheltered beach taken over by '
              'harbor seals, closed to people during pupping season.', ['seals', 'wildlife'], 'free', 'outdoor',
              ALL, DAY),
        place('la-jolla-shores', 'La Jolla Shores', 'beach', 'la-jolla', 'Gentle, wide beach for surf lessons, '
              'kayak tours and family swimming.', ['beach', 'surf-lessons', 'kayaking', 'kids'], 'free', 'outdoor',
              ALL, DAY),
        place('windansea', 'Windansea Beach', 'beach', 'la-jolla', 'Rocky surf beach with a palm-thatched shack, '
              'known among surfers.', ['surf', 'sunset', 'locals'], 'free', 'outdoor', ADULT, ['morning',
              'evening']),
        place('birch-aquarium', 'Birch Aquarium at Scripps', 'attraction', 'la-jolla', 'The public aquarium of the '
              'Scripps Institution of Oceanography, on a hill above the shore.', ['animals', 'ocean', 'kids',
              'rainy-day'], '$$', 'mixed', ALL, DAY),
        place('bird-rock-coffee', 'Bird Rock Coffee Roasters', 'cafe', 'la-jolla', 'Award-winning local roaster\'s '
              'original cafe on La Jolla Boulevard.', ['coffee', 'roaster'], '$', 'indoor', ADULT, DAY,
              cuisine='coffee'),
        place('mcasd-la-jolla', 'Museum of Contemporary Art San Diego', 'museum', 'la-jolla', 'Contemporary art '
              'museum on the ocean bluffs in La Jolla.', ['art', 'ocean-views', 'rainy-day'], '$$', 'indoor', ADULT,
              DAY),
        # North
        place('torrey-pines-reserve', 'Torrey Pines State Natural Reserve', 'trail', 'sorrento-valley', 'Clifftop '
              'trails through rare Torrey pines down to the beach.', ['hiking', 'views', 'beach'], '$', 'outdoor',
              ALL, DAY),
        place('torrey-pines-gliderport', 'Torrey Pines Gliderport', 'attraction', 'sorrento-valley', 'Paragliders '
              'launch from the cliffs over Black\'s Beach; tandem flights available.', ['paragliding', 'views'],
              '$$$', 'outdoor', ['friends', 'date', 'solo'], DAY),
        place('westfield-utc', 'Westfield UTC', 'shopping', 'university-city', 'Outdoor mall with an ice rink and a '
              'Blue Line trolley stop.', ['mall', 'ice-rink'], '$$', 'mixed', ALL, ['afternoon', 'evening']),
        place('geisel-library', 'Geisel Library', 'library', 'university-city', 'UC San Diego\'s brutalist library '
              'shaped like a stack of concrete hands.', ['architecture', 'books', 'quiet'], 'free', 'indoor',
              ['solo'], DAYLONG),
        # Mission Valley and Old Town
        place('fashion-valley', 'Fashion Valley', 'shopping', 'mission-valley', 'Upscale open-air mall with its own '
              'trolley station.', ['mall', 'luxury'], '$$$', 'mixed', ALL, ['afternoon', 'evening']),
        place('snapdragon-stadium', 'Snapdragon Stadium', 'stadium', 'mission-valley', 'Stadium for SDSU football '
              'and the city\'s professional soccer teams.', ['football', 'soccer', 'sports'], '$$', 'outdoor', ALL,
              ['afternoon', 'evening']),
        place('old-town-state-park', 'Old Town San Diego State Historic Park', 'landmark', 'old-town', 'Restored '
              'adobes, shops and museums from the Mexican and early American eras.', ['history', 'free', 'walk'],
              'free', 'outdoor', ALL, DAY),
        place('cafe-coyote', 'Cafe Coyote', 'restaurant', 'old-town', 'Big Old Town Mexican restaurant where '
              'tortillas are made by hand at the window.', ['mexican', 'margaritas', 'patio'], '$$', 'mixed', ALL,
              ['afternoon', 'evening'], cuisine='mexican'),
        # Barrio Logan and Coronado
        place('chicano-park', 'Chicano Park', 'landmark', 'barrio-logan', 'Park under the Coronado Bridge whose '
              'pillars are painted with Chicano murals.', ['murals', 'history', 'art'], 'free', 'outdoor', ALL,
              DAY),
        place('las-cuatro-milpas', 'Las Cuatro Milpas', 'restaurant', 'barrio-logan', 'Cash-only lunch counter '
              'making tortillas, rolled tacos and beans since the 1930s.', ['tacos', 'line', 'cash-only',
              'historic'], '$', 'indoor', ALL, ['morning', 'afternoon'], cuisine='mexican'),
        place('hotel-del', 'Hotel del Coronado', 'landmark', 'coronado', 'Red-roofed Victorian beach resort from '
              '1888, open to wander and grab a drink.', ['historic', 'architecture', 'iconic', 'beach'], '$$$',
              'mixed', ALL, DAYLONG),
        place('coronado-beach', 'Coronado Beach', 'beach', 'coronado', 'Wide, sparkling beach in front of the Hotel '
              'del Coronado.', ['beach', 'family', 'sunset'], 'free', 'outdoor', ALL, DAYLONG),
        # Kearny Mesa
        place('convoy-district', 'Convoy Street', 'restaurant', 'kearny-mesa', 'Strip malls packed with Korean, '
              'Japanese, Chinese and Vietnamese restaurants, boba shops and karaoke.', ['asian-food', 'ramen',
              'korean-bbq', 'boba'], '$$', 'indoor', ALL, ['afternoon', 'evening', 'late'], cuisine='pan-asian'),
        place('mitsuwa', 'Mitsuwa Marketplace', 'market', 'kearny-mesa', 'Japanese supermarket with a food court.',
              ['groceries', 'japanese', 'food-court'], '$', 'indoor', ALL, DAY, cuisine='japanese'),
        # Everyday neighborhood spots: cafes, diners, pubs, libraries, parks and markets.
        place('kansas-city-barbeque', 'Kansas City Barbeque', 'restaurant', 'downtown', 'Bayside barbecue joint and '
              'bar where the piano scene in Top Gun was filmed.', ['bbq', 'dive-bar', 'movie-history'], '$', 'indoor',
              ['friends', 'solo'], ['afternoon', 'evening', 'late'], cuisine='bbq'),
        place('horton-plaza-park', 'Horton Plaza Park', 'park', 'gaslamp', 'Plaza with an old fountain, splash '
              'jets and lunch kiosks at the top of the Gaslamp.', ['plaza', 'fountain', 'lunch-break'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('davis-horton-house', 'Davis-Horton House Museum', 'museum', 'gaslamp', 'The oldest surviving '
              'building in New Town, with walking tours of the Gaslamp\'s history.', ['history', 'tours'], '$',
              'indoor', ['solo', 'family', 'date'], DAY),
        place('spreckels-theatre', 'Spreckels Theatre', 'venue', 'gaslamp', 'Ornate 1912 theater on Broadway for '
              'concerts, comedy and touring shows.', ['theater', 'concerts', 'historic'], '$$', 'indoor',
              ['date', 'friends'], ['evening']),
        place('cafe-sevilla', 'Café Sevilla', 'restaurant', 'gaslamp', 'Long-running Spanish restaurant with '
              'tapas, paella, flamenco shows and salsa nights.', ['tapas', 'flamenco', 'dancing'], '$$', 'indoor',
              ['date', 'friends'], NIGHT, cuisine='spanish'),
        place('american-comedy-co', 'American Comedy Co.', 'venue', 'gaslamp', 'Basement comedy club on Sixth '
              'Avenue with touring headliners and open mics.', ['comedy', 'late-night'], '$$', 'indoor',
              ['friends', 'date'], NIGHT),
        place('basic-bar-pizza', 'Basic Bar & Pizza', 'restaurant', 'east-village', 'Warehouse bar serving '
              'thin-crust New Haven-style pizza, busy before Padres games.', ['pizza', 'beer', 'game-day'], '$$',
              'indoor', ['friends', 'date'], ['evening', 'late'], cuisine='pizza'),
        place('fault-line-park', 'Fault Line Park', 'park', 'east-village', 'Small new park with a playground, dog '
              'area and lawn among the East Village towers.', ['dogs', 'playground', 'local'], 'free', 'outdoor',
              ALL, ['morning', 'afternoon', 'evening']),
        place('half-door-brewing', 'Half Door Brewing Co.', 'bar', 'east-village', 'Irish-style brewpub in an old '
              'house a block from Petco Park.', ['brewery', 'pub', 'game-day'], '$$', 'mixed', ['friends', 'solo'],
              ['afternoon', 'evening', 'late'], cuisine='irish-pub'),
        place('filippis', 'Filippi\'s Pizza Grotto', 'restaurant', 'little-italy', 'Family Italian deli and '
              'red-sauce restaurant on India Street since 1950, with Chianti bottles on the ceiling.',
              ['pizza', 'italian', 'old-school'], '$$', 'indoor', ALL, ['afternoon', 'evening'], cuisine='italian'),
        place('amici-park', 'Amici Park', 'park', 'little-italy', 'Neighborhood park with bocce courts, a small '
              'amphitheatre and a dog run.', ['bocce', 'dogs', 'local'], 'free', 'outdoor', ALL,
              ['morning', 'afternoon', 'evening']),
        place('hob-nob-hill', 'Hob Nob Hill', 'restaurant', 'bankers-hill', 'Comfort-food coffee shop on First '
              'Avenue serving breakfasts and pot roast since 1944.', ['diner', 'breakfast', 'historic'], '$',
              'indoor', ALL, ['morning', 'afternoon', 'evening'], cuisine='american-diner'),
        place('hash-house-a-go-go', 'Hash House a Go Go', 'restaurant', 'hillcrest', 'Brunch spot on Fifth Avenue '
              'known for enormous plates and weekend waits.', ['brunch', 'big-portions'], '$$', 'indoor', ALL, DAY,
              cuisine='american'),
        place('bread-and-cie', 'Bread & Cie', 'cafe', 'hillcrest', 'Artisan bakery and cafe on University Avenue for '
              'sandwiches and loaves to take home.', ['bakery', 'coffee', 'sandwiches'], '$', 'indoor', ALL, DAY,
              cuisine='bakery'),
        place('mission-hills-hillcrest-library', 'Mission Hills-Hillcrest Library', 'library', 'hillcrest', 'Modern '
              'branch library with a rooftop terrace and community rooms.', ['books', 'study', 'quiet'], 'free',
              'indoor', ALL, DAY),
        place('caffe-calabria', 'Caffè Calabria', 'cafe', 'north-park', 'Roaster and Italian-style coffee bar on '
              '30th Street, with Neapolitan pizza at night.', ['coffee', 'roaster', 'pizza'], '$', 'indoor', ALL,
              ['morning', 'afternoon', 'evening'], cuisine='italian-cafe'),
        place('north-park-library', 'North Park Branch Library', 'library', 'north-park', 'Neighborhood branch '
              'library on 30th Street.', ['books', 'quiet', 'kids'], 'free', 'indoor', ALL, DAY),
        place('toronado-san-diego', 'Toronado', 'bar', 'north-park', 'Beer bar on 30th Street with a long draught '
              'list of local and Belgian beers.', ['beer', 'craft-beer'], '$$', 'indoor', ['friends', 'solo'], NIGHT),
        place('hamiltons-tavern', 'Hamilton\'s Tavern', 'bar', 'south-park', 'Corner beer bar with a famous tap list, '
              'pinball and pub food.', ['craft-beer', 'pub', 'local'], '$$', 'indoor', ['friends', 'solo'], NIGHT,
              cuisine='american-pub'),
        place('station-tavern', 'Station Tavern', 'restaurant', 'south-park', 'Burger and beer spot with a big '
              'family-friendly patio by the old streetcar stop.', ['burgers', 'patio', 'family'], '$$', 'mixed', ALL,
              ['afternoon', 'evening'], cuisine='burgers'),
        place('golden-hill-park', 'Golden Hill Park', 'park', 'south-park', 'Hilly southeastern corner of Balboa '
              'Park with a playground, picnic areas and a disc golf course.', ['playground', 'picnic', 'disc-golf'],
              'free', 'outdoor', ALL, DAY),
        place('morley-field', 'Morley Field Sports Complex', 'fitness', 'south-park', 'Balboa Park sports area with a '
              'public pool, tennis courts, disc golf and the velodrome.', ['pool', 'tennis', 'disc-golf'], '$',
              'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('grape-street-dog-park', 'Grape Street Dog Park', 'park', 'south-park', 'Big off-leash meadow on the '
              'edge of Balboa Park where neighbours meet with their dogs.', ['dogs', 'off-leash', 'local'], 'free',
              'outdoor', ['solo', 'family', 'friends'], ['morning', 'afternoon', 'evening']),
        place('blind-lady-ale-house', 'Blind Lady Ale House', 'restaurant', 'normal-heights', 'Neighborhood beer '
              'hall on Adams Avenue with wood-fired pizza and long shared tables.', ['pizza', 'craft-beer', 'local'],
              '$$', 'indoor', ALL, ['afternoon', 'evening'], cuisine='pizza'),
        place('lestats-adams', 'Lestat\'s Coffee House', 'cafe', 'normal-heights', 'Twenty-four-hour coffee house '
              'with an attached small venue for open mics and acoustic shows.', ['coffee', 'late-night', 'open-mic'],
              '$', 'indoor', ['solo', 'friends', 'date'], ['morning', 'afternoon', 'evening', 'late'],
              cuisine='cafe'),
        place('polite-provisions', 'Polite Provisions', 'bar', 'normal-heights', 'Apothecary-style cocktail bar at '
              'Adams and 30th, with a soda fountain look.', ['cocktails', 'date-night'], '$$', 'indoor',
              ['date', 'friends'], NIGHT),
        place('kensington-normal-heights-library', 'Kensington-Normal Heights Library', 'library', 'normal-heights',
              'Small neighborhood branch library on Adams Avenue.', ['books', 'quiet', 'kids'], 'free', 'indoor',
              ALL, DAY),
        place('kate-sessions-park', 'Kate Sessions Park', 'park', 'pacific-beach', 'Hilltop park with sweeping views '
              'over Mission Bay, popular for sunsets, kites and dogs.', ['views', 'sunset', 'dogs'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('pacific-beach-library', 'Pacific Beach/Taylor Branch Library', 'library', 'pacific-beach', 'Branch '
              'library on Grand Avenue with a reading garden.', ['books', 'quiet', 'kids'], 'free', 'indoor', ALL,
              DAY),
        place('konos-cafe', 'Kono\'s Cafe', 'restaurant', 'pacific-beach', 'Cheap, busy breakfast counter across '
              'from Crystal Pier with ocean views and breakfast burritos.', ['breakfast', 'cheap', 'views'], '$',
              'mixed', ALL, ['morning'], cuisine='american-breakfast'),
        place('the-mission-mission-beach', 'The Mission', 'restaurant', 'mission-beach', 'Laid-back breakfast spot '
              'on Mission Boulevard with Latin and Asian twists on brunch.', ['breakfast', 'brunch', 'local'], '$',
              'indoor', ALL, DAY, cuisine='californian'),
        place('mission-bay-aquatic-center', 'Mission Bay Aquatic Center', 'fitness', 'mission-beach', 'Public '
              'watersports center on the bay with kayak, paddleboard and sailing rentals and classes.',
              ['kayaking', 'paddleboard', 'sailing'], '$$', 'outdoor', ALL, DAY),
        place('la-jolla-library', 'La Jolla/Riford Library', 'library', 'la-jolla', 'Branch library in the village '
              'with a quiet reading garden and an art gallery.', ['books', 'quiet', 'art'], 'free', 'indoor', ALL,
              DAY),
        place('warwicks', 'Warwick\'s', 'shopping', 'la-jolla', 'Family-owned bookstore on Girard Avenue, among '
              'the oldest in the country, with frequent author events.', ['books', 'indie', 'events'], '$', 'indoor',
              ['solo', 'date', 'family'], ['morning', 'afternoon', 'evening']),
        place('rose-canyon', 'Rose Canyon Open Space', 'trail', 'university-city', 'Creek trail through a sycamore '
              'canyon under the trolley line, used by runners and dog walkers.', ['trail', 'running', 'dogs'],
              'free', 'outdoor', ['solo', 'friends', 'family'], DAY),
        place('university-community-library', 'University Community Library', 'library', 'university-city',
              'Branch library on Governor Drive serving families and students.', ['books', 'kids', 'study'], 'free',
              'indoor', ALL, DAY),
        place('doyle-community-park', 'Doyle Community Park', 'park', 'university-city', 'Park with a recreation '
              'center, fields and a playground beside the library.', ['playground', 'sports', 'rec-center'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('regents-pizzeria', 'Regents Pizzeria', 'restaurant', 'university-city', 'Neighborhood pizza and beer '
              'spot near UCSD, popular with students and families.', ['pizza', 'students', 'casual'], '$', 'indoor',
              ALL, ['afternoon', 'evening'], cuisine='pizza'),
        place('torrey-pines-golf', 'Torrey Pines Golf Course', 'fitness', 'sorrento-valley', 'Municipal clifftop '
              'golf course that hosts PGA Tour events and sells tee times to residents.', ['golf', 'views'], '$$$',
              'outdoor', ['solo', 'friends', 'coworkers'], DAY),
        place('penasquitos-canyon', 'Los Peñasquitos Canyon Preserve', 'trail', 'sorrento-valley', 'Canyon trail '
              'to a small waterfall, used by hikers, runners and mountain bikers.', ['hiking', 'waterfall',
              'mountain-biking'], 'free', 'outdoor', ['solo', 'friends', 'family'], DAY),
        place('torrey-pines-state-beach', 'Torrey Pines State Beach', 'beach', 'sorrento-valley', 'Long beach '
              'beneath sandstone cliffs, reached by a lot at the bottom of the reserve.', ['beach', 'cliffs',
              'walk'], '$', 'outdoor', ALL, DAY),
        place('karl-strauss-sorrento', 'Karl Strauss Brewing Company', 'restaurant', 'sorrento-valley', 'Brewery '
              'restaurant with a garden patio, a lunch and after-work spot for biotech workers.',
              ['brewery', 'after-work', 'patio'], '$$', 'mixed', ['coworkers', 'friends'], ['afternoon', 'evening'],
              cuisine='american-pub'),
        place('san-diego-river-trail', 'San Diego River Trail', 'trail', 'mission-valley', 'Paved path along the '
              'river through Mission Valley, used by commuters and runners.', ['running', 'cycling', 'river'],
              'free', 'outdoor', ['solo', 'friends'], ['morning', 'afternoon', 'evening']),
        place('mission-valley-library', 'Mission Valley Library', 'library', 'mission-valley', 'Large branch library '
              'by the river with study rooms and a big children\'s area.', ['books', 'study', 'kids'], 'free',
              'indoor', ALL, DAY),
        place('westfield-mission-valley', 'Westfield Mission Valley', 'shopping', 'mission-valley', 'Outdoor '
              'mall with discount stores, groceries and a cinema.', ['errands', 'mall'], '$$', 'outdoor', ALL,
              ['morning', 'afternoon', 'evening']),
        place('mission-san-diego', 'Mission Basilica San Diego de Alcalá', 'landmark', 'mission-valley', 'The first '
              'of the California missions, with gardens, a museum and an active parish.', ['history', 'church',
              'gardens'], '$', 'mixed', ['solo', 'family'], DAY),
        place('old-town-mexican-cafe', 'Old Town Mexican Café', 'restaurant', 'old-town', 'Busy Mexican restaurant '
              'where women make tortillas by hand in the front window.', ['mexican', 'margaritas', 'tortillas'],
              '$$', 'indoor', ALL, ['morning', 'afternoon', 'evening'], cuisine='mexican'),
        place('presidio-park', 'Presidio Park', 'park', 'old-town', 'Hilltop park above Old Town with lawns, '
              'trails and the Serra Museum on the site of the first Spanish fort.', ['history', 'views', 'picnic'],
              'free', 'outdoor', ALL, DAY),
        place('whaley-house', 'Whaley House', 'museum', 'old-town', '1857 brick house museum famous for its ghost '
              'stories and evening tours.', ['history', 'haunted'], '$', 'indoor', ['family', 'friends', 'date'],
              ['afternoon', 'evening']),
        place('cesar-chavez-park', 'Cesar Chavez Park', 'park', 'barrio-logan', 'Small waterfront park with a '
              'fishing pier looking across the bay at the shipyards and Coronado.', ['waterfront', 'fishing',
              'local'], 'free', 'outdoor', ALL, DAY),
        place('logan-heights-library', 'Logan Heights Branch Library', 'library', 'barrio-logan', 'Bilingual '
              'neighborhood library with homework help and murals.', ['books', 'bilingual', 'kids'], 'free',
              'indoor', ALL, DAY),
        place('salud-tacos', 'Salud!', 'restaurant', 'barrio-logan', 'Taco shop on Logan Avenue with lowrider '
              'culture on the walls and late hours on weekends.', ['tacos', 'local', 'late-night'], '$', 'mixed',
              ALL, ['afternoon', 'evening', 'late'], cuisine='mexican'),
        place('claytons-coffee-shop', 'Clayton\'s Coffee Shop', 'restaurant', 'coronado', 'Retro horseshoe-counter '
              'diner on Orange Avenue with jukeboxes at the stools.', ['diner', 'breakfast', 'retro'], '$', 'indoor',
              ALL, DAY, cuisine='american-diner'),
        place('coronado-library', 'Coronado Public Library', 'library', 'coronado', 'Handsome city library with a '
              'Spanish-style reading room by Spreckels Park.', ['books', 'quiet', 'historic'], 'free', 'indoor', ALL,
              DAY),
        place('spreckels-park', 'Spreckels Park', 'park', 'coronado', 'Town green with a playground, summer '
              'concerts and an art fair.', ['playground', 'concerts', 'local'], 'free', 'outdoor', ALL,
              ['morning', 'afternoon', 'evening']),
        place('coronado-ferry-landing', 'Coronado Ferry Landing', 'shopping', 'coronado', 'Bayside shops and '
              'restaurants where the ferry from downtown docks, with skyline views.', ['ferry', 'views', 'shops'],
              '$$', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('dumpling-inn', 'Dumpling Inn', 'restaurant', 'kearny-mesa', 'Small, long-running dumpling house in '
              'the Convoy district.', ['dumplings', 'chinese'], '$', 'indoor', ALL, ['afternoon', 'evening'],
              cuisine='chinese'),
        place('zion-market', 'Zion Market', 'market', 'kearny-mesa', 'Large Korean supermarket with a food court and '
              'banchan counter.', ['grocery', 'korean', 'food-court'], '$', 'indoor', ALL,
              ['morning', 'afternoon', 'evening'], cuisine='korean'),
        place('serra-mesa-kearny-mesa-library', 'Serra Mesa-Kearny Mesa Library', 'library', 'kearny-mesa', 'Branch '
              'library with study rooms and a children\'s area.', ['books', 'study', 'kids'], 'free', 'indoor', ALL,
              DAY),
        place('viejas-arena', 'Viejas Arena', 'venue', 'college-area', 'SDSU\'s arena for Aztecs basketball and '
              'touring concerts.', ['basketball', 'concerts', 'students'], '$$', 'indoor', ['friends', 'date'],
              ['evening']),
        place('sdsu-campus', 'San Diego State University campus', 'landmark', 'college-area', 'Mission Revival '
              'campus around Hepner Hall\'s bell tower, with a student union and free galleries.',
              ['campus', 'architecture', 'students'], 'free', 'outdoor', ALL, DAY),
        place('college-rolando-library', 'College-Rolando Library', 'library', 'college-area', 'Branch library on '
              'Montezuma Road used by students and neighbours.', ['books', 'study', 'quiet'], 'free', 'indoor', ALL,
              DAY),
        place('pal-joeys', 'Pal Joey\'s', 'bar', 'college-area', 'Old neighborhood dive bar with live bands, pool '
              'tables and cheap drinks.', ['dive-bar', 'live-music', 'pool-tables'], '$', 'indoor',
              ['friends', 'solo'], NIGHT),
        place('lake-murray', 'Lake Murray', 'trail', 'college-area', 'Reservoir with a paved shoreline path of '
              'about three miles, busy with walkers, runners and anglers.', ['running', 'walk', 'fishing'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('tecolote-canyon', 'Tecolote Canyon Natural Park', 'trail', 'linda-vista', 'Canyon park with a nature '
              'center and dirt trails running north from Mission Bay.', ['hiking', 'nature', 'dogs'], 'free',
              'outdoor', ['solo', 'friends', 'family'], DAY),
        place('linda-vista-library', 'Linda Vista Library', 'library', 'linda-vista', 'Branch library with '
              'collections in Vietnamese, Spanish and other languages.', ['books', 'multilingual', 'kids'], 'free',
              'indoor', ALL, DAY),
        place('usd-campus', 'University of San Diego campus', 'landmark', 'linda-vista', 'Spanish Renaissance-style '
              'campus on the mesa with the Immaculata church and bay views.', ['campus', 'architecture', 'views'],
              'free', 'outdoor', ['solo', 'date', 'family'], DAY),
        place('linda-vista-rec-center', 'Linda Vista Recreation Center', 'fitness', 'linda-vista', 'City recreation '
              'center with a gym, fields and youth sports leagues.', ['rec-center', 'sports', 'kids'], 'free',
              'mixed', ALL, ['afternoon', 'evening']),
        place('linda-vista-skate-park', 'Linda Vista Skate Park', 'park', 'linda-vista', 'Public concrete skate '
              'park with bowls and street features.', ['skate', 'teens'], 'free', 'outdoor', ['solo', 'friends'],
              ['afternoon', 'evening']),
    ],
    'colleges': [
        {'id': 'ucsd', 'name': 'University of California San Diego', 'type': 'research-university',
         'neighborhood': 'university-city', 'size': 'large', 'known_for': ['engineering', 'biology',
         'computer-science', 'medicine', 'oceanography', 'research'], 'source': S},
        {'id': 'ucsd-medicine', 'name': 'UC San Diego School of Medicine', 'type': 'medical-school',
         'neighborhood': 'university-city', 'size': 'medium', 'known_for': ['medicine', 'pharmacy',
         'biomedical-research'], 'source': S},
        {'id': 'scripps-oceanography', 'name': 'Scripps Institution of Oceanography', 'type': 'research-university',
         'neighborhood': 'la-jolla', 'size': 'small', 'known_for': ['oceanography', 'climate-science',
         'marine-biology'], 'source': S},
        {'id': 'sdsu', 'name': 'San Diego State University', 'type': 'public-university',
         'neighborhood': 'college-area', 'size': 'large', 'known_for': ['business', 'hospitality',
         'engineering', 'public-health', 'athletics'], 'source': S},
        {'id': 'usd', 'name': 'University of San Diego', 'type': 'private-university', 'neighborhood': 'linda-vista',
         'size': 'medium', 'known_for': ['business', 'law', 'nursing', 'peace-studies'], 'source': S},
        {'id': 'plnu', 'name': 'Point Loma Nazarene University', 'type': 'liberal-arts-college',
         'neighborhood': 'point-loma', 'size': 'small', 'known_for': ['nursing', 'education', 'liberal-arts'],
         'source': S},
        {'id': 'sd-city-college', 'name': 'San Diego City College', 'type': 'community-college',
         'neighborhood': 'east-village', 'size': 'medium', 'known_for': ['transfer', 'nursing', 'trades',
         'radio-and-tv'], 'source': S},
        {'id': 'sd-mesa-college', 'name': 'San Diego Mesa College', 'type': 'community-college',
         'neighborhood': 'kearny-mesa', 'size': 'large', 'known_for': ['transfer', 'health-sciences',
         'architecture'], 'source': S},
        {'id': 'cal-western', 'name': 'California Western School of Law', 'type': 'private-university',
         'neighborhood': 'downtown', 'size': 'small', 'known_for': ['law'], 'source': S},
        {'id': 'newschool', 'name': 'NewSchool of Architecture & Design', 'type': 'art-school',
         'neighborhood': 'east-village', 'size': 'small', 'known_for': ['architecture', 'interior-design',
         'game-design'], 'source': S},
    ],
    'employers': [
        {'id': 'naval-base-san-diego', 'name': 'Naval Base San Diego', 'sector': 'defense',
         'neighborhood': 'barrio-logan', 'size': 'large', 'summary': 'Principal homeport of the Pacific Fleet, '
         'with dozens of ships along the bay south of Barrio Logan.', 'careers': ['military-sailor',
         'port-logistics'], 'source': S},
        {'id': 'nas-north-island', 'name': 'Naval Air Station North Island', 'sector': 'defense',
         'neighborhood': 'coronado', 'size': 'large', 'summary': 'Naval aviation base on Coronado and homeport for '
         'aircraft carriers.', 'careers': ['military-sailor', 'defense-engineer'], 'source': S},
        {'id': 'naval-base-point-loma', 'name': 'Naval Base Point Loma', 'sector': 'defense',
         'neighborhood': 'point-loma', 'size': 'medium', 'summary': 'Submarine and fleet support base on the '
         'Point Loma peninsula.', 'careers': ['military-sailor'], 'source': S},
        {'id': 'mcas-miramar', 'name': 'Marine Corps Air Station Miramar', 'sector': 'defense',
         'neighborhood': 'kearny-mesa', 'size': 'large', 'summary': 'Marine Corps aviation base on the mesa north '
         'of Kearny Mesa.', 'careers': ['military-sailor'], 'source': S},
        {'id': 'niwc-pacific', 'name': 'Naval Information Warfare Center Pacific', 'sector': 'defense',
         'neighborhood': 'point-loma', 'size': 'large', 'summary': 'Navy research and engineering center with '
         'campuses on Point Loma and in Old Town.', 'careers': ['defense-engineer', 'software-engineer',
         'data-analyst'], 'source': S},
        {'id': 'nassco', 'name': 'General Dynamics NASSCO', 'sector': 'defense', 'neighborhood': 'barrio-logan',
         'size': 'large', 'summary': 'Shipyard building and repairing Navy and commercial ships on the bay.',
         'careers': ['construction-trades', 'defense-engineer', 'port-logistics'], 'source': S},
        {'id': 'general-atomics', 'name': 'General Atomics', 'sector': 'defense', 'neighborhood': 'sorrento-valley',
         'size': 'large', 'summary': 'Defense and energy research company headquartered on the Torrey Pines mesa.',
         'careers': ['defense-engineer', 'software-engineer', 'data-analyst'], 'source': S},
        {'id': 'qualcomm', 'name': 'Qualcomm', 'sector': 'technology', 'neighborhood': 'sorrento-valley',
         'size': 'large', 'summary': 'Wireless chip company headquartered in Sorrento Valley.',
         'careers': ['software-engineer', 'data-analyst', 'ux-designer', 'marketing-coordinator', 'accountant'],
         'source': S},
        {'id': 'illumina', 'name': 'Illumina', 'sector': 'biotech', 'neighborhood': 'university-city',
         'size': 'large', 'summary': 'Genetic sequencing company headquartered near UTC.',
         'careers': ['biotech-scientist', 'software-engineer', 'data-analyst', 'financial-analyst'], 'source': S},
        {'id': 'salk-institute', 'name': 'Salk Institute for Biological Studies', 'sector': 'biotech',
         'neighborhood': 'sorrento-valley', 'size': 'medium', 'summary': 'Research institute in Louis Kahn\'s '
         'concrete campus on the Torrey Pines cliffs.', 'careers': ['medical-researcher', 'biotech-scientist'],
         'source': S},
        {'id': 'scripps-research', 'name': 'Scripps Research', 'sector': 'biotech',
         'neighborhood': 'sorrento-valley', 'size': 'medium', 'summary': 'Biomedical research institute and '
         'graduate school on the Torrey Pines mesa.', 'careers': ['medical-researcher', 'biotech-scientist',
         'graduate-student'], 'source': S},
        {'id': 'ucsd-employer', 'name': 'UC San Diego', 'sector': 'education', 'neighborhood': 'university-city',
         'size': 'large', 'summary': 'The university is one of the region\'s largest employers.',
         'careers': ['professor', 'graduate-student', 'medical-researcher', 'data-analyst', 'software-engineer'],
         'source': S},
        {'id': 'ucsd-health', 'name': 'UC San Diego Health', 'sector': 'healthcare', 'neighborhood': 'hillcrest',
         'size': 'large', 'summary': 'Academic health system with hospitals in Hillcrest and La Jolla.',
         'careers': ['registered-nurse', 'night-nurse', 'physician-resident', 'pharmacist',
         'medical-researcher', 'social-worker'], 'source': S},
        {'id': 'scripps-mercy', 'name': 'Scripps Mercy Hospital', 'sector': 'healthcare', 'neighborhood': 'hillcrest',
         'size': 'large', 'summary': 'Scripps Health hospital and trauma center in Hillcrest.',
         'careers': ['registered-nurse', 'night-nurse', 'physician-resident', 'pharmacist'], 'source': S},
        {'id': 'sharp-memorial', 'name': 'Sharp Memorial Hospital', 'sector': 'healthcare',
         'neighborhood': 'kearny-mesa', 'size': 'large', 'summary': 'Flagship hospital of Sharp HealthCare in the '
         'Kearny Mesa medical cluster.', 'careers': ['registered-nurse', 'night-nurse', 'pharmacist',
         'social-worker'], 'source': S},
        {'id': 'rady-childrens', 'name': 'Rady Children\'s Hospital', 'sector': 'healthcare',
         'neighborhood': 'kearny-mesa', 'size': 'large', 'summary': 'The region\'s children\'s hospital.',
         'careers': ['registered-nurse', 'night-nurse', 'physician-resident', 'social-worker'], 'source': S},
        {'id': 'sempra', 'name': 'Sempra', 'sector': 'energy', 'neighborhood': 'east-village', 'size': 'large',
         'summary': 'Energy holding company, parent of SDG&E, headquartered downtown.',
         'careers': ['financial-analyst', 'accountant', 'data-analyst'], 'source': S},
        {'id': 'sd-unified', 'name': 'San Diego Unified School District', 'sector': 'education',
         'neighborhood': 'hillcrest', 'size': 'large', 'summary': 'The second-largest school district in '
         'California.', 'careers': ['teacher', 'social-worker'], 'source': S},
        {'id': 'city-of-san-diego', 'name': 'City of San Diego', 'sector': 'government', 'neighborhood': 'downtown',
         'size': 'large', 'summary': 'City departments around City Hall in the Civic Center.',
         'careers': ['government-analyst', 'accountant', 'social-worker'], 'source': S},
        {'id': 'county-of-san-diego', 'name': 'County of San Diego', 'sector': 'government',
         'neighborhood': 'downtown', 'size': 'large', 'summary': 'County agencies, courts and the District '
         'Attorney, centered on the County Administration Center.', 'careers': ['government-analyst',
         'social-worker', 'paralegal'], 'source': S},
        {'id': 'sd-lifeguards', 'name': 'San Diego Lifeguard Service', 'sector': 'recreation',
         'neighborhood': 'mission-beach', 'size': 'medium', 'summary': 'City Fire-Rescue lifeguards in towers on '
         'the beaches and boats on Mission Bay.', 'careers': ['lifeguard'], 'source': S},
        {'id': 'surf-diva', 'name': 'Surf Diva Surf School', 'sector': 'recreation', 'neighborhood': 'la-jolla',
         'size': 'small', 'summary': 'Long-running surf school giving lessons at La Jolla Shores.',
         'careers': ['surf-instructor'], 'source': S},
        {'id': 'seaworld', 'name': 'SeaWorld San Diego', 'sector': 'tourism', 'neighborhood': 'mission-beach',
         'size': 'large', 'summary': 'Marine theme park on Mission Bay.', 'careers': ['performer',
         'retail-associate', 'line-cook', 'tour-guide'], 'source': S},
        {'id': 'zoo-wildlife-alliance', 'name': 'San Diego Zoo Wildlife Alliance', 'sector': 'tourism',
         'neighborhood': 'bankers-hill', 'size': 'large', 'summary': 'Runs the San Diego Zoo in Balboa Park and '
         'the Safari Park.', 'careers': ['tour-guide', 'retail-associate', 'marketing-coordinator',
         'medical-researcher'], 'source': S},
        {'id': 'hotel-del-employer', 'name': 'Hotel del Coronado', 'sector': 'hospitality',
         'neighborhood': 'coronado', 'size': 'large', 'summary': 'Historic beach resort with conference and '
         'wedding business.', 'careers': ['hotel-front-desk', 'event-planner', 'server', 'bartender',
         'line-cook'], 'source': S},
        {'id': 'convention-center', 'name': 'San Diego Convention Center', 'sector': 'hospitality',
         'neighborhood': 'gaslamp', 'size': 'large', 'summary': 'Bayfront convention hall best known for '
         'Comic-Con.', 'careers': ['event-planner', 'line-cook', 'server'], 'source': S},
        {'id': 'padres', 'name': 'San Diego Padres', 'sector': 'sports', 'neighborhood': 'east-village',
         'size': 'medium', 'summary': 'The Major League Baseball team at Petco Park.',
         'careers': ['marketing-coordinator', 'data-analyst', 'event-planner'], 'source': S},
        {'id': 'san-diego-symphony', 'name': 'San Diego Symphony', 'sector': 'arts', 'neighborhood': 'downtown',
         'size': 'small', 'summary': 'Orchestra playing Jacobs Music Center indoors and The Rady Shell in summer.',
         'careers': ['musician', 'event-planner'], 'source': S},
        {'id': 'old-globe-employer', 'name': 'The Old Globe', 'sector': 'arts', 'neighborhood': 'bankers-hill',
         'size': 'small', 'summary': 'Regional theater in Balboa Park.', 'careers': ['actor', 'performer'],
         'source': S},
        {'id': 'kpbs', 'name': 'KPBS', 'sector': 'media', 'neighborhood': 'college-area', 'size': 'small',
         'summary': 'Public radio and television newsroom on the SDSU campus.', 'careers': ['journalist'],
         'source': S},
        {'id': 'sdsu-employer', 'name': 'San Diego State University', 'sector': 'education',
         'neighborhood': 'college-area', 'size': 'large', 'summary': 'A large public university campus.',
         'careers': ['professor', 'graduate-student'], 'source': S},
        {'id': 'port-of-san-diego', 'name': 'Port of San Diego', 'sector': 'logistics',
         'neighborhood': 'barrio-logan', 'size': 'medium', 'summary': 'Runs the Tenth Avenue Marine Terminal and '
         'the bay\'s tidelands.', 'careers': ['port-logistics', 'government-analyst'], 'source': S},
    ],
    'career_hubs': [
        {'id': 'downtown-core', 'name': 'Downtown offices', 'neighborhoods': ['downtown', 'east-village',
         'little-italy'], 'sectors': ['finance', 'legal', 'government', 'energy', 'business', 'real-estate',
         'creative', 'media'], 'summary': 'Law firms, banks, city and county government, Sempra and smaller '
         'agencies in the downtown towers.', 'source': S},
        {'id': 'gaslamp-hospitality', 'name': 'Gaslamp and convention hotels', 'neighborhoods': ['gaslamp',
         'downtown', 'east-village'], 'sectors': ['hospitality', 'tourism', 'entertainment', 'food'],
         'summary': 'Convention hotels, restaurants and bars around the Convention Center and Petco Park.',
         'source': S},
        {'id': 'golden-triangle', 'name': 'Torrey Pines mesa and UTC', 'neighborhoods': ['sorrento-valley',
         'university-city', 'la-jolla'], 'sectors': ['biotech', 'technology', 'healthcare', 'education',
         'defense'], 'summary': 'Biotech labs, research institutes, wireless and defense firms around UC San '
         'Diego.', 'source': S},
        {'id': 'san-diego-bay-military', 'name': 'San Diego Bay military and shipyards', 'neighborhoods': [
         'barrio-logan', 'coronado', 'point-loma'], 'sectors': ['defense', 'logistics', 'construction'],
         'summary': 'Navy bases, shipyards and marine terminals ringing San Diego Bay.', 'source': S},
        {'id': 'kearny-mesa-hub', 'name': 'Kearny Mesa', 'neighborhoods': ['kearny-mesa'],
         'sectors': ['healthcare', 'defense', 'technology', 'construction'], 'summary': 'Hospitals, office '
         'parks, defense contractors and MCAS Miramar.', 'source': S},
        {'id': 'mission-valley-hub', 'name': 'Mission Valley', 'neighborhoods': ['mission-valley', 'old-town'],
         'sectors': ['retail', 'real-estate', 'business', 'hospitality', 'finance'], 'summary': 'Malls, hotels '
         'and mid-rise offices along I-8.', 'source': S},
        {'id': 'beach-towns', 'name': 'Beach towns', 'neighborhoods': ['pacific-beach', 'mission-beach',
         'ocean-beach', 'la-jolla'], 'sectors': ['recreation', 'fitness', 'tourism', 'hospitality'],
         'summary': 'Gyms, surf shops, rentals, restaurants and bars serving beachgoers.', 'source': S},
    ],
    'climate': {
        'summary': 'Mild Mediterranean coastal climate: dry, sunny and warm most of the year, with short rainy '
                   'winters and a grey marine layer ("May Gray" and "June Gloom") in late spring.',
        'months': [
            {'high_f': 66, 'low_f': 49, 'rain_days': 7, 'note': 'Mild days, chilly nights; occasional storms.'},
            {'high_f': 66, 'low_f': 51, 'rain_days': 7, 'note': 'Wettest stretch of the year, still mostly sunny.'},
            {'high_f': 66, 'low_f': 53, 'rain_days': 7, 'note': 'Showers taper off; wildflowers inland.'},
            {'high_f': 68, 'low_f': 56, 'rain_days': 4, 'note': 'Pleasant; morning clouds start to return.'},
            {'high_f': 69, 'low_f': 59, 'rain_days': 2, 'note': 'May Gray: overcast mornings at the coast.'},
            {'high_f': 72, 'low_f': 62, 'rain_days': 1, 'note': 'June Gloom; sun often breaks through by afternoon.'},
            {'high_f': 76, 'low_f': 66, 'rain_days': 0, 'note': 'Warm and dry; beaches crowded.'},
            {'high_f': 78, 'low_f': 67, 'rain_days': 0, 'note': 'Warmest month; ocean at its warmest.'},
            {'high_f': 77, 'low_f': 66, 'rain_days': 1, 'note': 'Often hot; occasional Santa Ana heat waves.'},
            {'high_f': 74, 'low_f': 61, 'rain_days': 2, 'note': 'Clear and warm; dry Santa Ana winds possible.'},
            {'high_f': 70, 'low_f': 54, 'rain_days': 3, 'note': 'Sunny and mild; first rain of the season.'},
            {'high_f': 65, 'low_f': 49, 'rain_days': 6, 'note': 'Coolest days; winter storms arrive.'},
        ],
        'source': CLIMATE,
    },
    'annual_events': [
        {'id': 'padres-opening-day', 'name': 'Padres Opening Day', 'months': [3, 4], 'neighborhood': 'east-village',
         'summary': 'The baseball season opens at Petco Park and downtown fills with brown and gold.', 'source': S},
        {'id': 'crssd', 'name': 'CRSSD Festival', 'months': [3, 9], 'neighborhood': 'downtown',
         'summary': 'Electronic music festival at Waterfront Park, held in spring and autumn editions.',
         'source': S},
        {'id': 'chicano-park-day', 'name': 'Chicano Park Day', 'months': [4], 'neighborhood': 'barrio-logan',
         'summary': 'Celebration of the 1970 takeover that created Chicano Park, with music, dance and lowriders.',
         'source': S},
        {'id': 'rock-n-roll-marathon', 'name': 'Rock \'n\' Roll San Diego Marathon', 'months': [5, 6],
         'summary': 'Marathon and half marathon with bands along the course.', 'source': S},
        {'id': 'ob-street-fair', 'name': 'Ocean Beach Street Fair & Chili Cook-Off', 'months': [6],
         'neighborhood': 'ocean-beach', 'summary': 'Street fair on Newport Avenue with music stages and a chili '
         'contest.', 'source': S},
        {'id': 'san-diego-county-fair', 'name': 'San Diego County Fair', 'months': [6, 7], 'summary': 'Big '
         'summer fair with rides, livestock and fried food at the Del Mar Fairgrounds north of the city.',
         'source': S},
        {'id': 'comic-con', 'name': 'Comic-Con International', 'months': [7], 'neighborhood': 'gaslamp',
         'summary': 'The huge pop culture convention takes over the Convention Center and the Gaslamp.',
         'source': S},
        {'id': 'san-diego-pride', 'name': 'San Diego Pride', 'months': [7], 'neighborhood': 'hillcrest',
         'summary': 'Parade through Hillcrest and a festival in Balboa Park.', 'source': S},
        {'id': 'del-mar-racing', 'name': 'Del Mar summer racing season', 'months': [7, 8, 9],
         'summary': 'Thoroughbred racing at Del Mar, north of the city, opening with a famous hat-filled day.',
         'source': S},
        {'id': 'little-italy-festa', 'name': 'Little Italy Festa', 'months': [10], 'neighborhood': 'little-italy',
         'summary': 'Street festival with Italian food, music and chalk art.', 'source': S},
        {'id': 'fleet-week', 'name': 'Fleet Week San Diego', 'months': [10, 11], 'neighborhood': 'downtown',
         'summary': 'Weeks of events honouring the armed forces around the bay; dates vary by year.', 'source': S},
        {'id': 'december-nights', 'name': 'December Nights', 'months': [12], 'neighborhood': 'bankers-hill',
         'summary': 'Free holiday festival with lights, food and music across Balboa Park.', 'source': S},
        {'id': 'bay-parade-of-lights', 'name': 'San Diego Bay Parade of Lights', 'months': [12],
         'neighborhood': 'downtown', 'summary': 'Boats decorated with holiday lights parade around the bay.',
         'source': S},
        {'id': 'holiday-bowl', 'name': 'Holiday Bowl', 'months': [12], 'neighborhood': 'east-village',
         'summary': 'College football bowl game, now played at Petco Park.', 'source': S},
    ],
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
