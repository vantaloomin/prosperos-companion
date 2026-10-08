// Request helper adapted from prosperos-study src/api.ts at bbcbde4: Companion header and error codes.
export class ApiError extends Error {
  constructor(message: string, public status: number, public code?: string) { super(message) }
}

function errorMessage(status: number, data: { detail?: unknown }): string {
  if (typeof data.detail === 'string') return data.detail
  if (Array.isArray(data.detail)) return data.detail.map((item) => item.msg).join('; ')
  return `The Companion could not finish that (error ${status}). Please try again.`
}

export async function api<T>(path: string, body?: unknown, method?: string): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, {
      method: method ?? (body === undefined ? 'GET' : 'POST'),
      headers: { 'Content-Type': 'application/json', 'X-Companion-Client': 'workspace' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError('Cannot reach the Companion. Check that it is still running.', 0, 'offline')
  }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw failure(response.status, data)
  return data as T
}

/** A phone whose pairing was removed on the PC goes back to the pairing screen (src/features/phone). */
function failure(status: number, data: { detail?: unknown; code?: string }): ApiError {
  if (data.code === 'phone_unpaired') window.dispatchEvent(new Event('companion:unpaired'))
  return new ApiError(errorMessage(status, data), status, data.code)
}

export { newId } from './ids.ts'

/** Send a file as the request body, with its details in the query string. */
export async function upload<T>(path: string, file: Blob, params: Record<string, string>): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}?${new URLSearchParams(params)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/octet-stream', 'X-Companion-Client': 'workspace' },
      body: file,
    })
  } catch {
    throw new ApiError('Cannot reach the Companion. Check that it is still running.', 0, 'offline')
  }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw failure(response.status, data)
  return data as T
}
