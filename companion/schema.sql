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
  -- 'default' until set: 'pc' follows this PC's timezone, 'chosen' was picked in Settings and is kept.
  user_timezone_source TEXT NOT NULL DEFAULT 'default' CHECK (user_timezone_source IN ('default', 'pc', 'chosen')),
  automatic_memory INTEGER NOT NULL DEFAULT 0 CHECK (automatic_memory IN (0, 1)),
  sensitive_memory INTEGER NOT NULL DEFAULT 0 CHECK (sensitive_memory IN (0, 1)),
  share_profile_across_timelines INTEGER NOT NULL DEFAULT 1
    CHECK (share_profile_across_timelines IN (0, 1)),
  background_activity INTEGER NOT NULL DEFAULT 0 CHECK (background_activity IN (0, 1)),
  model_memory_suggestions INTEGER NOT NULL DEFAULT 0 CHECK (model_memory_suggestions IN (0, 1)),
  -- How the chat looks; presentation only, the same messages in every style.
  chat_style TEXT NOT NULL DEFAULT 'feed' CHECK (chat_style IN ('feed', 'bubbles', 'community', 'retro', 'novel')),
  chat_sounds INTEGER NOT NULL DEFAULT 0 CHECK (chat_sounds IN (0, 1)),
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

-- Before model profiles there was one connection. Kept so an older workspace can be read; opening
-- it moves the row into a profile (companion/text_models.py adopt_legacy) and leaves this empty.
CREATE TABLE IF NOT EXISTS connection (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  base_url TEXT NOT NULL,
  model TEXT NOT NULL,
  credential_ref TEXT,
  max_output_tokens INTEGER NOT NULL,
  context_tokens INTEGER NOT NULL,
  timeout_seconds INTEGER NOT NULL,
  updated_at TEXT NOT NULL,
  -- Optional; when set, semantic recall uses this model through the same connection's /embeddings.
  embedding_model TEXT
);

-- Settings > Models: one provider, model and saved key each (config is JSON; the key lives in the
-- OS credential vault under credential_ref).
CREATE TABLE IF NOT EXISTS model_profiles (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  config TEXT NOT NULL,
  credential_ref TEXT,
  revision INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- Which profile does each job; a job without a row uses the 'chat' job's profile.
CREATE TABLE IF NOT EXISTS model_routes (
  job TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL REFERENCES model_profiles(id) ON DELETE CASCADE,
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
  frozen_at TEXT,
  -- A historical edit (C4): the parent's history before `forked_at` is copied in, and the edited
  -- words wait in `draft` until they are sent on this timeline.
  label TEXT NOT NULL DEFAULT '',
  fork_message_id TEXT,
  forked_at TEXT,
  draft TEXT,
  activated_at TEXT
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
  -- For a message copied into a forked timeline, the message it was first written as.
  origin_id TEXT,
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
  updated_at TEXT NOT NULL,
  -- Normalised subject; single-valued keys such as home_city hold one current value (M8).
  subject_key TEXT NOT NULL DEFAULT '',
  origin TEXT NOT NULL DEFAULT 'user' CHECK (origin IN ('user', 'automatic', 'suggestion')),
  -- The later memory whose start ended this one ("I moved to Boston" ends Chicago, which stays history).
  ended_by_id TEXT,
  dates_uncertain INTEGER NOT NULL DEFAULT 0 CHECK (dates_uncertain IN (0, 1)),
  -- Set when the user accepted merging this memory into a near-identical one (M11).
  merged_into_id TEXT
);
CREATE INDEX IF NOT EXISTS memories_current ON memories(companion_id, status, layer);

-- Automatic extraction work, one job per user message, queued only while automatic memory is on.
-- A job runs only under the permission revision it was queued with (M7).
CREATE TABLE IF NOT EXISTS memory_jobs (
  message_id TEXT PRIMARY KEY REFERENCES messages(id),
  permission_revision INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('queued', 'done', 'stale', 'skipped', 'failed')),
  queued_at TEXT NOT NULL,
  finished_at TEXT,
  error TEXT,
  -- Model suggestions for this message, when enabled: NULL (not yet), done, skipped, failed or stale.
  model_status TEXT
);
CREATE INDEX IF NOT EXISTS memory_jobs_status ON memory_jobs(status, queued_at);

