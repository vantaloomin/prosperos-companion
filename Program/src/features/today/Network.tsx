import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Users } from 'lucide-react'
import { api } from '../../api'
import type { Acquaintance, NetworkAnswer, NetworkPerson } from '../../types'
import { Loading } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { metLine, networkLine } from './networkText'

/** Someone's own people, opened one layer at a time. They are built on request and mostly never come up. */
export function TheirPeople({ personKey, name }: { personKey: string; name: string }) {
  const answer = useQuery({ queryKey: ['network', personKey], queryFn: () => api<NetworkAnswer>(`/life/network?key=${encodeURIComponent(personKey)}`) })
  if (answer.isPending) return <Loading label={`Loading ${name}'s people`} />
  if (answer.isError) return <ErrorNotice error={answer.error} />
  if (answer.data.people.length === 0) return <p className="subtle">No one further out.</p>
  return (
    <ul className="network-list" aria-label={`${name}'s people`}>
      {answer.data.people.map((person) => <NetworkItem key={person.key} person={person} deeper={answer.data.deeper} />)}
    </ul>
  )
}

function NetworkItem({ person, deeper }: { person: NetworkPerson; deeper: boolean }) {
  const [open, setOpen] = useState(false)
  return (
    <li>
      <strong>{person.full}</strong> <span className="subtle">{networkLine(person)}</span>
      {person.met && <span className="badge">Met at {person.met}</span>}
      {deeper && <button type="button" className="text-button" aria-expanded={open} onClick={() => setOpen((value) => !value)}><Users aria-hidden="true" />{open ? 'Hide' : 'Their people'}</button>}
      {open && <TheirPeople personKey={person.key} name={person.name} />}
    </li>
  )
}

/** People the companion has met through friends, newest first. Hidden until there is someone. */
export function Acquaintances({ name }: { name: string }) {
  const met = useQuery({ queryKey: ['circle', 'acquaintances'], queryFn: () => api<Acquaintance[]>('/life/acquaintances') })
  if (!met.data || met.data.length === 0) return null
  return (
    <div className="acquaintances">
      <h3>People {name} has met through friends</h3>
      <ul className="network-list">
        {met.data.map((person) => <li key={person.key}><strong>{person.full}</strong> <span className="subtle">{networkLine(person)}. {metLine(person)}</span></li>)}
      </ul>
    </div>
  )
}
