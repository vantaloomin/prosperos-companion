import { useState } from 'react'
import { PinOff } from 'lucide-react'
import { Notice } from '../../components/Feedback'
import { useSetVoicePin, useVoicePins } from '../conversation/voicePins'
import { firstName } from './panelText'

/** Their own earlier replies in every chat reply, so they keep their voice when the model changes. */
export function Voice({ name }: { name: string }) {
  const pins = useVoicePins()
  const setPin = useSetVoicePin()
  const [error, setError] = useState<string | null>(null)
  const first = firstName(name)
  const unpin = async (id: string) => {
    try { await setPin(id, false); setError(null) } catch (failure) { setError(failure instanceof Error ? failure.message : 'That did not work.') }
  }
  const list = pins.data?.pins ?? []
  return (
    <section className="settings-section form-stack" aria-labelledby="voice-heading">
      <h2 id="voice-heading">How {first} sounds</h2>
      <p className="subtle">To keep {first} sounding like {first}, even if you change models, each reply is shown a few lines {first} said before. The app picks them from replies you kept, or pin up to {pins.data?.limit ?? 3} yourself with "Pin their voice" in a reply's menu.</p>
      {error && <Notice tone="error">{error}</Notice>}
      {list.length === 0 ? <p className="subtle">No pinned replies. The app is picking for now.</p> : (
        <ul className="plain-list">
          {list.map((pin) => (
            <li key={pin.message_id}>
              <q>{pin.text}</q>
              <span className="form-actions">
                <button type="button" className="text-button voice-unpin" onClick={() => void unpin(pin.message_id)}><PinOff aria-hidden="true" />Unpin</button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
