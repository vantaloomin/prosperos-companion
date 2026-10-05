# Backbone architecture

[Back to the README](../README.md)

This describes what the current backend implements against the
[product requirements](product-requirements.md). It covers the "Core companion preview" data
model and the life simulation; the endpoints the interface uses for it are in the
[life simulation API](life-api.md).

## Sources of truth (M1)

Each kind of record has its own table, so a model guess, a fictional event and a user statement
can never be confused.

| Table | Holds | Authority |
| --- | --- | --- |
| `companions`, `character_versions` | One focal companion and every version of its definition (C1) | User-authored; a new version applies from its effective time |
| `timelines` | The active timeline and any frozen ones, with the fork point and waiting draft of each historical edit (C4) | One active timeline advances with real time |
| `messages` | User messages and every reply attempt, with status | Only a `complete`, `active` reply is the conversational response |
| `life_events` | Proposed, committed, rejected and superseded fictional events (T2–T3, T7) | Committed events are the single account shared by chat, feed and recall |
| `memories`, `memory_sources` | Typed personal memories with sources (M6–M12) | `stated`/`confirmed` reach context; `tentative` does not |
| `memory_declines`, `deletion_markers` | Don't-remember choices and non-content deletion markers | Block re-extraction and reintroduction |
| `memory_jobs`, `memory_candidates`, `memory_activity` | Queued extraction, extracted candidates and suggestions, and an activity log of identities and reason codes | Candidates are not memories until committed |
| `workspace_settings`, `pauses` | Permissions, memory revision and pause intervals | Revisions make queued work detectably stale |
| `context_settings`, `context_services`, `context_tools` | The user's own location, MCP servers and confirmed tool mappings (X1) | A mapping runs only while its confirmed disclosure still matches |
| `context_observations`, `context_uses` | Every lookup attempt and which reply used it (X2, X3) | External data with freshness; never a personal memory |

## Revisions and stale work

- **Memory revision.** Every memory change and event correction advances it. A reply records the
  revision it was built from; if it changed by the time the reply finishes, the reply is kept as
  `withheld` and does not become active (M9).
- **Permission revision.** Changing automatic memory, sensitive memory, background activity or
  pause state advances it. An event proposed under an older revision is rejected at commit.
- **Event commit** also rejects a changed character version, an inactive timeline, an active pause,
  an interval that overlaps a pause, and an ordinary event that has not ended yet. A repeated
  commit with the same idempotency key is a no-op (T7).

## Conversation (C2)

Sending saves the user's text first, keyed by a client id so a retried send never duplicates
anything. Without a model connection the message is still saved and the response says
`not_configured`. Failed, cancelled and token-limited replies are saved with their partial text
and stay inactive. A reply left `streaming` by a crash is marked `incomplete` on the next start.
Alternatives keep the earlier wording; they are offered for the latest message only.

### Streaming replies

Sending (or asking for an alternative) with `?wait=false` returns as soon as the user's message
and the reply attempt are saved; the attempt is `streaming`. The client then follows
`GET /api/conversation/replies/{id}/events`, a server-sent event stream with three events:

| Event | Data |
| --- | --- |
| `snapshot` | `{id, text}`: everything written so far, so a reconnecting client catches up |
| `delta` | `{id, text}`: the next piece of text |
| `done` | The saved reply, in its final status (`complete`, `incomplete`, `cancelled`, `failed` or `withheld`) |

A finished reply's stream sends only `done`. Generation belongs to the app, not to the request or
the stream: closing the stream or reloading never stops a reply, only
`POST /api/conversation/replies/{id}/stop` does. Retrying a send while its reply is still being
written returns that same attempt instead of starting another. Without `wait=false` the request
waits for the finished reply, as before.

### Search

`GET /api/conversation/search?q=` returns up to 50 matching messages from the active timeline,
newest first, with `more` set when there may be others. Matching ignores case using Python's
`casefold`, so it works beyond ASCII. Deleted (redacted) messages never match. The interface
loads older pages until the match is on screen, then scrolls to it and marks it.

## Timelines (C4)

