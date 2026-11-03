import { useLifeSettings } from './useLifeSettings'
import { Notice } from '../../components/Feedback'
import { CountStepper, RowGroup, SettingRow, SwitchRow } from '../../components/Rows'
import { presetOptions } from '../../components/numberBounds'
import { countText, hoursText, minutesText } from '../../components/numberBounds'
import { SectionPending } from '../../components/SectionPending'

type NumberKey = 'catch_up_max_events' | 'catch_up_lookback_hours' | 'return_gap_hours' | 'background_interval_minutes' | 'background_daily_events' | 'texts_daily' | 'away_daily' | 'texts_gap_hours' | 'circle_size' | 'recap_after_days'

type Format = (value: number) => string
const counted = (one: string, many: string, zero?: string): Format => (value) => countText(value, one, many, zero)
const every: Format = (minutes) => ({ 60: 'Every hour', 1440: 'Once a day' })[minutes] ?? `Every ${minutesText(minutes)}`

// Iris's number controls (/mnt/project-files/companion-design/number-controls.md): steppers for small counts,
// friendly presets for time spans. Each saves on change; the server still checks the range. Grouped by topic with
// short labels, since the group title carries the context (Iris, step 11 review).
type NumberRow = { name: NumberKey; label: string; format: Format; tip?: string; nested?: boolean } & ({ min: number; max: number } | { presets: number[] })
const CATCHING_UP: NumberRow[] = [
  { name: 'return_gap_hours', label: "After you've been away", presets: [1, 2, 4, 8, 12, 24, 48], format: hoursText, nested: true },
  { name: 'catch_up_lookback_hours', label: 'How far back', presets: [6, 12, 24, 48, 72, 168, 336], format: hoursText, tip: 'Older time away stays quiet.', nested: true },
  { name: 'catch_up_max_events', label: 'Most events', min: 0, max: 6, format: counted('event', 'events', 'None'), tip: 'However long you were away.', nested: true },
  { name: 'recap_after_days', label: '"While you were away" after', presets: [0, 1, 2, 3, 5, 7, 14, 30, 60], format: counted('day', 'days', 'Off'), tip: 'Shown once in the chat when you come back: what happened in their life and around town.' },
]
const BACKGROUND: NumberRow[] = [
  { name: 'background_interval_minutes', label: 'Updates', presets: [15, 30, 60, 120, 240, 480, 1440], format: every },
  { name: 'background_daily_events', label: 'Most events a day', min: 0, max: 8, format: counted('event', 'events', 'None') },
  { name: 'circle_size', label: 'People in their circle', min: 0, max: 12, format: counted('person', 'people', 'Automatic'), tip: 'Automatic decides by how sociable they are: 4 for a homebody, 5 usually, 10 for a social butterfly. Add people from Today.' },
]
const FIRST_MESSAGES: NumberRow[] = [
  { name: 'texts_daily', label: 'Most a day, each', min: 1, max: 6, format: counted('message', 'messages'), nested: true },
  { name: 'away_daily', label: 'Most a day, all together', min: 0, max: 40, format: counted('message', 'messages', 'Off'), tip: 'Shared by every companion, so a day with the app left running stays within what you want to spend on your model.', nested: true },
  { name: 'texts_gap_hours', label: 'Quiet hours after talking', presets: [1, 2, 3, 4, 6, 8, 12, 24], format: hoursText, tip: 'How long after you last talked before they message first.', nested: true },
]

/** Settings > World > Life (style guide): app-wide, so it names no companion (Iris). Three groups, Catching up, In
 * the background and First messages, each a switch or two with its numbers as rows. Your birthday is in Worlds > You. */
export function LifeSettings({ name }: { name: string }) {
  const { settings, data, save, result } = useLifeSettings()
  if (!data) return <SectionPending queries={[settings]} heading="life-heading" title={`${name}'s life`} />
  const rows = (list: NumberRow[]) => list.map((row) => <NumberSetting key={row.name} row={row} value={data[row.name]} onChange={(value) => void save({ [row.name]: value }, 'Saved.')} />)
  return (
    <section className="form-stack" aria-labelledby="life-heading">
      <RowGroup id="life-catching-up" label="Catching up">
        <SwitchRow label="Catch up when you return" checked={data.catch_up_on_return} onChange={(value) => void save({ catch_up_on_return: value })}
          tip="Off: nothing is written for the time you were away, and their life picks up from when you return.">
          {rows(CATCHING_UP.filter((row) => row.nested))}
        </SwitchRow>
        {rows(CATCHING_UP.filter((row) => !row.nested))}
      </RowGroup>
      <RowGroup id="life-background" label="In the background">
        <SwitchRow label="Add everyday events without asking" checked={data.automatic_events} onChange={(value) => void save({ automatic_events: value })}
          tip="On unless you turn it off: their days just happen, and you can correct anything afterwards. Off: new events wait in Today for you to keep or discard." />
        <SwitchRow label="Let the model word their days" checked={data.phrase_with_model} onChange={(value) => void save({ phrase_with_model: value })}
          tip="What happens is always built from their routine and city. With this on, your model rewrites it in their voice; off, plain wording is used and no model calls are made." />
        <SwitchRow label="Let the model add what's on their mind" checked={data.model_routines} onChange={(value) => void save({ model_routines: value })}
          tip="Once a week, your model adds a few things on their mind, drawn from who they are. Their routine, work and plans stay as the app set them. One model call a week, for the companion you have open." />
        {rows(BACKGROUND)}
      </RowGroup>
      <RowGroup id="life-first-messages" label="First messages">
        <SwitchRow label="Companions can message you first" checked={data.texts_first} onChange={(value) => void save({ texts_first: value })}
          tip={'They may start a conversation: to check in on a break or after work, to ask about something they said they\'d ask about, how a plan of yours went, to share news from their day, or when something reminds them of you. Never during your quiet hours, while they sleep or twice without an answer, and even while you are chatting with someone else. Written by your chat model, so each first message is a model call. They count toward the limits below, even when "Let the model word their days" is off.'}>
          {rows(FIRST_MESSAGES)}
        </SwitchRow>
      </RowGroup>
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
    </section>
  )
}

/** One number as a row: a stepper for a small count, a select of friendly presets for a time span. */
function NumberSetting({ row, value, onChange }: { row: NumberRow; value: number; onChange: (value: number) => void }) {
  return (
    <SettingRow label={row.label} tip={row.tip} nested={row.nested}>
      {(id, disabled) => 'presets' in row
        ? <select id={id} value={value} disabled={disabled} onChange={(event) => onChange(Number(event.target.value))}>
          {presetOptions(row.presets, value, row.format).map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
        : <CountStepper id={id} label={row.label} value={value} min={row.min} max={row.max} format={row.format} disabled={disabled} onChange={onChange} />}
    </SettingRow>
  )
}
