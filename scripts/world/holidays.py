"""Holiday calendars for Prospero Companion. Run `python scripts/world/holidays.py` to rewrite the shipped JSON.

Each holiday has one rule: a fixed date (`month`, `day`), the nth weekday of a month (`month`, `weekday` with
Monday 0, `nth` with -1 for the last), or a number of days from Western Easter (`easter`). `kind` is `public`
(most offices and schools close), `observance` (widely marked, a normal working day) or `feast` (a church feast or
quarter day of the period).
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'holidays.json'
MON, TUE, WED, THU, FRI, SAT, SUN = range(7)


def fixed(id, name, month, day, kind, summary):
    return {'id': id, 'name': name, 'kind': kind, 'month': month, 'day': day, 'summary': summary}


def nth(id, name, month, weekday, n, kind, summary):
    return {'id': id, 'name': name, 'kind': kind, 'month': month, 'weekday': weekday, 'nth': n, 'summary': summary}


def easter(id, name, offset, kind, summary):
    return {'id': id, 'name': name, 'kind': kind, 'easter': offset, 'summary': summary}


US = [
    fixed('new-years-day', "New Year's Day", 1, 1, 'public', 'A slow day after the night before; most things closed.'),
    nth('mlk-day', 'Martin Luther King Jr. Day', 1, MON, 3, 'public', 'Federal holiday with days of service and '
        'marches; schools and government offices close.'),
    fixed('valentines-day', "Valentine's Day", 2, 14, 'observance', 'Restaurants book up; cards and flowers.'),
    nth('presidents-day', "Presidents' Day", 2, MON, 3, 'public', 'Federal holiday; government offices and many '
        'schools close, and stores run sales.'),
    fixed('st-patricks-day', "St. Patrick's Day", 3, 17, 'observance', 'Green beer, parades and crowded pubs.'),
    easter('easter', 'Easter Sunday', 0, 'observance', 'Church services, egg hunts and family brunch.'),
    nth('mothers-day', "Mother's Day", 5, SUN, 2, 'observance', 'Brunch reservations and calls home.'),
    nth('memorial-day', 'Memorial Day', 5, MON, -1, 'public', 'The unofficial start of summer: cookouts, beaches and '
        'remembrance of the war dead.'),
    nth('fathers-day', "Father's Day", 6, SUN, 3, 'observance', 'Cookouts and calls home.'),
    fixed('juneteenth', 'Juneteenth', 6, 19, 'public', 'Marks the end of slavery in the United States; festivals '
          'and cookouts.'),
    fixed('independence-day', 'Independence Day', 7, 4, 'public', 'Fireworks, cookouts and a day off.'),
    nth('labor-day', 'Labor Day', 9, MON, 1, 'public', 'The unofficial end of summer and a long weekend.'),
    fixed('halloween', 'Halloween', 10, 31, 'observance', 'Costumes, trick-or-treating and parties.'),
    fixed('veterans-day', 'Veterans Day', 11, 11, 'public', 'Federal holiday; government offices and banks close.'),
    nth('thanksgiving', 'Thanksgiving', 11, THU, 4, 'public', 'A big family meal, football and travel; most '
        'things close.'),
    fixed('christmas-eve', 'Christmas Eve', 12, 24, 'observance', 'Last-minute shopping and family gatherings; many '
          'offices close early.'),
    fixed('christmas', 'Christmas Day', 12, 25, 'public', 'Presents and family; almost everything closes.'),
    fixed('new-years-eve', "New Year's Eve", 12, 31, 'observance', 'Parties and countdowns at midnight.'),
]

US_1880S = [
    fixed('new-years-day', "New Year's Day", 1, 1, 'public', 'Calls on friends and an open house in the parlour.'),
    fixed('washingtons-birthday', "Washington's Birthday", 2, 22, 'public', 'Speeches, a ball and a day off for '
          'banks and offices.'),
    easter('easter', 'Easter Sunday', 0, 'observance', 'Church in new clothes and a big dinner after.'),
    fixed('decoration-day', 'Decoration Day', 5, 30, 'public', 'Veterans and townsfolk decorate soldiers\' graves '
          'with flowers, with a procession and speeches.'),
    fixed('independence-day', 'Independence Day', 7, 4, 'public', 'The biggest day of the year: parade, oration, '
          'races, a barbecue and fireworks.'),
    nth('thanksgiving', 'Thanksgiving Day', 11, THU, -1, 'public', 'Proclaimed each year for the last Thursday of '
        'November: church, turkey and a shooting match.'),
    fixed('christmas', 'Christmas Day', 12, 25, 'public', 'Church, a tree, presents and a big dinner.'),
]

UK_VICTORIAN = [
    fixed('new-years-day', "New Year's Day", 1, 1, 'observance', 'Not a holiday in England; Scots keep Hogmanay.'),
    fixed('lady-day', 'Lady Day', 3, 25, 'feast', 'A quarter day: rents fall due and servants\' terms change.'),
    easter('shrove-tuesday', 'Shrove Tuesday', -47, 'observance', 'Pancake day, with football in some towns.'),
    easter('good-friday', 'Good Friday', -2, 'public', 'Shops shut, hot cross buns and church.'),
    easter('easter', 'Easter Sunday', 0, 'observance', 'Church and a family dinner.'),
    easter('easter-monday', 'Easter Monday', 1, 'public', 'A bank holiday: excursion trains, fairs and Hampstead '
           'Heath crowded with day-trippers.'),
    fixed('queens-birthday', "The Queen's Birthday", 5, 24, 'observance', 'Flags, a royal salute and, in the '
          'colonies, a holiday.'),
    easter('whit-monday', 'Whit Monday', 50, 'public', 'A bank holiday: Whit walks, Sunday-school treats and '
           'excursions.'),
    fixed('midsummer-day', 'Midsummer Day', 6, 24, 'feast', 'A quarter day when rents fall due.'),
    nth('august-bank-holiday', 'August Bank Holiday', 8, MON, 1, 'public', 'The first Monday in August: seaside '
        'trips, crowded trains and fairs.'),
    fixed('michaelmas', 'Michaelmas', 9, 29, 'feast', 'A quarter day; goose for dinner and hiring fairs.'),
    fixed('bonfire-night', 'Guy Fawkes Night', 11, 5, 'observance', 'Bonfires, guys carried through the streets '
          'and fireworks.'),
    fixed('christmas', 'Christmas Day', 12, 25, 'public', 'Church, a goose or a joint, plum pudding and family.'),
    fixed('boxing-day', 'Boxing Day', 12, 26, 'public', 'A bank holiday: Christmas boxes for tradesmen and '
          'servants, and the pantomime season opens.'),
]

MEDIEVAL = [
    fixed('twelfth-night', 'Twelfth Night', 1, 5, 'feast', 'The last night of Christmas: a bean in the cake makes a '
          'king for the evening.'),
    fixed('epiphany', 'Epiphany', 1, 6, 'feast', 'The end of the twelve days of Christmas.'),
    nth('plough-monday', 'Plough Monday', 1, MON, 2, 'observance', 'Ploughboys drag a decorated plough round the '
        'town begging for pennies before work starts again.'),
    fixed('candlemas', 'Candlemas', 2, 2, 'feast', 'Candles blessed in church and carried in procession.'),
    easter('shrove-tuesday', 'Shrove Tuesday', -47, 'feast', 'Feasting, cock-throwing and football before Lent.'),
    easter('ash-wednesday', 'Ash Wednesday', -46, 'feast', 'Lent begins: no meat until Easter.'),
    fixed('lady-day', 'Lady Day', 3, 25, 'feast', 'The Annunciation and the start of the year; a quarter day.'),
    easter('palm-sunday', 'Palm Sunday', -7, 'feast', 'Procession with yew and willow for palms.'),
    easter('good-friday', 'Good Friday', -2, 'feast', 'Creeping to the cross; a day of fasting.'),
    easter('easter', 'Easter Day', 0, 'feast', 'Lent ends: meat, eggs and ale, and a day free of work.'),
    easter('hock-monday', 'Hock Monday', 8, 'observance', 'The women of the town rope the men and let them go for a '
           'forfeit; the men return the favour next day.'),
    fixed('may-day', 'May Day', 5, 1, 'observance', 'Bringing in the may at dawn, a maypole and dancing.'),
    easter('ascension', 'Ascension Day', 39, 'feast', 'Beating the bounds of the parish.'),
    easter('whitsun', 'Whitsunday (Pentecost)', 49, 'feast', 'A great feast; the king holds court and church ales '
           'are brewed.'),
    fixed('midsummer-eve', "St John's Eve", 6, 23, 'feast', 'Bonfires on the hills and watch fires in the town.'),
    fixed('lammas', 'Lammas', 8, 1, 'feast', 'Loaf-mass: bread from the first wheat blessed in church.'),
    fixed('michaelmas', 'Michaelmas', 9, 29, 'feast', 'Rents and reeves\' accounts due, and a goose for dinner.'),
    fixed('all-hallows', 'All Hallows', 11, 1, 'feast', 'Bells rung for the dead through the night before.'),
    fixed('martinmas', 'Martinmas', 11, 11, 'feast', 'Beasts slaughtered and salted for winter; a feast of fresh '
          'meat.'),
    fixed('christmas', 'Christmas Day', 12, 25, 'feast', 'Twelve days of feasting, games and no work in the fields.'),
]

HOLIDAYS = {
    'schema_version': 1,
    'source': {'kind': 'curated', 'title': 'Holiday calendars written for Prospero Companion', 'license': 'CC0-1.0',
               'retrieved': '2026-10-05',
               'note': 'Public holidays and observances from general knowledge. Moved weekend dates ("observed" '
                       'days) and religious holidays on lunar calendars are not included.'},
    'calendars': {
        'us': {'name': 'United States (current)', 'holidays': US},
        'us-1880s': {'name': 'United States in the 1880s', 'holidays': US_1880S},
        'uk-victorian': {'name': 'England in the 1890s', 'holidays': UK_VICTORIAN},
        'medieval-england': {'name': 'Medieval England', 'holidays': MEDIEVAL},
    },
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(HOLIDAYS, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
