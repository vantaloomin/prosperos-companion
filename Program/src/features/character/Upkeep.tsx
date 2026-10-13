import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { useWorkspaceSettings } from '../../companion'
import type { UpkeepHabit, UpkeepView } from '../../types'
import { Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { Field } from '../../components/Fields'
import { HABIT_CHOICES, lastClean, numbersText, upkeepSummary } from './upkeepText'

const UPKEEP_KEY = ['upkeep']

/** Housework at their place (companion/life/upkeep.py): how it is today in words, Set it, and their habit. */
export function Upkeep({ name }: { name: string }) {
  const client = useQueryClient()
  const upkeep = useQuery({ queryKey: UPKEEP_KEY, queryFn: () => api<UpkeepView>('/life/upkeep') })
  const numbers = useWorkspaceSettings().data?.show_home_meters === true
  const [feedback, setFeedback] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const save = async (change: { tidiness?: number; habit?: UpkeepHabit | 'auto' }, done: string) => {
    try {
      client.setQueryData(UPKEEP_KEY, await api<UpkeepView>('/life/upkeep', change, 'PUT'))
      setFeedback({ tone: 'info', text: done })
    } catch (error) {
      setFeedback({ tone: 'error', text: error instanceof Error ? error.message : 'That change was not saved.' })
    }
  }
  if (upkeep.isError) return <ErrorNotice error={upkeep.error} />
  if (!upkeep.data) return null
  const view = upkeep.data
  if (!view.on) {
    return (
      <div className="upkeep">
        <h3>Housework</h3>
        <p className="subtle">Housework is off, so their place stays as it is. Turn it on in <a href="#settings/realism">Settings &gt; Realism</a>.</p>
      </div>
    )
  }
  const last = lastClean(view)
  return (
    <div className="upkeep">
      <h3>Housework</h3>
      <p>{upkeepSummary(view)}</p>
      <p className="subtle">{name} {view.habit_text}.{last && <> Last big clean: <span title={last.date}>{last.when}</span>.</>}</p>
      {numbers && (
        <p className="upkeep-numbers subtle" title="Higher is messier">{numbersText(view.areas)}</p>
      )}
      <div className="upkeep-controls">
        <Field label="How tidy it is now" hint="How tidy their place is today. It drifts with their week after that.">{(id, describedBy) => (
          <select id={id} aria-describedby={describedBy} value={view.tidiness}
            onChange={(event) => void save({ tidiness: Number(event.target.value) }, `Saved. ${name}'s place is ${view.levels[Number(event.target.value)].toLowerCase()} today.`)}>
            {view.levels.map((label, index) => <option key={label} value={index}>{label}</option>)}
          </select>
        )}</Field>
        <Field label="Their habit" hint="How much they let build up before dealing with it.">{(id, describedBy) => (
          <select id={id} aria-describedby={describedBy} value={view.habit_set ? view.habit : 'auto'}
            onChange={(event) => void save({ habit: event.target.value as UpkeepHabit | 'auto' }, 'Saved. Their days ahead follow it.')}>
            <option value="auto">{view.habit_set ? 'Picked by the app' : `Picked by the app (${HABIT_CHOICES[view.habit]})`}</option>
            {(Object.keys(HABIT_CHOICES) as UpkeepHabit[]).map((habit) => <option key={habit} value={habit}>{HABIT_CHOICES[habit]}</option>)}
          </select>
        )}</Field>
      </div>
      <div aria-live="polite">{feedback && <Notice tone={feedback.tone}>{feedback.text}</Notice>}</div>
    </div>
  )
}
