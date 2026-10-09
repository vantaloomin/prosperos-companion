import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Globe, Plus, Trash2, UserRoundPlus } from 'lucide-react'
import { api } from '../../api'
import type { Persona, World, Worlds as WorldsData } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { PersonaForm } from './PersonaForm'
import { enter, useWorlds, WORLDS_KEY } from './useWorlds'
import { companionsLine, initial, personaName } from './worldsText'

type Run = (action: () => Promise<unknown>) => Promise<void>

/** Worlds and personas: who the user is, the worlds each persona lives in, and switching between them. */
export function Worlds() {
  const worlds = useWorlds()
  const client = useQueryClient()
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const run: Run = async (action) => {
    if (busy) return
    setError('')
    try { await action() } catch (failure) { setError(failure instanceof Error ? failure.message : 'That did not work. Try again.') } finally { setBusy('') }
  }
  const switchTo = (path: string, label: string) => { setBusy(label); return run(async () => { await api(path, {}); enter() }) }
  const store = (data: WorldsData) => client.setQueryData(WORLDS_KEY, data)
  if (worlds.isPending) return <Loading label="Loading your worlds" />
  if (worlds.isError) return <ErrorNotice error={worlds.error} />
  const data = worlds.data
  return (
    <section className="worlds" aria-labelledby="worlds-heading">
      <header className="worlds-header">
        <h1 id="worlds-heading">Worlds</h1>
        <p className="subtle">You are <strong>{personaName(data.persona)}</strong> in <strong>{data.world.name}</strong>. Each persona lives in their own worlds, with their own companions, town and history. Your settings and models come with you everywhere.</p>
        {busy && <Notice>Opening {busy}…</Notice>}
        {error && <Notice tone="error">{error}</Notice>}
      </header>
      <div className="worlds-list">
        {data.personas.map((persona) => (
          <PersonaWorlds key={persona.id} persona={persona} run={run} store={store}
            onSwitch={(world) => void switchTo(`/worlds/${world.id}/switch`, world.name)}
            onSwitchPersona={() => void switchTo(`/worlds/personas/${persona.id}/switch`, personaName(persona))} />
        ))}
        <div className="form-actions">
          <button type="button" className="button" aria-disabled={!!busy} onClick={() => void run(async () => {
            await api('/worlds/personas', {})
            await client.invalidateQueries({ queryKey: WORLDS_KEY })
          })}><UserRoundPlus aria-hidden="true" />New persona</button>
        </div>
        <p className="subtle small">A new persona gets a world of their own right away, in this city with new people in it and a first companion to meet. Change anything about them afterwards.</p>
        <PersonaForm key={data.persona.id} persona={data.persona} onSaved={store} />
      </div>
    </section>
  )
}

interface PersonaWorldsProps { persona: Persona; run: Run; store: (data: WorldsData) => void; onSwitch: (world: World) => void; onSwitchPersona: () => void }

function PersonaWorlds({ persona, run, store, onSwitch, onSwitchPersona }: PersonaWorldsProps) {
  const client = useQueryClient()
  const [deleting, setDeleting] = useState(false)
  const removable = !persona.active && persona.worlds.every((world) => !world.first)
  return (
    <section className="persona-worlds" aria-label={personaName(persona)}>
      <div className="persona-row">
        <span className="portrait persona-initial" aria-hidden="true">{initial(persona)}</span>
        <h2>{personaName(persona)}{persona.active && <span className="subtle"> (you, now)</span>}</h2>
        {!persona.active && <button type="button" className="button" onClick={onSwitchPersona}>Be {personaName(persona)}</button>}
        {removable && <button type="button" className="text-button" onClick={() => setDeleting(true)}><Trash2 aria-hidden="true" />Delete</button>}
      </div>
      <ul className="world-rows">
        {persona.worlds.map((world) => <WorldRow key={world.id} world={world} run={run} store={store} onSwitch={() => onSwitch(world)} />)}
      </ul>
      <button type="button" className="text-button" onClick={() => void run(async () => {
        await api('/worlds', { persona_id: persona.id })
        await client.invalidateQueries({ queryKey: WORLDS_KEY })
      })}><Plus aria-hidden="true" />New world for {personaName(persona)}</button>
      {deleting && <ConfirmDialog title={`Delete ${personaName(persona)}?`} onClose={() => setDeleting(false)} actions={<>
        <button type="button" className="button" onClick={() => setDeleting(false)}>Keep</button>
        <button type="button" className="button danger" onClick={() => void run(async () => { store(await api<WorldsData>(`/worlds/personas/${persona.id}`, undefined, 'DELETE')); setDeleting(false) })}>Delete</button>
      </>}>
        <p>Their {persona.worlds.length === 1 ? 'world goes' : `${persona.worlds.length} worlds go`} with them, with every companion and chat in it. A backup of each is kept in the data folder, under backups/deleted-worlds.</p>
      </ConfirmDialog>}
    </section>
  )
}

function WorldRow({ world, run, store, onSwitch }: { world: World; run: Run; store: (data: WorldsData) => void; onSwitch: () => void }) {
  const [renaming, setRenaming] = useState(false)
  const [name, setName] = useState(world.name)
  const [deleting, setDeleting] = useState(false)
  const rename = () => run(async () => { store(await api<WorldsData>(`/worlds/${world.id}`, { name }, 'PATCH')); setRenaming(false) })
  return (
    <li className="world-row" aria-current={world.active ? 'true' : undefined}>
      <span className="portrait" aria-hidden="true"><Globe /></span>
      {renaming
        ? <form className="world-rename" onSubmit={(event) => { event.preventDefault(); void rename() }}>
            <label className="visually-hidden" htmlFor={`world-name-${world.id}`}>World name</label>
            <input id={`world-name-${world.id}`} value={name} maxLength={80} required onChange={(event) => setName(event.target.value)} />
            <button type="submit" className="button">Save</button>
            <button type="button" className="text-button" onClick={() => { setRenaming(false); setName(world.name) }}>Cancel</button>
          </form>
        : <span className="world-row-text"><strong>{world.name}</strong><span className="subtle">{companionsLine(world)}</span></span>}
      <span className="world-row-actions">
        {world.active ? <span className="subtle">You are here</span> : <button type="button" className="button" onClick={onSwitch}>Go there</button>}
        {!renaming && <button type="button" className="text-button" onClick={() => setRenaming(true)}>Rename</button>}
        {!world.active && !world.first && <button type="button" className="text-button" aria-label={`Delete ${world.name}`} onClick={() => setDeleting(true)}><Trash2 aria-hidden="true" /></button>}
      </span>
      {deleting && <ConfirmDialog title={`Delete ${world.name}?`} onClose={() => setDeleting(false)} actions={<>
        <button type="button" className="button" onClick={() => setDeleting(false)}>Keep it</button>
        <button type="button" className="button danger" onClick={() => void run(async () => { store(await api<WorldsData>(`/worlds/${world.id}`, undefined, 'DELETE')); setDeleting(false) })}>Delete</button>
      </>}>
        <p>{companionsLine(world)} and everything that happened there go with it. A backup is kept in the data folder, under backups/deleted-worlds.</p>
      </ConfirmDialog>}
    </li>
  )
}
