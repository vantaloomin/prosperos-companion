import { useState, type FormEvent, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, Plus, RotateCcw, X } from 'lucide-react'
import { api } from '../../api'
import type { Closeness as ClosenessState, Memory } from '../../types'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Field } from '../../components/Fields'
import { ErrorNotice } from '../../components/ErrorNotice'
import { CLOSENESS_KEY, OPENNESS, basisText, milestoneText, shortBasis, stageSteered, stageText } from './closenessText'
import { FoldRow, RowGroup, SettingRow, SwitchRow } from '../../components/Rows'
import { InfoTip } from '../../components/InfoTip'

type Run = <T>(action: () => Promise<T>, done: string) => Promise<T | null>
const SHARED = new Set(['shared_experience', 'relationship'])

const COUNTING = (name: string) => `It counts the days you talked, not how many messages or how long, plus shared moments you keep in Memories. Time apart only lowers it if you turn on cooling in Adjust, and it only changes how ${name} talks with you: nothing in the app opens or closes with it. Excluding or deleting a shared moment takes it out of the count.`

/**
 * How close the companion feels, why, and the user's controls over it (PRD M4: never a hidden score). The stage name
 * and a five-step meter lead, with the stage's description under them; Adjust opens the controls. The stage names come
 * from companion/closeness.py by relationship and never change in a redesign (tester, 2026-11-02).
 */
export function Closeness({ name, memories, run }: { name: string; memories: Memory[]; run: Run }) {
  const client = useQueryClient()
  const closeness = useQuery({ queryKey: CLOSENESS_KEY, queryFn: () => api<ClosenessState>('/closeness') })
  const [adjusting, setAdjusting] = useState(false)
  const change = async (action: () => Promise<ClosenessState>, done: string) => {
    const result = await run(action, done)
    if (result) client.setQueryData(CLOSENESS_KEY, result)
    else void client.invalidateQueries({ queryKey: CLOSENESS_KEY })
  }
  if (closeness.isError) return <ErrorNotice error={closeness.error} />
  if (!closeness.data) return null
  const state = closeness.data
  return (
    <section className="closeness-now" aria-labelledby="closeness-heading">
      <div className="closeness-head">
        <h2 id="closeness-heading"><span className="visually-hidden">How close you are: </span>{state.name}</h2>
        <button type="button" className="text-button closeness-adjust" aria-expanded={adjusting} aria-controls="closeness-adjust" onClick={() => setAdjusting(!adjusting)}>Adjust</button>
      </div>
      <span className="row-sub closeness-basis">{shortBasis(state)}<InfoTip id="closeness-counting" label="How it is counted" text={`${basisText(state)} ${COUNTING(name)}`} /></span>
      <Meter state={state} />
      <p className="closeness-description">{OPENNESS[state.level - 1]}</p>
      {stageSteered(state) && <p className="row-sub">{stageText(state, name)}</p>}
      {adjusting && <ClosenessRows id="closeness-adjust" name={name} state={state} change={change}>
        <NicknameRow name={name} state={state} change={change} />
        <StartOverRow name={name} state={state} change={change} />
      </ClosenessRows>}
      {state.history.length > 0 && (
        <details className="closeness-history">
          <summary>When it changed</summary>
          <ul>{state.history.map((milestone) => <li key={milestone.level}>{milestoneText(milestone, state.stages)}</li>)}</ul>
        </details>
      )}
      <RowGroup><RunningJokes name={name} state={state} memories={memories} change={change} /></RowGroup>
    </section>
  )
}

/** Five steps, lit up to where you are, with the stage names under them; each step says its stage on hover. */
function Meter({ state }: { state: ClosenessState }) {
  return (
    <ol className="closeness-meter" aria-label="Closeness stages">
      {state.stages.map((stage, index) => (
        <li key={stage} className={index < state.level ? 'on' : undefined} aria-current={index + 1 === state.level ? 'step' : undefined} title={`${stage}: ${OPENNESS[index]}`}>
          <span className="closeness-bar" aria-hidden="true" /><span className="closeness-step">{stage}</span>
        </li>
      ))}
    </ol>
  )
}

interface ClosenessRowsProps { id?: string; name: string; state: ClosenessState; change: Change; path?: string; children?: ReactNode }

/**
 * Closeness as rows: the stage with a step back and a step closer, Never closer than, Hold at this stage and cooling.
 * Memories > Adjust adds the nickname and Start over; Settings > Realism shows the same rows for any companion (`path`
 * names which), so the two can't drift apart (Iris).
 */
