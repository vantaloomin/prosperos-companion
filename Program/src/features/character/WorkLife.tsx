import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { WorkLifeView } from '../../types'
import { Loading } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { AdminList } from '../today/AdminList'
import { calendarDay } from '../../when'
import { WORK_KEY, eventDay, eventText } from './workText'

/** The companion's job in plain words: the week, the project, late nights, time off and what changed lately. Nothing
 * for a companion without work in their week. */
export function WorkLife({ name }: { name: string }) {
  const query = useQuery({ queryKey: WORK_KEY, queryFn: () => api<{ work: WorkLifeView | null }>('/life/work') })
  const view = query.data?.work
  if (query.isSuccess && !view) return null
  return (
    <section id="work-life" className="home-panel work-panel" aria-labelledby="work-heading">
      <h2 id="work-heading">{name}'s work life</h2>
      <p className="subtle">Busy weeks, slow weeks, a project on the go and a raise once a year, as their job and city do them. Picked for them; move a late night like anything on their calendar.</p>
      {query.isPending && <Loading label="Loading their work life" />}
      {query.isError && <ErrorNotice error={query.error} />}
      {view && <WorkDetails view={view} />}
    </section>
  )
}

function WorkDetails({ view }: { view: WorkLifeView }) {
  return <>
    <ul className="admin-state">{view.state.map((line) => <li key={line}>{line}</li>)}</ul>
    {view.meter && <p className="subtle">Vacation: {view.meter.vacation_used} of {view.meter.vacation_total} days taken this year ({view.meter.allowance} a year where they live). Pay: {view.meter.pay_percent}% of where they started.</p>}
    {view.late_nights.length > 0 && <><h3>Late nights</h3><AdminList items={view.late_nights} /></>}
    {view.vacation.length > 0 && <>
      <h3>Time off</h3>
      <p className="subtle">{view.vacation.map((day) => calendarDay(day, { weekday: true })).join(', ')}</p>
    </>}
    {view.events.length > 0 && <details className="wardrobe-group">
      <summary>What changed <span className="subtle">({view.events.length})</span></summary>
      <dl className="admin-later">{view.events.map((event) => <div key={event.id}><dt>{eventText(event)}</dt><dd>{eventDay(event)}</dd></div>)}</dl>
    </details>}
  </>
}
