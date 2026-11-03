import { api } from '../../api'
import type { ContextCategory, ContextMapping, ContextPurpose, ContextServiceInfo, MappingSuggestion } from '../../types'

/**
 * Save when a built-in server's lookup runs and confirm its disclosure, or turn it off when no switch is on.
 * The disclosure is written above the switches, so nothing is sent before it is described.
 */
export async function saveBuiltin(serviceId: string, category: ContextCategory, run_in: ContextPurpose[], saved?: ContextMapping, suggestion?: MappingSuggestion) {
  const path = `/context/services/${serviceId}/tools/${category}`
  if (run_in.length === 0) return api(`${path}/disable`, {})
  const base = saved ?? suggestion!
  const updated = await api<ContextServiceInfo>(path, { tool: base.tool, arguments: base.arguments, run_in }, 'PUT')
  const mapping = updated.mappings.find((item) => item.category === category)
  if (mapping) await api(`${path}/enable`, { digest: mapping.disclosure.digest })
}

/** Whether any of a service's lookups is on. */
export const serviceIsOn = (service: ContextServiceInfo) => service.mappings.some((mapping) => mapping.enabled && mapping.approved)

/** The service's own On switch (Iris): off turns every lookup off; on turns on each lookup it can, keeping when
 * each one runs if it was set before, and confirming each disclosure, which the fold describes under the switch.
 * A server of your own turns back on only the lookups you set up; a built-in one sets up its suggested ones too. */
export async function setServiceOn(service: ContextServiceInfo, on: boolean, purposes: Record<ContextCategory, { purposes: ContextPurpose[] }>) {
  for (const category of Object.keys(purposes) as ContextCategory[]) await setLookupOn(service, category, on, purposes[category].purposes)
}

async function setLookupOn(service: ContextServiceInfo, category: ContextCategory, on: boolean, purposes: ContextPurpose[]) {
  const saved = service.mappings.find((mapping) => mapping.category === category)
  const path = `/context/services/${service.id}/tools/${category}`
  if (!on) return saved?.enabled && api(`${path}/disable`, {})
  const suggestion = service.builtin ? service.suggestions[category] : undefined
  if (!saved && !suggestion) return
  if (saved && !service.builtin) return api(`${path}/enable`, { digest: saved.disclosure.digest })
  return saveBuiltin(service.id, category, runsIn(saved, purposes), saved, suggestion)
}

/** Whether the On switch has anything to turn on. */
export const canTurnOn = (service: ContextServiceInfo) => service.builtin
  ? Object.keys(service.suggestions).length > 0 || service.mappings.length > 0
  : service.mappings.length > 0

/** When a lookup runs once turned back on: as it was set, or every time its kind can. */
const runsIn = (saved: ContextMapping | undefined, purposes: ContextPurpose[]) => saved?.run_in.length ? saved.run_in : purposes
