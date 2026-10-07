/** Applying and undoing a sidecar proposal, each through the app's own paths: the open character form or a new
 * character version, the reply edit, and the Memories corrections (docs/sidecar.md). */
import type { QueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { COMPANION_KEY, HISTORY_KEY, MEMORIES_KEY } from '../../companion'
import type { Companion, Memory } from '../../types'
import { completeDefinition } from '../character/definition'
import type { FieldValue, FormState } from '../character/drafting'
import { FIELD_LABELS, currentValue, withHelperField, type HelperField } from '../character/helper'
import type { Proposal } from './proposals'
import type { FormBridge } from './store'

interface Edited { id: string; text: string; previous_text: string }

/** Applies a proposal and returns what Undo needs. */
export async function apply(proposal: Proposal, bridge: FormBridge | null, client: QueryClient): Promise<unknown> {
  const { change } = proposal
  if (change.kind === 'whole') {
    if (!bridge) throw new Error('Open the character form to fill it in.')
    const previous = bridge.form
    bridge.setForm(change.form)
    return previous
  }
  if (change.kind === 'field') return setField(change.field, change.value, bridge, client)
  if (change.kind === 'reply') {
    await api<Edited>(`/conversation/messages/${change.message_id}/edit`, { text: change.text, expected_text: change.before })
    void client.invalidateQueries({ queryKey: HISTORY_KEY })
    return null
  }
  if (change.kind === 'memory') return (await memoryCall(client, `/memories/${change.memory_id}/correct`, { value: change.value, expected_revision: change.revision }))
  if (change.kind === 'new_memory') return (await memoryCall(client, '/memories', { layer: change.layer, subject: change.subject, value: change.value }))
  await memoryCall(client, `/memories/${change.memory_id}/exclude`, {})
  return null
}

export async function undo(proposal: Proposal, bridge: FormBridge | null, client: QueryClient): Promise<void> {
  const { change } = proposal
  if (change.kind === 'whole') {
    if (!bridge) throw new Error('Open the character form to put it back.')
    bridge.setForm(proposal.undo as FormState)
  } else if (change.kind === 'field') {
    await setField(change.field, proposal.undo as FieldValue, bridge, client)
  } else if (change.kind === 'reply') {
    await api<Edited>(`/conversation/messages/${change.message_id}/edit`, { text: change.before, expected_text: change.text })
    void client.invalidateQueries({ queryKey: HISTORY_KEY })
  } else if (change.kind === 'memory') {
    const corrected = proposal.undo as Memory
    await memoryCall(client, `/memories/${corrected.id}/correct`, { value: change.before, expected_revision: corrected.revision })
  } else if (change.kind === 'new_memory') {
    await memoryCall(client, `/memories/${(proposal.undo as Memory).id}/delete`, { delete_sources: false })
  } else {
    await memoryCall(client, `/memories/${change.memory_id}/include`, {})
  }
}

async function memoryCall(client: QueryClient, path: string, body: unknown): Promise<Memory> {
  const result = await api<Memory>(path, body)
  void client.invalidateQueries({ queryKey: MEMORIES_KEY })
  return result
}

/** A field goes into the open form, or into a new saved version; either way the value it replaced comes back. */
async function setField(field: HelperField, value: FieldValue, bridge: FormBridge | null, client: QueryClient): Promise<FieldValue> {
  if (bridge) {
    const previous = currentValue(bridge.form, field)
    bridge.setForm(withHelperField(bridge.form, field, value))
    return previous
  }
  const companion = await api<{ companion: Companion | null }>('/companion').then((data) => data.companion)
  if (!companion) throw new Error('Create the companion first.')
  const definition = completeDefinition(companion.version.definition)
  const previous = definition[field] as FieldValue
  const saved = await api<Companion>('/companion/versions', {
    definition: { ...definition, [field]: value }, note: `Changed in the sidecar: ${FIELD_LABELS[field].toLowerCase()}`, expected_version_id: companion.active_version_id,
  })
  client.setQueryData(COMPANION_KEY, saved)
  void client.invalidateQueries({ queryKey: ['versions'] })
  return previous
}
