import type { View } from '../../companion'
import { PersonaButton } from '../worlds/WorldButton'
import { ChatList } from './ChatList'
import { ChatsMenu } from './ChatsMenu'

/**
 * The phone's Chats tab: every one-to-one and group chat in one list with search, the way a messaging app opens.
 * Your persona's avatar sits top left and opens Worlds; + starts a group, opens Matchlight or Secrets.
 */
export function ChatsHome({ go }: { go: (view: View) => void }) {
  return (
    <section className="chats-home" aria-labelledby="chats-heading">
      <header className="chats-home-header">
        <PersonaButton onOpen={() => go('worlds')} />
        <h1 id="chats-heading">Chats</h1>
        <ChatsMenu go={go} />
      </header>
      <ChatList go={go} />
    </section>
  )
}
