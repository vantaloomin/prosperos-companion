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

export type WorldSub = 'life' | 'cities' | 'library'

/** Settings > World's pages of their own (v1.3 design, step 11), the same way as Realism's. */
export const WORLD_SUBS: Record<WorldSub, { title: string; tip: string; heading: string }> = {
  life: { title: 'Life', heading: 'life-heading',
    tip: 'When you come back, a few things that fit their routine are written for the time you were away. Nothing is written for time while paused. Drama, pace and closeness are in Realism.' },
  cities: { title: 'Cities', heading: 'cities-heading',
    tip: "A companion's days are built from their home city: its neighborhoods, places, work and weather. Start a city of your own, copy one to change it, or open a city file someone shared. Prospero's Draft Table draws up a whole place from one line, in a window of its own. A Marinara world map opens as a city straight away, with its places' notes as world lore." },
  library: { title: 'Library', heading: 'world-library-heading',
    tip: 'Long texts every companion in this world can draw on: a novel, a script, transcripts or a wiki export. Only the few passages that fit what you are talking about join each reply.' },
}

export type SubPage = { title: string; tip: string; heading: string }

/** Every group's pages of their own. */
export const SUB_PAGES: Partial<Record<string, Record<string, SubPage>>> = { realism: REALISM_SUBS, world: WORLD_SUBS }

/** The page a search result's heading is on, if it is on a page of its own within its group. */
export function subFor(tab: string, heading: string): string | null {
  const pages = SUB_PAGES[tab] ?? {}
  return Object.keys(pages).find((sub) => pages[sub].heading === heading) ?? null
}