-- Extracted candidates. Committed ones point at their memory; pending ones are suggestions the user
-- reviews. A declined fingerprint is never suggested again (M7).
CREATE TABLE IF NOT EXISTS memory_candidates (
  id TEXT PRIMARY KEY,
  companion_id TEXT NOT NULL REFERENCES companions(id),
  timeline_id TEXT NOT NULL REFERENCES timelines(id),
  message_id TEXT NOT NULL REFERENCES messages(id),
  source TEXT NOT NULL CHECK (source IN ('rule', 'model')),
  rule TEXT NOT NULL,
  proposal TEXT NOT NULL,
  fingerprint TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending', 'committed', 'declined', 'dismissed')),
  reason TEXT,
  memory_id TEXT,
  created_at TEXT NOT NULL,
  resolved_at TEXT,
  UNIQUE (message_id, fingerprint)
);
CREATE INDEX IF NOT EXISTS memory_candidates_status ON memory_candidates(companion_id, status);

-- Embeddings of memories and messages for semantic recall, keyed by the digest of the text embedded.
CREATE TABLE IF NOT EXISTS memory_vectors (
  owner_kind TEXT NOT NULL CHECK (owner_kind IN ('memory', 'message')),
  owner_id TEXT NOT NULL,
  model TEXT NOT NULL,
  digest TEXT NOT NULL,
  vector BLOB NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (owner_kind, owner_id, model)
);

-- Episode summaries (M11): quotes of the user's own sentences from one day, with exact sources.
-- A retrieval aid only; dropped when any source is deleted, declined or blocked.
CREATE TABLE IF NOT EXISTS memory_summaries (
  id TEXT PRIMARY KEY,
  timeline_id TEXT NOT NULL REFERENCES timelines(id),
  day TEXT NOT NULL,
  text TEXT NOT NULL,
  source_message_ids TEXT NOT NULL,
  basis TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (timeline_id, day)
);

-- Consolidation proposals the user decides on, such as merging two near-identical memories.
CREATE TABLE IF NOT EXISTS memory_proposals (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('merge')),
  keep_id TEXT NOT NULL,
  merge_id TEXT NOT NULL,
  fingerprint TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL CHECK (status IN ('pending', 'accepted', 'declined')),
  created_at TEXT NOT NULL,
  resolved_at TEXT
);

-- What memory formation did, by identity and reason code only, so deletion leaves no content here.
CREATE TABLE IF NOT EXISTS memory_activity (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL,
  action TEXT NOT NULL,
  memory_id TEXT,
  candidate_id TEXT,
  message_id TEXT,
  detail TEXT
);

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

-- Cities the user wrote or copied (PRD W5). Built-in cities ship as files and are never stored here.
CREATE TABLE IF NOT EXISTS world_cities (
  id TEXT PRIMARY KEY,
  definition TEXT NOT NULL,
  revision INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- The companion's social circle (PRD T8): supporting characters assembled from world data and a
-- seed. Never the user, never a real person, never a source of user facts.
CREATE TABLE IF NOT EXISTS circle_people (
  id TEXT PRIMARY KEY,
  timeline_id TEXT NOT NULL REFERENCES timelines(id),
  ordinal INTEGER NOT NULL,
  seed TEXT NOT NULL,
  name TEXT NOT NULL,
  role TEXT NOT NULL,
  career TEXT NOT NULL,
  details TEXT NOT NULL,
  schedule TEXT NOT NULL,
  revision INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'removed')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (timeline_id, ordinal)
);

-- Precomputed schedules for the companion and the circle (PRD T9). Upcoming entries stay hidden;
-- `basis` names the character version or person revision an entry was built from.
CREATE TABLE IF NOT EXISTS life_agenda (
  id TEXT PRIMARY KEY,
  timeline_id TEXT NOT NULL REFERENCES timelines(id),
  subject TEXT NOT NULL,
  slot_key TEXT NOT NULL,
  starts_at TEXT NOT NULL,
  ends_at TEXT NOT NULL,
  local_date TEXT NOT NULL,
  block TEXT NOT NULL,
  entry TEXT,
  basis TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'upcoming' CHECK (status IN ('upcoming', 'happened', 'skipped')),
  prepared TEXT,
  created_at TEXT NOT NULL,
  UNIQUE (timeline_id, subject, slot_key)
);
CREATE INDEX IF NOT EXISTS life_agenda_due ON life_agenda (timeline_id, status, ends_at);

CREATE TABLE IF NOT EXISTS agenda_cursors (
  timeline_id TEXT NOT NULL REFERENCES timelines(id),
  subject TEXT NOT NULL,
  through TEXT NOT NULL,
  PRIMARY KEY (timeline_id, subject)
);

