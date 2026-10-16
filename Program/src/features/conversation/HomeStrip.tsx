import { DoorOpen, Home } from 'lucide-react'
import { api } from '../../api'
import { homeLine, type WhereState } from './whereText'

/**
 * The chat strip while you live together (companion/life/moving_in.py), kept apart from the rest of the strip: home
 * together of an evening, with Heading out (the chat texts for a few hours), or out, with I'm home.
 */
export function HomeStrip({ where, name, onDone }: { where: WhereState; name: string; onDone: (found?: WhereState) => void }) {
  const line = homeLine(where, name)
  if (!line) return null
  const act = async () => onDone(await api<WhereState>(`/life/living/${line.action}`, {}).catch(() => undefined))
  const Glyph = line.action === 'out' ? DoorOpen : Home
  return (
    <aside className="where-strip" aria-label="Where you are" aria-live="polite">
      <Home aria-hidden="true" />
      <span>{line.lead}</span>
      <button type="button" className="text-button" onClick={() => void act()}><Glyph aria-hidden="true" />{line.label}</button>
    </aside>
  )
}
