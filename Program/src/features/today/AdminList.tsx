import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { CalendarClock, SkipForward, Undo2 } from 'lucide-react'
import { api } from '../../api'
import type { AdminItem } from '../../types'
import { Notice } from '../../components/Feedback'
import { ADMIN_KEY, adminMoved, adminTags, adminWhen, stayUnit } from './adminText'

/** Lists longer than this show their first few, with the rest a tap away (Iris's review). */
export const FOLD = 3

/** Appointments, errands and chores (companion/life/admin.py), each movable to another day. Shared by Today's Plans
 * and the Character page's Life admin panel. */
export function AdminList({ items, done = false, fold = FOLD, inWorkPanel = false }: { items: AdminItem[]; done?: boolean; fold?: number | null; inWorkPanel?: boolean }) {
  const client = useQueryClient()
  const [open, setOpen] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const send = async (id: string, path: string, failed: string) => {
    setError('')
    setBusy(id)
    try { await api(path, {}) } catch (failure) { setError(failure instanceof Error ? failure.message : failed) }
    setBusy('')
    void client.invalidateQueries({ queryKey: ADMIN_KEY })
    void client.invalidateQueries({ queryKey: ['today'] })
  }
  const move = (id: string) => send(id, `/life/admin/${id}/move`, 'It could not move.')
  // A stay with the other parent (companion/life/stays.py): moved to the next free weekend, skipped, or skip undone.
  const stay = (item: AdminItem, action: 'move' | 'skip' | 'undo') => send(item.id, `/life/admin/stays/${item.stay!.id}/${action}`, action === 'move' ? 'It could not move.' : 'That did not work.')
  const hidden = fold !== null && !open ? Math.max(0, items.length - fold) : 0
  const shown = hidden ? items.slice(0, fold ?? items.length) : items
  return (
    <>
      {error && <Notice tone="error">{error}</Notice>}
      <ul className="admin-list">
        {shown.map((item) => {
          const moved = adminMoved(item)
          return (
            <li key={item.id} className="admin-item">
              <div className="admin-head">
                <strong>{item.title}</strong>
                {adminTags(item, inWorkPanel).map((tag) => <span key={tag} className="badge">{tag}</span>)}
              </div>
              <div className="admin-when">
                <p className="subtle">{adminWhen(item)}</p>
                {!done && item.movable && <button type="button" className="text-button" disabled={busy === item.id} aria-label={`Move ${item.title} to another day`} onClick={() => void move(item.id)}><CalendarClock aria-hidden="true" />Move to another day</button>}
                {!done && item.stay && <StayButtons item={item} busy={busy === item.id} act={(action) => void stay(item, action)} />}
              </div>
              {item.detail && <p className="subtle">{item.detail}</p>}
              {item.line && <p className="subtle">{item.line}.</p>}
              {moved && <p className="subtle">{moved}</p>}
            </li>
          )
        })}
      </ul>
      {hidden > 0 && <button type="button" className="text-button admin-more" onClick={() => setOpen(true)}>Show {hidden} more</button>}
    </>
  )
}

/** Move and Skip this one on a stay still to come, or Undo on one skipped (companion/life/stays.py). */
function StayButtons({ item, busy, act }: { item: AdminItem; busy: boolean; act: (action: 'move' | 'skip' | 'undo') => void }) {
  const stay = item.stay!
  if (stay.undo) return <button type="button" className="text-button" disabled={busy} aria-label={`Undo skipping ${item.title}`} onClick={() => act('undo')}><Undo2 aria-hidden="true" />Undo</button>
  if (!stay.can_change) return null
  return (
    <span className="admin-actions">
      <button type="button" className="text-button" disabled={busy} aria-label={`Move ${item.title} to the next free ${stayUnit(item)}`} onClick={() => act('move')}><CalendarClock aria-hidden="true" />Move</button>
      <button type="button" className="text-button" disabled={busy} aria-label={`Skip ${item.title}`} onClick={() => act('skip')}><SkipForward aria-hidden="true" />Skip this one</button>
    </span>
  )
}
