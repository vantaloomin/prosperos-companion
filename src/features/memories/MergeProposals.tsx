import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Combine, X } from 'lucide-react'
import { api } from '../../api'
import type { MergeProposal } from '../../types'

const PROPOSALS_KEY = ['memory-proposals']

/** Near-identical memories found by background tidying. Nothing merges until you choose to. */
export function MergeProposals({ run }: { run: <T>(action: () => Promise<T>, done: string) => Promise<T | null> }) {
  const client = useQueryClient()
  const proposals = useQuery({ queryKey: PROPOSALS_KEY, queryFn: () => api<MergeProposal[]>('/memory/proposals') })
  if (!proposals.data?.length) return null
  const decide = async (proposal: MergeProposal, merge: boolean) => {
    await run(() => api(`/memory/proposals/${proposal.id}/${merge ? 'accept' : 'decline'}`, {}),
      merge ? `Merged into “${proposal.keep.value}”. The other wording is kept as history.` : 'Both are kept, and this pair won\'t be suggested again.')
    await client.invalidateQueries({ queryKey: PROPOSALS_KEY })
  }
  return (
    <section className="memory-group" aria-labelledby="proposals-heading">
      <h2 id="proposals-heading">Possible duplicates</h2>
      <p className="subtle">These look like the same memory. Merging keeps the newer wording with both sources.</p>
      <ul className="memory-list">
        {proposals.data.map((proposal) => (
          <li key={proposal.id} className="memory">
            <div className="memory-main">
              <p className="memory-subject">{proposal.keep.subject}</p>
              <p className="memory-value">{proposal.keep.value}</p>
              <p className="memory-meta"><span>Also remembered as: {proposal.merge.value}</span></p>
            </div>
            <div className="memory-actions" role="group" aria-label={`Decide about ${proposal.keep.subject}`}>
              <button type="button" className="text-button" onClick={() => void decide(proposal, true)}><Combine aria-hidden="true" />Merge</button>
              <button type="button" className="text-button" onClick={() => void decide(proposal, false)}><X aria-hidden="true" />Keep both</button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