export function ClosenessRows({ id, name, state, change, path = '/closeness', children }: ClosenessRowsProps) {
  const put = (body: object) => () => api<ClosenessState>(path, body, 'PUT')
  const setTo = (level: number) => void change(put({ set_level: level }), `${name} is at ${state.stages[level - 1]} now, and it grows from there.`)
  const cap = (value: string) => {
    const level = value ? Number(value) : null
    void change(put({ ceiling_level: level }), level ? `${name} won't get closer than ${state.stages[level - 1]}.` : 'Closeness can grow all the way again.')
  }
  const hold = (on: boolean) => void change(put({ held_level: on ? state.level : null }),
    on ? `${name} stays at ${state.name} until you change it.` : 'Closeness grows from your shared history again.')
  const cool = (on: boolean) => void change(put({ cooling: on }), on ? 'Long silences now cool things a little.' : 'Time apart no longer lowers closeness.')
  const stage = state.held_level ?? state.grown_level
  return (
    <div id={id} className="row-list closeness-rows">
      <SettingRow label="Stage" tip="It keeps growing from the stage you pick, unless you hold it.">
        {(id) => <span className="stepper" id={id} role="group" aria-label="Stage">
          <button type="button" className="icon-button" aria-label="One step back" disabled={stage <= 1} onClick={() => setTo(stage - 1)}><ChevronLeft aria-hidden="true" /></button>
          <span className="stepper-value" aria-live="polite">{state.stages[stage - 1]}</span>
          <button type="button" className="icon-button" aria-label="One step closer" disabled={stage >= state.stages.length} onClick={() => setTo(stage + 1)}><ChevronRight aria-hidden="true" /></button>
        </span>}
      </SettingRow>
      <SettingRow label="Never closer than" tip="Grows as usual up to this stage, then stops. Good for a slow burn.">
        {(id) => (
          <select id={id} value={state.ceiling_level ?? ''} onChange={(event) => cap(event.target.value)}>
            <option value="">No limit</option>
            {state.stages.map((item, index) => <option key={item} value={index + 1}>{item}</option>)}
          </select>
        )}
      </SettingRow>
      <SwitchRow label="Hold at this stage" checked={state.held_level !== null} onChange={hold} tip="Stays put, higher or lower, until you let it grow again." />
      <SwitchRow label="Long silences cool things" checked={state.cooling} onChange={cool}
        tip={`After 3 weeks without talking, ${name} is a step less familiar, after 2 months two steps, never below ${state.stages[1]}. Every 2 days you talk again bring a step back.`} />
      {children}
    </div>
  )
}

/** The nickname you are happy with, saved when you leave the box or press Enter. */
function NicknameRow({ name, state, change }: { name: string; state: ClosenessState; change: Change }) {
  const [nickname, setNickname] = useState(state.nickname)
  const save = () => {
    if (nickname.trim() === state.nickname.trim()) return
    void change(() => api('/closeness', { nickname }, 'PUT'),
      nickname.trim() ? `${name} may call you “${nickname.trim()}”.` : `${name} won't use a nickname you chose.`)
  }
  return (
    <SettingRow label="Nickname" tip={`A nickname you are happy with. Leave it empty and ${name} won't use a pet name before you are comfortable with each other.`}>
      {(id) => <input id={id} value={nickname} maxLength={40} autoComplete="off" placeholder="None" onChange={(event) => setNickname(event.target.value)} onBlur={save}
        onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); save() } }} />}
    </SettingRow>
  )
}

function StartOverRow({ name, state, change }: { name: string; state: ClosenessState; change: Change }) {
  const [confirming, setConfirming] = useState(false)
  const reset = () => {
    setConfirming(false)
    void change(() => api('/closeness/reset', {}), `Closeness starts again from today. ${name} is back to ${state.stages[0]}.`)
  }
  return (
    <div className="setting-row">
      <button type="button" className="text-button danger" onClick={() => setConfirming(true)}><RotateCcw aria-hidden="true" />Start closeness over</button>
      {confirming && (
        <ConfirmDialog title="Start closeness over?" onClose={() => setConfirming(false)} actions={<>
          <button type="button" className="button" onClick={() => setConfirming(false)}>Cancel</button>
          <button type="button" className="button danger" onClick={reset}>Start over</button>
        </>}>
          <p>{name} goes back to {state.stages[0]} and only days and shared moments from now on count. A kept or set stage and running jokes are cleared. Your messages, memories, nickname, limit and cooling choice are kept.</p>
        </ConfirmDialog>
      )}
    </div>
  )
}

export type Change = (action: () => Promise<ClosenessState>, done: string) => Promise<void>

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
    <FoldRow summary="Running jokes" value={state.jokes.length ? String(state.jokes.length) : 'None yet'}>
    <div className="fold-extra closeness-jokes">
      <p className="fold-about">Shared moments they bring back <InfoTip id="jokes-about" label="Running jokes" text={`Shared moments ${name} may bring back now and then. A moment that keeps coming up becomes one on its own; remove any you would rather they let go.`} /></p>
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
    </FoldRow>
  )
}
