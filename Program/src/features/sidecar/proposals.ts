/** What the sidecar proposes and how each proposal reads (docs/sidecar.md). Nothing here talks to the server. */
import type { CharacterDefinition, Layer } from '../../types'
import type { DraftField, FieldValue, FormState } from '../character/drafting.ts'
import { FIELD_LABELS, currentValue, shownValue, type HelperField } from '../character/helper.ts'

export type Change =
  | { kind: 'field'; field: HelperField; value: FieldValue }
  | { kind: 'reply'; message_id: string; before: string; text: string; created_at: string }
  | { kind: 'memory'; memory_id: string; revision: number; layer: Layer; subject: string; before: string; value: string }
  | { kind: 'new_memory'; layer: Layer; subject: string; value: string }
  | { kind: 'forget_memory'; memory_id: string; layer: Layer; subject: string; before: string }
/** A pasted character split into the open character form, as one proposal. */
export interface WholeForm { kind: 'whole'; form: FormState; filledIn: DraftField[] }

export interface SidecarReply { reply: string; changes: Change[] }
export type ProposalStatus = 'pending' | 'working' | 'applied' | 'dismissed'
/** `undo` is what putting it back needs: the earlier value, or the id the change created. */
export interface Proposal { id: string; change: Change | WholeForm; before: string; status: ProposalStatus; undo?: unknown; error?: string }
export interface Turn { id: string; message: string; reply: string; proposals: Proposal[] }
export interface HistoryTurn { role: 'user' | 'assistant'; content: string }

const HISTORY_TURNS = 5
const HISTORY_CHARS = 4000

/** The field's value now: in the open form, or in the saved character. */
export function fieldBefore(field: HelperField, form: FormState | null, saved: CharacterDefinition | null): string {
  if (form) return shownValue(field, currentValue(form, field))
  if (!saved) return ''
  return shownValue(field, field === 'name' || field === 'location' ? saved[field] : saved[field] as FieldValue)
}

export function proposals(changes: Change[], form: FormState | null, saved: CharacterDefinition | null, id: () => string): Proposal[] {
  return changes.map((change) => {
    const before = change.kind === 'field' ? fieldBefore(change.field, form, saved) : 'before' in change ? change.before : ''
    return { id: id(), change, before, status: 'pending' as const }
  }).filter((proposal) => proposal.change.kind !== 'field' || proposal.before !== after(proposal))
}

export function after(proposal: Proposal): string {
  const { change } = proposal
  if (change.kind === 'field') return shownValue(change.field, change.value)
  if (change.kind === 'reply') return change.text
  if (change.kind === 'memory' || change.kind === 'new_memory') return change.value
  return ''
}

export function title(proposal: Proposal, name: string): string {
  const { change } = proposal
  if (change.kind === 'whole') return 'Fill the form from your character'
  if (change.kind === 'field') return FIELD_LABELS[change.field]
  if (change.kind === 'reply') return `${name}'s reply${when(change.created_at)}`
  if (change.kind === 'memory') return `Memory: ${change.subject}`
  if (change.kind === 'new_memory') return `New memory: ${change.subject}`
  return `Set aside memory: ${change.subject}`
}

/** One line on what applying does, where it is not obvious. */
export function effect(proposal: Proposal, formOpen: boolean): string {
  const { change } = proposal
  if (change.kind === 'whole') return `Replaces every field except the relationship.${change.filledIn.length ? ` Filled in, not from your text: ${change.filledIn.map((field) => FIELD_LABELS[field]).join(', ')}.` : ''}`
  if (change.kind === 'field') return formOpen ? 'Changes the form; nothing is saved until you save it.' : 'Saves a new character version.'
  if (change.kind === 'reply') return 'Later replies and recall see the new wording.'
  if (change.kind === 'memory') return 'Corrects the memory everywhere it is used.'
  if (change.kind === 'forget_memory') return 'Keeps it in Memories but stops using it.'
  return ''
}

function when(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : `, ${date.toLocaleString(undefined, { weekday: 'short', hour: 'numeric', minute: '2-digit' })}`
}

/** What the server is sent of the conversation so far: the latest turns, each cut to a readable length. */
export function history(turns: Turn[]): HistoryTurn[] {
  return turns.slice(-HISTORY_TURNS).flatMap((turn) => [
    { role: 'user' as const, content: turn.message.slice(0, HISTORY_CHARS) },
    { role: 'assistant' as const, content: turn.reply.slice(0, HISTORY_CHARS) },
  ]).filter((turn) => turn.content.trim())
}

export function withProposal(turns: Turn[], proposalId: string, change: Partial<Proposal>): Turn[] {
  return turns.map((turn) => ({ ...turn, proposals: turn.proposals.map((item) => item.id === proposalId ? { ...item, ...change } : item) }))
}
