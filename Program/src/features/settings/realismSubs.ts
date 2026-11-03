/** Settings > Realism's pages of their own (v1.3 design, step 9). */

export type RealismSub = 'love' | 'home' | 'closeness' | 'adult' | 'hidden'

/** Each page of Realism: its title (the page's h1, with the way back above it), what it is about behind a "?", and
 * the heading id a search result lands on. */
export const REALISM_SUBS: Record<RealismSub, { title: string; tip: string; heading: string }> = {
  love: { title: 'Love and friendship', heading: 'love-heading',
    tip: 'Relationships move on by themselves: being exclusive, saying "I love you", meeting their people, becoming best friends. You can always bring a step up yourself, or set it on their Character page.' },
  home: { title: 'Around the home', heading: 'home-life-heading', tip: 'How much everyday life happens at home. Past days stay as they were; changes apply from today.' },
  closeness: { title: 'Closeness', heading: 'closeness-settings-heading',
    tip: 'Closeness grows from the days you talk and the moments you keep. Skip ahead, hold it still or put a limit on it. It only changes how they talk with you.' },
  adult: { title: 'Adult side of life', heading: 'adult-side-heading', tip: 'Real people have a love life and desires of their own. Off until you turn it on.' },
  hidden: { title: 'Hidden values', heading: 'hidden-values-heading',
    tip: 'Some things stay behind the curtain so it feels like real life: you notice them from how people talk, not from a label. They still shape every reply when hidden.' },
}

/** The page a search result's heading is on, if it is on one of Realism's own pages. */
export function realismSubFor(heading: string): RealismSub | null {
  return (Object.keys(REALISM_SUBS) as RealismSub[]).find((sub) => REALISM_SUBS[sub].heading === heading) ?? null
}
