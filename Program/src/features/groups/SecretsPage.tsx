import { Secrets } from './Secrets'

/** Secrets as a page of its own, opened from the Chats list's + (and from Today's header in a later step). */
export function SecretsPage() {
  return <div className="secrets-page"><Secrets heading={1} /></div>
}
