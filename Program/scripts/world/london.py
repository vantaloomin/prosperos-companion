"""Curated data for London today. Run `python scripts/world/london.py` to rewrite the shipped JSON.

London in 1895 is a separate city (`scripts/world/london_1895.py`, id `london-1895`).
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'cities' / 'london.json'
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


def college(id, name, type, hood, size, known_for):
    return {'id': id, 'name': name, 'type': type, 'neighborhood': hood, 'size': size, 'known_for': known_for,
            'source': S}


def employer(id, name, sector, hood, size, summary, careers):
    return {'id': id, 'name': name, 'sector': sector, 'neighborhood': hood, 'size': size, 'summary': summary,
            'careers': careers, 'source': S}


def hub(id, name, hoods, sectors, summary):
    return {'id': id, 'name': name, 'neighborhoods': hoods, 'sectors': sectors, 'summary': summary, 'source': S}


def line(id, name, kind, summary):
    return {'id': id, 'name': name, 'kind': kind, 'summary': summary, 'source': S}


def event(id, name, months, hood, summary):
    return {'id': id, 'name': name, 'months': months, 'neighborhood': hood, 'summary': summary, 'source': S}


def color(id, name, kind, summary, places=(), seasons=()):
    return {'id': id, 'name': name, 'kind': kind, 'summary': summary, 'places': list(places),
            'seasons': list(seasons), 'source': S}


def price(id, item, low, high, per=''):
    return {'id': id, 'item': item, 'low': low, 'high': high, 'per': per, 'source': S}


def month(high, low, rain, note):
    return {'high_f': high, 'low_f': low, 'rain_days': rain, 'note': note}


ALL = ['solo', 'friends', 'date', 'family']
ADULT = ['solo', 'friends', 'date']
PUB = ['friends', 'date', 'solo', 'coworkers']
DAY = ['morning', 'afternoon']
OPEN = ['morning', 'afternoon', 'evening']
LUNCH = ['afternoon', 'evening']
NIGHT = ['evening', 'late']
DRINKS = ['afternoon', 'evening', 'late']
WARM = ['spring', 'summer', 'fall']
SUMMER = ['summer']

# Typical asking rents in pounds a month (studio, one bedroom, two bedrooms).
PRIME = ([1900, 2800], [2600, 4200], [3600, 6500])
DEAR = ([1500, 2100], [2000, 2900], [2700, 4000])
MIDDLE = ([1250, 1650], [1650, 2300], [2100, 2900])
OUTER = ([1050, 1400], [1400, 1800], [1750, 2300])

BUS, BIKE, BOAT = 'london-buses', 'santander-cycles', 'thames-clippers'

CITY = {
    'schema_version': 1, 'id': 'london', 'name': 'London', 'region': 'Greater London', 'country': 'United Kingdom',
    'timezone': 'Europe/London',
    'aliases': ['London, UK', 'London, England', 'London UK', 'Greater London', 'The Big Smoke'],
    'summary': 'The capital of the United Kingdom: a sprawl of villages grown together along the Thames, with the '
               'Square Mile\'s banks, West End theatres, free national museums, royal parks, a pub on every corner '
               'and the Tube underneath it all.',
    'lat': 51.507, 'lon': -0.128,
    'currency': {'code': 'GBP', 'symbol': '£', 'name': 'pounds sterling'},
    'rent_period': 'month',
    'speeds': {'walk': 4.5, 'car': 16, 'rideshare': 16, 'bus': 11, 'subway': 26, 'light-rail': 22,
               'commuter-rail': 32, 'ferry': 20, 'bike-share': 13},
    # Rough heritage weights for residents' names (estimates, not census figures); `anglo` is local, so English.
    'names': {'mix': {'anglo': 6, 'south-asian': 1.5, 'west-african': 1, 'caribbean': 0.8, 'slavic': 0.6,
                       'irish': 0.5, 'east-asian': 0.5, 'arabic': 0.4, 'jewish': 0.3, 'italian': 0.3}},
    'sources': {
        S: {'kind': 'curated', 'title': 'London places and neighbourhoods written for Prospero Companion',
            'license': 'CC0-1.0', 'retrieved': '2026-10-10',
            'note': 'Well-known public places, institutions and employers from general knowledge. Businesses open '
                    'and close and rents move fast here: treat this as a snapshot for fiction. Rents are rounded '
                    'estimates of typical asking ranges in pounds a month, not listings. Coordinates are '
                    'approximate neighbourhood centres.'},
        CLIMATE: {'kind': 'curated', 'title': 'Approximate monthly climate for London (Heathrow)',
                  'license': 'CC0-1.0', 'retrieved': '2026-10-10',
                  'note': 'Rounded values in line with Met Office 1991-2020 averages for Heathrow, converted to '
                          'Fahrenheit; central London runs a degree or two warmer. Refresh with scripts/world when '
                          'network access to the Met Office is available.'},
    },
    'neighborhoods': [
        # Central
        hood('soho', 'Soho', 'The heart of the West End: narrow streets of restaurants, late bars, jazz clubs and '
             'LGBTQ+ venues, between Oxford Street, Chinatown, Theatreland and Trafalgar Square.',
             ['nightlife', 'food', 'theatre', 'lgbtq-friendly', 'central'], 51.513, -0.134, 'very-high', PRIME,
             ['mansion-block', 'flat-above-shop', 'new-build'], 'high',
             ['central', 'northern', 'victoria', 'piccadilly', 'elizabeth', 'national-rail', BUS, BIKE]),
        hood('covent-garden', 'Covent Garden', 'The old fruit-and-veg market turned piazza of street performers, '
             'shops and the Royal Opera House, running down to the Strand, Aldwych and the river.',
             ['touristy', 'theatre', 'shopping', 'historic', 'central'], 51.512, -0.123, 'very-high', PRIME,
             ['mansion-block', 'flat-above-shop', 'student-halls'], 'high',
             ['piccadilly', 'northern', 'district', 'national-rail', BUS, BIKE, BOAT]),
        hood('bloomsbury', 'Bloomsbury', 'Georgian squares, the British Museum and the University of London '
             'campus, quietly literary and full of students.', ['academic', 'literary', 'leafy', 'museums',
             'students'], 51.522, -0.127, 'high', DEAR, ['georgian-terrace', 'mansion-block', 'student-halls'],
             'high', ['piccadilly', 'northern', 'central', 'elizabeth', 'national-rail', BUS, BIKE]),
        hood('city-of-london', 'City of London', 'The Square Mile: Roman walls, Wren churches and St Paul\'s among '
             'the glass towers of banks and insurers; packed on weekdays, hushed at weekends.',
             ['business', 'historic', 'finance', 'quiet-weekends'], 51.515, -0.090, 'very-high', PRIME,
             ['new-build', 'barbican-flat', 'converted-office'], 'high',
             ['central', 'northern', 'district', 'elizabeth', 'dlr', 'national-rail', BUS, BIKE]),
        hood('kings-cross', 'King\'s Cross', 'Once railway lands and warehouses behind two great stations, now '
             'Granary Square, Coal Drops Yard, Google\'s offices, Central Saint Martins and the canal.',
             ['regenerated', 'tech', 'canalside', 'students', 'transport-hub'], 51.535, -0.124, 'high', DEAR,
             ['new-build', 'council-estate', 'victorian-conversion'], 'high',
             ['northern', 'victoria', 'piccadilly', 'national-rail', BUS, BIKE]),
        hood('south-bank', 'South Bank', 'The riverside arts strip from the London Eye past the Southbank Centre and '
             'National Theatre to Tate Modern, the Globe and Borough Market, with Waterloo and London Bridge '
             'stations at either end.', ['arts', 'riverside', 'food', 'touristy'], 51.506, -0.105, 'high', DEAR,
             ['new-build', 'council-estate', 'warehouse-conversion'], 'high',
             ['jubilee', 'northern', 'national-rail', BUS, BIKE, BOAT]),
        # East
        hood('shoreditch', 'Shoreditch', 'Street art, tech start-ups, cocktail bars and Sunday flower sellers '
             'around Hoxton Square, Old Street and the edge of the City.', ['creative', 'nightlife', 'tech',
             'street-art', 'young-professional'], 51.526, -0.079, 'high', DEAR,
             ['warehouse-conversion', 'new-build', 'council-estate'], 'high',
             ['overground', 'northern', 'central', 'elizabeth', BUS, BIKE]),
        hood('whitechapel', 'Whitechapel', 'The East End of Brick Lane\'s curry houses and Sunday markets, '
             'Spitalfields, the Royal London Hospital and the city\'s largest Bangladeshi community.',
             ['diverse', 'food', 'markets', 'historic', 'bangladeshi'], 51.518, -0.065, 'mid', MIDDLE,
             ['council-estate', 'victorian-terrace', 'new-build', 'warehouse-conversion'], 'high',
             ['district', 'central', 'overground', 'elizabeth', BUS, BIKE]),
        hood('hackney', 'Hackney', 'Victorian terraces around London Fields, Broadway Market and Victoria Park, '
             'running north to Dalston\'s Turkish grills, record shops and late clubs.',
             ['creative', 'parks', 'food', 'nightlife', 'young-families'], 51.543, -0.062, 'mid', MIDDLE,
             ['victorian-terrace', 'council-estate', 'warehouse-conversion', 'houseboat'], 'high',
             ['overground', BUS, BIKE]),
        hood('canary-wharf', 'Canary Wharf', 'The Docklands business district of bank towers and malls on the Isle '
             'of Dogs, with old riverside pubs in Limehouse and Wapping nearby.',
             ['business', 'finance', 'riverside', 'new-build'], 51.505, -0.020, 'high', DEAR,
             ['apartment-tower', 'new-build', 'warehouse-conversion'], 'medium',
             ['elizabeth', 'jubilee', 'dlr', BUS, BIKE, BOAT]),
        hood('stratford', 'Stratford', 'The 2012 Olympic Park, West Ham\'s stadium, Westfield and new towers, beside '
             'Hackney Wick\'s canal-side breweries; one of the best-connected stations in London.',
             ['regenerated', 'sport', 'shopping', 'new-build', 'transport-hub'], 51.541, -0.003, 'mid', MIDDLE,
             ['apartment-tower', 'new-build', 'victorian-terrace'], 'medium',
             ['elizabeth', 'central', 'jubilee', 'dlr', 'overground', 'national-rail', BUS, BIKE]),
        hood('walthamstow', 'Walthamstow', 'A neighbourly north-east London district of terraced streets, a mile-long '
             'street market, Walthamstow Village and reservoirs turned wetlands.',
             ['neighbourly', 'young-families', 'markets', 'nature'], 51.583, -0.020, 'mid', MIDDLE,
             ['victorian-terrace', 'edwardian-terrace', 'council-estate'], 'medium',
             ['victoria', 'overground', BUS]),
        hood('tottenham', 'Tottenham', 'A diverse, hard-working corner of north London around the High Road, with '
             'Spurs\' stadium, Caribbean, Turkish and West African shops and the Lee Valley marshes.',
             ['diverse', 'football', 'affordable', 'changing'], 51.597, -0.070, 'low', OUTER,
             ['victorian-terrace', 'council-estate', 'new-build'], 'medium',
             ['victoria', 'overground', 'national-rail', BUS]),
        # North
        hood('camden', 'Camden', 'Camden Market, the Lock, live-music pubs and punk history, between Regent\'s Park, '
             'Primrose Hill and the canal.', ['music', 'markets', 'alternative', 'nightlife', 'touristy'],
             51.539, -0.143, 'high', DEAR, ['victorian-conversion', 'council-estate', 'mansion-block'], 'high',
             ['northern', 'overground', BUS, BIKE]),
        hood('islington', 'Islington', 'Upper Street\'s restaurants and theatres, Georgian squares, antiques in '
             'Camden Passage and Arsenal\'s stadium up the road in Highbury.',
             ['food', 'theatre', 'georgian', 'football', 'professional'], 51.538, -0.103, 'high', DEAR,
             ['georgian-terrace', 'victorian-conversion', 'council-estate'], 'high',
             ['northern', 'victoria', 'overground', 'piccadilly', BUS, BIKE]),
        hood('hampstead', 'Hampstead', 'A hilltop village of Georgian lanes, old pubs and literary houses on the '
             'edge of Hampstead Heath, with its ponds, lido and views over the city.',
             ['affluent', 'leafy', 'literary', 'village', 'nature'], 51.556, -0.178, 'high',
             ([1600, 2300], [2200, 3300], [3200, 5200]), ['georgian-terrace', 'mansion-block', 'detached-house'],
             'medium', ['northern', 'overground', BUS]),
        # West
        hood('notting-hill', 'Notting Hill', 'Pastel terraces, Portobello Road\'s market and antiques, the Carnival '
             'every August, and Golborne Road\'s Portuguese and Moroccan cafes.',
             ['photogenic', 'markets', 'affluent', 'carnival', 'diverse'], 51.512, -0.205, 'very-high', PRIME,
             ['stucco-terrace', 'mews-house', 'council-estate', 'victorian-conversion'], 'high',
             ['central', 'district', BUS, BIKE]),
        hood('kensington', 'Kensington', 'South Kensington\'s great museums and Imperial College, Hyde Park and the '
             'Royal Albert Hall, running down to Chelsea\'s King\'s Road and Stamford Bridge.',
             ['museums', 'affluent', 'parks', 'students', 'grand'], 51.496, -0.174, 'very-high', PRIME,
             ['stucco-terrace', 'mansion-block', 'mews-house'], 'high',
             ['piccadilly', 'district', 'overground', BUS, BIKE]),
        hood('southall', 'Southall', 'West London\'s Little Punjab: sari shops, sweet centres and Punjabi grills '
             'along the Broadway and the largest Sikh gurdwara outside India, a short ride from Heathrow.',
             ['south-asian', 'food', 'family', 'affordable'], 51.511, -0.377, 'low', OUTER,
             ['semi-detached', 'victorian-terrace', 'council-estate'], 'medium', ['elizabeth', 'national-rail', BUS]),
        hood('richmond', 'Richmond', 'A riverside town on London\'s south-western edge, with deer in Richmond Park, '
             'Kew Gardens next door and Twickenham\'s rugby up the road.',
             ['leafy', 'riverside', 'affluent', 'family', 'nature'], 51.461, -0.303, 'high', DEAR,
             ['victorian-terrace', 'georgian-terrace', 'detached-house'], 'medium',
             ['district', 'overground', 'national-rail', BUS]),
        # South
        hood('brixton', 'Brixton', 'The heart of Caribbean London since the Windrush years: a covered market of '
             'food stalls, a famous music venue, a lido and plenty of late-night life.',
             ['caribbean', 'music', 'markets', 'nightlife', 'diverse'], 51.462, -0.115, 'mid', MIDDLE,
             ['victorian-conversion', 'council-estate', 'new-build'], 'high',
             ['victoria', 'national-rail', BUS]),
        hood('peckham', 'Peckham', 'Rye Lane\'s Nigerian and Ghanaian grocers, art-school bars on car-park '
             'rooftops and a creative crowd from nearby Goldsmiths and Camberwell.',
             ['creative', 'diverse', 'nightlife', 'west-african', 'young-professional'], 51.470, -0.069, 'mid',
             MIDDLE, ['victorian-conversion', 'council-estate', 'warehouse-conversion'], 'high',
             ['overground', 'national-rail', BUS]),
        hood('clapham', 'Clapham', 'Clapham Common\'s young professionals and brunch spots, running west to Battersea '
             'Park and the restored Battersea Power Station on the river.',
             ['young-professional', 'nightlife', 'parks', 'brunch'], 51.465, -0.145, 'high', DEAR,
             ['victorian-conversion', 'mansion-block', 'new-build'], 'high',
             ['northern', 'overground', 'national-rail', BUS, BIKE, BOAT]),
        hood('bermondsey', 'Bermondsey', 'Old warehouses and wharves south of Tower Bridge, now Bermondsey Street\'s '
             'restaurants, the weekend food market at Maltby Street and a beer mile under the railway arches.',
             ['food', 'beer', 'warehouse', 'riverside'], 51.498, -0.078, 'high', DEAR,
             ['warehouse-conversion', 'council-estate', 'new-build'], 'high',
             ['jubilee', 'overground', 'national-rail', BUS, BIKE, BOAT]),
        hood('greenwich', 'Greenwich', 'Maritime Greenwich: the Royal Observatory and the Prime Meridian, the Cutty '
             'Sark, a covered market and a big hilltop park, with the O2 across the peninsula.',
             ['historic', 'riverside', 'parks', 'family', 'touristy'], 51.481, -0.005, 'mid',
             ([1300, 1750], [1750, 2400], [2200, 3100]), ['georgian-terrace', 'new-build', 'victorian-terrace'],
             'high', ['dlr', 'jubilee', 'national-rail', BUS, BOAT]),
    ],
    'transit': [
        line('elizabeth', 'Elizabeth line', 'commuter-rail', 'Fast, air-conditioned purple trains in deep tunnels '
             'from Reading and Heathrow through Paddington, Bond Street, Tottenham Court Road, Liverpool Street and '
             'Canary Wharf to Stratford, Abbey Wood and Shenfield.'),
        line('central', 'Central line', 'subway', 'Red Tube line straight across London from Ealing and Notting '
             'Hill Gate through Oxford Circus, Holborn and Bank to Stratford and Essex; hot in summer.'),
        line('northern', 'Northern line', 'subway', 'Black Tube line from Edgware and High Barnet through Camden, '
             'Euston and the City or the West End to Clapham, Morden and Battersea Power Station.'),
        line('victoria', 'Victoria line', 'subway', 'Light-blue Tube line from Walthamstow and Tottenham through '
             'King\'s Cross, Oxford Circus and Victoria to Brixton, with trains every couple of minutes.'),
        line('piccadilly', 'Piccadilly line', 'subway', 'Dark-blue Tube line from Heathrow through South Kensington, '
             'Piccadilly Circus, Covent Garden and King\'s Cross to Arsenal and Cockfosters.'),
        line('jubilee', 'Jubilee line', 'subway', 'Grey Tube line from Stanmore through Bond Street, Westminster, '
             'Waterloo and London Bridge to Canary Wharf, North Greenwich and Stratford.'),
        line('district', 'District line', 'subway', 'Green, mostly sub-surface line from Richmond and Wimbledon '
             'through Earl\'s Court, South Kensington, Westminster and the City to Whitechapel and Upminster.'),
        line('overground', 'London Overground', 'commuter-rail', 'Orbital orange rail lines (Liberty, Lioness, '
             'Mildmay, Suffragette, Weaver and Windrush) linking Richmond, Hampstead, Camden, Islington, Dalston, '
             'Shoreditch, Whitechapel, Peckham, Clapham Junction, Walthamstow and Stratford without going central.'),
        line('dlr', 'Docklands Light Railway', 'light-rail', 'Driverless trains from Bank and Tower Gateway through '
             'Canary Wharf to Greenwich, Lewisham, Stratford and the Royal Docks; sit at the front.'),
        line('national-rail', 'National Rail suburban trains', 'commuter-rail', 'Thameslink, Southern, '
             'Southeastern, South Western and Greater Anglia trains from the main termini to the suburbs, all on '
             'the same contactless fares inside London.'),
        line(BUS, 'London buses', 'bus', 'Red buses, double-deckers on most routes, covering every corner of the '
             'city round the clock on night routes; tap in once with a card or phone, no cash.'),
        line(BIKE, 'Santander Cycles', 'bike-share', 'Docking-station hire bikes and e-bikes across central and inner '
             'London, from Hammersmith to Stratford and Clapham to Camden.'),
        line(BOAT, 'Uber Boat by Thames Clippers', 'ferry', 'River buses on the Thames from Battersea Power Station '
             'and Westminster past the South Bank and Tower Bridge to Canary Wharf, Greenwich and the O2.'),
    ],
    'places': [
        # Soho and the West End
        place('bar-italia', 'Bar Italia', 'cafe', 'soho', 'Frith Street espresso bar open since 1949, with a neon '
              'sign, a TV showing the football and tables out on the pavement until the small hours.',
              ['espresso', 'historic', 'late-night', 'people-watching'], '$', 'mixed', ADULT,
              ['morning', 'afternoon', 'evening', 'late'], cuisine='italian-cafe'),
        place('maison-bertaux', 'Maison Bertaux', 'cafe', 'soho', 'Tiny Greek Street patisserie founded in 1871, '
              'all cream cakes, eclairs and mismatched chairs.', ['pastries', 'historic', 'cosy'], '$', 'indoor',
              ALL, DAY, cuisine='french-patisserie'),
        place('kiln', 'Kiln', 'restaurant', 'soho', 'Counter seats facing clay pots and grills on Brewer Street, '
              'serving fiery northern-Thai and Burmese-influenced dishes.', ['thai', 'counter', 'spicy'], '$$',
              'indoor', ADULT, LUNCH, cuisine='thai'),
        place('french-house', 'The French House', 'bar', 'soho', 'Dean Street pub that pours beer only by the half '
              'pint, has no music or phones, and was the Free French\'s wartime haunt.',
              ['pub', 'historic', 'no-phones', 'wine'], '$$', 'indoor', PUB, DRINKS),
        place('ronnie-scotts', 'Ronnie Scott\'s', 'venue', 'soho', 'Frith Street jazz club open since 1959, with '
              'two sets a night and a late show upstairs.', ['jazz', 'live-music', 'historic'], '$$$', 'indoor',
              ADULT, NIGHT),
        place('chinatown', 'Chinatown', 'attraction', 'soho', 'Gerrard Street and Lisle Street under red lanterns: '
              'dim sum, roast duck in windows, bubble tea and bakeries.', ['food', 'lanterns', 'dim-sum'], '$$',
              'outdoor', ALL, ['afternoon', 'evening', 'late'], cuisine='cantonese'),
        place('national-gallery', 'National Gallery', 'museum', 'soho', 'Free national collection of European '
              'paintings on Trafalgar Square, from Van Eyck to Van Gogh\'s Sunflowers.',
              ['art', 'free', 'iconic', 'rainy-day'], 'free', 'indoor', ALL, DAY),
        place('west-end-theatres', 'Theatreland', 'venue', 'soho', 'The West End\'s Victorian and Edwardian theatres '
              'along Shaftesbury Avenue and around Leicester Square, with long-running musicals and new plays; the '
              'TKTS booth sells day-of seats.', ['theatre', 'musicals', 'iconic'], '$$$', 'indoor',
              ['date', 'friends', 'family'], ['afternoon', 'evening']),
        place('heaven-nightclub', 'Heaven', 'nightlife', 'soho', 'Long-running LGBTQ+ nightclub in the arches under '
              'Charing Cross station, open since 1979.', ['lgbtq', 'club', 'dancing'], '$$', 'indoor',
              ['friends', 'date'], ['late']),
        # Covent Garden
        place('covent-garden-piazza', 'Covent Garden Piazza and Market', 'market', 'covent-garden', 'The old market '
              'hall and piazza, with street performers outside St Paul\'s church and craft stalls in the Apple '
              'Market.', ['street-performers', 'shopping', 'iconic'], '$$', 'mixed', ALL, OPEN),
        place('royal-opera-house', 'Royal Opera House', 'venue', 'covent-garden', 'Home of the Royal Opera and the '
              'Royal Ballet, with cheap standing places and a public rooftop terrace.', ['opera', 'ballet',
              'classical'], '$$$', 'indoor', ['date', 'solo', 'friends'], ['afternoon', 'evening']),
        place('dishoom-covent-garden', 'Dishoom Covent Garden', 'restaurant', 'covent-garden', 'The first of the '
              'Bombay-cafe-style restaurants, known for bacon naan rolls at breakfast and black daal; expect a '
              'queue.', ['bombay-cafe', 'breakfast', 'queue'], '$$', 'indoor', ALL, OPEN, cuisine='indian'),
        place('monmouth-coffee', 'Monmouth Coffee', 'cafe', 'covent-garden', 'Monmouth Street coffee shop roasting '
              'its own beans since 1978, with a bench for four and a queue out the door.',
              ['coffee', 'roaster', 'historic'], '$', 'indoor', ['solo', 'friends'], DAY),
        place('lamb-and-flag', 'Lamb & Flag', 'bar', 'covent-garden', 'Low-beamed pub in an alley off Rose Street, '
              'one of the oldest in the West End; drinkers spill into the courtyard.', ['pub', 'historic',
              'real-ale'], '$$', 'mixed', PUB, DRINKS),
        place('rules-restaurant', 'Rules', 'restaurant', 'covent-garden', 'Opened in 1798 on Maiden Lane and said to '
              'be London\'s oldest restaurant: game, pies and puddings among red plush and paintings.',
              ['historic', 'british', 'special-occasion'], '$$$$', 'indoor', ['date', 'family'], LUNCH,
              cuisine='british'),
        place('oasis-sports-centre', 'Oasis Sports Centre', 'fitness', 'covent-garden', 'Council leisure centre on '
              'Endell Street with a heated outdoor pool open all year, a rare swim in the middle of the West End.',
              ['swimming', 'outdoor-pool', 'gym'], '$', 'mixed', ['solo', 'friends'], ['morning', 'evening']),
        # Bloomsbury
        place('british-museum', 'British Museum', 'museum', 'bloomsbury', 'Free world collection from the Rosetta '
              'Stone to the Parthenon sculptures under the Great Court\'s glass roof.', ['history', 'free',
              'iconic', 'rainy-day'], 'free', 'indoor', ALL, DAY),
        place('russell-square', 'Russell Square', 'park', 'bloomsbury', 'One of the largest Bloomsbury squares, with '
              'a fountain, plane trees and a cafe kiosk.', ['square', 'quiet', 'lunch-spot'], 'free', 'outdoor',
              ALL, OPEN),
        place('the-lamb-bloomsbury', 'The Lamb', 'bar', 'bloomsbury', 'Victorian pub on Lamb\'s Conduit Street with '
              'etched-glass snob screens around the bar.', ['pub', 'victorian', 'real-ale'], '$$', 'indoor', PUB,
              DRINKS),
        place('london-review-bookshop', 'London Review Bookshop', 'shopping', 'bloomsbury', 'Independent bookshop by '
              'the British Museum with a cake shop and evening author talks.', ['books', 'cake', 'talks'], '$$',
              'indoor', ['solo', 'date'], OPEN),
        place('ciao-bella', 'Ciao Bella', 'restaurant', 'bloomsbury', 'Old-school Italian trattoria on Lamb\'s '
              'Conduit Street since the 1980s, with a piano and big birthday tables.', ['trattoria', 'pasta',
              'lively'], '$$', 'indoor', ALL, LUNCH, cuisine='italian'),
        place('charles-dickens-museum', 'Charles Dickens Museum', 'museum', 'bloomsbury', 'Dickens\'s family home on '
              'Doughty Street, where he wrote Oliver Twist, with a garden cafe.', ['literary', 'historic-house',
              'rainy-day'], '$$', 'indoor', ['solo', 'date', 'family'], DAY),
        # City of London
        place('st-pauls-cathedral', 'St Paul\'s Cathedral', 'landmark', 'city-of-london', 'Wren\'s domed cathedral, '
              'with the Whispering Gallery and a climb to the Golden Gallery for the view.', ['iconic',
              'architecture', 'views'], '$$', 'indoor', ALL, DAY),
        place('tower-of-london', 'Tower of London', 'attraction', 'city-of-london', 'Norman fortress, royal prison and '
              'home of the Crown Jewels, with Yeoman Warders\' tours and the ravens.', ['history', 'crown-jewels',
              'iconic'], '$$$', 'mixed', ['family', 'friends', 'solo'], DAY),
        place('tower-bridge', 'Tower Bridge', 'landmark', 'city-of-london', 'The Victorian bascule bridge, with a '
              'glass-floored walkway between the towers and the bridge lifting for tall ships.',
              ['iconic', 'views', 'river'], '$$', 'mixed', ALL, OPEN),
        place('barbican-centre', 'Barbican Centre', 'venue', 'city-of-london', 'Brutalist arts centre in the Barbican '
              'Estate: the London Symphony Orchestra, theatre, cinema and galleries, with a lakeside terrace and a '
              'tropical conservatory open on some days.', ['concerts', 'brutalist', 'cinema', 'arts'], '$$',
              'indoor', ['date', 'solo', 'friends'], ['afternoon', 'evening']),
        place('sky-garden', 'Sky Garden', 'attraction', 'city-of-london', 'Free (booked ahead) glasshouse garden and '
              'bars at the top of the "Walkie-Talkie" at 20 Fenchurch Street.', ['views', 'free', 'rooftop'],
              'free', 'indoor', ALL, OPEN),
        place('leadenhall-market', 'Leadenhall Market', 'market', 'city-of-london', 'Ornate Victorian covered market '
              'of pubs, lunch spots and shops, busy with City workers at lunchtime.', ['victorian', 'lunch',
              'architecture'], '$$', 'indoor', ['coworkers', 'friends', 'solo'], ['afternoon', 'evening']),
        place('the-blackfriar', 'The Blackfriar', 'bar', 'city-of-london', 'Wedge-shaped pub by Blackfriars Bridge '
              'with an Arts and Crafts interior of carved jolly friars in bronze and marble.', ['pub', 'historic',
              'after-work'], '$$', 'indoor', PUB, DRINKS),
        place('sweetings', 'Sweetings', 'restaurant', 'city-of-london', 'Victorian fish restaurant on Queen Victoria '
              'Street, open for weekday lunch only, with counters, black velvet and no bookings.',
              ['seafood', 'historic', 'lunch'], '$$$', 'indoor', ['coworkers', 'solo', 'friends'], ['afternoon'],
              cuisine='british-seafood'),
        # King's Cross
        place('british-library', 'British Library', 'library', 'kings-cross', 'The national library on Euston Road: '
              'free treasures gallery, a glass tower of the King\'s books and reading rooms for anyone with a '
              'reader pass.', ['study', 'free', 'treasures', 'rainy-day'], 'free', 'indoor', ['solo'], OPEN),
        place('coal-drops-yard', 'Coal Drops Yard', 'shopping', 'kings-cross', 'Victorian coal sheds rebuilt with '
              'kissing rooflines, now independent shops, restaurants and bars.', ['shopping', 'design',
              'regenerated'], '$$', 'mixed', ['friends', 'date', 'solo'], ['afternoon', 'evening']),
        place('granary-square', 'Granary Square', 'square', 'kings-cross', 'Big public square on the Regent\'s Canal '
              'with dancing fountains, canal steps and the art school behind.', ['fountains', 'canal', 'free'],
              'free', 'outdoor', ALL, OPEN),
        place('dishoom-kings-cross', 'Dishoom King\'s Cross', 'restaurant', 'kings-cross', 'Bombay-cafe-style '
              'restaurant in a former railway goods shed, with a basement bar.', ['bombay-cafe', 'breakfast',
              'cocktails'], '$$', 'indoor', ALL, OPEN, cuisine='indian'),
        place('wellcome-collection', 'Wellcome Collection', 'museum', 'kings-cross', 'Free museum of medicine, life '
              'and art on Euston Road, with an upstairs reading room full of cushions.', ['free', 'science',
              'curious', 'rainy-day'], 'free', 'indoor', ADULT, DAY),
        place('the-lighterman', 'The Lighterman', 'bar', 'kings-cross', 'Three-floor pub and terrace on Granary '
              'Square overlooking the canal.', ['pub', 'terrace', 'canal', 'after-work'], '$$', 'mixed', PUB,
              DRINKS),
        place('caravan-kings-cross', 'Caravan King\'s Cross', 'cafe', 'kings-cross', 'All-day restaurant and coffee '
              'roastery in the Granary Building, a weekend brunch fixture.', ['coffee', 'brunch', 'roaster'], '$$',
              'indoor', ALL, OPEN),
        # South Bank
        place('tate-modern', 'Tate Modern', 'museum', 'south-bank', 'Free modern and contemporary art in the old '
              'Bankside power station, with the Turbine Hall and a view from the tenth floor.',
              ['art', 'free', 'iconic', 'rainy-day'], 'free', 'indoor', ALL, ['morning', 'afternoon', 'evening']),
        place('southbank-centre', 'Southbank Centre', 'venue', 'south-bank', 'The Royal Festival Hall, Queen Elizabeth '
              'Hall and Hayward Gallery, with free foyer music, a skate undercroft and a riverside book market.',
              ['concerts', 'skateboarding', 'free-events', 'riverside'], '$$', 'mixed', ALL, OPEN),
        place('national-theatre', 'National Theatre', 'venue', 'south-bank', 'Three stages in Denys Lasdun\'s '
              'concrete building by Waterloo Bridge, with cheap Friday Rush tickets.', ['theatre', 'brutalist',
              'riverside'], '$$', 'indoor', ['date', 'solo', 'friends'], ['afternoon', 'evening']),
        place('shakespeares-globe', 'Shakespeare\'s Globe', 'venue', 'south-bank', 'Open-air reconstruction of '
              'Shakespeare\'s playhouse, with five-pound standing tickets in the yard; candlelit plays in the '
              'indoor playhouse in winter.', ['shakespeare', 'theatre', 'open-air'], '$$', 'outdoor',
              ['date', 'friends', 'family', 'solo'], ['afternoon', 'evening'], WARM),
        place('bfi-southbank', 'BFI Southbank', 'venue', 'south-bank', 'The British Film Institute\'s cinemas under '
              'Waterloo Bridge, with seasons of classics and a free film archive viewing room.', ['cinema',
              'classics', 'rainy-day'], '$$', 'indoor', ['solo', 'date', 'friends'], ['afternoon', 'evening']),
        place('london-eye', 'London Eye', 'attraction', 'south-bank', 'Giant observation wheel opposite the Houses '
              'of Parliament; a half-hour turn in a glass pod.', ['views', 'iconic', 'touristy'], '$$$', 'mixed',
              ALL, OPEN),
        place('borough-market', 'Borough Market', 'market', 'south-bank', 'London\'s best-known food market under '
              'the railway at London Bridge: cheese, bread, oysters and street food, packed at lunchtime.',
              ['food', 'market', 'street-food', 'iconic'], '$$', 'mixed', ALL, DAY),
        place('george-inn', 'The George Inn', 'bar', 'south-bank', 'London\'s last galleried coaching inn, off '
              'Borough High Street, with a courtyard that fills on summer evenings.', ['pub', 'historic',
              'courtyard'], '$$', 'mixed', PUB, DRINKS),
        # Shoreditch
        place('columbia-road-flower-market', 'Columbia Road Flower Market', 'market', 'shoreditch', 'Sunday-morning '
              'flower market on a Victorian street of tiny shops, with traders calling out bargains near closing.',
              ['flowers', 'sunday', 'photogenic'], '$', 'outdoor', ALL, ['morning']),
        place('boxpark-shoreditch', 'Boxpark Shoreditch', 'market', 'shoreditch', 'Shipping containers of street '
              'food, bars and pop-up shops by Shoreditch High Street station.', ['street-food', 'casual',
              'football-screenings'], '$$', 'mixed', ['friends', 'coworkers'], ['afternoon', 'evening']),
        place('ozone-coffee', 'Ozone Coffee Roasters', 'cafe', 'shoreditch', 'Big roastery cafe on Leonard Street '
              'with a coffee bar and all-day brunch.', ['coffee', 'roaster', 'brunch', 'laptop-friendly'], '$$',
              'indoor', ['solo', 'friends', 'coworkers'], DAY),
        place('shoreditch-street-art', 'Shoreditch street art', 'attraction', 'shoreditch', 'Murals and paste-ups that '
              'change by the month around Brick Lane, Rivington Street and Great Eastern Street.', ['street-art',
              'free', 'walk'], 'free', 'outdoor', ADULT, DAY),
        place('village-underground', 'Village Underground', 'venue', 'shoreditch', 'Victorian warehouse venue for '
              'gigs and club nights, with old Tube carriages on the roof.', ['live-music', 'club', 'warehouse'],
              '$$', 'indoor', ['friends', 'date'], NIGHT),
        place('museum-of-the-home', 'Museum of the Home', 'museum', 'shoreditch', 'Rooms of London homes through '
              'four centuries in old almshouses on Kingsland Road, with period gardens.', ['history', 'free',
              'gardens', 'rainy-day'], 'free', 'mixed', ALL, DAY),
        place('song-que', 'Sông Quê Café', 'restaurant', 'shoreditch', 'Long-running Vietnamese canteen on Kingsland '
              'Road\'s "pho mile".', ['pho', 'casual', 'cheap-eats'], '$', 'indoor', ALL, LUNCH,
              cuisine='vietnamese'),
        # Whitechapel and Brick Lane
        place('brick-lane-curry-houses', 'Brick Lane curry houses', 'restaurant', 'whitechapel', 'The row of '
              'Bangladeshi-run curry houses on Brick Lane, with touts outside and bring-your-own-beer at some.',
              ['curry', 'iconic', 'late'], '$', 'indoor', ['friends', 'coworkers', 'date'], ['evening', 'late'],
              cuisine='bangladeshi'),
        place('beigel-bake', 'Beigel Bake', 'restaurant', 'whitechapel', 'Twenty-four-hour bagel bakery on Brick Lane '
              'serving hot salt beef and mustard to a queue at any hour.', ['bagels', '24-hour', 'salt-beef',
              'cheap-eats'], '$', 'indoor', ALL, ['morning', 'afternoon', 'evening', 'late'], cuisine='jewish'),
        place('tayyabs', 'Tayyabs', 'restaurant', 'whitechapel', 'Huge, noisy Punjabi grill off Whitechapel Road, '
              'famous for sizzling lamb chops; bring your own drinks.', ['grill', 'byob', 'lamb-chops'], '$',
              'indoor', ['friends', 'family', 'coworkers'], ['evening'], cuisine='punjabi'),
        place('whitechapel-gallery', 'Whitechapel Gallery', 'museum', 'whitechapel', 'Free contemporary art gallery '
              'on Whitechapel High Street that showed Picasso\'s Guernica in 1938.', ['art', 'free', 'rainy-day'],
              'free', 'indoor', ADULT, DAY),
        place('old-spitalfields-market', 'Old Spitalfields Market', 'market', 'whitechapel', 'Victorian market hall '
              'of fashion, vinyl and street food, with antiques on Thursdays.', ['market', 'street-food',
              'vintage'], '$$', 'indoor', ALL, DAY),
        place('e-pellicci', 'E. Pellicci', 'cafe', 'whitechapel', 'Family-run cafe on Bethnal Green Road since 1900, '
              'with a listed Art Deco wood-panelled interior and full English breakfasts.', ['full-english',
              'historic', 'family-run'], '$', 'indoor', ALL, DAY, cuisine='british-cafe'),
        place('ten-bells', 'The Ten Bells', 'bar', 'whitechapel', 'Victorian corner pub opposite Spitalfields Market '
              'with old tiled walls.', ['pub', 'historic'], '$$', 'indoor', PUB, DRINKS),
        place('york-hall', 'York Hall', 'fitness', 'whitechapel', 'Bethnal Green leisure centre known for boxing '
              'nights, with a pool and a basement Turkish baths spa.', ['boxing', 'swimming', 'spa'], '$', 'indoor',
              ['solo', 'friends'], ['morning', 'evening']),
        # Hackney
        place('broadway-market', 'Broadway Market', 'market', 'hackney', 'Saturday street market of bakers, coffee, '
              'street food and vintage between London Fields and the canal.', ['food', 'saturday', 'canal'], '$$',
              'outdoor', ALL, DAY),
        place('london-fields-lido', 'London Fields Lido', 'fitness', 'hackney', 'Heated fifty-metre outdoor pool on '
              'London Fields, open all year.', ['swimming', 'lido', 'outdoor-pool'], '$', 'outdoor',
              ['solo', 'friends', 'family'], ['morning', 'afternoon', 'evening']),
        place('victoria-park', 'Victoria Park', 'park', 'hackney', 'East London\'s big Victorian park, with boating '
              'lakes, a Chinese pagoda, a Sunday market and summer music festivals.', ['lakes', 'running',
              'festivals'], 'free', 'outdoor', ALL, OPEN),
        place('pavilion-cafe-victoria-park', 'Pavilion Cafe', 'cafe', 'hackney', 'Lakeside domed cafe in Victoria '
              'Park, busy with runners and buggies for breakfast.', ['breakfast', 'lakeside', 'park'], '$',
              'mixed', ALL, DAY),
        place('hackney-empire', 'Hackney Empire', 'venue', 'hackney', 'Frank Matcham\'s 1901 variety theatre on Mare '
              'Street, famous for comedy and its Christmas panto.', ['theatre', 'comedy', 'panto'], '$$', 'indoor',
              ALL, ['evening']),
        place('mangal-2', 'Mangal 2', 'restaurant', 'hackney', 'Family-run Turkish ocakbaşı grill on Stoke '
              'Newington Road, cooking over charcoal since 1994.', ['grill', 'kebab', 'family-run'], '$$', 'indoor',
              ALL, ['evening'], cuisine='turkish'),
        place('cat-and-mutton', 'The Cat & Mutton', 'bar', 'hackney', 'Corner pub at the top of Broadway Market, '
              'spilling onto the pavement on Saturdays.', ['pub', 'sunday-roast', 'local'], '$$', 'indoor', PUB,
              DRINKS),
        # Camden
        place('camden-market', 'Camden Market', 'market', 'camden', 'Rambling markets around Camden Lock and the '
              'Stables: street food, vintage, goth and punk stalls.', ['street-food', 'vintage', 'alternative',
              'touristy'], '$$', 'mixed', ['friends', 'date', 'family'], ['afternoon', 'evening']),
        place('regents-canal-towpath', 'Regent\'s Canal towpath', 'trail', 'camden', 'Canal walk from Camden Lock '
              'past narrowboats to King\'s Cross, or west through the Zoo to Little Venice.', ['canal', 'walk',
              'narrowboats'], 'free', 'outdoor', ALL, OPEN),
        place('primrose-hill', 'Primrose Hill', 'park', 'camden', 'Grassy hill above Regent\'s Park with one of the '
              'best free views of the skyline.', ['views', 'picnic', 'sunset'], 'free', 'outdoor', ALL, OPEN),
        place('roundhouse', 'Roundhouse', 'venue', 'camden', 'Victorian railway engine shed turned concert and '
              'circus venue on Chalk Farm Road.', ['live-music', 'historic', 'circus'], '$$', 'indoor',
              ['friends', 'date'], NIGHT),
        place('london-zoo', 'ZSL London Zoo', 'attraction', 'camden', 'The world\'s oldest scientific zoo, on the '
              'north edge of Regent\'s Park.', ['animals', 'family', 'historic'], '$$$', 'outdoor',
              ['family', 'date', 'friends'], DAY),
        place('regents-park-open-air-theatre', 'Regent\'s Park Open Air Theatre', 'venue', 'camden', 'Summer plays '
              'and musicals in a leafy amphitheatre in Regent\'s Park.', ['theatre', 'open-air', 'picnic'], '$$',
              'outdoor', ['date', 'friends', 'family'], ['afternoon', 'evening'], ['spring', 'summer']),
        place('hawley-arms', 'The Hawley Arms', 'bar', 'camden', 'Rock-and-roll pub by the Lock with a roof terrace, '
              'once a favourite of Amy Winehouse.', ['pub', 'music', 'terrace'], '$$', 'indoor', ['friends', 'date'],
              DRINKS),
        place('poppies-camden', 'Poppies Fish & Chips', 'restaurant', 'camden', 'Retro 1950s-style chippy run by a '
              'fish-and-chips veteran, with cod in newspaper-print paper and mushy peas.', ['fish-and-chips',
              'retro', 'casual'], '$$', 'indoor', ALL, LUNCH, cuisine='fish-and-chips'),
        # Islington
        place('camden-passage', 'Camden Passage', 'shopping', 'islington', 'Narrow lane off Upper Street of antique '
              'stalls, vintage shops and cafes.', ['antiques', 'vintage', 'browsing'], '$$', 'outdoor',
              ['solo', 'date', 'friends'], DAY),
        place('almeida-theatre', 'Almeida Theatre', 'venue', 'islington', 'Small, bold theatre off Upper Street whose '
              'productions often transfer to the West End.', ['theatre', 'new-writing'], '$$', 'indoor',
              ['date', 'solo', 'friends'], ['evening']),
        place('sadlers-wells', 'Sadler\'s Wells', 'venue', 'islington', 'London\'s home of dance, from ballet to '
              'hip-hop, on Rosebery Avenue.', ['dance', 'performance'], '$$', 'indoor', ['date', 'friends', 'solo'],
              ['evening']),
        place('emirates-stadium', 'Emirates Stadium', 'stadium', 'islington', 'Arsenal\'s 60,000-seat home in '
              'Holloway, with stadium tours on non-match days.', ['football', 'arsenal', 'matchday'], '$$$',
              'outdoor', ['friends', 'family'], ['afternoon', 'evening'], ['fall', 'winter', 'spring']),
        place('ottolenghi-islington', 'Ottolenghi Islington', 'restaurant', 'islington', 'Upper Street deli and '
              'restaurant with salads piled in the window and big meringues.', ['deli', 'brunch', 'salads'], '$$$',
              'indoor', ['date', 'friends'], OPEN, cuisine='middle-eastern'),
        place('island-queen', 'The Island Queen', 'bar', 'islington', 'Victorian pub near the Regent\'s Canal with '
              'papier-mache figures hanging from the ceiling and a good Sunday roast.', ['pub', 'sunday-roast',
              'local'], '$$', 'indoor', PUB, DRINKS),
        place('pophams-islington', 'Pophams', 'cafe', 'islington', 'Neighbourhood bakery near Essex Road with maple '
              'bacon pastries in the morning.', ['bakery', 'pastries', 'coffee'], '$', 'indoor', ALL, DAY),
        # Brixton
        place('brixton-village', 'Brixton Village and Market Row', 'market', 'brixton', 'Covered 1930s arcades of '
              'Caribbean, African and Latin American food stalls, plus Electric Avenue\'s street market outside.',
              ['street-food', 'caribbean', 'market', 'diverse'], '$', 'mixed', ALL, ['afternoon', 'evening']),
        place('brixton-academy', 'O2 Academy Brixton', 'venue', 'brixton', 'Art Deco former cinema with a sloping '
              'floor, one of London\'s best-loved gig venues.', ['live-music', 'art-deco'], '$$', 'indoor',
              ['friends', 'date'], NIGHT),
        place('ritzy-cinema', 'Ritzy Picturehouse', 'venue', 'brixton', 'Edwardian cinema on Windrush Square with a '
              'cafe-bar upstairs.', ['cinema', 'historic'], '$$', 'indoor', ['date', 'friends', 'solo'],
              ['afternoon', 'evening']),
        place('brockwell-park', 'Brockwell Park', 'park', 'brixton', 'Hilly park with views north to the City, a '
              'walled garden and summer festivals.', ['views', 'festivals', 'picnic'], 'free', 'outdoor', ALL,
              OPEN),
        place('brockwell-lido', 'Brockwell Lido', 'fitness', 'brixton', 'Grade II-listed 1937 lido, unheated and '
              'open all year for hardy swimmers, with a cafe by the water.', ['swimming', 'lido', 'cold-water'],
              '$', 'outdoor', ['solo', 'friends', 'family'], ['morning', 'afternoon']),
        place('black-cultural-archives', 'Black Cultural Archives', 'museum', 'brixton', 'National heritage centre '
              'for Black British history, on Windrush Square.', ['history', 'black-british', 'free'], 'free',
              'indoor', ['solo', 'family', 'friends'], DAY),
        place('fish-wings-and-tings', 'Fish, Wings & Tings', 'restaurant', 'brixton', 'Caribbean kitchen in Brixton '
              'Village: jerk chicken, saltfish fritters and rum punch.', ['caribbean', 'jerk', 'casual'], '$$',
              'indoor', ALL, LUNCH, cuisine='caribbean'),
        place('effra-hall-tavern', 'The Effra Hall Tavern', 'bar', 'brixton', 'Victorian pub with live jazz and a '
              'Caribbean kitchen at the back.', ['pub', 'jazz', 'caribbean'], '$', 'indoor', PUB, DRINKS),
        # Peckham
        place('franks-cafe', 'Frank\'s Cafe', 'bar', 'peckham', 'Summer-only bar on the top of a multi-storey car '
              'park, with Campari, sunsets and a skyline view.', ['rooftop', 'sunset', 'views', 'seasonal'], '$$',
              'outdoor', ['friends', 'date'], ['afternoon', 'evening'], ['spring', 'summer']),
        place('peckham-library', 'Peckham Library', 'library', 'peckham', 'Prize-winning upside-down-L library with '
              'a copper skin and coloured glass.', ['architecture', 'free', 'study'], 'free', 'indoor',
              ['solo', 'family'], OPEN),
        place('bussey-building', 'Bussey Building', 'nightlife', 'peckham', 'Old cricket-bat factory off Rye Lane '
              'with club nights, a rooftop and arts events.', ['club', 'warehouse', 'dancing'], '$$', 'indoor',
              ['friends'], ['late']),
        place('peckham-rye-park', 'Peckham Rye Park and Common', 'park', 'peckham', 'Common and park with a Japanese '
              'garden, a lake and Sunday football.', ['park', 'gardens', 'football'], 'free', 'outdoor', ALL, OPEN),
        place('kudu', 'Kudu', 'restaurant', 'peckham', 'Neighbourhood restaurant on Queen\'s Road with South '
              'African-inspired cooking and skillet bread.', ['date-night', 'south-african', 'neighbourhood'],
              '$$$', 'indoor', ['date', 'friends'], ['evening'], cuisine='south-african'),
        place('gowlett-arms', 'The Gowlett Arms', 'bar', 'peckham', 'Backstreet pub known for stone-baked pizzas and '
              'DJs on Sundays.', ['pub', 'pizza', 'local'], '$$', 'indoor', PUB, DRINKS),
        place('rye-lane', 'Rye Lane', 'shopping', 'peckham', 'Busy high street of Nigerian and Ghanaian grocers, '
              'fabric shops, hair salons and fried-fish counters.', ['african', 'groceries', 'busy'], '$',
              'outdoor', ['solo', 'friends', 'family'], DAY),
        # Clapham and Battersea
        place('clapham-common', 'Clapham Common', 'park', 'clapham', 'Big open common with ponds, a bandstand, '
              'running loops and summer festivals.', ['running', 'picnic', 'festivals'], 'free', 'outdoor', ALL,
              OPEN),
        place('clapham-grand', 'Clapham Grand', 'venue', 'clapham', 'Victorian music hall with comedy, gigs and '
              'singalong club nights.', ['comedy', 'club', 'historic'], '$$', 'indoor', ['friends', 'date'], NIGHT),
        place('windmill-clapham', 'The Windmill', 'bar', 'clapham', 'Big pub on the edge of Clapham Common with a '
              'garden full on sunny afternoons.', ['pub', 'beer-garden', 'common'], '$$', 'mixed', PUB, DRINKS),
        place('trinity-clapham', 'Trinity', 'restaurant', 'clapham', 'Michelin-starred neighbourhood restaurant in '
              'Clapham Old Town.', ['fine-dining', 'special-occasion'], '$$$$', 'indoor', ['date'], ['evening'],
              cuisine='modern-british'),
        place('battersea-park', 'Battersea Park', 'park', 'clapham', 'Riverside Victorian park with a Peace Pagoda, '
              'boating lake, children\'s zoo and the Pump House Gallery.', ['river', 'running', 'family'], 'free',
              'outdoor', ALL, OPEN),
        place('battersea-power-station', 'Battersea Power Station', 'shopping', 'clapham', 'The four-chimneyed power '
              'station restored as shops, restaurants and a lift up a chimney.', ['shopping', 'architecture',
              'river'], '$$', 'indoor', ALL, OPEN),
        place('pear-tree-cafe', 'Pear Tree Cafe', 'cafe', 'clapham', 'Lakeside cafe in Battersea Park.', ['cafe',
              'lakeside', 'brunch'], '$', 'mixed', ALL, DAY),
        # Notting Hill
        place('portobello-road-market', 'Portobello Road Market', 'market', 'notting-hill', 'Long street market of '
              'antiques on Saturdays, fruit and veg in the week and vintage under the Westway.',
              ['antiques', 'vintage', 'saturday', 'iconic'], '$$', 'outdoor', ALL, DAY),
        place('electric-cinema', 'Electric Cinema', 'venue', 'notting-hill', 'One of Britain\'s oldest working '
              'cinemas, from 1910, with armchairs and sofas.', ['cinema', 'historic', 'date-night'], '$$$',
              'indoor', ['date', 'friends'], ['afternoon', 'evening']),
        place('lisboa-patisserie', 'Lisboa Patisserie', 'cafe', 'notting-hill', 'Golborne Road Portuguese bakery '
              'known for custard tarts.', ['pasteis-de-nata', 'bakery', 'local'], '$', 'indoor', ALL, DAY,
              cuisine='portuguese'),
        place('holland-park', 'Holland Park', 'park', 'notting-hill', 'Woodland park with peacocks, the Kyoto '
              'Garden\'s koi and summer opera.', ['gardens', 'peacocks', 'quiet'], 'free', 'outdoor', ALL, OPEN),
        place('churchill-arms', 'The Churchill Arms', 'bar', 'notting-hill', 'Kensington Church Street pub covered '
              'in flowers outside, with a Thai kitchen in its conservatory.', ['pub', 'flowers', 'thai-food'], '$$',
              'indoor', PUB, DRINKS, cuisine='thai'),
        place('portobello-star', 'Portobello Star', 'bar', 'notting-hill', 'Narrow cocktail bar on Portobello Road, '
              'birthplace of a London gin.', ['cocktails', 'gin'], '$$$', 'indoor', ['date', 'friends'], NIGHT),
        # Kensington and Chelsea
        place('natural-history-museum', 'Natural History Museum', 'museum', 'kensington', 'Free museum in a '
              'Romanesque cathedral of terracotta, with Hope the blue whale and the dinosaurs.', ['dinosaurs',
              'free', 'family', 'rainy-day'], 'free', 'indoor', ALL, DAY),
        place('science-museum', 'Science Museum', 'museum', 'kensington', 'Free museum of engines, spacecraft and '
              'medicine, with an interactive gallery for children and adults-only Lates.', ['science', 'free',
              'family', 'rainy-day'], 'free', 'indoor', ALL, DAY),
        place('v-and-a', 'Victoria and Albert Museum', 'museum', 'kensington', 'Free museum of art and design, from '
              'Raphael cartoons to fashion, with a courtyard garden and paddling pool.', ['design', 'fashion',
              'free', 'rainy-day'], 'free', 'indoor', ALL, DAY),
        place('royal-albert-hall', 'Royal Albert Hall', 'venue', 'kensington', 'The great domed hall, home of the '
              'summer Proms with cheap standing tickets in the arena.', ['concerts', 'proms', 'iconic'], '$$',
              'indoor', ALL, ['afternoon', 'evening']),
        place('hyde-park', 'Hyde Park', 'park', 'kensington', 'The great royal park, with the Serpentine\'s boats, '
              'Speakers\' Corner and Kensington Gardens next door.', ['royal-park', 'boating', 'running'], 'free',
              'outdoor', ALL, OPEN),
        place('serpentine-lido', 'Serpentine Lido', 'fitness', 'kensington', 'Summer swimming in a roped-off stretch '
              'of the Serpentine lake in Hyde Park.', ['swimming', 'open-water', 'lake'], '$', 'outdoor',
              ['solo', 'friends', 'family'], DAY, SUMMER),
        place('stamford-bridge', 'Stamford Bridge', 'stadium', 'kensington', 'Chelsea FC\'s home on the Fulham Road '
              'since 1905.', ['football', 'chelsea', 'matchday'], '$$$', 'outdoor', ['friends', 'family'],
              ['afternoon', 'evening'], ['fall', 'winter', 'spring']),
        place('daquise', 'Daquise', 'restaurant', 'kensington', 'Polish restaurant by South Kensington station since '
              '1947: pierogi, beetroot soup and vodka.', ['historic', 'pierogi', 'vodka'], '$$', 'indoor', ALL,
              LUNCH, cuisine='polish'),
        place('anglesea-arms', 'The Anglesea Arms', 'bar', 'kensington', 'Old South Kensington pub with a terrace on '
              'a quiet street.', ['pub', 'terrace', 'sunday-roast'], '$$', 'mixed', PUB, DRINKS),
        # Greenwich
        place('royal-observatory', 'Royal Observatory', 'museum', 'greenwich', 'Flamsteed House, the Prime Meridian '
              'line and a planetarium on top of Greenwich Park.', ['astronomy', 'history', 'views'], '$$', 'mixed',
              ALL, DAY),
        place('national-maritime-museum', 'National Maritime Museum', 'museum', 'greenwich', 'Free museum of ships, '
              'navigation and exploration.', ['maritime', 'free', 'family', 'rainy-day'], 'free', 'indoor', ALL,
              DAY),
        place('cutty-sark', 'Cutty Sark', 'attraction', 'greenwich', 'Fastest of the tea clippers, raised above a '
              'glass-roofed dry dock.', ['ship', 'history', 'family'], '$$', 'mixed', ALL, DAY),
        place('greenwich-park', 'Greenwich Park', 'park', 'greenwich', 'Royal park with the best view of Canary Wharf '
              'and the City from the Observatory hill, plus deer in a walled enclosure.', ['views', 'royal-park',
              'picnic'], 'free', 'outdoor', ALL, OPEN),
        place('greenwich-market', 'Greenwich Market', 'market', 'greenwich', 'Covered market of crafts, antiques and '
              'street food.', ['crafts', 'street-food', 'antiques'], '$', 'indoor', ALL, DAY),
        place('trafalgar-tavern', 'Trafalgar Tavern', 'bar', 'greenwich', 'Regency riverside pub where Dickens and '
              'Thackeray ate whitebait.', ['pub', 'river', 'historic'], '$$', 'indoor', PUB, DRINKS),
        place('goddards', 'Goddards at Greenwich', 'restaurant', 'greenwich', 'Pie and mash shop run by the same '
              'family since 1890, with liquor sauce and jellied eels.', ['pie-and-mash', 'historic', 'cheap-eats'],
              '$', 'indoor', ALL, ['afternoon'], cuisine='pie-and-mash'),
        place('the-o2', 'The O2', 'venue', 'greenwich', 'The arena in the old Millennium Dome on Greenwich Peninsula, '
              'for big concerts and sport, with a walk over the roof.', ['concerts', 'arena'], '$$$', 'indoor',
              ['friends', 'date', 'family'], ['evening']),
        # Canary Wharf and Docklands
        place('crossrail-place-roof-garden', 'Crossrail Place Roof Garden', 'garden', 'canary-wharf', 'Free garden '
              'under a timber lattice roof on top of the Elizabeth line station.', ['free', 'gardens', 'lunch-spot'],
              'free', 'mixed', ALL, OPEN),
        place('london-museum-docklands', 'London Museum Docklands', 'museum', 'canary-wharf', 'Free museum of the '
              'river, port and people in a Georgian sugar warehouse at West India Quay.', ['history', 'free',
              'rainy-day'], 'free', 'indoor', ALL, DAY),
        place('the-grapes-limehouse', 'The Grapes', 'bar', 'canary-wharf', 'Narrow 18th-century riverside pub on '
              'Narrow Street, Limehouse, with a tiny balcony on the Thames.', ['pub', 'river', 'historic'], '$$',
              'indoor', PUB, DRINKS),
        place('prospect-of-whitby', 'Prospect of Whitby', 'bar', 'canary-wharf', 'Wapping pub claiming to be the '
              'oldest riverside tavern in London, with a flagstone floor and a gallows on the foreshore.',
              ['pub', 'river', 'historic'], '$$', 'indoor', PUB, DRINKS),
        place('mudchute-farm', 'Mudchute Park and Farm', 'park', 'canary-wharf', 'City farm and parkland on the Isle '
              'of Dogs, with llamas and a view of the towers.', ['farm', 'animals', 'family', 'free'], 'free',
              'outdoor', ALL, DAY),
        place('third-space-canary-wharf', 'Third Space Canary Wharf', 'fitness', 'canary-wharf', 'Large luxury gym '
              'with a pool, climbing wall and classes for the towers\' office workers.', ['gym', 'pool', 'classes'],
              '$$$', 'indoor', ['solo', 'coworkers'], ['morning', 'evening']),
        place('canary-wharf-ice-rink', 'Canary Wharf ice rink', 'attraction', 'canary-wharf', 'Winter ice rink among '
              'the towers.', ['ice-skating', 'christmas'], '$$', 'outdoor', ['friends', 'date', 'family'],
              ['afternoon', 'evening'], ['winter']),
        # Stratford
        place('queen-elizabeth-olympic-park', 'Queen Elizabeth Olympic Park', 'park', 'stratford', 'The 2012 Olympic '
              'Park of rivers, wildflower meadows, playgrounds and sports venues.', ['olympics', 'running',
              'family'], 'free', 'outdoor', ALL, OPEN),
        place('london-stadium', 'London Stadium', 'stadium', 'stratford', 'The Olympic stadium, now home to West Ham '
              'United and summer concerts and athletics.', ['football', 'west-ham', 'concerts'], '$$$', 'outdoor',
              ['friends', 'family'], ['afternoon', 'evening'], ['fall', 'winter', 'spring']),
        place('london-aquatics-centre', 'London Aquatics Centre', 'fitness', 'stratford', 'Zaha Hadid\'s wave-roofed '
              'Olympic pool, open to the public at leisure-centre prices.', ['swimming', 'olympic', 'architecture'],
              '$', 'indoor', ['solo', 'friends', 'family'], ['morning', 'afternoon', 'evening']),
        place('westfield-stratford', 'Westfield Stratford City', 'shopping', 'stratford', 'Huge shopping centre by '
              'the station, with a food court, cinema and bowling.', ['mall', 'cinema', 'food-court'], '$$', 'indoor',
              ALL, OPEN),
        place('theatre-royal-stratford-east', 'Theatre Royal Stratford East', 'venue', 'stratford', 'Victorian '
              'theatre with a long tradition of new, local and diverse work.', ['theatre', 'community'], '$$',
              'indoor', ALL, ['evening']),
        place('crate-brewery', 'Crate Brewery', 'bar', 'stratford', 'Canalside brewery and pizza bar in a Hackney '
              'Wick warehouse.', ['craft-beer', 'pizza', 'canal'], '$$', 'mixed', ['friends', 'date', 'coworkers'],
              DRINKS),
        # Walthamstow
        place('walthamstow-market', 'Walthamstow Market', 'market', 'walthamstow', 'Street market running about a '
              'kilometre down the High Street, said to be the longest outdoor market in Europe.', ['market',
              'cheap', 'local'], '$', 'outdoor', ALL, DAY),
        place('william-morris-gallery', 'William Morris Gallery', 'museum', 'walthamstow', 'Free museum in Morris\'s '
              'family home in Lloyd Park, with his textiles and wallpapers.', ['design', 'free', 'arts-and-crafts'],
              'free', 'indoor', ALL, DAY),
        place('lloyd-park', 'Lloyd Park', 'park', 'walthamstow', 'Family park behind the William Morris Gallery with '
              'a moat, a skate park and a cafe.', ['park', 'family', 'cafe'], 'free', 'outdoor', ALL, OPEN),
        place('walthamstow-wetlands', 'Walthamstow Wetlands', 'trail', 'walthamstow', 'Working reservoirs opened as '
              'Europe\'s largest urban wetland, with birdwatching paths and a cafe in an old engine house.',
              ['birdwatching', 'walk', 'free'], 'free', 'outdoor', ALL, DAY),
        place('gods-own-junkyard', 'God\'s Own Junkyard', 'attraction', 'walthamstow', 'Warehouse packed with neon '
              'signs, from film sets to old shopfronts, with a cafe; open at weekends.', ['neon', 'quirky',
              'photogenic'], 'free', 'indoor', ['friends', 'date', 'family'], DAY),
        place('signature-brew', 'Signature Brew', 'bar', 'walthamstow', 'Music-themed brewery taproom by Blackhorse '
              'Road on the "Blackhorse Beer Mile".', ['craft-beer', 'music', 'taproom'], '$$', 'indoor',
              ['friends', 'coworkers'], DRINKS),
        place('nags-head-walthamstow', 'The Nag\'s Head', 'bar', 'walthamstow', 'Walthamstow Village pub with a '
              'garden and resident cats.', ['pub', 'beer-garden', 'cats'], '$$', 'indoor', PUB, DRINKS),
        # Hampstead
        place('hampstead-heath', 'Hampstead Heath', 'park', 'hampstead', 'Eight hundred acres of meadow, woods and '
              'ponds, with the city spread out below Parliament Hill.', ['views', 'woods', 'wild', 'running'],
              'free', 'outdoor', ALL, OPEN),
        place('parliament-hill-lido', 'Parliament Hill Lido', 'fitness', 'hampstead', 'Unheated 1930s lido with a '
              'stainless-steel pool, open every day of the year.', ['swimming', 'lido', 'cold-water'], '$',
              'outdoor', ['solo', 'friends', 'family'], ['morning', 'afternoon']),
        place('hampstead-heath-ponds', 'Hampstead Heath swimming ponds', 'fitness', 'hampstead', 'Three spring-fed '
              'bathing ponds, one mixed and two single-sex, swum all year by regulars.', ['wild-swimming',
              'cold-water', 'nature'], '$', 'outdoor', ['solo', 'friends'], ['morning', 'afternoon']),
        place('kenwood-house', 'Kenwood House', 'museum', 'hampstead', 'Free neoclassical mansion on the Heath with '
              'a Rembrandt self-portrait and a Vermeer.', ['art', 'free', 'historic-house'], 'free', 'indoor', ALL,
              DAY),
        place('holly-bush', 'The Holly Bush', 'bar', 'hampstead', 'Snug Georgian pub up a lane in Hampstead '
              'village, with a fire in winter.', ['pub', 'cosy', 'historic', 'sunday-roast'], '$$', 'indoor', PUB,
              DRINKS),
        place('spaniards-inn', 'The Spaniards Inn', 'bar', 'hampstead', 'Sixteenth-century inn on the edge of the '
              'Heath with a big garden, linked in legend to Dick Turpin.', ['pub', 'historic', 'beer-garden'], '$$',
              'mixed', PUB, DRINKS),
        place('la-creperie-de-hampstead', 'La Creperie de Hampstead', 'restaurant', 'hampstead', 'Street stall on '
              'the High Street selling crepes since 1980.', ['crepes', 'street-food', 'cheap-eats'], '$', 'outdoor',
              ALL, ['afternoon', 'evening'], cuisine='french'),
        # Tottenham
        place('tottenham-hotspur-stadium', 'Tottenham Hotspur Stadium', 'stadium', 'tottenham', 'Spurs\' 62,000-seat '
              'stadium on the High Road, with a single-tier south stand and NFL games too.', ['football', 'spurs',
              'matchday'], '$$$', 'outdoor', ['friends', 'family'], ['afternoon', 'evening'],
              ['fall', 'winter', 'spring']),
        place('bruce-castle-museum', 'Bruce Castle Museum', 'museum', 'tottenham', 'Free local museum in a Tudor '
              'manor house in a park.', ['history', 'free', 'local'], 'free', 'indoor', ALL, DAY),
        place('tottenham-marshes', 'Tottenham Marshes', 'trail', 'tottenham', 'Lee Valley marshes and towpaths with '
              'narrowboats, cyclists and herons.', ['nature', 'walk', 'cycling'], 'free', 'outdoor', ALL, DAY),
        place('antwerp-arms', 'The Antwerp Arms', 'bar', 'tottenham', 'Community-owned pub by Bruce Castle Park, '
              'saved by its neighbours.', ['pub', 'community', 'local'], '$', 'indoor', PUB, DRINKS),
        place('tottenham-green-market', 'Tottenham Green Market', 'market', 'tottenham', 'Weekend market of street '
              'food, produce and crafts on Tottenham Green.', ['food', 'local', 'weekend'], '$', 'outdoor', ALL,
              DAY),
        place('bernie-grant-arts-centre', 'Bernie Grant Arts Centre', 'venue', 'tottenham', 'Arts centre named for '
              'the local MP, with theatre, music and a cafe.', ['arts', 'community', 'black-british'], '$', 'indoor',
              ALL, ['afternoon', 'evening']),
        # Southall
        place('gurdwara-sri-guru-singh-sabha', 'Gurdwara Sri Guru Singh Sabha', 'temple', 'southall', 'One of the '
              'largest Sikh temples outside India, where the langar kitchen serves free vegetarian meals to anyone.',
              ['sikh', 'langar', 'free'], 'free', 'indoor', ALL, OPEN),
        place('southall-broadway', 'Southall Broadway', 'shopping', 'southall', 'High street of sari and jewellery '
              'shops, sweet centres, grocers and Bollywood music.', ['south-asian', 'saris', 'sweets'], '$',
              'outdoor', ALL, OPEN),
        place('brilliant-southall', 'Brilliant', 'restaurant', 'southall', 'Family-run Punjabi restaurant since 1975, '
              'famous for butter chicken and big celebrations.', ['punjabi', 'family-run', 'celebrations'], '$$',
              'indoor', ALL, ['evening'], cuisine='punjabi'),
        place('new-asian-tandoori-centre', 'New Asian Tandoori Centre', 'restaurant', 'southall', 'Canteen-style '
              'Punjabi grill and sweet counter on the Green, open from breakfast to late.', ['punjabi', 'cheap-eats',
              'tandoori'], '$', 'indoor', ALL, OPEN, cuisine='punjabi'),
        place('jalebi-junction', 'Jalebi Junction', 'cafe', 'southall', 'Broadway stall frying hot jalebi and '
              'serving masala chai.', ['chai', 'sweets', 'street-food'], '$', 'outdoor', ALL,
              ['afternoon', 'evening'], cuisine='indian-sweets'),
        place('southall-park', 'Southall Park', 'park', 'southall', 'Local park with a playground and sports pitches '
              'just off the Broadway.', ['park', 'cricket', 'local'], 'free', 'outdoor', ALL, OPEN),
        # Bermondsey
        place('maltby-street-market', 'Maltby Street Market', 'market', 'bermondsey', 'Weekend food market squeezed '
              'into the Ropewalk under the railway arches.', ['street-food', 'weekend', 'arches'], '$$', 'outdoor',
              ['friends', 'date', 'solo'], DAY),
        place('fashion-and-textile-museum', 'Fashion and Textile Museum', 'museum', 'bermondsey', 'Bright pink and '
              'orange museum on Bermondsey Street founded by Zandra Rhodes.', ['fashion', 'design', 'rainy-day'],
              '$$', 'indoor', ADULT, DAY),
        place('jose-tapas', 'José', 'restaurant', 'bermondsey', 'Standing-room sherry and tapas bar on Bermondsey '
              'Street.', ['tapas', 'sherry', 'small'], '$$', 'indoor', ['date', 'friends'], LUNCH,
              cuisine='spanish'),
        place('the-garrison', 'The Garrison', 'bar', 'bermondsey', 'Gastropub on Bermondsey Street with a tiny '
              'basement cinema.', ['gastropub', 'sunday-roast'], '$$', 'indoor', PUB, DRINKS),
        place('bermondsey-beer-mile', 'Bermondsey Beer Mile', 'bar', 'bermondsey', 'Craft breweries and taprooms in '
              'railway arches, best walked on a Saturday.', ['craft-beer', 'arches', 'crawl'], '$$', 'indoor',
              ['friends', 'coworkers'], ['afternoon', 'evening']),
        place('the-watch-house', 'The Watch House', 'cafe', 'bermondsey', 'Coffee shop in a tiny 19th-century watch '
              'house built to guard the churchyard against body snatchers.', ['coffee', 'historic', 'tiny'], '$',
              'indoor', ['solo', 'friends'], DAY),
        place('manze-tower-bridge', 'M. Manze', 'restaurant', 'bermondsey', 'Tiled pie and mash shop on Tower Bridge '
              'Road since 1902, the oldest still trading.', ['pie-and-mash', 'historic', 'cheap-eats'], '$',
              'indoor', ALL, DAY, cuisine='pie-and-mash'),
        # Richmond
        place('richmond-park', 'Richmond Park', 'park', 'richmond', 'The largest royal park, with red and fallow deer, '
              'oak woods and a protected view of St Paul\'s from King Henry\'s Mound.', ['deer', 'cycling',
              'views', 'royal-park'], 'free', 'outdoor', ALL, DAY),
        place('kew-gardens', 'Kew Gardens', 'garden', 'richmond', 'The Royal Botanic Gardens, with Victorian '
              'glasshouses, a treetop walkway and winter light trails.', ['gardens', 'glasshouses', 'unesco'], '$$$',
              'mixed', ALL, DAY),
        place('pools-on-the-park', 'Pools on the Park', 'fitness', 'richmond', 'Outdoor and indoor pools in Old Deer '
              'Park by the river.', ['swimming', 'outdoor-pool'], '$', 'mixed', ['solo', 'family', 'friends'],
              ['morning', 'afternoon', 'evening']),
        place('petersham-nurseries', 'Petersham Nurseries', 'restaurant', 'richmond', 'Garden centre with a '
              'glasshouse cafe and teahouse among the plants, reached across the riverside meadows.', ['garden',
              'lunch', 'special-occasion'], '$$$', 'indoor', ['date', 'friends', 'family'], ['afternoon'],
              cuisine='seasonal'),
        place('white-cross-richmond', 'The White Cross', 'bar', 'richmond', 'Riverside pub that floods at high tide; '
              'there is a door for when the water comes in.', ['pub', 'river', 'beer-garden'], '$$', 'mixed', PUB,
              DRINKS),
        place('richmond-theatre', 'Richmond Theatre', 'venue', 'richmond', 'Frank Matcham\'s 1899 theatre on the '
              'Green, for touring plays and a big panto.', ['theatre', 'panto'], '$$', 'indoor', ALL, ['evening']),
        place('twickenham-stadium', 'Twickenham Stadium', 'stadium', 'richmond', 'The home of England rugby, packed '
              'for the Six Nations and autumn internationals.', ['rugby', 'matchday'], '$$$', 'outdoor',
              ['friends', 'family'], ['afternoon', 'evening'], ['fall', 'winter', 'spring']),
        place('pembroke-lodge', 'Pembroke Lodge', 'cafe', 'richmond', 'Georgian house and tearooms in Richmond Park '
              'with a view down the Thames valley.', ['tea', 'views', 'park'], '$$', 'mixed', ALL, DAY),
    ],
    'colleges': [
        college('ucl', 'University College London (UCL)', 'research-university', 'bloomsbury', 'large',
                ['medicine', 'engineering', 'architecture', 'law', 'research']),
        college('kings-college-london', 'King\'s College London', 'research-university', 'covent-garden', 'large',
                ['medicine', 'nursing', 'war-studies', 'law', 'humanities']),
        college('lse', 'London School of Economics', 'research-university', 'covent-garden', 'large',
                ['economics', 'politics', 'social-science', 'finance']),
        college('imperial-college', 'Imperial College London', 'research-university', 'kensington', 'large',
                ['engineering', 'medicine', 'science', 'business']),
        college('queen-mary', 'Queen Mary University of London', 'research-university', 'whitechapel', 'large',
                ['medicine', 'dentistry', 'law', 'engineering']),
        college('goldsmiths', 'Goldsmiths, University of London', 'public-university', 'peckham', 'medium',
                ['art', 'music', 'media', 'design']),
        college('soas', 'SOAS University of London', 'public-university', 'bloomsbury', 'medium',
                ['languages', 'area-studies', 'development', 'politics']),
        college('city-st-georges', 'City St George\'s, University of London', 'public-university', 'islington',
                'large', ['journalism', 'business', 'nursing', 'health-sciences', 'law']),
        college('central-saint-martins', 'Central Saint Martins (University of the Arts London)', 'art-school',
                'kings-cross', 'large', ['fashion-design', 'fine-art', 'graphic-design', 'performance']),
        college('birkbeck', 'Birkbeck, University of London', 'public-university', 'bloomsbury', 'medium',
                ['evening-study', 'adult-education', 'arts', 'management']),
        college('royal-college-of-music', 'Royal College of Music', 'music-school', 'kensington', 'small',
                ['classical-music', 'composition', 'performance']),
    ],
    'employers': [
        employer('barts-health', 'Barts Health NHS Trust', 'healthcare', 'whitechapel', 'large', 'The NHS trust '
                 'running the Royal London Hospital, with its helicopter on the roof, and St Bartholomew\'s in the '
                 'City.', ['registered-nurse', 'night-nurse', 'physician-resident', 'pharmacist', 'social-worker']),
        employer('guys-and-st-thomas', 'Guy\'s and St Thomas\' NHS Foundation Trust', 'healthcare', 'south-bank',
                 'large', 'Teaching hospitals at London Bridge and opposite Parliament, among the biggest NHS '
                 'employers.', ['registered-nurse', 'night-nurse', 'physician-resident', 'pharmacist',
                 'medical-researcher']),
        employer('uclh', 'University College London Hospitals NHS Foundation Trust', 'healthcare', 'bloomsbury',
                 'large', 'UCH\'s tower on Euston Road and specialist hospitals around Bloomsbury.',
                 ['registered-nurse', 'night-nurse', 'physician-resident', 'medical-researcher', 'pharmacist']),
        employer('kings-college-hospital', 'King\'s College Hospital NHS Foundation Trust', 'healthcare', 'peckham',
                 'large', 'Major trauma and liver hospital on Denmark Hill between Brixton and Peckham.',
                 ['registered-nurse', 'night-nurse', 'physician-resident', 'social-worker']),
        employer('francis-crick-institute', 'Francis Crick Institute', 'biotech', 'kings-cross', 'large',
                 'Biomedical research institute behind the British Library.', ['medical-researcher',
                 'biotech-scientist', 'biologist', 'data-analyst']),
        employer('tfl', 'Transport for London', 'government', 'south-bank', 'large', 'Runs the Tube, buses, '
                 'Overground, DLR, Elizabeth line and roads, with offices at Palestra in Southwark.',
                 ['government-analyst', 'construction-trades', 'data-analyst', 'software-engineer']),
        employer('hsbc', 'HSBC', 'finance', 'canary-wharf', 'large', 'Global bank with its headquarters at Canary '
                 'Wharf.', ['finance-banker', 'financial-analyst', 'software-engineer', 'data-analyst',
                 'accountant']),
        employer('jpmorgan-london', 'J.P. Morgan', 'finance', 'canary-wharf', 'large', 'The bank\'s European '
                 'headquarters at 25 Bank Street.', ['finance-banker', 'financial-analyst', 'software-engineer',
                 'data-analyst']),
        employer('bank-of-england', 'Bank of England', 'finance', 'city-of-london', 'large', 'The central bank on '
                 'Threadneedle Street.', ['financial-analyst', 'government-analyst', 'data-analyst', 'accountant']),
        employer('lloyds-of-london', 'Lloyd\'s of London', 'finance', 'city-of-london', 'large', 'The insurance '
                 'market in Richard Rogers\'s inside-out building on Lime Street.', ['financial-analyst',
                 'accountant', 'data-analyst', 'paralegal']),
        employer('linklaters', 'Linklaters', 'legal', 'city-of-london', 'large', 'Magic Circle law firm on Silk '
                 'Street by the Barbican.', ['paralegal', 'accountant']),
        employer('bbc', 'BBC', 'media', 'soho', 'large', 'The national broadcaster at Broadcasting House on Portland '
                 'Place, just north of Oxford Circus.', ['journalist', 'graphic-designer', 'software-engineer',
                 'musician', 'marketing-coordinator']),
        employer('google-kings-cross', 'Google King\'s Cross', 'technology', 'kings-cross', 'large', 'Google\'s UK '
                 'offices, including the long "landscraper" with a rooftop garden, and Google DeepMind next door.',
                 ['software-engineer', 'ux-designer', 'data-analyst', 'marketing-coordinator']),
        employer('the-guardian', 'The Guardian', 'media', 'kings-cross', 'medium', 'Newspaper and website at Kings '
                 'Place by the canal.', ['journalist', 'graphic-designer', 'software-engineer', 'data-analyst']),
        employer('heathrow-airport', 'Heathrow Airport', 'logistics', 'southall', 'large', 'The UK\'s busiest '
                 'airport, a short Elizabeth line or bus ride west of Southall and a huge local employer.',
                 ['port-logistics', 'hotel-front-desk', 'retail-associate', 'construction-trades', 'server']),
        employer('hackney-council', 'Hackney Council', 'government', 'hackney', 'large', 'The borough council at '
                 'Hackney Town Hall, running housing, social care and schools.', ['government-analyst',
                 'social-worker', 'teacher', 'accountant']),
        employer('lambeth-council', 'Lambeth Council', 'government', 'brixton', 'large', 'The borough council at '
                 'Lambeth Town Hall in Brixton.', ['government-analyst', 'social-worker', 'teacher']),
        employer('civil-service-whitehall', 'The Civil Service (Whitehall)', 'government', 'soho', 'large',
                 'Government departments along Whitehall, from the Treasury to the Ministry of Defence.',
                 ['government-analyst', 'data-analyst', 'accountant', 'paralegal', 'defense-engineer']),
        employer('ucl-employer', 'UCL', 'education', 'bloomsbury', 'large', 'Faculty, research and staff jobs '
                 'across the Bloomsbury campus.', ['professor', 'graduate-student', 'medical-researcher',
                 'data-analyst']),
        employer('imperial-employer', 'Imperial College London', 'education', 'kensington', 'large', 'Research and '
                 'teaching in science, engineering and medicine in South Kensington.', ['professor',
                 'graduate-student', 'biotech-scientist', 'medical-researcher']),
        employer('the-savoy', 'The Savoy', 'hospitality', 'covent-garden', 'large', 'Grand hotel on the Strand with '
                 'the American Bar and a ballroom.', ['hotel-front-desk', 'server', 'line-cook', 'bartender',
                 'event-planner']),
        employer('selfridges', 'Selfridges', 'retail', 'soho', 'large', 'Oxford Street\'s flagship department store, '
                 'famous for its window displays.', ['retail-associate', 'fashion-assistant',
                 'marketing-coordinator', 'graphic-designer']),
        employer('national-theatre-employer', 'National Theatre', 'entertainment', 'south-bank', 'medium',
                 'Productions, workshops and front-of-house on the South Bank.', ['actor', 'performer', 'musician',
                 'event-planner', 'bartender']),
        employer('natural-history-museum-employer', 'Natural History Museum', 'education', 'kensington', 'large',
                 'Scientists, curators and visitor teams at the museum and its research collections.',
                 ['biologist', 'medical-researcher', 'tour-guide', 'event-planner']),
        employer('historic-royal-palaces', 'Historic Royal Palaces', 'tourism', 'city-of-london', 'medium', 'The '
                 'charity running the Tower of London, Hampton Court and Kensington Palace.', ['tour-guide',
                 'event-planner', 'retail-associate']),
        employer('hippodrome-casino', 'The Hippodrome Casino', 'hospitality', 'soho', 'medium', 'Casino, cabaret '
                 'and restaurants in the Victorian Hippodrome on Leicester Square.', ['casino-dealer', 'bartender',
                 'server', 'performer']),
    ],
    'career_hubs': [
        hub('square-mile', 'The City (Square Mile)', ['city-of-london'], ['finance', 'legal', 'business',
            'insurance', 'real-estate'], 'Banks, insurers, the Bank of England, Lloyd\'s and the big law and '
            'accountancy firms, packed into the old City walls.'),
        hub('canary-wharf-finance', 'Canary Wharf', ['canary-wharf'], ['finance', 'legal', 'media', 'technology',
            'business'], 'Bank headquarters, regulators and newsrooms in the Docklands towers.'),
        hub('knowledge-quarter', 'King\'s Cross and the Knowledge Quarter', ['kings-cross', 'bloomsbury'],
            ['technology', 'biotech', 'healthcare', 'education', 'media', 'creative'], 'Google, the Crick, the '
            'British Library, UCL and its hospitals within a mile of King\'s Cross.'),
        hub('tech-city', 'Shoreditch tech and creative cluster', ['shoreditch', 'whitechapel'], ['technology',
            'creative', 'media', 'business', 'hospitality'], 'Start-ups, agencies, studios and bars around Old '
            'Street and Brick Lane.'),
        hub('west-end-and-whitehall', 'West End, Whitehall and the South Bank', ['soho', 'covent-garden',
            'south-bank'], ['entertainment', 'hospitality', 'tourism', 'retail', 'government', 'media', 'creative',
            'food'], 'Theatres, hotels, restaurants, shops, broadcasters and government departments in the centre.'),
    ],
    'climate': {
        'summary': 'Temperate oceanic: mild, damp and changeable all year, with grey drizzly winters that rarely '
                   'freeze, long light summer evenings, occasional heatwaves and rain spread evenly through the '
                   'year.',
        'months': [
            month(47, 37, 11, 'Coldest month: short grey days and drizzle; snow is rare and stops the city.'),
            month(48, 36, 9, 'Cold and damp, with the first daffodils late in the month.'),
            month(53, 40, 9, 'Changeable; blossom in the parks and clocks go forward at the end.'),
            month(59, 43, 9, 'Showers and sunshine; magnolias and bluebells.'),
            month(65, 48, 8, 'Mild and green; pub gardens fill up on sunny evenings.'),
            month(71, 54, 8, 'Long light evenings until after nine; lidos busy.'),
            month(75, 58, 8, 'Warmest month; heatwaves make the Tube stifling.'),
            month(74, 57, 8, 'Warm; many locals away and the city quieter.'),
            month(68, 53, 8, 'Often a warm, settled start; back to school and work.'),
            month(60, 48, 10, 'Cooling and wetter; leaves turn, clocks go back at the end.'),
            month(53, 41, 10, 'Damp and dark by half four; fireworks and Christmas lights.'),
            month(48, 37, 10, 'Cold, grey and festive; the city empties between Christmas and New Year.'),
        ],
        'source': CLIMATE,
    },
    'annual_events': [
        event('lunar-new-year-chinatown', 'Lunar New Year in Chinatown', [1, 2], 'soho', 'Lion dances, lanterns and '
              'a parade through Chinatown and Trafalgar Square on the Sunday after the new year.'),
        event('boat-race', 'The Boat Race', [3, 4], None, 'Oxford and Cambridge crews row from Putney to Mortlake, '
              'with crowds and picnics along the riverbank.'),
        event('london-marathon', 'London Marathon', [4], 'greenwich', 'Runners start in Greenwich and Blackheath and '
              'finish on the Mall, cheered along the whole route.'),
        event('chelsea-flower-show', 'RHS Chelsea Flower Show', [5], 'kensington', 'Show gardens in the grounds of '
              'the Royal Hospital Chelsea in late May.'),
        event('trooping-the-colour', 'Trooping the Colour', [6], 'soho', 'The King\'s official birthday parade on '
              'Horse Guards, with an RAF flypast over Buckingham Palace.'),
        event('wimbledon', 'Wimbledon', [6, 7], None, 'Two weeks of grass-court tennis in south-west London, with '
              'strawberries and cream and an overnight queue for tickets.'),
        event('pride-in-london', 'Pride in London', [6, 7], 'soho', 'The parade through the West End, with Soho\'s '
              'streets partying late.'),
        event('bbc-proms', 'The BBC Proms', [7, 8, 9], 'kensington', 'Eight weeks of nightly classical concerts at '
              'the Royal Albert Hall with cheap standing tickets, ending with the Last Night.'),
        event('notting-hill-carnival', 'Notting Hill Carnival', [8], 'notting-hill', 'Europe\'s biggest street '
              'festival over the August bank holiday weekend: steel bands, sound systems, costumes and jerk '
              'chicken.'),
        event('open-house-festival', 'Open House Festival', [9], None, 'Buildings across London open their doors '
              'for free tours for two weeks in September.'),
        event('totally-thames', 'Totally Thames', [9], 'south-bank', 'A month of river events, art and walks along '
              'the Thames.'),
        event('london-film-festival', 'BFI London Film Festival', [10], 'south-bank', 'Premieres and screenings '
              'across the city, centred on BFI Southbank and the West End.'),
        event('bonfire-night-fireworks', 'Bonfire Night fireworks', [11], None, 'Fireworks displays in parks across '
              'London around the fifth of November.'),
        event('christmas-lights', 'Christmas lights on Oxford Street and Regent Street', [11, 12], 'soho', 'The '
              'West End\'s Christmas lights are switched on in November.'),
        event('winter-wonderland', 'Hyde Park Winter Wonderland', [11, 12, 1], 'kensington', 'Christmas fair with '
              'rides, ice skating, mulled wine and a big wheel, from late November into early January.'),
        event('new-years-eve-fireworks', 'New Year\'s Eve fireworks on the Thames', [12], 'south-bank', 'The '
              'midnight fireworks around the London Eye, watched by ticketed crowds along the river.'),
    ],
    'local_color': [
        color('sunday-roast', 'Sunday roast', 'dish', 'Roast beef, chicken or lamb with roast potatoes, Yorkshire '
              'pudding, vegetables and gravy, eaten at the pub on Sunday afternoon.',
              ['island-queen', 'holly-bush', 'the-garrison', 'anglesea-arms', 'cat-and-mutton']),
        color('full-english', 'Full English', 'dish', 'Fried breakfast of eggs, bacon, sausage, beans, mushrooms, '
              'tomato and toast, best at an old-fashioned "caff".', ['e-pellicci']),
        color('pie-and-mash', 'Pie and mash', 'dish', 'Minced beef pie with mashed potato and green parsley "liquor", '
              'the old East End and South London working lunch.', ['manze-tower-bridge', 'goddards']),
        color('jellied-eels', 'Jellied eels', 'dish', 'Chopped eels set in their own jelly with chilli vinegar, a '
              'Cockney classic now mostly found at pie and mash shops.', ['manze-tower-bridge', 'goddards']),
        color('fish-and-chips', 'Fish and chips', 'dish', 'Battered cod or haddock and thick chips from the chippy, '
              'with salt, vinegar and mushy peas.', ['poppies-camden']),
        color('brick-lane-curry', 'A curry on Brick Lane', 'dish', 'The East End curry night, and the Punjabi grills '
              'of Whitechapel and Southall.', ['brick-lane-curry-houses', 'tayyabs', 'new-asian-tandoori-centre']),
        color('salt-beef-bagel', 'Salt beef bagel', 'dish', 'Hot salt beef with mustard in a bagel from the '
              'twenty-four-hour bakery on Brick Lane, a late-night ritual.', ['beigel-bake']),
        color('jerk-chicken', 'Jerk chicken', 'dish', 'Smoky Jamaican jerk from oil-drum grills and Caribbean '
              'kitchens, with rice and peas.', ['fish-wings-and-tings', 'brixton-village']),
        color('builders-tea', 'Builder\'s tea', 'drink', 'Strong black tea with milk and often two sugars; offering '
              'to "put the kettle on" is how many conversations start.'),
        color('a-pint', 'A pint', 'drink', 'Lager, bitter or cask ale by the pint at the bar; there is no table '
              'service in most pubs.'),
        color('buying-rounds', 'Buying rounds', 'custom', 'In a group at the pub, each person takes a turn buying '
              'drinks for everyone, and skipping your round is noticed.'),
        color('contactless', 'Oyster and contactless', 'custom', 'Tap a bank card, phone or Oyster card on the '
              'yellow reader to get through the barriers and tap out at the end; caps keep the daily cost down. '
              'Buses take no cash.'),
        color('stand-on-the-right', 'Stand on the right', 'custom', 'On Tube escalators, stand on the right and walk '
              'on the left, and never stop at the top of one.'),
        color('tube-etiquette', 'Tube etiquette', 'custom', 'Let people off first, move down inside the carriage, '
              'take your backpack off, keep your voice down and avoid eye contact; talking to strangers is for '
              'emergencies.'),
        color('mind-the-gap', '"Mind the gap"', 'saying', 'The Underground\'s warning about the space between train '
              'and platform, so familiar it is printed on souvenir T-shirts.'),
        color('you-alright', '"You alright?"', 'saying', 'A greeting that means hello rather than a question about '
              'your health; "Yeah, you?" is the right answer.'),
        color('cheers', '"Cheers"', 'saying', 'Used for thanks, goodbye and raising a glass alike.'),
        color('rhyming-slang', 'Cockney rhyming slang', 'saying', 'A few phrases survive in everyday use: "use your '
              'loaf" (head), "telling porkies" (pork pies, lies), "have a butcher\'s" (butcher\'s hook, look).'),
        color('north-south-divide', 'North or south of the river', 'saying', 'Londoners have strong loyalty to their '
              'side of the Thames, and "I don\'t go south of the river" is a running joke.'),
        color('queueing', 'Queueing', 'custom', 'Orderly queues for buses, bars and sample sales; jumping one is a '
              'serious social offence, met with tutting.'),
        color('corner-shop', 'The corner shop', 'shop', 'Off-licences and corner shops open late for milk, crisps, '
              'cans and a meal deal; the chicken shop is its after-dark partner.'),
        color('arsenal', 'Arsenal', 'team', 'The Gunners play in red at the Emirates in north London; their rivalry '
              'with Spurs is the north London derby.', ['emirates-stadium'], ['fall', 'winter', 'spring']),
        color('spurs', 'Tottenham Hotspur', 'team', 'Spurs, in white, play at their own stadium on Tottenham High '
              'Road and loathe Arsenal.', ['tottenham-hotspur-stadium'], ['fall', 'winter', 'spring']),
        color('chelsea-fc', 'Chelsea', 'team', 'The Blues play at Stamford Bridge in west London.',
              ['stamford-bridge'], ['fall', 'winter', 'spring']),
        color('west-ham', 'West Ham United', 'team', 'The Hammers play in claret and blue at the London Stadium, '
              'with fans singing "I\'m Forever Blowing Bubbles".', ['london-stadium'], ['fall', 'winter', 'spring']),
    ],
    'prices': [
        price('wage', 'A day\'s take-home pay in a low-paid job', 100, 145, 'a day, after tax'),
        price('coffee', 'Filter coffee', 2.6, 3.6, 'a cup'),
        price('latte', 'Flat white or latte', 3.4, 4.6),
        price('cheap-lunch', 'Cheap lunch', 5, 12, 'a meal deal to a cafe lunch'),
        price('dinner', 'Mid-range dinner', 30, 55, 'for one'),
        price('beer', 'Pint of beer', 6, 8),
        price('cocktail', 'Cocktail', 12, 16),
        price('sunday-roast', 'Sunday roast at the pub', 18, 28),
        price('fish-and-chips', 'Fish and chips', 11, 17),
        price('pie-and-mash', 'Pie and mash', 5, 9),
        price('groceries', 'Groceries', 55, 85, 'a week, one person'),
        price('transit', 'Tube fare', 2.8, 3.1, 'one way in central London, contactless'),
        price('bus-fare', 'Bus fare', 1.75, 1.75, 'any single journey'),
        price('bike-hire', 'Santander Cycles hire', 1.65, 3.3, 'a ride of up to an hour'),
        price('black-cab', 'Black cab across central London', 15, 30),
        price('theatre', 'West End theatre ticket', 30, 95),
        price('movie', 'Cinema ticket', 12, 20),
        price('gym', 'Gym membership', 25, 110, 'a month'),
        price('haircut', 'Haircut', 20, 50),
    ],
    'water': [
        {'kind': 'river', 'name': 'Thames', 'width_km': 0.3, 'points': [
            [51.452, -0.320], [51.468, -0.250], [51.475, -0.215], [51.481, -0.170], [51.486, -0.126],
            [51.500, -0.121], [51.509, -0.100], [51.508, -0.060], [51.504, -0.035], [51.490, -0.030],
            [51.487, -0.010], [51.497, 0.002], [51.506, 0.030]]},
    ],
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(CITY, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
