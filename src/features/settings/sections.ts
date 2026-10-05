/** Settings is split into tabs; this lists them, what each holds, and the words a search finds them by. */

export type SettingsTab = 'general' | 'models' | 'life' | 'memory' | 'lookups' | 'images' | 'notifications' | 'data'

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
  sections: SettingsSection[]
}

export const SETTINGS_TABS: SettingsTabInfo[] = [
  {
    id: 'general', label: 'General', sections: [
      { heading: 'time-heading', title: 'Your time', keywords: 'timezone time zone clock date quiet hours pc' },
      { heading: 'activity-heading', title: 'Pause', keywords: 'pause resume stop freeze' },
      { heading: 'background-heading', title: 'Background activity', keywords: 'background running open simulation' },
    ],
  },
  {
    id: 'models', label: 'Models', withoutCompanion: true, sections: [
      { heading: 'models-heading', title: 'Models', keywords: 'model connection provider api key openai anthropic openrouter google local kobold codex profile chat life memory drafting recall temperature' },
      { heading: 'prompts-heading', title: 'Character drafting prompts', keywords: 'prompt drafting help me write quick start' },
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
    id: 'data', label: 'Backups', sections: [
      { heading: 'backup-heading', title: 'Backups', keywords: 'backup restore data export archive' },
    ],
  },
]

export function availableTabs(hasCompanion: boolean): SettingsTabInfo[] {
  return hasCompanion ? SETTINGS_TABS : SETTINGS_TABS.filter((tab) => tab.withoutCompanion)
}

/** The tab to show for a deep link: the one asked for when it is available, else the first one. */
export function pickTab(requested: string | undefined, hasCompanion: boolean): SettingsTab {
  const tabs = availableTabs(hasCompanion)
  return (tabs.find((tab) => tab.id === requested) ?? tabs[0]).id
}

export interface SettingsMatch { tab: SettingsTabInfo; section: SettingsSection }

/** Sections whose title, tab or keywords contain every word of the query. */
export function searchSettings(query: string, hasCompanion: boolean): SettingsMatch[] {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean)
  if (!words.length) return []
  return availableTabs(hasCompanion).flatMap((tab) => tab.sections
    .filter((section) => {
      const text = `${section.title} ${tab.label} ${section.keywords}`.toLowerCase()
      return words.every((word) => text.includes(word))
    })
    .map((section) => ({ tab, section })))
}
