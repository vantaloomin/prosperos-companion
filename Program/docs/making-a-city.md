# Making a city

A companion's days are built from their home city: where they live, where they eat, drink and go out, where they work and study, and what the weather is doing. This guide covers what a city file needs, what makes one feel lived in, and how to ask a chatbot to write one. [world-data.md](world-data.md) is the full field reference for developers.

To add a finished file, open **Settings > Cities > Open a city file**. The [README](../../README.md#adding-your-own-cities) says where to drop files by hand.

## What a city needs to load

- **Valid JSON.** One object, `{ ... }`, saved as a `.json` file.
- **A name or an id.** With only `"name": "Port Calloway"`, the id becomes `port-calloway`. Ids use lowercase letters, numbers and dashes.
- **At least one neighbourhood** in `neighborhoods`.
- **At least one place** in `places`, each naming the neighbourhood it is in.

Everything else can be left out. When you open the file, the app fills in what's missing and fixes small mistakes, then lists everything it changed under "Along the way:". For example:

- Missing ids are made from names, and a missing region, country, timezone, coordinates, cost or time of day gets a sensible default.
- New kinds of place, school, transit line or local colour are kept as you wrote them. Words the app reasons about are read as the nearest one it knows, so "expensive" becomes `$$$`, "night" becomes `late` and "couples" becomes `date`.
- A job an employer hires for that the app doesn't have is added as one of the city's own jobs.
- A neighbourhood that a place names but that isn't listed is added. A second record with the same id is left out.
- Fields the app doesn't use are ignored.

A file opened this way never stops the rest of the app from working. If it still can't load, Settings > Cities says which file failed and why.

## What makes a city feel alive

None of these are required, but each one gives the life sim and the companion more to draw on:

| Part | What it adds |
| --- | --- |
| Food and drink in every neighbourhood | Places to grab coffee, eat out and meet friends close to home. Give places a `kind` (`cafe`, `restaurant`, `bar`, `park`, `museum`, `venue`...), a `cost` (`free`, `$` to `$$$$`), who they suit (`good_for`: `solo`, `friends`, `date`, `family`, `coworkers`) and when they're open (`day_parts`: `morning`, `afternoon`, `evening`, `late`). A place may also list up to eight named `spots` inside it (`"the café on L5"`, `"out on the roof terrace"`), used as detail; without them the app picks a few by kind. |
| `employers` and `careers` | Real jobs to have, at named workplaces. An employer lists the job ids it hires for. |
| `colleges` | Somewhere to study, with what each is `known_for`. |
| Neighbourhood rents and `housing` | What living there costs (`rent_tier`, and `rent` ranges for a studio, one and two bedrooms). |
| `climate` | Twelve months of highs, lows (°F) and rain days, so the weather fits the season. |
| `annual_events` and `holidays` | Festivals, parades and local days off, by month. |
| `local_color` | Dishes, drinks, sayings, teams and customs, so the companion can mention them without inventing them. |
| `prices` | Everyday costs (coffee, a pint, a bus fare) in the city's `currency`. |
| `transit` | Lines that neighbourhoods name, for getting around. |
| `water` | Sea, rivers and lakes for the drawn map of a city without a street map (fictional, original and private cities). A sea gives the `side` its coast faces (`north`, `south`, `east`, `west`); a river gives two or more `[lat, lon]` `points` in order; a lake gives one point, its centre. Each may have a `name` and a `width_km`. |
| `setting` and `era` | `real`, `fictional` or `original`, and `modern`, `victorian`, `medieval`, `fantasy`, `steampunk`, `frontier`, `jazz-age` (the 1920s), `future` or `other`. Real-world lookups only run for real, modern cities. |

Aim for 8 to 25 neighbourhoods with three or more places each, including somewhere to eat or drink in every one. The built-in cities have about 80 to 170 places.

## The smallest city that loads

```json
{
  "name": "Port Calloway",
  "region": "Maine",
  "country": "US",
  "timezone": "America/New_York",
  "summary": "A foggy harbour town that empties out in winter.",
  "neighborhoods": [
    { "name": "The Wharf", "summary": "Fish shacks, ferries and gulls.", "vibe": ["working-harbour"] }
  ],
  "places": [
    { "name": "Salt & Rope", "kind": "bar", "neighborhood": "The Wharf", "summary": "A sailors' bar with a stove.",
      "cost": "$", "good_for": ["friends", "solo"], "day_parts": ["evening", "late"] }
  ]
}
```

## Asking a chatbot to write one

Paste this into any capable chatbot, changing the first line:

```text
Write a city file for Prospero's Companion for: <city, era and anything you want in it>.
Reply with one JSON object only. Fields:
- name, region, country, timezone (IANA, e.g. "America/Los_Angeles"), summary, lat, lon,
  setting ("real", "fictional" or "original"), era ("modern", "victorian", "medieval", "fantasy",
  "steampunk", "frontier", "jazz-age", "future" or "other").
- sources: {"curated": {"kind": "curated", "title": "Written for this city", "license": "User content",
  "retrieved": "<today as YYYY-MM-DD>"}}; every record below has "source": "curated".
- neighborhoods (10-20): id, name, summary, vibe (1-3 words), lat, lon, rent_tier ("low", "mid", "high",
  "very-high"), rent {studio, one_bedroom, two_bedroom} as [low, high] monthly ranges, housing (e.g. "apartment",
  "rowhouse"), walkability ("low", "medium", "high").
- places (3-8 per neighbourhood, food or drink in every one): id, name, kind (cafe, restaurant, bar, park,
  museum, venue, shopping, fitness, nightlife, market, landmark...), neighborhood (an id above), summary,
  cost ("free", "$", "$$", "$$$", "$$$$"), setting ("indoor", "outdoor", "mixed"), good_for (from "solo",
  "friends", "date", "family", "coworkers"), day_parts (from "morning", "afternoon", "evening", "late").
- employers (15-30): id, name, sector, neighborhood, size ("small", "medium", "large"), summary, careers (job ids
  in kebab-case, e.g. "registered-nurse").
- colleges: id, name, type, neighborhood, size, known_for.
- climate: summary and 12 months of {high_f, low_f, rain_days}.
- annual_events: id, name, months (1-12), summary. local_color: id, name, kind ("dish", "drink", "saying",
  "custom", "team", "shop", "other"), summary. prices: id, item, low, high, per.
Use real places for a real city. Ids are lowercase with dashes and unique across the file.
```

Then open the file with **Settings > Cities > Open a city file** and read the "Along the way:" list for anything the app changed.
