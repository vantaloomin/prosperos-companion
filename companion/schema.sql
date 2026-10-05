-- Prospero Companion workspace schema. One database is one workspace with one focal companion.
-- Separate tables keep each source of truth distinct (PRD M1): character definitions, user
-- statements, committed fictional events, conversation and structured memories.

CREATE TABLE IF NOT EXISTS app_identity (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workspace_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  user_timezone TEXT NOT NULL DEFAULT 'UTC',
  automatic_memory INTEGER NOT NULL DEFAULT 0 CHECK (automatic_memory IN (0, 1)),
  sensitive_memory INTEGER NOT NULL DEFAULT 0 CHECK (sensitive_memory IN (0, 1)),
  share_profile_across_timelines INTEGER NOT NULL DEFAULT 1
    CHECK (share_profile_across_timelines IN (0, 1)),
  background_activity INTEGER NOT NULL DEFAULT 0 CHECK (background_activity IN (0, 1)),
  paused_at TEXT,
  review_required INTEGER NOT NULL DEFAULT 0 CHECK (review_required IN (0, 1)),
  permission_revision INTEGER NOT NULL DEFAULT 1,
  memory_revision INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pauses (
  id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  ended_at TEXT
);

CREATE TABLE IF NOT EXISTS connection (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  base_url TEXT NOT NULL,
  model TEXT NOT NULL,
  credential_ref TEXT,
  max_output_tokens INTEGER NOT NULL,
  context_tokens INTEGER NOT NULL,
  timeout_seconds INTEGER NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS companions (
  id TEXT PRIMARY KEY,
  slot INTEGER NOT NULL UNIQUE DEFAULT 1 CHECK (slot = 1),
  active_version_id TEXT,
  active_timeline_id TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS character_versions (
  id TEXT PRIMARY KEY,
  companion_id TEXT NOT NULL REFERENCES companions(id),
  number INTEGER NOT NULL,
  name TEXT NOT NULL,
  definition TEXT NOT NULL,
  relationship TEXT NOT NULL,
  timezone TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  effective_at TEXT NOT NULL,
  UNIQUE (companion_id, number)
);

CREATE TABLE IF NOT EXISTS timelines (
  id TEXT PRIMARY KEY,
  companion_id TEXT NOT NULL REFERENCES companions(id),
  parent_id TEXT REFERENCES timelines(id),
  forked_after_seq INTEGER,
  status TEXT NOT NULL CHECK (status IN ('active', 'frozen')),
  created_at TEXT NOT NULL,
  frozen_at TEXT
);

CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  timeline_id TEXT NOT NULL REFERENCES timelines(id),
  seq INTEGER NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user', 'companion')),
  text TEXT NOT NULL,
  client_id TEXT UNIQUE,
  reply_to TEXT REFERENCES messages(id),
  status TEXT NOT NULL CHECK (status IN
    ('complete', 'streaming', 'incomplete', 'cancelled', 'failed', 'withheld')),
  active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
  character_version_id TEXT REFERENCES character_versions(id),
  memory_revision INTEGER,
  receipt TEXT,
  error TEXT,
  redacted_at TEXT,
  created_at TEXT NOT NULL,
  completed_at TEXT,
  UNIQUE (timeline_id, seq)
);
CREATE INDEX IF NOT EXISTS messages_reply ON messages(reply_to);

CREATE TABLE IF NOT EXISTS life_events (
  id TEXT PRIMARY KEY,
  companion_id TEXT NOT NULL REFERENCES companions(id),
  timeline_id TEXT NOT NULL REFERENCES timelines(id),
  idempotency_key TEXT NOT NULL UNIQUE,
  kind TEXT NOT NULL CHECK (kind IN ('routine', 'plan', 'ordinary', 'thread')),
  status TEXT NOT NULL CHECK (status IN ('proposed', 'committed', 'rejected', 'superseded')),
  summary TEXT NOT NULL,
  details TEXT NOT NULL DEFAULT '{}',
  starts_at TEXT NOT NULL,
  ends_at TEXT NOT NULL,
  character_version_id TEXT NOT NULL REFERENCES character_versions(id),
  permission_revision INTEGER NOT NULL,
  inputs TEXT NOT NULL DEFAULT '{}',
  revision INTEGER NOT NULL DEFAULT 1,
  supersedes_id TEXT REFERENCES life_events(id),
  rejection TEXT,
  created_at TEXT NOT NULL,
  decided_at TEXT
);

CREATE TABLE IF NOT EXISTS memories (
  id TEXT PRIMARY KEY,
  companion_id TEXT NOT NULL REFERENCES companions(id),
  timeline_id TEXT NOT NULL REFERENCES timelines(id),
  layer TEXT NOT NULL CHECK (layer IN
    ('user_fact', 'shared_experience', 'plan', 'temporary', 'relationship', 'companion_life')),
  subject TEXT NOT NULL,
  value TEXT NOT NULL,
  reality TEXT NOT NULL CHECK (reality IN ('real', 'fiction')),
  authority TEXT NOT NULL CHECK (authority IN ('stated', 'confirmed', 'tentative')),
  status TEXT NOT NULL CHECK (status IN ('active', 'superseded', 'excluded')),
  boundary INTEGER NOT NULL DEFAULT 0 CHECK (boundary IN (0, 1)),
  pinned INTEGER NOT NULL DEFAULT 0 CHECK (pinned IN (0, 1)),
  sensitive INTEGER NOT NULL DEFAULT 0 CHECK (sensitive IN (0, 1)),
  plan_status TEXT CHECK (plan_status IN
    ('proposed', 'agreed', 'postponed', 'cancelled', 'completed')),
  event_id TEXT REFERENCES life_events(id),
  stated_at TEXT NOT NULL,
  applies_from TEXT,
  applies_until TEXT,
  revision INTEGER NOT NULL DEFAULT 1,
  supersedes_id TEXT REFERENCES memories(id),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS memories_current ON memories(companion_id, status, layer);

CREATE TABLE IF NOT EXISTS memory_sources (
  memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
  message_id TEXT NOT NULL REFERENCES messages(id),
  PRIMARY KEY (memory_id, message_id)
);

-- Statements the user asked not to turn into structured memory (M7, M12).
CREATE TABLE IF NOT EXISTS memory_declines (
  message_id TEXT PRIMARY KEY REFERENCES messages(id),
  created_at TEXT NOT NULL
);

-- Non-content markers that stop a deleted record being reintroduced (M5, M12).
CREATE TABLE IF NOT EXISTS deletion_markers (
  target_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  deleted_at TEXT NOT NULL
);

-- Life simulation (PRD T3–T7). Limits are user-visible and bounded by tested ceilings.
CREATE TABLE IF NOT EXISTS life_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  automatic_events INTEGER NOT NULL DEFAULT 0 CHECK (automatic_events IN (0, 1)),
  catch_up_on_return INTEGER NOT NULL DEFAULT 1 CHECK (catch_up_on_return IN (0, 1)),
  phrase_with_model INTEGER NOT NULL DEFAULT 1 CHECK (phrase_with_model IN (0, 1)),
  catch_up_max_events INTEGER NOT NULL DEFAULT 3,
  catch_up_lookback_hours INTEGER NOT NULL DEFAULT 48,
  return_gap_hours INTEGER NOT NULL DEFAULT 4,
  background_interval_minutes INTEGER NOT NULL DEFAULT 60,
  background_daily_events INTEGER NOT NULL DEFAULT 3,
  updated_at TEXT NOT NULL
);

-- How far each timeline's fictional time has been simulated. It only moves forward, so a clock
-- moving backward or a second launch can never simulate the same real interval twice.
CREATE TABLE IF NOT EXISTS life_cursors (
  timeline_id TEXT PRIMARY KEY REFERENCES timelines(id),
  simulated_through TEXT NOT NULL,
  last_reconciled_at TEXT,
  updated_at TEXT NOT NULL
);

-- One catch-up or background batch. The plan is fixed when the batch is created, so a batch
-- resumed after a restart produces the same slots and its events stay idempotent.
CREATE TABLE IF NOT EXISTS life_runs (
  id TEXT PRIMARY KEY,
  timeline_id TEXT NOT NULL REFERENCES timelines(id),
  run_key TEXT NOT NULL UNIQUE,
  mode TEXT NOT NULL CHECK (mode IN ('return', 'background')),
  status TEXT NOT NULL CHECK (status IN ('planned', 'running', 'completed', 'failed', 'interrupted')),
  window_start TEXT NOT NULL,
  window_end TEXT NOT NULL,
  plan TEXT NOT NULL,
  results TEXT NOT NULL DEFAULT '[]',
  character_version_id TEXT NOT NULL REFERENCES character_versions(id),
  permission_revision INTEGER NOT NULL,
  owner TEXT,
  lease_until TEXT,
  attempts INTEGER NOT NULL DEFAULT 0,
  error TEXT,
  created_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT
);
CREATE INDEX IF NOT EXISTS life_runs_timeline ON life_runs(timeline_id, created_at);

-- Private feed (PRD F1, F2, F4). A post shows committed events by reference, so a corrected
-- event changes the post too, and a rejected proposal never appears.
CREATE TABLE IF NOT EXISTS feed_posts (
  id TEXT PRIMARY KEY,
  timeline_id TEXT NOT NULL REFERENCES timelines(id),
  kind TEXT NOT NULL CHECK (kind IN ('event', 'digest')),
  idempotency_key TEXT NOT NULL UNIQUE,
  run_id TEXT REFERENCES life_runs(id),
  intro TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'visible' CHECK (status IN ('visible', 'hidden', 'removed')),
  reaction TEXT,
  occurs_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  read_at TEXT,
  removed_at TEXT,
  -- Hook for a later image job: state of the post's illustration, never blocking its text.
  image_status TEXT NOT NULL DEFAULT 'none' CHECK (image_status IN
    ('none', 'queued', 'running', 'completed', 'failed', 'cancelled', 'interrupted')),
  image_job_id TEXT,
  image_ref TEXT,
  image_error TEXT,
  image_updated_at TEXT
);
CREATE INDEX IF NOT EXISTS feed_posts_order ON feed_posts(timeline_id, occurs_at, id);

CREATE TABLE IF NOT EXISTS feed_post_events (
  post_id TEXT NOT NULL REFERENCES feed_posts(id),
  event_id TEXT NOT NULL REFERENCES life_events(id),
  position INTEGER NOT NULL,
  PRIMARY KEY (post_id, event_id)
);

-- A chat message written in reply to a post (PRD F1).
CREATE TABLE IF NOT EXISTS message_post_links (
  message_id TEXT PRIMARY KEY REFERENCES messages(id),
  post_id TEXT NOT NULL REFERENCES feed_posts(id)
);

-- When the user last looked at Today; only moves forward.
CREATE TABLE IF NOT EXISTS visits (
  timeline_id TEXT PRIMARY KEY REFERENCES timelines(id),
  last_seen_at TEXT NOT NULL
);

-- Visible, resettable relationship mood from the user's absence (PRD C6, M4). Only created
-- when the character has an absence trait; never a hidden score.
CREATE TABLE IF NOT EXISTS relationship_moods (
  id TEXT PRIMARY KEY,
  timeline_id TEXT NOT NULL REFERENCES timelines(id),
  kind TEXT NOT NULL CHECK (kind IN ('absence')),
  away_from TEXT NOT NULL,
  away_until TEXT NOT NULL,
  intensity INTEGER NOT NULL CHECK (intensity BETWEEN 1 AND 3),
  traits TEXT NOT NULL,
  character_version_id TEXT NOT NULL REFERENCES character_versions(id),
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  cleared_at TEXT,
  UNIQUE (timeline_id, kind, away_from)
);

-- Paused intervals the user chose to catch up (PRD T6); otherwise a pause blocks its interval.
CREATE TABLE IF NOT EXISTS pause_catch_ups (
  pause_id TEXT PRIMARY KEY REFERENCES pauses(id),
  requested_at TEXT NOT NULL
);
