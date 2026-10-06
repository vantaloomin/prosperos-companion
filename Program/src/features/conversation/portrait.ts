import { useCompanion } from '../../companion'

/** The address of the companion's profile picture, or null while they have none (their initial shows instead). */
export function usePortrait(): string | null {
  const id = useCompanion().data?.portrait_reference_id
  return id ? `/api/lora/references/${id}/file` : null
}