`companion/timelines.py` handles historical edits. Editing one of the user's earlier messages
(`POST /api/timelines` with `message_id` and the new `text`) never rewrites the live relationship:
it creates a separate, inactive timeline holding a copy of everything before that message. The
conversation, the companion's committed events (and plans made before the edit), the posts showing
them, the circle and the circle's diary are copied with new identities; the edited words wait as
the timeline's `draft` until they are sent there. Copied messages record the message they were
first written as (`origin_id`), and their embeddings are copied too, so recall needs no new requests.

`POST /api/timelines/{id}/activate` is the explicit choice. The previously active timeline is
frozen and its pending work reconciled: unreviewed events are rejected, unfinished batches stop,
the hidden upcoming agenda is dropped, images not yet started are cancelled, and replies still
being written there are stopped. The memory and permission revisions both advance, so anything
that finishes later is revalidated and withheld or rejected (T7); background proposals name the timeline they were planned for, so a late
one lands on the frozen timeline and fails its commit check. A timeline's life resumes from the
moment it is chosen: the time it spent frozen, or before a fork was first chosen, is never
simulated, and switching is not an absence for the absence mood. `GET /api/timelines` lists them
(the first is labelled "Original"); `PATCH /api/timelines/{id}` renames one or clears its draft.

In the interface, each of your messages has **Edit from here**, which opens the edit with a choice
to switch now or keep the new timeline for later. The branch button in the conversation header
lists timelines and switches between them after a confirmation. After switching to an edit, its
words wait in the message box; switching away again takes them out unsent.

**Memory across timelines** (`companion/lineage.py`). Memories are not copied. A timeline sees its
own memories plus those its ancestors formed before the fork point, so relationship history before
an edit carries over and nothing after it does. Real-user profile facts (`user_fact`, `plan`,
`temporary`) are shared across every timeline while `share_profile_across_timelines` is on (the
default, shown in Settings); turned off, they follow the same rule as everything else. Shared
experiences, relationship history and the companion's fictional life always stay with their
timeline (M6). Changing the setting advances the memory revision. Choices about a message reach all
of its copies: Don't remember this, an excluded memory's source block, and deleting a memory with
its source messages apply to the original and every copy, so a fork never brings back words the
user removed elsewhere (M12). The Memories view lists every memory, marking those from another
timeline that the current conversation does not use (`in_timeline: false`).

## Context builder (M10)

`companion/memory/context.py` assembles each reply:

1. Character guidance and the user's boundaries are required. If they do not fit, the request
   fails with `context_limit` instead of dropping them.
2. The current time in the user's and companion's timezones, and the gap since the previous
   message when it is six hours or more.
3. Recent conversation, newest first, so a tight budget drops the oldest turns.
4. Current profile facts (pinned first), open plans, and unexpired temporary circumstances.
5. The companion's latest committed events.
6. Older turns and episodic memories, ranked by the Study's lexical retrieval and rank fusion.
   When the connection names an embedding model, an embedding ranking of the same eligible pool
   joins the fusion, so a related memory is found without shared words ("puppy" finds "hound").

### Semantic recall

Nothing is downloaded: embeddings come from the connection's own `/embeddings` endpoint with the
optional `embedding_model`. The message being answered is embedded at conversation priority with a
two-second limit; any failure means keyword recall only, and the reply goes ahead. After each turn
`MemoryWorker` embeds memories and messages that lack a vector, in batches at maintenance priority.
`memory_vectors` keys each vector by owner, model and the digest of the exact text embedded, so an
edited text never matches an old vector. Deleting a memory, correcting it or redacting a message
deletes its vectors; excluded memories and their source messages never enter the pool, so their
vectors are never ranked. The receipt records whether semantic recall took part.

Eligibility is applied before ranking: only active, non-tentative, in-scope, currently applicable
memories qualify, and source messages of excluded memories are kept out of raw recall too. The
receipt stored with each reply lists included and omitted identities, never content, so deleting
a memory leaves nothing readable behind in old receipts.

