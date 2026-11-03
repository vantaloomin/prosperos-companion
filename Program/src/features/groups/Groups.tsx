import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { Backstory, CastMember, Group } from '../../types'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Backstories } from './Backstories'
import { toldOnly } from './groupText'
import { GROUPS_KEY } from './groupState'

/** Two or more companions, main or stepped back (everyone unless given), and optionally a name for the group. */
export function NewGroup({ companions, chosen, onClose, onMade }: { companions: CastMember[]; chosen?: string[]; onClose: () => void; onMade: (group: Group) => void }) {
  const client = useQueryClient()
  const [picked, setPicked] = useState<string[]>(() => chosen ?? companions.map((member) => member.id))
  const [name, setName] = useState('')
  const [ties, setTies] = useState<Backstory[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const toggle = (id: string) => setPicked((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id])
  const make = async () => {
    setBusy(true)
    setError('')
    try {
      const told = toldOnly(ties).filter((item) => picked.includes(item.a) && picked.includes(item.b))
      const group = await api<Group>('/groups', { companion_ids: picked, name: name.trim() || null, ties: told })
      await client.invalidateQueries({ queryKey: GROUPS_KEY })
      onMade(group)
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'The group was not made. Try again.') } finally { setBusy(false) }
  }
  return (
    <ConfirmDialog title="New group" onClose={onClose} actions={<>
      <button type="button" className="button" onClick={onClose}>Cancel</button>
      <button type="button" className="button primary" disabled={picked.length < 2 || busy} onClick={() => void make()}>Start the group</button>
    </>}>
      <fieldset className="group-picker">
        <legend>Who is in it (two or more)</legend>
        {companions.map((member) => (
          <label key={member.id} className="check-row">
            <input type="checkbox" checked={picked.includes(member.id)} onChange={() => toggle(member.id)} />
            {member.name}{member.main && <span className="subtle"> · main character</span>}
          </label>
        ))}
      </fieldset>
      <Backstories companionIds={picked} value={ties} onChange={setTies} />
      <label className="field">Name (optional)
        <input autoComplete="off" value={name} maxLength={60} placeholder="Shown instead of their names" onChange={(event) => setName(event.target.value)} />
      </label>
      {error && <p className="error-text" role="alert">{error}</p>}
    </ConfirmDialog>
  )
}
