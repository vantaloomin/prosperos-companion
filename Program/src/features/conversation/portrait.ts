import { useCompanion } from '../../companion'

/** The address of the companion's profile picture, or null while they have none (their initial shows instead). */
export function usePortrait(): string | null {
  return portraitUrl(useCompanion().data?.portrait_reference_id)
}

/** The address of a profile picture by its reference id, or null when there is none. */
export function portraitUrl(id: string | null | undefined): string | null {
  return id ? `/api/lora/references/${id}/file` : null
}