-- Image generation (PRD F3–F9). Every backend is off until the user configures it; text never
-- waits for an image.
CREATE TABLE IF NOT EXISTS image_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  automatic_images INTEGER NOT NULL DEFAULT 0 CHECK (automatic_images IN (0, 1)),
  automatic_since TEXT,
  daily_limit INTEGER NOT NULL DEFAULT 3,
  queue_limit INTEGER NOT NULL DEFAULT 6,
  fallback INTEGER NOT NULL DEFAULT 0 CHECK (fallback IN (0, 1)),
  aspect TEXT NOT NULL DEFAULT 'landscape' CHECK (aspect IN ('square', 'landscape', 'portrait')),
  style TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL
);

-- A configured backend. Secrets live in the OS vault under `credential_ref`, never here.
CREATE TABLE IF NOT EXISTS image_backends (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('comfyui', 'codex', 'hosted')),
  provider TEXT NOT NULL,
  label TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
  position INTEGER NOT NULL,
  config TEXT NOT NULL DEFAULT '{}',
  credential_ref TEXT,
  -- The user marked a non-loopback ComfyUI address as a machine they control (F6).
  controlled_machine INTEGER NOT NULL DEFAULT 0 CHECK (controlled_machine IN (0, 1)),
  concurrency INTEGER NOT NULL DEFAULT 1,
  -- Set when the backend must not run until the user acts, such as signing in to Codex again (F8).
  blocked_reason TEXT,
  disclosure_accepted_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- One image request. `inputs` freezes what was asked so a retry can repeat it exactly (F4).
CREATE TABLE IF NOT EXISTS image_jobs (
  id TEXT PRIMARY KEY,
  post_id TEXT NOT NULL REFERENCES feed_posts(id),
  timeline_id TEXT NOT NULL REFERENCES timelines(id),
  status TEXT NOT NULL CHECK (status IN
    ('queued', 'running', 'completed', 'failed', 'cancelled', 'interrupted')),
  trigger TEXT NOT NULL CHECK (trigger IN ('manual', 'automatic', 'retry', 'fallback')),
  retry_of TEXT REFERENCES image_jobs(id),
  inputs TEXT NOT NULL,
  character_version_id TEXT NOT NULL REFERENCES character_versions(id),
  classification TEXT NOT NULL CHECK (classification IN ('safe', 'nsfw', 'prohibited')),
  classification_reasons TEXT NOT NULL DEFAULT '[]',
  classifier TEXT NOT NULL,
  routing_reason TEXT NOT NULL,
  backend_id TEXT,
  backend_kind TEXT,
  provider TEXT,
  model TEXT,
  workflow TEXT,
  identity_method TEXT,
  seed INTEGER,
  remote_id TEXT,
  output_file TEXT,
  raw_file TEXT,
  width INTEGER,
  height INTEGER,
  usage TEXT,
  error TEXT,
  error_code TEXT,
  created_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT
);
CREATE INDEX IF NOT EXISTS image_jobs_post ON image_jobs(post_id, created_at);
CREATE INDEX IF NOT EXISTS image_jobs_status ON image_jobs(status, created_at);

-- Current context through MCP (PRD X1-X3). The user's own location is kept here, apart from the
-- companion's fictional location in its character definition.
CREATE TABLE IF NOT EXISTS context_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  user_place TEXT NOT NULL DEFAULT '',
  user_latitude REAL,
  user_longitude REAL,
  -- Links pasted in chat are opened on this computer so the companion can talk about them.
  read_links INTEGER NOT NULL DEFAULT 1 CHECK (read_links IN (0, 1)),
  updated_at TEXT NOT NULL
);

