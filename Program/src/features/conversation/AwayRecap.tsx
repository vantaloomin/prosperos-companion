import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { AwayRecap as Recap } from '../../types'

const RECAP_KEY = ['recap']

/** While you were away: after a few days without a message, a short catch-up above the composer, shown once. */
export function AwayRecap({ name }: { name: string }) {
  const client = useQueryClient()
  const recap = useQuery({ queryKey: RECAP_KEY, queryFn: () => api<{ recap: Recap | null }>('/conversation/recap').then((data) => data.recap) }).data
  if (!recap) return null
  const read = async () => {
    client.setQueryData(RECAP_KEY, null)
    await api('/conversation/recap/read', { since: recap.since }).catch(() => undefined)
  }
  return (
    <aside className="away-recap" aria-labelledby="away-recap-heading">
      <h2 id="away-recap-heading">While you were away <span className="subtle">({recap.days} days)</span></h2>
      <ul>{recap.items.map((item) => <li key={item}>{item}</li>)}</ul>
      <button type="button" className="text-button" onClick={() => void read()}>Got it, back to {name}</button>
    </aside>
  )
}
