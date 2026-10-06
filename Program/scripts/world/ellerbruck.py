"""Curated Ellerbrück data. Run `python scripts/world/ellerbruck.py` to rewrite the shipped JSON.

A fairy-tale market town drawn only from public-domain sources: the Brothers Grimm (Kinder- und Hausmärchen,
1812-1857, and Deutsche Sagen, 1816-1818), Perrault (Histoires ou contes du temps passé, 1697), Hans Christian
Andersen (1835-1872) and older European folklore. Nothing from Disney or any modern film, book or stage version.
Tale elements sit in the background as local lore; the town itself, its people and its trades are invented.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'cities' / 'ellerbruck.json'
S = 'curated-2026-10'
ERA = 'fantasy'


def hood(id, name, summary, vibe, lat, lon, tier, rent, housing, walk, transit):
    room, cottage, house = rent
    return {'id': id, 'name': name, 'summary': summary, 'vibe': vibe, 'lat': lat, 'lon': lon, 'rent_tier': tier,
            'rent': {'studio': room, 'one_bedroom': cottage, 'two_bedroom': house}, 'housing': housing,
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


def holiday(id, name, kind, summary, **rule):
    return {'id': id, 'name': name, 'kind': kind, 'summary': summary, **rule}


def color(id, name, kind, summary, places=(), seasons=()):
    return {'id': id, 'name': name, 'kind': kind, 'summary': summary, 'places': list(places),
            'seasons': list(seasons), 'source': S}


def price(id, item, low, high, per=''):
    return {'id': id, 'item': item, 'low': low, 'high': high, 'per': per, 'source': S}


ALL = ['solo', 'friends', 'date', 'family']
ADULT = ['solo', 'friends', 'date']
DAY = ['morning', 'afternoon']
DAYLONG = ['morning', 'afternoon', 'evening']
NIGHT = ['evening', 'late']
WARM = ['spring', 'summer', 'fall']
FOOT = ['on-foot', 'carters']

CITY = {
    'schema_version': 1, 'id': 'ellerbruck', 'name': 'Ellerbrück', 'setting': 'fictional', 'era': ERA,
    'basis': 'Drawn only from public-domain folk and fairy tales: the Brothers Grimm (1812-1857 editions of the '
             'Kinder- und Hausmärchen, and Deutsche Sagen), Perrault (1697), Andersen (1835-1872) and older '
             'European folklore, all long out of copyright. Nothing from Disney or any modern adaptation; the '
             'town and its people are invented.',
    'region': 'the Eller valley', 'country': 'a small German principality', 'timezone': 'Europe/Berlin',
    'aliases': ['Ellerbrueck', 'Ellerbruck', 'Ellerbrück an der Eller'],
    'summary': 'A walled market town where a stone bridge crosses the river Eller, with a small castle on the hill, '
               'a mill, guild lanes, goose meadows and a great dark forest beyond the fields, where people still '
               'tell the old tales about their neighbours.',
    'lat': 51.30, 'lon': 9.55,
    'currency': {'code': 'groschen', 'symbol': 'gr.', 'name': 'silver groschen'},
    'rent_period': 'week',
    'speeds': {'walk': 4.5, 'carriage': 6, 'horse': 10, 'ferry': 4, 'boat': 5},
    'sources': {
        S: {'kind': 'curated', 'title': 'Ellerbrück quarters, places and trades written for Prospero Companion',
            'license': 'CC0-1.0', 'retrieved': '2026-10-05',
            'note': 'An original town for fiction. Tale lore comes only from public-domain texts: Grimm\'s '
                    'Rumpelstiltskin, Elves and the Shoemaker, Hansel and Gretel, Bremen Town Musicians, Rapunzel, '
                    'Goose Girl, Mother Holle, Little Red Cap, Brave Little Tailor, Sweet Porridge, Table-Be-Set, '
                    'Clever Elsie, Hans in Luck, Fisherman and His Wife, Three Golden Hairs, Briar Rose, '
                    'Aschenputtel, Golden Goose, Wolf and Seven Kids; the Hamelin ratcatcher (Deutsche Sagen, '
                    '1816); Perrault\'s Little Thumb and Puss in Boots (1697); Andersen\'s Princess and the Pea '
                    '(1835). Nothing from Disney or later adaptations. Streets, inns and townsfolk are invented on '
                    'the pattern of small Hessian towns; coordinates are a fixed anchor in northern Hesse. Rents '
                    'are rough weekly sums in groschen. Climate is approximate Kassel-area averages, rounded.'},
    },
    'neighborhoods': [
        hood('am-markt', 'Am Markt', 'The cobbled market square at the heart of the town, with the town hall, '
             'the fountain, the best inn and the stalls on market days.', ['market', 'central', 'busy'], 51.300,
             9.550, 'high', ([3, 4], [5, 8], [9, 14]), ['room-over-shop', 'timber-frame-house'], 'high', FOOT),
        hood('schlossberg', 'Schlossberg', 'The hill above the market with the Count\'s small castle, its gardens, '
             'its kitchens and the houses of the court officials.', ['court', 'quiet', 'gardens'], 51.304, 9.548,
             'very-high', ([4, 6], [8, 12], [14, 20]), ['servants-attic', 'officials-house'], 'high',
             ['on-foot', 'hired-horses']),
        hood('schustergasse', 'Schustergasse', 'The cobblers\' and tailors\' lane, narrow and crooked, with '
             'workshops on the ground floor and families above.', ['crafts', 'guilds', 'narrow'], 51.299, 9.546,
             'mid', ([2, 3], [4, 6], [7, 10]), ['workshop-house', 'rented-room'], 'high', ['on-foot']),
        hood('backergasse', 'Bäckergasse', 'The bakers\' street behind the market, warm and smelling of bread from '
             'before dawn, with the common bakehouse and the porridge kitchen.', ['food', 'early', 'neighbourly'],
             51.301, 9.553, 'mid', ([2, 3], [4, 6], [7, 10]), ['workshop-house', 'rented-room'], 'high', ['on-foot']),
        hood('weberviertel', 'Weberviertel', 'The spinners\' and weavers\' quarter by the north wall, loud with '
             'looms by day and full of spinning rooms on winter nights.', ['crafts', 'cloth', 'family'], 51.303,
             9.556, 'mid', ([2, 3], [3, 5], [6, 9]), ['timber-frame-house', 'rented-room'], 'high', ['on-foot']),
        hood('kirchhof', 'St. Martin\'s Kirchhof', 'The quiet close around St. Martin\'s church and the convent of '
             'St. Clare, with the churchyard, the parsonage and the convent school.', ['quiet', 'religious',
             'old'], 51.302, 9.545, 'high', ([3, 4], [5, 8], [9, 13]), ['rented-room', 'canon-house'], 'high',
             ['on-foot']),
        hood('muhlbach', 'Mühlbach', 'The mill on the stream below the west wall, with its pond, weir and a '
             'cluster of millers\' and carters\' cottages.', ['river', 'working', 'quiet'], 51.297, 9.540, 'low',
             ([1, 2], [2, 4], [4, 6]), ['cottage', 'mill-house'], 'medium', ['on-foot', 'carters', 'mill-barges']),
        hood('fahrhaus', 'Am Fährhaus', 'The riverbank below the bridge where the ferry crosses, with fishermen\'s '
             'huts, drying nets and the Flounder tavern.', ['river', 'fishing', 'working'], 51.295, 9.552, 'low',
             ([1, 2], [2, 4], [4, 6]), ['cottage', 'fishers-hut'], 'medium', ['on-foot', 'eller-ferry']),
        hood('gerberviertel', 'Gerberviertel', 'The tanners\' quarter downstream by the south gate, smelly and '
             'cheap, with the bathhouse, the ratcatcher and the cheapest rooms in town.', ['cheap', 'river',
             'rough'], 51.294, 9.548, 'low', ([1, 2], [2, 3], [3, 5]), ['rented-room', 'cottage'], 'high',
             ['on-foot', 'mill-barges']),
        hood('ganseanger', 'Gänseanger', 'The goose meadow outside the dark east gate, with the cattle market '
             'ground, the marksmen\'s field and the carters\' inn.', ['open-ground', 'geese', 'market'], 51.301,
             9.562, 'low', ([1, 2], [2, 4], [4, 6]), ['cottage', 'stable-loft'], 'medium', FOOT),
        hood('gartenvorstadt', 'Gartenvorstadt', 'Walled kitchen gardens and orchards outside the north gate, '
             'and beyond them the open fields where the old tower stands.', ['gardens', 'outside-walls', 'quiet'],
             51.309, 9.552, 'mid', ([2, 3], [3, 5], [5, 8]), ['garden-cottage', 'cottage'], 'medium', FOOT),
        hood('waldrand', 'Am Waldrand', 'A hamlet of woodcutters and charcoal burners where the fields end and the '
             'forest begins, an hour\'s walk from the market.', ['forest', 'remote', 'poor'], 51.312, 9.528, 'low',
             ([1, 1], [1, 2], [2, 4]), ['cottage', 'woodcutters-hut'], 'low', ['carters']),
        hood('jagerhof', 'Jägerhof', 'The Count\'s hunting lodge and the foresters\' houses on the forest road, '
             'with trails running off into the deep wood.', ['forest', 'hunting', 'remote'], 51.318, 9.540, 'mid',
             ([1, 2], [2, 4], [4, 6]), ['foresters-house', 'cottage'], 'low', ['carters', 'hired-horses']),
        hood('eichdorf', 'Eichdorf', 'A farming village of strip fields, geese and a great linden tree, a half '
             'hour south of town across the bridge.', ['village', 'farming', 'family'], 51.285, 9.560, 'low',
             ([1, 1], [1, 2], [2, 4]), ['farmhouse', 'cottage'], 'low', ['carters']),
    ],
    'transit': [
        {'id': 'on-foot', 'name': 'On foot', 'kind': 'walk', 'summary': 'Everyone walks: the walls take twenty '
         'minutes to go round and the farthest hamlets are an hour out.', 'source': S},
        {'id': 'carters', 'name': 'Carters\' wagons', 'kind': 'carriage', 'summary': 'Ox and horse carts haul '
         'grain, timber and passengers willing to sit on the load, leaving from the market on market days.',
         'source': S},
        {'id': 'hired-horses', 'name': 'Hired horses', 'kind': 'horse', 'summary': 'Horses can be hired from '
         'the Golden Goose by the east gate, and court messengers ride the Count\'s.', 'source': S},
        {'id': 'eller-ferry', 'name': 'The Eller ferry', 'kind': 'ferry', 'summary': 'A rope ferry crosses the '
         'Eller below the bridge for carts too heavy for the old stone arches.', 'source': S},
        {'id': 'mill-barges', 'name': 'Mill barges', 'kind': 'boat', 'summary': 'Flat barges carry flour and '
         'hides between the mill, the tanyards and the bridge.', 'source': S},
    ],
    'places': [
        # Am Markt
        place('marktplatz', 'the Marktplatz', 'square', 'am-markt', 'The sloping market square in front of the '
              'town hall, where news is cried, notices are nailed up and children chase pigeons.', ['central',
              'news', 'meeting-point'], 'free', 'outdoor', ALL, DAYLONG),
        place('wochenmarkt', 'the Wednesday and Saturday market', 'market', 'am-markt', 'Stalls of eggs, cheese, '
              'cabbages, geese, pots and cloth fill the square twice a week.', ['market-day', 'food', 'haggling'],
              '$', 'outdoor', ALL, DAY, cuisine='german'),
        place('marktbrunnen', 'the market fountain', 'landmark', 'am-markt', 'A stone basin fed by a spring, '
              'where the town draws water and maids trade gossip with full buckets.', ['water', 'gossip', 'old'],
              'free', 'outdoor', ALL, DAYLONG),
        place('ratskeller', 'the Ratskeller', 'tavern', 'am-markt', 'A vaulted cellar under the town hall '
              'serving beer, wine and roast pork to councillors and anyone who can pay.', ['beer', 'councillors',
              'vaulted'], '$$', 'indoor', ADULT + ['coworkers'], ['afternoon', 'evening', 'late'], cuisine='german'),
        place('zum-tischlein', 'Zum Tischlein', 'inn', 'am-markt', 'The best inn in town, whose landlord gets '
              'touchy if guests ask whether he ever swapped a magic table for a plain one.', ['inn', 'travellers',
              'local-lore'], '$$', 'indoor', ALL, DAYLONG + ['late'], cuisine='german'),
        place('schwan-apotheke', 'the Swan apothecary', 'shopping', 'am-markt', 'Jars of salves, dried herbs and '
              'cough syrups behind a counter on the corner of the square.', ['herbs', 'remedies', 'shop'], '$',
              'indoor', ['solo', 'family'], DAY),
        # Schlossberg
        place('schlossgarten', 'the castle gardens', 'garden', 'schlossberg', 'Box hedges, fruit walls and a '
              'fountain behind the castle, opened to townsfolk on Sunday afternoons.', ['gardens', 'strolling',
              'court'], 'free', 'outdoor', ALL, ['afternoon'], WARM),
        place('dornenhecke', 'the briar hedge', 'landmark', 'schlossberg', 'A thick old hedge of wild roses '
              'grown over the ruined east wing, which the Count\'s gardeners are forbidden to cut.', ['roses',
              'local-lore', 'ruin'], 'free', 'outdoor', ALL, DAY, ['spring', 'summer']),
        place('schlosshof', 'the castle courtyard', 'landmark', 'schlossberg', 'The cobbled court inside the gate '
              'where petitioners wait, carts unload for the kitchens and the guard changes.', ['court',
              'petitions', 'busy'], 'free', 'outdoor', ['solo', 'coworkers'], DAY),
        place('schlosskapelle', 'the castle chapel', 'temple', 'schlossberg', 'A small painted chapel where the '
              'household hears mass and townsfolk may come in on feast days.', ['chapel', 'court', 'quiet'],
              'free', 'indoor', ['solo', 'family'], ['morning']),
        place('kuchengarten', 'the castle kitchen garden', 'garden', 'schlossberg', 'Rows of cabbages, beans and '
              'herbs below the kitchen windows, worked by the royal gardener and his boys.', ['vegetables',
              'work', 'gardens'], 'free', 'outdoor', ['solo', 'coworkers'], DAY, WARM),
        place('aussicht', 'the castle lookout', 'park', 'schlossberg', 'A linden-shaded terrace on the castle '
              'wall with a view over the roofs, the river and the dark line of the forest.', ['view', 'benches',
              'courting'], 'free', 'outdoor', ALL, ['afternoon', 'evening'], WARM),
        place('torkuche', 'the gate kitchen', 'restaurant', 'schlossberg', 'A hatch beside the castle gate where '
              'the under-cook sells yesterday\'s roasts and pies to petitioners, and boxes the scullion\'s ears if '
              'he dozes off.', ['pies', 'cheap', 'court'], '$', 'mixed', ALL, DAY, cuisine='german'),
        # Schustergasse
        place('lorenz-schuhe', 'Lorenz\'s shoe shop', 'shopping', 'schustergasse', 'A cobbler\'s shop with a pair of '
              'huge boots in the window labelled "seven leagues a stride, price on asking".', ['shoes', 'joke',
              'local-lore'], '$', 'indoor', ALL, DAY),
        place('sieben-streich', 'the Seven-at-a-Blow tailor', 'shopping', 'schustergasse', 'A tailor\'s shop whose '
              'owner keeps an embroidered belt over the counter and swears his grandfather earned it.', ['tailor',
              'clothes', 'local-lore'], '$$', 'indoor', ['solo', 'family'], DAY),
        place('zum-roten-stiefel', 'Zum Roten Stiefel', 'tavern', 'schustergasse', 'The Red Boot, a low-beamed '
              'tavern where journeymen drink after work and argue about their masters.', ['journeymen', 'beer',
              'cheap'], '$', 'indoor', ADULT + ['coworkers'], NIGHT),
        place('gesellenherberge', 'the journeymen\'s hostel', 'inn', 'schustergasse', 'Cheap bunks for travelling '
              'journeymen, kept by the guilds, with a long table for soup in the evening.', ['travellers', 'cheap',
              'guilds'], '$', 'indoor', ['solo', 'friends'], ['evening', 'late']),
        place('zunfthaus', 'the shoemakers\' and tailors\' guildhall', 'guildhall', 'schustergasse', 'A timber hall '
              'where the two guilds meet, test apprentices and hold their dances at Shrovetide.', ['guilds',
              'meetings', 'dances'], 'free', 'indoor', ['solo', 'coworkers', 'friends'], ['afternoon', 'evening']),
        # Bäckergasse
        place('becker-backerei', 'Becker\'s bakery', 'cafe', 'backergasse', 'Rye loaves, pretzels and poppy-seed '
              'rolls sold through the window from first light.', ['bread', 'pretzels', 'early'], '$', 'indoor', ALL,
              ['morning'], cuisine='bakery'),
        place('brei-kuche', 'the porridge kitchen', 'restaurant', 'backergasse', 'A widow\'s kitchen selling bowls '
              'of sweet millet porridge from a pot she swears she always tells to stop.', ['porridge', 'cheap',
              'local-lore'], '$', 'indoor', ALL, DAY, cuisine='german'),
        place('lebkuchner', 'the gingerbread baker', 'cafe', 'backergasse', 'Spiced honey cakes and gingerbread '
              'hearts, though the baker refuses outright to build a gingerbread cottage.', ['gingerbread', 'sweets',
              'gifts'], '$', 'indoor', ALL, DAY, cuisine='bakery'),
        place('backhaus', 'the common bakehouse', 'workshop', 'backergasse', 'The town oven where households bring '
              'their own dough to bake on Fridays and pay the baker a loaf in twenty.', ['oven', 'neighbours',
              'bread'], '$', 'indoor', ['solo', 'family'], ['morning']),
        place('wurststand', 'the sausage stall', 'market', 'backergasse', 'Grilled sausages on rye with mustard, '
              'sold from a brazier at the market end of the street.', ['sausages', 'quick', 'cheap'], '$',
              'outdoor', ALL, ['afternoon', 'evening'], cuisine='german'),
        place('zum-krug', 'Zum Krug', 'tavern', 'backergasse', 'The Jug, a bakers\' alehouse that opens at noon '
              'when the ovens cool and closes early.', ['beer', 'bakers', 'quiet'], '$', 'indoor', ADULT,
              ['afternoon', 'evening']),
        # Weberviertel
        place('holle-brunnen', 'the deep well', 'landmark', 'weberviertel', 'An old well in the weavers\' yard '
              'where, the story goes, a girl once dropped her spindle and climbed down after it.', ['well',
              'local-lore', 'water'], 'free', 'outdoor', ALL, DAYLONG),
        place('spinnstube', 'the spinning room', 'workshop', 'weberviertel', 'A big warm room where women bring '
              'their wheels on winter evenings to spin, sing and tell stories by one candle.', ['spinning',
              'stories', 'gossip'], 'free', 'indoor', ['solo', 'friends', 'family'], ['evening'], ['fall',
              'winter']),
        place('weberhof', 'the weavers\' yard', 'workshop', 'weberviertel', 'A courtyard ringed with loom rooms '
              'where linen is woven for the market and the castle.', ['looms', 'linen', 'work'], 'free', 'mixed',
              ['solo', 'coworkers'], DAY),
        place('bleiche', 'the bleaching green', 'park', 'weberviertel', 'A meadow inside the wall where linen is '
              'spread to whiten in the sun and children are paid to keep the geese off.', ['meadow', 'linen',
              'sunny'], 'free', 'outdoor', ALL, DAY, ['spring', 'summer']),
        place('zur-spindel', 'Zur Spindel', 'tavern', 'weberviertel', 'The Spindle, a weavers\' tavern with '
              'cheap cider and a fiddler on Saturdays.', ['cider', 'music', 'weavers'], '$', 'indoor', ADULT,
              NIGHT),
        # Kirchhof
        place('st-martin', 'St. Martin\'s church', 'temple', 'kirchhof', 'The town church with its squat tower, '
              'painted saints and the bell that rings the hours and the curfew.', ['church', 'bells', 'old'],
              'free', 'indoor', ALL, ['morning', 'afternoon']),
        place('haselbaum', 'the hazel tree in the churchyard', 'garden', 'kirchhof', 'An old hazel on a grave in '
              'the churchyard, where girls make wishes and leave a few lentils for the birds.', ['wishes',
              'birds', 'local-lore'], 'free', 'outdoor', ALL, DAY),
        place('klarissen', 'the convent of St. Clare', 'temple', 'kirchhof', 'A small house of nuns who keep a '
              'school, a herb garden and a guest room for women travelling alone.', ['convent', 'quiet',
              'herbs'], 'free', 'mixed', ['solo', 'family'], DAY),
        place('kirchlinde', 'the churchyard linden', 'park', 'kirchhof', 'A huge linden with a stone bench '
              'around its trunk, where old men sit after mass and the elders once held court.', ['shade',
              'benches', 'old'], 'free', 'outdoor', ALL, DAYLONG, WARM),
        place('pfarrbibliothek', 'the parish library', 'library', 'kirchhof', 'A room over the sacristy with '
              'chained books, sermons and an herbal, open to anyone who can read and asks the sexton.', ['books',
              'quiet', 'reading'], 'free', 'indoor', ['solo'], ['afternoon']),
        place('kusterschenke', 'the sexton\'s alehouse', 'tavern', 'kirchhof', 'Beer drawn in the sexton\'s front '
              'room by the lych gate; he no longer climbs the tower after dark, not since a boy who wanted to learn '
              'to shudder threw him down the stairs.', ['beer', 'local-lore', 'quiet'], '$', 'indoor', ADULT,
              ['afternoon', 'evening'], cuisine='german'),
        # Mühlbach
        place('alte-muhle', 'the old mill', 'workshop', 'muhlbach', 'The undershot mill on the Mühlbach, whose '
              'miller once boasted that his daughter could spin straw into gold.', ['mill', 'flour',
              'local-lore'], 'free', 'mixed', ['solo', 'coworkers'], DAY),
        place('muhlteich', 'the millpond', 'park', 'muhlbach', 'A reedy pond above the weir with ducks, a pair of '
              'swans and a path round it for an evening walk.', ['pond', 'swans', 'walks'], 'free', 'outdoor',
              ALL, ['afternoon', 'evening'], WARM),
        place('muhlgraben-weg', 'the millrace path', 'trail', 'muhlbach', 'A footpath along the millrace from the '
              'west gate to the weir under willows and alders.', ['willows', 'water', 'walks'], 'free', 'outdoor',
              ALL, DAYLONG, WARM),
        place('zum-kater', 'Zum Kater', 'tavern', 'muhlbach', 'The Tomcat, a millers\' tavern named for the '
              'youngest son who was left nothing but the mill cat.', ['beer', 'millers', 'local-lore'], '$',
              'indoor', ADULT, NIGHT, cuisine='german'),
        place('muhlfurt', 'the mill ford', 'landmark', 'muhlbach', 'Stepping stones across the stream below the '
              'mill, where carts splash through and boys catch crayfish.', ['ford', 'crayfish', 'stream'],
              'free', 'outdoor', ALL, DAY, ['summer']),
        # Am Fährhaus
        place('fahranleger', 'the ferry landing', 'docks', 'fahrhaus', 'The ferry stage under the bridge, where '
              'the ferryman pulls his raft across on a rope and grumbles that nobody ever takes the pole.',
              ['ferry', 'river', 'local-lore'], '$', 'outdoor', ALL, DAYLONG),
        place('fischmarkt', 'the fish stalls', 'market', 'fahrhaus', 'Fishermen\'s wives selling pike, carp, eel '
              'and crayfish from tubs on the bank every morning.', ['fish', 'river', 'early'], '$', 'outdoor', ALL,
              ['morning'], cuisine='fish'),
        place('zum-butt', 'Zum Butt', 'tavern', 'fahrhaus', 'The Flounder, a fishermen\'s tavern whose landlady is '
              'teased that she will want a palace next.', ['fish', 'river', 'local-lore'], '$', 'indoor', ADULT,
              NIGHT, cuisine='fish'),
        place('badestelle', 'the bathing meadow', 'beach', 'fahrhaus', 'A grassy bank and gravel shallows '
              'upstream of the ferry where the town swims on hot afternoons.', ['swimming', 'summer', 'meadow'],
              'free', 'outdoor', ALL, ['afternoon'], ['summer']),
        place('leinpfad', 'the towpath', 'trail', 'fahrhaus', 'A riverside path along the Eller past fishing '
              'huts, willows and the old boundary stones.', ['river', 'walks', 'willows'], 'free', 'outdoor', ALL,
              DAYLONG, WARM),
        # Gerberviertel
        place('badestube', 'the bathhouse', 'fitness', 'gerberviertel', 'A steam bath with hot tubs and a barber '
              'who trims beards, lets blood and knows everyone\'s business.', ['bath', 'steam', 'gossip'], '$',
              'indoor', ['solo', 'friends'], DAYLONG),
        place('gerberei', 'the tanyards', 'workshop', 'gerberviertel', 'Tan pits and drying sheds on the river '
              'below the town, kept downstream and downwind for good reason.', ['leather', 'smell', 'work'],
              'free', 'outdoor', ['solo', 'coworkers'], DAY),
        place('rattenfanger-haus', 'the ratcatcher\'s house', 'landmark', 'gerberviertel', 'A crooked house with '
              'the council\'s unpaid bill nailed to the door, kept by a ratcatcher with a long memory.', ['rats',
              'local-lore', 'odd'], 'free', 'outdoor', ALL, DAY),
        place('zur-laute', 'Zur Laute', 'tavern', 'gerberviertel', 'The Lute, a rough tavern where the town '
              'band of four old players has been "about to leave for Bremen" for twenty years.', ['music',
              'beer', 'local-lore'], '$', 'indoor', ADULT, NIGHT),
        place('garkuche', 'the south gate cookshop', 'restaurant', 'gerberviertel', 'Lentil soup, blood sausage '
              'and black bread for tanners and carters at the cheapest prices in town.', ['soup', 'cheap',
              'working'], '$', 'indoor', ['solo', 'friends', 'coworkers'], ['morning', 'afternoon'],
              cuisine='german'),
        # Gänseanger
        place('ganseweide', 'the goose meadow', 'park', 'ganseanger', 'A long green meadow outside the east gate '
              'where the goose girls drive the town\'s geese every morning.', ['geese', 'meadow', 'open'], 'free',
              'outdoor', ALL, DAY, WARM),
        place('dunkles-tor', 'the dark gate', 'landmark', 'ganseanger', 'The deep, dim east gate, with an old '
              'carved horse\'s head over the arch that the goose girls greet as they pass.', ['gate',
              'local-lore', 'old'], 'free', 'outdoor', ALL, DAYLONG),
        place('viehmarkt', 'the cattle market ground', 'market', 'ganseanger', 'Pens and hitching rails where '
              'cows, pigs, horses and geese are traded on the first Monday of each month.', ['livestock',
              'haggling', 'market-day'], 'free', 'outdoor', ALL, ['morning']),
        place('goldene-gans', 'the Golden Goose', 'inn', 'ganseanger', 'The carters\' inn by the east gate, with '
              'stabling, a long table and a painted goose on the sign that people swear sticks to fingers.',
              ['inn', 'carters', 'stabling'], '$', 'indoor', ALL, DAYLONG + ['late'], cuisine='german'),
        place('schutzenwiese', 'the marksmen\'s field', 'venue', 'ganseanger', 'A meadow with crossbow butts and '
              'a wooden bird on a pole, where the marksmen\'s guild shoots on summer Sundays.', ['crossbows',
              'contests', 'guild'], 'free', 'outdoor', ALL, ['afternoon'], ['spring', 'summer']),
        # Gartenvorstadt
        place('rapunzelgarten', 'the walled rampion garden', 'garden', 'gartenvorstadt', 'A high-walled garden '
              'full of rampion and lettuces whose owner sells nothing and lets nobody in.', ['gardens',
              'local-lore', 'walled'], 'free', 'outdoor', ['solo', 'date'], DAY, WARM),
        place('turm', 'the tower in the fields', 'landmark', 'gartenvorstadt', 'An old stone tower in the fields '
              'with one window at the top and no door at all, which nobody claims to own.', ['tower',
              'local-lore', 'walks'], 'free', 'outdoor', ALL, DAY),
        place('apothekergarten', 'the apothecary\'s garden', 'garden', 'gartenvorstadt', 'Neat beds of sage, '
              'chamomile, foxglove and poppies grown for the Swan apothecary\'s jars.', ['herbs', 'gardens',
              'quiet'], 'free', 'outdoor', ['solo', 'family'], DAY, WARM),
        place('obstwiesen-weg', 'the orchard path', 'trail', 'gartenvorstadt', 'A path through apple and pear '
              'meadows from the north gate out toward the tower.', ['orchards', 'blossom', 'walks'], 'free',
              'outdoor', ALL, DAYLONG, WARM),
        place('gartenwirtschaft', 'the garden tavern', 'tavern', 'gartenvorstadt', 'Tables under chestnut trees '
              'behind a market gardener\'s house, serving cider, cheese and radishes on summer evenings.',
              ['cider', 'outdoors', 'summer'], '$', 'outdoor', ALL, ['afternoon', 'evening'], ['spring', 'summer'],
              cuisine='german'),
        # Am Waldrand
        place('holzplatz', 'the woodyard', 'workshop', 'waldrand', 'A clearing stacked with cut logs, where the '
              'woodcutters split and sell firewood to carters from town.', ['timber', 'work', 'forest'], 'free',
              'outdoor', ['solo', 'coworkers'], DAY),
        place('verbotener-pfad', 'the path children are told not to take', 'trail', 'waldrand', 'A narrow track '
              'into the deep forest toward an old woman\'s cottage that local children are warned away from.',
              ['forest', 'local-lore', 'quiet'], 'free', 'outdoor', ['solo', 'friends'], DAY),
        place('kohlermeiler', 'the charcoal kilns', 'workshop', 'waldrand', 'Smoking turf-covered mounds tended '
              'day and night by the charcoal burners in their huts.', ['charcoal', 'smoke', 'work'], 'free',
              'outdoor', ['solo', 'coworkers'], DAYLONG),
        place('waldquelle', 'the forest spring', 'park', 'waldrand', 'A cold spring under beeches at the edge of '
              'the wood, a favourite place to rest on the way back with firewood.', ['spring', 'shade', 'water'],
              'free', 'outdoor', ALL, DAY, WARM),
        place('holzhauer-krug', 'the woodcutters\' alehouse', 'tavern', 'waldrand', 'A one-room alehouse with a '
              'bench outside, where woodcutters drink thin beer and talk about hard winters.', ['beer', 'forest',
              'cheap'], '$', 'indoor', ADULT, ['evening']),
        # Jägerhof
        place('jagdhaus', 'the hunting lodge inn', 'inn', 'jagerhof', 'The Count\'s old hunting lodge, now partly '
              'an inn serving venison and wild-mushroom stew to travellers on the forest road.', ['venison', 'inn',
              'forest'], '$$', 'indoor', ALL, DAYLONG, cuisine='german'),
        place('waldweg', 'the forest road path', 'trail', 'jagerhof', 'The marked path through the wood to the '
              'next village, where every parent says to keep to the path and not stop to pick flowers.',
              ['forest', 'local-lore', 'walks'], 'free', 'outdoor', ALL, DAY),
        place('hochsitz', 'the high seat', 'landmark', 'jagerhof', 'A wooden hunting stand on the edge of a '
              'clearing where deer come out at dusk.', ['deer', 'view', 'quiet'], 'free', 'outdoor', ['solo',
              'date'], ['morning', 'evening']),
        place('pilzwald', 'the mushroom woods', 'trail', 'jagerhof', 'Beech and oak woods where townsfolk go for '
              'mushrooms, bilberries and beechnuts in late summer and autumn.', ['foraging', 'berries',
              'mushrooms'], 'free', 'outdoor', ALL, DAY, ['summer', 'fall']),
        place('bildstock', 'the wayside shrine', 'temple', 'jagerhof', 'A painted shrine to St. Hubert on the '
              'forest road, where hunters leave a sprig of oak.', ['shrine', 'forest', 'quiet'], 'free', 'outdoor',
              ['solo', 'family'], DAY),
        # Eichdorf
        place('tanzlinde', 'the dancing linden', 'square', 'eichdorf', 'A great linden on the village green with '
              'a wooden floor built into its lower branches for dancing on feast days.', ['dancing', 'linden',
              'feasts'], 'free', 'outdoor', ALL, ['afternoon', 'evening'], WARM),
        place('dorfanger', 'the village green', 'park', 'eichdorf', 'Common grass with a pond for the geese, a '
              'pump and a bench for the old men.', ['green', 'geese', 'village'], 'free', 'outdoor', ALL, DAY),
        place('kelterei', 'the cider press', 'tavern', 'eichdorf', 'A farmhouse press that sells new cider and '
              'onion tart at long tables in autumn.', ['cider', 'autumn', 'farm'], '$', 'mixed', ALL,
              ['afternoon', 'evening'], ['fall'], cuisine='german'),
        place('dorfkirche', 'Eichdorf chapel', 'temple', 'eichdorf', 'A plain stone chapel with a wooden bell '
              'tower, served by the curate from town every other Sunday.', ['chapel', 'village', 'quiet'], 'free',
              'indoor', ['solo', 'family'], ['morning']),
        place('feldweg', 'the field path', 'trail', 'eichdorf', 'A path between strips of rye, flax and cabbages '
              'from the village back to the bridge.', ['fields', 'walks', 'larks'], 'free', 'outdoor', ALL,
              DAYLONG, WARM),
    ],
    'colleges': [
        {'id': 'klosterschule', 'name': 'the convent school of St. Clare', 'type': 'academy', 'neighborhood':
         'kirchhof', 'size': 'small', 'known_for': ['reading', 'needlework', 'latin', 'herbs'], 'source': S},
        {'id': 'zunftschule', 'name': 'the shoemakers\' and tailors\' guild apprenticeship', 'type': 'guild-school',
         'neighborhood': 'schustergasse', 'size': 'small', 'known_for': ['shoemaking', 'tailoring',
         'apprenticeship', 'masterpiece'], 'source': S},
        {'id': 'weberschule', 'name': 'the weavers\' guild school', 'type': 'guild-school', 'neighborhood':
         'weberviertel', 'size': 'small', 'known_for': ['weaving', 'spinning', 'linen'], 'source': S},
    ],
    'careers': [
        career('woodcutter', 'Woodcutter', 'forest', 'early', '$', 'Felling and splitting timber at the forest '
               'edge and selling firewood to carters from town.', ['the axe', 'hard winters', 'the forest',
               'feeding a family']),
        career('charcoal-burner', 'Charcoal burner', 'forest', 'rotating', '$', 'Building and tending the '
               'smoking kilns in the woods day and night for the smiths\' charcoal.', ['the kilns', 'night watches',
               'smoke', 'the deep wood']),
        career('miller', 'Miller', 'milling', 'early', '$$', 'Grinding grain at the Mühlbach mill and taking a '
               'share of every sack as toll.', ['the millstones', 'flour dust', 'tolls', 'boasting']),
        career('goose-girl', 'Goose girl', 'farming', 'early', '$', 'Driving the town\'s geese out through the '
               'dark gate to the meadow at dawn and home again at dusk.', ['the geese', 'the meadow', 'the gate',
               'long days']),
        career('shoemaker', 'Shoemaker', 'crafts', 'shift-day', '$', 'Cutting and stitching shoes and boots in '
               'a Schustergasse workshop, from the last to the finished pair.', ['the last', 'leather', 'the guild',
               'unfinished work']),
        career('tailor', 'Tailor', 'crafts', 'shift-day', '$', 'Cutting cloth, fitting customers and sewing '
               'coats and gowns, cross-legged on the workbench.', ['the needle', 'customers', 'the guild',
               'big talk']),
        career('baker', 'Baker', 'food', 'early', '$', 'Firing the oven before dawn for rye loaves, rolls and '
               'pretzels, by the town\'s weight rules.', ['the oven', 'dawn', 'the bread weight', 'neighbours']),
        career('spinner', 'Spinner', 'cloth', 'flexible', '$', 'Spinning flax and wool at home or in the '
               'spinning room, paid by the skein.', ['the wheel', 'piecework', 'stories', 'winter evenings']),
        career('weaver', 'Weaver', 'cloth', 'shift-day', '$', 'Weaving linen on a loom in the Weberviertel for '
               'merchants and the castle.', ['the loom', 'linen', 'the guild', 'family workshop']),
        career('huntsman', 'Huntsman', 'forest', 'early', '$$', 'Keeping the Count\'s game, culling deer and '
               'boar, and walking the forest road.', ['the forest', 'the Count', 'wolves', 'poachers']),
        career('ferryman', 'Ferryman', 'river', 'early', '$', 'Pulling the rope ferry across the Eller for carts, '
               'cattle and walkers, in all weathers.', ['the river', 'the rope', 'travellers', 'floods']),
        career('fisher', 'Fisher', 'river', 'early', '$', 'Setting nets and eel traps on the Eller and selling '
               'the catch from tubs on the bank.', ['nets', 'the river', 'the fish stalls', 'early mornings']),
        career('innkeeper', 'Innkeeper\'s hand', 'hospitality', 'evening', '$', 'Cooking, serving, making beds '
               'and stabling horses at one of the town\'s inns.', ['travellers', 'the kitchen', 'stabling',
               'news from the road']),
        career('apothecary', 'Apothecary', 'healing', 'shift-day', '$$', 'Making salves, syrups and powders at '
               'the Swan apothecary and advising on coughs and fevers.', ['herbs', 'remedies', 'patients',
               'the garden']),
        career('royal-gardener', 'Royal gardener', 'court', 'early', '$$', 'Keeping the castle\'s hedges, fruit '
               'walls and kitchen beds, and never cutting the briar hedge.', ['the castle gardens', 'seasons',
               'the Count', 'apprentices']),
        career('castle-servant', 'Castle servant', 'court', 'early', '$', 'Kitchen, laundry or chamber work in the '
               'Count\'s household, paid in wages, food and a livery coat.', ['the kitchen', 'the household',
               'gossip', 'feast days']),
        career('tanner', 'Tanner', 'crafts', 'shift-day', '$', 'Scraping hides and working the tan pits in the '
               'Gerberviertel.', ['the tan pits', 'leather', 'the smell', 'the river']),
        career('ratcatcher', 'Ratcatcher', 'trades', 'evening', '$', 'Trapping rats in cellars, granaries and '
               'the mill, and reminding the council what it owes.', ['rats', 'cellars', 'the council',
               'unpaid bills']),
        career('town-musician', 'Town musician', 'entertainment', 'evening', '$', 'Playing fiddle, horn or drum '
               'at weddings, dances and taverns as one of the town band.', ['the band', 'weddings', 'taverns',
               'old age']),
        career('carter', 'Carter', 'transport', 'early', '$', 'Driving ox and horse wagons of grain, timber and '
               'flour between the forest, the mill and the market.', ['the wagon', 'the roads', 'market days',
               'the horses']),
        career('market-gardener', 'Market gardener', 'farming', 'early', '$', 'Growing cabbages, lettuces, '
               'onions and herbs in the Gartenvorstadt for the market.', ['the garden', 'the market', 'weather',
               'neighbours\' walls']),
        career('convent-teacher', 'Convent schoolteacher', 'church', 'academic', '$', 'Teaching girls and small '
               'boys to read, count and sew at the convent of St. Clare.', ['the schoolroom', 'the sisters',
               'letters', 'pupils']),
    ],
    'employers': [
        employer('grafliche-hof', 'the Count\'s household', 'court', 'schlossberg', 'medium', 'The steward\'s '
                 'household that runs the castle\'s kitchens, laundry, chambers and stables.', ['castle-servant',
                 'royal-gardener', 'town-musician']),
        employer('schlossgartnerei', 'the castle gardens', 'court', 'schlossberg', 'small', 'The head gardener '
                 'and his boys, who keep the castle gardens and kitchen beds.', ['royal-gardener']),
        employer('forstamt', 'the Count\'s forest office', 'forest', 'jagerhof', 'small', 'The head forester\'s '
                 'office at the hunting lodge, which licenses woodcutting and keeps the game.', ['huntsman',
                 'woodcutter', 'charcoal-burner']),
        employer('jagdhaus-wirt', 'the hunting lodge inn', 'hospitality', 'jagerhof', 'small', 'The inn in the '
                 'old lodge on the forest road.', ['innkeeper']),
        employer('muhle', 'the Mühlbach mill', 'milling', 'muhlbach', 'small', 'The town\'s water mill, leased '
                 'from the Count to the master miller and his family.', ['miller', 'carter']),
        employer('tischlein-wirt', 'Zum Tischlein', 'hospitality', 'am-markt', 'medium', 'The best inn on the '
                 'market square, with kitchens, rooms and stabling.', ['innkeeper', 'town-musician']),
        employer('goldene-gans-wirt', 'the Golden Goose', 'hospitality', 'ganseanger', 'small', 'The carters\' '
                 'inn by the east gate, with stabling and horses for hire.', ['innkeeper', 'carter']),
        employer('schuhmacherzunft', 'the shoemakers\' and tailors\' guild', 'crafts', 'schustergasse', 'medium',
                 'The two craft guilds of Schustergasse and their masters\' workshops.', ['shoemaker', 'tailor']),
        employer('weberzunft', 'the weavers\' guild', 'cloth', 'weberviertel', 'medium', 'The guild of the '
                 'Weberviertel\'s weavers, who also put out flax to spinners.', ['weaver', 'spinner']),
        employer('backerzunft', 'the bakers of Bäckergasse', 'food', 'backergasse', 'small', 'Four family '
                 'bakeries and the common bakehouse under the bakers\' guild.', ['baker']),
        employer('schwan-apotheke-haus', 'the Swan apothecary', 'healing', 'am-markt', 'small', 'The town\'s only '
                 'apothecary, with a shop on the square and a garden outside the north gate.', ['apothecary',
                 'market-gardener']),
        employer('fahre', 'the Eller ferry and fishery', 'river', 'fahrhaus', 'small', 'The ferry rights and '
                 'fishing leases on the Eller, held from the town council.', ['ferryman', 'fisher']),
        employer('gerberei-haus', 'the Gerberviertel tanyards', 'crafts', 'gerberviertel', 'small', 'Three family '
                 'tanyards on the river below the south gate.', ['tanner']),
        employer('stadtrat', 'the town council', 'government', 'am-markt', 'small', 'The mayor and council in '
                 'the town hall, who pay the goose girls, the band and, in theory, the ratcatcher.',
                 ['goose-girl', 'ratcatcher', 'town-musician']),
        employer('klarissen-konvent', 'the convent of St. Clare', 'church', 'kirchhof', 'small', 'The nuns\' house '
                 'by St. Martin\'s, which runs the school and the herb garden.', ['convent-teacher', 'apothecary']),
        employer('eichdorf-hof', 'the Eichdorf farms', 'farming', 'eichdorf', 'medium', 'The village\'s farmers, '
                 'who hire hands for haymaking and harvest and send geese to market.', ['goose-girl', 'carter',
                 'market-gardener']),
    ],
    'career_hubs': [
        {'id': 'castle-and-forest', 'name': 'The castle and the forest', 'neighborhoods': ['schlossberg',
         'jagerhof', 'waldrand'], 'sectors': ['court', 'forest'], 'summary': 'The Count\'s household, gardens and '
         'forest office employ servants, gardeners, huntsmen and woodcutters.', 'source': S},
        {'id': 'guild-lanes', 'name': 'The guild lanes', 'neighborhoods': ['schustergasse', 'backergasse',
         'weberviertel', 'am-markt'], 'sectors': ['crafts', 'cloth', 'food', 'hospitality', 'healing'],
         'summary': 'Workshops, bakeries, inns and shops of the town\'s guilds inside the walls.', 'source': S},
        {'id': 'river-and-fields', 'name': 'The river and the fields', 'neighborhoods': ['muhlbach', 'fahrhaus',
         'gerberviertel', 'ganseanger', 'eichdorf'], 'sectors': ['milling', 'river', 'farming', 'transport'],
         'summary': 'The mill, ferry, tanyards, goose meadow and farms along the Eller.', 'source': S},
    ],
    'climate': {
        'summary': 'Approximate central-German weather: cold, grey winters with frost and some snow, late springs, '
                   'warm summers with thunderstorms, and misty autumns.',
        'months': [
            {'high_f': 37, 'low_f': 27, 'rain_days': 12, 'note': 'Cold; frost and the odd snowfall.'},
            {'high_f': 40, 'low_f': 28, 'rain_days': 10, 'note': 'Grey and raw; snow lies in the forest.'},
            {'high_f': 48, 'low_f': 32, 'rain_days': 11, 'note': 'Thaw and mud; first ploughing.'},
            {'high_f': 57, 'low_f': 37, 'rain_days': 10, 'note': 'Changeable; orchards in blossom late in '
             'the month.'},
            {'high_f': 65, 'low_f': 45, 'rain_days': 11, 'note': 'Mild and green; geese out on the meadow.'},
            {'high_f': 71, 'low_f': 51, 'rain_days': 11, 'note': 'Warm; haymaking and thunderstorms.'},
            {'high_f': 75, 'low_f': 55, 'rain_days': 12, 'note': 'Warmest month; swimming in the Eller.'},
            {'high_f': 74, 'low_f': 54, 'rain_days': 11, 'note': 'Warm; rye harvest in the fields.'},
            {'high_f': 66, 'low_f': 48, 'rain_days': 9, 'note': 'Mild; apples, mushrooms and cider.'},
            {'high_f': 56, 'low_f': 41, 'rain_days': 10, 'note': 'Cool and misty; leaves turn in the forest.'},
            {'high_f': 45, 'low_f': 35, 'rain_days': 12, 'note': 'Damp and dark early; first frosts.'},
            {'high_f': 39, 'low_f': 30, 'rain_days': 13, 'note': 'Cold and short days; snow some years.'},
        ],
        'source': S,
    },
    'annual_events': [
        event('epiphany-singers', 'Star singers', [1], 'kirchhof', 'Children in paper crowns carry a star from '
              'door to door at Epiphany, singing and chalking a blessing over each lintel.'),
        event('fastnacht', 'Fastnacht', [2, 3], 'schustergasse', 'The guilds hold dances and the journeymen parade '
              'in masks before Lent begins.'),
        event('walpurgis', 'Walpurgis night', [4], 'eichdorf', 'Bonfires on the hills and a racket of pots and '
              'whips to drive off witches on the last night of April.'),
        event('maypole', 'May Day', [5], 'eichdorf', 'Young people bring in birch boughs at dawn and dance round '
              'the maypole and the linden on Eichdorf green.'),
        event('schutzenfest', 'The marksmen\'s festival', [7], 'ganseanger', 'A week of crossbow shooting at a '
              'wooden bird, with a parade, a fair and a marksman king crowned for the year.'),
        event('st-john-fires', 'Midsummer fires', [6], 'fahrhaus', 'Bonfires on the riverbank on St. John\'s Eve, '
              'with couples jumping the embers and wreaths floated on the Eller.'),
        event('rye-harvest', 'Harvest home', [8], 'eichdorf', 'The last sheaf is tied into a figure and carried '
              'to the farm on a wagon, followed by a supper and dancing.'),
        event('kirmes', 'Kirmes', [9], 'am-markt', 'The church-dedication fair: booths, swings, roast ox and three '
              'days of dancing on the market square.'),
        event('erntedank', 'Harvest thanksgiving', [10], 'kirchhof', 'A harvest crown of grain and apples is hung '
              'in St. Martin\'s and the bread of the year is blessed.'),
        event('cider-pressing', 'Cider pressing', [9, 10], 'eichdorf', 'Families bring windfalls to the press and '
              'drink the new cider with onion tart at long tables.'),
        event('martinmas-lanterns', 'Martinmas lanterns', [11], 'kirchhof', 'Children carry paper lanterns through '
              'the streets singing St. Martin\'s songs, and every family that can afford one eats goose.'),
        event('st-nicholas', 'St. Nicholas\'s Eve', [12], 'backergasse', 'Children put out their shoes and find '
              'nuts, apples and gingerbread from the bakers in them in the morning.'),
        event('christmas-market', 'The Christmas market', [12], 'am-markt', 'Through Advent the square fills with '
              'booths of gingerbread, toys, candles and hot spiced wine.'),
        event('spinning-season', 'Spinning room season', [11, 12, 1, 2], 'weberviertel', 'From Martinmas to '
              'Candlemas the spinning rooms are full every evening of wheels, songs and long stories.'),
    ],
    'local_color': [
        color('straw-into-gold', 'The miller\'s boast', 'saying', 'When someone oversells a child or an apprentice, '
              'people say "careful, or they\'ll have to spin straw into gold", after the old miller of Mühlbach.',
              ['alte-muhle']),
        color('elves-finished-it', '"The elves finished it"', 'saying', 'Shoemakers who find work done that '
              'nobody admits to doing say the elves came in the night, and some leave out a small suit of clothes '
              'at Christmas just in case.', ['lorenz-schuhe']),
        color('seven-league-boots', 'Seven-league boots', 'shop', 'Lorenz the cobbler keeps a pair of enormous boots '
              'in his window as a joke and quotes an absurd price to anyone who asks.', ['lorenz-schuhe']),
        color('stay-on-the-path', '"Keep to the path"', 'saying', 'Every child sent through the wood is told to '
              'keep to the path, not stop to pick flowers and not talk to strangers, wolves especially.',
              ['waldweg', 'verbotener-pfad']),
        color('the-old-womans-cottage', 'The cottage in the wood', 'other', 'Children are warned off the track to '
              'an old woman\'s cottage deep in the forest, and told never to eat anything they find there.',
              ['verbotener-pfad']),
        color('bremen-band', 'The band that never got to Bremen', 'other', 'The town band of four old players, '
              'a braying horn, a fiddle, a growling bass and a crowing tenor, has been leaving for Bremen any day '
              'now for twenty years.', ['zur-laute']),
        color('the-unpaid-ratcatcher', 'The unpaid ratcatcher', 'custom', 'The council still owes the ratcatcher '
              'for clearing the granaries, he reminds them at every meeting, and mothers keep children indoors '
              'whenever he takes out his pipe.', ['rattenfanger-haus']),
        color('the-tower-with-no-door', 'The tower with no door', 'other', 'Nobody knows who built the tower in '
              'the fields; children dare each other to call up to the window, and the market gardeners give the '
              'walled rampion garden next to it a wide berth.', ['turm', 'rapunzelgarten']),
        color('frau-holle-snow', 'Frau Holle is shaking her beds', 'saying', 'When it snows, people say Mother '
              'Holle is shaking out her feather beds, and a hard-working girl is called a "gold girl".',
              ['holle-brunnen'], ['winter']),
        color('falada', 'Greeting the horse over the gate', 'custom', 'Goose girls say good morning to the carved '
              'horse\'s head over the dark gate every day, after the goose girl of the old story.',
              ['dunkles-tor', 'ganseweide']),
        color('little-pot-stop', '"Little pot, stop!"', 'saying', 'Said when anything runs on too long, from the '
              'tale of the sweet porridge pot that flooded a town because nobody knew the word to stop it.',
              ['brei-kuche']),
        color('sweet-millet', 'Sweet millet porridge', 'dish', 'Millet boiled in milk with honey and a pinch of '
              'cinnamon, the everyday breakfast for children and the poor.', ['brei-kuche']),
        color('seven-at-a-blow', '"Seven at one blow"', 'saying', 'A boast that turns out smaller than it sounds, '
              'after the little tailor whose seven were flies.', ['sieben-streich']),
        color('hans-in-luck', 'A Hans-in-luck trade', 'saying', 'Swapping something good for something worse and '
              'feeling pleased about it, like Hans who traded a lump of gold down to nothing on his way home.',
              ['wochenmarkt', 'viehmarkt']),
        color('clever-elsie', 'A Clever Elsie', 'saying', 'Someone who worries about troubles that have not '
              'happened yet, after the girl who wept in the cellar over a child she did not have.'),
        color('ilsebill', '"Like Ilsebill"', 'saying', 'Said of anyone never satisfied with what they have, after '
              'the fisherman\'s wife who kept asking the flounder for more.', ['zum-butt']),
        color('pea-under-the-mattress', 'The pea under the mattress', 'saying', 'A fussy guest is said to feel a pea '
              'through twenty mattresses, and the landlord of Zum Tischlein keeps a dried pea in a dish as a '
              'joke.', ['zum-tischlein']),
        color('martinmas-goose', 'Martinmas goose', 'dish', 'Roast goose with red cabbage and dumplings on St. '
              'Martin\'s day, the year\'s one goose for families who can manage it.', ['goldene-gans',
              'zum-tischlein'], ['fall']),
        color('gingerbread', 'Gingerbread', 'dish', 'Honey-and-spice cakes baked from Advent, sold as hearts and '
              'figures, though the baker will not make cottages.', ['lebkuchner'], ['winter']),
        color('show-me-your-paw', '"Show me your paw"', 'saying', 'What parents teach children to say before '
              'opening the door to a stranger, from the goat and the seven young kids.'),
    ],
    'names': {'groups': {'town': {
        'feminine': ['Gretel', 'Liese', 'Anna', 'Margarete', 'Katharina', 'Elisabeth', 'Barbara', 'Dorothea',
                     'Ursula', 'Agnes', 'Magdalena', 'Gertrud', 'Christine', 'Marie', 'Sophie', 'Johanna', 'Ilse',
                     'Hedwig', 'Klara', 'Regina', 'Sabine', 'Walburga', 'Eva', 'Apollonia'],
        'masculine': ['Hans', 'Jakob', 'Peter', 'Konrad', 'Heinrich', 'Friedrich', 'Wilhelm', 'Georg', 'Michel',
                      'Matthias', 'Kaspar', 'Lorenz', 'Martin', 'Johann', 'Christoph', 'Andreas', 'Ulrich', 'Veit',
                      'Sebastian', 'Thomas', 'Bastian', 'Wolfgang', 'Philipp', 'Nikolaus'],
        'neutral': ['Kim', 'Toni', 'Sascha', 'Luca'],
        'family': ['Müller', 'Schneider', 'Weber', 'Becker', 'Fischer', 'Schmidt', 'Wagner', 'Hoffmann', 'Koch',
                   'Bauer', 'Richter', 'Wolf', 'Schuster', 'Zimmermann', 'Krämer', 'Jäger', 'Gärtner', 'Vogt',
                   'Hartmann', 'Lange', 'Köhler', 'Holzer', 'Brenner', 'Fuchs', 'Engel', 'Keller', 'Roth',
                   'Sommer', 'Winter', 'Haas'],
    }}},
    'calendar': 'none',
    'holidays': [
        holiday('new-year', 'New Year\'s Day', 'public', 'The new year is rung in from St. Martin\'s tower and '
                'neighbours call with good wishes.', month=1, day=1),
        holiday('epiphany', 'Epiphany', 'feast', 'Twelfth Day, when the star singers go round and the Christmas '
                'greenery comes down.', month=1, day=6),
        holiday('candlemas', 'Candlemas', 'feast', 'Candles are blessed at St. Martin\'s and the spinning-room '
                'season ends.', month=2, day=2),
        holiday('shrove-tuesday', 'Fastnacht', 'observance', 'The last day before Lent, with doughnuts, masks '
                'and guild dances.', easter=-47),
        holiday('good-friday', 'Good Friday', 'public', 'A quiet day of fasting; the bells are silent until '
                'Easter.', easter=-2),
        holiday('easter', 'Easter Sunday', 'public', 'Coloured eggs, new clothes and the first lamb of the year '
                'after mass.', easter=0),
        holiday('easter-monday', 'Easter Monday', 'public', 'A day off for walking out to the villages and '
                'egg-rolling on the meadows.', easter=1),
        holiday('walpurgis-night', 'Walpurgis night', 'observance', 'Bonfires and noise to drive off witches on '
                'the eve of May.', month=4, day=30),
        holiday('may-day', 'May Day', 'feast', 'Birch boughs on the doors and dancing round the maypole.',
                month=5, day=1),
        holiday('ascension', 'Ascension Day', 'public', 'A holiday for walking the town bounds and drinking in '
                'the garden taverns.', easter=39),
        holiday('whit-monday', 'Whit Monday', 'public', 'Shops shut, the guilds walk out to the woods and the '
                'cattle go up to summer grazing.', easter=50),
        holiday('st-johns-day', 'St. John\'s Day', 'feast', 'Midsummer: bonfires on the eve and herbs gathered '
                'at dawn.', month=6, day=24),
        holiday('harvest-thanksgiving', 'Harvest thanksgiving', 'feast', 'The harvest crown at St. Martin\'s on '
                'the first Sunday of October.', month=10, weekday=6, nth=1),
        holiday('all-souls', 'All Souls\' Day', 'observance', 'Graves are tidied and candles lit in the '
                'churchyard.', month=11, day=2),
        holiday('martinmas', 'Martinmas', 'feast', 'Lantern processions, roast goose, and rents and wages due.',
                month=11, day=11),
        holiday('st-nicholas', 'St. Nicholas\'s Day', 'feast', 'Children find nuts and gingerbread in their '
                'shoes.', month=12, day=6),
        holiday('christmas-eve', 'Christmas Eve', 'observance', 'Shops close at noon and families gather for '
                'carp and the midnight mass.', month=12, day=24),
        holiday('christmas', 'Christmas Day', 'public', 'Mass, a goose or a ham, and no work in the fields.',
                month=12, day=25),
        holiday('st-stephens-day', 'St. Stephen\'s Day', 'public', 'The second day of Christmas, for visiting '
                'and riding out the horses.', month=12, day=26),
    ],
    'prices': [
        price('beer', 'Mug of beer', 0.5, 1),
        price('wine', 'Glass of wine', 1, 3),
        price('loaf', 'Rye loaf', 1, 2),
        price('gingerbread', 'Gingerbread', 0.25, 1, 'a piece'),
        price('meal', 'Meal at the Ratskeller', 3, 6),
        price('inn', 'Bed at the inn', 4, 8, 'a night'),
        price('board', 'Board and lodging', 15, 25, "a week's board"),
        price('ferry', 'Ferry crossing', 0.25, 0.5, 'one way'),
        price('cart-hire', 'Horse and cart', 12, 24, 'a day'),
        price('bath', 'Bathhouse', 1, 2, 'a bath'),
        price('tobacco', 'Pipe tobacco', 1, 2, 'a packet'),
        price('clogs', 'Wooden shoes', 4, 8, 'a pair'),
        price('goose', 'Goose at market', 12, 24, 'for Martinmas'),
        price('wage', "Labourer's wage", 6, 10, 'a day'),
    ],
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