How the companion reacts to time apart (`absence_reaction`) and its emotional traits
(`emotional_traits`: a name such as jealousy or guilt over absence, an intensity of mild, moderate
or strong, and an optional note) are part of the character definition (C6). A new character has
none. With neither, the companion is told to be neutral about absence. With traits but a
non-romantic framing, it is told never to express jealousy or possessiveness as romantic
exclusivity. A return after a day or more records a visible, resettable absence mood
(`relationship_moods`, `companion/life/mood.py`) only when a trait's name speaks of absence,
guilt, missing the user, neediness or sulking (`companion/traits.py`). The mood never exceeds that
trait's intensity and stops applying once the trait is removed. Product controls such as pause,
settings and export stay neutral either way.

## Consolidation (M10, M11)

`companion/memory/consolidation.py` runs without a model, at most hourly while automatic memory is
on, after formation and indexing (`POST /api/memory/consolidate` runs it on demand).

- **Episode summaries.** For each finished day with at least four user messages, the summary
  quotes up to three of the user's own sentences that best represent the day, with their exact
  source messages. Recall offers a summary labelled as quoted words and "a reminder, not
  confirmation". A summary is never read by extraction, so it cannot confirm itself or another
  summary. It is skipped while any source is declined or blocked by an exclusion, and deleted with
  any source message. A run handles at most five days and commits nothing if the memory revision
  changed while it worked.
- **Merge proposals.** Two active memories with the same layer and subject whose values share most
  of their words are proposed for merging; nothing merges until the user accepts. Accepting keeps
  the newer one with both sets of sources and makes the older one history (`merged_into_id`), so
  deleting either deletes both. A declined proposal is not made again.
- **Resurfacing.** An item recalled in two of the last six replies comes back only when the user's
  own words match it, so a semantic near-match cannot keep repeating the same anecdote, while a
  direct question still finds it.
- **Related experiences.** When a shared experience or relationship memory is recalled, the
  eligible experience sharing most of its words (a quarter or more) comes along, marked "related
  to" it, at most two per reply. Links are computed from the eligible pool for each reply and never
  stored, so exclusion, correction and deletion apply to them like everything else, and a link
  never claims two memories are the same event or person.

## Memory formation (M7, M8)

`companion/memory/extraction.py` captures explicitly stated facts with rules, without a model:
names, homes and moves, work, likes and dislikes, favourites, boundaries, allergies, relations and
pets, temporary circumstances, dated plans and plan updates ("my interview got postponed").
Questions, hypotheticals, conditionals, quoted text and messages with `*roleplay actions*` produce
nothing, so neither fiction nor the companion's own words can create a real-user fact. Relative
dates ("next Thursday", "ten years ago", "until Friday") resolve against the message's own time in
the user's timezone (`companion/memory/dates.py`); an ambiguous one is kept but marked
`dates_uncertain`.

`companion/memory/formation.py` keeps extraction, validation and commit separate:

- **Queueing.** Only while automatic memory is on, saving a user message queues one job under the
  current permission revision. Nothing is queued while it is off; turning it on does not reach back.
- **Running.** `MemoryWorker` drains the queue after each turn and waits while a reply is being
  written. A job commits only if automatic memory is still on under the same permission revision;
  otherwise it is `stale`. A failure marks the job `failed` and leaves the conversation alone.
- **Committing.** Ordinary stated facts commit as `automatic` memories with their source message.
  Sensitive ones (health, sexuality, religion, politics, finances, legal status, addresses) wait as
  suggestions unless sensitive memory is allowed. An added fact does not advance the memory revision,
  so it never withholds a reply being written; ending an earlier value or changing a plan does.
- **Suggestions.** Accepting one is deliberate permission. A declined suggestion's fingerprint is
  never suggested again, from that message or a later one.
- **Per message.** Remember this commits what the rules find in one of the user's messages (with
  automatic memory off too), or returns a draft for the Remember form. Don't remember this blocks
  extraction from the message and deletes memories extracted from it automatically; the transcript
  stays.

**Model suggestions.** Off by default, and only with automatic memory on, the user can let the
model suggest more (`model_memory_suggestions`). Messages in which the rules found nothing, of six
words or more, go to the chat connection in batches of eight at maintenance priority, so a
conversation interrupts them. Each answer must name a message in the batch and take most of its
words from that message, or it is dropped. Survivors wait as `model_guess` suggestions; keeping one
makes it `confirmed`, and nothing the model says is ever committed on its own. A malformed answer
marks the batch failed; changed permissions make it stale. Each message is sent once.

