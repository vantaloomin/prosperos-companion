import { useState } from 'react'
import { PinOff } from 'lucide-react'
import { Notice } from '../../components/Feedback'
import { FoldRow } from '../../components/Rows'
import { InfoTip } from '../../components/InfoTip'
import { useSetVoicePin, useVoicePins } from '../conversation/voicePins'
import { firstName } from './panelText'

/** Their own earlier replies in every chat reply, so they keep their voice when the model changes. A fold row whose
 * summary says how many are pinned. */
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
    <FoldRow summary={`How ${first} sounds`} value={list.length ? `${list.length} pinned` : 'Picked by the app'}>
      <div className="fold-extra form-stack">
        <p className="fold-about">Pinned replies <InfoTip id="voice-about" label="Pinned replies" text={`To keep ${first} sounding like ${first}, even if you change models, each reply is shown a few lines ${first} said before. The app picks them from replies you kept, or pin up to ${pins.data?.limit ?? 3} yourself with "Pin their voice" in a reply's menu.`} /></p>
        {error && <Notice tone="error">{error}</Notice>}
        {list.length > 0 && (
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
      </div>
    </FoldRow>
  )
}
