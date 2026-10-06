import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Trash2 } from 'lucide-react'
import { api } from '../../api'
import type { Observation } from '../../types'
import { Notice } from '../../components/Feedback'
import { observationSummary, sentArguments } from '../settings/contextTools'

const OBSERVATIONS_KEY = ['context-observations']

/** Real-world lookups, kept apart from memories: what was sent, where, when, and whether it is still current (PRD X2). */
export function LookedUp({ name }: { name: string }) {
  const client = useQueryClient()
  const [open, setOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const observations = useQuery({ queryKey: OBSERVATIONS_KEY, queryFn: () => api<{ observations: Observation[] }>('/context/observations?limit=50'), enabled: open })
  const act = async (action: () => Promise<unknown>) => {
    try { await action(); setError(null) } catch (failure) { setError(failure instanceof Error ? failure.message : 'Not deleted.') }
    await client.invalidateQueries({ queryKey: OBSERVATIONS_KEY })
  }
  const items = observations.data?.observations ?? []
  return (
    <details className="context-receipt" onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary>Real-world lookups</summary>
      <p className="subtle">Weather, news and events looked up for {name}'s replies. They are outside information, not memories, and are never saved as facts about you.</p>
      {error && <Notice tone="error">{error}</Notice>}
      {observations.isSuccess && items.length === 0 && <p className="subtle">Nothing has been looked up. Lookups are set up in Settings.</p>}
      <ul className="lookup-list">
        {items.map((item) => {
          const summary = observationSummary(item)
          return (
            <li key={item.id} className={`lookup-${summary.tone}`}>
              <div className="backend-title"><strong>{summary.title}</strong><span className="badge">{summary.state}</span></div>
              <p className="subtle">
                {new Date(item.requested_at).toLocaleString()} · {item.service_name}, tool {item.tool} · sent {sentArguments(item)} · to {item.destination}
                {item.attempts > 1 ? ` · ${item.attempts} attempts` : ''}
              </p>
              {item.content && <p className="lookup-content">{item.content}</p>}
              <div className="post-actions">
                <button type="button" className="text-button danger-text" onClick={() => void act(() => api(`/context/observations/${item.id}`, undefined, 'DELETE'))}><Trash2 aria-hidden="true" />Delete</button>
              </div>
            </li>
          )
        })}
      </ul>
      {items.length > 0 && <div className="form-actions"><button type="button" className="button" onClick={() => void act(() => api('/context/observations/clear', {}))}>Delete all lookups</button></div>}
    </details>
  )
}
