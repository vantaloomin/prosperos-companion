import { useState, type KeyboardEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Plus, RotateCcw } from 'lucide-react'
import { api } from '../../api'
import type { History, HistoryLine } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { HISTORY_KEY, byYear, daysText, stretchText } from './yearText'

/**
 * All of it (Our history at a glance): the whole time together, a line a week lately and a month or a year further
 * back, newest first. The same lines they remember in chat; correcting one in your own words, or leaving it out,
 * changes what they remember. The days talked sit beside each line, so a line starts with what happened (Iris).
 */
export function AllOfIt({ name }: { name: string }) {
  const history = useQuery({ queryKey: HISTORY_KEY, queryFn: () => api<History>('/life/history') })
  if (history.isPending) return <Loading label="Loading your history" />
  if (history.isError) return <ErrorNotice error={history.error} />
  if (!history.data.lines.length) return <Notice>The first line appears once your first week with {name} is over.</Notice>
  return (
    <div className="history">
      {byYear(history.data.lines).map((group) => (
        <section key={group.year} className="history-year" aria-labelledby={`history-${group.year}`}>
          <h2 id={`history-${group.year}`}>{group.year}</h2>
          <ol className="history-lines">
            {group.lines.map((line) => <Line key={line.key} line={line} />)}
          </ol>
        </section>
      ))}
      <button type="button" className="text-button history-top" onClick={() => document.querySelector('.our-year h1')?.scrollIntoView({ block: 'start' })}>Back to the start</button>
    </div>
  )
}

function Line({ line }: { line: HistoryLine }) {
  const client = useQueryClient()
  const [draft, setDraft] = useState<string | null>(null)
  const save = useMutation({
    mutationFn: (text: string | null) => text === null
      ? api<History>(`/life/history/${line.key}`, undefined, 'DELETE')
      : api<History>(`/life/history/${line.key}`, { text }, 'PUT'),
    onSuccess: (data) => { client.setQueryData(HISTORY_KEY, data); setDraft(null) },
  })
  const when = stretchText(line)
  const left = line.corrected === ''
  return (
    <li className={`history-line${left ? ' history-left-out' : ''}`}>
      <p className="history-when"><span>{when}</span><span className="subtle">{daysText(line.days, line.together)}</span>{left && !line.text && <span className="subtle">Left out</span>}</p>
      {draft === null
        ? <Shown line={line} when={when} left={left} busy={save.isPending} onEdit={() => setDraft(line.corrected || line.text)} onRestore={() => save.mutate(null)} />
        : <Editing line={line} when={when} draft={draft} setDraft={setDraft} save={save} />}
    </li>
  )
}

function Shown({ line, when, left, busy, onEdit, onRestore }: { line: HistoryLine; when: string; left: boolean; busy: boolean; onEdit: () => void; onRestore: () => void }) {
  const text = left ? line.text : line.corrected ?? line.text
  return (
    <div className="history-body">
      {text && (
        <p>
          {left ? <s>{text}</s> : text}
          <Tag corrected={line.corrected} />
        </p>
      )}
      <div className="history-actions">
        {text
          ? <button type="button" className="history-action" aria-label={`Correct ${when}`} onClick={onEdit}><Pencil aria-hidden="true" />Correct</button>
          : <button type="button" className="history-action" aria-label={`Add a line for ${when}`} onClick={onEdit}><Plus aria-hidden="true" />Add a line</button>}
        {line.corrected !== null && <button type="button" className="history-action" aria-label={`Put back the app's line for ${when}`} disabled={busy} onClick={onRestore}><RotateCcw aria-hidden="true" />Put back</button>}
      </div>
    </div>
  )
}

function Editing({ line, when, draft, setDraft, save }: { line: HistoryLine; when: string; draft: string; setDraft: (text: string | null) => void; save: { mutate: (text: string | null) => void; isPending: boolean; isError: boolean; error: Error | null } }) {
  const fieldId = `history-edit-${line.key}`
  const keys = (event: KeyboardEvent) => { if (event.key === 'Escape') { event.preventDefault(); setDraft(null) } }
  return (
    <form className="history-body history-edit" onKeyDown={keys} onSubmit={(event) => { event.preventDefault(); save.mutate(draft) }}>
      <label htmlFor={fieldId} className="subtle">How you remember {when}</label>
      <textarea id={fieldId} value={draft} maxLength={300} rows={3} autoFocus
        onFocus={(event) => { const end = event.currentTarget.value.length; event.currentTarget.setSelectionRange(end, end) }}
        onChange={(event) => setDraft(event.target.value)} />
      {save.error && <ErrorNotice error={save.error} />}
      <div className="history-actions">
        <button type="submit" className="button primary" disabled={save.isPending || !draft.trim()}>Save</button>
        <button type="button" className="button" disabled={save.isPending} onClick={() => save.mutate('')}>Leave it out</button>
        <button type="button" className="text-button" onClick={() => setDraft(null)}>Cancel</button>
      </div>
    </form>
  )
}

/** "In your words" or "Left out", right after the line, on its baseline (Iris). */
function Tag({ corrected }: { corrected: string | null }) {
  if (corrected === null) return null
  return <> <span className="history-tag">{corrected === '' ? 'Left out' : 'In your words'}</span></>
}
