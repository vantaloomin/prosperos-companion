# Worlds and personas

A **persona** is the user as someone in particular: a name, gender, age, birthday and a few lines about them. A
**world** is everything that happened to one persona there: companions, their lives and town, chats, memories, the
feed, pictures and voice notes. Each persona has one or more worlds. Two worlds can share a city: each seeds its own
townsfolk (`companions.town_seed`), so the same streets hold different people.

## Where things live

- Each world is its own workspace database in its own folder. The first world keeps the data folder's own
  `companion.sqlite3` (`Database.root`, `Database.home`); every other world is `worlds/<id>/companion.sqlite3`, with
  its own `images/`, `pictures/`, `voice-notes/`, `lora/` and `backups/` beside it.
- `worlds.json` in the data folder lists personas and worlds and which world is active (`companion/worlds.py`). It
  is written whole and swapped in.
- Shared by every world, in the data folder: downloaded models (`voice/`, `embeddings/`), logs, city packs and
  `worlds.json`.
- Each world's `persona` table holds the persona it belongs to, copied from `worlds.json` whenever the world opens
  or the persona changes. The prompt's "Who the user is" section (`companion/memory/context.py`) and Matchlight's
  profile prefill read it there. The birthday is kept in `life_settings.user_birthday`, where chat already saves it,
  and read back into the persona when the user leaves the world.

## Switching

`POST /api/worlds/{id}/switch` (or `/api/worlds/personas/{id}/switch`, the persona's most recent world) waits for
nothing: it refuses while a reply is being written, a LoRA trains or debug time is on. It checkpoints the current
database, points the app's one `Database` at the other file (`Database.use`), carries the user's settings across
(`worlds.SHARED`: restore's kept settings minus debug time, plus the user's own cities), moves the world's revisions
forward, writes the persona, and recovers half-finished work as a start does. The interface reloads into the chat.
Only the active world runs in the background; the others catch up when the user returns, as after any break.

## Defaults ("the world exists outside of User")

- Upgrading: the existing workspace becomes the first world, named after its city, with a persona made from the
  Matchlight profile and the birthday the user mentioned. Nothing to set up.
- A new world starts in the current city (or `city_id`) with fresh townsfolk and a starter companion: a grown-up
  townsperson picked by the world's seed, written from their town sheet with no model call (`cast.profile`), a friend
  at closeness stage 2.
- A new persona takes the current persona's gender and age, a name from the city's names, and a world of their own.

## Deleting

A world can be deleted unless it is active or the first world (which holds the others; Start over empties it). A
verified backup goes to `backups/deleted-worlds/` in the data folder first. A persona goes with all its worlds,
unless it is active or owns the first world.

## Automatic backups

`companion/auto_backup.py` backs up every world on its own while the app runs: daily by default
(`workspace_settings.auto_backups`: `daily`, `weekly` or `off`, Settings > Backups), first a couple of minutes after
a start, then checked every 15 minutes. A world unchanged since its last automatic backup is skipped. Archives go
to the world's own `backups/` as `auto-YYYYMMDDTHHMMSS.zip`, without reference pictures; the newest of each of the
last 7 days with one and of each of the 4 weeks before are kept. It never calls a model and waits while a reply is
being written.
