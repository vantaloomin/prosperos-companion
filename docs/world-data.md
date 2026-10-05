# World data

[Back to the README](../README.md) · [Architecture](architecture.md) · [Life simulation API](life-api.md)

The Companion ships static facts about a few real cities so that everyday life is assembled from data
and the model only phrases it (PRD W1–W4). A companion's outing, job, commute, rent and the weather
they had are picked by deterministic code from these records. The model never has to invent a
museum, an employer or a neighbourhood, and the same inputs always give the same choice.

Built-in cities come in three kinds (`setting`):

| Setting | Cities |
| --- | --- |
| `real` | Baltimore, New York, Miami, San Diego, Las Vegas |
| `fictional` | Well-known settings that are free to ship: the Emerald City of Oz (Baum's public-domain books), London in 1895 (Conan Doyle's Holmes stories) Camelot (Malory, Tennyson and other public-domain Arthurian sources) and Ellerbrück, a fairy-tale market town drawn from Grimm, Perrault and Andersen. Settings owned by others (Gotham, Night City, Baldur's Gate) are not shipped; users can build cities like them for themselves. |
| `original` | Settings written for the Companion: Whitlock, an 1880s territorial railroad and mining town, and Calderwick, an industrial canal city with a steampunk lean. |

Users can also build their own cities (see [Building a city](#building-a-city)). `GET /api/world/cities`
lists what a workspace actually has. Each city has neighbourhoods (with approximate centres, typical rents and
housing), places (attractions, museums, parks, venues, food, bars, shopping), colleges, major
employers, career hubs, transit, monthly climate and recurring annual events. A shared catalogue
of about 45 modern careers describes schedules and themes; a city whose `era` is not `modern`
(`victorian`, `medieval`, `fantasy`, `steampunk`, `frontier`, `future`, `other`) defines its own
careers. Each city also names its `currency` and `rent_period` (`month` or `week`); rents and climate
are optional, so a setting without money (Oz) or without weather data still works.

## Where the data lives

| Path | Holds |
| --- | --- |
| `companion/world/data/cities/<id>.json` | One city. Validated against `companion/world/schema.py` on load and in the tests. |
| `companion/world/data/careers.json` | Careers with sector, schedule pattern, pay band and themes. |
| `companion/world/data/names.json` | Name banks for residents, written by `scripts/world/names.py`. |
| `companion/world/data/holidays.json` | Holiday calendars, written by `scripts/world/holidays.py`. |
| `scripts/world/<city>.py` | The source each city's JSON is written from. Edit these, then rerun them. |

Nothing needs the network at run time. Every record names a source in its city's `sources` table
with kind, title, licence and retrieval date (`GET /api/world/cities/{id}/sources`). The current
records are curated from general knowledge and released as CC0; they are a snapshot for fiction,
not listings: businesses open and close, rents are rounded typical asking ranges and coordinates are
approximate. Each loaded city gets a `data_version` (a hash of its file) that generated results
carry, so an event can record exactly which data it was built from (PRD T7).

## Python API (for the life simulation)

```python
from companion.world import catalog, generators

data = catalog.city('baltimore')            # DomainError 404 for an unknown city
catalog.resolve('Fells Point, Baltimore')   # {'city': 'baltimore', 'neighborhood': 'fells-point'} or None
catalog.places(data, kind='museum', neighborhood='mount-vernon', tag=None, good_for='date')
catalog.nearby(data, 'canton', limit=4)     # closest neighbourhoods
catalog.find(data, 'fort-mchenry')          # any record by id

generators.conditions(data, day, seed)      # typical weather for the date, with a seeded rain chance
generators.annual_events(data, day)         # recurring events usually held that month
generators.holidays(data, start, end=None)  # holidays from start to end inclusive, each with its `date`
generators.commute(data, 'canton', 'towson', mode=None)
generators.outing(data, seed=..., day=..., day_part='evening', company='date',
                  neighborhood='fells-point', home='canton', budget='$$', kinds=None, exclude=[...])
generators.meal(data, seed=..., meal='brunch', neighborhood='hampden')
generators.job(data, 'registered-nurse', seed=..., home='canton', employer=None)  # employer: a record id
generators.schedule(career, seed)           # weekly routine blocks only
generators.home(data, seed=..., bedrooms='one_bedroom', budget=1400, vibe='arts', near='mount-vernon')
generators.facts(data, neighborhood='hampden')  # short lines to ground a prompt, including local colour
generators.local_color(data, seed=..., kinds=['dish'], day=..., count=3)  # dishes, sayings, customs, teams
generators.price(data, 'pint-of-beer', seed=...)  # one amount within the city's typical range

# People: the companion's social circle and anyone else in the city.
generators.circle(data, seed=..., size=6, home='canton', age=31, career='teacher', employer=None,
                  family=None, group=None)
generators.resident(data, seed=..., role='friend', career=None, age=None, near=None, employer=None,
                    family=None, group=None, local=True)
generators.name(data, seed=..., pronouns=None, group=None, family=None)
```

**Seeds.** Choices come from SHA-256 of the seed, never from `random`, so they are identical on every
machine and Python version. Use a seed that is stable for the moment being simulated, such as the
routine slot key (`evening@2026-10-04`) plus the companion id, so a resumed batch picks the same
outing. Pass recently used place ids in `exclude` for variety.

**Results** are plain dictionaries. Every generator result includes `city`, `data_version`, `refs`
(ids of every record used) and `sources` (source ids those records cite), ready to store in an
event's generation inputs.

| Generator | Returns |
| --- | --- |
| `outing`, `meal` | `place` (full record), `neighborhood`, `day_part`, `company`, `weather` (when `day` is given), `travel` (a commute from `home` or `neighborhood`), plus `meal` for meals. `None` only when no place of the requested kinds exists. Constraints relax (day part, then company) rather than fail. Rain or extreme heat or cold strongly favours indoor places; seasonal places only appear in season. |
| `job` | Careers come from `catalog.careers_for(data)`: the shared ones for the city's era plus its own. Returns `career`, `employer` (`name`, `id`, `named`, `fit`), `neighborhood`, `schedule`, `commute` (when `home` is given). `fit` says how the employer was found: `employer` (a named employer for that career), `college` (students), `workplace` (a fitting place, such as a cafe for a barista or a tavern for a career in hospitality), `hub` (an unnamed workplace in a matching career hub) or `weak` (no matching sector in this city). Unnamed employers are described, never given invented names. |
| `schedule` | Routine blocks in exactly the character `schedule` shape of the [life simulation API](life-api.md): `work` (or `study`), `sleep`, `after-work` leisure when there is time, and `day-off` leisure. They can be passed straight to `POST /api/companion`. |
| `home` | `neighborhood`, `housing` type, `bedrooms`, `rent` within the neighbourhood's range and the budget (in the city's `currency` per `rent_period`), `rent_range`; both `null` where the setting has no rents. |
| `commute` | `mode`, `line` (transit name or `null`), `distance_km`, `minutes`; walking for short trips, a shared rail line, then a shared bus, then a car. All values are estimates. |
| `circle` | `family` (the companion's family name, given or chosen) and `people`, closest first: close friend, coworker, sibling, friend, parent, neighbor, friend, cousin, old classmate, friend, mentor, coworker (up to 12). Coworkers share the companion's `employer` (or `career` when only that is known; with neither there are no coworkers). Neighbors live in the `home` neighbourhood. Parents and siblings share the family name and heritage group; cousins do half the time. Relatives live out of town about 40% of the time. Ages sit around the companion's `age`. Names are unique within a circle. |
| `resident` | `id` (stable for the seed), `role`, `closeness` (`close`, `regular`, `occasional`), `name`, `age`, `local`, `home` (a `home` result), `job` (a `job` result with a commute from home, or `null` when retired at 67 or out of town), `schedule` (routine blocks like `job`'s; a simple retired day; `null` out of town) and `haunts` (up to three affordable cafes, bars, parks and the like near home). Feed `schedule` to the background simulation the same way as a companion's. |
| `name` | `given`, `family`, `full`, `pronouns` (`she/her`, `he/him` or `they/them`) and `group` (the heritage group drawn from). |
| `conditions` | `season`, `month`, `high_f`, `low_f`, `rain`, `note`, `typical: true` (monthly climate, not a forecast), or `None` for a city without a climate. |

**Names.** Each era has a bank of name groups (`GET /api/world/names`): modern American heritages,
Victorian Britain, a West Riding mill town, medieval England and Wales, the 1880s territories, and a
plain storybook set for fantasy. Most of a resident's family names come from the same group as the
given name; one in five come from any group in the city. Real cities weight the groups by rough
local estimates in their `names.mix` (Miami leans Hispanic and Caribbean, Baltimore Black American).
A city may set `names` to pick another `bank`, weight groups with `mix`, or add its own `groups`
(`{"feminine": […], "masculine": […], "neutral": […], "family": […]}`); a city with its own groups and no
`mix` uses only those. Weights for groups a bank lacks are ignored, so changing a city's era keeps working.

**Local colour.** Each city lists things locals eat, drink, say, root for and do (`local_color`, with
`kind` dish, drink, saying, custom, team, shop or other), with the places they are easiest to find and
the seasons they belong to. `local_color` picks a few for a seed, in season on `day`, so the model can
mention crab feasts or a ventanita coffee without inventing them.

**Prices.** Each city with money lists typical prices for everyday things (`prices`: coffee, a pint,
a fare, a week's groceries, a night's lodging) as `low`–`high` ranges in its own currency, with a
`per` note where needed. Historical settings use their own units (shillings with pence noted,
silver pennies, 1880s dollars, groschen). `facts()` includes them and `price()` picks one amount, so
the model never has to guess what something costs. Oz has no money and no prices.

**Holidays.** Each city keeps a shared calendar chosen from its era and country (`catalog.calendar_id`):
`us` for modern US cities, `us-1880s` for the frontier, `uk-victorian` for Victorian and steampunk
England, `medieval-england` for medieval settings, and none otherwise (Oz has none). A city may name
another `calendar`, `'none'`, or add its own `holidays`. A holiday has one rule: `month` and `day`, a
`month`, `weekday` (Monday 0) and `nth` (-1 for the last), or `easter` (days from Western Easter).
`kind` is `public` (most offices and schools close), `observance` (widely marked, a working day) or
`feast` (a church feast or quarter day). Moved "observed" weekdays and lunar-calendar holidays are
not included.

Weather here is climate, not a forecast. Real current conditions belong to the MCP context tools
(PRD X1–X3); a life event built from climate must not be presented as today's weather.

### The composer's world source

`companion/world/source.py` provides `CatalogWorld`, the default world source the app passes to the
life engine (`companion/life/world.py`). It answers the composer's place kinds (`park`, `cafe`,
`waterfront`, `college` and so on) from this data, in a stable order. A character's `home_city` may
be a city id (`baltimore`) or free text that `catalog.resolve` recognises.
`places(city, kinds, *, day_part=None, day=None)` leaves out places closed at that part of the day
(`morning`, `afternoon`, `evening`, `late`) or out of season on that date. User cities and packs are
included. With `near=` (a neighborhood id, or the character's `location` text such as "Fells Point,
Baltimore"), everyday kinds (`cafe`, `restaurant`, `bar`, `market`, `grocery`, `library`, `gym`,
`park`) keep to places within 3 km of that neighborhood, or the nearest three, closest first, when fewer than two
are that close. Museums, venues, beaches and attractions stay city-wide.

## HTTP API

Reads are `GET`s and need no workspace header. The [builder](#building-a-city) endpoints write and
need `x-companion-client: workspace`. Every `{id}` may be a built-in city or one of the user's.

| Endpoint | Returns |
| --- | --- |
| `/api/world/cities` | City summaries with record counts and `data_version` |
| `/api/world/cities/{id}` | The whole city record |
| `/api/world/cities/{id}/sources` | Source, licence and retrieval date for each cited source |
| `/api/world/cities/{id}/places?kind=&neighborhood=&tag=&good_for=` | Matching places |
| `/api/world/cities/{id}/conditions?day=YYYY-MM-DD&seed=` | `{"conditions": … \| null, "annual_events": […], "holidays": […]}` |
| `/api/world/cities/{id}/local-color?seed=&day=&kind=&count=` | All local colour, or a seeded pick when `seed` is given |
| `/api/world/cities/{id}/prices?item=&seed=` | `{"currency", "prices"}`, or one `price` with an `amount` when `item` and `seed` are given |
| `/api/world/cities/{id}/holidays?start=&end=` | `{"calendar": id \| null, "holidays": [… with "date"]}` (at most 400 days) |
| `/api/world/cities/{id}/careers` | Careers this city offers |
| `/api/world/cities/{id}/commute?from=&to=&mode=` | A commute estimate |
| `/api/world/cities/{id}/generate/outing?seed=&day=&day_part=&company=&neighborhood=&home=&budget=&kind=&exclude=` | `{"outing": …}` |
| `/api/world/cities/{id}/generate/meal?seed=&meal=&…` | `{"outing": …}` with `meal` |
| `/api/world/cities/{id}/generate/home?seed=&bedrooms=&budget=&vibe=&near=` | A home |
| `/api/world/cities/{id}/generate/job?career=&seed=&home=&employer=` | `employer` puts the job at that record |
| `/api/world/cities/{id}/generate/circle?seed=&size=&home=&age=&career=&employer=&family=&group=` | A social circle |
| `/api/world/cities/{id}/generate/resident?seed=&role=&career=&age=&near=&employer=&family=&group=&local=` | One person |
| `/api/world/names` | The name banks and each era's default |
| `/api/world/careers` | The career catalogue |
| `/api/world/resolve?text=` | `{"match": {"city", "neighborhood"} \| null}` for a free-text location |

## Building a city

Users' own cities are stored in the workspace database (`world_cities`), so backups carry them.
They are validated by the same schema as built-in cities and work with every generator and with
the life composer. The minimum is one source, one neighbourhood and one place.

In the app, **Settings → Cities** lists built-in, pack and user cities. From there you can start a
new city from the template, open a city file someone shared, copy any city, edit or delete your own
(as JSON, with **Check** before **Save**), save a public city as a file, and reload the pack folders.

| Endpoint | Does |
| --- | --- |
| `GET /api/world/template` | The smallest valid city, to start from scratch |
| `POST /api/world/validate` (body: a city) | `{"valid": true, …}`, or 422 with `detail` naming what is wrong |
| `POST /api/world/cities` (body: a city) | Saves a new city. 409 if the id is taken or belongs to a built-in city. |
| `POST /api/world/cities/{id}/copy` `{"id", "name"}` | Copies any city (built-in or the user's) as a new city of the user's |
| `PUT /api/world/cities/{id}` `{"definition", "expected_revision"}` | Replaces a user city; 409 when the revision is stale |
| `DELETE /api/world/cities/{id}` | Deletes a user city; 409 while the companion's `home_city` is that city |

Built-in cities cannot be changed or deleted, only copied. A user city's `data_version` is a hash
of its content, so editing it changes the version later events record.

## City packs

A city pack is one city JSON file (the same schema) dropped into a pack folder. Packs load at start,
read-only like built-in cities (copy one to edit it), and can be personal or private: a pack marked
`"distribution": "private"` is meant for its owner only, such as fan cities of settings owned by
others. Pack folders:

- `private-cities/` in the checkout (gitignored, so packs there are never committed)
- `city-packs/` in the workspace data directory (`%LOCALAPPDATA%\ProsperoCompanion\city-packs` on Windows)
- or the folders in `COMPANION_CITY_PACKS` (separated by `;` on Windows, `:` elsewhere), instead of both

`GET /api/world/packs` lists the folders, the packs loaded and any file that failed validation with
the reason; `POST /api/world/packs/reload` rereads them without restarting. A pack cannot reuse a
built-in city's id.

**Checking a city file.** `python -m companion.world.check [FILE_OR_FOLDER ...]` validates files
exactly as the app loads them, and with no arguments checks the built-in cities and every pack
folder. Errors mean the file will not load. Warnings point out thin spots that make days there
repetitive: neighbourhoods with fewer than two places or nowhere to eat, no employers or career
hubs, or no climate. `--json` prints the results for tools. It exits 1 when any file has errors,
and CI runs it.

## Adding or refreshing a built-in city

1. Copy `scripts/world/baltimore.py`, keep its two source records, and fill in the city.
2. Run it to write `companion/world/data/cities/<id>.json`, then `python -m pytest tests/test_world.py`.
   The tests validate every reference, check every career gets a job and every generated schedule
   is a valid character routine.
3. Only add places you know are open, and prefer long-running institutions to new openings.
