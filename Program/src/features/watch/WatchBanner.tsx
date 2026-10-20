import { Eye } from 'lucide-react'
import { useObserver } from './useObserver'

/** Shown above every other view while the user is just watching (companion/observer.py), so they know nobody is
 * expecting them and how to get back to the Watching page. */
export function WatchBanner({ onWatch, onOpen }: { onWatch: boolean; onOpen: () => void }) {
  const observer = useObserver().data
  if (!observer?.watching || onWatch) return null
  const focus = observer.focus
  return (
    <div className="watch-banner" role="status">
      <Eye aria-hidden="true" />
      <span>You&apos;re just watching{focus ? ` ${focus.name}` : ''}. Writing to anyone steps you back in.</span>
      <button type="button" className="text-button" onClick={onOpen}>Back to watching</button>
    </div>
  )
}
