import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, X } from 'lucide-react'
import { api } from '../../api'
import type { SelfFact } from '../../types'
import { Notice } from '../../components/Feedback'
import { orderFacts, selfFactText } from './selfFactText'

const KEY = ['self-facts']

/** What the companion has said about themselves in conversation, kept consistent in later replies. */
export function SelfFacts({ name }: { name: string }) {
  const client = useQueryClient()
  const facts = useQuery({ queryKey: KEY, queryFn: () => api<{ facts: SelfFact[] }>('/self-facts') })
  const [error, setError] = useState<string | null>(null)
  const decide = async (fact: SelfFact, keep: boolean) => {
    try {
      client.setQueryData(KEY, await api<{ facts: SelfFact[] }>(`/self-facts/${fact.id}/${keep ? 'keep' : 'remove'}`, {}))
      setError(null)
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'That did not work.') }
  }
  const list = orderFacts(facts.data?.facts ?? [])
  return (
    <section className="settings-section" aria-labelledby="self-facts-heading">
      <h2 id="self-facts-heading">What {name} has said about themselves</h2>
      <p className="subtle">Picked up from {name}'s own messages so later replies stay consistent. Keep the ones you like; remove any you don't want to hold.</p>
      {error && <Notice tone="error">{error}</Notice>}
      {list.length === 0 ? <p className="subtle">Nothing yet. Things like "I hate cilantro" or "my brother Theo" show up here.</p> : (
        <ul className="plain-list">
          {list.map((fact) => (
            <li key={fact.id}>
              <strong>{selfFactText(fact)}</strong>{fact.status === 'kept' && <span className="badge">kept</span>}
              {fact.status === 'conflict' && <span className="badge">contradicts something they said earlier</span>}
              <br /><small className="subtle">"{fact.statement}"</small>
              <span className="form-actions">
                {fact.status !== 'kept' && <button type="button" className="text-button" onClick={() => void decide(fact, true)}><Check aria-hidden="true" />{fact.status === 'conflict' ? 'Keep this one' : 'Keep'}</button>}
                <button type="button" className="text-button" onClick={() => void decide(fact, false)}><X aria-hidden="true" />Remove</button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
