import { useState } from 'react'
import { api } from '../../api'
import type { Townsperson, Worlds } from '../../types'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Notice } from '../../components/Feedback'
import { enter } from '../worlds/useWorlds'
import { arrive } from '../worlds/arrival'

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
      const after = await api<Worlds>('/worlds/become', { key: person.key })
      arrive(person.name, after.world.companions[0])
      enter()
    } catch (failure) {
      setError(`Couldn't start ${person.name}'s world: ${failure instanceof Error ? failure.message : 'something went wrong.'} Your current world is unchanged.`)
      setBusy(false)
      setAsking(false)
    }
  }
  return (<>
    <p><button type="button" className="button" disabled={busy} onClick={() => setAsking(true)}>{busy ? 'Starting…' : `Become ${person.name}`}</button></p>
    {error && <Notice tone="error">{error}</Notice>}
    {asking && <ConfirmDialog title={`Become ${person.name}?`} onClose={() => setAsking(false)} actions={<>
      <button type="button" className="button" onClick={() => setAsking(false)}>Not now</button>
      <button type="button" className="button primary" disabled={busy} onClick={() => void become()}>{busy ? 'Starting…' : `Become ${person.name}`}</button>
    </>}>
      <p>This starts a new world in this same town where you live as {person.name}, with {person.name}&apos;s job, home and friends. Your current world stays exactly as it is, and you can switch back any time from Worlds.</p>
    </ConfirmDialog>}
  </>)
}
