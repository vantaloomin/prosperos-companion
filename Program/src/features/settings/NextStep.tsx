import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { Connection } from '../../types'
import { Notice } from '../../components/Feedback'
import { hasKeptDraft } from '../character/keptDraft'

/** With a model connected and no companion yet, the way on is creating them, or back to the picks the user left
 * there (src/features/character/keptDraft.ts). */
export function NextStep({ onCreate }: { onCreate: () => void }) {
  const connection = useQuery({ queryKey: ['connection'], queryFn: () => api<{ connection: Connection | null }>('/connection').then((data) => data.connection) })
  if (!connection.data) return null
  if (hasKeptDraft()) return <Notice action={<button type="button" className="button primary" onClick={onCreate}>Back to your companion</button>}>Your picks are saved.</Notice>
  return <Notice action={<button type="button" className="button primary" onClick={onCreate}>Create your companion</button>}>Your text model is ready. Next, create your companion.</Notice>
}
