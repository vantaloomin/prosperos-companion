import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Check, X } from 'lucide-react'
import { api } from '../../api'
import { TIMELINES_KEY } from '../../companion'
import type { Message, Timeline } from '../../types'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { TextArea, TextInput } from '../../components/Fields'
import { forkNote, timelineSummary } from './timelineText'
import { useSwitchTimeline, useTimelines } from './useTimelines'

export function TimelinePanel({ name, onClose }: { name: string; onClose: () => void }) {
  const timelines = useTimelines()
  const switchTo = useSwitchTimeline()
  const [choosing, setChoosing] = useState<Timeline | null>(null)
  const [error, setError] = useState<string | null>(null)
  const all = timelines.data?.timelines ?? []
  const confirm = async (timeline: Timeline) => {
    setChoosing(null)
    try { await switchTo(timeline.id); setError(null) } catch (failure) { setError(failure instanceof Error ? failure.message : 'The timeline was not switched.') }
  }
  return (
    <div className="conversation-search timeline-panel" role="region" aria-label="Timelines" onKeyDown={(event) => { if (event.key === 'Escape') onClose() }}>
      <div className="search-bar">
        <p className="timeline-intro">Only the current timeline moves with real time. To try something different, choose Branch from here or Edit in a message's actions (hover over it, or tap its ⋯ button).</p>
        <button type="button" className="icon-button" aria-label="Close timelines" onClick={onClose}><X aria-hidden="true" /></button>
      </div>
      <div className="search-results">
        {timelines.isPending && <Loading label="Loading timelines" />}
        {timelines.isError && <ErrorNotice error={timelines.error} />}
        {error && <Notice tone="error">{error}</Notice>}
        <ul>
          {all.map((timeline) => (
            <li key={timeline.id} className="timeline-row">
              <div className="search-result">
                <span className="search-meta"><strong>{timeline.label}</strong><span>{timelineSummary(timeline)}</span></span>
                {forkNote(timeline, all) && <span className="subtle">{forkNote(timeline, all)}</span>}
                {timeline.latest_text && <span className="search-snippet">“{timeline.latest_text}”</span>}
              </div>
              {timeline.active
                ? <span className="timeline-current"><Check aria-hidden="true" />Current</span>
                : <button type="button" className="button" onClick={() => setChoosing(timeline)}>Switch to this</button>}
            </li>
          ))}
        </ul>
      </div>
      {choosing && (
        <ConfirmDialog title={`Switch to ${choosing.label}?`} onClose={() => setChoosing(null)} actions={<>
          <button type="button" className="button" onClick={() => setChoosing(null)}>Cancel</button>
          <button type="button" className="button primary" onClick={() => void confirm(choosing)}>Switch</button>
        </>}>
          <p>The current timeline is set aside exactly as it is, and you can come back to it here. While it is set aside, no time passes for {name} there.</p>
          <p>Anything still waiting for your review on it is dropped, and a reply still being written there stops.</p>
        </ConfirmDialog>
      )}
    </div>
  )
}

/** Edit from here on your own message (the edited words wait in the new timeline), or Branch from here on any
 * message (the new timeline keeps everything up to and including it). */
export function EditDialog({ message, name, branch = false, onClose, onDone }: { message: Message; name: string; branch?: boolean; onClose: () => void; onDone: (text: string | null) => void }) {
  const switchTo = useSwitchTimeline()
  const client = useQueryClient()
  const [text, setText] = useState(message.text)
  const [label, setLabel] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const ready = branch || !!text.trim()
  const submit = async (andSwitch: boolean) => {
    if (!ready) return
    setBusy(true)
    try {
      const created = await api<Timeline>('/timelines', { message_id: message.id, label: label.trim(), ...(branch ? {} : { text }) })
      if (andSwitch) {
        await switchTo(created.id)
        onDone(branch ? null : text)
      } else {
        await client.invalidateQueries({ queryKey: TIMELINES_KEY })
        onClose()
      }
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'The timeline was not created.')
      setBusy(false)
    }
  }
  return (
    <ConfirmDialog title={branch ? 'Branch from here' : 'Edit your message'} onClose={onClose} actions={<>
      <button type="button" className="button" onClick={onClose} disabled={busy}>Cancel</button>
      <button type="button" className="button" onClick={() => void submit(false)} disabled={busy || !ready}>Keep it for later</button>
      <button type="button" className="button primary" onClick={() => void submit(true)} disabled={busy || !ready}>Switch to it</button>
    </>}>
      {branch ? <BranchPoint message={message} name={name} /> : <>
        <p>{name} remembers what you said, so an edit starts an alternate timeline from just before this message. Your current conversation stays exactly as it is, and you can switch back any time.</p>
        <TextArea label="Your message" value={text} onChange={setText} rows={4} maxLength={40000} hint="Sent in place of the original message in the new timeline." />
      </>}
      <TextInput label="Name for the new timeline (optional)" value={label} onChange={setLabel} maxLength={80} hint="Shown in the timeline list so you can tell them apart." />
      {error && <Notice tone="error">{error}</Notice>}
    </ConfirmDialog>
  )
}

function BranchPoint({ message, name }: { message: Message; name: string }) {
  return <>
    <p>This starts an alternate timeline that keeps everything up to and including {message.role === 'user' ? 'your message' : `${name}'s message`}, so you can take it somewhere else from there. Your current conversation with {name} stays exactly as it is, and you can switch back any time.</p>
    <blockquote className="branch-quote">{message.text.length > 280 ? `${message.text.slice(0, 280)}…` : message.text}</blockquote>
  </>
}

/** New wording for one of the companion's replies, in place. The old wording is kept, and the sidecar can undo it. */
export function ReplyEditDialog({ message, name, onClose, onDone }: { message: Message; name: string; onClose: () => void; onDone: (text: string) => void }) {
  const [text, setText] = useState(message.text)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const changed = !!text.trim() && text.trim() !== message.text.trim()
  const save = async () => {
    if (!changed) return
    setBusy(true)
    try {
      const edited = await api<{ text: string }>(`/conversation/messages/${message.id}/edit`, { text, expected_text: message.text })
      onDone(edited.text)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'The reply was not changed.')
      setBusy(false)
    }
  }
  return (
    <ConfirmDialog title={`Edit ${name}'s reply`} onClose={onClose} actions={<>
      <button type="button" className="button" onClick={onClose} disabled={busy}>Cancel</button>
      <button type="button" className="button primary" onClick={() => void save()} disabled={busy || !changed}>Save</button>
    </>}>
      <p>Every later reply sees the new wording. What the old wording said about {name} is noted again from the new one.</p>
      <TextArea label={`${name}'s reply`} value={text} onChange={setText} rows={6} maxLength={8000} />
      {error && <Notice tone="error">{error}</Notice>}
    </ConfirmDialog>
  )
}
