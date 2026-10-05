"""Original frontier town for Prospero Companion. Run `python scripts/world/whitlock.py` to rewrite the shipped JSON.

Whitlock is invented: a copper and silver town in southeastern Arizona Territory around 1882, modelled on real
territorial towns of the period (Tombstone, Bisbee, Globe, Silver City, Prescott) without copying any of them.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'cities' / 'whitlock.json'
S = 'curated-2026-10'
ERA = 'frontier'


def hood(id, name, summary, vibe, lat, lon, tier, rent, housing, walk, transit):
    studio, one, two = rent
    return {'id': id, 'name': name, 'summary': summary, 'vibe': vibe, 'lat': lat, 'lon': lon, 'rent_tier': tier,
            'rent': {'studio': studio, 'one_bedroom': one, 'two_bedroom': two}, 'housing': housing,
            'walkability': walk, 'transit': transit, 'source': S}


def place(id, name, kind, hood, summary, tags, cost, setting, good_for, day_parts, seasons=(), cuisine=''):
    return {'id': id, 'name': name, 'kind': kind, 'neighborhood': hood, 'summary': summary, 'tags': tags,
            'cost': cost, 'setting': setting, 'good_for': good_for, 'day_parts': day_parts,
            'seasons': list(seasons), 'cuisine': cuisine, 'source': S}


def career(id, name, sector, schedule, pay, summary, themes):
    return {'id': id, 'name': name, 'sector': sector, 'schedule': schedule, 'pay': pay, 'summary': summary,
            'themes': themes, 'eras': [ERA]}


def employer(id, name, sector, hood, size, summary, careers):
    return {'id': id, 'name': name, 'sector': sector, 'neighborhood': hood, 'size': size, 'summary': summary,
            'careers': careers, 'source': S}


def event(id, name, months, hood, summary):
    return {'id': id, 'name': name, 'months': months, 'neighborhood': hood, 'summary': summary, 'source': S}


ALL = ['solo', 'friends', 'date', 'family']
ADULT = ['solo', 'friends', 'date']
DAY = ['morning', 'afternoon']
DINNER = ['evening']
NIGHT = ['evening', 'late']
ALLDAY = ['morning', 'afternoon', 'evening']
WARM = ['spring', 'summer', 'fall']

# Rents are weekly, in 1882 dollars: a furnished room, a two-room adobe or cabin, a frame house.
CHEAP = ([2, 3], [3, 5], [5, 8])
MIDDLE = ([3, 5], [4, 7], [7, 11])
BETTER = ([4, 7], [6, 10], [10, 16])

CITY = {
    'schema_version': 1, 'id': 'whitlock', 'name': 'Whitlock', 'setting': 'original', 'era': ERA,
    'basis': 'Original setting written for Prospero Companion, modelled on real territorial towns of the 1880s.',
    'region': 'Arizona Territory', 'country': 'United States', 'timezone': 'America/Phoenix',
    'aliases': ['Whitlock, A.T.', 'Whitlock, Arizona Territory'],
    'summary': 'A copper and silver town of about four thousand people in southeastern Arizona Territory, 1882: '
               'a railroad depot and freight yards on the flat, the Sarah Ann mine and stamp mill on the hill, '
               'a Main Street of brick and adobe, a Chinese quarter, a Mexican plaza, and ranches and a cavalry '
               'post out in the valley.',
    'lat': 31.950, 'lon': -109.750,
    'currency': {'code': 'USD', 'symbol': '$', 'name': 'dollars (1882)'},
    'rent_period': 'week',
    'speeds': {'walk': 4.5, 'carriage': 9, 'horse': 11, 'stagecoach': 9, 'commuter-rail': 30},
    'sources': {
        S: {'kind': 'curated', 'title': 'Whitlock, Arizona Territory, written for Prospero Companion',
            'license': 'CC0-1.0', 'retrieved': '2026-10-05',
            'note': 'An invented town. Its institutions, trades, prices and yearly calendar follow what was usual '
                    'in territorial mining and railroad towns of the early 1880s (Tombstone, Bisbee, Globe, Silver '
                    'City, Prescott), drawn from general historical knowledge. Every business and person named is '
                    'fictional. Rents are weekly, in 1882 dollars. Coordinates are anchored in the Sulphur Springs '
                    'Valley of southeastern Arizona for distance estimates only; the climate follows that area at '
                    'about 4,600 feet.'},
    },
    'neighborhoods': [
        hood('main-street', 'Main Street', 'Four blocks of brick and adobe storefronts with wooden awnings: the '
             'mercantile, the bank, the assay office, the newspaper, the barber and bathhouse, hotels and '
             'saloons.', ['central', 'business', 'saloons', 'shopping'], 31.950, -109.750, 'high', BETTER,
             ['rooms-over-store', 'hotel-room', 'boarding-house'], 'high',
             ['on-foot', 'livery', 'buggies', 'stage-line']),
        hood('depot', 'The Depot and Front Street', 'The railroad depot, freight sheds, water tank and stock pens, '
             'with Front Street\'s cheap saloons, chophouses and lodging houses facing the tracks.',
             ['railroad', 'freight', 'rough', 'noisy'], 31.944, -109.756, 'low', CHEAP,
             ['lodging-house', 'boarding-house', 'section-house'], 'high',
             ['on-foot', 'railroad', 'livery', 'buggies', 'stage-line']),
        hood('mill-hill', 'Mill Hill', 'The Sarah Ann stamp mill, hoisting works and company offices on the slope '
             'above town; the stamps pound day and night and you stop hearing them after a week.',
             ['industrial', 'mining', 'loud'], 31.957, -109.738, 'low', CHEAP,
             ['company-cabin', 'boarding-house'], 'medium', ['on-foot', 'livery', 'buggies']),
        hood('sarah-ann-gulch', 'Sarah Ann Gulch', 'Miners\' cabins, tents and company boarding houses strung up '
             'the gulch to the shafts, with a company store and two saloons of its own.',
             ['mining', 'working-class', 'single-men'], 31.963, -109.731, 'low', CHEAP,
             ['company-cabin', 'tent-house', 'boarding-house'], 'medium', ['on-foot', 'livery']),
        hood('fourth-street', 'Fourth Street', 'Plain frame houses and boarding houses east of Main where clerks, '
             'mill foremen, teachers and railroad men with families live; washing lines and chicken yards out '
             'back.', ['residential', 'family', 'respectable'], 31.949, -109.742, 'mid', MIDDLE,
             ['frame-house', 'boarding-house', 'adobe-house'], 'high', ['on-foot', 'livery', 'buggies']),
        hood('courthouse-hill', 'Courthouse Hill', 'The county courthouse, the Methodist church, the schoolhouse '
             'and the brick houses of the bank cashier, the mine superintendent and the better-off merchants.',
             ['affluent', 'quiet', 'civic', 'churchgoing'], 31.954, -109.746, 'high', BETTER,
             ['brick-house', 'frame-house'], 'high', ['on-foot', 'livery', 'buggies']),
        hood('china-alley', 'China Alley', 'A narrow lane behind Main Street of adobe laundries, a herb shop, '
             'a Chinese grocery, a joss house and the vegetable gardeners who sell door to door.',
             ['chinese', 'laundries', 'close-knit'], 31.947, -109.753, 'low', CHEAP,
             ['adobe-house', 'rooms-behind-shop'], 'high', ['on-foot']),
        hood('la-plaza', 'La Plaza', 'The Mexican barrio around a dirt plaza with a bandstand, the Catholic church '
             'of San Ysidro, flat-roofed adobe houses, a cantina, a panaderia and evening paseos.',
             ['mexican', 'catholic', 'family', 'old'], 31.952, -109.758, 'low', CHEAP,
             ['adobe-house', 'rooms-around-courtyard'], 'high', ['on-foot', 'livery']),
        hood('ash-creek', 'Ash Creek', 'The creek bottom below town where cottonwoods and willows shade picnic '
             'spots, Mexican farmers grow chiles and corn, and boys swim in the deep hole in summer.',
             ['creek', 'shade', 'farms', 'picnics'], 31.938, -109.765, 'low', CHEAP,
             ['adobe-house', 'farmhouse'], 'medium', ['on-foot', 'livery', 'buggies']),
        hood('fairground-flat', 'Fairground Flat', 'Open ground south of the tracks with the racetrack, the county '
             'fair sheds, the baseball diamond and the brickyard.', ['open', 'sporting', 'fairground'], 31.935,
             -109.745, 'low', CHEAP, ['cabin', 'adobe-house'], 'medium', ['on-foot', 'livery', 'buggies']),
        hood('fort-merritt', 'Fort Merritt', 'A cavalry post of adobe barracks around a parade ground, six '
             'kilometres south on the valley road, with a sutler\'s store and officers\' row.',
             ['military', 'orderly', 'remote'], 31.905, -109.790, 'low', CHEAP,
             ['barracks', 'officers-quarters', 'adobe-house'], 'medium', ['livery', 'buggies']),
        hood('turkey-creek', 'Turkey Creek ranches', 'Cattle ranches spread across the grassland west of town: '
             'adobe headquarters, windmills, corrals and line camps.', ['ranching', 'open-range', 'quiet'],
             31.920, -109.810, 'low', CHEAP, ['ranch-house', 'bunkhouse'], 'low', ['livery', 'buggies']),
        hood('kuhns-springs', 'Kuhn\'s Hot Springs', 'Warm springs in a canyon northwest of town with a bathhouse, '
             'a small hotel and shade trees; a Sunday buggy ride out.', ['resort', 'springs', 'restful'], 31.985,
             -109.800, 'mid', MIDDLE, ['hotel-room', 'cabin'], 'low', ['livery', 'buggies', 'stage-line']),
        hood('copper-basin', 'Copper Basin', 'A smaller mining camp eight kilometres up the range, reached by the '
             'daily stage: one street, a hoist, a store, a saloon and a post office.',
             ['mining-camp', 'remote', 'rough'], 32.010, -109.705, 'low', CHEAP,
             ['tent-house', 'company-cabin'], 'low', ['livery', 'stage-line']),
    ],
    'transit': [
        {'id': 'on-foot', 'name': 'On foot', 'kind': 'walk', 'summary': 'Most people walk everywhere in town; '
         'Main Street to the depot is ten minutes, to the mill a stiff twenty uphill.', 'source': S},
        {'id': 'livery', 'name': 'Horses from the livery', 'kind': 'horse', 'summary': 'A saddle horse hired from '
         'the Union Livery or Ochoa\'s corral for about two dollars a day, or your own kept at livery.',
         'source': S},
        {'id': 'buggies', 'name': 'Buggies and wagons', 'kind': 'carriage', 'summary': 'Hired buggies for '
         'Sunday drives and doctor\'s calls, ore and freight wagons on the mill road, spring wagons to the '
         'ranches.', 'source': S},
        {'id': 'stage-line', 'name': 'Whitlock & Copper Basin Stage', 'kind': 'stagecoach', 'summary': 'A daily '
         'Concord coach from the depot to Copper Basin and the hot springs, carrying mail, payroll and '
         'passengers.', 'source': S},
        {'id': 'railroad', 'name': 'Gila Valley & Northern Railroad', 'kind': 'commuter-rail', 'summary': 'Two '
         'passenger trains a day each way to the main line junction, for trips to Tucson, El Paso and the '
         'East.', 'source': S},
    ],
    'places': [
        # Main Street
        place('palace-saloon', 'The Palace Saloon', 'bar', 'main-street', 'The best saloon on Main Street, with a '
              'mahogany bar shipped from St. Louis, a pianist most nights and card tables in the back.',
              ['saloon', 'piano', 'cards'], '$$', 'indoor', ['solo', 'friends'], NIGHT),
        place('brennans-saloon', 'Brennan\'s', 'bar', 'main-street', 'A plain Irish saloon where miners drink '
              'beer at five cents a glass and argue about the union and the Fenians.', ['saloon', 'beer',
              'miners'], '$', 'indoor', ['solo', 'friends'], NIGHT),
        place('cosmopolitan-dining-room', 'Cosmopolitan Hotel dining room', 'restaurant', 'main-street',
              'White tablecloths, oysters brought in on ice by rail, and a fifty-cent Sunday dinner that the '
              'whole town dresses up for.', ['hotel', 'oysters', 'sunday-dinner'], '$$', 'indoor',
              ['family', 'date', 'friends'], ['afternoon', 'evening'], cuisine='american'),
        place('can-can-chophouse', 'Can Can Chophouse', 'restaurant', 'main-street', 'A long counter and six '
              'tables serving steaks, chops, fried potatoes and pie at all hours.', ['chophouse', 'steak',
              'all-hours'], '$', 'indoor', ['solo', 'friends', 'coworkers'], ['morning', 'afternoon', 'evening',
              'late'], cuisine='american'),
        place('anderssons-bakery', 'Andersson\'s Bakery', 'cafe', 'main-street', 'Bread, doughnuts and coffee '
              'from four in the morning; Mrs. Andersson\'s cardamom buns sell out by eight.', ['bakery', 'coffee',
              'early'], '$', 'indoor', ALL, DAY, cuisine='bakery'),
        place('city-ice-cream-parlor', 'City Ice Cream Parlor', 'cafe', 'main-street', 'A cool room with marble '
              'tables and ice cream made with ice shipped in by rail; couples come after church.', ['ice-cream',
              'courting', 'cool'], '$', 'indoor', ['date', 'family', 'friends'], ['afternoon', 'evening'],
              WARM, cuisine='sweets'),
        place('feldman-mercantile-store', 'Feldman Bros. Mercantile', 'shopping', 'main-street', 'The big general '
              'store: dry goods, canned oysters, boots, blasting powder, calico and the latest catalogues from '
              'Chicago.', ['general-store', 'dry-goods', 'catalogues'], '$$', 'indoor', ALL, DAY),
        place('mrs-pruitts-millinery', 'Mrs. Pruitt\'s Millinery and Dressmaking', 'shopping', 'main-street',
              'A narrow shop of hats, ribbons and dress goods, where fittings take an hour and the news of the '
              'town comes free.', ['dressmaking', 'hats', 'gossip'], '$$', 'indoor', ['solo', 'friends'], DAY),
        place('pioneer-bathhouse', 'Pioneer Barber Shop and Baths', 'fitness', 'main-street', 'Three barber '
              'chairs out front and six tin tubs in back; a hot bath with a clean towel is twenty-five cents, '
              'more on Saturday nights.', ['bathhouse', 'barber', 'saturday'], '$', 'indoor', ['solo'], ALLDAY),
        place('miners-reading-room', 'Miners\' Union Reading Room', 'library', 'main-street', 'Upstairs over the '
              'bank: newspapers from San Francisco and New York, a few hundred books, chess boards and a stove, '
              'open to members and their families.', ['reading', 'newspapers', 'chess', 'quiet'], 'free',
              'indoor', ['solo', 'friends'], ALLDAY),
        place('harlan-opera-house', 'Harlan Opera House', 'venue', 'main-street', 'A two-storey adobe hall '
              'that hosts travelling theatre companies, minstrel shows, lectures, union meetings, church '
              'socials and the Saturday dances.', ['theatre', 'dances', 'meetings', 'lectures'], '$', 'indoor',
              ALL, NIGHT),
        place('wickes-photograph-gallery', 'Wickes\' Photograph Gallery', 'attraction', 'main-street', 'A skylit '
              'studio where people sit very still for cabinet cards to mail home; a dollar and a half for half a '
              'dozen.', ['photography', 'portraits', 'keepsakes'], '$$', 'indoor', ['solo', 'date', 'family'],
              DAY),
        place('whitlock-gazette-office', 'Whitlock Gazette office', 'landmark', 'main-street', 'The newspaper '
              'office with its press in the window; people gather outside when the telegraph news is posted on '
              'the board.', ['newspaper', 'news-board'], 'free', 'mixed', ['solo', 'friends'], DAY),
        place('main-street-boardwalk', 'Main Street boardwalk', 'square', 'main-street', 'The plank sidewalk under '
              'the awnings where everyone passes on Saturday evenings to see and be seen.', ['promenade',
              'saturday', 'people-watching'], 'free', 'outdoor', ALL, ['afternoon', 'evening']),
        # Depot and Front Street
        place('depot-platform', 'Gila Valley depot', 'landmark', 'depot', 'The red frame depot and platform where '
              'half the town turns out to meet the afternoon train and collect mail and newspapers.',
              ['railroad', 'trains', 'mail'], 'free', 'mixed', ALL, DAY),
        place('railroad-eating-house', 'Railroad Eating House', 'restaurant', 'depot', 'Fast plain meals for '
              'train passengers and section crews: beefsteak, beans, biscuits and strong coffee for thirty-five '
              'cents.', ['railroad', 'quick-meal', 'coffee'], '$', 'indoor', ['solo', 'coworkers'],
              ['morning', 'afternoon', 'evening'], cuisine='american'),
        place('railroad-exchange', 'The Railroad Exchange', 'bar', 'depot', 'A Front Street saloon of teamsters, '
              'brakemen and freighters, with a faro table and a lunch counter of pickled eggs.', ['saloon',
              'teamsters', 'faro'], '$', 'indoor', ['solo', 'friends'], NIGHT),
        place('freight-yards', 'Freight yards and corrals', 'docks', 'depot', 'Sheds, platforms and corrals where '
              'ore sacks go out and machinery, flour and barrels come in, worked by teamsters and Chinese '
              'labourers.', ['freight', 'wagons', 'work'], 'free', 'outdoor', ['solo', 'coworkers'], DAY),
        place('union-livery', 'Union Livery and Feed', 'workshop', 'depot', 'A big barn of rental horses, buggies and '
              'hay, with a farrier and a boy who will hold your horse for a nickel.', ['livery', 'horses',
              'buggies'], '$', 'mixed', ALL, ALLDAY),
        place('kellys-smithy', 'Kelly\'s blacksmith shop', 'workshop', 'depot', 'An open-fronted forge that '
              'shoes horses, sharpens drill steel for the mines and mends wagon tyres.', ['blacksmith', 'forge',
              'horses'], '$', 'mixed', ['solo'], DAY),
        # Mill Hill and the gulch
        place('stamp-mill-overlook', 'Stamp mill overlook', 'landmark', 'mill-hill', 'A spot on the mill road '
              'where you can watch ore wagons unload into the forty-stamp mill and see the whole valley to the '
              'fort.', ['view', 'mining', 'sunset'], 'free', 'outdoor', ALL, ['afternoon', 'evening']),
        place('company-store', 'Sarah Ann Company Store', 'market', 'sarah-ann-gulch', 'The company store for '
              'flour, coffee, bacon, candles and work clothes, paid in cash or against next month\'s wages.',
              ['company-store', 'groceries'], '$', 'indoor', ['solo', 'family'], DAY),
        place('gulch-saloon', 'The Shaft House', 'bar', 'sarah-ann-gulch', 'A tent saloon turned board shack at '
              'the head of the gulch, where shifts drink as they come off.', ['saloon', 'miners', 'shift-change'],
              '$', 'indoor', ['solo', 'friends'], NIGHT),
        place('cornish-boarding-table', 'Mrs. Trevithick\'s boarding table', 'restaurant', 'sarah-ann-gulch',
              'A long table of Cornish miners eating pasties, stew and saffron cake at twenty-five cents a meal.',
              ['boarding-house', 'pasties', 'cornish'], '$', 'indoor', ['solo', 'coworkers'], ['morning',
              'evening'], cuisine='cornish'),
        # China Alley
        place('sam-lee-laundry', 'Sam Lee Laundry', 'workshop', 'china-alley', 'An adobe laundry of copper '
              'boilers and flatirons where shirts are washed, starched and ironed for ten cents.', ['laundry',
              'chinese'], '$', 'indoor', ['solo'], DAY),
        place('quong-kee-herbs', 'Quong Kee herb shop', 'shopping', 'china-alley', 'Drawers of dried roots, '
              'teas and remedies; Dr. Quong takes pulses and prescribes for miners who distrust the company '
              'doctor.', ['herbs', 'medicine', 'tea'], '$', 'indoor', ['solo'], DAY),
        place('wing-hop-kitchen', 'Wing Hop Kitchen', 'restaurant', 'china-alley', 'A small kitchen serving '
              'noodles, rice and roast pork, and American breakfasts for railroad men at dawn.', ['noodles',
              'chinese', 'cheap'], '$', 'indoor', ['solo', 'friends'], ['morning', 'evening', 'late'],
              cuisine='chinese'),
        place('joss-house', 'China Alley joss house', 'temple', 'china-alley', 'A small temple with incense, '
              'red paper and a carved altar, busiest at New Year.', ['temple', 'incense'], 'free', 'indoor',
              ['solo', 'family'], DAY),
        # La Plaza
        place('plaza-bandstand', 'La Plaza and bandstand', 'square', 'la-plaza', 'The dirt plaza under pepper '
              'trees where families walk in the evening and a band plays on Sundays and fiesta nights.',
              ['plaza', 'paseo', 'music'], 'free', 'outdoor', ALL, ['afternoon', 'evening']),
        place('san-ysidro-church', 'San Ysidro Church', 'temple', 'la-plaza', 'A whitewashed adobe church with '
              'a bell brought from Sonora; Mass on Sundays and weddings on Saturdays.', ['church', 'catholic',
              'mass'], 'free', 'indoor', ['solo', 'family'], DAY),
        place('cantina-la-sonorense', 'Cantina La Sonorense', 'bar', 'la-plaza', 'A cool adobe cantina with mescal, '
              'beer and a guitar player, and tamales on Saturday nights.', ['cantina', 'mescal', 'guitar'], '$',
              'indoor', ['solo', 'friends', 'date'], NIGHT),
        place('panaderia-ochoa', 'Panadería Ochoa', 'cafe', 'la-plaza', 'An outdoor beehive oven turning out pan '
              'dulce, bolillos and coffee with canela.', ['bakery', 'pan-dulce', 'coffee'], '$', 'mixed', ALL,
              DAY, cuisine='mexican'),
        place('fonda-carrillo', 'Fonda Carrillo', 'restaurant', 'la-plaza', 'A family dining room off the plaza '
              'serving carne seca, frijoles, tortillas de harina and menudo on Sunday mornings.', ['mexican',
              'family-run', 'menudo'], '$', 'indoor', ALL, ['morning', 'afternoon', 'evening'], cuisine='sonoran'),
        # Courthouse Hill and Fourth Street
        place('methodist-church', 'First Methodist Church', 'temple', 'courthouse-hill', 'A frame church with a '
              'bell tower, Sunday services, a Wednesday prayer meeting and ice-cream socials.', ['church',
              'methodist', 'socials'], 'free', 'indoor', ['solo', 'family'], ['morning', 'evening']),
        place('courthouse-square', 'Courthouse square', 'park', 'courthouse-hill', 'The only lawn in town, '
              'watered by hand, with young ash trees and benches where the band plays on the Fourth.',
              ['lawn', 'shade', 'benches'], 'free', 'outdoor', ALL, ALLDAY, WARM),
        place('mrs-hales-boarding-house', 'Mrs. Hale\'s boarding house table', 'inn', 'fourth-street', 'A '
              'respectable boarding house where teachers and clerks take meals at seven dollars a week; '
              'Sunday chicken is the event of the week.', ['boarding-house', 'home-cooking'], '$', 'indoor',
              ['solo', 'friends'], ['morning', 'evening'], cuisine='american'),
        # Out of town
        place('ash-creek-picnic-grounds', 'Ash Creek picnic grounds', 'park', 'ash-creek', 'Cottonwood shade by '
              'the creek where families picnic on Sundays, couples walk, and the deep hole is good for a swim '
              'in summer.', ['creek', 'picnic', 'shade', 'swimming'], 'free', 'outdoor', ALL, DAY, WARM),
        place('ash-creek-trail', 'Ash Creek trail', 'trail', 'ash-creek', 'A path along the creek past farm '
              'plots and willow thickets to a small waterfall after the summer rains.', ['walk', 'birds',
              'creek'], 'free', 'outdoor', ADULT, DAY, WARM),
        place('whitlock-racetrack', 'Whitlock Driving Park', 'stadium', 'fairground-flat', 'A half-mile dirt '
              'track with a wooden grandstand for horse races on holidays and trotting matches most Sundays.',
              ['horse-racing', 'betting', 'holidays'], '$', 'outdoor', ALL, ['afternoon'], WARM),
        place('baseball-grounds', 'Fairground baseball grounds', 'park', 'fairground-flat', 'A rough diamond '
              'where the Whitlock Nine play the fort and the Copper Basin club on Sunday afternoons.',
              ['baseball', 'sunday', 'crowds'], 'free', 'outdoor', ALL, ['afternoon'], WARM),
        place('kuhns-bathhouse', 'Kuhn\'s Hot Springs bathhouse', 'fitness', 'kuhns-springs', 'Plank bathhouses '
              'over warm mineral pools, recommended for rheumatism and miners\' aches; fifty cents a soak.',
              ['hot-springs', 'bathing', 'rest'], '$', 'mixed', ['solo', 'friends', 'date'], DAY),
        place('kuhns-hotel', 'Kuhn\'s Springs Hotel', 'inn', 'kuhns-springs', 'A small adobe hotel with a '
              'shaded porch and a set chicken dinner for day visitors.', ['hotel', 'porch', 'sunday'], '$$',
              'mixed', ['date', 'family', 'friends'], ['afternoon', 'evening'], cuisine='american'),
        place('sutlers-store', 'Fort Merritt sutler\'s store', 'tavern', 'fort-merritt', 'The post trader\'s '
              'store and bar where soldiers buy tobacco, canned peaches and beer, and civilians hear the fort '
              'news.', ['fort', 'soldiers', 'store'], '$', 'indoor', ['solo', 'friends'], ['afternoon',
              'evening']),
        place('parade-ground', 'Fort Merritt parade ground', 'attraction', 'fort-merritt', 'The square where the '
              'cavalry drills and the band plays at retreat; townspeople ride out for Sunday guard mount.',
              ['cavalry', 'band', 'drill'], 'free', 'outdoor', ALL, ['morning', 'evening']),
        place('copper-basin-stage-stop', 'Copper Basin stage stop', 'tavern', 'copper-basin', 'A log store and '
              'saloon where the stage changes horses and passengers get coffee and a plate of beans.',
              ['stage', 'remote', 'coffee'], '$', 'indoor', ['solo', 'friends'], ['afternoon', 'evening']),
    ],
    'colleges': [
        {'id': 'whitlock-public-school', 'name': 'Whitlock Public School', 'type': 'academy',
         'neighborhood': 'courthouse-hill', 'size': 'small', 'known_for': ['primary-grades', 'spelling-bees',
         'recitations', 'one-teacher-rooms'], 'source': S},
        {'id': 'st-joseph-academy', 'name': 'Sisters of St. Joseph Academy', 'type': 'academy',
         'neighborhood': 'la-plaza', 'size': 'small', 'known_for': ['girls-school', 'music', 'needlework',
         'spanish-and-english'], 'source': S},
        {'id': 'telegraph-school', 'name': 'Depot telegraph class', 'type': 'technical-institute',
         'neighborhood': 'depot', 'size': 'small', 'known_for': ['morse-code', 'railroad-telegraphy',
         'evening-classes'], 'source': S},
        {'id': 'assay-classes', 'name': 'Professor Lindqvist\'s assay and mineralogy classes',
         'type': 'technical-institute', 'neighborhood': 'main-street', 'size': 'small',
         'known_for': ['assaying', 'mineralogy', 'surveying'], 'source': S},
    ],
    'careers': [
        career('miner', 'Hard-rock miner', 'mining', 'rotating', '$$', 'Ten-hour shifts underground in the Sarah '
               'Ann for four dollars a day, drilling, blasting and mucking by candlelight.',
               ['the shaft cage', 'candles and powder', 'partners on the drill', 'payday', 'the union']),
        career('mill-hand', 'Stamp mill hand', 'mining', 'rotating', '$', 'Feeding ore and tending the amalgam '
               'plates at the stamp mill on day or night shift, in constant noise.',
               ['the stamps', 'night shift', 'mercury and amalgam', 'deafness']),
        career('assayer', 'Assayer', 'mining', 'office', '$$', 'Testing ore samples with furnace and balance for '
               'the company and for prospectors who bring rocks in a sack.',
               ['furnace and crucibles', 'prospectors', 'honest numbers']),
        career('telegraph-operator', 'Telegraph operator', 'railroad', 'rotating', '$$', 'Keying train orders '
               'and messages at the depot, the first in town to hear any news.',
               ['train orders', 'news by wire', 'night trick', 'Morse chatter']),
        career('brakeman', 'Railroad brakeman', 'railroad', 'rotating', '$$', 'Riding freights to the junction '
               'and back, setting brakes on car roofs and coupling cars in the yard.',
               ['car tops', 'coupling', 'the junction', 'lost fingers']),
        career('teamster', 'Freighter', 'freight', 'early', '$$', 'Driving ore and freight wagons behind '
               'twelve-mule teams between the mill, the depot and the camps.',
               ['mules', 'the mill road', 'washouts', 'camping out']),
        career('stage-driver', 'Stagecoach driver', 'freight', 'early', '$$', 'Driving the daily Concord to '
               'Copper Basin and the springs with the mail and sometimes the payroll.',
               ['six-horse team', 'passengers', 'the mail', 'weather']),
        career('ranch-hand', 'Ranch hand', 'ranching', 'early', '$', 'Riding for the Turkey Creek outfits for '
               'thirty dollars a month and found: fences, windmills, roundup and branding.',
               ['horses', 'roundup', 'the bunkhouse', 'windmills', 'town on Saturday']),
        career('blacksmith', 'Blacksmith', 'trades', 'early', '$$', 'Shoeing horses and mules, sharpening drill '
               'steel and mending wagons at the forge.', ['the forge', 'horseshoes', 'drill steel']),
        career('store-clerk', 'Store clerk', 'retail', 'office', '$', 'Measuring calico, weighing coffee and '
               'keeping the ledger behind the mercantile counter, six days a week.',
               ['customers', 'the ledger', 'new goods off the train']),
        career('bank-clerk', 'Bank clerk', 'finance', 'office', '$$', 'Counting gold coin and keeping accounts '
               'at the bank, in a starched collar and sleeve garters.',
               ['the vault', 'payroll day', 'mine accounts']),
        career('typesetter', 'Printer\'s devil and typesetter', 'newspaper', 'evening', '$', 'Setting type by '
               'hand and inking the press for the weekly Gazette, working late before press day.',
               ['type cases', 'press day', 'the editor', 'ink']),
        career('hotel-clerk', 'Hotel clerk', 'hospitality', 'rotating', '$', 'Keeping the register and the keys '
               'at the Cosmopolitan and meeting every train.', ['the register', 'drummers', 'the night desk']),
        career('cook', 'Cook', 'hospitality', 'early', '$', 'Cooking for a hotel, chophouse or boarding house '
               'from before dawn, on a wood range.', ['the range', 'bread and pie', 'feeding miners']),
        career('laundress', 'Laundress', 'trades', 'early', '$', 'Washing, boiling, starching and ironing other '
               'people\'s shirts and linens by the piece.', ['washday', 'flatirons', 'regular customers']),
        career('dressmaker', 'Dressmaker', 'trades', 'flexible', '$', 'Making and altering dresses from catalogue '
               'patterns for fittings in the shop or at customers\' homes.',
               ['fittings', 'catalogue fashions', 'ball gowns at Christmas']),
        career('schoolteacher', 'Schoolteacher', 'education', 'academic', '$', 'Teaching forty children of every '
               'age in one room for sixty dollars a month, and boarding with a local family.',
               ['the schoolroom', 'recitations', 'the school board', 'boarding']),
        career('doctor', 'Doctor', 'medicine', 'flexible', '$$$', 'Company and town doctor: mine injuries, '
               'fevers, confinements and buggy calls to the ranches at night.',
               ['house calls', 'mine accidents', 'the drugstore', 'night rides']),
        career('deputy', 'Deputy sheriff', 'law', 'rotating', '$$', 'Serving papers, collecting taxes and '
               'keeping order for the county sheriff, mostly on foot along Main Street.',
               ['the jail', 'serving papers', 'Saturday nights', 'court days']),
        career('saloon-pianist', 'Saloon pianist', 'entertainment', 'evening', '$', 'Playing popular songs and '
               'waltzes at the Palace from supper until the small hours, and for dances on Saturdays.',
               ['the piano', 'requests', 'dances', 'late nights']),
        career('bartender', 'Bartender', 'hospitality', 'evening', '$$', 'Pouring whiskey and beer and keeping '
               'the peace behind a saloon bar.', ['regulars', 'the free lunch', 'trouble at closing']),
        career('trooper', 'Cavalry trooper', 'military', 'early', '$', 'Thirteen dollars a month at Fort Merritt: '
               'stables, drill, escort duty and long scouts in the mountains.',
               ['stable call', 'drill', 'scouts', 'the sutler']),
    ],
    'employers': [
        employer('sarah-ann-mining', 'Sarah Ann Consolidated Mining Company', 'mining', 'mill-hill', 'large',
                 'Owners of the Sarah Ann mine, hoisting works and company store; the biggest payroll in town.',
                 ['miner', 'assayer', 'doctor', 'store-clerk', 'blacksmith', 'teamster']),
        employer('sarah-ann-mill', 'Sarah Ann forty-stamp mill', 'mining', 'mill-hill', 'medium', 'The stamp mill '
                 'that crushes the company\'s ore and custom ore from smaller claims.', ['mill-hand', 'assayer']),
        employer('gila-valley-railroad', 'Gila Valley & Northern Railroad', 'railroad', 'depot', 'medium', 'The '
                 'branch railroad: depot, telegraph, section gangs and freight crews.',
                 ['telegraph-operator', 'brakeman', 'cook']),
        employer('feldman-mercantile', 'Feldman Bros. Mercantile', 'retail', 'main-street', 'medium', 'The '
                 'biggest store in town, which also runs freight wagons to the camps.',
                 ['store-clerk', 'teamster']),
        employer('valley-bank', 'Sulphur Valley Bank', 'finance', 'main-street', 'small', 'A brick bank with '
                 'a Hall\'s safe that holds the mine payroll and the ranchers\' accounts.', ['bank-clerk']),
        employer('whitlock-gazette', 'Whitlock Gazette', 'newspaper', 'main-street', 'small', 'The weekly '
                 'Republican paper, with a job-printing business on the side.', ['typesetter']),
        employer('cosmopolitan-hotel', 'Cosmopolitan Hotel', 'hospitality', 'main-street', 'medium', 'The best '
                 'hotel in town: forty rooms, a dining room and a bar.', ['hotel-clerk', 'cook', 'bartender']),
        employer('palace-saloon-employer', 'The Palace Saloon', 'hospitality', 'main-street', 'small', 'Main '
                 'Street\'s best saloon, open day and night.', ['bartender', 'saloon-pianist']),
        employer('copper-basin-stage', 'Whitlock & Copper Basin Stage Company', 'freight', 'depot', 'small',
                 'Runs the daily coach, the mail contract and a freight wagon line.', ['stage-driver', 'teamster',
                 'blacksmith']),
        employer('county-sheriff', 'County Sheriff\'s Office', 'law', 'courthouse-hill', 'small', 'The sheriff, '
                 'three deputies and the jail in the courthouse basement.', ['deputy']),
        employer('fort-merritt-employer', 'Fort Merritt', 'military', 'fort-merritt', 'medium', 'Two troops of '
                 'cavalry, with civilian blacksmiths, cooks and laundresses on the post.',
                 ['trooper', 'blacksmith', 'laundress', 'cook', 'doctor']),
        employer('turkey-creek-cattle', 'Turkey Creek Cattle Company', 'ranching', 'turkey-creek', 'medium', 'The '
                 'largest ranch in the valley, running several thousand head.', ['ranch-hand', 'cook']),
        employer('ochoa-ranch', 'Rancho Ochoa', 'ranching', 'turkey-creek', 'small', 'An old Sonoran family ranch '
                 'with cattle, horses and a corral in town.', ['ranch-hand']),
        employer('school-board', 'Whitlock School District', 'education', 'courthouse-hill', 'small', 'The public '
                 'school and its elected board.', ['schoolteacher']),
        employer('sam-lee-laundry-employer', 'Sam Lee Laundry', 'trades', 'china-alley', 'small', 'The busiest '
                 'laundry in China Alley.', ['laundress']),
        employer('pruitt-dressmaking', 'Mrs. Pruitt\'s Millinery and Dressmaking', 'trades', 'main-street', 'small',
                 'Hats, dress goods and dressmaking for the town\'s women.', ['dressmaker']),
    ],
    'career_hubs': [
        {'id': 'hub-mines', 'name': 'The mine and mill', 'neighborhoods': ['mill-hill', 'sarah-ann-gulch'],
         'sectors': ['mining'], 'summary': 'Shafts, hoists, the stamp mill and the assay office; the work that '
         'keeps the town alive.', 'source': S},
        {'id': 'hub-depot', 'name': 'The depot and freight yards', 'neighborhoods': ['depot'],
         'sectors': ['railroad', 'freight', 'trades'], 'summary': 'Trains, wagons, livery barns and smithies by '
         'the tracks.', 'source': S},
        {'id': 'hub-main-street', 'name': 'Main Street trade', 'neighborhoods': ['main-street', 'china-alley',
         'la-plaza'], 'sectors': ['retail', 'finance', 'newspaper', 'hospitality', 'entertainment', 'trades',
         'medicine'], 'summary': 'Stores, the bank, hotels, saloons, laundries and shops.', 'source': S},
        {'id': 'hub-valley', 'name': 'The valley', 'neighborhoods': ['turkey-creek', 'fort-merritt'],
         'sectors': ['ranching', 'military'], 'summary': 'Ranches and the cavalry post out on the grassland.',
         'source': S},
        {'id': 'hub-civic', 'name': 'Courthouse Hill', 'neighborhoods': ['courthouse-hill'],
         'sectors': ['law', 'education'], 'summary': 'The courthouse, jail and schoolhouse.', 'source': S},
    ],
    'climate': {
        'summary': 'High desert at about 4,600 feet: mild sunny winters with frosty nights, a hot dry May and '
                   'June, and afternoon thunderstorms from July into September that turn the washes to torrents.',
        'months': [
            {'high_f': 59, 'low_f': 32, 'rain_days': 4, 'note': 'Clear and cold at night; occasional snow on the '
             'range.'},
            {'high_f': 62, 'low_f': 34, 'rain_days': 4, 'note': 'Cool, with a few winter rains.'},
            {'high_f': 67, 'low_f': 38, 'rain_days': 3, 'note': 'Windy; dust blows down Main Street.'},
            {'high_f': 75, 'low_f': 44, 'rain_days': 1, 'note': 'Dry and pleasant; wildflowers after a wet winter.'},
            {'high_f': 84, 'low_f': 52, 'rain_days': 1, 'note': 'Hot and very dry.'},
            {'high_f': 93, 'low_f': 61, 'rain_days': 2, 'note': 'The hottest, driest month; everyone waits for '
             'the rains.'},
            {'high_f': 91, 'low_f': 65, 'rain_days': 13, 'note': 'Monsoon storms most afternoons, with lightning '
             'and flash floods.'},
            {'high_f': 88, 'low_f': 64, 'rain_days': 12, 'note': 'Afternoon thunderstorms; the grass turns green.'},
            {'high_f': 85, 'low_f': 59, 'rain_days': 6, 'note': 'Storms tapering off; warm days.'},
            {'high_f': 77, 'low_f': 48, 'rain_days': 3, 'note': 'Clear, mild and dry; the best month.'},
            {'high_f': 67, 'low_f': 38, 'rain_days': 2, 'note': 'Crisp mornings and warm afternoons.'},
            {'high_f': 59, 'low_f': 32, 'rain_days': 4, 'note': 'Cold nights, sunny days, an occasional storm.'},
        ],
        'source': S,
    },
    'annual_events': [
        event('chinese-new-year', 'Chinese New Year', [1, 2], 'china-alley', 'Firecrackers, red paper and open '
              'house in China Alley, with oranges and sweets handed to visitors from town.'),
        event('cinco-de-mayo', 'Cinco de Mayo', [5], 'la-plaza', 'A fiesta on the plaza with a band, speeches, '
              'dancing and food stalls.'),
        event('fourth-of-july', 'Fourth of July', [7], 'main-street', 'Parade, oration at the courthouse, '
              'hand-drilling contests between mine crews, horse races at the Driving Park and a dance at night.'),
        event('payday-saturday', 'Payday Saturday', [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], 'main-street', 'The '
              'Saturday after the mine pays out each month, when Main Street fills, the stores stay open late and '
              'the saloons are full.'),
        event('saturday-dances', 'Saturday dances', [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], 'main-street',
              'Dances at the opera house with a fiddle and piano, quadrilles and waltzes until midnight.'),
        event('monsoon-arrives', 'The rains come', [7], None, 'The first big thunderstorm of summer, when people '
              'stand in the street to smell the wet creosote.'),
        event('diez-y-seis', 'Mexican Independence Day', [9], 'la-plaza', 'The grito at midnight on the 15th and '
              'a day of music, horse racing and dancing on the 16th.'),
        event('county-fair', 'County fair and roundup', [10], 'fairground-flat', 'Fall roundup ends with a fair: '
              'cattle and produce shows, roping, races and a pie table.'),
        event('fort-band-concerts', 'Fort band concerts', [4, 5, 9, 10], 'fort-merritt', 'The post band plays '
              'Sunday afternoon concerts that townspeople drive out to hear.'),
        event('thanksgiving-turkey-shoot', 'Thanksgiving turkey shoot', [11], 'fairground-flat', 'A shooting '
              'match for turkeys and a dinner at the Methodist church.'),
        event('christmas-ball', 'Christmas ball', [12], 'main-street', 'The grand ball of the year at the opera '
              'house, with new dresses, an oyster supper and a midnight march.'),
        event('las-posadas', 'Las Posadas', [12], 'la-plaza', 'Nine nights of candlelit processions through the '
              'barrio before Christmas, ending with tamales and piñatas.'),
    ],
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
