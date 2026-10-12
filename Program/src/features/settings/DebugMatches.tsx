import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { Notice } from '../../components/Feedback'
import { Toggle } from '../../components/Fields'

const KEY = ['debug-matches']

/** Settings > Debug: every Matchlight like is liked back, to test matches and dates without swiping for them. */
export function DebugMatches() {
  const client = useQueryClient()
  const query = useQuery({ queryKey: KEY, queryFn: () => api<{ on: boolean }>('/debug-matches') })
  const [error, setError] = useState('')
  const change = async (on: boolean) => {
    setError('')
    try { client.setQueryData(KEY, await api<{ on: boolean }>('/debug-matches', { on }, 'PUT')) }
    catch (failure) { setError(failure instanceof Error ? failure.message : 'That did not work.') }
  }
  return (
    <section className="settings-section form-stack" aria-labelledby="debug-matches-heading">
      <h2 id="debug-matches-heading">Matchlight</h2>
      <Toggle label="100% Matchlight matches" checked={query.data?.on === true} disabled={!query.data} onChange={(checked) => void change(checked)}
        hint="Everyone you like on Matchlight likes you back. Passing still passes. Turn it off to go back to people choosing for themselves." />
      {error && <Notice tone="error">{error}</Notice>}
    </section>
  )
}
