import { useState, type ReactNode } from 'react'
import { FolderOpen } from 'lucide-react'
import { ApiError, api } from '../api'
import { usePhoneStatus } from '../features/phone/phoneAccess'
import { Notice } from './Feedback'

/**
 * A request that failed. When the Companion itself hit a bug, its message names the log file, and on the PC
 * a button opens the folder holding it, so the user does not have to find the data folder themself.
 */
export function ErrorNotice({ error, children, action }: { error: Error; children?: ReactNode; action?: ReactNode }) {
  const bug = error instanceof ApiError && error.code === 'server_error'
  return <Notice tone="error" action={<>{action}{bug && <LogFolderButton />}</>}>{children}{error.message}</Notice>
}

function LogFolderButton() {
  const phone = usePhoneStatus()
  const [failed, setFailed] = useState(false)
  if (phone.data?.remote) return null  // The folder is on the PC.
  const open = () => api('/logs/open-folder', {}).then(() => setFailed(false), () => setFailed(true))
  return (
    <button type="button" className="text-button" onClick={() => void open()}>
      <FolderOpen aria-hidden="true" size={14} />{failed ? 'Could not open it; try again' : 'Open the log folder'}
    </button>
  )
}
