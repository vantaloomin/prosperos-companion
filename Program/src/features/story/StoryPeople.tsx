import type { View } from '../../companion'
import type { StoryCompanion, StoryPerson } from '../../types'
import { companionLine, personLine } from './storyText'
import { useStartWith } from '../character/useSwitchBack'
import { Notice } from '../../components/Feedback'

interface Props {
  people: StoryPerson[]; companions: StoryCompanion[]; city: string; canSwitch: boolean
  go: (view: View) => void; onFind: (key: string) => void
  /** Says a line in the story for the user (asking someone out). */
  onSay: (line: string) => void; busy: boolean
}

/** The people the user can go to in the story: their companions, by where their day has them now, then everyone
 * they have met in it (theirs alone, not the companion's). */
export function StoryPeople({ people, companions, city, canSwitch, go, onFind, onSay, busy }: Props) {
  const starting = useStartWith(go)
  if (!people.length && !companions.length) return null
  return (
    <details className="story-people">
      <summary>{companions.length ? 'People you know' : "People you've met"} ({people.length + companions.length})</summary>
      {starting.error && <Notice tone="error">{starting.error}</Notice>}
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
              {person.place && <button type="button" className="text-button" onClick={() => onFind(person.key)}>Go to {first(person)}</button>}
              {person.ask && <button type="button" className="text-button" disabled={busy} onClick={() => onSay(person.ask!.line)}>{person.ask.label}</button>}
              <Become person={person} canSwitch={canSwitch} go={go} starting={starting} />
            </div>
          </li>))}
      </ul>
    </details>
  )
}

function first(person: StoryPerson): string {
  return person.name.split(' ')[0]
}

interface BecomeProps { person: StoryPerson; canSwitch: boolean; go: (view: View) => void; starting: ReturnType<typeof useStartWith> }

/** How someone met becomes a companion: one who said yes starts as a romance, as a match does (one tap, or their
 * profile first); anyone else can be made the main character, as a friend. A companion already is one. */
function Become({ person, canSwitch, go, starting }: BecomeProps) {
  if (person.companion_id) return null
  if (person.matched) return (<>
    <button type="button" className="text-button" disabled={starting.busy !== null} onClick={() => void starting.startWith(person.key)}>
      {starting.busy === person.key ? 'Starting…' : `Start talking to ${first(person)}`}</button>
    <button type="button" className="text-button" onClick={() => go(`match/${encodeURIComponent(person.key)}`)}>Read their profile first</button>
  </>)
  if (!canSwitch) return null
  return <button type="button" className="text-button" onClick={() => go(`cast/${encodeURIComponent(person.key)}`)}>Make {first(person)} the main character…</button>
}
