import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, X } from 'lucide-react'
import { api } from '../../api'
import type { Suggestion } from '../../types'
import { suggestionReason } from './memoryGroups'

const SUGGESTIONS_KEY = ['memory-suggestions']

/** Facts found in your messages that wait for a decision. Declined ones are never suggested again. */
export function Suggestions({ name, run }: { name: string; run: <T>(action: () => Promise<T>, done: string) => Promise<T | null> }) {
  const client = useQueryClient()
  const suggestions = useQuery({ queryKey: SUGGESTIONS_KEY, queryFn: () => api<Suggestion[]>('/memory/suggestions') })
  if (!suggestions.data?.length) return null
  const decide = async (suggestion: Suggestion, keep: boolean) => {
    await run(() => api(`/memory/suggestions/${suggestion.id}/${keep ? 'accept' : 'decline'}`, {}),
      keep ? `${name} will remember “${suggestion.subject}”.` : `“${suggestion.subject}” won't be suggested again.`)
    await client.invalidateQueries({ queryKey: SUGGESTIONS_KEY })
  }
  return (
    <section className="memory-group suggestions" aria-labelledby="suggestions-heading">
      <h2 id="suggestions-heading">Waiting for you</h2>
      <p className="subtle">Things you said that {name} only keeps if you agree.</p>
      <ul className="memory-list">
        {suggestions.data.map((suggestion) => (
          <li key={suggestion.id} className="memory">
            <div className="memory-main">
              <p className="memory-subject">{suggestion.subject}</p>
              <p className="memory-value">{suggestion.value || suggestion.excerpt}</p>
              <p className="memory-meta">{suggestion.sensitive && <span className="badge">Sensitive</span>}<span>{suggestionReason(suggestion.reason)}</span></p>
              <p className="memory-source">From your message: <q>{suggestion.excerpt}</q></p>
            </div>
            <div className="memory-actions" role="group" aria-label={`Decide about ${suggestion.subject}`}>
              <button type="button" className="text-button" onClick={() => void decide(suggestion, true)}><Check aria-hidden="true" />Remember</button>
              <button type="button" className="text-button" onClick={() => void decide(suggestion, false)}><X aria-hidden="true" />Don't remember</button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
