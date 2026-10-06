import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { MapPin } from 'lucide-react'
import { api } from '../../api'
import type { View } from '../../companion'
import type { Townsperson, TownspersonNow } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { useSwitchBack } from '../character/useSwitchBack'
import { townMet, townNow, townRole } from './townText'

/** Background people the companion keeps running into around town. Hidden until there is someone. */
export function Townsfolk({ name, go }: { name: string; go: (view: View) => void }) {
  const known = useQuery({ queryKey: ['townsfolk'], queryFn: () => api<Townsperson[]>('/life/townsfolk') })
  if (!known.data || known.data.length === 0) return null
  return (
    <section className="today-section" aria-labelledby="townsfolk-heading">
      <h2 id="townsfolk-heading">Around town</h2>
      <p className="subtle">People {name} keeps running into. {name} learns a little more each time.</p>
      <ul className="network-list">
        {known.data.map((person) => <TownItem key={person.key} person={person} go={go} />)}
      </ul>
    </section>
  )
}

function TownItem({ person, go }: { person: Townsperson; go: (view: View) => void }) {
  const [open, setOpen] = useState(false)
  return (
    <li>
      <strong>{person.full}</strong> <span className="subtle">{townRole(person)}. {townMet(person)}</span>
      <button type="button" className="text-button" aria-expanded={open} onClick={() => setOpen((value) => !value)}><MapPin aria-hidden="true" />{open ? 'Less' : 'More'}</button>
      {open && <TownDetail person={person} go={go} />}
    </li>
  )
}

function TownDetail({ person, go }: { person: Townsperson; go: (view: View) => void }) {
  const now = useQuery({ queryKey: ['townsfolk', person.key], queryFn: () => api<{ now: TownspersonNow | null }>(`/life/townsfolk/person?key=${encodeURIComponent(person.key)}`) })
  return (
    <div className="town-detail">
      <p>About {person.age}, {person.temperament}; {person.quirk}.</p>
      {person.goal && <p>Trying to {person.goal}.{person.lately ? ` Last heard: ${person.lately}.` : ''}</p>}
      {person.reached.length > 0 && <p className="subtle">Already managed to {person.reached.join('; ')}.</p>}
      {person.routine && <p className="subtle">Usually {person.routine}.</p>}
      {person.flaw && <p>{person.flaw.charAt(0).toUpperCase()}{person.flaw.slice(1)}; seems to want {person.desire}.</p>}
      {!person.goal && <p className="subtle">Cross paths again to learn more.</p>}
      {now.isPending ? <Loading label="Finding them" /> : now.isError ? <Notice tone="error">{now.error.message}</Notice> : now.data.now && <p className="subtle">{townNow(now.data.now)}</p>}
      <TownSwitch person={person} go={go} />
    </div>
  )
}

/** Another companion goes back to being the main character; anyone else gets a profile to review first. */
function TownSwitch({ person, go }: { person: Townsperson; go: (view: View) => void }) {
  const { switchTo, busy, error } = useSwitchBack(go)
  const companionId = person.cast
  if (!companionId) {
    return <p><button type="button" className="text-button" onClick={() => go(`cast/${encodeURIComponent(person.key)}`)}>Make {person.name} the main character…</button></p>
  }
  return (<>
    <p><button type="button" className="text-button" disabled={busy !== null} onClick={() => void switchTo(companionId)}>{busy ? 'Switching…' : `Switch back to ${person.name}`}</button></p>
    {error && <Notice tone="error">{error}</Notice>}
  </>)
}
