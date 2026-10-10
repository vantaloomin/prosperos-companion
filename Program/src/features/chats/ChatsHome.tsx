import { UsersRound } from 'lucide-react'
import type { View } from '../../companion'
import { PersonaButton } from '../worlds/WorldButton'
import { ChatList } from './ChatsPanel'

/**
 * The phone's Chats tab: every one-on-one and group chat in one list, the way a messaging app opens. Your persona's
 * avatar sits top left and opens Worlds; the group button opens group chats, where a new group starts.
 */
export function ChatsHome({ go }: { go: (view: View) => void }) {
  return (
    <section className="chats-home" aria-labelledby="chats-heading">
      <header className="chats-home-header">
        <PersonaButton onOpen={() => go('worlds')} />
        <h1 id="chats-heading">Chats</h1>
        <button type="button" className="icon-button" aria-label="Group chats" title="Group chats" onClick={() => go('groups')}><UsersRound aria-hidden="true" /></button>
      </header>
      <ChatList go={go} />
    </section>
  )
}
