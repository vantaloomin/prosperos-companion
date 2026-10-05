import type { RoutineBlock } from './features/character/schedule'

export type Relationship = 'friendship' | 'romance' | 'mentor' | 'family' | 'other'
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
}

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
  automatic_memory: boolean
  sensitive_memory: boolean
  share_profile_across_timelines: boolean
  background_activity: boolean
  paused: boolean
  paused_at: string | null
  review_required: boolean
}

export interface Connection {
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
  created_at: string
}

export interface RememberResult {
  memories: Memory[]
  draft: { layer: Layer; subject: string; value: string; source_message_ids: string[] } | null
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

export interface PostImage { status: ImageStatus; job_id: string | null; ref: string | null; error: string | null; updated_at: string | null }

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
