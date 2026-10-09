import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { COMPANION_KEY } from '../../companion'
import type { LifeChapter } from '../../types'
import { storyDate } from './storyText'
import { WhyItWent } from './WhyItWent'

/** Life chapters (companion/life/chapters.py): lasting changes to the companion's life, each with why it went this
 * way and an undo. Shown only when there is one. */
export function Chapters({ name }: { name: string }) {
  const client = useQueryClient()
  const list = useQuery({ queryKey: ['chapters'], queryFn: () => api<LifeChapter[]>('/life/chapters') })
  const undo = useMutation({
    mutationFn: (id: string) => api<LifeChapter[]>(`/life/chapters/${id}/undo`, {}),
    onSuccess: async (found) => {
      client.setQueryData(['chapters'], found)
      await client.invalidateQueries({ queryKey: COMPANION_KEY })
    },
  })
  if (!list.data?.length) return null
  return (
    <section className="today-section" aria-labelledby="chapters-heading">
      <h2 id="chapters-heading">New chapters in {name}'s life</h2>
      <ul className="plain-list">
        {list.data.map((item) => (
          <li key={item.id}>
            <p>
              <time dateTime={item.started_on}>{storyDate(item.started_on)}</time> {item.title}.{' '}
              <button type="button" className="text-button" disabled={undo.isPending}
                onClick={() => undo.mutate(item.id)}>Undo</button>
            </p>
            {item.consequence && <WhyItWent id={item.consequence} possibleOnly />}
          </li>
        ))}
      </ul>
      {undo.isError && <p className="subtle" role="alert">That chapter could not be undone. {undo.error.message}</p>}
    </section>
  )
}
