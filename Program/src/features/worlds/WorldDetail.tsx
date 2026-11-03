import { useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Copy, History, MoreHorizontal, Pause, Pencil, Play, Trash2 } from 'lucide-react'
import { api } from '../../api'
import type { Persona, World, Worlds as WorldsData } from '../../types'
import { Notice } from '../../components/Feedback'
import { InfoTip } from '../../components/InfoTip'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Menu, type MenuEntry } from '../../components/Menu'
import { RowGroup, SwitchRow } from '../../components/Rows'
import { PersonaForm } from './PersonaForm'
import { companionsLine, copyLabel, pausedNote, personaName, personaRef, yearBadge } from './worldsText'
import { useWatchActions } from '../watch/useObserver'
import type { Run } from './WorldForms'

interface WorldDetailProps {
  world: World; persona: Persona; data: WorldsData; run: Run; store: (data: WorldsData) => void
  onSwitch: () => void; onCopy: () => void; onGone: () => void
}

type Asking = '' | 'world' | 'persona'

/** The world picked in the list: its name with ⋯, how it stands, Go there or Just watch, and who you are there. */
export function WorldDetail({ world, persona, data, run, store, onSwitch, onCopy, onGone }: WorldDetailProps) {
  const [renaming, setRenaming] = useState(false)
  const head = useRef<HTMLDivElement>(null)
  // Saving or cancelling a rename puts focus back on ⋯, where Rename was (Iris).
  const doneRenaming = () => { setRenaming(false); requestAnimationFrame(() => head.current?.querySelector<HTMLButtonElement>('.menu-anchor > button')?.focus()) }
  const [asking, setAsking] = useState<Asking>('')
  const pause = usePause(world, run, store)
  const items = useWorldItems({ world, persona, onPause: pause, onRename: () => setRenaming(true), onCopy, onDelete: setAsking })
  const remove = (path: string) => run(async () => { store(await api<WorldsData>(path, undefined, 'DELETE')); setAsking(''); onGone() })
  return (
    <section className="world-detail" aria-labelledby="world-detail-heading">
      <div ref={head} className="world-detail-head">
        {renaming ? <RenameWorld world={world} run={run} store={store} onDone={doneRenaming} /> : <WorldTitle world={world} />}
        <Menu label="World actions" icon={MoreHorizontal} items={items} />
      </div>
      <WorldLines world={world} />
      {world.paused && <Notice action={<button type="button" className="text-button" onClick={() => void pause(false)}><Play aria-hidden="true" />Resume</button>}>{pausedNote(world, new Date())}</Notice>}
      {world.active ? <ActiveWorld world={world} run={run} /> : <div className="form-actions"><span className="label-row">
        <button type="button" className="button primary" onClick={onSwitch}>{goLabel(persona)}</button>
        <InfoTip id={`go-there-${world.id}`} label={goLabel(persona)} text={`You are ${personaRef(persona)} there. Who you are is set from inside the world.`} />
      </span></div>}
      {world.active && <div id="persona-edit"><PersonaForm key={`${data.persona.id}:${data.world.id}`} persona={data.persona} world={data.world} cityId={data.world.city_id} onSaved={(saved) => { if (saved) store(saved) }} /></div>}
      {asking === 'world' && <ConfirmDialog title={`Delete ${world.name}?`} onClose={() => setAsking('')} actions={<>
        <button type="button" className="button" onClick={() => setAsking('')}>Keep it</button>
        <button type="button" className="button danger" onClick={() => void remove(`/worlds/${world.id}`)}>Delete</button>
      </>}>
        <p>{companionsLine(world)} and everything that happened there go with it. A backup is kept in the data folder, under backups/deleted-worlds.</p>
      </ConfirmDialog>}
      {asking === 'persona' && <ConfirmDialog title={`Delete ${personaRef(persona)}?`} onClose={() => setAsking('')} actions={<>
        <button type="button" className="button" onClick={() => setAsking('')}>Keep</button>
        <button type="button" className="button danger" onClick={() => void remove(`/worlds/personas/${persona.id}`)}>Delete</button>
      </>}>
        <p>Their {persona.worlds.length === 1 ? 'world goes' : `${persona.worlds.length} worlds go`} with them, with every companion and chat in it. A backup of each is kept in the data folder, under backups/deleted-worlds.</p>
      </ConfirmDialog>}
    </section>
  )
}

