import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../../api'
import type { Consequence } from '../../types'
import { storyDate } from './storyText'

/** "Why it went this way": each way a turning could have gone, its odds and what moved them, and a way to make
 * it go another way. Loads only when opened. */
export function WhyItWent({ id }: { id: string }) {
  const [open, setOpen] = useState(false)
  const client = useQueryClient()
  const key = ['consequence', id]
  const outcome = useQuery({ queryKey: key, queryFn: () => api<Consequence>(`/life/consequences/${id}`), enabled: open })
  const change = async (option: number) => {
    client.setQueryData(key, await api<Consequence>(`/life/consequences/${id}/change`, { option }))
    await Promise.all([client.invalidateQueries({ queryKey: ['storylines'] }), client.invalidateQueries({ queryKey: ['reactions'] })])
  }
  return (
    <details className="why-it-went" onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary>Why it went this way</summary>
      {outcome.data && (
        <>
          <p className="subtle">{outcome.data.label}{outcome.data.picked_by === 'user' ? ': you picked how it went.' : '.'}</p>
          <ul className="plain-list">
            {outcome.data.options.map((item) => (
              <li key={item.option}>
                <p>
                  <strong>{Math.round(item.odds * 100)}%</strong> {item.label}
                  {item.option === outcome.data.picked && <span className="subtle"> (what happened)</span>}
                </p>
                {item.reasons.length > 0 && <p className="subtle">{item.reasons.join('. ')}.</p>}
                {item.option !== outcome.data.picked && (
                  <button type="button" className="text-button" onClick={() => void change(item.option)}>Make it go this way</button>
                )}
              </li>
            ))}
          </ul>
          {outcome.data.marks.length > 0 && (
            <>
              <p className="subtle">What it left, for a while:</p>
              <ul className="plain-list">
                {outcome.data.marks.map((mark) => (
                  <li key={mark.holder + mark.kind + mark.note} className="subtle">
                    {mark.ripple ? `It reached ${mark.who ?? 'another companion'}, who is close to them` : mark.note}, until {storyDate(mark.until)}.
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
      {outcome.isError && <p className="subtle">This outcome could not be loaded. {String(outcome.error.message)}</p>}
    </details>
  )
}
