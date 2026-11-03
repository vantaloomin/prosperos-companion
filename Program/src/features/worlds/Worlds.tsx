import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Check, Globe, Plus, UserRoundPlus } from 'lucide-react'
import { api } from '../../api'
import type { Persona, World, Worlds as WorldsData } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { PersonaForm } from './PersonaForm'
import { CopyPersona, NewWorld, type Run } from './WorldForms'
import { WorldDetail } from './WorldDetail'
import { enter, useWorlds, WORLDS_KEY } from './useWorlds'
import { companionsLine, copyLabel, personaName, personaRef, personaTitle, worldTag } from './worldsText'

/** What the detail side shows: the world picked in the list, a new persona, or a new world or copy for a persona. */
type Pane = { kind: 'world'; id: string } | { kind: 'persona' } | { kind: 'new-world' | 'copy'; persona: string }

/**
 * Worlds and personas (style guide: Worlds): on a wide screen a list of your worlds, grouped by who you are in them,
 * beside the world you picked, like Notes folders; on a phone the list, then the world. The check marks the world you
 * are in. Rename, copy and pause wait under the world's ⋯; who you are there is the form under it.
 */
export function Worlds() {
  const worlds = useWorlds()
  const client = useQueryClient()
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [pane, setPane] = useState<Pane | null>(null)
  // A copy just made (Iris): its group lights up briefly.
  const [arrived, setArrived] = useState('')
  const run: Run = async (action) => {
    if (busy) return
    setError('')
    try { await action() } catch (failure) { setError(failure instanceof Error ? failure.message : 'That did not work. Try again.') } finally { setBusy('') }
  }
  const switchTo = (path: string, label: string) => { setBusy(label); return run(async () => { await api(path, {}); enter() }) }
  const store = (data: WorldsData) => client.setQueryData(WORLDS_KEY, data)
  const loaded = !!worlds.data
  useEffect(() => { if (loaded && window.history.state?.focus === 'persona-home') toHomeCity() }, [loaded])
  if (worlds.isPending) return <Loading label="Loading your worlds" />
  if (worlds.isError) return <ErrorNotice error={worlds.error} />
  const data = worlds.data
  const shown = pane ?? { kind: 'world', id: data.world.id }
  const showWorld = (id: string) => setPane({ kind: 'world', id })
  const copied = (id: string) => {
    setArrived(id)
    const copy = data.personas.find((persona) => persona.id === id)
    setPane(copy?.worlds[0] ? { kind: 'world', id: copy.worlds[0].id } : null)
  }
  return (
    <section className="worlds" aria-labelledby="worlds-heading">
      <div className="worlds-pane">
        <header className="worlds-pane-head">
          <h1 id="worlds-heading">Worlds</h1>
          <button type="button" className="icon-button" aria-label="New persona" title="New persona" aria-pressed={shown.kind === 'persona'} onClick={() => setPane({ kind: 'persona' })}><UserRoundPlus aria-hidden="true" /></button>
        </header>
        {data.personas.map((persona) => (
          <PersonaGroup key={persona.id} persona={persona} tag={worldTag(persona, data.personas)} pane={shown} arrived={arrived === persona.id}
            onPick={showWorld} onNewWorld={() => setPane({ kind: 'new-world', persona: persona.id })} />
        ))}
      </div>
      <div className="worlds-detail" aria-live="polite">
        {busy && <Notice>Opening {busy}…</Notice>}
        {error && <Notice tone="error">{error}</Notice>}
        <Detail pane={shown} data={data} run={run} store={store} switchTo={switchTo} onPane={setPane} onCopied={copied} />
      </div>
    </section>
  )
}

interface DetailProps {
  pane: Pane; data: WorldsData; run: Run; store: (data: WorldsData) => void
  switchTo: (path: string, label: string) => Promise<void>; onPane: (pane: Pane | null) => void; onCopied: (id: string) => void
}

