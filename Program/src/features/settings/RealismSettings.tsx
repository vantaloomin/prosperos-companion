import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { SETTINGS_KEY, useWorkspaceSettings } from '../../companion'
import type { ChatList, Closeness as ClosenessState, WorkspaceSettings } from '../../types'
import { CHATS_KEY } from '../chats/useChats'
import { CLOSENESS_KEY } from '../memories/closenessText'
import { StageControls } from '../memories/Closeness'
import { DRAMA_LEVELS } from '../today/storyText'
import { LOOKS_LEVELS } from '../character/looksLatelyText'
import { KITCHEN_LEVELS } from '../character/kitchenText'
import { Notice } from '../../components/Feedback'
import { Field, TextInput, Toggle } from '../../components/Fields'
import { ErrorNotice } from '../../components/ErrorNotice'
import { SectionPending } from '../../components/SectionPending'
import { useLifeSettings, type SaveResult } from './useLifeSettings'
import { RealismPresets } from './RealismPresets'

/** Life admin (companion/life/admin.py) on the home features' shared scale: how much of the boring stuff fills their weeks. */
const ADMIN_LEVELS = [
  { label: 'Off', hint: 'No appointments, errands or paperwork of their own.' },
  { label: 'Light', hint: 'Only what comes due: the dentist, taxes, the lease. Nothing gets put off, no surprise bills, and anything moves for plans with you.' },
  { label: 'True to life', hint: 'What comes due, plus an errand or some paperwork most weeks. Now and then a chore gets put off, never past its deadline. The dentist and the vet keep their time; you can still move them.' },
  { label: 'Dramatic', hint: 'Errands and paperwork every week, and surprises like a parking ticket or a bank mix-up to sort out. Anything due that day holds too.' },
]

/** The top of Settings > Realism: Iris's opening line and one-tap presets for the world-wide settings below. */
export function RealismIntro() {
  return (
    <>
      <p className="subtle settings-intro">How true to life the world is. Everything here can be changed back any time.</p>
      <RealismPresets heading="presets-heading" title="Start from" />
    </>
  )
}

/** How much drama, their pace and plans that go off course: world-wide settings, so they come first. */
export function PaceSettings() {
  const { settings, data, save, result } = useLifeSettings()
  if (!data) return <SectionPending queries={[settings]} heading="pace-heading" title="Their days" />
  const level = DRAMA_LEVELS[data.drama] ?? DRAMA_LEVELS[1]
  const looks = LOOKS_LEVELS[data.looks_realism] ?? LOOKS_LEVELS[2]
  return (
    <section className="settings-section form-stack" aria-labelledby="pace-heading">
      <h2 id="pace-heading">Their days</h2>
      <Field label={`Drama in your world: ${level.label}`} hint={level.hint}>
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.drama} label={level.label}
          onChange={(drama) => void save({ drama })} />}
      </Field>
      <Field label={`Their looks change: ${looks.label}`} hint={looks.hint} tip="Only looks the app picked change. Anything you wrote about how someone looks stays exactly as you wrote it.">
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.looks_realism} label={looks.label}
          onChange={(looks_realism) => void save({ looks_realism })} />}
      </Field>
      <Toggle label="Reply at their own pace" checked={data.paced_replies} onChange={(value) => void save({ paced_replies: value })}
        hint={`When a companion is busy they decide how to answer: later, a quick holding text first, or a short note now. Asleep, they answer when they wake. In group chats, each reply shows after the time it would take to read and type it, one after another. Turn off for replies right away.`} />
      <Toggle label="Let their days go off plan" checked={data.day_shifts} onChange={(value) => void save({ day_shifts: value })}
        hint={`Now and then they run late, stay late, have plans fall through, have something come up or get a surprise visit. Rolled with fixed dice, so a day never changes after the fact. Off: every day goes as planned.`} />
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
    </section>
  )
}

