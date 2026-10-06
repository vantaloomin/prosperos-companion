import { useState } from 'react'
import { Pencil } from 'lucide-react'
import type { LifeEvent } from '../../types'
import { TextArea } from '../../components/Fields'

export interface EventCorrection { summary: string; details: LifeEvent['details'] }

/** Correct what happened. The correction becomes the account everywhere; the earlier version is kept. */
export function CorrectEvent({ event, onSave }: { event: LifeEvent; onSave: (correction: EventCorrection) => Promise<boolean> }) {
  const [open, setOpen] = useState(false)
  const [summary, setSummary] = useState(event.summary)
  const [post, setPost] = useState(event.details.post ?? '')
  const [saving, setSaving] = useState(false)
  if (!open) return <button type="button" className="text-button event-correct" onClick={() => setOpen(true)}><Pencil aria-hidden="true" />Correct</button>
  const save = async () => {
    setSaving(true)
    const details = event.details.post === undefined ? event.details : { ...event.details, post: post.trim() }
    if (await onSave({ summary: summary.trim(), details })) setOpen(false)
    setSaving(false)
  }
  return (
    <form className="correct-event" onSubmit={(submit) => { submit.preventDefault(); void save() }}>
      <TextArea label="What happened" value={summary} onChange={setSummary} rows={2} maxLength={2000} hint="Chat, memories and the feed use the corrected version from now on. The earlier version is kept." />
      {event.details.post !== undefined && <TextArea label="Their post about it" value={post} onChange={setPost} rows={2} maxLength={2000} hint="What the Feed shows them posting about it." />}
      <div className="form-actions">
        <button type="submit" className="button primary" disabled={saving || !summary.trim()}>Save correction</button>
        <button type="button" className="button quiet" onClick={() => setOpen(false)}>Cancel</button>
      </div>
    </form>
  )
}
