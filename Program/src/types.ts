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
  /** A reply held while the companion was busy shows at this time (companion/life/pacing.py). */
  held_until?: string | null
  /** The holding text sent before this full reply ("in a meeting, give me a bit"), kept as its own message. */
  held_line?: string | null
  /** Set on a full reply dropped unseen because the user wrote again first; it is never shown. */
  superseded_at?: string | null
  /** A photo of the moment this reply sent (photos in chat). */
  photo?: ChatPhoto | null
  /** Pictures the user sent with this message (companion/pictures.py). */
  pictures?: SentPicture[]
}

export interface SentPicture { id: string; width: number; height: number; status: 'pending' | 'seen' | 'unseen'; reason: string | null }

/** A picture a reply sent: a photo, selfie or view of the moment (shared with its feed post), or a meme. */
export interface ChatPhoto {
  message_id: string
  post_id: string
  kind: 'moment' | 'selfie' | 'view' | 'meme'
  summary: string
  /** A meme's captions, drawn over the picture. */
  top_text: string
  bottom_text: string
  status: ImageStatus
  job_id: string | null
  ref: string | null
  error: string | null
  /** Whether the moment has become an event in the feed yet. */
  in_feed: boolean
  /** Sent without being asked. */
  unasked: boolean
  /** The shape it is made in; the chat holds that space while it loads. Older servers leave it out. */
  aspect?: 'square' | 'landscape' | 'portrait'
}

export interface TextingStyle { bursts: boolean; lowercase: boolean; typos: boolean }

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
  /** The full reply after a holding text, held until the companion is free (companion/life/pacing.py). */
  follow_up?: Message | null
  /** Full replies dropped unseen because this message came first; the new reply takes their place. */
  dropped?: string[]
  connection: 'ready' | 'not_configured'
}

export type Intensity = 'mild' | 'moderate' | 'strong'

export interface EmotionalTrait { name: string; intensity: Intensity; note: string }

export interface CharacterDefinition {
  name: string
  /** "MM-DD"; empty picks a date for them. */
  birthday?: string
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
  /** The closeness stage they start at (1 = Just met) and how the two of you know each other already. */
  starting_closeness?: number
  history_together?: string
  /** How others see them and how they see themselves (companion/world/perception.py); empty fills itself in. */
  seen_as?: string
  sees_self?: string
  absence_reaction: string
  emotional_traits: EmotionalTrait[]
  timezone: string
  home_city: string
  schedule: RoutineBlock[]
  life_themes: string[]
  money: MoneySetup
  texting?: TextingStyle
}

export type SpendingStyle = 'careful' | 'balanced' | 'spender'

/** How the companion's money works; pay, rent and prices come from the world data. */
export interface MoneySetup {
  career: string
  style: SpendingStyle
  saving_for: string
  goal: number
  goal_since: string
}

export interface CareerSummary { id: string; name: string; pay: string; eras: string[] }

interface MoneyHappening { label: string; on: string; cost: number; for?: 'home' | 'clothes' }

