import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Archive, RotateCcw } from 'lucide-react'
import { api } from '../../api'
import type { BackupList, BackupResult } from '../../types'
import { Notice } from '../../components/Feedback'
import { Toggle } from '../../components/Fields'
import { backupLabel } from './backupText'

const BACKUPS_KEY = ['backups']
const formatDate = (iso: string) => new Date(iso).toLocaleString()

export function Backups() {
  const client = useQueryClient()
  const list = useQuery({ queryKey: BACKUPS_KEY, queryFn: () => api<BackupList>('/backups') })
  const [result, setResult] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const [datasets, setDatasets] = useState(false)
  const [confirming, setConfirming] = useState<string | null>(null)
  // Busy controls are marked, not disabled: disabling the focused control would drop keyboard focus.
  const run = async (action: () => Promise<unknown>, fallback: string) => {
    if (busy) return
    setBusy(true)
    try { await action() } catch (error) {
      setResult({ tone: 'error', text: error instanceof Error ? error.message : fallback })
    } finally { setBusy(false) }
  }
  const backup = () => run(async () => {
    const created = await api<BackupResult>(`/backups?include_datasets=${datasets}`, {})
    setResult({ tone: 'info', text: `Backup saved to ${created.path}.` })
    await client.invalidateQueries({ queryKey: BACKUPS_KEY })
  }, 'The backup failed.')
  const choose = (name: string) => run(async () => {
    client.setQueryData(BACKUPS_KEY, await api<BackupList>(`/backups/${encodeURIComponent(name)}/restore`, {}))
    setConfirming(null)
    setResult(null)
  }, 'That backup cannot be restored.')
  const cancel = () => run(async () => {
    client.setQueryData(BACKUPS_KEY, await api<BackupList>('/backups/restore', undefined, 'DELETE'))
  }, 'The restore was not cancelled.')
  const pending = list.data?.pending
  return (
    <section className="settings-section form-stack" aria-labelledby="backup-heading">
      <div>
        <h2 id="backup-heading">Backups</h2>
        <p className="subtle">A backup is a copy of this workspace, saved beside it: your conversation, memories, life, images and adapters. Your API keys are not included. Anything you delete later stays in backups made before.</p>
      </div>
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
      {pending && (
        <Notice action={<button type="button" className="text-button" aria-disabled={busy} onClick={() => void cancel()}>Cancel</button>}>
          {pending.name} will be restored the next time the Companion starts. Close it and start it again to finish.
        </Notice>
      )}
      <Toggle label="Include reference pictures" checked={datasets} onChange={setDatasets}
        hint="The pictures you collected to train a character adapter. Leave this off to keep them out of the backup; the adapters themselves are always included." />
      <div className="form-actions"><button type="button" className="button" aria-disabled={busy} onClick={() => void backup()}><Archive aria-hidden="true" />Back up now</button></div>
      {list.isError && <Notice tone="error">{list.error.message}</Notice>}
      {list.data && list.data.backups.length > 0 && (
        <div className="form-stack">
          <h3>Restore a backup</h3>
          <p className="subtle">Restoring replaces this workspace when the Companion next starts. The current one is moved aside, not deleted, and anything you deleted since the backup stays deleted. The restored workspace starts paused, with memory and background activity off, until you review it.</p>
          <ul className="plain-list">
            {list.data.backups.map((entry) => (
              <li key={entry.name}>
                {backupLabel(entry, formatDate)}{' '}
                {entry.readable && pending?.name !== entry.name && (confirming === entry.name
                  ? <>
                      <button type="button" className="text-button" aria-disabled={busy} onClick={() => void choose(entry.name)}>Restore on next start</button>{' '}
                      <button type="button" className="text-button" onClick={() => setConfirming(null)}>Keep current</button>
                    </>
                  : <button type="button" className="text-button" onClick={() => setConfirming(entry.name)}><RotateCcw aria-hidden="true" />Restore…</button>)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
