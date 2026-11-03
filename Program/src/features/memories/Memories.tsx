import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { BookHeart, Plus } from 'lucide-react'
import { api } from '../../api'
import { HISTORY_KEY, MEMORIES_KEY, type View } from '../../companion'
import type { Companion, DeleteResult, History, Memory, Message } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { useReturnFocus } from '../../components/returnFocus'
import { RowGroup, Switch } from '../../components/Rows'
import { InfoTip } from '../../components/InfoTip'
import { MemoryCard, type MemoryActions } from './MemoryCard'
import { RememberForm, type NewMemory } from './RememberForm'
import { ContextReceipt } from './ContextReceipt'
import { LookedUp } from './LookedUp'
import { Suggestions } from './Suggestions'
import { MergeProposals } from './MergeProposals'
import { Closeness } from './Closeness'
import { People } from './People'
import { CLOSENESS_KEY } from './closenessText'
import { PREVIEW_KEY } from './receiptRows'
import { LAYERS, PEOPLE_KEY, REMEMBER_KEY, groupMemories, layerTitle, type MemoryGroup, type RememberRequest } from './memoryGroups'

function takeRememberRequest(): RememberRequest | null {
  try {
    const value = sessionStorage.getItem(REMEMBER_KEY)
    sessionStorage.removeItem(REMEMBER_KEY)
    return value ? JSON.parse(value) : null
  } catch { return null }
}

export function Memories({ companion, go }: { companion: Companion; go: (view: View) => void }) {
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
      void client.invalidateQueries({ queryKey: CLOSENESS_KEY })
      void client.invalidateQueries({ queryKey: PEOPLE_KEY })
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
  // A refusal is shown on the form itself, next to what needs changing, rather than further down the page.
  const remember = async (memory: NewMemory): Promise<Memory | string> => {
    try {
      const saved = await api<Memory>('/memories', { ...memory, companion_id: companion.id })
      setFeedback({ tone: 'info', text: `${name} will remember “${memory.subject}”.` })
      void client.invalidateQueries({ queryKey: PREVIEW_KEY })
      void client.invalidateQueries({ queryKey: CLOSENESS_KEY })
      void client.invalidateQueries({ queryKey: PEOPLE_KEY })
      await client.invalidateQueries({ queryKey: MEMORIES_KEY })
      return saved
    } catch (error) {
      return error instanceof Error ? error.message : 'That memory was not saved.'
    }
  }
  const all = memories.data ?? []
  const groups = groupMemories(all)
  const empty = memories.isSuccess && all.length === 0
  const renderGroup = (group: MemoryGroup) => <LayerSection key={group.layer} group={group} name={name} all={all} sources={sources} actions={actions} corrected={corrected} />

  return (
    <section className="page">
      {/* How close you are leads; then the memories, with their two actions beside the heading (style guide: Memories). */}
      <Closeness name={name} memories={all} run={run} />
      <div className="memories-head">
        <h2 id="memories-heading">Memories</h2>
        <InfoTip id="memories-about" label="Memories" text={`What ${name} remembers and where it came from. Corrections and changes apply from the next reply.`} />
        <span className="memories-actions">
          <button type="button" className="button" onClick={() => go('year')}><BookHeart aria-hidden="true" />Our year</button>
          {!adding && <button ref={addButton} type="button" className="button" onClick={() => setAdding(true)}><Plus aria-hidden="true" />Remember</button>}
        </span>
      </div>
      {adding && <RememberForm name={name} request={request} onSave={remember} onCancel={() => setAdding(false)} />}
      <Suggestions name={name} run={run} />
      <MergeProposals run={run} />
      <div aria-live="polite">{feedback && <Notice tone={feedback.tone}>{feedback.text}</Notice>}</div>
      {memories.isPending && <Loading label="Loading memories" />}
      {memories.isError && <ErrorNotice error={memories.error} />}
      {empty && <p className="subtle empty-memories">Nothing remembered yet.</p>}
      {groups.filter((group) => group.layer === 'user_fact').map(renderGroup)}
      {memories.isSuccess && <People name={name} all={all} sources={sources} actions={actions} run={run} />}
      {groups.filter((group) => group.layer !== 'user_fact').map(renderGroup)}
      <MemoriesFoot name={name} all={all} history={history} setHistory={setHistory} />
    </section>
  )
}

/** Earlier values, quietly at the foot of the list and only once there is something to look back on; then what the
 * next reply uses and the lookups, as fold rows. */
function MemoriesFoot({ name, all, history, setHistory }: { name: string; all: Memory[]; history: boolean; setHistory: (on: boolean) => void }) {
  return <>
    {(all.length > 0 || history) && <span className="memory-history"><Switch id="memory-history" checked={history} onChange={setHistory} /><label htmlFor="memory-history">Show earlier values</label></span>}
    <RowGroup className="memories-folds">
      <ContextReceipt name={name} memories={all} />
      <LookedUp name={name} />
    </RowGroup>
  </>
}

/** The layer's name, with its hint behind an InfoTip. */
function LayerTitle({ group, name }: { group: MemoryGroup; name: string }) {
  const title = layerTitle(group.layer, name)
  const hint = LAYERS.find((item) => item.id === group.layer)?.hint
  return <div className="memory-group-title"><h3 id={`layer-${group.layer}`}>{title}</h3>{hint && <InfoTip id={`layer-${group.layer}-about`} label={title} text={hint} />}</div>
}

function LayerSection({ group, name, all, sources, actions, corrected }: { group: MemoryGroup; name: string; all: Memory[]; sources: Map<string, Message>; actions: MemoryActions; corrected: string | null }) {
  return (
    <section className="memory-group" aria-labelledby={`layer-${group.layer}`}>
      <LayerTitle group={group} name={name} />
      <ul className="memory-list">
        {group.current.map((memory) => <MemoryCard key={memory.id} memory={memory} all={all} sources={sources} actions={actions} focusOnMount={memory.id === corrected} />)}
      </ul>
      {group.finished.length > 0 && (
        <details className="memory-finished" open={group.finished.some((memory) => memory.id === corrected)}>
          <summary>Done and cancelled ({group.finished.length})</summary>
          <ul className="memory-list">
            {group.finished.map((memory) => <MemoryCard key={memory.id} memory={memory} all={all} sources={sources} actions={actions} focusOnMount={memory.id === corrected} />)}
          </ul>
        </details>
      )}
    </section>
  )
}
