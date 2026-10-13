import type { LifeSettings, WorkspaceSettings } from '../../types'

type LifePart = Pick<LifeSettings, 'drama' | 'paced_replies' | 'day_shifts' | 'on_her_mind' | 'upkeep_realism' | 'kitchen_realism' | 'looks_realism' | 'pets_realism' | 'pets_can_die' | 'admin_realism' | 'media_realism'>
type ShownPart = Required<Pick<WorkspaceSettings, 'show_moods' | 'show_news' | 'show_odds' | 'show_secret_slips' | 'show_home_meters'>>

export interface RealismPreset {
  id: string
  label: string
  description: string
  life: LifePart
  shown: ShownPart
}

const HIDDEN: ShownPart = { show_moods: false, show_news: false, show_odds: false, show_secret_slips: true, show_home_meters: false }

/**
 * One-tap starting points for Settings > Realism, named the way Wolfenstein names its difficulties (Vanta, 2026-10-10).
 * Each sets the world-wide settings on the tab; closeness stays per companion. The first is how a new world starts.
 */
export const REALISM_PRESETS: RealismPreset[] = [
  {
    id: 'real', label: 'I want real life', description: 'They answer when they can, plans go wrong now and then, and you read feelings from how they talk.',
    life: { drama: 1, paced_replies: true, day_shifts: true, on_her_mind: true, upkeep_realism: 2, kitchen_realism: 2, looks_realism: 2, pets_realism: 2, pets_can_die: true, admin_realism: 2, media_realism: 2 }, shown: HIDDEN,
  },
  {
    id: 'drama', label: 'Bring on the drama', description: 'Soap opera storylines, plans falling through and secrets everywhere. You still find out the hard way.',
    life: { drama: 3, paced_replies: true, day_shifts: true, on_her_mind: true, upkeep_realism: 3, kitchen_realism: 3, looks_realism: 3, pets_realism: 3, pets_can_die: true, admin_realism: 3, media_realism: 3 }, shown: HIDDEN,
  },
  {
    id: 'easy', label: 'I want an easy life', description: 'Quiet days that go to plan, and replies right away.',
    life: { drama: 0, paced_replies: false, day_shifts: false, on_her_mind: true, upkeep_realism: 1, kitchen_realism: 1, looks_realism: 1, pets_realism: 1, pets_can_die: false, admin_realism: 1, media_realism: 1 }, shown: HIDDEN,
  },
  {
    id: 'strings', label: 'I pull the strings', description: 'Everyday drama and plans that sometimes go wrong, as in real life, but replies right away and every hidden value on show: moods, who has heard what, and the odds, with a way to make things go another way.',
    life: { drama: 1, paced_replies: false, day_shifts: true, on_her_mind: true, upkeep_realism: 2, kitchen_realism: 2, looks_realism: 2, pets_realism: 2, pets_can_die: true, admin_realism: 2, media_realism: 2 },
    shown: { show_moods: true, show_news: true, show_odds: true, show_secret_slips: true, show_home_meters: true },
  },
]

/** How many of a preset's settings differ from the current ones. */
function distance(preset: RealismPreset, life: LifeSettings, workspace: WorkspaceSettings): number {
  const shown: ShownPart = {
    show_moods: !!workspace.show_moods, show_news: !!workspace.show_news, show_odds: !!workspace.show_odds,
    show_secret_slips: workspace.show_secret_slips !== false, show_home_meters: !!workspace.show_home_meters,
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
