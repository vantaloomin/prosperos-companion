import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { COMPANION_KEY } from '../../companion'
import type { CastMember, Companion } from '../../types'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Notice } from '../../components/Feedback'
import { townSeedText } from './castText'

/** The city's shared townsfolk, or new ones seeded for this companion alone. */
export function TownSeed({ companion }: { companion: Companion }) {
  const client = useQueryClient()
  const members = useQuery({ queryKey: ['cast'], queryFn: () => api<{ members: CastMember[] }>('/companion/cast').then((data) => data.members) })
  const [asking, setAsking] = useState<boolean | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const name = companion.version.name
  const own = !!companion.town_seed
  const shared = (members.data?.length ?? 1) > 1
  const text = townSeedText(name, own)
  const change = async (fresh: boolean) => {
    setBusy(true)
    setError('')
    try {
      client.setQueryData(COMPANION_KEY, await api<Companion>('/companion/town', { fresh }))
      await client.invalidateQueries({ queryKey: ['townsfolk'] })
      setAsking(null)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Nothing was changed.')
    } finally { setBusy(false) }
  }
  return (
    <section className="settings-section form-stack" aria-labelledby="town-seed-heading">
      <div>
        <h2 id="town-seed-heading">Townsfolk</h2>
        <p className="subtle">{shared ? `Your companions share one town, so its townsfolk stay as they are while there is more than one.` : text.about}</p>
      </div>
      {!shared && <div className="form-actions">
        <button type="button" className="button" onClick={() => setAsking(true)}>{own ? 'Seed new townsfolk again…' : 'Seed new townsfolk…'}</button>
        {own && <button type="button" className="text-button" onClick={() => setAsking(false)}>Use the city&apos;s shared townsfolk…</button>}
      </div>}
      {asking !== null && <ConfirmTown fresh={asking} busy={busy} error={error} warning={text.warning} onClose={() => setAsking(null)} onConfirm={() => void change(asking)} />}
    </section>
  )
}

interface ConfirmProps { fresh: boolean; busy: boolean; error: string; warning: string; onClose: () => void; onConfirm: () => void }

function ConfirmTown({ fresh, busy, error, warning, onClose, onConfirm }: ConfirmProps) {
  const action = fresh ? 'Seed new townsfolk' : 'Use shared townsfolk'
  return (
    <ConfirmDialog title={fresh ? 'Seed new townsfolk?' : 'Go back to the shared townsfolk?'} onClose={onClose} actions={<>
      <button type="button" className="button" onClick={onClose}>Cancel</button>
      <button type="button" className="button primary" aria-disabled={busy} onClick={onConfirm}>{busy ? 'Changing…' : action}</button>
    </>}>
      <p>{warning}</p>
      {error && <Notice tone="error">{error}</Notice>}
    </ConfirmDialog>
  )
}
