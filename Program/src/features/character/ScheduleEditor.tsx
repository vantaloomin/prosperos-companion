import { Plus, X } from 'lucide-react'
import { DAYS, KINDS, newBlock, starterSchedule, toggleDay, type BlockKind, type RoutineBlock } from './schedule'

export function ScheduleEditor({ blocks, onChange, timezone }: { blocks: RoutineBlock[]; onChange: (blocks: RoutineBlock[]) => void; timezone: string }) {
  const set = (index: number, change: Partial<RoutineBlock>) => onChange(blocks.map((block, position) => position === index ? { ...block, ...change } : block))
  return (
    <fieldset className="traits schedule">
      <legend>Weekly routine</legend>
      <p className="subtle">The shape of their week, in their time ({timezone}). Their life follows it: nothing happens while they sleep, and work or sleep explains a slow reply without ever stopping you from writing. A block that ends before it starts runs past midnight.</p>
      {blocks.length === 0 && (
        <p className="subtle">They follow a gentle default day until you describe one. <button type="button" className="text-button inline" onClick={() => onChange(starterSchedule())}>Start from a typical week</button></p>
      )}
      {blocks.map((block, index) => (
        <div className="schedule-row" key={index} role="group" aria-label={block.label || `Block ${index + 1}`}>
          <input aria-label="Name" value={block.label} maxLength={120} placeholder="Bakery shift" onChange={(event) => set(index, { label: event.target.value })} />
          <select aria-label="Kind" value={block.kind} onChange={(event) => set(index, { kind: event.target.value as BlockKind })}>
            {KINDS.map((kind) => <option key={kind.id} value={kind.id}>{kind.label}</option>)}
          </select>
          <input aria-label="Starts" type="time" value={block.start} onChange={(event) => set(index, { start: event.target.value })} />
          <input aria-label="Ends" type="time" value={block.end} onChange={(event) => set(index, { end: event.target.value })} />
          <button type="button" className="icon-button" aria-label={`Remove ${block.label || 'block'}`} onClick={() => onChange(blocks.filter((_, position) => position !== index))}><X aria-hidden="true" /></button>
          <div className="day-picks" role="group" aria-label="Days">
            {DAYS.map((day, number) => (
              <label key={day} className="day-pick"><input type="checkbox" checked={block.days.includes(number)} onChange={() => set(index, { days: toggleDay(block.days, number) })} /><span>{day}</span></label>
            ))}
          </div>
          <input className="schedule-themes" aria-label="Themes (optional)" value={block.themes.join(', ')} placeholder="Themes, such as regulars, new recipes (optional)"
            onChange={(event) => set(index, { themes: event.target.value.split(',') })} />
        </div>
      ))}
      {blocks.length > 0 && blocks.length < 24 && <button type="button" className="text-button" onClick={() => onChange([...blocks, newBlock()])}><Plus aria-hidden="true" />Add a block</button>}
    </fieldset>
  )
}
