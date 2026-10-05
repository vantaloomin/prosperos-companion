"""Curated Miami data. Run `python scripts/world/miami.py` to rewrite the shipped JSON."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'cities' / 'miami.json'
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
COOL = ['fall', 'winter', 'spring']

CITY = {
    'schema_version': 1, 'id': 'miami', 'name': 'Miami', 'region': 'Florida', 'country': 'US',
    'timezone': 'America/New_York', 'aliases': ['Magic City', 'Miami, FL', 'Miami-Dade', 'MIA'],
    'summary': 'A subtropical, majority-Hispanic metro on Biscayne Bay, known for its beaches, Cuban and '
               'Caribbean food, Art Deco Miami Beach, nightlife and a fast-growing finance scene.',
    'lat': 25.77, 'lon': -80.19,
    'speeds': {'walk': 4.5, 'car': 28, 'rideshare': 28, 'bus': 12, 'subway': 35, 'monorail': 15,
               'commuter-rail': 60, 'bike-share': 13},
    # Rough heritage weights for residents' names (estimates, not census figures).
    'names': {'mix': {'hispanic': 7, 'anglo': 1.2, 'black-american': 1, 'caribbean': 1.5, 'jewish': 0.4,
                       'italian': 0.2, 'east-asian': 0.2, 'south-asian': 0.2}},
    'sources': {
        S: {'kind': 'curated', 'title': 'Miami places and neighborhoods written for Prospero Companion',
            'license': 'CC0-1.0', 'retrieved': '2026-10-05',
            'note': 'Well-known public places, institutions and employers from general knowledge, covering the '
                    'City of Miami plus Miami Beach and nearby municipalities people treat as neighborhoods '
                    '(Coral Gables, Key Biscayne, Doral, Aventura, Miami Gardens). Businesses open and close and '
                    'rents move: treat this as a snapshot for fiction. Rents are rounded estimates of typical '
                    'asking ranges, not listings. Coordinates are approximate neighborhood centers.'},
        CLIMATE: {'kind': 'curated', 'title': 'Approximate monthly climate for Miami (Miami International '
                  'Airport area)', 'license': 'CC0-1.0', 'retrieved': '2026-10-05',
                  'note': 'Rounded values in line with NOAA 1991-2020 normals; refresh with scripts/world when '
                          'network access to NOAA is available. The wet season runs May to October and the '
                          'Atlantic hurricane season June to November.'},
    },
    'neighborhoods': [
        hood('brickell', 'Brickell', 'The financial district: a dense wall of glass condo and office towers along '
             'Brickell Avenue and the bay, with rooftop bars and Brickell City Center.',
             ['finance', 'high-rise', 'young-professional', 'nightlife'], 25.760, -80.193, 'very-high',
             ([2200, 2900], [2700, 3700], [3800, 5500]), ['apartment-tower', 'condo'], 'high',
             ['metrorail', 'metromover', 'metrobus', 'trolley', 'citi-bike']),
        hood('downtown', 'Downtown', 'Government buildings, the arena, Bayfront Park, museums on the bay and new '
             'towers, with MiamiCentral station for Brightline and Tri-Rail.', ['central', 'business', 'waterfront',
             'sports'], 25.775, -80.192, 'high', ([2000, 2700], [2500, 3400], [3400, 4800]),
             ['apartment-tower', 'condo'], 'high',
             ['metrorail', 'metromover', 'metrobus', 'brightline', 'tri-rail', 'trolley', 'citi-bike']),
        hood('edgewater', 'Edgewater', 'Bayfront condo towers north of downtown around Margaret Pace Park, '
             'between Biscayne Boulevard and the water.', ['waterfront', 'high-rise', 'dog-friendly'], 25.800,
             -80.188, 'very-high', ([2000, 2700], [2500, 3500], [3500, 5000]), ['apartment-tower', 'condo'],
             'medium', ['metromover', 'metrobus', 'trolley', 'citi-bike']),
        hood('wynwood', 'Wynwood', 'Former warehouse district covered in murals, now galleries, breweries, '
             'cafes, bars and new mid-rise apartments.', ['arts', 'murals', 'nightlife', 'trendy'], 25.801,
             -80.199, 'very-high', ([2100, 2800], [2600, 3500], [3600, 5000]), ['apartment', 'loft'], 'high',
             ['metrobus', 'trolley', 'citi-bike']),
        hood('midtown', 'Midtown', 'A planned cluster of mid-rise apartments and big-box shops between Wynwood '
             'and the Design District.', ['young-professional', 'shopping', 'new-build'], 25.808, -80.193, 'high',
             ([2000, 2600], [2400, 3200], [3300, 4500]), ['apartment', 'condo'], 'high',
             ['metrobus', 'trolley', 'citi-bike']),
        hood('design-district', 'Design District', 'Luxury fashion boutiques, public art, galleries and '
             'chef-driven restaurants in a few walkable blocks.', ['luxury', 'fashion', 'design', 'upscale'],
             25.813, -80.193, 'very-high', ([2200, 2800], [2600, 3500], [3600, 5000]), ['apartment', 'condo'],
             'high', ['metrobus', 'trolley']),
        hood('little-haiti', 'Little Haiti', 'The heart of Miami\'s Haitian community, with botanicas, Kreyol '
             'signage, a cultural complex and fast-rising rents.', ['haitian', 'cultural', 'changing',
             'affordable'], 25.830, -80.196, 'mid', ([1300, 1700], [1600, 2100], [2000, 2700]),
             ['apartment', 'single-family', 'duplex'], 'medium', ['metrobus', 'trolley']),
        hood('little-havana', 'Little Havana', 'The historic center of Cuban exile Miami along Calle Ocho, with '
             'cafecito windows, domino games, cigar shops and live salsa.', ['cuban', 'cultural', 'historic',
             'music'], 25.766, -80.217, 'mid', ([1300, 1700], [1600, 2100], [2000, 2700]),
             ['apartment', 'duplex', 'bungalow'], 'high', ['metrobus', 'trolley']),
        hood('overtown', 'Overtown', 'Historic Black neighborhood once called the Harlem of the South, now '
             'mixing public housing, churches and new development near downtown.', ['historic', 'black-history',
             'changing', 'affordable'], 25.785, -80.202, 'low', ([1200, 1700], [1500, 2100], [1900, 2700]),
             ['apartment', 'public-housing'], 'medium', ['metrorail', 'metrobus', 'trolley']),
        hood('allapattah', 'Allapattah', 'A working-class Dominican and Central American district of produce '
             'markets and garment shops, with new galleries arriving.', ['dominican', 'working-class', 'markets',
             'up-and-coming'], 25.810, -80.222, 'mid', ([1400, 1900], [1700, 2300], [2200, 3000]),
             ['apartment', 'single-family', 'duplex'], 'medium', ['metrorail', 'metrobus', 'trolley']),
        hood('health-district', 'Health District', 'The Civic Center medical campus around Jackson Memorial '
             'Hospital and the University of Miami Miller School of Medicine, beside the courthouse buildings.',
             ['medical', 'students', 'institutional'], 25.790, -80.212, 'mid', ([1600, 2100], [1900, 2600],
             [2500, 3400]), ['apartment', 'student-housing'], 'medium', ['metrorail', 'metrobus', 'trolley']),
        hood('coconut-grove', 'Coconut Grove', 'Miami\'s oldest neighborhood: leafy, bayside and bohemian-turned-'
             'affluent, with marinas, sailing clubs and a walkable village center.', ['leafy', 'waterfront',
             'affluent', 'village'], 25.728, -80.242, 'very-high', ([1900, 2500], [2500, 3400], [3300, 5000]),
             ['apartment', 'single-family', 'townhouse', 'condo'], 'medium', ['metrorail', 'metrobus', 'trolley']),
        hood('coral-gables', 'Coral Gables', 'A planned 1920s Mediterranean Revival city of banyan-lined streets, '
             'the Biltmore, Miracle Mile and the University of Miami.', ['affluent', 'leafy', 'historic',
             'corporate'], 25.721, -80.268, 'very-high', ([1800, 2300], [2200, 3000], [3000, 4300]),
             ['apartment', 'single-family', 'condo'], 'medium', ['metrorail', 'metrobus', 'trolley']),
        hood('key-biscayne', 'Key Biscayne', 'A quiet island village across the Rickenbacker Causeway with '
             'beaches, parks and a lighthouse.', ['island', 'beach', 'family', 'affluent', 'quiet'], 25.693,
             -80.163, 'very-high', ([2200, 2800], [2800, 3800], [4000, 6500]), ['condo', 'single-family'],
             'low', ['metrobus', 'car']),
        hood('south-beach', 'South Beach', 'The southern end of Miami Beach: Art Deco hotels, Ocean Drive, Lincoln '
             'Road, nightlife and a wide sandy beach.', ['beach', 'nightlife', 'art-deco', 'touristy',
             'lgbtq-friendly'], 25.783, -80.131, 'high', ([1700, 2300], [2200, 3000], [3000, 4500]),
             ['apartment', 'condo', 'art-deco-walkup'], 'high', ['metrobus', 'beach-trolley', 'citi-bike']),
        hood('mid-beach', 'Mid-Beach', 'Grand resort hotels like the Fontainebleau and Faena along Collins '
             'Avenue, with residential streets on Indian Creek behind them.', ['beach', 'resorts', 'upscale'],
             25.815, -80.123, 'high', ([1700, 2300], [2200, 3100], [3100, 4800]), ['condo', 'apartment',
             'single-family'], 'medium', ['metrobus', 'beach-trolley', 'citi-bike']),
        hood('north-beach', 'North Beach', 'A calmer, more local stretch of Miami Beach with MiMo-style low-rise '
             'apartments, reaching up toward Surfside and Bal Harbor.', ['beach', 'local', 'mimo', 'quiet'],
             25.858, -80.121, 'mid', ([1500, 1900], [1800, 2400], [2400, 3300]), ['apartment', 'condo'],
             'medium', ['metrobus', 'beach-trolley', 'citi-bike']),
        hood('doral', 'Doral', 'A city west of the airport of warehouses, corporate headquarters, TV studios, '
             'golf and a large Venezuelan community.', ['suburban', 'corporate', 'venezuelan', 'logistics'],
             25.819, -80.355, 'high', ([1800, 2200], [2100, 2700], [2700, 3500]), ['apartment', 'townhouse',
             'condo'], 'low', ['metrobus', 'trolley', 'car']),
        hood('kendall', 'Kendall', 'Sprawling southwestern suburbs of strip malls, cul-de-sacs and Dadeland '
             'Mall, at the end of the Metrorail line.', ['suburban', 'family', 'car-dependent'], 25.679, -80.317,
             'mid', ([1500, 1900], [1800, 2300], [2300, 3000]), ['apartment', 'single-family', 'townhouse'],
             'low', ['metrorail', 'metrobus', 'car']),
        hood('westchester', 'Westchester and University Park', 'Cuban-American suburban neighborhoods around '
             'Florida International University\'s main campus.', ['suburban', 'students', 'cuban'], 25.752,
             -80.355, 'mid', ([1400, 1800], [1700, 2200], [2200, 2900]), ['single-family', 'apartment',
             'student-housing'], 'low', ['metrobus', 'car']),
        hood('aventura', 'Aventura', 'A northern condo city built around Aventura Mall, with a Brightline '
             'station.', ['suburban', 'shopping', 'high-rise'], 25.956, -80.139, 'high',
             ([1800, 2300], [2200, 2900], [2800, 4000]), ['condo', 'apartment-tower'], 'low',
             ['brightline', 'metrobus', 'car']),
        hood('miami-gardens', 'Miami Gardens', 'A largely Black, largely residential city in the north of the '
             'county, home to Hard Rock Stadium.', ['residential', 'sports', 'family', 'affordable'], 25.942,
             -80.245, 'low', ([1300, 1700], [1600, 2000], [1900, 2500]), ['single-family', 'apartment'], 'low',
             ['metrobus', 'tri-rail', 'car']),
    ],
    'transit': [
        {'id': 'metrorail', 'name': 'Metrorail', 'kind': 'subway', 'summary': 'Elevated heavy-rail lines from '
         'Dadeland through Coconut Grove, Brickell, downtown and the Health District to the airport and '
         'Hialeah.', 'source': S},
        {'id': 'metromover', 'name': 'Metromover', 'kind': 'monorail', 'summary': 'A free automated people mover '
         'looping through downtown, Brickell and the Omni area.', 'source': S},
        {'id': 'metrobus', 'name': 'Metrobus', 'kind': 'bus', 'summary': 'The county bus network, including '
         'routes across the causeways to Miami Beach and Key Biscayne.', 'source': S},
        {'id': 'trolley', 'name': 'Free city trolleys', 'kind': 'bus', 'summary': 'Free trolley-style bus routes '
         'run by the City of Miami, Coral Gables and Doral.', 'source': S},
        {'id': 'beach-trolley', 'name': 'Miami Beach Trolley', 'kind': 'bus', 'summary': 'Free trolley loops '
         'through South Beach, Mid-Beach and North Beach.', 'source': S},
        {'id': 'brightline', 'name': 'Brightline', 'kind': 'commuter-rail', 'summary': 'Fast intercity trains '
         'from MiamiCentral via Aventura to Fort Lauderdale, West Palm Beach and Orlando.', 'source': S},
        {'id': 'tri-rail', 'name': 'Tri-Rail', 'kind': 'commuter-rail', 'summary': 'Regional commuter rail '
         'north to Broward and Palm Beach counties, serving the airport and MiamiCentral.', 'source': S},
        {'id': 'citi-bike', 'name': 'Citi Bike Miami', 'kind': 'bike-share', 'summary': 'Docked bike share in '
         'Miami and Miami Beach.', 'source': S},
        {'id': 'car', 'name': 'Driving', 'kind': 'car', 'summary': 'Most of the metro is built around the car; '
         'expect heavy traffic on I-95, the Palmetto and the causeways.', 'source': S},
    ],
    'places': [
        # Miami Beach
        place('south-beach-lummus', 'South Beach at Lummus Park', 'beach', 'south-beach', 'Wide sand beach with '
              'pastel lifeguard towers across from Ocean Drive.', ['beach', 'swimming', 'iconic', 'people-watching'],
              'free', 'outdoor', ALL, DAY),
        place('ocean-drive', 'Art Deco Historic District and Ocean Drive', 'landmark', 'south-beach', 'Pastel '
              'Art Deco hotels with neon signs and sidewalk cafes facing the beach.', ['architecture',
              'art-deco', 'walk', 'iconic'], 'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('south-pointe-park', 'South Pointe Park', 'park', 'south-beach', 'Park and pier at the tip of '
              'Miami Beach where cruise ships pass through Government Cut.', ['views', 'pier', 'sunset',
              'cruise-ships'], 'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('muscle-beach', 'Muscle Beach South Beach', 'fitness', 'south-beach', 'Free outdoor gym on the sand '
              'in Lummus Park.', ['workout', 'outdoor-gym', 'free'], 'free', 'outdoor', ['solo', 'friends'], DAY),
        place('lincoln-road', 'Lincoln Road', 'shopping', 'south-beach', 'Pedestrian mall of shops and outdoor '
              'restaurants designed by Morris Lapidus.', ['shopping', 'walk', 'people-watching'], '$$', 'outdoor',
              ALL, ['afternoon', 'evening']),
        place('lincoln-road-farmers-market', 'Lincoln Road Farmers Market', 'market', 'south-beach', 'Sunday '
              'market of produce, bread and prepared food on Lincoln Road.', ['farmers-market', 'sunday', 'food'],
              '$', 'outdoor', ALL, ['morning'], COOL),
        place('the-bass', 'The Bass', 'museum', 'south-beach', 'Contemporary art museum in a 1930s Art Deco '
              'building in Collins Park.', ['art', 'contemporary', 'rainy-day'], '$$', 'indoor', ADULT,
              ['afternoon']),
        place('wolfsonian', 'The Wolfsonian-FIU', 'museum', 'south-beach', 'Museum of design and propaganda art '
              'from 1850 to 1950.', ['design', 'history', 'rainy-day'], '$$', 'indoor', ['solo', 'date'],
              ['afternoon']),
        place('new-world-center', 'New World Center', 'venue', 'south-beach', 'Frank Gehry-designed concert hall '
              'of the New World Symphony, with free outdoor wallcasts in SoundScape Park.', ['classical',
              'concerts', 'architecture'], '$$', 'mixed', ['date', 'solo', 'family'], ['evening']),
        place('fillmore-miami-beach', 'The Fillmore Miami Beach', 'venue', 'south-beach', 'Concert and comedy '
              'theater in the former Jackie Gleason Theater.', ['concerts', 'comedy'], '$$$', 'indoor',
              ['friends', 'date'], NIGHT),
        place('joes-stone-crab', 'Joe\'s Stone Crab', 'restaurant', 'south-beach', 'Century-old institution for '
              'stone crab claws with mustard sauce and key lime pie; stone crab season runs mid-October to May.',
              ['stone-crab', 'historic', 'key-lime-pie'], '$$$$', 'indoor', ['date', 'family', 'friends'], DINNER,
              COOL, cuisine='seafood'),
        place('la-sandwicherie', 'La Sandwicherie', 'restaurant', 'south-beach', 'Late-night French sandwich '
              'counter with stools on the sidewalk.', ['sandwiches', 'late-night', 'cheap-eats'], '$', 'outdoor',
              ADULT, ['afternoon', 'evening', 'late'], cuisine='french-sandwich'),
        place('puerto-sagua', 'Puerto Sagua', 'restaurant', 'south-beach', 'Old-school Cuban diner on Collins '
              'Avenue serving ropa vieja and cafe con leche.', ['cuban', 'diner', 'old-school'], '$$', 'indoor',
              ALL, ['morning', 'afternoon', 'evening'], cuisine='cuban'),
        place('mangos', 'Mango\'s Tropical Cafe', 'nightlife', 'south-beach', 'Loud Ocean Drive party bar with '
              'Latin music and dancers on the bar.', ['salsa', 'party', 'touristy'], '$$$', 'indoor', ['friends'],
              NIGHT),
        place('fontainebleau', 'Fontainebleau Miami Beach', 'landmark', 'mid-beach', 'Morris Lapidus\'s curving '
              '1954 resort hotel, still the biggest name on Collins Avenue.', ['architecture', 'resort', 'pool',
              'iconic'], '$$$$', 'mixed', ADULT, ['afternoon', 'evening']),
        place('liv', 'LIV', 'nightlife', 'mid-beach', 'Celebrity-heavy nightclub inside the Fontainebleau.',
              ['club', 'dj', 'bottle-service'], '$$$$', 'indoor', ['friends'], ['late']),
        place('miami-beach-boardwalk', 'Miami Beach Boardwalk', 'trail', 'mid-beach', 'Beachwalk and boardwalk '
              'running behind the dunes for miles along the shore.', ['running', 'cycling', 'walk', 'ocean'],
              'free', 'outdoor', ALL, ['morning', 'evening']),
        place('north-beach-oceanside', 'North Beach Oceanside Park', 'beach', 'north-beach', 'Quieter local beach '
              'and park with shade trees and picnic areas.', ['beach', 'quiet', 'picnic'], 'free', 'outdoor',
              ALL, DAY),
        place('bal-harbour-shops', 'Bal Harbor Shops', 'shopping', 'north-beach', 'Open-air luxury mall in the '
              'village of Bal Harbor, just north of North Beach.', ['luxury', 'fashion', 'mall'], '$$$$', 'outdoor',
              ['solo', 'date', 'friends'], ['afternoon']),
        # Downtown, Brickell and the bay
        place('pamm', 'Pérez Art Museum Miami', 'museum', 'downtown', 'Modern and contemporary art museum on the '
              'bay with hanging gardens on its veranda.', ['art', 'bay-views', 'rainy-day'], '$$', 'mixed', ALL,
              DAY),
        place('frost-science', 'Phillip and Patricia Frost Museum of Science', 'museum', 'downtown', 'Science '
              'museum with a planetarium and a multi-level aquarium.', ['science', 'aquarium', 'kids',
              'rainy-day'], '$$$', 'indoor', ALL, DAY),
        place('maurice-ferre-park', 'Maurice A. Ferré Park', 'park', 'downtown', 'Large bayfront lawn between the '
              'two museums, used for festivals and dog walks.', ['bay-views', 'lawn', 'dogs'], 'free', 'outdoor',
              ALL, ['morning', 'afternoon', 'evening']),
        place('bayfront-park', 'Bayfront Park', 'park', 'downtown', 'Downtown park on Biscayne Bay with an '
              'amphitheatre and the Ultra festival grounds.', ['bay-views', 'concerts', 'walk'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('freedom-tower', 'Freedom Tower', 'landmark', 'downtown', 'Mediterranean Revival tower where Cuban '
              'refugees were processed in the 1960s, now a Miami Dade College museum.', ['history', 'cuban',
              'architecture'], 'free', 'mixed', ALL, ['afternoon']),
        place('historymiami', 'HistoryMiami Museum', 'museum', 'downtown', 'Museum of South Florida history at '
              'the Cultural Plaza on Flagler Street.', ['history', 'rainy-day'], '$', 'indoor', ALL, DAY),
        place('main-library', 'Miami-Dade Main Library', 'library', 'downtown', 'Central public library at the '
              'Cultural Plaza.', ['books', 'quiet', 'free'], 'free', 'indoor', ['solo', 'family'], DAY),
        place('bayside', 'Bayside Marketplace', 'shopping', 'downtown', 'Waterfront mall of souvenir shops, '
              'bars and boat tours beside the marina.', ['touristy', 'boat-tours', 'live-music'], '$$', 'outdoor',
              ALL, ['afternoon', 'evening']),
        place('kaseya-center', 'Kaseya Center', 'stadium', 'downtown', 'Bayfront arena of the Miami Heat and big '
              'touring concerts.', ['basketball', 'concerts', 'sports'], '$$$', 'indoor', ['friends', 'family',
              'date'], ['evening'], ['fall', 'winter', 'spring']),
        place('arsht-center', 'Adrienne Arsht Center for the Performing Arts', 'venue', 'downtown', 'The main '
              'performing arts center, hosting touring Broadway, opera, ballet and the Florida Grand Opera.',
              ['theater', 'broadway', 'opera', 'ballet'], '$$$', 'indoor', ['date', 'family', 'solo'],
              ['evening']),
        place('club-space', 'Club Space', 'nightlife', 'downtown', 'Electronic music club famous for its '
              'rooftop terrace and parties running past sunrise.', ['club', 'techno', 'after-hours'], '$$$',
              'mixed', ['friends'], ['late']),
        place('garcias', 'Garcia\'s Seafood Grille & Fish Market', 'restaurant', 'downtown', 'Family-run fish '
              'market and restaurant on the Miami River.', ['seafood', 'river', 'casual'], '$$', 'mixed', ALL,
              ['afternoon', 'evening'], cuisine='seafood'),
        place('brickell-city-centre', 'Brickell City Center', 'shopping', 'brickell', 'Multi-level open-air mall '
              'with a food hall, cinema and offices.', ['mall', 'shopping', 'food-hall'], '$$$', 'mixed', ALL,
              ['afternoon', 'evening']),
        place('the-underline', 'The Underline', 'trail', 'brickell', 'Linear park and path under the Metrorail '
              'tracks, starting at the Miami River.', ['running', 'cycling', 'walk'], 'free', 'outdoor', ALL,
              ['morning', 'evening']),
        place('margaret-pace-park', 'Margaret Pace Park', 'park', 'edgewater', 'Bayfront park with volleyball, '
              'tennis and a dog park below condo towers.', ['bay-views', 'dogs', 'volleyball'], 'free', 'outdoor',
              ALL, ['morning', 'evening']),
        place('enriquetas', 'Enriqueta\'s Sandwich Shop', 'restaurant', 'edgewater', 'Cuban lunch counter known '
              'for its Cuban sandwiches and cafecito.', ['cuban', 'lunch-counter', 'cafecito'], '$', 'indoor', ALL,
              ['morning', 'afternoon'], cuisine='cuban'),
        # Wynwood, Midtown, Design District, Little Haiti, Allapattah
        place('wynwood-walls', 'Wynwood Walls', 'attraction', 'wynwood', 'Outdoor museum of large murals by '
              'street artists from around the world.', ['murals', 'art', 'photos', 'iconic'], '$$', 'outdoor', ALL,
              DAY),
        place('zak-the-baker', 'Zak the Baker', 'cafe', 'wynwood', 'Kosher bakery-cafe known for sourdough and '
              'pastries.', ['bakery', 'bread', 'breakfast'], '$$', 'indoor', ALL, ['morning', 'afternoon'],
              cuisine='bakery'),
        place('panther-coffee', 'Panther Coffee', 'cafe', 'wynwood', 'Local specialty roaster with its original '
              'cafe in Wynwood.', ['coffee', 'laptop-friendly'], '$', 'indoor', ['solo', 'friends', 'date'],
              ['morning', 'afternoon'], cuisine='coffee'),
        place('gramps', 'Gramps', 'bar', 'wynwood', 'Neighborhood bar with a big back patio, drag brunch and '
              'live music.', ['bar', 'patio', 'live-music', 'drag'], '$$', 'mixed', ['friends', 'solo'], NIGHT),
        place('lagniappe', 'Lagniappe', 'bar', 'midtown', 'Wine bar with a candle-lit backyard and live jazz most '
              'nights.', ['wine', 'jazz', 'backyard'], '$$', 'mixed', ['date', 'friends'], NIGHT),
        place('ica-miami', 'Institute of Contemporary Art, Miami', 'museum', 'design-district', 'Free '
              'contemporary art museum with a sculpture garden.', ['art', 'free', 'contemporary'], 'free', 'mixed',
              ADULT, ['afternoon']),
        place('design-district-shops', 'Miami Design District shops', 'shopping', 'design-district', 'Luxury '
              'flagships, public art and architecture across a few walkable blocks.', ['luxury', 'fashion',
              'public-art'], '$$$$', 'outdoor', ['solo', 'date', 'friends'], ['afternoon']),
        place('mandolin', 'Mandolin Aegean Bistro', 'restaurant', 'design-district', 'Greek and Turkish food in '
              'a garden courtyard with blue-and-white decor.', ['garden', 'mediterranean', 'patio'], '$$$',
              'outdoor', ['date', 'friends'], ['afternoon', 'evening'], cuisine='greek-turkish'),
        place('michaels-genuine', 'Michael\'s Genuine Food & Drink', 'restaurant', 'design-district',
              'Long-running farm-to-table restaurant that helped build the district\'s dining scene.',
              ['farm-to-table', 'brunch'], '$$$', 'mixed', ['date', 'friends'], ['afternoon', 'evening'],
              cuisine='american'),
        place('boia-de', 'Boia De', 'restaurant', 'little-haiti', 'Small Italian restaurant in a strip mall with '
              'a Michelin star and hard-to-get reservations.', ['italian', 'michelin', 'reservations'], '$$$',
              'indoor', ['date', 'friends'], DINNER, cuisine='italian'),
        place('little-haiti-cultural-complex', 'Little Haiti Cultural Complex', 'venue', 'little-haiti', 'Arts '
              'center with a gallery, theater and the monthly Sounds of Little Haiti music night.',
              ['haitian', 'music', 'art', 'community'], 'free', 'mixed', ALL, ['afternoon', 'evening']),
        place('rubell-museum', 'Rubell Museum', 'museum', 'allapattah', 'Private contemporary art collection in '
              'converted industrial buildings.', ['art', 'contemporary', 'rainy-day'], '$$', 'indoor', ADULT,
              ['afternoon']),
        # Little Havana
        place('calle-ocho', 'Calle Ocho', 'landmark', 'little-havana', 'SW 8th Street\'s strip of cafecito '
              'windows, cigar rollers, murals and the Walk of Fame stars.', ['cuban', 'walk', 'iconic', 'cigars'],
              'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('domino-park', 'Domino Park', 'park', 'little-havana', 'Máximo Gómez Park, where older men play '
              'dominoes all day under the awning.', ['dominoes', 'cuban', 'people-watching'], 'free', 'outdoor',
              ALL, DAY),
        place('ball-and-chain', 'Ball & Chain', 'bar', 'little-havana', 'Historic Calle Ocho bar with live salsa '
              'on a pineapple-shaped stage.', ['salsa', 'live-music', 'dancing', 'historic'], '$$', 'mixed',
              ['friends', 'date'], NIGHT),
        place('versailles', 'Versailles', 'restaurant', 'little-havana', 'The famous Cuban restaurant and '
              'ventanita on Calle Ocho, a gathering place for exile politics.', ['cuban', 'cafecito', 'iconic',
              'late-night'], '$$', 'indoor', ALL, ['morning', 'afternoon', 'evening', 'late'], cuisine='cuban'),
        place('cafe-la-trova', 'Café La Trova', 'bar', 'little-havana', 'Cuban cocktail bar with live trova '
              'music and bartenders in white jackets.', ['cocktails', 'live-music', 'cuban'], '$$$', 'indoor',
              ['date', 'friends'], NIGHT, cuisine='cuban'),
        place('sanguich', 'Sanguich de Miami', 'restaurant', 'little-havana', 'Small shop making Cuban '
              'sandwiches with house-cured meats.', ['sandwiches', 'cuban'], '$', 'indoor', ALL,
              ['morning', 'afternoon'], cuisine='cuban'),
        place('azucar', 'Azucar Ice Cream Company', 'cafe', 'little-havana', 'Ice cream shop with Cuban flavours '
              'like Abuela Maria.', ['ice-cream', 'dessert', 'cuban'], '$', 'indoor', ALL,
              ['afternoon', 'evening'], cuisine='ice-cream'),
        place('la-camaronera', 'La Camaronera', 'restaurant', 'little-havana', 'Fish market turned seafood '
              'counter known for its fried pan con minuta.', ['seafood', 'fried-fish', 'casual'], '$$', 'indoor',
              ALL, ['afternoon', 'evening'], cuisine='cuban-seafood'),
        place('loandepot-park', 'loanDepot park', 'stadium', 'little-havana', 'The Marlins\' retractable-roof '
              'ballpark on the old Orange Bowl site.', ['baseball', 'sports'], '$$', 'indoor', ALL,
              ['afternoon', 'evening'], ['spring', 'summer', 'fall']),
        # Coconut Grove, Coral Gables, Key Biscayne
        place('vizcaya', 'Vizcaya Museum and Gardens', 'museum', 'coconut-grove', 'Italian Renaissance-style '
              'villa from 1916 with formal gardens on Biscayne Bay.', ['history', 'gardens', 'architecture',
              'photos'], '$$$', 'mixed', ALL, DAY),
        place('peacock-park', 'Peacock Park', 'park', 'coconut-grove', 'Bayfront lawn in the Grove village '
              'with sailboats moored offshore.', ['bay-views', 'picnic', 'dogs'], 'free', 'outdoor', ALL,
              ['morning', 'afternoon', 'evening']),
        place('cocowalk', 'CocoWalk', 'shopping', 'coconut-grove', 'Open-air shopping and dining center in the '
              'heart of Coconut Grove.', ['shopping', 'restaurants'], '$$', 'outdoor', ALL,
              ['afternoon', 'evening']),
        place('venetian-pool', 'Venetian Pool', 'attraction', 'coral-gables', 'Spring-fed public pool built in a '
              'former coral rock quarry, with grottoes and waterfalls.', ['swimming', 'historic', 'kids'], '$$',
              'outdoor', ALL, DAY, ['spring', 'summer', 'fall']),
        place('biltmore', 'The Biltmore Hotel', 'landmark', 'coral-gables', '1926 Mediterranean Revival hotel '
              'with a huge pool and a tower modelled on the Giralda.', ['architecture', 'historic', 'brunch'],
              '$$$', 'mixed', ['date', 'family'], ['morning', 'afternoon']),
        place('fairchild', 'Fairchild Tropical Botanic Garden', 'park', 'coral-gables', 'Large botanic garden of '
              'palms, cycads and rainforest plants, with a butterfly conservatory.', ['garden', 'nature',
              'butterflies'], '$$$', 'outdoor', ALL, DAY, COOL),
        place('matheson-hammock', 'Matheson Hammock Park', 'beach', 'coral-gables', 'County park with a calm '
              'tidal atoll pool beside the bay, popular with families.', ['swimming', 'kids', 'calm-water'], '$',
              'outdoor', ['family', 'friends'], DAY),
        place('miracle-mile', 'Miracle Mile', 'shopping', 'coral-gables', 'Downtown Coral Gables shopping street '
              'with restaurants and the Actors\' Playhouse.', ['shopping', 'walk', 'restaurants'], '$$', 'outdoor',
              ALL, ['afternoon', 'evening']),
        place('books-and-books', 'Books & Books', 'shopping', 'coral-gables', 'Independent bookstore in a '
              'Mediterranean-style building with a courtyard cafe and author talks.', ['books', 'author-events',
              'rainy-day'], '$', 'indoor', ['solo', 'date', 'family'], ['afternoon', 'evening']),
        place('lowe-art-museum', 'Lowe Art Museum', 'museum', 'coral-gables', 'The University of Miami\'s art '
              'museum.', ['art', 'campus', 'rainy-day'], '$', 'indoor', ['solo', 'date'], ['afternoon']),
        place('crandon-park', 'Crandon Park Beach', 'beach', 'key-biscayne', 'Long, calm family beach with '
              'shallow water sheltered by a sandbar.', ['beach', 'swimming', 'kids', 'picnic'], '$', 'outdoor',
              ALL, DAY),
        place('bill-baggs', 'Bill Baggs Cape Florida State Park', 'beach', 'key-biscayne', 'State park at the '
              'tip of Key Biscayne with a beach, bike paths and the 1825 Cape Florida Lighthouse.', ['beach',
              'lighthouse', 'state-park', 'cycling'], '$', 'outdoor', ALL, DAY),
        place('rickenbacker-causeway', 'Rickenbacker Causeway', 'trail', 'key-biscayne', 'The causeway to Key '
              'Biscayne, the city\'s favorite road-cycling and running route with skyline views.', ['cycling',
              'running', 'views'], 'free', 'outdoor', ['solo', 'friends'], ['morning']),
        # Suburbs and stadiums
        place('el-arepazo', 'El Arepazo', 'restaurant', 'doral', 'Busy Venezuelan restaurant serving arepas and '
              'cachapas late into the night.', ['venezuelan', 'arepas', 'late-night'], '$', 'indoor', ALL,
              ['afternoon', 'evening', 'late'], cuisine='venezuelan'),
        place('dolphin-mall', 'Dolphin Mall', 'shopping', 'doral', 'Big outlet mall west of the airport near '
              'Doral.', ['mall', 'outlets', 'rainy-day'], '$$', 'indoor', ALL, ['afternoon', 'evening']),
        place('dadeland-mall', 'Dadeland Mall', 'shopping', 'kendall', 'Large indoor mall beside the Dadeland '
              'Metrorail stations.', ['mall', 'rainy-day'], '$$', 'indoor', ALL, ['afternoon', 'evening']),
        place('shortys-bbq', 'Shorty\'s Bar-B-Q', 'restaurant', 'kendall', 'Barbecue joint on South Dixie Highway '
              'serving ribs since 1951.', ['bbq', 'ribs', 'old-school'], '$$', 'indoor', ALL,
              ['afternoon', 'evening'], cuisine='barbecue'),
        place('zoo-miami', 'Zoo Miami', 'attraction', 'kendall', 'Large open-air zoo south of Kendall, grouped by '
              'continent.', ['animals', 'kids'], '$$$', 'outdoor', ['family', 'date'], DAY, COOL),
        place('aventura-mall', 'Aventura Mall', 'shopping', 'aventura', 'One of the largest malls in the country, '
              'with a giant slide among its art pieces.', ['mall', 'luxury', 'rainy-day'], '$$$', 'indoor', ALL,
              ['afternoon', 'evening']),
        place('hard-rock-stadium', 'Hard Rock Stadium', 'stadium', 'miami-gardens', 'Home of the Dolphins and '
              'the Hurricanes, and host of the Miami Open, the Orange Bowl and the Formula 1 race.', ['football',
              'tennis', 'f1', 'tailgate'], '$$$', 'outdoor', ['friends', 'family'], ['afternoon', 'evening']),
        # Everyday neighborhood spots: cafes, diners, pubs, libraries, parks and markets.
        place('simpson-park', 'Simpson Park', 'park', 'brickell', 'Shady tropical hardwood hammock with a short '
              'nature trail, a quiet escape a few blocks from the towers.', ['nature', 'shade', 'quiet'], 'free',
              'outdoor', ['solo', 'family', 'date'], DAY),
        place('brickell-key-loop', 'Brickell Key loop', 'trail', 'brickell', 'Flat waterfront path around the '
              'island of Brickell Key, the neighborhood\'s jogging and dog-walking circuit.',
              ['running', 'waterfront', 'dogs'], 'free', 'outdoor', ALL, ['morning', 'evening']),
        place('perricones', 'Perricone\'s Marketplace & Cafe', 'restaurant', 'brickell', 'Italian restaurant and '
              'market in an old Vermont barn under the trees, known for its Sunday brunch.',
              ['italian', 'brunch', 'garden'], '$$', 'mixed', ALL, ['morning', 'afternoon', 'evening'],
              cuisine='italian'),
        place('blackbird-ordinary', 'Blackbird Ordinary', 'bar', 'brickell', 'Cocktail bar with a back patio, the '
              'neighborhood\'s after-work and late-night standby.', ['cocktails', 'patio', 'after-work'], '$$',
              'mixed', ['friends', 'coworkers', 'date'], NIGHT),
        place('venetian-causeway', 'Venetian Causeway', 'trail', 'edgewater', 'Low causeway of drawbridges and '
              'little islands from the mainland to Miami Beach, popular with runners and cyclists.',
              ['running', 'cycling', 'views'], 'free', 'outdoor', ['solo', 'friends', 'date'],
              ['morning', 'evening']),
        place('blue-collar', 'Blue Collar', 'restaurant', 'edgewater', 'Small diner-style restaurant in the MiMo '
              'district up Biscayne Boulevard with braises, burgers and a veggie board.', ['comfort-food',
              'brunch', 'local'], '$$', 'indoor', ALL, ['morning', 'afternoon', 'evening'], cuisine='american'),
        place('jimmys-eastside-diner', 'Jimmy\'s Eastside Diner', 'restaurant', 'edgewater', 'Old-fashioned '
              'breakfast diner on Biscayne Boulevard with a loyal neighborhood and LGBTQ+ crowd.',
              ['diner', 'breakfast', 'cheap'], '$', 'indoor', ALL, DAY, cuisine='american-diner'),
        place('wynwood-brewing', 'Wynwood Brewing Company', 'bar', 'wynwood', 'The neighborhood\'s first craft '
              'brewery, with a taproom and food trucks outside.', ['brewery', 'beer', 'food-trucks'], '$$', 'mixed',
              ['friends', 'date'], ['afternoon', 'evening']),
        place('coyo-taco', 'Coyo Taco', 'restaurant', 'wynwood', 'Taqueria with a speakeasy bar out back that '
              'stays busy late into the night.', ['tacos', 'late-night'], '$', 'indoor', ['friends', 'date', 'solo'],
              ['afternoon', 'evening', 'late'], cuisine='mexican'),
        place('shops-at-midtown', 'The Shops at Midtown Miami', 'shopping', 'midtown', 'Open-air big-box center '
              'with Target and other errand stores.', ['errands', 'groceries'], '$$', 'outdoor', ALL,
              ['morning', 'afternoon', 'evening']),
        place('sugarcane', 'Sugarcane Raw Bar Grill', 'restaurant', 'midtown', 'Busy small-plates restaurant with '
              'a raw bar, robata grill and weekend brunch.', ['small-plates', 'brunch', 'cocktails'], '$$$',
              'mixed', ['date', 'friends'], ['afternoon', 'evening'], cuisine='latin-asian'),
        place('buena-vista-deli', 'Buena Vista Deli', 'cafe', 'midtown', 'French bakery-cafe in Buena Vista with '
              'croissants, quiche and sidewalk tables.', ['bakery', 'coffee', 'french'], '$', 'mixed', ALL,
              ['morning', 'afternoon', 'evening'], cuisine='french-bakery'),
        place('roberto-clemente-park', 'Roberto Clemente Park', 'park', 'midtown', 'City park with ball fields, '
              'basketball courts and a playground just west of Midtown.', ['sports', 'playground', 'local'],
              'free', 'outdoor', ALL, ['afternoon', 'evening']),
        place('flys-eye-dome', 'Fly\'s Eye Dome', 'landmark', 'design-district', 'Buckminster Fuller\'s geodesic '
              'dome in Palm Court, the district\'s free-to-wander public art center.', ['art', 'architecture',
              'free'], 'free', 'outdoor', ['solo', 'date', 'friends'], ['afternoon', 'evening']),
        place('libreri-mapou', 'Libreri Mapou', 'shopping', 'little-haiti', 'Haitian bookstore with books in '
              'Kreyol, French and English and occasional readings and drumming.', ['books', 'haitian', 'culture'],
              '$', 'indoor', ['solo', 'friends', 'family'], DAY),
        place('little-haiti-soccer-park', 'Little Haiti Soccer Park', 'park', 'little-haiti', 'Community park with '
              'lit soccer fields, a running track and a playground.', ['soccer', 'running', 'playground'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('churchills-pub', 'Churchill\'s Pub', 'venue', 'little-haiti', 'Long-running dive and punk club with '
              'noise, rock and jazz nights.', ['live-music', 'punk', 'dive-bar'], '$', 'indoor', ['friends', 'solo'],
              NIGHT),
        place('chez-le-bebe', 'Chez Le Bebe', 'restaurant', 'little-haiti', 'Family Haitian restaurant serving '
              'griot, stewed goat and rice and beans.', ['haitian', 'cheap', 'local'], '$', 'indoor', ALL,
              ['afternoon', 'evening'], cuisine='haitian'),
        place('lemon-city-library', 'Lemon City Branch Library', 'library', 'little-haiti', 'Miami-Dade branch '
              'library with Haitian Creole collections and kids\' programs.', ['books', 'haitian', 'kids'], 'free',
              'indoor', ALL, DAY),
        place('lyric-theater-overtown', 'Historic Lyric Theater', 'venue', 'overtown', 'Restored 1913 theater run by '
              'the Black Archives, once the center of Overtown\'s "Little Broadway".', ['history', 'theater',
              'black-history'], '$$', 'indoor', ALL, ['evening']),
        place('jackson-soul-food', 'Jackson Soul Food', 'restaurant', 'overtown', 'Family-run breakfast and soul '
              'food spot on Northwest 3rd Avenue since the 1940s.', ['soul-food', 'breakfast', 'historic'], '$',
              'indoor', ALL, DAY, cuisine='soul-food'),
        place('gibson-park', 'Gibson Park', 'park', 'overtown', 'Rebuilt community park with a pool, ball field '
              'and indoor recreation center.', ['pool', 'rec-center', 'sports'], 'free', 'mixed', ALL,
              ['morning', 'afternoon', 'evening']),
        place('mount-zion-baptist', 'Historic Mount Zion Baptist Church', 'landmark', 'overtown', 'Stately church '
              'founded in 1896, a pillar of Overtown\'s history.', ['history', 'church', 'architecture'], 'free',
              'indoor', ['family', 'solo'], ['morning']),
        place('culmer-overtown-library', 'Culmer/Overtown Branch Library', 'library', 'overtown', 'Neighborhood '
              'branch library with computers and after-school help.', ['books', 'kids', 'computers'], 'free',
              'indoor', ALL, DAY),
        place('allapattah-produce-market', 'Allapattah produce markets', 'market', 'allapattah', 'Wholesale-and-'
              'retail produce warehouses along NW 22nd Avenue selling tropical fruit by the case.',
              ['produce', 'cheap', 'local'], '$', 'mixed', ALL, ['morning']),
        place('allapattah-library', 'Allapattah Branch Library', 'library', 'allapattah', 'Miami-Dade branch '
              'library with bilingual programs.', ['books', 'bilingual', 'kids'], 'free', 'indoor', ALL, DAY),
        place('duarte-park', 'Juan Pablo Duarte Park', 'park', 'allapattah', 'Neighborhood park with ball fields '
              'and a playground, busy with Dominican families on weekends.', ['sports', 'playground', 'local'],
              'free', 'outdoor', ALL, ['afternoon', 'evening']),
        place('bakehouse-art-complex', 'Bakehouse Art Complex', 'museum', 'allapattah', 'Former bakery turned into '
              'dozens of artist studios and galleries with open studio days.', ['art', 'studios', 'free'], 'free',
              'indoor', ['solo', 'friends', 'date'], ['afternoon']),
        place('miami-river-greenway', 'Miami River Greenway', 'trail', 'health-district', 'Riverside walkway past '
              'boatyards, fishing boats and bridges between downtown and the Civic Center.',
              ['waterfront', 'walk', 'boats'], 'free', 'outdoor', ['solo', 'friends', 'date'], DAY),
        place('lummus-park-river', 'Lummus Park Historic District', 'park', 'health-district', 'Small riverside '
              'park holding the city\'s oldest buildings, the Wagner House and Fort Dallas.', ['history', 'shade',
              'river'], 'free', 'outdoor', ['solo', 'family'], DAY),
        place('casablanca-seafood', 'Casablanca Seafood Bar & Grill', 'restaurant', 'health-district', 'Fish market '
              'and dock restaurant on the Miami River, serving the day\'s catch.', ['seafood', 'river', 'fish-market'],
              '$$', 'mixed', ALL, ['afternoon', 'evening'], cuisine='seafood'),
        place('kiki-on-the-river', 'Kiki on the River', 'restaurant', 'health-district', 'Greek restaurant on the '
              'Miami River with a party crowd on weekend afternoons.', ['greek', 'waterfront', 'party'], '$$$',
              'mixed', ['friends', 'date'], ['afternoon', 'evening'], cuisine='greek'),
        place('spring-garden', 'Spring Garden Historic District', 'landmark', 'health-district', 'Quiet 1920s houses '
              'along Wagner Creek behind the hospital campus.', ['history', 'walk', 'quiet'], 'free', 'outdoor',
              ['solo', 'date'], DAY),
        place('barnacle', 'The Barnacle Historic State Park', 'park', 'coconut-grove', 'The Grove\'s oldest house '
              'on a wooded bayfront lawn, with picnics and moonlight concerts.', ['history', 'picnic', 'bayfront'],
              '$', 'outdoor', ALL, DAY),
        place('kennedy-park', 'David T. Kennedy Park', 'park', 'coconut-grove', 'Bayfront park with a fitness '
              'course, dog park and views over the water.', ['running', 'dogs', 'bayfront'], 'free', 'outdoor', ALL,
              ['morning', 'afternoon', 'evening']),
        place('coconut-grove-library', 'Coconut Grove Branch Library', 'library', 'coconut-grove', 'Historic coral '
              'rock library on the bay, one of the oldest in Miami-Dade.', ['books', 'historic', 'quiet'], 'free',
              'indoor', ALL, DAY),
        place('greenstreet-cafe', 'GreenStreet Cafe', 'restaurant', 'coconut-grove', 'Sidewalk cafe in the center of '
              'the Grove, a people-watching spot from breakfast to late drinks.', ['brunch', 'sidewalk',
              'people-watching'], '$$', 'outdoor', ALL, ['morning', 'afternoon', 'evening'], cuisine='american'),
        place('montys-raw-bar', 'Monty\'s Raw Bar', 'bar', 'coconut-grove', 'Tiki-hut marina bar with stone crabs, '
              'happy-hour deals and live music.', ['tiki', 'happy-hour', 'waterfront'], '$$', 'outdoor', ADULT,
              ['afternoon', 'evening']),
        place('havana-harrys', 'Havana Harry\'s', 'restaurant', 'coral-gables', 'Casual, generous Cuban restaurant '
              'favoured by local families.', ['cuban', 'family'], '$$', 'indoor', ALL, ['afternoon', 'evening'],
              cuisine='cuban'),
        place('coral-gables-library', 'Coral Gables Branch Library', 'library', 'coral-gables', 'Mediterranean '
              'Revival branch library with a courtyard and a big children\'s room.', ['books', 'quiet', 'kids'],
              'free', 'indoor', ALL, DAY),
        place('rusty-pelican', 'Rusty Pelican', 'restaurant', 'key-biscayne', 'Bayside restaurant on Virginia Key '
              'with skyline views from the causeway.', ['views', 'brunch', 'waterfront'], '$$$', 'mixed',
              ['date', 'family', 'friends'], ['afternoon', 'evening'], cuisine='seafood'),
        place('village-green-park', 'Village Green Park', 'park', 'key-biscayne', 'The island\'s central park with '
              'ball fields, a playground and village events.', ['playground', 'sports', 'local'], 'free', 'outdoor',
              ALL, ['morning', 'afternoon', 'evening']),
        place('key-biscayne-library', 'Key Biscayne Branch Library', 'library', 'key-biscayne', 'Small island '
              'branch library next to the village green.', ['books', 'quiet', 'kids'], 'free', 'indoor', ALL, DAY),
        place('arthur-godfrey-road', 'Arthur Godfrey Road', 'shopping', 'mid-beach', 'The 41st Street main drag of '
              'kosher bakeries, delis, banks and everyday shops.', ['errands', 'kosher', 'local'], '$$', 'outdoor',
              ALL, DAY),
        place('roasters-n-toasters', 'Roasters \'n Toasters', 'restaurant', 'mid-beach', 'Jewish deli for corned '
              'beef, matzo ball soup and big breakfasts.', ['deli', 'breakfast'], '$$', 'indoor', ALL, DAY,
              cuisine='jewish-deli'),
        place('indian-beach-park', 'Indian Beach Park', 'park', 'mid-beach', 'Beachfront park with a playground and '
              'shady picnic spots on the boardwalk.', ['beach', 'playground', 'picnic'], 'free', 'outdoor', ALL, DAY),
        place('scott-rakow-center', 'Scott Rakow Youth Center', 'fitness', 'mid-beach', 'City recreation center with '
              'an ice rink, pool, gym and bowling.', ['rec-center', 'skating', 'kids'], '$', 'indoor', ALL,
              ['afternoon', 'evening']),
        place('cafe-prima-pasta', 'Café Prima Pasta', 'restaurant', 'north-beach', 'Long-running Argentine-Italian '
              'trattoria on 71st Street with fresh pasta and sidewalk tables.', ['italian', 'pasta', 'local'], '$$',
              'mixed', ['date', 'family', 'friends'], DINNER, cuisine='italian'),
        place('north-shore-library', 'North Shore Branch Library', 'library', 'north-beach', 'Branch library on '
              'Collins Avenue a block from the sand.', ['books', 'quiet'], 'free', 'indoor', ALL, DAY),
        place('normandy-village-market', 'Normandy Village Marketplace', 'market', 'north-beach', 'Saturday farmers '
              'market around the Normandy Isle fountain.', ['farmers-market', 'saturday', 'local'], '$', 'outdoor',
              ALL, ['morning']),
        place('doral-legacy-park', 'Doral Legacy Park', 'park', 'doral', 'Large city park with a community center, '
              'water play, fields and a walking path.', ['playground', 'sports', 'rec-center'], 'free', 'mixed',
              ALL, ['morning', 'afternoon', 'evening']),
        place('doral-library', 'Doral Branch Library', 'library', 'doral', 'Miami-Dade branch library with '
              'bilingual story times and study space.', ['books', 'bilingual', 'kids'], 'free', 'indoor', ALL, DAY),
        place('miami-international-mall', 'Miami International Mall', 'shopping', 'doral', 'Enclosed suburban mall '
              'by the Dolphin Expressway, a cool place to walk on hot afternoons.', ['mall', 'errands'], '$$',
              'indoor', ALL, ['morning', 'afternoon', 'evening']),
        place('kendall-indian-hammocks', 'Kendall Indian Hammocks Park', 'park', 'kendall', 'Large county park with '
              'sports fields, a playground and shady hammock trails.', ['sports', 'trail', 'playground'], 'free',
              'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('kendall-library', 'Kendall Branch Library', 'library', 'kendall', 'Suburban branch library used for '
              'homework help and story times.', ['books', 'kids', 'study'], 'free', 'indoor', ALL, DAY),
        place('tropical-park', 'Tropical Park', 'park', 'westchester', 'Big county park on Bird Road with lakes, an '
              'equestrian center, tennis and a running track.', ['running', 'lakes', 'sports'], 'free', 'outdoor',
              ALL, ['morning', 'afternoon', 'evening']),
        place('frost-art-museum', 'Patricia & Phillip Frost Art Museum', 'museum', 'westchester', 'Free art museum on '
              'FIU\'s campus with Latin American and contemporary work.', ['art', 'free', 'campus'], 'free',
              'indoor', ALL, DAY),
        place('westchester-library', 'Westchester Regional Library', 'library', 'westchester', 'Large regional '
              'library on Coral Way with study rooms and Spanish-language collections.', ['books', 'study',
              'bilingual'], 'free', 'indoor', ALL, ['morning', 'afternoon', 'evening']),
        place('islas-canarias', 'Islas Canarias Restaurant', 'restaurant', 'westchester', 'Family Cuban restaurant '
              'famous for its ham croquetas.', ['cuban', 'croquetas', 'family'], '$', 'indoor', ALL,
              ['morning', 'afternoon', 'evening'], cuisine='cuban'),
        place('bird-bowl', 'Bird Bowl', 'venue', 'westchester', 'Old-school bowling alley on Bird Road with leagues, '
              'billiards and a bar.', ['bowling', 'retro', 'leagues'], '$', 'indoor', ALL, ['afternoon', 'evening',
              'late']),
        place('founders-park', 'Founders Park', 'park', 'aventura', 'Aventura\'s main park with a playground, '
              'fields and a bayside walk.', ['playground', 'sports', 'bayfront'], 'free', 'outdoor', ALL,
              ['morning', 'afternoon', 'evening']),
        place('aventura-arts-center', 'Aventura Arts & Cultural Center', 'venue', 'aventura', 'Small performing '
              'arts center with concerts, comedy and touring shows.', ['theater', 'concerts'], '$$', 'indoor',
              ['date', 'family', 'friends'], ['evening']),
        place('ne-dade-aventura-library', 'Northeast Dade-Aventura Branch Library', 'library', 'aventura', 'Branch '
              'library beside the city hall complex.', ['books', 'quiet', 'kids'], 'free', 'indoor', ALL, DAY),
        place('oleta-river', 'Oleta River State Park', 'park', 'aventura', 'Mangrove park with mountain-bike trails, '
              'kayak rentals and a small beach.', ['kayaking', 'mountain-biking', 'nature'], '$', 'outdoor', ALL, DAY),
        place('bourbon-steak-aventura', 'Bourbon Steak', 'restaurant', 'aventura', 'Michael Mina\'s steakhouse at the '
              'Turnberry resort, the area\'s special-occasion dinner.', ['steak', 'special-occasion'], '$$$$',
              'indoor', ['date', 'family'], DINNER, cuisine='steakhouse'),
        place('betty-ferguson-complex', 'Betty T. Ferguson Recreational Complex', 'fitness', 'miami-gardens',
              'City recreation complex with a pool, gym, fields and a community center.', ['rec-center', 'pool',
              'sports'], '$', 'mixed', ALL, ['morning', 'afternoon', 'evening']),
        place('north-dade-library', 'North Dade Regional Library', 'library', 'miami-gardens', 'Large regional '
              'library with study rooms, computers and teen programs.', ['books', 'study', 'teens'], 'free',
              'indoor', ALL, ['morning', 'afternoon', 'evening']),
        place('rolling-oaks-park', 'Rolling Oaks Park', 'park', 'miami-gardens', 'Neighborhood park with ball '
              'fields, a playground and youth football on autumn evenings.', ['sports', 'playground', 'local'],
              'free', 'outdoor', ALL, ['afternoon', 'evening']),
        place('amelia-earhart-park', 'Amelia Earhart Park', 'park', 'miami-gardens', 'Large county park with lakes, '
              'a farm village, a skate park and mountain-bike trails.', ['lakes', 'skate', 'kids'], '$', 'outdoor',
              ALL, DAY),
        place('calder-casino', 'Calder Casino', 'nightlife', 'miami-gardens', 'Slots casino on the grounds of the '
              'old Calder Race Course, with a bar and live music on weekends.', ['casino', 'locals', 'music'],
              '$$', 'indoor', ADULT, NIGHT),
        place('miami-gardens-drive-takeouts', 'Jamaican and soul food takeouts on Miami Gardens Drive', 'restaurant',
              'miami-gardens', 'Strip-mall counters along NW 183rd Street selling jerk chicken, oxtail, fried fish '
              'and smothered pork chops by the plate.', ['caribbean', 'soul-food', 'takeout', 'cheap'], '$',
              'indoor', ALL, ['afternoon', 'evening'], cuisine='caribbean'),
        # Everyday routines: coffee and pastry stops and places to work out.
        place('los-pinarenos', 'Los Pinareños Frutería', 'cafe', 'little-havana', 'Calle Ocho fruit stand open '
              'since the 1960s, selling Cuban coffee, fresh juices and batidos.', ['coffee', 'juice', 'cuban'], '$',
              'outdoor', ALL, DAY, cuisine='cuban'),
        place('threefold-cafe', 'Threefold Cafe', 'cafe', 'coral-gables', 'Australian-run cafe on Giralda Avenue '
              'serving flat whites and brunch.', ['coffee', 'brunch', 'australian'], '$$', 'mixed', ALL, DAY,
              cuisine='cafe'),
        place('last-carrot', 'The Last Carrot', 'cafe', 'coconut-grove', 'Small health-food counter on Grand '
              'Avenue since the 1970s, known for juices and spinach pies.', ['juice', 'vegetarian', 'local'], '$',
              'indoor', ALL, DAY, cuisine='vegetarian'),
        place('all-day', 'All Day', 'cafe', 'downtown', 'Downtown coffee shop on North Miami Avenue serving '
              'espresso and all-day breakfast.', ['coffee', 'breakfast', 'laptop'], '$', 'indoor',
              ['solo', 'friends', 'coworkers'], DAY, cuisine='coffee'),
        place('pura-vida', 'Pura Vida', 'cafe', 'south-beach', 'Miami Beach health cafe for smoothies, acai bowls '
              'and coffee.', ['smoothies', 'healthy', 'coffee'], '$$', 'mixed', ['solo', 'friends'], DAY,
              cuisine='cafe'),
        place('crandon-tennis', 'Crandon Park Tennis Center', 'fitness', 'key-biscayne', 'County tennis center with '
              'hard and clay courts, long home of the Miami Open.', ['tennis', 'courts', 'lessons'], '$', 'outdoor',
              ['solo', 'friends', 'family'], ['morning', 'evening']),
        place('coconut-grove-sailing-club', 'Coconut Grove Sailing Club', 'fitness', 'coconut-grove', 'Member club '
              'on Biscayne Bay at Dinner Key, with sailing lessons and races.', ['sailing', 'bayfront', 'lessons'],
              '$$', 'outdoor', ['solo', 'friends', 'family'], ['morning', 'afternoon']),
        place('biltmore-golf', 'Biltmore Golf Course', 'fitness', 'coral-gables', 'City-owned 1925 Donald Ross '
              'course beside the Biltmore Hotel.', ['golf', 'historic'], '$$', 'outdoor', ['solo', 'friends'],
              ['morning', 'afternoon']),
        place('flamingo-park', 'Flamingo Park', 'fitness', 'south-beach', 'City park with a public pool, tennis '
              'center, running track and ball fields.', ['pool', 'tennis', 'track'], '$', 'outdoor', ALL,
              ['morning', 'evening']),
    ],
    'colleges': [
        {'id': 'um', 'name': 'University of Miami', 'type': 'research-university', 'neighborhood': 'coral-gables',
         'size': 'large', 'known_for': ['marine-science', 'business', 'music', 'communication', 'engineering',
         'research'], 'source': S},
        {'id': 'um-miller', 'name': 'University of Miami Miller School of Medicine', 'type': 'medical-school',
         'neighborhood': 'health-district', 'size': 'medium', 'known_for': ['medicine', 'biomedical-research',
         'nursing'], 'source': S},
        {'id': 'fiu', 'name': 'Florida International University', 'type': 'public-university',
         'neighborhood': 'westchester', 'size': 'large', 'known_for': ['hospitality', 'business', 'engineering',
         'international-relations', 'law', 'medicine'], 'source': S},
        {'id': 'mdc-wolfson', 'name': 'Miami Dade College, Wolfson Campus', 'type': 'community-college',
         'neighborhood': 'downtown', 'size': 'large', 'known_for': ['associate-degrees', 'transfer', 'business',
         'book-fair'], 'source': S},
        {'id': 'mdc-kendall', 'name': 'Miami Dade College, Kendall Campus', 'type': 'community-college',
         'neighborhood': 'kendall', 'size': 'large', 'known_for': ['associate-degrees', 'transfer', 'nursing'],
         'source': S},
        {'id': 'barry', 'name': 'Barry University', 'type': 'private-university', 'neighborhood': 'little-haiti',
         'size': 'medium', 'known_for': ['nursing', 'education', 'social-work'], 'source': S},
        {'id': 'st-thomas', 'name': 'St. Thomas University', 'type': 'private-university',
         'neighborhood': 'miami-gardens', 'size': 'small', 'known_for': ['law', 'business'], 'source': S},
        {'id': 'florida-memorial', 'name': 'Florida Memorial University', 'type': 'private-university',
         'neighborhood': 'miami-gardens', 'size': 'small', 'known_for': ['hbcu', 'aviation', 'education'],
         'source': S},
        {'id': 'nwsa', 'name': 'New World School of the Arts', 'type': 'art-school', 'neighborhood': 'downtown',
         'size': 'small', 'known_for': ['dance', 'music', 'theater', 'visual-arts'], 'source': S},
    ],
    'employers': [
        {'id': 'jackson-health', 'name': 'Jackson Health System', 'sector': 'healthcare',
         'neighborhood': 'health-district', 'size': 'large', 'summary': 'The county public hospital system, '
         'anchored by Jackson Memorial Hospital and its Ryder Trauma Center.', 'careers': ['registered-nurse',
         'night-nurse', 'physician-resident', 'pharmacist', 'social-worker'], 'source': S},
        {'id': 'uhealth', 'name': 'UHealth - University of Miami Health System', 'sector': 'healthcare',
         'neighborhood': 'health-district', 'size': 'large', 'summary': 'The University of Miami\'s academic '
         'medical system, including the Sylvester cancer center and research labs.', 'careers': [
         'registered-nurse', 'physician-resident', 'medical-researcher', 'biotech-scientist', 'pharmacist'],
         'source': S},
        {'id': 'baptist-health', 'name': 'Baptist Health South Florida', 'sector': 'healthcare',
         'neighborhood': 'kendall', 'size': 'large', 'summary': 'Large non-profit hospital system with Baptist '
         'Hospital of Miami in Kendall.', 'careers': ['registered-nurse', 'night-nurse', 'pharmacist',
         'social-worker'], 'source': S},
        {'id': 'um-employer', 'name': 'University of Miami (Coral Gables campus)', 'sector': 'education',
         'neighborhood': 'coral-gables', 'size': 'large', 'summary': 'Faculty, research and staff jobs on the '
         'main campus.', 'careers': ['professor', 'graduate-student', 'data-analyst', 'marketing-coordinator'],
         'source': S},
        {'id': 'fiu-employer', 'name': 'Florida International University', 'sector': 'education',
         'neighborhood': 'westchester', 'size': 'large', 'summary': 'A large public research university.',
         'careers': ['professor', 'graduate-student'], 'source': S},
        {'id': 'mdcps', 'name': 'Miami-Dade County Public Schools', 'sector': 'education',
         'neighborhood': 'edgewater', 'size': 'large', 'summary': 'One of the largest school districts in the '
         'country, headquartered on Biscayne Boulevard.', 'careers': ['teacher', 'social-worker'], 'source': S},
        {'id': 'miami-dade-county', 'name': 'Miami-Dade County government', 'sector': 'government',
         'neighborhood': 'downtown', 'size': 'large', 'summary': 'County agencies in the Stephen P. Clark '
         'Government Center and offices across the county.', 'careers': ['government-analyst', 'accountant',
         'social-worker'], 'source': S},
        {'id': 'eleventh-circuit', 'name': 'Eleventh Judicial Circuit of Florida', 'sector': 'legal',
         'neighborhood': 'health-district', 'size': 'medium', 'summary': 'Miami-Dade\'s state courts, with the '
         'criminal justice building near the Civic Center.', 'careers': ['paralegal', 'government-analyst'],
         'source': S},
        {'id': 'citadel', 'name': 'Citadel', 'sector': 'finance', 'neighborhood': 'brickell', 'size': 'medium',
         'summary': 'Hedge fund and market maker that moved its headquarters to Miami.', 'careers': [
         'financial-analyst', 'finance-banker', 'software-engineer', 'data-analyst'], 'source': S},
        {'id': 'carnival', 'name': 'Carnival Corporation', 'sector': 'tourism', 'neighborhood': 'doral',
         'size': 'large', 'summary': 'The world\'s largest cruise company, headquartered in Doral.', 'careers': [
         'marketing-coordinator', 'software-engineer', 'data-analyst', 'accountant', 'financial-analyst'],
         'source': S},
        {'id': 'royal-caribbean', 'name': 'Royal Caribbean Group', 'sector': 'tourism', 'neighborhood': 'downtown',
         'size': 'large', 'summary': 'Cruise company headquartered on Dodge Island at PortMiami.', 'careers': [
         'software-engineer', 'ux-designer', 'data-analyst', 'marketing-coordinator', 'event-planner'],
         'source': S},
        {'id': 'portmiami', 'name': 'PortMiami', 'sector': 'logistics', 'neighborhood': 'downtown', 'size': 'large',
         'summary': 'The cruise capital of the world and a major container port on Dodge Island.', 'careers': [
         'port-logistics'], 'source': S},
        {'id': 'mia-airport', 'name': 'Miami International Airport', 'sector': 'logistics', 'neighborhood': 'doral',
         'size': 'large', 'summary': 'Busy passenger hub and one of the top international air-cargo airports in '
         'the country, on Doral\'s eastern edge.', 'careers': ['port-logistics'],
         'source': S},
        {'id': 'lennar', 'name': 'Lennar', 'sector': 'real-estate', 'neighborhood': 'doral', 'size': 'large',
         'summary': 'National homebuilder headquartered in west Miami-Dade.', 'careers': ['real-estate-agent',
         'construction-trades', 'accountant', 'financial-analyst'], 'source': S},
        {'id': 'telemundo', 'name': 'Telemundo', 'sector': 'media', 'neighborhood': 'doral', 'size': 'large',
         'summary': 'Spanish-language network with its news and telenovela studios at Telemundo Center.',
         'careers': ['journalist', 'actor', 'performer', 'graphic-designer', 'marketing-coordinator'],
         'source': S},
        {'id': 'univision', 'name': 'Univision', 'sector': 'media', 'neighborhood': 'doral', 'size': 'large',
         'summary': 'Spanish-language broadcaster with major news and studio operations in Doral.', 'careers': [
         'journalist', 'marketing-coordinator', 'actor'], 'source': S},
        {'id': 'fontainebleau-employer', 'name': 'Fontainebleau Miami Beach', 'sector': 'hospitality',
         'neighborhood': 'mid-beach', 'size': 'large', 'summary': 'Huge resort hotel with nightclubs, restaurants '
         'and convention space.', 'careers': ['hotel-front-desk', 'event-planner', 'line-cook', 'server',
         'bartender'], 'source': S},
        {'id': 'faena', 'name': 'Faena Hotel Miami Beach', 'sector': 'hospitality', 'neighborhood': 'mid-beach',
         'size': 'medium', 'summary': 'Luxury hotel with its own theater for cabaret shows.', 'careers': [
         'hotel-front-desk', 'server', 'bartender', 'performer', 'event-planner'], 'source': S},
        {'id': 'magic-city-casino', 'name': 'Magic City Casino', 'sector': 'hospitality',
         'neighborhood': 'little-havana', 'size': 'medium', 'summary': 'Casino on NW 37th Avenue at the west '
         'edge of Little Havana.', 'careers': ['casino-dealer', 'bartender', 'server'], 'source': S},
        {'id': 'arsht-employer', 'name': 'Adrienne Arsht Center', 'sector': 'entertainment',
         'neighborhood': 'downtown', 'size': 'medium', 'summary': 'The main performing arts center.',
         'careers': ['performer', 'musician', 'actor', 'event-planner'], 'source': S},
        {'id': 'new-world-symphony', 'name': 'New World Symphony', 'sector': 'entertainment',
         'neighborhood': 'south-beach', 'size': 'small', 'summary': 'Orchestral academy for young musicians at '
         'the New World Center.', 'careers': ['musician'], 'source': S},
        {'id': 'miami-beach-ocean-rescue', 'name': 'Miami Beach Ocean Rescue', 'sector': 'recreation',
         'neighborhood': 'south-beach', 'size': 'medium', 'summary': 'The city lifeguard service staffing the '
         'towers along Miami Beach.', 'careers': ['lifeguard'], 'source': S},
        {'id': 'southcom', 'name': 'U.S. Southern Command', 'sector': 'defense', 'neighborhood': 'doral',
         'size': 'medium', 'summary': 'Military command for Latin America and the Caribbean, headquartered in '
         'Doral.', 'careers': ['military-sailor', 'government-analyst'], 'source': S},
        {'id': 'coast-guard-miami', 'name': 'U.S. Coast Guard Sector Miami', 'sector': 'defense',
         'neighborhood': 'south-beach', 'size': 'medium', 'summary': 'Coast Guard base by Government Cut with '
         'cutters patrolling the Florida Straits.', 'careers': ['military-sailor'], 'source': S},
    ],
    'career_hubs': [
        {'id': 'brickell-finance', 'name': 'Brickell financial district', 'neighborhoods': ['brickell',
         'downtown'], 'sectors': ['finance', 'legal', 'technology', 'real-estate', 'business'], 'summary': 'Banks, '
         'hedge funds, law firms and tech offices in the towers along Brickell Avenue.', 'source': S},
        {'id': 'downtown-port', 'name': 'Downtown and the port', 'neighborhoods': ['downtown', 'overtown'],
         'sectors': ['government', 'logistics', 'tourism', 'entertainment', 'education'], 'summary': 'County '
         'government, Miami Dade College, the arena, the arts center and PortMiami.', 'source': S},
        {'id': 'health-district-hub', 'name': 'Health District', 'neighborhoods': ['health-district', 'kendall'],
         'sectors': ['healthcare', 'biotech', 'social-services', 'legal'], 'summary': 'Jackson Memorial, UHealth '
         'and the medical school at the Civic Center, plus big hospitals in Kendall.', 'source': S},
        {'id': 'beach-hospitality', 'name': 'Miami Beach hotels and nightlife', 'neighborhoods': ['south-beach',
         'mid-beach', 'north-beach'], 'sectors': ['hospitality', 'tourism', 'recreation', 'fitness',
         'entertainment', 'retail', 'food'], 'summary': 'Hotels, restaurants, clubs, beaches and gyms that run on '
         'tourist seasons and events.', 'source': S},
        {'id': 'doral-corporate', 'name': 'Doral logistics and corporate parks', 'neighborhoods': ['doral'],
         'sectors': ['logistics', 'business', 'media', 'defense', 'construction', 'real-estate', 'technology'],
         'summary': 'Warehouses and freight forwarders by the airport, cruise and homebuilder headquarters, '
         'Spanish-language TV studios and SOUTHCOM.', 'source': S},
        {'id': 'gables-corporate', 'name': 'Coral Gables offices and campuses', 'neighborhoods': ['coral-gables',
         'westchester'], 'sectors': ['business', 'education', 'finance', 'legal'], 'summary': 'Multinational '
         'Latin America regional offices, consulates and two large universities.', 'source': S},
        {'id': 'creative-districts', 'name': 'Wynwood and the Design District', 'neighborhoods': ['wynwood',
         'design-district', 'midtown'], 'sectors': ['creative', 'retail', 'food', 'hospitality', 'technology'],
         'summary': 'Galleries, studios, fashion boutiques, restaurants and start-up offices.', 'source': S},
    ],
    'climate': {
        'summary': 'Tropical monsoon: warm, dry and sunny winters, and long hot, humid wet seasons from May to '
                   'October with daily afternoon storms; hurricane season runs June to November.',
        'months': [
            {'high_f': 76, 'low_f': 61, 'rain_days': 7, 'note': 'Dry season; peak tourist and snowbird months.'},
            {'high_f': 78, 'low_f': 63, 'rain_days': 6, 'note': 'Dry and sunny; occasional cool fronts.'},
            {'high_f': 80, 'low_f': 66, 'rain_days': 6, 'note': 'Warm, dry and busy with spring break and '
             'festivals.'},
            {'high_f': 83, 'low_f': 70, 'rain_days': 6, 'note': 'Warming up; still mostly dry.'},
            {'high_f': 87, 'low_f': 74, 'rain_days': 10, 'note': 'Wet season begins; humidity climbs.'},
            {'high_f': 89, 'low_f': 77, 'rain_days': 17, 'note': 'Hurricane season starts; daily afternoon '
             'downpours.'},
            {'high_f': 91, 'low_f': 78, 'rain_days': 17, 'note': 'Hot and steamy; brief heavy storms.'},
            {'high_f': 91, 'low_f': 78, 'rain_days': 19, 'note': 'Hottest and wettest stretch; Miami Spice '
             'begins.'},
            {'high_f': 89, 'low_f': 77, 'rain_days': 18, 'note': 'Peak of hurricane season.'},
            {'high_f': 86, 'low_f': 74, 'rain_days': 13, 'note': 'Still humid; king tides can flood streets.'},
            {'high_f': 82, 'low_f': 68, 'rain_days': 8, 'note': 'Dry season returns; hurricane season ends.'},
            {'high_f': 78, 'low_f': 64, 'rain_days': 7, 'note': 'Pleasant and dry; Art Basel week.'},
        ],
        'source': CLIMATE,
    },
    'annual_events': [
        {'id': 'sobewff', 'name': 'South Beach Wine & Food Festival', 'months': [2], 'neighborhood': 'south-beach',
         'summary': 'Celebrity-chef tastings in tents on the sand.', 'source': S},
        {'id': 'coconut-grove-arts-festival', 'name': 'Coconut Grove Arts Festival', 'months': [2],
         'neighborhood': 'coconut-grove', 'summary': 'Large outdoor juried art fair over Presidents\' Day '
         'weekend.', 'source': S},
        {'id': 'calle-ocho-festival', 'name': 'Calle Ocho Music Festival', 'months': [3],
         'neighborhood': 'little-havana', 'summary': 'A giant Latin street party on SW 8th Street, closing the '
         'Carnaval Miami season.', 'source': S},
        {'id': 'miami-music-week', 'name': 'Miami Music Week', 'months': [3], 'neighborhood': 'south-beach',
         'summary': 'A week of dance-music pool parties and club nights across Miami Beach and the mainland.',
         'source': S},
        {'id': 'ultra', 'name': 'Ultra Music Festival', 'months': [3], 'neighborhood': 'downtown',
         'summary': 'Huge electronic music festival at Bayfront Park.', 'source': S},
        {'id': 'miami-open', 'name': 'Miami Open', 'months': [3, 4], 'neighborhood': 'miami-gardens',
         'summary': 'Top-level tennis tournament held at Hard Rock Stadium.', 'source': S},
        {'id': 'miami-beach-pride', 'name': 'Miami Beach Pride', 'months': [4], 'neighborhood': 'south-beach',
         'summary': 'Parade and festival along Ocean Drive and Lummus Park.', 'source': S},
        {'id': 'f1-miami', 'name': 'Formula 1 Miami Grand Prix', 'months': [5], 'neighborhood': 'miami-gardens',
         'summary': 'Race weekend on a circuit built around Hard Rock Stadium.', 'source': S},
        {'id': 'miami-spice', 'name': 'Miami Spice', 'months': [8, 9], 'neighborhood': None,
         'summary': 'Restaurants across the county offer prix-fixe menus during the slow summer season.',
         'source': S},
        {'id': 'dolphins-season', 'name': 'Dolphins football season', 'months': [9, 10, 11, 12, 1],
         'neighborhood': 'miami-gardens', 'summary': 'Sunday game days and tailgates at Hard Rock Stadium.',
         'source': S},
        {'id': 'heat-season', 'name': 'Miami Heat season', 'months': [10, 11, 12, 1, 2, 3, 4],
         'neighborhood': 'downtown', 'summary': 'NBA games at Kaseya Center.', 'source': S},
        {'id': 'miami-book-fair', 'name': 'Miami Book Fair', 'months': [11], 'neighborhood': 'downtown',
         'summary': 'Week of author talks ending in a street fair at Miami Dade College\'s Wolfson Campus.',
         'source': S},
        {'id': 'art-basel', 'name': 'Art Basel Miami Beach and Miami Art Week', 'months': [12],
         'neighborhood': 'south-beach', 'summary': 'The big art fair at the Miami Beach Convention Center, with '
         'satellite fairs and parties across the city.', 'source': S},
        {'id': 'orange-bowl', 'name': 'Orange Bowl', 'months': [12, 1], 'neighborhood': 'miami-gardens',
         'summary': 'College football bowl game at Hard Rock Stadium around New Year.', 'source': S},
    ],
    'local_color': [
        color('cafecito', 'Cafecito', 'drink', 'Cuban espresso brewed strong and whipped with sugar into a sweet foam '
              '(espumita), drunk in a few sips standing at a walk-up window.', ['versailles', 'puerto-sagua']),
        color('colada', 'Colada', 'drink', 'A larger cafecito in a styrofoam cup with a stack of thimble-sized plastic '
              'cups, bought to share around the office or job site.', ['versailles']),
        color('cafe-con-leche-y-tostada', 'Café con leche and tostada', 'dish', 'The Cuban breakfast: hot milk with '
              'espresso and pressed, buttered Cuban bread for dunking.', ['versailles', 'puerto-sagua', 'enriquetas']),
        color('three-oh-five', '3:05 cafecito', 'custom', 'Miami\'s area code is 305, so 3:05 in the afternoon has '
              'become a time for a coffee break, with people posting their cafecitos.'),
        color('ventanita', 'Ventanitas', 'shop', 'Walk-up coffee windows at Cuban restaurants and bakeries, where '
              'people stand for cafecito, pastelitos, croquetas and talk about politics.',
              ['versailles', 'little-havana']),
        color('cuban-sandwich', 'Cuban sandwich', 'dish', 'Roast pork, ham, Swiss cheese, pickles and mustard pressed '
              'flat on Cuban bread; the medianoche is the same on a sweet egg roll.', ['sanguich', 'versailles']),
        color('pastelitos-and-croquetas', 'Pastelitos and croquetas', 'dish', 'Flaky pastries filled with guava, guava '
              'and cream cheese, or meat, and fried ham croquetas, bought by the dozen for any gathering.',
              ['little-havana']),
        color('frita', 'Frita', 'dish', 'The Cuban hamburger: a seasoned beef and chorizo patty with a pile of crisp '
              'shoestring potatoes on a soft bun.', ['little-havana']),
        color('stone-crabs', 'Stone crab claws', 'dish', 'Florida stone crab claws are served cold and cracked with '
              'mustard sauce; the season opens in mid-October and runs into spring.',
              ['joes-stone-crab'], ['fall', 'winter', 'spring']),
        color('pub-sub', 'Pub sub', 'dish', 'Floridians are devoted to the made-to-order deli subs at Publix '
              'supermarkets, especially the chicken tender sub.'),
        color('dale', '"Dale"', 'saying', 'All-purpose Miami Spanish for "go ahead", "let\'s go", "OK" or "bye", heard '
              'from everyone whatever their first language.'),
        color('spanglish', 'Miami Spanglish', 'saying', 'Conversations switch between English and Spanish '
              'mid-sentence, with phrases like "pero like" ("but, like") and greetings like the Cuban "¿qué bolá?" '
              '(what\'s up?).'),
        color('domino-games', 'Domino games', 'custom', 'Older men, many Cuban, play loud games of dominoes all day at '
              'the tables of Domino Park on Calle Ocho.', ['domino-park']),
        color('hurricane-prep', 'Hurricane prep', 'custom', 'From June through November people keep shutters, water, '
              'batteries and gas ready, and supermarket shelves empty fast when a storm is in the cone.',
              seasons=['summer', 'fall']),
        color('miami-dolphins', 'Miami Dolphins', 'team', 'The NFL team plays at Hard Rock Stadium in Miami Gardens, '
              'and fans never let anyone forget the 1972 perfect season.', ['hard-rock-stadium'], ['fall', 'winter']),
        color('miami-heat', 'Miami Heat', 'team', 'The NBA team plays downtown at Kaseya Center and is known for "Heat '
              'Culture", its demanding work ethic, and for crowds dressed in all white for playoff games.',
              ['kaseya-center'], ['fall', 'winter', 'spring']),
        color('miami-marlins', 'Miami Marlins', 'team', 'The Major League Baseball team plays in Little Havana at '
              'loanDepot park, which has a retractable roof against summer rain.',
              ['loandepot-park'], ['spring', 'summer', 'fall']),
        color('florida-panthers', 'Florida Panthers', 'team', 'The NHL team plays in Sunrise, north of the city, and '
              'won back-to-back Stanley Cups in 2024 and 2025.', seasons=['fall', 'winter', 'spring']),
        color('inter-miami', 'Inter Miami', 'team', 'The MLS soccer club co-owned by David Beckham, which made Lionel '
              'Messi the city\'s most famous footballer when he signed in 2023.'),
        color('miami-hurricanes', 'Miami Hurricanes', 'team', 'The University of Miami\'s teams, especially football, '
              'which plays at Hard Rock Stadium; fans flash the "U" with their hands.',
              ['hard-rock-stadium'], ['fall']),
    ],
    'prices': [
        price('coffee', 'Coffee', 2.5, 4, 'a cup'),
        price('cafecito', 'Cafecito or colada', 1.5, 4, 'colada is for sharing'),
        price('latte', 'Latte', 5, 7),
        price('cuban-sandwich', 'Cuban sandwich', 9, 14),
        price('cheap-lunch', 'Cheap lunch', 12, 20),
        price('dinner', 'Mid-range dinner', 40, 70, 'for one'),
        price('beer', 'Pint of beer', 8, 11, 'a pint'),
        price('cocktail', 'Cocktail', 15, 22),
        price('groceries', 'Groceries', 85, 130, 'a week, one person'),
        price('transit', 'Metrorail or Metrobus fare', 2.25, 2.25, 'one way'),
        price('rideshare', 'Rideshare across town', 15, 35),
        price('movie', 'Movie ticket', 14, 19),
        price('gym', 'Gym membership', 30, 80, 'a month'),
        price('haircut', 'Haircut', 25, 50),
    ],
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
