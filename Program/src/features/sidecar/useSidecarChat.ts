import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api, newId } from '../../api'
import { useCompanion, type View } from '../../companion'
import { splitForm, splitReply, wantsSplit, type SplitResult } from '../character/helper'
import { apply, undo } from './apply'
import { history, proposals, withProposal, type Proposal, type SidecarReply, type Turn } from './proposals'
import { sidecar, useSidecar } from './store'

const turnsNow = () => sidecar.get().turns
const update = (proposalId: string, change: Partial<Proposal>) => sidecar.setTurns(withProposal(turnsNow(), proposalId, change))

/** Sending to the sidecar, and applying or undoing what it proposes. */
export function useSidecarChat(view: View) {
  const { focus, bridge, turns } = useSidecar()
  const client = useQueryClient()
  const companion = useCompanion()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const split = async (text: string): Promise<Turn> => {
    const form = sidecar.get().bridge!
    const current = form.definition()
    const result = await api<SplitResult>('/companion/draft/split', { text, relationship: current.relationship, timezone: current.timezone })
    const proposal: Proposal = { id: newId(), change: { kind: 'whole', form: splitForm(form.form, result), filledIn: result.filled_in }, before: '', status: 'pending' }
    return { id: newId(), message: text, reply: splitReply(result), proposals: [proposal] }
  }
  const ask = async (text: string): Promise<Turn> => {
    const result = await api<SidecarReply>('/sidecar', {
      message: text, history: history(turnsNow()), view, focus_message_id: focus?.id ?? null, definition: bridge ? bridge.definition() : null,
    })
    const saved = companion.data?.version.definition ?? null
    return { id: newId(), message: text, reply: result.reply, proposals: proposals(result.changes, bridge?.form ?? null, saved, newId) }
  }
  /** Resolves true once the message was answered, so the composer can clear. */
  const send = async (text: string): Promise<boolean> => {
    setBusy(true)
    setError('')
    try {
      const turn = bridge && wantsSplit(bridge.definition(), text) ? await split(text) : await ask(text)
      sidecar.setTurns([...turnsNow(), turn])
      sidecar.clearFocus()
      return true
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'The sidecar could not answer.')
      return false
    } finally { setBusy(false) }
  }
  const run = async (proposal: Proposal, action: 'apply' | 'undo') => {
    update(proposal.id, { status: 'working', error: undefined })
    try {
      if (action === 'apply') update(proposal.id, { status: 'applied', undo: await apply(proposal, sidecar.get().bridge, client) })
      else { await undo(proposal, sidecar.get().bridge, client); update(proposal.id, { status: 'pending', undo: undefined }) }
    } catch (failure) {
      update(proposal.id, { status: action === 'apply' ? 'pending' : 'applied', error: failure instanceof Error ? failure.message : 'That did not work.' })
    }
  }
  const applyAll = async (turn: Turn) => {
    for (const proposal of turn.proposals) if (proposal.status === 'pending') await run(proposal, 'apply')
  }
  return {
    turns, focus, busy, error, setError, send, applyAll,
    formOpen: !!bridge,
    name: bridge?.form.definition.name || companion.data?.version.name || 'your companion',
    apply: (proposal: Proposal) => void run(proposal, 'apply'),
    undo: (proposal: Proposal) => void run(proposal, 'undo'),
    dismiss: (proposal: Proposal) => update(proposal.id, { status: 'dismissed' }),
    clear: () => sidecar.setTurns([]),
  }
}
export type SidecarChat = ReturnType<typeof useSidecarChat>
