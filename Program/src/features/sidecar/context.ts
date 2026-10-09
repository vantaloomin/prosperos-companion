import type { View } from '../../companion'

const PLACES: Partial<Record<string, string>> = {
  conversation: "{name}'s chat", character: "{name}'s character", memories: "{name}'s memories", today: "{name}'s day",
  feed: 'the feed', appearance: "{name}'s look", portraits: "{name}'s pictures", groups: 'group chats', dating: 'Matchlight',
  story: 'the story', settings: 'Settings', worlds: 'Worlds',
}

/** "Looking at: Maya's chat", for the sidecar's own window, which follows what the main window shows. */
export function lookingAt(view: View, name: string): string {
  const place = PLACES[view.split('/')[0]] ?? 'the app'
  return `Looking at: ${place.replace('{name}', name)}`
}
