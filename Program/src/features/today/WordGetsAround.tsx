import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { NewsItem } from '../../types'
import { storyDate } from './storyText'

/** News travels (companion/news.py): who has heard the companion's recent news, and from whom. Shown only once
 * someone besides them has. */
export function WordGetsAround({ name }: { name: string }) {
  const list = useQuery({ queryKey: ['news'], queryFn: () => api<NewsItem[]>('/life/news') })
  const items = (list.data ?? []).filter((item) => item.heard.length > 0)
  if (!items.length) return null
  return (
    <section className="today-section" aria-labelledby="word-heading">
      <h2 id="word-heading">Word getting around</h2>
      <p className="subtle">News from {name}&apos;s life travels from person to person, a step a day.</p>
      <ul className="plain-list">
        {items.map((item) => (
          <li key={item.id}>
            <p><time dateTime={item.happened_on}>{storyDate(item.happened_on)}</time> {item.text}.</p>
            <p className="subtle">{item.heard.map((person) => `${person.name} (${storyDate(person.heard_on)}${person.from ? `, from ${person.from}` : ''})`).join(', ')}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}
