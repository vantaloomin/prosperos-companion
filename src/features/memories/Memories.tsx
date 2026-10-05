import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { api } from '../../api'
import { HISTORY_KEY, MEMORIES_KEY } from '../../companion'
import type { Companion, DeleteResult, History, Memory } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { useReturnFocus } from '../../components/returnFocus'
import { Toggle } from '../../components/Fields'
import { MemoryCard, type MemoryActions } from './MemoryCard'
import { RememberForm, type NewMemory } from './RememberForm'
import { ContextReceipt } from './ContextReceipt'
import { LookedUp } from './LookedUp'
import { Suggestions } from './Suggestions'
import { MergeProposals } from './MergeProposals'
import { PREVIEW_KEY } from './receiptRows'
import { LAYERS, REMEMBER_KEY, groupMemories, layerTitle, type RememberRequest } from './memoryGroups'

function takeRememberRequest(): RememberRequest | null {
  try {
    const value = sessionStorage.getItem(REMEMBER_KEY)
    sessionStorage.removeItem(REMEMBER_KEY)
    return value ? JSON.parse(value) : null
  } catch { return null }
}

export function Memories({ companion }: { companion: Companion }) {
  const client = useQueryClient()
  const [history, setHistory] = useState(false)
  const [request] = useState(takeRememberRequest)
  const [adding, setAdding] = useState(request !== null)
  const addButton = useReturnFocus<HTMLButtonElement>(adding)
  const [feedback, setFeedback] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  // A correction replaces the card with the new revision's; keyboard focus follows it there.
  const [corrected, setCorrected] = useState<string | null>(null)
  const memories = useQuery({ queryKey: [...MEMORIES_KEY, history], queryFn: () => api<Memory[]>(`/memories?history=${history}`) })
  const conversation = client.getQueryData<History>(HISTORY_KEY)
  const sources = useMemo(() => new Map((conversation?.messages ?? []).map((message) => [message.id, message])), [conversation])
  const name = companion.version.name

  const run = async <T,>(action: () => Promise<T>, done: string): Promise<T | null> => {
    try {
      const result = await action()
      setFeedback({ tone: 'info', text: done })
      void client.invalidateQueries({ queryKey: PREVIEW_KEY })
      await client.invalidateQueries({ queryKey: MEMORIES_KEY })
      return result
    } catch (error) {
      setFeedback({ tone: 'error', text: error instanceof Error ? error.message : 'That change was not saved.' })
      void client.invalidateQueries({ queryKey: MEMORIES_KEY })
      return null
    }
  }
  const actions: MemoryActions = {
    correct: async (memory, body) => {
      const revised = await run(() => api<Memory>(`/memories/${memory.id}/correct`, { ...body, expected_revision: memory.revision }),
        body.plan_status && body.value === memory.value ? `Marked “${memory.subject}” as ${body.plan_status}.` : `Corrected “${memory.subject}”. The next reply uses the new value.`)
      if (revised) setCorrected(revised.id)
      return !!revised
    },
    confirm: (memory) => void run(() => api(`/memories/${memory.id}/confirm`, {}), `Confirmed “${memory.subject}”.`),
    pin: (memory, pinned) => void run(() => api(`/memories/${memory.id}/pin?pinned=${pinned}`, {}), pinned ? `Pinned “${memory.subject}”.` : `Unpinned “${memory.subject}”.`),
    exclude: (memory, excluded) => void run(() => api(`/memories/${memory.id}/${excluded ? 'exclude' : 'include'}`, {}),
      excluded ? `“${memory.subject}” is kept but no longer used in conversation, nor are the messages it came from.` : `“${memory.subject}” is used in conversation again.`),
    remove: async (memory, deleteSources) => {
      const result = await run(() => api<DeleteResult>(`/memories/${memory.id}/delete`, { delete_sources: deleteSources }), `Deleted “${memory.subject}”.`)
      if (result && deleteSources) {
        void client.invalidateQueries({ queryKey: HISTORY_KEY })
        const others = result.linked_memory_ids.length
        if (others) setFeedback({ tone: 'info', text: `Deleted “${memory.subject}” and its messages. ${others} other memor${others === 1 ? 'y' : 'ies'} came from those messages and ${others === 1 ? 'is' : 'are'} still kept.` })
      }
      return !!result
    },
  }
  const remember = (memory: NewMemory) => run(() => api<Memory>('/memories', memory), `${name} will remember “${memory.subject}”.`)
  const groups = groupMemories(memories.data ?? [])

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <h1>Memories</h1>
          <p className="subtle">What {name} remembers and where it came from. Corrections and changes apply from the next reply.</p>
        </div>
        {!adding && <button ref={addButton} type="button" className="button" onClick={() => setAdding(true)}><Plus aria-hidden="true" />Remember something</button>}
      </header>
      {adding && <RememberForm name={name} request={request} onSave={remember} onCancel={() => setAdding(false)} />}
      <Suggestions name={name} run={run} />
      <MergeProposals run={run} />
      <ContextReceipt name={name} memories={memories.data ?? []} />
      <LookedUp name={name} />
      <div className="memory-toolbar"><Toggle label="Show earlier values" checked={history} onChange={setHistory} /></div>
      <div aria-live="polite">{feedback && <Notice tone={feedback.tone}>{feedback.text}</Notice>}</div>
      {memories.isPending && <Loading label="Loading memories" />}
      {memories.isError && <Notice tone="error">{memories.error.message}</Notice>}
      {memories.isSuccess && groups.length === 0 && <p className="subtle empty-memories">Nothing is remembered yet. Use Remember something, or Remember this on one of your messages. Automatic memory is off unless you turn it on in Settings; with it on, facts you state directly are saved after each reply.</p>}
      {groups.map((group) => (
        <section key={group.layer} className="memory-group" aria-labelledby={`layer-${group.layer}`}>
          <h2 id={`layer-${group.layer}`}>{layerTitle(group.layer, name)}</h2>
          <p className="subtle">{LAYERS.find((item) => item.id === group.layer)?.hint}</p>
          <ul className="memory-list">
            {group.current.map((memory) => <MemoryCard key={memory.id} memory={memory} all={memories.data ?? []} sources={sources} actions={actions} focusOnMount={memory.id === corrected} />)}
          </ul>
        </section>
      ))}
    </section>
  )
}
