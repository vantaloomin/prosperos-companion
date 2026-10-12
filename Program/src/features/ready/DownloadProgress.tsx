import { useState } from 'react'
import { cardLine, heading, milestone, modelOf, percent, progressLine, type ReadyView } from './readyText'
import { useReadyActions } from './useReady'

/** One progress row for the welcome step, the Models card and anywhere else the download shows. A phone can pause
 * and resume but not cancel: deleting a 10 GB download from a phone is too easy to do by mistake (Iris). */
export function DownloadProgress({ view, phone = false, titled = true }: { view: ReadyView; phone?: boolean; titled?: boolean }) {
  const actions = useReadyActions()
  const [error, setError] = useState('')
  const value = percent(view)
  const announced = useAnnounced(value)
  const act = (work: () => Promise<unknown>) => async () => {
    setError('')
    try { await work() } catch (failure) { setError(failure instanceof Error ? failure.message : 'That did not work.') }
  }
  const model = modelOf(view)
  if (view.status === 'cancelled') {
    return (
      <div className="download-progress">
        <p role="status">Download cancelled. <button type="button" className="text-button" onClick={act(() => actions.start(model.key))}>Undo</button></p>
      </div>
    )
  }
  return (
    <div className="download-progress">
      {titled && <p className="download-title">{heading(view)}</p>}
      <p className={lineClass(view)}>{titled ? progressLine(view) : cardLine(view)}</p>
      <div className="download-bar" role="progressbar" aria-label={heading(view)} aria-valuemin={0} aria-valuemax={100} aria-valuenow={value}
        aria-valuetext={`${(view.received / 1e9).toFixed(1)} of ${(view.total / 1e9).toFixed(1)} gigabytes`}>
        <span style={{ width: `${value}%` }} />
      </div>
      <p className="visually-hidden" aria-live="polite">{announced ? `${model.name} ${announced}% downloaded.` : ''}</p>
      {view.status !== 'checking' && <Controls view={view} phone={phone} act={act} />}
      {error && <p className="download-short" role="alert">{error}</p>}
    </div>
  )
}

const lineClass = (view: ReadyView) => `subtle download-line${view.status === 'failed' ? ' stopped' : ''}`

type Act = (work: () => Promise<unknown>) => () => Promise<void>

function Controls({ view, phone, act }: { view: ReadyView; phone: boolean; act: Act }) {
  const actions = useReadyActions()
  const key = modelOf(view).key
  return <div className="form-actions">
    {view.status === 'paused' || view.status === 'failed'
      ? <button type="button" className="text-button" onClick={act(() => actions.start(key))}>Resume</button>
      : <button type="button" className="text-button" onClick={act(actions.pause)}>Pause</button>}
    {!phone && <button type="button" className="text-button" onClick={act(actions.cancel)}>Cancel</button>}
  </div>
}

/** The last quarter reached since the row appeared, so a screen reader hears 25, 50, 75 and 100 and nothing between:
 * the live region's text changes only when a quarter is passed. */
function useAnnounced(value: number) {
  const [start] = useState(() => milestone(value))
  const reached = milestone(value)
  return reached > start ? reached : 0
}
