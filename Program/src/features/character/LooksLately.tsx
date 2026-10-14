import { calendarDay } from '../../when.ts'
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { GroomingView } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { Toggle } from '../../components/Fields'
import { LOOKS_KEY, changeLine, fixedLine } from './looksLatelyText'
import { firstName } from './panelText'

/** How the companion looks lately: haircuts, nails, a tan and the occasional bold change, in words, with a switch to
 * keep their looks as they are. The numbers behind it show only with Hidden values on. */
export function LooksLately({ name }: { name: string }) {
  const client = useQueryClient()
  const looks = useQuery({ queryKey: LOOKS_KEY, queryFn: () => api<GroomingView>('/life/grooming') })
  const [error, setError] = useState('')
  const keep = async (kept: boolean) => {
    setError('')
    try { client.setQueryData(LOOKS_KEY, await api<GroomingView>('/life/grooming', { kept }, 'PUT')) }
    catch (failure) { setError(failure instanceof Error ? failure.message : 'That change was not saved.') }
  }
  const view = looks.data
  return (
    <section className="home-panel looks-panel" aria-labelledby="looks-lately-heading">
      <h2 id="looks-lately-heading">How {firstName(name)} looks lately</h2>
      <p className="subtle">Hair grows and gets cut, nails get done, a tan comes and fades, and every few months they try something new. Pictures and replies follow it. Anything you wrote about their looks stays as you wrote it.</p>
      {looks.isPending && <Loading label="Loading how they look" />}
      {looks.isError && <ErrorNotice error={looks.error} />}
      {view && <LooksBody view={view} name={name} keep={keep} error={error} />}
    </section>
  )
}

function LooksBody({ view, name, keep, error }: { view: GroomingView; name: string; keep: (kept: boolean) => Promise<void>; error: string }) {
  const fixed = fixedLine(view.fixed)
  return <>
    {view.level === 0 && <Notice tone="info">Looks don&apos;t change in this world. You can turn it back on in <a href="#settings/realism">Settings &gt; Realism</a>.</Notice>}
    {view.lines.length > 0 && (
      <dl className="looks-lines">{view.lines.map((line) => (
        <div key={line.label}><dt>{line.label}</dt><dd>{line.text}</dd></div>
      ))}</dl>
    )}
    {fixed && <p className="subtle">{fixed}</p>}
    {view.lora && <p className="subtle">Their pictures use a trained look, so only small changes happen: trims, nails and a tan, nothing bold.</p>}
    {view.numbers && (
      <dl className="looks-lines looks-numbers" aria-label="Numbers">{view.numbers.map((item) => (
        <div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>
      ))}</dl>
    )}
    <Toggle label="Let their looks change" checked={!view.kept} onChange={(checked) => void keep(!checked)}
      hint={view.kept ? `${name} keeps the look they have on their form. Changes already made are set aside.` : `On their own schedule, the way ${name} would. Turn off to keep their look as it is on their form.`} />
    {error && <Notice tone="error">{error}</Notice>}
    {view.changes.length > 0 && (
      <div className="home-changes">
        <h3>Recent changes</h3>
        <ul className="looks-changes">{view.changes.map((change) => (
          <li key={`${change.local_date}-${change.kind}`}>
            <time dateTime={change.local_date}>{calendarDay(change.local_date)}</time>
            <span>{changeLine(change.text)}{change.bold && <span className="badge looks-bold">Something new</span>}</span>
          </li>
        ))}</ul>
      </div>
    )}
  </>
}
