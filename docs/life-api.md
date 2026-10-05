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

`status` is `running`, `completed`, `interrupted` (a conversation took priority or the model was
unreachable; the next reconcile resumes it), or `failed` (shown with `error`). Each result's
`outcome` is:

- `proposed`: an event awaiting the user's review (automatic events are off).
- `committed`: an event that is now part of the companion's life.
- `rejected`: the event was made stale by a pause, character change or permission change (`reason`).
- `quiet`: nothing notable happened, or no model is connected (`reason`). Quiet stretches are valid.
- `skipped`: permissions changed or the timeline switched before this slot ran.

`GET /api/life/runs?limit=20` lists recent batches, newest first.

## Reviewing proposed events

With automatic events off (the default), catch-up only proposes. Proposed events appear in
`GET /api/events?history=true` with `status: "proposed"`. Commit or reject them with the existing
`POST /api/events/{id}/commit` and `POST /api/events/{id}/reject`. A commit can still come back
`rejected` with a `rejection` reason when the event became stale. Only committed events reach chat,
the feed and recall.

Life events carry `details` for display: `label` (routine block), `activity` (block kind),
`local_date`, `timezone`, `post` (an optional caption in the companion's voice) and `mood`.

## Limits and permissions

```http
GET /api/life/settings
PUT /api/life/settings
```

| Field | Default | Range | Meaning |
| --- | --- | --- | --- |
| `automatic_events` | `false` | | Commit ordinary events without review (PRD T3). Changing it advances the permission revision, so prepared work is revalidated. |
| `catch_up_on_return` | `true` | | Run a batch on return (PRD T4). |
| `catch_up_max_events` | 3 | 0–6 | Most events in one batch, however long the absence (PRD T5). |
| `catch_up_lookback_hours` | 48 | 6–336 | Only slots this recent are written; older absence stays uneventful. |
| `return_gap_hours` | 4 | 1–48 | Unsimulated time needed before a return batch runs. |
| `background_interval_minutes` | 60 | 15–1440 | Gap between background batches. |
| `background_daily_events` | 3 | 0–8 | Most background events in 24 hours; one per batch. |

Background batches also need `background_activity: true` in `PUT /api/settings`. Pausing
(`POST /api/pause`) stops new batches, and resuming skips the paused interval rather than
generating it.

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
