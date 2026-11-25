# Story

The **Story** tab is the user's own free-form story: they play themself in one of the cities, and a
narrator describes the place and voices the people there. When the story is where a companion is at
that hour, they are in the scene and speak for themselves ([Companions in the scene](#companions-in-the-scene)).
The story has its own tables (`story_scene`, `story_messages`, `story_cast`). Time spent with a companion
there counts in their life together ([Scenes count](#scenes-count)).

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

## API

| Request | Does |
| --- | --- |
| `GET /api/story` | `{scene, messages, people, companions, ready, can_switch}`. `people` are those met, newest first, with `meetings`, `notes`, `doing` and `place` now. Each also has `matched` (they said yes to the user), `companion_id` and `ask` (`{label, line}` while they are in the scene and can be asked, else null). `companions` are every companion, the main one first, with `here` (in the scene) and `place` now (null when the story cannot go to them). `scene.plan` is the plan being played here and each companion's `plan` is theirs under way (`{outing_id, companion_id, name, what, until, place, storyline, people}`), else null. `scene` has the city, place, `local_time` (city clock, no offset), `weather`, the city's `places`, `around` (who is there, named only once met; companions first) and `companions` (those in the scene). A message's `role` is `user`, `narrator`, `scene`, `companion` (with `speaker` and `name`) or `cast`. A `cast` line with no `speaker` says how asking someone out went. `ready` is false without a model. |
| `PUT /api/story/scene` `{city_id, place_id?}` | Moves there; a city alone means its opening place. 404 for an unknown city or place. |
| `POST /api/story/messages` `{text, client_id}` | Saves the user's line once per `client_id` and returns `{message, reply, replies}`: `reply` is the narrator's, `replies` all of them in order, a companion's own lines after it. A failed reply is saved with `status: failed` and its `error`. Sending the same `client_id` again returns the saved replies and writes only what is missing. 409 `no_connection` without a model; the line stays saved. |
| `POST /api/story/find` `{key}` | Moves the story to where someone the user has met is now, or a companion (`companion:<id>`). 404 if not met, 409 if they are nowhere the story can go. |
| `POST /api/story/plan` `{outing_id}` | Plays a plan under way as a scene: moves the story to where the plan is ([Playing a plan](#playing-a-plan)). 404 for an unknown outing, 409 when it is not under way or is somewhere the story cannot go. |
| `POST /api/story/plan/begin` `{client_id}` | Starts the scene of the plan being played here with no line from the user: saves a hidden user line once per `client_id` and returns what `POST /api/story/messages` does. 409 with no plan under way here. |
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
- **What the user tells them:** facts said to a companion face to face become their memories, by the rules a chat
  message goes through (`companion/story_said.py`), read from the words said out loud (in quotation marks when the
  line has any, so "I take off my jacket" is not a fact). Every companion the line is said to hears it. This follows
  automatic memory; a sensitive fact is kept only while sensitive memory is on. The card on Memories says "Said in
  Story:" with the words said, or the whole line when nothing is quoted (`story_line` on `GET /api/memories`, table `story_memories`).
- **How they feel:** the user's words move the mood and rough patches of the companion the line is meant for, as a
  text does: words that sting, an apology, kindness, a gesture (read from the whole line, "I hand Mira the
  flowers"), with a grin or a nudge making it teasing. A promise said in person stays with chat. Their own line can
  make up ("We're good"). Their line in the scene is written knowing their mood and any rough patch with the user
  (`story_said.feeling_lines`; A/B in project files companion-story-stick/ab: shown 20/117 before, 97/117 after).
- **Their chat afterward:** for a day and a half, the 'where' section of their 1:1 chat says when and where they
  were together, who came to whom, and the last six lines the two of them said (`story_visits.context_lines`).
  After that it is the memory.

A line to someone else in the scene, or one out of the story (OOC: or ((...))), counts for nothing. A new story
clears the lines but not the time spent: visits are settled before the lines go.

Settings > Realism > "Story scenes count" (`life_settings.story_counts`, on by default) turns all of it off. The
story is then apart from the companion's life, as it was before 1.5.

## Playing a plan

A plan with a companion that is under way can be played in the Story, at its place, with the people it is with
(`companion/story_plans.py`). A plan is an outing (`companion/life/outings.py`): a date or anything else the two
settled in chat, drinks with their friends, a big day, or the plan a storyline the user is part of booked. Rules
decide all of it and nothing new is stored.

- **Where they are:** while a plan is under way the companion is where the plan is, not where the rest of their day
  would have them (the second place once they moved on, or where their chat took them). At their place, the
  user's, their family's or on the move, the story cannot go there and the plan stays in the chat.
- **Getting there:** Today's "Out together" card says "Talk face to face or play it out in Story" while the plan is
  under way somewhere the story can go (`story` on `GET /api/life/outings`). The Story's first open and its
  people list offer it too. The app never moves the story by itself, and the chat stays face to face as before.
- **On screen:** the story's line reads "Mira is here with you, for dinner." The scene says "Here with Mira for
  dinner, until 9:00 PM." (and "Part of a storyline." when a storyline booked it). Until something is said, one
  button, Start the scene, has the narrator open it and the companion speak. It adds no line of the user's: the models
  read "I turn to Mira." said for them (`story_messages.hidden`), which the screen, exports and their chat never show.
  From anywhere else the Story's first open says "Go to Lupa", which only goes there.
- **Who is there:** the people the plan is with are in the scene ("Mira and their mom Ana are here."), voiced by the narrator, who is
  told who they are to the companion, whether they have met the user and how they are with them
  (`people_impressions`).
- **What is told:** the narrator's scene says the two came together on a plan and did not meet by chance. The
  companion's own notes say what the plan is, until when, that they came together, who else is there, what is on the
  menu and how long they have been at it, in place of who came to whom.
- **What it leaves:** the plan's own memory, bill and storyline beat, as when it is played in chat. The time counts
  as a day talked, and their chat is told what was said (`story_visits.outing_id`), but the visit leaves no shared
  moment of its own. While the plan is still going on their chat is not told they are apart.

The wording was chosen by A/B on ten models (`/mnt/project-files/companion-story-plans/ab/report.md`): without it
the companion acted as if they had not expected the user in 52 of 85 replies, with it in 4 of 88, and a friend
along spoke in 1 of 28 of the narrator's replies against 24 of 29.

## Asking someone out

Someone in the scene can be pursued (`companion/story_pursuit.py`). When the user's line asks them out, their own
rules answer, the same ones the dating app reads (`companion/world/dating.py`). No model decides it.

- **What counts as asking:** a plain phrase in the user's line ("I ask Dana out", "would you go out with me",
  "can I have your number", "may I call on you"), aimed at the person it names, or at the only person there. A
  message out of the story (OOC) asks nobody. While someone the user has met is in the scene, their card in the
  people list has **Ask Dana out** ("Ask to call on Dana" in older eras), which says the line for the user.
- **How they answer:** never anyone under 18 on either side, and never a pack's character marked as having no
  love life. Someone seeing someone or married says so. Someone not drawn to the user's gender, or for whom the
  age gap is too wide, turns it down. Anyone else says yes by the dating app's chance (`dating.likes`: pickier
  people less often), plus `WARMTH` (0.2) for every day the user has met them after the first. So a stranger
  asked cold says yes about as often as a like on the app is returned, and someone the user keeps coming back to
  comes round within a few visits. The roll is fixed per person, so asking twice on one day changes nothing.
  The user is read from their dating profile when they have one, else from who they are in this world (the
  Persona page); what is not known is not held against them, and no profile has to be filled in first.
  Settings > Data > 100% Matchlight matches makes everyone who could say yes do so.
- **The narrator** is told the answer in one bracketed line after the user's line and plays it out (`NOTES`). It
  was tested on ten models (`/mnt/project-files/companion-story-pursuit/ab/report.md`): told nothing, the
  narrator's answer matched the person's rules in 24 of 85 replies; with the line, in 85 of 89, and it never went
  the other way.
- **In the story:** once the narrator has told it, a line says how it went ("Dana said yes.", "Dana didn't say yes
  this time.", "Dana said no."). From then on the narrator knows who has said yes.
- **A yes is a match**, kept where the dating app keeps its own (`dating_swipes` with `source` 'story'), so it
  uses the same path: the people list shows "said yes" with **Start talking to Dana** and "Read their profile
  first" (`#match/<key>`), and Matchlight lists them under Your matches as "Met in your story", with Meet in your
  story and Unmatch. They become a companion as a match does (`companion/cast.py`): a romance, in the town they
  were met in, starting as close as the times the user has met them, with a profile that says they met in person.
  The companion already there steps back and stays in the same world.
- Starting a new story lets go of whoever said yes in it, unless they became a companion. Deleting the dating
  profile keeps them: they were never the app's.
