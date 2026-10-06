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
