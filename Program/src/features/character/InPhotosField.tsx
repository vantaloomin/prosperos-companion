import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { CharacterDefinition } from '../../types'
import { TextArea } from '../../components/Fields'
import { useSettled } from './useSettled'

interface Props { definition: () => CharacterDefinition; value: string | undefined; set: (change: Partial<CharacterDefinition>) => void }

/** The In photos line: what their pictures say about them besides Looks. The app fills it from Appearance, leaving
 * out what a camera cannot see; typing here replaces it, and "Follow Appearance" hands it back. */
export function InPhotosField({ definition, value, set }: Props) {
  const body = useSettled({ ...definition(), in_photos: '' })
  const found = useQuery({
    queryKey: ['looks', body],
    queryFn: () => api<{ in_photos: string }>('/companion/looks', { definition: body }),
    staleTime: Infinity,
  })
  const automatic = found.data?.in_photos ?? ''
  const mine = value ?? ''
  const own = mine.trim() !== ''
  // While they type, the box shows what they typed, even when it is empty for a moment, so clearing it to write a
  // new line never brings the app's line back mid-edit.
  const [draft, setDraft] = useState<string | null>(null)
  // Editing the app's line saves it as theirs; making it match the app's line again goes back to following Appearance.
  const change = (text: string) => {
    setDraft(text)
    set({ in_photos: text.trim() === automatic.trim() ? '' : text })
  }
  return (
    <div className="form-stack in-photos">
      <TextArea label="In photos" value={draft ?? (own ? mine : automatic)} onChange={change} onBlur={() => setDraft(null)} rows={2} maxLength={2000}
        placeholder="Leave empty to use Appearance"
        hint={hintFor(draft, own)}
        tip="Keep it to what a camera can see. Everyday clothes are best left out, since what they wear changes with the moment." />
      {own && <button type="button" className="text-button in-photos-follow" onClick={() => { setDraft(null); set({ in_photos: '' }) }}>Follow Appearance again</button>}
    </div>
  )
}

function hintFor(draft: string | null, own: boolean): string {
  if (draft !== null && !draft.trim()) return 'Empty, so pictures use Appearance.'
  return own ? 'Your line. Pictures use it as written.' : 'Made from Appearance. Change it if a picture should show something else.'
}
