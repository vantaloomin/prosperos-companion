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

Work already under way stays in its own world. Each request, each background tick (life, pictures, phone
notifications) and each memory drain is pinned to the world open when it began (`Database.pin`, a context variable
that every task it starts inherits), so a picture or a phrased message that comes back from a model after the switch
is stored where it was asked for, never in the world now open. Pages send the world they show
(`X-Companion-World`); a phone still showing the old world gets `409 world_changed` for anything it asks and
reloads into the new one, rather than writing into it.

## Defaults ("the world exists outside of User")

- Upgrading: the existing workspace becomes the first world, named after its city, with a persona made from the
  Matchlight profile and the birthday the user mentioned. Nothing to set up.
- A new world starts in the current city (or `city_id`) with fresh townsfolk and a starter companion: a grown-up
  townsperson picked by the world's seed, written from their town sheet with no model call (`cast.profile`), a friend
  at closeness stage 2.
- The persona is the exception: who the user is stays the user's to say (Vanta, 2026-10-09). "New persona" opens the
  persona form; the name they type is required, anything left blank stays blank, and the app makes nothing up. Their
  world is still decided for them, as above.

## Become a townsperson

`POST /api/worlds/become {key}` (Feature Hit List #43): "Become <name>" on someone the companion has met around
town (Today > Around town) starts a new life as them, after one confirm, and switches to it. It only happens when the
user picks the person; the app never puts them in someone else's shoes.

- A new world, not a second you: a new persona named after the townsperson, with their age and a gender from their
  pronouns, and a new world for it in the same city that reuses the town seed of the companion who met them, so the
  streets and townsfolk are the same. None of the user's companions come along, and the world they left waits as it
  was. They never play two people in one world.
- The persona's text starts from the person's town sheet, drafted by rules (`cast.profile`, no model call): who they
  are and their job, their street, what they are working toward, their routine ("Usually: ...") and how they come
  across. The user changes all of it like any persona. The persona keeps `townsfolk_key` and `town_seed`.
- Their circle is there: the starter companion is someone from their own usual place (a coworker, or a regular
  there), at closeness stage 3, whose background says how they know the user.
- In that world the townsperson is the user, so they are left out of the town's people: every list of townsfolk
  (people at places, residents, the Matchlight pool, the town paper, Around town) goes through one filter,
  `townsfolk.not_you`, with the user's key from `network.you`. Nobody runs into them, and Matchlight never offers
  them. `townsfolk.find` still names them, for their own persona. Townsfolk are always 18 or older.
- The page reloads into the new world's chat with a one-time line ("You're Maya now. Ines is your first companion. You can change anything about yourself in Worlds.").

## Back when

`GET /api/worlds/back-when` and `POST /api/worlds/back-when {year, from_history}` (Feature Hit List #79, 1.2 "The Dark
Backward", `companion/back_when.py`): go back to a past year with the main companion. It only starts from a world in
the present, and only goes back to years when both of them were 18 or older (never before 1990).

- The sheet offers three moments the app picked from what is stored: when you first met, the year before your latest
  step (the wedding, moving in), the year before a life chapter, and a round age of theirs ("When Mira was 25"). The
  user can pick any year in `earliest`..`latest` instead.
- Picking one makes a world named "Back when · 2009" in the same city, with the same town (their town seed comes
  with them), whose clock runs in that year (`world_year`), and switches to it. The world they left waits as it was.
- What comes along: who they are, their look, their circle, family, kids, home and love life, from their active
  timeline. What stays: chats, memories, the feed, pictures and the simulation's cursors.
- Rolled back to that day by rules (`companion/back_when_rollback.py`): later life chapters undone, people who died
  later alive, kids born later not born, partners met later not met, today's coworkers and later friends out of the
  circle, everyone younger by their birth date (anyone under 18 then leaves the circle), home items from later gone.
  Their age and the age in their own words ("34-year-old") go back too, in a new character version.
- The two of you start as strangers. "Work it out from our history" (`from_history`, off by default) keeps the steps
  reached by then instead, with dates worked out for steps written as history ("married ten years", "since college"),
  and strangers before the day you met.
- The persona is younger there by the years it goes back (the world's `back_when` row), never under 18. The worlds
  list shows `back_when: {year, name, companion_id}` for such a world.

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
