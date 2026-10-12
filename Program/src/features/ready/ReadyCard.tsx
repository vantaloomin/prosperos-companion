import { useState } from 'react'
import { usePhoneStatus } from '../phone/phoneAccess'
import { ConfirmDownload } from './ConfirmDownload'
import { DownloadProgress } from './DownloadProgress'
import { isActive, modelOf, size, type ReadyView } from './readyText'
import { useReady, useReadyActions } from './useReady'

/** Top of Settings > Models: the built-in model while it downloads, the offer to use it once it is ready if the user
 * picked another chat model meanwhile, and, with nothing set up yet, the same "Set it up for me" as the welcome. */
export function ReadyCard({ hasProfiles }: { hasProfiles: boolean }) {
  const remote = !!usePhoneStatus().data?.remote
  const view = useReady().data
  if (!view) return null
  if (isActive(view)) {
    return <div className="model-profile ready-card"><div><span className="eyebrow">Local</span><h3>Local · {modelOf(view).name}</h3>
      <DownloadProgress view={view} phone={remote} /></div></div>
  }
  if (view.status === 'ready' && !view.in_use) return <UseIt view={view} />
  if (view.status === 'idle' && !remote && !hasProfiles && view.pick.fits) return <Offer view={view} />
  return null
}

function UseIt({ view }: { view: ReadyView }) {
  const actions = useReadyActions()
  return <div className="model-profile ready-card"><div><span className="eyebrow">Local</span><h3>Local · {modelOf(view).name}</h3>
    <p className="subtle">Ready. <button type="button" className="text-button" onClick={() => void actions.use()}>Use it for conversation</button></p></div></div>
}

function Offer({ view }: { view: ReadyView }) {
  const [asking, setAsking] = useState(false)
  return <div className="model-profile ready-card"><div><span className="eyebrow">On this computer</span><h3>A free model on your graphics card</h3>
    <p className="subtle">{view.pick.name} ({size(view.pick.bytes)}) runs here, so your chats stay on this computer.</p>
    <div className="form-actions"><button type="button" className="button primary" onClick={() => setAsking(true)}>Set it up for me</button></div>
    {asking && <ConfirmDownload view={view} onClose={() => setAsking(false)} />}</div></div>
}