**Supersession.** Single-valued subjects (`preferred_name`, `home_city`, `work`, `birthday`,
`favourite_*`) hold one current value. A new current value ends the earlier one at its start
(`applies_until`, `ended_by_id`), which stays as history: "I moved to Boston" ends Chicago, "I might
move to Boston" is a proposed plan, and "I lived in Boston ten years ago" ends nothing. A different
value stated without saying it changed ("I live in Denver" while Chicago is current) does not end
anything automatically: it waits as a `conflict` suggestion that shows the value it would replace,
until the user picks one. Remember this on that message is the user's choice and replaces directly.
Spans are half-open, so a value ended at a moment is no longer current at that moment. A correction
is a different thing: a new revision that supersedes a wrong value. Ended facts are recallable
history marked "no longer current"; expired temporary circumstances are not recalled. Open plans
stay commitments after their date, marked "outcome not confirmed"; the Memories view asks whether
such a plan happened, and offers to set a date that was unclear.

## Life simulation (T1–T7)

`companion/life/` turns the character's routine into fictional events.

- **Routine slots.** The character's `schedule` (or a gentle default day) is expanded in the
  companion's timezone into slots keyed `block@local-date`. Wall times resolve with `fold=0`, so a
  daylight-saving change can lengthen, shorten or drop one slot but never adds a second one for the
  same block and day.
- **Cursor.** Each timeline records the real instant its life is simulated through, starting when
  the timeline was created. Reconciling plans a batch from the cursor to now and moves the cursor in
  the same write transaction; it never moves backward. A clock behind the cursor reports
  `clock_behind` and does nothing.
- **Bounded batches.** A return batch needs `return_gap_hours` of unsimulated time and takes at
  most `catch_up_max_events` slots from the last `catch_up_lookback_hours`, spread across that
  window. A 14-day absence costs the same as a one-day absence. Slots overlapping a pause are never
  chosen, which is how resuming skips the paused interval. Catching up a pause is a separate
  request; it records the pause in `pause_catch_ups`, which lifts its block on commits.
  Background batches run only with `background_activity`, one slot per batch and a 24-hour cap.
- **Integrity.** The plan is stored with the batch, so a resumed batch writes the same slots. Each
  event's idempotency key is `life:<timeline>:<slot>`, so a restart, a second process or a retry
  finds the existing event instead of writing another. A batch held by a live process is left
  alone (`in_progress`); one whose lease lapsed is resumed. The batch records the permission
  revision it was planned under and skips its remaining slots if permissions change.
- **Composing, not generating.** `companion/life/composer.py` decides each event without a
  model: the block's kind picks an activity from a fixed catalog (avoiding the last few, and
  leaning toward the character's interests), the
  world source supplies a real place in the character's `home_city` (or the city its `location`
  names), and templates write the
  summary, caption and mood. The choice is seeded by the event key, so a resumed batch composes
  the same event. Typical weather from the city's climate (shared by everyone there that day) moves
  outdoor activities indoors on rainy, very hot or very cold days, and a city's annual event, on the
  Saturday seeded for it each year, can draw the companion out. A circle member's seeded birthday
  takes one leisure or social block: a celebration with them, or a call when they live out of town. About one slot in five is deliberately quiet. With no matching place the
  wording stays generic ("at a café") instead of inventing one.
- **Plans.** An event sometimes adds one plan for a slot in the next week (`kind: plan`, keyed
  `plan:<timeline>:<slot>`). Batches always include a slot a committed plan names, and that slot is
  composed as the planned outing, linked by `details.fulfils`.
- **Unresolved threads.** A slot sometimes opens one small thread from a fixed catalog (a repair,
  a parcel, a waitlist), keyed `thread:<timeline>:<slot>`, with a date from which it settles. The
  first slot on or after that date proposes its outcome, keyed `settled:<thread key>`. At most one
  thread is open at a time.
