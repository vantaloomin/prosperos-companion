import { useState } from 'react'
import { X } from 'lucide-react'
import { Notice } from '../../components/Feedback'
import { Toggle } from '../../components/Fields'
import { DEFAULT_OOC_MARKERS, type OocMarker } from '../conversation/ooc'
import { useWorkspace } from './useWorkspace'

export function SectionError({ problem }: { problem: string | null }) {
  return problem ? <Notice tone="error">{problem}</Notice> : null
}

/** After a restore: shown above every tab, and finishing it lands on the memory settings it is about. */
export function RestoredReview({ onDone }: { onDone: () => void }) {
  const { data, save, problem } = useWorkspace()
  if (!data?.review_required) return null
  const complete = async () => { if (await save({ review_complete: true })) onDone() }
  return (
    <>
      <Notice action={<button type="button" className="text-button" onClick={() => void complete()}>Mark review complete</button>}>
        This workspace was restored from a backup. Look over its memories before turning on memory or background activity; a backup can hold things you asked to forget later.
      </Notice>
      <SectionError problem={problem} />
    </>
  )
}

export function MemorySettings() {
  const { data, save, problem } = useWorkspace()
  if (!data) return <SectionError problem={problem} />
  return (
        <section className="settings-section form-stack" aria-labelledby="memory-heading">
          <h2 id="memory-heading" tabIndex={-1}>Memory</h2>
          <SectionError problem={problem} />
          <Toggle label="Remember things automatically" checked={data.automatic_memory} onChange={(value) => void save({ automatic_memory: value })}
            hint="When on, facts you state directly in new messages (your name, where you live, a plan with a date) are saved with the messages they came from, after each reply. Questions, hypotheticals, quotes and roleplay are never saved. Earlier messages are not scanned. When off, only what you choose to remember is saved; your conversation is kept either way." />
          <Toggle label="Allow sensitive memories" checked={data.sensitive_memory} onChange={(value) => void save({ sensitive_memory: value })}
            hint="Health (like an allergy), beliefs, money and similar details are saved automatically with this on, so they can be remembered when it matters. Turn it off to have them wait in Memories as suggestions for you to keep or decline." />
          <Toggle label="Let the model catch more" checked={data.model_memory_suggestions ?? true} disabled={!data.automatic_memory}
            onChange={(value) => void save({ model_memory_suggestions: value })}
            hint="Messages the built-in rules found nothing in are sent to your model connection in the background, which picks out facts in your own words. They are saved automatically and marked that way in Memories, where you can correct or delete them; anything that contradicts a saved fact waits for you. Uses extra model time." />
          <Toggle label="Ask about people in your life" checked={data.ask_about_people ?? true} onChange={(value) => void save({ ask_about_people: value })}
            hint="People you mention (your sister, your boss, a friend by name) and what you say about them are remembered under the same setting as everything else. With this on, they may now and then ask how someone is doing or how their news turned out, at most once per question. Never after a loss, or about anyone a boundary covers." />
          <Toggle label="Let them look back when they need to" checked={data.recall_more ?? true} onChange={(value) => void save({ recall_more: value })}
            hint="When you bring up something from before that they can't place, they may take one more look through their memories and your earlier chats before answering. That reply can take up to twice as long. The app also widens its own search when the first look finds little; that needs no extra model time." />
          <Toggle label="Share what you've told them across alternate timelines" checked={data.share_profile_across_timelines} onChange={(value) => void save({ share_profile_across_timelines: value })}
            hint="Facts about you, your plans and how you're doing apply in every timeline, including ones you start with Edit from here. When off, each timeline only knows what you told it, plus what came before its edit. Shared moments and the companion's own life always stay in their own timeline." />
        </section>
  )
}

const sameMarkers = (a: OocMarker[], b: OocMarker[]) =>
  a.length === b.length && a.every((row, index) => row.open.toLowerCase() === b[index].open.toLowerCase() && row.close.toLowerCase() === b[index].close.toLowerCase())

