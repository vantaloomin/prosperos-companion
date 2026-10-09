import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../../api'
import type { Moment } from '../../types'
import { storyDate } from './storyText'

/** Little things (companion/life/deck.py): the small moment the Life deck drew into each of the last few days. With
 * Hidden values > odds on, each opens to its odds and a way to make it go another way. */
export function LittleThings({ moments, name }: { moments: Moment[] | undefined; name: string }) {
  if (!moments?.length) return null
  return (
    <section className="today-section" aria-labelledby="little-things-heading">
      <h2 id="little-things-heading">Little things</h2>
      <p className="subtle">Small moments in {name}&apos;s days, drawn from the Life deck. How often they happen is set by the drama level in Settings.</p>
      <ul className="plain-list">
        {moments.map((item) => (
          <li key={item.day}>
            <p><time dateTime={item.day}>{storyDate(item.day)}</time> {item.text}</p>
            {item.odds !== undefined && <MomentOdds item={item} />}
          </li>
        ))}
      </ul>
    </section>
  )
}

function chanceText(odds: number): string {
  if (odds >= 1) return 'Certain'
  return odds > 0 ? `About 1 in ${Math.max(2, Math.round(1 / odds))}` : 'Very unlikely'
}

function MomentOdds({ item }: { item: Moment }) {
  const client = useQueryClient()
  const [failed, setFailed] = useState('')
  const change = async (way: 'another' | 'nothing') => {
    setFailed('')
    try {
      await api<Moment[]>(`/life/moments/${item.day}/change`, { way })
    } catch (error) {
      setFailed(error instanceof Error ? error.message : String(error))
      return
    }
    await client.invalidateQueries({ queryKey: ['today'] })
  }
  return (
    <details className="why-it-went">
      <summary>Why it went this way</summary>
      <p className="subtle">
        {item.picked_by === 'user' ? 'You picked another way. ' : ''}
        Drawn from {item.source === 'Life deck' ? 'the Life deck' : `the ${item.source} table`}: “{item.title}”, {chanceText(item.odds ?? 0).toLowerCase()} that day.
      </p>
      <div className="form-actions">
        <button type="button" className="text-button" onClick={() => void change('another')}>Something else happens</button>
        <button type="button" className="text-button" onClick={() => void change('nothing')}>Nothing happens</button>
      </div>
      {failed && <p className="subtle" role="alert">{failed}</p>}
    </details>
  )
}
