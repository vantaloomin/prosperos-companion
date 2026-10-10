import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowUp, MessageSquareText, RotateCcw, SquareArrowOutUpRight, Undo2, X } from 'lucide-react'
import { api } from '../../api'
import type { View } from '../../companion'
import type { Connection } from '../../types'
import { Notice } from '../../components/Feedback'
import { TextComparison } from '../../components/TextComparison'
import { CardButton } from '../character/CardButton'
import { after, effect, title, type Proposal } from './proposals'
import { lookingAt } from './context'
import { sidecar, useSidecar } from './store'
import { useSidecarChat, type SidecarChat } from './useSidecarChat'

/** The sidecar, after the Collaborator in Prospero's Study: an out-of-context chat beside the app that sees the
 * character, the conversation and the memories, and proposes changes the user applies one by one. */
export function Sidecar({ view, go, windowed = false }: { view: View; go: (view: View) => void; windowed?: boolean }) {
  const chat = useSidecarChat(view)
  const { blocked } = useSidecar()
  const connection = useQuery({ queryKey: ['connection'], queryFn: () => api<{ connection: Connection | null }>('/connection').then((data) => data.connection) })
  return (
    <aside className="sidecar" aria-labelledby="sidecar-title">
      <header>
        <div>
          <h2 id="sidecar-title"><MessageSquareText aria-hidden="true" />Sidecar</h2>
          <p className="subtle">Only you see this. Nothing here reaches {chat.name}.</p>
          {windowed && <p className="sidecar-context subtle">{lookingAt(view, chat.name)}</p>}
        </div>
        <div className="sidecar-header-actions">
          {chat.turns.length > 0 && <button type="button" className="icon-button" aria-label="Start a new sidecar chat" onClick={chat.clear}><RotateCcw aria-hidden="true" /></button>}
          <WhereButtons windowed={windowed} />
        </div>
      </header>
      <Transcript chat={chat}>
        {blocked && !windowed && <Notice>Your browser blocked the sidecar window, so it opened here instead. Allowing pop-ups for this app lets it open in its own window.</Notice>}
        {connection.isSuccess && !connection.data && <Notice action={<button type="button" className="text-button" onClick={() => go('settings/models')}>Open Settings</button>}>The sidecar uses your text model, and none is connected yet.</Notice>}
      </Transcript>
      <Composer chat={chat} connected={!!connection.data} />
    </aside>
  )
}

/** Pop out (desktop only) and close beside the app; Put back in its own window, whose own close button closes it. */
function WhereButtons({ windowed }: { windowed: boolean }) {
  if (windowed) return <button type="button" className="text-button" onClick={() => sidecar.putBack()}>Put back</button>
  const wide = !!window.matchMedia?.('(min-width: 721px)').matches
  return (<>
    {wide && <button type="button" className="icon-button" aria-label="Open in its own window" title="Open in its own window" onClick={() => sidecar.popOut()}><SquareArrowOutUpRight aria-hidden="true" /></button>}
    <button type="button" className="icon-button" aria-label="Close the sidecar" onClick={() => sidecar.setOpen(false)}><X aria-hidden="true" /></button>
  </>)
}

function Transcript({ chat, children }: { chat: SidecarChat; children: ReactNode }) {
  const transcript = useRef<HTMLDivElement>(null)
  useEffect(() => { transcript.current?.scrollTo({ top: transcript.current.scrollHeight }) }, [chat.turns.length, chat.busy])
  return (
    <div className="sidecar-transcript" ref={transcript} aria-live="polite">
      {children}
      {chat.turns.length === 0 && <Welcome formOpen={chat.formOpen} name={chat.name} />}
      {chat.turns.map((turn) => (
        <article key={turn.id} className="sidecar-turn">
          <div className="sidecar-message">{turn.message.length > 600 ? `${turn.message.slice(0, 600)}…` : turn.message}</div>
          <p className="sidecar-reply">{turn.reply}</p>
          {turn.proposals.map((proposal) => <ProposalCard key={proposal.id} proposal={proposal} name={chat.name} formOpen={chat.formOpen} onApply={() => chat.apply(proposal)} onUndo={() => chat.undo(proposal)} onDismiss={() => chat.dismiss(proposal)} />)}
          {turn.proposals.filter((proposal) => proposal.status === 'pending').length > 1 && <button type="button" className="button" onClick={() => void chat.applyAll(turn)}>Apply all</button>}
        </article>
      ))}
      {chat.busy && <Notice>Thinking it over. A local model can take a minute or two.</Notice>}
    </div>
  )
}

