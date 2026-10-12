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
  // Editing the app's line saves it as theirs; making it match the app's line again goes back to following Appearance.
  const change = (text: string) => set({ in_photos: text.trim() === automatic.trim() ? '' : text })
  return (
    <div className="form-stack in-photos">
      <TextArea label="In photos" value={own ? mine : automatic} onChange={change} rows={2} maxLength={2000}
        placeholder="Write what Appearance says, and the line pictures use shows here."
        hint={own ? 'Your line. Pictures use it as written.' : 'Made from Appearance. Change it if a picture should show something else.'}
        tip="Keep it to what a camera can see. Everyday clothes are best left out, since what they wear changes with the moment." />
      {own && <div className="form-actions"><button type="button" className="text-button" onClick={() => set({ in_photos: '' })}>Follow Appearance again</button></div>}
    </div>
  )
}
