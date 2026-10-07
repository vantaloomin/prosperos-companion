import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { ArrowUp, MessageSquareText, Undo2, X } from 'lucide-react'
import { api, newId } from '../../api'
import type { CharacterDefinition } from '../../types'
import { Notice } from '../../components/Feedback'
import { TextComparison } from '../../components/TextComparison'
import type { FormState } from './drafting'
import { CardButton } from './CardButton'
import type { useHelperDock } from './useHelperDock'
import {
  FIELD_LABELS, applied, currentValue, fieldProposals, history, shownValue, splitForm, splitReply, undone, wantsSplit,
  type HelperReply, type Proposal, type SplitResult, type Turn,
} from './helper'

interface Props {
  /** Which character the conversation belongs to, so it survives saving a new version. */
  conversation: string
  form: FormState
  setForm: (form: FormState) => void
  definition: () => CharacterDefinition
  onClose: () => void
}

type Dock = ReturnType<typeof useHelperDock>


export function HelperToggle({ dock }: { dock: Dock }) {
  if (!dock.offered) return null
  return <button type="button" className="button helper-toggle" onClick={() => dock.choose(true)}><MessageSquareText aria-hidden="true" />Character helper</button>
}

export function HelperDock({ dock, conversation, ...props }: Omit<Props, 'onClose' | 'conversation'> & { dock: Dock; conversation?: string }) {
  if (!dock.shown) return null
  return <CharacterHelper {...props} conversation={conversation ?? 'new'} onClose={() => dock.choose(false)} />
}

// Conversations last while the app is open; the form remounts on every save.
const conversations = new Map<string, Turn[]>()

/** The sidecar beside the character form, after the Collaborator in Prospero's Study: paste a whole character or ask
 * for a change, and review each proposed field before it goes into the form. Nothing is saved until the form is. */