export type MoneyView = { date: string } & ({ available: false; reason: string } | {
  available: true
  currency: { code: string; symbol: string; name: string }
  period: 'month' | 'week'
  style: SpendingStyle
  career: { id: string; name: string; pay: string; guessed: boolean } | null
  housing: { unit: string; label: string; neighborhood: string }
  budget: { income: number; rent: number; upkeep: number; essentials: number; fun: number; saving: number }
  rent_from: 'home' | 'budget'
  bought: MoneyHappening[]
  payday: { last: string; next: string; cycle_days: number; today: boolean }
  left: number
  fun_cycle: number
  tight: boolean
  flush: boolean
  splurge: MoneyHappening | null
  surprise: MoneyHappening | null
  cant_afford: string[]
  goal: { label: string; amount: number; saved: number; share: number; custom: boolean; since: string; stalled: boolean }
  text: { income: string; rent: string; upkeep: string; essentials: string; fun: string; saving: string; left: string }
})

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
  // One of their reference pictures, shown as their picture; null shows their initial.
  portrait_reference_id?: string | null
  /** Set once the user seeds townsfolk of their own; empty means the city's shared townsfolk. */
  town_seed?: string
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
  /** Now and then the companion may ask about people you mentioned. On unless turned off. */
  ask_about_people?: boolean
  /** How the chat looks; the messages and every action are the same in each style. */
  chat_style?: ChatStyle
  /** Retro IM message sounds; off unless turned on. */
  chat_sounds?: boolean
  chat_retro_dark?: boolean
  /** Story mode (src/features/story) is opt-in, in Settings > Advanced. */
  story_mode?: boolean
  share_profile_across_timelines: boolean
  background_activity: boolean
  paused: boolean
  paused_at: string | null
  review_required: boolean
  /** The LoRA creator; hidden unless COMPANION_LORA_MAKER is set on the PC (docs/lora.md). */
  lora_maker?: boolean
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
  /** A value the user said was never true: replaced by nothing, and its old words are marked as wrong. */
  retracted?: boolean
  /** Set on what you said about someone in your life; see Person. */
  person_id?: string | null
}

/** Someone in your real life the companion has heard about. What they know is ordinary memories carrying person_id. */
export interface Person {
  id: string
  name: string | null
  relation: string | null
  /** The name, or "Your mum" while the name is not known. */
  label: string
  last_mentioned_at: string | null
  created_at: string
  memory_ids: string[]
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
  /** For a conflict or a correction: the current values keeping this would replace. */
  replaces?: string[]
  /** For a correction: the id of the memory it corrects, whether keeping it ends that memory as history, and
   * whether it drops a value that was never true. */
  corrects?: string
  ends?: boolean
  retracts?: boolean
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
  /** The companion may send the first message (companion/life/openers.py). */
  texts_first: boolean
  texts_daily: number
  /** First messages from all companions together in a day (companion/away.py); 0 for none. */
  away_daily: number
  texts_gap_hours: number
  /** 0 sizes the circle by how sociable the companion is. */
  circle_size: number
  /** "MM-DD" or empty; filled in when the user says it in chat. */
  user_birthday: string
  /** Replies wait while the companion is at work or asleep. */
  paced_replies: boolean
  day_shifts: boolean
  /** Storylines from quiet (0) through realistic and dramatic to soap opera (3). */
  drama: number
}

export interface BackupResult { path: string; created_at: string; database_bytes: number }
export interface BackupEntry {
  name: string; bytes: number; kind: 'backup' | 'pre-upgrade' | 'before-reset' | 'before-delete' | 'before-debug'; readable: boolean
  created_at?: string; app_version?: string; files?: number; datasets_included?: boolean
}
export interface StartOverPreview {
  name: string; messages: number; memories: number; timelines: number; images: number
  versions: number; adapters: number; references: number; training: boolean
  /** Other companions in the workspace, who stay; deleting brings back the first of them. */
  others: string[]
}
export interface StartOverResult { backup: { name: string; path: string } }
export interface DataFolderStatus {
  path: string; portable: boolean; pinned: boolean; target: string; default: string
  can_move: boolean; reason: string | null; pending: boolean; notes: string[]
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
  day: { date: string; body: BodyState | null }
  /** Birthdays and talking milestones today or within a week (companion/life/occasions.py). */
  occasions?: Occasion[]
}

/** How the companion feels physically today, carried over from the day before. */
export interface BodyState { state: 'sick' | 'hungover' | 'tired' | 'worn out' | 'sore'; because: string }

export interface PauseRecord { id: string; started_at: string; ended_at: string | null; catch_up_requested_at: string | null; catch_up_run_id: string | null }

export type Reaction = 'heart' | 'laugh' | 'wow' | 'sad' | 'hug'

export type FeedSource = 'all' | 'companion' | 'circle'
export interface FeedAuthor { kind: 'companion' | 'person'; id: string | null; name: string; role: string }
export interface FeedComment { author: 'companion' | 'person'; name: string; text: string; at: string }

