import { useState } from 'react'
import { api } from '../../api'
import type { Townsperson, Worlds } from '../../types'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Notice } from '../../components/Feedback'
import { enter } from '../worlds/useWorlds'
import { arrive } from '../worlds/arrival'
import { becomeLabel, firstName } from '../watch/watchText'

/** Become a townsperson (companion/worlds.py): start a new world as this person, in the same town with the same
 * people. The world the user is in now waits as it is. Offered as a quiet "Try life as", and the dialog leads with
 * what stays the same, so it reads as something to try rather than a switch that loses anything. */
export function BecomeThem({ person }: { person: Pick<Townsperson, 'key' | 'name'> }) {
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
  const first = firstName(person.name)
  return (<>
    <p><button type="button" className="text-button" disabled={busy} onClick={() => setAsking(true)}>{busy ? 'Starting…' : becomeLabel(person.name)}</button></p>
    {error && <Notice tone="error">{error}</Notice>}
    {asking && <ConfirmDialog title={`Try life as ${person.name}?`} onClose={() => setAsking(false)} actions={<>
      <button type="button" className="button" onClick={() => setAsking(false)}>Stay here</button>
      <button type="button" className="button primary" disabled={busy} onClick={() => void become()}>{busy ? 'Starting…' : `Start ${first}'s world`}</button>
    </>}>
      <p>This opens a separate world in the same town, where you live as {person.name}: {first}&apos;s job, home and friends.</p>
      <p>Nothing here changes. This world, your companions and your chats stay exactly as they are, and you can come back any time from Worlds.</p>
    </ConfirmDialog>}
  </>)
}
