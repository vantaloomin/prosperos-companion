import type { ChatStyle, WorkspaceSettings } from '../../types'

/** Presentation only: each style lays out the same messages, with the same actions. */
export const CHAT_STYLES: { id: ChatStyle; label: string; description: string }[] = [
  { id: 'feed', label: 'Feed', description: 'A calm reading column with names above each message.' },
  { id: 'bubbles', label: 'Bubbles', description: 'Texting-style bubbles: yours on the right, theirs on the left.' },
  { id: 'community', label: 'Community', description: 'A chat-server look with avatars, names and times on every message.' },
  { id: 'retro', label: 'Retro IM', description: 'An early-2000s instant messenger window with screen names in color.' },
  { id: 'novel', label: 'Visual novel', description: 'Their portrait on stage above, with the conversation in dialogue boxes beneath.' },
]

export function chatStyleOf(settings: Pick<WorkspaceSettings, 'chat_style'> | undefined): ChatStyle {
  const chosen = settings?.chat_style
  return CHAT_STYLES.some((style) => style.id === chosen) ? chosen! : 'feed'
}

/** Sounds only ever play in Retro IM, and only once the user turns them on. */
export function soundsOn(settings: Pick<WorkspaceSettings, 'chat_style' | 'chat_sounds'> | undefined) {
  return chatStyleOf(settings) === 'retro' && !!settings?.chat_sounds
}

/** Retro IM's dark window, off until the user turns it on; the other styles already follow the app's dark theme. */
export function retroDarkOn(settings: Pick<WorkspaceSettings, 'chat_style' | 'chat_retro_dark'> | undefined) {
  return chatStyleOf(settings) === 'retro' && !!settings?.chat_retro_dark
}
