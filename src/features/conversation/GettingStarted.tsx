import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, Circle } from 'lucide-react'
import { api } from '../../api'
import type { View } from '../../companion'
import type { Companion, Connection } from '../../types'
import { setupSteps } from './setup'

/** Shown before the first message: what is needed to talk, what is optional, and nothing presented as failed. */
export function GettingStarted({ companion, go }: { companion: Companion; go: (view: View) => void }) {
  // Shares the Settings cache entry, so saving a connection there ticks the step here.
  const connection = useQuery({ queryKey: ['connection'], queryFn: () => api<{ connection: Connection | null }>('/connection').then((data) => data.connection) })
  const name = companion.version.name
  if (!connection.isSuccess) return null
  const steps = setupSteps(companion, connection.data)
  return (
    <section className="getting-started" aria-labelledby="getting-started-heading">
      <h2 id="getting-started-heading">This is the start of your conversation with {name}</h2>
      <ol>
        {steps.map((step) => (
          <li key={step.id} className={step.done ? 'done' : undefined}>
            {step.done ? <CheckCircle2 aria-hidden="true" /> : <Circle aria-hidden="true" />}
            <div>
              <p className="step-label">{step.label}{step.optional && <span className="subtle"> (optional)</span>}<span className="visually-hidden">{step.done ? ', done' : ', not done yet'}</span></p>
              <p className="subtle">{step.detail}</p>
              {!step.done && <button type="button" className="text-button" onClick={() => go(step.view)}>{step.view === 'settings' ? 'Open Settings' : 'Open Character'}</button>}
            </div>
          </li>
        ))}
      </ol>
      <p className="subtle">Images, current-context tools and background activity are optional and can wait. Say hello whenever you like.</p>
    </section>
  )
}
