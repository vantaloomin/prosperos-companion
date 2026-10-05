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
