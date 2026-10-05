import { useState, type FormEvent } from 'react'
import { Check, Pencil, Pin, PinOff, Trash2, Eye, EyeOff } from 'lucide-react'
import type { Memory, Message } from '../../types'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Toggle } from '../../components/Fields'
import { earlierVersions, statusLabels } from './memoryGroups'

export interface MemoryActions {
  correct: (memory: Memory, value: string) => Promise<boolean>
  confirm: (memory: Memory) => void
  pin: (memory: Memory, pinned: boolean) => void
  exclude: (memory: Memory, excluded: boolean) => void
  remove: (memory: Memory, deleteSources: boolean) => Promise<boolean>
}

const date = (value: string | null) => value ? new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : '…'

export function MemoryCard({ memory, all, sources, actions }: { memory: Memory; all: Memory[]; sources: Map<string, Message>; actions: MemoryActions }) {
  const [editing, setEditing] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const history = earlierVersions(memory, all)
  const excluded = memory.status === 'excluded'
  return (
    <li className={`memory${excluded ? ' excluded' : ''}`}>
      <div className="memory-main">
        <p className="memory-subject">{memory.subject}</p>
        {editing ? <CorrectForm memory={memory} onDone={() => setEditing(false)} correct={actions.correct} /> : <p className="memory-value">{memory.value}</p>}
        <Meta memory={memory} />
        <Sources ids={memory.source_message_ids} sources={sources} />
        <EarlierValues history={history} />
      </div>
      <ActionBar memory={memory} editing={editing} actions={actions} onEdit={() => setEditing(true)} onDelete={() => setDeleting(true)} />
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

function ActionBar({ memory, editing, actions, onEdit, onDelete }: { memory: Memory; editing: boolean; actions: MemoryActions; onEdit: () => void; onDelete: () => void }) {
  const excluded = memory.status === 'excluded'
  return (
    <div className="memory-actions" role="group" aria-label={`Actions for ${memory.subject}`}>
      {!excluded && !editing && <button type="button" className="text-button" onClick={onEdit}><Pencil aria-hidden="true" />Correct</button>}
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

function CorrectForm({ memory, correct, onDone }: { memory: Memory; correct: MemoryActions['correct']; onDone: () => void }) {
  const [value, setValue] = useState(memory.value)
  const [saving, setSaving] = useState(false)
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    if (await correct(memory, value.trim())) onDone()
    setSaving(false)
  }
  return (
    <form className="correct-form" onSubmit={submit}>
      <label className="visually-hidden" htmlFor={`correct-${memory.id}`}>Corrected value for {memory.subject}</label>
      <textarea id={`correct-${memory.id}`} rows={2} value={value} maxLength={4000} autoFocus onChange={(event) => setValue(event.target.value)} />
      <p className="subtle">The old value is kept as history and stops being used from the next reply.</p>
      <div className="form-actions">
        <button type="submit" className="button primary" disabled={saving || !value.trim() || value.trim() === memory.value}>Save correction</button>
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
      <p className="subtle">Copies already sent to a model service, or in backups made earlier, cannot be removed by the app.</p>
    </ConfirmDialog>
  )
}
