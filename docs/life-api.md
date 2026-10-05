# Life simulation API

[Back to the README](../README.md) · [Architecture](architecture.md)

These endpoints back the interface's Today and Feed views. All times are UTC ISO 8601 strings
with an offset; display them in the user's timezone (`GET /api/settings` → `user_timezone`) or the
companion's (`GET /api/companion` → `version.timezone`). Writes need the
`x-companion-client: workspace` header, like the rest of the API.

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
inside a pause are marked skipped. Background reconciles extend the agenda only when background
activity is on.

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
| `day` | The companion's local day: `{date, weather, happenings, birthdays}`. `weather` is the typical weather (see Weather) or `null`, `happenings` the city's annual events that day, `birthdays` circle members (`{id, name}`) whose birthday it is. Weather and events appear once a reconcile has built the agenda. |

Call `POST /api/today/seen` once the user has looked at Today, so the next visit's `changes`
start from here. It never moves backward if the clock does. Event objects in `changes`, `review`
and `plans` have the same shape as `GET /api/events`.

## Feed

```http
GET  /api/feed?limit=20&before=…&hidden=false
GET  /api/feed/{post_id}
POST /api/feed/read                {"post_ids": ["…"]}   (omit the body to mark everything read)
POST /api/feed/{post_id}/reaction  {"reaction": "heart"} (heart, laugh, wow, sad, hug, or null to clear)
POST /api/feed/{post_id}/hide
POST /api/feed/{post_id}/unhide
POST /api/feed/{post_id}/remove
POST /api/feed/{post_id}/discuss   {"text": "…", "client_id": "…"}
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
  "image": {"status": "none", "job_id": null, "ref": null, "error": null, "updated_at": null}
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
  state. See [image generation](images.md).
- Hide is reversible. Remove clears the post for good but leaves its events in the companion's
  life and conversation. Removed posts are not listed or exported.
- `discuss` sends a chat message linked to the post and returns the same shape as
  `POST /api/conversation/messages`. The reply is written knowing which post the user meant.
- `POST /api/feed/posts` posts an event committed by other means; it is idempotent per event.
- `export` returns `{format: "prospero-companion-feed", version, exported_at, companion, posts}`,
  oldest first, hidden posts included.

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
