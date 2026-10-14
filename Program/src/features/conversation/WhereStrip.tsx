import { useQueryClient } from '@tanstack/react-query'
import { DoorOpen, Home, MapPin, Undo2 } from 'lucide-react'
import { api } from '../../api'
import { TOGETHER_KEY } from '../today/outingText'
import { useWhere } from './useWhere'
import { WHERE_KEY, stripAction, stripLine, type StripAction } from './whereText'

const ACTION_GLYPHS = { 'Head home': Home, Undo: Undo2 } as Record<string, typeof Home>

/**
 * The "where you are" strip above the composer, in every chat style: while they are together (out somewhere, at
 * their place, at yours) where and until when, with Head home, Say goodbye or Not now, and Undo for a minute or two
 * after. Nothing while apart.
 */
export function WhereStrip({ name }: { name: string }) {
  const client = useQueryClient()
  const where = useWhere()
  const line = stripLine(where.data, name)
  const action = stripAction(where.data)
  const outing = where.data?.outing
  if (!line || !outing) return null
  const act = async (verb: StripAction['action']) => {
    await api(`/life/outings/${outing.id}/${verb}`, {}).catch(() => undefined)
    void client.invalidateQueries({ queryKey: WHERE_KEY })
    void client.invalidateQueries({ queryKey: TOGETHER_KEY })
    void client.invalidateQueries({ queryKey: ['chats'] })
  }
  const Glyph = where.data?.kind === 'out' ? MapPin : Home
  return (
    <aside className="where-strip" aria-label="Where you are">
      <Glyph aria-hidden="true" />
      <span>{line.lead}{line.place && <a className="where-strip-place" href={`#map/${encodeURIComponent(line.place.id)}`} title="Show on map">{line.place.name}</a>}{line.tail}</span>
      {action && <StripButton action={action} onClick={() => void act(action.action)} />}
    </aside>
  )
}

function StripButton({ action, onClick }: { action: StripAction; onClick: () => void }) {
  const Glyph = ACTION_GLYPHS[action.label] ?? DoorOpen
  return <button type="button" className="text-button" onClick={onClick}><Glyph aria-hidden="true" />{action.label}</button>
}
