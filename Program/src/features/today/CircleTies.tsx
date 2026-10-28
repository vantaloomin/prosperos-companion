import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { api } from '../../api'
import type { CirclePerson } from '../../types'
import { Notice } from '../../components/Feedback'
import { TIE_CHOICES } from './circleText'
import type { Act } from './PersonForm'

type Feedback = { tone: 'info' | 'error'; text: string }

const NOT_AT_ALL = ''

/** Who someone knows in the companion's circle while their card is open for changes (companion/life/circle.py
 * set_tie): the app's links, each changeable or taken away, and a way to link them to someone else. Each change saves
 * on its own and shows on both people's cards. */
export function CircleTies({ person, act }: { person: CirclePerson; act: Act }) {
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const circle = useQuery({ queryKey: ['circle', false], queryFn: () => api<CirclePerson[]>('/life/circle?include_removed=false') })
  const knows = person.knows ?? []
  const others = (circle.data ?? []).filter((other) => other.id !== person.id && !other.shared && other.status === 'active' && !other.late
    && !knows.some((item) => item.id === other.id))
  const save = (otherId: string, otherName: string, how: string) => act(() => api(`/life/circle/${person.id}/ties`, { other_id: otherId, how }, 'PUT'),
    how === NOT_AT_ALL ? `${person.name} and ${otherName} don't know each other now.` : `Saved: ${person.name} and ${otherName}, ${how}.`, setFeedback)
  const headingId = `circle-ties-${person.id}`
  return (
    <section className="circle-pets circle-ties" aria-labelledby={headingId}>
      <h4 id={headingId}>Who {person.name} knows here</h4>
      <p className="subtle">Changes here save on their own and show on both cards.</p>
      <div aria-live="polite">{feedback && <Notice tone={feedback.tone}>{feedback.text}</Notice>}</div>
      {knows.length === 0 && <p className="subtle">No one else in this circle yet.</p>}
      {knows.length > 0 && <ul className="circle-tie-list">{knows.map((item) => (
        <li key={item.id} className="circle-tie">
          <label htmlFor={`${headingId}-${item.id}`}>{item.name}</label>
          <select id={`${headingId}-${item.id}`} value={item.how} onChange={(event) => void save(item.id, item.name, event.target.value)}>
            {choices(item.how).map((choice) => <option key={choice.value} value={choice.value}>{choice.label}</option>)}
            <option value={NOT_AT_ALL}>Don't know each other</option>
          </select>
        </li>))}</ul>}
      {others.length > 0 && <AddTie id={headingId} others={others} onAdd={save} />}
    </section>
  )
}

/** The listed ways, with the one they have now kept when it isn't one of them. */
function choices(how: string) {
  return TIE_CHOICES.some((choice) => choice.value === how) ? TIE_CHOICES : [{ value: how, label: how[0].toUpperCase() + how.slice(1) }, ...TIE_CHOICES]
}

function AddTie({ id, others, onAdd }: { id: string; others: CirclePerson[]; onAdd: (otherId: string, otherName: string, how: string) => Promise<boolean> }) {
  const [open, setOpen] = useState(false)
  const [other, setOther] = useState(others[0].id)
  const [how, setHow] = useState('friends')
  const picked = others.find((item) => item.id === other) ?? others[0]
  if (!open) return <button type="button" className="text-button" onClick={() => setOpen(true)}><Plus aria-hidden="true" />Add someone they know</button>
  const add = async () => { if (await onAdd(picked.id, picked.name, how)) setOpen(false) }
  return (
    <div className="circle-form-row circle-tie-add">
      <div className="circle-field">
        <label htmlFor={`${id}-who`}>Who</label>
        <select id={`${id}-who`} value={picked.id} onChange={(event) => setOther(event.target.value)}>
          {others.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
      </div>
      <div className="circle-field">
        <label htmlFor={`${id}-how`}>How they know each other</label>
        <select id={`${id}-how`} value={how} onChange={(event) => setHow(event.target.value)}>
          {TIE_CHOICES.map((choice) => <option key={choice.value} value={choice.value}>{choice.label}</option>)}
        </select>
      </div>
      <div className="rename-row">
        <button type="button" className="button primary" onClick={() => void add()}>Add</button>
        <button type="button" className="button quiet" onClick={() => setOpen(false)}>Cancel</button>
      </div>
    </div>
  )
}
