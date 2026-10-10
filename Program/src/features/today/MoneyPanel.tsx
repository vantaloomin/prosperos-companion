import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { MoneyView } from '../../types'
import { ErrorNotice } from '../../components/ErrorNotice'
import { boughtFor, cycleText, goalText, moodOfMoney, paydayText, rentText, shortDate, workText } from './moneyText'

/** The companion's budget this pay period: worked out from their pay and city, never from a model. */
export function MoneyPanel({ name, go }: { name: string; go: () => void }) {
  const money = useQuery({ queryKey: ['today', 'money'], queryFn: () => api<MoneyView>('/today/money') })
  if (money.isPending) return null
  if (money.isError) return <section className="today-section" aria-labelledby="money-heading"><h2 id="money-heading">Money</h2><ErrorNotice error={money.error} /></section>
  const view = money.data
  return (
    <section className="today-section" aria-labelledby="money-heading">
      <h2 id="money-heading">Money</h2>
      {!view.available ? <p className="subtle">{view.reason}</p> : <>
        <p>{moodOfMoney(view, name)} {paydayText(view)}</p>
        <ul className="plain-list">
          <li>{workText(view)} {cycleText(view)}</li>
          <li>{rentText(view)}</li>
          {view.budget.upkeep > 0 && <li>Pets and getting around: about {view.text.upkeep} {view.period === 'month' ? 'a month' : 'a week'}.</li>}
          <li>Everyday costs about {view.text.essentials}, fun about {view.text.fun}, savings about {view.text.saving}.</li>
          {view.splurge && <li>Splurged on {view.splurge.label} ({shortDate(view.splurge.on)}).</li>}
          {view.bought.map((item) => <li key={`${item.on}-${item.label}`}>{boughtFor(item.for)}, they {item.label} ({shortDate(item.on)}).</li>)}
          {view.surprise && <li>Unexpected expense: {view.surprise.label} ({shortDate(view.surprise.on)}).</li>}
          {view.cant_afford.length > 0 && <li>Can't afford right now: {view.cant_afford.join(', ')}.</li>}
        </ul>
        <div className="field">
          <label htmlFor="money-goal">{goalText(view)}</label>
          <progress id="money-goal" className="money-goal" max={1} value={view.goal.share}>{Math.round(view.goal.share * 100)}%</progress>
        </div>
        <p className="subtle">Worked out from their work and their city's rents. <button type="button" className="text-button inline" onClick={go}>Change their work or goal</button></p>
      </>}
    </section>
  )
}
