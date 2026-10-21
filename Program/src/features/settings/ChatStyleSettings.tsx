import { useId, useState } from 'react'
import { Notice } from '../../components/Feedback'
import { Toggle } from '../../components/Fields'
import { CHAT_STYLES } from '../conversation/chatStyles'
import { useChatStyle } from '../conversation/useChatStyle'
import { ColorSchemeSettings } from './ColorSchemeSettings'
import { DeviceLookSettings } from './DeviceLookSettings'

/** General > Appearance: how the chat looks, Retro IM's optional sounds and dark mode, period words, the app's colors,
 * and this device's text size, reading font and motion. */
export function ChatStyleSettings() {
  const chat = useChatStyle()
  const [error, setError] = useState<string | null>(null)
  const name = useId()
  const retro = chat.style === 'retro'
  const save = async (change: Parameters<typeof chat.save>[0]) => setError(await chat.save(change))
  return (
    <section className="settings-section form-stack" aria-labelledby="appearance-heading">
      <div>
        <h2 id="appearance-heading">Appearance</h2>
        <p className="subtle">Pick a chat style. Every style shows the same messages with the same actions; you can also switch from the top of the chat.</p>
      </div>
      {error && <Notice tone="error">{error}</Notice>}
      <fieldset className="chat-style-options">
        <legend className="visually-hidden">Chat style</legend>
        {CHAT_STYLES.map((style) => (
          <label key={style.id} className={`chat-style-option preview-${style.id}`}>
            <input type="radio" name={name} value={style.id} checked={chat.style === style.id} onChange={() => void save({ chat_style: style.id })} />
            <span className="chat-style-text"><span>{style.label}</span><small>{style.description}</small></span>
          </label>
        ))}
      </fieldset>
      {/* Both panels share one grid cell, so the area keeps the taller one's height and the page never jumps when the style changes. */}
      <div className="chat-style-extras">
        <div className="chat-style-extras-panel" hidden={!retro} inert={!retro}>
          <Toggle label="Retro IM sounds" checked={chat.soundsSetting} onChange={(checked) => void save({ chat_sounds: checked })}
            hint="A chime for each new reply." />
          <Toggle label="Retro IM dark mode" checked={chat.retroDarkSetting} onChange={(checked) => void save({ chat_retro_dark: checked })}
            hint="A dark version of the messenger window." />
        </div>
        <p className="chat-style-extras-panel subtle" hidden={retro}>No extra options for this style.</p>
      </div>
      <div className="period-words">
        <Toggle label="Period words in period cities" checked={chat.periodWords} onChange={(checked) => void save({ period_words: checked })}
          hint="In cities of another time, chats, posts and calls use that era's words. Settings always use today's." />
      </div>
      <ColorSchemeSettings theme={chat.theme} scheme={chat.scheme} palette={chat.palette} save={save} />
      <DeviceLookSettings />
    </section>
  )
}