export function CharacterHelper({ conversation, form, setForm, definition, onClose }: Props) {
  const [turns, setTurnsState] = useState<Turn[]>(() => conversations.get(conversation) ?? [])
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const transcript = useRef<HTMLDivElement>(null)
  const setTurns = (next: Turn[]) => { conversations.set(conversation, next); setTurnsState(next) }
  useEffect(() => { transcript.current?.scrollTo({ top: transcript.current.scrollHeight }) }, [turns.length, busy])

  const send = async (event?: FormEvent) => {
    event?.preventDefault()
    const text = message.trim()
    if (!text || busy) return
    setBusy(true)
    setError('')
    try {
      const current = definition()
      const turn = wantsSplit(current, text) ? await split(text, current) : await ask(text, current)
      setTurns([...turns, turn])
      setMessage('')
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'The helper could not answer.')
    } finally { setBusy(false) }
  }
  const split = async (text: string, current: CharacterDefinition): Promise<Turn> => {
    const result = await api<SplitResult>('/companion/draft/split', { text, relationship: current.relationship, timezone: current.timezone })
    const proposal: Proposal = { id: newId(), kind: 'whole', form: splitForm(form, result), filledIn: result.filled_in, homeCity: result.home_city, status: 'pending' }
    return { id: newId(), message: text, reply: splitReply(result), proposals: [proposal] }
  }
  const ask = async (text: string, current: CharacterDefinition): Promise<Turn> => {
    const result = await api<HelperReply>('/companion/helper', { definition: current, message: text, history: history(turns) })
    return { id: newId(), message: text, reply: result.reply, proposals: fieldProposals(form, result.changes, newId) }
  }
  const update = (turnId: string, proposalId: string, change: (proposal: Proposal) => Proposal | { state: FormState; proposal: Proposal }) => {
    let nextForm: FormState | null = null
    const next = turns.map((turn) => turn.id !== turnId ? turn : {
      ...turn, proposals: turn.proposals.map((proposal) => {
        if (proposal.id !== proposalId) return proposal
        const result = change(proposal)
        if ('state' in result) { nextForm = result.state; return result.proposal }
        return result
      }),
    })
    setTurns(next)
    if (nextForm) setForm(nextForm)
  }
  // Applying in turn, so each change builds on the form the previous one left.
  const applyAll = (turn: Turn) => {
    let state = form
    const proposals = turn.proposals.map((proposal) => {
      if (proposal.status !== 'pending') return proposal
      const result = applied(state, proposal)
      state = result.state
      return result.proposal
    })
    setTurns(turns.map((item) => item.id === turn.id ? { ...item, proposals } : item))
    setForm(state)
  }
  const keyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) { event.preventDefault(); void send() }
  }

  return (
    <aside className="character-helper" aria-labelledby="character-helper-title">
      <header>
        <h2 id="character-helper-title"><MessageSquareText aria-hidden="true" />Character helper</h2>
        <button type="button" className="icon-button" aria-label="Close the character helper" onClick={onClose}><X aria-hidden="true" /></button>
      </header>
      <div className="helper-transcript" ref={transcript} aria-live="polite">
        {turns.length === 0 && <div className="helper-welcome">
          <p>Paste a whole character, or ask for a change: &ldquo;make her older&rdquo;, &ldquo;he has a sister&rdquo;, &ldquo;less formal&rdquo;.</p>
          <p className="subtle">You see every change before it goes into the form, and nothing is saved until you save the form.</p>
        </div>}
        {turns.map((turn) => (
          <article key={turn.id} className="helper-turn">
            <div className="helper-message">{turn.message.length > 600 ? `${turn.message.slice(0, 600)}…` : turn.message}</div>
            <p className="helper-reply">{turn.reply}</p>
            {turn.proposals.map((proposal) => (
              <ProposalCard key={proposal.id} proposal={proposal} form={form}
                onApply={() => update(turn.id, proposal.id, (item) => applied(form, item))}
                onDismiss={() => update(turn.id, proposal.id, (item) => ({ ...item, status: 'dismissed' }))}
                onUndo={() => update(turn.id, proposal.id, (item) => undone(form, item))} />
            ))}
            {turn.proposals.filter((proposal) => proposal.status === 'pending').length > 1 &&
              <button type="button" className="button" onClick={() => applyAll(turn)}>Apply all</button>}
          </article>
        ))}
        {busy && <Notice>Thinking it over. A local model can take a minute or two.</Notice>}
      </div>
      <form className="helper-composer" onSubmit={(event) => void send(event)}>
        {error && <Notice tone="error">{error}</Notice>}
        <textarea aria-label="Message to the character helper" placeholder="Paste a character or ask for a change" rows={3} maxLength={40000}
          value={message} disabled={busy} onChange={(event) => setMessage(event.target.value)} onKeyDown={keyDown} />
        <div className="helper-send">
          <CardButton onText={setMessage} onError={setError} disabled={busy} />
          <button type="submit" className="send-button" aria-label="Send to the character helper" disabled={busy || !message.trim()}><ArrowUp aria-hidden="true" /></button>
        </div>
      </form>
    </aside>
  )
}

function ProposalCard({ proposal, form, onApply, onDismiss, onUndo }: { proposal: Proposal; form: FormState; onApply: () => void; onDismiss: () => void; onUndo: () => void }) {
  const title = proposal.kind === 'whole' ? 'Fill the form from your character' : FIELD_LABELS[proposal.field]
  return (
    <section className={`helper-proposal ${proposal.status}`} aria-label={title}>
      <p className="eyebrow">{proposal.status === 'pending' ? 'Proposed' : proposal.status === 'applied' ? 'In the form' : 'Dismissed'}</p>
      <strong>{title}</strong>
      {proposal.kind === 'whole'
        ? <p className="subtle">Replaces every field except the relationship.{proposal.filledIn.length ? ` Filled in, not from your text: ${proposal.filledIn.map((field) => FIELD_LABELS[field]).join(', ')}.` : ''}</p>
        : <details><summary>Compare</summary><TextComparison before={shownValue(proposal.field, proposal.previous ?? currentValue(form, proposal.field))} after={shownValue(proposal.field, proposal.value)} /></details>}
      <div className="helper-actions">
        {proposal.status === 'pending' && <>
          <button type="button" className="button primary" onClick={onApply}>Apply</button>
          <button type="button" className="text-button" onClick={onDismiss}>Dismiss</button>
        </>}
        {proposal.status === 'applied' && <button type="button" className="text-button" onClick={onUndo}><Undo2 aria-hidden="true" />Undo</button>}
      </div>
    </section>
  )
}
