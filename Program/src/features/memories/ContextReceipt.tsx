import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { ContextPreview, Memory } from '../../types'
import { Loading } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { PREVIEW_KEY, budgetShare, receiptRows, type ReceiptRow } from './receiptRows'


/** What the next reply would be built from, so a correction or exclusion can be seen taking effect (PRD M10). */
export function ContextReceipt({ name, memories }: { name: string; memories: Memory[] }) {
  const [open, setOpen] = useState(false)
  const preview = useQuery({ queryKey: PREVIEW_KEY, queryFn: () => api<ContextPreview>('/context/preview'), enabled: open, staleTime: 0 })
  return (
    <details className="context-receipt" onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary>What {name}'s next reply uses</summary>
      {preview.isPending && open && <Loading label="Working out the next reply's context" />}
      {preview.isError && <ErrorNotice error={preview.error} />}
      {preview.isSuccess && <ReceiptBody preview={preview.data} name={name} memories={memories} />}
    </details>
  )
}

function ReceiptBody({ preview, name, memories }: { preview: ContextPreview; name: string; memories: Memory[] }) {
  const { receipt } = preview
  const rows = receiptRows(receipt, memories, name)
  const share = budgetShare(receipt)
  const leftOut = rows.some((row) => row.omitted > 0)
  return (
    <div className="receipt-body">
      <p className="subtle">
        About {receipt.estimated_tokens.toLocaleString()} of {receipt.budget_tokens.toLocaleString()} tokens ({share}%) of the space your model connection allows.
        Excluded memories never appear here.
      </p>
      <div className="receipt-meter" role="img" aria-label={`${share}% of the context allowance used`}><span style={{ width: `${share}%` }} /></div>
      <ul className="receipt-rows">{rows.map((row) => <Row key={row.key} row={row} />)}</ul>
      {leftOut && <p className="subtle">Items marked “left out” did not fit. A larger context allowance in Settings makes room for them.</p>}
      <details className="receipt-raw">
        <summary>Exact instructions sent to the model</summary>
        <pre>{preview.system}</pre>
        <p className="subtle">Followed by the last {preview.history.length} messages of your conversation. These notes go with the latest one:</p>
        <pre>{preview.note}</pre>
      </details>
    </div>
  )
}

function Row({ row }: { row: ReceiptRow }) {
  return (
    <li>
      <span className="receipt-label">{row.label}</span>
      <span className="receipt-detail">
        {row.detail}
        {row.omitted > 0 && <span className="receipt-omitted"> · {row.omitted} left out</span>}
      </span>
    </li>
  )
}
