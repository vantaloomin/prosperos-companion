/** Keeps a typed number inside its range. While typing only the top is enforced, so "15" can be typed
 * through "1" when the least is 10; `leaving` (the box lost focus) enforces the bottom too. Blank stays blank. */
export function bounded(value: string, min?: number, max?: number, leaving = false): string {
  const number = Number(value)
  if (value.trim() === '' || !Number.isFinite(number)) return value
  if (max !== undefined && number > max) return String(max)
  if (leaving && min !== undefined && number < min) return String(min)
  return value
}
