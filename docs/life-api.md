# Life simulation API

[Back to the README](../README.md) · [Architecture](architecture.md)

These endpoints back the interface's Today and Feed views. All times are UTC ISO 8601 strings
with an offset; display them in the user's timezone (`GET /api/settings` → `user_timezone`) or the
companion's (`GET /api/companion` → `version.timezone`). Writes need the
`x-companion-client: workspace` header, like the rest of the API.

`user_timezone` follows this PC unless the user picks one (`user_timezone_source`: `default`, `pc` or
`chosen`). On startup the backend sets it from the Windows registry (mapped to IANA with CLDR,
`companion/windows_zones.py`) or `TZ` and `/etc/localtime`; the interface then sends the browser's zone
with `user_timezone_source: "detected"`, which is ignored once the user has chosen a zone.
`GET /api/settings` also returns `system_timezone`, the backend's own reading.

## When to call reconcile

Call `POST /api/life/reconcile` when the interface opens and when it becomes visible again after
being hidden. It is cheap when nothing is due and safe to call repeatedly, from several windows or
after a restart: at most one batch runs per return, and a repeated call returns `not_due`. The
server also reconciles once on start and, only when the user enabled background activity, about
once a minute while it runs.

```http
POST /api/life/reconcile
{"mode": "return"}
```

The response always has a `state`, plus the batch (`run`) when one started, resumed or is running:

| `state` | Meaning | Suggested interface |
| --- | --- | --- |
| `started` | A catch-up batch ran now. `run.results` lists each slot's outcome. | Refresh Today and Feed. |
| `resumed` | An interrupted batch from earlier finished now. | Same as `started`. |
| `in_progress` | Another window or process is running the batch. | Poll `GET /api/life/runs` or reconcile again later. |
| `not_due` | Too little time has passed since the last batch. `due_at` says when one could run. | Nothing. |
| `paused` | Activity is paused. Nothing is simulated while paused. | Show the paused state and Resume. |
| `clock_behind` | The computer's clock is earlier than time already simulated. Nothing is replayed. | Optional notice that the clock moved backward. |
| `disabled` | The user turned catch-up on return off. | Nothing. |
| `no_companion` | No companion exists yet. | Nothing. |

A batch synthesizes fiction *now* for routine slots that ended while the user was away. Its
`created_at` is when it ran; each event's `starts_at`/`ends_at` is when the fictional moment
happened. Never word this as the companion having been active while the app was closed.

### Preparing while the user types

