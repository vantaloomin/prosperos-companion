"""Grandport, capital of the Alnhama Republic in Oak's Neokosmos. Run `python scripts/world/grandport.py` to rewrite it.

Neokosmos (https://quietoak.github.io/NeokosmosWiki/) is by Oak and licensed CC BY-NC-SA 4.0. Prospero's
Companion includes this city with Oak's permission (2026-10-10); it is Oak's setting, not part of the app's
AGPL code. Every record cites `wiki` when the wiki says it, or `inferred` when it is filled in, in the
setting's voice, from what the wiki says.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'cities' / 'grandport.json'

W, INF = 'wiki', 'inferred'
LAT, LON = 38.72, -27.22


def hood(id, name, summary, vibe, dy, dx, tier, rent, housing, walk, transit, src):
    return {'id': id, 'name': name, 'summary': summary, 'vibe': vibe, 'lat': round(LAT + dy, 4),
            'lon': round(LON + dx, 4), 'rent_tier': tier, 'rent': {'studio': rent[0], 'one_bedroom': rent[1],
            'two_bedroom': rent[2]}, 'housing': housing, 'walkability': walk, 'transit': transit, 'source': src}


def place(id, name, kind, hood, summary, tags, cost, setting, good_for, parts, src, seasons=(), cuisine=''):
    return {'id': id, 'name': name, 'kind': kind, 'neighborhood': hood, 'summary': summary, 'tags': tags,
            'cost': cost, 'setting': setting, 'good_for': good_for, 'day_parts': parts, 'seasons': list(seasons),
            'cuisine': cuisine, 'source': src}


ALL = ['morning', 'afternoon', 'evening']
EVE = ['evening', 'late']
DAY = ['morning', 'afternoon']

neighborhoods = [
    hood('raft-palaces', 'The Raft Palaces',
         'Merchant princes\' palaces of carved ashlar floating on six-foot stone rafts laid in the drained marsh, '
         'with Lord Edgar Grandeholm\'s great tower above them all. Household guards and quiet gardens.',
         ['wealthy', 'merchant-princes', 'guarded', 'stone'], 0.012, -0.004, 'very-high',
         ([8, 14], [16, 30], [40, 90]), ['palace', 'townhouse', 'servants-quarters'], 'medium',
         ['streets-and-stairs', 'hired-carriages'], W),
    hood('ledger-quarter', 'The Ledger Quarter',
         'Old timber houses underpinned with stone counting houses on the ground floor: insurers, brokers, '
         'notaries and the chambers where the Merchant Circle and the commons\' house sit.',
         ['commerce', 'government', 'busy', 'clerks'], 0.006, -0.002, 'high',
         ([5, 8], [9, 15], [18, 30]), ['rooms-above-counting-house', 'townhouse'], 'high',
         ['streets-and-stairs', 'hired-carriages'], W),
    hood('guild-gables', 'Guild Gables',
         'The steepest, most competitive front-facing gables in the city: timber-framed guild halls, workshops '
         'and families whose houses are inspected every year by guild surveyors.',
         ['crafts', 'timber', 'guilds', 'proud'], 0.003, 0.004, 'mid',
         ([3, 5], [5, 9], [9, 15]), ['timber-house', 'rooms-above-workshop'], 'high', ['streets-and-stairs'], W),
    hood('the-quays', 'The Quays',
         'Grandport\'s working harbour: the dock office, bonded warehouses, cranes and the hiring line, where '
         'Ruestrian grain, Fresnian relics and Pictish furs are measured, taxed and insured.',
         ['harbour', 'noisy', 'trade', 'early'], -0.002, -0.006, 'low',
         ([2, 3], [3, 5], [5, 8]), ['lodging-house', 'rooms-above-tavern'], 'high', ['streets-and-stairs', 'wherries'], W),
    hood('shipwright-yards', 'Shipwright Yards',
         'Slipways where war carracks and merchant hulls rise in oak, with the long ropewalks and sail lofts '
         'behind them. Sawdust, tar and the shouts of the yard bells.',
         ['shipbuilding', 'industrial', 'tar', 'working'], -0.006, -0.012, 'low',
         ([2, 3], [3, 4], [4, 7]), ['row-house', 'lodging-house'], 'medium', ['streets-and-stairs', 'wherries'], INF),
    hood('lower-stairs', 'The Lower Stairs',
         'Steep alleys and stairs below the warehouses, home to rope girls, pressed sailors, guild militia '
         'widows and debtors. Hunger outlasted the siege here, and the Republic\'s critics say so.',
         ['poor', 'crowded', 'resilient', 'whispers'], -0.008, -0.002, 'low',
         ([1, 2], [2, 3], [3, 5]), ['shared-room', 'cellar-room', 'row-house'], 'high', ['streets-and-stairs'], W),
    hood('ashrow', 'Ashrow',
         'A district rebuilt in fresh oak after the last great fire, on merchant loans that are still being '
         'paid. The fire-watch tower and its bell stand at the top of the street.',
         ['rebuilt', 'new-timber', 'families', 'mortgaged'], 0.001, 0.010, 'mid',
         ([3, 4], [4, 7], [7, 12]), ['timber-house', 'rooms'], 'high', ['streets-and-stairs'], W),
    hood('admiralty-point', 'Admiralty Point',
         'The navy\'s fortress at the harbour mouth, Admiral Horatio Horne\'s headquarters, and the signal tower '
         'whose flags and shuttered lanterns talk to the whole island chain.',
         ['navy', 'military', 'windy', 'signals'], -0.004, -0.018, 'mid',
         ([3, 4], [4, 6], [6, 10]), ['barracks', 'officers-houses', 'rooms'], 'medium',
         ['streets-and-stairs', 'wherries'], W),
    hood('gran-porte', 'Old Gran Porte',
         'The first harbour King Aelfred secured, with the oldest quays and the shuttered royal palace. The '
         'street where King Alrdric fell is here, and old loyalties are spoken of quietly.',
         ['historic', 'old-quays', 'royalist-whispers', 'quiet'], 0.002, -0.010, 'mid',
         ([3, 5], [5, 8], [8, 13]), ['old-townhouse', 'rooms'], 'high', ['streets-and-stairs', 'wherries'], W),
    hood('chart-house-hill', 'Chart House Hill',
         'Where the Republic keeps its useful people: navigators, astronomers, engineers, printers and the '
         'public school, under the patronage of men like Magister Aldous Thorne.',
         ['learned', 'presses', 'young', 'ambitious'], 0.009, 0.006, 'mid',
         ([3, 5], [5, 8], [9, 14]), ['rooms', 'boarding-house', 'townhouse'], 'high', ['streets-and-stairs'], INF),
    hood('strangers-wharf', 'Strangers\' Wharf',
         'The wharf for foreign ships and foreign people: Ruestrian grain factors, Fresnian relic dealers, '
         'Pictish fur traders, and a small chapel of Sol Eternel kept by travelling missionaries.',
         ['foreign', 'mixed', 'markets', 'lively'], -0.005, 0.004, 'low',
         ([2, 3], [3, 5], [5, 8]), ['lodging-house', 'inn-room', 'rooms'], 'high', ['streets-and-stairs', 'wherries'], INF),
    hood('marsh-fields', 'The Marsh Fields',
         'Drained estuary land at the city\'s edge, behind dykes: barley and oat fields, cattle pasture, '
         'dairies and the market road into town.',
         ['farmland', 'cattle', 'open', 'quiet'], 0.018, 0.020, 'low',
         ([1, 2], [2, 3], [3, 6]), ['farmhouse', 'cottage'], 'low', ['market-road', 'streets-and-stairs'], INF),
]

places = [
    # Raft Palaces
    place('grandeholm-tower', 'Grandeholm Tower', 'landmark', 'raft-palaces',
          'The great tower Edgar Grandeholm built and rarely leaves, ruling from its upper chambers while agents '
          'and informants climb the stairs with ledgers. Visitors get as far as the gate.',
          ['edgar', 'power', 'architecture'], 'free', 'outdoor', ['solo', 'friends'], DAY, W),
    place('raft-gardens', 'The Raft Gardens', 'garden', 'raft-palaces',
          'Walled pleasure gardens laid on the stone rafts, opened to the public on Republic Day and to '
          'anyone with a merchant\'s token the rest of the year.',
          ['gardens', 'quiet', 'flowers'], '$', 'outdoor', ['date', 'solo', 'family'], DAY, INF, ['spring', 'summer']),
    place('gilded-ledger', 'The Gilded Ledger', 'restaurant', 'raft-palaces',
          'A dining house for merchant princes and their factors: beef from the Marsh Fields, Ruestrian wine and '
          'private rooms where contracts are signed over dessert.',
          ['fine-dining', 'deals', 'wine'], '$$$$', 'indoor', ['date', 'coworkers'], ['evening'], INF, (), 'Alnhaman'),
    place('thalassar-at-the-rafts', 'Temple of Thalassar on the Rafts', 'temple', 'raft-palaces',
          'A rich shrine to the sea Titan, paid for by ship-owning houses who come to ask for calm water before '
          'their convoys sail.',
          ['faith', 'sea', 'merchants'], 'free', 'indoor', ['solo', 'family'], DAY, INF),
    place('silkmarket-arcade', 'The Silk Arcade', 'shopping', 'raft-palaces',
          'A covered arcade of tailors, perfumers, ring makers and gold-thread embroiderers who dress the '
          'Merchant Circle in silks and scented oils.',
          ['luxury', 'tailors', 'jewellery'], '$$$', 'indoor', ['date', 'friends', 'solo'], DAY, INF),
    place('raft-cafe', 'The Weighing Room', 'cafe', 'raft-palaces',
          'A quiet coffee and chocolate room where factors wait for an audience, pretending not to read each '
          'other\'s papers.',
          ['coffee', 'gossip', 'factors'], '$$', 'indoor', ['solo', 'coworkers'], DAY, INF),

    # Ledger Quarter
    place('merchant-circle-hall', 'The Hall of the Two Houses', 'landmark', 'ledger-quarter',
          'Seat of the Republic: the Merchant Circle sits above, the commons\' house below. Public galleries '
          'fill when tariffs or the royalist question come up.',
          ['government', 'politics', 'republic'], 'free', 'indoor', ['solo', 'friends'], DAY, W),
    place('temple-of-nomion', 'Temple of Nomion', 'temple', 'ledger-quarter',
          'The great temple of the Titan of law and contract, where disputes are arbitrated, oaths sworn and '
          'the largest contracts witnessed on the altar steps.',
          ['faith', 'law', 'contracts'], 'free', 'indoor', ['solo', 'family'], DAY, W),
    place('insurers-exchange', 'The Insurers\' Exchange', 'guildhall', 'ledger-quarter',
          'A loud stone hall where cargoes, hulls and convoy escorts are priced and insured, with the latest '
          'signal-tower news chalked on boards by the door.',
          ['finance', 'news', 'busy'], 'free', 'indoor', ['coworkers', 'solo'], DAY, W),
    place('inkwell-tavern', 'The Inkwell', 'tavern', 'ledger-quarter',
          'Clerks\' tavern under the counting houses, with ale, pies and arguments about interest rates until '
          'the watch calls the hour.',
          ['clerks', 'ale', 'after-work'], '$', 'indoor', ['coworkers', 'friends'], EVE, INF, (), 'Alnhaman'),
    place('scales-coffee', 'The Honest Scales', 'cafe', 'ledger-quarter',
          'A narrow coffee house where brokers trade rumours at standing desks and a coin is touched to the '
          'little brass scale at the door for Chryseon\'s luck.',
          ['coffee', 'brokers', 'luck'], '$', 'indoor', ['solo', 'coworkers'], ['morning'], INF),
    place('notaries-row', 'Notaries\' Row', 'shopping', 'ledger-quarter',
          'A lane of scriveners, seal cutters, paper sellers and ledger binders, the cheapest place in the city '
          'to get a letter written.',
          ['paper', 'seals', 'scribes'], '$', 'mixed', ['solo'], DAY, INF),

    # Guild Gables
    place('masons-hall', 'Hall of the Pile-Drivers and Masons', 'guildhall', 'guild-gables',
          'The guild that drives oak piles to bedrock and inspects every joint in the city. Its surveyors\' '
          'settling records go back generations.',
          ['guild', 'building', 'records'], 'free', 'indoor', ['coworkers', 'solo'], DAY, W),
    place('carpenters-hall', 'Carpenters\' Gable Hall', 'guildhall', 'guild-gables',
          'The tallest gable on the street, built by the timber-framers to prove they could. Apprentices '
          'gather in its yard at dawn.',
          ['guild', 'timber', 'apprentices'], 'free', 'mixed', ['coworkers'], ['morning'], INF),
    place('gable-market', 'Gable Street Market', 'market', 'guild-gables',
          'Stalls under the overhangs selling bread, cheese, tools, cloth and second-hand guild coats.',
          ['market', 'bread', 'cheese'], '$', 'outdoor', ['solo', 'family', 'friends'], DAY, INF),
    place('crooked-joint', 'The Crooked Joint', 'tavern', 'guild-gables',
          'A craftsmen\'s alehouse named as a joke: the only building in the quarter the guild surveyors '
          'have ever failed. A hurdy-gurdy player most nights.',
          ['ale', 'music', 'craftsmen'], '$', 'indoor', ['friends', 'coworkers', 'date'], EVE, INF, (), 'Alnhaman'),
    place('oak-and-adze', 'Oak and Adze Workshop', 'workshop', 'guild-gables',
          'A joinery that takes small commissions: chests, cradles, ship models. Watchers are tolerated if '
          'they hold a plank now and then.',
          ['crafts', 'woodwork'], '$', 'indoor', ['solo', 'family'], DAY, INF),
    place('gable-bakery', 'Widow Aldwen\'s Bakehouse', 'cafe', 'guild-gables',
          'Oat bread, barley rolls and honey cakes from a brick oven the guild insisted on before it would let '
          'her keep a fire.',
          ['bakery', 'breakfast'], '$', 'indoor', ['solo', 'family'], ['morning'], INF),

    # Quays
    place('dock-office', 'The Dock Office', 'landmark', 'the-quays',
          'Where every cargo is measured, taxed and recorded before it may leave the quay. The queue starts '
          'before sunrise.',
          ['harbour', 'tolls', 'records'], 'free', 'indoor', ['coworkers', 'solo'], DAY, W),
    place('grand-quay', 'The Grand Quay', 'docks', 'the-quays',
          'The long stone quay on oak piles where carracks unload, cranes creak and the hiring line forms '
          'each morning.',
          ['ships', 'cranes', 'hiring'], 'free', 'outdoor', ['solo', 'friends'], ALL, W),
    place('bonded-warehouses', 'The Bonded Warehouses', 'landmark', 'the-quays',
          'Rows of guarded warehouses where goods wait for their duties to be paid. Smells of pepper, pitch and '
          'Pictish furs.',
          ['warehouses', 'trade'], 'free', 'outdoor', ['solo'], DAY, W),
    place('fish-steps', 'The Fish Steps', 'market', 'the-quays',
          'Morning fish market on the stone steps down to the water: herring, mackerel, eel and whatever the '
          'estuary boats bring.',
          ['fish', 'market', 'early'], '$', 'outdoor', ['solo', 'family'], ['morning'], INF),
    place('drowned-lantern', 'The Drowned Lantern', 'tavern', 'the-quays',
          'Sailors\' tavern by the hiring line. Cheap ale, loud news from every port, and press-gang rumours '
          'that send men out the back door.',
          ['sailors', 'ale', 'news'], '$', 'indoor', ['friends'], EVE, INF, (), 'Alnhaman'),
    place('quay-cookshop', 'Mother Hild\'s Cookshop', 'restaurant', 'the-quays',
          'Bowls of fish stew and barley bread eaten standing at the counter between shifts.',
          ['stew', 'cheap', 'dockers'], '$', 'indoor', ['solo', 'coworkers'], ['morning', 'afternoon'], INF, (), 'Alnhaman'),

    # Shipwright Yards
    place('great-slipways', 'The Great Slipways', 'docks', 'shipwright-yards',
          'Slipways where the navy\'s high-castled carracks and the merchant hulls are framed in oak. Launch '
          'days draw crowds.',
          ['ships', 'shipbuilding', 'spectacle'], 'free', 'outdoor', ['family', 'friends', 'solo'], DAY, W),
    place('long-ropewalk', 'The Long Ropewalk', 'workshop', 'shipwright-yards',
          'A covered walk a quarter-mile long where rope girls spin hemp into cable, singing to keep the pace.',
          ['rope', 'work', 'songs'], 'free', 'indoor', ['solo'], DAY, W),
    place('sail-loft', 'Canvas Loft', 'workshop', 'shipwright-yards',
          'Sailmakers cutting and stitching canvas on a floor so wide it is chalked like a map.',
          ['sails', 'crafts'], 'free', 'indoor', ['solo'], DAY, INF),
    place('tar-pot', 'The Tar Pot', 'tavern', 'shipwright-yards',
          'Shipwrights\' alehouse where the yard bell ends every argument. Fried eel and pickled onions.',
          ['ale', 'shipwrights', 'fried-eel'], '$', 'indoor', ['coworkers', 'friends'], EVE, INF, (), 'Alnhaman'),
    place('yard-chandlery', 'Pell\'s Chandlery', 'shopping', 'shipwright-yards',
          'Everything for a ship: lanterns, pitch, compasses, salt pork and belaying pins (sold, the owner '
          'says, for sailing only).',
          ['chandlery', 'supplies'], '$$', 'indoor', ['solo'], DAY, INF),
    place('launch-green', 'Launch Green', 'park', 'shipwright-yards',
          'A patch of grass above the slipways where yard families picnic and children race toy hulls in the '
          'drainage pond.',
          ['green', 'children', 'picnic'], 'free', 'outdoor', ['family', 'friends'], DAY, INF, ['spring', 'summer']),

    # Lower Stairs
    place('hundred-steps', 'The Hundred Steps', 'landmark', 'lower-stairs',
          'The long stair from the warehouses down into the Lower Stairs, slick after rain, where people sit '
          'to talk because there is nowhere else to sit.',
          ['stairs', 'neighbours', 'views'], 'free', 'outdoor', ['solo', 'friends'], ALL, W),
    place('relief-bread-hall', 'The Relief Hall', 'landmark', 'lower-stairs',
          'Where Republican grain was handed out during the siege. It still gives bread on Relief Day, and '
          'people still argue about who it was for.',
          ['history', 'charity', 'siege'], 'free', 'indoor', ['solo', 'family'], ['morning'], W),
    place('widows-kitchen', 'The Widows\' Kitchen', 'restaurant', 'lower-stairs',
          'A soup kitchen and cheap eating house run by militia widows. Pay what you can; the pottage is the '
          'same either way.',
          ['soup', 'cheap', 'community'], '$', 'indoor', ['solo', 'family'], ['afternoon', 'evening'], INF, (), 'Alnhaman'),
    place('blue-cloth', 'The Blue Cloth', 'tavern', 'lower-stairs',
          'A cellar tavern whose regulars still drink to the old Crown under their breath. Nobody admits what the '
          'faded blue cloth behind the bar once showed.',
          ['royalist-whispers', 'cellar', 'ale'], '$', 'indoor', ['friends'], EVE, INF, (), 'Alnhaman'),
    place('stairs-shrine', 'Shrine of Thalassar at the Stairs', 'temple', 'lower-stairs',
          'A niche shrine with a battered carved wave where sailors\' families leave shells and candle stubs.',
          ['faith', 'sea', 'candles'], 'free', 'outdoor', ['solo', 'family'], ALL, INF),
    place('rag-market', 'The Rag Market', 'market', 'lower-stairs',
          'Second-hand clothes, mended boots, old sailcloth and pawned trinkets sold off blankets on the steps.',
          ['second-hand', 'bargains'], '$', 'outdoor', ['solo', 'friends'], DAY, INF),

    # Ashrow
    place('firewatch-tower', 'Ashrow Fire-Watch Tower', 'landmark', 'ashrow',
          'The merchant-funded fire-watch tower with its great bell. Watchers sweep the rooftops all night for '
          'the first smoke.',
          ['fire-watch', 'bells', 'views'], 'free', 'outdoor', ['solo', 'friends'], ALL, W),
    place('new-oak-square', 'New Oak Square', 'square', 'ashrow',
          'The rebuilt square, its houses still pale fresh oak, with a well, benches and a loan broker\'s booth.',
          ['square', 'well', 'neighbours'], 'free', 'outdoor', ['family', 'friends', 'solo'], ALL, INF),
    place('phoenix-alehouse', 'The Phoenix', 'tavern', 'ashrow',
          'An alehouse whose first owner rebuilt it three times. Cheerful, crowded, and nervous about candles.',
          ['ale', 'neighbours', 'music'], '$', 'indoor', ['friends', 'date'], EVE, INF, (), 'Alnhaman'),
    place('ashrow-pie-shop', 'Ember Lane Pie Shop', 'restaurant', 'ashrow',
          'Beef and barley pies, eel pies and apple pasties sold hot through a window.',
          ['pies', 'takeaway'], '$', 'mixed', ['solo', 'family'], ['afternoon', 'evening'], INF, (), 'Alnhaman'),
    place('ashrow-bathhouse', 'The Rain Barrel Baths', 'fitness', 'ashrow',
          'A small bathhouse fed from the fire-watch cisterns, with a steam room and a wrestling floor.',
          ['baths', 'steam', 'wrestling'], '$', 'indoor', ['solo', 'friends'], ALL, INF),

    # Admiralty Point
    place('admiralty-fortress', 'The Admiralty Fortress', 'landmark', 'admiralty-point',
          'The navy\'s harbour fortress, its walls patched with thicker stone round the gun ports. Admiral Horne '
          'keeps his quarters here.',
          ['navy', 'fortress', 'horne'], 'free', 'outdoor', ['solo', 'friends'], DAY, W),
    place('signal-tower', 'The Signal Tower', 'landmark', 'admiralty-point',
          'A granite base with a tall oak spire. Coloured flags by day and shuttered lanterns by night carry '
          'messages across the island chain in minutes.',
          ['signals', 'flags', 'views'], 'free', 'outdoor', ['solo', 'date', 'family'], ALL, W),
    place('archery-butts', 'Point Archery Butts', 'fitness', 'admiralty-point',
          'Longbow butts below the fortress walls where the militia companies practise and anyone may pay for '
          'a dozen arrows.',
          ['archery', 'sport', 'militia'], '$', 'outdoor', ['friends', 'solo', 'coworkers'], DAY, W),
    place('powder-and-plum', 'The Powder and Plum', 'tavern', 'admiralty-point',
          'Officers\' tavern with a view of the harbour mouth. Plum brandy, roast fowl, and captains comparing '
          'commissions they bought.',
          ['officers', 'brandy', 'views'], '$$', 'indoor', ['coworkers', 'date', 'friends'], EVE, INF, (), 'Alnhaman'),
    place('point-walk', 'The Mole Walk', 'trail', 'admiralty-point',
          'A path along the harbour mole to the outer light, windy, salty and popular with couples.',
          ['walk', 'sea', 'wind'], 'free', 'outdoor', ['date', 'solo', 'friends'], ['afternoon', 'evening'], INF),

    # Old Gran Porte
    place('aelfreds-quay', 'Aelfred\'s Quay', 'docks', 'gran-porte',
          'The oldest quay, where King Aelfred first made the harbour a charge of the Crown. Now used by fishing '
          'boats and wherries.',
          ['history', 'fishing-boats'], 'free', 'outdoor', ['solo', 'family', 'date'], ALL, W),
    place('royal-palace', 'The Shuttered Palace', 'landmark', 'gran-porte',
          'The old palace of House van Alnhalm, its banner lowered and windows boarded since the Revolution. '
          'The Republic has not decided what to do with it.',
          ['history', 'royalty', 'eerie'], 'free', 'outdoor', ['solo', 'friends'], DAY, INF),
    place('kings-fall-street', 'King\'s Fall Street', 'landmark', 'gran-porte',
          'The street where King Alrdric died trying to calm a hungry crowd. Republicans walk past; royalists '
          'leave a bread crust on the step.',
          ['history', 'revolution', 'memorial'], 'free', 'outdoor', ['solo'], DAY, W),
    place('crowned-horse', 'The Old Horse', 'inn', 'gran-porte',
          'An old coaching inn whose sign was repainted after the Revolution; the horse\'s crown still shows '
          'through in the rain.',
          ['inn', 'history', 'ale'], '$$', 'indoor', ['friends', 'date'], ['afternoon', 'evening', 'late'], INF, (), 'Alnhaman'),
    place('gran-porte-market', 'Gran Porte Fish and Herb Market', 'market', 'gran-porte',
          'A small morning market under the old harbour wall: fish, herbs, eggs and island butter.',
          ['market', 'fish', 'herbs'], '$', 'outdoor', ['solo', 'family'], ['morning'], INF),
    place('wherry-stairs-cafe', 'The Wherry Stairs', 'cafe', 'gran-porte',
          'A tea and coffee stall at the wherry landing, with benches facing the old harbour.',
          ['coffee', 'views'], '$', 'outdoor', ['solo', 'date'], ['morning', 'afternoon'], INF),

    # Chart House Hill
    place('chart-house', 'The Chart House', 'museum', 'chart-house-hill',
          'Where Eadric Wyrmscraft\'s charts of Neokosmos are drawn, copied and sold, with the reconstructed '
          'Atlantean sextant shown on feast days.',
          ['maps', 'navigation', 'atlantis'], '$', 'indoor', ['solo', 'friends'], DAY, W),
    place('observatory', 'The Hill Observatory', 'attraction', 'chart-house-hill',
          'A dome of oak and copper where Republic-funded astronomers time the stars for longitude tables. '
          'Open to visitors on clear nights for a coin.',
          ['stars', 'science'], '$', 'mixed', ['date', 'solo', 'friends'], ['evening', 'late'], INF),
    place('public-press', 'The Republic Press', 'workshop', 'chart-house-hill',
          'The printing house that turns out the Ledger of Liberty, shipping lists and a weekly broadsheet the '
          'royalists call the Merchant\'s Gospel.',
          ['printing', 'news', 'politics'], 'free', 'indoor', ['solo', 'coworkers'], DAY, W),
    place('compass-rose', 'The Compass Rose', 'tavern', 'chart-house-hill',
          'Students\' and navigators\' tavern where bets are settled with dividers and every table has a chart '
          'scratched into it.',
          ['students', 'ale', 'debate'], '$', 'indoor', ['friends', 'date'], EVE, INF, (), 'Alnhaman'),
    place('booksellers-steps', 'Booksellers\' Steps', 'shopping', 'chart-house-hill',
          'Stalls of almanacs, tide tables, histories (both kinds), and sea romances.',
          ['books', 'almanacs'], '$', 'outdoor', ['solo', 'date'], DAY, INF),
    place('thorne-library', 'The Thorne Library', 'library', 'chart-house-hill',
          'A subscription library endowed by Magister Aldous Thorne, open free to public school pupils.',
          ['library', 'study', 'quiet'], 'free', 'indoor', ['solo'], ALL, INF),

    # Strangers' Wharf
    place('strangers-quay', 'The Strangers\' Quay', 'docks', 'strangers-wharf',
          'Where foreign ships must berth: Ruestrian grain galleys, Fresnian traders from the gulf and Pictish '
          'fur boats from the north.',
          ['foreign-ships', 'trade'], 'free', 'outdoor', ['solo', 'friends'], ALL, W),
    place('sol-chapel', 'Chapel of Sol Eternel', 'temple', 'strangers-wharf',
          'A plain chapel kept by travelling missionaries like Aelric Stillhand, where Ruestrian sailors hear '
          'rites and curious locals listen at the door.',
          ['faith', 'sol-eternel', 'foreigners'], 'free', 'indoor', ['solo', 'family'], ALL, INF),
    place('fur-and-relic-market', 'The Fur and Relic Market', 'market', 'strangers-wharf',
          'Pictish furs and carved bone beside Fresnian dealers swearing their Atlantean shards are genuine. '
          'Most are not.',
          ['furs', 'relics', 'haggling'], '$$', 'mixed', ['friends', 'solo', 'date'], DAY, INF),
    place('ruestrian-cookhouse', 'Le Pain Solaire', 'restaurant', 'strangers-wharf',
          'A Ruestrian cookhouse serving bread, lentils and wine the way the grain sailors like it.',
          ['ruestrian', 'wine', 'bread'], '$$', 'indoor', ['friends', 'date'], ['afternoon', 'evening'], INF, (), 'Ruestrian'),
    place('fresnian-alehouse', 'De Gulden Kraan', 'tavern', 'strangers-wharf',
          'A Fresnian alehouse with red-brick walls brought as ballast, stepped gables painted on the sign and '
          'dark gulf beer.',
          ['fresnian', 'beer', 'sailors'], '$', 'indoor', ['friends', 'coworkers'], EVE, INF, (), 'Fresnian'),
    place('dancers-hall', 'The Silver Wake', 'nightlife', 'strangers-wharf',
          'A late hall of music and dancers from every port, where exiles reinvent themselves nightly.',
          ['dancing', 'music', 'late'], '$$', 'indoor', ['friends', 'date'], ['late'], INF),

    # Marsh Fields
    place('dyke-walk', 'The Dyke Walk', 'trail', 'marsh-fields',
          'A path along the sea dyke with fields on one side and marsh birds on the other.',
          ['walk', 'birds', 'quiet'], 'free', 'outdoor', ['solo', 'date', 'family'], ALL, INF),
    place('cattle-fair-ground', 'The Cattle Ground', 'market', 'marsh-fields',
          'Weekly cattle and grain market where island farmers sell beef, barley and oats into the city.',
          ['cattle', 'farmers', 'market'], '$', 'outdoor', ['family', 'solo'], ['morning'], INF),
    place('dairy-house', 'Marsh Dairy House', 'cafe', 'marsh-fields',
          'Buttermilk, fresh cheese and oatcakes served on a farmhouse bench by the dairy door.',
          ['dairy', 'breakfast', 'farm'], '$', 'mixed', ['family', 'solo', 'date'], ['morning', 'afternoon'], INF),
    place('barley-mow', 'The Barley Mow', 'tavern', 'marsh-fields',
          'A farmers\' alehouse at the city gate with its own brewhouse and the best barley ale on the island.',
          ['ale', 'farmers', 'brewhouse'], '$', 'indoor', ['friends', 'family'], ['afternoon', 'evening'], INF, (), 'Alnhaman'),
    place('windmill', 'Dyke Mill', 'landmark', 'marsh-fields',
          'The windmill that pumps the fields dry and grinds the barley, its sails visible from the signal tower.',
          ['windmill', 'views'], 'free', 'outdoor', ['family', 'solo'], DAY, INF),
]

transit = [
    {'id': 'streets-and-stairs', 'name': 'Streets, stairs and alleys', 'kind': 'walk',
     'summary': 'Most people walk the narrow gabled streets and the stairs that climb from the quays.', 'source': INF},
    {'id': 'wherries', 'name': 'Harbour wherries', 'kind': 'boat',
     'summary': 'Rowing boats for hire between the quays, the yards, Admiralty Point and Gran Porte.', 'source': INF},
    {'id': 'hired-carriages', 'name': 'Hired carriages', 'kind': 'carriage',
     'summary': 'Few streets are wide enough; merchant houses keep carriages for the raft-palace avenues.', 'source': INF},
    {'id': 'market-road', 'name': 'The market road', 'kind': 'walk',
     'summary': 'The dyke road from the Marsh Fields into the city, busy with carts on market mornings.', 'source': INF},
]

colleges = [
    {'id': 'public-school', 'name': 'The Republic\'s Public School', 'type': 'academy', 'neighborhood': 'chart-house-hill',
     'size': 'medium', 'known_for': ['letters', 'arithmetic', 'civics'], 'source': W},
    {'id': 'navigators-school', 'name': 'School of Navigation', 'type': 'technical-institute',
     'neighborhood': 'chart-house-hill', 'size': 'small', 'known_for': ['navigation', 'astronomy', 'cartography'],
     'source': INF},
    {'id': 'masons-school', 'name': 'Guild School of Piling and Masonry', 'type': 'guild-school',
     'neighborhood': 'guild-gables', 'size': 'small', 'known_for': ['foundations', 'masonry', 'inspection'], 'source': INF},
    {'id': 'shipwrights-school', 'name': 'Shipwrights\' Apprentice Loft', 'type': 'guild-school',
     'neighborhood': 'shipwright-yards', 'size': 'small', 'known_for': ['shipbuilding', 'carpentry'], 'source': INF},
    {'id': 'counting-school', 'name': 'The Counting School', 'type': 'academy', 'neighborhood': 'ledger-quarter',
     'size': 'small', 'known_for': ['bookkeeping', 'contracts', 'insurance'], 'source': INF},
]

employers = [
    {'id': 'house-grandeholm', 'name': 'House Grandeholm', 'sector': 'commerce', 'neighborhood': 'raft-palaces',
     'size': 'large', 'summary': 'Edgar Grandeholm\'s trading, credit and insurance empire, with agents everywhere.',
     'careers': ['counting-clerk', 'merchant-factor', 'house-guard', 'house-servant', 'courier'], 'source': W},
    {'id': 'house-thorne', 'name': 'House Thorne', 'sector': 'commerce', 'neighborhood': 'ledger-quarter',
     'size': 'medium', 'summary': 'Magister Aldous Thorne\'s naval trading house and patronage of the sciences.',
     'careers': ['counting-clerk', 'merchant-factor', 'courier'], 'source': W},
    {'id': 'admiralty', 'name': 'The Republic Admiralty', 'sector': 'military', 'neighborhood': 'admiralty-point',
     'size': 'large', 'summary': 'Admiral Horatio Horne\'s navy: carracks, galleys, fortresses and watchtowers.',
     'careers': ['sailor', 'ships-man-at-arms', 'signal-keeper', 'naval-officer'], 'source': W},
    {'id': 'dock-office-employer', 'name': 'The Dock Office', 'sector': 'government', 'neighborhood': 'the-quays',
     'size': 'medium', 'summary': 'Measures, taxes and records every cargo through the port.',
     'careers': ['tide-waiter', 'counting-clerk', 'dockhand'], 'source': W},
    {'id': 'merchant-circle', 'name': 'The Two Houses', 'sector': 'government', 'neighborhood': 'ledger-quarter',
     'size': 'medium', 'summary': 'The Republic\'s government: Merchant Circle, commons\' house and their clerks.',
     'careers': ['counting-clerk', 'courier', 'arbiter'], 'source': W},
    {'id': 'masons-guild', 'name': 'Guild of Pile-Drivers and Masons', 'sector': 'construction',
     'neighborhood': 'guild-gables', 'size': 'large', 'summary': 'Builds and inspects every foundation in Grandport.',
     'careers': ['pile-driver', 'guild-mason', 'guild-surveyor'], 'source': W},
    {'id': 'carpenters-guild', 'name': 'Carpenters\' Guild', 'sector': 'construction', 'neighborhood': 'guild-gables',
     'size': 'large', 'summary': 'Timber-framers and joiners who raise the gables and rebuild after fires.',
     'careers': ['timber-framer', 'joiner'], 'source': W},
    {'id': 'great-yards', 'name': 'The Great Yards', 'sector': 'shipbuilding', 'neighborhood': 'shipwright-yards',
     'size': 'large', 'summary': 'Slipways building navy carracks and merchant hulls.',
     'careers': ['shipwright', 'sailmaker', 'ropewalk-spinner', 'caulker'], 'source': INF},
    {'id': 'fire-watch', 'name': 'The Fire-Watch', 'sector': 'public-safety', 'neighborhood': 'ashrow',
     'size': 'medium', 'summary': 'Merchant-funded watchers, bells and bucket crews across the timber districts.',
     'careers': ['fire-watcher'], 'source': W},
    {'id': 'city-militia', 'name': 'Grandport Militia', 'sector': 'military', 'neighborhood': 'admiralty-point',
     'size': 'medium', 'summary': 'District companies of longbowmen and pikemen, outfitted by merchant lords.',
     'careers': ['militia-archer'], 'source': W},
    {'id': 'chart-house-employer', 'name': 'The Chart House', 'sector': 'science', 'neighborhood': 'chart-house-hill',
     'size': 'small', 'summary': 'Draws, corrects and sells charts under Republic patronage.',
     'careers': ['chart-copyist', 'navigator'], 'source': INF},
    {'id': 'republic-press', 'name': 'The Republic Press', 'sector': 'press', 'neighborhood': 'chart-house-hill',
     'size': 'small', 'summary': 'Prints histories, shipping lists and the weekly broadsheet.',
     'careers': ['printer'], 'source': W},
    {'id': 'insurers', 'name': 'The Insurers\' Exchange', 'sector': 'finance', 'neighborhood': 'ledger-quarter',
     'size': 'medium', 'summary': 'Underwriters pricing hulls, cargoes and convoy escorts.',
     'careers': ['underwriter', 'counting-clerk'], 'source': W},
    {'id': 'temple-of-nomion-employer', 'name': 'Temple of Nomion', 'sector': 'religion', 'neighborhood': 'ledger-quarter',
     'size': 'small', 'summary': 'Arbitrates disputes and witnesses contracts.', 'careers': ['arbiter'], 'source': W},
    {'id': 'harbour-taverns', 'name': 'Harbour taverns and cookshops', 'sector': 'hospitality',
     'neighborhood': 'the-quays', 'size': 'medium', 'summary': 'The alehouses, inns and cookshops along the waterfront.',
     'careers': ['tavern-keeper', 'tavern-server', 'cook', 'musician'], 'source': INF},
    {'id': 'marsh-farms', 'name': 'The Marsh Farms', 'sector': 'agriculture', 'neighborhood': 'marsh-fields',
     'size': 'medium', 'summary': 'Barley, oat and cattle farms behind the dykes.',
     'careers': ['farmhand', 'dairymaid', 'drover'], 'source': W},
]

career_hubs = [
    {'id': 'harbour-hub', 'name': 'The harbour', 'neighborhoods': ['the-quays', 'strangers-wharf', 'gran-porte'],
     'sectors': ['logistics', 'government', 'hospitality', 'commerce'],
     'summary': 'Quays, warehouses, the dock office, taverns and foreign traders.', 'source': W},
    {'id': 'ledger-hub', 'name': 'The Ledger Quarter and the Rafts', 'neighborhoods': ['ledger-quarter', 'raft-palaces'],
     'sectors': ['commerce', 'finance', 'government', 'religion'],
     'summary': 'Counting houses, insurers, the Two Houses and the merchant palaces.', 'source': W},
    {'id': 'yards-hub', 'name': 'The yards and the gables', 'neighborhoods': ['shipwright-yards', 'guild-gables', 'ashrow'],
     'sectors': ['shipbuilding', 'construction', 'crafts', 'public-safety'],
     'summary': 'Slipways, ropewalks, guild workshops and the fire-watch.', 'source': INF},
    {'id': 'point-hub', 'name': 'Admiralty Point and the Hill', 'neighborhoods': ['admiralty-point', 'chart-house-hill'],
     'sectors': ['military', 'science', 'press', 'education'],
     'summary': 'The navy, the militia, the chart house, the press and the schools.', 'source': INF},
]


def career(id, name, sector, schedule, pay, summary, themes):
    return {'id': id, 'name': name, 'sector': sector, 'schedule': schedule, 'pay': pay, 'summary': summary,
            'themes': themes, 'eras': ['fantasy']}


careers = [
    career('dockhand', 'Dockhand', 'logistics', 'early', '$', 'Hauling cargo on the Grand Quay for a day wage, hired at the line each morning.',
           ['the hiring line', 'heavy bales', 'the foreman', 'press-gang rumours']),
    career('tide-waiter', 'Tide-waiter', 'government', 'shift-day', '$$', 'A Dock Office officer who boards ships to measure and tax their cargo.',
           ['measuring rods', 'bribes refused', 'foreign captains', 'ledgers']),
    career('counting-clerk', 'Counting-house clerk', 'commerce', 'office', '$$', 'Copying ledgers, contracts and cargo lists in a stone-floored counting house.',
           ['ink and ledgers', 'interest tables', 'the head clerk', 'late accounts']),
    career('merchant-factor', 'Merchant\'s factor', 'commerce', 'flexible', '$$$', 'Buying, selling and negotiating for a great house in port and abroad.',
           ['deals', 'foreign ports', 'the house\'s orders', 'leverage']),
    career('underwriter', 'Underwriter', 'finance', 'office', '$$$', 'Pricing the risk on hulls and cargoes at the Insurers\' Exchange.',
           ['risk', 'signal-tower news', 'wrecks', 'odds']),
    career('courier', 'Courier', 'commerce', 'flexible', '$', 'Running sealed letters between counting houses, palaces and the Two Houses.',
           ['sealed letters', 'stairs', 'gossip overheard', 'tips']),
    career('arbiter', 'Arbiter of Nomion', 'religion', 'office', '$$', 'Hearing disputes and witnessing contracts at the Temple of Nomion.',
           ['disputes', 'oaths', 'precedent', 'quarrelling merchants']),
    career('pile-driver', 'Pile-driver', 'construction', 'early', '$', 'Driving oak piles through estuary silt to bedrock for new foundations.',
           ['the ram', 'mud', 'the crew chant', 'bedrock refusal']),
    career('guild-mason', 'Guild mason', 'construction', 'early', '$$', 'Cutting and laying ashlar for counting houses and merchant palaces.',
           ['ashlar', 'mortar', 'inspection', 'apprentices']),
    career('guild-surveyor', 'Guild surveyor', 'construction', 'office', '$$', 'Inspecting joints and recording each house\'s yearly settling.',
           ['settling marks', 'failed joints', 'angry owners', 'old records']),
    career('timber-framer', 'Timber-framer', 'construction', 'early', '$$', 'Raising oak frames and steep gables, and rebuilding after fires.',
           ['oak', 'gables', 'the raising', 'fire loans']),
    career('joiner', 'Joiner', 'crafts', 'office', '$$', 'Making chests, panelling and furniture in a guild workshop.',
           ['commissions', 'joints', 'apprentices', 'fussy clients']),
    career('shipwright', 'Shipwright', 'shipbuilding', 'early', '$$', 'Framing and planking carracks and merchant hulls on the slipways.',
           ['the hull', 'launch day', 'the yard bell', 'navy contracts']),
    career('caulker', 'Caulker', 'shipbuilding', 'early', '$', 'Packing seams with oakum and hot pitch so the hulls stay dry.',
           ['pitch', 'oakum', 'burns', 'tight seams']),
    career('sailmaker', 'Sailmaker', 'shipbuilding', 'office', '$$', 'Cutting and stitching canvas in the sail loft.',
           ['canvas', 'palm and needle', 'patterns', 'storm damage']),
    career('ropewalk-spinner', 'Ropewalk spinner', 'shipbuilding', 'early', '$', 'Walking backwards down the ropewalk spinning hemp into cable.',
           ['hemp', 'songs', 'the walk', 'blisters']),
    career('sailor', 'Sailor', 'logistics', 'rotating', '$', 'Crewing a merchant or navy ship between the islands and foreign ports.',
           ['the voyage', 'the captain', 'pay day', 'ports']),
    career('ships-man-at-arms', 'Ship\'s man-at-arms', 'military', 'rotating', '$$', 'A professional boarding fighter with shield, seax and gambeson.',
           ['boarding drills', 'pirates', 'the bosun', 'old scars']),
    career('naval-officer', 'Naval officer', 'military', 'rotating', '$$$', 'A lieutenant or captain whose commission was most likely bought.',
           ['commissions', 'convoys', 'the admiral', 'discipline']),
    career('signal-keeper', 'Signal-keeper', 'military', 'rotating', '$$', 'Reading and sending flag and lantern signals across the island chain.',
           ['flags', 'lanterns', 'codes', 'night watches']),
    career('militia-archer', 'Militia longbowman', 'military', 'flexible', '$', 'A district militia archer who drills on rest days and works a trade otherwise.',
           ['the butts', 'drill days', 'the captain', 'contests']),
    career('fire-watcher', 'Fire-watcher', 'public-safety', 'shift-night', '$', 'Watching the rooftops from a tower all night and ringing the bell at smoke.',
           ['the bell', 'smoke', 'bucket crews', 'long nights']),
    career('house-guard', 'House guard', 'security', 'rotating', '$$', 'Guarding a merchant prince\'s palace, gates and secrets.',
           ['the gate', 'visitors', 'secrets', 'the household']),
    career('house-servant', 'House servant', 'domestic', 'early', '$', 'Cooking, cleaning or waiting in a raft palace.',
           ['the household', 'banquets', 'gossip', 'the steward']),
    career('navigator', 'Navigator', 'science', 'flexible', '$$$', 'Fixing positions with sextant and tables, trained in the new Republic methods.',
           ['sextant', 'longitude', 'charts', 'captains who doubt']),
    career('chart-copyist', 'Chart copyist', 'science', 'office', '$', 'Copying and correcting charts at the Chart House.',
           ['fine pens', 'coastlines', 'corrections', 'the master']),
    career('printer', 'Printer', 'press', 'office', '$$', 'Setting type and pulling sheets at the Republic Press.',
           ['type', 'ink', 'deadlines', 'politics']),
    career('tavern-keeper', 'Tavern keeper', 'hospitality', 'evening', '$$', 'Running an alehouse: barrels, regulars, debts and the watch.',
           ['regulars', 'barrels', 'fights', 'tabs']),
    career('tavern-server', 'Tavern server', 'hospitality', 'evening', '$', 'Carrying ale and gossip between tables, binding the regulars together.',
           ['regulars', 'gossip', 'tips', 'rowdy nights']),
    career('cook', 'Cookshop cook', 'hospitality', 'early', '$', 'Stews, pies and bread for dockers and clerks.',
           ['the pot', 'early fires', 'regulars', 'shortages']),
    career('musician', 'Tavern musician', 'entertainment', 'evening', '$', 'Playing hurdy-gurdy, fiddle or pipes for coins and supper.',
           ['tunes', 'crowds', 'coins in the hat', 'sea songs']),
    career('dancer', 'Dancer', 'entertainment', 'evening', '$$', 'Dancing in the halls of Strangers\' Wharf for coin and patrons.',
           ['patrons', 'costumes', 'late nights', 'reinvention']),
    career('fishmonger', 'Fishmonger', 'food', 'early', '$', 'Selling the night\'s catch on the Fish Steps.',
           ['the catch', 'ice and salt', 'haggling', 'early mornings']),
    career('baker', 'Baker', 'food', 'early', '$', 'Baking oat and barley bread before dawn under guild fire rules.',
           ['the oven', 'flour', 'fire rules', 'early customers']),
    career('farmhand', 'Farmhand', 'agriculture', 'early', '$', 'Working barley fields and dykes in the Marsh Fields.',
           ['harvest', 'dykes', 'weather', 'market day']),
    career('dairymaid', 'Dairy worker', 'agriculture', 'early', '$', 'Milking, churning and cheese-making at a marsh dairy.',
           ['milking', 'butter', 'cheese', 'cattle']),
    career('drover', 'Drover', 'agriculture', 'early', '$', 'Bringing cattle down the market road to the Cattle Ground.',
           ['the herd', 'market day', 'the road', 'buyers']),
    career('schoolteacher', 'Public school teacher', 'education', 'academic', '$$', 'Teaching letters, sums and civics at the Republic\'s public school.',
           ['pupils', 'slates', 'civics lessons', 'parents']),
]

holidays = [
    {'id': 'republic-day', 'name': 'Republic Day', 'kind': 'public', 'month': 9, 'day': 14,
     'summary': 'The founding of the Republic, with white and yellow banners, speeches at the Two Houses and the Raft Gardens opened to all.'},
    {'id': 'relief-day', 'name': 'Relief Day', 'kind': 'observance', 'month': 3, 'day': 2,
     'summary': 'The day Republican grain reached the besieged city; bread is handed out at the Relief Hall.'},
    {'id': 'fall-day', 'name': 'Fall Day', 'kind': 'observance', 'month': 1, 'day': 1,
     'summary': 'New year of the A.F. reckoning, counted from the Fall of Atlantis; lanterns are set on the water for drowned cities.'},
    {'id': 'blessing-of-the-fleet', 'name': 'Thalassar\'s Blessing', 'kind': 'feast', 'month': 4, 'weekday': 6, 'nth': 1,
     'summary': 'The shipping season opens: priests of Thalassar bless the convoys and the whole harbour turns out.'},
    {'id': 'contract-day', 'name': 'Nomion\'s Day', 'kind': 'public', 'month': 6, 'day': 1,
     'summary': 'Leases, apprenticeships and yearly contracts renew; queues at the Temple of Nomion all day.'},
    {'id': 'chryseons-night', 'name': 'Chryseon\'s Night', 'kind': 'feast', 'month': 12, 'day': 31,
     'summary': 'A coin is weighed and given away for luck in the coming year; counting houses close early.'},
    {'id': 'harbour-day', 'name': 'Harbour Day', 'kind': 'feast', 'month': 7, 'day': 20,
     'summary': 'Old Gran Porte\'s founding: boat races, fish suppers on Aelfred\'s Quay. Royalists drink to Aelfred, Republicans to the harbour.'},
    {'id': 'ash-day', 'name': 'Ash Day', 'kind': 'observance', 'month': 10, 'day': 9,
     'summary': 'Remembering the last great fire; every fire-watch bell rings at noon and hearths are inspected.'},
    {'id': 'sol-midsummer', 'name': 'Sol\'s Midsummer', 'kind': 'observance', 'month': 6, 'day': 21,
     'summary': 'The faithful of Sol Eternel keep a dawn rite at the Strangers\' Wharf chapel.'},
    {'id': 'kings-fall', 'name': 'The Lowered Banner', 'kind': 'observance', 'month': 9, 'day': 11,
     'summary': 'The anniversary of King Alrdric\'s death, kept only by royalists with bread crusts and quiet toasts.'},
]

annual_events = [
    {'id': 'longbow-fair', 'name': 'The Longbow Fair', 'months': [8], 'neighborhood': 'admiralty-point',
     'summary': 'District militia companies compete at the butts; archery is as much sport as duty here.', 'source': W},
    {'id': 'settling-survey', 'name': 'The Settling Survey', 'months': [5], 'neighborhood': 'guild-gables',
     'summary': 'Guild surveyors measure every building\'s yearly settling and chalk the marks on house corners.', 'source': W},
    {'id': 'grain-fleet', 'name': 'The Grain Fleet', 'months': [9, 10], 'neighborhood': 'strangers-wharf',
     'summary': 'Ruestrian grain galleys crowd the Strangers\' Quay and bread prices finally fall.', 'source': INF},
    {'id': 'fur-boats', 'name': 'The Fur Boats', 'months': [6], 'neighborhood': 'strangers-wharf',
     'summary': 'Pictish boats arrive with furs and deep-wood goods; the Fur and Relic Market doubles in size.', 'source': INF},
    {'id': 'launch-day', 'name': 'Spring Launch', 'months': [4], 'neighborhood': 'shipwright-yards',
     'summary': 'New carracks slide down the slipways before the season, with crowds on Launch Green.', 'source': INF},
    {'id': 'cattle-fair', 'name': 'The Autumn Cattle Fair', 'months': [10], 'neighborhood': 'marsh-fields',
     'summary': 'The big autumn cattle and barley fair before winter feed runs short.', 'source': INF},
    {'id': 'convoy-season-end', 'name': 'Laying Up', 'months': [11], 'neighborhood': 'the-quays',
     'summary': 'Ships come home for the winter gales and sailors spend a season\'s pay in a week.', 'source': INF},
    {'id': 'circle-sitting', 'name': 'The Spring Sitting', 'months': [3], 'neighborhood': 'ledger-quarter',
     'summary': 'The Two Houses open their year; tariffs are argued and the galleries fill.', 'source': INF},
]

local_color = [
    {'id': 'beef-barley-pie', 'name': 'Beef and barley pie', 'kind': 'dish',
     'summary': 'Island beef and barley in a thick crust, the everyday hot meal from the Marsh Fields to the quays.',
     'places': ['ashrow-pie-shop', 'inkwell-tavern', 'barley-mow'], 'seasons': [], 'source': INF},
    {'id': 'fish-stew', 'name': 'Quay stew', 'kind': 'dish',
     'summary': 'Whatever the boats brought, stewed with onions and eaten with barley bread.',
     'places': ['quay-cookshop', 'fish-steps'], 'seasons': [], 'source': INF},
    {'id': 'siege-loaf', 'name': 'Siege loaf', 'kind': 'dish',
     'summary': 'A hard, dark ration loaf baked on Relief Day; old people eat it in silence.',
     'places': ['relief-bread-hall', 'gable-bakery'], 'seasons': ['spring'], 'source': INF},
    {'id': 'oatcakes-buttermilk', 'name': 'Oatcakes and buttermilk', 'kind': 'dish',
     'summary': 'The farm breakfast from the Marsh Fields.', 'places': ['dairy-house', 'cattle-fair-ground'],
     'seasons': [], 'source': INF},
    {'id': 'barley-ale', 'name': 'Barley ale', 'kind': 'drink',
     'summary': 'Brewed from island barley, brown and plain; every district argues whose is best.',
     'places': ['barley-mow', 'crooked-joint', 'drowned-lantern'], 'seasons': [], 'source': INF},
    {'id': 'ruestrian-red', 'name': 'Ruestrian red', 'kind': 'drink',
     'summary': 'Imported wine, cheap on the wharf and dear on the Rafts.',
     'places': ['ruestrian-cookhouse', 'gilded-ledger'], 'seasons': [], 'source': INF},
    {'id': 'plum-brandy', 'name': 'Plum brandy', 'kind': 'drink',
     'summary': 'The naval officers\' drink, carried in flasks on watch.', 'places': ['powder-and-plum'],
     'seasons': ['fall', 'winter'], 'source': INF},
    {'id': 'saying-chryseon', 'name': '"By Chryseon\'s scale"', 'kind': 'saying',
     'summary': 'An oath sworn on deals and bets; Chryseon\'s name is spoken whenever coin is weighed.',
     'places': [], 'seasons': [], 'source': W},
    {'id': 'saying-sooner', 'name': '"Ships that arrive sooner arrive richer"', 'kind': 'saying',
     'summary': 'Eadric Wyrmscraft\'s line, now said about anything done promptly.', 'places': [], 'seasons': [], 'source': W},
    {'id': 'saying-bread', 'name': '"The Crown brought soldiers; the Republic brought bread"', 'kind': 'saying',
     'summary': 'Republican slogan from the siege; in the Lower Stairs it is usually said with a twist.',
     'places': [], 'seasons': [], 'source': W},
    {'id': 'saying-unseen', 'name': '"Budget for the unseen"', 'kind': 'saying',
     'summary': 'The builders\' rule, after the oak piles under every house, used for any careful planning.',
     'places': [], 'seasons': [], 'source': W},
    {'id': 'saying-crown', 'name': '"What sank may yet rise"', 'kind': 'saying',
     'summary': 'A royalist whisper, from Captain Sterling\'s history of the Crown beneath the waves.',
     'places': ['blue-cloth', 'crowned-horse'], 'seasons': [], 'source': W},
    {'id': 'custom-settling-marks', 'name': 'Settling marks', 'kind': 'custom',
     'summary': 'Every house corner carries chalk and chisel marks from the yearly settling survey; people read them like ages.',
     'places': [], 'seasons': [], 'source': W},
    {'id': 'custom-colours', 'name': 'White and yellow', 'kind': 'custom',
     'summary': 'The Republic\'s colours. A crowned horse on blue cloth is the old royal sign and is not shown openly.',
     'places': [], 'seasons': [], 'source': W},
    {'id': 'custom-signal-reading', 'name': 'Reading the flags', 'kind': 'custom',
     'summary': 'Harbour children and idle clerks try to read the signal tower\'s flags before the news reaches the Exchange.',
     'places': ['signal-tower', 'insurers-exchange'], 'seasons': [], 'source': INF},
    {'id': 'custom-fire-rules', 'name': 'Fire rules', 'kind': 'custom',
     'summary': 'Guild rules on chimneys, ovens and candles; neighbours report each other to the fire-watch without shame.',
     'places': ['firewatch-tower'], 'seasons': [], 'source': INF},
    {'id': 'team-longbow-companies', 'name': 'District longbow companies', 'kind': 'team',
     'summary': 'Militia archers wear their district\'s ribbon and the Longbow Fair settles a year of boasting.',
     'places': ['archery-butts'], 'seasons': ['summer'], 'source': INF},
]

prices = [
    {'id': 'ale', 'item': 'Mug of barley ale', 'low': 0.03, 'high': 0.05, 'per': '', 'source': INF},
    {'id': 'wine', 'item': 'Cup of Ruestrian red', 'low': 0.08, 'high': 0.2, 'per': '', 'source': INF},
    {'id': 'pie', 'item': 'Beef and barley pie', 'low': 0.04, 'high': 0.06, 'per': '', 'source': INF},
    {'id': 'meal', 'item': 'Tavern supper', 'low': 0.15, 'high': 0.3, 'per': 'a meal', 'source': INF},
    {'id': 'fine-dinner', 'item': 'Dinner at the Gilded Ledger', 'low': 3, 'high': 8, 'per': 'a person', 'source': INF},
    {'id': 'bread', 'item': 'Barley loaf', 'low': 0.01, 'high': 0.02, 'per': '', 'source': INF},
    {'id': 'coffee', 'item': 'Cup of coffee', 'low': 0.05, 'high': 0.1, 'per': '', 'source': INF},
    {'id': 'wherry', 'item': 'Wherry across the harbour', 'low': 0.02, 'high': 0.05, 'per': 'one way', 'source': INF},
    {'id': 'arrows', 'item': 'A dozen arrows at the butts', 'low': 0.05, 'high': 0.1, 'per': '', 'source': INF},
    {'id': 'chart', 'item': 'Copied coastal chart', 'low': 2, 'high': 6, 'per': '', 'source': INF},
    {'id': 'dockhand-wage', 'item': 'Dockhand\'s day wage', 'low': 0.3, 'high': 0.5, 'per': 'a day', 'source': INF},
    {'id': 'baths', 'item': 'Bathhouse entry', 'low': 0.03, 'high': 0.06, 'per': '', 'source': INF},
    {'id': 'inn-room', 'item': 'Room at an inn', 'low': 0.4, 'high': 1.2, 'per': 'a night', 'source': INF},
]

climate = {
    'summary': 'Warm island sea weather: mild wet winters with gales, gentle summers, wind off the water most days. '
               'High rainfall keeps the fields green.',
    'months': [
        {'high_f': 61, 'low_f': 52, 'rain_days': 17, 'note': 'Winter gales; ships laid up.'},
        {'high_f': 60, 'low_f': 51, 'rain_days': 15, 'note': 'Grey and blustery.'},
        {'high_f': 61, 'low_f': 52, 'rain_days': 15, 'note': 'First fair days; the Two Houses sit.'},
        {'high_f': 63, 'low_f': 53, 'rain_days': 12, 'note': 'Shipping season opens.'},
        {'high_f': 66, 'low_f': 56, 'rain_days': 10, 'note': 'Settling survey weather.'},
        {'high_f': 71, 'low_f': 60, 'rain_days': 7, 'note': 'Fur boats and long evenings.'},
        {'high_f': 75, 'low_f': 64, 'rain_days': 5, 'note': 'Warmest month; fire-watch on alert.'},
        {'high_f': 77, 'low_f': 65, 'rain_days': 6, 'note': 'Longbow Fair.'},
        {'high_f': 75, 'low_f': 64, 'rain_days': 9, 'note': 'Grain fleet arrives.'},
        {'high_f': 71, 'low_f': 60, 'rain_days': 13, 'note': 'Autumn squalls begin.'},
        {'high_f': 66, 'low_f': 57, 'rain_days': 15, 'note': 'Laying up for winter.'},
        {'high_f': 63, 'low_f': 54, 'rain_days': 17, 'note': 'Wet, windy, lamplit.'},
    ],
    'source': INF,
}

def words(text):
    return text.split()


# Name banks extrapolated from the wiki's naming patterns. Canon characters' names are kept out so random
# townsfolk never pose as their relatives (the characters themselves are `notables`).
ALNHAMAN_F = words("""Aelfflaed Aethelburh
    Aethelflaed Aethelgifu Aethelgyth Aethelhild Aethelthryth Aethelwyn Aldwen Aldgyth Beaduhild Beorhtgifu
    Beornwyn Brithwen Burgwyn Cwenburh Cwenhild Cwenthryth Cyneburh Cynegyth Cynehild Cynethryth Eadburh
    Eadgifu Eadgyth Eadhild Eadwyn Ealdgyth Ealhswith Eanflaed Eanswith Ecgwyn Edith Elfleda Eormengild
    Frideswide Godgifu Godhild Godwyn Goldburh Gunhild Heahburh Hereswith Hild Hildeburh Hrothwyn Leofgifu
    Leofrun Leofwyn Mildreth Mildburh Osburh Osgyth Oswyn Rowena Saehild Saewyn Sigeburh Sigewyn Sunniva
    Tilda Wenflaed Werburh Wihtburh Wilburh Wulfgifu Wulfhild Wulfrun Wulfwyn Wynflaed Wynburh
    Aldburh Ceolburh Deorwyn Ealdwyn Ecgburh Freawyn Gytha Hildwyn Leofeva Maethild Seaxburh Tova
    Waerburh Wenna Wynna Aeswyn""")
ALNHAMAN_M = words("""Aethelbald Aethelberht Aethelhard Aethelmaer
    Aethelnoth Aethelstan Aethelwulf Aldhun Aldwine Alnoth Baldwin Beorhtnoth Beorhtric Beorn Beornwulf Brand
    Brihtmaer Burgred Ceolred Ceolwulf Cenwulf Cuthbert Cuthred Cuthwine Cynebald Cynric Cynewulf Deorman
    Dunstan Eadbald Eadberht Eadgar Eadmer Eadnoth Eadred Eadwig Eadwine Eadwulf Ealdhelm Ealdred Ealdwulf
    Ealhmund Eanbald Eanred Ecgberht Ecgfrith Edwin Elfstan Ethelred Folcwine Frithric Godric Godwine
    Guthlac Haethured Heahmund Herewald Hereward Hrothgar Hunberht Ingwald Leofric Leofstan Leofwine
    Ordgar Ordric Osberht Osmund Oswald Oswin Oswulf Saewulf Sigeberht Sigeric Sigewulf Theodred Tostig
    Ulfcytel Waltheof Wigheard Wigmund Wilfrid Wulfgar Wulfhere Wulfmaer Wulfnoth Wulfric Wystan
    Beornred Garmund Hengist Ordwulf""")
ALNHAMAN_N = words("Wren Ash Robin Kit Rowan Lark Tamsin Sparrow")
ALNHAMAN_FAMILY = words("""Ashby Ashdown Bancroft Barrow Blackwater Bracewell Bramley Brookhouse
    Burnell Caldwell Carver Chandler Clayborne Coldharbour Colwell Cooper Cowling Crane Dykeman Eastbrook
    Eddings Fairwind Fairweather Farrow Fenwick Fletcher Galloway Gablestone Gilder Glover Greyhaven Hale
    Halliwell Harwood Hatherley Hayward Holt Hornsey Kettlewell Keelson Lanternman Larkin
    Ledgerwood Linwood Locke Lowther Marshall Mercer Merriweather Middleton Netherby Norwood Oakhurst Ollerton
    Palmer Penhallow Pilewright Plover Quayle Ravensby Redsail Ropewell Rowntree Saltmarsh Sandford Seawold
    Sedgwick Shipley Silverton Slade Southwell Steadhand Stoke Strand Tallow Tanner Tarrant Thatcher
    Thornbury Tidewell Tollgate Tunstall Underhill Wainwright Warrender Waterman Weatherby Wells Westmoor
    Whitby Whitlow Wickham Winslow Woodward Wyrmsley Yarrow Grandfield Brandreth Coppersmith Eastgate
    Fiddler Gale Hythe Kemble Lockyer Mariner Netherwood Ostler Pennywell Rookwood Sailor Shorehouse
    Stillwell Swanwick Tidemore Wharton Whitecliffe Windham Withers Wrexham Breakwater Cordwell Dockett""")
FRESNIAN_F = words("""Aaltje Adriana Agatha Aleida Anke Anneke Antje Baukje Cato Christina Dieuwke Elske Femke
    Geertje Gesina Griet Grietje Hendrika Hilde Ida Jacoba Janneke Jantje Johanna Josina Katrijn Klaartje Lijsbet
    Liesbeth Lotte Margriet Maaike Marieke Mayke Neeltje Petronella Reinske Saskia Sjoukje Stijntje Tanneke Teuntje
    Trijntje Wilhelmina Willemijn Wobbe Ytje Zwaantje Fokje Geeske Hiske""")
FRESNIAN_M = words("""Adriaan Arend Barend Bastiaan Bouwe Claes Cornelis Daan Diederik Dirk Douwe Egbert Evert
    Folkert Gerrit Gijsbert Govert Hendrik Hidde Jacob Jan Jelle Joost Jurriaan Kees Klaas Lammert Lieven
    Maarten Melis Nanne Pieter Reinier Roelof Ruben Sander Sibrand Siemen Sjoerd Steven Teunis Thijs Tjerk
    Walraven Wessel Willem Wouter Ysbrand Jorrit""")
FRESNIAN_FAMILY = words("""Bakker Bosch Brouwer Claessen Dekker Hoekstra Jansen Kuiper Meijer Mulder Postma Prins
    Schouten Smit Visser Vos Wouters Zijlstra Dijkstra Hendriksen Koopman Molenaar Scheepmaker Timmerman
    Veenstra Wierda""") + ['de Boer', 'de Graaf', 'de Groot', 'de Jong', 'de Vries', 'de Wit', 'van Dam',
    'van den Berg', 'van der Berg', 'van der Meer', 'van Dijk', 'van Hal', 'van Leeuwen', 'van Rijn',
    'van Wijk', 'ter Horst', 'van Asperen', 'van Brakel']
RUESTRIAN_F = words("""Adelaide Agnès Aline Amice Anne Ascelina Aude Avice Béatrix Berthe Blanche Cécile Clémence
    Colette Constance Denise Edeline Emmeline Ermengarde Esclarmonde Guillemette Héloïse Hermine Isabeau
    Isabelle Jacquette Jeanne Laure Léonor Mahaut Marguerite Marie Mélisande Nicolette Odette Pernelle Perrine
    Philippa Richilde Rosamonde Sibylle Sybille Thomasse Ysolde Yvette Gisèle Alix Brunissende""")
RUESTRIAN_M = words("""Aimery Anseau Arnaud Aubert Baudouin Bertrand Charlot Denis Drogo Enguerrand Étienne
    Eustache Foulques Gaucher Gautier Geoffroy Gérard Gilles Guérin Guillaume Hugues Jacquemin Jourdain
    Lambert Lucien Martial Mathieu Nicolas Odon Oudard Philippe Pierre Raimbaut Raoul Robert Roland Simon
    Thibaut Thierry Tristan Yves Amaury Bérenger Clément Fulbert Hélias Josselin Lancelin""")
RUESTRIAN_FAMILY = words("""Auclair Beaumont Bertin Blanchard Bonnet Chevalier Clément Delacroix Dubois Duval
    Fontaine Fournier Garnier Gauthier Guérin Lambert Lebrun Leclerc Lefèvre Legrand Marchand Martel Mercier
    Moreau Perrin Rivière Rousseau Tessier Vasseur Vidal Charpentier Boulanger Tonnelier Fauconnier""") + [
    'de Lisle', 'de Montfort', 'de Roche', 'de Vaux', "d'Aubricourt", 'de Marsan', 'de Solvane']
PICT_F = words("""Asa Brynja Dagna Gudra Hela Inga Jorna Kveta Lagra Mira Nessa Orla Rana Sigra Tova Ulla
    Vala Yrsa Bera Dalla Freka Gunna Hrafna Ketta Morva Renna Saga Torva Vigga""")
PICT_M = words("""Arn Bram Dag Eirik Grim Hakon Lok Murn Orm Rask Sten Tor Ulf Varg Bjorn Hrolf Agnar
    Brok Dregg Fenn Gorm Harald Krag Mord Rurik Skarn Thrain Ulfar Vidar""")
PICT_FAMILY = ['of the Boar', 'of the Bear', 'of the Wolf', 'of the Deer', 'of the Shadowfang',
    'of the Thunderhoof', 'of the Elk', 'of the Raven', 'of the Seal', 'of the Lynx']
ELF_F = words("""Aerwen Ithriel Lairenë Saelwen Tuilinë Merawen Nimriel Elanwë Silmarë Faelith Iriel Lothiel
    Varanë Celewen Aranel Ilwen Yavië Loriel Thessa Daphne Ione Phaedra Rhea Thalia Melina Aletha""")
ELF_M = words("""Aerendil Thalion Voriel Saeron Tuilar Calandor Elorin Maranor Ithrandir Faelor Lairon Quelaron
    Belion Caranor Nethril Varion Halion Erevan Ilmarin Tavor Theon Doros Kallias Myron Nikias""")
ELF_FAMILY = ['of the Hrívë Court', 'Fernwhisper', 'Mossfall', 'Thornwillow', 'Leafmantle',
    'Brookshade', 'Ashenbough', 'Dewglen', 'Starbriar', 'Quellarin', 'Tuilëandor']
FAR_F = words("Freya Xenia Kalliope Irina Sigrun Thora Asta Liv Ragna Dalia Zora Leandra Nerissa Selka Yara")
FAR_M = words("Theron Halvard Torvin Ivar Damon Leander Ragnar Orm Darius Esben Kasimir Nils Tarik Yannick")
FAR_FAMILY = words("Freyhold Seafarer Islesend Farshore Northwind Wavecrest Saltwind Longvoyage Driftwell Westerly Tradewind Harbourne")

names = {
 'year': 2578,
 'mix': {'alnhaman': 8, 'fresnian': 1.2, 'ruestrian': 1.0, 'far-voyagers': 0.6, 'pictish': 0.25, 'elven': 0.08},
 'groups': {
 # Old English given names with English place and trade family names, like the wiki's Alnhamans.
 'alnhaman': {'feminine': ALNHAMAN_F, 'masculine': ALNHAMAN_M, 'neutral': ALNHAMAN_N,
 'family': ALNHAMAN_FAMILY},
 # Dutch, like the wiki's Fresnians (Floris van der Veen, Marijke van Daal, Geert Folke).
 'fresnian': {'feminine': FRESNIAN_F, 'masculine': FRESNIAN_M, 'neutral': [], 'family': FRESNIAN_FAMILY},
 # French, like the wiki's Ruestrians (Jehan Guilbert, Louvin l'Audice, Renauld).
 'ruestrian': {'feminine': RUESTRIAN_F, 'masculine': RUESTRIAN_M, 'neutral': [], 'family': RUESTRIAN_FAMILY},
 # Far-voyaging Alnhama mixes more than its neighbours (Freydis, Ophir, Xanthe in the wiki).
 'far-voyagers': {'feminine': FAR_F, 'masculine': FAR_M, 'neutral': [], 'family': FAR_FAMILY},
 # Short northern names with the tribe as the family name, like the wiki's Kasa of the Boar Tribe.
 'pictish': {'feminine': PICT_F, 'masculine': PICT_M, 'neutral': [], 'family': PICT_FAMILY,
 'own_family': True},
 # Elves are rare since the Veil; names after the wiki's elven and Greek-sounding ones.
 'elven': {'feminine': ELF_F, 'masculine': ELF_M, 'neutral': [], 'family': ELF_FAMILY, 'own_family': True},
 },
}

notables = [
 {'id': 'edgar-grandeholm', 'name': 'Edgar Grandeholm', 'given': 'Edgar', 'pronouns': 'he/him', 'age': 56,
 'place': 'grandeholm-tower', 'role': 'Merchant Lord of Grandport', 'staff': True, 'temperament': 'shrewd',
 'about': 'Founder of the Merchant Circle and its richest man: large, silk-clad, rings on nearly every finger. '
 'He rules contracts, insurance and harbour policy from the upper chambers of his tower and believes '
 'only in leverage.', 'source': W},
 {'id': 'aldous-thorne', 'name': 'Aldous Thorne', 'given': 'Aldous', 'pronouns': 'he/him', 'age': 64,
 'place': 'merchant-circle-hall', 'role': 'Magister of the Merchant Circle', 'staff': False,
 'temperament': 'principled',
 'about': 'Author of The Ledger of Liberty and the Republic\'s idealist: austere dark wools, silver beard, sharp '
 'grey eyes. Led the militia in the siege and now patrons navigators and scholars.', 'source': W},
 {'id': 'horatio-horne', 'name': 'Horatio Horne', 'given': 'Horatio', 'pronouns': 'he/him', 'age': 51,
 'place': 'admiralty-fortress', 'role': 'Admiral of the Republic', 'staff': True, 'temperament': 'blunt',
 'about': 'The Merchant Circle founder who brought the ships: broad, copper-red hair and beard, gold-trimmed '
 'dark coats. Royalists call him a turncoat; he talks of hulls, powder and tides.', 'source': W},
 {'id': 'eadric-wyrmscraft', 'name': 'Eadric Wyrmscraft', 'given': 'Eadric', 'pronouns': 'he/him', 'age': 22,
 'place': 'chart-house', 'role': 'cartographer of the Republic', 'staff': True, 'temperament': 'confident',
 'about': 'A shipwright\'s son who rebuilt an Atlantean sextant and bounded the longitude problem; sharp, '
 'arrogant and usually right. Finishing his great book of the geography of Neokosmos.', 'source': W},
 {'id': 'aelric-stillhand', 'name': 'Aelric Stillhand', 'given': 'Aelric', 'pronouns': 'he/him', 'age': 46,
 'place': 'sol-chapel', 'role': 'merchant and missionary of Sol Eternel', 'staff': False,
 'temperament': 'gentle',
 'about': 'Alnhaman trader turned missionary, captain of the Sunnlad: thinning hair, broad bearded face, light '
 'blue eyes that listen. Keeps careful accounts of every faith he meets.', 'source': W},
 {'id': 'ceolmund', 'name': 'Ceolmund', 'pronouns': 'he/him', 'age': 48, 'place': 'grand-quay',
 'role': 'trader', 'staff': False, 'temperament': 'steady',
 'about': 'A calm, honest trader known in many ports: stocky, salt-and-pepper beard, warm hazel eyes, dark '
 'overcoat and a ledger always to hand. Settles crew quarrels with a few measured words.', 'source': W},
 {'id': 'ceolwynn', 'name': 'Ceolwynn', 'pronouns': 'she/her', 'age': 20, 'place': 'drowned-lantern',
 'role': 'hurdy-gurdy player', 'staff': False, 'temperament': 'shy',
 'about': 'Ceolmund\'s quiet daughter, petite with soft brown eyes and her mother\'s pendant. Says little; her '
 'hurdy-gurdy says the rest, and sailors swear it steadies a whole room.', 'source': W},
 {'id': 'freydis', 'name': 'Freydis', 'pronouns': 'she/her', 'age': 26, 'place': 'insurers-exchange',
 'role': 'merchant guild clerk', 'staff': False, 'temperament': 'bold',
 'about': 'Tall and athletic, black-dyed bob, icy blue eyes; an orphan raised by the merchant guild. Quick, '
 'funny and somehow a slightly different person each time you meet her.', 'source': W},
 {'id': 'ophir', 'name': 'Ophir', 'pronouns': 'she/her', 'age': 29, 'place': 'dancers-hall',
 'role': 'dancer', 'staff': True, 'temperament': 'charming',
 'about': 'A former noblewoman turned dancer: tall, sun-tanned, long black hair, light blue eyes, white silk '
 'trimmed in gold. Every smile is calculated; she means to be powerful again.', 'source': W},
]

sources = {
 'wiki': {
 'kind': 'other', 'title': 'Neokosmos Wiki: Children of Sol Eternel, The Steel and the Sun',
 'license': 'CC BY-NC-SA 4.0; included with Oak\'s permission', 'retrieved': '2026-10-10', 'url': 'https://quietoak.github.io/NeokosmosWiki/',
 'attribution': 'Oak',
 'note': 'Named in or directly described by the wiki: Grandport\'s raft palaces, Edgar\'s tower, guild '
 'inspection, fire-watch, dock office, lower stairs, the Two Houses, Admiralty, signal towers, '
 'Nomion, Thalassar and Chryseon, people and history.',
 },
 'inferred': {
 'kind': 'other', 'title': 'Filled in from the Neokosmos lore for Prospero\'s Companion',
 'license': 'Neokosmos is CC BY-NC-SA 4.0 by Oak; included with Oak\'s permission', 'retrieved': '2026-10-10',
 'attribution': 'Oak (source world)',
 'note': 'Everyday places, careers, holidays and their dates, food, prices, climate and the exact '
 'district layout are invented in the setting\'s voice to give the city street-level detail. '
 'Correct freely. Coordinates are a stand-in grid for distances only.',
 },
}

CITY = {
 'schema_version': 1, 'id': 'grandport', 'name': 'Grandport', 'setting': 'fictional', 'era': 'fantasy',
 'category': 'fictional',
 'basis': 'Grandport in Neokosmos, a dark fantasy world by Oak (https://quietoak.github.io/NeokosmosWiki/, '
 'CC BY-NC-SA 4.0), included with Oak\'s permission.',
 'region': 'The Alnhaman Islands', 'country': 'The Alnhama Republic', 'timezone': 'Atlantic/Azores',
 'aliases': ['Gran Porte'],
 'summary': 'The merchant republic\'s capital, built on oak piles in a shifting estuary: steep timber gables, '
 'stone counting houses and merchant palaces on stone rafts. Ten years after the Revolution, the '
 'Merchant Circle rules and royalists still whisper about the exiled prince.',
 'lat': LAT, 'lon': LON,
 'currency': {'code': 'sw', 'symbol': 'sw', 'name': 'silver weights'},
 'rent_period': 'week', 'speeds': {'walk': 4.0, 'boat': 6, 'carriage': 8},
 'sources': sources, 'neighborhoods': neighborhoods, 'places': places, 'colleges': colleges,
 'employers': employers, 'career_hubs': career_hubs, 'transit': transit, 'climate': climate,
 'annual_events': annual_events, 'careers': careers, 'names': names, 'local_color': local_color,
 'prices': prices, 'calendar': 'none', 'holidays': holidays, 'notables': notables,
}
if __name__ == '__main__':
 OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
 print(f'Wrote {OUT}')
