import { useEffect, useState } from 'react'
import type { CharacterDefinition } from '../../types'

/** The sheet once typing pauses, so suggestions follow the form without a request per keystroke. */
export function useSettled(value: CharacterDefinition, delay = 600): CharacterDefinition {
  const [settled, setSettled] = useState(value)
  const key = JSON.stringify(value)
  useEffect(() => {
    const timer = window.setTimeout(() => setSettled(JSON.parse(key) as CharacterDefinition), delay)
    return () => window.clearTimeout(timer)
  }, [key, delay])
  return settled
}
