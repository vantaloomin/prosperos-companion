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
    'sources': {
        S: {'kind': 'curated', 'title': 'Miami places and neighbourhoods written for Prospero Companion',
            'license': 'CC0-1.0', 'retrieved': '2026-10-05',
            'note': 'Well-known public places, institutions and employers from general knowledge, covering the '
                    'City of Miami plus Miami Beach and nearby municipalities people treat as neighbourhoods '
                    '(Coral Gables, Key Biscayne, Doral, Aventura, Miami Gardens). Businesses open and close and '
                    'rents move: treat this as a snapshot for fiction. Rents are rounded estimates of typical '
                    'asking ranges, not listings. Coordinates are approximate neighbourhood centres.'},
        CLIMATE: {'kind': 'curated', 'title': 'Approximate monthly climate for Miami (Miami International '
                  'Airport area)', 'license': 'CC0-1.0', 'retrieved': '2026-10-05',
                  'note': 'Rounded values in line with NOAA 1991-2020 normals; refresh with scripts/world when '
                          'network access to NOAA is available. The wet season runs May to October and the '
                          'Atlantic hurricane season June to November.'},
    },
    'neighborhoods': [
        hood('brickell', 'Brickell', 'The financial district: a dense wall of glass condo and office towers along '
             'Brickell Avenue and the bay, with rooftop bars and Brickell City Centre.',
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
        hood('overtown', 'Overtown', 'Historic Black neighbourhood once called the Harlem of the South, now '
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
        hood('coconut-grove', 'Coconut Grove', 'Miami\'s oldest neighbourhood: leafy, bayside and bohemian-turned-'
             'affluent, with marinas, sailing clubs and a walkable village centre.', ['leafy', 'waterfront',
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
             'apartments, reaching up toward Surfside and Bal Harbour.', ['beach', 'local', 'mimo', 'quiet'],
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
        hood('westchester', 'Westchester and University Park', 'Cuban-American suburban neighbourhoods around '
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
              'theatre in the former Jackie Gleason Theater.', ['concerts', 'comedy'], '$$$', 'indoor',
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
        place('bal-harbour-shops', 'Bal Harbour Shops', 'shopping', 'north-beach', 'Open-air luxury mall in the '
              'village of Bal Harbour, just north of North Beach.', ['luxury', 'fashion', 'mall'], '$$$$', 'outdoor',
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
              'performing arts centre, hosting touring Broadway, opera, ballet and the Florida Grand Opera.',
              ['theatre', 'broadway', 'opera', 'ballet'], '$$$', 'indoor', ['date', 'family', 'solo'],
              ['evening']),
        place('club-space', 'Club Space', 'nightlife', 'downtown', 'Electronic music club famous for its '
              'rooftop terrace and parties running past sunrise.', ['club', 'techno', 'after-hours'], '$$$',
              'mixed', ['friends'], ['late']),
        place('garcias', 'Garcia\'s Seafood Grille & Fish Market', 'restaurant', 'downtown', 'Family-run fish '
              'market and restaurant on the Miami River.', ['seafood', 'river', 'casual'], '$$', 'mixed', ALL,
              ['afternoon', 'evening'], cuisine='seafood'),
        place('brickell-city-centre', 'Brickell City Centre', 'shopping', 'brickell', 'Multi-level open-air mall '
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
        place('gramps', 'Gramps', 'bar', 'wynwood', 'Neighbourhood bar with a big back patio, drag brunch and '
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
              'centre with a gallery, theatre and the monthly Sounds of Little Haiti music night.',
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
        place('cocowalk', 'CocoWalk', 'shopping', 'coconut-grove', 'Open-air shopping and dining centre in the '
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
              'Biscayne, the city\'s favourite road-cycling and running route with skyline views.', ['cycling',
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
         'size': 'small', 'known_for': ['dance', 'music', 'theatre', 'visual-arts'], 'source': S},
    ],
    'employers': [
        {'id': 'jackson-health', 'name': 'Jackson Health System', 'sector': 'healthcare',
         'neighborhood': 'health-district', 'size': 'large', 'summary': 'The county public hospital system, '
         'anchored by Jackson Memorial Hospital and its Ryder Trauma Center.', 'careers': ['registered-nurse',
         'night-nurse', 'physician-resident', 'pharmacist', 'social-worker'], 'source': S},
        {'id': 'uhealth', 'name': 'UHealth - University of Miami Health System', 'sector': 'healthcare',
         'neighborhood': 'health-district', 'size': 'large', 'summary': 'The University of Miami\'s academic '
         'medical system, including the Sylvester cancer centre and research labs.', 'careers': [
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
         'size': 'medium', 'summary': 'Luxury hotel with its own theatre for cabaret shows.', 'careers': [
         'hotel-front-desk', 'server', 'bartender', 'performer', 'event-planner'], 'source': S},
        {'id': 'magic-city-casino', 'name': 'Magic City Casino', 'sector': 'hospitality',
         'neighborhood': 'little-havana', 'size': 'medium', 'summary': 'Casino on NW 37th Avenue at the west '
         'edge of Little Havana.', 'careers': ['casino-dealer', 'bartender', 'server'], 'source': S},
        {'id': 'arsht-employer', 'name': 'Adrienne Arsht Center', 'sector': 'entertainment',
         'neighborhood': 'downtown', 'size': 'medium', 'summary': 'The main performing arts centre.',
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
         'government, Miami Dade College, the arena, the arts centre and PortMiami.', 'source': S},
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
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
