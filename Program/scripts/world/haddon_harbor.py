"""Haddon Harbor, an original small harbour town on the Maine coast. Run `python scripts/world/haddon_harbor.py` to
rewrite it."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'cities' / 'haddon-harbor.json'
S = 'curated-2026-10'


def hood(id, name, summary, vibe, lat, lon, tier, rent, housing, walk, transit):
    studio, one, two = rent
    return {'id': id, 'name': name, 'summary': summary, 'vibe': vibe, 'lat': lat, 'lon': lon, 'rent_tier': tier,
            'rent': {'studio': studio, 'one_bedroom': one, 'two_bedroom': two}, 'housing': housing,
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
            'themes': themes, 'eras': ['modern']}


def event(id, name, months, hood, summary):
    return {'id': id, 'name': name, 'months': months, 'neighborhood': hood, 'summary': summary, 'source': S}


def line(id, name, kind, summary):
    return {'id': id, 'name': name, 'kind': kind, 'summary': summary, 'source': S}


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
DAYTIME = ['morning', 'afternoon', 'evening']
NIGHT = ['evening', 'late']
WARM = ['spring', 'summer', 'fall']
SUMMER = ['summer']
SHUTTLE = 'summer-shuttle'
FERRY = 'tarbox-ferry'
BIKES = 'library-bikes'

HOODS = [
    hood('the-green', 'Main Street and the Green', 'The middle of town: a sloping green with a bandstand and a '
         'war memorial, white Congregational steeple at the top, and two blocks of brick and clapboard shopfronts '
         'running down to the water. Flats over the shops, and nobody crosses the street without being stopped '
         'for a chat.', ['downtown', 'walkable', 'historic', 'shops', 'everyone-knows-everyone'], 43.9700, -69.3000,
         'mid', ([950, 1250], [1150, 1550], [1450, 1950]), ['apartment-over-shop', 'federal-house', 'condo'],
         'high', [SHUTTLE, BIKES]),
    hood('the-harbor', 'The Harbor', 'The working waterfront below Main Street: the town fish pier, the lobster '
         'co-op, bait barrels, stacked traps, the ferry slip and a harbour full of boats on moorings. Busy at '
         'four in the morning and again at four in the afternoon, when the boats come in.',
         ['working-waterfront', 'lobster', 'boats', 'early-risers'], 43.9662, -69.2958, 'mid',
         ([975, 1300], [1200, 1600], [1500, 2000]), ['apartment-over-shop', 'cape', 'converted-loft'], 'high',
         [SHUTTLE, FERRY, BIKES]),
    hood('mill-end', 'Mill End', 'Where the Mill River drops over the falls into the tide: the long brick Kendall '
         'Mill, which made shoes until 1987, is now studios, a brewery, a dance school and a climbing gym, with '
         'worker housing in the old mill tenements up the hill.', ['arts', 'makers', 'riverside', 'young',
         'brick'], 43.9742, -69.3062, 'mid', ([900, 1200], [1100, 1450], [1350, 1800]),
         ['mill-loft', 'tenement-apartment', 'triple-decker'], 'high', [BIKES]),
    hood('packard-hill', 'Packard Hill', 'The hill above the harbour where the sea captains built: big square '
         'houses with widow\'s walks, the old Packard House Inn on its lawn, an eighteenth-century burying ground '
         'and the best sledding slope in town.', ['historic', 'views', 'quiet', 'old-houses', 'inns'], 43.9722,
         -69.2928, 'high', ([1100, 1450], [1350, 1800], [1750, 2500]), ['captains-house', 'carriage-house-flat',
         'inn-rooms'], 'medium', [SHUTTLE]),
    hood('college-street', 'College Street', 'The north end of the village around Whitcomb College: brick halls '
         'and a sloping quad, porches stacked with bikes, faculty houses with overgrown gardens and a pocket of '
         'cheap food that stays open after nine.', ['college', 'students', 'leafy', 'porches'], 43.9782, -69.3020,
         'mid', ([925, 1250], [1150, 1500], [1500, 1950]), ['shared-house', 'apartment', 'faculty-house'],
         'high', [BIKES]),
    hood('birch-meadow', 'Birch Meadow', 'The newer side of town off the Augusta road: cul-de-sacs of capes and '
         'colonials built from the nineties onward, basketball hoops over garages, the elementary school and a '
         'park full of strollers on Saturday mornings.', ['suburban', 'families', 'newer', 'quiet'], 43.9850,
         -69.3150, 'mid', ([1000, 1300], [1250, 1600], [1650, 2250]), ['cape', 'colonial', 'townhouse'], 'low',
         []),
    hood('ridge-road', 'Ridge Road', 'The farms and orchards on the high ground inland: stone walls, apple '
         'trees, a sugarhouse, the grange hall and the fairgrounds, with honour-system stands at the ends of '
         'driveways and a view of the bay from the top of Higgins Hill.', ['rural', 'farms', 'orchards',
         'stone-walls'], 44.0050, -69.3200, 'low', ([800, 1050], [950, 1300], [1250, 1700]),
         ['farmhouse', 'ell-apartment', 'mobile-home'], 'low', []),
    hood('ledge-point', 'Ledge Point', 'The rocky point at the mouth of the harbour, with the white lighthouse, '
         'the keeper\'s house museum, tide pools, a small sand cove and a road of shingled summer cottages that '
         'go dark after Columbus Day.', ['lighthouse', 'scenic', 'summer', 'rocky-shore'], 43.9500, -69.2820,
         'high', ([1100, 1500], [1350, 1850], [1750, 2600]), ['summer-cottage', 'cape'], 'low', [SHUTTLE]),
    hood('long-pond', 'Long Pond', 'A clear six-mile lake north of town ringed with camps on dirt roads, two old '
         'summer camps for children, a town beach and a store that sells crawlers, coffee and pie. In winter '
         'the ice-fishing shacks come out.', ['lake', 'camps', 'summer', 'woods', 'loons'], 44.0150, -69.2900,
         'low', ([800, 1050], [950, 1300], [1250, 1750]), ['lake-camp', 'cabin', 'year-round-camp'], 'low',
         []),
    hood('route-1', 'The Route 1 Strip', 'Route 1 where it skirts the village: the grocery, the hardware store, '
         'the gym, the ice arena, candlepin lanes and a coffee shack, with plenty of parking and the only '
         'traffic light in town.', ['practical', 'errands', 'car-oriented', 'local'], 43.9900, -69.3000, 'low',
         ([850, 1100], [1000, 1350], [1300, 1700]), ['apartment', 'duplex', 'motel-conversion'], 'low', []),
    hood('south-haddon', 'South Haddon', 'The neighbouring village down the peninsula: a white church, a general '
         'store with a porch bench, a town landing full of skiffs and a salt marsh where the land trust keeps '
         'the trails mown. Quieter than town, and proud of it.', ['village', 'rural', 'saltwater', 'quiet'],
         43.9350, -69.3200, 'mid', ([875, 1150], [1050, 1400], [1350, 1850]), ['cape', 'farmhouse',
         'cottage'], 'low', []),
    hood('tarbox-island', 'Tarbox Island', 'An island forty minutes out by ferry with about two hundred people '
         'all year and many more in summer: a lobster wharf, one store, a community hall, a one-room school '
         'and a loop road where everyone waves.', ['island', 'remote', 'lobster', 'close-knit', 'summer'],
         43.9250, -69.2500, 'mid', ([850, 1150], [1000, 1400], [1300, 1900]), ['island-house', 'cottage',
         'cape'], 'medium', [FERRY]),
    hood('dyers-cove', "Dyer's Cove", 'The cove south of the fish pier where the Hatch boatyard has built and '
         'stored boats for four generations, with the marina, the community sailing dock, the Legion post and '
         'small houses whose yards hold more boats than cars.', ['boatyard', 'working', 'marina', 'tight-knit'],
         43.9620, -69.3050, 'low', ([875, 1150], [1050, 1400], [1350, 1800]), ['cape', 'bungalow', 'duplex'],
         'medium', [SHUTTLE, BIKES]),
    hood('west-end', 'West End', 'Older neighbourhood of triple-deckers and capes west of the village, with '
         'the hospital, the high school and its field, Cobb Pond for skating, an Italian market and the pub '
         'where the nurses go after a shift.', ['residential', 'working', 'hospital', 'schools'], 43.9720,
         -69.3150, 'low', ([875, 1150], [1050, 1400], [1350, 1800]), ['triple-decker', 'cape', 'duplex'],
         'medium', [BIKES]),
    hood('back-shore', 'The Back Shore', 'The ocean side of the peninsula: a cliff path over granite ledges, a '
         'cobble beach, the nine-hole links, a chapel that only opens in summer and long-held family cottages '
         'with names painted on boards.', ['oceanfront', 'scenic', 'summer', 'walks'], 43.9580, -69.2780,
         'very-high', ([1200, 1600], [1500, 2100], [2000, 3000]), ['shingle-cottage', 'summer-house'], 'low',
         [SHUTTLE]),
]

PLACES = [
    # Main Street and the Green
    place('bluebird-diner', 'Bluebird Diner', 'restaurant', 'the-green', 'The diner everyone goes to: a narrow '
          'room of red stools, six booths and a wall of regulars\' mugs on pegs. Blueberry pancakes, hash from '
          'scratch, and town business settled at the counter before seven.', ['diner', 'breakfast', 'mug-wall',
          'regulars', 'cash-friendly'], '$', 'indoor', ALL, DAY, cuisine='diner'),
    place('spruce-street-bakery', 'Spruce Street Bakery', 'cafe', 'the-green', 'A bakery just off Main with a '
          'line out the door by eight for morning buns, whoopie pies, sourdough and a molasses doughnut that '
          'sells out by ten. Two small tables and a bench in the sun.', ['bakery', 'pastries', 'bread',
          'morning'], '$', 'indoor', ALL, DAY, cuisine='bakery'),
    place('fog-bell-books', 'Fog Bell Books', 'shopping', 'the-green', 'An independent bookshop in a former bank, '
          'with the vault kept as the children\'s room, staff picks written by hand, a shelf of Maine authors and '
          'an armchair nobody is ever asked to leave.', ['books', 'independent', 'readings', 'cozy'], '$$',
          'indoor', ALL, DAYTIME),
    place('anchor-tavern', 'The Anchor Tavern', 'bar', 'the-green', 'The pub at the bottom of Main: low beams, '
          'local drafts, a good haddock sandwich and Tuesday trivia night, where the same four teams have been '
          'fighting over the top spot for years.', ['pub', 'trivia', 'local-beer', 'pub-food'], '$$', 'indoor',
          ADULT, NIGHT, cuisine='pub'),
    place('cappellis-pizza', "Cappelli's Pizza", 'restaurant', 'the-green', 'The pizza and sub shop on Main, run '
          'by the same family since 1962: thin-crust pies, Italian sandwiches, and Friday night pickups for half '
          'the town.', ['pizza', 'subs', 'takeout', 'family-run'], '$', 'indoor', ALL,
          ['afternoon', 'evening'], cuisine='pizza'),
    place('haddon-town-hall', 'Haddon Harbor Town Hall', 'landmark', 'the-green', 'A white clapboard hall from '
          '1871 with a second-floor meeting room, creaking benches and a portrait of every first selectman. '
          'Select board meetings on Monday nights can get heated over parking, moorings or the school budget.',
          ['civic', 'meetings', 'historic', 'local-politics'], 'free', 'indoor', ['solo', 'friends'],
          ['morning', 'afternoon', 'evening']),
    place('abbott-library', 'Abbott Memorial Library', 'library', 'the-green', 'The town library in a granite '
          'building with a reading room, a fireplace, a seed library, lending bikes, story time on Wednesdays '
          'and a book sale every August that empties the basement.', ['library', 'quiet', 'story-time',
          'free'], 'free', 'indoor', ALL, DAYTIME),
    place('main-street-pharmacy', 'Main Street Pharmacy', 'shopping', 'the-green', 'An old-fashioned pharmacy '
          'with a soda fountain at the back where the pharmacist\'s family still makes frappes and lime rickeys, '
          'and a greeting-card rack that has not changed in decades.', ['pharmacy', 'soda-fountain',
          'old-fashioned'], '$', 'indoor', ALL, DAY),
    place('upstairs-yoga', 'Upstairs Yoga', 'fitness', 'the-green', 'A sunny yoga studio over the pharmacy, '
          'up a steep flight of stairs, with early flow classes, a gentle class popular with retirees and '
          'community classes by donation on Sundays.', ['yoga', 'classes', 'community'], '$', 'indoor',
          ['solo', 'friends'], ['morning', 'evening']),
    place('town-green', 'The Town Green', 'park', 'the-green', 'The green at the head of Main Street, with a '
          'bandstand for Thursday concerts, the war memorial, old elms, the Christmas tree in December and '
          'somebody walking a dog across it at any hour.', ['green', 'bandstand', 'concerts', 'heart-of-town'],
          'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
    place('farmers-market', 'Haddon Harbor Farmers Market', 'market', 'the-green', 'Saturday mornings on the '
          'green from May to October: farm vegetables, blueberries, goat cheese, smoked fish, maple syrup, '
          'flowers, bread and a fiddler by the bandstand.', ['farmers-market', 'local-food', 'saturdays'], '$',
          'outdoor', ALL, ['morning'], WARM),
    place('first-parish-vestry', 'First Parish Vestry', 'venue', 'the-green', 'The supper hall under the '
          'Congregational church, with long tables and a pass-through kitchen: bean suppers on the first '
          'Saturday, the strawberry supper in June and every funeral reception in town.', ['church-supper',
          'bean-supper', 'community'], '$', 'indoor', ['family', 'friends', 'solo'], ['evening']),
    place('elmwood-theatre', 'Elmwood Theatre', 'venue', 'the-green', 'A single-screen cinema from 1926 kept '
          'open by a nonprofit: second-run films, Wednesday five-dollar nights, real butter on the popcorn and a '
          'stage for the community players\' winter show.', ['cinema', 'theatre', 'nonprofit', 'historic'],
          '$', 'indoor', ALL, NIGHT),
    place('central-fire-station', 'Central Fire Station', 'landmark', 'the-green', 'Home of the volunteer fire '
          'department behind the town hall, with two engines, a ladder truck, a noon whistle and the Sunday '
          'pancake breakfasts that pay for new gear.', ['fire-station', 'volunteers', 'pancake-breakfast'],
          'free', 'mixed', ['family', 'solo'], ['morning']),
    # The Harbor
    place('town-fish-pier', 'Town Fish Pier', 'docks', 'the-harbor', 'The town pier where lobster boats tie up '
          'to unload, sell bait and take on fuel. The best seat in town at four in the afternoon, on an '
          'upturned crate, watching the boats come in.', ['working-waterfront', 'boats', 'lobster', 'views'],
          'free', 'outdoor', ALL, ['morning', 'afternoon']),
    place('lobster-co-op', 'Haddon Harbor Lobster Co-op', 'market', 'the-harbor', 'The lobstering co-op\'s '
          'wharf store, where you buy lobsters, crab meat and clams straight off the boats at the boat price, '
          'and someone will cook them for you in the steamer out back.', ['lobster', 'seafood', 'co-op',
          'off-the-boat'], '$$', 'mixed', ALL, DAY, cuisine='seafood'),
    place('coombs-wharf-shack', 'Coombs Wharf Lobster Shack', 'restaurant', 'the-harbor', 'A shack on pilings '
          'with picnic tables over the water: lobster rolls with butter or mayo (a matter of family loyalty), '
          'steamers, corn and blueberry pie. Open Memorial Day to Columbus Day and always a line.',
          ['lobster-roll', 'waterfront', 'picnic-tables', 'seasonal'], '$$', 'outdoor', ALL,
          ['afternoon', 'evening'], ['spring', 'summer', 'fall'], cuisine='seafood'),
    place('the-galley', 'The Galley', 'restaurant', 'the-harbor', 'A breakfast counter that opens at four for the '
          'lobster crews: eggs, home fries, coffee in heavy mugs and the marine forecast on the radio. Closes '
          'at noon, when the cook goes fishing.', ['breakfast', 'early', 'working-waterfront'], '$', 'indoor',
          ['solo', 'friends'], ['morning'], cuisine='diner'),
    place('ferry-landing-coffee', 'Ferry Landing Coffee Cart', 'cafe', 'the-harbor', 'A coffee cart at the '
          'ferry slip pouring drip coffee, iced coffee and hot chocolate for island commuters, with doughnuts '
          'from the bakery until they run out.', ['coffee', 'cart', 'ferry', 'seasonal'], '$', 'outdoor',
          ['solo', 'friends'], ['morning'], WARM, cuisine='coffee'),
    place('the-ropewalk', 'The Ropewalk', 'restaurant', 'the-harbor', 'The anniversary restaurant: a long room in '
          'an old rope-making shed with a view of the moorings, local oysters, halibut, a short wine list and '
          'reservations needed in August.', ['date-night', 'seafood', 'waterfront', 'special-occasion'], '$$$',
          'indoor', ['date', 'friends', 'family'], ['evening'], cuisine='new-england'),
    place('harbor-walk', 'Harbor Walk', 'trail', 'the-harbor', 'A boardwalk and gravel path along the '
          'waterfront from the fish pier to Dyer\'s Cove, with benches donated in memory of half the town and '
          'a view of every boat on its mooring.', ['waterfront', 'walking', 'benches', 'views'], 'free',
          'outdoor', ALL, ['morning', 'afternoon', 'evening']),
    place('schooner-meadowlark', 'Schooner Meadowlark', 'attraction', 'the-harbor', 'A two-masted wooden '
          'schooner that takes passengers out for two-hour sails around the islands, past seals and the '
          'lighthouse, with a sunset sail on Fridays.', ['sailing', 'schooner', 'tourists', 'sunset'], '$$$',
          'outdoor', ALL, ['afternoon', 'evening'], SUMMER),
    place('harbor-marine-supply', 'Harbor Marine Supply', 'shopping', 'the-harbor', 'A chandlery where rope, '
          'oilskins, buoy paint, wool socks and boat gossip are all on offer; locals buy their winter boots '
          'here, not at the mall.', ['chandlery', 'boots', 'boats', 'practical'], '$$', 'indoor',
          ['solo', 'friends'], DAY),
    place('harbormasters-float', "Harbormaster's Float", 'landmark', 'the-harbor', 'The little shingled office '
          'on the float where the harbourmaster keeps the mooring list (twenty years long), lends a dinghy, '
          'and chalks the tide times on a board.', ['harbor', 'tides', 'moorings'], 'free', 'outdoor',
          ['solo', 'family'], DAY, WARM),
    # Mill End
    place('kendall-mill-studios', 'Kendall Mill Studios', 'attraction', 'mill-end', 'Four floors of the old '
          'shoe mill turned into painters\', potters\', weavers\' and woodworkers\' studios, open on second '
          'Fridays with wine in paper cups, and all weekend in November for open studios.', ['art', 'studios',
          'makers', 'open-studios'], 'free', 'indoor', ALL, ['afternoon', 'evening']),
    place('weir-street-roasters', 'Weir Street Coffee Roasters', 'cafe', 'mill-end', 'A roaster in the mill\'s '
          'old boiler room, with the roasting drum behind glass, long tables for laptops, a cardamom bun worth '
          'the walk and the falls roaring outside.', ['coffee', 'roaster', 'laptops', 'riverside'], '$',
          'indoor', ['solo', 'friends', 'date'], DAY, cuisine='coffee'),
    place('mill-river-brewing', 'Mill River Brewing Co.', 'bar', 'mill-end', 'The brewery taproom in the mill\'s '
          'dye house: pale ales and a stout named after the noon whistle, a food truck in the yard, dogs '
          'welcome and a river deck in summer.', ['brewery', 'taproom', 'dog-friendly', 'deck'], '$$', 'mixed',
          ['friends', 'date', 'solo'], ['afternoon', 'evening'], cuisine='pub'),
    place('kendall-mill-dance', 'Kendall Mill School of Dance', 'fitness', 'mill-end', 'A dance school on the '
          'mill\'s top floor with sprung maple floors: ballet and tap for children, adult tap on Tuesday nights, '
          'and the June recital that fills the high school auditorium.', ['dance', 'classes', 'children',
          'recital'], '$$', 'indoor', ['solo', 'family', 'friends'], ['afternoon', 'evening']),
    place('mill-falls-park', 'Mill Falls Park', 'park', 'mill-end', 'A small park on the riverbank at the foot '
          'of the falls, with a fish ladder where people gather in May to watch the alewives run, and a bench '
          'everyone uses for proposals.', ['river', 'falls', 'alewives', 'picnics'], 'free', 'outdoor', ALL,
          ['morning', 'afternoon', 'evening']),
    place('the-carding-room', 'The Carding Room', 'venue', 'mill-end', 'An events room in the mill with iron '
          'columns and big windows: contra dances on second Saturdays, folk and bluegrass concerts, a winter '
          'film series and wedding receptions in between.', ['music', 'contra-dance', 'concerts', 'events'],
          '$$', 'indoor', ALL, NIGHT),
    place('weir-street-noodles', 'Weir Street Noodle Shop', 'restaurant', 'mill-end', 'A counter with eight '
          'stools serving pho, ramen and dumplings to artists, students and nurses, with a line at lunch and a '
          'chalkboard special that changes with whatever came off the boats.', ['noodles', 'lunch', 'casual'],
          '$', 'indoor', ['solo', 'friends', 'date'], ['afternoon', 'evening'], cuisine='asian'),
    place('kendall-clay', 'Kendall Clay Co-op', 'workshop', 'mill-end', 'A shared pottery studio with wheels, '
          'kilns and evening classes, where beginners make lopsided mugs for the diner\'s mug wall.',
          ['pottery', 'classes', 'makers'], '$$', 'indoor', ['solo', 'friends', 'date'], ['evening']),
    place('boiler-house-climbing', 'Boiler House Climbing', 'fitness', 'mill-end', 'A bouldering gym in the '
          'mill\'s old boiler house, with walls up to the coal chute and a regular Thursday crowd of college '
          'students, boatbuilders and a retired dentist who out-climbs them all.', ['climbing', 'bouldering',
          'gym'], '$$', 'indoor', ['solo', 'friends', 'date'], ['afternoon', 'evening']),
    # Packard Hill
    place('packard-house-inn', 'Packard House Inn', 'inn', 'packard-hill', 'The old inn at the top of the hill, '
          'a sea captain\'s house of 1820 with later wings, a wraparound porch of rocking chairs, wide-board '
          'floors, a Sunday brunch and weddings on the lawn all summer.', ['inn', 'historic', 'porch', 'brunch',
          'weddings'], '$$$', 'indoor', ['date', 'family', 'friends'], ['morning', 'afternoon', 'evening']),
    place('packard-tap-room', 'The Tap Room at the Packard', 'bar', 'packard-hill', 'The inn\'s low-ceilinged '
          'tavern with a fireplace, a few local beers, a good chowder and a regular crowd of locals who have '
          'had the same table on Fridays for twenty years.', ['tavern', 'fireplace', 'chowder', 'historic'],
          '$$', 'indoor', ['friends', 'date', 'solo'], NIGHT, cuisine='new-england'),
    place('packard-hill-lookout', 'Packard Hill Lookout', 'park', 'packard-hill', 'The open top of the hill with '
          'a bench and a view over the harbour to the islands: sunrise in summer, the sledding run in winter '
          'and fireworks on the Fourth.', ['views', 'sledding', 'sunrise'], 'free', 'outdoor', ALL,
          ['morning', 'afternoon', 'evening']),
    place('old-burying-ground', 'Old Burying Ground', 'landmark', 'packard-hill', 'The town\'s first cemetery, '
          'with slate stones carved with willows and ships, many for sailors lost at sea; the historical society '
          'gives lantern tours in October.', ['historic', 'cemetery', 'quiet', 'lantern-tours'], 'free',
          'outdoor', ['solo', 'friends'], DAY),
    place('three-chimneys-bnb', 'Three Chimneys Bed & Breakfast', 'inn', 'packard-hill', 'A five-room bed and '
          'breakfast in a captain\'s house, known for its blueberry-stuffed French toast and for the hosts '
          'knowing exactly which beach is quiet that day.', ['bed-and-breakfast', 'breakfast', 'historic'],
          '$$$', 'indoor', ['date', 'family'], ['morning'], cuisine='breakfast'),
    place('historical-society', 'Haddon Harbor Historical Society', 'museum', 'packard-hill', 'A small museum in '
          'a captain\'s house: ship portraits, a shoe from every year the mill ran, the town\'s old fire bell '
          'and a volunteer who will tell you who built your house.', ['history', 'maritime', 'volunteers'],
          '$', 'indoor', ALL, ['afternoon'], ['summer', 'fall']),
    place('st-brendans-hall', "St. Brendan's Parish Hall", 'venue', 'packard-hill', 'The Catholic parish hall '
          'on the far side of the hill, with Thursday bingo, a St. Patrick\'s corned beef supper and the '
          'Italian Christmas Eve fish dinner that the parish has served since the 1950s.', ['bingo', 'suppers',
          'parish', 'community'], '$', 'indoor', ['family', 'friends', 'solo'], ['evening']),
    # College Street
    place('whitcomb-quad', 'Whitcomb Quad', 'park', 'college-street', 'The sloping lawn at the heart of '
          'Whitcomb College, ringed by brick halls and old oaks, with frisbees in September, a snow sculpture '
          'contest in February and the town walking through it on the way to everything.', ['campus', 'lawn',
          'oaks'], 'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
    place('kimball-pool', 'Kimball Pool', 'fitness', 'college-street', 'The college pool in the athletic '
          'centre, open to town residents for early lap swim and Saturday family swim. The masters group swims '
          'at six whatever the weather outside.', ['pool', 'swimming', 'lap-swim', 'family-swim'], '$',
          'indoor', ['solo', 'family', 'friends'], ['morning', 'evening']),
    place('hathaway-museum', 'Hathaway Museum of Art', 'museum', 'college-street', 'Whitcomb College\'s free art '
          'museum: Maine landscapes, a room of folk portraits, student shows in the spring and a Thursday '
          'evening opening with cheese cubes and earnest conversation.', ['art', 'free', 'college'], 'free',
          'indoor', ALL, ['afternoon', 'evening']),
    place('college-street-coffee', 'College Street Coffee', 'cafe', 'college-street', 'A cafe in an old '
          'hardware store with tin ceilings, mismatched chairs, open mic on Wednesday and students writing '
          'theses beside retired professors doing the crossword.', ['coffee', 'students', 'open-mic', 'study'],
          '$', 'indoor', ['solo', 'friends', 'date'], DAYTIME, cuisine='coffee'),
    place('the-night-owl', 'The Night Owl', 'restaurant', 'college-street', 'A late-night grilled cheese and '
          'tomato soup counter that stays open until one on weekends, the only food in town after ten, staffed '
          'by students and loved by nurses coming off the late shift.', ['late-night', 'grilled-cheese',
          'students', 'cheap'], '$', 'indoor', ['friends', 'solo', 'date'], NIGHT, cuisine='american'),
    place('whitcomb-boathouse', 'Whitcomb Boathouse', 'fitness', 'college-street', 'The college boathouse on '
          'the Mill River estuary, home of the crew and the town rowing club, which takes beginners out in old '
          'eights at six in the morning from April to October.', ['rowing', 'river', 'club', 'early'], '$$',
          'outdoor', ['solo', 'friends'], ['morning', 'evening'], WARM),
    place('whitcomb-chapel', 'Whitcomb Chapel', 'venue', 'college-street', 'A granite chapel that is now the '
          'college\'s concert hall: the orchestra, the a cappella groups, visiting string quartets and a carol '
          'sing in December that the town never misses.', ['concerts', 'classical', 'carols', 'college'], '$',
          'indoor', ALL, ['evening']),
    place('spin-again-records', 'Spin Again Records', 'shopping', 'college-street', 'A secondhand record and '
          'tape shop in a basement, with a listening chair, a free bin, local band flyers and an owner with '
          'opinions about every album you pick up.', ['records', 'music', 'secondhand'], '$', 'indoor',
          ['solo', 'friends', 'date'], ['afternoon', 'evening']),
    # Birch Meadow
    place('birch-meadow-park', 'Birch Meadow Park', 'park', 'birch-meadow', 'A neighbourhood park with a big '
          'wooden playground the parents built in a weekend, a splash pad, a ball field and a skating rink the '
          'fire department floods in January.', ['playground', 'splash-pad', 'families'], 'free', 'outdoor',
          ['family', 'friends'], ['morning', 'afternoon']),
    place('meadow-variety', 'Meadow Variety', 'market', 'birch-meadow', 'The neighbourhood store: milk, scratch '
          'tickets, breakfast sandwiches, and Italian sandwiches on soft rolls with pickles and olives, wrapped '
          'in paper for the beach.', ['convenience', 'italian-sandwich', 'breakfast'], '$', 'indoor', ALL, DAY,
          cuisine='deli'),
    place('birch-meadow-courts', 'Birch Meadow Courts', 'fitness', 'birch-meadow', 'Four pickleball courts and '
          'two tennis courts that are never empty after five, with a sign-up board and a fierce morning league '
          'of retirees.', ['pickleball', 'tennis', 'outdoor'], 'free', 'outdoor', ['friends', 'solo'],
          ['morning', 'evening'], WARM),
    place('meadow-community-garden', 'Birch Meadow Community Garden', 'garden', 'birch-meadow', 'Forty raised '
          'beds behind the elementary school, with a shared tool shed, a zucchini giveaway table in August and '
          'a waiting list.', ['garden', 'community', 'vegetables'], 'free', 'outdoor', ['solo', 'family'],
          ['morning', 'evening'], WARM),
    place('golden-harbor-chinese', 'Golden Harbor Chinese Restaurant', 'restaurant', 'birch-meadow', 'The '
          'Chinese-American restaurant in the little plaza: crab rangoon, pu pu platters, a lounge with a '
          'fish tank, and Christmas Eve takeout orders that start in November.', ['chinese-american',
          'takeout', 'family'], '$', 'indoor', ALL, ['afternoon', 'evening'], cuisine='chinese-american'),
    place('birch-meadow-dog-park', 'Birch Meadow Dog Park', 'park', 'birch-meadow', 'A fenced acre of pines '
          'where the same dog owners meet every morning, know each dog\'s name and not always each other\'s.',
          ['dogs', 'community', 'morning'], 'free', 'outdoor', ['solo', 'friends'], ['morning', 'evening']),
    # Ridge Road
    place('higgins-hill-orchard', 'Higgins Hill Orchard', 'market', 'ridge-road', 'A hillside orchard with '
          'pick-your-own apples in the fall, cider pressed in the barn, cider doughnuts, a corn maze and a view '
          'down to the bay from the top row of Macouns.', ['orchard', 'apples', 'cider-doughnuts',
          'pick-your-own'], '$', 'outdoor', ALL, DAY, ['summer', 'fall'], cuisine='farm'),
    place('ridge-road-farm-stand', 'Ridge Road Farm Stand', 'market', 'ridge-road', 'An honour-system stand at '
          'the end of a farm driveway: eggs in the cooler, sweet corn, pies on Saturdays, flowers in buckets '
          'and a cash box nobody has ever locked.', ['farm-stand', 'honor-system', 'eggs', 'corn'], '$',
          'outdoor', ALL, DAY, WARM, cuisine='farm'),
    place('ridge-road-antiques', 'Ridge Road Antique Barn', 'shopping', 'ridge-road', 'Three floors of a cow barn '
          'packed with dealers\' booths: lobster buoys, quilts, oyster plates, old tools and furniture that '
          'needs a truck. Bring cash and time.', ['antiques', 'barn', 'browsing'], '$$', 'indoor', ALL, DAY),
    place('tibbetts-sugarhouse', 'Tibbetts Sugarhouse', 'attraction', 'ridge-road', 'A family sugarhouse that '
          'boils sap from four thousand taps, with steam pouring out the roof in March, syrup on snow for '
          'children and maple cream sold from the house all year.', ['maple', 'sugarhouse', 'farm'], '$',
          'mixed', ['family', 'friends', 'date'], DAY, ['winter', 'spring']),
    place('bickford-dairy-bar', 'Bickford Dairy Bar', 'restaurant', 'ridge-road', 'A dairy farm\'s ice cream '
          'window with picnic tables facing the cows: black raspberry, maple walnut, kiddie cones bigger than '
          'the kiddies, and a line every hot evening.', ['ice-cream', 'farm', 'summer-evenings'], '$', 'outdoor',
          ALL, ['afternoon', 'evening'], ['spring', 'summer'], cuisine='ice-cream'),
    place('ridge-grange-hall', 'Ridge Grange Hall', 'venue', 'ridge-road', 'The grange hall on the crossroads, '
          'with a stage and a sprung floor: contra dances, a winter farmers market on Saturdays, community '
          'suppers and the 4-H show.', ['grange', 'community', 'dances', 'winter-market'], '$', 'indoor', ALL,
          ['morning', 'evening']),
    place('ridge-road-veterinary', 'Ridge Road Veterinary Clinic', 'vet', 'ridge-road', 'The town vet in a '
          'converted farmhouse, treating dogs, cats, goats and the occasional cow, with pet supplies in the '
          'front room and a waiting room where everyone compares notes on their animals.', ['veterinarian', 'animals', 'practical'], '$$',
          'indoor', ['solo', 'family'], DAY),
    place('haddon-fairgrounds', 'Haddon Harbor Fairgrounds', 'venue', 'ridge-road', 'The fairgrounds with the '
          'exhibition barns, a half-mile track and the pie tent: busy for the harvest fair in September and '
          'used for the ox pull, the dog show and the flea market the rest of the season.', ['fair',
          'agricultural', 'community'], '$', 'outdoor', ALL, DAYTIME, WARM),
    # Ledge Point
    place('ledge-point-light', 'Ledge Point Light', 'landmark', 'ledge-point', 'A white brick lighthouse from '
          '1857 on the granite at the harbour mouth, with a red-roofed keeper\'s house, a foghorn the town hears '
          'on thick nights, and the best sunsets on this side of the bay.', ['lighthouse', 'views', 'photos',
          'sunset'], 'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
    place('keepers-house-museum', "Keeper's House Museum", 'museum', 'ledge-point', 'The lighthouse keeper\'s '
          'house kept as a museum, with logbooks, the old Fresnel lens, a keeper\'s kitchen and a climb to the '
          'lantern on summer Saturdays.', ['lighthouse', 'history', 'maritime'], '$', 'indoor', ALL,
          ['afternoon'], SUMMER),
    place('ledge-point-park', 'Ledge Point Park', 'park', 'ledge-point', 'Lawns and ledges around the '
          'lighthouse with picnic tables, tide pools full of periwinkles and crabs, and a bench where people '
          'scatter ashes and watch boats.', ['tide-pools', 'picnics', 'rocky-shore'], 'free', 'outdoor', ALL,
          ['morning', 'afternoon', 'evening']),
    place('sand-cove-beach', 'Sand Cove Beach', 'beach', 'ledge-point', 'A small crescent of real sand on a '
          'coast of rocks, cold enough to make your ankles ache even in August, with families on towels and '
          'teenagers daring each other to swim to the float.', ['beach', 'swimming', 'cold-water'], 'free',
          'outdoor', ALL, ['morning', 'afternoon'], SUMMER),
    place('keepers-kitchen', "The Keeper's Kitchen", 'cafe', 'ledge-point', 'A summer cafe in the old oil house '
          'by the lighthouse: coffee, blueberry muffins, crab rolls and lemonade at tables on the grass.',
          ['cafe', 'seasonal', 'lighthouse'], '$', 'outdoor', ALL, DAY, SUMMER, cuisine='cafe'),
    place('ledge-point-trail', 'Ledge Point Trail', 'trail', 'ledge-point', 'A rough two-mile trail through '
          'spruce and over ledges from the cottages to the lighthouse, with a fog bell you can hear from the '
          'woods and raspberries in late July.', ['hiking', 'spruce', 'ocean-views'], 'free', 'outdoor',
          ['solo', 'friends', 'date'], DAY),
    place('ledge-point-chowder-house', 'Ledge Point Chowder House', 'restaurant', 'ledge-point', 'A shingled '
          'summer restaurant on the point road: haddock chowder, fried clams, a fish fry on Fridays and a deck '
          'that catches the last of the sun.', ['chowder', 'fried-clams', 'deck', 'seasonal'], '$$', 'mixed',
          ALL, ['afternoon', 'evening'], ['summer', 'fall'], cuisine='seafood'),
    # Long Pond
    place('long-pond-town-beach', 'Long Pond Town Beach', 'beach', 'long-pond', 'A sandy town beach on the pond '
          'with a lifeguard chair, a roped swim area, a raft to swim out to and warm, clear water that tempts '
          'the people who will not swim in the ocean.', ['lake', 'swimming', 'lifeguard', 'families'], 'free',
          'outdoor', ALL, ['morning', 'afternoon'], SUMMER),
    place('camp-hemlock', 'Camp Hemlock', 'attraction', 'long-pond', 'A children\'s summer camp since 1921, '
          'with cabins, canoes, a dining hall and an end-of-summer song night that former campers come back '
          'for decades later.', ['summer-camp', 'canoes', 'tradition'], '$$$', 'outdoor', ['family'],
          ['morning', 'afternoon', 'evening'], SUMMER),
    place('camp-tall-pines', 'Camp Tall Pines', 'attraction', 'long-pond', 'A day camp on the north shore with '
          'swimming, archery and sailing lessons for town children, and family open house nights with a '
          'campfire.', ['day-camp', 'campfire', 'children'], '$$', 'outdoor', ['family'], DAYTIME, SUMMER),
    place('long-pond-store', 'Long Pond Store', 'cafe', 'long-pond', 'A general store on the pond road selling '
          'coffee, crawlers, gas, whoopie pies, hand-cut fries and slices of pie, with a porch where camp '
          'people trade news about loons and water levels.', ['general-store', 'coffee', 'pie', 'porch'], '$',
          'indoor', ALL, DAY, cuisine='cafe'),
    place('long-pond-boat-rentals', 'Long Pond Boat Rentals', 'attraction', 'long-pond', 'Canoes, kayaks and '
          'paddleboards by the hour from a dock by the store, with a map of the coves where the loons nest.',
          ['canoe', 'kayak', 'paddleboard', 'lake'], '$$', 'outdoor', ALL, DAY, SUMMER),
    place('loon-cove-trail', 'Loon Cove Trail', 'trail', 'long-pond', 'A three-mile woods walk along the east '
          'shore of the pond to a quiet cove, flat and needle-soft, good for snowshoes in winter.',
          ['woods', 'lake', 'snowshoe'], 'free', 'outdoor', ['solo', 'friends', 'family', 'date'], DAY),
    # The Route 1 Strip
    place('grays-market', "Gray's Market", 'market', 'route-1', 'The town grocery, family owned: a good meat '
          'counter, local milk, a deli that knows your order, and the bulletin board by the door that is the '
          'real town newspaper.', ['grocery', 'deli', 'bulletin-board', 'local'], '$$', 'indoor', ALL,
          DAYTIME),
    place('hobbs-hardware', 'Hobbs Hardware', 'shopping', 'route-1', 'The hardware store, with a popcorn '
          'machine by the register, a coffee pot for contractors, keys cut while you wait, bins of nails sold '
          'by the pound and a clerk who can tell you exactly what you need.', ['hardware', 'popcorn',
          'practical', 'advice'], '$$', 'indoor', ALL, DAY),
    place('harbor-fitness', 'Harbor Fitness', 'fitness', 'route-1', 'A plain, friendly gym in the old bowling '
          'supply building, with free weights, a spin room, early classes for lobster crews and a front desk '
          'that knows everyone\'s schedule.', ['gym', 'classes', 'early'], '$$', 'indoor',
          ['solo', 'friends'], ['morning', 'afternoon', 'evening']),
    place('haddon-ice-arena', 'Haddon Harbor Ice Arena', 'fitness', 'route-1', 'The community ice rink: youth '
          'hockey before dawn, public skate on Saturday afternoons, adult pickup on Sunday nights and the high '
          'school team\'s home ice, with a snack bar and a cold bench.', ['ice-rink', 'skating', 'hockey'], '$',
          'indoor', ALL, ['morning', 'afternoon', 'evening'], ['winter', 'fall', 'spring']),
    place('route-1-coffee-shack', 'Route 1 Coffee Shack', 'cafe', 'route-1', 'A drive-through coffee hut in the '
          'grocery lot with a walk-up window, a dog biscuit for every dog in the car and a punch card everybody '
          'has three of.', ['coffee', 'drive-through', 'quick'], '$', 'outdoor', ['solo'], ['morning'],
          cuisine='coffee'),
    place('captains-catch', "Captain's Catch", 'restaurant', 'route-1', 'A fried-seafood takeout window with '
          'picnic tables beside the parking lot: clam strips, haddock baskets, onion rings and a crab roll, '
          'open from April to October.', ['fried-seafood', 'takeout', 'picnic-tables'], '$', 'outdoor', ALL,
          ['afternoon', 'evening'], WARM, cuisine='seafood'),
    place('auxiliary-thrift-shop', 'Hospital Auxiliary Thrift Shop', 'shopping', 'route-1', 'The thrift shop '
          'run by hospital volunteers, where summer people\'s cast-offs end up: wool sweaters, cast iron, '
          'board games with most of the pieces and a bag sale on the last Saturday.', ['thrift', 'volunteers',
          'bargains'], '$', 'indoor', ALL, DAY),
    place('route-1-candlepin', 'Route 1 Candlepin Lanes', 'venue', 'route-1', 'Twelve lanes of candlepin, the '
          'skinny-pin, small-ball bowling of New England, with league nights, birthday parties, cheap pitchers '
          'and a scoreboard that still needs a pencil.', ['bowling', 'candlepin', 'leagues', 'retro'], '$',
          'indoor', ALL, ['afternoon', 'evening', 'late']),
    # South Haddon
    place('south-haddon-store', 'South Haddon General Store', 'cafe', 'south-haddon', 'A general store with a '
          'porch bench, a woodstove, coffee, breakfast sandwiches, pie by the slice and a post office counter '
          'at the back, where the village checks in every morning.', ['general-store', 'coffee', 'post-office',
          'porch'], '$', 'indoor', ALL, DAY, cuisine='cafe'),
    place('tide-mill-restaurant', 'Tide Mill Restaurant', 'restaurant', 'south-haddon', 'A farm-to-table '
          'restaurant in a restored tide mill over the marsh, with a short menu that changes daily and a waiting '
          'list people from the city drive up for.', ['farm-to-table', 'special-occasion', 'marsh-views'],
          '$$$$', 'indoor', ['date', 'friends', 'family'], ['evening'], WARM, cuisine='new-american'),
    place('south-haddon-landing', 'South Haddon Town Landing', 'docks', 'south-haddon', 'A gravel ramp and a '
          'float where skiffs and kayaks put in, with a bench, a view up the river and someone always digging '
          'clams on the flats at low tide.', ['landing', 'clamming', 'kayaks'], 'free', 'outdoor', ALL, DAY),
    place('south-haddon-common', 'South Haddon Common', 'park', 'south-haddon', 'The village common with a '
          'gazebo, a horse trough turned flower bed and the white Union church, where the village holds its '
          'own Fourth of July and its own opinions.', ['village-green', 'gazebo', 'church'], 'free', 'outdoor',
          ALL, ['morning', 'afternoon', 'evening']),
    place('pratt-marsh-preserve', 'Pratt Marsh Preserve', 'trail', 'south-haddon', 'Land trust trails and a '
          'boardwalk across the salt marsh, with herons, ospreys on the nesting platform, and a blind where '
          'birders sit in silence at dawn.', ['marsh', 'birding', 'boardwalk', 'land-trust'], 'free', 'outdoor',
          ['solo', 'friends', 'family', 'date'], DAY),
    place('the-rusty-hinge', 'The Rusty Hinge', 'bar', 'south-haddon', 'The village tavern in a former '
          'blacksmith shop: a pool table, two drafts, a jukebox and a cribbage tournament on Wednesday nights '
          'that the same retired lobstering couple wins every year.', ['tavern', 'cribbage', 'pool', 'locals'],
          '$', 'indoor', ['friends', 'solo'], NIGHT, cuisine='pub'),
    # Tarbox Island
    place('tarbox-ferry-landing', 'Tarbox Ferry Landing', 'docks', 'tarbox-island', 'The island ferry slip, '
          'where trucks, groceries, mail and gossip come ashore, and half the island turns up to meet the last '
          'boat on Friday.', ['ferry', 'island-life', 'landing'], 'free', 'outdoor', ALL, DAYTIME),
    place('tarbox-island-store', 'Tarbox Island Store', 'cafe', 'tarbox-island', 'The one store on the island: '
          'groceries, hardware, coffee, chowder on Fridays, a lending shelf of paperbacks and the only public '
          'phone. Closed Sunday afternoons.', ['island-store', 'coffee', 'chowder', 'groceries'], '$', 'indoor',
          ALL, DAY, cuisine='cafe'),
    place('tarbox-community-hall', 'Tarbox Community Hall', 'venue', 'tarbox-island', 'The island\'s hall above '
          'the school, for potluck suppers, town meeting, square dances in summer and a talent show every '
          'February that is the best entertainment of the winter.', ['community', 'potluck', 'dances'], 'free',
          'indoor', ALL, ['evening']),
    place('tarbox-loop-road', 'Tarbox Loop Road', 'trail', 'tarbox-island', 'Seven miles of narrow road around '
          'the island past lobster gear, spruce and the open ocean side, walked or biked by summer people and '
          'driven very slowly by islanders who wave at all of them.', ['island', 'walking', 'cycling',
          'ocean-views'], 'free', 'outdoor', ALL, DAY),
    place('tarbox-lobster-wharf', 'Tarbox Lobster Wharf', 'market', 'tarbox-island', 'The island lobstering '
          'co-op\'s wharf, where you can buy lobsters from the tank and eat them at a picnic table on the pier '
          'while the boats unload beside you.', ['lobster', 'co-op', 'wharf'], '$$', 'outdoor', ALL, DAY,
          WARM, cuisine='seafood'),
    place('tarbox-island-inn', 'Tarbox Island Inn', 'inn', 'tarbox-island', 'A rambling summer inn above the '
          'harbour with rocking chairs facing the mainland, family-style dinners and rooms with no locks and no '
          'televisions.', ['inn', 'island', 'summer', 'family-style'], '$$$', 'indoor', ['date', 'family',
          'friends'], ['morning', 'evening'], SUMMER, cuisine='new-england'),
    place('tarbox-long-beach', 'Tarbox Long Beach', 'beach', 'tarbox-island', 'A long sand beach on the far '
          'side of the island, often empty, with sea glass at the tide line and cold surf.', ['beach',
          'sea-glass', 'quiet'], 'free', 'outdoor', ALL, ['morning', 'afternoon'], SUMMER),
    # Dyer's Cove
    place('dyers-cove-marina', "Dyer's Cove Marina", 'docks', 'dyers-cove', 'The marina beside the boatyard, '
          'with sailboats and lobster boats side by side, a fuel dock, showers for cruising sailors and boat '
          'shrink-wrap glowing white in the yard all winter.', ['marina', 'boats', 'sailing'], 'free', 'outdoor',
          ALL, DAY, WARM),
    place('boatyard-grill', 'The Boatyard Grill', 'restaurant', 'dyers-cove', 'A bar and grill upstairs at the '
          'marina, with burgers, fish tacos and a deck over the floats; boatbuilders at lunch, sailors at '
          'sunset, and a locals\' night on Thursdays in winter.', ['grill', 'deck', 'marina', 'locals-night'],
          '$$', 'mixed', ALL, ['afternoon', 'evening'], cuisine='american'),
    place('community-sailing', 'Haddon Harbor Community Sailing', 'fitness', 'dyers-cove', 'A nonprofit '
          'sailing centre with small boats for lessons, adult evening races on Wednesdays and kids learning to '
          'capsize on purpose in July.', ['sailing', 'lessons', 'racing', 'nonprofit'], '$$', 'outdoor', ALL,
          ['morning', 'afternoon', 'evening'], SUMMER),
    place('cove-variety', 'Cove Variety', 'market', 'dyers-cove', 'A corner store that opens at five for the '
          'boatyard crews: breakfast pizza, coffee, bait, lottery tickets and the best-informed person in town '
          'behind the counter.', ['convenience', 'breakfast-pizza', 'early'], '$', 'indoor', ALL, DAY,
          cuisine='deli'),
    place('legion-post', 'American Legion Post 41', 'bar', 'dyers-cove', 'The Legion post on the cove road, '
          'with cheap drafts, a meat raffle on Saturdays, the Memorial Day breakfast and a hall rented for '
          'every retirement party and baby shower in town.', ['legion', 'cheap-drinks', 'meat-raffle',
          'community'], '$', 'indoor', ['friends', 'solo'], NIGHT),
    place('harbor-paddle', 'Harbor Paddle', 'attraction', 'dyers-cove', 'Sea kayak rentals and guided paddles '
          'from the cove out to the seal ledges and around Ledge Point, with sunrise trips for the keen.',
          ['kayaking', 'guided', 'seals'], '$$', 'outdoor', ['friends', 'date', 'solo', 'family'], DAY, SUMMER),
    # West End
    place('high-school-field', 'Haddon Harbor High School Field', 'stadium', 'west-end', 'The high school field '
          'with aluminium bleachers and a concession stand run by the boosters: Friday night football under '
          'the lights, soccer in the rain, and the Fourth of July fireworks launched from the far end.',
          ['high-school', 'football', 'friday-nights', 'boosters'], '$', 'outdoor', ALL,
          ['afternoon', 'evening'], ['fall', 'spring']),
    place('cobb-pond', 'Cobb Pond', 'park', 'west-end', 'A small pond the fire department tests and flags for '
          'skating each winter, with a warming hut, a bonfire barrel, cocoa sold by the eighth grade and boot '
          'prints from every child in town.', ['skating', 'pond', 'warming-hut', 'winter'], 'free', 'outdoor',
          ALL, ['afternoon', 'evening'], ['winter']),
    place('kearneys-pub', "Kearney's Pub", 'bar', 'west-end', 'An Irish pub across from the hospital, with a '
          'Guinness poured slowly, shepherd\'s pie, a session on Sunday afternoons and a corner where night '
          'nurses unwind at eight in the morning.', ['irish-pub', 'session', 'nurses'], '$$', 'indoor',
          ['friends', 'solo', 'date'], ['afternoon', 'evening', 'late'], cuisine='irish'),
    place('rizzos-market', "Rizzo's Market", 'market', 'west-end', 'An Italian grocery and deli from the days '
          'when Italian stonecutters worked the quarries: imported pasta, homemade sausage, Italian sandwiches '
          'and a Christmas order of baccala.', ['italian', 'deli', 'sausage', 'family-run'], '$', 'indoor', ALL,
          DAY, cuisine='italian'),
    place('the-spin-cycle', 'The Spin Cycle', 'cafe', 'west-end', 'A laundromat with an espresso machine and a '
          'pastry case, where a wash, a latte and the local paper make a Sunday morning, and the bulletin '
          'board sells everything from firewood to kittens.', ['laundromat', 'coffee', 'bulletin-board'], '$',
          'indoor', ['solo', 'friends'], DAY, cuisine='coffee'),
    place('west-end-rec-center', 'West End Recreation Center', 'fitness', 'west-end', 'The town rec centre in '
          'an old school gym: pickup basketball, Zumba, a senior walking club in winter and after-school '
          'programs that half the parents in town depend on.', ['gym', 'basketball', 'community', 'seniors'],
          '$', 'indoor', ['solo', 'friends', 'family'], ['morning', 'afternoon', 'evening']),
    # The Back Shore
    place('back-shore-path', 'Back Shore Path', 'trail', 'back-shore', 'A public right of way along the '
          'cliffs, over granite ledges and past summer cottages\' lawns, with surf booming below in a storm '
          'and wild roses in June.', ['cliff-walk', 'ocean', 'walking', 'views'], 'free', 'outdoor', ALL,
          ['morning', 'afternoon', 'evening']),
    place('cobble-beach', 'Cobble Beach', 'beach', 'back-shore', 'A steep beach of rounded stones that roar '
          'when the waves pull back, good for skipping stones and a bracing dip, and for the New Year\'s Day '
          'plunge.', ['beach', 'stones', 'polar-plunge'], 'free', 'outdoor', ALL, ['morning', 'afternoon']),
    place('beach-plum-cafe', 'The Beach Plum', 'cafe', 'back-shore', 'A summer cafe in a shingled cottage with '
          'coffee, scones, lobster salad on croissants and beach plum jam, and Adirondack chairs facing the '
          'open ocean.', ['cafe', 'seasonal', 'ocean-views'], '$$', 'mixed', ALL, DAY, SUMMER, cuisine='cafe'),
    place('back-shore-links', 'Back Shore Links', 'attraction', 'back-shore', 'A nine-hole golf course from '
          'the 1890s on the ocean bluff, windy, cheap after four, and played by retired lobstering families and '
          'summer people in the same foursome.', ['golf', 'ocean', 'historic'], '$$', 'outdoor',
          ['solo', 'friends'], ['morning', 'afternoon', 'evening'], WARM),
    place('back-shore-chapel', 'Back Shore Chapel', 'landmark', 'back-shore', 'A tiny shingled chapel open only '
          'in July and August, with Sunday services, the windows open to the sound of the surf, and a lot of '
          'small weddings.', ['chapel', 'weddings', 'seasonal', 'quiet'], 'free', 'indoor',
          ['solo', 'family', 'date'], ['morning'], SUMMER),
    place('back-shore-lobster-pound', 'Back Shore Lobster Pound', 'restaurant', 'back-shore', 'A lobster pound '
          'on the cove where you pick your lobster from the tank, they steam it in seawater over a wood fire, '
          'and you eat it at a picnic table with your own bottle of wine.', ['lobster', 'byob', 'picnic-tables',
          'sunset'], '$$', 'outdoor', ALL, ['afternoon', 'evening'], SUMMER, cuisine='seafood'),
]

CITY = {
    'schema_version': 1, 'id': 'haddon-harbor', 'name': 'Haddon Harbor', 'setting': 'original', 'era': 'modern',
    'basis': 'Original setting written for Prospero Companion, modelled on real Maine coastal towns.',
    'region': 'Maine', 'country': 'US', 'timezone': 'America/New_York',
    'aliases': ['Haddon Harbor, Maine', 'Haddon Harbor, ME'],
    'summary': 'A harbour town of about nine thousand on the Maine coast, where the lobster boats leave before '
               'dawn, the diner keeps a wall of regulars\' mugs, town meeting runs late every March and '
               'everyone knows everyone, including what they said at the last select board meeting.',
    'lat': 43.970, 'lon': -69.300,
    'speeds': {'walk': 4.5, 'car': 40, 'bus': 22, 'ferry': 15, 'bike-share': 14},
    # Rough heritage weights for a midcoast Maine town: mostly old Yankee and Irish families, an Italian
    # community from the quarry days and a little of everywhere through the college and hospital.
    'names': {'mix': {'anglo': 7, 'irish': 2, 'french-canadian': 1.5, 'italian': 0.8, 'jewish': 0.2, 'slavic': 0.2, 'hispanic': 0.3,
                       'black-american': 0.2, 'east-asian': 0.2, 'south-asian': 0.15, 'arabic': 0.1,
                       'west-african': 0.1}},
    'sources': {
        S: {'kind': 'curated', 'title': 'Haddon Harbor, an original setting written for Prospero Companion',
            'license': 'CC0-1.0', 'retrieved': '2026-10-10',
            'note': 'Invented town with no real counterpart; every business, institution and person named is '
                    'fictional. Its texture follows ordinary life in midcoast Maine harbour towns: working '
                    'waterfronts and lobstering co-ops, town meeting, bean suppers, grange halls, summer '
                    'people, mud season and island ferries. Rents are rounded typical asking ranges for a small '
                    'Maine town in 2026. Climate is rounded from midcoast Maine normals.'},
    },
    'neighborhoods': HOODS,
    'places': PLACES,
    'transit': [
        line(SHUTTLE, 'Harbor Summer Shuttle', 'bus', 'A free open-sided shuttle bus run by the town from late '
             'June to Labor Day, looping every half hour from Main Street to the harbour, Packard Hill, Dyer\'s '
             'Cove, Ledge Point and the Back Shore.'),
        line(FERRY, 'Tarbox Island Ferry', 'ferry', 'The car ferry from the town pier to Tarbox Island, forty '
             'minutes each way, four round trips a day in winter and seven in summer, with reservations for cars '
             'and a deckhand who knows every islander\'s order.'),
        line(BIKES, 'Library loaner bikes', 'bike-share', 'Sturdy town bikes borrowed with a library card from '
             'racks at the library, the harbour, the college, the mill and the hospital, April to November.'),
        line('car', 'Car', 'car', 'How most people get around beyond the village: Route 1, the Augusta road and '
             'the back roads to the pond, the farms and South Haddon.'),
        line('walk', 'On foot', 'walk', 'The village, the harbour, the mill and the college are all within a '
             'fifteen-minute walk of the green.'),
    ],
    'colleges': [
        {'id': 'whitcomb-college', 'name': 'Whitcomb College', 'type': 'liberal-arts-college',
         'neighborhood': 'college-street', 'size': 'small', 'known_for': ['liberal-arts', 'marine-biology',
         'environmental-studies', 'creative-writing', 'music', 'rowing'], 'source': S},
    ],
    'employers': [
        employer('whitcomb-college-employer', 'Whitcomb College', 'education', 'college-street', 'medium', 'A '
                 'liberal arts college of about 1,800 students and the town\'s largest employer after the '
                 'hospital: faculty, a small marine lab, dining, grounds and admissions.',
                 ['professor', 'biologist', 'data-analyst', 'marketing-coordinator', 'event-planner', 'accountant',
                  'software-engineer']),
        employer('sewall-memorial-hospital', 'Sewall Memorial Hospital', 'healthcare', 'west-end', 'medium',
                 'A community hospital with an emergency department, a birthing centre and clinics that serve '
                 'the whole peninsula and the islands.', ['registered-nurse', 'night-nurse', 'physician-resident',
                 'pharmacist', 'social-worker', 'medical-researcher']),
        employer('hatch-boatyard', 'Hatch Boatyard', 'marine-trades', 'dyers-cove', 'medium', 'A family '
                 'boatyard in its fourth generation, building wooden and composite lobster boats, storing and '
                 'repairing yachts and running the marina.', ['boatbuilder', 'construction-trades',
                 'marketing-coordinator']),
        employer('kendall-mill', 'Kendall Mill', 'arts', 'mill-end', 'small', 'The old shoe mill, now owned by a '
                 'nonprofit that rents studios, runs the events room and shares a floor with a small design '
                 'firm and a software startup.', ['graphic-designer', 'ux-designer', 'musician',
                 'software-engineer', 'event-planner']),
        employer('haddon-harbor-schools', 'Haddon Harbor School Department', 'education', 'west-end', 'medium',
                 'The town\'s schools: the elementary in Birch Meadow, the middle and high schools in the West '
                 'End, and the one-room school on Tarbox Island.', ['teacher', 'social-worker']),
        employer('lobster-co-op-employer', 'Haddon Harbor Lobster Co-op', 'fishing', 'the-harbor', 'small', 'The '
                 'lobstering co-op owned by about sixty boats, buying their catch, selling bait and fuel, and '
                 'shipping lobster by truck to Boston and beyond.', ['lobster-fisher', 'port-logistics',
                 'retail-associate']),
        employer('packard-house-employer', 'Packard House Inn', 'hospitality', 'packard-hill', 'small', 'The old '
                 'inn on the hill with its tavern and wedding lawn, busy all summer and quiet but open all '
                 'winter.', ['innkeeper', 'hotel-front-desk', 'server', 'line-cook', 'bartender', 'event-planner']),
        employer('town-of-haddon-harbor', 'Town of Haddon Harbor', 'government', 'the-green', 'medium', 'The town '
                 'office, public works, the harbourmaster, the library, the rec department and the summer '
                 'lifeguards at the town beaches.', ['government-analyst', 'accountant', 'lifeguard',
                 'social-worker']),
        employer('hobbs-hardware-employer', 'Hobbs Hardware', 'retail', 'route-1', 'small', 'The family hardware '
                 'store, which also runs the lumber yard behind it and delivers to the island on Tuesdays.',
                 ['retail-associate']),
        employer('granite-coast-savings', 'Granite Coast Savings Bank', 'finance', 'the-green', 'medium', 'A '
                 'regional savings bank with its headquarters in the brick block on Main Street and branches up '
                 'and down the coast.', ['finance-banker', 'financial-analyst', 'accountant', 'data-analyst']),
        employer('mill-river-brewing-employer', 'Mill River Brewing Co.', 'food', 'mill-end', 'small', 'The '
                 'brewery in the mill, which brews, cans and ships its beer around New England and runs the '
                 'taproom.', ['bartender', 'line-cook', 'marketing-coordinator']),
        employer('grays-market-employer', "Gray's Market", 'retail', 'route-1', 'small', 'The family grocery, '
                 'with a bakery and deli counter that start before dawn.', ['retail-associate', 'baker']),
        employer('haddon-harbor-register', 'The Haddon Harbor Register', 'media', 'the-green', 'small', 'The '
                 'weekly town paper, founded in 1858, with a newsroom of four, a police log everyone reads first '
                 'and a website that went up in 2009.', ['journalist', 'graphic-designer']),
        employer('higgins-hill-employer', 'Higgins Hill Orchard', 'agriculture', 'ridge-road', 'small', 'The '
                 'orchard and farm store, with a few year-round hands and a crowd of pickers and cider makers '
                 'in the fall.', ['orchard-farmer', 'retail-associate']),
        employer('harbor-and-hill-realty', 'Harbor & Hill Realty', 'real-estate', 'the-green', 'small', 'The '
                 'busiest estate agency in town, selling summer cottages and finding winter rentals.',
                 ['real-estate-agent']),
        employer('schooner-meadowlark-employer', 'Schooner Meadowlark', 'tourism', 'the-harbor', 'small', 'The '
                 'windjammer day-sail business, hiring a captain, mates and guides every summer.',
                 ['tour-guide']),
    ],
    'career_hubs': [
        {'id': 'main-street-hub', 'name': 'Main Street shops and offices', 'neighborhoods': ['the-green',
         'packard-hill'], 'sectors': ['retail', 'hospitality', 'government', 'finance', 'media', 'real-estate',
         'food'], 'summary': 'The town office, the bank, the paper, the shops, the inns and the restaurants '
         'around the green.', 'source': S},
        {'id': 'waterfront-hub', 'name': 'The waterfront', 'neighborhoods': ['the-harbor', 'dyers-cove',
         'tarbox-island'], 'sectors': ['fishing', 'marine-trades', 'tourism', 'logistics', 'recreation'],
         'summary': 'The fish pier, the co-ops, the boatyard, the marina, the ferry and the summer boat '
         'businesses.', 'source': S},
        {'id': 'college-and-hospital-hub', 'name': 'The college and the hospital', 'neighborhoods':
         ['college-street', 'west-end'], 'sectors': ['education', 'healthcare', 'social-services'], 'summary':
         'Whitcomb College, Sewall Memorial Hospital and the schools.', 'source': S},
        {'id': 'route-1-hub', 'name': 'Route 1 and the farms', 'neighborhoods': ['route-1', 'ridge-road',
         'mill-end'], 'sectors': ['retail', 'agriculture', 'construction', 'fitness', 'arts', 'technology'],
         'summary': 'The grocery, the hardware store and lumber yard, the gym, the farms and the mill\'s '
         'studios and small firms.', 'source': S},
    ],
    'careers': [
        career('lobster-fisher', 'Lobster fisher', 'fishing', 'early', '$$', 'Hauls traps from a lobster boat, '
               'as a sternman or with a boat and a licence of their own, out before dawn and back mid-afternoon.',
               ['weather', 'the boat', 'trap limits', 'prices at the co-op', 'early mornings', 'the sea']),
        career('boatbuilder', 'Boatbuilder', 'marine-trades', 'shift-day', '$$', 'Builds and repairs wooden and '
               'fibreglass boats at the boatyard: lofting, planking, glassing, painting and launching in spring.',
               ['craft', 'launch day', 'winter storage', 'sawdust and resin', 'old-timers']),
        career('innkeeper', 'Innkeeper', 'hospitality', 'flexible', '$$', 'Runs an inn or a bed and breakfast: '
               'cooking breakfast, turning rooms, answering guests\' questions and surviving August.',
               ['guests', 'breakfast', 'the season', 'old houses', 'reviews']),
        career('orchard-farmer', 'Orchard farmer', 'agriculture', 'early', '$', 'Works an orchard and farm: '
               'pruning in winter, spraying and mowing in summer, picking and pressing cider in the fall.',
               ['weather', 'harvest', 'the farm stand', 'frost', 'the seasons']),
    ],
    'climate': {
        'summary': 'Midcoast Maine: cold, snowy winters, a muddy spring, short warm summers cooled by the sea and '
                   'fog, and a long golden fall. Nor\'easters bring snow or rain at any time from November to '
                   'April.',
        'months': [
            month(31, 13, 11, 'Coldest month; the harbour steams with sea smoke on still mornings.'),
            month(34, 15, 10, 'Snow on the ground, skating on Cobb Pond and the winter carnival.'),
            month(41, 24, 11, 'Sugaring season; snow, sleet and the first thaw.'),
            month(52, 34, 12, 'Mud season; ice goes out on Long Pond and the boats go back in.'),
            month(63, 43, 13, 'Lilacs, black flies and the alewife run.'),
            month(72, 52, 12, 'Fog mornings and long evenings; the summer people arrive.'),
            month(78, 58, 10, 'Warmest month; the water is still cold.'),
            month(77, 57, 10, 'Lobster festival weather; busy and bright.'),
            month(69, 49, 10, 'Clear and crisp; the best month, locals say.'),
            month(57, 38, 11, 'Peak foliage and apple picking; the cottages close.'),
            month(46, 30, 12, 'Grey and windy; boats come out of the water.'),
            month(36, 20, 12, 'Dark by four; first snow and the lighting of the green.'),
        ],
        'source': S,
    },
    'annual_events': [
        event('polar-plunge', 'New Year\'s Day Plunge', [1], 'back-shore', 'Hundreds run into the sea at Cobble '
              'Beach at noon on New Year\'s Day in costumes, raising money for the food pantry, then thaw out at '
              'the Legion.'),
        event('winter-carnival', 'Winter Carnival', [2], 'west-end', 'A weekend of skating races on Cobb Pond, '
              'snow sculptures on the quad, a chili cook-off at the rec centre, a smelt fry and the crowning of '
              'a carnival king and queen from the senior class.'),
        event('town-meeting-day', 'Town Meeting Day', [3], 'the-green', 'The annual open town meeting in the '
              'high school gym, where every voter can stand up and argue over the budget, the harbour '
              'moorings and the new fire truck, usually until long after supper.'),
        event('maple-weekend', 'Maple Weekend', [3], 'ridge-road', 'The sugarhouses open their doors on the '
              'fourth weekend of March for syrup tastings, pancake breakfasts, sugar on snow and muddy boots.'),
        event('ice-out-contest', 'Long Pond Ice-Out Contest', [4], 'long-pond', 'The town bets a dollar a guess '
              'on the day and hour the ice goes out on Long Pond, judged from the store porch; the winner splits '
              'the pot with the volunteer fire department.'),
        event('alewife-run', 'Alewife Run', [5], 'mill-end', 'When the alewives run up the fish ladder at the '
              'falls, schools bring classes, ospreys circle and the mill holds a smoked-fish breakfast.'),
        event('commencement', 'Whitcomb Commencement', [5], 'college-street', 'Graduation on the quad, with '
              'every inn booked, the bakery sold out and parents photographing the lighthouse.'),
        event('blessing-of-the-fleet', 'Blessing of the Fleet', [6], 'the-harbor', 'Lobster boats dressed in '
              'flags parade past the fish pier to be blessed by the clergy of every church in town, and a '
              'wreath is laid for those lost at sea.'),
        event('strawberry-supper', 'Strawberry Supper', [6], 'the-green', 'The First Parish strawberry supper, '
              'with ham, potato salad, baked beans and shortcake on biscuits, two sittings and a line down the '
              'church steps.'),
        event('fourth-of-july-parade', 'Fourth of July Parade', [7], 'the-green', 'Fire engines, the high school '
              'band, floats on hay wagons, kids on decorated bikes and the lobster boat on a trailer that wins '
              'every year, with fireworks over the harbour that night.'),
        event('harbor-regatta', 'Harbor Regatta', [7], 'dyers-cove', 'A weekend of sailboat races off Dyer\'s Cove '
              'for every kind of boat, from children in prams to old wooden yachts, ending with a cookout at the '
              'boatyard.'),
        event('lobster-festival', 'Haddon Harbor Lobster Festival', [8], 'the-harbor', 'Four days of lobster '
              'dinners, a parade, a crate race across floating lobster crates, the sea goddess pageant and a '
              'midway on the waterfront.'),
        event('tarbox-island-day', 'Tarbox Island Day', [8], 'tarbox-island', 'The island hosts the mainland for '
              'one day: an extra ferry, a lobster bake, boat races, a fun run around the loop road and a dance '
              'in the community hall.'),
        event('harvest-fair', 'Haddon Harbor Harvest Fair', [9], 'ridge-road', 'The agricultural fair at the '
              'fairgrounds: ox pulling, 4-H barns, the giant pumpkin weigh-in, fried dough, and the pie contest '
              'whose results the Register prints in full.'),
        event('head-of-the-mill', 'Head of the Mill', [10], 'college-street', 'The college regatta, a rowing race '
              'up the Mill River estuary that brings crews from across New England and a crowd with blankets on '
              'the bank.'),
        event('halloween-on-main', 'Halloween on Main Street', [10], 'the-green', 'The shops hand out candy, Main '
              'Street closes to cars, the historical society gives lantern tours of the burying ground and the '
              'costume parade ends at the bandstand.'),
        event('open-studios', 'Kendall Mill Open Studios', [11], 'mill-end', 'Every studio in the mill opens on '
              'the weekend before Thanksgiving, with makers selling their work and the brewery pouring a winter '
              'ale.'),
        event('first-snow-breakfast', 'First Snow Pancake Breakfast', [11, 12], 'the-green', 'On the Saturday '
              'after the first real snowfall, the volunteer firefighters serve pancakes and sausages at the '
              'Central Fire Station; the phone tree spreads the word the night before.'),
        event('lighting-of-the-green', 'Lighting of the Green', [12], 'the-green', 'On the first Saturday of '
              'December the town gathers on the green for carols, cocoa and the lighting of the tree, and the '
              'harbour boats light up their rigging.'),
    ],
    'local_color': [
        color('mug-wall', 'The mug wall', 'custom', 'Regulars at the Bluebird keep their own mug on a numbered peg '
              'behind the counter. Getting a peg takes years; when a regular dies, their mug is retired to a '
              'shelf over the door.', ['bluebird-diner']),
        color('phone-tree', 'The town phone tree', 'custom', 'Snow days, lost dogs, power cuts, a fire at the '
              'pier, a casserole needed for a family in trouble: news goes out on the phone tree, each person '
              'calling the next three, faster than any app.'),
        color('honor-farm-stand', 'Honour-system farm stands', 'custom', 'Eggs, corn and pies sit unattended at '
              'the ends of driveways with a cash box or a jar. People leave exact change, or an IOU on the '
              'notepad, and settle up next time.', ['ridge-road-farm-stand', 'ridge-road'], WARM),
        color('police-log', 'Reading the police log', 'custom', 'Everyone turns first to the police log in the '
              'Register on Thursday: loose cows, a suspicious kayak, a raccoon in the bank, and guessing who '
              'the unnamed caller was.'),
        color('swap-shop', 'The swap shop', 'custom', 'A shed at the town transfer station where people leave '
              'what still works and take what they need; plenty of furniture in town has been through it twice.'),
        color('town-meeting-arguments', 'Town meeting arguments', 'custom', 'People settle in for town meeting '
              'with a thermos and a sandwich, knowing the article about the moorings or the school roof will '
              'take two hours and someone will quote the 1974 vote.', ['haddon-town-hall'], ['winter',
              'spring']),
        color('bean-supper', 'Bean supper', 'dish', 'Baked beans slow-cooked in a crock with salt pork and '
              'molasses, with brown bread, coleslaw, hot dogs and pie: the first-Saturday supper at the church '
              'and the grange.', ['first-parish-vestry', 'ridge-grange-hall']),
        color('lobster-roll', 'The lobster roll argument', 'dish', 'Lobster on a buttered, toasted split-top '
              'roll, served with mayonnaise or with warm butter. Families, and marriages, have firm positions.',
              ['coombs-wharf-shack', 'lobster-co-op'], ['summer']),
        color('whoopie-pie', 'Whoopie pie', 'dish', 'Two soft chocolate cakes around a thick white filling, the '
              'state treat, sold by every bakery, store and church sale.', ['spruce-street-bakery',
              'long-pond-store']),
        color('red-hot-dogs', 'Red hot dogs', 'dish', 'Bright red natural-casing hot dogs that snap when you '
              'bite them, served at bean suppers, ball games and the fair.', ['high-school-field',
              'haddon-fairgrounds']),
        color('italian-sandwich', 'Italian sandwich', 'dish', 'A Maine Italian: ham, American cheese, onions, '
              'green peppers, tomatoes, pickles and black olives on a soft roll with oil, salt and pepper.',
              ['meadow-variety', 'rizzos-market', 'cove-variety']),
        color('blueberry-pie', 'Wild blueberry pie', 'dish', 'Pie made with the small wild blueberries raked on '
              'the barrens, best in August and judged harshly at the harvest fair.',
              ['coombs-wharf-shack', 'ridge-road-farm-stand'], ['summer']),
        color('cider-doughnuts', 'Cider doughnuts', 'dish', 'Warm doughnuts made with boiled cider and rolled in '
              'cinnamon sugar, sold in paper bags at the orchard all fall.', ['higgins-hill-orchard'], ['fall']),
        color('moxie', 'Moxie', 'drink', 'The bitter, old-fashioned soda that older people swear by and '
              'newcomers try exactly once.', ['main-street-pharmacy', 'long-pond-store']),
        color('frappe', 'A frappe', 'drink', 'A thick milkshake made with ice cream; in this town a "milkshake" is '
              'just flavoured milk, and the soda fountain will ask which you meant.', ['main-street-pharmacy',
              'bickford-dairy-bar']),
        color('ayuh', '"Ayuh"', 'saying', 'Yes, or I agree, or I heard you, depending on the tone; heard on the '
              'fish pier more than on College Street.'),
        color('wicked', '"Wicked"', 'saying', 'Very: wicked good, wicked cold, wicked busy in August.'),
        color('from-away', '"From away"', 'saying', 'Anyone not born here, however long they have lived in town. '
              'Their children are from away too, some say.'),
        color('dooryard', '"Dooryard"', 'saying', 'The yard by the kitchen door where trucks, traps and firewood '
              'live: "Pull into the dooryard."'),
        color('upta-camp', '"Upta camp"', 'saying', 'At the family\'s cabin on Long Pond, where people go every '
              'summer weekend and are unreachable.', ['long-pond'], ['summer']),
        color('mud-season', 'Mud season', 'other', 'The weeks in April when the frost comes out of the ground, dirt '
              'roads turn to soup, posted roads close to heavy trucks and everyone owns two pairs of boots.',
              ['ridge-road', 'long-pond'], ['spring']),
        color('noon-whistle', 'The noon whistle', 'custom', 'The fire station whistle sounds at noon every day; '
              'people check their watches against it and newcomers jump.', ['central-fire-station']),
        color('steering-wheel-wave', 'The steering-wheel wave', 'custom', 'On the back roads drivers lift two '
              'fingers off the wheel at every passing car, and on Tarbox Island a whole hand.', ['ridge-road',
              'tarbox-island']),
        color('harbor-high-clippers', 'Harbor High Clippers', 'team', 'The high school teams in navy and gold; '
              'Friday night football under the lights and the Thanksgiving game against South Haddon\'s old '
              'rivals draw the whole town.', ['high-school-field', 'haddon-ice-arena'], ['fall', 'winter']),
        color('whitcomb-ospreys', 'Whitcomb Ospreys', 'team', 'The college teams, best known for rowing and '
              'women\'s hockey; townspeople line the bank for the Head of the Mill.', ['whitcomb-boathouse',
              'haddon-ice-arena']),
        color('hardware-popcorn', 'Hardware store popcorn', 'shop', 'Hobbs Hardware gives away popcorn by the '
              'register and coffee to contractors, and will sell you one screw if one is all you need.',
              ['hobbs-hardware']),
    ],
    'prices': [
        price('coffee', 'Cup of coffee', 2.25, 4.5),
        price('latte', 'Latte', 4.5, 6),
        price('diner-breakfast', 'Diner breakfast', 9, 16),
        price('lobster-roll', 'Lobster roll', 28, 42, 'market price'),
        price('lobster', 'Live lobster at the co-op', 7, 14, 'a pound, by season'),
        price('pint', 'Pint of local beer', 7, 9, 'a pint'),
        price('pizza', 'Large pizza', 16, 24),
        price('dinner-out', 'Dinner out', 25, 75, 'a person'),
        price('groceries', "A week's groceries", 110, 180, 'one person'),
        price('ferry', 'Tarbox Island ferry', 7, 12, 'a passenger round trip'),
        price('ferry-car', 'Tarbox Island ferry with a car', 35, 55, 'round trip'),
        price('inn-night', 'Night at an inn', 160, 380, 'a room, winter to August'),
        price('movie', 'Elmwood Theatre ticket', 5, 10),
        price('bean-supper', 'Church bean supper', 12, 15, 'a plate with pie'),
        price('heating-oil', 'Heating oil', 3.5, 4.5, 'a gallon'),
        price('firewood', 'Cord of firewood', 300, 400, 'a cord, cut and split'),
        price('transfer-station', 'Transfer station sticker', 25, 40, 'a year'),
        price('gas', 'Gasoline', 3.2, 3.9, 'a gallon'),
    ],
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
