import { useId, useState } from 'react'
import { Notice } from '../../components/Feedback'
import { Toggle } from '../../components/Fields'
import { CHAT_STYLES } from '../conversation/chatStyles'
import { useChatStyle } from '../conversation/useChatStyle'

/** Appearance > Chat style: one self-contained section, so it can move wherever Settings groups appearance. */
export function ChatStyleSettings() {
  const chat = useChatStyle()
  const [error, setError] = useState<string | null>(null)
  const name = useId()
  const save = async (change: Parameters<typeof chat.save>[0]) => setError(await chat.save(change))
  return (
    <section className="settings-section form-stack" aria-labelledby="chat-style-heading">
      <div>
        <h2 id="chat-style-heading">Chat style</h2>
        <p className="subtle">How the conversation looks. Every style shows the same messages with the same actions; you can also switch from the top of the chat.</p>
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
        hint="A door sound when they come free to talk, another when they step away, and a chime for each new reply. Only in the Retro IM style." />
    </section>
  )
}