/** The right side: the picked world with who you are there, or the form for something new. */
function Detail({ pane, data, run, store, switchTo, onPane, onCopied }: DetailProps) {
  const client = useQueryClient()
  const back = () => onPane(null)
  if (pane.kind === 'persona') {
    return <PersonaForm cityId={data.world.city_id} kinds={data.persona.kind_shown} onCancel={back} onSaved={() => { back(); void client.invalidateQueries({ queryKey: WORLDS_KEY }) }} />
  }
  const found = findWorld(data, pane.kind === 'world' ? pane.id : '')
  const persona = pane.kind === 'world' ? found?.persona : data.personas.find((item) => item.id === pane.persona)
  if (!persona) return null
  if (pane.kind === 'new-world') return <NewWorldPane title={`New world for ${personaRef(persona)}`}><NewWorld persona={persona} cityId={data.world.city_id} run={run} onDone={back} /></NewWorldPane>
  if (pane.kind === 'copy') return <NewWorldPane title={copyLabel(persona)}><CopyPersona persona={persona} cityId={data.world.city_id} run={run} onDone={back} onCopied={onCopied} /></NewWorldPane>
  const world = found?.world ?? data.world
  return <WorldDetail key={world.id} world={world} persona={persona} data={data} run={run} store={store}
    onSwitch={() => void switchTo(`/worlds/${world.id}/switch`, world.name)}
    onCopy={() => onPane({ kind: 'copy', persona: persona.id })} onGone={back} />
}

function NewWorldPane({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="worlds-new" aria-label={title}><h2>{title}</h2>{children}</section>
}

/** The world with this id and whose it is, or nothing once it is gone. */
function findWorld(data: WorldsData, id: string): { world: World; persona: Persona } | null {
  for (const persona of data.personas) {
    const world = persona.worlds.find((item) => item.id === id)
    if (world) return { world, persona }
  }
  return null
}

interface PersonaGroupProps { persona: Persona; tag: string; pane: Pane; arrived: boolean; onPick: (id: string) => void; onNewWorld: () => void }

/** One persona's worlds in the list: their name, each world (a check on the one you are in) and New world. */
function PersonaGroup({ persona, tag, pane, arrived, onPick, onNewWorld }: PersonaGroupProps) {
  const adding = pane.kind === 'new-world' && pane.persona === persona.id
  return (
    <section className={arrived ? 'worlds-group arrived' : 'worlds-group'} aria-label={tag ? `${personaTitle(persona)} (${tag})` : personaTitle(persona)}>
      <h2 className="worlds-group-label">{groupName(persona)}{tag && <span className="subtle"> ({tag})</span>}{persona.active && <Check className="world-here" aria-label="You, now" />}</h2>
      <ul>
        {persona.worlds.map((world) => (
          <li key={world.id}>
            <button type="button" className={pane.kind === 'world' && pane.id === world.id ? 'chat-row world-pick current' : 'chat-row world-pick'} aria-current={pane.kind === 'world' && pane.id === world.id ? 'true' : undefined} onClick={() => onPick(world.id)}>
              <span className="portrait" aria-hidden="true"><Globe /></span>
              <span className="chat-row-text"><strong>{world.name}</strong><span className="chat-row-preview">{companionsLine(world)}</span></span>
              {world.active && <Check className="world-here" aria-label="You are here" />}
            </button>
          </li>
        ))}
        <li>
          <button type="button" className={adding ? 'chat-row world-new current' : 'chat-row world-new'} onClick={onNewWorld}>
            <span className="portrait" aria-hidden="true"><Plus /></span><span className="chat-row-text">New world<span className="visually-hidden"> for {personaRef(persona)}</span></span>
          </button>
        </li>
      </ul>
    </section>
  )
}

/** A persona's name in the list, or "You" for the one you are now while it has none (Iris). */
function groupName(persona: Persona): string {
  return personaName(persona) || (persona.active ? 'You' : personaTitle(persona))
}

/** Where you live, on the persona form (opened from "Change your home city" on the Character page). */
function toHomeCity() {
  const field = document.querySelector<HTMLSelectElement>('#persona-edit .persona-home select')
  field?.scrollIntoView({ block: 'center' })
  field?.focus()
}
