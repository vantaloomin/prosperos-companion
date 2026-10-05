import type { RoutineBlock } from './features/character/schedule'

export type Relationship = 'friendship' | 'romance' | 'mentor' | 'family' | 'other'
export type ChatStyle = 'feed' | 'bubbles' | 'community' | 'retro' | 'novel'
export type ReplyStatus = 'complete' | 'streaming' | 'incomplete' | 'cancelled' | 'failed' | 'withheld'

export interface Message {
  id: string
  timeline_id: string
  seq: number
  role: 'user' | 'companion'
  text: string
  reply_to: string | null
  status: ReplyStatus
  active: boolean
  redacted: boolean
  error: string | null
  character_version_id: string | null
  created_at: string
  completed_at: string | null
  /** For a message copied into an alternate timeline, the message it was first written as. */
  origin_id?: string | null
}

export interface Timeline {
  id: string
  label: string
  status: 'active' | 'frozen'
  active: boolean
  parent_id: string | null
  fork_message_id: string | null
  forked_at: string | null
  created_at: string
  activated_at: string | null
  frozen_at: string | null
  /** The edited words of a historical edit, waiting to be sent on this timeline. */
  draft: string | null
  messages: number
  last_message_at: string | null
  latest_text: string
}

export interface TimelineList { active_id: string; timelines: Timeline[]; stopped_reply_ids?: string[] }

export interface History { timeline_id: string; messages: Message[] }

export interface SearchResult { id: string; seq: number; role: 'user' | 'companion'; text: string; status: Message['status']; reply_to: string | null; created_at: string }
export interface SearchResults { query: string; results: SearchResult[]; more: boolean }

export interface SendResult {
  message: Message
  reply: Message | null
  connection: 'ready' | 'not_configured'
}

export type Intensity = 'mild' | 'moderate' | 'strong'

export interface EmotionalTrait { name: string; intensity: Intensity; note: string }

export interface CharacterDefinition {
  name: string
  identity: string
  personality: string
  voice: string
  skills: string[]
  flaws: string[]
  interests: string[]
  background: string
  appearance: string
  routine: string
  location: string
  relationship: Relationship
  absence_reaction: string
  emotional_traits: EmotionalTrait[]
  timezone: string
  home_city: string
  schedule: RoutineBlock[]
  life_themes: string[]
}

export interface CharacterVersion {
  id: string
  number: number
  name: string
  note: string
  effective_at: string
  definition: CharacterDefinition
}

export interface Companion {
  id: string
  active_version_id: string
  active_timeline_id: string
  version: CharacterVersion
}

export interface WorkspaceSettings {
  user_timezone: string
  /** 'pc' follows this PC's timezone; 'chosen' was picked in Settings; 'default' is the untouched UTC. */
  user_timezone_source: 'default' | 'pc' | 'chosen'
  /** What the backend worked out from the PC (Windows registry, TZ), or null. */
  system_timezone: string | null
  automatic_memory: boolean
  sensitive_memory: boolean
  model_memory_suggestions?: boolean
  /** How the chat looks; the messages and every action are the same in each style. */
  chat_style?: ChatStyle
  /** Retro IM door, away and message sounds; off unless turned on. */
  chat_sounds?: boolean
  share_profile_across_timelines: boolean
  background_activity: boolean
  paused: boolean
  paused_at: string | null
  review_required: boolean
}

/** The conversation's model profile (GET /api/connection); Settings > Models has the rest. */
export interface Connection {
  profile_id: string
  name: string
  provider: string
  provider_name: string
  base_url: string
  model: string
  has_key: boolean
  max_output_tokens: number
  context_tokens: number
  timeout_seconds: number
  embedding_model?: string | null
}

export type Layer = 'user_fact' | 'shared_experience' | 'plan' | 'temporary' | 'relationship' | 'companion_life'
export type PlanStatus = 'proposed' | 'agreed' | 'postponed' | 'cancelled' | 'completed'

export interface Memory {
  id: string
  layer: Layer
  subject: string
  value: string
  reality: 'real' | 'fiction'
  authority: 'stated' | 'confirmed' | 'tentative'
  status: 'active' | 'superseded' | 'excluded'
  boundary: boolean
  pinned: boolean
  sensitive: boolean
  plan_status: PlanStatus | null
  stated_at: string
  applies_from: string | null
  applies_until: string | null
  revision: number
  supersedes_id: string | null
  source_message_ids: string[]
  updated_at: string
  subject_key?: string
  /** user: added or remembered deliberately; automatic: extracted from a stated fact; suggestion: a suggestion you accepted. */
  origin?: 'user' | 'automatic' | 'suggestion'
  /** The later memory that ended this one ("I moved to Boston" ends Chicago). */
  ended_by_id?: string | null
  dates_uncertain?: boolean
  /** False once its applicable period has ended; it stays as history. */
  current?: boolean
  /** False for a memory from another timeline, which the current conversation does not use. */
  in_timeline?: boolean
}

