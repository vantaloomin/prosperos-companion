import type { Companion } from '../../types'
import { Backups } from './Backups'
import { ChatStyleSettings } from './ChatStyleSettings'
import { ContextSettings } from './ContextSettings'
import { ImageSettings } from './ImageSettings'
import { LifeSettings } from './LifeSettings'
import { NotificationSettings } from './NotificationSettings'
import { PromptSettings } from './PromptSettings'
import { WorkspaceSettings } from './WorkspaceSettings'
import { Cities } from '../world/Cities'
import { ModelSettings } from './models/ModelSettings'

export function Settings({ companion }: { companion: Companion | null }) {
  return (
    <section className="page settings">
      <header className="page-header"><h1>Settings</h1></header>
      <ModelSettings />
      <PromptSettings />
      {companion && <ChatStyleSettings />}
      {companion && <WorkspaceSettings />}
      {companion && <LifeSettings name={companion.version.name} />}
      {companion && <Cities />}
      {companion && <NotificationSettings />}
      {companion && <ImageSettings />}
      {companion && <ContextSettings name={companion.version.name} />}
      {companion && <Backups />}
    </section>
  )
}
