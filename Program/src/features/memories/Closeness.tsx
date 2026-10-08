import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, RotateCcw, X } from 'lucide-react'
import { api } from '../../api'
import type { Closeness as ClosenessState, Memory } from '../../types'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Field, TextInput } from '../../components/Fields'
import { ErrorNotice } from '../../components/ErrorNotice'
import { CLOSENESS_KEY, OPENNESS, basisText, milestoneText, stageText } from './closenessText'

type Run = <T>(action: () => Promise<T>, done: string) => Promise<T | null>
const SHARED = new Set(['shared_experience', 'relationship'])

/** How close the companion feels, why, and the user's controls over it (PRD M4: never a hidden score). */
export function Closeness({ name, memories, run }: { name: string; memories: Memory[]; run: Run }) {
  const client = useQueryClient()
  const closeness = useQuery({ queryKey: CLOSENESS_KEY, queryFn: () => api<ClosenessState>('/closeness') })
  const change = async (action: () => Promise<ClosenessState>, done: string) => {
    const result = await run(action, done)
    if (result) client.setQueryData(CLOSENESS_KEY, result)
    else void client.invalidateQueries({ queryKey: CLOSENESS_KEY })
  }
  if (closeness.isError) return <ErrorNotice error={closeness.error} />
  if (!closeness.data) return null
  const state = closeness.data
  return (
    <section className="memory-group closeness" aria-labelledby="closeness-heading">
      <h2 id="closeness-heading">How close you are</h2>
      <p>{stageText(state, name)} {basisText(state)}</p>
      <ol className="closeness-stages">
        {state.stages.map((stage, index) => (
          <li key={stage} aria-current={index + 1 === state.level ? 'step' : undefined}>
            <span className="closeness-stage">{stage}{index + 1 === state.level && <span className="badge">Now</span>}</span>
            <span className="subtle">{OPENNESS[index]}</span>
          </li>
        ))}
      </ol>
      {state.history.length > 0 && (
        <details className="closeness-history">
          <summary>When it changed</summary>
          <ul>{state.history.map((milestone) => <li key={milestone.level}>{milestoneText(milestone, state.stages)}</li>)}</ul>
        </details>
      )}
      <p className="subtle">
        It counts the days you talked, not how many messages or how long, plus shared moments you keep in Memories. Time apart never lowers it,
        and it only changes how {name} talks with you: nothing in the app opens or closes with it. Excluding or deleting a shared moment takes it out of the count.
      </p>
      <Controls name={name} state={state} change={change} />
      <RunningJokes name={name} state={state} memories={memories} change={change} />
    </section>
  )
}

type Change = (action: () => Promise<ClosenessState>, done: string) => Promise<void>

function Controls({ name, state, change }: { name: string; state: ClosenessState; change: Change }) {
  const [nickname, setNickname] = useState(state.nickname)
  const [confirming, setConfirming] = useState(false)
  const hold = (value: string) => {
    const level = value ? Number(value) : null
    void change(() => api('/closeness', { held_level: level }, 'PUT'),
      level ? `${name} stays at ${state.stages[level - 1]} until you change it.` : 'Closeness grows from your shared history again.')
  }
  const saveNickname = (event: FormEvent) => {
    event.preventDefault()
    void change(() => api('/closeness', { nickname }, 'PUT'),
      nickname.trim() ? `${name} may call you “${nickname.trim()}”.` : `${name} won't use a nickname you chose.`)
  }
  const reset = () => {
    setConfirming(false)
    void change(() => api('/closeness/reset', {}), `Closeness starts again from today. ${name} is back to ${state.stages[0]}.`)
  }
  return (
    <div className="closeness-controls">
      <Field label="Stage" hint="Hold it anywhere, higher or lower, or let it follow your shared history.">{(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} value={state.held_level ?? ''} onChange={(event) => hold(event.target.value)}>
          <option value="">Follow shared history</option>
          {state.stages.map((stage, index) => <option key={stage} value={index + 1}>Hold at {stage}</option>)}
        </select>
      )}</Field>
      <form className="closeness-nickname" onSubmit={saveNickname}>
        <TextInput label="A nickname you are happy with" value={nickname} onChange={setNickname} maxLength={40}
          hint={`Leave it empty and ${name} won't use a pet name before you are comfortable with each other.`} />
        <button type="submit" className="button">Save nickname</button>
      </form>
      <div>
        <button type="button" className="button danger" onClick={() => setConfirming(true)}><RotateCcw aria-hidden="true" />Start over</button>
      </div>
      {confirming && (
        <ConfirmDialog title="Start closeness over?" onClose={() => setConfirming(false)} actions={<>
          <button type="button" className="button" onClick={() => setConfirming(false)}>Cancel</button>
          <button type="button" className="button danger" onClick={reset}>Start over</button>
        </>}>
          <p>{name} goes back to {state.stages[0]} and only days and shared moments from now on count. A held stage and running jokes are cleared. Your messages, memories and nickname are kept.</p>
        </ConfirmDialog>
      )}
    </div>
  )
}

