import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { WorkLifeView } from '../../types'
import { Loading } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { AdminList } from '../today/AdminList'
import { WORK_KEY, eventDay, eventText, meterText, timeOffText } from './workText'

/** The companion's job in plain words: the week, the project, late nights, time off and what changed lately. Nothing
 * for a companion without work in their week. */
export function WorkLife({ name }: { name: string }) {
  const query = useQuery({ queryKey: WORK_KEY, queryFn: () => api<{ work: WorkLifeView | null }>('/life/work') })
  const view = query.data?.work
  if (query.isSuccess && !view) return null
  return (
    <section id="work-life" className="home-panel work-panel" aria-labelledby="work-heading">
      <h2 id="work-heading">{name.split(' ')[0]}'s work life</h2>
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
    {view.meter && <p className="subtle">{meterText(view.meter)}</p>}
    {view.late_nights.length > 0 && <><h3>Late nights</h3><AdminList items={view.late_nights} inWorkPanel /></>}
    {view.level > 0 && view.status === 'working' && <>
      <h3>Time off</h3>
      <p className="subtle">{timeOffText(view.vacation)}</p>
    </>}
    {view.events.length > 0 && <details className="wardrobe-group">
      <summary>What changed <span className="subtle">({view.events.length})</span></summary>
      <ul className="admin-state work-events">{view.events.map((event) => <li key={event.id}><span className="subtle">{eventDay(event)} · </span>{eventText(event)}</li>)}</ul>
    </details>}
  </>
}
