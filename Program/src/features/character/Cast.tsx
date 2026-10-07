import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { View } from '../../companion'
import type { CastMember } from '../../types'
import { Notice } from '../../components/Feedback'
import { steppedBack } from './castText'
import { useSwitchBack } from './useSwitchBack'

const CAST_KEY = ['cast']

/** Companions who stepped back from being the main character, with a way back to each. */
export function Cast({ go }: { go: (view: View) => void }) {
  const members = useQuery({ queryKey: CAST_KEY, queryFn: () => api<{ members: CastMember[] }>('/companion/cast').then((data) => data.members) })
  const { switchTo, busy, error } = useSwitchBack(go)
  const others = (members.data ?? []).filter((member) => !member.main)
  if (others.length === 0) return null
  return (
    <section className="settings-section form-stack" aria-labelledby="cast-heading">
      <div>
        <h2 id="cast-heading">Your other companions</h2>
        <p className="subtle">They stepped back from being the main character and go on living around town by simple rules. Switching back picks up where you left off, with every chat and memory.</p>
      </div>
      <ul className="network-list">
        {others.map((member) => (
          <li key={member.id}>
            <strong>{member.name}</strong> <span className="subtle">{steppedBack(member)}.</span>
            <button type="button" className="text-button" disabled={busy !== null} onClick={() => void switchTo(member.id)}>{busy === member.id ? 'Switching…' : `Switch to ${member.name}`}</button>
          </li>
        ))}
      </ul>
      {error && <Notice tone="error">{error}</Notice>}
    </section>
  )
}
