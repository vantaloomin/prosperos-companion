import { Heart, LockKeyhole, Plus, UsersRound } from 'lucide-react'
import type { View } from '../../companion'
import { Menu } from '../../components/Menu'
import { useCast } from '../groups/groupState'
import { useEraWords } from '../world/useEraWords'
import { openNewGroup } from './newGroupStore'
import { newGroupNeeds } from './chatText'

/** The Chats list's +: a new group (once there are two companions), someone new on Matchlight, and Secrets. */
export function ChatsMenu({ go, up = false }: { go: (view: View) => void; up?: boolean }) {
  const companions = useCast().data?.members.length ?? 0
  const dating = useEraWords().dating_tab
  const needs = newGroupNeeds(companions)
  return <Menu label="New" icon={Plus} align="end" up={up} className="chats-menu" items={[
    { label: 'New group', icon: UsersRound, value: needs, disabled: !!needs, onSelect: () => openNewGroup() },
    { label: `Find someone on ${dating}`, icon: Heart, onSelect: () => go('dating') },
    { label: 'Secrets', icon: LockKeyhole, onSelect: () => go('secrets') },
  ]} />
}
