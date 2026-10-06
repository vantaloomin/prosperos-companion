import { useState } from 'react'
import type { Companion } from '../../types'
import type { View } from '../../companion'
import { STEPS, type Step } from './loraState'
import { Prepare, Review } from './References'
import { Configure, Train } from './Training'
import { Evaluate } from './Evaluation'
import { Adopt } from './Adapters'

/** The guided character LoRA maker (PRD "Character LoRA maker requirements"). */
export function Appearance({ companion, go }: { companion: Companion; go: (view: View) => void }) {
  const [step, setStep] = useState<Step>('prepare')
  return (
    <section className="page">
      <header className="page-header">
        <div>
          <h1>{companion.version.name}'s look</h1>
          <p className="subtle">Teach the local image model what {companion.version.name} looks like with a LoRA, or keep drawing from the appearance description. Nothing changes for images until you adopt a version, and earlier images always keep theirs.</p>
        </div>
        <button type="button" className="button" onClick={() => go('character')}>Back to the character</button>
      </header>
      <nav className="stepper" aria-label="LoRA steps">
        {STEPS.map((item, index) => (
          <button key={item.id} id={`step-${item.id}`} type="button" aria-current={step === item.id ? 'step' : undefined} onClick={() => setStep(item.id)}>
            <span aria-hidden="true">{index + 1}</span>{item.label}
          </button>
        ))}
      </nav>
      <section aria-labelledby="step-heading">
        <h2 id="step-heading" className="visually-hidden">{STEPS.find((item) => item.id === step)?.label}</h2>
        <StepView step={step} setStep={setStep} />
      </section>
    </section>
  )
}

function StepView({ step, setStep }: { step: Step; setStep: (step: Step) => void }) {
  if (step === 'prepare') return <Prepare />
  if (step === 'review') return <Review />
  // Starting a run removes the focused Start button; continue from the Train step in the stepper.
  if (step === 'configure') return <Configure onStarted={() => { setStep('train'); document.getElementById('step-train')?.focus() }} />
  if (step === 'train') return <Train />
  if (step === 'evaluate') return <Evaluate />
  return <Adopt />
}