-- MCP servers the user configured. Nothing runs until a category on it is enabled.
CREATE TABLE IF NOT EXISTS context_services (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  transport TEXT NOT NULL CHECK (transport IN ('stdio', 'http')),
  command TEXT,
  url TEXT,
  credential_ref TEXT,
  secret_name TEXT NOT NULL DEFAULT '',
  tools TEXT NOT NULL DEFAULT '[]',
  server_info TEXT,
  checked_at TEXT,
  check_error TEXT,
  cooldown_until TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- Which tool answers a category, which arguments it receives and when it may run. `approved`
-- is the digest of the disclosure the user confirmed; a changed mapping needs a new confirmation.
CREATE TABLE IF NOT EXISTS context_tools (
  service_id TEXT NOT NULL REFERENCES context_services(id) ON DELETE CASCADE,
  -- The categories are checked by the app (companion/mcp/services.py CATEGORIES).
  category TEXT NOT NULL,
  tool TEXT NOT NULL,
  arguments TEXT NOT NULL,
  run_in TEXT NOT NULL DEFAULT '["conversation"]',
  enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
  approved TEXT,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (service_id, category)
);

-- Every lookup attempt with what was sent, where, when and how long it counts as fresh.
CREATE TABLE IF NOT EXISTS context_observations (
  id TEXT PRIMARY KEY,
  service_id TEXT REFERENCES context_services(id) ON DELETE SET NULL,
  service_name TEXT NOT NULL,
  category TEXT NOT NULL,
  purpose TEXT NOT NULL,
  tool TEXT NOT NULL,
  arguments TEXT NOT NULL,
  destination TEXT NOT NULL,
  location TEXT,
  status TEXT NOT NULL CHECK (status IN ('ok', 'failed', 'refused')),
  content TEXT NOT NULL DEFAULT '',
  structured TEXT,
  error_code TEXT,
  error TEXT,
  attempts INTEGER NOT NULL DEFAULT 1,
  requested_at TEXT NOT NULL,
  retrieved_at TEXT,
  fresh_until TEXT
);
CREATE INDEX IF NOT EXISTS context_observations_recent ON context_observations (category, requested_at);

-- Which observations a user message's reply was given.
CREATE TABLE IF NOT EXISTS context_uses (
  message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
  observation_id TEXT NOT NULL REFERENCES context_observations(id) ON DELETE CASCADE,
  PRIMARY KEY (message_id, observation_id)
);

-- Character LoRA maker (PRD "Character LoRA maker requirements"). Files live in `lora/` beside the
-- workspace database; these tables hold what they are, where they came from and who chose them.
CREATE TABLE IF NOT EXISTS lora_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  trainer TEXT NOT NULL DEFAULT 'ai-toolkit',
  -- The trainer's own Python interpreter and checkout; the app never installs either.
  python_path TEXT NOT NULL DEFAULT '',
  trainer_dir TEXT NOT NULL DEFAULT '',
  base_model TEXT NOT NULL DEFAULT 'krea/Krea-2-Raw',
  -- ComfyUI's models/loras folder, so an adopted adapter can be copied where ComfyUI finds it.
  comfy_lora_dir TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL
);

-- One reference picture. The original file is never changed; a crop is a separate copy.
CREATE TABLE IF NOT EXISTS lora_references (
  id TEXT PRIMARY KEY,
  companion_id TEXT NOT NULL REFERENCES companions(id),
  file TEXT NOT NULL,
  original_name TEXT NOT NULL DEFAULT '',
  media_type TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  -- 64-bit difference hash computed by the interface, for near-duplicate warnings.
  dhash TEXT,
  width INTEGER NOT NULL,
  height INTEGER NOT NULL,
  bytes INTEGER NOT NULL,
  rights TEXT NOT NULL DEFAULT 'unknown' CHECK (rights IN
    ('own_work', 'commissioned', 'licensed', 'generated', 'unknown')),
  source_note TEXT NOT NULL DEFAULT '',
  role TEXT NOT NULL DEFAULT 'train' CHECK (role IN ('train', 'evaluation', 'excluded')),
  exclusion_reason TEXT NOT NULL DEFAULT '',
  caption TEXT NOT NULL DEFAULT '',
  caption_origin TEXT NOT NULL DEFAULT 'empty' CHECK (caption_origin IN ('empty', 'suggested', 'edited')),
  crop TEXT,
  crop_file TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (companion_id, sha256)
);

-- A trained or imported adapter file and its provenance.
CREATE TABLE IF NOT EXISTS lora_adapters (
  id TEXT PRIMARY KEY,
  companion_id TEXT NOT NULL REFERENCES companions(id),
  origin TEXT NOT NULL CHECK (origin IN ('trained', 'imported')),
  run_id TEXT,
  step INTEGER,
  name TEXT NOT NULL,
  file TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  bytes INTEGER NOT NULL,
  format TEXT NOT NULL CHECK (format IN ('lora', 'lokr', 'unknown')),
  base_model TEXT NOT NULL,
  trainer TEXT NOT NULL DEFAULT '',
  trigger TEXT NOT NULL DEFAULT '',
  license_note TEXT NOT NULL DEFAULT '',
  metadata TEXT NOT NULL DEFAULT '{}',
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  -- Removing an adapter deletes its file but keeps this record, since images may name it.
  removed_at TEXT
);

