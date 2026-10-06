import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { QrCode, RefreshCw, Smartphone } from 'lucide-react'
import { api } from '../../api'
import { Notice } from '../../components/Feedback'
import { linkParts } from '../phone/pairing'
import { PHONE_ACCESS_KEY, PHONE_STATUS_KEY, usePhoneStatus, type PhoneAccess, type PhonePairing } from '../phone/phoneAccess'

const formatDate = (iso: string | null) => iso ? new Date(iso).toLocaleString() : 'never'

/** Settings > Phone access: share the Companion privately over Tailscale and pair phones (companion/phone/). */
export function PhoneSettings() {
  const status = usePhoneStatus()
  return (
    <section className="settings-section form-stack" aria-labelledby="phone-heading">
      <div>
        <h2 id="phone-heading">Phone access</h2>
        <p className="subtle">Use your companion from your phone, at home or away. Tailscale gives the Companion a private https address that only your own devices can open. Nothing is opened to the internet or your router, and your PC has to be on for the phone to reach it.</p>
      </div>
      {status.data?.remote ? <ThisPhone /> : <OnThePc />}
    </section>
  )
}

function ThisPhone() {
  const status = usePhoneStatus()
  const client = useQueryClient()
  const [error, setError] = useState('')
  const signOut = async () => {
    try {
      await api('/phone/sign-out', {})
      await client.invalidateQueries({ queryKey: PHONE_STATUS_KEY })
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Signing out did not work.') }
  }
  return (
    <div className="form-stack">
      {error && <Notice tone="error">{error}</Notice>}
      <p>This phone is paired as <strong>{status.data?.device?.name}</strong>.</p>
      <p className="subtle">Models, backups, imports, image backends, real-world lookup tools and LoRA training can only be changed on your PC. To keep the Companion on your home screen, use your browser’s Add to Home Screen.</p>
      <div className="form-actions"><button type="button" className="button" onClick={() => void signOut()}>Sign this phone out</button></div>
    </div>
  )
}

function OnThePc() {
  const client = useQueryClient()
  const access = useQuery({ queryKey: PHONE_ACCESS_KEY, queryFn: () => api<PhoneAccess>('/phone') })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [pairing, setPairing] = useState<PhonePairing | null>(null)
  // Busy controls are marked, not disabled: disabling the focused control would drop keyboard focus.
  const run = async (action: () => Promise<void>) => {
    if (busy) return
    setBusy(true)
    setError('')
    try { await action() } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'That did not work. Try again.')
    } finally { setBusy(false) }
  }
  const change = (path: string) => run(async () => {
    client.setQueryData(PHONE_ACCESS_KEY, await api<PhoneAccess>(path, {}))
    setPairing(null)
  })
  const pair = () => run(async () => setPairing(await api<PhonePairing>('/phone/pairings', {})))
  const remove = (id: string) => run(async () => {
    const { devices } = await api<{ devices: PhoneAccess['devices'] }>(`/phone/devices/${encodeURIComponent(id)}`, undefined, 'DELETE')
    client.setQueryData<PhoneAccess>(PHONE_ACCESS_KEY, (old) => old && { ...old, devices })
  })
  if (access.isPending) return <p className="subtle">Checking Tailscale…</p>
  if (access.isError) return <Notice tone="error">{access.error.message}</Notice>
  const { enabled, devices, tailscale } = access.data
  return (
    <div className="form-stack">
      {error && <Notice tone="error"><Linked text={error} /></Notice>}
      <Explanation access={access.data} />
      <div className="form-actions">
        {enabled ? <>
            {tailscale.running && <button type="button" className="button primary" aria-disabled={busy} onClick={() => void pair()}><QrCode aria-hidden="true" />Pair a phone</button>}
            <button type="button" className="button" aria-disabled={busy} onClick={() => void change('/phone/disable')}>Turn off phone access</button>
          </>
          : tailscale.running ? <button type="button" className="button primary" aria-disabled={busy} onClick={() => void change('/phone/enable')}><Smartphone aria-hidden="true" />Turn on phone access</button>
            : <button type="button" className="button" aria-disabled={busy} onClick={() => void access.refetch()}><RefreshCw aria-hidden="true" />Check again</button>}
      </div>
      {pairing && <PairingCode pairing={pairing} />}
      {devices.length > 0 && (
        <div className="form-stack">
          <h3>Paired phones</h3>
          <ul className="plain-list">
            {devices.map((device) => (
              <li key={device.id}>
                <strong>{device.name}</strong> <span className="subtle">paired {formatDate(device.created_at)}, last used {formatDate(device.last_seen_at)}</span>{' '}
                <button type="button" className="text-button" aria-disabled={busy} onClick={() => void remove(device.id)}>Remove</button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function Explanation({ access: { enabled, address, tailscale } }: { access: PhoneAccess }) {
  if (!tailscale.installed) {
    return <p>First, install Tailscale on this PC and on your phone, and sign in to both with the same account. It is free for personal use. <a className="text-button" href={tailscale.install_url} target="_blank" rel="noreferrer">Get Tailscale</a></p>
  }
  if (!tailscale.running) return <p>Tailscale is installed but not connected. Open it on this PC and sign in, then check again.</p>
  if (!enabled) return <p>Tailscale is connected as <strong>{tailscale.name}</strong>. Turning phone access on asks Tailscale to share the Companion at https://{tailscale.name}.</p>
  return (
    <>
      <p>Your phone opens the Companion at <strong>{address}</strong>.{!tailscale.serving && ' Tailscale is not sharing it right now; turn phone access off and on again.'}</p>
      <p className="subtle">Install Tailscale on your phone and sign in with the same account, then pair it here. A paired phone can chat and use Today, the Feed, Memories and Character. Models, backups, imports, image backends, lookup tools and LoRA training stay on this PC.</p>
    </>
  )
}

function PairingCode({ pairing }: { pairing: PhonePairing }) {
  return (
    <div className="phone-pairing" role="group" aria-label="Pairing code">
      {/* The QR code is drawn by the Companion itself (segno) from the link below. */}
      <div className="phone-qr" aria-hidden="true" dangerouslySetInnerHTML={{ __html: pairing.qr_svg }} />
      <div className="form-stack">
        <p>Scan this with your phone’s camera, or open <strong>{pairing.link}</strong> on the phone.</p>
        <p>Code: <strong className="phone-code">{pairing.code}</strong></p>
        <p className="subtle">It works once, until {new Date(pairing.expires_at).toLocaleTimeString()}.</p>
      </div>
    </div>
  )
}

function Linked({ text }: { text: string }) {
  return <>{linkParts(text).map((part, index) => part.link ? <a key={index} className="text-button" href={part.text} target="_blank" rel="noreferrer">{part.text}</a> : <span key={index}>{part.text}</span>)}</>
}
