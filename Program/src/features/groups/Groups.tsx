import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, UsersRound } from 'lucide-react'
import { api } from '../../api'
import type { View } from '../../companion'
import type { CastMember, Group } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Stamp } from '../../components/Stamp'
import { latestLine, membersLine } from './groupText'
import { GROUPS_KEY, useCast } from './groupState'

/** Every group chat, most recently active first, and New group. Groups sit beside the 1:1 chats. */
export function Groups({ go }: { go: (view: View) => void }) {
  const groups = useQuery({ queryKey: GROUPS_KEY, queryFn: () => api<{ groups: Group[] }>('/groups') })
  const cast = useCast()
  const [creating, setCreating] = useState(false)
  const companions = cast.data?.members ?? []
  return (
    <section className="groups" aria-labelledby="groups-heading">
      <GroupsHeader companions={cast.isSuccess ? companions.length : null} go={go} onNew={() => setCreating(true)} />
      <div className="groups-list">
        {groups.isPending && <Loading label="Loading your groups" />}
        {groups.isError && <ErrorNotice error={groups.error} />}
        {groups.isSuccess && !groups.data.groups.length && <p className="subtle groups-empty">No groups yet.</p>}
        <ul>
          {groups.data?.groups.map((group) => (
            <li key={group.id}>
              <button type="button" className="group-row" onClick={() => go(`group/${group.id}`)}>
                <span className="portrait" aria-hidden="true"><UsersRound /></span>
                <span className="group-row-text">
                  <strong>{group.title}</strong>
                  <span className="subtle">{latestLine(group) || membersLine(group)}</span>
                </span>
                {group.latest && <Stamp value={group.latest.created_at} className="subtle" />}
              </button>
            </li>
          ))}
        </ul>
      </div>
      {creating && <NewGroup companions={companions} onClose={() => setCreating(false)} onMade={(group) => { setCreating(false); go(`group/${group.id}`) }} />}
    </section>
  )
}

function GroupsHeader({ companions, go, onNew }: { companions: number | null; go: (view: View) => void; onNew: () => void }) {
  return (
    <header className="groups-header">
      <h1 id="groups-heading">Groups</h1>
      <p className="subtle">Talk with several of your companions at once. Each of them knows only what they were there for.</p>
      <div className="form-actions">
        <button type="button" className="button primary" disabled={(companions ?? 0) < 2} onClick={onNew}><Plus aria-hidden="true" />New group</button>
      </div>
      {companions !== null && companions < 2 && <Notice action={<button type="button" className="text-button" onClick={() => go('dating')}>Open Matchlight</button>}>
        A group needs at least two companions. Find another on Matchlight, or make someone you&apos;ve met around town a companion.</Notice>}
    </header>
  )
}

/** Pick two or more companions, main or stepped back, and optionally name the group. */
export function NewGroup({ companions, chosen = [], onClose, onMade }: { companions: CastMember[]; chosen?: string[]; onClose: () => void; onMade: (group: Group) => void }) {
  const client = useQueryClient()
  const [picked, setPicked] = useState<string[]>(chosen)
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const toggle = (id: string) => setPicked((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id])
  const make = async () => {
    setBusy(true)
    setError('')
    try {
      const group = await api<Group>('/groups', { companion_ids: picked, name: name.trim() || null })
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
      <label className="field">Name (optional)
        <input value={name} maxLength={60} placeholder="Shown instead of their names" onChange={(event) => setName(event.target.value)} />
      </label>
      {error && <p className="error-text" role="alert">{error}</p>}
    </ConfirmDialog>
  )
}
