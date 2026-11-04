import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { Consequence } from '../../types'
import { storyDate } from './storyText'
import { WhyItWent } from './WhyItWent'
import { firstName } from '../character/panelText'

/** How the companion took things the user did lately (companion/life/reactions.py). Shown only when there is one. The
 * heading uses their first name; the date is quiet, so the sentence starts with the person (Iris, #96). */
export function Reactions({ name }: { name: string }) {
  const list = useQuery({ queryKey: ['reactions'], queryFn: () => api<Consequence[]>('/life/reactions') })
  if (!list.data?.length) return null
  return (
    <section className="today-section" aria-labelledby="reactions-heading">
      <h2 id="reactions-heading">How {firstName(name)} took things lately</h2>
      <ul className="plain-list">
        {list.data.map((item) => (
          <li key={item.id}>
            <p><time className="reaction-date" dateTime={item.decided_on}>{storyDate(item.decided_on)}</time> {item.options[item.picked].label}.</p>
            <WhyItWent id={item.id} />
          </li>
        ))}
      </ul>
    </section>
  )
}
