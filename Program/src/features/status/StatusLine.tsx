import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Briefcase, MapPin, Moon, Pencil } from 'lucide-react'
import { api } from '../../api'
import { COMPANION_KEY } from '../../companion'
import { shown, statusLabel, stickHint, type AwayGlyph, type CompanionStatus } from './statusText'

const GLYPHS: Record<AwayGlyph, typeof Moon> = { moon: Moon, briefcase: Briefcase, pin: MapPin }

/**
 * A companion's status, or their away line while they sleep, work or are out (italic, with an outline glyph).
 * Only a hint, like an AIM away message: never an online dot, and the chat stays open either way.
 */
export function StatusText({ name, status, className = '' }: { name: string; status: CompanionStatus | null | undefined; className?: string }) {
  const line = shown(status)
  if (!line) return null
  const Glyph = line.away ? GLYPHS[line.away] : null
  return (
    <span className={`status-line${line.away ? ' away' : ''} ${className}`} title={line.text} aria-label={statusLabel(name, status)}>
      {Glyph && <Glyph aria-hidden="true" />}<span aria-hidden="true">{line.text}</span>
    </span>
  )
}

/** The status on the profile card and Character page: click it to write your own, Enter saves, Esc cancels. */
export function StatusEditor({ id, name, status }: { id: string; name: string; status: CompanionStatus | null | undefined }) {
  const client = useQueryClient()
  const [draft, setDraft] = useState<string | null>(null)
  const [error, setError] = useState('')
  const save = async (text: string) => {
    setDraft(null)
    if (text.trim() === (status?.set_by === 'you' ? status.text : '')) return
    try {
      await api(`/companion/${id}/status`, { text }, 'PUT')
      setError('')
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'That status did not save.') }
    void client.invalidateQueries({ queryKey: COMPANION_KEY })
    void client.invalidateQueries({ queryKey: ['chats'] })
  }
  if (draft === null) {
    return (
      <div className="status-edit">
        <button type="button" className="status-button" aria-label={`${statusLabel(name, status) || `${name}'s status`}. Edit`} onClick={() => setDraft(status?.set_by === 'you' ? status.text : '')}>
          <StatusText name={name} status={status} /><Pencil className="status-pencil" aria-hidden="true" />
        </button>
        {error && <p className="field-error" role="alert">{error}</p>}
      </div>
    )
  }
  return (
    <div className="status-edit">
      <input autoFocus className="status-input" value={draft} maxLength={120} aria-label={`${name}'s status`} placeholder={status?.text ?? ''}
        onChange={(event) => setDraft(event.target.value)} onBlur={() => void save(draft)}
        onKeyDown={(event) => { if (event.key === 'Enter') void save(draft); if (event.key === 'Escape') setDraft(null) }} />
      <p className="subtle status-hint">{stickHint(name)}</p>
    </div>
  )
}
