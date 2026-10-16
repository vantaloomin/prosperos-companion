/** Rough patches and making up (companion/life/rough_patches.py): the slider's steps and the Character page line, kept apart from the components for tests. */

export const ROUGH_PATCH_KEY = ['rough-patch']

/** `about` (what it is over) comes only with Hidden values > moods on; a small one shows only then too. */
export interface RoughPatch { open: boolean; id: string | null; text: string; since: string | null; about: string | null; small: boolean }

/** The Rough patches slider (life_settings.rough_patches_realism), 0 to 3. */
export const ROUGH_PATCH_LEVELS = [
  { label: 'Off', hint: 'Nothing you say or miss starts a falling-out. Moods still come and go within a day.' },
  { label: 'Blows over', hint: 'Something that stings can leave things a bit tense for the rest of the day, and it is gone by morning.' },
  { label: 'True to life', hint: 'Hurtful words, a missed plan, a forgotten birthday, a broken promise or a secret coming out can leave things tense for a few days. An apology or a kind gesture mends it sooner.' },
  { label: 'Dramatic', hint: 'Falling-outs come more easily and linger until you make up. Something serious, like a secret coming out, takes both an apology and a gesture.' },
]

/** One sentence: "Things are a bit tense", and with moods shown what it is over ("Things are a bit tense over what you
 * said: "…""), or what they did ("Things are a bit tense: they called off dinner at the last minute"). */
export function roughPatchLine(patch: RoughPatch | undefined): string {
  if (!patch?.open) return ''
  if (!patch.about) return patch.text
  return patch.about.startsWith('over ') ? `${patch.text} ${patch.about}` : `${patch.text}: ${patch.about}`
}

/** How long "You let it go. Undo" stays before it drops. */
export const UNDO_MS = 6000
