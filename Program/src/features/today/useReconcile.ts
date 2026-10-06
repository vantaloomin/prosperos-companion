import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'

/**
 * Reconcile the companion's life when the app opens and whenever it becomes visible again
 * (docs/life-api.md). It is cheap when nothing is due; a finished batch refreshes Today and Feed.
 */
export function useReconcile(enabled: boolean) {
  const client = useQueryClient()
  useEffect(() => {
    if (!enabled) return
    let running = false
    const reconcile = async () => {
      if (running || document.visibilityState === 'hidden') return
      running = true
      try {
        const result = await api<{ state: string }>('/life/reconcile', { mode: 'return' })
        if (result.state === 'started' || result.state === 'resumed') {
          void client.invalidateQueries({ queryKey: ['today'] })
          void client.invalidateQueries({ queryKey: ['feed'] })
        }
      } catch { /* Today shows the latest batch state; a failed reconcile is retried on the next visit. */ } finally { running = false }
    }
    void reconcile()
    document.addEventListener('visibilitychange', reconcile)
    return () => document.removeEventListener('visibilitychange', reconcile)
  }, [enabled, client])
}
