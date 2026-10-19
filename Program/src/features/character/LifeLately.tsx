import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { LifeLately as LatelyView } from '../../types'
import { ErrorNotice } from '../../components/ErrorNotice'
import { storyDate } from '../today/storyText'
import { panelTitle } from './panelText'
import { LATELY_KEY } from './turnsText'

/** Their life lately (companion/life/big_turns.py): a big turn on its way (a course, a place they are buying,
 * retiring, a business, a health turn, caring for a parent) and the latest chapters that already happened. Nothing until there is one. */
export function LifeLately({ name }: { name: string }) {
  const query = useQuery({ queryKey: LATELY_KEY, queryFn: () => api<LatelyView>('/life/chapters/lately') })
  if (query.isError) return <ErrorNotice error={query.error} />
  const view = query.data
  if (!view || (!view.now.length && !view.lately.length)) return null
  return (
    <section id="life-lately" className="home-panel lately-panel" aria-labelledby="lately-heading">
      <h2 id="lately-heading">{panelTitle(name, 'life lately')}</h2>
      <p className="subtle">Big turns come on their own, as often as Life's big turns in Settings &gt; Realism says. Undo any of them on Today.</p>
      {view.now.length > 0 && <ul className="admin-state">{view.now.map((item) => <li key={item.id}><span className="subtle">Now · </span>{item.line}</li>)}</ul>}
      {view.lately.length > 0 && <>
        <h3>Lately</h3>
        <ul className="admin-state">{view.lately.map((item) => (
          <li key={item.id}><span className="subtle"><time dateTime={item.on}>{storyDate(item.on)}</time> · </span>{item.title}.</li>
        ))}</ul>
      </>}
    </section>
  )
}