/** Going to a world of another persona makes you them there. */
function goLabel(persona: Persona): string {
  const name = personaName(persona)
  return persona.active || !name ? 'Go there' : `Go there as ${name}`
}

/** Pause or resume this world, the one you are in or one you left (tester, 1.3.0); the world you are in refreshes
 * everything, since its settings and life read the pause too. */
function usePause(world: World, run: Run, store: (data: WorldsData) => void) {
  const client = useQueryClient()
  return (on: boolean) => run(async () => {
    store(await api<WorldsData>(`/worlds/${world.id}/${on ? 'pause' : 'resume'}`, {}))
    if (world.active) await client.invalidateQueries()
  })
}

interface ItemsArgs { world: World; persona: Persona; onPause: (on: boolean) => Promise<void>; onRename: () => void; onCopy: () => void; onDelete: (what: Asking) => void }

/** The world's ⋯: Rename, Copy you to a new world, Pause or Resume (any world), and Delete where allowed. */
function useWorldItems({ world, persona, onPause, onRename, onCopy, onDelete }: ItemsArgs): MenuEntry[] {
  const pause = (on: boolean) => void onPause(on)
  const items: MenuEntry[] = [
    { label: 'Rename', icon: Pencil, onSelect: onRename },
    { label: copyLabel(persona), icon: Copy, onSelect: onCopy },
  ]
  items.push(world.paused ? { label: 'Resume this world', icon: Play, onSelect: () => pause(false) } : { label: 'Pause this world', icon: Pause, onSelect: () => pause(true) })
  const deletes: MenuEntry[] = []
  if (!world.active && !world.first) deletes.push({ label: 'Delete this world', icon: Trash2, onSelect: () => onDelete('world') })
  if (!persona.active && persona.worlds.every((item) => !item.first)) deletes.push({ label: `Delete ${personaRef(persona)}`, icon: Trash2, onSelect: () => onDelete('persona') })
  return deletes.length ? [...items, 'separator', ...deletes] : items
}

function WorldTitle({ world }: { world: World }) {
  const badge = yearBadge(world)
  return (
    <h2 id="world-detail-heading" className="world-detail-name">
      {world.name}
      {badge && <span className="badge year-badge" title={badge.label}><History aria-hidden="true" /><span className="visually-hidden">{badge.label}</span><span aria-hidden="true">{badge.text}</span></span>}
      {world.paused && <span className="badge paused-badge"><Pause aria-hidden="true" />Paused</span>}
    </h2>
  )
}

/** Who lives there, and since you were last there and what going back does; a paused world says so in its notice. */
function WorldLines({ world }: { world: World }) {
  const note = world.paused ? null : pausedNote(world, new Date())
  return <>
    <p className="subtle">{companionsLine(world)}{world.watching ? ' · Just watching' : ''}</p>
    {note && <p className="subtle paused-note">{note}</p>}
  </>
}

function RenameWorld({ world, run, store, onDone }: { world: World; run: Run; store: (data: WorldsData) => void; onDone: () => void }) {
  const [name, setName] = useState(world.name)
  const rename = () => run(async () => { store(await api<WorldsData>(`/worlds/${world.id}`, { name }, 'PATCH')); onDone() })
  return (
    <form className="world-rename" onSubmit={(event) => { event.preventDefault(); void rename() }} onKeyDown={(event) => { if (event.key === 'Escape') onDone() }}>
      <label className="visually-hidden" htmlFor={`world-name-${world.id}`}>World name</label>
      <input autoComplete="off" autoFocus id={`world-name-${world.id}`} value={name} maxLength={80} required onChange={(event) => setName(event.target.value)} />
      <button type="submit" className="button">Save</button>
      <button type="button" className="text-button" onClick={onDone}>Cancel</button>
    </form>
  )
}

/** "Just watch" (companion/observer.py) for the world you are in: your persona sits out while everyone else's life
 * goes on, and the Watching page opens. */
function ActiveWorld({ world, run }: { world: World; run: Run }) {
  const { change } = useWatchActions()
  const toggle = (on: boolean) => run(async () => {
    await change({ watching: on })
    if (on) window.location.hash = '#watch'
  })
  return <>
    <RowGroup>
      <SwitchRow label="Just watch" tip="Sit back and watch this world go on without you. Nobody texts you or asks you along meanwhile. Writing to anyone steps you back in." checked={!!world.watching} onChange={(on) => void toggle(on)} />
    </RowGroup>
  </>
}
