# Bring your characters

[Back to the README](../../README.md)

**Import a character or lorebook** on the Character page brings a character from another app into this
world in one step. There is no review screen and no model call: the character arrives, moves into town and
becomes the companion the app is about. Whoever was the main companion steps back and keeps every chat and
memory (as when a townsperson takes over, [life-api.md](life-api.md)). Everything can be changed on the
Character page afterwards.

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
- **when one of its keywords comes up** in the last four messages, as a whole word in any letter case. These
  go in the notes for that reply (`lore_now` in `NOW`, [prompts.md](prompts.md)), at most eight per reply.

Only plain primary keywords carry over, as in the Study. An entry whose keywords are search patterns (regex,
`use_regex`, or NovelAI's `&`) keeps its text but stays off: the Companion matches literal words only. Secondary
keys, insertion order and depth, probability, timed effects and recursion are not translated. Entries that were
off in the source stay off.

**Lore** on the Character page lists the open companion's books and the world's, with a switch for each book
and entry and a way to remove a book.

## API

| Request | Purpose |
| --- | --- |
| `POST /api/import/character {filename, data}` | Imports one file (`data` is base64, up to 10 MiB). Returns `format`, `companion` (or null for a lorebook), `book` (`name`, `world`, `entries`, `off`), `picture`, `stepped_back` |
| `GET /api/lore` | The open companion's lorebooks and the world's, with entries |
| `PUT /api/lore/books/{id} {enabled}`, `DELETE /api/lore/books/{id}` | Turn a book on or off, or remove it |
| `PUT /api/lore/entries/{id} {enabled}` | Turn an entry on or off; an entry with search patterns cannot be turned on |
