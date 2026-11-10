import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, X } from 'lucide-react'
import { api } from '../../api'
import { Notice } from '../../components/Feedback'
import { InfoTip } from '../../components/InfoTip'
import { SectionPending } from '../../components/SectionPending'
import { caughtNote, caughtTitle, OWN_WORDS_KEY, ruleNote, shownPhrase, type OwnWordsData } from './wordRulesText'

/** Their own words (companion/memory/own_words.py, Hit List #97): wording caught lately in the current companion's
 * replies, each with Keep (a catchphrase, never flagged again) and Dismiss, and the user's own short list of words
 * to drop or swap after a reply is written. The list starts empty and nothing asks to fill it. */

const quote = (phrase: string) => `“${phrase}”`

export function OwnWords({ name }: { name: string }) {
  const client = useQueryClient()
  const words = useQuery({ queryKey: OWN_WORDS_KEY, queryFn: () => api<OwnWordsData>('/own-words') })
  const [problem, setProblem] = useState('')
  if (!words.data) return <SectionPending queries={[words]} heading="own-words-heading" title="Their own words" />
  const data = words.data
  const change = async (path: string, body?: unknown, method?: string) => {
    setProblem('')
    try { client.setQueryData(OWN_WORDS_KEY, await api<OwnWordsData>(path, body, method)); return true }
    catch (failure) { setProblem(failure instanceof Error ? failure.message : 'That was not saved.'); return false }
  }
  const listed = data.rules.length
  return (
    <section className="settings-section row-group own-words" aria-labelledby="own-words-heading">
      <h2 id="own-words-heading" className="section-title">Their own words<InfoTip id="own-words-tip" label="Their own words"
        text={`Stock phrases and habits in ${name || 'their'} replies are pointed out to them from the first time. One that keeps coming back after that is taken out of their next replies. Words on your list are dropped or swapped once a reply is written.`} /></h2>
      <h3 className="row-group-label">{caughtTitle(name)}</h3>
      <div className="row-list">
        {data.caught.length === 0
          ? <p className="setting-row row-empty">Nothing caught lately.</p>
          : <ul className="backend-list">{data.caught.map((item) => (
            <li key={item.phrase} className="setting-row own-words-row">
              <span className="setting-row-label own-words-phrase"><span className="own-words-text">{quote(shownPhrase(item.phrase))}</span><span className="own-words-note">{caughtNote(item)}</span></span>
              <span className="own-words-actions">
                <button type="button" className="text-button" title="Their own phrase. Never flagged again." disabled={listed >= data.limit} onClick={() => void change('/own-words', { phrase: item.phrase, action: 'keep' })}>Keep</button>
                <button type="button" className="text-button" title="Not a problem this time." onClick={() => void change('/own-words', { phrase: item.phrase, action: 'dismiss' })}>Dismiss</button>
              </span>
            </li>))}</ul>}
      </div>
      <h3 className="row-group-label">Your list <span className="own-words-count">{listed} of {data.limit}</span></h3>
      <div className="row-list">
        {listed > 0 && <ul className="backend-list">{data.rules.map((rule) => (
          <li key={rule.id} className="setting-row own-words-row">
            <span className="setting-row-label own-words-phrase"><span className="own-words-text">{quote(rule.phrase)}</span><span className="own-words-note">{ruleNote(rule)}</span></span>
            <button type="button" className="icon-button own-words-remove" aria-label={`Remove ${quote(rule.phrase)}`} onClick={() => void change(`/own-words/${rule.id}`, undefined, 'DELETE')}><X aria-hidden="true" /></button>
          </li>))}</ul>}
        <AddRule full={listed >= data.limit} add={(body) => change('/own-words', body)} />
      </div>
      {problem && <Notice tone="error">{problem}</Notice>}
    </section>
  )
}

function AddRule({ full, add }: { full: boolean; add: (body: object) => Promise<boolean> }) {
  const [phrase, setPhrase] = useState('')
  const [action, setAction] = useState<'drop' | 'swap'>('drop')
  const [replacement, setReplacement] = useState('')
  const [everyone, setEveryone] = useState(false)
  const submit = async () => {
    if (!phrase.trim() || full) return
    if (await add({ phrase, action, replacement: action === 'swap' ? replacement : '', everyone })) {
      setPhrase(''); setReplacement('')
    }
  }
  return (
    <form className="setting-row own-words-add" onSubmit={(event) => { event.preventDefault(); void submit() }}>
      <input autoComplete="off" value={phrase} maxLength={120} aria-label="Word or phrase" placeholder="A word, a phrase or —" disabled={full} onChange={(event) => setPhrase(event.target.value)} />
      <select aria-label="What to do with it" value={action} disabled={full} onChange={(event) => setAction(event.target.value as 'drop' | 'swap')}>
        <option value="drop">Drop it</option>
        <option value="swap">Swap for</option>
      </select>
      {action === 'swap' && <input autoComplete="off" value={replacement} maxLength={120} aria-label="Swap for" placeholder="Instead" disabled={full} onChange={(event) => setReplacement(event.target.value)} />}
      <select aria-label="Where" value={everyone ? 'everyone' : 'world'} disabled={full} onChange={(event) => setEveryone(event.target.value === 'everyone')}>
        <option value="world">This world</option>
        <option value="everyone">Every world</option>
      </select>
      <button type="submit" className="text-button add-button own-words-submit" disabled={full || !phrase.trim()}><Plus aria-hidden="true" />Add</button>
    </form>
  )
}
