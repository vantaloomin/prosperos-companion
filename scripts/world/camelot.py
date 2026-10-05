"""Curated Camelot data. Run `python scripts/world/camelot.py` to rewrite the shipped JSON."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'cities' / 'camelot.json'
S = 'curated-2026-10'


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
            'themes': themes, 'eras': ['medieval']}


def employer(id, name, sector, hood, size, summary, careers):
    return {'id': id, 'name': name, 'sector': sector, 'neighborhood': hood, 'size': size, 'summary': summary,
            'careers': careers, 'source': S}


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
WARM = ['spring', 'summer', 'fall']
FOOT = ['on-foot', 'carriers']

CITY = {
    'schema_version': 1, 'id': 'camelot', 'name': 'Camelot', 'setting': 'fictional', 'era': 'medieval',
    'basis': 'Arthurian legend in public-domain tellings: Malory\'s Le Morte d\'Arthur (1485), the romances of '
             'Chretien de Troyes (12th century), Tennyson\'s Idylls of the King (1859-1885) and Howard Pyle\'s '
             'King Arthur books (1903-1910). Town life is filled in from ordinary medieval English towns.',
    'region': 'Logres', 'country': 'Britain', 'timezone': 'Europe/London',
    'aliases': ['Camelot in Logres', 'the King\'s city', 'Kamelot'],
    'summary': 'King Arthur\'s walled city on a hill above the river Cam: the castle with its Round Table hall '
               'and St Stephen\'s Minster at the top, and below them markets, guild streets, inns, mills, '
               'tanneries and farmland worked by ordinary townsfolk.',
    'lat': 51.02, 'lon': -2.53,
    'currency': {'code': 'penny', 'symbol': 'd.', 'name': 'silver pennies'},
    'rent_period': 'week',
    'speeds': {'walk': 4.5, 'horse': 10, 'carriage': 5, 'boat': 6},
    'sources': {
        S: {'kind': 'curated', 'title': 'Camelot wards, places and trades written for Prospero Companion',
            'license': 'CC0-1.0', 'retrieved': '2026-10-05',
            'note': 'An original town plan for fiction. The castle, the Round Table, St Stephen\'s church (where '
                    'Malory has Arthur wed Guenever), Pentecost courts and tournaments, the river barge from '
                    'Astolat and the realm of Logres come from public-domain sources: Malory, Chretien de Troyes, '
                    'Tennyson and Howard Pyle. Streets, inns, guilds and townspeople are invented on the pattern '
                    'of real medieval English towns; nothing is taken from modern film, television or stage '
                    'adaptations. Coordinates sit around Cadbury Castle in Somerset, the traditional site. Rents '
                    'are rough weekly sums in silver pennies. Climate values are rounded southern England '
                    'averages.'},
    },
    'neighborhoods': [
        hood('castle-ward', 'Castle Ward', 'The upper bailey inside the castle walls: the great hall of the Round '
             'Table, the royal lodgings, kitchens, stables and the barracks of the household.',
             ['royal', 'walled', 'busy-at-court'], 51.025, -2.530, 'very-high', ([4, 6], [8, 12], [16, 24]),
             ['servants-loft', 'tower-chamber', 'lodging-range'], 'high', ['on-foot', 'kings-horses']),
        hood('minster-close', 'Minster Close', 'The quiet walled close around St Stephen\'s Minster, with canons\' '
             'houses, the song school and a lawn where clerks walk between services.',
             ['quiet', 'religious', 'scholarly'], 51.022, -2.526, 'high', ([3, 5], [7, 10], [12, 18]),
             ['canons-house', 'rented-chamber'], 'high', ['on-foot']),
        hood('cheapside', 'Cheapside', 'The market street and square below the castle gate, lined with shops, '
             'the guildhall, the market cross and the best inns.', ['market', 'central', 'crowded'], 51.019,
             -2.531, 'high', ([3, 5], [6, 10], [12, 20]), ['shop-with-solar', 'rented-chamber', 'timber-house'],
             'high', FOOT),
        hood('shambles', 'The Shambles', 'A narrow street of butchers\' stalls with overhanging upper floors, '
             'cookshops and cheap rooms over the shops.', ['narrow', 'food', 'cheap-rooms'], 51.018, -2.534, 'mid',
             ([2, 3], [4, 6], [7, 11]), ['rented-chamber', 'shop-with-solar'], 'high', ['on-foot']),
        hood('smithgate', 'Smithgate', 'The street of forges and armourers by the west gate, loud with hammers '
             'from dawn and busy before every tournament.', ['crafts', 'noisy', 'working'], 51.020, -2.538, 'mid',
             ([2, 3], [4, 6], [8, 12]), ['workshop-dwelling', 'rented-chamber'], 'high', FOOT),
        hood('fishergate', 'Fishergate', 'The lane down from the market to the river wharf, with fishmongers, '
             'the watermen\'s houses and the Swan inn.', ['river', 'working', 'fish'], 51.015, -2.528, 'mid',
             ([2, 3], [4, 6], [7, 11]), ['timber-house', 'rented-chamber'], 'high', ['on-foot', 'cam-barges']),
        hood('bridgefoot', 'Bridgefoot', 'Where the stone bridge crosses the Cam: the toll house, the wharf for '
             'barges up from Astolat, warehouses and a row of alehouses.', ['river', 'trade', 'alehouses'], 51.012,
             -2.525, 'mid', ([2, 3], [4, 7], [8, 12]), ['timber-house', 'warehouse-loft'], 'high',
             ['on-foot', 'cam-barges', 'carriers']),
        hood('southgate', 'Southgate', 'A ward of weavers, dyers and bakers inside the south gate, with tenter '
             'frames in the yards and the bathhouse on Pump Lane.', ['crafts', 'family', 'neighbourly'], 51.014,
             -2.535, 'mid', ([2, 3], [3, 5], [6, 10]), ['timber-house', 'rented-chamber', 'cottage'], 'high', FOOT),
        hood('barkers-end', 'Barkers End', 'The tannery quarter outside the walls on the river, kept downwind of '
             'the town for its smell: tan pits, curriers and cheap cottages.', ['outside-walls', 'river', 'cheap'],
             51.008, -2.533, 'low', ([1, 2], [2, 3], [4, 6]), ['cottage', 'rented-chamber'], 'medium',
             ['on-foot', 'cam-barges']),
        hood('mill-end', 'Mill End', 'The King\'s mill on the Cam with its weir, the miller\'s house, a ford, '
             'and a hamlet of millers\' and carters\' cottages.', ['river', 'rural-edge', 'quiet'], 51.010, -2.515,
             'low', ([1, 2], [2, 4], [5, 7]), ['cottage', 'longhouse'], 'medium', ['on-foot', 'carriers',
             'mill-ferry']),
        hood('st-giles', 'St Giles Without', 'A suburb outside the east gate around the Hospital of St Giles, '
             'with its infirmary, almshouses and herb garden.', ['outside-walls', 'hospital', 'quiet'], 51.021,
             -2.518, 'low', ([1, 2], [2, 4], [5, 8]), ['cottage', 'almshouse', 'rented-chamber'], 'medium', FOOT),
        hood('abbey-precinct', 'St Mary\'s Abbey', 'The Benedictine abbey north of the walls, with its school, '
             'library, orchards, fishponds and the lay folk who work its lands.', ['religious', 'orchards',
             'scholarly'], 51.032, -2.524, 'mid', ([2, 3], [3, 5], [6, 10]), ['cottage', 'guest-house'], 'medium',
             FOOT),
        hood('tiltyard-meads', 'Tiltyard Meads', 'Flat meadows by the river below the castle where the lists are '
             'set up for tournaments, with grazing, archery butts and the horse fair ground.',
             ['tournaments', 'open-ground', 'horses'], 51.028, -2.540, 'mid', ([2, 3], [3, 5], [6, 9]),
             ['cottage', 'stable-loft'], 'medium', ['on-foot', 'kings-horses']),
        hood('woolston', 'Woolston', 'A farming village of open fields, strips and a green, two miles out on the '
             'road to Ilchester.', ['village', 'farming', 'family'], 51.040, -2.565, 'low',
             ([1, 2], [2, 3], [3, 6]), ['cottage', 'longhouse', 'farmhouse'], 'low', ['carriers']),
        hood('forest-side', 'Forest Side', 'Scattered cottages, charcoal burners and the verderer\'s lodge where '
             'the fields give way to the King\'s forest to the east.', ['forest', 'remote', 'quiet'], 51.020,
             -2.480, 'low', ([1, 1], [1, 3], [3, 5]), ['cottage', 'woodward-lodge'], 'low',
             ['carriers', 'kings-horses']),
    ],
    'transit': [
        {'id': 'on-foot', 'name': 'On foot', 'kind': 'walk', 'summary': 'How almost everyone gets about: the walls '
         'can be walked round in half an hour and the villages are an hour out.', 'source': S},
        {'id': 'kings-horses', 'name': 'Horses from the royal stables', 'kind': 'horse', 'summary': 'Household '
         'officers and messengers ride; others hire a hackney from the ostlers at the Bell.', 'source': S},
        {'id': 'carriers', 'name': 'Carriers\' carts', 'kind': 'carriage', 'summary': 'Ox and horse carts carry '
         'grain, wool, timber and riders willing to sit on the load, leaving from Cheapside on market days.',
         'source': S},
        {'id': 'cam-barges', 'name': 'Cam barges', 'kind': 'boat', 'summary': 'Flat barges poled and towed along '
         'the Cam between Bridgefoot, Barkers End and Astolat downriver.', 'source': S},
        {'id': 'mill-ferry', 'name': 'Mill End ferry', 'kind': 'ferry', 'summary': 'A rope ferry across the Cam '
         'above the weir, for when the ford is too high.', 'source': S},
    ],
    'places': [
        # Castle and court
        place('round-table-hall', 'the great hall of the Round Table', 'landmark', 'castle-ward', 'The castle\'s '
              'great hall, where the Round Table stands and the court sits down to feast on high days.',
              ['court', 'iconic', 'feasts'], 'free', 'indoor', ['solo', 'friends', 'coworkers'], ['afternoon',
              'evening']),
        place('castle-gatehouse', 'the castle gatehouse', 'landmark', 'castle-ward', 'Twin towers over the gate '
              'where petitioners queue, news is cried and the watch changes at dusk.', ['court', 'news', 'walls'],
              'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('castle-herb-garden', 'the Queen\'s herb garden', 'garden', 'castle-ward', 'A walled garden of '
              'turf seats, roses, lavender and kitchen herbs under the south wall of the castle.',
              ['flowers', 'quiet', 'walled'], 'free', 'outdoor', ['solo', 'date', 'friends'], DAY, WARM),
        place('castle-wall-walk', 'the wall walk', 'trail', 'castle-ward', 'The walkway along the castle '
              'battlements, with a view down over the town, the river and the forest.', ['views', 'walk',
              'walls'], 'free', 'outdoor', ['solo', 'date', 'friends'], ['morning', 'afternoon', 'evening']),
        place('tiltyard', 'the tiltyard', 'stadium', 'tiltyard-meads', 'The lists on the meadow below the castle, '
              'with stands for the court and standing room for the town on tournament days.',
              ['tournaments', 'crowds', 'horses'], '$', 'outdoor', ALL, DAY, WARM),
        place('archery-butts', 'the archery butts', 'fitness', 'tiltyard-meads', 'Earth banks with straw targets '
              'where townsmen practise the longbow on Sunday afternoons.', ['archery', 'practice', 'sport'],
              'free', 'outdoor', ['solo', 'friends'], DAY, WARM),
        place('horse-fair-ground', 'the horse fair ground', 'market', 'tiltyard-meads', 'Railed pens by the '
              'river where horses are trotted out, haggled over and sold.', ['horses', 'trade'], '$', 'outdoor',
              ['solo', 'friends', 'family'], DAY, WARM),
        # Minster and churches
        place('st-stephens-minster', 'St Stephen\'s Minster', 'temple', 'minster-close', 'The great church of '
              'Camelot, where knights keep their vigil before they are made and the court hears mass on feast '
              'days.', ['church', 'iconic', 'vigil'], 'free', 'indoor', ALL, ['morning', 'afternoon', 'evening']),
        place('minster-treasury', 'the minster treasury', 'museum', 'minster-close', 'A vaulted chamber where the '
              'canons show pilgrims the reliquaries, banners and gifts given by kings.', ['relics', 'history',
              'pilgrims'], '$', 'indoor', ALL, DAY),
        place('minster-close-lawn', 'the Close lawn', 'park', 'minster-close', 'Grass and old yews inside the '
              'Close wall, where clerks read and townsfolk sit after mass.', ['quiet', 'trees', 'reading'], 'free',
              'outdoor', ALL, DAY, WARM),
        place('st-martins-church', 'St Martin\'s, Cheapside', 'temple', 'cheapside', 'The market parish church, '
              'its porch used for weddings, contracts and gossip.', ['church', 'parish', 'weddings'], 'free',
              'indoor', ALL, ['morning', 'afternoon']),
        # Market and shops
        place('market-square', 'the market square', 'square', 'cheapside', 'The open square under the castle hill '
              'with the market cross, the stocks, the town well and space for criers and players.',
              ['market', 'news', 'crowds'], 'free', 'outdoor', ALL, ['morning', 'afternoon']),
        place('cheapside-market', 'Cheapside market', 'market', 'cheapside', 'Wednesday and Saturday stalls of '
              'cheese, eggs, poultry, onions, cloth and pots along both sides of the street.', ['market', 'food',
              'haggling'], '$', 'outdoor', ALL, DAY),
        place('the-mercery', 'the Mercery', 'shopping', 'cheapside', 'A row of mercers\' shops selling linen, '
              'silk ribbon, thread, gloves and purses from open shutters.', ['cloth', 'shopping', 'fine-goods'],
              '$$', 'mixed', ['solo', 'friends', 'date'], DAY),
        place('guildhall', 'the Guildhall', 'guildhall', 'cheapside', 'The merchants\' hall over an open arcade, '
              'where the mayor\'s court sits and the guild feasts are held.', ['guilds', 'civic', 'feasts'], 'free',
              'indoor', ['solo', 'coworkers', 'friends'], DAY),
        place('the-bell', 'the Bell', 'inn', 'cheapside', 'The largest inn on Cheapside, with a galleried yard, '
              'stabling for forty horses and a long table for travellers\' suppers.', ['inn', 'travellers',
              'suppers'], '$$', 'indoor', ['solo', 'friends', 'date', 'coworkers'], NIGHT, cuisine='English'),
        place('the-chequers', 'the Chequers', 'tavern', 'cheapside', 'A wine tavern under a chequerboard sign, '
              'where clerks and merchants dice and drink Gascon wine.', ['wine', 'dice', 'merchants'], '$$',
              'indoor', ADULT, NIGHT),
        place('market-cross-steps', 'the steps of the market cross', 'landmark', 'cheapside', 'Stone steps round '
              'the market cross where friars preach, criers read proclamations and people wait to meet.',
              ['meeting-place', 'news', 'preaching'], 'free', 'outdoor', ALL, DAY),
        # Shambles
        place('shambles-cookshop', 'Agnes Pie\'s cookshop', 'restaurant', 'shambles', 'A hot cookshop on the '
              'Shambles selling meat pies, pease pottage and roast capon over the counter.', ['pies', 'cheap',
              'hot-food'], '$', 'indoor', ALL, ['afternoon', 'evening'], cuisine='English'),
        place('shambles-bakehouse', 'the Shambles bakehouse', 'cafe', 'shambles', 'A common oven where '
              'households bring dough at dawn and buy wastel loaves and spiced buns warm.', ['bread', 'morning',
              'neighbours'], '$', 'indoor', ALL, ['morning']),
        place('butchers-row', 'Butchers\' Row', 'market', 'shambles', 'The open-fronted meat stalls of the '
              'Shambles, cheapest just before the Saturday bell.', ['meat', 'market', 'haggling'], '$', 'outdoor',
              ['solo', 'family'], ['morning']),
        place('the-three-cranes', 'the Three Cranes', 'tavern', 'shambles', 'A low-beamed alehouse with a '
              'settle by the fire, popular with butchers, carters and apprentices.', ['ale', 'cheap', 'fire'], '$',
              'indoor', ADULT, NIGHT),
        # Smithgate
        place('armourers-row', 'Armourers\' Row', 'workshop', 'smithgate', 'Forges where mail is riveted and '
              'plates are hammered, with squires waiting outside for repairs before tournaments.', ['forges',
              'armour', 'tournaments'], '$$', 'mixed', ['solo', 'friends'], DAY),
        place('the-green-dragon', 'the Green Dragon', 'tavern', 'smithgate', 'A smiths\' alehouse by the west '
              'gate with a skittle alley in the yard.', ['ale', 'skittles', 'craftsmen'], '$', 'mixed', ADULT,
              NIGHT),
        place('west-gate-smithy-yard', 'the west gate smithy yard', 'workshop', 'smithgate', 'The farrier\'s '
              'yard where horses are shod and carters wait their turn.', ['horses', 'farrier', 'waiting'], '$',
              'outdoor', ['solo', 'friends'], DAY),
        # River
        place('fishergate-fish-market', 'Fishergate fish stalls', 'market', 'fishergate', 'Wet slabs of eel, '
              'pike, salted herring and river trout sold early, especially on Fridays and through Lent.',
              ['fish', 'market', 'early'], '$', 'outdoor', ['solo', 'family'], ['morning']),
        place('the-swan', 'the Swan', 'inn', 'fishergate', 'A riverside inn with a garden down to the water, '
              'where bargemen and travellers eat eel pie.', ['river', 'garden', 'eel-pie'], '$$', 'mixed', ALL,
              ['afternoon', 'evening'], cuisine='English'),
        place('bridgefoot-wharf', 'Bridgefoot wharf', 'docks', 'bridgefoot', 'The stone quay below the bridge '
              'where barges from Astolat unload wine, salt, wool and timber.', ['river', 'barges', 'trade'],
              'free', 'outdoor', ['solo', 'friends', 'family'], DAY),
        place('cam-bridge', 'the Cam bridge', 'landmark', 'bridgefoot', 'The five-arched stone bridge with a '
              'small chapel on the middle pier where travellers leave a coin.', ['bridge', 'chapel', 'views'],
              'free', 'outdoor', ALL, ['morning', 'afternoon', 'evening']),
        place('the-star', 'the Star', 'tavern', 'bridgefoot', 'A bargemen\'s alehouse on the quay, rowdy on '
              'pay nights, with a brewster who brews twice a week.', ['ale', 'bargemen', 'river'], '$', 'indoor',
              ADULT, NIGHT),
        place('towpath', 'the Cam towpath', 'trail', 'bridgefoot', 'A path along the river past willows, eel '
              'traps and grazing meadows toward Astolat.', ['river', 'walk', 'willows'], 'free', 'outdoor', ALL,
              DAY, WARM),
        place('cam-shallows', 'the bathing shallows', 'beach', 'mill-end', 'A gravel bank above the weir where '
              'children paddle and townsfolk swim on hot evenings.', ['swimming', 'summer', 'river'], 'free',
              'outdoor', ['friends', 'family', 'solo'], ['afternoon', 'evening'], ['summer']),
        place('kings-mill', 'the King\'s mill', 'workshop', 'mill-end', 'The undershot water mill where the town\'s '
              'grain is ground and millers take their toll from every sack.', ['mill', 'grain', 'river'], 'free',
              'mixed', ['solo', 'family'], DAY),
        # Southgate
        place('pump-lane-bathhouse', 'the Pump Lane bathhouse', 'fitness', 'southgate', 'A stewhouse with wooden '
              'tubs and a steam room, men\'s days and women\'s days, cheap on Saturdays.', ['bath', 'steam',
              'clean'], '$', 'indoor', ['solo', 'friends'], ['afternoon', 'evening']),
        place('bread-street-bakery', 'Bread Street bakers', 'cafe', 'southgate', 'Three bakers\' shops side by '
              'side selling white loaves, rye, simnel cakes and hot cross buns in season.', ['bread', 'cakes',
              'morning'], '$', 'indoor', ALL, ['morning']),
        place('dyers-yard', 'the dyers\' yard', 'workshop', 'southgate', 'Vats of woad, madder and weld steaming '
              'in a yard by the town ditch, cloth hung blue and red on the tenter frames.', ['cloth', 'colour',
              'craft'], 'free', 'outdoor', ['solo', 'friends'], DAY),
        place('mother-joans-alehouse', 'Mother Joan\'s alehouse', 'tavern', 'southgate', 'A front-room '
              'alehouse with an ale-stake over the door, where weavers\' wives meet in the evening.', ['ale',
              'neighbours', 'homely'], '$', 'indoor', ['solo', 'friends'], NIGHT),
        # Outside the walls
        place('barkers-end-tan-pits', 'the tan pits', 'workshop', 'barkers-end', 'Pits of oak-bark liquor where '
              'hides soak for a year; the smell carries if the wind turns.', ['tannery', 'leather', 'smell'],
              'free', 'outdoor', ['solo'], DAY),
        place('st-giles-hospital', 'the Hospital of St Giles', 'temple', 'st-giles', 'The infirmary hall and '
              'chapel run by the brothers and sisters of St Giles, open to the sick, the old and travellers.',
              ['infirmary', 'charity', 'chapel'], 'free', 'indoor', ['solo', 'family'], ['morning', 'afternoon']),
        place('st-giles-physic-garden', 'the St Giles physic garden', 'garden', 'st-giles', 'Raised beds of '
              'feverfew, comfrey, sage and poppy kept by the infirmarer, with a bench by the well.', ['herbs',
              'quiet', 'healing'], 'free', 'outdoor', ['solo', 'date', 'friends'], DAY, WARM),
        place('abbey-library', 'the abbey library', 'library', 'abbey-precinct', 'A cloister walk of book '
              'presses and a chained reading desk, open to scholars and to townsfolk with the librarian\'s leave.',
              ['books', 'quiet', 'scholars'], 'free', 'indoor', ['solo'], DAY),
        place('abbey-orchards', 'the abbey orchards', 'park', 'abbey-precinct', 'Rows of apple, pear and medlar '
              'trees by the fishponds, open for walking and blossom in spring, picking in autumn.', ['orchard',
              'blossom', 'apples'], 'free', 'outdoor', ALL, DAY, WARM),
        place('abbey-guest-hall', 'the abbey guest hall', 'inn', 'abbey-precinct', 'Plain lodging and a supper '
              'of bread, pottage and small beer for pilgrims and travellers, paid for by gift.', ['pilgrims',
              'plain', 'quiet'], '$', 'indoor', ['solo', 'family'], DINNER, cuisine='English'),
        place('woolston-green', 'Woolston green', 'park', 'woolston', 'A village green with a pond, a maypole '
              'and a bench under the elm, where the reeve calls the harvest.', ['village', 'maypole', 'pond'],
              'free', 'outdoor', ALL, ['afternoon', 'evening'], WARM),
        place('the-plough', 'the Plough', 'tavern', 'woolston', 'A thatched village alehouse where field hands '
              'drink after work and fiddlers play on Saturdays.', ['ale', 'village', 'fiddle'], '$', 'indoor',
              ['solo', 'friends'], NIGHT),
        place('forest-ride', 'the forest ride', 'trail', 'forest-side', 'A broad green track into the King\'s '
              'forest under oak and beech, used by hunts, swineherds and walkers.', ['forest', 'walk', 'oaks'],
              'free', 'outdoor', ['solo', 'friends', 'date'], DAY, WARM),
        place('guildhall-undercroft', 'the Guildhall undercroft', 'venue', 'cheapside', 'A vaulted room under the '
              'Guildhall where minstrels, storytellers and the guild players perform on winter evenings.',
              ['music', 'stories', 'plays'], '$', 'indoor', ADULT + ['family'], DINNER, ['fall', 'winter']),
        # More everyday places, so every ward has somewhere to eat, drink and meet
        place('castle-buttery', 'the buttery hatch', 'restaurant', 'castle-ward', 'The hatch by the castle kitchens '
              'where the butler hands out bread, cheese and ale to the household, and the broken meats of the high '
              'table go to the poor.', ['bread', 'ale', 'household'], 'free', 'indoor', ['solo', 'coworkers'],
              ['morning', 'afternoon'], cuisine='English'),
        place('castle-well-court', 'the well court', 'square', 'castle-ward', 'A cobbled yard round the castle well '
              'where grooms, laundresses and pages draw water and trade the gossip of the court.',
              ['well', 'gossip', 'servants'], 'free', 'outdoor', ALL, DAY),
        place('the-mitre', 'the Mitre', 'tavern', 'minster-close', 'A quiet alehouse just outside the Close gate, '
              'kept by a former verger, where clerks and choirmen drink after evensong.',
              ['ale', 'clerks', 'quiet'], '$', 'indoor', ADULT, NIGHT),
        place('song-school-door', 'the song school door', 'venue', 'minster-close', 'A long room by the cloister '
              'where the choirboys practise plainsong each morning and anyone may stand at the door and listen.',
              ['music', 'chant', 'choir'], 'free', 'indoor', ALL, ['morning']),
        place('pudding-wifes-stall', 'the pudding wife\'s stall', 'cafe', 'shambles', 'A trestle at the foot of the '
              'Shambles selling hot black puddings, sausages and tripe from a pan over coals.',
              ['sausages', 'cheap', 'hot-food'], '$', 'outdoor', ['solo', 'friends'], DAY, cuisine='English'),
        place('cutlers-cookstall', 'the cutlers\' cookstall', 'cafe', 'smithgate', 'A cookstall against the forge '
              'wall where smiths buy hot pasties and mulled ale between heats.', ['pasties', 'cheap', 'hot-food'],
              '$', 'outdoor', ['solo', 'friends', 'coworkers'], DAY, cuisine='English'),
        place('west-gate-conduit', 'the west gate conduit', 'square', 'smithgate', 'A stone cistern fed by a pipe '
              'from the hill spring, where apprentices fill buckets for the quenching tubs and wives fill jugs.',
              ['water', 'meeting-place', 'neighbours'], 'free', 'outdoor', ALL, DAY),
        place('fishergate-net-lofts', 'the net lofts', 'workshop', 'fishergate', 'Lofts over the fish stalls where '
              'old fishermen and their wives mend eel nets and weave traps from willow.', ['nets', 'craft',
              'river'], 'free', 'indoor', ['solo', 'friends'], DAY),
        place('fishergate-water-stairs', 'the water stairs', 'docks', 'fishergate', 'Stone steps down to the Cam '
              'where watermen wait in their boats to row folk across or down to Bridgefoot for a halfpenny.',
              ['river', 'boats', 'watermen'], '$', 'outdoor', ALL, DAY),
        place('fishergate-smokehouse', 'the smokehouse', 'market', 'fishergate', 'A blackened shed where herring and '
              'eels are hung over oak smoke and sold by the dozen from the door.', ['fish', 'smoked', 'market'],
              '$', 'mixed', ['solo', 'family'], ['morning', 'afternoon'], cuisine='smoked fish'),
        place('bridgefoot-ropewalk', 'the ropewalk', 'workshop', 'bridgefoot', 'A long open shed along the river '
              'where ropers walk backwards twisting hemp into tow ropes for the barges.', ['rope', 'craft',
              'river'], 'free', 'mixed', ['solo', 'friends', 'family'], DAY),
        place('weavers-hall', 'the weavers\' hall', 'guildhall', 'southgate', 'A plain timber hall where the '
              'weavers\' guild searches cloth for faults, settles quarrels and holds its feast on St Blaise\'s day.',
              ['guild', 'cloth', 'feasts'], 'free', 'indoor', ['solo', 'coworkers'], DAY),
        place('the-bull', 'the Bull', 'tavern', 'barkers-end', 'A tanners\' alehouse by the river with a strong '
              'fire, strong ale and no complaints about the smell.', ['ale', 'tanners', 'cheap'], '$', 'indoor',
              ADULT, NIGHT),
        place('curriers-row', 'Curriers\' Row', 'workshop', 'barkers-end', 'Open sheds where tanned hides are '
              'shaved, oiled and dressed into leather for saddles, shoes and buckets.', ['leather', 'craft'],
              '$', 'mixed', ['solo', 'friends'], DAY),
        place('washing-stones', 'the washing stones', 'square', 'barkers-end', 'Flat stones on the riverbank above '
              'the tan pits where women beat linen with paddles and spread it on the grass to dry.',
              ['laundry', 'river', 'neighbours'], 'free', 'outdoor', ['solo', 'friends', 'family'], DAY, WARM),
        place('st-clements-chapel', 'St Clement\'s chapel', 'temple', 'barkers-end', 'A small chapel of ease '
              'outside the walls, so the tanners need not carry their smell up to the town churches.',
              ['chapel', 'parish', 'small'], 'free', 'indoor', ['solo', 'family'], ['morning']),
        place('the-wheatsheaf', 'the Wheatsheaf', 'tavern', 'mill-end', 'The millers\' and carters\' alehouse by '
              'the ford, with a bench outside for waiting on the ferry.', ['ale', 'carters', 'river'], '$',
              'mixed', ['solo', 'friends', 'family'], ['afternoon', 'evening'], cuisine='English'),
        place('mill-ferry-landing', 'the ferry landing', 'docks', 'mill-end', 'The rope ferry\'s wooden landing '
              'above the weir, where folk wait with baskets and the ferryman takes a farthing.',
              ['ferry', 'river', 'waiting'], '$', 'outdoor', ALL, DAY),
        place('mill-pond', 'the mill pond', 'park', 'mill-end', 'The still water behind the weir, with willows, '
              'moorhens and boys fishing for roach when the miller is not looking.', ['fishing', 'willows',
              'quiet'], 'free', 'outdoor', ALL, DAY, WARM),
        place('the-cross-keys', 'the Cross Keys', 'tavern', 'st-giles', 'An alehouse outside the east gate where '
              'travellers arriving after the gate shuts can eat, drink and sleep on the settles.',
              ['ale', 'travellers', 'late'], '$', 'indoor', ADULT, NIGHT, cuisine='English'),
        place('st-giles-well', 'St Giles\'s well', 'square', 'st-giles', 'A walled spring by the hospital said to '
              'ease sore eyes, where neighbours draw water and the sick sit in the sun.', ['well', 'healing',
              'neighbours'], 'free', 'outdoor', ALL, DAY),
        place('east-gate-cookshop', 'the east gate cookshop', 'restaurant', 'st-giles', 'A cookshop in a cottage '
              'front selling pottage, bacon and oatcakes to carters and visitors to the infirmary.',
              ['pottage', 'cheap', 'travellers'], '$', 'indoor', ALL, ['morning', 'afternoon'], cuisine='English'),
        place('abbey-brewhouse', 'the abbey brewhouse', 'tavern', 'abbey-precinct', 'The brewhouse by the abbey '
              'gate where the lay brothers sell good ale by the jug to the abbey\'s tenants.', ['ale', 'abbey',
              'brewing'], '$', 'mixed', ['solo', 'friends', 'family'], ['afternoon', 'evening']),
        place('abbey-fishponds', 'the abbey fishponds', 'park', 'abbey-precinct', 'Three stepped ponds of carp '
              'and bream, with a path round them where the novices walk and townsfolk come to feed the swans.',
              ['ponds', 'walk', 'swans'], 'free', 'outdoor', ALL, DAY, WARM),
        place('the-horseshoe', 'the Horseshoe', 'tavern', 'tiltyard-meads', 'An alehouse on the edge of the meads '
              'full of horse dealers, grooms and squires, busiest on fair and tourney days.',
              ['ale', 'horses', 'squires'], '$', 'mixed', ADULT, ['afternoon', 'evening']),
        place('saddlers-sheds', 'the saddlers\' sheds', 'workshop', 'tiltyard-meads', 'A row of sheds by the '
              'horse lines where saddles, girths and harness are stitched and mended while you wait.',
              ['leather', 'horses', 'craft'], '$', 'mixed', ['solo', 'friends'], DAY),
        place('st-andrews-woolston', 'St Andrew\'s, Woolston', 'temple', 'woolston', 'The village church of '
              'flint and thatch, with a church ale in the nave at Whitsun.', ['church', 'village', 'church-ale'],
              'free', 'indoor', ALL, ['morning']),
        place('woolston-common-oven', 'the common oven', 'cafe', 'woolston', 'The village oven by the green where '
              'wives bake their loaves on Saturdays and swap news while the bread rises.', ['bread', 'village',
              'neighbours'], '$', 'indoor', ALL, ['morning'], cuisine='bread'),
        place('woolston-smithy', 'the Woolston smithy', 'workshop', 'woolston', 'The village forge where '
              'ploughshares are sharpened and oxen are shod, with men waiting on the bench outside.',
              ['forge', 'village', 'ploughs'], '$', 'mixed', ['solo', 'friends'], DAY),
        place('the-holly-bush', 'the Holly Bush', 'tavern', 'forest-side', 'A cottage alehouse with a holly bush '
              'over the door, where charcoal burners and swineherds drink by a peat fire.',
              ['ale', 'forest', 'fire'], '$', 'indoor', ['solo', 'friends'], NIGHT),
        place('charcoal-hearths', 'the charcoal hearths', 'workshop', 'forest-side', 'Turf-covered stacks '
              'smouldering in a clearing for days, watched by colliers who sleep in a hut beside them.',
              ['charcoal', 'forest', 'craft'], 'free', 'outdoor', ['solo', 'friends'], DAY),
        place('forest-hermitage', 'the hermitage', 'temple', 'forest-side', 'A hermit\'s cell and chapel at the '
              'forest edge, of the kind Malory\'s knights are always finding, where any traveller may ask for '
              'bread and a blessing.', ['hermit', 'chapel', 'malory'], 'free', 'indoor', ['solo'], DAY),
        place('verderers-lodge', 'the verderer\'s lodge', 'landmark', 'forest-side', 'The timber lodge where the '
              'verderer holds his court for forest offences and grants leave to gather fallen wood and pannage.',
              ['forest', 'court', 'firewood'], 'free', 'mixed', ['solo', 'family'], DAY),
    ],
    'colleges': [
        {'id': 'abbey-school', 'name': 'St Mary\'s Abbey school', 'type': 'seminary', 'neighborhood':
         'abbey-precinct', 'size': 'small', 'known_for': ['latin', 'grammar', 'copying', 'chant'], 'source': S},
        {'id': 'minster-song-school', 'name': 'the Minster song school', 'type': 'music-school', 'neighborhood':
         'minster-close', 'size': 'small', 'known_for': ['plainsong', 'choristers', 'reading'], 'source': S},
        {'id': 'castle-pages-school', 'name': 'the castle household school', 'type': 'academy', 'neighborhood':
         'castle-ward', 'size': 'small', 'known_for': ['horsemanship', 'arms', 'courtesy', 'carving-at-table'],
         'source': S},
        {'id': 'armourers-guild-school', 'name': 'the Armourers\' and Smiths\' guild apprentices', 'type':
         'guild-school', 'neighborhood': 'smithgate', 'size': 'small', 'known_for': ['mail', 'plate', 'smithing',
         'apprenticeship'], 'source': S},
        {'id': 'st-giles-infirmary-school', 'name': 'the St Giles infirmary', 'type': 'medical-school',
         'neighborhood': 'st-giles', 'size': 'small', 'known_for': ['herbs', 'nursing', 'bonesetting'],
         'source': S},
    ],
    'careers': [
        career('castle-servant', 'Castle servant', 'household', 'early', '$', 'Kitchen, buttery, laundry or '
               'chamber work in the King\'s household, paid in wages, food and a livery gown at Christmas.',
               ['the great kitchen', 'feast days', 'the steward', 'servants\' gossip']),
        career('groom', 'Groom of the stables', 'household', 'early', '$', 'Feeding, mucking out, grooming and '
               'exercising horses in the royal stables.', ['horses', 'the stable yard', 'tournament days',
               'early mornings']),
        career('falconer', 'Falconer', 'household', 'early', '$$', 'Training and flying the King\'s hawks and '
               'falcons from the mews, and riding out with hunting parties.', ['hawks', 'the mews', 'hunting',
               'patience']),
        career('squire', 'Squire', 'household', 'rotating', '$', 'Serving a knight: arming him, carving at his '
               'table, keeping his horses and gear, and training for knighthood.', ['arms practice', 'serving a '
               'knight', 'tournaments', 'the vigil to come']),
        career('man-at-arms', 'Man-at-arms', 'household', 'rotating', '$$', 'Garrison soldier on watch at the '
               'gates and walls, escorting travellers and keeping order at fairs.', ['night watch', 'the '
               'gatehouse', 'drill', 'barrack life']),
        career('court-clerk', 'Clerk of the court', 'government', 'office', '$$', 'Writing letters, writs and '
               'accounts for the King\'s chancery and exchequer at the castle.', ['parchment', 'seals',
               'accounts', 'the chancellor']),
        career('scribe', 'Scribe', 'church', 'office', '$', 'Copying and illuminating books in the abbey '
               'scriptorium, or writing letters and wills for townsfolk.', ['the scriptorium', 'ink and quills',
               'candlelight', 'commissions']),
        career('armourer', 'Armourer', 'crafts', 'shift-day', '$$', 'Making and mending mail and plate in a '
               'Smithgate forge, with a rush of work before every tournament.', ['the forge', 'fitting knights',
               'apprentices', 'tournament rush']),
        career('blacksmith', 'Blacksmith', 'crafts', 'shift-day', '$', 'Shoeing horses and making nails, '
               'hinges, tools and ploughshares at a town forge.', ['the anvil', 'shoeing', 'farm tools',
               'regular customers']),
        career('alewife', 'Alewife', 'victualling', 'evening', '$', 'Brewing ale in her own house, selling it '
               'under an ale-stake and keeping the alehouse in the evenings.', ['brewing', 'regulars', 'the '
               'ale-taster', 'evening talk']),
        career('baker', 'Baker', 'victualling', 'early', '$', 'Up before dawn to fire the oven and bake loaves '
               'to the assize weight for the morning trade.', ['the oven', 'dawn', 'the assize of bread',
               'neighbours']),
        career('innkeeper', 'Innkeeper\'s hand', 'victualling', 'evening', '$', 'Serving, cooking, making beds '
               'and stabling horses at one of the town\'s inns.', ['travellers', 'the inn yard', 'suppers',
               'news from the road']),
        career('weaver', 'Weaver', 'cloth', 'shift-day', '$', 'Working a broadloom in a Southgate house for a '
               'clothier who supplies the yarn and buys the cloth.', ['the loom', 'piecework', 'the guild',
               'family workshop']),
        career('dyer', 'Dyer', 'cloth', 'shift-day', '$', 'Steeping cloth in woad, madder and weld vats, with '
               'blue hands to show for it.', ['dye vats', 'colours', 'the tenter yard', 'stained hands']),
        career('tanner', 'Tanner', 'crafts', 'shift-day', '$', 'Scraping hides and working the tan pits at '
               'Barkers End outside the walls.', ['the tan pits', 'leather', 'the smell', 'river work']),
        career('mason', 'Mason', 'building', 'shift-day', '$$', 'Cutting and laying stone at the minster works '
               'or the castle, under a master mason in the lodge.', ['the lodge', 'stone', 'scaffolding',
               'the master mason']),
        career('minstrel', 'Minstrel', 'entertainment', 'evening', '$', 'Playing harp, fiddle or pipe and '
               'telling tales in the castle hall, the Guildhall undercroft and the inns.', ['songs and tales',
               'feast nights', 'patrons', 'travelling']),
        career('infirmarer', 'Healer at the infirmary', 'healing', 'rotating', '$', 'Nursing the sick, setting '
               'bones and making salves at the Hospital of St Giles.', ['the infirmary hall', 'herbs', 'the '
               'sick', 'the brothers and sisters']),
        career('merchant', 'Merchant', 'trade', 'flexible', '$$$', 'Buying wool, wine and cloth by the barge '
               'load and selling from a shop on Cheapside.', ['the Guildhall', 'barges from Astolat', 'credit',
               'market days']),
        career('boatman', 'Bargeman', 'river', 'early', '$', 'Poling and towing barges on the Cam between '
               'Bridgefoot and Astolat with wool, timber and wine.', ['the river', 'the towpath', 'loading',
               'Astolat']),
        career('miller', 'Miller', 'river', 'early', '$$', 'Running the King\'s mill on the Cam, grinding grain '
               'and taking the toll.', ['the millstones', 'the weir', 'flour dust', 'tolls']),
        career('farmer', 'Farmer', 'farming', 'early', '$', 'Working strips in Woolston\'s open fields, keeping '
               'pigs and geese, and owing days of labour on the King\'s demesne.', ['ploughing', 'harvest',
               'the reeve', 'weather']),
        career('chaplain', 'Chantry priest', 'church', 'academic', '$', 'Singing daily masses at the minster '
               'and teaching a few boys their letters between services.', ['the minster', 'mass', 'teaching',
               'the canons']),
    ],
    'employers': [
        employer('kings-household', 'the King\'s household', 'household', 'castle-ward', 'large', 'The steward\'s '
                 'department that runs the castle: kitchens, hall, chambers, laundry and the garrison.',
                 ['castle-servant', 'squire', 'man-at-arms', 'minstrel']),
        employer('royal-stables', 'the royal stables', 'household', 'castle-ward', 'medium', 'Long stone '
                 'stables under the castle wall, run by the marshal, with the King\'s and knights\' horses.',
                 ['groom', 'squire', 'blacksmith']),
        employer('royal-mews', 'the King\'s mews', 'household', 'tiltyard-meads', 'small', 'The hawk house by '
                 'the meadows where the falcons are kept, moulted and trained.', ['falconer', 'groom']),
        employer('chancery', 'the chancery and exchequer', 'government', 'castle-ward', 'medium', 'The writing '
                 'office and counting house of the court, in the tower by the hall.', ['court-clerk', 'scribe']),
        employer('st-stephens-chapter', 'the chapter of St Stephen\'s', 'church', 'minster-close', 'medium',
                 'The dean and canons of the minster, who employ priests, clerks and the building works.',
                 ['chaplain', 'scribe', 'court-clerk']),
        employer('minster-works', 'the minster works lodge', 'building', 'minster-close', 'medium', 'The masons\' '
                 'lodge and yard rebuilding the minster\'s west front, paid by the chapter.', ['mason']),
        employer('st-marys-abbey', 'St Mary\'s Abbey', 'church', 'abbey-precinct', 'medium', 'The abbey employs '
                 'lay scribes, farm servants, bakers and brewers on its lands.', ['scribe', 'farmer', 'baker',
                 'chaplain']),
        employer('st-giles-hospital-employer', 'the Hospital of St Giles', 'healing', 'st-giles', 'small', 'The '
                 'religious house that runs the infirmary and almshouses outside the east gate.', ['infirmarer']),
        employer('ferrour-forge', 'Hugh Ferrour\'s forge', 'crafts', 'smithgate', 'small', 'The busiest armourer\'s '
                 'shop on Smithgate, with three journeymen and the court\'s custom.', ['armourer', 'blacksmith']),
        employer('weavers-guild', 'the Weavers\' and Dyers\' guild', 'cloth', 'southgate', 'medium', 'The craft '
                 'guild of Southgate\'s cloth workers, who weave and dye for clothiers on Cheapside.', ['weaver',
                 'dyer']),
        employer('the-bell-inn', 'the Bell', 'victualling', 'cheapside', 'medium', 'The largest inn on '
                 'Cheapside, with a brewhouse, kitchens and stabling.', ['innkeeper', 'alewife', 'groom',
                 'minstrel']),
        employer('bread-street-bakers', 'the bakers of Bread Street', 'victualling', 'southgate', 'small', 'Three '
                 'family bakehouses under the bakers\' company.', ['baker']),
        employer('mercers-company', 'the Mercers\' company', 'trade', 'cheapside', 'medium', 'The merchants\' '
                 'guild that keeps the Guildhall and trades wool, wine and cloth by river.', ['merchant',
                 'court-clerk']),
        employer('cam-watermen', 'the Cam watermen', 'river', 'bridgefoot', 'small', 'The fraternity of '
                 'bargemen that works the river between Bridgefoot and Astolat.', ['boatman']),
        employer('kings-mill-employer', 'the King\'s mill', 'river', 'mill-end', 'small', 'The water mill on the '
                 'Cam, leased by the crown to a master miller.', ['miller', 'boatman']),
        employer('barkers-end-tannery', 'Barkers End tanyards', 'crafts', 'barkers-end', 'small', 'A row of '
                 'family tanyards on the river below the town walls.', ['tanner']),
        employer('woolston-manor', 'Woolston manor', 'farming', 'woolston', 'medium', 'The King\'s demesne farm '
                 'and its tenants\' open fields, run by a reeve.', ['farmer']),
        employer('the-star-alehouse', 'the Star alehouse', 'victualling', 'bridgefoot', 'small', 'A bargemen\'s '
                 'alehouse on the quay with its own brewster.', ['alewife']),
    ],
    'career_hubs': [
        {'id': 'castle-and-court', 'name': 'The castle and court', 'neighborhoods': ['castle-ward',
         'tiltyard-meads'], 'sectors': ['household', 'government', 'entertainment'], 'summary': 'The King\'s '
         'household, stables, mews and writing offices employ hundreds, from scullions to clerks.', 'source': S},
        {'id': 'church-houses', 'name': 'The minster, abbey and hospital', 'neighborhoods': ['minster-close',
         'abbey-precinct', 'st-giles'], 'sectors': ['church', 'healing', 'building'], 'summary': 'The religious '
         'houses employ priests, scribes, masons, healers and lay servants.', 'source': S},
        {'id': 'guild-streets', 'name': 'The guild streets', 'neighborhoods': ['cheapside', 'smithgate',
         'southgate', 'shambles'], 'sectors': ['crafts', 'cloth', 'trade', 'victualling'], 'summary': 'Shops '
         'and workshops of the craft and merchant guilds inside the walls.', 'source': S},
        {'id': 'river-and-fields', 'name': 'The river and the fields', 'neighborhoods': ['bridgefoot',
         'barkers-end', 'mill-end', 'woolston'], 'sectors': ['river', 'farming', 'crafts'], 'summary': 'Barges, '
         'the mill, the tanyards and the manor farm along the Cam.', 'source': S},
    ],
    'climate': {
        'summary': 'Mild and damp southern English weather: cool, wet winters with the odd frost or snow, green '
                   'springs, warm but rarely hot summers, and rainy autumns.',
        'months': [
            {'high_f': 47, 'low_f': 36, 'rain_days': 13, 'note': 'Cold and wet; frosts some nights, mud on the '
             'roads.'},
            {'high_f': 48, 'low_f': 35, 'rain_days': 10, 'note': 'Raw and grey; snowdrops and lambing.'},
            {'high_f': 52, 'low_f': 38, 'rain_days': 10, 'note': 'Windy; ploughing and sowing begin.'},
            {'high_f': 57, 'low_f': 41, 'rain_days': 9, 'note': 'Showers and blossom in the orchards.'},
            {'high_f': 63, 'low_f': 46, 'rain_days': 9, 'note': 'Green and mild; hawthorn in flower.'},
            {'high_f': 68, 'low_f': 51, 'rain_days': 8, 'note': 'Long light evenings; haymaking.'},
            {'high_f': 72, 'low_f': 55, 'rain_days': 8, 'note': 'Warmest month; swimming at the shallows.'},
            {'high_f': 71, 'low_f': 54, 'rain_days': 9, 'note': 'Warm; harvest in the fields.'},
            {'high_f': 66, 'low_f': 50, 'rain_days': 9, 'note': 'Mild; apples picked and hops dried.'},
            {'high_f': 59, 'low_f': 45, 'rain_days': 12, 'note': 'Rain returns; leaves turn in the forest.'},
            {'high_f': 52, 'low_f': 40, 'rain_days': 13, 'note': 'Wet and dark early; pigs to the forest for '
             'acorns.'},
            {'high_f': 48, 'low_f': 37, 'rain_days': 13, 'note': 'Short days, rain and the Christmas feast.'},
        ],
        'source': S,
    },
    'annual_events': [
        {'id': 'plough-monday', 'name': 'Plough Monday', 'months': [1], 'neighborhood': 'woolston',
         'summary': 'Ploughmen drag a decorated plough through the village and into town, begging pennies for '
         'the plough light.', 'source': S},
        {'id': 'candlemas', 'name': 'Candlemas', 'months': [2], 'neighborhood': 'minster-close',
         'summary': 'Townsfolk carry candles in procession to St Stephen\'s to have them blessed for the year.',
         'source': S},
        {'id': 'easter', 'name': 'Easter', 'months': [3, 4], 'neighborhood': 'minster-close',
         'summary': 'Lent ends with the Easter vigil at the minster, new clothes and eggs at breakfast.',
         'source': S},
        {'id': 'may-day', 'name': 'May Day', 'months': [5], 'neighborhood': 'woolston',
         'summary': 'Young people go out at dawn to bring in hawthorn, then dance round the maypole on Woolston '
         'green.', 'source': S},
        {'id': 'pentecost-court', 'name': 'Pentecost court and tournament', 'months': [5, 6],
         'neighborhood': 'tiltyard-meads', 'summary': 'The King holds his great court at Pentecost: new knights '
         'are made, petitions heard, and a tournament runs for days in the lists.', 'source': S},
        {'id': 'midsummer', 'name': 'Midsummer Eve', 'months': [6], 'neighborhood': 'cheapside',
         'summary': 'Bonfires in the streets, doors hung with birch and St John\'s wort, and a watch procession '
         'with torches.', 'source': S},
        {'id': 'harvest-home', 'name': 'Harvest home', 'months': [8, 9], 'neighborhood': 'woolston',
         'summary': 'The last sheaf is brought in on a decorated cart and the manor gives the reapers a supper.',
         'source': S},
        {'id': 'michaelmas-fair', 'name': 'Michaelmas fair', 'months': [9, 10], 'neighborhood': 'tiltyard-meads',
         'summary': 'A week-long fair of horses, cattle, cloth and hiring, with goose dinners, rents due and '
         'servants seeking new places.', 'source': S},
        {'id': 'martinmas', 'name': 'Martinmas', 'months': [11], 'neighborhood': 'shambles',
         'summary': 'Beasts are slaughtered and salted for winter and the Shambles runs with work for a week.',
         'source': S},
        {'id': 'christmas-court', 'name': 'Christmas court', 'months': [12, 1], 'neighborhood': 'castle-ward',
         'summary': 'Twelve days of feasting in the great hall, mummers and carols in the town, and no work in '
         'the fields.', 'source': S},
    ],
    'local_color': [
        color('no-meat-before-a-marvel', 'No meat before a marvel', 'custom', 'At the high feast of Pentecost King '
              'Arthur will not sit down to eat until he has seen or heard of some marvel or adventure, so the hall '
              'waits on news.', ['round-table-hall'], ['spring']),
        color('pentecost-oath', 'The Pentecost oath', 'custom', 'Every year at Pentecost the knights of the Round '
              'Table renew their oath: to flee treason, give mercy to those who ask it, and always help ladies and '
              'damosels.', ['round-table-hall', 'st-stephens-minster'], ['spring']),
        color('siege-perilous', 'The Siege Perilous', 'other', 'Each seat at the Round Table bears its knight\'s name '
              'in letters of gold, but one, the Siege Perilous, is kept empty, and no one sits there and lives.',
              ['round-table-hall']),
        color('gramercy', '"Gramercy" and "fair sir"', 'saying', 'Courtesy runs on set phrases: "gramercy" for many '
              'thanks, "fair sir" and "fair damosel" to strangers, and "God speed" to anyone setting out.'),
        color('beaumains', '"Beaumains"', 'saying', 'Sir Kay\'s mocking name, "Fair-hands", for the tall kitchen lad '
              'who turned out to be Gareth of Orkney; to call a scullion Beaumains is to warn that he may be more than '
              'he seems.', ['castle-buttery']),
        color('jousting-sides', 'Taking sides at the jousts', 'custom', 'At every tournament the town cheers for a '
              'party: Lancelot\'s kin or Gawain\'s Orkney brothers, and arguments carry on in the taverns afterward.',
              ['tiltyard', 'the-green-dragon']),
        color('a-maying', 'Going a-Maying', 'custom', 'On May morning the court and the townsfolk ride or walk into '
              'the woods and fields to bring home green boughs and flowers, as the Queen does with her knights.',
              ['forest-ride', 'woolston-green'], ['spring']),
        color('pottage', 'Pottage', 'dish', 'The everyday meal: a thick pot of peas, beans, leeks and grain, with '
              'bacon when there is any, kept going on the hearth from day to day.',
              ['shambles-cookshop', 'east-gate-cookshop']),
        color('trenchers', 'Trenchers', 'custom', 'At table meat is served on thick slices of stale bread called '
              'trenchers, which soak up the gravy and are given to the poor or the dogs after the meal.',
              ['bread-street-bakery', 'castle-buttery']),
        color('hot-pies-cry', '"Hot pies, hot!"', 'shop', 'Cooks and pie-wives cry their wares in the street, and '
              'cookshops sell hot pies, roast meat and puddings ready to carry home.',
              ['shambles-cookshop', 'pudding-wifes-stall', 'cutlers-cookstall']),
        color('ale-stake', 'The ale-stake', 'custom', 'A bush or bundle of greenery on a pole over the door means a '
              'house has new ale to sell, and the town ale-taster must try it before it is sold.',
              ['mother-joans-alehouse', 'the-chequers']),
        color('spiced-wine', 'Spiced wine', 'drink', 'At feasts the butler serves wine sweetened with honey and spiced '
              'with ginger and cinnamon, while ordinary folk drink ale.', ['castle-buttery', 'round-table-hall']),
        color('frumenty', 'Frumenty', 'dish', 'Hulled wheat boiled in milk with egg yolks and saffron, eaten with '
              'venison at feasts or plain at harvest.', seasons=['fall', 'winter']),
        color('lammas-loaf', 'Lammas loaf', 'custom', 'On the first of August a loaf baked from the first ripe wheat '
              'is carried to the church and blessed.', ['st-stephens-minster', 'woolston-common-oven'], ['summer']),
        color('fish-days', 'Fish days', 'custom', 'No meat is eaten on Fridays, through Lent, or on other fast days, '
              'so the town lives on herring, eels and river fish.',
              ['fishergate-fish-market', 'fishergate-smokehouse']),
        color('curfew-bell', 'The curfew bell', 'custom', 'At dusk the minster bell rings curfew: hearth fires are '
              'covered, gates are shut, and anyone abroad without a light may be questioned by the watch.',
              ['st-stephens-minster']),
        color('hue-and-cry', 'Hue and cry', 'custom', 'Anyone who sees a crime must raise the hue and cry, and every '
              'household within earshot is bound to turn out and chase the wrongdoer.'),
        color('wassail', 'Wassail', 'drink', 'At Christmas and Twelfth Night a bowl of hot spiced ale with roasted '
              'apples is passed around with the greeting "wassail" ("be well") and the answer "drinkhail".',
              seasons=['winter']),
    ],
    'prices': [
        price('ale', 'Ale', 1, 1.5, 'a gallon'),
        price('loaf', 'Loaf of bread', 0.25, 0.5, 'a farthing or halfpenny loaf'),
        price('pie', 'Pie from a cookshop', 0.5, 1),
        price('inn-meal', 'Meal at an inn', 1, 3),
        price('wine', 'Wine', 4, 8, 'a gallon'),
        price('inn-bed', 'Bed at an inn', 0.5, 1, 'a night, often shared'),
        price('board', 'Board and lodging', 6, 10, "a week's board"),
        price('stabling', 'Stabling a horse', 1, 2, 'a night'),
        price('horse-hire', 'Hired horse', 6, 12, 'a day'),
        price('toll', 'Bridge toll', 0.25, 1, 'on foot to a laden cart'),
        price('bath', 'Bathhouse', 0.5, 1, 'a bath'),
        price('candles', 'Tallow candles', 1, 1.5, 'a pound'),
        price('shoes', 'Shoes', 4, 8, 'a pair'),
        price('wage', "Labourer's wage", 2, 4, 'a day'),
    ],
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