-- How images draw the character from a point in time (PRD F2). Jobs freeze the version they used,
-- so adopting a new one never changes an image already made.
CREATE TABLE IF NOT EXISTS appearance_versions (
  id TEXT PRIMARY KEY,
  companion_id TEXT NOT NULL REFERENCES companions(id),
  number INTEGER NOT NULL,
  method TEXT NOT NULL CHECK (method IN ('text', 'lora')),
  adapter_id TEXT REFERENCES lora_adapters(id),
  strength REAL NOT NULL DEFAULT 1.0,
  comfy_name TEXT,
  note TEXT NOT NULL DEFAULT '',
  adopted_at TEXT NOT NULL,
  UNIQUE (companion_id, number)
);

CREATE TABLE IF NOT EXISTS appearance_current (
  companion_id TEXT PRIMARY KEY REFERENCES companions(id),
  version_id TEXT NOT NULL REFERENCES appearance_versions(id)
);

-- One training run: the Configure and Train steps. `options`, `trainer_config` and `dataset` freeze
-- what was asked and what the trainer received, so the adapter's provenance survives.
CREATE TABLE IF NOT EXISTS lora_runs (
  id TEXT PRIMARY KEY,
  companion_id TEXT NOT NULL REFERENCES companions(id),
  name TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'cancelled', 'interrupted')),
  trainer TEXT NOT NULL,
  trainer_tested TEXT NOT NULL,
  base_model TEXT NOT NULL,
  trigger TEXT NOT NULL,
  options TEXT NOT NULL,
  trainer_config TEXT NOT NULL,
  dataset TEXT NOT NULL,
  folder TEXT NOT NULL,
  attempt INTEGER NOT NULL DEFAULT 1,
  resumed_from_step INTEGER,
  -- Only what the trainer printed; never estimated.
  progress_step INTEGER,
  progress_total INTEGER,
  progress_at TEXT,
  checkpoints TEXT NOT NULL DEFAULT '[]',
  adapter_id TEXT,
  pid INTEGER,
  exit_code INTEGER,
  log_tail TEXT NOT NULL DEFAULT '',
  error TEXT,
  error_code TEXT,
  disclosure_accepted_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT
);
CREATE INDEX IF NOT EXISTS lora_runs_companion ON lora_runs(companion_id, created_at);

-- The Evaluate step: a fixed set of prompts rendered with an adapter (and, for comparison, from the
-- text description alone) on a local ComfyUI backend. Every output and failure is kept.
CREATE TABLE IF NOT EXISTS lora_evaluations (
  id TEXT PRIMARY KEY,
  companion_id TEXT NOT NULL REFERENCES companions(id),
  adapter_id TEXT NOT NULL REFERENCES lora_adapters(id),
  set_version INTEGER NOT NULL,
  strength REAL NOT NULL,
  comfy_name TEXT NOT NULL,
  backend_id TEXT,
  held_out TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'cancelled', 'interrupted')),
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS lora_eval_images (
  id TEXT PRIMARY KEY,
  evaluation_id TEXT NOT NULL REFERENCES lora_evaluations(id),
  position INTEGER NOT NULL,
  prompt_key TEXT NOT NULL,
  variant TEXT NOT NULL CHECK (variant IN ('lora', 'text')),
  prompt TEXT NOT NULL,
  negative TEXT NOT NULL,
  seed INTEGER NOT NULL,
  width INTEGER NOT NULL,
  height INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN
    ('queued', 'running', 'completed', 'failed', 'cancelled', 'interrupted')),
  classification TEXT NOT NULL,
  workflow TEXT,
  model TEXT,
  output_file TEXT,
  error TEXT,
  rating TEXT NOT NULL DEFAULT '' CHECK (rating IN ('', 'good', 'weak')),
  started_at TEXT,
  finished_at TEXT
);
CREATE INDEX IF NOT EXISTS lora_eval_images_evaluation ON lora_eval_images(evaluation_id, position);

-- Candidate reference pictures generated in the Prepare step from an editable shot list. One
-- seed and one base description keep a set consistent. Each shot is classified and routed like
-- any image request; nothing joins the dataset until the user keeps it.
CREATE TABLE IF NOT EXISTS lora_generations (
  id TEXT PRIMARY KEY,
  companion_id TEXT NOT NULL REFERENCES companions(id),
  base TEXT NOT NULL,
  seed INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'cancelled', 'interrupted')),
  created_at TEXT NOT NULL,
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS lora_gen_images (
  id TEXT PRIMARY KEY,
  generation_id TEXT NOT NULL REFERENCES lora_generations(id),
  position INTEGER NOT NULL,
  label TEXT NOT NULL,
  shot TEXT NOT NULL,
  prompt TEXT NOT NULL,
  negative TEXT NOT NULL,
  aspect TEXT NOT NULL CHECK (aspect IN ('square', 'landscape', 'portrait')),
  seed INTEGER NOT NULL,
  classification TEXT NOT NULL,
  reasons TEXT NOT NULL DEFAULT '[]',
  route_reason TEXT NOT NULL DEFAULT '',
  backend_id TEXT,
  backend_label TEXT,
  backend_kind TEXT,
  status TEXT NOT NULL CHECK (status IN
    ('queued', 'running', 'completed', 'failed', 'cancelled', 'interrupted')),
  error TEXT,
  output_file TEXT,
  width INTEGER,
  height INTEGER,
  used_seed INTEGER,
  model TEXT,
  workflow TEXT,
  decision TEXT CHECK (decision IN ('kept', 'discarded')),
  reference_id TEXT,
  started_at TEXT,
  finished_at TEXT
);
CREATE INDEX IF NOT EXISTS lora_gen_images_generation ON lora_gen_images(generation_id, position);

