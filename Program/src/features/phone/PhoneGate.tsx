import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Smartphone } from 'lucide-react'
import { api } from '../../api'
import { Loading, Notice } from '../../components/Feedback'
import { Field, TextInput } from '../../components/Fields'
import { codeFromAddress, guessDeviceName } from './pairing'
import { PHONE_STATUS_KEY, UNPAIRED_EVENT, usePhoneStatus } from './phoneAccess'

/**
 * On this PC the app opens as always. A phone reaching it through Tailscale pairs first, with the code
 * shown in Settings > Phone access, and returns here if its pairing is removed.
 */
export function PhoneGate({ children }: { children: ReactNode }) {
  const status = usePhoneStatus()
  useEffect(() => {
    // Reloading drops everything this phone had loaded before its pairing was removed.
    const unpaired = () => window.location.reload()
    window.addEventListener(UNPAIRED_EVENT, unpaired)
    return () => window.removeEventListener(UNPAIRED_EVENT, unpaired)
  }, [])
  if (status.isPending) return <div className="gate"><Loading label="Opening your companion" /></div>
  if (status.isError) return <div className="gate"><Notice tone="error">{status.error.message}</Notice></div>
  if (status.data.remote && !status.data.paired) return <PairScreen />
  return children
}

function PairScreen() {
  const client = useQueryClient()
  const [code, setCode] = useState(() => codeFromAddress(window.location.search))
  const [name, setName] = useState(() => guessDeviceName(navigator.userAgent))
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (busy) return
    setBusy(true)
    setError('')
    try {
      await api('/phone/pair', { code, name })
      window.history.replaceState(null, '', window.location.pathname + window.location.hash)
      await client.invalidateQueries({ queryKey: PHONE_STATUS_KEY })
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'That did not work. Try again.')
    } finally { setBusy(false) }
  }
  return (
    <main className="gate">
      <form className="gate-card form-stack" onSubmit={(event) => void submit(event)}>
        <Smartphone aria-hidden="true" className="gate-icon" />
        <h1>Pair this phone</h1>
        <p className="subtle">On your PC, open Settings &gt; Phone access and choose Pair a phone. Scan the code with this phone, or type the code shown under it.</p>
        {error && <Notice tone="error">{error}</Notice>}
        <Field label="Pairing code" hint="Letters and numbers, shown under the QR code on your PC. It works once and expires after 10 minutes.">
          {(id, hint) => <input id={id} aria-describedby={hint} value={code} onChange={(event) => setCode(event.target.value)} autoCapitalize="characters" autoComplete="one-time-code" spellCheck={false} placeholder="ABCD-EFGH" required />}
        </Field>
        <TextInput label="Name for this phone" hint="Shown in the list of paired phones on your PC." value={name} onChange={setName} maxLength={80} />
        <div className="form-actions"><button type="submit" className="button primary" aria-disabled={busy}>Pair</button></div>
      </form>
    </main>
  )
}
