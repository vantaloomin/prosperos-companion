import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../../api'
import { Notice } from '../../../components/Feedback'
import { HARDWARE_KEY, gb, useHardware, type HardwareReport, type HardwareWarning } from './hardware'

/** Settings > Models: the graphics card and memory, what fits, and setups that will run badly. */
export function HardwareCheck() {
  const client = useQueryClient()
  const query = useHardware()
  const [busy, setBusy] = useState(false)
  const data = query.data
  if (!data) return null
  const { computer } = data
  const again = async () => {
    setBusy(true)
    try { client.setQueryData(HARDWARE_KEY, await api<HardwareReport>('/hardware?fresh=true')) } finally { setBusy(false) }
  }
  return <section className="settings-section form-stack" aria-labelledby="hardware-heading">
    <div>
      <h2 id="hardware-heading">This computer</h2>
      <p className="subtle">What models running on this computer can expect, from its graphics card and memory. Sizes are rough estimates from model names.</p>
    </div>
    <ul className="plain-list hardware-summary">
      {computer.gpus.map(gpu => <li key={gpu.index}>{gpu.name}: {gb(gpu.memory_gb)}{gpu.used_gb != null && `, ${gb(gpu.used_gb)} in use now`}</li>)}
      <li>Memory: {computer.memory_gb ? gb(computer.memory_gb) : 'unknown'}, {computer.cores} processor threads</li>
      {computer.gpu_note && <li>{computer.gpu_note}</li>}
    </ul>
    <ul className="plain-list">{data.can_run.map(line => <li key={line}>{line}</li>)}</ul>
    <HardwareWarnings warnings={data.warnings} />
    <div className="form-actions"><button type="button" className="button" disabled={busy} onClick={() => void again()}>{busy ? 'Checking…' : 'Check again'}</button></div>
  </section>
}

/** Warnings for the setup in use; `area` keeps only those about one part, such as pictures. */
export function HardwareWarnings({ warnings, area }: { warnings: HardwareWarning[]; area?: HardwareWarning['area'] }) {
  const shown = area ? warnings.filter(warning => warning.area === area) : warnings
  return <>{shown.map(warning => <Notice key={warning.text} tone={warning.tone === 'warning' ? 'warning' : 'info'}>{warning.text}</Notice>)}</>
}