export interface FeedPost {
  id: string
  /** Life posts tell life events; social posts (friends, status, shout-outs, city news, questions) carry their own text. */
  kind: 'digest' | 'event' | 'status' | 'friend' | 'birthday' | 'holiday' | 'city' | 'question'
  source: 'life' | 'social'
  author: FeedAuthor
  intro: string
  status: 'visible' | 'hidden'
  read: boolean
  reaction: Reaction | null
  occurs_at: string
  created_at: string
  events: { id: string; summary: string; caption: string; mood: string | null; label: string | null; kind: string; starts_at: string; ends_at: string; revision: number }[]
  text?: string
  context?: string
  place?: string
  options?: string[]
  answer?: string | null
  image: PostImage | null
  audience: { likes: string[]; comments: FeedComment[] }
}

export interface FeedPage { posts: FeedPost[]; next_before: string | null; unread: number }

export interface CitySummary { id: string; name: string; region: string; country: string; timezone: string; summary: string; era?: string }

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
  /** Where their own people are built from (GET /life/network?key=). */
  key: string
  name: string
  role: string
  status: 'active' | 'removed'
  revision: number
  career: string | null
  employer: string | null
  neighborhood: string | null
  city: string | null
  full_name?: string
  married?: boolean
  birth_family?: string
  pronouns?: string
  age?: number
  local?: boolean
  closeness?: string
  haunts?: string[]
  works_with_companion?: boolean
  /** Who they know inside the circle and how. */
  knows?: CircleTie[]
  /** How close they and the companion feel, both ways (companion/memory/pairs.py); read-only. */
  stage?: PairStage | null
  now: RoutineBlock | null
  recent: DiaryEntry[]
}

/** Someone around the circle, a few layers out (companion/life/network.py); built on request, never stored. */
export interface NetworkPerson {
  key: string
  name: string
  full: string
  pronouns: string
  age: number
  relation: string
  depth: number
  of: string
  how: string
  occupation: string
  /** Where the companion met them, when they have. */
  met?: string | null
}
export interface NetworkAnswer { person: Pick<NetworkPerson, 'key' | 'name' | 'depth'>; people: NetworkPerson[]; deeper: boolean }
export interface Acquaintance extends Omit<NetworkPerson, 'depth' | 'met'> { occasion: string; met_on: string; met_at: string }

export interface CircleTie { id: string; name: string; how: string }
export interface CircleRoom { people: number; target: number; sociability: 'quiet' | 'usual' | 'social' }

export type ImageStatus = 'none' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'interrupted'

export interface PostImage { status: ImageStatus; job_id: string | null; ref: string | null; error: string | null; updated_at: string | null; outdated?: boolean }

export type BackendKind = 'comfyui' | 'codex' | 'hosted'
export type HostedProvider = 'openrouter' | 'google' | 'openai' | 'nanogpt' | 'other'

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
  // Starts this backend's image prompts; '' uses the general style.
  style: string
  cli_path: string
  custom_workflow: boolean
  // ComfyUI: files chosen for the built-in workflow ('' means its default); null for other kinds.
  model_files: ModelFiles | null
  // ComfyUI: LoRAs applied after the character's own, in order; null for other kinds.
  style_loras: StyleLora[] | null
  // ComfyUI: the built-in workflow's sampler; null in a field means the workflow's own value.
  sampler: SamplerSettings | null
  reference_workflow: boolean
  // Can make a picture that follows an earlier one (the onboarding profile pictures).
  takes_reference: boolean
  has_key: boolean
  controlled_machine: boolean
  concurrency: number
  local: boolean
  accepts_nsfw: boolean
  // Image APIs other than Google and OpenAI: the user switched it to take NSFW requests too.
  allows_nsfw: boolean
  // Whether that switch is offered for this backend.
  nsfw_switch: boolean
  blocked_reason: string | null
  disclosure: string | null
  disclosure_accepted: boolean
  experimental: boolean
}

