import { profileTab } from '../profile/profileText.ts'

/** Every view with a side rail button (AppNav.tsx). */
export const RAIL_IDS = new Set(['conversation', 'groups', 'dating', 'story', 'today', 'memories', 'settings', 'watch'])

/**
 * The phone's tab bar (Iris's spec, companion-design/phone-tab-bar.md): Chats, Today, Story, Matchlight and
 * Settings, the most Apple and Google put in a bottom bar. Chats holds what were the Profile, Groups, Memories
 * and Worlds tabs, so every view below belongs under it.
 */
export function inChats(view: string): boolean {
  return view === 'chats' || view === 'groups' || view.startsWith('group/') || view === 'worlds' || underProfile(view)
}

/** A profile tab, or Create another companion, opened from the Character page outside the tabs. */
function underProfile(view: string): boolean {
  return profileTab(view) !== null || view === 'another'
}

/**
 * Where the Chats tab goes, the iOS way: from another tab, back to where the user was under Chats; tapped
 * again while a chat is open, to the list.
 */
export function chatsTarget(view: string, last: string): string {
  return inChats(view) ? 'chats' : last
}

/** The map and Who knows who open from Today, so its tab stays lit on them. */
export function fromToday(view: string): boolean {
  return view === 'people' || view === 'map' || view.startsWith('map/')
}

/** Whether a side rail button is lit. The phone's Chats tab uses inChats instead. */
export function railCurrent(id: string, view: string): boolean {
  if (id === 'conversation') return view === 'chats' || (underProfile(view) && view !== 'memories')
  if (id === 'today') return view === 'today' || fromToday(view)
  if (id === 'settings') return view === 'settings' || view.startsWith('settings/')
  if (id === 'groups') return view === 'groups' || view.startsWith('group/')
  return view === id
}
