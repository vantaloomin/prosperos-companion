import type { View } from '../../companion'
import type { StoryPerson } from '../../types'
import { personLine } from './storyText'

interface Props { people: StoryPerson[]; canSwitch: boolean; go: (view: View) => void; onFind: (key: string) => void }

/** The people the user has met in the story: theirs alone, not the companion's. */
export function StoryPeople({ people, canSwitch, go, onFind }: Props) {
  if (!people.length) return null
  return (
    <details className="story-people">
      <summary>People you&apos;ve met ({people.length})</summary>
      <ul>
        {people.map((person) => (
          <li key={person.key}>
            <p><strong>{person.name}</strong> <span className="subtle">{person.role}, {person.city}</span></p>
            <p className="subtle">{personLine(person)}</p>
            {person.notes.length > 0 && <p className="story-note">{person.notes[person.notes.length - 1]}</p>}
            <div className="form-actions">
              {person.place && <button type="button" className="text-button" onClick={() => onFind(person.key)}>Go to {person.name.split(' ')[0]}</button>}
              {canSwitch && <button type="button" className="text-button" onClick={() => go(`cast/${encodeURIComponent(person.key)}`)}>Make {person.name.split(' ')[0]} the main character…</button>}
            </div>
          </li>))}
      </ul>
    </details>
  )
}