export interface ImageSettings { automatic_images: boolean; chat_photos: boolean; unprompted_photos: boolean; daily_limit: number; queue_limit: number; fallback: boolean; aspect: 'square' | 'landscape' | 'portrait'; style: string }

export interface BackendCheck { ok: boolean; summary: string; details: string[] }

export type ModelFileKey = 'unet_name' | 'clip_name' | 'clip_type' | 'vae_name'
export type ModelFiles = Record<ModelFileKey, string>
export type FileListKey = ModelFileKey | 'lora' | 'sampler_name' | 'scheduler'
export interface SamplerSettings { steps: number | null; cfg: number | null; sampler_name: string | null; scheduler: string | null }
export interface StyleLora { name: string; strength: number; trigger: string }
/** What a ComfyUI server offers the built-in workflow's loaders and its LoRAs, Krea 2's first (`krea` lists
 * those); ok is false when it could not be asked. The character's own LoRA is left out of `lora`. */
export interface BackendFiles { ok: boolean; error: string | null; defaults: ModelFiles; sampler_defaults: SamplerSettings; options: Record<FileListKey, string[]>; krea: Record<FileListKey, string[]>; character_lora: string | null }
export interface ModelLink { name: string; role: 'model' | 'clip' | 'vae'; file: string | null; url: string; licence: string }

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
export type ContextCategory = 'weather' | 'news' | 'local_events' | 'link' | 'web_search' | 'culture'
export type ContextPurpose = 'conversation' | 'companion_city' | 'ambient'
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
  builtin: 'weather' | 'pulse' | 'culture' | null
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

export interface DesktopNotification { id: string; kind: 'post' | 'digest' | 'message'; post_ids: string[]; message_id?: string; companion_id?: string; title: string; body: string }

export interface TextCheck { state: string; kind?: string; message: Message | null; companion_id?: string; focus?: boolean }

/** One chat in the chat list (companion/chats.py): a companion's, and later group chats. Never says who is around. */
export interface Chat {
  kind: string
  id: string
  /** What its read position is kept by: a companion's active timeline. */
  thread_id: string
  name: string
  focus: boolean
  unread: number
  last: { role: 'user' | 'companion'; text: string; at: string } | null
  active_at: string
}
export interface ChatList { chats: Chat[]; unread: number }

export interface NotificationCheck { notification: DesktopNotification | null; held: string | null }

export type ShotAspect = 'square' | 'landscape' | 'portrait'

export interface Shot { key: string; label: string; shot: string; aspect: ShotAspect }

export interface GenerationDraft { base: string; style: string; negative: string; seed: number; shots: Shot[] }

export interface PlannedShot {
  label: string
  shot: string
  aspect: ShotAspect
  prompt: string
  tier: 'safe' | 'nsfw' | 'prohibited'
  reasons: string[]
  route_reason: string
  refusal: string | null
  backend: { id: string; label: string; kind: string; local: boolean } | null
  // Onboarding portraits: the position of the picture this one follows.
  follows?: number | null
}

export interface PortraitDraft extends GenerationDraft { any_backend: boolean; reference_backend: { id: string; label: string; kind: string; local: boolean } | null }

export interface GeneratedImage {
  id: string
  position: number
  label: string
  shot: string
  prompt: string
  aspect: ShotAspect
  seed: number
  used_seed: number | null
  classification: string
  reasons: string[]
  backend_id: string | null
  backend_label: string | null
  backend_kind: string | null
  status: EvalImageStatus
  error: string | null
  width: number | null
  height: number | null
  model: string | null
  decision: 'kept' | 'discarded' | null
  reference_id: string | null
  has_image: boolean
  follows?: number | null
}

export interface Generation {
  id: string
  base: string
  seed: number
  status: 'running' | 'completed' | 'cancelled' | 'interrupted'
  counts: Record<EvalImageStatus | 'kept', number>
  images: GeneratedImage[]
  created_at: string
}

