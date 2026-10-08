import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, Circle } from 'lucide-react'
import { api } from '../../api'
import type { View } from '../../companion'
import type { Connection } from '../../types'
import { useHardware } from '../settings/models/hardware'
import { usePhoneStatus } from '../phone/phoneAccess'
import { welcomeSteps } from './welcomeSteps'

/** The first screen with no companion: connect the model they think with, then create them. */
export function Welcome({ go }: { go: (view: View) => void }) {
  // Shares the Settings cache entry, so saving a model there ticks the first step here.
  const connection = useQuery({ queryKey: ['connection'], queryFn: () => api<{ connection: Connection | null }>('/connection').then((data) => data.connection) })
  const steps = welcomeSteps(connection.isSuccess ? connection.data : undefined)
  const remote = !!usePhoneStatus().data?.remote
  const hardware = useHardware()
  return (
    <section className="welcome">
      <p className="eyebrow">Prospero Companion</p>
      <h1>Meet someone new</h1>
      <p className="lede">Two steps: connect the text model your companion thinks with, then create them. You can change everything later.</p>
      <ol className="welcome-steps">
        {steps.map((step) => (
          <li key={step.id} className={step.done ? 'done' : undefined}>
            {step.done ? <CheckCircle2 aria-hidden="true" /> : <Circle aria-hidden="true" />}
            <div>
              <p className="step-label">{step.label}<span className="visually-hidden">{step.done ? ', done' : ', not done yet'}</span></p>
              <p className="subtle">{step.detail}</p>
              {step.action && <button type="button" className={step.primary ? 'button primary' : 'text-button'} onClick={() => go(step.view)}>{step.action}</button>}
            </div>
          </li>
        ))}
      </ol>
      {!remote && hardware.data && <div className="welcome-hardware subtle">
        <p>On this computer: {hardware.data.can_run.join(' ')}</p>
        {hardware.data.warnings.length > 0 && <p>Settings &gt; Models has {hardware.data.warnings.length === 1 ? 'a warning' : 'warnings'} about the models you set up.</p>}
      </div>}
    </section>
  )
}
