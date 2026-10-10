import { UserRound } from 'lucide-react'
import { useFollowWorld, useWorlds } from './useWorlds'
import { initial, whereLine } from './worldsText'

/** Who the user is and which world they are in, at the top of the nav; opens Worlds, where they switch persona or
 * world. It also follows a switch made on another screen (a paired phone, another tab). */
export function WorldButton({ current, onOpen }: { current: boolean; onOpen: () => void }) {
  const worlds = useFollowWorld().data
  return (
    <button type="button" className="nav-world rail-only" aria-current={current ? 'page' : undefined} onClick={onOpen}
      title={worlds ? `${whereLine(worlds.persona, worlds.world)}. Switch persona or world.` : 'Worlds'}>
      <span className="nav-persona" aria-hidden="true">{initial(worlds?.persona) || <UserRound size={14} />}</span><span>{worlds?.world.name ?? 'Worlds'}</span>
    </button>
  )
}

/** The same switch on the phone, as the avatar at the top left of Chats, the way messaging apps show yours. */
export function PersonaButton({ onOpen }: { onOpen: () => void }) {
  // The nav's WorldButton, always mounted, already follows a switch made elsewhere.
  const worlds = useWorlds().data
  const where = worlds ? whereLine(worlds.persona, worlds.world) : 'Worlds'
  return (
    <button type="button" className="persona-button" aria-label={`${where}. Switch persona or world.`} title={where} onClick={onOpen}>
      <span className="nav-persona" aria-hidden="true">{initial(worlds?.persona) || <UserRound size={16} />}</span>
    </button>
  )
}