export interface ClosenessJoke { memory_id: string; subject: string; value: string }
/** A stage reached from shared history, or (kind) where it started or the day the user set it. */
export interface ClosenessMilestone { level: number; on: string | null; days?: number; moments?: number; kind?: 'start' | 'set' }
/** Worked out from shared history each time (PRD M4): never a hidden score. */
export interface Closeness {
  level: number
  name: string
  grown_level: number
  held_level: number | null
  /** From history, a set stage and the starting stage, before a ceiling or cooling. */
  earned_level: number
  ceiling_level: number | null
  starting_level: number
  cooling: boolean
  cooled_steps: number
  warm_days_left: number
  silent_days: number
  set_on: string | null
  relationship: string
  stages: string[]
  days_talked: number
  shared_moments: number
  counted_moments: number
  first_day: string | null
  counted_from: string | null
  nickname: string
  history: ClosenessMilestone[]
  jokes: ClosenessJoke[]
  joke_candidates: (ClosenessJoke & { days: number })[]
}

/** Something the companion said about themselves (companion/self_facts.py). */
export interface SelfFact {
  id: string
  message_id: string
  category: 'likes' | 'dislikes' | 'favorite' | 'person' | 'pet' | 'never' | 'grew_up' | 'allergy' | 'team' | 'plays'
    | 'works_at' | 'detail'
  label: string
  subject: string
  value: string
  statement: string
  status: 'noted' | 'kept' | 'conflict'
  conflicts_with: string | null
  /** For a conflict with their circle: who the circle has in that role ("mom Cathy"). */
  circle_person?: string
  /** For a fact the user said was wrong: what they wrote (empty once that message is deleted). */
  user_said?: string
  /** For a fact the character definition contradicts: the place it names. */
  definition_says?: string
  created_at: string
  decided_at: string | null
}

/** Something the user recommended (companion/life/recommendations.py). */
export interface Recommendation {
  id: string
  kind: 'show' | 'movie' | 'book' | 'music' | 'game' | 'outing'
  title: string
  state: 'waiting' | 'started' | 'finished'
  sessions_done: number
  verdict: string | null
  created_at: string
  finished_at: string | null
}

export interface StoryBeat { on: string; text: string; share: string; tone: 'good' | 'bad' | 'mixed' }
/** Something unfolding in the companion's or their circle's lives (companion/life/storylines.py). */
export interface Storyline {
  id: string
  story: string
  level: 'quiet' | 'realistic' | 'dramatic' | 'soap opera'
  started_on: string
  status: 'running' | 'ended'
  cast: { id: string; name: string; role: string }[]
  beats: StoryBeat[]
  unfolding: boolean
}

export interface Occasion { key: string; kind: 'user_birthday' | 'own_birthday' | 'circle_birthday' | 'anniversary'; date: string; days: number; span: string; text: string; template: string | null; person?: string; relation?: string }
export type HomeKind = 'home' | 'pet' | 'plant' | 'vehicle' | 'favorite'

export interface HomeItem {
  id: string
  kind: HomeKind
  name: string
  variety: string
  description: string
  origin: 'generated' | 'change' | 'user'
  since: string
  until: string | null
  edited: boolean
  revision: number
  neighborhood?: string
  city?: string
  features?: string[]
  rent?: number | null
  rent_period?: 'month' | 'week'
  currency?: { code: string; symbol: string; name: string }
  out_of_action?: string | null
}

export interface HomeChange { local_date: string; kind: string; text: string }

export interface HomeView {
  today: string
  items: HomeItem[]
  removed: HomeItem[]
  changes: HomeChange[]
  costs: { rent: number | null; rent_period: string } | null
  varieties: { pet: string[]; vehicle: string[] }
}

export type WardrobeCategory = 'top' | 'bottom' | 'dress' | 'suit' | 'layer' | 'outerwear' | 'shoes' | 'accessory' | 'active' | 'lounge' | 'sleep' | 'work'

export interface WardrobeItem {
  id: string
  category: WardrobeCategory
  name: string
  variety: string
  description: string
  occasions: string
  favorite: boolean
  slot: string | null
  origin: 'generated' | 'change' | 'user'
  since: string
  until: string | null
  edited: boolean
  revision: number
}

