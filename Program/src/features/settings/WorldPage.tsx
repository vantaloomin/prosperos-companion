import type { ReactNode } from 'react'
import { LinkRow } from '../../components/Rows'
import { Cities } from '../world/Cities'
import { Library } from '../character/Library'
import { ContextSettings } from './ContextSettings'
import { LifeSettings } from './LifeSettings'
import { WORLD_SUBS, type WorldSub } from './subPages'

/**
 * Settings > World (style guide): where you are, links and the lookup services on the page itself, and rows that open
 * Life, Cities and Library on a page of their own. Settings shows the open page's title and the way back.
 */
export function WorldPage({ name, sub, open }: { name: string; sub: WorldSub | null; open: (sub: WorldSub) => void }) {
  if (sub) {
    const pages: Record<WorldSub, ReactNode> = { life: <LifeSettings name={name} />, cities: <Cities />, library: <Library world /> }
    return pages[sub]
  }
  return <>
    <ContextSettings name={name} />
    <div className="row-list">
      {(Object.keys(WORLD_SUBS) as WorldSub[]).map((item) => <LinkRow key={item} label={WORLD_SUBS[item].title} onOpen={() => open(item)} />)}
    </div>
  </>
}
