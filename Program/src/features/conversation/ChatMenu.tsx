import { Download, Ellipsis } from 'lucide-react'
import type { ChatStyle } from '../../types'
import { Menu, type MenuEntry } from '../../components/Menu'
import { EXPORT_FORMATS, exportHref } from '../chats/exportText'
import { CHAT_STYLES } from './chatStyles'
import { useChatStyle } from './useChatStyle'
import { MIX, useModelSwitch } from '../settings/models/useModelSwitch'

/**
 * A chat's ⋯ (style guide: everything past the header's four buttons). The caller's own items come first, then
 * Export, then the model that answers (once there are two to pick) and the chat style as small previews: the
 * picture explains the style, so no descriptions.
 */
export function ChatMenu({ threadId, items = [] }: { threadId: string; items?: MenuEntry[] }) {
  const exports: MenuEntry[] = EXPORT_FORMATS.map(({ format, label }) => ({ label, icon: Download, onSelect: () => download(exportHref({ kind: 'chat', threadId }, format)) }))
  return <Menu label="More" icon={Ellipsis} items={[...items, ...(items.length ? ['separator' as const] : []), ...exports]} footer={<><ModelSwitch /><StylePreviews /></>} className="chat-menu" />
}

/** The file is made by the server and saved by the browser, as a plain link would. */
function download(href: string) {
  const link = document.createElement('a')
  link.href = href
  link.download = ''
  link.click()
}

/** Which model answers in chat, once there is more than one to pick. */
function ModelSwitch() {
  const models = useModelSwitch()
  if (models.profiles.length < 2) return null
  return <>
    <hr className="menu-sep" />
    <label className="menu-field"><span className="menu-caption">Model</span>
      <select value={models.current} onChange={(event) => void models.choose(event.target.value).catch(() => undefined)}>
        {models.canMix && <option value={MIX}>Mix ({models.mixCount} models)</option>}
        {models.profiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.name}</option>)}
      </select>
    </label>
  </>
}

/** The five chat styles as small pictures of their layout; Settings > General has the same choice. */
function StylePreviews() {
  const chat = useChatStyle()
  return <>
    <hr className="menu-sep" />
    <div className="menu-caption" id="chat-style-caption">Chat style</div>
    <div className="style-previews" role="group" aria-labelledby="chat-style-caption">
      {CHAT_STYLES.map((style) => (
        <button key={style.id} type="button" role="menuitemradio" aria-checked={chat.style === style.id} className="style-preview" onClick={() => void chat.save({ chat_style: style.id })}>
          <StyleThumb style={style.id} /><span>{style.label === 'Visual novel' ? 'Novel' : style.label}</span>
        </button>
      ))}
    </div>
  </>
}

/** Three lines drawn the way each style lays out messages: yours right in Bubbles and Retro, a stage in Novel. */
const ROWS: Record<ChatStyle, string[]> = { feed: ['', '', ''], bubbles: ['l', 'r', 'l'], community: ['a', 'a', 'a'], retro: ['n', 'n', 'n'], novel: ['s', 'b', 'b'] }

export function StyleThumb({ style }: { style: ChatStyle }) {
  return <span className={`style-thumb thumb-${style}`} aria-hidden="true">{ROWS[style].map((kind, index) => <i key={index} className={kind ? `t-${kind}` : undefined} />)}</span>
}
