import type { Companion } from '../../types'
import { Backups } from './Backups'
import { ConnectionSettings } from './ConnectionSettings'
import { ContextSettings } from './ContextSettings'
import { ImageSettings } from './ImageSettings'
import { LifeSettings } from './LifeSettings'
import { NotificationSettings } from './NotificationSettings'
import { PromptSettings } from './PromptSettings'
import { WorkspaceSettings } from './WorkspaceSettings'
import { Cities } from '../world/Cities'

export function Settings({ companion }: { companion: Companion | null }) {
  return (
    <section className="page settings">
      <header className="page-header"><h1>Settings</h1></header>
      <ConnectionSettings />
      <PromptSettings />
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
