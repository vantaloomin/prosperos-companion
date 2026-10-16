import { useState, type MouseEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { COMPANION_KEY } from '../../companion'
import type { StepsView } from '../../types'
import { Field, Toggle } from '../../components/Fields'
import { Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { WhyItWent } from '../today/WhyItWent'
import { firstName } from './panelText'
import { STEPS_KEY, askText, howText, movingText, plannedText, stepDate } from './stepsText'

/** Where you and them stand (companion/life/steps.py): one plain line, the steps so far, what came up lately and,
 * for a friend, the "just friends" lock. The app moves it on; the user can set it here. Nothing for a mentor or family. */
export function Steps({ name }: { name: string }) {
  const client = useQueryClient()
  const query = useQuery({ queryKey: STEPS_KEY, queryFn: () => api<StepsView>('/life/steps') })
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
  return (
    <section id="steps" className="home-panel steps-panel" aria-labelledby="steps-heading">
      <h2 id="steps-heading">You and {who}</h2>
      <p className="steps-line">{view.text}</p>
      <Field label="Where things stand" hint={`Picked and moved on by the app, as ${who} brings things up and you answer. Set it yourself any time; moving it back takes the later steps back.`}>
        {(id, describedBy) => (
          <select id={id} aria-describedby={describedBy} value={view.step} onChange={(event) => void save({ step: event.target.value })}>
            {view.ladder_steps?.map((item) => <option key={item.step} value={item.step}>{item.label}</option>)}
          </select>
        )}
      </Field>
      <StepsSoFar view={view} name={name} />
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
      {moving.consequence_id && <WhyItWent id={moving.consequence_id} />}
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
