import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { ChatList, Closeness as ClosenessState } from '../../types'
import { CHATS_KEY } from '../chats/useChats'
import { CLOSENESS_KEY, stageText } from '../memories/closenessText'
import { StageControls } from '../memories/Closeness'
import { DRAMA_LEVELS } from '../today/storyText'
import { Notice } from '../../components/Feedback'
import { Field, Toggle } from '../../components/Fields'
import { ErrorNotice } from '../../components/ErrorNotice'
import { SectionPending } from '../../components/SectionPending'
import { useLifeSettings, type SaveResult } from './useLifeSettings'

/** The opening line of Settings > Realism: everything here is on the side of real life until you dial it down. */
export function RealismIntro() {
  return (
    <p className="subtle settings-intro">
      Everything here starts out the way real life works: people answer when they can, plans go wrong, closeness takes time and you learn how
      someone feels from how they talk. Turn any of it down or off for a world that bends your way.
    </p>
  )
}

/** Their pace, plans that go off course and how much drama: the life settings that make days feel unscripted. */
export function PaceSettings({ name }: { name: string }) {
  const { settings, data, save, result } = useLifeSettings()
  if (!data) return <SectionPending queries={[settings]} heading="pace-heading" title="Their pace and their days" />
  const level = DRAMA_LEVELS[data.drama] ?? DRAMA_LEVELS[1]
  return (
    <section className="settings-section form-stack" aria-labelledby="pace-heading">
      <h2 id="pace-heading">Their pace and their days</h2>
      <Toggle label={`Reply at ${name}'s pace`} checked={data.paced_replies} onChange={(value) => void save({ paced_replies: value })}
        hint={`When ${name} is busy they decide how to answer: later, a quick holding text first, or a short note now. Asleep, they answer when they wake. In group chats, each reply shows after the time it would take to read and type it, one after another. Turn off for replies right away.`} />
      <Toggle label={`Let ${name}'s days go off plan`} checked={data.day_shifts} onChange={(value) => void save({ day_shifts: value })}
        hint={`Now and then ${name} runs late, stays late, has plans fall through, has something come up or gets a surprise visit. Rolled with fixed dice, so a day never changes after the fact. Off: every day goes as planned.`} />
      <Field label={`Drama in ${name}'s world: ${level.label}`} hint={level.hint}>
        {(id, describedBy) => <input id={id} type="range" min={0} max={3} step={1} value={data.drama} aria-valuetext={level.label} aria-describedby={describedBy}
          onChange={(event) => void save({ drama: Number(event.target.value) })} />}
      </Field>
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
    </section>
  )
}

/**
 * Closeness for any companion, picked from a list that starts on the open one: steps, Set it to, Keep it at,
 * Never closer than and gentle cooling. Nickname, running jokes and Start over stay with the stages in Memories.
 */
export function ClosenessSettings({ name }: { name: string }) {
  const chats = useQuery({ queryKey: CHATS_KEY, queryFn: () => api<ChatList>('/chats') })
  const companions = (chats.data?.chats ?? []).filter((chat) => chat.kind === 'companion')
  const [picked, setPicked] = useState('')
  const chosen = companions.find((chat) => chat.id === picked) ?? companions.find((chat) => chat.focus) ?? companions[0]
  return (
    <section className="settings-section form-stack" aria-labelledby="closeness-settings-heading">
      <div>
        <h2 id="closeness-settings-heading">How close you get</h2>
        <p className="subtle">Closeness grows from the days you talk and the moments you keep. Skip ahead, hold it still or put a limit on it. It only changes how they talk with you.</p>
      </div>
      {companions.length > 1 && (
        <Field label="Companion">{(id, describedBy) => (
          <select id={id} aria-describedby={describedBy} value={chosen?.id ?? ''} onChange={(event) => setPicked(event.target.value)}>
            {companions.map((chat) => <option key={chat.id} value={chat.id}>{chat.name}</option>)}
          </select>
        )}</Field>
      )}
      {chosen ? <CompanionCloseness key={chosen.id} id={chosen.id} name={chosen.name} /> : <CompanionCloseness id="" name={name} />}
      <p className="subtle">A nickname, running jokes and starting over are with the stages in Memories.</p>
    </section>
  )
}

function CompanionCloseness({ id, name }: { id: string; name: string }) {
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
    <div className="closeness-controls">
      <p>{stageText(closeness.data, name)}</p>
      <StageControls name={name} state={closeness.data} change={change} path={path} />
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
    </div>
  )
}
