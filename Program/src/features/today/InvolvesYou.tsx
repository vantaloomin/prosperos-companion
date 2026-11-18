import { useQuery, useQueryClient } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { api } from '../../api'
import type { Storyline } from '../../types'
import { STORYLINES_KEY, storyDate, storylineAnchor, withYou, yourPart } from './storyText'
import { outingAnchor } from './outingText'
import { useTogether } from './useTogether'
import { WhyItWent } from './WhyItWent'
import { showOnToday } from './showOnToday'

/** The storylines the user is part of (companion/life/shared_storylines.py): each beat so far with the user's part
 * in it, never what comes next. One stays a week after it is over; the scrapbook keeps it after that. */
export function InvolvesYou({ name }: { name: string }) {
  const client = useQueryClient()
  const list = useQuery({ queryKey: STORYLINES_KEY, queryFn: () => api<Storyline[]>('/life/storylines') })
  const plans = useTogether().data?.outings ?? []
  const found = withYou(list.data ?? [], true)
  const end = async (item: Storyline) => {
    client.setQueryData(STORYLINES_KEY, await api<Storyline[]>(`/life/storylines/${item.id}/end`, {}))
  }
  if (!found.length) return null
  return (
    <section className="today-section" aria-labelledby="involves-you-heading">
      <h2 id="involves-you-heading">Things that involve you</h2>
      <ul className="plain-list involves-you">
        {found.map((item) => (
          <li key={item.id} id={storylineAnchor(item.id)}>
            {item.beats.map((beat) => {
              const plan = beat.via === 'plan' ? plans.find((outing) => outing.place.storyline === item.id) : undefined
              const part = yourPart(beat.you, name, beat.via)
              return (
                <div key={beat.on + beat.text}>
                  <p><time dateTime={beat.on}>{storyDate(beat.on)}</time> {beat.text}</p>
                  {part && <p className="subtle your-part">{part}{plan && (beat.you?.did === 'set' || beat.you?.did === 'now') && <> <button type="button" className="text-button inline" onClick={() => showOnToday(outingAnchor(plan.id))}>See the plan</button></>}</p>}
                  {beat.consequence && <WhyItWent id={beat.consequence} />}
                </div>
              )
            })}
            {item.unfolding && <p className="subtle">Still unfolding.</p>}
            <button type="button" className="text-button" onClick={() => void end(item)}><X aria-hidden="true" />End this storyline</button>
          </li>
        ))}
      </ul>
    </section>
  )
}
