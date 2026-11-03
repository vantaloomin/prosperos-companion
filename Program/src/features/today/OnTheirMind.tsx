import type { Thought } from '../../types'
import { storyDate } from './storyText'
import { firstName } from '../character/panelText'

/** On their mind (companion/life/thoughts.py): one private thought a day, worked out from what happened. The newest
 * shows in the Now card as plain text; the rest of the week folds under it. Never part of the chat, and the companion
 * never knows it was read. Nothing shows while there are none. */
export function OnTheirMind({ thoughts, name }: { thoughts: Thought[]; name: string }) {
  if (!thoughts.length) return null
  const [latest, ...earlier] = thoughts
  return (
    <div className="on-their-mind">
      <p><span className="mind-label">On {firstName(name)}&apos;s mind:</span> {latest.text}</p>
      {earlier.length > 0 && <details>
        <summary>Earlier this week · {earlier.length}</summary>
        <ul className="plain-list">
          {earlier.map((item) => (
            <li key={item.day}><time dateTime={item.day}>{storyDate(item.day)}</time> {item.text}</li>
          ))}
        </ul>
      </details>}
    </div>
  )
}