/** A fact found in one of your messages, waiting for you to keep or decline it. */
export interface Suggestion {
  id: string
  message_id: string
  layer: Layer
  subject: string
  value: string
  sensitive: boolean
  boundary: boolean
  plan_status: PlanStatus | null
  applies_from: string | null
  applies_until: string | null
  dates_uncertain: boolean
  excerpt: string
  reason: string | null
  /** For a conflict: the current values keeping this would replace. */
  replaces?: string[]
  created_at: string
}

export interface RememberResult {
  memories: Memory[]
  draft: { layer: Layer; subject: string; value: string; source_message_ids: string[] } | null
}

export interface DeletePreview {
  memory_ids: string[]
  source_message_ids: string[]
  other_memories: { id: string; subject: string }[]
  summaries_with_sources: number
  kept: string
}

export interface MergeProposal { id: string; keep: Memory; merge: Memory; created_at: string }

export interface DeclineResult { message_id: string; declined: boolean; removed_memory_ids: string[] }

export interface DeleteResult { deleted_memory_ids: string[]; redacted_message_ids: string[]; linked_memory_ids: string[] }

export interface LifeSettings {
  automatic_events: boolean
  phrase_with_model: boolean
  catch_up_on_return: boolean
  catch_up_max_events: number
  catch_up_lookback_hours: number
  return_gap_hours: number
  background_interval_minutes: number
  background_daily_events: number
}

export interface BackupResult { path: string; created_at: string; database_bytes: number }
export interface BackupEntry {
  name: string; bytes: number; kind: 'backup' | 'pre-upgrade'; readable: boolean
  created_at?: string; app_version?: string; files?: number; datasets_included?: boolean
}
export interface BackupList { backups: BackupEntry[]; pending: { name: string; requested_at: string } | null }

export interface LifeEvent {
  id: string
  kind: 'routine' | 'plan' | 'ordinary' | 'thread'
  status: 'proposed' | 'committed' | 'rejected' | 'superseded'
  summary: string
  details: { label?: string; activity?: string; post?: string; mood?: string; local_date?: string; timezone?: string }
  starts_at: string
  ends_at: string
  revision: number
  rejection: string | null
}

export interface RoutineSlot { starts_at: string; ends_at: string; local_date: string; block: { label: string; kind: string } }

export interface AbsenceMood { id: string; kind: string; intensity: string; away_hours: number; traits: string[]; expires_at: string }

export interface LifeRun { id: string; status: 'running' | 'completed' | 'interrupted' | 'failed'; error: string | null; finished_at: string | null }

export interface SharedPlan { id: string; subject: string; value: string; status: string; applies_from: string | null; applies_until: string | null }

export interface Today {
  now: string
  companion_local_time: string
  companion_timezone: string
  availability: { state: 'free' | 'working' | 'out' | 'asleep'; label: string; until: string | null }
  routine: { default_schedule: boolean; current: RoutineSlot | null; next: RoutineSlot | null }
  changes: LifeEvent[]
  review: LifeEvent[]
  plans: { shared: SharedPlan[]; companion: LifeEvent[]; threads: LifeEvent[] }
  feed_unread: number
  last_run: LifeRun | null
  paused: boolean
  paused_at: string | null
  clock_behind: boolean
  mood: AbsenceMood | null
  last_seen_at: string | null
}

export interface PauseRecord { id: string; started_at: string; ended_at: string | null; catch_up_requested_at: string | null; catch_up_run_id: string | null }

export type Reaction = 'heart' | 'laugh' | 'wow' | 'sad' | 'hug'

export interface FeedPost {
  id: string
  kind: 'digest' | 'event'
  intro: string
  status: 'visible' | 'hidden'
  read: boolean
  reaction: Reaction | null
  occurs_at: string
  created_at: string
  events: { id: string; summary: string; caption: string; mood: string | null; label: string | null; kind: string; starts_at: string; ends_at: string; revision: number }[]
  image: PostImage
}

export interface FeedPage { posts: FeedPost[]; next_before: string | null; unread: number }

export interface CitySummary { id: string; name: string; region: string; country: string; timezone: string; summary: string }

export interface ContextReceipt { budget_tokens: number; estimated_tokens: number; included: Record<string, string[]>; omitted: Record<string, string[]> }
export interface ContextPreview { system: string; messages: { role: 'user' | 'assistant'; content: string }[]; receipt: ContextReceipt }

