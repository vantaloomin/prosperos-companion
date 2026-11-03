import type { View } from '../../companion'
import { NewGroup } from '../groups/Groups'
import { useCast } from '../groups/groupState'
import { closeNewGroup, useNewGroup } from './newGroupStore'

/** The New group dialog, wherever it was opened from; a made group opens straight away. */
export function NewGroupHost({ go }: { go: (view: View) => void }) {
  const { open, chosen } = useNewGroup()
  const cast = useCast()
  if (!open || !cast.isSuccess) return null
  return <NewGroup companions={cast.data.members} chosen={chosen} onClose={closeNewGroup} onMade={(group) => { closeNewGroup(); go(`group/${group.id}`) }} />
}
