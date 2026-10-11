import { current as sidecarWindow } from './popout'
import { sidecar } from './store'

/** The rail button and the phone's chat header button: opens the sidecar where it last was, brings its window forward, or closes the docked panel. */
export function toggleSidecar(open: boolean) {
  const popped = sidecarWindow()
  if (open && popped) popped.focus()
  else if (open) sidecar.setOpen(false)
  else sidecar.show()
}
