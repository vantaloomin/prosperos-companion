import { useEffect, useState, type MouseEvent } from 'react'
import { CloudRain, HeartCrack, Undo2 } from 'lucide-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { COMPANION_KEY } from '../../companion'
import type { StepsView } from '../../types'
import { Field, Toggle } from '../../components/Fields'
import { Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { WhyItWent } from '../today/WhyItWent'
import { firstName } from './panelText'
import { Wedding } from './WeddingPlan'
import { STEPS_KEY, askText, howText, movingText, plannedText, stepDate } from './stepsText'
import { apartHint, BREAKUP_KEY, breakupLine, isApart, mendLabel, mendedText, type BreakupView } from './breakupText'
import { UNDO_MS } from '../profile/roughPatchText'

/** Where you and them stand (companion/life/steps.py): one plain line, the steps so far, what came up lately and,
 * for a friend, the "just friends" lock. The app moves it on; the user can set it here. Nothing for a mentor or family. */
export function Steps({ name }: { name: string }) {
  const client = useQueryClient()
  const query = useQuery({ queryKey: STEPS_KEY, queryFn: () => api<StepsView>('/life/steps') })
  const breakup = useQuery({ queryKey: BREAKUP_KEY, queryFn: () => api<BreakupView>('/life/breakup') })
  const [error, setError] = useState('')
  const view = query.data
  if (query.isError) return <ErrorNotice error={query.error} />
  if (!view?.ladder) return null
  const save = async (change: { step?: string; just_friends?: boolean }) => {
    setError('')
    try {
      client.setQueryData(STEPS_KEY, await api<StepsView>('/life/steps', change, 'PUT'))
      void client.invalidateQueries({ queryKey: COMPANION_KEY })
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'That was not saved.') }
  }
  const who = firstName(name)
  // On a break or broken up (companion/life/breakups.py) the summary says so, and the steps wait.
  const apart = isApart(breakup.data)
  const hint = apartHint(breakup.data) ||
    `Picked and moved on by the app, as ${who} brings things up and you answer. Set it yourself any time; moving it back takes the later steps back.`
  return (
    <section id="steps" className="home-panel steps-panel" aria-labelledby="steps-heading">
      <h2 id="steps-heading">You and {who}</h2>
      <p className="steps-line">{apart && breakup.data?.summary ? breakup.data.summary : view.text}</p>
      <BreakupLine name={name} view={breakup.data} />
      <Field label="Where things stand" hint={hint}>
        {(id, describedBy) => (
          <select id={id} aria-describedby={describedBy} value={view.step} disabled={apart} onChange={(event) => void save({ step: event.target.value })}>
            {view.ladder_steps?.map((item) => <option key={item.step} value={item.step}>{item.label}</option>)}
          </select>
        )}
      </Field>
      <StepsSoFar view={view} name={name} />
      <Wedding name={name} />
      {view.can_fall && (
        <Toggle label="Just friends" checked={view.just_friends} onChange={(just_friends) => void save({ just_friends })}
          hint={`On: ${who} stays a friend. Off: a close friend can fall for you now and then, if Friends can fall for you is on in Settings > Realism.`} />
      )}
      {error && <Notice tone="error">{error}</Notice>}
    </section>
  )
}

/** The Living together step's detail: where you live together, or the move planned. Waiting on the user to move cities,
 * it links to where they change it: their persona's home on Worlds. */
function MovingLine({ moving, name }: { moving: NonNullable<StepsView['moving_in']>; name: string }) {
  const change = (event: MouseEvent) => {
    event.preventDefault()
    window.history.pushState({ focus: 'persona-home' }, '', '#worlds')
    window.dispatchEvent(new PopStateEvent('popstate', { state: { focus: 'persona-home' } }))
  }
  return (
    <div className="steps-detail">
      <p>{movingText(moving, name)}{moving.status === 'waiting' && <> <a className="text-button inline" href="#worlds" onClick={change}>Change your home city</a> when you're ready.</>}</p>
      {moving.consequence_id && <WhyItWent id={moving.consequence_id} settled={moving.status === 'moved'} />}
    </div>
  )
}

/** The steps so far with their dates, what came up lately and (with odds shown) what is planned. */
function StepsSoFar({ view, name }: { view: StepsView; name: string }) {
  return <>
    {view.steps && view.steps.length > 1 && (
      <ol className="steps-list">
        {view.steps.map((item) => (
          <li key={item.step}>
            <strong>{item.label}</strong> <span className="subtle">{item.how === 'history' ? howText(item.how, name) : `${stepDate(item.on)} · ${howText(item.how, name)}`}</span>
            {item.step === 'moving_in' && view.moving_in && <MovingLine moving={view.moving_in} name={name} />}
          </li>
        ))}
      </ol>
    )}
    {view.asks && view.asks.length > 0 && (
      <details className="wardrobe-group">
        <summary>What came up lately <span className="subtle">({view.asks.length})</span></summary>
        <ul className="plain-list">
          {view.asks.map((ask) => (
            <li key={ask.id}>
              <p><span className="subtle">{stepDate(ask.on)} · </span>{askText(ask, name)}</p>
              {ask.consequence_id && <WhyItWent id={ask.consequence_id} />}
            </li>
          ))}
        </ul>
      </details>
    )}
    {view.planned && (
      <div className="steps-planned">
        <p className="subtle">{plannedText(view.planned, name)}</p>
        {view.planned.consequence_id && <WhyItWent id={view.planned.consequence_id} />}
      </div>
    )}
  </>
}

/** Breaks and breakups (companion/life/breakups.py): "Things are strained", "They're thinking about a break", a break or
 * the breakup, with "Why it went this way" for each roll (Hidden values > odds) and the override, with Undo after. */
function BreakupLine({ name, view }: { name: string; view: BreakupView | undefined }) {
  const client = useQueryClient()
  const [mended, setMended] = useState<{ id: string; text: string } | null>(null)
  useEffect(() => {
    if (!mended) return
    const timer = window.setTimeout(() => setMended(null), UNDO_MS)
    return () => window.clearTimeout(timer)
  }, [mended])
  const act = async (id: string, action: 'mend' | 'undo', text = '') => {
    client.setQueryData(BREAKUP_KEY, await api<BreakupView>(`/life/breakup/${id}/${action}`, {}))
    setMended(action === 'mend' ? { id, text } : null)
    void client.invalidateQueries({ queryKey: STEPS_KEY })
  }
  if (mended) return (
    <p className="breakup-line" role="status" aria-live="polite">
      <span>{mended.text}</span>
      <button type="button" className="text-button" onClick={() => void act(mended.id, 'undo')}><Undo2 aria-hidden="true" />Undo</button>
    </p>
  )
  const line = breakupLine(view, name)
  if (!view?.id || !line.status) return null
  const Glyph = view.stage === 'ended' ? HeartCrack : CloudRain
  const id = view.id
  return (
    <div className="breakup-block">
      <div className="breakup-line">
        <Glyph aria-hidden="true" />
        <p className="breakup-text">{line.status}{line.detail && <small className="subtle">{line.detail}</small>}</p>
        {view.mendable && <button type="button" className="text-button" onClick={() => void act(id, 'mend', mendedText(view))}>{mendLabel(view)}</button>}
      </div>
      {view.odds.map((odds) => <WhyItWent key={odds} id={odds} />)}
    </div>
  )
}
