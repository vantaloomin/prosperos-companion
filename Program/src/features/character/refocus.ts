import type { QueryClient } from '@tanstack/react-query'
import { PHONE_STATUS_KEY } from '../phone/phoneAccess'

// Not reset: whether this device may open the app (resetting it unmounts the whole app while it is
// asked again, so the view falls back to the old address), a switch page's own draft, and the chat list (it
// covers every companion, so it stays on screen while the switch happens).
const KEPT = new Set([PHONE_STATUS_KEY[0], 'cast-draft', 'chats'])

/** After the main character changes or starts over, every view reloads for the one now in focus. */
export async function refocus(client: QueryClient) {
  await client.resetQueries({ predicate: (query) => !KEPT.has(String(query.queryKey[0])) })
  await client.invalidateQueries({ queryKey: ['chats'] })
}
