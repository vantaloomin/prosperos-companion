import type { Companion } from '../../types'

export interface StudyWorkspace { path: string; database: string; study_version: string; schema_fingerprint: string }
export interface StudyCharacterSummary { id: string; name: string; version_id: string; version_number: number; versions: number; updated_at: string; has_artwork: boolean }
export interface StudyField { source: string; label: string; target: string | null; target_label: string | null; status: 'copied' | 'shortened' | 'not_imported'; characters: number | null; note: string }
export interface StudyArtwork { sha256: string; width: number | null; height: number | null; format: string | null; bytes: number | null; status: 'included' | 'excluded'; reason: string; thumbnail: string | null }
export interface StudyReview {
  workspace: StudyWorkspace
  source: { character_id: string; version_id: string; version_number: number; name: string; created_at: string }
  fields: StudyField[]
  artwork: StudyArtwork[]
  exclusions: { item: string; detail: string }[]
  defaults: string[]
  companion_exists: boolean
  review_token: string
}
export interface StudyImportResult { companion: Companion }

/** Fields that will be copied, and fields the review lists as staying in the Study. */
export function splitFields(fields: StudyField[]): { included: StudyField[]; left: StudyField[] } {
  return { included: fields.filter((field) => field.status !== 'not_imported'), left: fields.filter((field) => field.status === 'not_imported') }
}

export function fieldLine(field: StudyField): string {
  if (field.status === 'not_imported') return `${field.label}: ${field.note}`
  const into = field.target_label && field.target_label !== field.label ? ` → ${field.target_label}` : ''
  const size = field.characters !== null ? ` (${field.characters.toLocaleString('en')} characters)` : ''
  return `${field.label}${into}${size}${field.status === 'shortened' ? `. ${field.note}` : ''}`
}

export function studyVersionLabel(workspace: StudyWorkspace): string {
  return workspace.study_version ? `Study ${workspace.study_version}` : 'Study version not recorded'
}