export interface DiaryEntry {
  subject: string
  slot: string
  starts_at: string
  ends_at: string
  local_date: string
  block: string
  entry: { summary: string; activity?: string; place?: string | null; mood?: string | null; post?: unknown }
  status: string
}
export interface CirclePerson {
  id: string
  name: string
  role: string
  status: 'active' | 'removed'
  revision: number
  career: string | null
  employer: string | null
  neighborhood: string | null
  city: string | null
  full_name?: string
  pronouns?: string
  age?: number
  local?: boolean
  closeness?: string
  haunts?: string[]
  now: RoutineBlock | null
  recent: DiaryEntry[]
}

export type ImageStatus = 'none' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'interrupted'

export interface PostImage { status: ImageStatus; job_id: string | null; ref: string | null; error: string | null; updated_at: string | null; outdated?: boolean }

export type BackendKind = 'comfyui' | 'codex' | 'hosted'
export type HostedProvider = 'openrouter' | 'google' | 'openai' | 'other'

export interface ImageBackend {
  id: string
  kind: BackendKind
  provider: string
  label: string
  enabled: boolean
  position: number
  base_url: string
  model: string
  api_style: 'images' | 'chat' | null
  cli_path: string
  custom_workflow: boolean
  has_key: boolean
  controlled_machine: boolean
  concurrency: number
  local: boolean
  accepts_nsfw: boolean
  blocked_reason: string | null
  disclosure: string | null
  disclosure_accepted: boolean
  experimental: boolean
}

export interface ImageSettings { automatic_images: boolean; daily_limit: number; queue_limit: number; fallback: boolean; aspect: 'square' | 'landscape' | 'portrait'; style: string }

export interface BackendCheck { ok: boolean; summary: string; details: string[] }

export interface ImageJob {
  id: string
  post_id: string
  status: Exclude<ImageStatus, 'none'>
  trigger: 'manual' | 'automatic' | 'retry' | 'fallback'
  retry_of: string | null
  classification: 'safe' | 'nsfw' | 'prohibited'
  classification_reasons: string[]
  routing_reason: string
  backend_id: string | null
  backend_label: string | null
  backend_kind: BackendKind | null
  provider: string | null
  model: string | null
  workflow: string | null
  identity_method: string | null
  seed: number | null
  width: number | null
  height: number | null
  usage: Record<string, unknown> | null
  error: string | null
  error_code: string | null
  waiting_for: string | null
  has_image: boolean
  prompt: string
  marked_nsfw: boolean
  current: boolean
  retry_original_available: boolean
  created_at: string
  finished_at: string | null
}

// Current context through MCP (PRD X1–X3)
export type ContextCategory = 'weather' | 'news' | 'local_events' | 'link' | 'web_search'
export type ContextPurpose = 'conversation' | 'companion_city'
export type ArgumentSource = 'place' | 'latitude' | 'longitude' | 'topic' | 'date' | 'literal' | 'url'
export interface ToolArgument { source: ArgumentSource; value?: string | number | boolean }
export interface ContextTool { name: string; description: string; input_schema: { properties?: Record<string, { type?: string; description?: string }>; required?: string[] }; read_only: boolean }
export interface Disclosure {
  digest: string
  destination: string
  transport: 'stdio' | 'http'
  tool: string
  category: ContextCategory
  sends: { argument: string; source: ArgumentSource; description: string; example: string | number | null }[]
  run_in: ContextPurpose[]
  never_sent: string[]
  summary: string[]
}
export interface ContextMapping { category: ContextCategory; tool: string; arguments: Record<string, ToolArgument>; run_in: ContextPurpose[]; enabled: boolean; approved: boolean; disclosure: Disclosure }
export interface MappingSuggestion { tool: string; arguments: Record<string, ToolArgument>; missing: string[] }
export interface ContextServiceInfo {
  id: string
  name: string
  transport: 'stdio' | 'http'
  command: string[] | null
  /** A server that ships with the app, run by the app itself. */
  builtin: 'weather' | null
  url: string | null
  has_key: boolean
  secret_name: string
  tools: ContextTool[]
  server_info: { protocol: string; name: string; version: string } | null
  checked_at: string | null
  check_error: string | null
  cooldown_until: string | null
  mappings: ContextMapping[]
  suggestions: Partial<Record<ContextCategory, MappingSuggestion>>
}
export interface ContextLocation { user_place: string; user_latitude: number | null; user_longitude: number | null; read_links: boolean; updated_at: string }
export interface ContextOverview {
  /** The companion's real-world city, when it has one; weather for it can be looked up. */
  companion_place: string | null
  location: ContextLocation
  services: ContextServiceInfo[]
  categories: Record<ContextCategory, { label: string; purposes: ContextPurpose[] }>
  purposes: Record<ContextPurpose, string>
  sources: Record<ArgumentSource, string>
  never_sent: string[]
}
export interface Observation {
  id: string
  service_id: string | null
  service_name: string
  category: ContextCategory
  purpose: ContextPurpose
  tool: string
  arguments: Record<string, unknown>
  destination: string
  location: { label: string; whose: 'user' | 'companion'; url?: string } | null
  status: 'ok' | 'failed' | 'refused'
  content: string
  error_code: string | null
  error: string | null
  attempts: number
  requested_at: string
  retrieved_at: string | null
  fresh_until: string | null
  fresh: boolean
}

