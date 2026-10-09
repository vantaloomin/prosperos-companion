/** Settings is split into tabs; this lists them, what each holds, and the words a search finds them by. */

export type SettingsTab = 'general' | 'models' | 'life' | 'memory' | 'lookups' | 'images' | 'notifications' | 'phone' | 'data' | 'debug' | 'advanced'

export interface SettingsSection {
  /** The id of the section's heading, used to land on it from a search result. */
  heading: string
  title: string
  keywords: string
}

export interface SettingsTabInfo {
  id: SettingsTab
  label: string
  /** Shown before a companion exists. Everything else needs a workspace to change. */
  withoutCompanion?: boolean
  /** Hidden on a paired phone: the Companion only allows it from the PC (companion/phone/access.py). */
  pcOnly?: boolean
  /** Listed only while "Show advanced settings" is on. */
  advanced?: boolean
  sections: SettingsSection[]
}

export const SETTINGS_TABS: SettingsTabInfo[] = [
  {
    id: 'general', label: 'General', sections: [
      { heading: 'time-heading', title: 'Your time', keywords: 'timezone time zone clock date quiet hours pc' },
      { heading: 'appearance-heading', title: 'Appearance', keywords: 'appearance chat style look feed bubbles texting community avatars retro im messenger visual novel portrait sounds' },
      { heading: 'activity-heading', title: 'Pause', keywords: 'pause resume stop freeze' },
      { heading: 'background-heading', title: 'Background activity', keywords: 'background running open simulation' },
    ],
  },
  {
    id: 'models', label: 'Models', withoutCompanion: true, sections: [
      { heading: 'hardware-heading', title: 'This computer', keywords: 'hardware graphics card gpu vram memory ram nvidia fit warning slow local' },
      { heading: 'models-heading', title: 'Models', keywords: 'model connection provider api key openai anthropic openrouter google local kobold codex profile chat life memory drafting recall temperature' },
      { heading: 'recall-profiles-heading', title: 'Recall', keywords: 'recall embedding embeddings semantic memory search ollama lm studio openai nomic qwen gemma profile' },
      { heading: 'recall-heading', title: 'Built-in recall', keywords: 'recall embedding embeddings semantic llama.cpp llama-server gguf gemma embeddinggemma qwen local memory search' },
      { heading: 'voice-heading', title: 'Voice notes', keywords: 'voice voices voice notes audio speech tts text to speech kokoro sherpa openai elevenlabs google accent preview' },
    ],
  },
  {
    id: 'life', label: 'Life & cities', sections: [
      { heading: 'life-heading', title: 'Life', keywords: 'life events pace themes days routine' },
      { heading: 'cities-heading', title: 'Cities', keywords: 'city cities places home world pack' },
    ],
  },
  {
    id: 'memory', label: 'Memory', sections: [
      { heading: 'memory-heading', title: 'Memory', keywords: 'memory remember automatic sensitive suggestions timelines privacy' },
    ],
  },
  {
    id: 'lookups', label: 'Real-world lookups', sections: [
      { heading: 'context-heading', title: 'Real-world lookups', keywords: 'weather search web links urls mcp tools news current' },
    ],
  },
  {
    id: 'images', label: 'Images', sections: [
      { heading: 'images-heading', title: 'Images', keywords: 'image pictures photos comfyui krea codex nsfw backend' },
    ],
  },
  {
    id: 'notifications', label: 'Notifications', sections: [
      { heading: 'notifications-heading', title: 'Notifications', keywords: 'notifications alerts desktop quiet hours' },
    ],
  },
  {
    id: 'phone', label: 'Phone access', sections: [
      { heading: 'phone-heading', title: 'Phone access', keywords: 'phone mobile tailscale network remote away pair qr code device home screen install wifi wi-fi lan local network' },
    ],
  },
  {
    id: 'data', label: 'Backups', pcOnly: true, sections: [
      { heading: 'backup-heading', title: 'Backups', keywords: 'backup restore data export archive' },
    ],
  },
  {
    id: 'debug', label: 'Debug', pcOnly: true, sections: [
      { heading: 'debug-heading', title: 'Debug time', keywords: 'debug test testing time travel jump skip ahead days fast forward speed accelerate spoof date clock' },
    ],
  },
  {
    id: 'advanced', label: 'Advanced', withoutCompanion: true, advanced: true, sections: [
      { heading: 'story-mode-heading', title: 'Story mode', keywords: 'story mode narrator roleplay role play travel townsfolk meet people dating experimental' },
      { heading: 'prompts-heading', title: 'Prompts', keywords: 'advanced prompt prompts system instructions wording chat character in character first texts check-ins life phrasing memory suggestions pictures describe drafting help me write quick start power user' },
    ],
  },
]

export function availableTabs(hasCompanion: boolean, onPhone = false, advanced = false): SettingsTabInfo[] {
  return SETTINGS_TABS.filter((tab) => (hasCompanion || tab.withoutCompanion) && !(onPhone && tab.pcOnly) && (advanced || !tab.advanced))
}

/** The tab to show for a deep link: the one asked for when it is available, else the first one. */
export function pickTab(requested: string | undefined, hasCompanion: boolean, onPhone = false, advanced = false): SettingsTab {
  const tabs = availableTabs(hasCompanion, onPhone, advanced)
  return (tabs.find((tab) => tab.id === requested) ?? tabs[0]).id
}

export interface SettingsMatch { tab: SettingsTabInfo; section: SettingsSection }

/**
 * Sections whose title, tab or keywords contain every word of the query. Advanced sections are found
 * even while hidden; picking one turns "Show advanced settings" on.
 */
export function searchSettings(query: string, hasCompanion: boolean, onPhone = false): SettingsMatch[] {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean)
  if (!words.length) return []
  return availableTabs(hasCompanion, onPhone, true).flatMap((tab) => tab.sections
    .filter((section) => {
      const text = `${section.title} ${tab.label} ${section.keywords}`.toLowerCase()
      return words.every((word) => text.includes(word))
    })
    .map((section) => ({ tab, section })))
}