export interface WardrobeView {
  today: string
  items: WardrobeItem[]
  removed: WardrobeItem[]
  changes: HomeChange[]
  wearing: { occasion: string; label: string; text: string; items: string[] } | null
  profile: { styles: string[]; size: number; count: number; tier: number; spending: string; work: string | null; career: string | null; summary: string }
  categories: WardrobeCategory[]
  labels: Record<WardrobeCategory, string>
}

/** A townsperson the companion has met around the city: only what the companion has learned so far. */
export interface Townsperson {
  key: string
  name: string
  full: string
  pronouns: string
  age: number
  role: string
  /** Staff at their place, a regular there, or an ordinary resident of `neighborhood`. */
  kind: 'staff' | 'regular' | 'resident'
  staff: boolean
  place: { id: string; name: string; kind: string; neighborhood: string }
  neighborhood: string
  temperament: string
  quirk: string
  times: number
  first_met: string
  first_place: string
  last_met: string
  last_place: string
  goal: string | null
  lately: string | null
  reached: string[]
  routine: string | null
  flaw: string | null
  desire: string | null
  /** How they come across (companion/world/perception.py): the first impression, fuller from the second meeting. */
  comes_across: string | null
  /** From the third meeting: how they once described themselves. */
  says_they_are: string | null
  /** Another of the user's companions, living in town by rules since stepping back: their companion id. */
  cast: string | null
  /** How close they and the companion feel, both ways; read-only. */
  stage?: PairStage | null
}

/** Closeness between two people (companion/memory/pairs.py): how the companion feels, and how the other feels. */
export interface PairStage { level: number; name: string; their_level: number; their_name: string }
/** Another companion this one knows, for the profile: worked out from what happened between them. */
export interface PairTie {
  companion_id: string
  name: string
  feels: { level: number; name: string; cooled: boolean }
  they_feel: { level: number; name: string; cooled: boolean }
  how: string
  group_days: number
  meetings: number
}
/** Two companions about to share a group for the first time: their backstory can be told, once. */
export interface UntoldPair { a: string; b: string; a_name: string; b_name: string; level: number }
/** What the user tells about two companions: a starting stage and a line, both optional. */
export interface Backstory { a: string; b: string; level: number | null; how: string }
/** A companion already here, as a new one would start with them (by their meetings around town). */
export interface NewTie { companion_id: string; name: string; meetings: number; level: number; name_of_level: string }
/** A companion in the workspace: the main character, or one who stepped back. */
export interface CastMember { id: string; name: string; main: boolean; from_town: boolean; stepped_back_at: string | null; created_at: string }
/** A townsperson's drafted profile, before they become the main character. */
export interface CastDraft {
  definition: CharacterDefinition
  person: { key: string; name: string; full: string; age: number; role: string; kind: string; place: string; neighborhood: string }
  /** Who steps back; null when there is no main character yet (a dating match as the first companion). */
  stepping_back: string | null
  matched?: boolean
  /** The companions already here, at the stage the new one would start with each. */
  ties?: NewTie[]
}
export interface TownspersonNow { doing: string; place: { id: string; name: string } | null; mood: string }

/** Debug time (Settings > Debug, companion/debug_time.py): the app clock moved ahead or running faster. */
export interface DebugTime {
  active: boolean
  /** The app's time, and the PC's real time. */
  now: string
  real_now: string
  speed: number
  speeds: number[]
  started_at: string | null
  app_started_at: string | null
  backup: string | null
  jumping: { to: string; done: number } | null
  kept?: boolean
}

