import type { CompanionStatus } from './features/status/statusText'
import type { RoutineBlock } from './features/character/schedule'
import type { ColorScheme, Palette } from './features/settings/palette'

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
  /** Another version of the full reply after a holding text: the first version's id (companion/reply_versions.py). */
  version_of?: string | null
  /** Set on a full reply dropped unseen because the user wrote again first; it is never shown. */
  superseded_at?: string | null
  /** A photo of the moment this reply sent (photos in chat). */
  photo?: ChatPhoto | null
  /** Pictures the user sent with this message (companion/pictures.py). */
  pictures?: SentPicture[]
  /** Sent as a voice note: the audio, with the text as its transcript (companion/voice/notes.py). */
  voice?: VoiceNote | null
  /** Your message sounds like self-harm: the app's note with places to get help shows under it (companion/safety.py). */
  crisis_help?: boolean
  /** Set on a message brought in from an old chat file (companion/imports/chats.py): older history. */
  import_id?: string | null
}

export interface VoiceNote { url: string; duration_ms: number | null; engine: string }

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
  /** Taken out of the chat by the user; the chat shows nothing, or Undo while it is still open. */
  removed?: boolean
  /** The shape it is made in; the chat holds that space while it loads. Older servers leave it out. */
  aspect?: 'square' | 'landscape' | 'portrait'
  /** A meme's picture: made by an image model, a template on this computer, or a reaction GIF (companion/images/gifs.py). */
  source?: 'model' | 'template' | 'gif'
  /** A template's or GIF's own address and size, there from the start; null for a picture an image model makes. */
  src?: string | null
  width?: number | null
  height?: number | null
  /** A template's text boxes as fractions of the picture, top to bottom; empty for the classic top and bottom lines. */
  boxes?: MemeBox[]
  /** A GIF's page on GIPHY. */
  page?: string
  /** A GIF's first frame, shown instead while motion is reduced. */
  still?: string
}

export interface MemeBox { x: number; y: number; w: number; h: number }

/** Where meme pictures come from (Settings > Images > Memes and GIFs). */
export interface MemeSources { folder: string; mine: number; pack: number; formats_on: boolean; formats_here: number; formats_total: number; gif_key: boolean; key_here: boolean }

export interface TextingStyle { bursts: boolean; lowercase: boolean; typos: boolean; quick?: boolean }

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

/** What they look like, field by field; empty strings and nulls are drawn for them, leaving out what Appearance says. */
export interface Looks {
  age: number | null
  height_cm: number | null
  weight_kg: number | null
  build: string
  skin: string
  face: string
  jaw: string
  nose: string
  eyes: string
  eye_shape: string
  hair: string
  facial_hair: string
  feature: string
  /** What the app filled in when a townsperson became a companion; still-equal fields may change over time. */
  drawn?: Partial<Record<string, string | number>>
}

export interface CharacterDefinition {
  name: string
  /** "MM-DD"; empty picks a date for them. */
  birthday?: string
  /** On: they stay the age written instead of turning a year older on each birthday (companion/life/ages.py). */
  keeps_age?: boolean
  kind?: string
  lifespan?: number | null
  identity: string
  personality: string
  voice: string
  skills: string[]
  flaws: string[]
  interests: string[]
  background: string
  appearance: string
  /** The In photos line pictures use (companion/images/prompts.py `in_photos`); empty follows the appearance. */
  in_photos?: string
  /** Their name in every picture prompt (companion/images/runner.py `named`), off by default. */
  name_in_pictures?: boolean
  /** Face shape, height, build and the rest (companion/world/looks.py); an empty field is drawn for them. */
  looks?: Looks
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
  /** Their week moved to fit your evenings or onto your clock (companion/life/their_hours.py); the server moves it. */
  their_hours?: TheirHours | null
  life_themes: string[]
  money: MoneySetup
  texting?: TextingStyle
  /** Their adult side as the user set it (companion/world/intimacy.py); empty fields use the roll. */
  intimacy?: IntimacySetup | null
  /** Personality sliders (companion/world/personality.py); null, or a trait left out, is read from their words and rolled. */
  personality_sliders?: PersonalitySliders | null
}

/** How their week sits against your clock: 'fit' moved by the app, 'mine' on your clock, 'city' their city's hours. */
export interface TheirHours { mode: 'fit' | 'mine' | 'city'; shift: number; why: string; zone: string; fit: number }

export type PersonalityKey = 'social' | 'warmth' | 'order' | 'curiosity' | 'stress'
/** One slider: 0 low, 1 in between, 2 high, and who set it. */
export interface PersonalitySlider { level: 0 | 1 | 2; source: 'rolled' | 'idea' | 'you' }
export type PersonalitySliders = Partial<Record<PersonalityKey, PersonalitySlider>>
/** A slider's words: its name, each end and what each stop looks like. */
export interface PersonalityTrait { key: PersonalityKey; name: string; low: string; high: string; shows: [string, string, string] }
/** The sliders as profiles show them: summary chips and the four-letter type they read as. */
export interface PersonalityView { sliders: Required<PersonalitySliders>; chips: string[]; type: string | null; traits?: PersonalityTrait[] }

export interface IntimacySetup {
  orientation: string; level: string; drive: string; interests: string[]
  /** The user chose the interests, so an empty list means none rather than the roll. */
  interests_picked?: boolean
  /** Their own turn-ons and turn-offs, in the user's words. */
  own_into: string[]; not_into: string[]; note: string
}

/** An adult side with labels for showing it (companion/world/intimacy.py view). */
export interface AdultSide extends IntimacySetup { level_label: string; drive_label: string; interest_labels: string[] }

/** What the character form offers for the adult side, and what the seed gives them as the form stands. */
export interface AdultSideChoices {
  rolled: AdultSide | null
  /** False when their sheet reads as under 18: they never get one. */
  adult: boolean
  orientations: string[]
  levels: { id: string; label: string; text: string }[]
  drives: { id: string; label: string; text: string }[]
  groups: { id: string; label: string }[]
  interests: { id: string; label: string; tier: number; group: string }[]
}

export type SpendingStyle = 'careful' | 'balanced' | 'spender'

/** How the companion's money works; pay, rent and prices come from the world data. */
/** Their hours: '' follows their work (companion/life/shifts.py). */
export type Employment = '' | 'staff' | 'rota' | 'freelance'

export interface MoneySetup {
  career: string
  style: SpendingStyle
  saving_for: string
  goal: number
  goal_since: string
  employment: Employment
  /** What a student studies; empty reads it from who they are. */
  field?: string
}

export interface CareerSummary { id: string; name: string; pay: string; eras: string[]; adult?: boolean }

interface MoneyHappening { label: string; on: string; cost: number; for?: MoneyFor; shown?: string }
export type MoneyFor = 'home' | 'clothes' | 'outing' | 'trip' | 'looks' | 'food' | 'media' | 'hobby' | 'ring' | 'wedding' | 'school' | 'deposit' | 'business' | 'care' | 'gift' | 'funeral' | 'admin' | 'family' | 'owed' | 'childcare' | 'sitter' | 'baby'

