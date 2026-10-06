# Import from Prospero's Study

An optional, reviewed copy of one character from a Prospero's Study workspace into an empty
Companion workspace (PRD "Standalone product boundary"). It lives in `companion/imports/` and
appears as **Import from Prospero's Study** on the Character page before a companion exists.

## Steps

| Route | What it does | Writes |
| --- | --- | --- |
| `POST /api/import/study/inspect {path}` | Checks the workspace and lists its library characters | Nothing |
| `POST /api/import/study/review {path, character_id}` | Shows the mapped definition, artwork, exclusions and attribution, with a `review_token` | Nothing |
| `POST /api/import/study {path, character_id, review_token}` | Repeats the review; creates the companion only if the token still matches | Companion workspace only |
| `GET /api/import/study` | Attribution records for the current companion | Nothing |

`path` is the Study folder (holding `data/roleplay.sqlite3` or `roleplay.sqlite3`) or the database
file itself, and must be absolute. If the Study character changed after the review (a new
version, removed artwork), the import is refused with 409 and the user reviews again. If the
workspace already has a companion the import is refused with 409; it never replaces or adds a
version to an existing companion.

## Reading the Study

The database is opened with a `file:…?mode=ro` URI and `PRAGMA query_only`; no pragma that writes
is used, and `immutable=1` is not, because the Study may be running. The main database file is
never modified (tests compare its bytes and modification time). As with any SQLite reader of a
WAL database, SQLite may leave the usual `-wal` and `-shm` side files beside it.

The Study has no identity marker, so a database counts as a Study workspace when it has no
`app_identity` table, at least two of `stories`, `nodes`, `branches`, `side_threads` and
`manifests`, and the library tables below with the Study's columns. The Companion's own database,
any other Companion workspace, other SQLite files and non-database files are refused.

Only these tables are read (shape from prosperos-study `server/schema.sql` at `bbcbde4`):

- `assets` (`kind='character'`) and `asset_versions`: the character and its latest version.
- `library_media`: the artwork that version names in `artwork_sha256`.
- Row counts of `stories`, `side_threads` and `assets`, so the review can say what stays behind.

Story nodes, Sidebar threads and turns, connection profiles, preferences, backup settings and
runs, lorebooks and personas are never selected. Model credentials are in the Study's own
credential store, which the Companion never opens.

## Mapping

| Study field | Companion field |
| --- | --- |
| version name | `name` |
| `text` (Character & background) | `background` |
| `behavior_rules` (Behavior & boundaries) | `personality` |
| `voice` (Voice & manner) | `voice` |
| `pronouns`, `address` | `identity`, as "Pronouns: …" and "Form of address: …" lines |

Text longer than the Companion's limit is shortened and marked as such in the review. Not
copied and listed in the review: `scenario`, `example_dialogue`, `greetings`, `author_notes`,
`lorebook_versions` and any other key. Relationship starts as friendship and the timezone as UTC;
interests, routine, home city and emotional traits start empty. Nothing becomes a memory,
message or relationship history.

## Artwork

A Study character version names at most one artwork, stored in the database as base64 (there are
no image files on disk and no NSFW or private flags). It is included only when it belongs to the
selected version, is present in `library_media`, its bytes match the recorded SHA-256, and it is a
PNG or JPEG that the LoRA reference set accepts (64–12000 px, at most 30 MB). WebP or damaged
artwork is listed as not included with the reason. Included artwork is copied byte for byte into
the reference pictures (`lora/references/`, `lora_references`) under a new id, with rights "Not
stated" so it cannot be used for training until the user confirms the rights. Artwork of earlier
versions and other characters is never copied.

## Attribution

`study_imports` records the Study workspace and database path, the Study version (from the
folder's `pyproject.toml` when it is the Study checkout; the database records none), a
fingerprint of the table shape read, the source character id, version id and number, the name,
the review token, the field mapping, the artwork and the reference id it became, and the import
time. The first character version's note also says where it came from. Study ids are kept only
in this record; every Companion row gets a new id.