function Composer({ chat, connected }: { chat: SidecarChat; connected: boolean }) {
  const [message, setMessage] = useState('')
  const box = useRef<HTMLTextAreaElement>(null)
  // Back from its own window: the keyboard carries on here, not on the page body.
  useEffect(() => { if (sidecar.takeReturning()) box.current?.focus() }, [])
  const send = async (event?: FormEvent) => {
    event?.preventDefault()
    const text = message.trim()
    if (text && !chat.busy && await chat.send(text)) setMessage('')
  }
  const keyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) { event.preventDefault(); void send() }
  }
  const { focus } = chat
  return (
    <form className="sidecar-composer" onSubmit={(event) => void send(event)}>
      {focus && <p className="sidecar-focus"><span>About {chat.name}&rsquo;s reply: &ldquo;{focus.text.length > 90 ? `${focus.text.slice(0, 90)}…` : focus.text}&rdquo;</span><button type="button" className="icon-button" aria-label="Stop asking about this reply" onClick={() => sidecar.clearFocus()}><X aria-hidden="true" /></button></p>}
      {chat.error && <Notice tone="error">{chat.error}</Notice>}
      <textarea ref={box} aria-label="Message to the sidecar" placeholder={chat.formOpen ? 'Paste a character or ask for a change' : 'Ask about a reply, a memory or the character'} rows={3} maxLength={40000}
        value={message} disabled={chat.busy} onChange={(event) => setMessage(event.target.value)} onKeyDown={keyDown} />
      <div className="sidecar-send">
        {chat.formOpen ? <CardButton onText={setMessage} onError={chat.setError} disabled={chat.busy} /> : <span className="subtle">Ctrl+Enter sends</span>}
        <button type="submit" className="send-button" aria-label="Send to the sidecar" disabled={chat.busy || !message.trim() || !connected}><ArrowUp aria-hidden="true" /></button>
      </div>
    </form>
  )
}

function Welcome({ formOpen, name }: { formOpen: boolean; name: string }) {
  return (
    <div className="sidecar-welcome">
      {formOpen
        ? <p>Paste a whole character, or ask for a change: &ldquo;make them older&rdquo;, &ldquo;they have a sister&rdquo;, &ldquo;less formal&rdquo;.</p>
        : <p>Ask about {name}: &ldquo;was that reply in character?&rdquo;, &ldquo;rewrite that last reply shorter&rdquo;, &ldquo;which memories are wrong?&rdquo;.</p>}
      <p className="subtle">It can see the character, the recent chat and the memories. You review every change it proposes before it is used.</p>
    </div>
  )
}

interface CardProps { proposal: Proposal; name: string; formOpen: boolean; onApply: () => void; onDismiss: () => void; onUndo: () => void }

function ProposalCard({ proposal, name, formOpen, onApply, onDismiss, onUndo }: CardProps) {
  const label = title(proposal, name)
  const kind = proposal.change.kind
  const state = { pending: 'Proposed', working: 'Working…', applied: 'Done', dismissed: 'Dismissed' }[proposal.status]
  return (
    <section className={`sidecar-proposal ${proposal.status}`} aria-label={label}>
      <p className="eyebrow">{state}</p>
      <strong>{label}</strong>
      {effect(proposal, formOpen) && <p className="subtle">{effect(proposal, formOpen)}</p>}
      {kind === 'new_memory' && <p className="sidecar-value">{after(proposal)}</p>}
      {kind === 'forget_memory' && <p className="sidecar-value">{proposal.before}</p>}
      {(kind === 'field' || kind === 'reply' || kind === 'memory') && <details><summary>Compare</summary><TextComparison before={proposal.before} after={after(proposal)} /></details>}
      {proposal.error && <p className="field-help-error" role="alert">{proposal.error}</p>}
      <div className="sidecar-actions">
        {proposal.status === 'pending' && <>
          <button type="button" className="button primary" onClick={onApply}>Apply</button>
          <button type="button" className="text-button" onClick={onDismiss}>Dismiss</button>
        </>}
        {proposal.status === 'applied' && <button type="button" className="text-button" onClick={onUndo}><Undo2 aria-hidden="true" />Undo</button>}
      </div>
    </section>
  )
}