export type MoneyView = { date: string } & ({ available: false; reason: string } | {
  available: true
  currency: { code: string; symbol: string; name: string }
  period: 'month' | 'week'
  style: SpendingStyle
  career: { id: string; name: string; pay: string; guessed: boolean } | null
  housing: { unit: string; label: string; neighborhood: string }
  budget: { income: number; rent: number; upkeep: number; essentials: number; fun: number; saving: number }
  rent_from: 'home' | 'budget'
  /** Living on a pension, and paying a mortgage on a place they bought (companion/life/big_turns.py). */
  retired?: boolean
  /** A medieval kingdom or a fairy-tale land: payments on a place instead of a mortgage, and no pension. */
  medieval?: boolean
  /** Their own business's short name ('bakery') while they run one (companion/life/business.py). */
  business?: string | null
  owned?: boolean
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
  /** Their status line, or away line while they sleep, work or are out (companion/life/status.py). */
  status?: CompanionStatus | null
}

export interface WorkspaceSettings {
  user_timezone: string
  auto_backups?: AutoBackups
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
  /** Period words in period cities: letters in Camelot, comms aboard a ship (companion/world/era_words.py). On unless turned off. */
  period_words?: boolean
  /** Keep my colours everywhere: no companion's own colours or name font (companion/their_look.py). */
  keep_my_colours?: boolean
  /** The app's colors (Prospero's Study's palettes); Retro IM keeps its own. */
  color_scheme?: ColorScheme
  /** The four colors of the custom scheme, or null before one is made. */
  custom_palette?: Palette | null
  /** 'system' matches the computer (Paper or Ink), 'paper' is the light profile, 'scheme' uses color_scheme. */
  theme?: 'system' | 'scheme' | 'paper'
  /** They can ask to remember more: one hidden extra look through memory when a reply needs it. On unless turned off. */
  recall_more?: boolean
  /** Out-of-character asides go to the helper instead of the companion (src/features/conversation/ooc.ts). */
  ooc_to_helper?: boolean
  /** The markers for those asides; null means the defaults (OOC: and ((...))). */
  ooc_markers?: { open: string; close: string }[] | null
  /** Story mode (src/features/story) is opt-in, in Settings > Advanced. */
  story_mode?: boolean
  /** The note under a group message when someone lets a secret slip; on unless turned off. */
  show_secret_slips?: boolean
  /** Hidden values: how companions feel (Today, group members); off unless turned on. */
  show_moods?: boolean
  /** Hidden values: who has heard a companion's news (Today); off unless turned on. */
  show_news?: boolean
  /** Hidden values: "Why it went this way" and its odds under storylines, chapters and reactions; off unless turned on. */
  show_odds?: boolean
  /** Settings > Realism > Adult side of life (companion/world/intimacy.py): adults only; off unless turned on. */
  adult_side?: boolean
  /** Hidden values: what townsfolk are like that way, for the user's eyes; off unless turned on. */
  show_adult_side?: boolean
  /** The numbers behind their life, such as upkeep meters (Settings > Realism > Hidden values). */
  show_home_meters?: boolean
  /** Settings > Debug: every model request and response is written in full to logs/model-calls; off by default. */
  record_model_calls?: boolean
  /** The one-time notice that the characters are AI, with the 18+ confirmation, has been read. */
  ai_notice_confirmed?: boolean
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
  /** The model "Set it up for me" downloaded (companion/ready.py), named as the welcome step names it. */
  builtin?: boolean
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
  /** A plan that closed on its own once it was over: the open status it had. */
  settled_from?: PlanStatus | null
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
  /** A pet: work, studies and family are not offered for them. */
  pet?: boolean
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
  /** On a companion message: what they said about themselves, now kept. */
  self_facts?: SelfFact[]
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
  model_routines: boolean
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
  recap_after_days: number
  texts_gap_hours: number
  /** 0 sizes the circle by how sociable the companion is. */
  circle_size: number
  /** "MM-DD" or empty; filled in when the user says it in chat. */
  user_birthday: string
  /** Replies wait while the companion is at work or asleep. */
  paced_replies: boolean
  day_shifts: boolean
  on_her_mind: boolean
  /** Storylines from quiet (0) through realistic and dramatic to soap opera (3). */
  drama: number
  /** This world's own drama level (companion/life/world_drama.py), or null while it still follows the level carried
   * between worlds; `drama` is always the level this world runs at. */
  world_drama: number | null
  /** Their companion is the only one in this world, so storylines start a little more often for them. */
  alone: boolean
  /** Home upkeep (companion/life/upkeep.py): 0 off, 1 light, 2 true to life, 3 messy. */
  upkeep_realism: number
  /** Looks that change (companion/life/grooming.py): never (0), now and then, like real life (2), often (3). */
  looks_realism: number
  /** Pets with lives of their own (companion/life/pets.py): 0 off, 1 light, 2 true to life, 3 dramatic. */
  pets_realism: number
  pets_can_die: boolean
  /** Kitchen ups and downs on the same scale: staples running out, dinners going sideways (companion/life/kitchen.py). */
  kitchen_realism: number
  /** Life admin (companion/life/admin.py): 0 off, 1 light, 2 true to life, 3 dramatic. */
  admin_realism: number
  /** Work life (companion/life/work.py): 0 off, 1 steady, 2 true to life, 3 dramatic. */
  work_realism: number
  /** Group chat guests (companion/group_guests.py): how often someone named in a group is pulled in, 0 never to 3. */
  guests_realism: number
  /** Reading, watching and listening (companion/life/media.py): 0 off, 1 light, 2 true to life, 3 dramatic. */
  media_realism: number
  /** Hobbies that progress (companion/life/hobbies.py): 0 off, 1 light, 2 true to life, 3 dramatic. */
  hobbies_realism: number
  /** Memes and GIFs (companion/images/photos.py): how often memes come unasked, 0 never (none at all) to 3 often. */
  memes_realism: number
  /** Inner voice (companion/life/narrator.py): how much of what is on their mind the Watching page tells, 0 to 3. */
  inner_voice: number
  /** Their look in chat (companion/their_look.py): 0 off, 1 steady, 2 true to life, 3 expressive. */
  their_look: number
  waking_realism: number
  /** How quickly they read your texts while free (companion/life/reading.py): 0 at once, 1 quick, 2 natural, 3 slow. */
  read_pace: number
  /** Getting together (companion/life/together.py): how often they suggest meeting up, invite you over and drop by, 0 never on their own to 3 often. */
  together_realism: number
  /** Rough patches (companion/life/rough_patches.py): 0 off, 1 blows over by morning, 2 true to life, 3 dramatic. */
  rough_patches_realism: number
  /** Next steps (companion/life/steps.py): how soon they bring up the next step, 0 only when you do, 1 slow, 2 true to life, 3 fast. */
  steps_pace: number
  /** Whether a close friend can fall for you (companion/life/steps.py). */
  friends_fall: boolean
  /** Breaks and breakups (companion/life/breakups.py): on for real life and drama, off for an easy life. */
  breakups: boolean
  /** Their own love life (companion/life/love_life.py): 0 nothing new, 1 quiet, 2 true to life, 3 lots going on. */
  love_life: number
  /** Life's big turns (companion/life/big_turns.py): how often life chapters come, 0 off, 1 gentle (good turns only), 2 true to life, 3 eventful. */
  life_turns: number
  /** Births and growing families (companion/life/families.py): 0 none, 1 now and then, 2 true to life, 3 lots. */
  growing_families: number
  /** Our child (companion/life/our_child.py): 0 easy kids ... 3 true-to-life chaos. */
  family_life: number
  /** The family a new companion comes from (companion/life/family_tree.py): 0 simple, 1 gentle, 2 true to life, 3 more drama. */
  family_shapes: number
  /** Loss and grief (companion/life/loss.py): whether people can pass away (off on every preset), and how often: 0 rare, 1 now and then, 2 true to life, 3 often. */
  people_pass_away: boolean
  loss: number
  /** Local politics (companion/life/politics.py): 0 off, 1 quiet, 2 true to life, 3 lively. */
  politics_realism: number
  /** Trolls and snark on posts (companion/life/social.py): 0 off, 1 rivals only, 2 snarky, 3 trolls. */
  trolls_realism: number
}

/** Where you and the open companion stand on their ladder (GET /api/life/steps); `ladder` is null for mentors, family and other. */
export interface StepsView {
  ladder: 'romance' | 'friendship' | null
  just_friends: boolean
  step?: string
  label?: string
  next?: string | null
  since?: string
  text?: string
  can_fall?: boolean
  steps?: { step: string; label: string; on: string; how: 'start' | 'history' | 'them' | 'you' | 'set' | 'confession' }[]
  ladder_steps?: { step: string; label: string }[]
  /** Only with Hidden values' odds on. */
  planned?: { step: string; due_on: string; consequence_id: string | null; topic: string } | null
  asks?: { id: string; step: string; side: 'them' | 'you'; status: 'open' | 'yes' | 'not_yet' | 'no' | 'lapsed'; topic: string; on: string; consequence_id: string | null }[]
  /** Moving in together (companion/life/moving_in.py), from the moving-in step on; `consequence_id` only with odds on. */
  moving_in?: MovingIn | null
  /** Living apart again after living together: since when, and who moved out ('you' the user, 'them' the companion). */
  apart?: { since: string; by: 'you' | 'them' | null } | null
}

/** Wanting children (GET /api/life/steps/family, companion/life/parenthood.py); `shown` false for one who reads as
 * a minor. The route and the family step only for a romance; consequence ids only with Hidden values' odds on. */
export interface FamilyView {
  shown: boolean
  wants: 'yes' | 'someday' | 'no'
  wants_how: 'set' | 'description' | 'seeded' | 'nudged'
  nudged_by: string | null
  wants_consequence_id: string | null
  wants_options: { key: string; label: string }[]
  romance: boolean
  route?: string; route_how?: 'set' | 'seeded'; route_consequence_id?: string | null
  routes?: { key: string; label: string }[]
  decided_on?: string | null; decided_how?: 'them' | 'you' | 'set' | null; can_decide?: boolean
  /** Expecting or adopting together (companion/life/expecting.py), once you two have decided. */
  journey?: Journey | null
  /** Another child (companion/life/parenthood.py): when you two decided on one, and whether it can be set now. */
  another_on?: string | null
  can_decide_another?: boolean
}

/** The pair's own children (GET /api/life/steps/ours, companion/life/our_child.py); `shown` false with none. Who
 * looks after them is the app's pick (`seeded`) or the user's (`set`); its consequence id only with Hidden values'
 * odds on. */
export interface OursView {
  shown: boolean
  children: OurChild[]
  care?: 'both_work' | 'part_time' | 'them_home' | 'you_home'
  care_how?: 'set' | 'seeded'
  /** Whether it applies now: until the youngest starts school. */
  care_now?: boolean
  care_consequence_id?: string | null
  cares?: { key: string; label: string }[]
  /** Where they live while their parents live apart (companion/life/custody.py); null under one roof. */
  custody?: Custody | null
}

/** Where the pair's children live after a breakup (`split`) or across cities (`far`, with the user's `city`):
 * `patterns` to pick from only after a breakup; the consequence id only with Hidden values' odds on. */
export interface Custody {
  pattern: 'with_them' | 'shared' | 'with_you'
  how: 'set' | 'seeded'
  split: boolean
  far: boolean
  /** The day it ended, after a breakup. */
  ended_on: string | null
  city: string | null
  detail: string
  patterns: { key: string; label: string }[]
  consequence_id: string | null
}

/** One child of the pair: their sheet for now (a newborn has only a temperament) and the milestones reached. Words
 * only, never a picture. */
export interface OurChild {
  id: string
  name: string
  pronouns: string
  born_on: string
  arrived_on: string
  journey_id: string
  age: number
  age_text: string
  grown: boolean
  relation: 'son' | 'daughter' | 'child'
  temperament: string | null
  likes: string | null
  quirk: string | null
  milestones: { key: string; label: string; date: string }[]
  latest: { label: string; date: string } | null
  kind?: KindShown
}

/** A child of the pair on Today. */
export type TodayChild = Pick<OurChild, 'id' | 'name' | 'age_text' | 'relation' | 'likes' | 'latest'> & {
  /** 'With Sam today', 'With you today', 'Lives with Sam' while their parents live apart. */
  where_today?: string | null
}

/** How the child comes: the stages reached, and once it is under way those to come; the child's name once known;
 * consequence ids only with Hidden values' odds on. */
export interface Journey {
  route: string
  status: 'planned' | 'running' | 'home'
  due_on: string | null
  arrived_on: string | null
  name: string | null
  renamed: boolean
  stages: { key: string; label: string; date: string | null; done: boolean }[]
  consequences: string[]
  /** The same outcomes with the engine's choice each is ('soon', 'turn', 'wait', 'match', 'fostered'). */
  outcomes?: { key: string; id: string }[]
}

/** Companions who already have kids (GET /api/life/steps/kids, companion/life/kids.py); `shown` false with none. Where
 * they live is the app's pick (`seeded`), fixed by the description or the household (`fixed`), or the user's (`set`);
 * consequence ids only with Hidden values' odds on. */
export interface KidsView {
  shown: boolean
  how?: 'description' | 'town' | 'seeded'
  kids?: Kid[]
  /** Whether the user can add a child of theirs by hand (never for a companion who reads as under 18). */
  can_add?: boolean
  other?: KidsParent | null
  /** Who in their circle could be the kids' other parent, the one who is first. */
  others?: KidsParent[]
  pattern?: 'together' | 'with_them' | 'shared' | 'weekends' | 'sole'
  pattern_how?: 'set' | 'seeded' | 'fixed'
  patterns?: { key: string; label: string }[]
  pattern_consequence_id?: string | null
  consequence_id?: string | null
  /** The arrangement spelled out: "with Dana, every other weekend at Mark's". */
  detail?: string
  step_parent?: boolean
  /** For a romance not living together: whether you have met the kids. */
  meeting?: 'met' | 'soon' | 'unmet' | null
}

export interface Kid { id: string; name: string; pronouns: string; born_on: string; age: number; age_text: string; relation: 'son' | 'daughter' | 'child'; by_hand?: boolean }

/** The kids' other parent, or someone in their circle who could be: `made` when the app made them for the kids (naming
 * someone else renames them), `made_up` when nobody named them either. */
export interface KidsParent { id: string; name: string; role: string; made: boolean; made_up: boolean }

/** Whose place in one city ('yours', 'theirs', 'new'), or who moves across the distance ('them' to your city; 'you',
 * which waits until you move to theirs). `place` is the neighbourhood, `city` the city, `home` the shared home once moved. */
export interface MovingIn {
  status: 'moving' | 'waiting' | 'moved'; plan: 'yours' | 'theirs' | 'new' | 'them' | 'you'
  city: string; place: string; home: string; move_on: string | null; moved_on: string | null; consequence_id: string | null
  /** Sharing a home: moving into (or living in) the home you share with another partner (`with`, first names), whether
   * they are open to sharing it (`ready`), and who living there isn't (`not_ready`). */
  joins?: boolean; ready?: boolean; with?: string[]; not_ready?: string[]
  /** On the page of one living with you: another partner who would move in, and whether this one is open to it. */
  newcomers?: Newcomer[]
  /** While that move waits or is on its way: each one's answer, the newcomer first. */
  rolls?: ShareRoll[]
}

export interface ShareRoll { name: string; open: boolean; consequence_id: string | null }

export interface Newcomer {
  name: string; status: 'moving' | 'waiting'; move_on: string | null; open: boolean; not_ready: string[]
  consequence_id: string | null
}

export interface BackupResult { path: string; created_at: string; database_bytes: number }
export interface BackupEntry {
  name: string; bytes: number; kind: 'backup' | 'pre-upgrade' | 'before-reset' | 'before-delete' | 'before-debug' | 'auto'; readable: boolean
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

export type AutoBackups = 'off' | 'daily' | 'weekly'
export interface BackupList {
  backups: BackupEntry[]; pending: { name: string; requested_at: string } | null
  /** Automatic backups of every world (companion/auto_backup.py), and when this world last had one. */
  auto_backups: AutoBackups; last_auto_backup: string | null; auto_backup_count: number
}

export interface LifeEvent {
  id: string
  kind: 'routine' | 'plan' | 'ordinary' | 'thread'
  status: 'proposed' | 'committed' | 'rejected' | 'superseded'
  summary: string
  details: { label?: string; activity?: string; post?: string; mood?: string; local_date?: string; timezone?: string; place?: { id: string; name: string } | null; trip?: unknown; outing?: { at: string } | null }
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
  plans: { shared: SharedPlan[]; companion: LifeEvent[]; threads: LifeEvent[]; admin?: AdminItem[]; stays?: AdminItem[] }
  feed_unread: number
  last_run: LifeRun | null
  paused: boolean
  paused_at: string | null
  clock_behind: boolean
  mood: AbsenceMood | null
  /** How they feel right now (companion/moods.py); only with Hidden values > Show how they're feeling on. */
  feeling?: GroupMood | null
  last_seen_at: string | null
  day: { date: string; body: BodyState | null }
  /** Birthdays and talking milestones today or within a week (companion/life/occasions.py). */
  occasions?: Occasion[]
  /** On their mind (companion/life/thoughts.py): the last week, newest first; null when switched off. */
  mind?: { thoughts: Thought[] } | null
  moments: Moment[]
  dreams: Dream[]
  /** The pair's own children (companion/life/our_child.py). */
  family?: TodayChild[]
}

/** One day's thought on the companion's mind. */
export interface Thought { day: string; text: string }
/** A small moment the Life deck drew into a day (companion/life/deck.py); `odds` only with Hidden values > odds on. */
/** A dream the night before `day` (companion/life/dreams.py). */
export interface Dream { day: string; text: string; sleep_talk: string | null }
export interface Moment { day: string; title: string; text: string; source: string; picked_by: 'dice' | 'user'; odds?: number }

/** How the companion feels physically today, carried over from the day before. */
export interface BodyState { state: 'sick' | 'hungover' | 'tired' | 'worn out' | 'sore'; because: string }

export interface PauseRecord { id: string; started_at: string; ended_at: string | null; catch_up_requested_at: string | null; catch_up_run_id: string | null }

export type Reaction = 'heart' | 'laugh' | 'wow' | 'sad' | 'hug'

export type FeedSource = 'all' | 'companion' | 'circle' | 'mine'
/** `user` is the user's own post, which every companion and their circles see. */
export interface FeedAuthor { kind: 'companion' | 'person' | 'user'; id: string | null; name: string; role: string }
/** `role` says whose friend a commenter is ("Mira's sister"), on the user's own posts. */
export interface FeedComment { author: 'companion' | 'person'; name: string; text: string; at: string; role?: string }

export interface FeedPost {
  id: string
  /** Life posts tell life events; social posts (friends, status, shout-outs, city news, questions) and the user's own carry their own text. */
  kind: 'digest' | 'event' | 'status' | 'friend' | 'birthday' | 'holiday' | 'city' | 'question' | 'user'
  source: 'life' | 'social' | 'user'
  author: FeedAuthor
  intro: string
  status: 'visible' | 'hidden'
  read: boolean
  reaction: Reaction | null
  occurs_at: string
  created_at: string
  events: { id: string; summary: string; caption: string; mine?: { caption: string; summary: string }; mood: string | null; label: string | null; kind: string; starts_at: string; ends_at: string; revision: number }[]
  text?: string
  context?: string
  place?: string
  options?: string[]
  answer?: string | null
  image: PostImage | null
  audience: { likes: string[]; comments: FeedComment[] }
  /** The user's comments and the poster's answers, oldest first; `waiting` while an answer is still to show. */
  thread?: { comments: ThreadComment[]; waiting: boolean }
}

/** A comment the user left on a post (`user`) or the answer it got from whoever posted (`poster`, with their name). */
export interface ThreadComment { id: string; author: 'user' | 'poster'; name: string | null; text: string; reply_to: string | null; at: string }

export interface FeedPage { posts: FeedPost[]; next_before: string | null; unread: number }

export interface CitySummary { id: string; name: string; region: string; country: string; timezone: string; summary: string; era?: string; category?: string }

export interface ContextReceipt { budget_tokens: number; estimated_tokens: number; included: Record<string, string[]>; omitted: Record<string, string[]> }
export interface ContextPreview { system: string; note: string; history: { role: 'user' | 'assistant'; content: string }[]; messages: { role: 'user' | 'assistant'; content: string }[]; receipt: ContextReceipt }

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
/** Someone's kind and how long they live (companion/world/lifespans.py `described`). `own` is the user's pick of
 * How long they live: null as their kind, 0 doesn't age. `years` is what applies (null: they don't age). */
export interface KindShown {
  kind: string
  label: string
  own: number | null
  years: number | null
  kind_years: number | null
  life_age: number | null
  /** The app's pick, and the user's ('' for none) where it can differ. */
  found?: string
  from_parents?: boolean
  picked?: string
}

/** What the Kind and How long they live pickers offer (GET /life/kinds). */
export interface KindChoices {
  kinds: { id: string; label: string; lifespan: number | null }[]
  spans: number[]
}

/** Someone in another companion's circle the open companion could know too (GET /life/circle/shareable). */
export interface ShareablePerson {
  id: string
  name: string
  full_name: string
  role: string
  owner_id: string
  owner: string
}

export interface CirclePerson {
  kind?: KindShown
  own_kind?: string
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
  /** Someone from another companion's circle this one knows too (companion/life/shared_people.py): whose circle
   * they live in and who they are there; `role` above is who they are to this companion. */
  shared?: { owner_id: string; owner: string; role: string }
  /** Someone the app made who stepped aside when a shared person took their place (a second mom): who that is. */
  made_room_for?: string | null
  /** The other companions who know someone in this circle, and who they are to each. */
  also?: { companion_id: string; name: string; role: string }[]
  /** How close they and the companion feel, both ways (companion/memory/pairs.py). */
  stage?: PairStage | null
  /** Where the user says the two of them start, 1 Just met to 5; unset is the app's pick. */
  start_stage?: number
  /** Whether they and the companion know each other, or only one knows of the other (companion/life/circle.py
   * `knowing`): 'they' know the companion, or the 'companion' knows of them. `knowing_set` when the user said so. */
  knowing?: Knowing
  knowing_set?: boolean
  /** What they think of you, once they have met you (companion/life/their_people.py). */
  met?: CircleMet | null
  now: RoutineBlock | null
  recent: DiaryEntry[]
  /** Their pets (companion/life/pets.py), seeded by who they are until the user changes them. */
  pets?: CirclePetView[]
  /** Someone the companion is seeing (companion/life/love_life.py): "Together 8 months, exclusive". */
  love?: string
  /** The latest roll for the two of them, only with Hidden values' odds on. */
  love_odds?: string | null
  /** Their children (companion/life/families.py), in words only. */
  children?: CircleChild[]
  /** The month their baby is due while they are expecting: "March". */
  expecting?: string | null
  /** The companion and this partner are adopting rather than expecting. */
  adopting?: boolean
  /** Their place in the companion's family plan (companion/life/family_circle.py). */
  kin?: { id: string; ties: Record<string, string> }
  /** Family the companion doesn't talk to anymore: removed, in a Not in touch group. */
  estranged?: boolean
  /** Someone who died before the companion's story began: the companion's age then. */
  long_ago?: number
  /** Written into the character's description (companion/life/named.py): spared from passing away unless `spared` is false. */
  sheet?: string
  /** Added by the user on the circle list (companion/life/circle_edit.py): spared from passing away like `sheet`. */
  by_hand?: boolean
  /** The user's own words about them, which the chat reads. */
  note?: string
  /** People can pass away (companion/life/loss.py): whether the user spared them, or let them pass away. */
  spared?: boolean
  /** The day they passed away, when they have. */
  late?: string
  loss?: { id: string; died_on: string; consequence_id: string | null } | null
}

/** A child in the circle (companion/life/families.py): born in the app, listed under their parent. `relation` is what
 * they are to the companion ('niece', 'godson'), null for a friend's or coworker's baby. */
export interface CircleChild {
  id: string
  name: string
  pronouns: string
  born_on: string
  age: number
  /** 'a newborn', '3 weeks old', '7 months old', '2'. */
  age_text: string
  relation: string | null
  title: 'family' | 'godchild' | 'friend'
  /** The companion's own child with their partner (companion/life/own_family.py). */
  own?: boolean
}

/** A circle person who has met the user, or is about to (companion/life/their_people.py). `before` is a couple who go
 * back years, so they have always known you; `meeting` is a meet-up still to come ('soon') or under way ('now'). `consequence_id` only with Hidden
 * values' odds on. */
export interface CircleMet {
  met_on: string | null
  before: boolean
  meeting: 'soon' | 'now' | null
  impression: 'warm' | 'smitten' | 'curious' | 'protective' | 'wary'
  warmth: number
  label: string
  consequence_id: string | null
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
export type Knowing = 'both' | 'they' | 'companion'
/** Whether the companion lives aboard a ship or station (companion/world/ships.py `vessel`), else null. */
export interface CircleHome { aboard: 'ship' | 'station' | null }

export interface CircleRoom { people: number; target: number; sociability: 'quiet' | 'usual' | 'social' }

export type ImageStatus = 'none' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'interrupted'

export interface PostImage { status: ImageStatus; job_id: string | null; ref: string | null; error: string | null; updated_at: string | null; outdated?: boolean }

export type BackendKind = 'comfyui' | 'codex' | 'hosted'
export type HostedProvider = 'openrouter' | 'google' | 'openai' | 'nanogpt' | 'novelai' | 'other'

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
  // ComfyUI: the model family whose built-in workflow runs; null for other kinds.
  family: ImageFamily | null
  // The style the model family starts prompts with while `style` is '' (Booru and NovelAI: quality tags); null for none.
  family_style: string | null
  // Its prompts go out as booru tags (solo, 1boy, ...) rather than sentences.
  tag_prompts: boolean
  // ComfyUI: files chosen for the built-in workflow ('' means its default); null for other kinds.
  model_files: ModelFiles | null
  // The smaller Krea 2 model file the app picked for this computer's graphics card, used while no model is chosen.
  model_fit: string | null
  // ComfyUI: LoRAs applied after the character's own, in order; null for other kinds.
  style_loras: StyleLora[] | null
  // ComfyUI: the built-in workflow's sampler; null in a field means the workflow's own value.
  sampler: SamplerSettings | null
  reference_workflow: boolean
  // Can make a picture that follows an earlier one (the onboarding profile pictures).
  takes_reference: boolean
  has_key: boolean
  // With no key of its own: the text model profile whose key it uses for the same service.
  key_from: string | null
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
  /** Whether this world draws with it (companion/images/world_choice.py). */
  in_world: boolean
}

/** Which backends this world draws with: all of them until the user picks some (`own`). `falls_back`: none of the
 * picks is on, so every backend is used for now. `used`: the backends it draws with now, in the user's order. */
export interface WorldImageBackends { own: boolean; picked: string[]; falls_back: boolean; used: string[] }
export interface ImageBackendList { backends: ImageBackend[]; world: WorldImageBackends }

export interface ImageSettings { automatic_images: boolean; chat_photos: boolean; unprompted_photos: boolean; meme_formats: boolean; follow_profile_picture: boolean; daily_limit: number; queue_limit: number; fallback: boolean; aspect: 'square' | 'landscape' | 'portrait'; style: string }

export interface BackendCheck { ok: boolean; summary: string; details: string[]; install?: { id: string; label: string }[] }

export type ImageFamily = 'krea2' | 'qwen21' | 'zimage' | 'anima' | 'booru'
export type ModelFileKey = 'unet_name' | 'clip_name' | 'clip_type' | 'vae_name' | 'ckpt_name' | 'ref_unet_name'
/** The files of the family's own loaders only ('' means the workflow's default). */
export type ModelFiles = Partial<Record<ModelFileKey, string>>
export type FileListKey = ModelFileKey | 'lora' | 'sampler_name' | 'scheduler'
export interface SamplerSettings { steps: number | null; cfg: number | null; sampler_name: string | null; scheduler: string | null }
export interface StyleLora { name: string; strength: number; trigger: string }
/** What a ComfyUI server offers the built-in workflow's loaders and its LoRAs, the family's own first (`matching`
 * lists those); ok is false when it could not be asked. The character's own LoRA is left out of `lora`. */
export interface BackendFiles { ok: boolean; error: string | null; family: ImageFamily; defaults: ModelFiles; sampler_defaults: SamplerSettings; options: Partial<Record<FileListKey, string[]>>; matching: Partial<Record<FileListKey, string[]>>; character_lora: string | null }
export interface ModelLink { name: string; role: 'model' | 'clip' | 'vae' | 'reference'; file: string | null; url: string; licence: string; family: ImageFamily }

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
export type ArgumentSource = 'place' | 'latitude' | 'longitude' | 'topic' | 'date' | 'literal' | 'url' | 'session'
export interface ToolArgument { source: ArgumentSource; value?: string | number | boolean }
export interface ToolProperty { type?: string | string[]; description?: string; enum?: unknown[]; minimum?: number; maximum?: number; default?: unknown }
export interface ContextTool { name: string; description: string; input_schema: { properties?: Record<string, ToolProperty>; required?: string[] }; read_only: boolean }
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

/** One chat in the chat list (companion/chats.py): a companion's, and later group chats. Never says who is online; a
 * companion's status may carry an away message, as a hint only. */
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
  /** A companion's status line (companion/life/status.py); absent for group chats. */
  status?: CompanionStatus | null
  /** A companion's profile picture (lora_references), or null while they have none; absent for group chats. */
  portrait_reference_id?: string | null
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
  // Picture 1 when it is their profile picture as it is (often the user's own): nothing is made for it.
  own?: string
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
    | 'works_at' | 'detail' | 'said'
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
  /** A pet fact: 'tracked' when it names a pet the app keeps (that pet's own lines win), else 'untracked'. */
  pet_link?: 'tracked' | 'untracked'
  /** The pet kind the fact's words point to, for "Add as their pet". */
  pet_kind?: string
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

export interface StoryBeat {
  on: string; text: string; share: string; tone: 'good' | 'bad' | 'mixed'
  /** The consequence engine's outcome this beat came from, when it could have gone more than one way. */
  consequence: string | null
}
/** A lasting change to the companion's life (companion/life/chapters.py). */
/** News travels (companion/news.py): the companion's recent news and who has heard it, in the order they did. */
export interface NewsItem {
  id: string
  text: string
  happened_on: string
  heard: { name: string; heard_on: string; from: string | null; companion_id: string | null }[]
}

/** The pregnancy's hard turn once it has come (companion/life/expecting.py `turn_shown`), listed on Today with an
 * Undo like a chapter: bed rest until the birth, an early arrival for two weeks after it. */
export interface FamilyTurn {
  /** The journey's id. */
  id: string
  kind: 'bed_rest' | 'early'
  on: string
  title: string
  consequence: string | null
}
export interface LifeChapter {
  id: string
  kind: 'new_job' | 'move' | 'pet' | 'hobby' | 'friend_moves' | 'relationship' | 'move_in' | 'move_out' | 'school' | 'career_change' | 'buy_place' | 'retire' | 'business' | 'health' | 'caring'
  started_on: string
  title: string
  /** Where a big turn stands (companion/life/big_turns.py); null for other chapters. */
  stage: string | null
  /** The day its latest stage came (the day it began for other chapters), as Today shows it. */
  on: string
  consequence: string | null
  /** How its latest stage went (a business's months, a health turn's outlook, a parent's care), still changeable. */
  outcome?: string | null
  undone: boolean
}

/** The Character page's life lately (GET /api/life/chapters/lately): big turns on their way, and the latest chapters. */
export interface LifeLately {
  now: { id: string; kind: LifeChapter['kind']; started_on: string; line: string }[]
  lately: { id: string; kind: LifeChapter['kind']; on: string; title: string }[]
}

/** Which way a reason pushed the odds of the option it sits under. */
export type ReasonMove = 'more' | 'less' | 'out' | 'possible'
/** How a turning in the world went and why (companion/consequences.py). */
export interface Consequence {
  id: string
  label: string
  decided_on: string
  /** `moves` says which way each reason pushed its option (missing on outcomes recorded before v0.13). */
  options: { option: number; label: string; odds: number; reasons: string[]; moves?: ReasonMove[] }[]
  picked: number
  picked_by: 'dice' | 'user'
  /** The choice it answered ("business:how"). */
  choice?: string
  /** Set when it can no longer change (how a stage went that already led to a later one): why, shown as a hint. */
  settled?: string
  /** What it left behind for a while, tilting later odds; a ripple reached a companion close to them. */
  marks: { kind: 'mood' | 'money' | 'avoid'; amount: number; note: string; until: string; ripple: boolean; holder: string; who: string | null }[]
}
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

export interface Occasion { key: string; kind: 'user_birthday' | 'own_birthday' | 'circle_birthday' | 'anniversary' | 'tradition' | 'step_anniversary' | 'death_anniversary'; date: string; days: number; span: string; text: string; template: string | null; person?: string; relation?: string; holiday?: string; tradition?: string; teaser?: string; did?: string; step?: string; turns?: number }

/** A holiday the companion's family keeps (companion/life/traditions.py). */
export interface Tradition { id: string; holiday: string; name: string; text: string; origin: 'seeded' | 'user'; edited: boolean; next: string | null }
export interface TraditionsView { traditions: Tradition[]; removed: Tradition[]; holidays: { id: string; name: string }[]; decorations: string[] }

/** Our year so far (companion/life/scrapbook.py): the stretches there are, and one stretch's pages. */
export interface ScrapbookPeriod { key: string; title: string; start: string; end: string }
export interface ScrapbookListing { periods: ScrapbookPeriod[]; featured: string | null; featured_days: number }
export interface ScrapbookItem { date?: string; text: string }
export type ScrapbookPage =
  | { kind: 'cover'; title: string; subtitle: string; stats: { value: string; label: string }[] }
  | { kind: 'first'; title: string; date: string; said: string; reply: string | null }
  | { kind: 'photos'; title: string; photos: { ref: string; summary: string; date: string | null }[] }
  | { kind: 'jokes'; title: string; items: ScrapbookItem[]; note: string | null }
  | { kind: 'closer' | 'moments' | 'their-year'; title: string; items: ScrapbookItem[] }
  | { kind: 'closing'; title: string; text: string }
  | { kind: 'wedding'; title: string; date: string; text: string; items: ScrapbookItem[]; guests: string[]; more?: number; photo: string | null; photo_alt: string }
export interface Scrapbook extends ScrapbookPeriod { name: string; pages: ScrapbookPage[] }
/** Our history at a glance: one line a week lately, a month, then a year further back (companion/memory/history.py).
 * `corrected` is the user's own words, an empty string when they left the line out, or null for the app's line. */
export interface HistoryLine { key: string; kind: 'week' | 'month' | 'year'; start: string; end: string; label: string; days: number; together?: number; text: string; corrected: string | null }
export interface History { name: string; lines: HistoryLine[] }
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
  /** A place they bought: `rent` is then the mortgage (companion/life/big_turns.py). */
  owned?: boolean
  /** Bought in a medieval kingdom or a fairy-tale land: payments on it, not a mortgage. */
  medieval?: boolean
  currency?: { code: string; symbol: string; name: string }
  /** The rent (or mortgage) as money.py says it, in the city's money: "$1,410", "8 d.", "15s.". */
  rent_text?: string
  out_of_action?: string | null
}

export interface HomeChange { local_date: string; kind: string; text: string }

export type MealKind = 'cook' | 'leftovers' | 'takeout' | 'simple' | 'out' | 'hosting' | 'away'
export type StapleState = 'stocked' | 'low' | 'out'

/** The Character page's Kitchen panel (GET /api/life/kitchen): all in words; `numbers` only with hidden values shown. */
export type HobbyStatus = 'active' | 'stalled' | 'dropped'
export type HobbySource = 'interest' | 'app' | 'user'
export interface Hobby {
  id: string
  label: string
  /** In a sentence: "the cello", "rock climbing". */
  name: string
  kind: string
  source: HobbySource
  status: HobbyStatus
  /** 0 just starting out to 4 really good. */
  level: number
  kept: boolean
  /** "Good at the cello". */
  level_text: string
  /** "About two years in". */
  since_text: string
  /** "Twice a week.", "Stalled lately: work got busy.", "Gave it up in March." */
  status_text: string
  recent: { date: string; kind: 'milestone' | 'stalled' | 'resumed' | 'dropped' | 'started'; text: string }[]
  numbers?: { skill: number; best: number; sessions: number; next_at: number; talent: number }
}
export interface HobbiesView {
  today: string
  hobbies: Hobby[]
  level_names: string[]
  realism: number
  can_add: boolean
}

export interface KitchenView {
  today: string
  diet: string
  avoids: string[]
  skill: number
  skill_text: string
  bakes: boolean
  favorites: string[]
  summary: string
  cuisine: string
  week: { date: string; kind: MealKind; text: string; groceries: boolean; today: boolean }[]
  /** "Grocery run" now, "Food shopping" from the 1880s to the 1920s, "Market day" in medieval towns. */
  run_label: string
  pantry: { name: string; state: StapleState }[]
  pantry_text: string
  changed: string[]
  diets: string[]
  avoid_choices: string[]
  skills: string[]
  realism: number
  numbers?: { rhythm: Record<string, number>; days_left: Record<string, number | null> }
}

export interface HomeView {
  today: string
  items: HomeItem[]
  removed: HomeItem[]
  changes: HomeChange[]
  costs: { rent: number | null; rent_period: string } | null
  varieties: { pet: string[]; vehicle: string[] }
}

export type UpkeepArea = 'laundry' | 'dishes' | 'clutter'
export type UpkeepHabit = 'neat' | 'average' | 'messy'

/** How tidy the companion's place is today (companion/life/upkeep.py), in words, with the numbers behind it. */
export interface UpkeepView {
  on: boolean
  level: number
  today: string
  away: boolean
  habit: UpkeepHabit
  habit_set: boolean
  habit_text: string
  /** 0 spotless to 4 a disaster. */
  tidiness: number
  tidiness_label: string
  levels: string[]
  set_on: string | null
  areas: { area: UpkeepArea; text: string; value: number }[]
  last_big_clean: string | null
  recent: { date: string; kind: string; text: string }[]
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

/** How the companion looks lately (companion/life/grooming.py `view`). */
export interface GroomingView {
  today: string
  /** The user keeps their looks as they are. */
  kept: boolean
  /** Settings > Realism: 0 never, 1 now and then, 2 like real life, 3 often. */
  level: number
  level_name: string
  lines: { label: string; text: string }[]
  /** Looks fields the user wrote, which never change. */
  fixed: string[]
  /** Pictured with a LoRA: gradual changes only. */
  lora: boolean
  changes: { local_date: string; kind: string; text: string; bold: boolean }[]
  /** Hidden values on: the numbers behind the words. */
  numbers: { label: string; value: string }[] | null
}

/** A townsperson the companion has met around the city: only what the companion has learned so far. */
/** A pet and how it is doing, in plain words (companion/life/pets.py `view`). */
export interface PetView {
  key: string
  name: string
  kind: string
  kind_label: string
  looks: string
  born: string
  age: string
  state: 'well' | 'sick' | 'vet' | 'away' | 'died'
  /** Plain words: "Biscuit is under the weather: an upset stomach." Empty when all is well. */
  status: string
  /** A serious illness, the one status shown as a warning. */
  serious?: boolean
  died_on: string | null
  recent: { date: string; kind: 'sick' | 'vet' | 'checkup' | 'died'; text: string }[]
  /** Hidden values (show_home_meters): 0 to 100, and how long their kind usually lives. */
  health: number | null
  lifespan_years: number | null
}
/** A pet of someone in the circle; `number` names it in the user's changes (companion/life/circle_pets.py). */
export interface CirclePetView extends PetView { number: number }
/** The companion's own pets (GET /api/life/pets): a pet id is its home item's. */
export interface CompanionPet extends PetView { id: string; edited?: boolean }
export interface PetsView {
  today: string
  pets: CompanionPet[]
  remembered: CompanionPet[]
  /** The user's own pets, from their persona. */
  yours: PetView[]
  kinds: { id: string; label: string }[]
  numbers: boolean
}

/** How and when a townsperson left their place or town (companion/world/turnover.py). */
export interface TownLeft { why: 'moved' | 'new job' | 'retired' | 'passed'; day: string; text: string }

export interface Townsperson {
  key: string
  name: string
  full: string
  pronouns: string
  age: number
  /** Their kind's name when they aren't human ("Vulcan", "Elf"), else null (companion/world/lifespans.py). */
  folk?: string | null
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
  /** Where their love life stands, once the companion knows them (companion/world/couples.py): "married to Dana Ruiz". */
  love?: string | null
  reached: string[]
  routine: string | null
  flaw: string | null
  desire: string | null
  /** How they come across (companion/world/perception.py): the first impression, fuller from the second meeting. */
  comes_across: string | null
  /** From the third meeting: how they once described themselves. */
  says_they_are: string | null
  /** Their personality sliders (companion/life/town_personality.py); null for a companion living in town. */
  personality?: PersonalityView | null
  /** With the adult side on: who they're drawn to, once the companion knows their heart. */
  orientation?: string | null
  /** With the adult side on and shown in Hidden values: all of it, for the user's eyes only. */
  adult_side?: AdultSide | null
  /** What the companion has picked up about their life (companion/world/life_details.py), a little more each meeting. */
  facts?: string[]
  /** Stories from their past they have told, from the fourth meeting, one per meeting. */
  stories?: string[]
  /** Another of the user's companions, living in town by rules since stepping back: their companion id. */
  cast: string | null
  /** Once the companion would know: they have since moved away, left their place or passed away. */
  left?: TownLeft | null
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
/** Another companion the current one doesn't know yet, as the app would start them (Character > Who they know). */
export interface UntoldTie { companion_id: string; name: string; level: number; how: string }
/** Two companions about to share a group for the first time: their backstory can be told, once. */
export interface UntoldPair { a: string; b: string; a_name: string; b_name: string; level: number; how: string }
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
  /** How many years behind real time this world runs (a world in a past year, companion/world_year.py); 0 now. */
  years_back?: number
  speed: number
  speeds: number[]
  started_at: string | null
  app_started_at: string | null
  backup: string | null
  jumping: { to: string; done: number } | null
  kept?: boolean
}

/** Story mode (companion/story.py): the user's own story with a narrator, apart from the companion. */
export interface StoryPlace {
  id: string; name: string; kind: string; neighborhood: string; summary?: string
  /** Named spots inside, for detail (companion/world/inside.py): "the back patio". */
  spots?: string[]
}
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
  crisis_help?: boolean
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
  /** A long-lived kind's age in human terms (matching reads it); null when it is their age. */
  life_age?: number | null
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
  /** They have since moved away or passed away (companion/world/turnover.py). */
  left?: TownLeft | null
}
/** A townsperson's one portrait (companion/dating_photos.py). */
export interface DatingPhoto { status: 'none' | 'queued' | 'running' | 'completed' | 'failed'; error?: string | null; url?: string | null }
export interface DatingWords { title: string; noun: string; like: string; pass: string; matched: string; missed: string; empty: string; tagline: string; get: string; getting: string; unseen: string; /** A phone app to install: the Download glyph; else UserPlus (Iris). */ app: boolean }
export interface Dating {
  surface: 'app' | 'column' | 'matchmaker'
  words: DatingWords
  city: { id: string; name: string }
  profile: DatingProfile | null
  /** Settings > Debug > 100% Matchlight matches is on. */
  all_matches?: boolean
  /** Just watching (companion/observer.py): Matchlight waits until the user steps back in. */
  watching?: boolean
  /** Who the user is in this world, so a new profile starts filled in. */
  persona?: { name: string; gender: string; age: number | null; about: string } | null
  /** Whether Story mode is on, so a match can be met there. */
  story: boolean
  /** Whether an image backend is set up, so "Show photo" can make one. */
  photos: boolean
  deck: DatingCard[]
  remaining: number
  matches: DatingMatch[]
  date: { key: string; name: string; place_id: string } | null
  /** The person the user just answered, whose answer Undo can take back; null once undone or anything else changed. */
  undo?: string | null
  /** After a like: the person, when they liked the user back. */
  matched?: DatingCard | null
}

/** Group chats (companion/groups.py, docs/group-chat.md). */
export interface GroupMember {
  companion_id: string | null
  /** Their person key: `companion:<id>`, or a guest's circle or townsfolk key. */
  key: string
  /** Their full name now; `label` is how the chat names them (a first name unless two share it). */
  name: string
  label: string
  main: boolean
  joined_at: string
  /** The first message they can see: 1 when added with everything so far. */
  sees_from: number
  /** How they seem right now (companion/moods.py), read-only; only in a chat's own view. */
  mood?: GroupMood | null
  /** Someone from a member's life who joined for a while (companion/group_guests.py); null for companions. */
  guest?: GroupGuest | null
}

export interface GroupGuest {
  /** The companion who knows them. */
  host_id: string | null
  /** "Mira's close friend". */
  relation: string
  /** The user kept them: they stay however quiet the chat gets. */
  kept: boolean
  /** They came back often enough to stay on their own. */
  regular: boolean
  visits: number
  regular_after: number
  replies_left: number
  replies_each: number
}

/** Someone a companion in the group knows who could join it (GET /api/groups/{id}/guests). */
export interface GuestOption {
  key: string
  name: string
  relation: string
  kind: 'circle' | 'town'
  host_id: string | null
}

/** Record model calls (companion/model_calls.py), Settings > Debug. */
export interface ModelCallLog { recording: boolean; folder: string; keep_days: number; files: number; bytes: number }

export interface GroupMood {
  feeling: 'calm' | 'happy' | 'excited' | 'annoyed' | 'hurt' | 'angry' | 'anxious' | 'sad'
  intensity: number
  /** "Seems angry at Sally". */
  text: string
  reason: string | null
  /** Who they aren't speaking to right now, by the chat's name for them. */
  ignoring: string | null
}

export interface GroupMessage {
  id: string
  seq: number
  /** The user, a companion, a guest, or the app's own line about who joined or left. */
  kind: 'user' | 'companion' | 'guest' | 'app'
  companion_id: string | null
  name: string
  text: string
  status: 'complete' | 'streaming' | 'failed' | 'cancelled'
  error: string | null
  reply_to: string | null
  /** What the secret check did to this reply (companion/secrets.py): rewritten once, let a secret slip, or held back. */
  guard?: 'redrafted' | 'revealed' | 'held' | null
  created_at: string
  /** Kept as a shared moment: it brings everyone who was there a little closer. */
  kept?: boolean
  /** Your message sounds like self-harm: the app's note with places to get help shows under it. */
  crisis_help?: boolean
}

export interface Group {
  id: string
  name: string
  /** The name, or who is in it when it has none. */
  title: string
  reply_cap: number
  /** Someone furious may walk out (off by default). */
  walk_out?: boolean
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

/** Secrets in group chats (companion/secrets.py): who knows what, and who must not find out. */
export type SecretVia = 'origin' | 'witness' | 'slip' | 'history' | 'reveal'

export interface SecretHolder {
  key: string
  companion_id: string | null
  name: string
  via: SecretVia
  /** How they came to know it, in words ("heard it from Billy in a group"). */
  how: string
  /** Who told them, as they'd say it ("Billy", "the user"), or null. */
  told_by?: string | null
  learned_at: string
  /** The group they learned it in, when they did. */
  group: { id: string; name: string } | null
}

export interface Secret {
  id: string
  /** The user's own, or registered from a companion's storyline or description. */
  kind: 'declared' | 'storyline' | 'character' | 'memory'
  statement: string
  /** "You added this", "From Billy's storyline". */
  source: string
  about: string[]
  /** The words the reply check looks for; `own_key_words` are the ones the user set. */
  key_words: string[]
  own_key_words: string[]
  keep_from_everyone: boolean
  knows: SecretHolder[]
  kept_from: { key: string; companion_id: string | null; name: string }[]
  created_at: string
}

export interface SecretsData {
  secrets: Secret[]
  companions: { id: string; name: string }[]
  /** Drama is at soap opera: a slip that gets past the rewrite stays. */
  slips: boolean
}

/** The town paper for the companion's city (companion/world/paper.py): one Sunday's issue, written from what
 * happened in the world. `next` is null on this week's issue. */
export interface TownPaper {
  title: string
  city: string
  date: string
  news: { id: string; headline: string; text: string }[]
  townsfolk: { key: string; headline: string; text: string }[]
  /** Townsfolk engagements and weddings that week (companion/world/couples.py). */
  couples: { key: string; headline: string; text: string }[]
  seen: { companion_id: string; text: string }[]
  gossip: { text: string }[]
  /** Local issues that moved that week (companion/life/politics.py paper_items). */
  politics?: { key: string; headline: string; text: string; date: string }[]
  ahead: {
    events: { date: string; name: string; text: string }[]
    holidays: { date: string; name: string }[]
    weather: string | null
  }
  previous: string
  next: string | null
}

/** Local politics (companion/life/politics.py): what people in the companion's city argue about, the factions behind
 * each side and where the companion and their people stand. Views run from 2 (strongly for the first side) to -2
 * (strongly for the second); `by` says whether the app or the user set it. */
export type PoliticsStage = 'whispers' | 'open' | 'heated' | 'settled' | 'ended'
export interface PoliticsSide { name: string; stand: string }
export interface PoliticsBeat { on: string; text: string; stage?: string; favors?: number }
export interface PoliticsView { view: number; by: 'world' | 'you' }
export interface PoliticsIssue {
  id: string
  kind: 'era' | 'local'
  title: string
  question: string
  sides: PoliticsSide[]
  stage: PoliticsStage
  beats: PoliticsBeat[]
  /** How many of the townsfolk who stand for the town are on each side, or don't much care. */
  split: { first: number; second: number; neither: number }
  /** How a local issue went, with the odds of each way (shown only with Hidden values > odds). */
  settled: { options: { option: number; label: string; odds: number; reasons: string[]; moves?: ReasonMove[] }[]; picked: number; picked_by: 'dice' | 'user' } | null
  settled_on: string | null
  /** A real question of the city's year (Prohibition in 1925): it never settles against history. */
  real: boolean
  /** 'news' for an issue made from real local headlines (companion/life/politics_news.py). */
  origin: 'seeded' | 'user' | 'news'
  started: string | null
  /** 'you' when the user set how far a local issue has got. */
  stage_by: 'you' | null
  /** The side each faction takes: 0 or 1, null when it stays out. */
  lines: Record<string, number | null>
  edited: boolean
}
export interface PoliticsFaction {
  id: string
  name: string
  kind: string
  about: string
  /** 1 to 5; `change` is how far recent wins or losses moved it from `base_pull`. */
  pull: number
  base_pull: number
  change: number
  origin: 'city' | 'era' | 'user'
  /** The companion and people they know who belong. */
  members: string[]
  /** The sides the user told it to take, by issue. */
  sides: Record<string, number>
}
export interface PoliticsRelation { a: string; b: string; stance: number; by: 'world' | 'you' }
export interface PoliticsPerson { key: string; name: string; role: string; kind: string; factions: string[]; views: Record<string, PoliticsView> }
export interface TownPolitics {
  level: number
  city: { id: string | null; name: string | null }
  issues: PoliticsIssue[]
  factions: PoliticsFaction[]
  relations: PoliticsRelation[]
  companion: { key: string; name: string; factions: string[]; views: Record<string, PoliticsView> } | null
  people: PoliticsPerson[]
}

/** Worlds and personas (companion/worlds.py): the user as someone in particular, and the worlds they live in. */
export interface WorldHome { city_id: string; city: string; region: string; neighbourhood: string; neighbourhood_name: string; set_by: 'app' | 'you' }
/** The persona form's "Where you live": the cities the persona can live in from this world, and one city's neighbourhoods. */
export interface HomeChoices { home: WorldHome | null; cities: CitySummary[]; city_id: string; neighbourhoods: { id: string; name: string }[] }
export interface World {
  id: string; name: string; persona_id: string; folder: string; city_id: string; created_at: string; used_at: string
  active: boolean
  /** The first world holds the others, so it cannot be deleted. */
  first: boolean
  /** Its companions' names, main character first. */
  companions: string[]
  /** Whether the user is just watching it (Observer mode, companion/observer.py). */
  watching?: boolean
  /** The year it is there when the world runs in a past year (companion/world_year.py); null in the present. */
  year?: number | null
  /** A Back when world (companion/back_when.py): the year it was made for and the companion it went back with. */
  back_when?: { year: number; name: string; companion_id: string } | null
  /** Where the persona lives in this world (companion/life/where.py); the app picks it until the user changes it. */
  home: WorldHome | null
  /** Life stands still there (companion/worlds.py `paused`): every world but the one the user is in, and one paused in
   * Settings > Pause. `paused_since` is when they left it or paused it, null when it can't be told. */
  paused?: boolean
  paused_since?: string | null
  paused_in_settings?: boolean
  /** Going back fills in a few events from the time away (Settings > Life, catch up on return). */
  catches_up?: boolean
}
/** One moment the Back when sheet offers (companion/back_when.py `moments`): "When you first met", 2019. `age` is the
 * companion's age then, null when it can't be told. */
export interface BackWhenMoment { key: string; label: string; year: number; name: string; age: number | null }
/** The Back when sheet: the app's three moments, the years the user can pick instead, and why none, when none. */
export interface BackWhenMoments {
  companion_id: string; name: string; moments: BackWhenMoment[]
  earliest: number; latest: number; available: boolean; from_history: boolean; reason: string | null
}
export type PersonaGender = 'woman' | 'man' | 'nonbinary' | ''
/** One of the user's own pets on their persona: their words, given a life by companion/life/pets.py. */
export interface PersonaPet { name: string; kind: string; looks: string; born?: string; added?: string; age?: number | null }
export interface Persona {
  id: string; name: string; gender: PersonaGender; age: number | null; about: string; birthday: string; created_at: string
  pets?: PersonaPet[]
  /** Kind and How long they live as picked on the Persona page ('' and null: read from About you). */
  kind?: string; lifespan?: number | null
  /** What applies, the app's pick from their words, and what the pickers offer (companion/worlds.py `kind_shown`). */
  kind_shown?: KindShown & KindChoices & { found: string; found_label: string; picked: string }
  active: boolean
  worlds: World[]
}
export interface Worlds {
  active_world_id: string; active_persona_id: string; world: World; persona: Persona; personas: Persona[]
}

/** While you were away (companion/recap.py): a catch-up after a few days without a message. */
export interface AwayRecap { since: string; days: number; items: string[] }

/** Settings > Debug > Townsfolk mix (companion/world/mix.py): the shares the townsfolk rolls use. */
export interface MixValues {
  nonbinary: number; women: number; height_woman: number; height_man: number
  slender: number; middle: number; heavier: number; beard: number
  gay: number; bisexual: number; bolder: number; drive: number
}
export interface MixTown {
  city: string; people: number
  genders: Record<'woman' | 'man' | 'nonbinary', number>
  heights: Record<'woman' | 'man' | 'nonbinary', number | null>
  builds: Record<'slender' | 'middle' | 'heavier', number>
  beard: number; gay: number; bisexual: number
  levels: Record<string, number>; drives: Record<string, number>
}
export interface TownsfolkMix {
  mix: MixValues; defaults: MixValues; limits: Record<keyof MixValues, [number, number, number]>
  bands: { ages: string; gay: number; bisexual_women: number; bisexual_men: number }[]
  levels: Record<string, Record<string, number>>; drives: Record<string, Record<string, number>>
  adult_side: boolean; town: MixTown | null
}

/** One appointment, errand or chore on a companion's calendar (companion/life/admin.py). */
export interface AdminItem {
  id: string
  key: string
  source: 'admin' | 'pets' | 'upkeep' | 'kitchen' | 'looks' | 'work' | 'family'
  kind: string
  title: string
  /** What just happened, for a surprise ("A parking ticket was tucked under the wiper"). */
  line: string
  local_date: string
  at_time: string
  until: string
  fixed: boolean
  status: 'planned' | 'done' | 'removed' | 'skipped'
  place: string
  moved_from: string | null
  /** "moved for a plan", "put off", "moved by you", "moved for a trip", or empty. */
  moved_reason: string
  moves: number
  deadline: string | null
  cost_text: string
  /** False for another feature's item shown read-only (Looks' haircuts follow their own draw). */
  movable: boolean
  /** A late night's project, shown under its title (companion/life/work.py); empty otherwise. */
  detail?: string
  /** The last day of a stay that runs several days (companion/life/stays.py). */
  end_date?: string
  /** A stay with the other parent (companion/life/stays.py): moved or skipped by the user while still to come, and a
   * skip taken back. */
  stay?: StayActions
}

export interface StayActions {
  id: string
  status: 'planned' | 'skipped'
  can_change: boolean
  undo: boolean
  /** The make-up's first day, on a skipped stay (shown under it, Iris). */
  made_up?: string | null
}

export interface AdminLater { kind: string; title: string; local_date: string; due: boolean }

/** A guest on the wedding list: `side` is 'theirs' (their family and friends) or 'yours' (people you told them about,
 * your other companions). `who` is how they know the couple ("Mira's mom", "your sister"). */
export interface WeddingGuest { key: string; name: string; who: string; side: 'theirs' | 'yours'; invited: boolean }
/** The wedding an engagement plans (companion/life/wedding.py): picked by the app, changed by the user. */
export interface WeddingPlan {
  id: string; status: 'planned' | 'done'; engaged_on: string; date: string; at: string; until: string
  size: 'small' | 'proper' | 'big'; size_label: string; sizes: { key: string; label: string }[]
  venue: { id: string; name: string; kind: string; neighborhood: string; mapped: boolean }
  budget_text: string; share_text: string; guest_count: number; guests: WeddingGuest[]; moved_by_user: boolean
  customs: string; tasks: { title: string; date: string; done: boolean; done_text?: string }[]; consequence_id: string | null
}

/** The Character page's Life admin panel (/api/life/admin). */
export interface AdminView {
  state: string[]
  habit: 'organised' | 'average' | 'scattered'
  upcoming: AdminItem[]
  later: AdminLater[]
  done: AdminItem[]
  level: number
  /** 0 to 100, only with Hidden values' home-life meters on. */
  meter: number | null
  /** The wedding being planned (companion/life/wedding.py), null when there is none. */
  wedding: WeddingPlan | null
}

/** Something that changed at work (companion/life/work.py): a raise, a promotion, a project wrapped up, a new job. */
export interface WorkEvent {
  id: string
  kind: 'raise' | 'freeze' | 'promotion' | 'project' | 'laid-off' | 'quit' | 'new-job'
  local_date: string
  /** "the yearly raise, about 3.2%", "wrapped up the spring menu change; it went well". */
  text: string
}

/** The Character page's Work life panel (GET /api/life/work). */
export interface WorkLifeView {
  state: string[]
  workload: 'slammed' | 'normal' | 'slow' | null
  status: 'working' | 'hunting'
  project: { title: string; index: number; started: string; due: string }
  started_on: string
  tenure: string
  employer: string
  late_nights: AdminItem[]
  /** Vacation days still to come this year. */
  vacation: string[]
  events: WorkEvent[]
  level: number
  /** Only with Hidden values' home-life meters on. */
  meter: { vacation_total: number; vacation_used: number; allowance: number; pay_percent: number; level: number } | null
  /** Same days every week, shifts that change weekly, or freelance gigs (companion/life/shifts.py). */
  hours: 'staff' | 'rota' | 'freelance'
  /** A student (companion/life/work.py STUDY), and what they study. */
  studying?: boolean
  field?: string
  /** What they are working on is the user's own words, and its due date the user's own. */
  own_project?: boolean
  own_due?: boolean
  /** Their local today, the earliest a due date can move to. */
  today?: string
}

/** Reading, watching and listening (companion/life/media.py): what they are on now and what ended lately. */
export interface MediaNow {
  id: string; kind: 'book' | 'show' | 'music'; title: string; by: string; format: string; text: string
  set_by_you: boolean; started_on: string
  /** Something the user recommended, ahead of their own pick (`waiting`, the title it holds up). */
  recommended?: boolean; waiting?: string | null
}
export interface MediaView {
  off: boolean; today: string; realism: number; real: boolean
  /** The bank their titles come from (companion/world/data/media), for era-fitting examples. */
  bank?: string
  now: MediaNow[]
  lately: { id: string; kind: 'book' | 'show' | 'music'; title: string; ended_on: string; text: string }[]
  /** Hidden values (show_home_meters). */
  numbers?: { reader: number; watcher: number; library: boolean; drop: number; recommend: number
    items: Record<string, { along: number; days_left: number; ends: 'finish' | 'put down' }> }
}

/** Someone the Watching page can follow (companion/life/narrator.py): a companion or a townsperson. */
export interface WatchFocus {
  key: string
  /** A companion, someone in a companion's circle who lives in town, or someone from around town. */
  kind: 'companion' | 'circle' | 'townsperson'
  name: string
  /** Who they are in a few words: "Your companion · nurse", "Sett's mom · nurse", "Line cook at Blue Moon Cafe". */
  line: string
  /** Why the picker offers them, for someone the user may not know: "Sett has run into them around town twice." */
  why?: string
  /** How a townsperson came to be offered: the main companion met them, or the app picked them for a busy week. */
  source?: 'met' | 'busy'
  /** The companion whose circle they are in, or who met them, by first name. */
  owner?: string
  companion_id?: string
  town_key?: string
}
/** Observer mode (companion/observer.py): whether the user is just watching, who the page follows and who else it could. */
export interface Observer { watching: boolean; started_at: string | null; focus: WatchFocus | null; choices: WatchFocus[] }
export type WatchKind = 'day' | 'moment' | 'dream' | 'thought' | 'story' | 'chapter' | 'news' | 'mood' | 'met' | 'family' | 'loss' | 'love' | 'private'
/** One line of a watched day: what happened, with a thought after it and, under Hidden values, its numbers. */
export interface WatchLine { id: string; at: string; kind: WatchKind; text: string; inner: string | null; numbers: string[] }
export interface WatchDay { date: string; entry: string | null; items: WatchLine[] }
export interface WatchFeed { focus: WatchFocus; voice: number; timezone: string; shown: { moods: boolean; odds: boolean }; days: WatchDay[] }

/** Settings > General > Updates (companion/updates.py). */
export interface UpdateCheck {
  status: 'newer' | 'current' | 'unavailable'
  current: string; latest: string | null; title: string | null; published: string | null
  /** The release's page on GitHub, or the latest-release page when the check failed. */
  page: string
  install: 'installer' | 'folder'; system: 'windows' | 'mac' | 'other'
}
