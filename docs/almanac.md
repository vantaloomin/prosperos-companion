# The built-in calendar (almanac)

`companion/almanac/` tells the companion what a person living in their city knows about the date
without reading any news. It's computed from bundled data, so it needs no network and no model work.

- **Holidays** come from the world data (`companion/world/data/holidays.json`), which also decides days off.
- **Observances and seasons** for cities on the modern US calendar are in
  `companion/almanac/data/observances.json`. They cover days like Super Bowl Sunday, the clock changes,
  Black Friday and Lunar New Year, and seasons like Pride Month, tax season, back-to-school, and the
  NFL, MLB, NBA and NHL seasons. A rule uses the world's holiday rule shapes, the id of a world
  holiday plus `days`, or a `dates` table by year. Lunar and lunisolar dates are listed through 2030,
  and Islamic dates are approximate.
- **The city's own seasons** (a team's season, from its annual events) come from the city data.
- **Daylight and the moon** come from `sky.py`, which uses NOAA's solar equations for sunrise and
  sunset (accurate to a minute or two) and mean synodic months for the moon's phase (accurate to
  within a day).

The chat context has one section, "The calendar where you live". It lists today's holiday or
observance, what's coming within three weeks, what's going on now, and daylight and the moon phase.
For modern US cities it also reminds the model that this is a calendar and not news, so it must not
make up recent scores, headlines or releases.

The life simulation gets the day's parties (Halloween parties, Super Bowl watch parties, New Year's
Eve parties) as annual happenings, so a free evening can go to one the way it can go to a festival.
