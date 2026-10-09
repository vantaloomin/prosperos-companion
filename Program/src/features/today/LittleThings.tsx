import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../../api'
import type { Dream, Moment } from '../../types'
import { storyDate } from './storyText'

/** Little things (companion/life/deck.py): the small moment the Life deck drew into each of the last few days. With
 * Hidden values > odds on, each opens to its odds and a way to make it go another way. */
export function LittleThings({ moments, dreams, name }: { moments: Moment[] | undefined; dreams: Dream[] | undefined; name: string }) {
  if (!moments?.length && !dreams?.length) return null
  return (
    <section className="today-section" aria-labelledby="little-things-heading">
      <h2 id="little-things-heading">Little things</h2>
      <p className="subtle">Small moments in {name}&apos;s days, and the odd dream. How often they happen is set by the drama level in Settings.</p>
      <ul className="plain-list">
        {(dreams ?? []).map((item) => (
          <li key={`dream-${item.day}`}>
            <p><time dateTime={item.day}>{storyDate(item.day)}</time> <span className="subtle">Dream:</span> {item.text}</p>
            {item.sleep_talk && <p className="subtle">{item.sleep_talk}</p>}
          </li>
        ))}
        {(moments ?? []).map((item) => (
          <li key={item.day}>
            <p><time dateTime={item.day}>{storyDate(item.day)}</time> {item.text}</p>
            {item.odds !== undefined && <MomentOdds item={item} />}
          </li>
        ))}
      </ul>
    </section>
  )
}

function percent(odds: number): string {
  return odds < 0.01 ? 'Under 1%' : `${Math.round(odds * 100)}%`
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
      <p className="subtle">{item.picked_by === 'user' ? 'You drew another card. ' : ''}{item.source === 'Life deck' ? 'Drawn from the Life deck' : `From the ${item.source} table`}</p>
      <div className="deck-card">
        <strong>{item.title}</strong>
        <span>{item.text}</span>
        <span className="subtle">{percent(item.odds ?? 0)} today</span>
      </div>
      <div className="form-actions">
        <button type="button" className="text-button" onClick={() => void change('another')}>Draw another card</button>
        <button type="button" className="text-button" onClick={() => void change('nothing')}>Nothing happens</button>
      </div>
      {failed && <p className="subtle" role="alert">{failed}</p>}
    </details>
  )
}
