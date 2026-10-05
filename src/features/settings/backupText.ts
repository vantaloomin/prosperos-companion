import type { BackupEntry } from '../../types'

export function backupSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

/** One line describing a backup in the list; names the ones made before an upgrade. */
export function backupLabel(entry: BackupEntry, formatDate: (iso: string) => string): string {
  if (!entry.readable) return `${entry.name} (cannot be read)`
  const when = entry.created_at ? formatDate(entry.created_at) : entry.name
  const kind = entry.kind === 'pre-upgrade' ? 'Before an upgrade' : 'Backup'
  const extras = [backupSize(entry.bytes)]
  if (entry.kind !== 'pre-upgrade') extras.push(entry.datasets_included ? 'with reference pictures' : 'without reference pictures')
  return `${kind}, ${when} (${extras.join(', ')})`
}
