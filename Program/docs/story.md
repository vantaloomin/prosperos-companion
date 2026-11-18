# Story

The **Story** tab is the user's own free-form story: they play themself in one of the cities, and a
narrator describes the place and voices the people there. It is apart from every companion. The
story has its own tables (`story_scene`, `story_messages`), and no companion prompt reads them, so
nothing said in the story reaches the companion's chat, memories or life.

## Part of every world

The Story is a normal part of the app since 1.5: its tab is always in the side rail and the phone's tab bar,
with or without a companion, and there is no switch for it. It makes a model call only when the user plays, as
chat does. A story with nothing in it yet opens on one line saying what it is and a Look around button, which
says "I look around." for the user; the box below takes any other first line. The dating app is its own feature.

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
  family names, so a name means the same person in both. Companions are never in the story, including
  ones who stepped back.

The narrator model only voices the scene. Its prompt is "The Story narrator" in Settings > Advanced
(`NARRATOR`, [prompts.md](prompts.md)), followed by a `## Scene` section with the facts above. The
narrator gets the names of the people present, with a rule not to use a name until that person
gives it. The screen lists them only as the user would see them ("the barista", "a
regular").

The narrator stays in the story as companions do. Sentences saying it is an AI are dropped
(`in_character.Guard`), and OOC: or ((…)) gets a plain answer. Its model is the **Story narrator**
job in Settings > Models, which is the conversation profile unless another is chosen.

## API

| Request | Does |
| --- | --- |
| `GET /api/story` | `{scene, messages, people, ready, can_switch}`. `people` are those met, newest first, with `meetings`, `notes`, `doing` and `place` now. `scene` has the city, place, `local_time` (city clock, no offset), `weather`, the city's `places` and `around` (who is there, named only once met). `ready` is false without a model. |
| `PUT /api/story/scene` `{city_id, place_id?}` | Moves there; a city alone means its opening place. 404 for an unknown city or place. |
| `POST /api/story/messages` `{text, client_id}` | Saves the user's line once per `client_id` and returns `{message, reply}`. A failed reply is saved with `status: failed` and its `error`. Sending the same `client_id` again returns the saved reply, or tries again if it failed. 409 `no_connection` without a model; the line stays saved. |
| `POST /api/story/find` `{key}` | Moves the story to where someone the user has met is now. 404 if not met, 409 if they are nowhere the story can go. |
| `POST /api/story/retry` | Tells the reply to the latest user line again, replacing the one there. |
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

Starting a new story clears the people met too.

## Scenes count

Time the user spends with a companion in the Story is part of their life together (`companion/story_visits.py`,
table `story_visits`). A visit is one stretch of the story with a companion in the scene. It opens with the
user's first line while they are there. It ends when the user goes somewhere else or starts a new story, when the
companion's day takes them away, or when nothing has been said for two hours. Everything here is rules, with no
model call:

- **Closeness:** a day the user talked with them in person counts as a day talked, the same as a day of texting
  (`closeness.talk_days`). A day with both still counts once.
- **A shared moment:** a visit with a real exchange (two of the user's lines to them and one of their own) leaves
  one memory, "In person at Club Charles: Mira and you spent time together at Club Charles." There is at most one
  a day for each companion, and one for each place: time at the same place again is the same moment. Its card on
  Memories says "In Story" and the date (`in_story` on `GET /api/memories`). It also shows in the scrapbook and in
  "Our history", and counts toward closeness as any shared moment does.
- **Relationship steps:** what the user says to them is read by the step rules chat uses
  (`steps.said_in_person`). The user can bring a step up ("I think we should be exclusive") or answer one the
  companion brought up. The words in quotation marks are the speech. With no chat turn to go by, an answer counts
  only when it names the step, or is a plain yes or no right after the companion's own line named it. The
  companion's line in the scene is written knowing the answer. Starting a family and separating stay with chat.
- **Their chat afterward:** for a day and a half, the 'where' section of their 1:1 chat says when and where they
  were together, who came to whom, and the last six lines the two of them said (`story_visits.context_lines`).
  After that it is the memory.

A line to someone else in the scene, or one out of the story (OOC: or ((...))), counts for nothing. A new story
clears the lines but not the time spent: visits are settled before the lines go.

Settings > Realism > "Story scenes count" (`life_settings.story_counts`, on by default) turns all of it off. The
story is then apart from the companion's life, as it was before 1.5.

## Planned

- Narrator-played dates with a dating-app match. The dating app itself is a
  standalone feature for finding new companions.
