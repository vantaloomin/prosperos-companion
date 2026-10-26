# Bring your characters

[Back to the README](../../README.md)

**Import a character or lorebook** on the Character page brings a character from another app into this
world. No model is asked: the character arrives, moves into town and becomes the companion the app is about.
Whoever was the main companion steps back and keeps every chat and memory (as when a townsperson takes over,
[life-api.md](life-api.md)). Everything can be changed on the Character page afterwards.

## Choosing what to import

Before anything is saved, the page lists what the file holds (`POST /api/import/character/inspect`): the
character, their picture, their lorebook entry by entry, and the parts left out. Everything starts ticked, so
**Import** brings it all in one click. Unticking a part leaves it out (`pick` on `POST /api/import/character`):

- **Only the lorebook**: untick the character. The lorebook goes to everyone in this world, or to a companion
  you already have, chosen under **Whose lore**.
- **Some entries**: **Choose entries** lists them with when each comes up; the unticked ones are left out.
- **The character without their lorebook or picture**: untick those.
- **Whose lore**: the new character by default; a character's lorebook can go to the whole world or to another
  companion instead. What did not fit their background (below) stays theirs either way.

A character who is already one of your companions (by name) starts unticked, and their lorebook goes to them,
so importing the same file again adds lore rather than a second copy. A Marinara world map picked here lists its
city and its places' notes the same way (`/api/world/import/marinara/inspect` and `/picked`); notes brought
without their city are lore for the whole world, and a map that already came in has its city unticked.

## What it reads

The same range as Prospero's Study's library import (`prosperos-study` at `bbcbde4`,
`server/library_formats/`); see [Development](development.md#code-reused-from-prosperos-study).

| File | From | Read as |
| --- | --- | --- |
| Character Card V1, V2, V3 (`.json`, or `.png` with the card inside) | SillyTavern, Chub, Agnai, RisuAI, most card sites | A character, with its own lorebook (`character_book`) |
| CHARX (`.charx`) | RisuAI and others (Character Card V3 in a ZIP) | A character, its lorebook and its `icon` picture |
| Backyard Archive (`.byaf`) | Backyard AI | A character: persona, the first scenario's example messages, lore items, picture |
| Pygmalion JSON (`char_name`, `char_persona`) | Pygmalion | A character |
| Backyard / Faraday legacy JSON (`aiName`, `aiPersona`) | Faraday | A character |
| World info (`entries` as an object) | SillyTavern | A world lorebook |
| Character Card V3 lorebook (`spec: lorebook_v3`) | Card editors, SillyTavern | A world lorebook |
| Lorebook (`lorebookVersion` 3 to 6, `.lorebook` or `.json`) | NovelAI | A world lorebook |
| Memory book (`kind: memory`) | Agnai | A world lorebook |
| Lorebook (`type: risu`, `ver: 1`) | RisuAI | A world lorebook |
| A card's lorebook saved on its own (`entries` with `keys` and `content`) | Card editors | A world lorebook |

ZIP files (CHARX, BYAF) are opened with the Study's checks: at most 256 files, 10 MiB each and 32 MiB in all,
no paths that leave the archive, no links, no encryption. Pictures that live on the web are never fetched;
nothing in a file runs (scripts, regex, macros other than `{{char}}` and `{{user}}`).

## What the character becomes

| From the file | Becomes |
| --- | --- |
| Name | Their name (a nameless card gets one from the city, as any new companion does) |
| Description | Background; past 12,000 characters, the rest is an always-on lore entry |
| Personality | Personality |
| Example messages | Voice ("How they write, from their examples") |
| Lorebook | Their lorebook |
| Picture (PNG card, CHARX icon, BYAF image) | A reference picture, rights "Not stated" ([lora.md](lora.md)); PNG and JPEG only |

`{{char}}` becomes their name and `{{user}}` "the user". The world gives the rest ("The world exists outside of
User"): a grown-up townsperson's sheet, picked by the character's name (and the pronouns their description
uses), lends a job, a neighborhood, a weekly schedule, a routine, interests and the city's timezone
(`companion/imports/characters.py`, `cast.profile`). The same card always gets the same life in the same town.
The townsperson stays in town as themselves; the sheet is only a template. Relationship and closeness start
at the defaults (friendship, just met).

Not used: the scenario, greetings and creator's notes, which set up someone else's story (the companion's life
starts here), and a card's system prompt or post-history instructions.

## Lore

A lorebook that came with a character belongs to that companion; one imported on its own belongs to the whole
world, so every companion in it uses it. Lore lives in the world's database (`lore_books`, `lore_entries`) and
goes when its companion is deleted.

An entry joins a reply (`companion/lore.py`):

- **always**, when the source marked it always on (`constant`, NovelAI `forceActivation`, RisuAI
  `alwaysActive`). These sit in the system prompt (`lore` in `HEADINGS`), so they stay cacheable;
- **when one of its keywords comes up** in the last four messages, as a whole word in any letter case, or
  **when the moment fits its "when"** (below). These go in the notes for that reply (`lore_now` in `NOW`,
  [prompts.md](prompts.md)), keyword entries first, at most eight per reply.

### Lore that fits the moment

An entry can also say when it applies (`companion/lore_moments.py`), as conditions `kind:value`: the weather
(`weather:rain`, `snow`, `heat`, `fog`), the season (`season:spring` ... `season:winter`), the time of day
(`time:morning` from 5:00, `afternoon` from 12:00, `evening` from 17:00, `night` from 21:00), `day:weekday` or
`day:weekend`, one of the city's holidays or observances (`holiday:Christmas Day`), a neighbourhood or place of the
city (`place:hampden`) and being on a work shift (`work:yes`). Conditions of one kind are alternatives; different
kinds all have to hold, so rain and night means rainy nights. An entry with keywords and a "when" joins a reply
when either holds. Always-on entries have no "when".

The app reads the moment as Today does: the day's weather (observed when looked up, else typical; snow is a wet day
at or below 30°F at night, heat a high of 88°F or more, fog a dry day in a month whose climate note names fog or
mist), the city's calendar, and where the companion is in their day (their current agenda entry's place and
neighbourhood, or their home's neighbourhood). Aboard a ship or station there is no weather or Earth season, so
those never hold there and the pickers leave them out; night is ship's night. Rules only: no model picks anything.

