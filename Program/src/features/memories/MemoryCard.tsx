import { appDate } from '../../appTime.ts'
import { useEffect, useState, type FormEvent, type RefObject } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import { Check, Pencil, Pin, PinOff, Trash2, Eye, EyeOff } from 'lucide-react'
import type { DeletePreview, Memory, Message, PlanStatus } from '../../types'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Toggle } from '../../components/Fields'
import { useReturnFocus } from '../../components/returnFocus'
import { correction, dayInput, deletePreviewText, earlierVersions, followUp, statusLabels, type Correction } from './memoryGroups'

export interface MemoryActions {
  correct: (memory: Memory, body: Correction) => Promise<boolean>
  confirm: (memory: Memory) => void
  pin: (memory: Memory, pinned: boolean) => void
  exclude: (memory: Memory, excluded: boolean) => void
  remove: (memory: Memory, deleteSources: boolean) => Promise<boolean>
}

const date = (value: string | null) => value ? new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : '…'

export function MemoryCard({ memory, all, sources, actions, focusOnMount }: { memory: Memory; all: Memory[]; sources: Map<string, Message>; actions: MemoryActions; focusOnMount?: boolean }) {
  const [editing, setEditing] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const correctButton = useReturnFocus<HTMLButtonElement>(editing)
  useEffect(() => { if (focusOnMount && document.activeElement === document.body) correctButton.current?.focus() }, [focusOnMount, correctButton])
  const history = earlierVersions(memory, all)
  const excluded = memory.status === 'excluded'
  return (
    <li className={`memory${excluded ? ' excluded' : ''}`}>
      <div className="memory-main">
        <p className="memory-subject">{memory.subject}</p>
        {editing ? <CorrectForm memory={memory} onDone={() => setEditing(false)} correct={actions.correct} /> : <p className="memory-value">{memory.value}</p>}
        <Meta memory={memory} />
        {!editing && <FollowUp memory={memory} correct={actions.correct} onEdit={() => setEditing(true)} />}
        <Sources ids={memory.source_message_ids} sources={sources} />
        <EarlierValues history={history} />
      </div>
      <ActionBar memory={memory} editing={editing} actions={actions} correctButton={correctButton} onEdit={() => setEditing(true)} onDelete={() => setDeleting(true)} />
      {deleting && <DeleteDialog memory={memory} versions={history.length + 1} onClose={() => setDeleting(false)} remove={actions.remove} />}
    </li>
  )
}

function Meta({ memory }: { memory: Memory }) {
  return (
    <p className="memory-meta">
      {statusLabels(memory).map((label) => <span key={label} className="badge">{label}</span>)}
      <span>Said {date(memory.stated_at)}</span>
      {(memory.applies_from || memory.applies_until) && <span>Applies {date(memory.applies_from)} to {date(memory.applies_until)}</span>}
    </p>
  )
}

function EarlierValues({ history }: { history: Memory[] }) {
  if (!history.length) return null
  return (
    <details className="memory-history">
      <summary>Earlier values ({history.length})</summary>
      <ul>{history.map((item) => <li key={item.id}>{item.value} <small>until {date(item.updated_at)}</small></li>)}</ul>
    </details>
  )
}

function ActionBar({ memory, editing, actions, correctButton, onEdit, onDelete }: { memory: Memory; editing: boolean; actions: MemoryActions; correctButton: RefObject<HTMLButtonElement | null>; onEdit: () => void; onDelete: () => void }) {
  const excluded = memory.status === 'excluded'
  return (
    <div className="memory-actions" role="group" aria-label={`Actions for ${memory.subject}`}>
      {!excluded && !editing && <button ref={correctButton} type="button" className="text-button" onClick={onEdit}><Pencil aria-hidden="true" />Correct</button>}
      {memory.authority === 'tentative' && !excluded && <button type="button" className="text-button" onClick={() => actions.confirm(memory)}><Check aria-hidden="true" />Confirm</button>}
      <PinButton memory={memory} actions={actions} />
      <button type="button" className="text-button" onClick={() => actions.exclude(memory, !excluded)} title={excluded ? 'Use this again in conversation' : 'Keep this but stop using it, including the messages it came from'}>
        {excluded ? <Eye aria-hidden="true" /> : <EyeOff aria-hidden="true" />}{excluded ? 'Use again' : 'Stop using'}
      </button>
      <button type="button" className="text-button danger-text" onClick={onDelete}><Trash2 aria-hidden="true" />Delete</button>
    </div>
  )
}

function PinButton({ memory, actions }: { memory: Memory; actions: MemoryActions }) {
  const Icon = memory.pinned ? PinOff : Pin
  return <button type="button" className="text-button" onClick={() => actions.pin(memory, !memory.pinned)}><Icon aria-hidden="true" />{memory.pinned ? 'Unpin' : 'Pin'}</button>
}

function Sources({ ids, sources }: { ids: string[]; sources: Map<string, Message> }) {
  if (!ids.length) return <p className="memory-source subtle">Added by you directly.</p>
  return (
    <ul className="memory-source" aria-label="Where this came from">
      {ids.map((id) => {
        const message = sources.get(id)
        return <li key={id}>{message ? (message.redacted ? 'From a message you deleted.' : <>From your message: <q>{message.text.length > 160 ? `${message.text.slice(0, 160)}…` : message.text}</q></>) : 'From an earlier message in your conversation.'}</li>
      })}
    </ul>
  )
}

