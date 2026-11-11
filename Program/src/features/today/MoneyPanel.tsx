import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { MoneyView } from '../../types'
import { ErrorNotice } from '../../components/ErrorNotice'
import { FoldRow } from '../../components/Rows'
import { InfoTip } from '../../components/InfoTip'
import { firstName } from '../character/panelText'
import { boughtFor, costsText, cycleText, goalText, moodOfMoney, ownerText, paydayText, perText, rentText, shortDate, workText } from './moneyText'

/** The companion's budget this pay period: worked out from their pay and city, never from a model. One fold row on
 * Today whose summary is the money line ("About $116 left to spend until payday"). */
export function MoneyPanel({ name, go }: { name: string; go: () => void }) {
  const money = useQuery({ queryKey: ['today', 'money'], queryFn: () => api<MoneyView>('/today/money') })
  if (money.isPending) return null
  if (money.isError) return <div className="fold-extra"><ErrorNotice error={money.error} /></div>
  const view = money.data
  if (!view.available) return <FoldRow summary="Money" sub={view.reason}><div className="fold-extra" /></FoldRow>
  return (
    <FoldRow summary={moodOfMoney(view, firstName(name))} sub={paydayText(view)}>
      <div className="fold-extra">
        <ul className="plain-list money-list">
          <li>{[workText(view), cycleText(view)].filter(Boolean).join(' ')}</li>
          <li>{rentText(view)}</li>
          {ownerText(view) && <li>{ownerText(view)}</li>}
          {view.budget.upkeep > 0 && <li>Pets and getting around: about {view.text.upkeep} {perText(view)}.</li>}
          <li>{costsText(view)}</li>
          {view.splurge && <li>Splurged on {view.splurge.label} ({shortDate(view.splurge.on)}).</li>}
          {view.bought.map((item) => <li key={`${item.on}-${item.label}`}>{boughtFor(item.for)}, they {item.shown ?? item.label} ({shortDate(item.on)}).</li>)}
          {view.surprise && <li>Unexpected expense: {view.surprise.label} ({shortDate(view.surprise.on)}).</li>}
          {view.cant_afford.length > 0 && <li>Can't afford right now: {view.cant_afford.join(', ')}.</li>}
        </ul>
        <div className="field">
          <span className="label-row money-goal-label"><label htmlFor="money-goal">{goalText(view)}</label><InfoTip id="money-about" label="Money" text="Worked out from their work and their city's rents." /></span>
          <progress id="money-goal" className="money-goal" max={1} value={view.goal.share}>{Math.round(view.goal.share * 100)}%</progress>
        </div>
        <p className="row-sub"><button type="button" className="text-button inline" onClick={go}>Change their work, home or goal</button></p>
      </div>
    </FoldRow>
  )
}