/** What is wrong with one marker row, if anything. */
function markerProblem(rows: MarkerRow[], index: number): string | null {
  const row = rows[index]
  if (!row.open.trim() || (row.pair && !row.close.trim())) return 'A marker needs at least one character.'
  const same = (other: OocMarker) => other.open.trim().toLowerCase() === row.open.trim().toLowerCase() && other.close.trim().toLowerCase() === row.close.trim().toLowerCase()
  return rows.slice(0, index).some(same) ? 'That marker is already in the list.' : null
}

type MarkerRow = OocMarker & { pair: boolean }

/** The markers as nested rows inside the out-of-character group: one row per marker with its fields on the right,
 * then Add marker. They switch off with the row above them. */
export function OocMarkers({ markers, save, disabled }: { markers: OocMarker[]; save: (markers: OocMarker[]) => void; disabled?: boolean }) {
  const [rows, setRows] = useState<MarkerRow[]>(() => markers.map((row) => ({ ...row, pair: !!row.close })))
  const [adding, setAdding] = useState(false)
  // Saved as soon as every marker is complete; while one isn't, its row says why.
  const change = (next: MarkerRow[]) => {
    setRows(next)
    if (next.length && next.every((_row, index) => !markerProblem(next, index))) {
      save(next.map((row) => ({ open: row.open.trim(), close: row.pair ? row.close.trim() : '' })))
    }
  }
  const edit = (index: number, part: Partial<MarkerRow>) => change(rows.map((row, at) => (at === index ? { ...row, ...part } : row)))
  const add = (pair: boolean) => { setRows([...rows, { open: '', close: '', pair }]); setAdding(false) }
  const off = disabled ? ' disabled' : ''
  return <>
    {rows.map((row, index) => (
      <MarkerRowEditor key={index} row={row} problem={markerProblem(rows, index)} only={rows.length < 2} disabled={!!disabled}
        onChange={(part) => edit(index, part)} onRemove={() => change(rows.filter((_, at) => at !== index))} />
    ))}
    <div className={`setting-row nested marker-add${off}`}>
      {adding
        ? <span role="group" aria-label="Kind of marker" className="marker-kinds">
            <button type="button" className="text-button" disabled={disabled} onClick={() => add(false)}>Starts with</button>
            <button type="button" className="text-button" disabled={disabled} onClick={() => add(true)}>Between</button>
          </span>
        : <button type="button" className="text-button" onClick={() => setAdding(true)} disabled={disabled || rows.length >= 12}>Add marker</button>}
      {!sameMarkers(rows, DEFAULT_OOC_MARKERS) && <button type="button" className="text-button marker-reset" disabled={disabled} onClick={() => change(DEFAULT_OOC_MARKERS.map((row) => ({ ...row, pair: !!row.close })))}>Reset to defaults</button>}
    </div>
  </>
}

interface MarkerRowProps { row: MarkerRow; problem: string | null; only: boolean; disabled: boolean; onChange: (part: Partial<MarkerRow>) => void; onRemove: () => void }

function MarkerRowEditor({ row, problem, only, disabled, onChange, onRemove }: MarkerRowProps) {
  const box = (value: string, label: string, set: (text: string) => void) =>
    <input autoComplete="off" value={value} maxLength={12} size={5} aria-label={label} aria-invalid={!!problem} disabled={disabled} onChange={(event) => set(event.target.value)} />
  return (
    <div className={disabled ? 'setting-row nested marker-row disabled' : 'setting-row nested marker-row'}>
      <span className="setting-row-label">{row.pair ? 'Between' : 'Starts with'}{problem && <span className="marker-problem" role="alert">{problem}</span>}</span>
      <span className="marker-fields">
        {row.pair
          ? <>{box(row.open, 'Opening marker', (open) => onChange({ open }))}<span aria-hidden="true">and</span>{box(row.close, 'Closing marker', (close) => onChange({ close }))}</>
          : box(row.open, 'Starting word', (open) => onChange({ open }))}
        <button type="button" className="icon-button marker-remove" aria-label="Remove this marker" disabled={only || disabled} onClick={onRemove}><X aria-hidden="true" /></button>
      </span>
    </div>
  )
}
