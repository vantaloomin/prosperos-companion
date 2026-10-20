import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, Circle } from 'lucide-react'
import { api } from '../../api'
import type { View } from '../../companion'
import type { Connection } from '../../types'
import { useHardware } from '../settings/models/hardware'
import { usePhoneStatus } from '../phone/phoneAccess'
import { welcomeLede, welcomeSteps, type SetUp, type WelcomeStep } from './welcomeSteps'
import { RealismPresets } from '../settings/RealismPresets'
import { ConfirmDownload } from '../ready/ConfirmDownload'
import { DownloadProgress } from '../ready/DownloadProgress'
import { isActive, modelOf, offered, type ReadyView } from '../ready/readyText'
import { useReady } from '../ready/useReady'
import { BackTo, FeelsLike } from './WorldArrival'
import { arrivalLede, useArrival, type Arrival } from './arrivalText'
import { useWatchActions } from '../watch/useObserver'

/** The first screen with no companion: connect the model they think with, then create them. */
export function Welcome({ go }: { go: (view: View) => void }) {
  // Shares the Settings cache entry, so saving a model there ticks the first step here.
  const connection = useQuery({ queryKey: ['connection'], queryFn: () => api<{ connection: Connection | null }>('/connection').then((data) => data.connection) })
  const remote = !!usePhoneStatus().data?.remote
  const ready = useReady(!remote).data
  const setUp = setUpState(ready, !!(connection.isSuccess && connection.data), remote)
  const builtin = builtinName(ready)
  // Once "Set it up for me" is part of this computer's story, step 1 and the lede keep its "get" wording.
  const getWording = ready?.status === 'ready'
  const steps = welcomeSteps(connection.isSuccess ? connection.data : undefined, setUp, builtin, getWording)
  const arrival = useArrival()
  return (
    <section className="welcome">
      <WelcomeHeader arrival={arrival} lede={welcomeLede(getWording ? 'active' : setUp)} />
      <ol className="welcome-steps">
        {steps.map((step) => <Step key={step.id} step={step} setUp={step.id === 'model' ? setUp : null} ready={ready} go={go} />)}
      </ol>
      <Feel arrival={arrival} go={go} />
      <WatchInstead go={go} />
      {!remote && !arrival && <HardwareNote />}
    </section>
  )
}

/** What this computer can run: first-install advice, so not shown to a user arriving in another world (Iris). */
function HardwareNote() {
  const hardware = useHardware()
  if (!hardware.data) return null
  return (
    <div className="welcome-hardware subtle">
      <p>On this computer: {hardware.data.can_run.join(' ')}</p>
      {hardware.data.warnings.length > 0 && <p>Settings &gt; Models has {hardware.data.warnings.length === 1 ? 'a warning' : 'warnings'} about the models you set up.</p>}
    </div>
  )
}

/** Where they are when they just arrived in a new world; the app's name on a first run. */
function WelcomeHeader({ arrival, lede }: { arrival: Arrival | null; lede: string }) {
  return (<>
    <p className="eyebrow">{arrival ? `New world · ${arrival.city}` : 'Prospero Companion'}</p>
    <h1>Meet someone new</h1>
    <p className="lede">{arrival ? arrivalLede(arrival) : lede}</p>
  </>)
}

/** How it should feel: asked on the first run; in a world after that, the user's preset said once with a way out. */
function Feel({ arrival, go }: { arrival: Arrival | null; go: (view: View) => void }) {
  if (arrival) return <>{arrival.previous && <BackTo world={arrival.previous} />}<FeelsLike go={go} /></>
  // Wolfenstein-style presets (Vanta, 2026-10-10): one is already picked, so this never holds anything up.
  return <RealismPresets heading="welcome-presets-heading" title="How should it feel?"
    intro="One is picked for you. Tap another if you like; you can change it any time in Settings > Realism." />
}

/** Step 1's choice when this computer can run a model: set it up here, or use a service. */
function SetUpButtons({ view, go, step }: { view: ReadyView; go: (view: View) => void; step: WelcomeStep }) {
  const [asking, setAsking] = useState(false)
  return (
    <div className="form-actions">
      <button type="button" className="button primary" onClick={() => setAsking(true)}>Set it up for me</button>
      <button type="button" className="text-button" onClick={() => go(step.view)}>Use a service instead</button>
      {asking && <ConfirmDownload view={view} onClose={() => setAsking(false)} />}
    </div>
  )
}

function setUpState(ready: ReadyView | undefined, connected: boolean, remote: boolean): SetUp {
  if (!offered(ready, connected, remote)) return null
  if (ready?.status === 'cancelled') return 'cancelled'
  return isActive(ready) ? 'active' : 'offer'
}

function Step({ step, setUp, ready, go }: { step: WelcomeStep; setUp: SetUp; ready?: ReadyView; go: (view: View) => void }) {
  return (
    <li className={step.done ? 'done' : undefined}>
      {step.done ? <CheckCircle2 aria-hidden="true" /> : <Circle aria-hidden="true" />}
      <div>
        <p className="step-label">{step.label}<span className="visually-hidden">{step.done ? ', done' : ', not done yet'}</span></p>
        {showsProgress(setUp, ready) ? <DownloadProgress view={ready as ReadyView} /> : <p className="subtle">{step.detail}</p>}
        {setUp === 'offer' && ready && <SetUpButtons view={ready} go={go} step={step} />}
        {step.action && <button type="button" className={step.primary ? 'button primary' : 'text-button'} onClick={() => go(step.view)}>{step.action}</button>}
      </div>
    </li>
  )
}

/** The built-in model's name once it does the chat job, so step 1 can say it runs on this computer. */
const builtinName = (ready?: ReadyView) => ready?.status === 'ready' && ready.in_use ? modelOf(ready).name : ''
const showsProgress = (setUp: SetUp, ready?: ReadyView) => !!setUp && setUp !== 'offer' && isActive(ready)

/** Observer mode (companion/observer.py): no companion is needed to watch the town go on. */
function WatchInstead({ go }: { go: (view: View) => void }) {
  const { change } = useWatchActions()
  const [error, setError] = useState('')
  const watch = async () => {
    try { await change({ watching: true }); go('watch') } catch (failure) { setError(failure instanceof Error ? failure.message : 'That did not work. Try again.') }
  }
  return (
    <div className="welcome-watch">
      <p className="subtle">Or <button type="button" className="text-button inline" onClick={() => void watch()}>just watch this city</button> for a while, following whoever you like, and step in when you want.</p>
      {error && <p className="error-text" role="alert">{error}</p>}
    </div>
  )
}
