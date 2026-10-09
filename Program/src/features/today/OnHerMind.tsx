import { Sparkles } from 'lucide-react'
import type { Thought } from '../../types'
import { storyDate } from './storyText'

/** On her mind (companion/life/thoughts.py): one private thought a day, worked out from what happened. Folded under
 * the day's heading; opening it shows the last week. Never part of the chat, and the companion never knows it was read. */
export function OnHerMind({ thoughts, name }: { thoughts: Thought[]; name: string }) {
  if (!thoughts.length) return null
  return (
    <details className="on-her-mind">
      <summary><Sparkles aria-hidden="true" />On {name}&apos;s mind</summary>
      <ul className="plain-list">
        {thoughts.map((item) => (
          <li key={item.day}><time dateTime={item.day}>{storyDate(item.day)}</time> {item.text}</li>
        ))}
      </ul>
    </details>
  )
}
