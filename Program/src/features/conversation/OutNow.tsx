import { useQueryClient } from '@tanstack/react-query'
import { Home, MapPin, Undo2 } from 'lucide-react'
import { api } from '../../api'
import { useTogether } from '../today/useTogether'
import { TOGETHER_KEY, outNow, timeText } from '../today/outingText'

/** While an outing with the user is under way, a slim strip above the composer: where they are, and Head home
 * (with Undo for a minute or two after). */
export function OutNow({ name }: { name: string }) {
  const client = useQueryClient()
  const data = useTogether()
  const outing = outNow(data.data)
  if (!outing) return null
  const act = async (action: 'home' | 'undo') => {
    await api(`/life/outings/${outing.id}/${action}`, {}).catch(() => undefined)
    void client.invalidateQueries({ queryKey: TOGETHER_KEY })
  }
  const headed = outing.state === 'done'
  return (
    <aside className="out-now" aria-label="Out together">
      <MapPin aria-hidden="true" />
      <span>{headed ? `Headed home from ${outing.place.name}.` : <>Out with {name} at <a className="out-now-place" href={`#map/${encodeURIComponent(outing.place.id)}`} title="Show on map">{outing.place.name}</a> until {timeText(outing.until_time)}</>}</span>
      {headed
        ? <button type="button" className="text-button" onClick={() => void act('undo')}><Undo2 aria-hidden="true" />Undo</button>
        : <button type="button" className="text-button" onClick={() => void act('home')}><Home aria-hidden="true" />Head home</button>}
    </aside>
  )
}
