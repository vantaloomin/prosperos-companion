import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { QrCode, RefreshCw, Smartphone } from 'lucide-react'
import { api } from '../../api'
import { useWorkspaceSettings } from '../../companion'
import { Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { linkParts } from '../phone/pairing'
import { PHONE_ACCESS_KEY, PHONE_STATUS_KEY, usePhoneStatus, type PhoneAccess, type PhonePairing, type TailnetPhone } from '../phone/phoneAccess'

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
  const loraMaker = useWorkspaceSettings().data?.lora_maker
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
      <p className="subtle">{pcOnly(loraMaker)} can only be changed on your PC. To keep the Companion on your home screen, use your browser’s Add to Home Screen.</p>
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
  if (access.isError) return <ErrorNotice error={access.error} />
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

/** What only the PC can change; LoRA training is named only while the LoRA creator is switched on. */
function pcOnly(loraMaker?: boolean) {
  return `Models, backups, imports, image backends${loraMaker ? ', real-world lookup tools and LoRA training' : ' and real-world lookup tools'}`
}

function Explanation({ access: { enabled, address, tailscale } }: { access: PhoneAccess }) {
  const loraMaker = useWorkspaceSettings().data?.lora_maker
  if (!tailscale.installed) {
    return <p>First, install Tailscale on this PC and on your phone, and sign in to both with the same account. It is free for personal use. <a className="text-button" href={tailscale.install_url} target="_blank" rel="noreferrer">Get Tailscale</a></p>
  }
  if (!tailscale.running) return <p>Tailscale is installed but not connected. Open it on this PC and sign in, then check again.</p>
  if (!enabled) return <p>Tailscale is connected as <strong>{tailscale.name}</strong>. Turning phone access on asks Tailscale to share the Companion at https://{tailscale.name}.</p>
  return (
    <>
      <p>Your phone opens the Companion at <strong>{address}</strong>.{!tailscale.serving && ' Tailscale is not sharing it right now; turn phone access off and on again.'}</p>
      <PhonesOnTailnet phones={tailscale.phones} />
      {!tailscale.magic_dns && <Notice tone="warning"><Linked text={`MagicDNS is off for your tailnet, so a phone cannot find ${tailscale.name}. Turn it on under DNS in the Tailscale admin console, https://login.tailscale.com/admin/dns, or use the backup address when you pair.`} /></Notice>}
      <p className="subtle">A paired phone can chat and use Today, the Feed, Memories and Character. {pcOnly(loraMaker)} stay on this PC.</p>
    </>
  )
}

/** The usual reason a phone opens the link and nothing loads: Tailscale is not on it, or is switched off. */
function PhonesOnTailnet({ phones }: { phones: TailnetPhone[] }) {
  if (phones.length === 0) {
    return <Notice tone="warning">No phone is signed in to your Tailscale account yet. Install the Tailscale app on your phone, sign in with the same account as this PC and switch it on. Without it, the phone cannot open the address.</Notice>
  }
  const names = (list: TailnetPhone[]) => list.map((phone) => phone.name).join(', ')
  const online = phones.filter((phone) => phone.online)
  if (online.length === 0) {
    return <Notice tone="warning">Tailscale is switched off on {names(phones)}. Open the Tailscale app on the phone and switch it on before you scan the code.</Notice>
  }
  const offline = phones.filter((phone) => !phone.online)
  return <p className="subtle">Connected to Tailscale now: {names(online)}.{offline.length > 0 && ` Not connected: ${names(offline)}.`}</p>
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
        <details className="phone-help">
          <summary>If nothing opens on the phone</summary>
          <ol>
            <li>Open the Tailscale app on the phone and check it is switched on and signed in to the same account as this PC.</li>
            <li>The first visit can take up to a minute while Tailscale sets up the secure address. Wait, then reload the page.</li>
            {pairing.backup_link && <li>Still nothing? Open <strong>{pairing.backup_link}</strong> on the phone instead. It skips the name lookup and works the same, except that phone notifications need the first address.</li>}
            <li>If only that backup address works, the phone looks up names without Tailscale. On Android, set Settings &gt; Network &amp; internet &gt; Private DNS to Automatic or Off. In the Tailscale app, keep Use Tailscale DNS on.</li>
          </ol>
        </details>
      </div>
    </div>
  )
}

function Linked({ text }: { text: string }) {
  return <>{linkParts(text).map((part, index) => part.link ? <a key={index} className="text-button" href={part.text} target="_blank" rel="noreferrer">{part.text}</a> : <span key={index}>{part.text}</span>)}</>
}
