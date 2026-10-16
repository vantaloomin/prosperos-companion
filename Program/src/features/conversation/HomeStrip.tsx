import { DoorOpen, Home, MapPin } from 'lucide-react'
import { api } from '../../api'
import { homeLine, type WhereState } from './whereText'

/**
 * The chat strip while you live together (companion/life/moving_in.py), kept apart from the rest of the strip: home
 * together of an evening, with Heading out (the chat texts for a few hours), or out, with I'm home. Out is the
 * everyday texting state, so it is the quiet one: no tint, and the pin for apart instead of the house.
 */
export function HomeStrip({ where, name, onDone }: { where: WhereState; name: string; onDone: (found?: WhereState) => void }) {
  const line = homeLine(where, name)
  if (!line) return null
  const act = async () => onDone(await api<WhereState>(`/life/living/${line.action}`, {}).catch(() => undefined))
  const out = line.action === 'home'
  const Glyph = out ? Home : DoorOpen
  const Lead = out ? MapPin : Home
  return (
    <aside className={out ? 'where-strip quiet' : 'where-strip'} aria-label="Where you are" aria-live="polite">
      <Lead aria-hidden="true" />
      <span>{line.lead}</span>
      <button type="button" className="text-button" onClick={() => void act()}><Glyph aria-hidden="true" />{line.label}</button>
    </aside>
  )
}
