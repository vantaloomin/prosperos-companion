import { Eye } from 'lucide-react'
import { useObserver } from './useObserver'
import { firstName } from './watchText'

/** Shown above a chat while the user is just watching (companion/observer.py), so they know writing steps them back
 * in, and how to get back to the Watching page. Other views leave it to the Watching tab. */
export function WatchBanner({ inChat, onOpen }: { inChat: boolean; onOpen: () => void }) {
  const observer = useObserver().data
  if (!observer?.watching || !inChat) return null
  const focus = observer.focus
  return (
    <div className="watch-banner" role="status">
      <Eye aria-hidden="true" />
      <span>Just watching{focus ? ` ${firstName(focus.name)}` : ''}. Writing steps you back in.</span>
      <button type="button" className="text-button" onClick={onOpen}>Back to watching</button>
    </div>
  )
}
