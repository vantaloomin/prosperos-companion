import type { ChatStyle } from '../../types'
import type { StatusWhere } from '../status/statusText'
import { MODERN_WORDS, type EraWords } from '../world/eraWords.ts'

/** The companion's profile holds three views, opened from their name in the chat (v1.3). The chat itself is not one of
 * them any more; the address keeps the older names so every link still works. */
export type ProfileTab = 'feed' | 'memories' | 'character'

/** The three tabs, Posts in the era's words ("Chronicle" in Camelot). */
export function profileTabs(words: EraWords = MODERN_WORDS): { id: ProfileTab; label: string }[] {
  return [
    { id: 'feed', label: words.posts_tab },
    { id: 'memories', label: 'Memories' },
    { id: 'character', label: 'Character' },
  ]
}

/** Which profile tab a view sits under, or null when the view is not part of the profile. */
export function profileTab(view: string): ProfileTab | null {
  if (view === 'feed' || view === 'memories' || view === 'character') return view
  if (view === 'appearance' || view === 'portraits' || view.startsWith('cast/')) return 'character'
  if (view === 'year') return 'memories'
  return null
}

/** The profile header shows above each of the three tabs; the pages under them (pictures, Our year) keep only the tabs. */
export function showsCard(view: string): boolean {
  return view === 'feed' || view === 'memories' || view === 'character'
}

/** A screen name made from their name, the way a social app would show it. */
/** Whether a profile shows an @handle: not before the 2000s, when nobody had one (Iris, 2026-10-29). */
export function showsHandle(decade: string | null | undefined): boolean {
  return !decade || decade >= '2000s'
}

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

/** Where they live on the card: "Long distance, Lisbon, 5 hours ahead" when they live in another city than yours
 * (companion/life/together.py state), else the place their definition names. */
export function placeFact(place: string, where: StatusWhere | null | undefined): string {
  return where?.kind === 'long-distance' && where.text ? where.text : place
}
