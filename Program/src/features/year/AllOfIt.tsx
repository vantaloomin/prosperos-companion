import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, RotateCcw } from 'lucide-react'
import { api } from '../../api'
import type { History, HistoryLine } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { HISTORY_KEY, byYear, stretchText } from './yearText'

/**
 * All of it (Our history at a glance): the whole time together, a line a week lately and a month or a year further
 * back, newest first. The same lines they remember in chat; correcting one in your own words, or leaving it out,
 * changes what they remember.
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
  const fieldId = `history-edit-${line.key}`
  return (
    <li className={`history-line${left ? ' history-left-out' : ''}`}>
      <span className="history-when">{when}</span>
      {draft === null ? (
        <div className="history-body">
          <p>{left ? <><s>{line.text}</s> <span className="subtle">Left out</span></> : line.corrected ?? line.text}</p>
          {line.corrected !== null && !left && <p className="history-tag subtle">In your words</p>}
          <div className="history-actions">
            <button type="button" className="text-button" aria-label={`Correct ${when}`} onClick={() => setDraft(line.corrected || line.text)}><Pencil aria-hidden="true" />Correct</button>
            {line.corrected !== null && <button type="button" className="text-button" aria-label={`Put back the app's line for ${when}`} disabled={save.isPending} onClick={() => save.mutate(null)}><RotateCcw aria-hidden="true" />Put back</button>}
          </div>
        </div>
      ) : (
        <form className="history-body history-edit" onSubmit={(event) => { event.preventDefault(); save.mutate(draft) }}>
          <label htmlFor={fieldId} className="subtle">How you remember {when}</label>
          <textarea id={fieldId} value={draft} maxLength={300} rows={3} autoFocus onChange={(event) => setDraft(event.target.value)} />
          {save.isError && <ErrorNotice error={save.error} />}
          <div className="history-actions">
            <button type="submit" className="button primary" disabled={save.isPending || !draft.trim()}>Save</button>
            <button type="button" className="button" disabled={save.isPending} onClick={() => save.mutate('')}>Leave it out</button>
            <button type="button" className="text-button" onClick={() => setDraft(null)}>Cancel</button>
          </div>
        </form>
      )}
    </li>
  )
}