/** Story mode (companion/story.py): the user's own story with a narrator, apart from the companion. */
export interface StoryPlace { id: string; name: string; kind: string; neighborhood: string; summary?: string }
export interface StoryScene {
  city: { id: string; name: string; era: string }
  place: StoryPlace
  local_time: string
  weather: string
  places: StoryPlace[]
  /** Who is around, as the user would see them ("the barista there"); never names they have not been given. */
  around: string[]
}
export interface StoryMessage {
  id: string; seq: number; role: 'user' | 'narrator' | 'scene'; text: string; reply_to: string | null
  status: 'complete' | 'failed'; error: string | null; city_id: string; place_id: string; created_at: string
}
/** Someone the user has met in their story (companion/story_people.py), with where their rules put them now. */
export interface StoryPerson {
  key: string; name: string; role: string; city: string; meetings: number; last_met_at: string; notes: string[]
  doing: string; place: { id: string; name: string; city_id: string } | null
}
export interface Story { scene: StoryScene; messages: StoryMessage[]; people: StoryPerson[]; ready: boolean; can_switch: boolean }

/** The dating app (companion/dating.py): the user's profile, the deck, matches and any Story mode date. */
export type DatingGender = 'woman' | 'man' | 'nonbinary'
export type DatingAim = 'serious' | 'casual' | 'friends'
export interface DatingProfile {
  name: string; age: number; gender: DatingGender; interested_in: DatingGender[]; looking_for: DatingAim
  age_min: number; age_max: number; bio: string
}
export interface DatingCard {
  key: string; name: string; age: number; gender: DatingGender; pronouns: string; orientation: string
  looking: DatingAim; looking_text: string; looks: string; job: string; neighborhood: string; bio: string
  /** An older era's personal-column notice, with initials only; '' on a dating app. */
  notice: string
}
export interface DatingPlace { id: string; name: string; kind: string; neighborhood: string; theirs: boolean }
export interface DatingMatch extends DatingCard {
  city: { id: string; name: string }
  /** Set once the match became a companion. */
  companion_id: string | null
  places: DatingPlace[]
}
/** A townsperson's one portrait (companion/dating_photos.py). */
export interface DatingPhoto { status: 'none' | 'queued' | 'running' | 'completed' | 'failed'; error?: string | null; url?: string | null }
export interface DatingWords { title: string; noun: string; like: string; pass: string; matched: string; empty: string; tagline: string; get: string; getting: string }
export interface Dating {
  surface: 'app' | 'column' | 'matchmaker'
  words: DatingWords
  city: { id: string; name: string }
  profile: DatingProfile | null
  /** Whether Story mode is on, so a match can be met there. */
  story: boolean
  /** Whether an image backend is set up, so "Show photo" can make one. */
  photos: boolean
  deck: DatingCard[]
  remaining: number
  matches: DatingMatch[]
  date: { key: string; name: string; place_id: string } | null
  /** After a like: the person, when they liked the user back. */
  matched?: DatingCard | null
}

/** Group chats (companion/groups.py, docs/group-chat.md). */
export interface GroupMember {
  companion_id: string | null
  /** Their full name now; `label` is how the chat names them (a first name unless two share it). */
  name: string
  label: string
  main: boolean
  joined_at: string
  /** The first message they can see: 1 when added with everything so far. */
  sees_from: number
}

export interface GroupMessage {
  id: string
  seq: number
  /** The user, a companion, or the app's own line about who joined or left. */
  kind: 'user' | 'companion' | 'app'
  companion_id: string | null
  name: string
  text: string
  status: 'complete' | 'streaming' | 'failed' | 'cancelled'
  error: string | null
  reply_to: string | null
  created_at: string
  /** Kept as a shared moment: it brings everyone who was there a little closer. */
  kept?: boolean
}

export interface Group {
  id: string
  name: string
  /** The name, or who is in it when it has none. */
  title: string
  reply_cap: number
  created_at: string
  updated_at: string
  members: GroupMember[]
  latest?: GroupMessage | null
}

export type GroupPhase = 'preparing' | 'waiting' | 'writing'

export interface GroupChat {
  group: Group
  messages: GroupMessage[]
  ready: boolean
  /** Replies are being written; `phase` says what the app is doing, never who is about to answer. */
  busy: boolean
  phase: GroupPhase | null
  /** Text written so far, by message id. */
  live: Record<string, string>
}
