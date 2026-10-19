import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { COMPANION_KEY } from '../../companion'
import type { FamilyTurn, LifeChapter } from '../../types'
import { storyDate } from './storyText'
import { WhyItWent } from './WhyItWent'
import { LATELY_KEY, outcomeSummary } from '../character/turnsText'
import { FAMILY_KEY, OURS_KEY } from '../character/familyText'

const FAMILY_TURNS_KEY = ['family-turns']

/** Life chapters (companion/life/chapters.py): lasting changes to the companion's life, each with why it went this
 * way and an undo, and a pregnancy's hard turn (bed rest, an early arrival; companion/life/expecting.py) with its
 * undo the same way (why it went that way is on the Family panel). Shown only when there is one. */
export function Chapters({ name }: { name: string }) {
  const client = useQueryClient()
  const list = useQuery({ queryKey: ['chapters'], queryFn: () => api<LifeChapter[]>('/life/chapters') })
  const turns = useQuery({ queryKey: FAMILY_TURNS_KEY, queryFn: () => api<FamilyTurn[]>('/life/steps/family/turns') })
  const undo = useMutation({
    mutationFn: (id: string) => api<LifeChapter[]>(`/life/chapters/${id}/undo`, {}),
    onSuccess: async (found) => {
      client.setQueryData(['chapters'], found)
      await client.invalidateQueries({ queryKey: COMPANION_KEY })
      await client.invalidateQueries({ queryKey: LATELY_KEY })
    },
  })
  const undoTurn = useMutation({
    mutationFn: (id: string) => api<FamilyTurn[]>(`/life/steps/family/turns/${id}/undo`, {}),
    onSuccess: async (found) => {
      client.setQueryData(FAMILY_TURNS_KEY, found)
      await Promise.all([FAMILY_KEY, OURS_KEY, ['today'], COMPANION_KEY].map((queryKey) => client.invalidateQueries({ queryKey })))
    },
  })
  const busy = undo.isPending || undoTurn.isPending
  if (!list.data?.length && !turns.data?.length) return null
  return (
    <section className="today-section" aria-labelledby="chapters-heading">
      <h2 id="chapters-heading">New chapters in {name}'s life</h2>
      <ul className="plain-list">
        {turns.data?.map((item) => (
          <li key={`turn-${item.id}`}>
            <p>
              <time dateTime={item.on}>{storyDate(item.on)}</time> {item.title}.{' '}
              <button type="button" className="text-button" disabled={busy} onClick={() => undoTurn.mutate(item.id)}>Undo</button>
            </p>
          </li>
        ))}
        {list.data?.map((item) => (
          <li key={item.id}>
            <p>
              <time dateTime={item.on}>{storyDate(item.on)}</time> {item.title}.{' '}
              <button type="button" className="text-button" disabled={busy}
                onClick={() => undo.mutate(item.id)}>Undo</button>
            </p>
            {item.consequence && <WhyItWent id={item.consequence} possibleOnly />}
            {item.outcome && <WhyItWent id={item.outcome} summary={outcomeSummary(item.kind)} name={name} />}
          </li>
        ))}
      </ul>
      {undo.isError && <p className="subtle" role="alert">That chapter could not be undone. {undo.error.message}</p>}
      {undoTurn.isError && <p className="subtle" role="alert">That could not be undone. {undoTurn.error.message}</p>}
    </section>
  )
}
