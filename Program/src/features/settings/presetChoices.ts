import type { LifeSettings, WorkspaceSettings } from '../../types'

type LifePart = Pick<LifeSettings, 'drama' | 'paced_replies' | 'day_shifts' | 'on_her_mind'>
type ShownPart = Required<Pick<WorkspaceSettings, 'show_moods' | 'show_news' | 'show_odds' | 'show_secret_slips'>>

export interface RealismPreset {
  id: string
  label: string
  description: string
  life: LifePart
  shown: ShownPart
}

const HIDDEN: ShownPart = { show_moods: false, show_news: false, show_odds: false, show_secret_slips: true }

/**
 * One-tap starting points for Settings > Realism, named the way Wolfenstein names its difficulties (Vanta, 2026-10-10).
 * Each sets the world-wide settings on the tab; closeness stays per companion. The first is how a new world starts.
 */
export const REALISM_PRESETS: RealismPreset[] = [
  {
    id: 'real', label: 'I want real life', description: 'They answer when they can, plans go wrong now and then, and you read feelings from how they talk.',
    life: { drama: 1, paced_replies: true, day_shifts: true, on_her_mind: true }, shown: HIDDEN,
  },
  {
    id: 'drama', label: 'Bring on the drama', description: 'Soap opera storylines, plans falling through and secrets everywhere. You still find out the hard way.',
    life: { drama: 3, paced_replies: true, day_shifts: true, on_her_mind: true }, shown: HIDDEN,
  },
  {
    id: 'easy', label: 'I want an easy life', description: 'Quiet days that go to plan, and replies right away.',
    life: { drama: 0, paced_replies: false, day_shifts: false, on_her_mind: true }, shown: HIDDEN,
  },
  {
    id: 'strings', label: 'I pull the strings', description: 'Everyday drama and plans that sometimes go wrong, as in real life, but replies right away and every hidden value on show: moods, who has heard what, and the odds, with a way to make things go another way.',
    life: { drama: 1, paced_replies: false, day_shifts: true, on_her_mind: true },
    shown: { show_moods: true, show_news: true, show_odds: true, show_secret_slips: true },
  },
]

/** How many of a preset's settings differ from the current ones. */
function distance(preset: RealismPreset, life: LifeSettings, workspace: WorkspaceSettings): number {
  const shown: ShownPart = {
    show_moods: !!workspace.show_moods, show_news: !!workspace.show_news, show_odds: !!workspace.show_odds,
    show_secret_slips: workspace.show_secret_slips !== false,
  }
  return (Object.keys(preset.life) as (keyof LifePart)[]).filter((key) => life[key] !== preset.life[key]).length
    + (Object.keys(preset.shown) as (keyof ShownPart)[]).filter((key) => shown[key] !== preset.shown[key]).length
}

/** The preset the current settings match exactly, or null for the user's own mix. */
export function matchPreset(life: LifeSettings, workspace: WorkspaceSettings): RealismPreset | null {
  return REALISM_PRESETS.find((preset) => distance(preset, life, workspace) === 0) ?? null
}

/** For "your own mix, based on ...": the preset with the fewest settings changed (the first wins a tie). */
export function nearestPreset(life: LifeSettings, workspace: WorkspaceSettings): RealismPreset {
  return REALISM_PRESETS.reduce((best, preset) => distance(preset, life, workspace) < distance(best, life, workspace) ? preset : best)
}
