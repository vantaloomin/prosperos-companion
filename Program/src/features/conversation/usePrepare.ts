import { useCallback, useRef } from 'react'
import { api } from '../../api'

const EVERY = 10_000

/**
 * Tell the life simulation the user is typing, at most every ten seconds, so it can bring the
 * agenda up to date and phrase upcoming moments in the background. It never delays sending.
 */
export function usePrepare() {
  const last = useRef(0)
  return useCallback(() => {
    const now = Date.now()
    if (now - last.current < EVERY) return
    last.current = now
    void api('/life/prepare', {}).catch(() => undefined)
  }, [])
}
