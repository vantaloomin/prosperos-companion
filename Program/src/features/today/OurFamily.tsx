import type { TodayChild } from '../../types'
import { stepDate } from '../character/stepsText'
import { ourChildAge } from '../character/familyText'

/** Your children with them (companion/life/our_child.py) on Today: name and age, what they are into lately and the
 * latest milestone. Words only, no picture. */
export function OurFamily({ family }: { family?: TodayChild[] }) {
  if (!family?.length) return null
  return (
    <section className="today-section" aria-labelledby="our-family-heading">
      <h2 id="our-family-heading">{family.length === 1 ? 'Your child' : 'Your children'}</h2>
      <ul className="event-list">
        {family.map((child) => (
          <li key={child.id} className="event our-family-item">
            <p><strong>{child.name}</strong> <span className="subtle">· {ourChildAge(child.age_text)}</span></p>
            {child.where_today && <p className="subtle">{child.where_today}.</p>}
            {child.likes && <p>Lately into {child.likes}.</p>}
            {child.latest && <p className="subtle pet-line"><span className="pet-line-label">Latest ·</span> {child.latest.label}, {stepDate(child.latest.date)}</p>}
          </li>
        ))}
      </ul>
    </section>
  )
}