- **World data.** `companion/life/world.py` defines the `WorldSource` interface
  (`places(city, kinds) -> [Place]`) passed to `create_app(world=...)`. The default is
  `CatalogWorld`, the shipped city data ([world data](world-data.md)); `EmptyWorld` has no places.
- **Social circle and agenda.** `companion/life/circle.py` assembles five supporting people per
  timeline with the world data's circle generator (name, role, age, home, job, routine, haunts), with no model. `companion/life/agenda.py`
  precomputes every subject's routine a week ahead in `life_agenda`, seeded per slot. On open it
  fills in any gap up to 30 days back, and a running server advances it in steps with the same
  result. Each entry records the version it was built from (`basis`), so upcoming entries rebuild
  after a change. Ended entries become `happened`, or `skipped` under a pause. Batches simulate a
  slot from its precomputed entry, so T5 caps only the reviewed, model-phrased part. Social entries
  name a circle member whose agenda is free then.
- **Prepared wording.** `POST /api/life/prepare` (sent while the user types or idles) and each
  background tick phrase the companion's next upcoming agenda entries at `LIFE_SYNTHESIS` priority
  and store the result on the entry. A batch uses it only when the model, address and prompt
  version still match; a rebuilt entry drops it.
- **Optional phrasing.** With a model connection and `phrase_with_model` on, one
  background-priority request (`LIFE_SYNTHESIS`) rewrites the wording in the character's voice.
  The model gets the composed facts only, never the user's memories, and may not add places,
  people or events; a reply that drops the place name, fails to parse or errors keeps the
  template wording. A conversation interrupts phrasing and the batch resumes on the next
  reconcile. Event `inputs` record the template text, world source, composer and prompt versions.
- **Corrections.** A correction is a new committed revision. A place or person in the details that
  the corrected wording no longer names is dropped, so a later image, a fulfilled plan or recall
  never brings back what the user corrected away.
- **Review.** Events are proposed and wait for review unless the user turned on
  `automatic_events`. Commit revalidates the character version, timeline, pause and permission
  revision as before.

## Feed and Today (F1, F2, F4)

`companion/life/feed.py` keeps posts as references to life events (`feed_post_events`). A post
renders each event at its current committed revision, so the feed, chat and recall share one
account of every event and a correction reaches all three. A return batch publishes one digest
post and a background batch one post per event; posts wait until at least one of their events is
committed. Read state, hide/remove, reactions, export and links from chat messages
(`message_post_links`) live beside the posts. A message linked to a post adds that post to the
next reply's context. The image columns record the post's current image job, which only that
job may change ([image generation](images.md)).

`companion/life/today.py` assembles the Today view and records the last visit (`visits`), which
only moves forward.

## Images (F3–F9)

`companion/images/` classifies each request locally before dispatch, routes NSFW to a local
ComfyUI only and refuses Prohibited requests everywhere, then runs it on a ComfyUI server, the
Codex CLI or a hosted image API. Jobs freeze their inputs and record provenance; a late result
never replaces the post's chosen image. See [image generation](images.md).

## Backups

`POST /api/backups` writes a zip with a manifest and a consistent SQLite snapshot beside the
workspace. Restore only targets a new path, checks the format marker and digest, and leaves the
restored workspace paused with automatic memory and background activity off and its saved key
reference cleared. Enabling memory or background activity requires marking the review complete.

## Current context (X1–X3)

`companion/mcp/` looks up real weather, news and local events through MCP servers the user
configures, under a disclosure the user confirms. The app decides when to look something up from
the user's message; the model never gets tools. Lookups are recorded in `context_observations`
with their tool, arguments, destination, location and freshness, quoted into the reply's context
as external data, and listed in the reply's receipt under `outside`. Details, limits and the tested
transports are in [current context tools](context-tools.md). A same-day lookup for the companion's
real city can replace that day's typical weather in the life simulation (`ObservedWorld`).

## Not yet built

A branch map of timelines, LoRA training, reference images
for image requests, durable cross-process scheduling, restore into an existing workspace, and a
Windows installer (the install and launch scripts need Python and Node already present).
