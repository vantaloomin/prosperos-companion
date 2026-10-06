import { useId, useState } from 'react'
import { Notice } from '../../components/Feedback'
import { Toggle } from '../../components/Fields'
import { CHAT_STYLES } from '../conversation/chatStyles'
import { useChatStyle } from '../conversation/useChatStyle'

/** General > Appearance: how the chat looks, and Retro IM's optional sounds and dark mode. */
export function ChatStyleSettings() {
  const chat = useChatStyle()
  const [error, setError] = useState<string | null>(null)
  const name = useId()
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
      <Toggle label="Retro IM sounds" checked={chat.soundsSetting} onChange={(checked) => void save({ chat_sounds: checked })}
        hint="A chime for each new reply. Only in the Retro IM style." />
      <Toggle label="Retro IM dark mode" checked={chat.retroDarkSetting} onChange={(checked) => void save({ chat_retro_dark: checked })}
        hint="A dark version of the messenger window. Only in the Retro IM style." />
    </section>
  )
}
