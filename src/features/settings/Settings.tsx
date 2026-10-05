import { useState } from 'react'
import { Archive } from 'lucide-react'
import { api } from '../../api'
import type { BackupResult, Companion } from '../../types'
import { Notice } from '../../components/Feedback'
import { ConnectionSettings } from './ConnectionSettings'
import { ContextSettings } from './ContextSettings'
import { ImageSettings } from './ImageSettings'
import { LifeSettings } from './LifeSettings'
import { WorkspaceSettings } from './WorkspaceSettings'

export function Settings({ companion }: { companion: Companion | null }) {
  return (
    <section className="page settings">
      <header className="page-header"><h1>Settings</h1></header>
      <ConnectionSettings />
      {companion && <WorkspaceSettings />}
      {companion && <LifeSettings name={companion.version.name} />}
      {companion && <ImageSettings />}
      {companion && <ContextSettings name={companion.version.name} />}
      {companion && <Backups />}
    </section>
  )
}

function Backups() {
  const [result, setResult] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const backup = async () => {
    setBusy(true)
    try {
      const created = await api<BackupResult>('/backups', {})
      setResult({ tone: 'info', text: `Backup saved to ${created.path}.` })
    } catch (error) { setResult({ tone: 'error', text: error instanceof Error ? error.message : 'The backup failed.' }) } finally { setBusy(false) }
  }
  return (
    <section className="settings-section form-stack" aria-labelledby="backup-heading">
      <div>
        <h2 id="backup-heading">Backups</h2>
        <p className="subtle">A backup is a copy of everything in this workspace, saved beside it. Your API key is not included. Anything you delete later stays in backups made before.</p>
      </div>
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
      <div className="form-actions"><button type="button" className="button" disabled={busy} onClick={() => void backup()}><Archive aria-hidden="true" />Back up now</button></div>
    </section>
  )
}
