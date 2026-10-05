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
  /** Edited by the life simulation's routine tools; kept as-is when the character form saves. */
  schedule?: unknown[]
  life_themes?: string[]
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
}

export interface DeleteResult { deleted_memory_ids: string[]; redacted_message_ids: string[]; linked_memory_ids: string[] }
