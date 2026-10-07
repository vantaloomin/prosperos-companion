import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { Connection } from '../../types'
import { Notice } from '../../components/Feedback'

/** With a model connected and no companion yet, the way on is creating them. */
export function NextStep({ onCreate }: { onCreate: () => void }) {
  const connection = useQuery({ queryKey: ['connection'], queryFn: () => api<{ connection: Connection | null }>('/connection').then((data) => data.connection) })
  if (!connection.data) return null
  return <Notice action={<button type="button" className="button primary" onClick={onCreate}>Create your companion</button>}>Your text model is ready. Next, create your companion.</Notice>
}
