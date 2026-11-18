# Story

The **Story** tab is the user's own free-form story: they play themself in one of the cities, and a
narrator describes the place and voices the people there. When the story is where a companion is at
that hour, they are in the scene and speak for themselves ([Companions in the scene](#companions-in-the-scene)).
The story has its own tables (`story_scene`, `story_messages`, `story_cast`). A companion's chat never
reads them, and nothing said in the story is saved to their memories or changes their life.

## Part of every world

The Story is a normal part of the app since 1.5: its tab is always in the side rail and the phone's tab bar,
with or without a companion, and there is no switch for it. It makes a model call only when the user plays, as
chat does. A story with nothing in it yet opens on one line saying what it is and one button; the box below
takes any other first line. With no companion the line is "Your own story in Baltimore, told by a narrator."
and the button is Look around, which says "I look around." for the user. With a companion whose day has them
somewhere the story can go, the line is "Play out a scene with Mira, anywhere in Baltimore." and the button is
Find Mira: it moves the story to where they are and says "I look around for Mira." When they are at home or
asleep the line says so ("Mira isn't out right now.") and the button is Look around. The dating app is its own
feature.

## Who decides what

The app decides the scene, the same way the life sim decides the companion's day
(`companion/story.py`):

- **Where:** the city and place the user picked under "Go somewhere else…". A new story starts in
  the companion's city (Baltimore without one) at its first cafe. Moving adds a line to the story
  ("You arrive at …") that the narrator sees as a note.
- **When:** the app clock (debug time included) in the city's own timezone.
- **Weather:** the city's typical weather for the date (`generators.conditions`).
- **Who is there:** the townsfolk rules at that moment (`encounters.present`): people seeded at the
  place and residents whose routines bring them there. These are the same people the companion's
  world has. When the story is in the companion's city, it uses the companion's own town seed and
  family names, so a name means the same person in both.
- **Which companions are there:** each companion's own day (`companion/story_cast.py`, below). They are
  never placed by the townsfolk rules and the narrator never voices them.

The narrator model only voices the scene. Its prompt is "The Story narrator" in Settings > Advanced
(`NARRATOR`, [prompts.md](prompts.md)), followed by a `## Scene` section with the facts above. The
narrator gets the names of the people present, with a rule not to use a name until that person
gives it. The screen lists them only as the user would see them ("the barista", "a
regular").

The narrator stays in the story as companions do. Sentences saying it is an AI are dropped
(`in_character.Guard`), and OOC: or ((…)) gets a plain answer. Its model is the **Story narrator**
job in Settings > Models, which is the conversation profile unless another is chosen.

## Companions in the scene

When the story is where a companion is at that hour, they are there (`companion/story_cast.py`). Rules
decide it from their own day, for the main character and for companions who stepped back alike
(`place_now`): during a shift they are at the place they work, otherwise at the city place the slot of
their agenda happens at, or one their block names ("Training yard"). Asleep, off sick, at home or anywhere
the city has no place for, they are not in the story. The user cannot summon them: the story goes to
where they are.

- **On screen:** they are named first in who is around ("Mira and the barista are here."). A line in the
  story says when one comes or goes ("Mira is here.", "Mira has gone."). The people list shows every
  companion with where they are now and "Go to Mira" when that is somewhere the story can go.
- **Who answers:** the narrator's reply comes first, then each companion in the scene in their own line,
  shown under their name. Each is one ordinary model call with the conversation's text model, the group
  chat way: the scene rules ("Companions in the Story" in Settings > Advanced), the scene and the story
  since they came in, the same for every speaker, then their own 1:1 sections with one "This scene"
  section (where they are and why, who came to whom), then the turn. They talk in person: the texting
  habits go, as on an outing. A line that names only someone else in the scene ("Dana, could I get the
  bill?") is not theirs to answer, and neither is a message out of the story (OOC).
- **What they know:** a companion reads the story only from the line they came in at (`story_cast`
  keeps it), never what was said before or somewhere else. Going somewhere else or starting a new story
  leaves them behind.
- **The narrator** is told who speaks for themself: in the scene, with a line to keep its own part
  short, and again after the user's latest line. It reads a companion's lines under their name.
- **Leaving:** when their day moves on (the shift ends) they go with the next line. Someone the user is
  in the middle of talking with stays up to 45 minutes after the scene's last line (`LINGER`).
- **Failures:** a companion's line that fails is shown as such; Try again writes only what failed and
  keeps the rest. With nothing failed it tells the whole reply again.

The wording was chosen by A/B on ten models (`/mnt/project-files/companion-story-cast-ab/report.md`):
without it the narrator wrote the companion's words in 50 of 85 replies, with it in 0 of 87.

Nothing in a scene is saved for the companion yet: no memory, no closeness, no line in their chat.

## API

| Request | Does |
| --- | --- |
| `GET /api/story` | `{scene, messages, people, companions, ready, can_switch}`. `people` are those met, newest first, with `meetings`, `notes`, `doing` and `place` now. `companions` are every companion, the main one first, with `here` (in the scene) and `place` now (null when the story cannot go to them). `scene` has the city, place, `local_time` (city clock, no offset), `weather`, the city's `places`, `around` (who is there, named only once met; companions first) and `companions` (those in the scene). A message's `role` is `user`, `narrator`, `scene`, `companion` (with `speaker` and `name`) or `cast`. `ready` is false without a model. |
| `PUT /api/story/scene` `{city_id, place_id?}` | Moves there; a city alone means its opening place. 404 for an unknown city or place. |
| `POST /api/story/messages` `{text, client_id}` | Saves the user's line once per `client_id` and returns `{message, reply, replies}`: `reply` is the narrator's, `replies` all of them in order, a companion's own lines after it. A failed reply is saved with `status: failed` and its `error`. Sending the same `client_id` again returns the saved replies and writes only what is missing. 409 `no_connection` without a model; the line stays saved. |
| `POST /api/story/find` `{key}` | Moves the story to where someone the user has met is now, or a companion (`companion:<id>`). 404 if not met, 409 if they are nowhere the story can go. |
| `POST /api/story/retry` | Writes again what failed in the replies to the latest user line; with nothing failed, tells them all again. |
| `DELETE /api/story` | Starts a new story: the history and the people met go, the scene stays. |

Start over and Delete character keep the story (it is in `start_over.WORKSPACE`).

## People you've met

Someone present in the scene is met once their name comes up, either because the narrator voices them
giving it or because the user uses it (`companion/story_people.py`, table `story_people`). Each local day
they come up counts as one meeting. Up to eight sentences of narration that name them are kept as
notes. The next time they are in the scene, the narrator is told the user has met them, how often and
when, along with the latest notes, so they remember the user however far back the story has been
trimmed. The screen then shows their given name ("Dana, the barista").

The list is the user's alone. It is not the companion's `townsfolk_encounters`, and a townsperson keeps no
memories of their own. Under "People you've met" each person shows how often the user has met them and
what their rules have them doing now. "Go to …" moves the story to where they are (refused while they
are at home, at work elsewhere or on their street). "Make … the main character…" opens the usual switch
(`companion/cast.py`). `cast.townsperson` accepts anyone met in the story, in any city, and their
profile says "Has met the user in person …".

Other features that put the user with someone (a date, say) record the meeting with
`story_people.meet(connection, sheet, city_id, now, local_day, notes)`.

Starting a new story clears the people met too. Companions are not in this list's table: they are listed
above it from their own days.

## Planned

- Narrator-played dates with a dating-app match. The dating app itself is a
  standalone feature for finding new companions.
