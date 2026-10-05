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
| `timelines` | The active timeline and any frozen ones (C4) | One active timeline advances with real time |
| `messages` | User messages and every reply attempt, with status | Only a `complete`, `active` reply is the conversational response |
| `life_events` | Proposed, committed, rejected and superseded fictional events (T2–T3, T7) | Committed events are the single account shared by chat, feed and recall |
| `memories`, `memory_sources` | Typed personal memories with sources (M6–M12) | `stated`/`confirmed` reach context; `tentative` does not |
| `memory_declines`, `deletion_markers` | Don't-remember choices and non-content deletion markers | Block re-extraction and reintroduction |
| `workspace_settings`, `pauses` | Permissions, memory revision and pause intervals | Revisions make queued work detectably stale |

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
   Semantic rankings plug into the same fusion later.

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
- **Writing.** With a model connection, each slot is one background-priority request
  (`LIFE_SYNTHESIS`) that a conversation interrupts; the batch resumes on the next reconcile.
  The model sees the character, the block and the last five committed events, never the user's
  memories, and may answer that the stretch was quiet. Unusable output leaves the slot quiet.
  Without a connection every slot stays quiet.
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
next reply's context. The image columns are a hook for the later image job, which may only
complete the job currently recorded on the post.

`companion/life/today.py` assembles the Today view and records the last visit (`visits`), which
only moves forward.

## Backups

`POST /api/backups` writes a zip with a manifest and a consistent SQLite snapshot beside the
workspace. Restore only targets a new path, checks the format marker and digest, and leaves the
restored workspace paused with automatic memory and background activity off and its saved key
reference cleared. Enabling memory or background activity requires marking the review complete.

## Not yet built

Interface, timeline forking, automatic memory extraction, semantic embeddings, plans and threads
generated by the simulation, MCP tools, image generation and LoRA training, durable cross-process scheduling, restore into an existing
workspace, and packaging.
