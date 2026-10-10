import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { ChatList, Closeness as ClosenessState } from '../../types'
import { CHATS_KEY } from '../chats/useChats'
import { CLOSENESS_KEY } from '../memories/closenessText'
import { StageControls } from '../memories/Closeness'
import { DRAMA_LEVELS } from '../today/storyText'
import { Notice } from '../../components/Feedback'
import { Field, TextInput, Toggle } from '../../components/Fields'
import { ErrorNotice } from '../../components/ErrorNotice'
import { SectionPending } from '../../components/SectionPending'
import { useLifeSettings, type SaveResult } from './useLifeSettings'

/** The opening line of Settings > Realism (Iris's wording). */
export function RealismIntro() {
  return (
    <p className="subtle settings-intro">How true to life the world is. Everything here can be changed back any time.</p>
  )
}

/** How much drama, their pace and plans that go off course: world-wide settings, so they come first. */
export function PaceSettings() {
  const { settings, data, save, result } = useLifeSettings()
  if (!data) return <SectionPending queries={[settings]} heading="pace-heading" title="Their days" />
  const level = DRAMA_LEVELS[data.drama] ?? DRAMA_LEVELS[1]
  return (
    <section className="settings-section form-stack" aria-labelledby="pace-heading">
      <h2 id="pace-heading">Their days</h2>
      <Field label={`Drama in your world: ${level.label}`} hint={level.hint}>
        {(id, describedBy) => <input id={id} type="range" min={0} max={3} step={1} value={data.drama} aria-valuetext={level.label} aria-describedby={describedBy}
          onChange={(event) => void save({ drama: Number(event.target.value) })} />}
      </Field>
      <Toggle label="Reply at their own pace" checked={data.paced_replies} onChange={(value) => void save({ paced_replies: value })}
        hint={`When a companion is busy they decide how to answer: later, a quick holding text first, or a short note now. Asleep, they answer when they wake. In group chats, each reply shows after the time it would take to read and type it, one after another. Turn off for replies right away.`} />
      <Toggle label="Let their days go off plan" checked={data.day_shifts} onChange={(value) => void save({ day_shifts: value })}
        hint={`Now and then they run late, stay late, have plans fall through, have something come up or get a surprise visit. Rolled with fixed dice, so a day never changes after the fact. Off: every day goes as planned.`} />
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
    </section>
  )
}

/**
 * Closeness for any companion, picked from a list that starts on the open one (picking never changes the open chat):
 * Set it to, Never closer than, steps, Keep it at and gentle cooling. Nickname, running jokes and Start over stay
 * with the stages in Memories.
 */
export function ClosenessSettings({ name }: { name: string }) {
  const chats = useQuery({ queryKey: CHATS_KEY, queryFn: () => api<ChatList>('/chats') })
  const companions = (chats.data?.chats ?? []).filter((chat) => chat.kind === 'companion')
  const [picked, setPicked] = useState('')
  const [filter, setFilter] = useState('')
  const chosen = companions.find((chat) => chat.id === picked) ?? companions.find((chat) => chat.focus) ?? companions[0]
  const words = filter.trim().toLowerCase()
  const shown = companions.filter((chat) => chat.id === chosen?.id || chat.name.toLowerCase().includes(words))
  return (
    <section className="settings-section form-stack" aria-labelledby="closeness-settings-heading">
      <div>
        <h2 id="closeness-settings-heading">Closeness</h2>
        <p className="subtle">Closeness grows from the days you talk and the moments you keep. Skip ahead, hold it still or put a limit on it. It only changes how they talk with you.</p>
      </div>
      {companions.length > SEARCH_FROM && (
        <TextInput label="Find a companion" value={filter} onChange={setFilter} maxLength={60} type="search" />
      )}
      {companions.length > 1 && (
        <Field label="Companion" hint="Shows their closeness here. Your open chat stays as it is.">{(id, describedBy) => (
          <select id={id} aria-describedby={describedBy} value={chosen?.id ?? ''} onChange={(event) => setPicked(event.target.value)}>
            {shown.map((chat) => <option key={chat.id} value={chat.id}>{chat.name}</option>)}
          </select>
        )}</Field>
      )}
      {chosen ? <CompanionCloseness key={chosen.id} id={chosen.id} name={chosen.name} open={chosen.focus} /> : <CompanionCloseness id="" name={name} open />}
    </section>
  )
}

/** More companions than this and the picker gets a search box (100+ companions are supported). */
const SEARCH_FROM = 8

function CompanionCloseness({ id, name, open }: { id: string; name: string; open: boolean }) {
  const client = useQueryClient()
  const path = id ? `/closeness?companion=${encodeURIComponent(id)}` : '/closeness'
  const key = [...CLOSENESS_KEY, id]
  const closeness = useQuery({ queryKey: key, queryFn: () => api<ClosenessState>(path) })
  const [result, setResult] = useState<SaveResult>(null)
  const change = async (action: () => Promise<ClosenessState>, done: string) => {
    try {
      client.setQueryData(key, await action())
      setResult({ tone: 'info', text: done })
    } catch (error) {
      setResult({ tone: 'error', text: error instanceof Error ? error.message : 'Not saved.' })
    }
    // Memories shows the open companion's stages from its own copy.
    void client.invalidateQueries({ queryKey: CLOSENESS_KEY, exact: true })
  }
  if (closeness.isError) return <ErrorNotice error={closeness.error} />
  if (!closeness.data) return null
  return (
    <div className="form-stack">
      <p>{stageLine(closeness.data, name)}</p>
      <div className="closeness-controls"><StageControls name={name} state={closeness.data} change={change} path={path} /></div>
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
      {open
        ? <p className="subtle">Nickname, running jokes and starting over are in <a href="#memories">{name}&apos;s Memories</a>.</p>
        : <p className="subtle">Nickname, running jokes and starting over are in {name}&apos;s Memories, once their chat is open.</p>}
    </div>
  )
}

/** "Mira is at Friends.", saying so when the user set or keeps it there. */
export function stageLine(state: ClosenessState, name: string) {
  const how = state.held_level ? ', kept there by you' : state.set_on ? ', set by you' : ''
  return `${name} is at ${state.name}${how}.`
}
