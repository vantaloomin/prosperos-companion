import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { RotateCcw, Trash2 } from 'lucide-react'
import { api } from '../../api'
import { useWorkspaceSettings, type View } from '../../companion'
import type { StartOverPreview, StartOverResult } from '../../types'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { TextInput } from '../../components/Fields'
import { usePhoneStatus } from '../phone/phoneAccess'
import { nameMatches, othersStay, removedSummary, type StartOverMode } from './startOverText'
import { refocus } from './refocus'

const PREVIEW_KEY = ['start-over']

/** Start over with the same character, or delete them; both after a verified backup, and only on the PC. */
export function StartOver({ name, go }: { name: string; go: (view: View) => void }) {
  const onPhone = !!usePhoneStatus().data?.remote
  const [mode, setMode] = useState<StartOverMode | null>(null)
  if (onPhone) return null
  return (
    <section className="settings-section form-stack" aria-labelledby="start-over-heading">
      <div>
        <h2 id="start-over-heading">Start over or delete</h2>
        <p className="subtle">Starting over keeps {name} as you wrote them, with their look, and clears everything that happened: chats, memories, their life, the feed, their circle and every timeline. Deleting removes {name} completely, so you can create someone new. Either way a full backup is saved first, and your settings and model connections stay.</p>
      </div>
      <div className="form-actions">
        <button type="button" className="button" onClick={() => setMode('reset')}><RotateCcw aria-hidden="true" />Start over…</button>
        <button type="button" className="button danger" onClick={() => setMode('delete')}><Trash2 aria-hidden="true" />Delete {name}…</button>
      </div>
      {mode && <ConfirmStartOver mode={mode} onClose={() => setMode(null)} go={go} />}
    </section>
  )
}

function ConfirmStartOver({ mode, onClose, go }: { mode: StartOverMode; onClose: () => void; go: (view: View) => void }) {
  const preview = useQuery({ queryKey: PREVIEW_KEY, queryFn: () => api<StartOverPreview>('/companion/start-over'), staleTime: 0 })
  const [typed, setTyped] = useState('')
  const state = dialogState(mode, preview.data, typed)
  const { busy, error, confirm } = useConfirm(mode, typed, state.ready, () => { onClose(); go(mode === 'reset' || preview.data?.others.length ? 'conversation' : 'character') })
  return (
    <ConfirmDialog title={state.title} onClose={onClose} actions={<>
      <button type="button" className="button" onClick={onClose}>Cancel</button>
      <button type="button" className="button danger" aria-disabled={busy || !state.ready} onClick={() => void confirm()}>{busy ? 'Backing up…' : state.action}</button>
    </>}>
      {preview.isError && <ErrorNotice error={preview.error} />}
      {preview.data && <Removed preview={preview.data} mode={mode} />}
      <p>A full backup is saved first. To undo this, restore it in Settings, Backups.</p>
      {state.blocked && <Notice tone="error">An adapter is training for {state.name}. Stop it first.</Notice>}
      {error && <Notice tone="error">{error}</Notice>}
      <TextInput label={state.label} value={typed} onChange={setTyped} maxLength={200} hint="Capital letters do not matter." />
    </ConfirmDialog>
  )
}

function dialogState(mode: StartOverMode, preview: StartOverPreview | undefined, typed: string) {
  const name = preview?.name ?? ''
  const blocked = mode === 'delete' && !!preview?.training
  return {
    name, blocked,
    ready: !!preview && nameMatches(typed, name) && !blocked,
    title: mode === 'reset' ? `Start over with ${name}?` : `Delete ${name}?`,
    action: mode === 'reset' ? 'Start over' : `Delete ${name}`,
    label: `Type ${name || 'their name'} to confirm`,
  }
}

function Removed({ preview, mode }: { preview: StartOverPreview; mode: StartOverMode }) {
  const loraMaker = useWorkspaceSettings().data?.lora_maker
  return <>
    <p>This removes {removedSummary(preview, mode)}. {mode === 'reset'
      ? `${preview.name} stays as you wrote them, with their look, and meets you fresh from now.`
      : loraMaker ? 'Training folders and adapter test pictures are not in backups and are removed for good.' : ''}</p>
    {preview.others.length > 0 && <p>{othersStay(preview, mode)}</p>}
  </>
}

function useConfirm(mode: StartOverMode, typed: string, ready: boolean, done: () => void) {
  const client = useQueryClient()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const confirm = async () => {
    if (busy || !ready) return
    setBusy(true)
    setError(null)
    try {
      await api<StartOverResult>(mode === 'reset' ? '/companion/start-over' : '/companion/delete', { name: typed })
      // Everything shown came from the old history; start every view from what is there now.
      await refocus(client)
      done()
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Nothing was changed.')
      setBusy(false)
    }
  }
  return { busy, error, confirm }
}