Call `POST /api/life/prepare` (no body) when the user starts typing or the window sits idle;
debouncing to once every few seconds is plenty. It returns at once with `{"state": "started"}` or
`{"state": "in_progress"}` and never delays anything. In the background it brings the agenda up to
date and, when a model is connected and `phrase_with_model` is on, phrases the companion's next
couple of upcoming agenda entries at background priority. A conversation reply interrupts it. When
one of those slots is later simulated, the batch uses the prepared wording without another model
call (the event's `inputs.prepared` is `true`), provided the model, address and prompt version are
unchanged. A server running with background activity on prepares after each tick as well.

### Batch (`run`) shape

```json
{
  "id": "…", "mode": "return", "status": "completed",
  "window_start": "2026-10-05T12:00:00.000000+00:00", "window_end": "2026-10-06T12:00:00.000000+00:00",
  "plan": [{"key": "morning@2026-10-06", "local_date": "2026-10-06", "starts_at": "…", "ends_at": "…",
            "block": {"key": "morning", "label": "Morning", "kind": "leisure", "days": [0,1,2,3,4,5,6],
                      "start": "09:00", "end": "12:00", "themes": []}}],
  "results": [{"slot": "morning@2026-10-06", "outcome": "proposed", "event_id": "…"}],
  "attempts": 1, "error": null, "created_at": "…", "started_at": "…", "finished_at": "…"
}
```

`status` is `running`, `completed`, `interrupted` (a conversation took priority; the next
reconcile resumes it), or `failed` (shown with `error`). Each result's
`outcome` is:

- `proposed`: an event awaiting the user's review (automatic events are off).
- `committed`: an event that is now part of the companion's life.
- `rejected`: the event was made stale by a pause, character change or permission change (`reason`).
- `quiet`: nothing notable happened (`reason`). Quiet stretches are valid.
- `skipped`: permissions changed or the timeline switched before this slot ran.

`GET /api/life/runs?limit=20` lists recent batches, newest first.

## Reviewing proposed events

With automatic events off (the default), catch-up only proposes. Proposed events appear in
`GET /api/events?history=true` with `status: "proposed"`. Commit or reject them with the existing
`POST /api/events/{id}/commit` and `POST /api/events/{id}/reject`. A commit can still come back
`rejected` with a `rejection` reason when the event became stale. Only committed events reach chat,
the feed and recall.

Life events carry `details` for display: `label` (routine block), `block_kind`, `activity` (the
composed activity, such as `walk` or `groceries`), `place` (`{id, name, kind, city, neighborhood}`
from the world data, or `null`), `local_date`, `timezone`, `post` (a caption in the companion's
voice), `mood` and `weather` (below, or `null`).

### Interests

The character's `interests` and `life_themes` make matching activities about three times as likely
as the others in the same block: "books" leans toward reading, the library and browsing shops,
"jazz" toward shows, "baking" toward cooking at home. Matching is by word, without a model, so a
character with no matching words keeps the even mix.

### Weather

Each day has typical weather for the companion's city, drawn from the world data's monthly climate
averages with a seeded chance of rain: `{season, high_f, low_f, rain, note}`. It is the same for
everyone in the city that day, so the companion and their circle agree. It is not a forecast and
never claims to be real. On a rainy, very hot (93°F and up) or very cold (38°F and below) day,
outdoor activities give way to indoor ones: no walks, and workouts happen at a gym rather than a
park. A rainy day at home sometimes gets a rainy caption. Agenda entries carry it as
`block.weather`, events as `details.weather`, and the chat context includes today's line, marked
as typical for the season and not a real forecast. Cities without climate data, and world sources
without a `weather` method, have no weather and every day is fair.

### City events

The world data lists each city's annual events by month. Each year one Saturday in one of those
months is picked from a seed of the city, event and year, so everyone in the city agrees on the
date; whole seasons (a team's season) are left out. On that day a leisure or social block may be
spent at the event (`activity: "festival"`, `place.kind: "event"`, at most once a day and less
often in bad weather), possibly with a free circle member. Agenda blocks carry the day's events as
`block.happenings` (`[{id, name, neighborhood, city}]`), and the chat context lists them beside the
weather, marked as fictional dates.

### Birthdays

Each circle member has a birthday (`birthday: "MM-DD"` in the circle API), seeded by their id. On
that date one leisure or social block goes to them: the companion celebrates with a local friend
who is free then (`activity: "birthday"`, at a restaurant or bar, `with` naming them), or calls a
relative who lives out of town (no place). The chat context marks the person's birthday on the day.

Events are composed from the routine, a fixed activity catalog and the world data, without a
model. When a model is connected and `phrase_with_model` is on, it only rewrites the wording;
`inputs.wording` is `model` or `template`. Set `home_city` on the character to a city id from the
world data (for example `"baltimore"`) so events use real places there. Without `home_city`, the
character's `location` is used when it names a known city, such as `"Fells Point, Baltimore"`.
When the location also names a neighborhood, everyday places (cafés, restaurants, bars, markets,
libraries, gyms, parks) stay near it; museums, venues and attractions stay city-wide. Circle members
use their own home neighborhood.

### Companion plans

Now and then an event also produces a plan for an upcoming leisure or social slot, such as
"Mira is planning to visit the Walters Art Museum on Saturday (afternoon)". A plan is a life event
with `kind: "plan"`, its `starts_at`/`ends_at` set to the target slot, and `details.target_slot`.
It is reviewed and committed like any other event, and the batch result for the event it came
from carries `plan_event_id` and `plan_outcome`. Committed upcoming plans appear in
`GET /api/today` under `plans.companion`. A plan is not an outing: when its slot is simulated, the
batch always includes that slot and writes the outing "as planned", with `details.fulfils` set to
the plan's id. If the slot falls outside a later batch's lookback, the plan quietly lapses.

### Unresolved threads

Now and then a simulated slot also opens a small open question in the companion's life, such as
"Mira ordered a secondhand record player and is waiting for it to arrive". A thread is a life event
with `kind: "thread"` and `details.state: "open"`, a stable `details.thread_key` and
`details.settles_on`, the local date from which it may settle. Once it is committed, the first
simulated slot on or after that date writes how it turned out: another `kind: "thread"` event with
`details.state: "settled"` and the same `thread_key`. Both are reviewed like any event, at most one
thread is open at a time, and the batch result for the slot carries `thread_event_id` and
`thread_outcome`. `GET /api/today` lists committed open threads whose outcome is not committed yet
under `plans.threads`.

## Social circle

The companion has a small circle of supporting people (PRD T8). Each is assembled from the city
data and a seed, without a model. In a known city this uses the world data's circle generator: a
name from the city's name groups, how they know the companion, an age, a home near the
companion's neighborhood when their location names one, a job with its weekly routine and a few
regular haunts. Relatives may live out of town, with no routine here. Elsewhere a simpler version
picks a first name, a role and a career's routine. The circle is created the first time it is needed. Its members are fictional
supporting characters, never the user and never a source of facts about the user.

```http
GET   /api/life/circle                     # ?include_removed=true also lists removed people
PATCH /api/life/circle/{id}                {"name": "Rowan"}
POST  /api/life/circle/{id}/remove
POST  /api/life/circle/{id}/restore
GET   /api/life/circle/{id}/diary          # ?before=<starts_at>&limit=20, newest first
```

A person is `{id, name, role, status, revision, career, employer, neighborhood, city, refs, sources,
data_version, birthday, schedule, now, recent}`, plus `full_name`, `pronouns`, `age`, `local`, `closeness` and
`haunts` when they came from a known city. `name` is the given name used in events; `local: false`
means they live out of town and have an empty `schedule`. `now` is the routine block they are in right now (for example
`{"label": "Registered nurse", "kind": "work", ...}`) or `null`. `recent` is the newest three diary
entries. A diary entry is `{subject, slot, starts_at, ends_at, local_date, block, entry, status}`,
where `entry` holds `summary`, `activity`, `place`, `mood` and `post`. Diary entries also carry `with_companion`
(`{event_id, summary}` or `null`): a committed companion event this person was part of. One that no
diary entry overlaps appears as its own entry with `slot` and `block` set to `null`. People favour
their regular haunts when one fits. Renaming, removing or
restoring someone rebuilds their upcoming entries and the companion's upcoming entries that name
them. Entries that already happened keep the earlier name. Social events can name a circle member
who is free at the time: the event's `details.with` is `{id, name}` or `null`. The chat context
lists the circle with each person's current block and latest diary entry.

### Circle size and who knows whom

How many people the circle has depends on the companion. Words in their identity, personality,
interests and themes decide how sociable they are (`social butterfly`, `outgoing`, `extroverted`
against `shy`, `introvert`, `homebody`; a negated word such as "not shy" doesn't count): 4 people
for a quiet one, 5 usually and 10 for a sociable one. The Life setting `circle_size` (0 to 12, 0 = decide
from the character) overrides it. A sociable circle fills in as close friend, longtime friend, coworker,
sibling, parent, new friend, a second coworker, friend, the other parent, a second new friend, cousin
and friend. Parents and siblings are named as the companion would say it (`mom`, `dad`, `sister`,
`brother`) when their pronouns say which. A coworker in a sociable circle works where the companion
works: their `schedule` has the companion's work blocks, `career` reads "Works with {name}" and
`works_with_companion` is `true`. A companion with no work block has friends instead of coworkers.

```http
GET  /api/life/circle/room     # {people, target, sociability}
POST /api/life/circle/grow     # adds people up to the target; 409 when the circle is already full
```

A circle assembled smaller than its target (an existing companion, or a size raised in Settings)
grows with `grow`: missing roles first, nobody already there changes. Each person also has `knows`:
the other active members they know (`{id, name, how}`), derived from roles and a seed, so it is the
same on every read. `how` is `family`, `married` or `divorced` (the two parents), `coworkers`, `old
friends`, `known for years` (an old friend and the family) or `friends`. The chat context adds it to
each person's line ("Married to Rui. Knows Ana (family).").
## Home and belongings

`companion/life/home.py` gives the companion a home and things they live with, assembled once per
timeline without a model: the home the budget (`money.py`) pays rent on, same neighbourhood, size and rent
(else one from `generators.home`), plus the kind of building and its quirks; maybe a
pet, a few plants, a way to get around (a car is less likely in a city with a subway; earlier eras
ride or cycle) and a few favourite things weighted toward their interests. Every two weeks a seeded
draw may change one thing on one day: a new plant, a plant lost, the car into the shop for a few
days, a new favourite thing, a vet visit, an adopted pet, rearranged furniture. Evolving in steps or
all at once gives the same log.

- **Events.** `agenda.extend_subject` calls `home.touch` once per companion entry (the only hook in
  the life sim). It appends one plain sentence to the summary: the day's change, or now and then a
  belonging that fits the activity (the dog on a walk, watering a plant while cooking, riding the
  bike to the shops). `entry.home` records `{items, change, sentence}`. Circle entries are untouched.
- **Images.** `images/prompts.build` adds `home.image_hint`: the room for a moment at home, and how a
  belonging named in the event looks.
- **Chat.** The context has a "Your home and belongings" section with today's inventory, any repair
  under way and the last three weeks of changes.
- **Money.** `home.monthly_costs(connection, timeline_id, day)` returns `{rent, rent_period, currency,
  estimate, pets, vehicles}`; `home.purchases(connection, timeline_id, start, end)` returns the
  changes that cost something (`spend` is `$` or `$$`). Read these rather than the tables.

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/life/home?include_removed=` | | `{today, items, removed, changes, costs, varieties}` |
| POST | `/api/life/home/items` | `{kind, name, description?, variety?}` | the same view |
| PATCH | `/api/life/home/items/{id}` | `{name?, description?, variety?}` | the same view |
| POST | `/api/life/home/items/{id}/remove` / `restore` | | the same view |

An item is `{id, kind, name, variety, description, origin: generated|change|user, since, until,
edited, revision, out_of_action}`; the home also has `neighborhood, city, features, rent,
rent_range, currency, rent_period, estimate`. `variety` is a pet's species or a vehicle's type
(`varieties` lists the choices). The home itself can be edited but not removed. Any edit forgets
the seeded changes still ahead and rebuilds the upcoming agenda entries that mention the home;
moments that already happened keep what they said. A fork keeps the home as it was at the fork.

## Friends of friends

Everyone in the circle has their own people, and theirs have theirs, down to four layers from the
companion (`companion/life/network.py`). Nobody out there is stored or simulated: a person is a seeded
path from a circle member (`circle:<timeline>:<n>/2/0`) rebuilt the same way on request, with an
era-fitting name (`companion/world/naming.py`) and only relatives sharing a family name. A partner gets no
partner of their own.

```http
GET /api/life/network?key=<key>   # {person, people: [{key, full, relation, how, age, occupation, met}], deeper}
GET /api/life/acquaintances       # people met through the circle, newest first
```

A circle member's `key` is on `GET /api/life/circle`; each person returned carries the key for the next
layer while `deeper` is true.

They come up at gatherings and run-ins. When the agenda writes a Friday or Saturday evening the companion
has free, a free friend (not family) may host something: a Friendsgiving in November, a summer barbecue, a
holiday party in December, game night, a dinner party, a housewarming. The companion goes, the entry names
two to four of the host's people they met, sometimes one of a guest's people too, and each is saved as an
acquaintance with a snapshot of who they are. An acquaintance counts once that evening has happened and its
entry still records the meeting. Later, out somewhere, the companion now and then runs into one of them
("Ran into Jordan Lee (Becca's coworker, from Becca's Friendsgiving) there."). The chat context lists the
six most recent acquaintances and where they met; forks keep those met before the fork. No model is
involved.

## Townsfolk around the city

Every place in the city has two or three seeded background people (`companion/world/townsfolk.py`): staff
(the barista, the barkeep, the librarian) and regulars, each with an era-fitting name and job, a home
neighborhood near the place, a temperament, a quirk, a flaw, a desire and a list of goals. They are never
stored; `town:<city>:<place>:<n>` rebuilds one. Plain if/then/else rules (`whereabouts`) put them somewhere
at any hour: on shift, asleep, on their usual visit, off working toward their goal (a run in the park, study
at the library), out at a bar on a weekend evening when they want company, or at home. Their goal moves
week by week from 5 January 2026 (`story`): a seeded roll each week makes progress, stalls or is a setback,
a driven temperament helps and a procrastinating or spendthrift flaw drags, and once enough progress is made
they reach it and start the next goal.

When the agenda sends the companion somewhere real for leisure, an errand or a social plan, someone there by
their rules may cross paths with them (`companion/life/encounters.py`; at most one a day). The first time is
a chat with a stranger; the second reveals what they are working toward; from the third the companion knows
their flaw and what they seem to want, and later meetings bring their news. People already met can turn up
wherever their rules take them. A meeting counts once its slot has happened and the entry still records it
(`entry.townsfolk = {key, times}`), and forks keep meetings before the fork. The chat context lists the six
most recently seen, with only what the companion has learned. No model is involved.

```http
GET /api/life/townsfolk                     # townsfolk met, most recently seen first, only what is known
GET /api/life/townsfolk/person?key=<key>    # one of them, plus `now`: where their rules put them right now
GET /api/world/cities/<id>/places/<place>/people?on=<date>&at=<HH:MM>   # the city's full view of a place's people
```

## Precomputed agenda

Every reconcile also brings a hidden agenda up to date, without a model (PRD T9). The agenda holds
the routine of the companion and of each circle member, composed slot by slot a week ahead and
seeded by the slot. When the app opens after time away, the whole gap is filled in at once, up to
30 days back. A server left running advances the same agenda in small steps, and both reach the same
entries. Upcoming entries are never returned by the API. Circle members' past entries are their
diary. The companion's past entries become part of their account only through the capped,
reviewed events above: a batch uses the precomputed entry for each slot it simulates, and a plan
reveals an upcoming entry. Changing the character rebuilds the companion's upcoming entries. The chat context lists the companion's next few
upcoming entries within a day as likely intentions, so "what are you doing tonight?" gets an answer
that matches what later happens; the companion is told they have not happened and may change, and
mentioning them commits nothing. On a public holiday in the city's
calendar, a work or study block becomes a day off: the entry's block has `kind: "leisure"`, a label
such as "Thanksgiving (day off)" and `holiday`, and events simulated from it carry that block. Slots
inside a pause are marked skipped.

Each day also carries how its subject feels physically (`companion/life/body.py`), worked out from
the day before with no model and seeded by the subject and date: a late night out can leave them
`tired` or `hungover`, a hectic shift `worn out`, a workout `sore`, and now and then a cold
(`sick`, more often in winter) lasts two or three days. Every block that day gets
`body: {state, because}`. A cold turns work or study into a sick day and leisure into "Home sick"
(`kind: "rest"`, `sick_day: true`), and a sick circle member is not free for plans. A low day keeps
leisure and social time to calm activities at home or nearby. Events carry `details.body`, Today's
`day.body` shows it and the chat context gets one line about it. Background reconciles extend the agenda only when background
activity is on.

### Recommendations

When the user writes "you should watch / read / listen to / play / try / visit / go to / check out X"
(not as a question or hypothetical), `companion/life/recommendations.py` records X with a kind
(`show`, `movie`, `book`, `music`, `game` or `outing`) and a seeded number of sessions. From 12 hours
later, the companion's free leisure, social or rest slots get one session a day (activity
`recommendation`, `entry.recommendation: {id, title, kind, session, of, verdict}`), and the last one
carries a verdict, seeded and tipped warmer by matching interests or stated likes. Return batches
simulate these slots before others, so they become committed events. The chat context lists each
recommendation's committed progress and tells the companion it knows nothing about it beyond its
name. A finished one can open a conversation. `GET /api/life/recommendations` lists them as
`{id, kind, title, state: waiting|started|finished, sessions_done, verdict}`, and
`POST /api/life/recommendations/{id}/drop` takes one back, clearing its upcoming sessions.

### Storylines

Things unfold over days in the companion's life and their circle's (`companion/life/storylines.py`):
"my dad just got a promotion", "the new guy at work keeps hitting on me", "I got drunk and kissed my
best friend". Each is a fixed template with a cast from the circle (or the companion's own work) and
one to three beats a few days apart. Whether one starts on a day, which template, who is in it and
how each beat turns out are decided by a seed when it starts, never by a model; later beats stay
hidden until their local date. The Life setting `drama` (0 quiet, 1 realistic, 2 dramatic, 3 soap
opera; default 1) sets how often one starts (about 4%, 8%, 15% or 28% of days), how many run at once
(1 to 4) and which templates can happen: quiet keeps to good news; realistic adds everyday trouble
(a creepy new coworker, a friend's breakup, layoff rumors); dramatic adds health scares, feuds and
secret romances; soap opera adds drunk kisses, separations and family secrets. A template doesn't
repeat within 90 days, a person is in one running storyline at a time, and a companion in a romance
with the user never gets one about their own love life.

```http
GET  /api/life/storylines                 # ?include_ended=true also lists ended ones
POST /api/life/storylines/{id}/end        # it leaves Today and the context; later beats never happen
```

A storyline is `{id, story, level, started_on, status, cast: [{id, name, role}], beats: [{on, text,
share, tone}], unfolding}`, listing only beats whose date has come. Names are filled in as people are
named now; removing someone ends the storylines they are in. The chat context lists the last three
weeks' storylines and says when one is still unfolding, so the companion never guesses the ending.
A beat from today or yesterday can open a conversation, using its `share` line when no model is
connected. Days are decided as the agenda extends, up to 14 days back after time away.

### Birthdays and anniversaries

`companion/life/occasions.py` keeps three kinds of day, from the calendar and saved state only:

- The companion's birthday: the definition's `birthday` (`"MM-DD"`), or a date seeded by the
  companion's id when it is empty. On the day, their first free leisure or social slot from noon is a
  celebration (`activity: "own-birthday"`), with a free circle member when there is one.
- The user's birthday: the Life setting `user_birthday` (`"MM-DD"` or empty). It is filled in the first
  time the user says it plainly ("my birthday is March 3rd", "it's my birthday today"; questions and
  "if…" are skipped) and is never replaced by a later message; the user changes or clears it in
  Settings.
- How long they have talked, counted from the timeline's first message in the user's timezone: a
  month, 100 days, three months, six months, then every year. For a romance it reads as their
  anniversary.

The chat context lists the day itself and birthdays within a week. Today's response has `occasions`
(`[{key, kind, date, days, span, text, template}]`, `kind` one of `user_birthday`, `own_birthday`,
`anniversary`). On the day, an occasion is the first reason the companion may message first.

## Limits and permissions

```http
GET /api/life/settings
PUT /api/life/settings
```

| Field | Default | Range | Meaning |
| --- | --- | --- | --- |
| `automatic_events` | `false` | | Commit ordinary events without review (PRD T3). Changing it advances the permission revision, so prepared work is revalidated. |
| `catch_up_on_return` | `true` | | Run a batch on return (PRD T4). |
| `phrase_with_model` | `true` | | Let the connected model reword composed events. Off means template wording and no model calls. |
| `catch_up_max_events` | 3 | 0–6 | Most events in one batch, however long the absence (PRD T5). |
| `catch_up_lookback_hours` | 48 | 6–336 | Only slots this recent are written; older absence stays uneventful. |
| `return_gap_hours` | 4 | 1–48 | Unsimulated time needed before a return batch runs. |
| `background_interval_minutes` | 60 | 15–1440 | Gap between background batches. |
| `background_daily_events` | 3 | 0–8 | Most background events in 24 hours; one per batch. |
| `texts_first` | `false` | | The companion may send the first message (see First messages). |
| `texts_daily` | 2 | 1–6 | Most first messages in 24 hours. |
| `texts_gap_hours` | 3 | 1–24 | Hours since the last message before the companion writes first. |

Background batches also need `background_activity: true` in `PUT /api/settings`. Pausing
(`POST /api/pause`) stops new batches, and resuming skips the paused interval rather than
generating it.

### Catching up a paused interval

```http
GET  /api/life/pauses
POST /api/life/pauses/{pause_id}/catch-up
```

Resuming never fills in the paused time. If the user deliberately asks for it, call the catch-up
endpoint for that pause. It runs one batch for slots inside the pause, within the same limits as
a return, and returns the same shape as reconcile (`state` is `started`, or `already_done` with the
earlier batch). It is refused (409) while paused or for a pause that has not ended.
`GET /api/life/pauses` lists pauses newest first with `started_at`, `ended_at`,
`catch_up_requested_at` and `catch_up_run_id`.

## First messages

```http
POST /api/life/texts/check   → {state, kind?, message: Message | null}
```

With `texts_first` on, the companion can start a conversation (`companion/life/openers.py`). The
open app calls this about once a minute, and a server with background activity on checks on its own
tick. Fixed triggers decide when, in this order, each at most once per timeline:

| Kind | When | Needs a model |
| --- | --- | --- |
| `follow_up` | A plan the user mentioned ended between an hour and three days ago without an outcome | No (template: "Hey! How did the … go?") |
| `news` | An open thread in the companion's life settled in the last day | Yes |
| `reminder` | An event committed in the last day shares a distinctive word with a user fact or shared experience | Yes |
| `silence` | Only with an absence trait: no word from the user for two days | No (template by intensity) |

The model gets the normal chat context plus the reason and its facts, and is told not to add events,
places or people. A reply that is empty, cut off or longer than 600 characters falls back to the
template, or to nothing for triggers without one. `state` says why nothing was sent: `off`,
`paused`, `quiet_hours` (the notification quiet hours, in the user's timezone), `asleep` (a sleep
block in the companion's routine), `recent_conversation`, `waiting_for_answer` (their last first
message is still unanswered), `daily_cap`, `interrupted` or `nothing`. A sent message is an ordinary
companion message with `reply_to: null`; the chat shows it before the user's next message and the
next reply sees it. With notifications on it is announced (kind `message`) before any waiting
posts. A forked timeline keeps the triggers its parent already used.

## Texting rhythm

How the companion texts is part of their definition: `texting: {bursts, lowercase, typos}`, all off
by default (`companion/texting.py`). The character section of the context tells the model the style.
A complete reply is then restyled by fixed rules: all lowercase except links, and with typos on, a
seeded one reply in eight gets one swapped pair of letters and a `*word` line after it. Bursts are
blank-line separated parts, shown as separate bubbles in the Bubbles chat style.

The companion decides when to answer, and the app never says whether they are free: the chat and
Today show no availability (the `availability` field below is for the context only). With the Life
setting `paced_replies` on (the default), a reply to a message sent while they are at work or out is,
by a seeded choice (`companion/life/pacing.py`), one of:

- written now and shown later: 8 to 45 minutes at work, 5 to 25 out, never past the end of the block;
- a quick holding text now ("in a meeting, give me a bit", the message's `held_line`) and the full
  reply later;
- a quick short note now instead of a real conversation (the model is told to keep it brief).

Asleep, the reply shows when they wake (at most ten hours). A held reply carries `held_until`; the
chat shows nothing for it (or only the holding text) until then. A reply that shows at once also
shows every earlier one still held, and one held while another is waiting shows no sooner than it,
so replies keep their order. The day that counts is the precomputed agenda's, so a holiday or a sick
day is not work, and a shifted day (see Day disruptions) counts as it ended up. A held reply that
shows while the app is in the background is announced like a first message, unless the user has
written since.

## Day disruptions

Nobody's day goes exactly to plan (`companion/life/disruptions.py`). When the agenda writes a slot,
for the companion and for circle members alike, it rolls on a d100 table for that kind of block with
the dice and table logic copied from Prospero's Study (`companion/life/chance.py`), seeded by the
slot, so a slot always shifts the same way and a day never changes after the fact:

| Block | No event | Shifts |
| --- | --- | --- |
| work, study | 84% | running late 10 to 45 minutes (9%), staying late 15 to 60 minutes (7%) |
| social | 76% | running late (8%), plans falling through: a quiet night in (11%), something coming up: an errand (5%) |
| leisure | 84% | something coming up (7%), a free circle member dropping by: company (9%) |

Each shift rolls a reason on a child table ("missed the bus", "a meeting ran long"). Running late
moves the slot's start and stretches the slot that ended there (often sleep); staying late moves
its end, and the next slot starts when it ends. A changed block keeps what was `planned` and
carries `shift: {key, minutes, reason, friend, text}`; the composed entry starts with the shift
("Mira ran 20 minutes late (missed the bus). …"). Holidays, sick days and sleep never shift. The
chat context lists today's shifts so far, so the companion knows why they were late, and paced
replies follow the day as it turned out. The Life setting `day_shifts` (on by default) turns it off
for slots written from then on.

## Routine

```http
GET /api/life/routine
```

Returns the companion's routine `blocks`, the `current` and `next` slot (each as in a batch plan;
`current` is `null` between blocks), `timezone`, `default_schedule` (true while the character has
no schedule of its own), `simulated_through`, `now` and `clock_behind`.

Use `current` for availability (PRD C5): a `sleep` or `work` block explains a slow or brief
reply but never locks the conversation.

The schedule is part of the character definition (`POST /api/companion`,
`POST /api/companion/versions`):

```json
"schedule": [
  {"key": "shift", "label": "Bakery shift", "kind": "work", "days": [0,1,2,3,4],
   "start": "06:00", "end": "14:00", "themes": ["regulars", "new recipes"]},
  {"label": "Asleep", "kind": "sleep", "start": "22:30", "end": "06:00"}
],
"life_themes": ["cycling", "the harbour"]
```

`kind` is one of `work`, `study`, `errand`, `leisure`, `social`, `rest`, `sleep`; nothing is
simulated in `sleep` blocks. `days` are 0 (Monday) to 6 (Sunday), all days by default. An `end` at
or before `start` crosses midnight. `key` is optional and derived from the label.

## Today

```http
GET  /api/today
POST /api/today/seen
```

`GET /api/today` returns everything the Today view needs in one call:

| Field | Meaning |
| --- | --- |
| `now`, `user_timezone`, `companion_timezone`, `companion_local_time` | Clock context for display |
| `availability` | `{state, label, until}`; `state` is `free`, `working`, `out` or `asleep`, from the current routine block. It explains a slow or short reply and never blocks sending (PRD C5). |
| `routine` | `{default_schedule, current, next}`, as in `GET /api/life/routine` |
| `changes` | Events committed since `last_seen_at`, newest first (the latest ten on a first visit) |
| `review` | Proposed events waiting for the user's commit or reject, oldest first |
| `plans` | `shared`: the user's open plans from memory; `companion`: the companion's upcoming committed plans; `threads`: committed open threads whose outcome is not committed yet |
| `feed_unread` | Unread feed posts |
| `last_run` | The most recent batch, or `null` |
| `paused`, `paused_at`, `simulated_through`, `clock_behind`, `limits` | State for the activity controls |
| `last_seen_at` | When the user last marked Today as seen |
| `day` | The companion's local day: `{date, weather, happenings, birthdays, body}`. `body` is how they feel today (`{state, because}`, see the agenda) or `null`. `weather` is the typical weather (see Weather) or `null`, `happenings` the city's annual events that day, `birthdays` circle members (`{id, name}`) whose birthday it is. Weather and events appear once a reconcile has built the agenda. |

Call `POST /api/today/seen` once the user has looked at Today, so the next visit's `changes`
start from here. It never moves backward if the clock does. Event objects in `changes`, `review`
and `plans` have the same shape as `GET /api/events`.

### Money

```http
GET /api/today/money
```

The companion's budget on their local today, from `companion/life/money.py`. It is computed, not
stored: the career's pay tier (`definition.money.career`, else a career named in who they are, else an
ordinary wage), the home city's rents, prices and currency, and `definition.money.style`
(`careful`, `balanced` or `spender`). The same character and date always give the same answer, and
the model only phrases it (chat context section "Your money").

- **Pay**: modern US cities pay a monthly take-home by pay tier, a little higher where rents are
  higher; other cities use their `wage` price, else a multiple of a typical rent. Pay comes every
  other Friday where rent is monthly and every Saturday where it is weekly.
- **Rent**: a neighbourhood named in their location, else one whose rent tier fits their pay. When
  rent would take more than 45% of pay they take a smaller place, or a room in a shared one.
- **Pay period**: fun money runs down through the period. A seeded splurge may land on or after
  payday, and now and then a surprise bill. `tight` marks the low stretch; `cant_afford` lists the
  outings that cost more than what is left.
- **Saving**: `goal` is the user's `saving_for` and `goal` amount (counted from `goal_since`), or a
  seeded everyday goal for each half of the year.

- **Home**: once their home exists (`companion/life/home.py`), rent comes from its `monthly_costs`
  (`rent_from: "home"`), pets and vehicles add `upkeep`, and home changes this pay period that cost
  something (`purchases`: a new pet, a repair) are listed in `bought` and come out of what is left.
  Before then the budget's own rent estimate applies (`rent_from: "budget"`). The composer's
  `affordable` check uses the budget without the home, since it has no database.

Where the setting has no money (Oz) or no known city, `available` is `false` with a `reason`.

The composer calls `money.affordable(definition, activity_key, local_date)` once per option: an
outing they cannot afford that day gives way to a free activity (a walk, cooking at home). If
nothing is affordable the routine happens as before.

## Feed

```http
GET  /api/feed?limit=20&before=…&hidden=false&source=all
GET  /api/feed/{post_id}
POST /api/feed/read                {"post_ids": ["…"]}   (omit the body to mark everything read)
POST /api/feed/{post_id}/reaction  {"reaction": "heart"} (heart, laugh, wow, sad, hug, or null to clear)
POST /api/feed/{post_id}/hide
POST /api/feed/{post_id}/unhide
POST /api/feed/{post_id}/remove
POST /api/feed/{post_id}/discuss   {"text": "…", "client_id": "…"}
POST /api/feed/{post_id}/answer    {"option": "Tacos", "client_id": "…"}   (question posts)
POST /api/feed/posts               {"event_id": "…", "intro": "…"}
GET  /api/feed/export
```

`GET /api/feed` returns `{posts, next_before, unread}`, newest first. Pass `next_before` as
`before` to load older posts; it is `null` at the end of the history. `hidden=true` includes
hidden posts. Opening the feed does not mark anything read; call `POST /api/feed/read` for the
posts the user actually saw, so a new post never steals focus or silently disappears from unread.

A post:

```json
{
  "id": "…", "kind": "digest", "intro": "", "status": "visible", "read": false, "read_at": null,
  "reaction": null, "occurs_at": "…", "created_at": "…",
  "events": [{"id": "…", "summary": "Walked to the harbour market.", "caption": "Lovely light today.",
              "mood": "content", "label": "Morning", "kind": "ordinary",
              "starts_at": "…", "ends_at": "…", "revision": 1}],
  "image": {"status": "none", "job_id": null, "ref": null, "error": null, "updated_at": null, "outdated": false}
}
```

- `kind` is `digest` (one per catch-up batch, covering its events) or `event` (one event, from
  background activity or an explicit post).
- A post shows events by reference, always at their current committed revision. Correcting an
  event changes every post that shows it. Proposed events appear only once committed, and
  rejected ones never do, so a post with nothing committed is left out of the feed.
- `caption` is the companion's own line for the moment, falling back to the summary.
- `occurs_at` is the fictional time the post is about; `created_at` is when it was written.
- `image.status` is `none`, `queued`, `running`, `completed`, `failed`, `cancelled` or
  `interrupted`; `image.ref` is the job whose file is shown. Render the text whatever the image
  state. `image.outdated` is true when the shown picture was made from an event version that has
  since been corrected or withdrawn; say so rather than presenting it as the corrected moment. See
  [image generation](images.md).
- Hide is reversible. Remove clears the post for good but leaves its events in the companion's
  life and conversation. Removed posts are not listed or exported.
- `discuss` sends a chat message linked to the post and returns the same shape as
  `POST /api/conversation/messages`. The reply is written knowing which post the user meant.
- `POST /api/feed/posts` posts an event committed by other means; it is idempotent per event.
- `export` returns `{format: "prospero-companion-feed", version (2), exported_at, companion, posts}`,
  oldest first, hidden posts included.
- Every post has `source` (`life` for the posts above, `social` below), an `author`
  (`{kind: "companion" | "person", id, name, role}`) and an `audience`
  (`{likes: [names], comments: [{author, name, text, at}]}`).

### The social side

`source=companion` keeps only the companion's posts and `source=circle` only their friends'.
Reading the feed or Today writes the social posts due for the last few days
([companion/life/social.py](../companion/life/social.py)). No model is involved: everything comes
from the agenda, the circle, the city data and fixed phrasing, under seeded idempotency keys.

- `friend`: a circle member shares a happened diary entry (`text` is their line, `context` what
  happened, `place` where). A few a day across the circle, at most one per person.
- `status`: a passing thought of the companion's from the day's weather, how they feel, the weekday
  or an interest. It never claims anything happened.
- `birthday` (a circle member's birthday), `holiday` (a public holiday), `city` (an opening,
  closing or road works the day people hear of it, or an annual event on its day).
- `question`: an either-or with `options`; `answer` records the user's pick and sends it to chat as
  a reply to the post. `answer` is `null` until then.

Social posts have `events: []` and `image: null`. They are read, reacted to, hidden, removed and
discussed with the same endpoints. Likes and comments are derived, not stored: they come from the
post, the active circle and the clock, arriving within a few hours of the post, at most three
comments each. No line is said twice on one post or repeated on the few posts just before it. The companion likes and comments on friends' posts. A renamed friend shows their new
name; a removed one's posts and comments leave the feed. A branched timeline keeps the social posts from before it split off, with their read, reaction and answer state.

## Emotional traits and absence mood

Traits are part of the character definition (`emotional_traits`, empty by default; see PRD C6):
each has a `name`, an `intensity` of `mild`, `moderate` or `strong`, and an optional `note`.

When the user returns at least a day after their last message and a trait's name speaks of
absence, guilt, missing the user, neediness or sulking, the return records a mood (PRD M4).
`GET /api/today` shows it as `mood`, which is `null` otherwise:

```json
"mood": {"id": "…", "kind": "absence", "intensity": "moderate", "away_hours": 72,
         "away_from": "…", "away_until": "…", "traits": ["guilt over absence"],
         "created_at": "…", "expires_at": "…",
         "recorded_traits": [{"name": "guilt over absence", "intensity": "moderate", "note": ""}]}
```

- The intensity never exceeds the current trait's intensity, however long the absence.
- A paused interval is not an absence.
- The mood lasts two days, until the user resets it, or until the traits are removed, whichever
  comes first. Removing the trait ends it from the next reply.
- `POST /api/today/mood/{id}/reset` clears it and returns `{"mood": null}`.

Show the mood plainly in Today with its reset action. Product controls and system notices stay
neutral whatever the traits: never word Settings, Pause or permission prompts in character.
