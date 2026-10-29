import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { History } from 'lucide-react'
import { api } from '../../api'
import type { BackWhenMoments } from '../../types'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Field, Toggle } from '../../components/Fields'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { enter, useWorlds } from '../worlds/useWorlds'
import { backWhenNote, backWhenYears, firstPick, firstYear, HISTORY_HINT, momentLine, pickedYear, type BackWhenPick } from './backWhenText'

/** Back when (companion/back_when.py): go back to a year when the two of you were younger, in a new world the app
 * builds for it. Only from a world in the present, so a Back when world doesn't offer it again. */
export function BackWhen({ id, name }: { id: string; name: string }) {
  const world = useWorlds().data?.world
  const [open, setOpen] = useState(false)
  if (!world || world.year) return null
  return (
    <section className="settings-section form-stack" aria-labelledby="back-when-heading">
      <div>
        <h2 id="back-when-heading">Back when</h2>
        <p className="subtle">Go back to when you and {name} were younger: the year you met, before a big step, or any year back to 1990. Phones, prices and songs are from that year.</p>
      </div>
      <div className="form-actions">
        <button type="button" className="button" onClick={() => setOpen(true)}><History aria-hidden="true" />Back when…</button>
      </div>
      {open && <BackWhenSheet id={id} name={name} onClose={() => setOpen(false)} />}
    </section>
  )
}

function BackWhenSheet({ id, name, onClose }: { id: string; name: string; onClose: () => void }) {
  const moments = useQuery({ queryKey: ['back-when', id], queryFn: () => api<BackWhenMoments>(`/worlds/back-when?companion_id=${encodeURIComponent(id)}`), staleTime: 0 })
  const data = moments.data
  return (
    <ConfirmDialog title={`Back when with ${name}`} onClose={onClose} actions={data?.available ? null : <button type="button" className="button" onClick={onClose}>Close</button>}>
      {moments.isPending && <Loading label="Looking back" />}
      {moments.isError && <ErrorNotice error={moments.error} />}
      {data && !data.available && <p>{data.reason}</p>}
      {data?.available && <BackWhenChoice data={data} onClose={onClose} />}
    </ConfirmDialog>
  )
}

/** The app's moments with one picked, a year of the user's own, and "Work it out from our history", off. */
function BackWhenChoice({ data, onClose }: { data: BackWhenMoments; onClose: () => void }) {
  const [pick, setPick] = useState<BackWhenPick>(() => firstPick(data))
  const [year, setYear] = useState(() => firstYear(data))
  const [fromHistory, setFromHistory] = useState(data.from_history)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const chosen = pickedYear(data, pick, year)
  const go = async () => {
    if (busy) return
    setBusy(true)
    setError('')
    try {
      await api('/worlds/back-when', { year: chosen, from_history: fromHistory, companion_id: data.companion_id })
      enter()
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Nothing was changed. Try again.')
      setBusy(false)
    }
  }
  return (<>
    <p>{backWhenNote(data.name)}</p>
    <fieldset className="back-when-moments" disabled={busy}>
      <legend>When to go back to</legend>
      {data.moments.map((moment) => (
        <label key={moment.key} className="back-when-moment">
          <input type="radio" name="back-when" checked={pick.kind === 'moment' && pick.key === moment.key} onChange={() => setPick({ kind: 'moment', key: moment.key })} />
          <span><span>{moment.label}</span><small>{momentLine(moment, data.name)}</small></span>
        </label>
      ))}
      <label className="back-when-moment">
        <input type="radio" name="back-when" checked={pick.kind === 'year'} onChange={() => setPick({ kind: 'year' })} />
        <span><span>{data.moments.length ? 'Another year' : 'Pick a year'}</span><small>Any year from {data.earliest} to {data.latest}</small></span>
      </label>
      {pick.kind === 'year' && <Field label="Year">
        {(fieldId) => <select id={fieldId} value={year} onChange={(event) => setYear(Number(event.target.value))}>
          {backWhenYears(data).map((option) => <option key={option} value={option}>{option}</option>)}
        </select>}
      </Field>}
    </fieldset>
    <Toggle label="Work it out from our history" checked={fromHistory} disabled={busy} onChange={setFromHistory} hint={HISTORY_HINT} />
    {error && <Notice tone="error">{error}</Notice>}
    <div className="dialog-actions">
      <button type="button" className="button" disabled={busy} onClick={onClose}>Cancel</button>
      <button type="button" className="button primary" disabled={busy} onClick={() => void go()}>{busy ? `Going back to ${chosen}…` : `Go back to ${chosen}`}</button>
    </div>
  </>)
}
