import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Eye } from 'lucide-react'
import { api } from '../../api'
import type { Persona } from '../../types'
import { CityPick, SOMEWHERE_NEW } from './CityPick'
import { WORLDS_KEY } from './useWorlds'
import { copyLabel, copyNote, defaultPastYear, pastYears, personaRef } from './worldsText'
import { Field, Toggle } from '../../components/Fields'
import { InfoTip } from '../../components/InfoTip'

export type Run = (action: () => Promise<unknown>) => Promise<void>

/** Where the persona's new world is: somewhere new the app picks unless the user picks a city. */
export function NewWorld({ persona, cityId, run, onDone }: { persona: Persona; cityId: string; run: Run; onDone: () => void }) {
  const client = useQueryClient()
  const [city, setCity] = useState(SOMEWHERE_NEW)
  const [making, setMaking] = useState<'' | 'make' | 'watch'>('')
  const [year, setYear] = useState<number | null>(null)
  // "Watch a city": the new world starts just watching (companion/observer.py).
  const make = (watch = false) => { setMaking(watch ? 'watch' : 'make'); return run(async () => {
    await api('/worlds', { persona_id: persona.id, city_id: city, watch, year })
    await client.invalidateQueries({ queryKey: WORLDS_KEY })
    onDone()
  }).finally(() => setMaking('')) }
  return (
    <form className="new-world form-stack" aria-label={`New world for ${personaRef(persona)}`} onSubmit={(event) => { event.preventDefault(); void make() }}
      onKeyDown={(event) => { if (event.key === 'Escape' && !making) onDone() }}>
      <CityPick value={city} currentId={cityId} disabled={!!making} autoFocus onChange={setCity} />
      <PastYear year={year} disabled={!!making} onChange={setYear} />
      <div className="form-actions wrap">
        <button type="submit" className="button primary" disabled={!!making}>{making === 'make' ? 'Making the world…' : 'Make this world'}</button>
        <span className="label-row">
          <button type="button" className="button" disabled={!!making} onClick={() => void make(true)}><Eye aria-hidden="true" />{making === 'watch' ? 'Making the world…' : 'Watch a city'}</button>
          <InfoTip id={`watch-city-${persona.id}`} label="Watch a city" text="See the town go on without you, following whoever you like. Step in whenever you want." />
        </span>
        <button type="button" className="text-button" disabled={!!making} onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}

/** "Start in a past year" (companion/world_year.py): off, the world is in the present; on, the app offers ten years
 * back and the user can pick any year back to 1990. The clock runs in that year at real speed. */
function PastYear({ year, disabled, onChange }: { year: number | null; disabled: boolean; onChange: (year: number | null) => void }) {
  const thisYear = new Date().getFullYear()
  return (
    <div className="past-year form-stack">
      <Toggle label="Start in a past year" checked={year !== null} disabled={disabled} onChange={(on) => onChange(on ? defaultPastYear(thisYear) : null)}
        tip="Its calendar runs in that year at real speed, with the phones, prices, songs and jobs of the time." />
      {year !== null && <Field label="Year">
        {(id) => <select id={id} value={year} disabled={disabled} onChange={(event) => onChange(Number(event.target.value))}>
          {pastYears(thisYear).map((option) => <option key={option} value={option}>{option}</option>)}
        </select>}
      </Field>}
    </div>
  )
}

/** A separate copy of the persona, so the user need not type them again: a world of their own where they pick the
 * city (somewhere new unless they pick), with everything on the persona's form but where they live. */
export function CopyPersona({ persona, cityId, run, onDone, onCopied }: { persona: Persona; cityId: string; run: Run; onDone: () => void; onCopied: (id: string) => void }) {
  const client = useQueryClient()
  const [city, setCity] = useState(SOMEWHERE_NEW)
  const [making, setMaking] = useState(false)
  const make = () => { setMaking(true); return run(async () => {
    const copy = await api<Persona>(`/worlds/personas/${persona.id}/copy`, { city_id: city })
    await client.invalidateQueries({ queryKey: WORLDS_KEY })
    onCopied(copy.id)
  }).finally(() => setMaking(false)) }
  return (
    <form className="new-world form-stack" aria-label={copyLabel(persona)} onSubmit={(event) => { event.preventDefault(); void make() }}
      onKeyDown={(event) => { if (event.key === 'Escape' && !making) onDone() }}>
      <p className="subtle">{copyNote(persona)}</p>
      <CityPick value={city} currentId={cityId} disabled={making} autoFocus onChange={setCity} />
      <div className="form-actions wrap">
        <button type="submit" className="button primary" disabled={making}>{making ? 'Making the copy…' : 'Make the copy'}</button>
        <button type="button" className="text-button" disabled={making} onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}