function RunningJokes({ name, state, memories, change }: { name: string; state: ClosenessState; memories: Memory[]; change: Change }) {
  const [picked, setPicked] = useState('')
  const chosen = new Set(state.jokes.map((joke) => joke.memory_id))
  const available = memories.filter((memory) => SHARED.has(memory.layer) && memory.status === 'active' && !chosen.has(memory.id))
  const add = (memoryId: string, subject: string) => change(() => api('/closeness/jokes', { memory_id: memoryId }), `“${subject}” is a running joke now.`)
  const remove = (memoryId: string, subject: string) => change(() => api(`/closeness/jokes/${memoryId}/remove`, {}), `“${subject}” is no longer a running joke.`)
  const submit = (event: FormEvent) => {
    event.preventDefault()
    const memory = available.find((item) => item.id === picked)
    if (memory) void add(memory.id, memory.subject).then(() => setPicked(''))
  }
  return (
    <div className="closeness-jokes">
      <h3>Running jokes</h3>
      <p className="subtle">Shared moments {name} may bring back now and then. Only the ones you pick are used.</p>
      {state.jokes.length > 0 && (
        <ul className="memory-list">
          {state.jokes.map((joke) => (
            <li key={joke.memory_id} className="memory">
              <div className="memory-main"><p className="memory-subject">{joke.subject}</p><p className="memory-value">{joke.value}</p></div>
              <div className="memory-actions"><button type="button" className="text-button" onClick={() => void remove(joke.memory_id, joke.subject)}><X aria-hidden="true" />Remove<span className="visually-hidden"> {joke.subject}</span></button></div>
            </li>
          ))}
        </ul>
      )}
      {state.joke_candidates.length > 0 && (
        <ul className="memory-list" aria-label="Moments that keep coming up">
          {state.joke_candidates.map((candidate) => (
            <li key={candidate.memory_id} className="memory">
              <div className="memory-main">
                <p className="memory-subject">{candidate.subject}</p>
                <p className="memory-meta"><span>Came up on {candidate.days} separate days</span></p>
              </div>
              <div className="memory-actions"><button type="button" className="text-button" onClick={() => void add(candidate.memory_id, candidate.subject)}><Plus aria-hidden="true" />Make it a running joke</button></div>
            </li>
          ))}
        </ul>
      )}
      {available.length > 0 ? (
        <form className="closeness-pick" onSubmit={submit}>
          <Field label="Pick a shared moment" hint="It becomes a running joke they bring up now and then, only when it fits.">{(id, hint) => (
            <select id={id} aria-describedby={hint} value={picked} onChange={(event) => setPicked(event.target.value)}>
              <option value="">Choose one</option>
              {available.map((memory) => <option key={memory.id} value={memory.id}>{memory.subject}</option>)}
            </select>
          )}</Field>
          <button type="submit" className="button" disabled={!picked}><Plus aria-hidden="true" />Add</button>
        </form>
      ) : state.jokes.length === 0 && <p className="subtle">Shared moments you keep in Memories can become running jokes.</p>}
    </div>
  )
}