const PLAN_STATUSES: PlanStatus[] = ['proposed', 'agreed', 'postponed', 'cancelled', 'completed']

/** A focused question: whether a past plan happened, or when an unclear date applies (PRD M8). */
function FollowUp({ memory, correct, onEdit }: { memory: Memory; correct: MemoryActions['correct']; onEdit: () => void }) {
  const question = followUp(memory, appDate())
  const mark = (plan_status: PlanStatus) => void correct(memory, { value: memory.value, plan_status })
  if (question === 'outcome') {
    return (
      <div className="memory-followup" role="group" aria-label={`Did ${memory.subject} happen?`}>
        <span>The date has passed. Did it happen?</span>
        <button type="button" className="text-button" onClick={() => mark('completed')}>It happened</button>
        <button type="button" className="text-button" onClick={() => mark('cancelled')}>It was cancelled</button>
        <button type="button" className="text-button" onClick={onEdit}>It moved</button>
      </div>
    )
  }
  if (question !== 'date') return null
  return (
    <div className="memory-followup">
      <span>The date was unclear, so it is only a best guess.</span>
      <button type="button" className="text-button" onClick={onEdit}>Set the date</button>
    </div>
  )
}

function CorrectForm({ memory, correct, onDone }: { memory: Memory; correct: MemoryActions['correct']; onDone: () => void }) {
  const [draft, setDraft] = useState({ value: memory.value, plan_status: memory.plan_status, from: dayInput(memory.applies_from), until: dayInput(memory.applies_until) })
  const [saving, setSaving] = useState(false)
  const body = correction(memory, draft)
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!body) return
    setSaving(true)
    if (await correct(memory, body)) onDone()
    setSaving(false)
  }
  const id = `correct-${memory.id}`
  return (
    <form className="correct-form" onSubmit={submit}>
      <label className="visually-hidden" htmlFor={id}>Corrected value for {memory.subject}</label>
      <textarea id={id} aria-describedby={`${id}-hint`} rows={2} value={draft.value} maxLength={4000} autoFocus onChange={(event) => setDraft({ ...draft, value: event.target.value })} />
      <div className="correct-dates">
        {memory.plan_status && (
          <label>Status
            <select value={draft.plan_status ?? ''} onChange={(event) => setDraft({ ...draft, plan_status: event.target.value as PlanStatus })}>
              {PLAN_STATUSES.map((status) => <option key={status} value={status}>{status[0].toUpperCase() + status.slice(1)}</option>)}
            </select>
          </label>
        )}
        <label>From<input type="date" value={draft.from} onChange={(event) => setDraft({ ...draft, from: event.target.value })} /></label>
        <label>Until<input type="date" value={draft.until} onChange={(event) => setDraft({ ...draft, until: event.target.value })} /></label>
      </div>
      <p className="subtle" id={`${id}-hint`}>The old value is kept as history and stops being used from the next reply.{memory.dates_uncertain ? ' Saving the dates marks them as confirmed.' : ''}</p>
      <div className="form-actions">
        <button type="submit" className="button primary" disabled={saving || !body}>Save correction</button>
        <button type="button" className="button" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}

function DeleteDialog({ memory, versions, remove, onClose }: { memory: Memory; versions: number; remove: MemoryActions['remove']; onClose: () => void }) {
  const [withSources, setWithSources] = useState(false)
  const [busy, setBusy] = useState(false)
  const confirm = async () => { setBusy(true); if (await remove(memory, withSources)) onClose(); else setBusy(false) }
  return (
    <ConfirmDialog title={`Delete “${memory.subject}”?`} onClose={onClose} actions={<>
      <button type="button" className="button" onClick={onClose}>Cancel</button>
      <button type="button" className="button danger" disabled={busy} onClick={confirm}>Delete</button>
    </>}>
      <p>This removes the memory{versions > 1 ? ` and its ${versions - 1} earlier value${versions > 2 ? 's' : ''}` : ''} from this computer. Only a marker without its content is kept, so it is not added back automatically. If you only want it left out of conversation, choose Stop using instead.</p>
      {memory.source_message_ids.length > 0 && (
        <Toggle label="Also delete the messages it came from" checked={withSources} onChange={setWithSources}
          hint="Their text is removed from your conversation and replaced with a note that it was deleted. Other memories from those messages are listed afterwards." />
      )}
      <PreviewNote memory={memory} withSources={withSources} />
      <p className="subtle">Copies already sent to a model service, or in backups made earlier, cannot be removed by the app.</p>
    </ConfirmDialog>
  )
}

/** What else Delete touches, fetched before anything is applied. */
function PreviewNote({ memory, withSources }: { memory: Memory; withSources: boolean }) {
  const preview = useQuery({ queryKey: ['delete-preview', memory.id], queryFn: () => api<DeletePreview>(`/memories/${memory.id}/delete-preview`) })
  if (!preview.data) return null
  const lines = deletePreviewText(preview.data, withSources)
  return lines.length ? <ul className="subtle">{lines.map((line) => <li key={line}>{line}</li>)}</ul> : null
}
