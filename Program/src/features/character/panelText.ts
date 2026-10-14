/** The companion's first name, which every Character panel heading uses ("Dana's kitchen", "How Dana looks lately"). */
export function firstName(name: string): string {
  return name.trim().split(/\s+/)[0] || name
}

/** A Character panel heading by first name: "Dana's work life". */
export function panelTitle(name: string, what: string): string {
  return `${firstName(name)}'s ${what}`
}
