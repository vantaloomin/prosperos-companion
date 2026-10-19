import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../../api'
import { COMPANION_KEY, useWorkspaceSettings } from '../../companion'
import type { Consequence, ReasonMove } from '../../types'
import { storyDate } from './storyText'
import { LATELY_KEY, markLine, outcomeIntro, outcomeRow } from '../character/turnsText'
import { todayIso } from '../character/money'

/** "Why it went this way": each way a turning could have gone, its odds and what moved them, and a way to make
 * it go another way. Loads only when opened, and shows only with Hidden values > odds turned on. `settled` when it can't
 * be changed any more (they already moved in): the odds without the buttons. */
export function WhyItWent({ id, possibleOnly = false, settled = false, summary = 'Why it went this way', name = '' }: { id: string; possibleOnly?: boolean; settled?: boolean; summary?: string; name?: string }) {
  return useWorkspaceSettings().data?.show_odds === true ? <Odds id={id} possibleOnly={possibleOnly} settled={settled} summary={summary} name={name} /> : null
}

function Odds({ id, possibleOnly, settled, summary, name }: { id: string; possibleOnly: boolean; settled: boolean; summary: string; name: string }) {
  const [open, setOpen] = useState(false)
  const [failed, setFailed] = useState('')
  const client = useQueryClient()
  const key = ['consequence', id]
  const outcome = useQuery({ queryKey: key, queryFn: () => api<Consequence>(`/life/consequences/${id}`), enabled: open })
  const change = async (option: number) => {
    setFailed('')
    try {
      client.setQueryData(key, await api<Consequence>(`/life/consequences/${id}/change`, { option }))
    } catch (error) {
      // Already led to a later stage: the refreshed outcome says so as a hint, in place of the buttons.
      const fresh = await outcome.refetch()
      if (!fresh.data?.settled) setFailed(error instanceof Error ? error.message : String(error))
      return
    }
    await Promise.all([['storylines'], ['reactions'], ['chapters'], ['circle'], ['breakup'], ['steps'], LATELY_KEY, COMPANION_KEY].map((queryKey) => client.invalidateQueries({ queryKey })))
  }
  return (
    <details className="why-it-went" onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary>{summary}</summary>
      {outcome.data && (
        <>
          <p className="subtle">{outcomeIntro(outcome.data.choice, outcome.data.label, name)}{outcome.data.picked_by === 'user' ? ': you picked how it went.' : '.'}</p>
          <ul className="plain-list">
            {outcome.data.options.map((item) => (
              <li key={item.option}>
                <p>
                  <strong>{Math.round(item.odds * 100)}%</strong> {outcomeRow(outcome.data.choice, item.option, item.label)}
                  {item.option === outcome.data.picked && <span className="subtle"> (what happened)</span>}
                </p>
                <Reasons reasons={item.reasons} moves={item.moves} />
                {item.option !== outcome.data.picked && !settled && !outcome.data.settled && !(possibleOnly && item.odds === 0) && (
                  <button type="button" className="text-button" onClick={() => void change(item.option)}>Make it go this way</button>
                )}
              </li>
            ))}
          </ul>
          {settled && <p className="subtle">Already happened, so this one can't be changed.</p>}
          {!settled && outcome.data.settled && <p className="subtle">{outcome.data.settled}</p>}
          <Marks marks={outcome.data.marks} />
        </>
      )}
      {failed && <p className="subtle" role="alert">{failed}</p>}
      {outcome.isError && <p className="subtle">This outcome could not be loaded. {String(outcome.error.message)}</p>}
    </details>
  )
}

/** "What it left, for a while", only what still lasts (an effect whose day has passed is left out). */
function Marks({ marks }: { marks: Consequence['marks'] }) {
  const today = todayIso()
  const lasting = marks.filter((mark) => mark.until >= today)
  if (lasting.length === 0) return null
  return (
    <>
      <p className="subtle marks-lead">What it left, for a while:</p>
      <ul className="plain-list">
        {lasting.map((mark) => (
          <li key={mark.holder + mark.kind + mark.note} className="subtle">
            {markLine(mark.ripple ? `it reached ${mark.who ?? 'another companion'}, who is close to them` : mark.note, storyDate(mark.until))}
          </li>
        ))}
      </ul>
    </>
  )
}

const LEADS: [ReasonMove, string][] = [
  ['possible', 'Possible because'], ['more', 'More likely because'], ['less', 'Less likely because'], ['out', 'Ruled out because'],
]
const SHOWN = 3

/** An option's reasons under the way each one pushed it ("Less likely because Mira doesn't feel close enough yet"),
 * so a reason that lowered the odds never reads as one for them. A ruled-out option shows only why it was ruled out.
 * Outcomes from before v0.13 keep the plain list. */
export function Reasons({ reasons, moves }: { reasons: string[]; moves?: ReasonMove[] }) {
  if (reasons.length === 0) return null
  if (moves?.length !== reasons.length) return <p className="subtle">{reasons.join('. ')}.</p>
  const leads = moves.includes('out') ? LEADS.filter(([way]) => way === 'out') : LEADS
  return (
    <div>
      {leads.map(([way, lead]) => {
        const these = reasons.filter((_, index) => moves[index] === way)
        return these.length > 0 && <ReasonGroup key={way} lead={lead} reasons={these} />
      })}
    </div>
  )
}

function ReasonGroup({ lead, reasons }: { lead: string; reasons: string[] }) {
  const [all, setAll] = useState(false)
  if (all || reasons.length <= SHOWN) return <p className="subtle reason-group">{lead} {listed(reasons)}.</p>
  return (
    <p className="subtle reason-group">
      {lead} {reasons.slice(0, SHOWN).join(', ')} and{' '}
      <button type="button" className="text-button" onClick={() => setAll(true)}>{reasons.length - SHOWN} more</button>.
    </p>
  )
}

function listed(items: string[]): string {
  return items.length < 2 ? items.join('') : `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`
}
