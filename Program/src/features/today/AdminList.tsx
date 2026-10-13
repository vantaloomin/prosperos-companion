import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { CalendarClock } from 'lucide-react'
import { api } from '../../api'
import type { AdminItem } from '../../types'
import { Notice } from '../../components/Feedback'
import { ADMIN_KEY, adminMoved, adminTags, adminWhen } from './adminText'

/** Lists longer than this show their first few, with the rest a tap away (Iris's review). */
export const FOLD = 3

/** Appointments, errands and chores (companion/life/admin.py), each movable to another day. Shared by Today's Plans
 * and the Character page's Life admin panel. */
export function AdminList({ items, done = false, fold = FOLD }: { items: AdminItem[]; done?: boolean; fold?: number | null }) {
  const client = useQueryClient()
  const [open, setOpen] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const move = async (id: string) => {
    setError('')
    setBusy(id)
    try { await api(`/life/admin/${id}/move`, {}) } catch (failure) { setError(failure instanceof Error ? failure.message : 'It could not move.') }
    setBusy('')
    void client.invalidateQueries({ queryKey: ADMIN_KEY })
    void client.invalidateQueries({ queryKey: ['today'] })
  }
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
                {adminTags(item).map((tag) => <span key={tag} className="badge">{tag}</span>)}
              </div>
              <div className="admin-when">
                <p className="subtle">{adminWhen(item)}</p>
                {!done && item.movable && <button type="button" className="text-button" disabled={busy === item.id} aria-label={`Move ${item.title} to another day`} onClick={() => void move(item.id)}><CalendarClock aria-hidden="true" />Move to another day</button>}
              </div>
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
