import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ImageIcon } from 'lucide-react'
import { api } from '../../api'
import type { DatingPhoto } from '../../types'
import { Notice } from '../../components/Feedback'

const POLL_MS = 3000

/** "Show photo": their one portrait, made the first time it is asked for and kept (companion/dating_photos.py). */
export function Photo({ personKey, name }: { personKey: string; name: string }) {
  const queryKey = ['dating-photo', personKey]
  const client = useQueryClient()
  const photo = useQuery({
    queryKey, queryFn: () => api<DatingPhoto>(`/dating/photos/${encodeURIComponent(personKey)}`),
    refetchInterval: (query) => ['queued', 'running'].includes(query.state.data?.status ?? '') ? POLL_MS : false,
  })
  const [error, setError] = useState('')
  const ask = async () => {
    setError('')
    try { client.setQueryData(queryKey, await api<DatingPhoto>('/dating/photos', { key: personKey })) } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'The photo could not be made.')
    }
  }
  const shown = photo.data ?? { status: 'none' }
  if (shown.status === 'completed' && shown.url) return <img className="dating-photo" src={shown.url} alt={`${name}'s photo`} />
  return <Ask photo={shown} name={name} error={error} onAsk={() => void ask()} />
}

function Ask({ photo, name, error, onAsk }: { photo: DatingPhoto; name: string; error: string; onAsk: () => void }) {
  const waiting = photo.status === 'queued' || photo.status === 'running'
  return (
    <div className="dating-photo-ask">
      {waiting
        ? <p className="subtle" role="status">Getting {name}'s photo…</p>
        : <button type="button" className="text-button" onClick={onAsk}><ImageIcon aria-hidden="true" />{photo.status === 'failed' ? 'Try the photo again' : 'Show photo'}</button>}
      {photo.status === 'failed' && photo.error && <Notice tone="error">{photo.error}</Notice>}
      {error && <Notice tone="error">{error}</Notice>}
    </div>
  )
}
