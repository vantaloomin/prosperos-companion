import { useQuery, useQueryClient } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { api } from '../../api'
import type { Storyline } from '../../types'
import { STORYLINES_KEY as KEY, storyDate, withYou } from './storyText'
import { WhyItWent } from './WhyItWent'

/** What is unfolding in the companion's life and their people's: the beats so far, never what comes next. The ones
 * the user is part of have their own section above (InvolvesYou.tsx). */
export function Storylines({ name }: { name: string }) {
  const client = useQueryClient()
  const list = useQuery({ queryKey: KEY, queryFn: () => api<Storyline[]>('/life/storylines') })
  const found = withYou(list.data ?? [], false)
  if (!found.length) return null
  const end = async (item: Storyline) => {
    client.setQueryData(KEY, await api<Storyline[]>(`/life/storylines/${item.id}/end`, {}))
  }
  return (
    <section className="today-section" aria-labelledby="storylines-heading">
      <h2 id="storylines-heading">Going on in {name}'s world</h2>
      <p className="subtle">Fiction about {name} and their people. How much happens is set by the drama level in Settings.</p>
      <ul className="plain-list">
        {found.map((item) => (
          <li key={item.id}>
            {item.beats.map((beat) => (
              <div key={beat.on + beat.text}>
                <p><time dateTime={beat.on}>{storyDate(beat.on)}</time> {beat.text}</p>
                {beat.consequence && <WhyItWent id={beat.consequence} />}
              </div>
            ))}
            {item.unfolding && <p className="subtle">Still unfolding.</p>}
            <button type="button" className="text-button" onClick={() => void end(item)}><X aria-hidden="true" />End this storyline</button>
          </li>
        ))}
      </ul>
    </section>
  )
}
