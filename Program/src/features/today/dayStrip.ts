/**
 * Today's day strip: their routine across their own calendar day (GET /life/routine `today`), as segments placed on a
 * 24-hour line in their time zone, with where "now" falls. Worked out here from the slots, no model.
 */
export interface DaySlot { starts_at: string; ends_at: string; block: { label: string; kind: string } }
export interface Segment { label: string; kind: string; left: number; width: number }

const DAY = 24 * 60

/** The calendar day and the minute of that day an instant falls on where they live. */
export function localParts(iso: string, timeZone: string): { date: string; minutes: number } {
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
    .formatToParts(new Date(iso)).map((part) => [part.type, part.value]))
  return { date: `${parts.year}-${parts.month}-${parts.day}`, minutes: Number(parts.hour) * 60 + Number(parts.minute) }
}

/** Where a slot edge sits on the day's line, in minutes: before the day starts at 0, after it ends at 24 hours. */
function edge(iso: string, day: string, timeZone: string): number {
  const at = localParts(iso, timeZone)
  return at.date < day ? 0 : at.date > day ? DAY : at.minutes
}

/** The day's segments as percentages of the line, in order, and where now sits. */
export function daySegments(slots: DaySlot[], now: string, timeZone: string): { segments: Segment[]; now: number } {
  const here = localParts(now, timeZone)
  const segments = slots.flatMap((slot) => {
    const start = edge(slot.starts_at, here.date, timeZone)
    const end = edge(slot.ends_at, here.date, timeZone)
    return end > start ? [{ label: slot.block.label, kind: slot.block.kind, left: (start / DAY) * 100, width: ((end - start) / DAY) * 100 }] : []
  })
  return { segments, now: (here.minutes / DAY) * 100 }
}

/** Whether a part of the strip is wide enough for its whole name, about 7px a letter plus padding, on a strip
 * `width` pixels wide. */
export function labelFits(segment: Pick<Segment, 'label' | 'width'>, width: number): boolean {
  return (segment.width / 100) * width >= segment.label.length * 7 + 14
}

/** Whether a part's name stays clear of the line at now (`now` in percent), so the line is never drawn through it. */
export function clearOfNow(segment: Pick<Segment, 'label' | 'left'>, width: number, now: number): boolean {
  if (!width) return true
  const start = (segment.left / 100) * width
  const end = start + segment.label.length * 7 + 14
  const at = (now / 100) * width
  return at < start || at > end
}
