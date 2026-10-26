import type { UpdateCheck as Found } from '../../types'

const SCRIPT: Record<Found['system'], string> = {
  windows: 'update.bat in the Windows folder',
  mac: 'update.command in the Mac folder',
  other: 'update.bat (Windows) or update.command (Mac)',
}

/** How to get a newer version onto this copy: the installer from the release page, or the folder's update script. */
export function howToUpdate(found: Found, onPhone: boolean): string {
  const how = found.install === 'installer'
    ? 'Download the new installer from the release page and run it. Your world and conversations stay as they are.'
    : `Close the Companion, then run ${SCRIPT[found.system]} next to the Program folder. Your world and conversations stay as they are.`
  return onPhone ? `Update it on the computer the Companion runs on. ${how}` : how
}

/** ", released 26 October 2026", or nothing when GitHub gave no date. */
export function releasedOn(iso: string | null): string {
  return iso ? `, released ${new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' })}` : ''
}

/** "Download" only where the release page is the next step (the installer, on the PC); elsewhere it shows what changed. */
export function linkLabel(found: Found, onPhone: boolean): string {
  if (found.status === 'unavailable') return 'Releases page'
  if (found.status === 'current') return `What’s new in ${found.current}`
  return found.install === 'installer' && !onPhone ? 'Download' : 'What’s new'
}