// Character LoRA maker (docs/lora.md)
export type Rights = 'own_work' | 'commissioned' | 'licensed' | 'generated' | 'unknown'
export type ReferenceRole = 'train' | 'evaluation' | 'excluded'
export interface Crop { x: number; y: number; width: number; height: number }

export interface LoraReference {
  id: string
  original_name: string
  media_type: string
  width: number
  height: number
  bytes: number
  rights: Rights
  rights_label: string
  source_note: string
  role: ReferenceRole
  exclusion_reason: string
  caption: string
  caption_origin: 'empty' | 'suggested' | 'edited'
  crop: Crop | null
  has_crop: boolean
  similar_to: string | null
  missing: boolean
  updated_at: string
}

export interface DatasetReview { training: number; evaluation: number; excluded: number; blocking: string[]; advice: string[]; ready: boolean }

export interface LoraSettings { python_path: string; trainer_dir: string; base_model: string; comfy_lora_dir: string }

export interface TrainerDescription {
  name: string
  tested: string
  verified: boolean
  arch: string
  default_base_model: string
  disclosure: string
  requirements: string[]
  control: string
  defaults: RunOptions
  check: { ok: boolean; problems: string[]; notes: string[] }
}

export interface RunOptions { network: 'lokr' | 'lora'; rank: number; steps: number; learning_rate: number; save_every: number; resolution: 512 | 1024; low_vram: boolean }

export interface Checkpoint { step: number; final: boolean; file: string; bytes: number; verified: boolean; format: string | null; sha256: string | null; problem: string | null }

export type RunStatus = 'running' | 'completed' | 'failed' | 'cancelled' | 'interrupted'

export interface TrainingRun {
  id: string
  name: string
  status: RunStatus
  trainer: string
  trainer_tested: string
  base_model: string
  trigger: string
  options: RunOptions
  dataset: { pictures: { reference_id: string; caption: string }[] }
  folder: string
  attempt: number
  resumed_from_step: number | null
  progress_step: number | null
  progress_total: number | null
  progress_at: string | null
  checkpoints: Checkpoint[]
  adapter_id: string | null
  exit_code: number | null
  log_tail: string
  error: string | null
  resumable: boolean
  restartable: boolean
  verified_on_hardware: boolean
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export interface LoraAdapter {
  id: string
  origin: 'trained' | 'imported'
  run_id: string | null
  step: number | null
  name: string
  sha256: string
  bytes: number
  format: 'lora' | 'lokr' | 'unknown'
  base_model: string
  trainer: string
  trigger: string
  license_note: string
  note: string
  available: boolean
  created_at: string
}

export interface AppearanceVersion {
  id: string | null
  number: number
  method: 'text' | 'lora'
  adapter_id: string | null
  strength: number
  comfy_name: string | null
  note: string
  adopted_at: string | null
  adapter: LoraAdapter | null
  current?: boolean
}

export interface AppearanceState { current: AppearanceVersion; versions: AppearanceVersion[]; install?: { comfy_name: string; installed: boolean; note: string } }

export type EvalImageStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'interrupted'

export interface EvalImage {
  id: string
  position: number
  prompt_key: string
  label: string
  variant: 'lora' | 'text'
  prompt: string
  seed: number
  width: number
  height: number
  status: EvalImageStatus
  classification: string
  workflow: string | null
  model: string | null
  error: string | null
  rating: '' | 'good' | 'weak'
  has_image: boolean
}

export interface Evaluation {
  id: string
  adapter_id: string
  adapter: { name: string; format: string; trigger: string }
  set_version: number
  strength: number
  comfy_name: string
  status: 'running' | 'completed' | 'cancelled' | 'interrupted'
  held_out: string[]
  counts: Record<EvalImageStatus, number>
  images: EvalImage[]
  created_at: string
  install?: { installed: boolean; note: string }
}

export type NotificationPreview = 'full' | 'name' | 'private'

export interface NotificationSettings {
  enabled: boolean
  quiet_start: string
  quiet_end: string
  preview: NotificationPreview
  daily_cap: number
  min_gap_minutes: number
  queued: number
}

export interface DesktopNotification { id: string; kind: 'post' | 'digest'; post_ids: string[]; title: string; body: string }

export interface NotificationCheck { notification: DesktopNotification | null; held: string | null }