-- Desktop notifications (PRD compute and job control): off by default; quiet hours, preview
-- privacy and a frequency cap. Settings never depend on the character's traits.
CREATE TABLE IF NOT EXISTS notification_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
  quiet_start TEXT NOT NULL DEFAULT '22:00',
  quiet_end TEXT NOT NULL DEFAULT '08:00',
  preview TEXT NOT NULL DEFAULT 'name' CHECK (preview IN ('full', 'name', 'private')),
  daily_cap INTEGER NOT NULL DEFAULT 3,
  min_gap_minutes INTEGER NOT NULL DEFAULT 120,
  updated_at TEXT NOT NULL
);

-- One per post a background batch published while notifications were on. Several waiting at
-- delivery collapse into one digest delivery.
CREATE TABLE IF NOT EXISTS notifications (
  id TEXT PRIMARY KEY,
  post_id TEXT NOT NULL UNIQUE REFERENCES feed_posts(id),
  status TEXT NOT NULL CHECK (status IN ('queued', 'delivered', 'digested', 'dropped', 'cancelled')),
  delivery_id TEXT,
  reason TEXT,
  created_at TEXT NOT NULL,
  settled_at TEXT
);
CREATE INDEX IF NOT EXISTS notifications_status ON notifications(status, created_at);

CREATE TABLE IF NOT EXISTS notification_deliveries (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('post', 'digest', 'message')),
  post_count INTEGER NOT NULL,
  delivered_at TEXT NOT NULL
);

-- Where an imported companion came from: a reviewed copy of one Prospero's Study character
-- version. Study ids are kept only as attribution; every local row has a new id.
CREATE TABLE IF NOT EXISTS study_imports (
  id TEXT PRIMARY KEY,
  companion_id TEXT NOT NULL REFERENCES companions(id),
  character_version_id TEXT NOT NULL REFERENCES character_versions(id),
  workspace_path TEXT NOT NULL,
  database_path TEXT NOT NULL,
  study_version TEXT NOT NULL DEFAULT '',
  schema_fingerprint TEXT NOT NULL,
  source_character_id TEXT NOT NULL,
  source_version_id TEXT NOT NULL,
  source_version_number INTEGER NOT NULL,
  source_name TEXT NOT NULL,
  review_token TEXT NOT NULL,
  fields TEXT NOT NULL,
  artwork TEXT NOT NULL,
  imported_at TEXT NOT NULL
);

