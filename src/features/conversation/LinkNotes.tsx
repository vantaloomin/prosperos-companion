import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { Message, Observation } from '../../types'
import { hasLink, linkNotes } from './linkState'

/** Out-of-character notes on the links in a message: whether the app could open each one, and why not. */
export function LinkNotes({ message, settled }: { message: Message; settled: string }) {
  const enabled = !message.redacted && hasLink(message.text)
  const found = useQuery({
    queryKey: ['message-links', message.id, settled],
    queryFn: () => api<{ observations: Observation[] }>(`/context/messages/${message.id}/observations`),
    enabled,
  })
  const notes = linkNotes(found.data?.observations ?? [])
  if (!enabled || notes.length === 0) return null
  return (
    <ul className="link-notes" aria-label="Links">
      {notes.map((note) => (
        <li key={note.id} className={note.read ? 'link-note' : 'link-note failed'}>
          {note.read ? `Opened ${note.host}` : `Couldn't load ${note.host}: ${note.reason}`}
        </li>
      ))}
    </ul>
  )
}
