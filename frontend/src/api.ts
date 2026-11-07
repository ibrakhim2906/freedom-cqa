export async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, body === undefined ? undefined : {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({detail: response.statusText}))
    const detail = Array.isArray(error.detail) ? error.detail.map((e: {loc?: string[]; msg: string}) => `${e.loc?.join('.')}: ${e.msg}`).join('; ') : error.detail
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return response.json()
}