-- The user's own wording for the character drafting prompts; without a row the shipped file is used.
CREATE TABLE IF NOT EXISTS prompt_overrides (
  name TEXT PRIMARY KEY,
  text TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- Closeness stages (PRD M3, M4) are worked out from shared history, never stored as a score. These rows
-- hold only the user's own choices for one timeline: when counting restarted, a held stage, a nickname
-- and the shared moments they made running jokes.
CREATE TABLE IF NOT EXISTS closeness_settings (
  timeline_id TEXT PRIMARY KEY REFERENCES timelines(id),
  counted_from TEXT,
  held_level INTEGER CHECK (held_level BETWEEN 1 AND 5),
  nickname TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS closeness_jokes (
  timeline_id TEXT NOT NULL REFERENCES timelines(id),
  memory_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (timeline_id, memory_id)
);

-- A message the companion sent first (companion/life/openers.py). Each trigger fires once per
-- timeline; `notify` follows its desktop notification like `notifications` does for posts.
CREATE TABLE IF NOT EXISTS openers (
  id TEXT PRIMARY KEY,
  timeline_id TEXT NOT NULL REFERENCES timelines(id),
  trigger_key TEXT NOT NULL,
  kind TEXT NOT NULL,
  facts TEXT NOT NULL,
  message_id TEXT NOT NULL REFERENCES messages(id),
  wording TEXT NOT NULL CHECK (wording IN ('model', 'template')),
  notify TEXT CHECK (notify IN ('queued', 'delivered', 'dropped', 'cancelled')),
  created_at TEXT NOT NULL,
  UNIQUE (timeline_id, trigger_key)
);
CREATE INDEX IF NOT EXISTS openers_message ON openers(message_id);

-- What the companion said about themselves (companion/self_facts.py): fiction about the character,
-- tied to the message it came from, noted automatically and kept or removed by the user.
CREATE TABLE IF NOT EXISTS self_facts (
  id TEXT PRIMARY KEY,
  companion_id TEXT NOT NULL REFERENCES companions(id),
  message_id TEXT NOT NULL REFERENCES messages(id),
  key TEXT NOT NULL,
  category TEXT NOT NULL,
  subject TEXT NOT NULL,
  value TEXT NOT NULL,
  statement TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('noted', 'kept', 'rejected', 'conflict')),
  conflicts_with TEXT,
  created_at TEXT NOT NULL,
  decided_at TEXT,
  UNIQUE (message_id, key)
);
CREATE INDEX IF NOT EXISTS self_facts_message ON self_facts(message_id);
-- Changes to a city the workspace keeps (companion/world/changes.py): the user's own, and headlines remembered
-- from real local-event lookups, deleted with their lookup. Seeded changes are computed from the city and month,
-- not stored; one the user dismisses is listed in world_change_dismissals and never happens.
CREATE TABLE IF NOT EXISTS world_changes (
  id TEXT PRIMARY KEY,
  city_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('opening', 'closing', 'renovation', 'roadworks', 'news')),
  origin TEXT NOT NULL CHECK (origin IN ('user', 'real')),
  place_id TEXT,
  neighborhood_id TEXT,
  name TEXT NOT NULL,
  summary TEXT NOT NULL DEFAULT '',
  details TEXT,
  announced_on TEXT NOT NULL,
  starts_on TEXT NOT NULL,
  ends_on TEXT,
  observation_id TEXT REFERENCES context_observations(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS world_changes_city ON world_changes(city_id, starts_on);

CREATE TABLE IF NOT EXISTS world_change_dismissals (
  change_id TEXT PRIMARY KEY,
  city_id TEXT NOT NULL,
  dismissed_at TEXT NOT NULL
);

-- A recommendation the user made (companion/life/recommendations.py); its sessions are agenda entries
-- that carry `recommendation.id`.
CREATE TABLE IF NOT EXISTS recommendations (
  id TEXT PRIMARY KEY,
  timeline_id TEXT NOT NULL REFERENCES timelines(id),
  message_id TEXT NOT NULL REFERENCES messages(id),
  kind TEXT NOT NULL CHECK (kind IN ('show', 'movie', 'book', 'music', 'game', 'outing')),
  title TEXT NOT NULL,
  sessions INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('waiting', 'dropped')),
  starts_after TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS recommendations_timeline ON recommendations(timeline_id, status);

-- Storylines in the companion's and their circle's lives (companion/life/storylines.py): a seeded
-- template, its cast (circle_people ids) and its beats with their local dates. Beats stay hidden
-- until their date; `storyline_days` is how far starting days have been decided.
CREATE TABLE IF NOT EXISTS storylines (
  id TEXT PRIMARY KEY,
  timeline_id TEXT NOT NULL REFERENCES timelines(id),
  story TEXT NOT NULL,
  level INTEGER NOT NULL,
  cast_ids TEXT NOT NULL,
  stages TEXT NOT NULL,
  started_on TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('running', 'ended')),
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS storylines_timeline ON storylines(timeline_id, status, started_on);

CREATE TABLE IF NOT EXISTS storyline_days (
  timeline_id TEXT PRIMARY KEY REFERENCES timelines(id),
  through TEXT NOT NULL
);
-- A picture the companion sent with a chat reply (companion/images/photos.py): a photo, selfie or
-- view of the current moment, made on the post keyed to the slot it shows so the chat and the feed
-- share one picture, or a meme on a post of its own that never reaches the feed. `job_id` is the
-- version this reply showed.
CREATE TABLE IF NOT EXISTS chat_photos (
  message_id TEXT PRIMARY KEY REFERENCES messages(id),
  post_id TEXT NOT NULL REFERENCES feed_posts(id),
  job_id TEXT REFERENCES image_jobs(id),
  kind TEXT NOT NULL DEFAULT 'moment' CHECK (kind IN ('moment', 'selfie', 'view', 'meme')),
  event_key TEXT NOT NULL DEFAULT '',
  summary TEXT NOT NULL,
  top_text TEXT NOT NULL DEFAULT '',
  bottom_text TEXT NOT NULL DEFAULT '',
  -- 1 when the companion chose to send it without being asked.
  unasked INTEGER NOT NULL DEFAULT 0 CHECK (unasked IN (0, 1)),
  created_at TEXT NOT NULL
);

-- The companion's home and belongings (companion/life/home.py): assembled once per timeline from
-- the city data and a seed, then changed slowly by seeded draws, at most one per two weeks.
CREATE TABLE IF NOT EXISTS home_state (
  timeline_id TEXT PRIMARY KEY REFERENCES timelines(id),
  seed TEXT NOT NULL,
  started TEXT NOT NULL,
  era TEXT NOT NULL,
  next_period INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- One belonging, kept from local date `since` until `until` (exclusive; NULL while they still have it).
CREATE TABLE IF NOT EXISTS home_items (
  id TEXT PRIMARY KEY,
  timeline_id TEXT NOT NULL REFERENCES timelines(id),
  kind TEXT NOT NULL CHECK (kind IN ('home', 'pet', 'plant', 'vehicle', 'favorite')),
  name TEXT NOT NULL,
  variety TEXT NOT NULL DEFAULT '',
  details TEXT NOT NULL,
  origin TEXT NOT NULL CHECK (origin IN ('generated', 'change', 'user')),
  since TEXT NOT NULL,
  until TEXT,
  edited INTEGER NOT NULL DEFAULT 0 CHECK (edited IN (0, 1)),
  revision INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS home_items_timeline ON home_items(timeline_id, since);

-- Each change to the home, on the local date it happens; `until` ends a repair.
CREATE TABLE IF NOT EXISTS home_log (
  id TEXT PRIMARY KEY,
  timeline_id TEXT NOT NULL REFERENCES timelines(id),
  period INTEGER NOT NULL,
  local_date TEXT NOT NULL,
  kind TEXT NOT NULL,
  item_id TEXT,
  until TEXT,
  text TEXT NOT NULL,
  spend TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  UNIQUE (timeline_id, period)
);

-- People the companion met through their circle (companion/life/network.py): a friend of a friend,
-- keyed by the seeded path that builds them, with a snapshot of who they are. A meeting counts once
-- the agenda slot it happened in has happened and still records it.
CREATE TABLE IF NOT EXISTS acquaintances (
  timeline_id TEXT NOT NULL REFERENCES timelines(id),
  key TEXT NOT NULL,
  person TEXT NOT NULL,
  slot_key TEXT NOT NULL,
  occasion TEXT NOT NULL,
  met_on TEXT NOT NULL,
  met_at TEXT NOT NULL,
  PRIMARY KEY (timeline_id, key, slot_key)
);

-- The social side of the feed (companion/life/social.py): the circle's posts and the companion's posts that
-- are not life events. `author` is 'companion' or a circle person's id. Likes and comments are derived, not stored.
CREATE TABLE IF NOT EXISTS social_posts (
  id TEXT PRIMARY KEY,
  timeline_id TEXT NOT NULL REFERENCES timelines(id),
  kind TEXT NOT NULL CHECK (kind IN ('status', 'friend', 'birthday', 'holiday', 'city', 'question')),
  author TEXT NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE,
  content TEXT NOT NULL,
  answer TEXT,
  status TEXT NOT NULL DEFAULT 'visible' CHECK (status IN ('visible', 'hidden', 'removed')),
  reaction TEXT,
  occurs_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  read_at TEXT,
  removed_at TEXT
);
CREATE INDEX IF NOT EXISTS social_posts_order ON social_posts(timeline_id, occurs_at, id);

-- A chat message written in reply to a social post.
CREATE TABLE IF NOT EXISTS message_social_links (
  message_id TEXT PRIMARY KEY REFERENCES messages(id),
  post_id TEXT NOT NULL REFERENCES social_posts(id)
);

-- People in the user's real life the companion has heard about (companion/memory/people.py). Everything said
-- about them is an ordinary memory carrying memories.person_id, so consent, correction, exclusion and deletion
-- work as for any memory; a person with no memories left is removed with the last one.
CREATE TABLE IF NOT EXISTS user_people (
  id TEXT PRIMARY KEY,
  companion_id TEXT NOT NULL REFERENCES companions(id),
  name TEXT,
  relation TEXT,
  last_mentioned_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS user_people_companion ON user_people(companion_id);
