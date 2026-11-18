import type { View } from '../../companion'
import type { StoryCompanion, StoryPerson } from '../../types'
import { companionLine, personLine } from './storyText'

interface Props {
  people: StoryPerson[]; companions: StoryCompanion[]; city: string; canSwitch: boolean
  go: (view: View) => void; onFind: (key: string) => void
}

/** The people the user can go to in the story: their companions, by where their day has them now, then everyone
 * they have met in it (theirs alone, not the companion's). */
export function StoryPeople({ people, companions, city, canSwitch, go, onFind }: Props) {
  if (!people.length && !companions.length) return null
  return (
    <details className="story-people">
      <summary>{companions.length ? 'People you know' : "People you've met"} ({people.length + companions.length})</summary>
      <ul>
        {companions.map((companion) => (
          <li key={companion.key}>
            <p><strong>{companion.name}</strong></p>
            <p className="subtle">{companionLine(companion, city)}</p>
            {companion.place && !companion.here && <div className="form-actions">
              <button type="button" className="text-button" onClick={() => onFind(companion.key)}>Go to {companion.name}</button>
            </div>}
          </li>))}
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
