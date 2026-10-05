import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Check, X } from 'lucide-react'
import { api } from '../../api'
import { TIMELINES_KEY } from '../../companion'
import type { Message, Timeline } from '../../types'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Loading, Notice } from '../../components/Feedback'
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
        <p className="timeline-intro">Only the current timeline moves with real time. To try something different, choose Edit from here on one of your messages.</p>
        <button type="button" className="icon-button" aria-label="Close timelines" onClick={onClose}><X aria-hidden="true" /></button>
      </div>
      <div className="search-results">
        {timelines.isPending && <Loading label="Loading timelines" />}
        {timelines.isError && <Notice tone="error">{timelines.error.message}</Notice>}
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

export function EditDialog({ message, name, onClose, onDone }: { message: Message; name: string; onClose: () => void; onDone: (text: string) => void }) {
  const switchTo = useSwitchTimeline()
  const client = useQueryClient()
  const [text, setText] = useState(message.text)
  const [label, setLabel] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const submit = async (andSwitch: boolean) => {
    if (!text.trim()) return
    setBusy(true)
    try {
      const created = await api<Timeline>('/timelines', { message_id: message.id, text, label: label.trim() })
      if (andSwitch) {
        await switchTo(created.id)
        onDone(text)
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
    <ConfirmDialog title="Edit from here" onClose={onClose} actions={<>
      <button type="button" className="button" onClick={onClose} disabled={busy}>Cancel</button>
      <button type="button" className="button" onClick={() => void submit(false)} disabled={busy || !text.trim()}>Keep it for later</button>
      <button type="button" className="button primary" onClick={() => void submit(true)} disabled={busy || !text.trim()}>Switch to it</button>
    </>}>
      <p>This starts an alternate timeline from just before this message. Your current conversation with {name} stays exactly as it is, and you can switch back any time.</p>
      <TextArea label="Your message" value={text} onChange={setText} rows={4} maxLength={40000} />
      <TextInput label="Name for the new timeline (optional)" value={label} onChange={setLabel} maxLength={80} />
      {error && <Notice tone="error">{error}</Notice>}
    </ConfirmDialog>
  )
}
