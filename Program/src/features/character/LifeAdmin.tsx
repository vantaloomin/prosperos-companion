import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { AdminView } from '../../types'
import { Loading } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { AdminList } from '../today/AdminList'
import { ADMIN_KEY } from '../today/adminText'
import { dayText } from '../today/outingText'
import { calendarDay } from '../../when'
import { panelTitle } from './panelText'
import { WeddingPlan } from './WeddingPlan'

/** The companion's life admin in plain words: what is on the list, what comes due later and what got done lately. */
export function LifeAdmin({ name }: { name: string }) {
  const admin = useQuery({ queryKey: ADMIN_KEY, queryFn: () => api<AdminView>('/life/admin') })
  const view = admin.data
  return (
    <section id="life-admin" className="home-panel admin-panel" aria-labelledby="admin-heading">
      <h2 id="admin-heading">{panelTitle(name, 'life admin')}</h2>
      <p className="subtle">The dentist, taxes, the lease and the week's errands, as their city does them. Picked for them; move anything to another day.</p>
      {admin.isPending && <Loading label="Loading their life admin" />}
      {admin.isError && <ErrorNotice error={admin.error} />}
      {view && <>
        <ul className="admin-state">{view.state.map((line) => <li key={line}>{line}</li>)}</ul>
        {view.wedding?.status === 'planned' && <WeddingPlan plan={view.wedding} name={name} />}
        {view.meter !== null && <p className="subtle">On top of things: {view.meter} out of 100</p>}
        {view.upcoming.length > 0 && <><h3>Coming up</h3><AdminList items={view.upcoming} /></>}
        {view.later.length > 0 && <>
          <h3>Later on</h3>
          <dl className="admin-later">{view.later.map((item) => <div key={item.kind}><dt>{item.title}</dt><dd>{item.due ? `Due ${dayText(item.local_date)}` : `Around ${calendarDay(item.local_date)}`}</dd></div>)}</dl>
        </>}
        {view.done.length > 0 && <details className="wardrobe-group">
          <summary>Done lately <span className="subtle">({view.done.length})</span></summary>
          <AdminList items={view.done} done fold={null} />
        </details>}
      </>}
    </section>
  )
}
