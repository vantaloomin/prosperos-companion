import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { Consequence } from '../../types'
import { storyDate } from './storyText'
import { WhyItWent } from './WhyItWent'

/** How the companion took things the user did lately (companion/life/reactions.py). Shown only when there is one. */
export function Reactions({ name }: { name: string }) {
  const list = useQuery({ queryKey: ['reactions'], queryFn: () => api<Consequence[]>('/life/reactions') })
  if (!list.data?.length) return null
  return (
    <section className="today-section" aria-labelledby="reactions-heading">
      <h2 id="reactions-heading">How {name} took things lately</h2>
      <ul className="plain-list">
        {list.data.map((item) => (
          <li key={item.id}>
            <p><time dateTime={item.decided_on}>{storyDate(item.decided_on)}</time> {item.options[item.picked].label}.</p>
            <WhyItWent id={item.id} />
          </li>
        ))}
      </ul>
    </section>
  )
}
