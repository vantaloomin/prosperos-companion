import { useQuery, useQueryClient } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { api } from '../../api'
import type { Recommendation } from '../../types'
import { recommendationText } from './todayText'

const KEY = ['recommendations']

/** Things the user recommended, with how far the companion has got. Taking one back clears what is still to come. */
export function Recommendations({ name }: { name: string }) {
  const client = useQueryClient()
  const list = useQuery({ queryKey: KEY, queryFn: () => api<Recommendation[]>('/life/recommendations') })
  if (!list.data?.length) return null
  const drop = async (item: Recommendation) => {
    client.setQueryData(KEY, await api<Recommendation[]>(`/life/recommendations/${item.id}/drop`, {}))
  }
  return (
    <section className="today-section" aria-labelledby="recommendations-heading">
      <h2 id="recommendations-heading">You recommended</h2>
      <ul className="plain-list">
        {list.data.map((item) => (
          <li key={item.id}>
            <strong>{item.title}</strong>: {recommendationText(item, name)}
            {item.state !== 'finished' && <button type="button" className="text-button" onClick={() => void drop(item)}><X aria-hidden="true" />Take back</button>}
          </li>
        ))}
      </ul>
    </section>
  )
}
