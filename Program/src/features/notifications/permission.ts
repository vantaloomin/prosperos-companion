/** Browser notification permission, kept apart from React so it can be tested without a browser. */
export type Permission = 'granted' | 'denied' | 'default' | 'unsupported'

export function currentPermission(source: { Notification?: { permission: string } } = globalThis as never): Permission {
  const permission = source.Notification?.permission
  return permission === 'granted' || permission === 'denied' || permission === 'default' ? permission : 'unsupported'
}

/** Notifications are on in the app but the system no longer allows them: turn them off, which cancels what is queued. */
export const mustRevoke = (enabled: boolean, permission: Permission) => enabled && permission !== 'granted'

/** Neutral wording for each permission state; never in the companion's voice. */
export function permissionNote(permission: Permission): string | null {
  if (permission === 'denied') return 'Notifications are blocked for this page in your browser or system settings. Allow them there to turn this on.'
  if (permission === 'unsupported') return 'This browser cannot show desktop notifications.'
  return null
}