/** Around the home: one slider for each home feature (Vanta, 2026-10-13), each its own life setting. */
export function HomeLifeSettings() {
  const { settings, data, save, result } = useLifeSettings()
  if (!data) return <SectionPending queries={[settings]} heading="home-life-heading" title="Around the home" />
  const upkeep = UPKEEP_LEVELS[data.upkeep_realism] ?? UPKEEP_LEVELS[2]
  const kitchen = KITCHEN_LEVELS[data.kitchen_realism] ?? KITCHEN_LEVELS[2]
  const pets = PET_LEVELS[data.pets_realism] ?? PET_LEVELS[2]
  const admin = ADMIN_LEVELS[data.admin_realism] ?? ADMIN_LEVELS[2]
  return (
    <section className="settings-section form-stack" aria-labelledby="home-life-heading">
      <div>
        <h2 id="home-life-heading">Around the home</h2>
        <p className="subtle">How much everyday life happens at home. Past days stay as they were; changes apply from today.</p>
      </div>
      <Field label={`Housework: ${upkeep.label}`} hint={upkeep.hint}>
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.upkeep_realism} label={upkeep.label}
          onChange={(upkeep_realism) => void save({ upkeep_realism })} />}
      </Field>
      <Field label={`Kitchen: ${kitchen.label}`} hint={kitchen.hint}>
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.kitchen_realism} label={kitchen.label}
          onChange={(kitchen_realism) => void save({ kitchen_realism })} />}
      </Field>
      <Field label={`Pets: ${pets.label}`} hint={pets.hint}>
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.pets_realism} label={pets.label}
          onChange={(pets_realism) => void save({ pets_realism })} />}
      </Field>
      <Toggle label="Pets can die" checked={data.pets_can_die} disabled={data.pets_realism === 0} onChange={(value) => void save({ pets_can_die: value })}
        hint="Rarely, and only late in life: of old age, or a serious illness when they are very old. Off: pets still grow old but are always there. A pet that died can be brought back on the Character page." />
      <Field label={`Life admin: ${admin.label}`} hint={admin.hint}>
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.admin_realism} label={admin.label}
          onChange={(admin_realism) => void save({ admin_realism })} />}
      </Field>
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
    </section>
  )
}

/** A four-step Realism slider (0 to 3) in the accent colour, with a tick at each step and the step's name read out. */
function StepSlider({ id, describedBy, value, label, onChange }: { id: string; describedBy?: string; value: number; label: string; onChange: (value: number) => void }) {
  return <>
    <input id={id} className="step-slider" type="range" list={`${id}-steps`} min={0} max={3} step={1} value={value} aria-valuetext={label}
      aria-describedby={describedBy} onChange={(event) => onChange(Number(event.target.value))} />
    <datalist id={`${id}-steps`}>{[0, 1, 2, 3].map((step) => <option key={step} value={step} />)}</datalist>
  </>
}

/** The Housework slider's steps (companion/life/upkeep.py SCALE). */
const UPKEEP_LEVELS = [
  { label: 'Off', hint: 'Laundry, dishes and clutter never come up. Their place stays as it is.' },
  { label: 'Light', hint: 'Mess builds slowly and they deal with it early. A tidy, easy home.' },
  { label: 'True to life', hint: 'Laundry, dishes and clutter build up with their week, and they catch up the way their habit says, with a big clean on a day off.' },
  { label: 'Messy', hint: 'More mess, piling up longer, and big cleans that wait until the place is a real state.' },
]

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
function stageLine(state: ClosenessState, name: string) {
  const how = state.held_level ? ', kept there by you' : state.set_on ? ', set by you' : ''
  return `${name} is at ${state.name}${how}.`
}

/** The adult side of life (companion/world/intimacy.py): off until turned on, adults only, private to each person. */
export function AdultSideSettings() {
  const client = useQueryClient()
  const settings = useWorkspaceSettings()
  const [error, setError] = useState('')
  const save = async (adult_side: boolean) => {
    setError('')
    try {
      client.setQueryData(SETTINGS_KEY, await api<WorkspaceSettings>('/settings', { adult_side }, 'PUT'))
      void client.invalidateQueries({ queryKey: ['townsfolk'] })
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'That setting was not saved.') }
  }
  return (
    <section className="settings-section form-stack" aria-labelledby="adult-side-heading">
      <div>
        <h2 id="adult-side-heading">Adult side of life</h2>
        <p className="subtle">Real people have a love life and desires of their own. Off until you turn it on.</p>
      </div>
      <Toggle label="Give adults an adult side" checked={settings.data?.adult_side === true} disabled={!settings.data} onChange={(checked) => void save(checked)}
        hint="Every adult townsperson and companion gets who they're drawn to, how adventurous they are, their drive and a few things they're into, rolled by the app. Adults only: nobody under 18 ever gets one. It stays private to each person and only shapes them when romance or intimacy comes up. It never goes into pictures, the town paper or the feed."
        tip="Change a companion's on their Character page, under Life details. Hidden values can show what townsfolk are like this way." />
      {error && <Notice tone="error">{error}</Notice>}
    </section>
  )
}

/** How much happens to pets (companion/life/pets.py), from nothing at all to a dramatic life. */
const PET_LEVELS = [
  { label: 'Off', hint: 'Pets stay well: no off days, vet visits or losses.' },
  { label: 'Light', hint: 'Now and then a pet has an off day or a checkup. Short spells, small bills.' },
  { label: 'True to life', hint: 'Off days, vet visits and checkups about as often as real pets have them, more as they grow old.' },
  { label: 'Dramatic', hint: 'More illnesses, longer spells and bigger vet bills.' },
]
