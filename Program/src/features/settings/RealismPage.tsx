import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import { useWorkspaceSettings } from '../../companion'
import type { LifeSettings } from '../../types'
import { LinkRow } from '../../components/Rows'
import { HiddenValues } from './HiddenValues'
import { AdultSideSettings, ClosenessSettings, HomeLifeSettings, LoveSettings, PaceSettings, RealismIntro } from './RealismSettings'
import { LIFE_KEY } from './useLifeSettings'
import { REALISM_SUBS, type RealismSub } from './subPages'

/**
 * Settings > Realism (style guide): the presets as one segmented control, every slider of their days as a row, and
 * rows that open Love and friendship, Around the home, Closeness, the adult side and Hidden values on a page of their
 * own. Settings shows the open page's title and the way back.
 */
export function RealismPage({ name, sub, open }: { name: string; sub: RealismSub | null; open: (sub: RealismSub) => void }) {
  if (sub) {
    const pages: Record<RealismSub, ReactNode> = {
      love: <LoveSettings />, home: <HomeLifeSettings />, closeness: <ClosenessSettings name={name} />, adult: <AdultSideSettings />, hidden: <HiddenValues name="" />,
    }
    return pages[sub]
  }
  return <>
    <RealismIntro />
    <PaceSettings name={name} />
    <RealismPages open={open} />
  </>
}

/** The rows that open each page, with a word for where it stands. */
function RealismPages({ open }: { open: (sub: RealismSub) => void }) {
  const workspace = useWorkspaceSettings().data
  const life = useQuery({ queryKey: LIFE_KEY, queryFn: () => api<LifeSettings>('/life/settings') }).data
  const shown = workspace ? (['show_moods', 'show_news', 'show_odds', 'show_home_meters'] as const).filter((key) => workspace[key]).length + (life?.on_her_mind !== false ? 1 : 0) : 0
  const values: Partial<Record<RealismSub, string>> = {
    adult: workspace ? (workspace.adult_side ? 'On' : 'Off') : undefined,
    hidden: workspace ? (shown ? `${shown} shown` : 'All hidden') : undefined,
  }
  return (
    <div className="row-list">
      {(Object.keys(REALISM_SUBS) as RealismSub[]).map((sub) => <LinkRow key={sub} label={REALISM_SUBS[sub].title} value={values[sub]} onOpen={() => open(sub)} />)}
    </div>
  )
}
