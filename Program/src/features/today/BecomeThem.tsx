import { useState } from 'react'
import { api } from '../../api'
import type { Townsperson } from '../../types'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Notice } from '../../components/Feedback'
import { enter } from '../worlds/useWorlds'

/** Become a townsperson (companion/worlds.py): start a new world as this person, in the same town with the same
 * people. The world the user is in now waits as it is. */
export function BecomeThem({ person }: { person: Townsperson }) {
  const [asking, setAsking] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const become = async () => {
    setBusy(true)
    setError('')
    try {
      await api('/worlds/become', { key: person.key })
      enter()
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'That did not work. Try again.')
      setBusy(false)
      setAsking(false)
    }
  }
  return (<>
    <p><button type="button" className="text-button" disabled={busy} onClick={() => setAsking(true)}>{busy ? 'Starting…' : `Become ${person.name}`}</button></p>
    {error && <Notice tone="error">{error}</Notice>}
    {asking && <ConfirmDialog title={`Start a new life as ${person.full}?`} onClose={() => setAsking(false)} actions={<>
      <button type="button" className="button" onClick={() => setAsking(false)}>Not now</button>
      <button type="button" className="button primary" disabled={busy} onClick={() => void become()}>{busy ? 'Starting…' : `Become ${person.name}`}</button>
    </>}>
      <p>You start a new world as {person.name}, in the same town with the same people, and someone from {person.name}&apos;s own circle is there to talk to. Their job, street and routine come with them, and you can change anything about who you are in Worlds.</p>
      <p className="subtle">This world and everyone in it stay just as they are. You can come back any time from Worlds.</p>
    </ConfirmDialog>}
  </>)
}
