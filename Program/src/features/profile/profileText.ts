import type { ChatStyle } from '../../types'

/** The companion's profile holds three views; the address keeps the older names so every link still works. */
export type ProfileTab = 'conversation' | 'feed' | 'character'

export const PROFILE_TABS: { id: ProfileTab; label: string }[] = [
  { id: 'conversation', label: 'Messages' },
  { id: 'feed', label: 'Posts' },
  { id: 'character', label: 'Character' },
]

/** Which profile tab a view sits under, or null when the view is not part of the profile. */
export function profileTab(view: string): ProfileTab | null {
  if (view === 'conversation' || view === 'feed' || view === 'character') return view
  if (view === 'appearance' || view === 'portraits' || view.startsWith('cast/')) return 'character'
  return null
}

/** The full profile card shows above Posts and Character; Messages and the pages under Character keep only the tabs. */
export function showsCard(view: string): boolean {
  return view === 'feed' || view === 'character'
}

/** A screen name made from their name, the way a social app would show it. */
export function handle(name: string): string {
  const base = name.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '.').replace(/^\.+|\.+$/g, '')
  return base ? `@${base}` : ''
}

/** The profile follows the chat style, and Retro IM's dark window when that is on. */
export function profileClass(style: ChatStyle, retroDark: boolean): string {
  return `profile profile-${style}${style === 'retro' && retroDark ? ' retro-dark' : ''}`
}

export function circleText(count: number): string {
  return `${count} ${count === 1 ? 'person' : 'people'} in their circle`
}