An imported entry gets a "when" by rule only from keywords that are themselves a moment: a season (not "fall",
which is a verb too), a weather word, a part of the day, weekend or weekday, or one of the city's holidays by name.
Only one kind is read, the first found, so "winter" and "rain" means winter, not rainy winter days. While the user
has not changed it, this is read again each time (`lore_entries.moment` is NULL), so it follows a move to a city
with other holidays; the Lore screen marks it "Read from its keywords". Changing it stores the user's own.

### Lore that comes with a city

A city file can carry a `lore` block ([making-a-city.md](making-a-city.md)). Its entries are the world's lore
while the companion lives in that city: read from the city each time, so they follow it into every world, and
`city_lore_choices` keeps what the user switched off or changed in this world. The book is listed as "<City> lore"
("Comes with the city") and can be switched off but not removed. The built-in moment lore lives beside the city
files in `world/data/city_lore/<id>.json`, one file per city, merged when the city loads.

Only plain primary keywords carry over, as in the Study. An entry whose keywords are search patterns (regex,
`use_regex`, or NovelAI's `&`) keeps its text but stays off: the Companion matches literal words only. Secondary
keys, insertion order and depth, probability, timed effects and recursion are not translated. Entries that were
off in the source stay off.

**Lore** on the Character page lists the open companion's books, the world's and their city's, with a switch for
each book and entry, a way to remove an imported book, and each entry's moments: chips to take one off and a picker
to add one (no free text). An entry whose moment holds right now says "Fits right now".

## Taking a companion to another world

**Take them to another world** on the Character page (**Save Spock to a file**) saves a companion with
everything that happened between you, as a `.companion` file (`GET /api/export/companion/{id}`,
companion/carry.py). Opening that file with **Import a character or lorebook** in another world
brings them there straight away, with nothing to pick (`POST /api/export/companion`, the file as the body):

- **What comes along** is what Delete would remove (companion/start_over.py `CHARACTER` and `HISTORY`): every
  character version and timeline, the chats with their pictures and voice notes, memories, the feed, Closeness,
  relationship steps, kids, their circle, home, wardrobe, hobbies and the rest of their life, their look (reference
  pictures and character sheets) and voice.
- **What stays behind**: queued work (memory jobs, notifications, unread marks, held replies), real-world lookups
  made for the old world's city, the observer's notes, and LoRA training and trained adapters, which run to
  hundreds of megabytes each. A row pointing at something left behind loses that pointer, or stays behind with it.
- **They become the main character**, as an imported character does; whoever was steps back with everything.
- **In another city they move there**, as a companion moving to the user's city does (companion/life/moving_in.py):
  a new character version with that city's clock, the same job there or one like it, and a neighborhood; a new
  home from today; coworkers stay at the old job, and friends and family stay in the old city. Who they are
  stays as written. A companion without a home city of their own lives wherever the world is.
- **The same companion twice** is turned away ("already live in this world").

This is also how a companion survives a fresh world, for example one built from an updated city pack. To keep the
same world instead, open the updated city file under Settings > Life & cities: when its id matches one of your
cities, it updates that city in place ([making-a-city.md](making-a-city.md)).

## API

| Request | Purpose |
| --- | --- |
| `POST /api/import/character {filename, data}` | Imports one file (`data` is base64, up to 10 MiB). Returns `format`, `companion` (or null for a lorebook), `book` (`name`, `world`, `entries`, `off`), `picture`, `stepped_back` |
| `GET /api/export/companion/{id}` | A companion saved with their history, as a `.companion` zip (`manifest.json`, `rows.json`, `files/`) |
| `POST /api/export/companion` | Opens a saved companion in this world (the file as the body, up to 4 GiB). Returns `companion`, `name`, `moved_to`, `stepped_back`, `counts`, `left_out` |
| `GET /api/lore` | The open companion's lorebooks and the world's, with entries |
| `PUT /api/lore/books/{id} {enabled}`, `DELETE /api/lore/books/{id}` | Turn a book on or off, or remove it |
| `PUT /api/lore/entries/{id} {enabled}` | Turn an entry on or off; an entry with search patterns cannot be turned on |
