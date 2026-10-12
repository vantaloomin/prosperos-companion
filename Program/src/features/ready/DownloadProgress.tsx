import { useState } from 'react'
import { heading, milestone, modelOf, percent, progressLine, type ReadyView } from './readyText'
import { useReadyActions } from './useReady'

/** One progress row for the welcome step, the Models card and anywhere else the download shows. A phone can pause
 * and resume but not cancel: deleting a 10 GB download from a phone is too easy to do by mistake (Iris). */
export function DownloadProgress({ view, phone = false }: { view: ReadyView; phone?: boolean }) {
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
  const stopped = view.status === 'paused' || view.status === 'failed'
  return (
    <div className="download-progress">
      <p className="download-title">{heading(view)}</p>
      <p className="subtle download-line">{progressLine(view)}</p>
      <div className="download-bar" role="progressbar" aria-label={heading(view)} aria-valuemin={0} aria-valuemax={100} aria-valuenow={value}
        aria-valuetext={`${(view.received / 1e9).toFixed(1)} of ${(view.total / 1e9).toFixed(1)} gigabytes`}>
        <span style={{ width: `${value}%` }} />
      </div>
      <p className="visually-hidden" aria-live="polite">{announced ? `${model.name} ${announced}% downloaded.` : ''}</p>
      {view.status !== 'checking' && <div className="form-actions">
        {stopped
          ? <button type="button" className="text-button" onClick={act(() => actions.start(model.key))}>Resume</button>
          : <button type="button" className="text-button" onClick={act(actions.pause)}>Pause</button>}
        {!phone && <button type="button" className="text-button" onClick={act(actions.cancel)}>Cancel</button>}
      </div>}
      {error && <p className="download-short" role="alert">{error}</p>}
    </div>
  )
}

/** The last quarter reached since the row appeared, so a screen reader hears 25, 50, 75 and 100 and nothing between:
 * the live region's text changes only when a quarter is passed. */
function useAnnounced(value: number) {
  const [start] = useState(() => milestone(value))
  const reached = milestone(value)
  return reached > start ? reached : 0
}
